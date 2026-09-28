"""OS/platform detection helpers used by setup and workspace commands."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


def is_wsl() -> bool:
    if not is_linux():
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def which(name: str) -> str | None:
    return shutil.which(name)


def has_apt() -> bool:
    return which("apt-get") is not None


def has_brew() -> bool:
    return which("brew") is not None


def refresh_mise_shims_on_path() -> None:
    """Make sure a binary mise just installed is found by `which()` right
    away, in this same process, without waiting for a new shell.

    mise puts shims in `~/.local/share/mise/shims` (or `$MISE_DATA_DIR/
    shims`); a shell only picks that up via `mise activate` in its rc file,
    which a script invoked mid-run never re-sources. Without this, `gea
    setup` would install a tool with mise and then immediately report it
    as still missing.
    """
    data_dir = os.environ.get("MISE_DATA_DIR") or str(Path.home() / ".local" / "share" / "mise")
    shims_dir = str(Path(data_dir) / "shims")
    current_path = os.environ.get("PATH", "")
    if shims_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = shims_dir + os.pathsep + current_path
