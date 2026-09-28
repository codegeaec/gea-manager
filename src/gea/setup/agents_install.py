"""Installers for the coding-agent CLIs, rtk and codegraph.

Each agent is optional except the primary one, chosen in `gea init`/`gea
setup`'s wizard. Kept data-driven so adding a new agent CLI is one entry,
not a new function.
"""

from __future__ import annotations

from dataclasses import dataclass

from gea import platform, proc


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
    proc.run(agent.install_cmd, timeout=180)
    return platform.which(agent.binary) is not None


def install_herdr_integrations(agents: list[AgentCli]) -> list[str]:
    """Run `herdr integration install <target>` for each agent that needs
    one. Returns the targets attempted."""
    targets = [a.herdr_integration_target for a in agents if a.herdr_integration_target]
    for target in targets:
        proc.run(["herdr", "integration", "install", target], timeout=60)
    return targets


RTK_INSTALL_URL = "https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh"


def ensure_rtk() -> bool:
    if platform.which("rtk"):
        return False
    proc.run(["bash", "-c", f"curl -fsSL {RTK_INSTALL_URL} | sh"], timeout=120)
    return platform.which("rtk") is not None


def rtk_init_for(agents: list[AgentCli]) -> None:
    """Wire rtk's Bash-rewrite hook into every detected agent."""
    proc.run(["rtk", "init", "-g"], timeout=60)
    for agent in agents:
        if agent.rtk_flag:
            proc.run(["rtk", "init", "-g", *agent.rtk_flag.split()], timeout=60)


CODEGRAPH_INSTALL_URL = (
    "https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh"
)


def ensure_codegraph() -> bool:
    if platform.which("codegraph"):
        return False
    proc.run(["bash", "-c", f"curl -fsSL {CODEGRAPH_INSTALL_URL} | sh"], timeout=120)
    return platform.which("codegraph") is not None


def codegraph_install_agents() -> None:
    """Wire the codegraph MCP server into every detected agent."""
    proc.run(["codegraph", "install"], timeout=60)


def ensure_shadcn_cli() -> bool:
    if platform.which("shadcn"):
        return False
    proc.run(["npm", "install", "-g", "shadcn"], timeout=120)
    return platform.which("shadcn") is not None
