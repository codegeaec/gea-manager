from gea.agents import state


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(state.paths, "global_state_path", lambda: tmp_path / "state.json")
    assert state.load() == {}


def test_mark_and_check_exhaustion(tmp_path, monkeypatch):
    monkeypatch.setattr(state.paths, "global_state_path", lambda: tmp_path / "state.json")
    until = state.now() + state.timedelta(hours=1)
    state.mark_exhausted("opencode-go", until)
    assert state.is_pool_available("opencode-go") is False
    assert state.is_pool_available("other-pool") is True


def test_reset_pool_clears_exhaustion(tmp_path, monkeypatch):
    monkeypatch.setattr(state.paths, "global_state_path", lambda: tmp_path / "state.json")
    state.mark_exhausted("agy-gemini", state.now() + state.timedelta(hours=1))
    state.reset_pool("agy-gemini")
    assert state.is_pool_available("agy-gemini") is True


def test_load_drops_expired_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(state.paths, "global_state_path", lambda: tmp_path / "state.json")
    state.mark_exhausted("codex", state.now() - state.timedelta(hours=1))
    assert state.load() == {}


def test_detect_exhaustion_matches_rate_limit_text():
    until = state.detect_exhaustion("Error: rate limited, retrying in 30m")
    assert until is not None


def test_detect_exhaustion_returns_none_for_normal_text():
    assert state.detect_exhaustion("Implemented the feature, tests pass.") is None
