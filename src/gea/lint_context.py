"""`gea lint` — warn when always-loaded agent context gets heavy.

Sizes are approximated as characters / 4 (good enough to catch bloat; not
a real tokenizer). Advisory only: warnings never fail the command.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gea import paths, ui

CHARS_PER_TOKEN = 4
MAX_INSTRUCTION_TOKENS = 2000  # AGENTS.md / CLAUDE.md, loaded on every turn
MAX_SKILL_TOKENS = 5000  # one SKILL.md, loaded whenever it triggers
MAX_TOTAL_TOKENS = 4000  # AGENTS.md + CLAUDE.md together (the always-loaded part)


@dataclass
class Item:
    label: str
    tokens: int
    limit: int

    @property
    def over(self) -> bool:
        return self.tokens > self.limit


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def _size(path: Path) -> int:
    try:
        return estimate_tokens(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def collect(repo_root: Path | None = None) -> list[Item]:
    root = repo_root or Path.cwd()
    items: list[Item] = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        if path.is_file():
            items.append(Item(str(path), _size(path), MAX_INSTRUCTION_TOKENS))
    seen: set[Path] = set()
    for base in paths.skill_dirs():
        for skill in sorted(base.rglob("SKILL.md")):
            real = skill.resolve()
            if real in seen:
                continue
            seen.add(real)
            items.append(Item(str(skill), _size(skill), MAX_SKILL_TOKENS))
    return items


def run_lint(repo_root: Path | None = None, strict: bool = False) -> int:
    """Advisory by default. `strict` (pre-commit) fails when AGENTS.md/CLAUDE.md
    are over their limits — skills never fail it."""
    items = collect(repo_root)
    if not items:
        ui.ok("no AGENTS.md, CLAUDE.md or skills found to lint")
        return 0
    instructions = [i for i in items if i.limit == MAX_INSTRUCTION_TOKENS]
    skills = [i for i in items if i.limit == MAX_SKILL_TOKENS]
    for item in sorted(instructions, key=lambda i: -i.tokens):
        report = ui.warn if item.over else ui.ok
        limit = f" (limit ~{item.limit})" if item.over else ""
        report(f"~{item.tokens} tokens  {item.label}{limit}")
    total = sum(i.tokens for i in instructions)
    if total > MAX_TOTAL_TOKENS:
        ui.warn(f"AGENTS.md + CLAUDE.md total ~{total} tokens (limit ~{MAX_TOTAL_TOKENS})")
    for item in sorted(skills, key=lambda i: -i.tokens):
        if item.over:
            ui.warn(f"~{item.tokens} tokens  {item.label} (limit ~{item.limit})")
    if skills:
        ui.ok(f"{len(skills)} skill(s) scanned, largest ~{max(i.tokens for i in skills)} tokens")
    if strict and (total > MAX_TOTAL_TOKENS or any(i.over for i in instructions)):
        return 1
    return 0
