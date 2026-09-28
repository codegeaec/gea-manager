from gea.setup import skills


def test_sync_third_party_skills_uses_mapped_agent_ids(monkeypatch):
    calls = []
    monkeypatch.setattr(
        skills.proc, "run", lambda cmd, timeout=30: calls.append(cmd) or ("", "", 0)
    )
    synced = skills.sync_third_party_skills(["claude", "codex", "unknown-agent"])
    assert synced == skills.THIRD_PARTY_SKILLS
    assert all("-a" in cmd and "claude-code" in cmd and "codex" in cmd for cmd in calls)


def test_sync_third_party_skills_noop_without_known_agents(monkeypatch):
    called = []
    monkeypatch.setattr(skills.proc, "run", lambda *a, **k: called.append(1))
    assert skills.sync_third_party_skills(["unknown-agent"]) == []
    assert called == []


def test_sync_gea_skills_reads_local_skills_dir(tmp_path, monkeypatch):
    (tmp_path / "gea-init").mkdir()
    (tmp_path / "gea-plan").mkdir()
    (tmp_path / "not-a-dir.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(skills, "GEA_SKILLS_DIR", tmp_path)
    monkeypatch.setattr(skills.proc, "run", lambda cmd, timeout=30: ("", "", 0))
    synced = skills.sync_gea_skills(["claude"])
    assert synced == ["gea-init", "gea-plan"]
