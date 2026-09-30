"""`gea setup` — the machine wizard. Each step is idempotent and prints its
own ✓/!/✗ line (see gea.ui); `--yes` skips every prompt and takes the
recommended default.
"""

from __future__ import annotations

from gea import config, dryrun, platform, ui
from gea.agents import profiles
from gea.i18n import t
from gea.setup import agents_install, global_instructions, shadcn_setup, shell_rc, skills, tools


def _choose_language(assume_yes: bool) -> str:
    if assume_yes:
        return "es"
    index = ui.ask_choice(
        t("setup.lang_prompt"),
        [t("setup.lang_es"), t("setup.lang_en")],
        default_index=0,
    )
    return "es" if index == 0 else "en"


def _step_language(assume_yes: bool) -> None:
    lang = _choose_language(assume_yes)
    cfg = config.load_global()
    cfg["ui_lang"] = lang
    config.save_global(cfg)
    ui.ok(f"ui_lang = {lang}")


def _step_system_packages() -> None:
    installed = tools.ensure_system_packages()
    if installed:
        ui.ok(f"system packages installed: {', '.join(installed)}")
    else:
        ui.ok("system packages: all present")


def _step_mise() -> None:
    if tools.ensure_mise():
        ui.ok("mise installed")
    else:
        ui.ok("mise: already present" if platform.which("mise") else "mise: install failed")

    installed = tools.install_mise_tools()
    still_missing = tools.missing_mise_tools()
    if installed:
        ui.ok(f"mise tools installed: {', '.join(installed)}")
    if still_missing:
        ui.warn(f"still missing: {', '.join(still_missing)}")


def _step_node() -> None:
    if platform.which("node"):
        ui.ok("node: already present (respecting existing nvm/node)")
    elif tools.ensure_node():
        ui.ok("node installed via mise")
    else:
        ui.warn("node: install failed")


def _step_herdr() -> None:
    if tools.ensure_herdr():
        ui.ok("herdr installed")
    else:
        ui.ok("herdr: already present" if platform.which("herdr") else "herdr: install failed")


def _step_agents(assume_yes: bool) -> list[agents_install.AgentCli]:
    ui.info("Agents (Claude Code recommended as primary)")
    to_install: list[agents_install.AgentCli] = []
    for agent in agents_install.AGENT_CLIS:
        if platform.which(agent.binary):
            ui.ok(f"{agent.id}: already present")
            to_install.append(agent)
            continue
        recommended = agent.id == "claude"
        wants_it = assume_yes and recommended
        if not assume_yes:
            wants_it = ui.ask_yes_no(
                f"Install {agent.id}?" + (" (recommended)" if recommended else ""),
                default=recommended,
            )
        if wants_it:
            if agents_install.install_agent(agent):
                ui.ok(f"{agent.id} installed")
                to_install.append(agent)
            else:
                ui.warn(f"{agent.id}: install failed")
    return to_install


def _step_herdr_integrations(installed_agents: list[agents_install.AgentCli]) -> None:
    targets = agents_install.install_herdr_integrations(installed_agents)
    if targets:
        ui.ok(f"herdr integrations installed: {', '.join(targets)}")


def _step_rtk(installed_agents: list[agents_install.AgentCli]) -> None:
    if not config.load_global().get("optional", {}).get("rtk", True):
        ui.ok("rtk: skipped (opted out)")
        return
    if agents_install.ensure_rtk():
        ui.ok("rtk installed")
    else:
        ui.ok("rtk: already present" if platform.which("rtk") else "rtk: install failed")
    agents_install.rtk_init_for(installed_agents)
    ui.ok("rtk hooks wired into detected agents")


def _step_codegraph() -> None:
    if agents_install.ensure_codegraph():
        ui.ok("codegraph installed")
    else:
        ok = platform.which("codegraph") is not None
        ui.ok("codegraph: already present" if ok else "codegraph: install failed")
    agents_install.codegraph_install_agents()


