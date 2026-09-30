# Commands added in the hardening pass

## Config schema

`~/gea/config.json` and `gea.json` carry `schema_version` (currently `1`).
Files without it load as version 1. A file with a *newer* version, or an
invalid one, is refused with a clear error instead of being misread. There
are no migrations yet.

## `--dry-run`

`gea setup|init|skills sync|uninstall --dry-run` prints `[dry-run] would …`
for every file write and installer command. The seams: `proc.run_visible`,
`config._write_json`, the scaffold writers, global instructions and shell rc
edits (see `src/gea/dryrun.py`). Read-only probes still run.

## `gea uninstall`

`gea setup` records what it touched in `~/gea/manifest.json` (managed
instruction blocks, installed skills). `gea uninstall` reverts exactly that,
backing files up to `~/gea-uninstall-backup-<timestamp>/` first and asking
for confirmation (`--yes` skips it, `--purge` also deletes `~/gea`).
Installed binaries are never removed.

## Optional pieces

`gea setup` asks whether to install **ponytail** (a skill) and **rtk** (a
binary with no skill of its own). Answers persist in
`config.json["optional"]` and are honored by `gea update`/`skills sync`.

## Tasks

- `gea task new --type bugfix|feature|refactor|spike` uses
  `templates/<lang>/tasks/<type>.md`.
- `## Acceptance` bullets containing a backticked command are run by
  `gea verify --task <ID>` through the same runner as the project's verify
  commands.
- Closing a task appends its `## Decisions` to `docs/decisions.md`
  (idempotent).

## Checkpoints

`gea delegate` saves `refs/gea/checkpoints/<ID>` (tracked changes, including
uncommitted ones), `refs/gea/checkpoint-heads/<ID>` and the list of
pre-existing untracked files. `gea undo <ID>` resets to that HEAD,
re-applies the snapshot and deletes only untracked files created since.

## Secrets

`gea scan-secrets` scans the lines a staged commit adds (never prints the
match). `gea init` installs it as `.git/hooks/pre-commit` unless another
pre-commit hook exists. Whitelist a line with `gea:allow-secret`.

## Context lint

`gea lint` (also run by `gea doctor`) estimates tokens as chars/4 and warns
above ~2000 tokens for AGENTS.md/CLAUDE.md (~4000 together) and ~5000 per
SKILL.md.

## Autonomy

`gea.json["autonomy"]`: `supervised`, `balanced` (default) or `autonomous`.
Written into AGENTS.md/builder.md at `gea init` and appended to every
delegation prompt from the *current* `gea.json`.

## Stable prompt prefix

Templates and the delegation prompt keep fixed text first and everything
project- or task-specific last, so prompt caches can reuse the prefix.

## `gea doctor` sessions

Per CLI: `claude auth status`, `codex login status`, `opencode auth list`;
agy is judged by its OAuth token file; kimi is reported unknown. A logged-in
CLI whose pool is exhausted (state.json) is reported as "out of tokens",
distinct from "no session".

## agy pools

agy has one pool per model family (`agy-gemini`, `agy-claude`,
`agy-gpt-oss`), filtered by what `agy models` lists. agy exposes no quota
command, so exhaustion is detected from pane output like the other CLIs.

# Delegation, review and hand-off pass

## Delegation log

Every builder attempt (and review/handoff) appends one JSON line to
`~/gea/delegations.jsonl` (`src/gea/agents/log.py`): agent, pool, tier,
result (`done|blocked|timeout|error`), duration, `verify_ok`, files outside
scope, worktree. `gea agents stats` summarizes it; tier routing reads it.

## Budget, notification, scope

- `Budget: 45m` in a task header (default `builders.budget_minutes`, 30) is
  passed to `herdr agent prompt --wait --timeout`. On timeout gea appends the
  pane's last output to *Implementation Notes*, logs `timeout` and leaves the
  pane running.
