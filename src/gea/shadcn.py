"""Detect (and optionally remove) shadcn MCP servers so shadcn is always
driven through its CLI instead — see AGENTS.md's global instructions block
and gea-manager's plan for the rationale (CLI gives diffable, reviewable
component code; the MCP server duplicates that path)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from gea import paths

# Config files that may embed an MCP server named "shadcn" (or containing
# "shadcn" in its command/args), keyed by a human label for reporting.
_CANDIDATE_CONFIGS: list[tuple[str, str]] = [
    ("Claude Code (user)", "~/.claude.json"),
    ("Codex CLI", "~/.codex/config.toml"),
]


@dataclass
class ShadcnMcpHit:
    location: str
    key: str | None = None


def _expand(path_str: str) -> Path:
    return Path(path_str.replace("~", str(paths.home()), 1))


def _scan_mcp_servers_json(path: Path, label: str) -> list[ShadcnMcpHit]:
    """Scan a JSON file for an `mcpServers`/`mcp_servers` map with a shadcn entry."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    hits: list[ShadcnMcpHit] = []
    for servers_key in ("mcpServers", "mcp_servers", "mcp"):
        servers = data.get(servers_key)
        if not isinstance(servers, dict):
            continue
        for name, server_cfg in servers.items():
            haystack = json.dumps(server_cfg).lower() + name.lower()
            if "shadcn" in haystack:
                hits.append(ShadcnMcpHit(location=f"{label} ({path})", key=name))
    return hits


def detect_mcp_servers(project_root: Path | None = None) -> list[ShadcnMcpHit]:
    """Look for shadcn MCP servers in known global and project config files."""
    hits: list[ShadcnMcpHit] = []
    for label, path_str in _CANDIDATE_CONFIGS:
        hits.extend(_scan_mcp_servers_json(_expand(path_str), label))

    if project_root is not None:
        hits.extend(_scan_mcp_servers_json(project_root / ".mcp.json", "project .mcp.json"))

    return hits


def remove_from_claude_config(server_name: str) -> bool:
    """Remove a shadcn MCP entry from ~/.claude.json's mcpServers map.

    Returns True if something was removed. Caller is responsible for
    backing up the file first (see setup.tools.backup_file).
    """
    path = _expand("~/.claude.json")
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or server_name not in servers:
        return False
    del servers[server_name]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True
