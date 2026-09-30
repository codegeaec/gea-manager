"""Managed block of instructions injected into each agent's global
instructions file (~/.claude/CLAUDE.md, ~/.codex/AGENTS.md, ...).

The block lives between markers so it can be regenerated on every
`gea setup`/`gea update` without touching anything else the user wrote in
that file.
"""

from __future__ import annotations

from pathlib import Path

from gea import managed_block, manifest, paths
from gea.managed_block import END_MARKER, START_MARKER  # noqa: F401 (re-exported)

# (label, target path relative to $HOME) — verified per machine at setup
# time; a missing file/dir is simply skipped (that agent isn't installed).
TARGETS: dict[str, str] = {
    "claude": ".claude/CLAUDE.md",
    "codex": ".codex/AGENTS.md",
    "opencode": ".config/opencode/AGENTS.md",
}

BLOCK_BODY = """## Available CLI tools

Prefer these tools when applicable:

- rg: search source code
- fd: find files
- jq: process JSON
- yq: process YAML
- ast-grep: structural code search
- gh: GitHub operations
- git: version control
- just: project tasks
- duckdb: query CSV/JSON/Parquet
- sqlite3: inspect SQLite databases
- curl: HTTP/API requests
- shellcheck: validate shell scripts

## Token-saving tools

- **rtk**: a hook already rewrites your Bash commands (e.g. `git status` ->
  `rtk git status`) to compact their output. Don't bypass it by calling the
  underlying tool with different flags to get "the real" output — the
  compact form is enough for nearly everything; only drop to the raw
  command when you actually need the full, uncompacted output.
- **codegraph**: if this project has a `.codegraph/` directory, use its MCP
  tools to look up symbols/call sites instead of grepping the whole tree.

## shadcn/ui

If this project uses shadcn/ui (a `components.json` file), **always** use
its CLI (`add`, `search`, `view`, `diff`, `init`) through the project's
package manager runner (`pnpm dlx shadcn@latest ...` / `npx shadcn@latest
...` / `bunx shadcn@latest ...`, matching the project's lockfile) — never
through an MCP server. If you find a shadcn MCP server configured, flag it
and recommend removing it (`gea doctor` also detects this).

## File size

Keep files at or under 400 lines. If a change genuinely needs more,
justify it explicitly instead of splitting the file in an arbitrary way.
"""


def render_block() -> str:
    return managed_block.render(BLOCK_BODY)


def _target_path(agent: str) -> Path:
    return paths.home() / TARGETS[agent]


def apply_to_file(path: Path) -> bool:
    """Insert or replace the global instructions block in `path`."""
    return managed_block.upsert(path, BLOCK_BODY)


def remove_from_file(path: Path) -> bool:
    """Strip the block from `path`. Returns True if it changed."""
    return managed_block.remove(path)


def apply_for_installed_agents(installed_agents: list[str]) -> list[str]:
    """Apply the block to every target whose agent is in `installed_agents`.

    Returns the list of paths actually changed.
    """
    changed: list[str] = []
    for agent in installed_agents:
        if agent not in TARGETS:
            continue
        path = _target_path(agent)
        if apply_to_file(path):
            changed.append(str(path))
            manifest.record(manifest.KIND_INSTRUCTIONS, str(path))
    return changed
