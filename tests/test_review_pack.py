import subprocess

import pytest

from gea import checkpoint, review_pack
from gea.tasks import store


@pytest.fixture
def repo(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"},"verify":["true","false"]}')
    (tmp_path / "a.py").write_text("one\n")
    git("add", ".")
    git("commit", "-qm", "i")
    return tmp_path


def test_pack_contains_task_diff_verify_and_scope(repo):
    path = store.create_task("Do it", repo_root=repo)
    path.write_text(path.read_text().replace("## Files\n", "## Files\n\n- `a.py`\n", 1))
    checkpoint.create("TASK-001", repo)
    (repo / "a.py").write_text("two\n")
    (repo / "extra.py").write_text("\n".join(f"l{i}" for i in range(400)))

    pack = review_pack.build("TASK-001", repo)
    assert "# Review pack — TASK-001" in pack and "## Task" in pack
    assert "PASS `true`" in pack and "FAIL `false`" in pack
    assert "+two" in pack
    assert "outside `## Files`: `extra.py`" in pack
    assert "more lines cut" in pack


def test_unknown_task(repo):
    assert review_pack.build("TASK-404", repo) is None
