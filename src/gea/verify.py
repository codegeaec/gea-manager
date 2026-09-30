"""`gea verify` — run this project's configured verify commands
(`gea.json["verify"]`), one at a time, reporting pass/fail.

`gea verify --task <ID>` additionally runs the executable acceptance
criteria of that task: every backticked command on a bullet under its
`## Acceptance` heading (see tasks/acceptance.py) goes through the very
same runner.

Built for unattended callers (builder agents): it prints `→ command` when a
command starts and a heartbeat every few seconds while it runs (silence looks
like a hang and gets the command killed with exit 130), kills the whole process
tree if interrupted, and only one verify runs per repo at a time.
"""

from __future__ import annotations

import fcntl
import json
import os
import shlex
import signal
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from gea import config, proc, ui
from gea.i18n import t

HEARTBEAT_SECONDS = 5


class Interrupted(Exception):
    """The run was interrupted (Ctrl-C / SIGTERM) while `command` was running."""

    def __init__(self, command: str, seconds: int, typical: int | None):
        super().__init__(command)
        self.command, self.seconds, self.typical = command, seconds, typical


def _state_dir(repo_root: Path) -> Path | None:
    out, _err, code = proc.run(["git", "-C", str(repo_root), "rev-parse", "--absolute-git-dir"])
    if code != 0 or not out.strip():
        return None
    directory = Path(out.strip()) / "gea"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _durations(state_dir: Path | None) -> dict[str, int]:
    if state_dir is None:
        return {}
    try:
        return json.loads((state_dir / "verify-durations.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _remember(state_dir: Path | None, command: str, seconds: int) -> None:
    if state_dir is None:
        return
    durations = _durations(state_dir)
    durations[command] = seconds
    (state_dir / "verify-durations.json").write_text(json.dumps(durations), encoding="utf-8")


@contextmanager
def _one_at_a_time(state_dir: Path | None, progress: bool) -> Iterator[None]:
    """Serialize verify runs of one repo (an agent's retry, the orchestrator's own
    run...). The flock is released by the OS if the holder dies."""
    if state_dir is None:
        yield
        return
    with (state_dir / "verify.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.seek(0)
            if progress:
                print(t("verify.waiting", pid=handle.read().strip() or "?"), file=sys.stderr)
            fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def execute(
    command: str,
    cwd: Path | None = None,
    timeout: int = 300,
    on_tick=None,
) -> tuple[bool, str]:
    """Run one command through bash (in `cwd` if given). Returns (passed, last 20 lines).

    The whole process tree is killed on timeout or interruption."""
    script = f"cd {shlex.quote(str(cwd))} && {command}" if cwd else command
    out, err, code = proc.run_streaming(
        ["bash", "-c", script], timeout=timeout, on_tick=on_tick, tick_every=HEARTBEAT_SECONDS
    )
    return code == 0, "\n".join((out + err).strip().splitlines()[-20:])


def commands_for(repo_root: Path, task_id: str | None = None) -> list[str] | None:
    """Project verify commands plus the task's acceptance commands. None if
    `task_id` is unknown."""
    commands: list[str] = list(config.load_project(repo_root).get("verify", []))
    if task_id:
        from gea.tasks import acceptance

        criteria = acceptance.for_task(task_id, repo_root)
        if criteria is None:
            return None
        commands += [c for c in criteria if c not in commands]
    return commands


def run_commands(
    commands: list[str],
    quiet: bool = False,
    cwd: Path | None = None,
    progress: bool = True,
    state_dir: Path | None = None,
) -> list[str]:
    """Run each command through bash, printing pass/fail (only failures when
    `quiet`). With `progress`, also `→ command` at start and a heartbeat on stderr.
    Returns the failed ones; raises `Interrupted` if the run is cut short."""
    failed = []
    typical = _durations(state_dir)
    for command in commands:
        if progress:
            hint = t("verify.last_time", seconds=typical[command]) if command in typical else ""
            print(f"→ {command}{hint}", file=sys.stderr, flush=True)
        started = time.monotonic()

        def tick(elapsed: int, command: str = command) -> None:
            if progress:
                print(f"… {command} ({elapsed}s)", file=sys.stderr, flush=True)

        try:
            passed, tail = execute(command, cwd, on_tick=tick)
        except KeyboardInterrupt:
            raise Interrupted(
                command, round(time.monotonic() - started), typical.get(command)
            ) from None
        _remember(state_dir, command, round(time.monotonic() - started))
        if passed:
            if not quiet:
                ui.ok(command)
        else:
            ui.err(command)
            for line in tail.splitlines():
                print(f"    {line}")
            failed.append(command)
    return failed


def run_verify(
    repo_root: Path | None = None,
    task_id: str | None = None,
    quiet: bool = False,
    cwd: Path | None = None,
    progress: bool = True,
) -> int:
    repo_root = repo_root or Path.cwd()
    commands = commands_for(repo_root, task_id)
    if commands is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1

    if not commands:
        ui.warn(t("verify.none"))
        return 1

    def on_sigterm(signum, frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, on_sigterm)
    state_dir = _state_dir(repo_root)
    try:
        with _one_at_a_time(state_dir, progress):
            failed = run_commands(
                commands, quiet=quiet, cwd=cwd, progress=progress, state_dir=state_dir
            )
    except Interrupted as stop:
        typical = t("verify.typical", seconds=stop.typical) if stop.typical else ""
        ui.err(t("verify.interrupted", command=stop.command, seconds=stop.seconds, typical=typical))
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous)
    if failed:
        ui.warn(t("verify.failed", count=len(failed)))
        return 1
    ui.ok(t("verify.passed", count=len(commands)))
    return 0
