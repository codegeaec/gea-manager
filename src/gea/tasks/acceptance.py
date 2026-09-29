"""Executable acceptance criteria: the `## Acceptance` section of a task.

Each bullet may carry one backticked shell command, e.g.

    - [ ] The CLI rejects bad input: `uv run pytest tests/test_cli.py -q`

Bullets without a backticked command are prose criteria and are ignored
here (a human/reviewer checks those). `gea verify --task <ID>` runs the rest.
"""

from __future__ import annotations

import re
from pathlib import Path

from gea.tasks import store
from gea.tasks.sections import section

COMMAND_RE = re.compile(r"`([^`]+)`")


def parse(text: str) -> list[str]:
    commands = []
    for line in section(text, "Acceptance").splitlines():
        if not line.lstrip().startswith(("-", "*")):
            continue
        found = COMMAND_RE.search(line)
        if found:
            commands.append(found.group(1).strip())
    return commands


def for_task(task_id: str, repo_root: Path | None = None) -> list[str] | None:
    """Commands from the task's Acceptance section; None if the task is unknown."""
    path = store.find_task_path(task_id, repo_root)
    if path is None:
        return None
    return parse(path.read_text(encoding="utf-8"))
