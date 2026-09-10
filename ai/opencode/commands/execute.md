---
description: Implement the identified GitHub issue plan and report verification.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Issue and optional exact plan URL: $ARGUMENTS

Read the issue and all comments. Identify the current plan; ask if ambiguous or
requirements invalidate it. This command authorizes implementing that plan.
Confirm the correct repository and isolated feature branch/worktree; establish one
under repository conventions if needed. Register the branch and refresh freshness.
If Needs sync, ask whether to run the explicit sync workflow before proceeding.
Set Implementing and post a start comment linking the exact plan and branch.
Implement the plan, verify actual acceptance criteria, and report material blockers.
Post completion/progress with changes, tests and remaining manual checks. Keep
Implementing until a requested PR is ready for review. Use existing git skills
only when the user requests commits/PRs; after PR publication update the project
and link the PR. Do not mark Done merely because local implementation is complete.
