from gea.agents import profiles


def test_detect_profiles_empty_when_no_cli_present(monkeypatch):
    monkeypatch.setattr(profiles.platform, "which", lambda name: None)
    assert profiles.detect_profiles() == []


def test_detect_profiles_codex_and_kimi(monkeypatch):
    monkeypatch.setattr(
        profiles.platform, "which", lambda name: "/x" if name in ("codex", "kimi") else None
    )
    detected = profiles.detect_profiles()
    ids = {p.id for p in detected}
    assert ids == {"codex", "kimi"}


def test_detect_profiles_agy_has_one_pool_per_model_family(monkeypatch):
    monkeypatch.setattr(profiles.platform, "which", lambda name: "/x" if name == "agy" else None)
    monkeypatch.setattr(profiles.proc, "run", lambda cmd, timeout=30: ("", "", 1))
    detected = profiles.detect_profiles()
    assert {p.id for p in detected} == {"agy", "agy-claude", "agy-gpt-oss"}
    assert len({p.pool for p in detected}) == 3
    assert all(p.cli == "agy" for p in detected)


def test_detect_profiles_agy_skips_models_it_does_not_list(monkeypatch):
    monkeypatch.setattr(profiles.platform, "which", lambda name: "/x" if name == "agy" else None)
    listing = "gemini-3.1-pro-high\tGemini\nclaude-sonnet-4-6\tClaude\n"
    monkeypatch.setattr(profiles.proc, "run", lambda cmd, timeout=30: (listing, "", 0))
    assert {p.id for p in profiles.detect_profiles()} == {"agy", "agy-claude"}


def test_refresh_and_save_persists_to_global_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path))
    monkeypatch.setattr(profiles.platform, "which", lambda name: "/x" if name == "codex" else None)
    saved = profiles.refresh_and_save()
    assert [p.id for p in saved] == ["codex"]
    loaded = profiles.load_profiles()
    assert [p.id for p in loaded] == ["codex"]
