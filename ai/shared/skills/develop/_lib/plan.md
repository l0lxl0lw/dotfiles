# Implementation plan — internal preparation method

Read [workflow.md](workflow.md). Build the plan within `develop-prepare` using
verified research and user choices. No additional stage invocation is required.

1. Spot-check real entry points, logic/storage and test patterns. Reuse research
   while checking changed source references. Do not add a mandatory audit chain.
2. Map every required requirement ID to scenario/input → observable response →
   state change/no-change → proving check. Cover meaningful negatives: malformed
   input, ownership/authorization, missing/default/NULL data, compatibility,
   transport wiring and relevant state transitions. Avoid fixtures that bypass
   the behavior being tested. For bugs specify a regression check, or justified
   manual proof if automation is impractical.
3. Specify exact affected components and 2–4 ordered implementation steps. Include
   targeted argv/cwd/check formats, prerequisites, environment assumptions,
   required repository/CI checks and baseline exclusions. Read the existing
   `.opencode/workflow/checks.json`; do not write it during preparation.
4. Cover every required criterion with checks or a justified review_reason and
   concrete manual evidence expectations. Compilation is not behavioral proof.
   Required failures cannot be waived by labeling them baseline. Unresolved
   product decisions block execution. Self-check completeness once and present
   the consolidated preparation result for approval.

After approval and contract/research publication, publish schemas/plan.example.json
with acceptance_matrix, coverage, check_manifest, steps, exact research facts,
source references and current contract revision. Use `handoff.py record ISSUE
plan --data FILE --input RESEARCH_URL`, superseding the exact prior plan. Set
Ready when prepared; it does not imply execution approval. An explicit combined
"publish and deliver through PR" approval permits the Prepare owner to invoke
`develop-deliver` immediately with the returned exact Plan URL. Otherwise stop
with the published plan. Never report proposed checks as already run.
