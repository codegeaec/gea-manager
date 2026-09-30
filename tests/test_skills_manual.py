from gea.setup import skills, skills_manual


def test_mark_manual_disables_model_invocation_and_is_idempotent(tmp_path):
    skill = tmp_path / "wrangler"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: wrangler\ndescription: x\n---\nbody\n")
    assert skills_manual.mark_manual(skill)
    text = (skill / "SKILL.md").read_text()
    assert text.startswith("---\ndisable-model-invocation: true\nname: wrangler")
    assert "allow_implicit_invocation: false" in (skill / "agents" / "openai.yaml").read_text()
    assert not skills_manual.mark_manual(skill)
    assert (skill / "SKILL.md").read_text().count("disable-model-invocation") == 1


def test_sync_installs_the_named_skills_then_marks_them(tmp_path, monkeypatch):
    monkeypatch.setattr(skills_manual.Path, "home", lambda: tmp_path)
    cmds = []

    def fake_run(cmd, timeout=0):
        cmds.append(cmd)
        d = tmp_path / ".agents" / "skills" / "wrangler"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("---\nname: wrangler\n---\n")
        return 0

    monkeypatch.setattr(skills_manual.proc, "run_visible", fake_run)
    monkeypatch.setattr(skills_manual, "MANUAL_SKILLS", {"https://x/skills": ["wrangler"]})
    monkeypatch.setattr(skills_manual.manifest, "record", lambda *a: None)
    assert skills_manual.sync_manual_skills(["claude-code"]) == ["wrangler"]
    assert "https://x/skills" in cmds[0] and "-y" in cmds[0]
    assert "disable-model-invocation" in (
        tmp_path / ".agents" / "skills" / "wrangler" / "SKILL.md"
    ).read_text()
    assert skills  # module wiring imports cleanly
