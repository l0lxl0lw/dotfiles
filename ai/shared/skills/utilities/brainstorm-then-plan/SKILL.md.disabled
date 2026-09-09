---
name: brainstorm-then-plan
description: Discover context, settle important decisions, and write a standalone plan for one final approval, then stop. Use for "brainstorm then plan", "plan this change", or a cold-session handoff to implement-plan.
disable-model-invocation: true
---

# Brainstorm, Then Plan

Produce an approved plan, not an implementation. This workflow works in Claude,
Codex, Grok, and OpenCode without plugins or native plan tools. Use the available
read, search, question, and file-edit tools.
Native plan mode is optional and must not auto-start implementation on approval.

Read `../_lib/plan-template.md` and `../_lib/verification-contract.md` relative to
this skill's resolved source directory (resolve the skill symlink first, not the
shell working directory). If unavailable, report the missing reference, not an
invented replacement contract.

## Ask Through The Question UI

For every discovery question and final approval, use the harness's interactive
question tool when available: OpenCode `question`, Claude `AskUserQuestion`, or the
equivalent exposed by the current host. This is required, not a stylistic choice.
The registered OpenCode fresh-handoff popup below replaces only final approval.
Do not print a numbered menu or end a chat message with a question and wait for
typed input when the question tool is available.

Send one question per tool call. Offer concise, meaningful selectable options with
short explanations; put the recommended option first and label it Recommended.
Allow a custom answer using the tool's built-in facility when supported. Do not
invent choices for genuinely open-ended input. Explain necessary context briefly
in chat, then invoke the question tool in the same turn and wait for its answer.
Use plain-text questions only if no interactive question tool is exposed or it
explicitly reports that it is unavailable; explain that fallback briefly.

## Discover Before Asking

1. Inspect repository instructions, status (staged, unstaged, and untracked),
   relevant docs, entry points, callers, tests, and environment/verification
   scripts. Preserve others' work. Record the repo root, revision, dirty baseline,
   and the specific sources supporting the design. Graphs may locate code but
   current files are authoritative. No implementation or setup side effects.
2. Identify the user-visible goal, constraints, exclusions, and risks. Draft
   stable acceptance IDs (`AC-01`, etc.) early, with concrete scenarios and
   observable outcomes; use them to expose missing decisions, not as a final
   paperwork step. Read the verification contract before promising any proof.
3. Use the question UI to ask **one question at a time**, only for an unresolved important decision that
    inspection cannot answer: behavior, scope, tradeoff, authorization, or a
    prerequisite that changes feasibility. Do not ask users to recite discoverable
    facts or choose a planner/model. State safe, low-impact assumptions in the plan.
    Treat a decision as important if implementation would have to stop to obtain it;
    do not defer it to the implementer. In particular, inspect the tools and scripts
    the plan will run for likely generated or side-effect output: API collections or
    clients, snapshots, lockfiles, schema/migration files, fixtures, and formatted
    files. Resolve each material outcome before approval: authorize its specific
    scope, choose a pinned/configured invocation that prevents it, or exclude the
    invocation that produces it. Do not hide broad generated churn behind a generic
    authorization to run tests or generation.
4. Match depth to uncertainty and risk. A small fix needs a short grounded plan;
   a cross-system change needs boundaries, failure paths, and migration/recovery
   detail. Compare meaningful viable alternatives with tradeoffs and a recommended
   choice when there is a real choice. Include doing nothing when viable; do not
   manufacture alternatives or impose design-review approval rounds.

## Make The Plan Executable

Write the standalone plan using the template at the explicit canonical path
`~/.agents/plans/<project>/<task>/plan.md`. Choose unambiguous filesystem-safe
project/task names; do not overwrite an unrelated plan. Resolve and display the
absolute path. The cold reader must not need the brainstorming transcript.

- Name affected files, coherent implementation units and their dependencies,
  decisions and rejected alternatives, non-goals, and relevant current contracts.
