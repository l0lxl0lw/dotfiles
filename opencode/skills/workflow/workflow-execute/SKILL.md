---
name: workflow-execute
description: Use for /execute on a GitHub issue and approved plan, optionally with a review to fix. Implement, verify, and publish content-bound evidence in a fresh context.
---

# Execute: implement the contract, then prove it

Read `~/dotfiles/opencode/tracking/WORKFLOW.md` once. Load compact execute context,
pinning the exact plan and supplied Review with repeated `--include` arguments.
Do not infer scope from parent conversation or treat a plan's checked boxes as proof
that review findings are fixed. Resolve conflicting plans or changed product decisions.

Confirm the correct repo and isolated feature worktree, register the issue branch,
and refresh freshness once. Ask before sync; a Needs sync indication is not permission
to rebase. `/execute` authorizes this identified plan/fix stage, not commits or pushes.
Set Implementing. Small-task implementation target: 5–12 minutes; do not sacrifice
correctness to that target. If work grows, name the concrete cause and narrow the
next investigation instead of reopening all research.

1. Read the plan's relevant code and tests, not the whole research transcript.
   Implement a coherent vertical slice using existing patterns. Keep a short todo
   list if useful. Inspect unfamiliar dirty files as possible user work before editing.
2. Add meaningful tests from the acceptance matrix. Validate the public transport
   behavior as well as service logic when relevant. Exercise real DB semantics for
   SQL-sensitive changes; mocks do not prove row isolation, NULL handling, or inheritance.
3. Run focused checks during iteration. Fix failures caused by this change. Once they
   pass, run remaining required repo/CI checks once. Preserve actual outputs/commands,
   relevant baseline failures, skipped tests, and unperformed checks. Do not fix
   unrelated baseline failures or claim that a compile-only command tested behavior.
4. If reality invalidates a material design decision, ask and record the deviation;
   do not silently change the API contract. Avoid delegation unless targeted debugging
   has a specific unanswered question. One bounded analyzer is preferable to another
   general investigation cycle.

## Review-fix invocation

If compact context contains a current changes-requested Review but the caller did
not pin it, resolve that artifact before editing. Do not blindly repeat the original
plan while leaving its known findings open.

When a Review URL is supplied, treat it as a scoped repair pass against the same
contract. Address actionable findings, add the missing regression cases, rerun
affected checks, and record each finding as fixed or disputed with evidence. A
disputed material finding must return to review; it is not silently closed. Do not
restart ticket/research/planning unless the fix changes the agreed scope.

Publish **Verification** via `handoff.py publish ... --input PLAN_URL` (and
`--input REVIEW_URL` for fixes). Include acceptance row → test/result, commands,
baseline failures/skips, deviations, and remaining work. The helper binds evidence
to the current HEAD and changed-file content digest; finish code edits before posting.
Supersede the previous Verification artifact when replacing it.

Return the Verification URL and `/review ISSUE_URL PLAN_URL` (plus previous Review
URL on a repair). Implementation complete is not review pass. Stop before commit.
