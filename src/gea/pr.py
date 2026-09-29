"""`gea pr <ID>` — open a GitHub PR from a task.

The body is generated from the task's Objective, Decisions and Verification
sections. Creating a PR is outward-facing, so the generated text is shown
and confirmed first (`--yes` skips it). No tool signature is added.
"""

from __future__ import annotations

import re

from gea import proc, ui
from gea.agents import worktree
from gea.i18n import t
from gea.tasks import store
from gea.tasks.sections import section


def build(task_id: str, text: str) -> tuple[str, str]:
    """(title, body) for the task's PR."""
    heading = re.match(r"# (?:TASK-[\d.]+)\s*-\s*(.+)", text)
    title = heading.group(1).strip() if heading else task_id
    parts = []
    for label, name in (("Summary", "Objective"), ("Decisions", "Decisions"),
                        ("Verification", "Verification")):
        body = section(text, name).strip()
        if body:
            parts += [f"## {label}", "", body, ""]
    parts.append(f"Task: {task_id}")
    return title, "\n".join(parts)


def run_pr(task_id: str, assume_yes: bool = False) -> int:
    path = store.find_task_path(task_id)
    if path is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1
    title, body = build(task_id, path.read_text(encoding="utf-8"))
    print(f"{title}\n\n{body}\n")
    if not ui.ask_yes_no(t("pr.confirm"), default=False, assume_yes=assume_yes):
        ui.warn(t("common.aborted"))
        return 1
    cmd = ["gh", "pr", "create", "--title", title, "--body", body]
    wt = worktree.lookup(task_id)
    if wt and wt.branch:
        cmd += ["--head", wt.branch]
    code = proc.run_visible(cmd, timeout=120)
    if code != 0:
        ui.err(t("pr.failed"))
        return 1
    return 0


