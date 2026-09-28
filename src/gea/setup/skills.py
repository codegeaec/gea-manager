"""`gea skills sync|list` — install/update global skills across agents.

Uses the `skills` CLI (npx skills add -g -a <agent...>) for third-party
skills, plus this repo's own `skills/gea-*` folder for the gea-specific
ones.
"""

from __future__ import annotations

from pathlib import Path

from gea import proc

# Third-party skills recommended by gea (see the plan's rationale for each).
THIRD_PARTY_SKILLS = [
    "dietrichgebert/ponytail",
    "vercel-labs/agent-skills",  # grill-me / find-skills live in this bundle
    "nextlevelbuilder/ui-ux-pro-max-skill",
]

# Maps a detected agent binary to the id `npx skills` expects via `-a`.
SKILLS_AGENT_IDS = {
    "claude": "claude-code",
    "codex": "codex",
    "opencode": "opencode",
}

GEA_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills"


def sync_third_party_skills(installed_agents: list[str]) -> list[str]:
    agent_ids = [SKILLS_AGENT_IDS[a] for a in installed_agents if a in SKILLS_AGENT_IDS]
    if not agent_ids:
        return []
    synced = []
    for source in THIRD_PARTY_SKILLS:
        cmd = ["npx", "skills", "add", "-g", source, "-a", *agent_ids]
        _out, _err, code = proc.run(cmd, timeout=120)
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
        cmd = ["npx", "skills", "add", "-g", str(skill_dir), "-a", *agent_ids]
        _out, _err, code = proc.run(cmd, timeout=60)
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
