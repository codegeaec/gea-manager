import subprocess

import pytest

from gea import paths, ui
from gea.agents import delegate, log, worktree
from gea.tasks import store


@pytest.fixture
def repo(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"},"verify":[]}')
    (tmp_path / "a.py").write_text("one\n")
    git("add", "a.py")
    git("commit", "-qm", "init")
    return tmp_path


@pytest.fixture
def fake_herdr(monkeypatch, repo):
    """herdr's worktree commands, implemented with real git."""
    calls = []

    def herdr_json(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["worktree", "create"]:
            opt = dict(zip(cmd[2::2], cmd[3::2], strict=False))
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "-b", opt["--branch"], opt["--path"],
                 opt["--base"]],
                check=True, capture_output=True,
            )
            return {"workspace": {"workspace_id": "w9"}}, None
        if cmd[:2] == ["worktree", "remove"]:
            path = paths.gea_home() / "worktrees" / repo.name
            for child in path.iterdir():
                subprocess.run(
                    ["git", "-C", str(repo), "worktree", "remove", "--force", str(child)],
                    check=True, capture_output=True,
                )
            return {}, None
        return {}, None

    monkeypatch.setattr(worktree.herdr, "herdr_json", herdr_json)
    return calls


def test_create_uses_a_deterministic_path_and_copies_config(repo, fake_herdr):
    wt = worktree.create("TASK-001", repo)
    assert wt.branch == "gea/task-001" and wt.workspace_id == "w9"
    assert wt.path == paths.gea_home() / "worktrees" / repo.name / "task-001"
    assert (wt.path / "gea.json").exists()  # untracked config travels along
    assert wt.slug == "001"


def test_create_failure_leaves_nothing_behind(repo, monkeypatch):
    monkeypatch.setattr(worktree.herdr, "herdr_json", lambda cmd, timeout=15: ({}, "boom"))
    assert worktree.create("TASK-001", repo) is None
    assert not (paths.gea_home() / "worktrees").exists()


def test_changed_files_ignores_copied_config_and_commit_all_keeps_it_out(repo, fake_herdr):
    wt = worktree.create("TASK-001", repo)
    (wt.path / "a.py").write_text("two\n")
    (wt.path / "new.py").write_text("x\n")
    assert worktree.changed_files(wt) == ["a.py", "new.py"]
    assert worktree.commit_all(wt, "wip")
    tracked = subprocess.run(
        ["git", "-C", str(wt.path), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True,
    ).stdout.split()
    assert "gea.json" not in tracked and "new.py" in tracked


def _delegate(repo, monkeypatch, start_status="started"):
    monkeypatch.setenv("GEA_HOME", str(paths.gea_home()))
    paths.gea_home().mkdir(parents=True, exist_ok=True)
    paths.global_config_path().write_text(
        '{"builders":{"profiles":[{"id":"c","cli":"c","model":null,"pool":"c","priority":1}]}}'
    )
    path = store.create_task("wt", repo_root=repo)
    path.write_text(path.read_text().replace("## Files\n", "## Files\n\n- `a.py`\n", 1))
    monkeypatch.chdir(repo)
    started = []
    monkeypatch.setattr(
        delegate.herdr, "start_agent_pane", lambda *a: started.append(a) or start_status
    )
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: True)
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    return started


def test_delegate_in_a_worktree_logs_it_and_skips_the_checkpoint(repo, fake_herdr, monkeypatch):
    started = _delegate(repo, monkeypatch)
    assert delegate.delegate_task("TASK-001", use_worktree=True) == 0
    name = delegate.herdr.pane_name_for(repo, "wt", "001")
    assert started[0][0] == name and started[0][3] == worktree.lookup("TASK-001").path
    entry = log.last_for_task("TASK-001")
    assert entry["branch"] == "gea/task-001" and entry["worktree"]
    assert subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "refs/gea/"], capture_output=True, text=True
    ).stdout == ""


def test_a_worktree_is_removed_when_the_agent_fails_to_start(repo, fake_herdr, monkeypatch):
    _delegate(repo, monkeypatch, start_status="FAILED (x)")
    deleted = []
    monkeypatch.setattr(
        worktree, "delete_branch", lambda wt, root, force=False: deleted.append(force)
    )
    assert delegate.delegate_task("TASK-001", use_worktree=True) == 1
    assert deleted == [True]  # the branch goes too, so a retry needs no manual cleanup
    assert ["worktree", "remove", "--workspace", "w9", "--force"] in fake_herdr
    assert ["workspace", "close", "w9"] in fake_herdr
    assert not any((paths.gea_home() / "worktrees" / repo.name).iterdir())


def _task_done_setup(repo, fake_herdr, monkeypatch, merged=True):
    _delegate(repo, monkeypatch)
    delegate.delegate_task("TASK-001", use_worktree=True)
    monkeypatch.setattr(worktree, "branch_merged", lambda wt, root: merged)
    monkeypatch.setattr(worktree, "delete_branch", lambda wt, root: True)


def _boom(*a, **k):
    raise AssertionError("must not prompt")


def test_task_done_yes_removes_a_merged_worktree_without_asking(repo, fake_herdr, monkeypatch):
    from gea.tasks import commands

    _task_done_setup(repo, fake_herdr, monkeypatch)
    monkeypatch.setattr(ui, "ask_yes_no", _boom)
    commands._offer_worktree_removal("TASK-001", assume_yes=True)
    assert worktree.lookup("TASK-001") is None  # marked removed in the log
    commands._offer_worktree_removal("TASK-404", assume_yes=True)  # unknown task: no error


def test_task_done_never_reads_stdin_when_not_a_terminal(repo, fake_herdr, monkeypatch):
    from gea.tasks import commands

    _task_done_setup(repo, fake_herdr, monkeypatch)
    monkeypatch.setattr(ui, "ask_yes_no", _boom)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    commands._offer_worktree_removal("TASK-001")
    assert worktree.lookup("TASK-001") is not None  # kept, with a hint


def test_task_done_keeps_an_unmerged_worktree(repo, fake_herdr, monkeypatch):
    from gea.tasks import commands

    _task_done_setup(repo, fake_herdr, monkeypatch, merged=False)
    monkeypatch.setattr(ui, "ask_yes_no", _boom)
    commands._offer_worktree_removal("TASK-001", assume_yes=True)
    assert worktree.lookup("TASK-001") is not None


def test_review_pack_reads_the_diff_from_the_worktree(repo, fake_herdr, monkeypatch):
    from gea import review_pack

    _delegate(repo, monkeypatch)
    delegate.delegate_task("TASK-001", use_worktree=True)
    wt = worktree.lookup("TASK-001")
    (wt.path / "a.py").write_text("built in the worktree\n")
    pack = review_pack.build("TASK-001", repo)
    assert "+built in the worktree" in pack and "### a.py" in pack


def test_files_written_in_the_main_checkout_are_reported_not_reverted(repo, monkeypatch):
    from gea.tasks import store

    path = store.create_task("Leak", repo_root=repo)
    before = delegate._dirty(repo)
    (repo / "leak.py").write_text("x\n")  # what a builder that ignored its worktree leaves
    leaked = delegate._check_main_untouched(path, repo, before)
    assert leaked == ["leak.py"] and (repo / "leak.py").exists()
    assert "leak.py" in path.read_text()
    assert delegate._check_main_untouched(path, repo, before | {"leak.py"}) == []
