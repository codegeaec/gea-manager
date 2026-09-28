# `gea init`

Idempotent per-project wizard — never overwrites a file that already
exists, so it's safe to re-run after upgrading gea.

1. Offers `git init` if there's no repo yet.
2. Picks the primary agent among installed ones (Claude Code recommended).
3. Asks where tasks/subtasks live: `home` (`~/gea/projects/<name>`, with a
   gitignored `.gea` symlink in the repo) or `repo` (`.gea/` versioned).
4. Asks the commit language and the docs language (defaults to the same).
5. Detects the package manager from the lockfile (`src/gea/init/detect.py`)
   and whether the project uses shadcn/ui (`components.json`).
6. Detects likely verify commands (tsc/lint/test from `package.json`,
   pytest/ruff from `pyproject.toml`, cargo/go equivalents) and confirms
   them before writing `gea.json`.
7. Writes `gea.json`, `AGENTS.md`, `CLAUDE.md` (only if Claude Code is
   installed), `.agents/{README,commit-conventions,gotchas,builder}.md`,
   optionally `docs/{INDEX,00-vision-*,adr/0000-template}.md`, merges
   `.claude/settings.json`'s `attribution` block, and updates `.gitignore`.
8. Creates the `.gea` symlink to `~/gea/projects/<name>` when
   `tasks.location` is `home`.
9. Offers to run `codegraph init` if codegraph is installed.

Templates live in `src/gea/templates/{es,en}/`, chosen by the project's
`lang.docs`. `gea.json`'s `builders.allow` is seeded from every detected
agent profile (`gea.agents.profiles.load_profiles()`), and `builders.mode`
defaults to `ask`.

`gea verify` (`src/gea/verify.py`) simply runs `gea.json["verify"]`'s
commands one at a time via `bash -c`, printing ✓/✗ and the tail of a
failing command's output.

## Primary model (claude only)

If the primary agent is Claude Code, `gea init` asks whether to
automatically set `/model opusplan` the first time `gea` creates that
project's claude tab (`gea.json`'s `primaryModel`, recommended default:
yes). `gea` (see `docs/workspace.md`) only sends it on the tab's actual
first creation — reopening an already-running tab never resends it.
