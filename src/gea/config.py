"""Global (~/gea/config.json) and per-project (gea.json) configuration.

Both are plain JSON with sane defaults — missing keys never crash callers,
they just fall back (see `load_global`/`load_project`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gea import paths

DEFAULT_GLOBAL_CONFIG: dict[str, Any] = {
    "ui_lang": "es",
    "primary_agent": None,
    "builders": {"mode": "ask"},
}

DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
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
}


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)
    merged = dict(default)
    merged.update(data)
    return merged


def _write_json(path: Path, data: dict[str, Any]) -> None:
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
