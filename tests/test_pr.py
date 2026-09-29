from gea import pr
from gea.tasks import store, templates

TEXT = templates.render_task("TASK-004", "Add widget", "2026-01-01").replace(
    "## Objective\n", "## Objective\n\nShip the widget.\n", 1
).replace("## Decisions\n", "## Decisions\n\n- Use sqlite.\n", 1)


def test_build_uses_objective_decisions_verification_and_no_signature():
    title, body = pr.build("TASK-004", TEXT)
    assert title == "Add widget"
    assert "## Summary\n\nShip the widget." in body and "Use sqlite." in body
    assert "## Verification" in body and body.endswith("Task: TASK-004")
    assert "Generated" not in body and "Claude" not in body


def test_pr_asks_first_and_then_runs_gh(tmp_path, monkeypatch):
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)
    store.create_task("Add widget", repo_root=tmp_path)
    ran = []
    monkeypatch.setattr(pr.proc, "run_visible", lambda cmd, timeout=None: ran.append(cmd) or 0)
    monkeypatch.setattr("builtins.input", lambda _="": "n")
    assert pr.run_pr("TASK-001") == 1 and ran == []
    assert pr.run_pr("TASK-001", assume_yes=True) == 0
    assert ran[0][:3] == ["gh", "pr", "create"] and "Add widget" in ran[0]


def test_unknown_task(tmp_path, monkeypatch):
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    monkeypatch.chdir(tmp_path)
    assert pr.run_pr("TASK-404", assume_yes=True) == 1
