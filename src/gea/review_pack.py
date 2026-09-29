"""`gea review-pack <ID>` — one file with everything a reviewer needs:
the task, the diffstat, a size-capped diff, the verify results and scope
warnings. The reviewer reads this instead of running git/cat by hand,
which is where review tokens usually go.
"""

from __future__ import annotations

from pathlib import Path

from gea import checkpoint, proc, ui, verify
from gea.i18n import t
from gea.tasks import scope, store

MAX_LINES_PER_FILE = 150


def _diff_for(root: Path, base: str, path: str) -> str:
    diff, _err, _code = proc.run(["git", "-C", str(root), "diff", base, "--", path])
    if not diff.strip():  # untracked file: show its head instead
        try:
            body = (root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "(unreadable)"
        diff = "\n".join(f"+{line}" for line in body.splitlines())
    lines = diff.splitlines()
    if len(lines) > MAX_LINES_PER_FILE:
        cut = len(lines) - MAX_LINES_PER_FILE
        lines = lines[:MAX_LINES_PER_FILE] + [f"... ({cut} more lines cut)"]
    return "\n".join(lines)


def build(task_id: str, root: Path) -> str | None:
    task_path = store.find_task_path(task_id, root)
    if task_path is None:
        return None
    task_text = task_path.read_text(encoding="utf-8")
    base = checkpoint.base_ref(task_id, root)
    files = checkpoint.changed_files(task_id, root)
    if files is None:
        out, _e, _c = proc.run(["git", "-C", str(root), "diff", "--name-only", "HEAD"])
        files = out.split()

    parts = [f"# Review pack — {task_id}", "", "## Task", "", task_text.strip(), ""]
    stray = scope.out_of_scope(files, scope.allowed_patterns(task_text))
    if stray:
        parts += ["## Scope warnings", ""] + [f"- outside `## Files`: `{f}`" for f in stray] + [""]

    parts += ["## Verify", ""]
    for command in verify.commands_for(root, task_id) or []:
        passed, tail = verify.execute(command)
        parts.append(f"- {'PASS' if passed else 'FAIL'} `{command}`")
        if not passed:
            parts += ["", "```", tail, "```", ""]
    parts += ["", f"## Diff ({len(files)} file(s))", ""]
    for f in files:
        parts += [f"### {f}", "", "```diff", _diff_for(root, base, f), "```", ""]
    return "\n".join(parts)


def run_review_pack(task_id: str) -> int:
    root = Path.cwd()
    content = build(task_id, root)
    if content is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1
    target = store.task_root(root) / "review" / f"{task_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    ui.ok(t("pack.written", target=target))
    return 0
