"""Thin subprocess wrapper — the single seam tests mock instead of calling
into the real shell (AGENTS.md: tests never touch the real machine)."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path

from gea import dryrun


def run(cmd: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run `cmd`, returning (stdout, stderr, returncode).

    On failure to even start (missing binary, timeout), returns
    ("", "", 1) so callers don't need a try/except at every call site.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.stdout, proc.stderr, proc.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", "", 1


def run_ok(cmd: list[str], timeout: int = 30) -> bool:
    _out, _err, code = run(cmd, timeout=timeout)
    return code == 0


def run_visible(cmd: list[str], timeout: int | None = None) -> int:
    """Run `cmd` inheriting stdout/stderr/stdin instead of capturing them.

    For slow or possibly-interactive installers (curl|sh scripts, npm
    installs, `rtk init`, `codegraph install`, `npx skills add`):
    capturing their output hides progress bars and, worse, hides an
    interactive prompt entirely — the terminal looks hung even though the
    child process is just waiting on stdin. This lets the user see (and
    answer) whatever the child prints.
    """
    if dryrun.active():
        dryrun.report(f"run: {' '.join(cmd)}")
        return 0
    try:
        completed = subprocess.run(cmd, timeout=timeout, check=False)
        return completed.returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def _kill_group(process: subprocess.Popen, grace: float = 2.0) -> None:
    """Terminate `process` and everything it started (its whole process group)."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        return
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.wait()


def run_streaming(
    cmd: list[str],
    timeout: int = 300,
    on_tick: Callable[[int], None] | None = None,
    tick_every: float = 5.0,
    cwd: Path | None = None,
) -> tuple[str, str, int]:
    """Like `run`, but for long commands (verify, installs).

    - `on_tick(elapsed_seconds)` is called every `tick_every` seconds while it runs,
      so callers can show a heartbeat instead of minutes of silence;
    - the command runs in its own process group, and on timeout, Ctrl-C or SIGTERM
      the *whole group* is killed — `subprocess.run` only kills the direct child,
      leaving grandchildren (pnpm -> tsc/eslint) running as orphans;
    - a timeout returns code 124 (with a note on stderr), a missing binary 127.
    """
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True, cwd=cwd,
        )
    except OSError as exc:
        return "", str(exc), 127
    elapsed = 0.0
    try:
        while True:
            try:
                out, err = process.communicate(timeout=tick_every)
                return out, err, process.returncode
            except subprocess.TimeoutExpired:
                elapsed += tick_every
                if elapsed >= timeout:
                    _kill_group(process)
                    return "", f"timed out after {timeout}s", 124
                if on_tick:
                    on_tick(int(elapsed))
    except BaseException:  # KeyboardInterrupt, SystemExit from a SIGTERM handler, ...
        _kill_group(process)
        raise
