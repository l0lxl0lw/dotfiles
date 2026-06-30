---
name: git-sync-main-and-commit
description: On a feature branch with uncommitted changes, pull the latest default branch into local main, merge main into the feature branch (resolving conflicts), then commit the user's work and push. Use when the user is on a branch, has uncommitted changes, and someone else has advanced main.
disable-model-invocation: true
allowed-tools: Bash(bash *), Bash(git *), Read, Edit
---

# Sync Main and Commit

Sync the latest default branch into your feature branch, resolve any merge conflicts, then commit uncommitted changes and push.

## Scripts

Helper scripts in `~/.claude/skills/git-sync-main-and-commit/scripts/`:

| Script | Purpose |
|--------|---------|
| `analyze-state.sh` | Current branch, uncommitted summary, local-main vs origin/main divergence, upstream status |
| `sync-main.sh` | Fast-forward local default branch from origin |
| `merge-main.sh` | Merge default branch into current feature branch; reports conflict state |
| `stage-files.sh [files\|--all]` | Stage files with sensitive-file warnings |
| `create-commit.sh <msg> [--amend]` | Create commit (rejects AI attribution) |

## Steps

### Phase 1: Analyze State

1. Run the analysis script from the repo root:
   ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/git-sync-main-and-commit/scripts/analyze-state.sh'
   ```
   Output includes:
   - Current branch (must NOT be the default branch)
   - Default branch name
   - Uncommitted file summary
   - Local `<default>` vs `origin/<default>` divergence (behind / ahead / diverged)
   - Any existing unresolved merge state

2. Refuse to proceed if:
   - Current branch IS the default branch — tell the user to use `git-push-to-main` or `git-pr-from-main`.
   - Repo is already in a conflicted merge — tell the user to finish or abort that merge first (`git merge --continue` or `git merge --abort`).
   - Local default branch has diverged from `origin/<default>` (has commits that aren't upstream) — bail out and tell the user: "Your local `<default>` has unpushed commits; this skill won't overwrite them. Push/rebase your `<default>` first, or sync manually."

### Phase 2: Stash Uncommitted Work

3. If there are uncommitted changes (tracked OR untracked):
   ```bash
   git stash push -u -m "git-sync-main-and-commit autostash"
   ```
   Record that a stash was created. If there are no uncommitted changes, skip this phase and note that the skill will still sync main into the branch (no final commit to make at the end).

### Phase 3: Update Local Default Branch

4. Run `sync-main.sh`. It:
   ```bash
   git fetch origin
   git checkout <default>
   git merge --ff-only origin/<default>
   git checkout <feature>
   ```
   If the fast-forward fails, the script exits non-zero. Restore the stash (`git stash pop`), return to the feature branch, and report the failure to the user.

### Phase 4: Merge Default Branch Into Feature Branch

5. Run `merge-main.sh`:
   ```bash
   git merge <default>
   ```
   Capture the exit code and conflict state.

### Phase 5: Resolve Merge Conflicts (if any)

6. If conflicts exist, list them:
   ```bash
   git diff --name-only --diff-filter=U
   ```

7. For **each conflicted file**:
   - Read the file to see the `<<<<<<<` / `=======` / `>>>>>>>` markers.
   - Propose a specific resolution based on both sides' intent.
   - Show the proposed resolution to the user and ask: *"Apply this resolution, or type your own?"* Wait for confirmation or a replacement.
   - Write the resolved content, then `git add <file>`.

8. After all files resolved, finalize the merge:
   ```bash
   git commit --no-edit
   ```
   (Uses git's default merge commit message — which does NOT contain AI attribution.)

9. If the user wants to abort mid-conflict: run `git merge --abort`, restore the stash (`git stash pop`), and stop.

### Phase 6: Restore Uncommitted Work

10. If a stash was created in Phase 2:
    ```bash
    git stash pop
    ```
    If `stash pop` itself produces conflicts (the stashed changes conflict with the merged content), repeat the Phase 5 resolution flow for those files. Do NOT drop the stash until it applies cleanly or the user explicitly confirms.

### Phase 7: Review and Propose Commit Message

11. Summarize the restored uncommitted changes for the user.

12. **Auto-propose a commit message**. Show it and ask: *"Use this message, or type a replacement?"* Wait for confirm or replacement.

### Phase 8: Stage and Commit

13. Stage:
    ```bash
    bash ~/.claude/skills/git-sync-main-and-commit/scripts/stage-files.sh --all
    ```
14. Commit:
    ```bash
    bash ~/.claude/skills/git-sync-main-and-commit/scripts/create-commit.sh "commit message here"
    ```
    Script rejects AI attribution.

### Phase 9: Push

15. Push:
    ```bash
    git push
    ```
    If no upstream:
    ```bash
    git push -u origin $(git branch --show-current)
    ```
    NEVER force-push from this skill.

## Rules

- Refuse to run on the default branch
- Refuse to run when a merge is already in progress
- Bail out if local default branch has diverged from `origin/<default>`
- Never discard the user's uncommitted work — stash first, restore last, never drop without explicit confirmation
- Resolve conflicts file-by-file with user confirmation before applying each resolution
- If `git stash pop` conflicts, resolve them the same way; do not drop the stash until applied
- NEVER commit while any file remains in conflicted state
- NEVER include "Co-Authored-By" or any "Claude Code" / AI attribution — the commit script rejects it
- NEVER force-push
- Always propose the final commit message and wait for user confirmation (or a replacement) before committing
- Use conventional commit style if the repo uses it
- The stage-files.sh script warns about sensitive files (.env, .pem, .key, etc.) and does not stage them
