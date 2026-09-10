---
name: git-merge-pr
description: Merge an explicitly requested PR after checking CI and mergeability, then reconcile tracked GitHub work branches. Use when asked to merge or land a PR.
---

# Merge PR with issue tracking

Read `~/dotfiles/ai/shared/skills/git/git-merge-pr/SKILL.md` and follow its full
workflow and strategy question. Use scripts from that directory instead of
Claude-specific paths, and native question tools for questions.

Before merging, inspect `python3 ~/dotfiles/ai/opencode/tracking/track.py list`
and record the current branch's issue, if registered. After a successful merge,
read its acceptance criteria and remaining required PRs. Only mark Done when all
are satisfied; post the merge URL and verification summary. Then unregister the
completed branch before cleanup removes its worktree. Partial completion remains
open and gets a progress comment. Do not treat issue auto-closure as proof.

Run the helper's `refresh` after merge to detect other tracked branches now behind.
Report errors without implying automatic sync occurred. Cleanup still follows
the base skill's explicit user choice. No automatic rebase, merge or force-push
of other branches is authorized by merging this PR.
