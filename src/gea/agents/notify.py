"""Tell the orchestrator when a builder is done, without it polling.

`gea delegate` blocks until the builder settles, but herdr's idle/working state
is unreliable and the orchestrator often runs delegate in the background or in a
terminal that gets closed. So each run also spawns a detached watcher that waits
for the *reliable* signals — the task's `Status:` turning `review`/`blocked`/
`error` (in the main checkout or in the builder's worktree), or the builder's
pane dying (SIGILL, kill -4, ...) — and sends ONE prompt to the orchestrator's
pane: `herdr agent prompt <pane> "TASK-X terminó (review). Corré gea review-pack TASK-X"`.

State lives in `<gea home>/watchers/<project>-<task>.json` (the watcher's pid).
That file is also the idempotency token: the watcher exits as soon as it is gone
or no longer holds its own pid, so `stop()` (gea undo / gea task done) or a newer
delegate of the same task cancels it, and a notice is never sent twice.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from gea import paths
from gea.agents import herdr
from gea.i18n import t
from gea.tasks import store

POLL_S = 5
DEAD_READS = 3  # consecutive polls without a live agent before calling it crashed
SEND_TRIES = 6  # the orchestrator may be mid-dialog (agent_blocked): retry a while
SEND_WAIT_S = 10
MARGIN_S = 300  # watcher outlives the builder budget a little
DONE_STATUSES = {"review": "review", "blocked": "blocked", "error": "error"}


def _state_path(project: str, task_id: str) -> Path:
    return paths.gea_home() / "watchers" / f"{project}-{task_id}.json"


def _read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _is_watcher(pid: int) -> bool:
    """The pid is alive and really one of our watchers (pids get reused)."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return b"gea.agents.notify" in cmdline


def stop(project: str, task_id: str) -> bool:
    """Cancel the task's watcher, if any. Safe to call when there is none."""
    path = _state_path(project, task_id)
    pid = _read_state(path).get("pid")
    path.unlink(missing_ok=True)
    if isinstance(pid, int) and _is_watcher(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return False
        return True
    return False


def start(
    task_id: str,
    task_path: Path,
    root: Path,
    pane_name: str,
    wt_path: Path | None,
    budget_s: int,
) -> bool:
    """Spawn the detached watcher for this run. False when there is no
    orchestrator pane to notify (not inside herdr)."""
    target = os.environ.get("HERDR_PANE_ID")
    if os.environ.get("HERDR_ENV") != "1" or not target:
        return False
    stop(root.name, task_id)  # a re-delegation replaces the previous run's watcher
    spec = {
        "project": root.name,
        "task_id": task_id,
        "task_paths": _task_paths(task_path, root, wt_path),
        "pane": pane_name,
        "target": target,
        "deadline": time.time() + budget_s + MARGIN_S,
    }
    try:
        child = subprocess.Popen(
            [sys.executable, "-m", "gea.agents.notify", json.dumps(spec)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # survives the terminal that ran delegate
            close_fds=True,
        )
    except OSError:
        return False
    path = _state_path(root.name, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": child.pid, **spec}), encoding="utf-8")
    return True


def _task_paths(task_path: Path, root: Path, wt_path: Path | None) -> list[str]:
    """Where the builder may write the status: the task file itself and, for a
    task kept inside the repo, its copy in the worktree."""
    found = [str(task_path)]
    if wt_path:
        try:
            found.append(str(wt_path / task_path.relative_to(root)))
        except ValueError:
            pass
    return found


def _statuses(task_paths: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for p in task_paths:
        path = Path(p)
        out[p] = store.read_status(path) if path.is_file() else None
    return out


def _outcome(task_paths: list[str], initial: dict[str, str | None]) -> str | None:
    """`review`/`blocked`/`error` once a task file *changed* to it (so a task
    already in review when re-delegated does not fire at once)."""
    for p, status in _statuses(task_paths).items():
        if status in DONE_STATUSES and status != initial.get(p):
            return DONE_STATUSES[status]
    return None


def _message(task_id: str, outcome: str) -> str:
    return t("notify.message", task_id=task_id, outcome=outcome)


def _send(target: str, message: str) -> bool:
    for attempt in range(SEND_TRIES):
        _out, code, _error = herdr.prompt_result(target, message, wait=False)
        if code == 0:
            return True
        if attempt + 1 < SEND_TRIES:
            time.sleep(SEND_WAIT_S)
    return False


def watch(spec: dict, poll_s: float = POLL_S) -> str | None:
    """Block until the run ends, notify once, return the outcome sent (None when
    cancelled, closed or timed out without a signal)."""
    state_path = _state_path(spec["project"], spec["task_id"])
    task_paths = spec["task_paths"]
    initial = _statuses(task_paths)
    dead = 0
    while time.time() < spec["deadline"]:
        time.sleep(poll_s)
        if _read_state(state_path).get("pid") != os.getpid():
            return None  # cancelled (undo / task done) or superseded
        outcome = _outcome(task_paths, initial)
        if outcome is None:
            if not any(Path(p).is_file() for p in task_paths):
                return None  # task closed (moved to done/)
            dead = 0 if herdr.agent_alive(spec["pane"]) else dead + 1
            if dead >= DEAD_READS:
                outcome = "crashed"
        if outcome:
            state_path.unlink(missing_ok=True)  # one notice per run, whatever happens next
            _send(spec["target"], _message(spec["task_id"], outcome))
            return outcome
    state_path.unlink(missing_ok=True)
    return None


if __name__ == "__main__":
    watch(json.loads(sys.argv[1]), float(os.environ.get("GEA_WATCH_POLL", POLL_S)))
