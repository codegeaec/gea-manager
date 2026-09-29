"""Managed block of instructions injected into each agent's global
instructions file (~/.claude/CLAUDE.md, ~/.codex/AGENTS.md, ...).

The block lives between markers so it can be regenerated on every
`gea setup`/`gea update` without touching anything else the user wrote in
that file.
"""

from __future__ import annotations

from pathlib import Path

from gea import dryrun, manifest, paths

START_MARKER = "<!-- gea:start -->"
END_MARKER = "<!-- gea:end -->"

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
    return f"{START_MARKER}\n{BLOCK_BODY.strip()}\n{END_MARKER}\n"


def _target_path(agent: str) -> Path:
    return paths.home() / TARGETS[agent]


def apply_to_file(path: Path) -> bool:
    """Insert or replace the managed block in `path`. Creates the file
    (and parent dirs) if it doesn't exist. Returns True if the file was
    changed."""
    block = render_block()
    if dryrun.active():
        dryrun.report(f"update the gea block in {path}")
        return True
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        return True

    original = path.read_text(encoding="utf-8")
    if START_MARKER in original and END_MARKER in original:
        before, rest = original.split(START_MARKER, 1)
        _old, after = rest.split(END_MARKER, 1)
        new_content = before + block.rstrip("\n") + after
    else:
        separator = "\n\n" if original and not original.endswith("\n\n") else ""
        new_content = original + separator + block

    if new_content == original:
        return False
    path.write_text(new_content, encoding="utf-8")
    return True


def remove_from_file(path: Path) -> bool:
    """Strip the managed block from `path`. Returns True if it changed."""
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    if START_MARKER not in original or END_MARKER not in original:
        return False
    before, rest = original.split(START_MARKER, 1)
    _block, after = rest.split(END_MARKER, 1)
    remaining = (before.rstrip("\n") + "\n" + after.lstrip("\n")).strip("\n")
    if dryrun.active():
        dryrun.report(f"remove the gea block from {path}")
        return True
    path.write_text(remaining + "\n" if remaining else "", encoding="utf-8")
    return True


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
