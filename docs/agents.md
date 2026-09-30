# Builder agents

Ported from Cotizaciones' `scripts/agents.py`, generalized to be global
instead of per-repo:

- `~/gea/config.json["builders"]["profiles"]` — detected agent profiles
  (id, cli, model, quota pool, priority). Refreshed by `gea setup`/`gea
  agents refresh`.
- `~/gea/state.json` — which pools are exhausted and until when. Global on
  purpose: a rate limit belongs to the account, not to one project, so it
  now carries over between repos instead of resetting per-project.
- `agents` in `gea.local.json` (schema and resolution rules in
  `src/gea/agents/spec.py`, README "Agentes"): the planner CLI/model and the
  project's subagents — detected ids, model overrides and custom entries — in
  priority order. It replaces the old `primary`, `primaryModel` and
  `builders.allow`, which are still read and migrate on save.
  `["builders"]["mode"]` is `ask`/`auto`.
- Models are read from each CLI (`agents/models.py`: `opencode models`,
  `agy models`, `codex debug models`; claude aliases; kimi free text).
  `gea agents manage` (`agents/manage.py`) edits all of this interactively, and
  `gea agents planner|add|remove|models|list` do it from scripts.

`gea agents available` prints the mode and every non-exhausted subagent
of the project. `gea agents start <id>` reuses an existing `<prefix>-builder-<id>` herdr
pane or splits a sibling pane in the current tab (same heuristic as the
Cotizaciones skill: wide pane splits right, narrow/tall splits down).
`gea agents check <id>` reads the pane and marks its whole pool exhausted
if it matches a rate-limit pattern.

`gea delegate <task-id> [--agent <id>]` picks the requested (or
highest-priority available) agent, starts its pane, and sends a short
prompt pointing at the task file — the task itself carries the plan, so the
prompt stays short. Unlike Claude Code's own delegar skill, this is a
blocking CLI call (`herdr agent prompt --wait`): there's no harness here to
resume a backgrounded wait.
