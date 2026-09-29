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
