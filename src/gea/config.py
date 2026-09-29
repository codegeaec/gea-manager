"""Global (~/gea/config.json) and per-project (gea.json) configuration.

Both are plain JSON with sane defaults — missing keys never crash callers,
they just fall back (see `load_global`/`load_project`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gea import dryrun, paths

# Bumped whenever a file's shape changes incompatibly. There are no
# migrations yet: a file written by a *newer* gea is refused on load
# instead of being silently misread (or clobbered on the next save).
SCHEMA_VERSION = 1

AUTONOMY_LEVELS = ("supervised", "balanced", "autonomous")
DEFAULT_AUTONOMY = "balanced"


class ConfigError(Exception):
    """A config file is unusable (newer schema, wrong type, bad value)."""


DEFAULT_GLOBAL_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "ui_lang": "es",
    "primary_agent": None,
    "builders": {"mode": "ask"},
}

DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "name": None,
    "primary": None,
    # Only meaningful when primary == "claude": sent as "/model <value>" to
    # the claude tab the first time gea creates it (see workspace.py). None
    # means don't set a model automatically.
    "primaryModel": None,
    "tasks": {"location": "home"},
    "verify": [],
    "builders": {"mode": "ask", "allow": [], "ponytail": True},
    "lang": {"commits": "es", "docs": "es"},
    "pm": None,
    # How much freedom a builder gets (see AUTONOMY_LEVELS and autonomy.py).
    "autonomy": DEFAULT_AUTONOMY,
}


def validate(data: dict[str, Any], path: Path) -> None:
    version = data.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ConfigError(f"{path}: invalid schema_version {version!r}")
    if version > SCHEMA_VERSION:
        raise ConfigError(
            f"{path}: schema_version {version} is newer than this gea supports "
            f"({SCHEMA_VERSION}) — upgrade gea"
        )
    autonomy = data.get("autonomy", DEFAULT_AUTONOMY)
    if autonomy not in AUTONOMY_LEVELS:
        raise ConfigError(f"{path}: autonomy must be one of {', '.join(AUTONOMY_LEVELS)}")


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a JSON object")
    merged = dict(default)
    merged.update(data)
    validate(merged, path)
    return merged


def _write_json(path: Path, data: dict[str, Any]) -> None:
    if dryrun.active():
        dryrun.report(f"write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_global() -> dict[str, Any]:
    return _read_json(paths.global_config_path(), DEFAULT_GLOBAL_CONFIG)


def save_global(data: dict[str, Any]) -> None:
    _write_json(paths.global_config_path(), data)


def project_config_path(repo_root: Path) -> Path:
    return repo_root / "gea.json"


def load_project(repo_root: Path) -> dict[str, Any]:
    return _read_json(project_config_path(repo_root), DEFAULT_PROJECT_CONFIG)


def save_project(repo_root: Path, data: dict[str, Any]) -> None:
    _write_json(project_config_path(repo_root), data)
