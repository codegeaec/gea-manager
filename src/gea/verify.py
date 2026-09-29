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


def run_commands(commands: list[str], quiet: bool = False) -> list[str]:
    """Run each command through bash, printing pass/fail (only failures when
    `quiet`). Returns the failed ones."""
    failed = []
    for command in commands:
        out, err, code = proc.run(["bash", "-c", command], timeout=300)
        if code == 0:
            if not quiet:
                ui.ok(command)
        else:
            ui.err(command)
            tail = (out + err).strip().splitlines()[-20:]
            for line in tail:
                print(f"    {line}")
            failed.append(command)
    return failed


def run_verify(
    repo_root: Path | None = None, task_id: str | None = None, quiet: bool = False
) -> int:
    repo_root = repo_root or Path.cwd()
    cfg = config.load_project(repo_root)
    commands: list[str] = list(cfg.get("verify", []))

    if task_id:
        from gea.tasks import acceptance

        criteria = acceptance.for_task(task_id, repo_root)
        if criteria is None:
            ui.err(f"task not found: {task_id}")
            return 1
        commands += [c for c in criteria if c not in commands]

    if not commands:
        ui.warn("no verify commands configured — run `gea init` or edit gea.json")
        return 1

    failed = run_commands(commands, quiet=quiet)
    if failed:
        ui.warn(f"{len(failed)} command(s) failed")
        return 1
    ui.ok(f"all {len(commands)} verify command(s) passed")
    return 0
