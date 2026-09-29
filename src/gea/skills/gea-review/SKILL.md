---
name: gea-review
description: Review a builder's diff against its task, apply or request fixes, and close the task with a commit. Use after a task comes back in `review` status — whether you delegated it (gea-delegate) or implemented it yourself.
---

# gea-review — review and close a task

This is the second half of `gea-delegate`'s review step, pulled out on its
own for when a task needs (re)reviewing without going through delegation
again — e.g. reviewing your own direct implementation, or a second pass
after a fix.

## 1. Read

- Run `gea review-pack <TASK-ID>` and read only the file it writes
  (`<task root>/review/<TASK-ID>.md`): the task, a size-capped diff since
  the pre-delegation checkpoint, verify results run by gea itself (never
  trust a builder's self-report) and scope warnings. Don't `git diff` /
  `cat` files one by one — that is where review tokens go.
- In the task: is `Status: review`? Are *Implementation Notes* and
  *Deviations* filled in (even briefly)?
- Open a source file only when the pack's excerpt cuts something you need.

## 2. Check against

- The task's own `## Plan` and `## Files` — did it actually do what was
  planned, only what was planned?
- `AGENTS.md`'s hard rules for this project: file-size limit, reuse before
  creating (including within the same file — a repeated block is a
  finding), naming, package manager.
- If `gea.json`'s `builders.ponytail` is on: did the builder add anything
  the task didn't ask for (an unrequested dependency, a speculative
  abstraction, a wrapper nobody needed)? That's a legitimate finding here
  too, not just a builder-side habit.
- Did behavior or architecture change without a matching `docs/` update?

## 3. Findings

Write them into the task's `## Review`, one per line, with a severity
(`critical` / `important` / `minor`) and `file:line`. Be concrete about the
failure scenario, not just "this looks off".

- **Critical/important** → either fix them yourself (small, mechanical) or
  send them back to the builder (see `gea-delegate` step 3) if it's still
  available.
- **None, or all resolved** → continue to closing.

## 4. Close

1. Check off `## Verification`'s checklist for real (don't just tick
   boxes — actually ran what they say).
2. Update `docs/` if this task changed behavior or architecture, in the
   same commit.
3. `gea task done <TASK-ID>` (moves it to the `done/` subfolder).
4. Commit — atomic, in the project's `lang.commits`, no co-author or tool
   signature (see `.agents/commit-conventions.md`). If the task was split
   into subtasks, each subtask gets committed on its own as soon as it's
   clean; the parent task's own close (docs + moving it to `done/`) is a
   separate, final commit once every subtask has already landed.
