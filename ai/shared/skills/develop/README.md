# Develop a feature

Shared methods for a user-driven development cycle. Each stage stops after its
handoff; a prepared plan is not implementation approval.

```text
ticket → research → plan → explicit execution approval → execute → review
                                                          ↑         │
                                                          └─ repair ┘
review pass → separately requested git-commit / git-pr / other git-* skill
```

## Entry points

| Skill / native slash command | Input | Result |
|---|---|---|
| `/develop-feature` | Requested stage, task or exact issue/artifact URLs | One fresh stage worker and its next-action handoff |
| `/develop-ticket` | Explicit request to create/refine a ticket | Scoped issue and versioned contract |
| `/develop-research` | Issue and optional contract URL | Source-bound research facts |
| `/develop-plan` | Issue and exact research URL | Acceptance matrix, steps and check manifest |
| `/develop-execute` | Issue, exact approved plan, optional review URL | Implementation/repair and actual verification receipt |
| `/develop-review` | Issue, exact plan, verification and optional previous review | `pass`, `changes_requested`, or `blocked` |

Skills register their own slash commands. There are no duplicate command files.
Direct stage commands run in the **current session**. For fresh-context execution,
use `/develop-feature plan ISSUE_URL RESEARCH_URL`, for example. Its OpenCode
adapter is one of five thin `develop-*` subagents; methods live here, not in agents.
Each dispatch creates a new worker, including repairs and re-reviews. On a host
without fresh workers, report that limitation and ask for a new session; do not
claim isolation. A reviewer must not review its own implementation context.

`/develop-feature` alone does not authorize issue creation or implementation. Ask
for the next stage when it is ambiguous. Research and planning may publish their
stage artifacts when requested, but an explicit chat-only/no-publication request
takes precedence. Without an issue, scope the request and ask whether to create
one or use an exact existing issue. No URL is fabricated.

## Approval and completion

The plan defines done using stable requirement IDs and:

**scenario/input → observable response → state change/no-change → proving check**.

Every required criterion has actual targeted tests or justified manual evidence.
Required repository checks, prerequisites, source identities, baseline exclusions,
exact affected components and implementation steps are explicit. Optional coverage
does not become a moving completion target. Missing material decisions block execution.

`/develop-execute ISSUE_URL PLAN_URL` (or an equally explicit request through
`develop-feature`) authorizes that identified implementation stage, not Git operations.
Repairs require another explicit execute request with the exact review. There is
**no automatic execute-review-repair loop** and therefore no automatic repair budget.
After two unsuccessful repair rounds against one plan, stop to diagnose the remaining
contract/fixture/evidence problem with the user before accepting another repair.
Record the round and prior review in handoffs so resumption does not reset the count.
Material product questions always stop the stage; no silent scope change is allowed.

Review inspects actual changes before author claims, then verifies source-bound
evidence. Fixes require fresh re-review. `pass` requires every required check and no
unresolved required finding; defects yield `changes_requested`; unavailable decisions
or required proof yield `blocked`. A gate receipt does not replace semantic review.

Verified implementation is distinct from commit, PR, merge and Done. The final
handoff names the applicable existing Git skill and exact evidence, but does not
invoke it automatically. No `develop-commit` or legacy stage aliases are installed.

## Resources and host integration

Read [_lib/workflow.md](_lib/workflow.md) for common rules. Resolve sibling files
from the physical skill directory, not the flattened installation link or cwd.
`_lib/resolve-root.py` locates the tracking integration without a machine-specific
path: inherited `OPENCODE_WORKFLOW_ROOT` wins; otherwise inspect physical ancestors
for the live `opencode/`, relocated `ai/opencode/`, or snapshot root. An invalid
explicit root fails rather than silently mixing resource revisions.

Tracking helpers own JSON formats, GitHub packets/publication, check execution and
content identities. This group owns stage methods. Native tools and model defaults
belong to the host. Private full-stack adapters remain private; cross-repository
acceptance must bind both source trees and external fixture/environment state.

OpenCode snapshots include this entire group, including the library and resolver.
Workers load the pinned skill alias from their agent prompt. Project overrides and
raw-skill fallbacks retain ordinary catalog precedence; they do not replace the
pinned worker method. Custom commands can occupy a skill's slash name; use the
catalog's `/skill-<name>` fallback in that case. Restart after catalog/config edits.

## Provenance

Adapted from the removed workflow at dotfiles `960a611^`, compared with
[`opencode-workflow` at `36ffbd0`](https://github.com/l0lxl0lw/opencode-workflow/tree/36ffbd06acd7a50c89566dd58be2f66e3cf15685).
Preserves its acceptance matrix, explicit execution approval, independent review
and source-bound verification. Retired model profiles and the commit stage are not
restored. Orca supervision remains a separate, explicit workflow.
