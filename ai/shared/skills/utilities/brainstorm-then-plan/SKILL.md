---
name: brainstorm-then-plan
description: Discover context, settle important decisions, and write a standalone plan for one final approval, then stop. Use for "brainstorm then plan", "plan this change", or a cold-session handoff to implement-plan.
disable-model-invocation: true
---

# Brainstorm, Then Plan

Produce an approved plan, not an implementation. This workflow works in Claude,
Codex, Grok, and OpenCode without plugins or native plan tools. Use the available
read, search, question, and file-edit tools; a plain chat question is sufficient.
Native plan mode is optional and must not auto-start implementation on approval.

Read `../_lib/plan-template.md` and `../_lib/verification-contract.md` relative to
this skill's resolved source directory (resolve the skill symlink first, not the
shell working directory). If unavailable, report the missing reference, not an
invented replacement contract.

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
3. Ask **one question at a time**, only for an unresolved important decision that
   inspection cannot answer: behavior, scope, tradeoff, authorization, or a
   prerequisite that changes feasibility. Do not ask users to recite discoverable
   facts or choose a planner/model. State safe, low-impact assumptions in the plan.
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

## One Final Approval, Then Stop

Present the completed plan, its exact path, key tradeoffs, exact authorized effects,
verification budget, and any exclusions/blockers. Ask for one final plan approval.
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
