---
name: develop-plan
description: Use to turn verified development research into exact implementation steps and an observable acceptance matrix with proving checks before implementation.
---

# Define done and how to prove it

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. Load `handoff.py packet ISSUE --stage plan --include
RESEARCH_URL`. Resolve ambiguous artifacts and later decisions. Set Planning without
regressing later work. Direct invocation uses this session and does not edit application code.

1. Reuse source-pinned research. Spot-check the real entry point, core logic/persistence
   and test pattern. Inspect changed cited files when stale; update only invalidated
   findings. Do not repeat broad research or launch a mandatory planning-agent audit.
2. Build the acceptance matrix for every stable required requirement ID:
   **scenario/input → observable response → state change/no-change → proving check**.
   Cover happy path and material negatives/edges. Where relevant distinguish malformed,
   forbidden and missing inputs; trusted identity and ownership; NULL/default rows;
   actual transport wiring; both boolean values and later inherited-default changes.
   Valid success fixtures must not bypass validation using fake identifiers.
3. Resolve material product decisions in a focused question batch. Record required vs
   optional scope, exact affected components and 2–4 ordered implementation steps.
   Specify actual targeted test commands, cwd, prerequisites, relevant environment
   assumptions and required repository/CI checks. Read existing
   `.opencode/workflow/checks.json`; do not create or edit it during planning.
4. Map every required criterion to checks or justified manual review. Manual proof
   must explain why automation is insufficient and what source/observed evidence will
   prove it. Record evidence-backed baseline exclusions separately. A nonzero required
   check cannot be waived as baseline. Compilation alone cannot prove behavior.
5. Self-check completeness once: IDs, negative behavior, state/identity invariants,
   realistic fixtures, normalization, callers and documentation assumptions where
   applicable. Missing checks or unresolved material decisions leave the plan blocked.
   Optional coverage cannot be promoted into required scope without agreement.
6. Publish a v2 Implementation plan with an `acceptance_matrix` array in the record:
   each row has `requirement`, `scenario`, `response`, `state`, and `checks` (check IDs)
   or a justified `review_reason`. The helper retains this additional field in the
   rendered record; keep its proving IDs consistent with the validated `coverage`.
   Include exact source/research references, contract revision, steps, coverage and
   `check_manifest` using schemas/plan.example.json and `handoff.py record ISSUE plan
   --data FILE --input RESEARCH_URL`. Explicitly supersede an old plan. Set Ready only
   when prepared; Ready is not approval. Do not report a check as run unless it ran.

Return the exact Plan URL and suggested `/develop-execute ISSUE_URL PLAN_URL`, or
`/develop-feature execute ISSUE_URL PLAN_URL` for fresh execution. Stop. The user's
explicit execution of that identified plan supplies implementation authorization;
do not add a ceremonial approval round when the request already clearly does so.
