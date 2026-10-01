import json
import subprocess

import pytest

from gea import config, paths
from gea.agents import delegate, herdr, review, worktree
from gea.tasks import store


def test_flags_per_cli_and_mode():
    assert herdr.permission_args("claude", "yolo") == ["--dangerously-skip-permissions"]
    assert herdr.permission_args("claude", "safe") == ["--permission-mode", "acceptEdits"]
    assert herdr.permission_args("codex", "yolo") == ["--dangerously-bypass-approvals-and-sandbox"]
    assert "workspace-write" in herdr.permission_args("codex", "safe")
    assert herdr.permission_args("opencode", "yolo") == ["--auto"]
    assert herdr.permission_args("opencode", "safe") == []  # its own opencode.jsonc rules
    assert herdr.permission_args("kimi", "yolo") == []  # unverified: never guessed
    assert herdr.permission_args("codex", "nope") == []


def test_the_orchestrators_own_tab_never_gets_permission_flags():
    for cli, cfg in herdr.CLI_ARGS.items():
        assert not any("permission" in a or "dangerous" in a for a in cfg["base"]), cli


def test_agent_start_receives_the_extra_flags_before_the_model(monkeypatch, tmp_path):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "w:p1")
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "w")
    started = []

    def fake(cmd, timeout=15):
        if cmd[:2] == ["agent", "start"]:
            started.append(cmd)
            return {"agent": "x"}, None
        if cmd[:2] == ["pane", "split"]:
            return {"pane": {"pane_id": "w:p2"}}, None
        if cmd[:2] == ["agent", "list"]:
            return {"agents": []}, None
        return {}, "agent_not_found"

    monkeypatch.setattr(herdr, "herdr_json", fake)
    herdr.start_builder_pane("cx", "codex", "gpt", tmp_path, permissions="yolo")
    tail = started[0][started[0].index("--") + 1 :]
    assert tail == ["--dangerously-bypass-approvals-and-sandbox", "--no-daemon", "-m", "gpt"]


@pytest.mark.parametrize(
    "builders",
    [{"permissions": "wild"}, {"worktree": "x"}, {"worktree": {"setup": 3}},
     {"worktree": {"copy": ".env"}}, {"worktree": {"copy": ["/etc/passwd"]}},
     {"worktree": {"copy": ["../x"]}}],
)
def test_invalid_builder_settings_are_refused(tmp_path, builders):
    (tmp_path / "gea.json").write_text(json.dumps({"builders": builders}))
    with pytest.raises(config.ConfigError):
        config.load_project(tmp_path)


def test_valid_settings_load(tmp_path):
    b = {"permissions": "yolo", "worktree": {"copy": [".env"], "setup": "pnpm install"}}
    (tmp_path / "gea.json").write_text(json.dumps({"builders": b}))
    assert config.load_project(tmp_path)["builders"]["permissions"] == "yolo"
    assert config.load_project(tmp_path / "none")["builders"].get("permissions", "safe") == "safe"


