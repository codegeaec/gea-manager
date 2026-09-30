---
name: gea-init
description: Set up the current repo to work with gea — run `gea init`, then help fill in docs/00-vision-product.md and the project's glossary through conversation. Use when a repo has no gea.json yet, or when the user asks to "set up gea", "run gea init", or "get this project onto gea".
---

# gea-init — set up a project

`gea init` (see `docs/init.md` in gea-manager, or `gea init --help`)
handles the mechanical scaffolding: `gea.json`, `AGENTS.md`/`CLAUDE.md`,
`.agents/`, optionally `docs/`, `.claude/settings.json`, `.gitignore`, and
a `codegraph init` if codegraph is installed. This skill's job is what the
wizard *can't* automate: turning a conversation with the user into a real
first draft of `docs/00-vision-product.md` (or `-producto.md`) and the
project's glossary.

## Steps

1. If `gea.json` doesn't exist yet, run `gea init` and answer its prompts
   together with the user (primary agent, tasks location, the language of
   agents / docs / commits, verify commands, builder agents). On a project
   that already has AGENTS.md, CLAUDE.md, `.agents/` or tasks, read the
   inspection report it prints first: existing files are kept and only get a
   gea block; offer `gea task import` for tasks in another layout.
2. If `gea init` wrote `docs/00-vision-product(o).md`, don't leave it as
   the placeholder text. Ask the user:
   - What does this product do, in one paragraph?
   - Who is it for?
   - What's explicitly out of scope for now?
   Write their answers into that file directly — this is the one piece of
   gea-init that's genuinely conversational, not templated.
3. If the project has domain-specific vocabulary worth keeping consistent
   between two languages (e.g. Spanish UI copy over English code
   identifiers, like `AGENTS.md`'s "Language" rule expects), offer to start
   a `.agents/glossary.md` (or `glosario.md`, matching `lang.docs`) with a
   two-column table and a handful of terms from the conversation so far.
4. Confirm the generated `AGENTS.md`'s verify commands actually work
   (`gea verify`) before considering the setup done.

## What not to do

- Don't re-run `gea init` speculatively on a repo that already has a
  `gea.json` — it's idempotent but there's no reason to re-answer settled
  questions. Edit `gea.json` directly for small config changes instead.
- Don't invent product vision from the code — ask. That's the entire point
  of this skill over `gea init` alone.
