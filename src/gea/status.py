"""`gea status` — one screen: active tasks (with their last delegation),
gea-managed herdr panes and exhausted quota pools."""

from __future__ import annotations

from pathlib import Path

from gea import ui
from gea.agents import herdr, log, state
from gea.i18n import t
from gea.tasks import store

# Panes named before the project prefix existed are still recognised.
LEGACY_PREFIXES = ("builder-", "wt-", "orchestrator-")


def _last_attempt(task_id: str) -> str:
    entry = log.last_for_task(task_id)
    if not entry:
        return "-"
    return f"{entry.get('agent_id')} {entry.get('result')} verify={entry.get('verify_ok')}"


def _managed_agents() -> list[tuple[str, str]]:
    prefixes = (f"{herdr.project_prefix(Path.cwd())}-", *LEGACY_PREFIXES)
    result, err = herdr.herdr_json(["agent", "list"])
    if err:
        return []
    return [
        (a["name"], a.get("agent_status", "unknown"))
        for a in result.get("agents", [])
        if str(a.get("name") or "").startswith(prefixes)
    ]


def run_status() -> int:
    root = Path.cwd()
    ui.info(t("status.tasks"))
    tasks = store.list_tasks(repo_root=root)
    for task_id, status in tasks:
        print(f"  {task_id:<12} {status:<12} {_last_attempt(task_id)}")
    if not tasks:
        print(f"  {t('status.none')}")

    ui.info(t("status.panes"))
    panes = _managed_agents()
    for name, status in panes:
        print(f"  {name:<24} {status}")
    if not panes:
        print(f"  {t('status.none')}")

    exhausted = state.load()
    if exhausted:
        ui.info(t("status.exhausted"))
        for pool, until in exhausted.items():
            print(f"  {pool:<16} {until}")
    return 0
