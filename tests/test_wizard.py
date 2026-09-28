from gea.init import wizard


def test_pick_primary_model_returns_none_for_non_claude():
    assert wizard._pick_primary_model("opencode") is None


def test_pick_primary_model_returns_opusplan_when_accepted(monkeypatch):
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: True)
    assert wizard._pick_primary_model("claude") == "opusplan"


def test_pick_primary_model_returns_none_when_declined(monkeypatch):
    monkeypatch.setattr(wizard.ui, "ask_yes_no", lambda *a, **k: False)
    assert wizard._pick_primary_model("claude") is None
