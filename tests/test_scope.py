import subprocess

from gea import checkpoint
from gea.tasks import scope

TASK = "# T\n\n## Files\n\n- `src/app.py`\n- `src/pkg/`\n- `tests/test_*.py`\n\n## Decisions\n"


def test_patterns_come_from_the_files_section_only():
    assert scope.allowed_patterns(TASK) == ["src/app.py", "src/pkg/", "tests/test_*.py"]


def test_out_of_scope_matching():
    patterns = scope.allowed_patterns(TASK)
    files = ["src/app.py", "src/pkg/a/b.py", "tests/test_x.py", "src/other.py", "docs/x.md"]
    assert scope.out_of_scope(files, patterns) == ["src/other.py"]


def test_no_declared_scope_means_no_guard():
    assert scope.out_of_scope(["anything.py"], []) == []


def test_changed_files_ignores_pre_existing_dirt(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("1")
    git("add", ".")
    git("commit", "-qm", "i")
    (tmp_path / "a.txt").write_text("dirty before")
    (tmp_path / "old_untracked").write_text("x")
    checkpoint.create("TASK-001", tmp_path)

    (tmp_path / "b.txt").write_text("builder")
    (tmp_path / "new.py").write_text("builder")
    assert checkpoint.changed_files("TASK-001", tmp_path) == ["b.txt", "new.py"]
    assert checkpoint.changed_files("TASK-404", tmp_path) is None


def test_missing_for_delegation_flags_empty_files_and_acceptance():
    from gea.tasks import templates

    empty = templates.render_task("TASK-001", "T", "2026-01-01")
    assert len(scope.missing_for_delegation(empty)) == 2
    filled = empty.replace("## Files\n", "## Files\n\n- `a.py`\n", 1).replace(
        "- [ ] \n", "- [ ] works: `pytest`\n", 1
    )
    assert scope.missing_for_delegation(filled) == []
