"""Git checkpoints around `gea delegate`, and `gea undo` to go back.

Before a builder touches the tree we record, under `refs/gea/`:
- the snapshot of tracked changes (`git stash create`, or HEAD if clean),
- HEAD itself,
- the untracked files that already existed (in `<git-dir>/gea/`).

`gea undo <TASK-ID>` resets to that HEAD, re-applies the snapshot and
deletes only the untracked files created since — never anything that was
already there.
"""

from __future__ import annotations

import json
from pathlib import Path

from gea import proc, ui
from gea.i18n import t

SNAPSHOT_REF = "refs/gea/checkpoints/{task_id}"
HEAD_REF = "refs/gea/checkpoint-heads/{task_id}"


def _git(root: Path, *args: str) -> tuple[str, int]:
    out, _err, code = proc.run(["git", "-C", str(root), *args], timeout=60)
    return out.strip(), code


def untracked(root: Path) -> list[str]:
    out, _code = _git(root, "ls-files", "--others", "--exclude-standard")
    return out.splitlines()


def _meta_path(root: Path, task_id: str) -> Path:
    git_dir, _ = _git(root, "rev-parse", "--absolute-git-dir")
    return Path(git_dir) / "gea" / f"{task_id}.json"


def create(task_id: str, repo_root: Path | None = None) -> bool:
    """Record a checkpoint for `task_id`. False if the repo has no commits."""
    root = repo_root or Path.cwd()
    head, code = _git(root, "rev-parse", "HEAD")
    if code != 0:
        return False
    snapshot, _ = _git(root, "stash", "create")
    _git(root, "update-ref", SNAPSHOT_REF.format(task_id=task_id), snapshot or head)
    _git(root, "update-ref", HEAD_REF.format(task_id=task_id), head)
    meta = _meta_path(root, task_id)
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps({"untracked": untracked(root)}), encoding="utf-8")
    return True


def base_ref(task_id: str, repo_root: Path | None = None) -> str:
    """The snapshot to diff against: the task's checkpoint, else HEAD."""
    root = repo_root or Path.cwd()
    snapshot, code = _git(root, "rev-parse", "--verify", SNAPSHOT_REF.format(task_id=task_id))
    return snapshot if code == 0 else "HEAD"


def changed_files(task_id: str, repo_root: Path | None = None) -> list[str] | None:
    """Files changed since the checkpoint (tracked edits vs. the snapshot, plus
    untracked files that did not exist then). None if there is no checkpoint."""
    root = repo_root or Path.cwd()
    snapshot, code = _git(root, "rev-parse", "--verify", SNAPSHOT_REF.format(task_id=task_id))
    if code != 0:
        return None
    diff, _ = _git(root, "diff", "--name-only", snapshot)
    changed = set(diff.splitlines())
    meta = _meta_path(root, task_id)
    if meta.exists():
        before = set(json.loads(meta.read_text(encoding="utf-8"))["untracked"])
        changed |= set(untracked(root)) - before
    return sorted(changed)


def moved_past(task_id: str, repo_root: Path | None = None) -> bool:
    """True when HEAD is no longer the checkpoint's: restoring would `reset
    --hard` it back and drop every commit made since (a merge, a fast-forward)."""
    root = repo_root or Path.cwd()
    head, h_code = _git(root, "rev-parse", "--verify", HEAD_REF.format(task_id=task_id))
    now, n_code = _git(root, "rev-parse", "HEAD")
    return h_code == 0 and n_code == 0 and head != now


def restore(task_id: str, repo_root: Path | None = None, force: bool = False) -> bool:
    """Back to the checkpoint. Refuses (False) when HEAD moved since it was
    taken, unless `force`: gea must never move HEAD backwards on its own."""
    root = repo_root or Path.cwd()
    if not force and moved_past(task_id, root):
        return False
    snapshot, s_code = _git(root, "rev-parse", "--verify", SNAPSHOT_REF.format(task_id=task_id))
    head, h_code = _git(root, "rev-parse", "--verify", HEAD_REF.format(task_id=task_id))
    if s_code != 0 or h_code != 0:
        return False
    meta = _meta_path(root, task_id)
    before = None
    if meta.exists():
        before = set(json.loads(meta.read_text(encoding="utf-8"))["untracked"])

    _git(root, "reset", "--hard", head)
    if snapshot != head:
        _git(root, "stash", "apply", snapshot)
    if before is not None:
        for name in set(untracked(root)) - before:
            (root / name).unlink(missing_ok=True)
    return True


def run_undo(task_id: str, assume_yes: bool = False, force: bool = False) -> int:
    root = Path.cwd()
    _, code = _git(root, "rev-parse", "--verify", HEAD_REF.format(task_id=task_id))
    if code != 0:
        ui.err(t("undo.none", task_id=task_id))
        return 1
    status, _ = _git(root, "status", "--short")
    ui.info(t("undo.warning", task_id=task_id))
    print(status or t("undo.clean"))
    if not ui.ask_yes_no(t("undo.confirm"), default=False, assume_yes=assume_yes):
        ui.warn(t("common.aborted"))
        return 1
    if moved_past(task_id, root) and not force:
        ui.err(t("undo.head_moved", task_id=task_id))
        return 1
    if not restore(task_id, root, force=True):
        ui.err(t("undo.failed"))
        return 1
    ui.ok(t("undo.done", task_id=task_id))
    return 0
