"""`gea setup` — the machine wizard. Each step is idempotent and prints its
own ✓/!/✗ line (see gea.ui); `--yes` skips every prompt and takes the
recommended default.
"""

from __future__ import annotations

from gea import config, platform, ui
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


def _step_global_instructions(installed_agents: list[agents_install.AgentCli]) -> None:
    changed = global_instructions.apply_for_installed_agents([a.id for a in installed_agents])
    for path in changed:
        ui.ok(f"global instructions updated: {path}")


def _step_skills_sync(installed_agents: list[agents_install.AgentCli]) -> None:
    ids = [a.id for a in installed_agents]
    synced = skills.sync_third_party_skills(ids) + skills.sync_gea_skills(ids)
    if synced:
        ui.ok(f"skills synced: {', '.join(synced)}")


def _step_cleanup_legacy() -> None:
    actions = shell_rc.cleanup_legacy_setup()
    for action in actions:
        ui.ok(action)


def run_setup(assume_yes: bool = False, only: str | None = None) -> int:
    steps: dict[str, object] = {
        "lang": lambda: _step_language(assume_yes),
        "system": _step_system_packages,
        "mise": _step_mise,
        "node": _step_node,
        "herdr": _step_herdr,
        "cleanup": _step_cleanup_legacy,
    }
    if only and only not in steps:
        ui.err(t("cli.unknown_command", command=only))
        return 1

    if only:
        if only in steps:
            steps[only]()
        return 0

    for name in ("lang", "system", "mise", "node", "herdr"):
        steps[name]()

    installed_agents = _step_agents(assume_yes)
    _step_herdr_integrations(installed_agents)
    _step_rtk(installed_agents)
    _step_codegraph()
    _step_shadcn(assume_yes)
    _step_global_instructions(installed_agents)
    _step_skills_sync(installed_agents)
    _step_cleanup_legacy()

    ui.ok("gea setup complete")
    return 0


def run_update() -> int:
    tools.install_mise_tools()
    installed_agents = agents_install.detected_agents()
    _step_global_instructions(installed_agents)
    _step_skills_sync(installed_agents)
    ui.ok("gea update complete")
    return 0