def _delegate_setup(tmp_path, monkeypatch, builders):
    paths.gea_home().mkdir(parents=True, exist_ok=True)
    profile = {"id": "c", "cli": "codex", "model": None, "pool": "c", "priority": 1}
    paths.global_config_path().write_text(json.dumps({"builders": {"profiles": [profile]}}))
    (tmp_path / "gea.json").write_text(
        json.dumps({"tasks": {"location": "repo"}, "builders": builders})
    )
    monkeypatch.chdir(tmp_path)
    store.create_task("t", repo_root=tmp_path)
    started = []
    monkeypatch.setattr(delegate.checkpoint, "create", lambda *_: False)
    monkeypatch.setattr(delegate.checkpoint, "changed_files", lambda *a: ["a.py"])
    monkeypatch.setattr(
        delegate.herdr, "start_agent_pane", lambda *a: started.append(a) or "started x"
    )
    monkeypatch.setattr(delegate.herdr, "notify", lambda *a, **k: True)
    monkeypatch.setattr(delegate.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(delegate.herdr, "close_agent_pane", lambda n: True)
    monkeypatch.setattr(delegate.verify, "run_verify", lambda *a, **k: 0)
    return started


def test_yolo_without_a_worktree_is_refused_before_anything_starts(tmp_path, monkeypatch, capsys):
    started = _delegate_setup(tmp_path, monkeypatch, {"permissions": "yolo"})
    assert delegate.delegate_task("TASK-001") == 1
    assert started == [] and "worktree" in capsys.readouterr().out


def test_safe_mode_passes_the_safe_flags(tmp_path, monkeypatch):
    started = _delegate_setup(tmp_path, monkeypatch, {})
    assert delegate.delegate_task("TASK-001") == 0
    assert started[0][4] == herdr.permission_args("codex", "safe") + ["--no-daemon"]


def test_yolo_in_a_worktree_passes_the_yolo_flags(tmp_path, monkeypatch):
    started = _delegate_setup(tmp_path, monkeypatch, {"permissions": "yolo", "worktrees": True})
    wt = worktree.Worktree("TASK-001", tmp_path / "wt", "gea/task-001", "abc")
    monkeypatch.setattr(delegate.worktree, "create", lambda *a, **k: wt)
    monkeypatch.setattr(delegate.worktree, "changed_files", lambda w: ["a.py"])
    monkeypatch.setattr(delegate.worktree, "commit_all", lambda *a: True)
    assert delegate.delegate_task("TASK-001") == 0
    assert started[0][4] == ["--dangerously-bypass-approvals-and-sandbox", "--no-daemon"]


def test_a_review_never_runs_with_full_access(tmp_path, monkeypatch):
    from gea.agents import log

    paths.gea_home().mkdir(parents=True, exist_ok=True)
    profs = [
        {"id": p, "cli": p, "model": None, "pool": p, "priority": i} for i, p in enumerate("ab")
    ]
    paths.global_config_path().write_text(json.dumps({"builders": {"profiles": profs}}))
    (tmp_path / "gea.json").write_text(
        json.dumps({"tasks": {"location": "repo"}, "builders": {"permissions": "yolo"}})
    )
    monkeypatch.chdir(tmp_path)
    store.create_task("t", repo_root=tmp_path)
    log.append({"kind": "build", "task_id": "TASK-001", "agent_id": "a", "pool": "a"})
    seen = []
    monkeypatch.setattr(
        review.herdr, "start_builder_pane", lambda *a: seen.append(a[-1]) or "started x"
    )
    monkeypatch.setattr(review.herdr, "prompt_result", lambda *a, **k: ("", 0, None))
    monkeypatch.setattr(review.herdr, "close_agent_pane", lambda n: True)
    monkeypatch.setattr(review.review_pack, "run_review_pack", lambda *_: 0)
    review.review_task("TASK-001")
    assert seen == ["safe"]


@pytest.fixture
def repo(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / ".gitignore").write_text(".env\n")
    (tmp_path / "a.py").write_text("one\n")
    git("add", ".")
    git("commit", "-qm", "init")
    (tmp_path / ".env").write_text("SECRET=1\n")
    return tmp_path


@pytest.fixture
def real_worktrees(monkeypatch, repo):
    def herdr_json(cmd, timeout=15):
        if cmd[:2] == ["worktree", "create"]:
            opt = dict(zip(cmd[2::2], cmd[3::2], strict=False))
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "-b", opt["--branch"], opt["--path"],
                 opt["--base"]],
                check=True, capture_output=True,
            )
            return {"workspace": {"workspace_id": "w9"}}, None
        if cmd[:2] == ["worktree", "remove"]:
            for child in (paths.gea_home() / "worktrees" / repo.name).iterdir():
                subprocess.run(
                    ["git", "-C", str(repo), "worktree", "remove", "--force", str(child)],
                    check=True, capture_output=True,
                )
        return {}, None

    monkeypatch.setattr(worktree.herdr, "herdr_json", herdr_json)


def test_worktree_gets_the_copied_files_and_runs_setup_there(repo, real_worktrees):
    setup = {"copy": [".env", "missing.txt"], "setup": "pwd > .setup-ran"}
    wt = worktree.create("TASK-001", repo, setup)
    assert (wt.path / ".env").read_text() == "SECRET=1\n"
    assert (wt.path / ".setup-ran").read_text().strip() == str(wt.path)
    assert wt.copied == [".env"]  # the missing one is skipped silently


def test_copied_files_never_reach_the_changed_list_or_the_commit(repo, real_worktrees):
    (repo / "local.cfg").write_text("mine\n")  # untracked and NOT gitignored
    wt = worktree.create("TASK-001", repo, {"copy": ["local.cfg"]})
    (wt.path / "a.py").write_text("two\n")
    assert worktree.changed_files(wt) == ["a.py"]
    assert worktree.commit_all(wt, "wip")
    tracked = subprocess.run(
        ["git", "-C", str(wt.path), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True,
    ).stdout.split()
    assert "local.cfg" not in tracked and "a.py" in tracked


def test_a_failing_setup_removes_the_worktree_and_reports(repo, real_worktrees, capsys):
    assert worktree.create("TASK-001", repo, {"setup": "echo boom >&2; exit 3"}) is None
    assert "boom" in capsys.readouterr().out
    assert not any((paths.gea_home() / "worktrees" / repo.name).iterdir())


def test_agent_args_default_to_no_daemon_for_codex_and_can_be_overridden():
    assert herdr.agent_args("codex", {}) == ["--no-daemon"]
    assert herdr.agent_args("codex", {"agentArgs": {"codex": []}}) == []  # opt out
    assert herdr.agent_args("codex", {"agentArgs": {"codex": ["--x"]}}) == ["--x"]
    assert herdr.agent_args("opencode", {}) == []
