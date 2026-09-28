"""Clean up the old herdr-setup gist's shell integration.

That gist (`herdr-setup.sh`) added a `herdr()` shell function to
`.bashrc`/`.zshrc` that hijacked `herdr` with no args to open a
llama.cpp/WSL-specific workspace, plus a standalone `~/.local/bin/herdr-repo`
script. `gea setup` replaces that whole flow (`gea` with no args, see
workspace.py) so the old one has to go — otherwise the two fight over the
same command.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from gea import paths

OLD_MARKER = '# herdr: al invocar "herdr" sin argumentos'
OLD_HERDR_REPO = paths.local_bin() / "herdr-repo"


def _backup_suffix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def find_legacy_snippet(rc_path: Path) -> bool:
    if not rc_path.exists():
        return False
    return OLD_MARKER in rc_path.read_text(encoding="utf-8")


def remove_legacy_snippet(rc_path: Path) -> bool:
    """Remove the old herdr() function block from an rc file.

    The block runs from the marker comment through the next blank line
    following its closing brace — see herdr-setup.sh's SNIPPET. Returns
    True if something was removed. Always backs up the file first.
    """
    if not find_legacy_snippet(rc_path):
        return False

    backup = rc_path.with_suffix(rc_path.suffix + f".bak.{_backup_suffix()}")
    shutil.copy2(rc_path, backup)

    lines = rc_path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    skipping = False
    brace_depth = 0
    seen_open_brace = False
    for line in lines:
        if not skipping and OLD_MARKER in line:
            skipping = True
            brace_depth = 0
            seen_open_brace = False
            continue
        if skipping:
            brace_depth += line.count("{") - line.count("}")
            seen_open_brace = seen_open_brace or "{" in line
            # Once we've opened at least one brace (the function body) and
            # closed them all again, the block is done.
            if seen_open_brace and brace_depth <= 0:
                skipping = False
            continue
        output.append(line)

    rc_path.write_text("".join(output), encoding="utf-8")
    return True


def remove_legacy_herdr_repo() -> bool:
    if OLD_HERDR_REPO.exists():
        backup = OLD_HERDR_REPO.with_name(OLD_HERDR_REPO.name + f".bak.{_backup_suffix()}")
        shutil.copy2(OLD_HERDR_REPO, backup)
        OLD_HERDR_REPO.unlink()
        return True
    return False


def cleanup_legacy_setup() -> list[str]:
    """Remove the legacy herdr()/herdr-repo setup from this machine.

    Returns a list of human-readable actions taken (empty if there was
    nothing to clean up).
    """
    actions: list[str] = []
    for rc_path in paths.shell_rc_files():
        if remove_legacy_snippet(rc_path):
            actions.append(f"removed legacy herdr() function from {rc_path}")
    if remove_legacy_herdr_repo():
        actions.append(f"removed legacy {OLD_HERDR_REPO}")
    return actions
