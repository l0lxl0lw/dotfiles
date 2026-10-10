# Prepare and deliver features or bug fixes

Two public entry points:

| Command | Where | Result |
|---|---|---|
| `/develop-prepare` | Planning session on main | Approved scope, research, ticket, acceptance checks and implementation plan |
| `/develop-deliver` | Dispatch from main; execution in an Orca feature workspace | Reviewed implementation, commits and an open PR with required CI green |

```text
main: Prepare → approve publication and delivery
                     ↓ Orca handoff + receiver acknowledgement
feature: Execute → Verify → Independent review ↔ Repair
         → Commit → Push → Ready PR → Required CI green
```

## Prepare

Prepare consolidates clarification, source research, ticket/contract and planning
in one session. It supports features and bug fixes: bug preparation investigates
actual/expected behavior, reproduction, root-cause evidence or explicit uncertainty,
and regression checks. Ask only questions that require user input.

The reviewed preparation result contains stable requirement IDs and acceptance
rows: scenario/input → response → state change/no-change → proving checks. Required
checks, meaningful negatives, environment prerequisites and manual evidence are
explicit. A prepared plan does not by itself authorize implementation.

Approve the result to publish the issue/contract/research/plan. Existing issue URLs
are preserved. Issue repository and Project board are separate destinations; no
configuration field is invented to infer one from the other. Partial publication
is reconciled without duplicating issues or losing human edits.

**"Approved—publish and deliver through PR"** grants both publication and the
delivery run for that exact plan. Otherwise Prepare stops with the published plan.
Targeted research/design/plan revisions also use Prepare; no additional public
stage commands or handwritten `/brainstorm` alias are installed.

## Deliver

The main session initializes one private journal and dispatches through the Orca
handoff helper. It waits only for the receiving workflow's acknowledgement, then
releases ownership. The feature workspace owns the rest of the run. Local Orca
and a shared local filesystem/state directory are currently required.

The owner dispatches NEW internal `develop-execute` and `develop-review` Task
workers. The reviewer must be independent of the writer and coordinator. Workers
load the internal methods directly, return one evidence artifact and stop. They
are not slash commands. Review reads actual code before author claims and uses
source-bound verification; schema validity alone is not semantic correctness.

There are **three repair cycles total**, shared by review and attributable CI or
integration defects. Initial implementation/review and routine main integration
do not count. Each repair has fresh verification and independent review before
push. Missing product decisions, changed scope, unrelated failures or exhausted
repairs stop with a resumable blocker, not silently relaxed acceptance.

Git operations use the initial through-PR approval: generate repo-style messages,
commit only reviewed files, push without force, and create a non-draft PR. Fetch
origin/main before publication and final completion; merge newer commits into the
feature branch, resolve straightforward conflicts and reverify/review integrated
changes. Product-ambiguous conflicts need user input. Never modify the main
checkout as part of delivery.

Completion requires current-head required CI, passing independent review and the
latest observed main integrated. It returns the PR URL, head, observed main,
checks and repair count. It does not merge the PR, close the issue or mark Done.

## Internal layout and recovery

- `develop-prepare/SKILL.md` and `develop-deliver/SKILL.md`: public commands.
- `_lib/brainstorm.md`, `ticket.md`, `research.md`, `plan.md`: preparation methods.
- `_lib/execute.md`, `review.md`: methods for the two internal workers.
- `_lib/workflow.md`, `resolve-root.py`: shared contract and physical integration
  resolution; pinned snapshots retain their exact resource revision.

See the [delivery protocol](../../../opencode/tracking/references/delivery.md)
for journal commands, receiver acknowledgement, worker identities, Git/CI gates
and interruption recovery. Unknown send/worker/PR outcomes are reconciled using
the existing key rather than duplicated. Existing standalone Git skills remain
available outside a delivery run.

OpenCode loads methods and sibling resources into immutable snapshots. Restart
through the normal launcher to sync the new catalog and remove old managed links.
The retired standalone development skills and `/brainstorm` alias are not needed.

## Provenance

The internal methods preserve the acceptance, independent review and source-bound
verification approach adapted from dotfiles `960a611^` and
[`opencode-workflow` at `36ffbd0`](https://github.com/l0lxl0lw/opencode-workflow/tree/36ffbd06acd7a50c89566dd58be2f66e3cf15685).
Clarification is adapted from Superpowers commit
`8ca22dba9a94f28898bbce59f2537ff4d87c747d`; its [source record](_lib/sources.md)
and [MIT license](_lib/LICENSE.superpowers) are retained with the internal method.
