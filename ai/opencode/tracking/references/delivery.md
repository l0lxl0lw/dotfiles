# Prepare → Deliver protocol

This is an explicitly authorized mode of the existing development workflow.
Standalone Git behavior stays unchanged; stage methods are internal. Publication approval covers one
prepared result. **Deliver through PR** covers that exact published plan's
execution, independent review, three repair cycles, commits, pushes, ready PR,
attributable CI repairs and merge-based integration of origin/main. It does not
authorize PR merge, changed product scope, hook bypasses or force-pushes.

## Journal and dispatch

Use the physical revision's ROOT/tracking/delivery.py, Python 3.9+. State defaults
to `${OPENCODE_WORKFLOW_STATE:-~/.local/state/opencode-workflow}/deliveries/KEY`,
outside Git. Keep this exact state root and key for the whole run. Commands emit
JSON; exit 2 is a blocker, never success. Journal/brief files are private.

From the clean main planning checkout, after explicit authorization:

```sh
python3 ROOT/tracking/delivery.py init --key TASK --issue ISSUE_URL --plan PLAN_URL --authorize-through-pr
python3 ROOT/tracking/delivery.py dispatch --key TASK
python3 ROOT/tracking/delivery.py wait-start --key TASK --timeout 120
```

Substitute the actual absolute ROOT; quote paths with spaces. `dispatch` generates
the receiver brief and calls the pinned Orca helper using the same operation key.
Its state includes full workspace/process identity. It does not wait for task
completion. `wait-start` waits only for receiver acknowledgement and releases the
journal lock between reads. If it times out, inspect both journals and the terminal;
do not deliver again under another key. Keyed Orca receipt reconciliation cannot
guarantee redelivery. Explicit operator-confirmed lost-input recovery stays in the
Orca helper and preserves its original state; never invoke it automatically.

### Pre-send launch recovery

For an explicitly requested repair when a workspace was created but readiness
failed before any send intent, run `delivery.py recover-launch --key TASK` from
the original main checkout using the current repaired helper. This narrow action
may repair an older pinned run: it records helper hashes but preserves that run's
resource root, exact brief, approved plan, workspace and repair budget. It refuses
an acknowledged run, pending worker, prior send intent or changed repository.
The transport revalidates the original terminal/process and uses `retry-ready`;
the receiver still runs the original pinned protocol and must acknowledge it.

New edits in the planning checkout do not enter the already-created worktree, so
this recovery does not require discarding/stashing them. Initial dispatch still
requires clean main. After recovery, use the pinned `wait-start` action; an
accepted receipt alone does not prove startup. Recovery never creates a new
workspace or resends a previously attempted prompt.

The receiving owner begins with:

```sh
python3 ROOT/tracking/delivery.py ack --key TASK --session ACTUAL_OWNER_SESSION_ID
python3 ROOT/tracking/delivery.py sync --key TASK
python3 ROOT/tracking/delivery.py inspect --key TASK
```

The acknowledgement proves that the receiving workflow executed from the bound
feature checkout. It is separate from Orca's `turn_started` receipt and never
rewrites that receipt. Use actual host session identifiers; don't invent them.
The launcher's delivery-context plugin supplies `Workflow session ID` to the
owner and each Task child. If absent, restart with the current launcher rather
than guessing an identity. The coordinator can also use actual Task-result IDs.
The receiver must have access to the exact journal/resource paths. Remote hosts
without this local shared state are currently blocked before dispatch.

## Workers and evidence

`begin --key TASK` writes one worker intent and returns `attempt.id` and its stage.
Dispatch one NEW Task for that stage. Pass the bounded inputs and this attempt ID.
The worker can `claim`, or the coordinator can record the actual returned Task
session ID after it returns (never fabricate or reuse one):

```sh
python3 ROOT/tracking/delivery.py claim --key TASK --attempt ATTEMPT --session ACTUAL_WORKER_SESSION_ID
python3 ROOT/tracking/delivery.py finish --key TASK --attempt ATTEMPT --artifact ARTIFACT_URL
```

