"""`gea agents [list|available|start|check|reset|mode]` dispatch."""

from __future__ import annotations

from pathlib import Path

from gea import config
from gea.agents import herdr, profiles, state


def _project_allowlist() -> list[str] | None:
    cfg = config.load_project(Path.cwd())
    allow = cfg.get("builders", {}).get("allow")
    return allow or None


def cmd_list() -> int:
    for p in profiles.load_profiles():
        model = p.model or "-"
        print(f"{p.id} {p.cli} {model} pool={p.pool}")
    return 0


def cmd_available() -> int:
    cfg = config.load_project(Path.cwd())
    mode = cfg.get("builders", {}).get("mode", "ask")
    print(f"mode {mode}")

    allow = _project_allowlist()
    pools = state.load()
    for p in profiles.load_profiles():
        if allow and p.id not in allow:
            continue
        if state.is_pool_available(p.pool, pools):
            model = p.model or "-"
            print(f"{p.id} {p.cli} {model}")
    return 0


def cmd_start(agent_id: str) -> int:
    profile = next((p for p in profiles.load_profiles() if p.id == agent_id), None)
    if not profile:
        print(f"unknown agent: {agent_id}")
        return 1
    result = herdr.start_builder_pane(agent_id, profile.cli, profile.model, Path.cwd())
    print(result)
    return 0


def cmd_check(agent_id: str) -> int:
    profile = next((p for p in profiles.load_profiles() if p.id == agent_id), None)
    if not profile:
        print(f"unknown agent: {agent_id}")
        return 1
    text = herdr.read_pane(herdr.pane_name_for(Path.cwd(), "builder", agent_id))
    until = state.detect_exhaustion(text)
    if until is None:
        print("OK")
        return 0
    for other in profiles.load_profiles():
        if other.pool == profile.pool:
            state.mark_exhausted(other.pool, until)
    print(f"EXHAUSTED {state.iso(until)}")
    return 0


def cmd_reset(agent_id: str) -> int:
    profile = next((p for p in profiles.load_profiles() if p.id == agent_id), None)
    if not profile:
        print(f"unknown agent: {agent_id}")
        return 1
    state.reset_pool(profile.pool)
    print("OK")
    return 0


def cmd_refresh() -> int:
    """Detect the builder CLIs installed here and store their profiles."""
    detected = profiles.refresh_and_save()
    for p in detected:
        print(f"{p.id} {p.cli} {p.model or '-'} pool={p.pool}")
    if not detected:
        print("no builder CLIs found (opencode, agy, codex, kimi)")
    return 0


def cmd_mode(value: str) -> int:
    cfg = config.load_project(Path.cwd())
    cfg.setdefault("builders", {})["mode"] = value
    config.save_project(Path.cwd(), cfg)
    print(f"mode {value}")
    return 0


def dispatch_agents(args) -> int:
    command = args.agents_command
    if command == "list":
        return cmd_list()
    if command == "available":
        return cmd_available()
    if command == "start":
        return cmd_start(args.agent_id)
    if command == "check":
        return cmd_check(args.agent_id)
    if command == "reset":
        return cmd_reset(args.agent_id)
    if command == "mode":
        return cmd_mode(args.value)
    if command == "refresh":
        return cmd_refresh()
    if command == "stats":
        from gea.agents.stats import run_stats

        return run_stats()
    print("usage: gea agents [list|available|start|check|reset|mode|refresh|stats]")
    return 1
