from gea import paths
from gea.setup import skills_prune


def _skill(base, name, size):
    d = base / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("x" * size)


def test_foreign_skills_exclude_gea_ones_and_system_dirs():
    base = paths.home() / ".claude" / "skills"
    _skill(base, "grill-me", 400)  # gea's third-party list
    _skill(base, "big-one", 4000)
    _skill(base, "small-one", 40)
    _skill(base, ".system", 4000)
    found = skills_prune.foreign_skills()
    assert [s.name for s in found] == ["big-one", "small-one"]
    assert found[0].tokens == 1000


def test_prune_removes_only_what_the_user_confirms(monkeypatch):
    base = paths.home() / ".claude" / "skills"
    _skill(base, "big-one", 4000)
    _skill(base, "small-one", 40)
    ran = []
    monkeypatch.setattr(
        skills_prune.proc, "run_visible", lambda cmd, timeout=None: ran.append(cmd) or 0
    )
    monkeypatch.setattr(
        skills_prune.ui, "ask_yes_no", lambda q, default=True, assume_yes=False: "big" in q
    )
    assert skills_prune.run_prune() == 0
    assert ran == [["npx", "skills", "remove", "-g", "-y", "big-one"]]
