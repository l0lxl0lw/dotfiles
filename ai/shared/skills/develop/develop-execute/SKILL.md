---
name: develop-execute
description: Use when explicitly authorized to implement an identified development plan or repair its exact review findings, then record source-bound verification.
---

# Implement, then prove the approved behavior

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. Require explicit execution authorization and an exact plan.
Load `handoff.py packet ISSUE --stage execute`, pinning plan and any Review with
`--include`. Resolve conflicting/stale decisions and a known current review before
editing. Direct invocation uses this session; it does not create a fresh worker.

1. Confirm repository and isolated feature worktree. Inspect dirty files as potential
   user work. Follow operations.md for issue branch registration, Orca attachment and
   freshness; preserve conflicts. A Needs sync result is not authorization to rebase.
   Set Implementing. Execution never grants commit/push/PR authority.
2. Read relevant code/tests, then implement the smallest coherent approved slice.
   Use existing patterns. If reality invalidates a material design choice, stop, ask,
   revise the plan and obtain renewed authorization rather than changing the contract.
3. Add meaningful proving tests from the matrix. Exercise public transport as well as
   service logic where relevant. SQL-sensitive claims need real database semantics;
   mocks alone do not prove ownership isolation, NULLs or inherited defaults.
4. Run focused checks during iteration, fix introduced failures, then remaining
   required repo/CI checks once. Preserve actual outputs, skipped/missing tests and
   baseline evidence. Do not repair unrelated baseline problems or claim compilation
   tested behavior. Delegate only a bounded, consequential debugging question.

## Repair invocation

Use the exact review's open finding IDs and repair delta. Fetch full prior review
details when needed. Count prior repairs and include this round in the handoff.
After two unsuccessful rounds for this plan, stop for one focused diagnosis and
fresh user direction before editing again. There is no automatic repair loop.

Report every required finding as fixed/disputed/unresolved with evidence. Disputed
material findings remain open for review. Inspect affected invariants/regressions;
do not restart research unless scope materially changed. Never equate checked plan
boxes with resolved findings.

## Verification handoff

After authorized implementation, reconcile the approved manifest with `verify.py init
ISSUE --plan PLAN_URL`. Preserve an incompatible existing manifest and explicitly
reconcile/revise the plan. Finish edits, then run `verify.py run ISSUE --plan PLAN_URL`.
Use `--reuse` only when source and declared assumptions, including external state,
still match. The runner receipt records actual exits/skips/fingerprints/private logs.

Publish `handoff.py record ISSUE verification --run RUN_ID`, with `--input REVIEW_URL`
for repairs and `--supersedes PREVIOUS_VERIFICATION_URL` when replacing evidence.
Failed receipts remain publishable but cannot support pass. Return the Verification
URL, finding resolutions, round, baseline/skipped/missing checks and exact review
invocation. Prefer `/develop-feature review ...` for an independent worker. Stop
before dispatching review or invoking any Git skill.
