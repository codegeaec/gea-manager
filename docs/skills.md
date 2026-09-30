# gea skills

Four skills live in `src/gea/skills/gea-{init,plan,delegate,review}/` —
packaged with the wheel (not a top-level repo folder) so `gea skills sync`
can install them on any machine, not just from a gea-manager checkout.

- **gea-init** — runs `gea init`, then does what the wizard can't: turns a
  conversation with the user into `docs/00-vision-product.md` and a
  starter glossary.
- **gea-plan** — grills the request for the couple of questions that would
  actually change the plan, checks for existing code first, writes it with
  `gea task new` / `gea subtask new`.
- **gea-delegate** — the global, gea.json-driven version of Cotizaciones'
  `delegar` skill: `gea agents available` → `gea delegate <ID>` → read the
  diff, not the terminal → review → close.
- **gea-review** — the review/close half on its own, for re-reviewing
  without going through delegation again.

`gea skills sync` installs these plus a short list of third-party skills
(`src/gea/setup/skills.py`'s `THIRD_PARTY_SKILLS`) into every detected
agent via `npx skills add -g -a <agent-ids>`:

- **ponytail** (`dietrichgebert/ponytail`, `skills/ponytail` subpath) — the
  builder-side minimalism habit (see `AGENTS.md`'s ponytail rationale).
- **grill-me** (`mattpocock/skills`, `skills/productivity/grill-me`
  subpath) — the "ask the couple of questions that would actually change
  the plan" habit `gea-plan` builds on.
- **find-skills** (`vercel-labs/skills`, `skills/find-skills` subpath) —
  discovering other installable skills.
- **ui-ux-pro-max** (`nextlevelbuilder/ui-ux-pro-max-skill`) — the only
  entry that's a whole-repo install; that repo is a single skill, not a
  bundle.

Every source above is scoped to one exact skill subpath (a `.../tree/main/
skills/<path>` URL), not a bare repo. Several of the repos these skills
live in bundle many unrelated skills — `dietrichgebert/ponytail` alone also
ships `ponytail-audit`/`-debt`/`-gain`/`-help`/`-review`. Pointing `npx
skills add` at a whole multi-skill repo makes it prompt an interactive
"select skills to install" screen for everything in it, which has no
place in a non-interactive `gea setup` step. (An earlier version of this
list pointed at `vercel-labs/agent-skills` — a 9-skill Vercel-deploy
bundle that happens to share a similar name, but has neither grill-me nor
find-skills in it. `test_skills.py::test_third_party_skills_point_at_a_
single_skill_subpath` guards against that regression.)

## User-invoked-only skills

`gea skills sync` (and `gea setup`/`gea update`) also installs skills that the
agent must never pick on its own — you run them explicitly as `/<skill>`.
Today: `security-audit` from `cloudflare/security-audit-skill`. gea sets
`disable-model-invocation: true` in its `SKILL.md` (Claude Code) and
`allow_implicit_invocation: false` in `agents/openai.yaml` (Codex) after every
sync. The list lives in `MANUAL_SKILLS` (`src/gea/setup/skills_manual.py`).
