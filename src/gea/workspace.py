"""`gea` with no arguments: open (or focus) this project's herdr workspace.

Tabs, idempotent by label (ported from the old herdr-setup gist's
`herdr-repo`, minus the llama.cpp/WSL-specific opencode-roles logic):

- `<primary>` — the project's primary agent (gea.json["primary"],
  "claude" if unset), an interactive CLI tab. On a brand-new workspace it
  reuses the tab herdr creates with the workspace, so no stray "1" is left.
- `terminal` — a plain shell, for anything else the user wants to run by hand.
- one tab per entry of gea.json["tabs"] (`label`, `cwd` relative to the repo,
  optional `command` run only when the tab is created), e.g. for monorepos.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
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


@dataclass
class Workspace:
    id: str
    # Only set right after herdr created the workspace: the tab/pane it comes
    # with, which gea reuses for the primary agent instead of leaving them idle.
    initial_tab_id: str | None = None
    initial_pane_id: str | None = None


def _find_or_create_workspace(label: str, repo_root: Path) -> Workspace | None:
    listing, err = herdr_json(["workspace", "list"])
    if err is None:
        for ws in listing.get("workspaces", []):
            if ws.get("label") == label:
                return Workspace(ws.get("workspace_id"))

    created, err = herdr_json(
        ["workspace", "create", "--cwd", str(repo_root), "--label", label, "--focus"]
    )
    workspace_id = created.get("workspace", {}).get("workspace_id")
    if err or not workspace_id:
        return None
    return Workspace(
        workspace_id,
        created.get("tab", {}).get("tab_id"),
        created.get("root_pane", {}).get("pane_id"),
    )


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


def _agent_name(cli: str, repo_label: str) -> str:
    """herdr agent names are unique among live agents, so a bare `claude` in a
    second project would collide with the first one's. Tab labels stay short."""
    return f"{cli}-{repo_label}"[:32].rstrip("-_")


def _adopt_initial_tab(initial: tuple[str, str], label: str) -> str | None:
    """Rename the workspace's own first tab to `label`; its pane, or None."""
    tab_id, pane_id = initial
    _result, err = herdr_json(["tab", "rename", tab_id, label])
    if err:
        ui.warn(f"could not rename the initial tab to '{label}' ({err})")
        return None
    return pane_id


def _ensure_agent_tab(
    workspace_id: str,
    repo_root: Path,
    label: str,
    cli: str,
    initial: tuple[str, str] | None = None,
    agent_name: str | None = None,
) -> bool:
    """Make the `<label>` tab and start `cli` in it if it doesn't exist yet
    (reusing `initial` = (tab_id, pane_id), the tab a new workspace comes
    with, when given). Returns True only when this call actually created and
    started it — callers use that to do first-time-only setup (e.g. picking a
    model), never on a reopen of an already-running tab."""
    if _existing_tab_id(workspace_id, label):
        return False
    pane_id = _adopt_initial_tab(initial, label) if initial else None
    pane_id = pane_id or _create_tab(workspace_id, repo_root, label)
    if not pane_id:
        ui.warn(f"could not create tab '{label}'")
        return False
    cli_cfg = CLI_ARGS.get(cli, DEFAULT_CLI_ARGS)
    start_args = [
        "agent", "start", agent_name or label, "--kind", cli, "--pane", pane_id, "--",
    ] + cli_cfg["base"]
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


def _ensure_extra_tabs(workspace_id: str, repo_root: Path, tabs: list[dict]) -> None:
    """One tab per gea.json["tabs"] entry. `command` runs only when the tab
    is created here, so reopening the workspace never restarts a dev server."""
    for entry in tabs:
        label = entry["label"].strip()
        if _existing_tab_id(workspace_id, label):
            continue
        cwd = repo_root / entry.get("cwd", "")
        if not cwd.is_dir():
            ui.warn(f"tab '{label}': {cwd} does not exist — skipped")
            continue
        pane_id = _create_tab(workspace_id, cwd, label)
        if not pane_id:
            ui.warn(f"could not create tab '{label}'")
            continue
        if entry.get("command"):
            _result, err = herdr_json(["pane", "run", pane_id, entry["command"]])
            if err:
                ui.warn(f"tab '{label}': could not run its command ({err})")


def open_or_focus() -> int:
    repo_root = _find_repo_root()
    cfg = config.load_project(repo_root)
    primary = cfg.get("primary") or "claude"
    label = _safe_label(repo_root.name)

    workspace = _find_or_create_workspace(label, repo_root)
    if not workspace:
        ui.err("could not create or find the herdr workspace")
        return 1
    workspace_id = workspace.id
    initial = (
        (workspace.initial_tab_id, workspace.initial_pane_id)
        if workspace.initial_tab_id and workspace.initial_pane_id
        else None
    )

    agent_name = _agent_name(primary, label)
    created = _ensure_agent_tab(workspace_id, repo_root, primary, primary, initial, agent_name)
    _ensure_plain_tab(workspace_id, repo_root, "terminal")
    _ensure_extra_tabs(workspace_id, repo_root, cfg.get("tabs", []))

    if created and primary == "claude":
        model = cfg.get("primaryModel")
        if model:
            ui.ok(f"setting /model {model} in the claude tab")
            prompt_pane(agent_name, f"/model {model}", wait=False)

    if os.environ.get("HERDR_ENV") == "1":
        herdr_json(["workspace", "focus", workspace_id])
        return 0

    os.execvp("herdr", ["herdr"])
    return 0  # unreachable — execvp replaces this process on success
