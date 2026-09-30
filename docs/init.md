# `gea init`

Per-project wizard for new **and** already-started projects. Idempotent
(a second run changes nothing) and it never overwrites what the user wrote:
missing files are created, existing ones get a gea-managed block between
`<!-- gea:start -->` / `<!-- gea:end -->` markers (`src/gea/managed_block.py`).

Machine vs. project: `gea setup` prepares the machine once (tools, agent CLIs,
herdr integrations, builder profiles, global skills). `gea init` prepares each
project. `gea doctor` checks both.

## Flow

1. Warns if required tools are missing (`gea setup` first) and offers
   `git init` if there is no repo.
2. **Inspects** the repo read-only (`init/inspect.py`, `init/report.py`) and
   prints what exists / what gea will add / what it will not touch: existing
   AGENTS.md/CLAUDE.md (with token size), `.agents/` files, equivalents that
   make a gea file unnecessary (e.g. `convenciones-commits.md` covers
   `commit-conventions.md`), tasks in another layout, a project-level shadcn
   MCP server.
3. Asks: planner, its model (read from the CLI) and subagents (`agents` in
   `gea.local.json`; the same prompts as `gea agents manage`), tasks location
   (`home` = `~/gea/projects/<name>` behind a gitignored `.gea` symlink, or
   `repo` = versioned `.gea/`), the **three languages one by one** —
   agents (`AGENTS.md`, `CLAUDE.md`, `.agents/*`), documents (`docs/*`, task
   templates) and commits, each defaulting to the previous answer —
   builder autonomy and the detected verify commands. Subagents can be any
   detected profile or a custom one (another model of an installed CLI); models
   are picked from the list each CLI reports.
4. Writes `gea.json` (policy, committed) and `gea.local.json` (personal,
   gitignored), then, per file:

   | File | Missing | Already there |
   |---|---|---|
   | `AGENTS.md` | full template | managed block ("Working with gea") appended |
   | `CLAUDE.md` | full template (if Claude is installed) | block importing `@.agents/orchestrator.md` (and `@AGENTS.md` if absent) |
   | `README.md` | minimal README + section | "Working with gea" section appended |
   | `.agents/{builder,orchestrator,gea}.md`, `README.md` | created | untouched |
   | `.agents/{commit-conventions,gotchas}.md` | created | skipped if an equivalent exists |
   | `docs/*` | created if the folder does not exist | folder left alone |
   | `.claude/commands/gea-*.md`, `.opencode/commands/gea-*.md` | created for installed CLIs | untouched |

5. Installs the pre-commit hook (secret scan + strict context lint), updates
   `.gitignore`, links `.gea`, offers `codegraph init`.
6. Offers to import tasks kept in another layout (`gea task import`).

Non-interactive: `gea init --yes [--lang-agents es|en] [--lang-docs es|en]
[--lang-commits es|en]`. Preview with `--dry-run`. Existing files are not
translated: only missing ones are generated in the chosen language.

## Agents without skills

Everything an agent needs is inside the project:

- `AGENTS.md` (read by every CLI) points to `.agents/gea.md`, a cheat sheet of
  the ~12 commands that matter.
- `gea guide [plan|delegate|review|build|all]` prints the step-by-step guide
  (`templates/<lang>/guide/*.md`, the single source; the bundled skills and the
  slash commands only say "run `gea guide <x>`").
- `/gea-plan`, `/gea-delegate`, `/gea-review` slash commands for Claude Code
  and OpenCode; other CLIs simply read `AGENTS.md`.

## Importing existing tasks

`gea task import [dir] [--dry-run] [--remove-source] [--yes]` converts
`<dir>/active|completed/TASK-*.md` or flat `TASK-*.md` files into gea's
`tasks/`, `subtasks/` and `done/` (see `tasks/importer.py`). Bodies are copied
byte for byte; only the `Status:` line is normalised (a trailing remark
becomes `Note:`). Idempotent; a different file already at the destination
aborts everything; originals are kept unless `--remove-source`, which needs
every imported file tracked and clean in git and asks for confirmation.

## Verify

`gea verify` (`src/gea/verify.py`) runs `gea.json["verify"]` one command at a
time via `bash -c`, printing ✓/✗ and the tail of a failing command's output.

## Planner model

`gea init` asks for the planner's model (`agents.plannerModel`), suggesting
`opusplan` for Claude Code. `gea` (see `docs/workspace.md`) applies it only when
it creates the planner's tab: Claude gets `/model <value>` once, every other CLI
its model flag at start. Change it later with `gea agents manage`.
