"""`gea delegate <task-id>` — start a builder pane and send it a short
prompt pointing at the task file. Blocks (via `herdr agent prompt --wait`)
until the builder settles, unlike Claude Code's own background-and-resume
pattern — a plain CLI has no harness to resume it later.
"""

from __future__ import annotations

from pathlib import Path

from gea import autonomy, checkpoint, config, ui
from gea.agents import herdr, profiles, state
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
    status = herdr.start_builder_pane(agent.id, agent.cli, agent.model, Path.cwd())
    print(status)
    if status.startswith("BLOCKED") or "FAILED" in status or "!=" in status:
        return 1

    pane_name = f"builder-{agent.id}"
    cfg = config.load_project(Path.cwd())
    prompt = BUILDER_PROMPT_TEMPLATE.format(
        task_id=task_id,
        task_path=task_path,
        autonomy_line=autonomy.describe(cfg.get("autonomy"), cfg.get("lang", {}).get("docs", "en")),
    )
    out, code = herdr.prompt_pane(pane_name, prompt, wait=True)
    print(out)
    return 0 if code == 0 else 1
