"""`gea delegate <task-id>` — start a builder pane and send it a short
prompt pointing at the task file. Blocks (via `herdr agent prompt --wait`)
until the builder settles, unlike Claude Code's own background-and-resume
pattern — a plain CLI has no harness to resume it later.
"""

from __future__ import annotations

import time
from pathlib import Path

from gea import autonomy, checkpoint, config, ui
from gea.agents import herdr, log, profiles, state
from gea.tasks import budget as budget_mod
from gea.tasks import scope, store
from gea.tasks.store import find_task_path

# Fixed instructions first, variable parts (task, autonomy) last: the stable
# prefix stays identical across delegations so prompt caches can reuse it.
BUILDER_PROMPT_TEMPLATE = (
    "Follow .agents/builder.md: implement the task below following its plan. "
    "Move it to in-progress, run `gea verify --task {task_id}`, fill in "
    "Implementation Notes and Deviations, and leave it in review. Do not commit.\n"
    "Task: {task_path}\n"
    "Autonomy: {autonomy_line}"
)


def _pick_agent(agent_id: str | None) -> profiles.AgentProfile | None:
    available_ids = set()
    pools = state.load()
    allow = config.load_project(Path.cwd()).get("builders", {}).get("allow")
    all_profiles = profiles.load_profiles()
    for p in all_profiles:
        if allow and p.id not in allow:
            continue
        if state.is_pool_available(p.pool, pools):
            available_ids.add(p.id)

    if agent_id:
        return next((p for p in all_profiles if p.id == agent_id and p.id in available_ids), None)
    ranked = [p for p in all_profiles if p.id in available_ids]
    return ranked[0] if ranked else None


def _check_scope(task_id: str, task_path: Path) -> list[str]:
    """Warn (and note in the task's Review) about files outside `## Files`."""
    files = checkpoint.changed_files(task_id)
    patterns = scope.allowed_patterns(task_path.read_text(encoding="utf-8"))
    stray = scope.out_of_scope(files or [], patterns)
    if stray:
        ui.warn(f"{len(stray)} file(s) touched outside the task's ## Files: {', '.join(stray)}")
        store.append_to_section(
            task_path,
            "Review",
            "important: builder touched files outside `## Files`:\n"
            + "\n".join(f"- `{f}`" for f in stray),
        )
    return stray


def delegate_task(task_id: str, agent_id: str | None = None) -> int:
    task_path = find_task_path(task_id)
    if task_path is None:
        ui.err(f"task not found: {task_id}")
        return 1

    agent = _pick_agent(agent_id)
    if agent is None:
        ui.warn("no builder agent available — implement it yourself or run `gea agents available`")
        return 1

    if checkpoint.create(task_id):
        ui.info(f"checkpoint saved — `gea undo {task_id}` restores it")
    ui.info(f"delegating {task_id} to {agent.id} ({agent.cli})")
    started = time.monotonic()
    attempt = len(log.read(task_id=task_id)) + 1

    def record(result: str, stray: list[str] | None = None) -> None:
        log.append(
            {
                "project": Path.cwd().name,
                "task_id": task_id,
                "agent_id": agent.id,
                "pool": agent.pool,
                "result": result,
                "duration_s": round(time.monotonic() - started),
                "round": attempt,
                "files_out_of_scope": len(stray or []),
            }
        )
        herdr.notify(
            f"{task_id}: {result}",
            f"{agent.id} finished in {round(time.monotonic() - started)}s",
            sound="done" if result == "done" else "request",
        )

    status = herdr.start_builder_pane(agent.id, agent.cli, agent.model, Path.cwd())
    print(status)
    if status.startswith("BLOCKED") or "FAILED" in status or "!=" in status:
        record("blocked" if status.startswith("BLOCKED") else "error")
        return 1

    pane_name = f"builder-{agent.id}"
    cfg = config.load_project(Path.cwd())
    prompt = BUILDER_PROMPT_TEMPLATE.format(
        task_id=task_id,
        task_path=task_path,
        autonomy_line=autonomy.describe(cfg.get("autonomy"), cfg.get("lang", {}).get("docs", "en")),
    )
    budget = budget_mod.seconds_for(task_path, Path.cwd())
    out, code, error = herdr.prompt_result(pane_name, prompt, wait=True, budget_s=budget)
    print(out)
    if error == "timeout":
        tail = herdr.read_pane(pane_name)
        store.append_to_section(
            task_path,
            "Implementation Notes",
            f"gea: builder `{agent.id}` hit the {budget // 60} min budget; "
            f"last output:\n\n```\n{tail.strip()}\n```",
        )
        ui.warn(f"budget of {budget // 60} min exceeded — the builder pane was left running")
        record("timeout")
        return 1
    stray = _check_scope(task_id, task_path)
    record("done" if code == 0 else ("blocked" if error == "agent_blocked" else "error"), stray)
    return 0 if code == 0 else 1