def _step_shadcn(assume_yes: bool) -> None:
    if agents_install.ensure_shadcn_cli():
        ui.ok("shadcn CLI installed")
    else:
        ok = platform.which("shadcn") is not None
        ui.ok("shadcn CLI: already present" if ok else "shadcn CLI: install failed")
    shadcn_setup.review_mcp_servers(assume_yes=assume_yes)


def _step_agent_profiles() -> None:
    detected = profiles.refresh_and_save()
    ui.ok(f"builder profiles: {', '.join(p.id for p in detected) or 'none detected'}")


def _step_global_instructions(installed_agents: list[agents_install.AgentCli]) -> None:
    changed = global_instructions.apply_for_installed_agents([a.id for a in installed_agents])
    for path in changed:
        ui.ok(f"global instructions updated: {path}")


def _step_skills_sync(installed_agents: list[agents_install.AgentCli]) -> None:
    ids = [a.id for a in installed_agents]
    synced = skills.sync_all_skills(ids)
    if synced:
        ui.ok(f"skills synced: {', '.join(synced)}")


def _step_cleanup_legacy() -> None:
    actions = shell_rc.cleanup_legacy_setup()
    for action in actions:
        ui.ok(action)


def _step_optional(assume_yes: bool) -> None:
    """Ask which optional pieces to install; the answers persist in
    ~/gea/config.json["optional"] so `gea update`/`skills sync` honor them."""
    cfg = config.load_global()
    optional = cfg.setdefault("optional", {})
    questions = {
        "ponytail": "Install the ponytail skill (minimal-code discipline)?",
        "rtk": "Install rtk (token-saving command output proxy)?",
    }
    for name, question in questions.items():
        current = optional.get(name, True)
        optional[name] = current if assume_yes else ui.ask_yes_no(question, default=current)
        ui.ok(f"{name}: {'on' if optional[name] else 'off'}")
    config.save_global(cfg)


def _only_steps(assume_yes: bool) -> dict[str, object]:
    return {
        "lang": lambda: _step_language(assume_yes),
        "optional": lambda: _step_optional(assume_yes),
        "system": _step_system_packages,
        "mise": _step_mise,
        "node": _step_node,
        "herdr": _step_herdr,
        "cleanup": _step_cleanup_legacy,
    }


def run_setup(assume_yes: bool = False, only: str | None = None, dry_run: bool = False) -> int:
    dryrun.enable(dry_run)
    if dry_run:
        ui.info("dry-run: nothing will be installed or written")
    only_steps = _only_steps(assume_yes)
    if only:
        if only not in only_steps:
            ui.err(t("cli.unknown_command", command=only))
            return 1
        only_steps[only]()
        return 0

    agents_found: list[agents_install.AgentCli] = []

    def _agents() -> None:
        agents_found.extend(_step_agents(assume_yes))

    # Ordered (label, step) pairs — printed as "[n/total]" headers so the
    # user always knows what's currently happening, even while a
    # slow/streaming installer step is quiet for a while.
    steps = [
        ("language", lambda: _step_language(assume_yes)),
        ("optional tools", lambda: _step_optional(assume_yes)),
        ("system packages", _step_system_packages),
        ("mise tools", _step_mise),
        ("node", _step_node),
        ("herdr", _step_herdr),
        ("agents", _agents),
        ("herdr integrations", lambda: _step_herdr_integrations(agents_found)),
        ("builder profiles", _step_agent_profiles),
        ("rtk", lambda: _step_rtk(agents_found)),
        ("codegraph", _step_codegraph),
        ("shadcn", lambda: _step_shadcn(assume_yes)),
        ("global instructions", lambda: _step_global_instructions(agents_found)),
        ("skills", lambda: _step_skills_sync(agents_found)),
        ("legacy cleanup", _step_cleanup_legacy),
    ]
    for n, (label, step) in enumerate(steps, start=1):
        ui.info(f"[{n}/{len(steps)}] {label}")
        step()

    ui.ok("gea setup complete")
    return 0


def run_update() -> int:
    tools.install_mise_tools()
    installed_agents = agents_install.detected_agents()
    _step_global_instructions(installed_agents)
    _step_skills_sync(installed_agents)
    ui.ok("gea update complete")
    return 0
