---
name: git-push-to-main
description: Commit current changes on the default branch (main/master) and push to remote. Use when the user is on main, has verified their changes work, and wants to ship directly without a PR.
disable-model-invocation: true
allowed-tools: Bash(bash *), Bash(git *), Read, Edit
---

# Push to Main

Commit current changes on the default branch and push directly to remote. For verified work that does not need a PR.

## Scripts

This skill includes helper scripts in `~/.claude/skills/git-push-to-main/scripts/`:

| Script | Purpose |
|--------|---------|
| `analyze-changes.sh` | Full repo analysis: status, unpushed commits, diffs, recent commits |
| `stage-files.sh [files\|--all]` | Stage files with sensitive file warnings |
| `create-commit.sh <msg> [--amend]` | Create commit or amend previous (rejects AI attribution) |

## Steps

### Phase 0: Verify On Default Branch

1. Check current branch. If it is NOT the default branch (`main` or `master`), **stop immediately** and tell the user:
   > "This skill only runs on the default branch. You're on `<branch>`. Use `git-pr-from-main` if you want a PR, `git-sync-main-and-commit` if you want to sync main into this branch, or `git-commit-local-changes` for a plain branch commit."
   Do not proceed.

### Phase 1: Analyze Repository State

2. Run the analysis script **from the repo root**:
   ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/git-push-to-main/scripts/analyze-changes.sh'
   ```

   This outputs:
   - Git status
   - Unpushed commits count and list
   - Staged changes (diff --cached)
   - Unstaged changes (diff)
   - Untracked files
   - Recent commits (for style reference)
   - README existence check

### Phase 2: Handle Unpushed Commits

3. If there are unpushed commits, ask the user:
   - **Squash**: Merge new changes into existing commit(s) using `--amend`
   - **Stack**: Add a new commit on top
   - **Other**: Let user specify

### Phase 3: Review and Propose Commit Message

4. Summarize the changes for the user:
   - What files changed
   - What the changes do

5. **Auto-propose a commit message** based on the diff. Show it to the user and ask: *"Use this message, or type a replacement?"* Wait for the user to either confirm or provide their own message. Never commit without this confirmation step.

6. If README.md exists, check if changes affect documented content:
   - New features need documenting
   - Changed commands/structure
   - Removed functionality
   - Update README if needed (only for meaningful user-visible changes)

### Phase 4: Stage and Commit

7. Stage files:
   ```bash
   bash ~/.claude/skills/git-push-to-main/scripts/stage-files.sh --all
   ```
   Or stage specific files:
   ```bash
   bash ~/.claude/skills/git-push-to-main/scripts/stage-files.sh file1.js file2.js
   ```

8. Create commit with the user-confirmed message:
   ```bash
   bash ~/.claude/skills/git-push-to-main/scripts/create-commit.sh "commit message here"
   ```
   Or amend previous commit (for squash):
   ```bash
   bash ~/.claude/skills/git-push-to-main/scripts/create-commit.sh "updated message" --amend
   ```
   The script will refuse any message containing AI attribution (`Co-Authored-By`, `Generated with Claude Code`, etc.).

### Phase 5: Push

9. Push the commit(s):
   ```bash
   git push
   ```
   If no upstream is configured:
   ```bash
   git push -u origin $(git branch --show-current)
   ```
   If the commit was amended (squash), **ask the user for confirmation first**, then:
   ```bash
   git push --force-with-lease
   ```

## Rules

- Run only on the default branch — refuse in Phase 0 otherwise
- Always propose a commit message and get explicit user confirmation (or a replacement) before running `create-commit.sh`
- NEVER include "Co-Authored-By" or any "Claude Code" / AI attribution line in commit messages — the script will reject them and the commit will fail
- NEVER force push without explicit user confirmation
- When squashing, use `--amend` to combine changes into the previous commit
- Keep commit messages short and focused on the "why"
- Use conventional commit style if the repo uses it (check `analyze-changes.sh` recent-commits output)
- Only update README when changes meaningfully affect documented content
- The stage-files.sh script warns about sensitive files (.env, .pem, .key, etc.) and does not stage them automatically
