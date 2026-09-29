"""`gea handoff [--to <cli>]` — switch orchestrator without losing the thread.

Writes `<task_root>/HANDOFF.md`: a resume prompt generated from what is
actually in flight (tasks in progress/review, git state, pending
checkpoints, exhausted pools). The conversation itself is never transferred
— tasks are the durable memory (see gea-plan), which is why this works
across CLIs. With `--to`, the new orchestrator is started in a herdr pane
and pointed at the file; `gea.json["primary"]` follows after confirmation.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from gea import config, platform, proc, ui
from gea.agents import herdr, log, state
from gea.tasks import store

ORCHESTRATORS = ("claude", "codex", "opencode", "agy", "kimi")
ACTIVE_STATUSES = ("in-progress", "review")
SECTION_LINES = 6

# Fixed text first: the variable state below it comes last (stable prefix).
ROLE = """# Handoff

You are taking over as this repo's **orchestrator**: you plan, delegate and
review; builders implement. Read `AGENTS.md` (and `.agents/orchestrator.md`
if it exists), then continue from the state below. Tools: `gea task`,
`gea delegate`, `gea review-pack`, `gea review`, `gea verify`, `gea undo`.
Do not redo finished work; the tasks are the source of truth."""


def _first_lines(text: str, n: int = SECTION_LINES) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(lines[:n])


def _section_text(task_text: str, heading: str) -> str:
    from gea.tasks.sections import section

    return _first_lines(section(task_text, heading))


def _git(root: Path, *args: str) -> str:
    out, _err, _code = proc.run(["git", "-C", str(root), *args])
    return out.strip()


def _task_block(task_id: str, root: Path) -> str:
    path = store.find_task_path(task_id, root)
    text = path.read_text(encoding="utf-8")
    title = re.match(r"# (.+)", text)
    last = log.last_for_task(task_id)
    attempt = (
        f"{last.get('agent_id')} -> {last.get('result')}, verify_ok={last.get('verify_ok')}"
        if last
        else "never delegated"
    )
    parts = [
        f"### {title.group(1) if title else task_id}",
        f"Status: {store.read_status(path)} · Tier: {store.read_header(path, 'Tier')} "
        f"· last delegation: {attempt}",
        f"File: {path}",
    ]
    for heading in ("Objective", "Implementation Notes", "Review"):
        body = _section_text(text, heading)
        if body:
            parts += [f"**{heading}**", body]
    return "\n".join(parts)


def build(root: Path) -> str:
    parts = [ROLE, "", f"## Project: {root.name}", ""]
    active = [
        task_id
        for status in ACTIVE_STATUSES
        for task_id, _s in store.list_tasks(status, root)
    ]
    parts.append("## In-flight tasks")
    parts += [""] + (["(none)"] if not active else [])
    for task_id in active:
        parts += [_task_block(task_id, root), ""]

    parts += ["## Git", "", f"Branch: {_git(root, 'rev-parse', '--abbrev-ref', 'HEAD')}"]
    parts += [f"Last commit: {_git(root, 'log', '-1', '--oneline')}", "```"]
    parts += [_git(root, "status", "--short") or "(clean)", "```", ""]

    refs = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/gea/checkpoint-heads")
    if refs:
        ids = [r.rsplit("/", 1)[-1] for r in refs.splitlines()]
        parts += ["## Pending checkpoints (`gea undo <ID>` restores)", "", ", ".join(ids), ""]
    exhausted = state.load()
    if exhausted:
        parts += ["## Exhausted pools", ""] + [f"- {p} until {u}" for p, u in exhausted.items()]
    return "\n".join(parts).rstrip("\n") + "\n"


def run_handoff(to: str | None = None, assume_yes: bool = False) -> int:
    root = Path.cwd()
    if to and to not in ORCHESTRATORS:
        ui.err(f"unknown orchestrator: {to} (use {', '.join(ORCHESTRATORS)})")
        return 1
    if to and not platform.which(to):
        ui.err(f"{to} is not installed")
        return 1

    target = store.task_root(root) / "HANDOFF.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build(root), encoding="utf-8")
    ui.ok(f"handoff written: {target}")
    resume = f"Read {target} and continue as orchestrator."
    if not to:
        print(f"Paste into the new orchestrator:\n  {resume}")
        return 0

    started = time.monotonic()
    status = herdr.start_agent_pane(f"orchestrator-{to}", to, None, root)
    print(status)
    if status.startswith("BLOCKED") or "FAILED" in status or "!=" in status:
        return 1
    herdr.prompt_pane(f"orchestrator-{to}", resume, wait=False)
    log.append(
        {
            "kind": "handoff",
            "project": root.name,
            "agent_id": to,
            "result": "handoff",
            "duration_s": round(time.monotonic() - started),
        }
    )
    cfg = config.load_project(root)
    if cfg.get("primary") != to and ui.ask_yes_no(
        f"Make {to} this project's primary agent in gea.json?", default=True, assume_yes=assume_yes
    ):
        cfg["primary"] = to
        config.save_project(root, cfg)
        ui.ok(f"primary = {to}")
    return 0
