"""`gea agents stats` — success rate, average duration and timeouts per
agent and tier, computed from the delegation log."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from gea.agents import log
from gea.i18n import t


def summarize(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e.get("kind", "build") == "build":
            groups[(e.get("agent_id", "?"), e.get("tier") or "-")].append(e)
    rows = []
    for (agent, tier), items in sorted(groups.items()):
        ok = sum(1 for e in items if e.get("result") == "done" and e.get("verify_ok"))
        rows.append(
            {
                "agent": agent,
                "tier": tier,
                "attempts": len(items),
                "success": ok / len(items),
                "avg_s": round(sum(e.get("duration_s", 0) for e in items) / len(items)),
                "timeouts": sum(1 for e in items if e.get("result") == "timeout"),
            }
        )
    return rows


def run_stats() -> int:
    rows = summarize(log.read())
    if not rows:
        print(t("stats.empty"))
        return 0
    print(t("stats.header"))
    for r in rows:
        print(
            f"{r['agent']:<14} {r['tier']:<4} {r['attempts']:>8} "
            f"{r['success']:>8.0%} {r['avg_s']:>7}s {r['timeouts']:>9}"
        )
    return 0
