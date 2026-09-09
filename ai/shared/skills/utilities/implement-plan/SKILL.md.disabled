---
name: implement-plan
description: Implement an explicitly approved plan in a fresh session using its path, bounded verification, and durable evidence. Use for "implement-plan <path>", "build the approved plan", or "implement the plan file".
disable-model-invocation: true
---

# Implement An Approved Plan

Build the approved scope, not a new design. Works in Claude, Codex, Grok, and
OpenCode with their available tools. Medium effort is the default recommendation;
Sonnet is a cost hint if available and suitable, not a model requirement or an
instruction to switch models. Do not require native planning or delegation tools.

Read `../_lib/verification-contract.md` relative to this skill's resolved source
directory (resolve symlinks first). The plan and adjacent `progress.md` carry the
cold-session context; do not reconstruct the brainstorming conversation.

## Re-enter Safely

1. Require an explicit plan path, normally
   `~/.agents/plans/<project>/<task>/plan.md`. If omitted, ask for it; do not select
   the newest plan. Read the full plan and existing `progress.md`.
2. Verify explicit user approval provenance and the exact approved plan hash.
   If missing or mismatched, stop and ask for approval of the actual plan; a file
   named plan.md, an invocation, or an adapter token is not proof of approval.
3. Inspect repository instructions, revision, staged/unstaged/untracked status,
   and the relevant diff against the plan baseline. Preserve unrelated work.
   Re-read affected files, callers, tests, and local `ADAPTER.md` selectively to
   check assumptions. Avoid whole-repo rediscovery and ritual rereads; re-read
   when edits, concurrent changes, stale context, or failures make it necessary.
4. Do not relitigate settled scope. For material drift (changed behavior/contract,
    conflicting edits, missing required prerequisites, newly unsafe effects, or
    invalid design), record evidence and stop with the smallest decision needed.
    Harmless line shifts are not material drift. Never silently widen approval.
    Unexpected broad generated output is material drift unless the approved plan
    explicitly authorizes those paths and output class. Do not accept it merely
    because a planned command produced it. This should be rare: a handoff-ready plan
    has already resolved the expected-output policy before implementation starts.

## Implement And Verify

Turn the plan's coherent units into a small checklist in `progress.md`. Implement
inline by default with focused edits using the harness's supported editing tools.
Delegate selectively only when an available tool can assign a coherent independent
unit with clear files, inputs, acceptance IDs, proof, and non-overlapping ownership.
Keep dependent or tightly coupled work together. Integrate and verify delegated
results yourself; a worker's completion claim is not evidence. No mandatory
subagents, reviewer loops, worktrees, or commits.

Follow the shared verification contract's cheap-test ladder and approved limits.
Run targeted checks as units land; run expensive checks only after cheap gates and
prerequisites pass. Repair only defects within approved scope. Each repair needs
a concrete hypothesis and the smallest discriminating check. After **two distinct
ineffective fixes for the same failure**, stop and record the attempts and blocker;
do not reset the counter by renaming the failure or delegating it. Stop earlier on
budget exhaustion, unsafe effects, or material drift. Never blindly rerun expensive
tests or substitute mocks for required real proof.

If a local adapter applies, read its `ADAPTER.md`, validate the approved plan block,
and follow the shared adapter procedure. Exact effects already approved in the plan
are sufficient authorization for the matching local adapter run; no redundant
confirmation ritual. Tool permissions still apply. Changed effects need approval.

Review proportionally to risk: inspect the final diff for AC coverage, regressions,
error paths, scope creep, and accidental edits. Seek focused independent review for
high-risk changes if useful and available; otherwise do a targeted self-review and
state the limitation. Reviews do not replace tests or force a repeated review loop.

## Durable Evidence And Handoff

Update adjacent `progress.md` after each unit, verification run, failure/repair,
and before a pause. Preserve the approval record and prior evidence; record:

- Plan path/hash, approval provenance, repository root, baseline and tested revision,
  staged/unstaged/untracked state, and diff/content fingerprints for dirty inputs.
- Completed/remaining units, changed files, AC IDs, decisions within approved scope,
  and targeted rereads/drift findings.
- Exact command and cwd, time, environment/tool versions and fixture identity,
  exit status and relevant observations, durable artifact/log paths, effects and
  cleanup outcome, attempt/budget usage, and evidence invalidated by later changes.
- Per-AC and per-proof outcomes: **verified**, **failed**, or **blocked**, with reasons
  and proof limits. Exclusions live separately. Unexecuted work is not a success;
  required unexecuted proof is blocked, with the reason it was not run.

If pausing, hand off the explicit plan and progress paths. Resume by checking drift
and evidence applicability, not by repeating completed expensive runs. Never edit
the approved plan merely to match the implementation.

Finish with changes, verified/failed/blocked ACs, evidence paths, exclusions and
remaining decisions. Claim completion only when all required AC proofs are current
and verified. No automatic git operations (including staging, commits, branches,
worktrees, pulls, pushes), deployment, uninstall, or live synchronization. Read-only
git inspection is allowed; other effects must be explicitly authorized in the plan
and allowed by the available tools.
