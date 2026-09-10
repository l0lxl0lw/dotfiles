---
name: git-sync
description: Sync a feature branch with main using explicit rebase or merge, interactive conflict resolution, and GitHub project branch-sync reporting. Use when asked to sync, rebase onto main, or merge main into a work branch.
---

# Sync with project tracking

Read `~/dotfiles/ai/shared/skills/git/git-sync/SKILL.md` as the base workflow.
Use its scripts from that directory instead of `~/.claude/skills/git-sync/`, and
the native question tool instead of AskUserQuestion. Follow its strategy and
conflict-resolution rules. Loading this skill never authorizes force-push.

Run `python3 ~/dotfiles/ai/opencode/tracking/track.py list`. If the current branch
is registered, read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and the sync
procedure in `~/dotfiles/ai/opencode/commands/sync.md`. Integrate that procedure's
Syncing/Conflicts/Verifying/evidence transitions into the base workflow. Do not
load this skill recursively from the sync command; the shared file is the base.

For unregistered branches, follow the base workflow without project mutations.
Explicit sync authorization is required, even if a monitor reports Needs sync.
