"""`gea agents [list|available|start|check|reset|mode]` dispatch."""

from __future__ import annotations

from pathlib import Path

from gea import config
from gea.agents import herdr, manage, models, profiles, spec, state
from gea.i18n import t


def _project_profiles() -> list[profiles.AgentProfile]:
    """The project's subagents, resolved (agents.subagents, in priority order)."""
    return profiles.resolve_subagents(config.load_project(Path.cwd()))


def cmd_list() -> int:
    cfg = config.load_project(Path.cwd())
    value = config.agents(cfg)
    detected = profiles.load_profiles()
    print(t("agents.planner_set", planner=value.planner,
            model=value.planner_model or manage.DEFAULT_LABEL))
    for line in manage.describe(value, detected):
        print(line)
    unknown = profiles.unknown_subagent_ids(cfg, detected)
    if unknown:
        print(t("agents.unknown_ids", ids=", ".join(unknown)))
    return 0


def cmd_available() -> int:
    cfg = config.load_project(Path.cwd())
    mode = cfg.get("builders", {}).get("mode", "ask")
    print(f"mode {mode}")

    pools = state.load()
    for p in _project_profiles():
        if state.is_pool_available(p.pool, pools):
            model = p.model or "-"
            print(f"{p.id} {p.cli} {model}")
    return 0


def _save(mutate) -> int:
    """Apply `mutate(spec, detected) -> spec` to the project's agents and save them."""
    root = Path.cwd()
    cfg = config.load_project(root)
    detected = profiles.load_profiles()
    try:
        value = mutate(config.agents(cfg), detected)
    except ValueError as exc:
        print(exc)
        return 1
    config.store_agents(cfg, value)
    config.save_project(root, cfg)
    return 0


def cmd_planner(cli: str, model: str | None) -> int:
    if cli not in spec.KNOWN_CLIS:
        print(t("agents.unknown_cli", cli=cli, options=", ".join(spec.KNOWN_CLIS)))
        return 1
    if model and models.is_known(cli, model) is False:
        print(t("agents.model_unknown", model=model, cli=cli))
    code = _save(lambda value, _d: manage.set_planner(value, cli, model))
    if code == 0:
        print(t("agents.planner_set", planner=cli, model=model or manage.DEFAULT_LABEL))
    return code


def cmd_add(ident: str, cli: str | None, model: str | None, pool: str | None) -> int:
    if model and cli and models.is_known(cli, model) is False:
        print(t("agents.model_unknown", model=model, cli=cli))

    def mutate(value, detected):
        if cli:
            return manage.add_custom(value, ident, cli, model, pool, detected)
        return manage.add_detected(value, ident, detected)

    code = _save(mutate)
    if code == 0:
        print(t("agents.added", id=ident))
    return code


def cmd_remove(ident: str) -> int:
    code = _save(lambda value, detected: manage.remove(value, ident, detected))
    if code == 0:
        print(t("agents.removed", id=ident))
    return code


def cmd_models(cli: str | None) -> int:
    for name in [cli] if cli else manage.installed_clis():
        available = models.list_models(name)
        print(f"# {name}")
        for m in available or []:
            print(m)
        if available is None:
            print(f"({name} cannot list its models)")
    return 0


def cmd_start(agent_id: str) -> int:
    profile = next((p for p in _project_profiles() if p.id == agent_id), None)
    if not profile:
        print(f"unknown agent: {agent_id}")
        return 1
    cfg = config.load_project(Path.cwd())
    permissions = cfg.get("builders", {}).get("permissions", config.DEFAULT_PERMISSIONS)
    if permissions == "yolo":
        permissions = "safe"  # yolo only ever applies inside `gea delegate --worktree`
    result = herdr.start_builder_pane(agent_id, profile.cli, profile.model, Path.cwd(), permissions)
    print(result)
    return 0


def cmd_check(agent_id: str) -> int:
    profile = next((p for p in _project_profiles() if p.id == agent_id), None)
    if not profile:
        print(f"unknown agent: {agent_id}")
        return 1
    text = herdr.read_pane(herdr.pane_name_for(Path.cwd(), "builder", agent_id))
    until = state.detect_exhaustion(text)
    if until is None:
        print("OK")
        return 0
    for other in _project_profiles():
        if other.pool == profile.pool:
            state.mark_exhausted(other.pool, until)
    print(f"EXHAUSTED {state.iso(until)}")
    return 0


def cmd_reset(agent_id: str) -> int:
    profile = next((p for p in _project_profiles() if p.id == agent_id), None)
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
    if command == "manage":
        return manage.run_manage()
    if command == "planner":
        return cmd_planner(args.cli, args.model)
    if command == "add":
        return cmd_add(args.agent_id, args.cli, args.model, args.pool)
    if command == "remove":
        return cmd_remove(args.agent_id)
    if command == "models":
        return cmd_models(args.cli)
    if command == "refresh":
        return cmd_refresh()
    if command == "stats":
        from gea.agents.stats import run_stats

        return run_stats()
    print(
        "usage: gea agents [list|available|start|check|reset|mode|refresh|stats|"
        "manage|planner|add|remove|models]"
    )
    return 1