- For every AC, specify scenarios, fixtures, prerequisites, non-vacuity checks,
  a cheap proof and the necessary real-system proof (or justified non-applicability),
  expected observations, and what the proof explicitly does not establish.
- Specify exact commands, working directories, environment identity, authorized
  effects and targets, cleanup, time/cost/attempt limits, and stop conditions.
  Missing infrastructure is a stated blocker, never implicit permission to create it.
- Discover repository-local `ADAPTER.md` (including the local verification skill
  directory). If applicable, read it and include its required fenced machine
  contract block, using its schema and validation instructions. The shared
  template is not a backend schema. If that contract is absent or ambiguous,
  do not guess fields or promise an adapter run; resolve the blocker before
  approval if that run is required. See the shared verification contract.
- Self-check traceability from AC to step to proof and the ability to resume from
  `progress.md`. Use review only where risk warrants it, with available tools;
  no mandatory reviewer loop, delegation, worktree, or commit.
- Complete a **handoff-readiness gate before presenting final approval**. Check every
  implementation step, effectful command, likely generated output, required proof,
  prerequisite, and material-drift stop condition. The plan must say whether it is
  authorized, prohibited, non-applicable, or already resolved by an explicit user
  decision. If any item would require the implementer to ask "accept this output,
  change the command/version, or stop?", it is unresolved: ask that one question
  now through the question UI and revise the plan. Do not offer final approval while
  required work is knowingly blocked by an undecided policy, tool/version, access,
  fixture, or contract.

## One Final Approval, Then Stop

### OpenCode Native Fresh Handoff (Only When Registered)

If the current OpenCode tool catalog actually exposes `prepare_plan_handoff`,
only call it after the handoff-readiness gate passes. Present the completed plan,
absolute path, material effects, verification budget, exclusions and blockers, then
call that tool with `planPath` and an `effects` summary containing those disclosures.
Do not request final approval separately:
the local TUI popup is the ONE final approval of both the exact plan and starting
implementation in a fresh session. Never simulate the tool using shell commands,
socket messages, or invented tool names.

On successful preparation, **STOP this turn immediately**, with no more tools,
approval questions, or implementation. Preparation is not approval. After this
source is idle, the TUI checks the plan again, presents the popup, and only on
Confirm records approval provenance and the exact SHA-256 in `progress.md`, then
uses the native new-session prompt to submit `/implement-plan <absolute-path>`.
The implementation runs in that fresh session, never in the brainstorming turn.
Cancel, missing UI, changed files, stale source, or failed prerequisites start
nothing automatically. Do not retry preparation automatically. If preparation
reports unavailable/failure, explain that and use the manual workflow below.
If the user returns after cancellation with edits, revise before preparing again.

This exception requires the real registered tool and successful local TUI
preparation. It does not authorize workers, forks, compaction, transcript copying,
or automatic git operations. Other harnesses and installations without the tool
retain the manual approval-and-stop behavior below unchanged.

### Manual Approval And Handoff

Only after the handoff-readiness gate passes, present the completed plan, its exact
path, key tradeoffs, exact authorized effects, verification budget, and any
exclusions/blockers. Request one final plan approval through the question UI with
explicit Approve and Request Changes options. Approval
authorizes this plan and its stated effects, not immediate implementation here.
Clarification answers, silence, a tool exit, or your own recommendation are not
approval. If the user requests edits, revise before seeking final approval again.

Only after explicit user approval, record the approval provenance and SHA-256 of
the exact approved `plan.md` bytes in adjacent `progress.md`, not by mutating the
approved plan. Do not manufacture approval for a draft or claim a hash is a user
decision. Preserve that immutable snapshot; material revisions need new approval.

Then **STOP**. Return the absolute plan path and this handoff:

> Start a fresh/cleared session, then invoke `implement-plan <absolute-plan-path>`.

Use the harness's new-session/clear mechanism if available; `/clear` is not a
portable requirement. Do not implement, launch a worker to implement, or continue
automatically. No automatic git operations (including staging, commits, branch or
worktree creation, pulls, or pushes); read-only git inspection is allowed.
