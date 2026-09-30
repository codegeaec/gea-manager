"""Thin JSON wrapper over the `herdr` CLI, plus the builder-pane start
logic (reuse an existing pane, or split a sibling pane in the current tab).

Ported from Cotizaciones' scripts/agents.py `cmd_start`, generalized to not
assume a fixed repo root.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from gea import proc

SPLIT_WIDE_RATIO = 2.0

CLI_ARGS: dict[str, dict[str, list[str]]] = {
    "opencode": {"base": ["--agent", "builder"], "model": ["--model", "{model}"]},
    "codex": {"base": [], "model": ["-m", "{model}"]},
    "agy": {"base": [], "model": ["--model", "{model}"]},
    "claude": {"base": [], "model": []},
    "kimi": {"base": [], "model": ["--model", "{model}"]},
}
DEFAULT_CLI_ARGS: dict[str, list[str]] = {"base": [], "model": []}

# Flags that stop a *builder* from stalling on permission dialogs (herdr cannot
# answer them by script, so an unanswered one leaves the run BLOCKED). Never
# applied to the orchestrator's own tab. `builders.permissions` in gea.json:
# - safe: as unattended as each CLI allows while staying sandboxed/limited
# - yolo: no permission checks at all — gea only allows it inside a worktree
# Flags checked against each CLI's `--help`; kimi's are unknown, so it gets none.
PERMISSION_ARGS: dict[str, dict[str, list[str]]] = {
    "claude": {
        "safe": ["--permission-mode", "acceptEdits"],
        "yolo": ["--dangerously-skip-permissions"],
    },
    "codex": {
        "safe": ["--sandbox", "workspace-write", "--ask-for-approval", "never"],
        "yolo": ["--dangerously-bypass-approvals-and-sandbox"],
    },
    "opencode": {"safe": [], "yolo": ["--auto"]},  # safe: opencode.jsonc rules apply
    "agy": {"safe": ["--mode", "accept-edits"], "yolo": ["--dangerously-skip-permissions"]},
}


def permission_args(cli: str, mode: str) -> list[str]:
    return list(PERMISSION_ARGS.get(cli, {}).get(mode, []))

INTEGRATION_TARGETS: dict[str, str] = {
    "opencode": "opencode",
    "codex": "codex",
    "agy": "antigravity-cli",
}


def herdr_json(cmd: list[str], timeout: int = 15) -> tuple[dict[str, Any], str | None]:
    """Run a herdr subcommand, returning (result, error_code).

    herdr prints JSON on stdout on success ({"result": {...}}) and on
    stderr on error ({"error": {"code": ...}}) with a non-zero exit code.
    error_code is None on success, even if result comes back empty.
    """
    stdout, stderr, code = proc.run(["herdr", *cmd], timeout=timeout)
    if code == 0:
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            return {}, None
        return parsed.get("result", {}) or {}, None
    try:
        parsed = json.loads(stderr) if stderr else {}
    except json.JSONDecodeError:
        return {}, "unknown_error"
    return {}, (parsed.get("error", {}) or {}).get("code", "unknown_error")


def safe_label(name: str) -> str:
    """Lowercase slug of a folder/project name (`[a-z0-9_-]`, never empty)."""
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-")
    return slug or "repo"


def project_prefix(repo_root: Path) -> str:
    """First 3 letters/digits of the project folder, e.g. `cotizaciones` -> `cot`.
    Always starts with a letter, as herdr agent names require."""
    prefix = re.sub(r"[^a-z0-9]", "", safe_label(repo_root.name))[:3]
    if not prefix or prefix[0].isdigit():
        prefix = ("p" + prefix)[:3]
    return prefix


def agent_name(prefix: str, *parts: str) -> str:
    """`cot-claude`, `cot-builder-oc-kimi`: herdr allows `[a-z][a-z0-9_-]{0,31}`."""
    return "-".join([prefix, *parts])[:32].rstrip("-_")


def free_agent_name(base: str, workspace_id: str | None) -> str:
    """`base`, or `base-2`, `base-3`... when a live agent of *another* workspace
    already has it (herdr agent names are unique among all live agents). An
    agent in our own workspace counts as ours, so its pane is reused."""
    if os.environ.get("HERDR_ENV") != "1":
        return base
    for n in range(1, 10):
        name = base if n == 1 else f"{base[:30]}-{n}"
        info, _err = herdr_json(["agent", "get", name])
        found = info.get("agent") or {}
        if not found or found.get("workspace_id") == workspace_id:
            return name
    return base


def pane_name_for(repo_root: Path, *parts: str) -> str:
    """The name gea gives a pane/agent of this project: `<prefix>-<parts...>`."""
    base = agent_name(project_prefix(repo_root), *parts)
    return free_agent_name(base, os.environ.get("HERDR_WORKSPACE_ID"))


def start_builder_pane(
    agent_id: str, cli: str, model: str | None, cwd: Path, permissions: str = "safe"
) -> str:
    """Start (or reuse) this project's `<prefix>-builder-<agent_id>` pane. Returns
    a short human-readable status line, same convention as `gea agents start`."""
    return start_agent_pane(
        pane_name_for(cwd, "builder", agent_id), cli, model, cwd, permission_args(cli, permissions)
    )


def start_agent_pane(
    pane_name: str,
    cli: str,
    model: str | None,
    cwd: Path,
    extra_args: list[str] | None = None,
) -> str:
    """Start (or reuse) a pane named `pane_name` running `cli` (`extra_args`:
    e.g. the builder permission flags)."""
    if os.environ.get("HERDR_ENV") != "1":
        return "HERDR_ENV != 1 — this must run inside a herdr pane"
    caller_pane = os.environ.get("HERDR_PANE_ID")
    workspace_id = os.environ.get("HERDR_WORKSPACE_ID")
    if not caller_pane or not workspace_id:
        return "missing HERDR_PANE_ID/HERDR_WORKSPACE_ID in the environment"

    existing, _err = herdr_json(["agent", "get", pane_name])
    if existing:
        return f"pane {pane_name} already exists, reusing it"

    agents_result, err = herdr_json(["agent", "list"])
    if err:
        return f"could not list herdr agents ({err})"
    agents_list = agents_result.get("agents", [])

    unnamed = next(
        (
            a
            for a in agents_list
            if a.get("agent") == cli
            and not a.get("name")
            and a.get("agent_status") == "idle"
            and a.get("cwd") == str(cwd)
            and a.get("workspace_id") == workspace_id
        ),
        None,
    )
    if unnamed:
        pane_id = unnamed["pane_id"]
        _renamed, err = herdr_json(["agent", "rename", pane_id, pane_name])
        return f"{'reused' if err is None else 'FAILED (' + err + ')'} existing pane as {pane_name}"

    layout, err = herdr_json(["pane", "layout", "--pane", caller_pane])
    rect = next(
        (
            p["rect"]
            for p in layout.get("layout", {}).get("panes", [])
            if p.get("pane_id") == caller_pane
        ),
        None,
    )
    direction = "right" if rect and rect["width"] >= rect["height"] * SPLIT_WIDE_RATIO else "down"

    split_cmd = [
        "pane", "split", "--pane", caller_pane, "--direction", direction,
        "--cwd", str(cwd), "--no-focus",
    ]
    split, err = herdr_json(split_cmd)
    pane_id = split.get("pane", {}).get("pane_id")
    if not pane_id:
        return f"could not create pane for {pane_name} ({err})"

    args = cli_cfg_args(cli, model, extra_args)
    state, info = _run_start(pane_name, cli, pane_id, args)
    if state == "dead" and _needs_no_daemon(cli, info, args):
        state, info = _run_start(pane_name, cli, pane_id, args + [CODEX_NO_DAEMON])
    if state == "blocked":
        return f"BLOCKED {pane_name} — started but is waiting on a confirmation dialog"
    if state == "dead":
        herdr_json(["pane", "close", pane_id])  # nothing useful is left in it
        return f"FAILED ({cli} did not start; last output of its pane:\n{info.strip()})"
    if state == "failed":
        return f"FAILED ({info})"
    model_suffix = f" {model}" if model else ""
    return f"started {pane_name} ({cli}{model_suffix})"


CODEX_NO_DAEMON = "--no-daemon"
CODEX_DAEMON_ERROR = "shared background server"
STARTUP_WAIT_S = 10


def cli_cfg_args(cli: str, model: str | None, extra_args: list[str] | None) -> list[str]:
    cli_cfg = CLI_ARGS.get(cli, DEFAULT_CLI_ARGS)
    args = cli_cfg["base"] + list(extra_args or [])
    if model:
        args += [flag.format(model=model) for flag in cli_cfg["model"]]
    return args


def _needs_no_daemon(cli: str, tail: str, args: list[str]) -> bool:
    """Codex's shared app-server can be stuck and reject new clients; its own
    advice is to rerun with --no-daemon, which isolates this builder."""
    return cli == "codex" and CODEX_DAEMON_ERROR in tail and CODEX_NO_DAEMON not in args


def _agent_up(pane_name: str) -> bool:
    """herdr sees a live agent (non-empty kind, status other than unknown)."""
    deadline = time.monotonic() + STARTUP_WAIT_S
    while True:
        info, _err = herdr_json(["agent", "get", pane_name])
        agent = info.get("agent") or {}
        if agent.get("agent") and agent.get("agent_status") != "unknown":
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(1)


def read_pane_id(pane_id: str, lines: int = 15) -> str:
    out, _err, _code = proc.run(["herdr", "pane", "read", pane_id, "--lines", str(lines)])
    return out


def _run_start(pane_name: str, cli: str, pane_id: str, args: list[str]) -> tuple[str, str]:
    """`agent start` in `pane_id`, then check the agent really came up. State:
    ok | blocked | failed (info = herdr error) | dead (info = the pane's last lines)."""
    cmd = ["agent", "start", pane_name, "--kind", cli, "--pane", pane_id,
           "--timeout", "60000", "--", *args]
    result, err = herdr_json(cmd, timeout=65)
    if err == "agent_not_ready":
        return "blocked", ""
    if not result:
        return "failed", err or ""
    if _agent_up(pane_name):
        return "ok", ""
    return "dead", read_pane_id(pane_id)


def missing_integrations(clis: set[str]) -> list[str]:
    status_out, _err, _code = proc.run(["herdr", "integration", "status"])
    missing = []
    for cli in clis:
        target = INTEGRATION_TARGETS.get(cli)
        if not target:
            continue
        line = next((ln for ln in status_out.splitlines() if ln.startswith(f"{target}:")), None)
        if line and "not installed" in line:
            missing.append(target)
    return missing


def read_pane(pane_name: str, lines: int = 40) -> str:
    if os.environ.get("HERDR_ENV") != "1":
        return ""  # no herdr session, no pane to read
    cmd = [
        "herdr", "agent", "read", pane_name,
        "--source", "recent-unwrapped", "--lines", str(lines),
    ]
    out, _err, _code = proc.run(cmd)
    return out


def prompt_pane(
    pane_name: str, message: str, wait: bool = True, budget_s: int = 1800
) -> tuple[str, int]:
    """Send `message` to the pane. With `wait`, herdr itself enforces
    `budget_s` (--timeout, ms) so a long build is cut cleanly by herdr
    instead of gea's subprocess timeout killing the wait mid-flight."""
    out, code, _error = prompt_result(pane_name, message, wait, budget_s)
    return out, code


def prompt_result(
    pane_name: str, message: str, wait: bool = True, budget_s: int = 1800
) -> tuple[str, int, str | None]:
    """Like `prompt_pane`, plus herdr's error code (`timeout`, `agent_blocked`,
    `agent_prompt_stalled`, ...) parsed from its stderr JSON, or None."""
    cmd = ["herdr", "agent", "prompt", pane_name, message]
    if wait:
        cmd += ["--wait", "--timeout", str(budget_s * 1000)]
    out, err, code = proc.run(cmd, timeout=budget_s + 30)
    error = None
    if code != 0:
        try:
            error = (json.loads(err).get("error") or {}).get("code", "unknown_error")
        except (json.JSONDecodeError, AttributeError):
            error = "unknown_error"
    return out, code, error


def notify(title: str, body: str = "", sound: str = "done") -> bool:
    """Show a herdr notification (best effort — never raises or blocks)."""
    cmd = ["herdr", "notification", "show", title, "--sound", sound]
    if body:
        cmd += ["--body", body]
    _out, _err, code = proc.run(cmd, timeout=10)
    return code == 0


# Slash command that starts a fresh conversation, per CLI. Only CLIs whose
# command is known are listed; the rest keep their session.
CLEAR_COMMANDS = {"claude": "/clear", "codex": "/new", "opencode": "/new"}


def clear_session(pane_name: str, cli: str) -> bool:
    """Start a fresh conversation in the pane. False if the CLI has no known command."""
    command = CLEAR_COMMANDS.get(cli)
    if not command:
        return False
    _out, code, _error = prompt_result(pane_name, command, wait=False)
    time.sleep(1)  # let the command land before the real prompt is sent
    return code == 0


def close_agent_pane(name: str) -> bool:
    """Close the pane hosting agent `name`. Never the caller's own pane."""
    if os.environ.get("HERDR_ENV") != "1":
        return False
    info, _err = herdr_json(["agent", "get", name])
    pane_id = (info.get("agent") or {}).get("pane_id")
    if not pane_id or pane_id == os.environ.get("HERDR_PANE_ID"):
        return False
    _result, err = herdr_json(["pane", "close", pane_id])
    return err is None


def created_by_gea(status: str) -> bool:
    """Did `start_agent_pane` make (or find) a pane gea owns, as opposed to
    adopting a pane the user opened themselves ('reused existing pane as ...')?"""
    return status.startswith("started") or "already exists" in status