- `herdr notification show` fires when a builder finishes.
- The paths in backticks under `## Files` are the task's scope. After a run
  gea warns (and writes into `## Review`) about anything else that changed;
  `docs/` and `.gea/` are always allowed. `gea delegate` also warns when
  `## Files` or `## Acceptance` are empty.
- `gea delegate` prints a ~5-line summary instead of the builder's terminal.

## Review

- `gea review-pack <ID>` → `<task root>/review/<ID>.md` (task, diff capped at
  150 lines per file, verify results, scope warnings).
- `gea review <ID>` picks an available agent from a *different pool* than the
  task's last builder and asks it to write findings into `## Review`.

## Routing

`Tier: S|M|L` in the task header. Without history the priority order rules.
Agents with ≥5 logged builds in a tier are ranked by verified success rate;
`builders.tiers` in gea.json (`{"L": ["codex"]}`) restricts and orders outright.

## Hand-off between orchestrators

`gea handoff [--to claude|codex|opencode|agy|kimi]` writes
`<task root>/HANDOFF.md` from what is in flight (in-progress/review tasks,
last delegation each, git state, pending checkpoints, exhausted pools).
`--to` starts the new orchestrator in a herdr pane (`<prefix>-orchestrator-<cli>`),
sends it "read HANDOFF.md", and offers to update `gea.json["primary"]`.
Instructions are portable: every CLI reads `AGENTS.md`; the orchestrator role
lives in `.agents/orchestrator.md`, which `CLAUDE.md` imports.

## Team mode

`gea.json` is committed project policy; `gea.local.json` (gitignored) holds
personal keys (`primary`, `primaryModel`, `builders.allow`, `builders.mode`)
and wins on load with a deep merge. `save_project` splits them again.
`gea init` offers to stop ignoring an old gitignored `gea.json` (backup kept).

## Worktrees

`gea delegate --worktree` (or `builders.worktrees: true`) uses
`herdr worktree create` at `~/gea/worktrees/<repo>/<task>` on branch
`gea/<task>`, copies `gea.json`/`gea.local.json` in, runs the builder there,
verifies there, and commits its output on the branch. No checkpoint is taken
(the worktree is the isolation). A worktree created for a run that fails to
start is removed; `gea task done` offers to remove the task's worktree (the
branch is kept). gea never removes a worktree it did not create.

## Token savers

`gea verify --quiet`, compact `delegate` summary, `review-pack`, fresh builder
session when the task changes (`/clear` or `/new` for claude/codex/opencode),
`gea skills prune`, `gea lint --strict` in the pre-commit hook, and
self-sufficient tasks (`## Files` + `## Acceptance`, filled with codegraph).

## Extras

`gea status`, `gea task new --from-issue N` (uses `gh issue view`),
`gea pr <ID>` (generated body, confirmation first, no tool signature).

# Workspace tabs

`gea` no longer leaves herdr's initial tab "1": it becomes the agent tab.
`gea.json["tabs"]` (`label`, `cwd`, optional `command`) adds tabs for
monorepos; see `docs/workspace.md` and the README.

# Init and adoption pass

`gea init` (see `docs/init.md`): three separate language questions
(agents/docs/commits, `lang.agents` falls back to `lang.docs`), read-only
inspection and report, managed blocks in existing AGENTS.md/CLAUDE.md/README,
no duplicate `.agents` files, builder selection, `gea task import`.
`gea guide [plan|delegate|review|build|all] [--lang]` prints the working guide;
`.agents/gea.md` is the command cheat sheet; `/gea-*` slash commands for
Claude Code and OpenCode. `gea agents refresh` detects builder profiles.

# Builder panes

After a verified `gea delegate` (and after `gea review`), gea closes the pane
it opened for the builder, so panes stop piling up task after task
(`herdr pane close`, via `herdr.close_agent_pane`). `builders.close` in
`gea.json`: `"on-success"` (default) or `"never"`. Failed, unverified, blocked
or timed-out runs stay open to inspect; a pane the user opened themselves
("reused existing pane as …") and the caller's own pane are never closed.
A correction round after a close starts a fresh session; use `"never"` to keep
the builder's session across rounds.
