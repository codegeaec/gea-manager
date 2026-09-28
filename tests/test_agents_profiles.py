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


def test_detect_profiles_agy_adds_two_profiles(monkeypatch):
    monkeypatch.setattr(profiles.platform, "which", lambda name: "/x" if name == "agy" else None)
    detected = profiles.detect_profiles()
    assert {p.id for p in detected} == {"agy", "agy-claude"}
    assert all(p.cli == "agy" for p in detected)


def test_refresh_and_save_persists_to_global_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path))
    monkeypatch.setattr(profiles.platform, "which", lambda name: "/x" if name == "codex" else None)
    saved = profiles.refresh_and_save()
    assert [p.id for p in saved] == ["codex"]
    loaded = profiles.load_profiles()
    assert [p.id for p in loaded] == ["codex"]
