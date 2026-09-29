"""Process-wide `--dry-run` switch for `gea setup|init|skills sync`.

Every write to the user's machine (files, installers) goes through a seam
that asks `active()` first and, when it's on, calls `report()` instead of
acting. Read-only probes (`which`, `opencode models`) still run so the
report reflects what would really happen.
"""

from __future__ import annotations

from gea import ui

_active = False


def enable(value: bool = True) -> None:
    global _active
    _active = value


def active() -> bool:
    return _active


def report(action: str) -> None:
    ui.info(f"[dry-run] would {action}")
