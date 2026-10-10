---
name: develop-prepare
description: Prepare a feature or bug fix on main by consolidating clarification, source-backed research, acceptance criteria, ticket and implementation planning. Ends with approval and optional authorized delivery through PR.
---

# Prepare a feature or bug fix

Use the current planning session on `main`. Resolve the physical skill directory,
read `../_lib/workflow.md`, and resolve ROOT with `../_lib/resolve-root.py`.
This is one user-facing preparation stage. Brainstorm with the user here; use
research subagents for evidence, a fresh planning subagent for the draft plan,
and a fresh scoping reviewer only for larger/riskier changes. Read
`../_lib/prepare-workers.md` for the roles, risk triggers and dispatch contract.
Read the internal methods as needed: `../_lib/brainstorm.md`, `../_lib/ticket.md`,
`../_lib/research.md`, and `../_lib/plan.md`. They are references, not additional
public skills or approval gates. Ask only questions that need the user.

## Prepare before publication

1. Verify the repository, branch, current changes, existing issue (if supplied),
   relevant project instructions and issue/Project destinations. On a feature
   branch, ask where to prepare; don't switch or discard work automatically.
   Exploration is read-only. Existing local changes are not part of a new Orca
   worktree; make this explicit in source context and resolve before delivery.
2. Determine feature or bug-fix path. A feature starts with intended capability,
   users, scope and compatibility. A bug starts with actual vs expected behavior,
   reproduction, logs and affected cases. Verify the root cause where possible;
   label hypotheses, missing evidence and inability to reproduce. Skip speculative
   brainstorming when expected behavior is already clear.
3. Delegate focused source investigations to research specialists. Verify decisive
   findings and record source locations and main revision. Use the Superpowers-style
   method in `../_lib/brainstorm.md` here: ask one question at a time, compare
   meaningful alternatives, and review the design in sections. Alternate research
   and discussion when findings change the options; do not outsource the user
   conversation or guess product decisions.
4. Once the design is agreed, dispatch a NEW develop-plan worker. Check its draft
   against the user's decisions. For larger/riskier changes dispatch a separate
   NEW develop-scope-review worker, resolve required findings, and re-review material
   revisions. For small understood changes do the completeness check here. Record
   the scoping-review decision and rationale. Synthesize one preparation result:
   outcome, requirements with stable IDs,
   exclusions, evidence, source refs, exact steps, compatibility/negative cases,
   acceptance matrix and executable check definitions. For bugs, include a
   regression check demonstrating the failure/fix when practical, or a justified
   observable manual check. Material unanswered product questions block delivery.
5. Present that result, then request approval using the popup below. Preserve the
   exact approved result. A source or scope change requiring a materially different
   plan returns to the user, not silent plan replacement.

## Approval popup

Once the preparation is complete and material questions are resolved, summarize
the exact scope, acceptance checks, plan and publication destination in chat.
Then invoke the host's native question tool (OpenCode: `question`) with one
single-select question. Do not merely print a menu or require the user to remember
a command or approval phrase.

- **Header:** `Preparation ready`
- **Question:** `What should I do with this preparation?`
- **Options:**
  - **Publish and deliver through PR** — `Approve this preparation, publish the
    ticket and plan, then hand off to an Orca feature workspace for implementation,
    independent review, up to three repair cycles, commits, PR and required CI.
    Includes merging updates from main; does not merge the PR.`
  - **Publish only** — `Approve and publish the ticket and plan, then stop before
    implementation.`
  - **Keep refining** — `Continue discussing or revising the preparation without
    publishing or starting delivery.`

The first selection is explicit publication and through-PR authorization for
the preparation just shown. Publish it and load `develop-deliver` immediately;
do not ask for another routine confirmation. The second authorizes publication
only. The third authorizes neither: ask what needs changing, refine, and offer
the popup again when ready. A dismissed/unanswered popup grants no authorization.
Custom answers are valid; clarify ambiguous intent instead of mapping it to the
first option. Preserve any restrictions the user adds.

An already explicit **"Approved—publish and deliver through PR"** response for
the exact current preparation is equally valid; don't show a redundant popup.
On hosts without a question tool, ask the same single-choice question in chat
and wait. Do not offer delivery while material product decisions remain open.

## Publish the approved result

Use ROOT/tracking/references/records.md and ROOT/schemas examples. Create a new
issue only in the confirmed repository, assigned to the authenticated user; use
the exact existing issue for an approved update. Preserve human text. Project
setup and Orca linking remain independent outcomes; report partial failures.

Publish the existing v2 artifact types in dependency order, without asking for
four approvals: contract → research → plan. Reconcile the issue checkpoint before
publishing the contract, use actual source hashes, and use returned revisions/URLs
in dependent records. Supersede exact earlier artifacts when applicable. The plan
must include acceptance_matrix and coverage/check_manifest per the existing plan
method. Read-only preparation does not create `.opencode/workflow/checks.json`.

On partial publication, inspect existing issue/comments and reuse matching
records. Never create another issue because a comment or Project update failed.
Return issue and exact plan URL, plus any unresolved publication outcome.

## Transition

If the user approved **deliver through PR** for this preparation, load
`develop-deliver` immediately with the exact published issue/plan and authorization.
No second execution, commit-message or PR-creation confirmation is needed.
Otherwise stop with the published plan and the suggested deliver invocation.
Do not start an agent just because the ticket exists or the plan is Ready.

Prepare also handles targeted design/research/plan revisions when asked. Only
Prepare and Deliver are public development commands; supporting methods live
under `_lib`. Research specialists, the planner and conditional scoping reviewer
are internal workers; execution and mandatory independent code review remain
separate workers in the delivery workspace.
