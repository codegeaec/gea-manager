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


def _fake_start(monkeypatch, tmp_path, up_after_no_daemon, tail):
    """herdr where `agent start` succeeds but the agent only comes up if
    `--no-daemon` was passed (or never, when `up_after_no_daemon` is False)."""
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "p0")
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "ws-1")
    monkeypatch.setattr(herdr.time, "sleep", lambda s: None)
    monkeypatch.setattr(herdr, "STARTUP_WAIT_S", 0)
    monkeypatch.setattr(herdr, "read_pane_id", lambda pane_id, lines=15: tail)
    calls, state = [], {"no_daemon": False}

    def fake(cmd, timeout=15):
        calls.append(cmd)
        if cmd[:2] == ["agent", "get"]:
            up = state["no_daemon"] and up_after_no_daemon
            return ({"agent": {"agent": "codex", "agent_status": "idle"}} if up else {}), None
        if cmd[:2] == ["agent", "list"]:
            return {"agents": []}, None
        if cmd[:2] == ["pane", "split"]:
            return {"pane": {"pane_id": "p1"}}, None
        if cmd[:2] == ["agent", "start"]:
            state["no_daemon"] = "--no-daemon" in cmd
            return {"agent": {"name": cmd[2]}}, None
        return {}, None

    monkeypatch.setattr(herdr, "herdr_json", fake)
    return calls


def test_a_dead_agent_is_reported_with_the_pane_output_and_its_pane_closed(monkeypatch, tmp_path):
    calls = _fake_start(monkeypatch, tmp_path, False, "Error: login expired")
    status = herdr.start_agent_pane("cot-builder-codex", "codex", None, tmp_path)
    assert status.startswith("FAILED") and "login expired" in status
    assert ["pane", "close", "p1"] in calls


def test_codex_daemon_failure_is_retried_with_no_daemon(monkeypatch, tmp_path):
    calls = _fake_start(
        monkeypatch, tmp_path, True, "Error: Cannot use the shared background server"
    )
    status = herdr.start_agent_pane("cot-builder-codex", "codex", None, tmp_path)
    assert status.startswith("started")
    starts = [c for c in calls if c[:2] == ["agent", "start"]]
    assert len(starts) == 2 and "--no-daemon" in starts[1] and "--no-daemon" not in starts[0]


def test_wait_settled_keeps_waiting_while_the_agent_is_working(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(herdr.time, "sleep", lambda s: None)
    statuses = iter(["working", "idle", "idle", "working", "idle", "idle", "idle"])
    reads = []

    def fake(cmd, timeout=15):
        status = next(statuses)
        reads.append(status)
        return {"agent": {"agent": "opencode", "agent_status": status}}, None

    monkeypatch.setattr(herdr, "herdr_json", fake)
    assert herdr.wait_settled("x", 60, stable_reads=3) == "settled"
    assert len(reads) == 7  # the dip to idle mid-run did not count as finished


def test_wait_settled_times_out_when_still_working(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(herdr.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        herdr, "herdr_json", lambda cmd, timeout=15: ({"agent": {"agent_status": "working"}}, None)
    )
    assert herdr.wait_settled("x", 0) == "timeout"
