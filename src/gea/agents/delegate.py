"""`gea delegate <task-id>` — start a builder pane and send it a short
prompt pointing at the task file. Blocks (via `herdr agent prompt --wait`)
until the builder settles, unlike Claude Code's own background-and-resume
pattern — a plain CLI has no harness to resume it later.
"""

from __future__ import annotations

import time
from pathlib import Path

from gea import autonomy, checkpoint, config, ui, verify
from gea.agents import exhaustion, herdr, log, profiles, worktree
from gea.i18n import t
from gea.tasks import budget as budget_mod
from gea.tasks import scope, store
from gea.tasks.store import find_task_path

# Fixed instructions first, variable parts (task, autonomy) last: the stable
# prefix stays identical across delegations so prompt caches can reuse it.
BUILDER_PROMPT_TEMPLATE = (
    "Follow .agents/builder.md: implement the task below following its plan. "
    "Move it to in-progress, run `gea verify --quiet --task {task_id}`, fill in "
    "Implementation Notes and Deviations, and leave it in review. Do not commit.\n"
    "Task: {task_path}\n"
    "Autonomy: {autonomy_line}"
)


def _changed(task_id: str, wt: worktree.Worktree | None) -> list[str]:
    if wt:
        return worktree.changed_files(wt)
    return checkpoint.changed_files(task_id) or []


def _check_scope(task_id: str, task_path: Path, wt: worktree.Worktree | None) -> list[str]:
    """Warn (and note in the task's Review) about files outside `## Files`."""
    patterns = scope.allowed_patterns(task_path.read_text(encoding="utf-8"))
    stray = scope.out_of_scope(_changed(task_id, wt), patterns)
    if stray:
        ui.warn(t("delegate.stray", count=len(stray), files=", ".join(stray)))
        store.append_to_section(
            task_path,
            "Review",
            "important: builder touched files outside `## Files`:\n"
            + "\n".join(f"- `{f}`" for f in stray),
        )
    return stray


def _print_summary(task_id, agent_id, started, task_path, stray, verify_ok, wt) -> None:
    """The orchestrator reads this instead of the builder's raw terminal output."""
    minutes, seconds = divmod(round(time.monotonic() - started), 60)
    ui.ok(t("delegate.done", task_id=task_id, agent=agent_id, minutes=minutes, seconds=seconds))
    print(t("delegate.files", changed=len(_changed(task_id, wt)), stray=len(stray)))
    print(t("delegate.verify_ok") if verify_ok else t("delegate.verify_bad", task_id=task_id))
    print(t("delegate.task_line", path=task_path))
    if wt:
        print(t("delegate.worktree", branch=wt.branch, path=wt.path))


def close_finished_pane(cfg: dict, pane_name: str, status: str, verify_ok: bool) -> bool:
    """Close the builder's pane after a verified run (`builders.close`), so panes
    don't pile up task after task. Failed or unverified runs stay open to inspect,
    and a pane the user opened themselves is never closed."""
    policy = cfg.get("builders", {}).get("close", config.DEFAULT_CLOSE)
    if policy != "on-success" or not verify_ok or not herdr.created_by_gea(status):
        return False
    closed = herdr.close_agent_pane(pane_name)
    if closed:
        ui.info(t("delegate.closed", pane=pane_name))
    return closed


