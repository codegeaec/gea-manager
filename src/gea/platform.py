"""OS/platform detection helpers used by setup and workspace commands."""

from __future__ import annotations

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
