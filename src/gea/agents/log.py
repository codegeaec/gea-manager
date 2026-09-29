"""Append-only log of delegations: `~/gea/delegations.jsonl`, one JSON
object per builder attempt. It is the base for routing by tier, review by
a different model and `gea agents stats`.

Entry keys: ts, project, task_id, agent_id, pool, tier, result
(done|blocked|timeout|exhausted|error|handoff), duration_s, verify_ok,
files_out_of_scope, round. Readers tolerate corrupt lines.
"""

from __future__ import annotations

import json
from typing import Any

from gea import dryrun, paths
from gea.agents import state


def append(entry: dict[str, Any]) -> None:
    if dryrun.active():
        return
    record = {"ts": state.iso(state.now()), **entry}
    path = paths.delegations_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read(**filters: Any) -> list[dict[str, Any]]:
    """All entries whose fields equal every given filter (e.g. task_id="TASK-001")."""
    path = paths.delegations_log_path()
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and all(entry.get(k) == v for k, v in filters.items()):
            entries.append(entry)
    return entries


def last_for_task(task_id: str, **filters: Any) -> dict[str, Any] | None:
    entries = read(task_id=task_id, **filters)
    return entries[-1] if entries else None


def last_build_for_agent(agent_id: str) -> dict[str, Any] | None:
    builds = [e for e in read(agent_id=agent_id) if e.get("kind", "build") == "build"]
    return builds[-1] if builds else None
