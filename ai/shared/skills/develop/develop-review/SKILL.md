---
name: develop-review
description: Use for independent acceptance review of a development plan's actual diff and source-bound verification, including re-review after repairs.
---

# Independent acceptance gate

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. This skill runs in the current session when invoked
directly. If this context implemented the change or contains its implementation
reasoning, stop and request `/develop-feature review ISSUE_URL PLAN_URL
VERIFICATION_URL` for a new worker (or a separate fresh session). Do not label a
self-review independent. A fresh stage reviewer does the work itself; no reviewer fan-out.

Load `handoff.py packet ISSUE --stage review` with exact Plan, Verification and optional
previous Review pinned. Read the contract and plan before author claims. For the first
review, do not read old review bodies without a concrete reason.

1. Identify base/head and the full intended diff: committed, staged, unstaged and
   untracked. Separate unrelated user work and unchanged baseline defects. Inspect
   each changed behavior and necessary caller/route/schema context.
2. Check each acceptance row against actual code and tests. Look for invalid success
   fixtures, wrong response/status, missing ownership dimensions, one-value default
   assumptions and missing production wiring. Prefer a concrete reproduction over
   speculation. Optional suggestions are not newly frozen acceptance requirements.
3. Read Verification after forming an initial assessment. Verify source/contract/run
   identities and declared environment assumptions. Reuse matching evidence; run
   missing, stale or discriminating checks rather than reflexively rerunning suites.
   Required proof cannot be waived. Manual coverage needs actual source locations
   and observed evidence. Missing local logs require genuine re-verification.
4. Record stable finding IDs, severity, required/optional status, file/line, expected
   vs observed behavior and the smallest correction. Re-review carries every previous
   required ID as open/disputed/resolved; resolved IDs need concrete evidence. Fetch
   the full prior review to retain history, inspect repair deltas and regressions;
   inspect the full intended diff when the prior local snapshot is unavailable.

Publish with schemas/review.example.json and `handoff.py record ISSUE review --data
FILE --input PLAN_URL --input VERIFICATION_URL`, binding the contract revision and
verification run ID. Include `manual_evidence` for required manual criteria. On
re-review include `previous_review` and explicitly supersede it. Verdicts:

- `pass`: all required criteria/checks satisfied and no unresolved required findings.
- `changes_requested`: introduced defect or missing required behavior/test.
- `blocked`: required evidence/check or material decision cannot yet be resolved.

The record helper requires a current published Verification even for a blocked
Review. If that prerequisite is absent, report blocked in the handoff with the exact
missing artifact; do not invent a run ID or claim a Review URL was published.

For pass, run `handoff.py gate ISSUE --plan PLAN_URL --review REVIEW_URL` before
reporting verified readiness. If the gate fails, report the blocker, not readiness.
Schema/runner validity does not establish semantic correctness by itself.

Return exact Review URL, source/base, coverage, evidence reused/run, findings, remaining
checks and next action. Changes requested proposes an explicit execute invocation
with plan and review; pass proposes an existing Git skill when the user wants Git
operations. No application edits, automatic repair, commits or Done/issue closure.
