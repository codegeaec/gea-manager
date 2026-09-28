"""Installers for the coding-agent CLIs, rtk and codegraph.

Each agent is optional except the primary one, chosen in `gea init`/`gea
setup`'s wizard. Kept data-driven so adding a new agent CLI is one entry,
not a new function.
"""

from __future__ import annotations

from dataclasses import dataclass

from gea import platform, proc, ui


@dataclass(frozen=True)
class AgentCli:
    id: str
    binary: str
    install_cmd: list[str]
    # rtk's `--agent`/`--codex`/etc. flag for `rtk init -g`, if any.
    rtk_flag: str | None = None
    herdr_integration_target: str | None = None


AGENT_CLIS: list[AgentCli] = [
    AgentCli(
        id="claude",
        binary="claude",
        install_cmd=["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
        rtk_flag=None,  # rtk's default target is Claude Code
    ),
    AgentCli(
        id="opencode",
        binary="opencode",
        install_cmd=["npm", "install", "-g", "opencode-ai@latest"],
        rtk_flag="--opencode",
        herdr_integration_target="opencode",
    ),
    AgentCli(
        id="codex",
        binary="codex",
        install_cmd=["npm", "install", "-g", "@openai/codex"],
        rtk_flag="--codex",
        herdr_integration_target="codex",
    ),
    AgentCli(
        id="agy",
        binary="agy",
        install_cmd=["npm", "install", "-g", "@antigravity/cli"],
        rtk_flag="--agent antigravity",
        herdr_integration_target="antigravity-cli",
    ),
    AgentCli(
        id="kimi",
        binary="kimi",
        install_cmd=["uv", "tool", "install", "kimi-code"],
        rtk_flag="--agent kimi",
    ),
]


def detected_agents() -> list[AgentCli]:
    return [a for a in AGENT_CLIS if platform.which(a.binary)]


def install_agent(agent: AgentCli) -> bool:
    if platform.which(agent.binary):
        return False
    ui.info(f"Installing {agent.id}…")
    proc.run_visible(agent.install_cmd, timeout=180)
    return platform.which(agent.binary) is not None


def install_herdr_integrations(agents: list[AgentCli]) -> list[str]:
    """Run `herdr integration install <target>` for each agent that needs
    one. Returns the targets attempted."""
    targets = [a.herdr_integration_target for a in agents if a.herdr_integration_target]
    for target in targets:
        proc.run_visible(["herdr", "integration", "install", target], timeout=60)
    return targets


RTK_INSTALL_URL = "https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh"


def ensure_rtk() -> bool:
    if platform.which("rtk"):
        return False
    ui.info("Installing rtk…")
    proc.run_visible(["bash", "-c", f"curl -fsSL {RTK_INSTALL_URL} | sh"], timeout=120)
    return platform.which("rtk") is not None


def rtk_init_for(agents: list[AgentCli]) -> None:
    """Wire rtk's Bash-rewrite hook into every detected agent.

    `--auto-patch` keeps this non-interactive (rtk's own flag for CI/CD —
    see its README) so it can't sit waiting on a prompt the caller can't
    see; `run_visible` means if it prints anything anyway, it's not hidden.
    """
    ui.info("Wiring rtk into detected agents…")
    proc.run_visible(["rtk", "init", "-g", "--auto-patch"], timeout=60)
    for agent in agents:
        if agent.rtk_flag:
            cmd = ["rtk", "init", "-g", "--auto-patch", *agent.rtk_flag.split()]
            proc.run_visible(cmd, timeout=60)


CODEGRAPH_INSTALL_URL = (
    "https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh"
)


def ensure_codegraph() -> bool:
    if platform.which("codegraph"):
        return False
    ui.info("Installing codegraph…")
    proc.run_visible(["bash", "-c", f"curl -fsSL {CODEGRAPH_INSTALL_URL} | sh"], timeout=120)
    return platform.which("codegraph") is not None


def codegraph_install_agents() -> None:
    """Wire the codegraph MCP server into every detected agent."""
    ui.info("Wiring codegraph into detected agents…")
    proc.run_visible(["codegraph", "install"], timeout=60)


def ensure_shadcn_cli() -> bool:
    if platform.which("shadcn"):
        return False
    ui.info("Installing shadcn CLI…")
    proc.run_visible(["npm", "install", "-g", "shadcn"], timeout=120)
    return platform.which("shadcn") is not None
