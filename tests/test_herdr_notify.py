from gea.agents import herdr


def test_notify_builds_the_command(monkeypatch):
    seen = []
    monkeypatch.setattr(herdr.proc, "run", lambda cmd, timeout=30: seen.append(cmd) or ("", "", 0))
    assert herdr.notify("T", "b", sound="request") is True
    assert seen[0] == [
        "herdr", "notification", "show", "T", "--sound", "request", "--body", "b"
    ]


def test_notify_reports_failure_without_raising(monkeypatch):
    monkeypatch.setattr(herdr.proc, "run", lambda cmd, timeout=30: ("", "", 1))
    assert herdr.notify("T") is False
