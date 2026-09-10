---
name: git-branch-and-pr
description: Move default-branch work to a feature branch, commit it and open a PR, updating its registered GitHub issue. Use when asked to branch this work and open a PR.
---

# Branch and PR with issue tracking

Read `~/dotfiles/ai/shared/skills/git/git-branch-and-pr/SKILL.md` and follow its
complete workflow. Resolve any Claude-specific helper paths to the corresponding
`~/dotfiles/ai/shared/skills/git/` directories and use native question tools.

If the user supplied an OpenCFO issue, read
`~/dotfiles/ai/opencode/tracking/WORKFLOW.md`. Register the new branch to that issue
after creating the branch and before publishing, then refresh freshness. If Needs
sync, report it and ask about sync rather than rebasing/merging automatically.
Include the issue URL in the PR body, using a closing reference only when the PR
completes its acceptance criteria. After successful non-draft publication, post
the PR URL on the issue and set In review with the helper. Report failed project
updates separately from a successfully published PR.

With no supplied or registered issue, do not create an unrelated project ticket.
