"""`gea review <ID>` — have a *different* model review a task's diff.

The reviewer is picked from the available agents excluding the pool of
the builder that implemented the task (from the delegation log), so the
model that wrote the code never grades its own work.
"""

from __future__ import annotations

import time
from pathlib import Path

from gea import review_pack, ui
from gea.agents import herdr, log, profiles
from gea.tasks import budget, store

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


def review_task(task_id: str, agent_id: str | None = None) -> int:
    root = Path.cwd()
    task_path = store.find_task_path(task_id, root)
    if task_path is None:
        ui.err(f"task not found: {task_id}")
        return 1

    builder_pool = last_builder_pool(task_id)
    exclude = (builder_pool,) if builder_pool else ()
    reviewer = profiles.pick_agent(agent_id, exclude_pools=exclude, repo_root=root)
    if reviewer is None:
        ui.warn("no other agent available to review — review it yourself (gea review-pack)")
        return 1

    if review_pack.run_review_pack(task_id) != 0:
        return 1
    pack = store.task_root(root) / "review" / f"{task_id}.md"

    started = time.monotonic()
    ui.info(f"{task_id}: reviewing with {reviewer.id} (implemented in pool {builder_pool})")
    status = herdr.start_builder_pane(reviewer.id, reviewer.cli, reviewer.model, root)
    print(status)
    result = "error"
    if not (status.startswith("BLOCKED") or "FAILED" in status or "!=" in status):
        prompt = REVIEW_PROMPT_TEMPLATE.format(pack=pack, task=task_path)
        _out, code, error = herdr.prompt_result(
            f"builder-{reviewer.id}",
            prompt,
            wait=True,
            budget_s=budget.seconds_for(task_path, root),
        )
        result = "done" if code == 0 else ("timeout" if error == "timeout" else "error")
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
        ui.ok(f"review written into {task_path} (## Review)")
        return 0
    ui.err(f"review {result}")
    return 1