Execution publishes the existing Verification; review publishes the existing
Review. `finish` fetches and checks these records, the approved plan/contract,
current source and runner evidence. It advances execute → review → publish or
needs_repair/blocked. It records worker sessions so a reviewer cannot be a prior
writer, coordinator or reused reviewer. Session identity recording is an agent
protocol, not cryptographic attestation; the host Task invocation must actually
create the fresh child. Verification never substitutes for independent review.

For required review findings:

```sh
python3 ROOT/tracking/delivery.py repair --key TASK --reason 'Review URL and required finding IDs'
```

For CI failures, first diagnose actual logs/diff and record attribution:

```sh
python3 ROOT/tracking/delivery.py repair --key TASK --attributable --reason 'Check URL, reproduction and why this change caused it'
```

Each successful repair transition consumes one of three persisted repair cycles.
Then begin execute again with the prior review/CI context. Re-review keeps stable
findings and supersedes the previous Review. Three exhausted repairs cannot be
reset by resume. Unrelated infrastructure/baseline failures block instead.

## Git publication and main integration

At publish, inspect status, complete diff and recent log, confirm intended paths
and absence of secrets, and run required repository pre-PR checks. Use the current
verification/review gate; adding changes requires new verification and review.

```sh
python3 ROOT/tracking/delivery.py commit --key TASK --message 'Generated repo-style message' --file path/one --file path/two
python3 ROOT/tracking/delivery.py sync --key TASK
```

Sync fetches origin/main, merges it without rewriting published history, and
returns to execute for integration verification if content/history advanced.
In this integration pass, verify the merged result before editing. Routine merge
and re-verification use no repair cycle. If tests reveal an attributable defect
requiring edits, report the failed evidence to the coordinator before repair;
record it via `integration-failure` then `repair` before changing code.
Use `integration-failure --key TASK --attempt ATTEMPT --artifact FAILED_VERIFICATION_URL`
after the claimed integration worker publishes its failed runner evidence; then
`repair --key TASK --attributable --reason EVIDENCE` authorizes the code correction.
Resolve straightforward conflicts preserving both intended behaviors; product
ambiguity requires a blocker. Resolve an interrupted Git merge before rerunning
sync. Do not stash/drop user edits or use the scheduled checkout-refresh helper.

After any integration pass has new verification and passing review:

```sh
python3 ROOT/tracking/delivery.py publish --key TASK --title 'PR title' --body-file /absolute/reviewed-body.md
python3 ROOT/tracking/delivery.py ci --key TASK
```

Publication checks current review, clean source and main ancestry, pushes without
force, reconciles an existing PR for the exact branch, then creates one only if
no previous create intent is ambiguous. Commit retry inspects current source;
unchanged committed bytes preserve the gate. Hooks run normally.

Poll `ci` every 15–30 seconds while pending, keeping the existing run. Each call
is bounded; on session interruption continue from its journal. If GitHub awaits
external permission, required-workflow rules need unsupported inspection, checks
are unavailable, or unrelated failures prevent green, record a blocker rather
than claiming completion. Skipped/neutral checks do not silently count as pass.
An explicitly observed empty required-check policy can complete with no required
CI; absence of reported jobs under a nonempty policy stays pending.

`ci` binds observations to the current PR head, checks policy for missing required
contexts, refetches main, and reruns the review gate before complete. If main
advanced, run sync and the verification/review/publication loop again. No finite
run can guarantee freshness after its final observation.

## Recovery

```sh
python3 ROOT/tracking/delivery.py block --key TASK --reason 'Evidence and specific unresolved question'
python3 ROOT/tracking/delivery.py resume --key TASK
```

Resume displays the next persisted stage; the receiving `develop-deliver` owner
continues the loop. It does not start another terminal. Revalidate blockers before
resuming; changed plan/contract requires renewed user authorization, not silent
hash refresh. A pending worker intent prevents another begin. Recover its actual
session/result first. Only after confirming the worker stopped may the owner use
`abandon-worker --confirm-worker-stopped --reason EVIDENCE`, then begin a fresh
replacement for that same stage. Preserve the repair count.

An unknown PR-create outcome is reconciled by querying GitHub for the branch;
if still absent, stop for manual reconciliation instead of duplicating creation.
Completion returns the PR, head, final observed main, required checks and repair
count. No automatic merge, issue close, workspace deletion or Done transition.
