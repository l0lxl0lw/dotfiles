# Execution and repair — internal worker method

Read sibling [workflow.md](workflow.md). Resolve ROOT with sibling resolve-root.py
and read ROOT/tracking/references/delivery.md. Require an exact authorized plan
and delivery run. Run `handoff.py packet ISSUE --stage execute` with the Plan and
any repair Review pinned via --include. Reconcile stale sources/changed decisions
and current review findings before editing. A stage worker does not coordinate
the delivery loop; return its evidence to the owner.

1. Verify the bound feature workspace and branch. Inspect dirty files as potential
   user work. Follow operations.md for issue registration, Orca attachment and
   stage updates. Sync belongs to the owner; never edit main or another worker's
   checkout. Do not commit, push or create a PR from this worker.
2. Implement the smallest coherent approved slice, consistent with existing code.
   If findings invalidate a material design choice, stop with evidence for the
   owner/user rather than silently changing the contract. For an integration-only
   pass, verify the merged source before edits; publish failed verification if
   attributable defects need a budgeted repair. Routine integration is not an
   opportunity for uncounted code repairs.
3. Add meaningful proving tests from the acceptance matrix. Exercise transport,
   service and database semantics where relevant. Mocks alone cannot prove actual
   database ownership, NULL/default or inherited behavior. Fix introduced failures;
   do not repair unrelated baseline defects or equate compilation with behavior.
4. Repairs address the exact required finding IDs or diagnosed attributable CI
   failure. Carry prior findings, repair delta and the journal's shared three-cycle
   budget. Record each finding as fixed/disputed/unresolved with source evidence.
   Unresolved/disputed required findings still block. No implicit reset or extra
   repair beyond the owner's persisted authorization.
5. Reconcile the check manifest with `verify.py init ISSUE --plan PLAN_URL`.
   Preserve an incompatible existing manifest and report a material change.
   Finish edits then `verify.py run ISSUE --plan PLAN_URL`. Reuse only matching
   source/environment evidence; check external state separately. Preserve exits,
   skipped/missing checks, baseline facts and actual private runner logs.
6. Publish `handoff.py record ISSUE verification --run RUN_ID`, including the
   repair Review as --input and explicitly superseding prior Verification.
   Failed receipts can be published honestly but cannot support a pass.

Return the exact Verification URL, source, checks/results, findings, repair round
and blockers. Stop; the delivery owner records finish and dispatches a fresh
independent reviewer. Never claim accepted/commit-ready from verification alone.
