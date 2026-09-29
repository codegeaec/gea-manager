"""Decisions that outlive their task: when a task is closed, its
`## Decisions` section is appended to `docs/decisions.md` in the repo."""

from __future__ import annotations

import re
from datetime import date as date_cls
from pathlib import Path

from gea.tasks.sections import section

LOG_RELATIVE = Path("docs") / "decisions.md"
LOG_HEADER = "# Decisions\n\nDecisions carried over from closed tasks (newest last).\n"


def _title(text: str, fallback: str) -> str:
    match = re.match(r"# (.+)", text)
    return match.group(1).strip() if match else fallback


def archive(task_path: Path, task_id: str, repo_root: Path) -> bool:
    """Append the task's non-empty Decisions section to docs/decisions.md.

    Idempotent: a task already recorded (by its `## TASK-ID` heading) is
    skipped. Returns True if something was written.
    """
    text = task_path.read_text(encoding="utf-8")
    body = section(text, "Decisions").strip()
    if not body:
        return False

    log = repo_root / LOG_RELATIVE
    existing = log.read_text(encoding="utf-8") if log.exists() else LOG_HEADER
    heading = f"## {_title(text, task_id)}"
    if heading in existing:
        return False

    entry = f"\n{heading}\n\n_Closed {date_cls.today().isoformat()}_\n\n{body}\n"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(existing.rstrip("\n") + "\n" + entry, encoding="utf-8")
    return True
