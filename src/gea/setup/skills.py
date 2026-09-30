"""`gea skills sync|list` — install/update global skills across agents.

Uses the `skills` CLI (npx skills add -g -a <agent...>) for third-party
skills, plus this repo's own `skills/gea-*` folder for the gea-specific
ones.
"""

from __future__ import annotations

from pathlib import Path

from gea import config, dryrun, manifest, proc, ui
from gea.setup import skills_manual

# Third-party skills recommended by gea. Each entry points at one exact
# skill subpath, not a bare repo — several of these repos bundle many
# unrelated skills (e.g. dietrichgebert/ponytail also ships ponytail-audit/
# -debt/-gain/-help/-review; vercel-labs/agent-skills is a 9-skill Vercel
# deploy bundle with nothing to do with skill discovery). Pointing `npx
# skills add` at a whole multi-skill repo makes it prompt interactively
# "select skills to install" for everything in it — not what a
# non-interactive `gea setup` step should ever trigger. A `.../tree/main/
# skills/<path>` URL resolves to exactly one skill, no prompt.
THIRD_PARTY_SKILLS = [
    "https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me",
    "https://github.com/vercel-labs/skills/tree/main/skills/find-skills",
    "nextlevelbuilder/ui-ux-pro-max-skill",  # this repo IS a single skill
]

# Skills `gea setup` asks about (id -> source). Which ones the user accepted
# lives in ~/gea/config.json["optional"]; see `chosen_optional_sources`.
# rtk has no skill of its own — its opt-in is the rtk install step itself.
OPTIONAL_SKILLS = {
    "ponytail": "https://github.com/dietrichgebert/ponytail/tree/main/skills/ponytail",
}

# Maps a detected agent binary to the id `npx skills` expects via `-a`.
SKILLS_AGENT_IDS = {
    "claude": "claude-code",
    "codex": "codex",
    "opencode": "opencode",
}

GEA_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def skill_name(source: str) -> str:
    """The name `npx skills remove` knows a source by (last path segment)."""
    return source.rstrip("/").rsplit("/", 1)[-1]


def is_optional_enabled(name: str) -> bool:
    return bool(config.load_global().get("optional", {}).get(name, True))


def chosen_optional_sources() -> list[str]:
    return [src for name, src in OPTIONAL_SKILLS.items() if is_optional_enabled(name)]


def sync_third_party_skills(installed_agents: list[str]) -> list[str]:
    agent_ids = [SKILLS_AGENT_IDS[a] for a in installed_agents if a in SKILLS_AGENT_IDS]
    if not agent_ids:
        return []
    synced = []
    for source in THIRD_PARTY_SKILLS + chosen_optional_sources():
        ui.info(f"Syncing skill {source}…")
        cmd = ["npx", "skills", "add", "-g", source, "-a", *agent_ids]
        code = proc.run_visible(cmd, timeout=120)
        if code == 0:
            synced.append(source)
            manifest.record(manifest.KIND_SKILL, skill_name(source))
    return synced


def sync_all_skills(installed_agents: list[str]) -> list[str]:
    """Third-party, user-invoked-only and gea's own skills for every detected agent."""
    agent_ids = [SKILLS_AGENT_IDS[a] for a in installed_agents if a in SKILLS_AGENT_IDS]
    return (
        sync_third_party_skills(installed_agents)
        + (skills_manual.sync_manual_skills(agent_ids) if agent_ids else [])
        + sync_gea_skills(installed_agents)
    )


def sync_gea_skills(installed_agents: list[str]) -> list[str]:
    """Install this repo's own skills/gea-* for every detected agent."""
    agent_ids = [SKILLS_AGENT_IDS[a] for a in installed_agents if a in SKILLS_AGENT_IDS]
    if not agent_ids or not GEA_SKILLS_DIR.exists():
        return []
    synced = []
    for skill_dir in sorted(GEA_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        ui.info(f"Syncing skill {skill_dir.name}…")
        cmd = ["npx", "skills", "add", "-g", str(skill_dir), "-a", *agent_ids]
        code = proc.run_visible(cmd, timeout=60)
        if code == 0:
            synced.append(skill_dir.name)
            manifest.record(manifest.KIND_SKILL, skill_dir.name)
    return synced


def dispatch_skills(args) -> int:
    from gea.setup.agents_install import detected_agents

    installed = [a.id for a in detected_agents()]

    if args.skills_command == "list":
        for name in THIRD_PARTY_SKILLS:
            print(name)
        for name, source in OPTIONAL_SKILLS.items():
            state = "on" if is_optional_enabled(name) else "off"
            print(f"{source} (optional: {name}, {state})")
        for source, names in skills_manual.MANUAL_SKILLS.items():
            print(f"{source} (user-invoked only: /{', /'.join(names)})")
        if GEA_SKILLS_DIR.exists():
            for skill_dir in sorted(GEA_SKILLS_DIR.iterdir()):
                if skill_dir.is_dir():
                    print(skill_dir.name)
        return 0

    if args.skills_command == "sync":
        dryrun.enable(getattr(args, "dry_run", False))
        for name in sync_all_skills(installed):
            print(f"✓ {name}")
        return 0

    if args.skills_command == "prune":
        from gea.setup.skills_prune import run_prune

        dryrun.enable(getattr(args, "dry_run", False))
        return run_prune()

    print("usage: gea skills [sync|list|prune]")
    return 1
