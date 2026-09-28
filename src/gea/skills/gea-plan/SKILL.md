---
name: gea-plan
description: Turn a request into a concrete task (and subtasks, if it's large) under this project's gea task root. Use whenever the user asks for a non-trivial change and there's no task for it yet, or explicitly asks to "plan this" or "/gea-plan".
---

# gea-plan — turn a request into a task

A task is the durable bridge between planning and implementation (see
`.agents/builder.md` and `gea delegate`): whoever implements it — you, a
delegated agent, a teammate days later — reads the task file, not the chat
history.

## 1. Ground the request (grill-me pattern)

Before writing anything, make sure the request is actually well-formed.
Borrowing the "grill me" habit: ask the two or three questions that would
most change the plan if answered differently (scope boundary, which
existing code this touches, what "done" looks like) — don't ask questions
whose answer wouldn't change what you write. If the request is already
concrete and the codebase makes the constraints obvious, skip straight to
step 2 instead of asking out of habit.

## 2. Look for existing code first

Read the relevant docs (`docs/INDEX.md`) and search the codebase (use
codegraph if the project has it — `.codegraph/`) for something that
already does most of this. `AGENTS.md`'s reuse rule applies to planning
too: a task that says "extend X" is better than one that says "add a new
Y" when X already covers most of it.

## 3. Write the task

```bash
gea task new "<short title>"
```

Fill in Objective, Context, Requirements, Existing Implementation, Plan
(numbered steps), Files, Decisions — leave Implementation Notes, Deviations
and Review empty for whoever implements it. Be concrete: file paths,
function names, the exact verify commands (`gea verify` already knows
them from `gea.json`, but call out anything task-specific).

## 4. Split into subtasks if it's big

If the plan has 4+ steps touching clearly separable groups of files (e.g.
"schema" doesn't share files with "UI"), or it touches a migration step
that needs a pause for the user to run something by hand, split it:

```bash
gea subtask new TASK-00N "<subtask title>" [--depends TASK-00N.M]
```

Each subtask gets its own acotated `Files` list — if two subtasks would
touch the same file, they're sequential (`--depends`), not parallel. Each
subtask goes through its own plan → implement → review → close cycle and
gets its own commit; don't let several subtasks' changes pile up
uncommitted waiting for the last one to finish.

## 5. Hand off

Once the task (or its first ready subtask) is written, either delegate it
(`gea-delegate` skill) or implement it directly for something trivial.
