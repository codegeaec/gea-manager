"""`gea verify` — run this project's configured verify commands
(`gea.json["verify"]`), one at a time, reporting pass/fail.

`gea verify --task <ID>` additionally runs the executable acceptance
criteria of that task: every backticked command on a bullet under its
`## Acceptance` heading (see tasks/acceptance.py) goes through the very
same runner.
"""

from __future__ import annotations

from pathlib import Path

from gea import config, proc, ui
from gea.i18n import t


def execute(command: str) -> tuple[bool, str]:
    """Run one command through bash. Returns (passed, last 20 output lines)."""
    out, err, code = proc.run(["bash", "-c", command], timeout=300)
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


def run_commands(commands: list[str], quiet: bool = False) -> list[str]:
    """Run each command through bash, printing pass/fail (only failures when
    `quiet`). Returns the failed ones."""
    failed = []
    for command in commands:
        passed, tail = execute(command)
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
    repo_root: Path | None = None, task_id: str | None = None, quiet: bool = False
) -> int:
    repo_root = repo_root or Path.cwd()
    commands = commands_for(repo_root, task_id)
    if commands is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1

    if not commands:
        ui.warn(t("verify.none"))
        return 1

    failed = run_commands(commands, quiet=quiet)
    if failed:
        ui.warn(t("verify.failed", count=len(failed)))
        return 1
    ui.ok(t("verify.passed", count=len(commands)))
    return 0
