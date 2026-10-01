import subprocess

import pytest

from gea import checkpoint


@pytest.fixture
def repo(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("one\n")
    git("add", ".")
    git("commit", "-qm", "init")
    return tmp_path


def test_undo_restores_dirty_state_and_removes_only_new_untracked(repo):
    (repo / "a.txt").write_text("dirty\n")  # uncommitted work before delegating
    (repo / "mine.txt").write_text("keep me\n")  # pre-existing untracked file
    assert checkpoint.create("TASK-001", repo)

    (repo / "a.txt").write_text("builder edit\n")
    (repo / "new.txt").write_text("builder file\n")
    assert checkpoint.restore("TASK-001", repo)

    assert (repo / "a.txt").read_text() == "dirty\n"
    assert (repo / "mine.txt").exists()
    assert not (repo / "new.txt").exists()


def test_undo_from_a_clean_tree(repo):
    checkpoint.create("TASK-002", repo)
    (repo / "a.txt").write_text("changed\n")
    checkpoint.restore("TASK-002", repo)
    assert (repo / "a.txt").read_text() == "one\n"


def test_restore_without_checkpoint_returns_false(repo):
    assert checkpoint.restore("TASK-404", repo) is False


def test_undo_refuses_to_reset_away_commits_made_since_the_checkpoint(repo):
    import subprocess

    checkpoint.create("TASK-001", repo)
    (repo / "merged.txt").write_text("integrated work\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "merge"], check=True)
    assert checkpoint.moved_past("TASK-001", repo)
    assert checkpoint.restore("TASK-001", repo) is False  # HEAD must not go backwards
    assert (repo / "merged.txt").exists()
    assert checkpoint.restore("TASK-001", repo, force=True)  # only on explicit request
