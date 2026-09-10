---
description: Inspect, register, refresh or repair GitHub issue and branch project tracking.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Request: $ARGUMENTS

Use the tracking helper to list registrations, register an issue in the current
feature worktree, refresh one or all issues, set an explicitly requested development
status, or unregister obsolete/incorrect local monitoring. With no arguments show
registrations and project status. Never infer authorization to rebase/merge from
a refresh request. Report errors and stale observations accurately. Do not mark Done
without checking merged PRs and acceptance criteria. For renamed branches, show
the old/new identity and repair the registration explicitly. For unrelated
repositories explain that an explicit project mapping is required.
