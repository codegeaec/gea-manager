from gea.setup import steps


def test_run_setup_only_runs_single_step(monkeypatch):
    calls = []
    monkeypatch.setitem(steps.__dict__, "_step_mise", lambda: calls.append("mise"))
    monkeypatch.setattr(steps, "run_setup", steps.run_setup)  # keep reference stable
    code = steps.run_setup(assume_yes=True, only="mise")
    assert code == 0
    assert calls == ["mise"]


def test_run_setup_rejects_unknown_only(capsys):
    code = steps.run_setup(assume_yes=True, only="not-a-real-step")
    assert code == 1
