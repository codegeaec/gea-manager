"""`gea verify` — run this project's configured verify commands
(`gea.json["verify"]`), one at a time, reporting pass/fail."""

from __future__ import annotations

from pathlib import Path

from gea import config, proc, ui


def run_verify(repo_root: Path | None = None) -> int:
    repo_root = repo_root or Path.cwd()
    cfg = config.load_project(repo_root)
    commands: list[str] = cfg.get("verify", [])

    if not commands:
        ui.warn("no verify commands configured — run `gea init` or edit gea.json")
        return 1

    failed = []
    for command in commands:
        out, err, code = proc.run(["bash", "-c", command], timeout=300)
        if code == 0:
            ui.ok(command)
        else:
            ui.err(command)
            tail = (out + err).strip().splitlines()[-20:]
            for line in tail:
                print(f"    {line}")
            failed.append(command)

    if failed:
        ui.warn(f"{len(failed)} command(s) failed")
        return 1
    ui.ok("all verify commands passed")
    return 0
