---
name: develop-prepare
description: Prepare a feature or bug fix on main by consolidating clarification, source-backed research, acceptance criteria, ticket and implementation planning. Ends with approval and optional authorized delivery through PR.
---

# Prepare a feature or bug fix

Use the current planning session on `main`. Resolve the physical skill directory,
read `../_lib/workflow.md`, and resolve ROOT with `../_lib/resolve-root.py`.
This is one user-facing preparation stage. Do the work here; don't dispatch the
individual stage workers or stop between brainstorming, research and planning.
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
3. Inspect real entry points, implementations and relevant tests. Record concrete
   source locations and the main revision. Alternate research and clarification
   when findings change the design; no ceremonial four-stage handoff.
4. Draft one coherent preparation result: outcome, requirements with stable IDs,
   exclusions, evidence, source refs, exact steps, compatibility/negative cases,
   acceptance matrix and executable check definitions. For bugs, include a
   regression check demonstrating the failure/fix when practical, or a justified
   observable manual check. Material unanswered product questions block delivery.
5. Present that result for approval. Approval authorizes ticket/plan publication;
   it does not by itself authorize code changes. The combined response
   **"Approved—publish and deliver through PR"** grants both. Preserve the exact
   approved result. A source or scope change requiring a materially different plan
   returns to the user, not silent plan replacement.

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
under `_lib`, and execution/review are internal Task workers.
