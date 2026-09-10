---
name: git-pr
description: Open a PR for a committed feature branch, run the repository checks, and update its registered GitHub project issue. Use when asked to open or publish a pull request.
---

# Publish PR with issue tracking

Read `~/dotfiles/ai/shared/skills/git/git-pr/SKILL.md` and follow its full workflow.
Use scripts from that directory instead of Claude-specific paths, and native
question tools for questions.

Before publication, run `python3 ~/dotfiles/ai/opencode/tracking/track.py list`.
If this branch is registered, read the tracking WORKFLOW.md in the same directory
as track.py, read its issue and plan, and refresh its freshness. Report Needs sync
and ask whether to sync; never automatically rebase/merge. Include the issue URL
in the PR body. Use a closing reference only if this PR completes the ticket.

After successful publication, post the PR URL to that issue and set In review
only for a non-draft PR. Verify helper success; report failed tracking separately
from successful PR publication. No registration means no project mutation.
