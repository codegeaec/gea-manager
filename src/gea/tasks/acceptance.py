"""Executable acceptance criteria: the `## Acceptance` section of a task.

A bullet may carry a backticked shell command, e.g.

    - [ ] The CLI rejects bad input: `uv run pytest tests/test_cli.py -q`

A backticked span counts as a command only if it starts with `run:` (always
a command: `run: pnpm lint`) or its first word resolves to an executable
(`pnpm`, `rg`, `gea`...). Component names, paths and JSX in backticks are
prose, never executed. Bullets without a command are checked by a human or
reviewer; `gea verify --task <ID>` runs the rest.
"""

from __future__ import annotations

import re
from pathlib import Path

from gea import platform, ui
from gea.tasks import store
from gea.tasks.sections import section

COMMAND_RE = re.compile(r"`([^`]+)`")
RUN_PREFIX = "run:"


def _as_command(span: str) -> str | None:
    span = span.strip()
    if span.startswith(RUN_PREFIX):
        return span[len(RUN_PREFIX):].strip() or None
    first = span.split(maxsplit=1)[0] if span else ""
    return span if first and platform.which(first) else None


def scan(text: str) -> tuple[list[str], int]:
    """(commands, number of bullets whose backticks were not commands)."""
    commands, skipped = [], 0
    for line in section(text, "Acceptance").splitlines():
        if not line.lstrip().startswith(("-", "*")):
            continue
        spans = COMMAND_RE.findall(line)
        command = next((c for c in map(_as_command, spans) if c), None)
        if command:
            commands.append(command)
        elif spans:
            skipped += 1
    return commands, skipped


def parse(text: str) -> list[str]:
    return scan(text)[0]


def for_task(task_id: str, repo_root: Path | None = None) -> list[str] | None:
    """Commands from the task's Acceptance section; None if the task is unknown."""
    path = store.find_task_path(task_id, repo_root)
    if path is None:
        return None
    commands, skipped = scan(path.read_text(encoding="utf-8"))
    if skipped:
        ui.info(f"{skipped} acceptance bullet(s) with backticks are not commands — skipped "
                f"(start a command with `{RUN_PREFIX}` to force it)")
    return commands
