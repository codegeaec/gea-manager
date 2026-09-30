"""Skills installed globally but never auto-invoked: the user runs them
explicitly as `/<skill>`. Used for situational skills (Cloudflare's security-audit)
that should only run when the user asks for them (e.g. a security audit).

Claude Code honours `disable-model-invocation: true` in the SKILL.md
frontmatter; Codex honours `policy.allow_implicit_invocation: false` in the
skill's `agents/openai.yaml`. Both are (re)applied after every sync, since
`npx skills add` overwrites the files.
"""

from __future__ import annotations

from pathlib import Path

from gea import manifest, proc, ui

# source -> the skill name it installs. Each source points at one exact skill
# (`.../tree/main/skills/<name>`), so `npx skills add` never prompts.
MANUAL_SKILLS: dict[str, list[str]] = {
    "https://github.com/cloudflare/security-audit-skill/tree/main/skills/security-audit": [
        "security-audit",
    ],
}

FLAG = "disable-model-invocation: true"
CODEX_POLICY = "policy:\n  allow_implicit_invocation: false\n"


def skill_roots() -> list[Path]:
    home = Path.home()
    return [home / ".agents" / "skills", home / ".claude" / "skills"]


def mark_manual(skill_dir: Path) -> bool:
    """Make the skill user-invoked only. True if anything was changed."""
    changed = False
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        if text.startswith("---\n") and FLAG not in text.split("\n---", 1)[0]:
            skill_md.write_text(text.replace("---\n", f"---\n{FLAG}\n", 1), encoding="utf-8")
            changed = True
    codex = skill_dir / "agents" / "openai.yaml"
    if skill_md.is_file() and not codex.exists():
        codex.parent.mkdir(exist_ok=True)
        codex.write_text(CODEX_POLICY, encoding="utf-8")
        changed = True
    return changed


def sync_manual_skills(agent_ids: list[str]) -> list[str]:
    synced: list[str] = []
    for source, names in MANUAL_SKILLS.items():
        ui.info(f"Syncing skills {source} (user-invoked only)…")
        cmd = ["npx", "skills", "add", "-g", source, "-y", "-a", *agent_ids]
        if proc.run_visible(cmd, timeout=180) != 0:
            continue
        for name in names:
            seen: set[Path] = set()
            for root in skill_roots():
                skill_dir = root / name
                if skill_dir.is_dir() and skill_dir.resolve() not in seen:
                    seen.add(skill_dir.resolve())
                    mark_manual(skill_dir)
            synced.append(name)
            manifest.record(manifest.KIND_SKILL, name)
    return synced
