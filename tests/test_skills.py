from gea.setup import skills


def test_third_party_skills_point_at_a_single_skill_subpath():
    # Regression test: earlier gea shipped "vercel-labs/agent-skills" here,
    # assuming it held grill-me/find-skills — it's actually a 9-skill
    # Vercel-deploy bundle with neither, which made `npx skills add`
    # prompt an interactive "select skills to install" for all 9. Every
    # multi-skill source below must be scoped to one exact skill path.
    for source in skills.THIRD_PARTY_SKILLS:
        if "github.com" in source:
            assert "/tree/main/skills/" in source, source
    sources = " ".join(skills.THIRD_PARTY_SKILLS)
    assert "vercel-labs/agent-skills" not in sources
    assert "mattpocock/skills/tree/main/skills/productivity/grill-me" in sources
    assert "vercel-labs/skills/tree/main/skills/find-skills" in sources


def test_sync_third_party_skills_uses_mapped_agent_ids(monkeypatch):
    calls = []
    monkeypatch.setattr(
        skills.proc, "run_visible", lambda cmd, timeout=30: calls.append(cmd) or 0
    )
    synced = skills.sync_third_party_skills(["claude", "codex", "unknown-agent"])
    assert synced == skills.THIRD_PARTY_SKILLS + list(skills.OPTIONAL_SKILLS.values())
    assert all("-a" in cmd and "claude-code" in cmd and "codex" in cmd for cmd in calls)


def test_sync_third_party_skills_noop_without_known_agents(monkeypatch):
    called = []
    monkeypatch.setattr(skills.proc, "run_visible", lambda *a, **k: called.append(1))
    assert skills.sync_third_party_skills(["unknown-agent"]) == []
    assert called == []


def test_sync_gea_skills_reads_local_skills_dir(tmp_path, monkeypatch):
    (tmp_path / "gea-init").mkdir()
    (tmp_path / "gea-plan").mkdir()
    (tmp_path / "not-a-dir.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(skills, "GEA_SKILLS_DIR", tmp_path)
    monkeypatch.setattr(skills.proc, "run_visible", lambda cmd, timeout=30: 0)
    synced = skills.sync_gea_skills(["claude"])
    assert synced == ["gea-init", "gea-plan"]
