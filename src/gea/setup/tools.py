"""Base toolchain installers: system packages, mise-managed CLI tools, and
node. Each `ensure_*` function is idempotent (checks first, installs only
if missing) and returns True if it changed anything.
"""

from __future__ import annotations

from gea import platform, proc, ui

# CLI tools installed via mise (https://mise.jdx.dev) — same binary names
# on Linux, WSL and macOS, no sudo required. Kept in one place so `gea
# doctor`/`gea setup`/the global-instructions block all agree on the list.
MISE_TOOLS = [
    "gh", "jq", "yq", "ripgrep", "fd", "ast-grep", "just", "duckdb", "shellcheck", "uv", "lazygit",
]

# System packages that need the OS package manager (not available via mise
# as portable binaries, or need to be truly "system", like a compiler).
SYSTEM_PACKAGES_APT = ["git", "curl", "sqlite3", "build-essential"]
SYSTEM_PACKAGES_BREW = ["git", "curl", "sqlite3"]


def ensure_mise() -> bool:
    if platform.which("mise"):
        return False
    ui.info("Installing mise…")
    proc.run_visible(["bash", "-c", "curl -fsSL https://mise.run | sh"], timeout=120)
    platform.refresh_mise_shims_on_path()
    return platform.which("mise") is not None


def install_mise_tools(tools: list[str] | None = None) -> list[str]:
    """Install each missing tool with `mise use -g <tool>`.

    Returns the list of tools mise reported as installed successfully
    (checked with `which()` right after, PATH already refreshed) — callers
    can diff against `missing_mise_tools()` to see what still failed.
    """
    tools = tools if tools is not None else MISE_TOOLS
    installed: list[str] = []
    for tool in tools:
        binary = _binary_name(tool)
        if platform.which(binary):
            continue
        ui.info(f"Installing {tool} (mise)…")
        proc.run_visible(["mise", "use", "-g", tool], timeout=120)
        platform.refresh_mise_shims_on_path()
        if platform.which(binary):
            installed.append(tool)
    return installed


def _binary_name(mise_tool: str) -> str:
    # A couple of mise package names don't match their binary name.
    return {"ripgrep": "rg"}.get(mise_tool, mise_tool)


def missing_mise_tools(tools: list[str] | None = None) -> list[str]:
    tools = tools if tools is not None else MISE_TOOLS
    return [tool for tool in tools if not platform.which(_binary_name(tool))]


def ensure_system_packages() -> list[str]:
    """Install missing system packages via apt or brew. No-op (returns [])
    on a platform with neither."""
    if platform.has_apt():
        packages = [p for p in SYSTEM_PACKAGES_APT if not platform.which(p.split("-")[0])]
        if packages:
            ui.info(f"Installing system packages (apt): {', '.join(packages)}…")
            proc.run_visible(["sudo", "apt-get", "update"], timeout=120)
            proc.run_visible(["sudo", "apt-get", "install", "-y", *packages], timeout=300)
        return packages
    if platform.has_brew():
        packages = [p for p in SYSTEM_PACKAGES_BREW if not platform.which(p)]
        if packages:
            ui.info(f"Installing system packages (brew): {', '.join(packages)}…")
            proc.run_visible(["brew", "install", *packages], timeout=300)
        return packages
    return []


def ensure_node() -> bool:
    """Respect an existing nvm/node install; otherwise use mise for node LTS."""
    if platform.which("node"):
        return False
    ui.info("Installing node (mise)…")
    proc.run_visible(["mise", "use", "-g", "node@lts"], timeout=180)
    platform.refresh_mise_shims_on_path()
    return platform.which("node") is not None


def ensure_herdr() -> bool:
    if platform.which("herdr"):
        return False
    ui.info("Installing herdr…")
    proc.run_visible(["bash", "-c", "curl -fsSL https://herdr.dev/install.sh | sh"], timeout=120)
    return platform.which("herdr") is not None
