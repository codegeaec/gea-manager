"""`gea skills prune` — list installed skills gea did not install and offer
to remove them. Every skill's description is loaded into the agent's
context, so unused ones cost tokens on every session.

Only skills directly under a skills directory are considered (not the
`.system` bundles or claude.ai-synced ones, which `npx skills remove`
cannot manage).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gea import dryrun, paths, proc, ui
from gea.i18n import t
from gea.lint_context import estimate_tokens
from gea.setup import skills


@dataclass
class InstalledSkill:
    name: str
    tokens: int
    path: Path


def known_names() -> set[str]:
    names = {skills.skill_name(src) for src in skills.THIRD_PARTY_SKILLS}
    names |= {skills.skill_name(src) for src in skills.OPTIONAL_SKILLS.values()}
    if skills.GEA_SKILLS_DIR.exists():
        names |= {d.name for d in skills.GEA_SKILLS_DIR.iterdir() if d.is_dir()}
    return names


def foreign_skills() -> list[InstalledSkill]:
    known = known_names()
    found: dict[str, InstalledSkill] = {}
    for base in paths.skill_dirs():
        for child in sorted(base.iterdir()):
            skill_md = child / "SKILL.md"
            if child.name.startswith(".") or child.name in known or not skill_md.is_file():
                continue
            tokens = estimate_tokens(skill_md.read_text("utf-8", "replace"))
            found.setdefault(child.name, InstalledSkill(child.name, tokens, child))
    return sorted(found.values(), key=lambda s: -s.tokens)


def run_prune() -> int:
    candidates = foreign_skills()
    if not candidates:
        ui.ok(t("prune.none"))
        return 0
    ui.info(t("prune.header", count=len(candidates)))
    chosen = [
        s for s in candidates if ui.ask_yes_no(t("prune.ask", name=s.name, tokens=s.tokens), False)
    ]
    if not chosen:
        return 0
    names = [s.name for s in chosen]
    if dryrun.active():
        dryrun.report(f"run: npx skills remove -g -y {' '.join(names)}")
        return 0
    code = proc.run_visible(["npx", "skills", "remove", "-g", "-y", *names], timeout=120)
    if code != 0:
        ui.err(t("prune.failed"))
        return 1
    ui.ok(t("prune.removed", names=", ".join(names)))
    return 0
