"""`gea uninstall` — revert what `gea setup` recorded in the manifest.

Reverts only config-level changes: managed instruction blocks and skills.
Installed binaries (mise, herdr, agent CLIs) are left alone. Every edited
file is backed up first; nothing happens without confirmation unless
`--yes` is passed (AGENTS.md rule 8). `--purge` also removes ~/gea, after
copying it to the backup directory.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from gea import dryrun, manifest, paths, proc, ui
from gea.setup import global_instructions


def _backup_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return paths.home() / f"gea-uninstall-backup-{stamp}"


def _plan(purge: bool) -> list[str]:
    plan = [f"remove the gea block from {p}" for p in manifest.of_kind(manifest.KIND_INSTRUCTIONS)]
    skills = manifest.of_kind(manifest.KIND_SKILL)
    if skills:
        plan.append(f"remove skills: {', '.join(skills)}")
    if purge:
        plan.append(f"delete {paths.gea_home()} (config, state, tasks)")
    return plan


def _backup_file(path: Path, backup: Path) -> None:
    dest = backup / path.relative_to(paths.home()) if path.is_relative_to(paths.home()) else (
        backup / path.name
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def run_uninstall(assume_yes: bool = False, purge: bool = False, dry_run: bool = False) -> int:
    dryrun.enable(dry_run)
    plan = _plan(purge)
    if not plan:
        ui.ok("nothing recorded by `gea setup` — nothing to uninstall")
        return 0

    ui.info("gea uninstall will:")
    for line in plan:
        print(f"  - {line}")
    if dry_run:
        return 0
    if not ui.ask_yes_no("Continue? (backups go to ~/gea-uninstall-backup-*)", False, assume_yes):
        ui.warn("aborted")
        return 1

    backup = _backup_dir()
    for target in manifest.of_kind(manifest.KIND_INSTRUCTIONS):
        path = Path(target)
        if path.exists():
            _backup_file(path, backup)
        if global_instructions.remove_from_file(path):
            ui.ok(f"gea block removed from {path}")

    skills = manifest.of_kind(manifest.KIND_SKILL)
    if skills:
        code = proc.run_visible(["npx", "skills", "remove", "-g", "-y", *skills], timeout=120)
        (ui.ok if code == 0 else ui.warn)(f"skills removal exit code {code}")

    if purge and paths.gea_home().exists():
        shutil.copytree(paths.gea_home(), backup / "gea", dirs_exist_ok=True)
        shutil.rmtree(paths.gea_home())
        ui.ok(f"{paths.gea_home()} removed")
    else:
        # Keep the manifest honest: what it listed has now been reverted.
        (paths.gea_home() / "manifest.json").unlink(missing_ok=True)

    ui.ok(f"gea uninstall complete (backup: {backup})")
    return 0
