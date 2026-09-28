"""`gea skills sync|list` — install/update global skills across agents.

Uses the `skills` CLI (npx skills add -g -a <agent...>) for third-party
skills, plus this repo's own `skills/gea-*` folder for the gea-specific
ones.
"""

from __future__ import annotations

from pathlib import Path

from gea import proc, ui

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
    "https://github.com/dietrichgebert/ponytail/tree/main/skills/ponytail",
    "https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me",
    "https://github.com/vercel-labs/skills/tree/main/skills/find-skills",
    "nextlevelbuilder/ui-ux-pro-max-skill",  # this repo IS a single skill
]

# Maps a detected agent binary to the id `npx skills` expects via `-a`.
SKILLS_AGENT_IDS = {
    "claude": "claude-code",
    "codex": "codex",
    "opencode": "opencode",
}

GEA_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def sync_third_party_skills(installed_agents: list[str]) -> list[str]:
    agent_ids = [SKILLS_AGENT_IDS[a] for a in installed_agents if a in SKILLS_AGENT_IDS]
    if not agent_ids:
        return []
    synced = []
    for source in THIRD_PARTY_SKILLS:
        ui.info(f"Syncing skill {source}…")
        cmd = ["npx", "skills", "add", "-g", source, "-a", *agent_ids]
        code = proc.run_visible(cmd, timeout=120)
        if code == 0:
            synced.append(source)
    return synced


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
    return synced


def dispatch_skills(args) -> int:
    from gea.setup.agents_install import detected_agents

    installed = [a.id for a in detected_agents()]

    if args.skills_command == "list":
        for name in THIRD_PARTY_SKILLS:
            print(name)
        if GEA_SKILLS_DIR.exists():
            for skill_dir in sorted(GEA_SKILLS_DIR.iterdir()):
                if skill_dir.is_dir():
                    print(skill_dir.name)
        return 0

    if args.skills_command == "sync":
        third_party = sync_third_party_skills(installed)
        gea_skills = sync_gea_skills(installed)
        for name in third_party + gea_skills:
            print(f"✓ {name}")
        return 0

    print("usage: gea skills [sync|list]")
    return 1
