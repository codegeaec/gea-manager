"""Filesystem locations gea reads and writes on the user's machine.

Every user-machine-specific path must go through this module (AGENTS.md
rule 5) — never hardcode a home directory elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("HOME") or os.path.expanduser("~"))


def gea_home() -> Path:
    """~/gea — the root for global config, state and per-project task trees."""
    override = os.environ.get("GEA_HOME")
    return Path(override) if override else home() / "gea"


def global_config_path() -> Path:
    return gea_home() / "config.json"


def global_state_path() -> Path:
    return gea_home() / "state.json"


def projects_root() -> Path:
    return gea_home() / "projects"


def project_task_root(project_name: str) -> Path:
    return projects_root() / project_name


def local_bin() -> Path:
    return home() / ".local" / "bin"


def skill_dirs() -> list[Path]:
    """Where agents keep globally installed skills (only existing dirs)."""
    candidates = [
        home() / ".claude" / "skills",
        home() / ".agents" / "skills",
        home() / ".codex" / "skills",
        home() / ".config" / "opencode" / "skills",
    ]
    return [p for p in candidates if p.is_dir()]


def shell_rc_files() -> list[Path]:
    candidates = [home() / ".bashrc", home() / ".zshrc"]
    return [p for p in candidates if p.exists()]
