from gea.agents import herdr


def test_herdr_json_parses_stdout_on_success(monkeypatch):
    monkeypatch.setattr(herdr.proc, "run", lambda cmd, timeout=15: ('{"result": {"a": 1}}', "", 0))
    result, err = herdr.herdr_json(["status"])
    assert result == {"a": 1}
    assert err is None


def test_herdr_json_parses_stderr_on_failure(monkeypatch):
    monkeypatch.setattr(
        herdr.proc, "run", lambda cmd, timeout=15: ("", '{"error": {"code": "not_found"}}', 1)
    )
    result, err = herdr.herdr_json(["agent", "get", "x"])
    assert result == {}
    assert err == "not_found"


def test_start_builder_pane_requires_herdr_env(monkeypatch):
    monkeypatch.delenv("HERDR_ENV", raising=False)
    status = herdr.start_builder_pane("codex", "codex", None, __import__("pathlib").Path("/tmp"))
    assert "HERDR_ENV" in status


def test_start_builder_pane_reuses_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "pane-1")
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "ws-1")
    ours = {"agent": {"workspace_id": "ws-1"}}
    monkeypatch.setattr(herdr, "herdr_json", lambda cmd, timeout=15: (ours, None))
    status = herdr.start_builder_pane("codex", "codex", None, tmp_path)
    assert "already exists" in status
