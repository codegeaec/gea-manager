"""Per-task time budget: `Budget: 30m` in the task header, falling back to
`gea.json["builders"]["budget_minutes"]`."""

from __future__ import annotations

import re
from pathlib import Path

from gea import config
from gea.tasks import store

DEFAULT_MINUTES = 30
BUDGET_RE = re.compile(r"^(\d+)\s*(m|min|h)?$", re.I)


def parse_minutes(value: str | None) -> int | None:
    """'30m' -> 30, '2h' -> 120, '45' -> 45; anything else -> None."""
    match = BUDGET_RE.match((value or "").strip())
    if not match:
        return None
    amount = int(match.group(1))
    return amount * 60 if (match.group(2) or "m").lower() == "h" else amount


def seconds_for(task_path: Path, repo_root: Path) -> int:
    minutes = parse_minutes(store.read_header(task_path, "Budget"))
    if minutes is None:
        cfg = config.load_project(repo_root)
        minutes = cfg.get("builders", {}).get("budget_minutes", DEFAULT_MINUTES)
    return max(1, int(minutes)) * 60
