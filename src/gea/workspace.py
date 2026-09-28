"""`gea` with no arguments: open (or focus) this project's herdr workspace.

Two tabs, idempotent by label (ported from the old herdr-setup gist's
`herdr-repo`, minus the llama.cpp/WSL-specific opencode-roles logic):

- `<primary>` — the project's primary agent (gea.json["primary"],
  "claude" if unset), an interactive CLI tab.
- `terminal` — a plain shell, for `pnpm dev`/anything else the user wants
  to run by hand.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from gea import config, proc, ui
from gea.agents.herdr import CLI_ARGS, DEFAULT_CLI_ARGS, herdr_json, prompt_pane


def _find_repo_root(start: Path | None = None) -> Path:
    start = start or Path.cwd()
    out, _err, code = proc.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"])
    if code == 0 and out.strip():
        return Path(out.strip())
    return start


def _safe_label(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-")
    return slug or "repo"


def _find_or_create_workspace(label: str, repo_root: Path) -> str | None:
    listing, err = herdr_json(["workspace", "list"])
    if err is None:
        for ws in listing.get("workspaces", []):
            if ws.get("label") == label:
                return ws.get("workspace_id")

    created, err = herdr_json(
        ["workspace", "create", "--cwd", str(repo_root), "--label", label, "--focus"]
    )
    if err:
        return None
    return created.get("workspace", {}).get("workspace_id")


def _existing_tab_id(workspace_id: str, label: str) -> str | None:
    listing, err = herdr_json(["tab", "list", "--workspace", workspace_id])
    if err:
        return None
    for tab in listing.get("tabs", []):
        if tab.get("label") == label:
            return tab.get("tab_id")
    return None


def _create_tab(workspace_id: str, repo_root: Path, label: str) -> str | None:
    cmd = [
        "tab", "create", "--workspace", workspace_id,
        "--cwd", str(repo_root), "--label", label, "--no-focus",
    ]
    result, err = herdr_json(cmd)
    if err:
        return None
    return result.get("root_pane", {}).get("pane_id")


def _ensure_agent_tab(workspace_id: str, repo_root: Path, label: str, cli: str) -> bool:
    """Create the `<label>` tab and start `cli` in it if it doesn't exist
    yet. Returns True only when this call actually created and started it
    — callers use that to do first-time-only setup (e.g. picking a model),
    never on a reopen of an already-running tab."""
    if _existing_tab_id(workspace_id, label):
        return False
    pane_id = _create_tab(workspace_id, repo_root, label)
    if not pane_id:
        ui.warn(f"could not create tab '{label}'")
        return False
    cli_cfg = CLI_ARGS.get(cli, DEFAULT_CLI_ARGS)
    start_args = ["agent", "start", label, "--kind", cli, "--pane", pane_id, "--"] + cli_cfg["base"]
    _result, err = herdr_json(start_args, timeout=65)
    if err:
        ui.warn(f"tab '{label}' created but agent failed to start ({err})")
        return False
    return True


def _ensure_plain_tab(workspace_id: str, repo_root: Path, label: str) -> None:
    if _existing_tab_id(workspace_id, label):
        return
    if not _create_tab(workspace_id, repo_root, label):
        ui.warn(f"could not create tab '{label}'")


def open_or_focus() -> int:
    repo_root = _find_repo_root()
    cfg = config.load_project(repo_root)
    primary = cfg.get("primary") or "claude"
    label = _safe_label(repo_root.name)

    workspace_id = _find_or_create_workspace(label, repo_root)
    if not workspace_id:
        ui.err("could not create or find the herdr workspace")
        return 1

    created = _ensure_agent_tab(workspace_id, repo_root, primary, primary)
    _ensure_plain_tab(workspace_id, repo_root, "terminal")

    if created and primary == "claude":
        model = cfg.get("primaryModel")
        if model:
            ui.ok(f"setting /model {model} in the claude tab")
            prompt_pane(primary, f"/model {model}", wait=False)

    if os.environ.get("HERDR_ENV") == "1":
        herdr_json(["workspace", "focus", workspace_id])
        return 0

    os.execvp("herdr", ["herdr"])
    return 0  # unreachable — execvp replaces this process on success
