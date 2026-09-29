import json

from gea.agents import herdr
from gea.tasks import budget, store


def test_parse_minutes():
    assert budget.parse_minutes("30m") == 30
    assert budget.parse_minutes("2h") == 120
    assert budget.parse_minutes("45") == 45
    assert budget.parse_minutes("soon") is None and budget.parse_minutes(None) is None


def test_seconds_from_header_then_config_then_default(tmp_path):
    (tmp_path / "gea.json").write_text('{"tasks":{"location":"repo"}}')
    path = store.create_task("t", repo_root=tmp_path)
    assert budget.seconds_for(path, tmp_path) == 30 * 60
    cfg = '{"tasks":{"location":"repo"},"builders":{"budget_minutes":10}}'
    (tmp_path / "gea.json").write_text(cfg)
    assert budget.seconds_for(path, tmp_path) == 600
    path.write_text(path.read_text().replace("Status: planned", "Status: planned\nBudget: 2h", 1))
    assert budget.seconds_for(path, tmp_path) == 7200


def test_prompt_result_passes_herdr_timeout_and_parses_error(monkeypatch):
    seen = []
    err = json.dumps({"error": {"code": "timeout"}})
    monkeypatch.setattr(
        herdr.proc, "run", lambda cmd, timeout=30: seen.append((cmd, timeout)) or ("", err, 1)
    )
    out, code, error = herdr.prompt_result("builder-x", "go", budget_s=60)
    assert error == "timeout" and code == 1
    cmd, subprocess_timeout = seen[0]
    assert cmd[-2:] == ["--timeout", "60000"] and subprocess_timeout == 90


def test_append_to_section_appends_and_creates(tmp_path):
    path = tmp_path / "t.md"
    path.write_text("# T\n\n## Notes\n\nold\n\n## Review\n\n")
    store.append_to_section(path, "Notes", "new")
    store.append_to_section(path, "Extra", "made")
    text = path.read_text()
    assert text.index("old") < text.index("new") < text.index("## Review")
    assert "## Extra\n\nmade" in text


