---
name: gea-delegate
description: Delegate an already-planned task (created with gea-plan) to a builder agent via herdr, wait for it, and review the resulting diff. Use when the user says "delegate this", "/gea-delegate TASK-00N", or a planned task is ready to implement and you want to spend your own tokens on the plan and review, not on writing the code.
---

# gea-delegate — hand a task to a builder

The goal is to spend the orchestrator's tokens on the plan and the review,
not on writing code or watching a terminal.

## 0. Preconditions

- The task exists (`gea task show <ID>`), `Status: planned` (or
  `in-progress` for a continuation), with a concrete plan and file list —
  if it's vague, improve it first (see `gea-plan`).
- Working tree is clean or the user knows about the pending changes. Note
  the base commit (`git rev-parse --short HEAD`).
- Running inside herdr (`$HERDR_ENV = 1`) — delegation talks to another
  agent's pane, which only exists inside a herdr session.

## 1. Pick an agent

```bash
gea agents available
```

Prints the mode (`ask`/`auto`) and every non-exhausted, allowed agent. In
`ask` mode, ask the user which one to use. In `auto` mode, use the first
one listed. An empty list means everything is exhausted or nothing is
installed — skip straight to step 4.

## 2. Delegate

```bash
gea delegate <TASK-ID> [--agent <id>]
```

This starts (or reuses) the `builder-<id>` pane, sends it a short prompt
pointing at the task file (the task already carries the plan — the prompt
stays short on purpose), and blocks until the builder settles. **While it
runs, don't edit files in the repo yourself** — you'd both be writing to
the same tree.

If the command reports `BLOCKED`, the CLI is waiting on a confirmation
dialog. Read it:

```bash
herdr agent read builder-<id> --source recent-unwrapped --lines 40
```

Decide what's safe to approve yourself and tell the user what to click if
it needs a human (herdr blocks scripting an answer to a permission
prompt on purpose).

If it looks stuck without a clear status, it may have hit a rate limit:

```bash
gea agents check <id>
```

`EXHAUSTED <until>` marks that whole pool unavailable and gea won't offer
it again until then — check what it already wrote (`git status --short`,
`git diff`) and go back to step 1 to pick the next available agent instead
of waiting for the retry.

## 3. Review

Read files, not the terminal:

`gea delegate` already printed a compact summary (files changed, files
outside scope, verify result) — don't ask for the builder's terminal.

1. `gea review-pack <TASK-ID>`, then read that single file: task, diff,
   verify results and scope warnings.
2. The task: `Status` should be `review`, with *Implementation Notes* and
   *Deviations* filled in.

Check against the plan and `AGENTS.md` (reuse, file-size limit, naming,
docs updated). Write findings into the task's `## Review` section with a
severity (`critical`/`important`/`minor`) and `file:line`.

- **Critical/important findings** → send them back to the *same* pane
  (same session, so it remembers its own work):
  `gea delegate <TASK-ID> --agent <id>` again, after updating the task
  with what to fix. After two rounds without it landing, switch to another
  available agent (step 1) instead of a third round with the same one.
- **Clean** → mark `No findings` in `## Review`, check off *Verification*,
  and move on to closing (see `.agents/builder.md`'s cycle): move the task
  to `done/` (`gea task done <ID>`), commit.

## 4. No agents available

Implement it yourself from the plan, and note that in *Deviations*.
