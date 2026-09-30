"""`gea review <ID>` — have a *different* model review a task's diff.

The reviewer is picked from the available agents excluding the pool of
the builder that implemented the task (from the delegation log), so the
model that wrote the code never grades its own work.
"""

from __future__ import annotations

import time
from pathlib import Path

from gea import config, review_pack, ui
from gea.agents import exhaustion, herdr, log, profiles
from gea.i18n import t
from gea.tasks import budget, store
from gea.tasks.sections import section

REVIEW_PROMPT_TEMPLATE = (
    "Review only; do not modify code and do not commit. Read the review pack "
    "below (task, diff, verify results, scope warnings) and write your findings "
    "in the task's `## Review` section, one per line, each with a severity "
    "(critical/important/minor) and file:line. Write `No findings` if clean.\n"
    "Review pack: {pack}\n"
    "Task: {task}"
)


def last_builder_pool(task_id: str) -> str | None:
    builds = [e for e in log.read(task_id=task_id) if e.get("kind", "build") == "build"]
    return builds[-1].get("pool") if builds else None


def _review_text(task_path: Path) -> str:
    return section(task_path.read_text(encoding="utf-8"), "Review")


def review_task(task_id: str, agent_id: str | None = None) -> int:
    root = Path.cwd()
    task_path = store.find_task_path(task_id, root)
    if task_path is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1

    builder_pool = last_builder_pool(task_id)
    exclude = (builder_pool,) if builder_pool else ()
    reviewer = profiles.pick_agent(agent_id, exclude_pools=exclude, repo_root=root)
    if reviewer is None:
        ui.warn(t("review.none"))
        return 1

    if review_pack.run_review_pack(task_id) != 0:
        return 1
    pack = store.task_root(root) / "review" / f"{task_id}.md"

    review_before = _review_text(task_path)
    started = time.monotonic()
    ui.info(t("review.start", task_id=task_id, agent=reviewer.id, pool=builder_pool))
    cfg = config.load_project(root)
    permissions = cfg.get("builders", {}).get("permissions", config.DEFAULT_PERMISSIONS)
    if permissions == "yolo":
        permissions = "safe"  # a review reads and writes findings only: never full access
    status = herdr.start_builder_pane(reviewer.id, reviewer.cli, reviewer.model, root, permissions)
    print(status)
    result = "error"
    if not (status.startswith("BLOCKED") or "FAILED" in status or "!=" in status):
        prompt = REVIEW_PROMPT_TEMPLATE.format(pack=pack, task=task_path)
        _out, code, error = herdr.prompt_result(
            herdr.pane_name_for(root, "builder", reviewer.id),
            prompt,
            wait=True,
            budget_s=budget.seconds_for(task_path, root),
        )
        result = "done" if code == 0 else ("timeout" if error == "timeout" else "error")
        reviewer_pane = herdr.pane_name_for(root, "builder", reviewer.id)
        untouched = _review_text(task_path) == review_before
        if (result != "done" or untouched) and exhaustion.check_exhausted(
            reviewer_pane, reviewer, root, status, f"gea review {task_id} --agent {{agent}}"
        ):
            result = "exhausted"
    log.append(
        {
            "kind": "review",
            "project": root.name,
            "task_id": task_id,
            "agent_id": reviewer.id,
            "pool": reviewer.pool,
            "result": result,
            "duration_s": round(time.monotonic() - started),
        }
    )
    if result == "done":
        cfg = config.load_project(root)
        if cfg.get("builders", {}).get("close", config.DEFAULT_CLOSE) == "on-success" and (
            herdr.created_by_gea(status)
        ):
            herdr.close_agent_pane(herdr.pane_name_for(root, "builder", reviewer.id))
        ui.ok(t("review.done", path=task_path))
        return 0
    ui.err(t("review.failed", result=result))
    return 1
