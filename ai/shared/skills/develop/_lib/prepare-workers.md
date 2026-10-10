# Prepare: main-session brainstorming with research and planning workers

This method is part of `develop-prepare`. Its invocation authorizes these
read-only delegations, not implementation or publication. All preparation uses
the same main checkout. Do not create an Orca workspace until approved delivery.

## Main-session owner

Keep the user conversation here. Follow [brainstorm.md](brainstorm.md): discover
intent, ask one focused question at a time, reflect answers, compare meaningful
approaches and review the design in understandable sections. For bugs establish
actual vs expected behavior and root-cause confidence rather than force feature
brainstorming. Subagents supply evidence and challenges; they do not replace this
conversation or make product decisions. Incorporate the user's answers before
asking again. Agreement on design sections does not authorize publication.

## Research alongside brainstorming

Delegate concrete technical unknowns to the existing research specialists:

| Internal agent | Assignment |
|---|---|
| codebase-locator | Relevant entry points, implementation/store/schema and tests |
| codebase-analyzer | Runtime/data flow, ownership, error behavior and invariants |
| codebase-pattern-finder | Close implementation and meaningful test analogues |
| web-search-researcher | Specific external API/dependency question using primary documentation |
| thoughts-locator | Relevant historical decisions in an identified document area |
| thoughts-analyzer | Decisions and contradictions in explicitly supplied historical artifacts |

Use only roles that answer real questions; no mandatory six-agent checklist.
Independent investigations can run in parallel. Dependent analysis waits for the
locator/findings it needs. Avoid duplicating an active worker's investigation in
the parent. Read decisive returned source ranges to verify conclusions and resolve
contradictions. Return new uncertainties to research or the user as appropriate.

Require findings with paths/lines, current main revision, affected callers and
contracts, relevant failure cases, test gaps, compatibility/data assumptions,
and explicit uncertainty. For bugs distinguish demonstrated cause from a
hypothesis and identify the regression check. The owner may run focused baseline
commands where useful, passing actual results back; read-only specialists must
not invent executions. Research can change the options under discussion, so do
not freeze the design before investigating material constraints.

## Fresh planning worker

Once the design is agreed and material questions are settled, dispatch a NEW Task
with subagent_type **develop-plan**. Pass the complete agreed requirements/design,
reconciled source-backed research, source revision, exclusions and acceptance
expectations. The planner follows [plan.md](plan.md), independently spot-checks
critical references and returns a draft implementation plan/check manifest.
It does not publish a ticket or ask its own user questions. An unpublished task
does not need an issue or artifact URLs to be planned.

The owner checks that the draft preserves user choices, covers every requirement
and makes no unsupported assumptions. Resolve discrepancies before approval.
Targeted follow-ups get a fresh worker and just the necessary prior draft/evidence;
do not restart all research or forward the planner's reasoning transcript.

## Conditional scoping review

Assess risk after initial scope and revisit it when research/planning changes the
picture. Record the reason in the preparation summary. Use a NEW Task with
subagent_type **develop-scope-review** for a larger or riskier change, including:

- Multiple interacting subsystems or public API/contract changes.
- Authentication/authorization, sensitive data or financial behavior.
- Database migrations, concurrency, retries or destructive operations.
- Significant uncertainty about root cause, design or compatibility.

A small, well-understood change with none of these characteristics needs the
owner's completeness check, not an extra scoping-review worker. A user can also
explicitly request review. Do not classify by line count alone or omit the
review just to save a turn when a substantive risk is present.

The scoping reviewer is independent of the planner/researchers and follows
[scope-review.md](scope-review.md). Pass requirements, agreed design, evidence,
draft plan and the risk rationale—not author reasoning or assurances of quality.
Resolve concrete findings through targeted research, user clarification and/or
fresh planning. Re-review substantive revisions in a fresh scoping context before
presenting the final approval popup. If resolution requires a missing product
decision, ask the user rather than endlessly cycling or expanding scope silently.

This assesses whether the design/plan is sufficient. It is not a v2 implementation
Review, does not need implementation Verification, and does not consume Deliver's
three-repair budget. Record the result in the preparation/plan narrative; do not
fabricate a passing code-review record. Independent **code review remains
mandatory on every delivery**, regardless of preparation risk.

## Worker brief and fallback

Use fresh Task sessions with the literal agent identifiers above, not snapshot
skill aliases. Provide the exact pinned method/helper root, repository/checkout,
main revision, task kind, agreed
decisions, precise question, relevant file/artifact references and the desired
output. Include draft-only boundaries: no edits, publication, Git mutations or
direct user dialogue. Workers return questions to the owner and cannot delegate
further. Preserve required context but do not copy the entire conversation.

If a needed agent is unavailable, report it and ask how to proceed. Do not
silently claim the parent did fresh-subagent work. All user-facing clarification,
final synthesis, approval and post-approval ticket/plan publication belong to
the main-session owner. Prepare and Deliver remain the only public commands.
