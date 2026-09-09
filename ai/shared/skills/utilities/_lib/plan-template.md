# Cold-Session Plan Template

This is shared prose, not an entry skill or a backend schema. Adapt the depth to
the task, but retain the approval boundary and verification/authorization details.
Replace placeholders with inspected facts; mark unresolved requirements explicitly.

## Identity And Context

- Canonical path: `~/.agents/plans/<project>/<task>/plan.md` (also give absolute path).
- Repository root, branch/revision, staged/unstaged/untracked baseline and relevant
  fingerprints; preserve existing work and name any overlap.
- Problem, user-visible outcome, constraints, source files/docs/tests inspected,
  and the current behavior/contracts that drive the design.
- Approval: this file is a draft until explicitly approved. Record user approval
  provenance and the hash of these exact bytes in adjacent `progress.md` afterward.

## Decisions And Boundaries

Chosen approach and rationale; meaningful alternatives and why rejected. Scope,
explicit exclusions, assumptions, risks, and material-drift stop conditions.
Document important decisions without referring to the planning conversation.

List every likely generated or incidental output from planned commands (for example,
API collections/clients, snapshots, lockfiles, migrations, fixtures, and formatting).
For each material output, state its expected paths and the explicit decision: accept
the scoped update, use a pinned/configured command that prevents it, or prohibit the
producing command. A generic test/generation authorization is not approval for broad
unrelated churn. The plan is not ready for approval if implementation would need to
ask whether to accept, suppress, or reconfigure an expected output.

## Acceptance And Proof

Create stable IDs early and retain them across revisions. Repeat for each AC:

### AC-01: <Observable Requirement>

- Scenario: given <state/fixture>, when <action>, then <observable result>.
- Include relevant success, negative, boundary, and failure cases, not arbitrary
  case counts. Name exact fixture/input identities and expected outputs.
- Prerequisites: environment, services, data, credentials by reference (no secrets),
  versions, and read-only availability checks. State what blocks execution.
- Non-vacuity: how to prove the intended cases/data/path actually executed (e.g.
  nonzero selected tests, expected records, exercised branch or received request).
- Cheap proof: exact command, cwd, assertions and expected observations.
- Real proof: exact integration/end-to-end command and target with assertions;
  if not applicable, explain why the cheap proof is sufficient for this requirement.
- Proof limits: what this does not prove; explicitly separate exclusions from
  required proofs that are currently blocked.

## Implementation Units

For each coherent unit: AC IDs, repository-relative files to change and why,
dependencies/order, important interface details, and targeted checks. Keep tightly
coupled work together. Mark an independent delegation candidate only if useful;
inline implementation is the default. Include docs and risk-based review needs.

## Execution Authorization And Limits

- Exact commands/cwd and target environment identity. Enumerate effects, not just
  verbs: allowed file paths, service lifecycle, database/schema/rows, fixture writes,
  network destinations, external resources, costs, and cleanup/recovery actions.
  State forbidden targets/effects. A generic "run tests" is not blanket permission.
- Specify setup and cleanup authorization separately; never assume production,
  destructive reset, deployment, git mutation, or live sync is allowed.
- Cheap-test ladder and prerequisites before expensive runs. Set concrete maximum
  attempts (including retries), duration/timeouts, and applicable cost/resource
  budgets for expensive commands. Define success, abort, and cleanup observations.
- Repairs stay in scope. Two distinct ineffective fixes for the same failure,
  budget exhaustion, or material drift stops execution for a user decision.

## Local Adapter Contract (When Applicable)

Record the discovered repository-local `ADAPTER.md` path and contract version or
fingerprint. Read it and insert its required **fenced machine contract block** here
with all required fields filled according to that local schema. Do not copy a
schema from this global template, invent fields, or leave this placeholder in a
plan claiming adapter readiness. Verify agreement between prose, block, ACs, and
authorized effects before presenting for approval.

## Evidence And Cold Handoff

Use adjacent `progress.md` for approval provenance/hash, unit checklist, tested
revision plus dirty-input identity, command/environment/fixture outcomes, durable
logs/artifacts, budget/repair history, and per-AC verified/failed/blocked status.
Keep explicit exclusions separate; do not use "not-run" as an evidence status.
Record required unexecuted checks as blocked with reasons. No secrets in artifacts.

Final approval covers this exact plan and its exact effects, not future expansions.
After approval the planner stops. Start a cold session with
`implement-plan <absolute-plan-path>`; native plan/clear tools are optional.
