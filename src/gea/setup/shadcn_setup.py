"""Interactive review of detected shadcn MCP servers during `gea setup`."""

from __future__ import annotations

from gea import shadcn, ui


def review_mcp_servers(assume_yes: bool = False) -> None:
    hits = shadcn.detect_mcp_servers()
    if not hits:
        ui.ok("no shadcn MCP servers found")
        return

    for hit in hits:
        ui.warn(f"shadcn MCP server found: {hit.location}")

    if "Claude Code" not in "".join(h.location for h in hits):
        return

    remove = assume_yes or ui.ask_yes_no(
        "Remove the shadcn MCP server from Claude Code and use the CLI instead?",
        default=True,
    )
    if not remove:
        ui.info("Keeping shadcn MCP as-is — the CLI is still recommended for new work.")
        return

    for hit in hits:
        if hit.key and "Claude Code" in hit.location:
            _backup_claude_config()
            if shadcn.remove_from_claude_config(hit.key):
                ui.ok(f"removed shadcn MCP server '{hit.key}' from Claude Code")


def _backup_claude_config() -> None:
    import shutil
    from datetime import datetime

    from gea import paths

    path = paths.home() / ".claude.json"
    if path.exists():
        backup = path.with_suffix(path.suffix + f".bak.{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(path, backup)
