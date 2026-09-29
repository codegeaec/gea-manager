import pytest

from gea import config, verify
from gea.tasks import acceptance, decisions, store, templates


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "gea.json").write_text('{"tasks": {"location": "repo"}, "lang": {"docs": "en"}}')
    return tmp_path


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("kind", templates.TASK_TYPES)
def test_every_task_type_renders_in_both_languages(kind, lang):
    text = templates.render_task("TASK-001", "T", "2026-01-01", lang=lang, task_type=kind)
    assert f"Type: {kind}" in text
    assert "## Acceptance" in text
    assert "{" not in text


def test_unknown_task_type_is_rejected():
    with pytest.raises(ValueError):
        templates.render_task("TASK-001", "T", "2026-01-01", task_type="epic")


def test_create_task_with_type(repo):
    path = store.create_task("Fix crash", repo_root=repo, task_type="bugfix")
    assert "Root Cause" in path.read_text(encoding="utf-8")


def test_acceptance_parses_only_backticked_bullets():
    text = "## Acceptance\n\n- [ ] prose only\n- [ ] runs `pytest -q`\n\n## Files\n- `nope`\n"
    assert acceptance.parse(text) == ["pytest -q"]


def test_verify_task_runs_acceptance_commands(repo, monkeypatch):
    path = store.create_task("A", repo_root=repo)
    path.write_text(path.read_text().replace("- [ ] \n", "- [ ] `echo hi`\n", 1))
    ran = []
    monkeypatch.setattr(verify, "run_commands", lambda cmds, quiet=False: ran.extend(cmds) or [])
    monkeypatch.chdir(repo)
    assert verify.run_verify(repo, task_id="TASK-001") == 0
    assert ran == ["echo hi"]


def test_verify_unknown_task_fails(repo):
    assert verify.run_verify(repo, task_id="TASK-999") == 1


def test_closing_a_task_archives_its_decisions_once(repo):
    path = store.create_task("Pick db", repo_root=repo)
    text = path.read_text().replace("## Decisions\n", "## Decisions\n\n- Use sqlite.\n", 1)
    path.write_text(text)
    assert store.close_task("TASK-001", repo_root=repo)
    log = (repo / "docs" / "decisions.md").read_text()
    assert "TASK-001 - Pick db" in log and "Use sqlite." in log

    done = next((repo / ".gea" / "tasks" / "done").glob("*.md"))
    assert decisions.archive(done, "TASK-001", repo) is False  # idempotent


def test_closing_a_task_without_decisions_writes_no_log(repo):
    store.create_task("Nothing", repo_root=repo)
    store.close_task("TASK-001", repo_root=repo)
    assert not (repo / "docs" / "decisions.md").exists()


def test_config_still_valid(repo):
    assert config.load_project(repo)["tasks"]["location"] == "repo"


def test_acceptance_module_imports_cleanly_in_a_fresh_interpreter():
    import subprocess
    import sys

    for module in ("gea.tasks.acceptance", "gea.tasks.decisions", "gea.verify"):
        subprocess.run([sys.executable, "-c", f"import {module}"], check=True)


def test_quiet_verify_prints_only_failures(repo, monkeypatch, capsys):
    (repo / "gea.json").write_text(
        '{"tasks": {"location": "repo"}, "verify": ["true", "false"]}'
    )
    assert verify.run_verify(repo, quiet=True) == 1
    out = capsys.readouterr().out
    assert "false" in out and "true" not in out.replace("false", "")


@pytest.mark.parametrize("kind", [None, *templates.TASK_TYPES])
def test_every_task_template_has_a_tier(kind):
    text = templates.render_task("TASK-001", "T", "2026-01-01", task_type=kind)
    assert "Tier: M" in text
