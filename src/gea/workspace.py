"""`gea` with no arguments: open (or focus) this project's herdr workspace.

Tabs, idempotent by label (ported from the old herdr-setup gist's
`herdr-repo`, minus the llama.cpp/WSL-specific opencode-roles logic):

- `<planner>` — the project's planner agent (`agents.planner`, "claude" if
  unset, started with `agents.plannerModel` when the CLI has a model flag), an
  interactive CLI tab. On a brand-new workspace it
  reuses the tab herdr creates with the workspace, so no stray "1" is left.
  With `gea --only` (workflow "only", claude) it starts with a system prompt
  that turns off the task/delegation flow.
- `terminal` — a plain shell, for anything else the user wants to run by hand.
- `git` — lazygit, when it's installed (started when the tab is created, and
  again on a later `gea` if the tab is back at an empty shell prompt).
- one tab per entry of gea.json["tabs"] (`label`, `cwd` relative to the repo,
  optional `command` run only when the tab is created), e.g. for monorepos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gea import config, platform, proc, ui
from gea.agents.herdr import (
    CLI_ARGS,
    DEFAULT_CLI_ARGS,
    agent_name,
    free_agent_name,
    herdr_json,
    project_prefix,
    prompt_pane,
)
from gea.agents.herdr import safe_label as _safe_label

ONLY_FLAG = "--append-system-prompt"


def _find_repo_root(start: Path | None = None) -> Path:
    start = start or Path.cwd()
    out, _err, code = proc.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"])
    if code == 0 and out.strip():
        return Path(out.strip())
    return start


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


def _find_tab(workspace_id: str, label: str) -> dict | None:
    listing, err = herdr_json(["tab", "list", "--workspace", workspace_id])
    if err:
        return None
    for tab in listing.get("tabs", []):
        if tab.get("label") == label:
            return tab
    return None


def _existing_tab_id(workspace_id: str, label: str) -> str | None:
    return (_find_tab(workspace_id, label) or {}).get("tab_id")


def _tab_process(workspace_id: str, tab_id: str | None) -> tuple[str | None, dict]:
    """(pane_id, process_info) of the tab's first pane; (None, {}) if unknown."""
    if not tab_id:
        return None, {}
    listing, err = herdr_json(["pane", "list", "--workspace", workspace_id])
    if err:
        return None, {}
    pane_id = next(
        (p.get("pane_id") for p in listing.get("panes", []) if p.get("tab_id") == tab_id), None
    )
    if not pane_id:
        return None, {}
    info, err = herdr_json(["pane", "process-info", "--pane", pane_id])
    return pane_id, ({} if err else info.get("process_info", {}))


def _is_idle_shell(info: dict) -> bool:
    """True when the pane's own shell is in the foreground: nothing is running."""
    group = info.get("foreground_process_group_id")
    return group is not None and group == info.get("shell_pid")


def _has_arg(info: dict, flag: str) -> bool:
    procs = info.get("foreground_processes", [])
    return any(flag in p.get("argv", []) for p in procs)


def _create_tab(workspace_id: str, repo_root: Path, label: str) -> str | None:
    cmd = [
        "tab", "create", "--workspace", workspace_id,
        "--cwd", str(repo_root), "--label", label, "--no-focus",
    ]
    result, err = herdr_json(cmd)
    if err:
        return None
    return result.get("root_pane", {}).get("pane_id")


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
    model: str | None = None,
    extra_args: list[str] | None = None,
) -> bool:
    """Make the `<label>` tab and start `cli` in it if it doesn't exist yet
    (reusing `initial` = (tab_id, pane_id), the tab a new workspace comes
    with, when given). An existing tab whose pane is back at an empty shell
    (the agent died) gets the agent started again. Returns True only when this
    call actually started it — callers use that to do first-time-only setup
    (e.g. picking a model), never on a reopen of an already-running tab."""
    tab = _find_tab(workspace_id, label)
    if tab:
        pane_id, info = _tab_process(workspace_id, tab.get("tab_id"))
        if not pane_id or not _is_idle_shell(info):
            if pane_id and cli == "claude" and _has_arg(info, ONLY_FLAG) != bool(extra_args):
                ui.warn(f"'{label}' runs in the other mode — /exit it and run gea again")
            return False
        ui.ok(f"'{label}' was not running — starting it again")
    else:
        pane_id = _adopt_initial_tab(initial, label) if initial else None
        pane_id = pane_id or _create_tab(workspace_id, repo_root, label)
        if not pane_id:
            ui.warn(f"could not create tab '{label}'")
            return False
    cli_cfg = CLI_ARGS.get(cli, DEFAULT_CLI_ARGS)
    start_args = [
        "agent", "start", agent_name or label, "--kind", cli, "--pane", pane_id, "--",
    ] + cli_cfg["base"] + (extra_args or [])
    if model:  # claude has no start flag: its model goes in through /model afterwards
        start_args += [flag.format(model=model) for flag in cli_cfg["model"]]
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


def _ensure_git_tab(workspace_id: str, repo_root: Path) -> None:
    lazygit = platform.which("lazygit")
    if not lazygit:
        ui.warn("lazygit not found — skipping the 'git' tab (run `gea update` to install it)")
        return
    tab = _find_tab(workspace_id, "git")
    if tab:  # relaunch only if lazygit died and left the pane at its shell
        pane_id, info = _tab_process(workspace_id, tab.get("tab_id"))
        if not pane_id or not _is_idle_shell(info):
            return
        ui.ok("lazygit was not running — starting it again")
    else:
        pane_id = _create_tab(workspace_id, repo_root, "git")
        if not pane_id:
            ui.warn("could not create tab 'git'")
            return
    _result, err = herdr_json(["pane", "run", pane_id, lazygit])
    if err:
        ui.warn(f"tab 'git': could not start lazygit ({err})")


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


def _only_args(cfg: dict, primary: str) -> list[str]:
    """Claude's start args for workflow "only": a system prompt (it outranks
    CLAUDE.md) that switches off the orchestrator/task flow, nothing written
    to the repo. Other CLIs have no equivalent flag, so they run as usual."""
    if cfg.get("workflow") != "only":
        return []
    if primary != "claude":
        ui.warn(f"--only needs claude as the planner (it is '{primary}') — running as usual")
        return []
    from gea.init.scaffold import read_template

    return [ONLY_FLAG, read_template(config.agents_lang(cfg), "agents/only.md").strip()]


def open_or_focus(workflow: str | None = None) -> int:
    repo_root = _find_repo_root()
    if workflow:
        config.set_workflow(repo_root, workflow)
    cfg = config.load_project(repo_root)
    planner = config.agents(cfg)
    primary = planner.planner
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

    name = free_agent_name(agent_name(project_prefix(repo_root), primary), workspace_id)
    created = _ensure_agent_tab(
        workspace_id, repo_root, primary, primary, initial, name, planner.planner_model,
        _only_args(cfg, primary),
    )
    _ensure_plain_tab(workspace_id, repo_root, "terminal")
    _ensure_git_tab(workspace_id, repo_root)
    _ensure_extra_tabs(workspace_id, repo_root, cfg.get("tabs", []))

    if created and primary == "claude":
        model = planner.planner_model
        if model:
            ui.ok(f"setting /model {model} in the claude tab")
            prompt_pane(name, f"/model {model}", wait=False)

    if os.environ.get("HERDR_ENV") == "1":
        herdr_json(["workspace", "focus", workspace_id])
        return 0

    os.execvp("herdr", ["herdr"])
    return 0  # unreachable — execvp replaces this process on success
