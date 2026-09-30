import re
from pathlib import Path

import pytest

from gea import guide
from gea.init import scaffold

TEMPLATES = Path(scaffold.__file__).resolve().parent.parent / "templates"
SKILLS = Path(scaffold.__file__).resolve().parent.parent / "skills"


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("topic", guide.TOPICS)
def test_every_topic_exists_in_both_languages_without_ansi(topic, lang):
    text = guide.guide_text(topic, lang)
    assert text.startswith("# gea guide: ") and "\x1b" not in text and "{" not in text


def test_topics_mention_only_real_commands():
    """Every `gea <sub>` a guide or the cheat sheet tells an agent to run must exist."""
    from gea import cli

    subcommands = set(cli._build_parser()._subparsers._group_actions[0].choices)
    text = "".join(guide.guide_text("all", lang) for lang in ("es", "en"))
    for lang in ("en", "es"):
        text += (TEMPLATES / lang / "agents" / "gea.md").read_text()
    for cmd in set(re.findall(r"`gea ([a-z][a-z-]*)", text)):
        assert cmd in subcommands, cmd


def test_guide_language_follows_the_project_then_the_ui(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "gea.json").write_text('{"lang": {"agents": "en", "docs": "es", "commits": "es"}}')
    assert guide.run_guide("plan") == 0
    assert "Turn a request into a durable task" in capsys.readouterr().out
    assert guide.run_guide("plan", "es") == 0
    assert "Convertí un pedido" in capsys.readouterr().out
    assert guide.run_guide("nope") == 1


def test_slash_commands_only_point_at_the_guide(tmp_path):
    written = scaffold.write_slash_commands(tmp_path, "en", ["claude", "opencode", "codex"])
    assert len(written) == 6 and not (tmp_path / ".codex").exists()
    text = (tmp_path / ".claude" / "commands" / "gea-review.md").read_text()
    assert "gea guide review" in text and "$ARGUMENTS" in text and text.startswith("---\n")
    assert scaffold.write_slash_commands(tmp_path, "en", ["claude"]) == []  # never overwrites


def test_readme_section_is_added_without_touching_the_rest(tmp_path):
    (tmp_path / "README.md").write_text("# Mine\n\nHello\n")
    assert scaffold.ensure_readme(tmp_path, "es", "demo", ".gea") == "updated"
    text = (tmp_path / "README.md").read_text()
    assert text.startswith("# Mine\n\nHello\n") and "## Trabajo con gea" in text
    assert scaffold.ensure_readme(tmp_path, "es", "demo", ".gea") == "unchanged"


def test_readme_is_created_when_missing(tmp_path):
    assert scaffold.ensure_readme(tmp_path, "en", "demo", ".gea") == "created"
    assert (tmp_path / "README.md").read_text().startswith("# demo\n")


@pytest.mark.parametrize("skill", ["gea-plan", "gea-delegate", "gea-review"])
def test_bundled_skills_are_wrappers_of_the_guide(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    assert f"gea guide {skill.removeprefix('gea-')}" in text and len(text.splitlines()) < 25
