import subprocess

import pytest

from gea import config
from gea.init import inspect as inspect_mod
from gea.tasks import importer, store


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


BODY = "\n## Objective\n\nHacer cosas — con `código` y tabs\t.\n\n## Files\n\n- `a.py`\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A cotizaciones-like project: tasks/active + tasks/completed, subtasks by dotted id."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    t = tmp_path / "tasks"
    head7 = "# TASK-007 - Enlazadas\n\nStatus: planned\n"
    _write(t / "active" / "TASK-007-enlazadas.md", head7 + BODY)
    head8 = "# TASK-008 - Ajuste\n\nStatus: planned — partida en subtasks\n"
    _write(t / "active" / "TASK-008-ajuste.md", head8 + BODY)
    head81 = "# TASK-008.1 - Schema\n\nParent: TASK-008\nStatus: planned\n"
    _write(t / "active" / "TASK-008.1-schema.md", head81 + BODY)
    _write(t / "completed" / "TASK-002-roles.md", "# TASK-002 - Roles\n\nStatus: review\n" + BODY)
    _write(t / "completed" / "TASK-004.1-x.md", "# TASK-004.1 - X\n\nStatus: completed\n" + BODY)
    _write(t / "INDEX.md", "# index")
    _write(t / "_template.md", "# TASK-XXX")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "i"], check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _body(path):
    return path.read_text().partition("\n## ")[2]


def test_layout_is_detected_and_templates_are_ignored(repo):
    (layout,) = importer.detect_layouts(repo)
    assert layout.kind == "active-completed" and layout.count == 5
    assert inspect_mod.inspect(repo).task_layouts[0].root == repo / "tasks"


def test_import_routes_by_id_and_state_and_keeps_bodies_intact(repo):
    assert importer.run_import() == 0
    root = repo / ".gea"
    assert (root / "tasks" / "TASK-007-enlazadas.md").exists()
    assert (root / "subtasks" / "TASK-008.1-schema.md").exists()
    assert (root / "tasks" / "done" / "TASK-002-roles.md").exists()
    assert (root / "subtasks" / "done" / "TASK-004.1-x.md").exists()
    for src in (repo / "tasks").rglob("TASK-*.md"):
        dest = next(root.rglob(src.name))
        assert _body(dest) == _body(src)
    note = (root / "tasks" / "TASK-008-ajuste.md").read_text()
    assert "Status: planned\nNote: partida en subtasks" in note
    assert "Status: completed" in (root / "tasks" / "done" / "TASK-002-roles.md").read_text()
    assert (repo / "tasks" / "active" / "TASK-007-enlazadas.md").exists()  # originals stay
    assert ("TASK-007", "planned") in store.list_tasks(repo_root=repo)


def test_import_is_idempotent_and_dry_run_writes_nothing(repo):
    importer.run_import(dry_run=True)
    assert not (repo / ".gea").exists()
    importer.run_import()
    before = {p: p.read_text() for p in (repo / ".gea").rglob("*.md")}
    assert importer.run_import() == 0
    assert {p: p.read_text() for p in (repo / ".gea").rglob("*.md")} == before


def test_different_existing_task_is_a_conflict_and_nothing_is_imported(repo):
    _write(repo / ".gea" / "tasks" / "TASK-007-enlazadas.md", "# mine\n\nStatus: planned\n")
    assert importer.run_import() == 1
    assert not (repo / ".gea" / "tasks" / "TASK-008-ajuste.md").exists()


def test_remove_source_only_removes_clean_tracked_imports(repo, monkeypatch):
    assert importer.run_import(remove_source=True, assume_yes=True) == 0
    assert not (repo / "tasks" / "active" / "TASK-007-enlazadas.md").exists()
    assert (repo / "tasks" / "INDEX.md").exists()  # not a task: untouched


def test_remove_source_refuses_a_dirty_tree(repo):
    (repo / "tasks" / "active" / "TASK-007-enlazadas.md").write_text("changed\nStatus: planned\n")
    assert importer.run_import(remove_source=True, assume_yes=True) == 1
    assert (repo / "tasks" / "active" / "TASK-007-enlazadas.md").exists()


def test_init_offers_the_import(repo, monkeypatch):
    from gea.init import wizard

    monkeypatch.setattr(wizard.platform, "which", lambda n: None)
    monkeypatch.setattr(wizard, "load_profiles", lambda: [])
    monkeypatch.setattr(wizard, "refresh_and_save", lambda: [])
    (repo / "gea.json").unlink()
    wizard.run_init(assume_yes=True, langs=("es", "es", "es"))
    assert config.load_project(repo)["tasks"]["location"] == "home"  # --yes default
    assert ("TASK-007", "planned") in store.list_tasks(repo_root=repo)  # imported by init
    assert (repo / "tasks" / "active" / "TASK-007-enlazadas.md").exists()
