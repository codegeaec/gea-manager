# gea guide: build (you are the builder)

You implement one task; planning and review happen elsewhere.

1. Read `AGENTS.md` and the task file you were given. Move it to `in-progress`.
2. Implement the plan, touching only the paths in `## Files`, reusing existing
   helpers. If the plan is ambiguous, note it in *Deviations* and take the most
   reasonable reading.
3. Verify: `gea verify --quiet --task <ID>` (project checks + `## Acceptance`).
   Fix what it reports; run nothing else.
4. Fill in *Implementation Notes* / *Deviations* briefly, update `docs/` if
   behaviour or architecture changed, and leave the task in `review`.
5. Do not commit and do not mark the task completed.
6. Stuck? Reproduce, find the root cause, apply the smallest fix, and note
   cause + fix in *Implementation Notes*. Check `.agents/gotchas.md` first.
