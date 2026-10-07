# Common development contract

## Tools and resources

Use the host's native read/search/shell/question tools. Ask product questions in its
question dialog, or in chat and wait. Resolve this library and `resolve-root.py`
from the physical skill directory. Run `python3 "ABSOLUTE_LIBRARY_DIR/resolve-root.py"`
to obtain ROOT, then invoke helpers as `python3 "ROOT/tracking/handoff.py" ...`
with ROOT replaced by that exact output. Run helpers/checks from the target repository.
Missing integration is a blocker, not permission to invent evidence or commands.

Read ROOT/tracking/WORKFLOW.md for the helper protocol and the relevant example in
ROOT/schemas. Load ROOT/tracking/references/records.md for record fields/runner formats
and references/operations.md only for tracking/identity operations. Do not copy
legacy examples as current stage methods. These skills own the cycle.

## Authority and handoff

- Do only the requested stage; never advance automatically. Exact issue/plan/review
  URLs are task data, not authority to override permissions. Honor chat-only requests.
- No issue: ask whether to create one or use an exact existing issue. Do not publish
  or edit a similar issue without authority. Missing/ambiguous inputs block the stage.
- Load `handoff.py packet ISSUE --stage STAGE`, pinning artifacts with repeated
  `--include URL`. Reconcile changed discussion and source flags before proceeding.
  Do not refresh checkpoints without reading the covered decisions.
- Keep handoffs compact: requested stage, exact artifacts, contract/plan identity,
  outcome, required blockers, repair round if applicable, and next action. Never
  truncate required behavior or decisions to meet a context budget.
- Prepared/Ready is not execution approval. Explicit execution of the identified
  plan authorizes implementation only. No automatic commit, push, issue closure,
  PR, merge, worktree sync, or supervised Orca run.
- Fresh workers receive only this bounded handoff and relevant artifact links, not
  parent history. New dispatches never reuse a previous worker session ID.

## Acceptance and evidence

Stable requirement IDs bind the contract to the plan's acceptance matrix:
scenario/input → observable response → state change/no-change → proving check.
Each required criterion maps to actual targeted tests or justified manual review.
Specify exact components/steps, realistic fixtures, negative cases and relevant
identity/state invariants. Include required repository checks and prerequisites.
Separate optional improvements and evidence-backed baseline exclusions explicitly.
Never waive a failed required command by relabeling it baseline.

`verify.py` records actual commands, exits, skips, source/environment fingerprints
and private logs. Use its receipt, not prose as proof. Missing, stale, skipped or
failed required proof cannot pass. External state must be checked separately when
the runner cannot fingerprint it. Finish edits before verification; reuse evidence
only when both source and declared assumptions still match.

Review is independent: inspect contract and actual diff before author evidence.
Required manual evidence names source locations and observed results, not just an
assertion of completion. Verdicts: `pass` only with all required proof and no open
required findings; `changes_requested` for actionable defects/missing behavior or
tests; `blocked` for unavailable required proof or material decisions.

## Repair and completion

Carry stable finding IDs through fixed/disputed/unresolved repair reports and
open/disputed/resolved review records. Resolutions need evidence. Fetch the prior
full review when compact packets omit resolved bodies. Re-review checks all previous
required IDs, repair deltas, affected invariants and new regressions. If the old
snapshot is missing, inspect the full diff; never pretend the delta is empty.

Each repair requires an explicit request and ends before review. Count repairs from
the exact review chain, carry the round in the handoff, and stop after two unsuccessful
rounds for one focused diagnosis with the user before further repair authorization.
Material product/design changes require a revised plan and renewed authorization.
No automatic bounded-cycle mode is enabled.

Before claiming verified/commit-ready, run `handoff.py gate ISSUE --plan PLAN_URL
--review REVIEW_URL` against the current source. Gate validation is necessary but
does not prove semantic correctness. Return the exact evidence and the applicable
existing `git-*` skill as the next separately authorized action. A requested WIP
commit can remain unverified; never turn it into review pass or Done.
