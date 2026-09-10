---
description: Create or refine a GitHub issue ticket and add it to Azu's Tasks.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Input: $ARGUMENTS

Resolve the repository and whether this is a new ticket or an existing issue.
For new tickets, clarify missing requirements that materially affect scope, then
create a repository issue with `gh issue create --body-file ...`. Include problem,
desired outcome, scope, acceptance criteria, and known dependencies. Add the issue
to the configured project with the helper, set Status to Backlog and use
`sync-state ISSUE 'Not started'` for this unregistered item.
For existing tickets, read body and comments, preserve useful content, and refine
requirements using `gh issue edit --body-file ...`; do not reset their status.
Return the issue and board links. Do not start research or implementation implicitly.
