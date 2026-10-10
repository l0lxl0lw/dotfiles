# Source-backed research — internal preparation method

Read [workflow.md](workflow.md) and [prepare-workers.md](prepare-workers.md).
The main-session owner delegates focused investigations to research specialists
alongside brainstorming; an unpublished draft needs no issue or tracking setup.

1. Identify the concrete technical unknowns blocking a plan. Trace real entry
   points, callers, core logic, storage and close test analogues. Expand only to
   settle consequential invariants; no mandatory repository-wide agent pipeline.
2. Prepare authorizes the owner to dispatch the research specialists listed in
   prepare-workers.md for concrete questions. Parallelize independent assignments;
   wait for dependencies. Require decisive paths/lines and explicit uncertainty.
   Spot-check the returned evidence and reconcile contradictions. Specialists do
   not delegate further; do not claim delegation when the host lacks it.
3. Verify source claims, ownership, defaults/NULL behavior, error paths, affected
   contracts and test prerequisites. For bugs reproduce the failure when possible,
   trace its cause and distinguish root-cause proof from a hypothesis. If evidence
   is missing, identify what would resolve it. Run focused baseline checks when
   useful; never edit application code as part of unapproved preparation.
4. Record bounded findings with source locations and unresolved technical questions.
   Reuse findings while they remain current; verify changed cited files rather
   than repeating broad investigation. Return to clarification for product choices.

Once the full preparation result is approved and its contract published, reconcile
the research packet and publish schemas/research.example.json via `handoff.py
record ISSUE research --data FILE --input CONTRACT_URL`. Bind actual file hashes;
explicitly supersede the old Research when replacing it. No fabricated URLs or
provenance. Pass its returned URL into the plan record within the same Prepare run.
