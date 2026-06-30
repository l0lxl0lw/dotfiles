---
name: git-pr-from-main
description: Wrap current default-branch changes into a new feature branch with a single commit and open a GitHub pull request. Use when the user is on main/master and wants their work reviewed as a PR instead of pushed directly.
disable-model-invocation: true
allowed-tools: Bash(bash *), Bash(git *), Bash(gh *), Read, Edit
---

# PR From Main

Take uncommitted changes on the default branch, move them to a new feature branch as one commit, and open a GitHub PR.

## Scripts

This skill includes helper scripts in `~/.claude/skills/git-pr-from-main/scripts/`:

| Script | Purpose |
|--------|---------|
| `analyze-changes.sh` | Full repo analysis: status, branch info, diffs, recent commits, PR template check |
| `stage-files.sh [files\|--all]` | Stage files with sensitive file warnings |
| `create-commit.sh <msg> [--amend]` | Create commit or amend previous (rejects AI attribution) |

## Steps

### Phase 0: Verify On Default Branch

1. Check current branch. If it is NOT the default branch (`main` or `master`), **stop immediately** and tell the user:
   > "This skill only runs on the default branch. You're on `<branch>`. If you already have a feature branch with commits and want to open a PR for it, do it manually with `gh pr create`. Use `git-commit-local-changes` + `gh pr create` for branch-local commit workflows."
   Do not proceed.

### Phase 1: Analyze Repository State

2. Run the analysis script **from the repo root**:
   ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/git-pr-from-main/scripts/analyze-changes.sh'
   ```

   This outputs:
   - Git status and branch info
   - Default branch detection
   - Staged/unstaged changes and diffs
   - Untracked files
   - Recent commits (for style reference)
   - README and PR template existence

### Phase 2: Propose and Create Feature Branch

3. Generate a short, descriptive kebab-case branch name from the diff (e.g. `add-auth-middleware`, `fix-cache-eviction`).

4. **Propose the branch name to the user** and ask: *"Use this branch name, or type a replacement?"* Wait for confirmation or a replacement name. Never create the branch without this confirmation.

5. Create and switch to the new branch:
   ```bash
   git checkout -b <branch-name>
   ```

### Phase 3: Review and Propose Commit Message

6. Summarize the changes for the user:
   - What files changed
   - What the changes do

7. **Auto-propose a commit message** based on the diff. Show it and ask: *"Use this commit message, or type a replacement?"* Wait for confirm or replacement.

8. If README.md exists, check if changes affect documented content (new features, changed commands, removed functionality). Update README if needed — only for meaningful user-visible changes.

### Phase 4: Stage and Commit (single commit)

9. Stage files:
   ```bash
   bash ~/.claude/skills/git-pr-from-main/scripts/stage-files.sh --all
   ```
   Or stage specific files:
   ```bash
   bash ~/.claude/skills/git-pr-from-main/scripts/stage-files.sh file1.js file2.js
   ```

10. Create the single commit with the user-confirmed message:
    ```bash
    bash ~/.claude/skills/git-pr-from-main/scripts/create-commit.sh "commit message here"
    ```
    The script rejects AI attribution.

### Phase 5: Propose PR Title and Body

11. Gather context:
    ```bash
    git log --oneline $(git merge-base <default> HEAD)..HEAD
    git diff <default>...HEAD --stat
    ```

12. Draft:
    - **Title**: short (under 70 chars), describes the change purpose
    - **Body** (or the repo's PR template if one exists):
      ```
      ## Summary
      <1-3 bullet points explaining what changed and why>

      ## Changes
      <Grouped list of specific changes — e.g., by file or area>

      ## Test plan
      <How to verify these changes work — manual steps, test commands, etc.>
      ```

13. **Show the title and full body to the user** and ask: *"Use this, or type a replacement?"* Wait for confirmation or edits before pushing.

### Phase 6: Push and Create PR

14. Once confirmed, push and open the PR:
    ```bash
    git push -u origin $(git branch --show-current)
    ```
    ```bash
    gh pr create --title "<title>" --body "$(cat <<'EOF'
    ## Summary
    ...

    ## Changes
    ...

    ## Test plan
    ...
    EOF
    )"
    ```

15. Output the PR URL so the user can see it.

## Rules

- Run only from the default branch — refuse in Phase 0 otherwise
- Single commit: this skill creates exactly one commit on the new branch. If the user wants multiple commits or additional iterations, they should use `git-commit-local-changes` from that branch afterward.
- NEVER push or create the PR without asking the user for confirmation first
- NEVER include "Co-Authored-By" or any "Claude Code" / AI attribution in commits OR in the PR body — the commit script will reject attribution in commits, and the same rule applies to the PR body (do not include it)
- NEVER force push to `main` or `master`
- Always propose a branch name and wait for user confirmation/edit before `git checkout -b`
- Always propose the commit message and wait for user confirmation/edit before `create-commit.sh`
- Always propose the PR title and body and wait for user confirmation/edit before `git push` / `gh pr create`
- Use conventional commit style if the repo uses it
- The PR description must accurately reflect the full diff
- If the diff is large, group changes by area/component in the Changes section
- Keep the Summary section focused on the "why"; Changes section on the "what"
- The stage-files.sh script warns about sensitive files (.env, .pem, .key, etc.)
- Only update README when changes meaningfully affect documented content
- Do not add draft flag unless the user asks for a draft PR
