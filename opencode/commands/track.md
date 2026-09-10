---
description: Inspect, register, refresh or repair GitHub issue and branch project tracking.
agent: build
model: openai/gpt-5.6-luna-fast
---
Read `~/dotfiles/opencode/tracking/WORKFLOW.md` and follow its contract.

Request: $ARGUMENTS

Use the tracking helper to list registrations, register an issue in the current
feature worktree, refresh one or all issues, set an explicitly requested development
status, attach an issue to the current Orca worktree with `link-orca`, or unregister
obsolete/incorrect local monitoring. A conflicting Orca issue link requires the same
explicit, observed-number replacement gate documented in the workflow; never invent
`--replace-existing` authorization. With no arguments show registrations and project
status. Never infer authorization to rebase/merge from a refresh request. Report
errors and stale observations accurately. Do not mark Done without checking merged
PRs and acceptance criteria. For renamed branches, show the old/new identity and
repair the registration explicitly. Every repository uses the configured Project 4.