def delegate_task(
    task_id: str, agent_id: str | None = None, use_worktree: bool | None = None
) -> int:
    root = Path.cwd()
    task_path = find_task_path(task_id)
    if task_path is None:
        ui.err(t("common.task_not_found", task_id=task_id))
        return 1

    for gap in scope.missing_for_delegation(task_path.read_text(encoding="utf-8")):
        ui.warn(t("delegate.gap", task_id=task_id, gap=gap))
    tier = store.read_header(task_path, "Tier")
    agent = profiles.pick_agent(agent_id, tier=tier)
    if agent is None:
        ui.warn(t("delegate.no_agent"))
        return 1

    cfg = config.load_project(root)
    if use_worktree is None:
        use_worktree = bool(cfg.get("builders", {}).get("worktrees"))
    builders = cfg.get("builders", {})
    permissions = builders.get("permissions", config.DEFAULT_PERMISSIONS)
    if permissions == "yolo" and not use_worktree:
        ui.err(t("delegate.yolo_needs_worktree"))
        return 1
    wt = None
    if use_worktree:
        wt = worktree.create(task_id, root, builders.get("worktree"))
        if wt is None:
            ui.err(t("delegate.worktree_failed"))
            return 1
    elif checkpoint.create(task_id):
        ui.info(t("delegate.checkpoint", task_id=task_id))
    ui.info(t("delegate.delegating", task_id=task_id, agent=agent.id, cli=agent.cli))
    started = time.monotonic()
    attempt = len(log.read(task_id=task_id)) + 1

    def record(
        result: str, stray: list[str] | None = None, verify_ok: bool | None = None
    ) -> None:
        entry = {
            "kind": "build",
            "tier": tier,
            "project": root.name,
            "task_id": task_id,
            "agent_id": agent.id,
            "pool": agent.pool,
            "result": result,
            "duration_s": round(time.monotonic() - started),
            "round": attempt,
            "files_out_of_scope": len(stray or []),
            "verify_ok": verify_ok,
        }
        if wt:
            entry |= {
                "worktree": str(wt.path), "branch": wt.branch, "base": wt.base,
                "workspace_id": wt.workspace_id,
            }
        log.append(entry)
        herdr.notify(
            f"{task_id}: {result}",
            f"{agent.id} finished in {round(time.monotonic() - started)}s",
            sound="done" if result == "done" else "request",
        )

    pane_name = (
        herdr.pane_name_for(root, "wt", wt.slug)
        if wt
        else herdr.pane_name_for(root, "builder", agent.id)
    )
    status = herdr.start_agent_pane(
        pane_name,
        agent.cli,
        agent.model,
        wt.path if wt else root,
        herdr.permission_args(agent.cli, permissions) + herdr.agent_args(agent.cli, builders),
    )
    print(status)
    if status.startswith("BLOCKED") or "FAILED" in status or "!=" in status:
        if wt:  # a worktree gea just created must not be left half-used
            worktree.remove(wt, root, force=True)
            worktree.delete_branch(wt, root, force=True)
            wt = None  # the log entry must not point at a worktree that is gone
        if "FAILED" in status:
            ui.err(t("delegate.start_failed", task_id=task_id, agent=agent.id))
        record("blocked" if status.startswith("BLOCKED") else "error")
        return 1

    previous = log.last_build_for_agent(agent.id)
    if "reus" in status and previous and previous.get("task_id") != task_id:
        # A reused pane still holds the previous task's context: drop it.
        if herdr.clear_session(pane_name, agent.cli):
            ui.info(t("delegate.fresh", pane=pane_name, previous=previous.get("task_id")))
    prompt = BUILDER_PROMPT_TEMPLATE.format(
        task_id=task_id,
        task_path=task_path,
        autonomy_line=autonomy.describe(cfg.get("autonomy"), config.agents_lang(cfg)),
    )
    def out_of_quota() -> bool:
        retry = f"gea delegate {task_id} --agent {{agent}}"
        return exhaustion.check_exhausted(pane_name, agent, root, status, retry, tier)

    budget = budget_mod.seconds_for(task_path, root)
    prompted = time.monotonic()
    out, code, error = herdr.prompt_result(pane_name, prompt, wait=True, budget_s=budget)
    if code == 0:  # `--wait` can return early between an agent's steps: confirm it is done
        left = max(budget - round(time.monotonic() - prompted), 0)
        settled = herdr.wait_settled(pane_name, left)
        if settled != "settled":
            code, error = 1, "timeout" if settled == "timeout" else "agent_blocked"
    if error == "timeout":
        tail = herdr.read_pane(pane_name)
        store.append_to_section(
            task_path,
            "Implementation Notes",
            f"gea: builder `{agent.id}` hit the {budget // 60} min budget; "
            f"last output:\n\n```\n{tail.strip()}\n```",
        )
        ui.warn(t("delegate.budget", minutes=budget // 60))
        record("exhausted" if out_of_quota() else "timeout")
        return 1
    if code != 0:
        print("\n".join(out.strip().splitlines()[-5:]))
        blocked = "blocked" if error == "agent_blocked" else "error"
        record("exhausted" if out_of_quota() else blocked)
        return 1
    stray = _check_scope(task_id, task_path, wt)
    if not _changed(task_id, wt):
        if out_of_quota():  # a builder stuck on a quota message also "finishes" empty
            record("exhausted", stray, None)
            return 1
        # Nothing changed: verify would "pass" vacuously, so it is not run and the
        # pane stays open for a look.
        record("no-changes", stray, None)
        ui.warn(t("delegate.no_changes", task_id=task_id, agent=agent.id))
        print(t("delegate.task_line", path=task_path))
        return 0
    verify_ok = (
        verify.run_verify(
            root, task_id, quiet=True, cwd=wt.path if wt else None, progress=False
        )
        == 0
    )
    # A builder stuck on a quota message returns "done" having changed nothing.
    if not verify_ok and out_of_quota():
        record("exhausted", stray, verify_ok)
        return 1
    if wt:
        worktree.commit_all(wt, f"wip({task_id}): builder output")
    record("done", stray, verify_ok)
    _print_summary(task_id, agent.id, started, task_path, stray, verify_ok, wt)
    close_finished_pane(cfg, pane_name, status, verify_ok)
    return 0
