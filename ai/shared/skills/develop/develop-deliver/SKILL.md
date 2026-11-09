---
name: develop-deliver
description: Deliver an explicitly approved feature or bug-fix plan through an Orca feature workspace, fresh execution/review workers, at most three repairs, commit, push, PR and green required CI with main integrated. Supports resuming the same delivery.
---

# Deliver the approved plan through PR

If the exact issue/plan or through-PR approval is missing, ask for that input
before running helpers or dispatching a worker. No delivery authorization can be
inferred from an unspecified request to develop a feature.

Resolve this skill's physical directory and ROOT with `../_lib/resolve-root.py`.
Read `../_lib/workflow.md` and ROOT/tracking/references/delivery.md. The latter is
the executable protocol; use its helper rather than inventing state commands.

## Dispatcher in main

Require the exact issue/plan and explicit **deliver through PR** authorization.
An approved preparation with **publish and deliver through PR** supplies it.
Initialize one delivery journal, then dispatch through the physical `orca-handoff`
helper using the delivery helper's `dispatch` action. The receiver is the
same CLI you dispatch from (Claude Code or Codex) unless the user asks
for another via `dispatch --agent`. Wait for the receiving workflow's
acknowledgement using `wait-start`. The old Orca accepted receipt alone
does not prove startup. Report the workspace, key and startup status, then stop.
The receiving workspace owns delivery; do not supervise its completion from main.

Initial delivery requires a clean main checkout and local Orca with the same
filesystem/state directory. Do not publish unrelated planning-checkout edits to
satisfy this prerequisite. Remote execution without shared state is unsupported
and must report that limitation before launching anything.

## Receiver in the feature workspace

The brief provides the exact pinned protocol/helper paths, key, state directory,
approved plan and authorization. Read them even if the receiver launcher has an
older catalog. Acknowledge the run from the exact created workspace using the
actual receiving session ID for your host (`_lib/workflow.md` Hosts). Inspect or
resume its journal and reconcile current Git, artifact and PR state; never
initialize or redispatch from the receiver.

Own the full delivery loop:

1. Sync main at entry. Begin an execution attempt and dispatch a NEW worker
   named develop-execute with the exact plan, key, helper path, acceptance scope,
   and repair findings when relevant. Include delivery authorization and budget.
   Record the real worker session ID and its published verification result.
2. Begin review and dispatch a NEW worker named develop-review with the exact
   plan and verification plus the previous review for re-review. Do not pass the
   execution transcript/reasoning. Worker writes must have stopped. Reviewers do
   not change application code. Record their actual session ID and Review URL.
3. A passing review permits publication. Required findings permit one repair
   cycle, then fresh verification and another independent review. Budget is three
   repairs total across review and attributable CI/integration failures. Initial
   execution/review and routine main integration do not consume repairs.
4. Inspect the complete diff/status and recent commit style. Use the journal's
   gated commit command with explicit reviewed paths and a generated message.
   Sync main before publication; if integrated content changed, get updated
   verification and fresh independent review. Publish a non-draft PR with a
   description of the full branch diff and issue-closing reference. Preserve hooks
   and repository-declared checks; don't amend, force-push or change Git config.
5. Observe required CI on the current head. Pending/missing checks mean wait, not
   success. Diagnose failures: changes caused by this work can use the remaining
   repair budget; unrelated failures, missing access, product decisions or scope
   changes become explicit blockers. Every CI repair gets verification and fresh
   review before commit/push. A failure during integration requiring code changes
   also consumes a repair cycle, with evidence of attribution.
6. Before success, fetch main again, integrate if needed, reverify/review/push and
   wait for current-head CI again. Complete only when the helper records complete.
   Report PR URL, current head, final observed main, checks and repair count. Keep
   tracking In review: an open PR is not merged/Done.

Pause only for a real blocker. Record it before asking the user, with exact
recovery references and remaining budget. Do not reset budget by starting a new
key or silently lower required coverage. Source/plan changes invalidate stale
evidence. On interruption, inspect the same journal; reconcile a pending worker
before starting a replacement. Missing worker identity is a blocker, not proof
that no worker ran.

## Continue in another tool

A delivery belongs to its journal and workspace, not to one CLI. When the owning
session runs out or stops, open the same Orca feature workspace in
Claude Code or Codex and invoke develop-deliver there to resume:

1. Run `python3 ROOT/tracking/delivery.py locate` from the workspace. It lists
   the key, stage and the exact pinned helper to use for every following call.
2. Confirm the previous coordinator has really stopped (its terminal is closed or
   idle and is no longer running a turn). Two owners would race on the journal.
3. Run `adopt --key KEY --session YOUR_SESSION_ID --confirm-previous-owner-stopped
   --reason WHY` with the pinned helper, then `inspect`.
4. Reconcile any pending worker attempt exactly as after an interruption, then
   continue the loop from the recorded stage. The repair budget, evidence and
   worker independence carry over; nothing is redispatched.

This skill authorizes the coordinator to dispatch successive fresh execution and
review workers within the recorded run. Individual workers read `_lib/execute.md`
and `_lib/review.md`, return one stage result and stop. They are agent identifiers,
not public slash commands. Prepare and Deliver are the only public entry points.
