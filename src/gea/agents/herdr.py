"""Thin JSON wrapper over the `herdr` CLI, plus the builder-pane start
logic (reuse an existing pane, or split a sibling pane in the current tab).

Ported from Cotizaciones' scripts/agents.py `cmd_start`, generalized to not
assume a fixed repo root.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from gea import proc

SPLIT_WIDE_RATIO = 2.0

CLI_ARGS: dict[str, dict[str, list[str]]] = {
    "opencode": {"base": ["--agent", "builder"], "model": ["--model", "{model}"]},
    "codex": {"base": [], "model": ["-m", "{model}"]},
    "agy": {"base": ["--dangerously-skip-permissions"], "model": ["--model", "{model}"]},
    "claude": {"base": [], "model": []},
    "kimi": {"base": [], "model": ["--model", "{model}"]},
}
DEFAULT_CLI_ARGS: dict[str, list[str]] = {"base": [], "model": []}

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


def start_builder_pane(agent_id: str, cli: str, model: str | None, cwd: Path) -> str:
    """Start (or reuse) the `builder-<agent_id>` pane. Returns a short
    human-readable status line, same convention as `gea agents start`."""
    return start_agent_pane(f"builder-{agent_id}", cli, model, cwd)


def start_agent_pane(pane_name: str, cli: str, model: str | None, cwd: Path) -> str:
    """Start (or reuse) a pane named `pane_name` running `cli`."""
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

    start_args = [
        "agent", "start", pane_name, "--kind", cli, "--pane", pane_id,
        "--timeout", "60000", "--",
    ]
    cli_cfg = CLI_ARGS.get(cli, DEFAULT_CLI_ARGS)
    start_args += cli_cfg["base"]
    if model:
        start_args += [flag.format(model=model) for flag in cli_cfg["model"]]
    result, err = herdr_json(start_args, timeout=65)
    if err == "agent_not_ready":
        return f"BLOCKED {pane_name} — started but is waiting on a confirmation dialog"
    outcome = "started" if result else f"FAILED ({err or ''})"
    model_suffix = f" {model}" if model else ""
    return f"{outcome} {pane_name} ({cli}{model_suffix})"


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
