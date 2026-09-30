## Working with gea

This project is set up for [gea](https://github.com/codegeaec/gea-manager),
which orchestrates AI coding agents.

- Once per machine: install gea, then `gea setup`.
- Once per project: `gea init` (already done here).
- Flow: `gea task new` → `gea delegate <ID>` → `gea review-pack <ID>` →
  `gea task done <ID>`.
- Tasks live in `{tasks_root}`. Agents: `AGENTS.md`, `.agents/gea.md`
  (command cheat sheet) and `gea guide` (step-by-step guides).
