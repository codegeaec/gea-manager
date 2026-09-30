"""`gea guide [plan|delegate|review|build|all]` — the step-by-step working
guide, printed to stdout so any agent can read it without installing skills.

Single source of truth: `templates/<lang>/guide/*.md`. The bundled skills and
the project's slash commands only tell the agent to run this command.
Language: `--lang`, else the project's agents language, else the UI language.
"""

from __future__ import annotations

from pathlib import Path

from gea import config, ui
from gea.i18n import current_lang
from gea.init.scaffold import read_template

TOPICS = ("plan", "delegate", "review", "build")


def resolve_lang(explicit: str | None, cwd: Path | None = None) -> str:
    if explicit:
        return explicit
    root = cwd or Path.cwd()
    if (root / "gea.json").exists():
        return config.agents_lang(config.load_project(root))
    return current_lang()


def guide_text(topic: str, lang: str) -> str:
    topics = TOPICS if topic == "all" else (topic,)
    return "\n".join(read_template(lang, f"guide/{t}.md").rstrip() + "\n" for t in topics)


def run_guide(topic: str = "all", lang: str | None = None) -> int:
    if topic != "all" and topic not in TOPICS:
        ui.err(f"unknown topic: {topic} (use {', '.join(TOPICS)} or all)")
        return 1
    print(guide_text(topic, resolve_lang(lang)), end="")
    return 0
