"""What to do when a builder's pane is stuck on a quota / rate-limit message
(e.g. "Individual quota reached ... Resets in 70h21m6s"): mark its pool
exhausted until the reset time, close the dead pane and recommend another
agent. Detection reuses `state.detect_exhaustion` on the pane's last lines.
"""

from __future__ import annotations

from pathlib import Path

from gea import ui
from gea.agents import herdr, profiles, state
from gea.i18n import t

TAIL_LINES = 20  # the limit message is the last thing the CLI prints


def check_exhausted(
    pane_name: str,
    agent: profiles.AgentProfile,
    root: Path,
    status: str,
    retry_cmd: str,
    tier: str | None = None,
) -> bool:
    """True if `pane_name` shows an exhausted quota; in that case the pool is
    marked, the pane closed and a next agent suggested. `retry_cmd` is the
    command to re-run, with `{agent}` replaced by the suggestion."""
    until = state.detect_exhaustion(herdr.read_pane(pane_name, lines=TAIL_LINES))
    if until is None:
        return False
    state.mark_exhausted(agent.pool, until)
    ui.warn(t("exhausted.agent", agent=agent.id, pool=agent.pool, until=state.iso(until)))
    if herdr.created_by_gea(status) and herdr.close_agent_pane(pane_name):
        ui.info(t("exhausted.closed", pane=pane_name))
    nxt = profiles.pick_agent(exclude_pools=[agent.pool], repo_root=root, tier=tier)
    if nxt:
        ui.info(t("exhausted.next", agent=nxt.id, cmd=retry_cmd.format(agent=nxt.id)))
    else:
        ui.warn(t("exhausted.none"))
    return True
