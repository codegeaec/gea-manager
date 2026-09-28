"""Thin subprocess wrapper — the single seam tests mock instead of calling
into the real shell (AGENTS.md: tests never touch the real machine)."""

from __future__ import annotations

import subprocess


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
