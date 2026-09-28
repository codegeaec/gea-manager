from gea.setup import skills


def test_gea_skills_dir_contains_all_four_skills():
    names = {p.name for p in skills.GEA_SKILLS_DIR.iterdir() if p.is_dir()}
    assert names == {"gea-init", "gea-plan", "gea-delegate", "gea-review"}


def test_each_skill_has_frontmatter_name_and_description():
    for skill_dir in skills.GEA_SKILLS_DIR.iterdir():
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---\nname:")
        assert "description:" in content.splitlines()[2]
