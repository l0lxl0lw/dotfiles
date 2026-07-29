---
name: git-commit-local-changes
description: Analyze uncommitted changes and create a commit, with options to squash or stack on existing unpushed commits.
disable-model-invocation: true
allowed-tools: Bash(bash *), Bash(git *), Read, Edit
---

# Commit Local Changes

Analyze uncommitted changes and create a commit.

## Scripts

This skill includes helper scripts in `~/.claude/skills/git-commit-local-changes/scripts/`:

| Script | Purpose |
|--------|---------|
| `analyze-changes.sh` | Full repo analysis: status, unpushed, diffs, recent commits |
| `stage-files.sh [files\|--all]` | Stage files with sensitive file warnings |
| `create-commit.sh <msg> [--amend]` | Create commit or amend previous |

## Steps

### Phase 1: Analyze Repository State

1. Run the analysis script **from the repo root** to get full picture:
   ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/git-commit-local-changes/scripts/analyze-changes.sh'
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

2. If there are unpushed commits, ask the user:
   - **Squash**: Merge new changes into existing commit(s) using `--amend`
   - **Stack**: Add a new commit on top
   - **Other**: Let user specify

### Phase 3: Review and Propose Commit Message

3. Summarize the changes for the user:
   - What files changed
   - What the changes do

4. **Auto-propose a commit message** based on the diff. Show it to the user and ask: *"Use this message, or type a replacement?"* Wait for the user to confirm or provide a replacement. Never commit without this confirmation.

5. If README.md exists, check if changes affect documented content:
   - New features need documenting
   - Changed commands/structure
   - Removed functionality
   - Update README if needed

### Phase 4: Stage and Commit

6. Stage files:
   ```bash
   bash ~/.claude/skills/git-commit-local-changes/scripts/stage-files.sh --all
   ```
   Or stage specific files:
   ```bash
   bash ~/.claude/skills/git-commit-local-changes/scripts/stage-files.sh file1.js file2.js
   ```

7. Create commit with the user-confirmed message:
   ```bash
   bash ~/.claude/skills/git-commit-local-changes/scripts/create-commit.sh "commit message here"
   ```
   Or amend previous commit (for squash):
   ```bash
   bash ~/.claude/skills/git-commit-local-changes/scripts/create-commit.sh "updated message" --amend
   ```
   The script will refuse any message containing AI attribution.

## Rules

- Continue to the next phase automatically if the current phase completes without errors
- Always propose a commit message and wait for user confirmation (or a replacement) before running `create-commit.sh`
- NEVER include "Co-Authored-By" or any "Claude Code" / AI attribution in commit messages — the script rejects them
- NEVER run `git push` - user pushes manually
- When squashing, use `--amend` to combine changes into the previous commit
- Keep commit messages short and focused on the "why"
- Use conventional commit style if the repo uses it
- Only update README when changes meaningfully affect documented content
- Do not add to README for minor fixes, refactors, or internal changes
- The stage-files.sh script warns about sensitive files (.env, .pem, .key, etc.)
