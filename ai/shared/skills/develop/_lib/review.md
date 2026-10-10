# Independent review — internal worker method

Read sibling [workflow.md](workflow.md), resolve ROOT with resolve-root.py, and
read ROOT/tracking/references/delivery.md. Be a fresh Task worker independent of
the coordinator and every execution worker. If this context implemented the
change or contains its reasoning, report blocked and ask the owner for a new
worker. Never label self-review independent or edit application files.

Load `handoff.py packet ISSUE --stage review` with exact Plan, Verification and
previous Review for re-review. Read the contract and real diff before author
claims. Do the review yourself; no reviewer fan-out.

1. Identify base/head and full intended committed/staged/unstaged/untracked diff.
   Separate unrelated user work and unchanged baseline defects. Inspect each
   changed behavior, necessary callers, transport, SQL and schemas as applicable.
2. Check each acceptance row against actual code and meaningful tests. Look for
   missing ownership conditions, invalid fixtures, untested defaults, wrong
   responses and missing production wiring. Prefer concrete reproduction over
   speculation. Optional suggestions cannot become new required scope.
3. Read Verification after forming an initial view. Verify source, contract, run
   identity and environment assumptions. Reuse matching evidence; run missing,
   stale or discriminating checks. Do not waive required proof. Missing local logs
   require real re-verification. Manual criteria need source locations and actual
   observations, not a conclusory assurance.
4. Record stable finding IDs, severity, required/optional, location,
   expected/observed and open/disputed/resolved status. Re-review carries all
   previous required findings and checks repairs/regressions. Fetch full previous
   findings when packets compact them. Resolutions require concrete evidence;
   inspect full diff when prior local snapshots are unavailable.
5. Publish schemas/review.example.json via `handoff.py record ISSUE review --data
   FILE --input PLAN_URL --input VERIFICATION_URL`. Bind contract/run identity;
   include required manual_evidence. Re-review names previous_review and explicitly
   supersedes it. A current published Verification is required even for a blocked
   Review; without it report the missing prerequisite rather than inventing one.

Verdicts: pass only when all required criteria/checks pass and no required finding
is open; changes_requested for introduced defects/missing required behavior;
blocked for unavailable proof or product decisions. For pass, run `handoff.py gate
ISSUE --plan PLAN_URL --review REVIEW_URL` against current source. The gate checks
evidence identity, not the semantic sufficiency of tests.

Return Review URL, source/base, coverage, reused/new evidence, findings and
blockers. Stop. The delivery owner—not this worker—advances repairs or Git under
the recorded three-cycle authorization. No commits, issue close, PR merge or Done.
