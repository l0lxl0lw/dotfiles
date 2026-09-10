---
description: Commit requested work using the existing git-commit workflow.
agent: build
---

## Local workflow contract

Use the `git-commit` skill for this explicit request. Its locally owned base is
`~/dotfiles/ai/shared/skills/git/git-commit/`; use those scripts and OpenCode's
native question tool. The upstream prompt below remains additional commit-quality
guidance, but do not create local `thoughts/` artifacts. Inspect status, diff, and
recent history; stage only intended files and do not push unless asked. If the
branch appears in `~/dotfiles/ai/opencode/tracking/track.py list`, include its issue
reference in the report. A commit alone does not advance project status.

# Commit Changes

You are tasked with creating git commits for the changes made during this session.

## Commit Types

Use conventional commit prefixes to categorize changes:

- **fix:** Bugs that are being fixed or adjustments to how things work
- **feat:** Features that have been added
- **chore:** Tidying things up, not making substantial changes to how things work
- **refactor:** Changes that don't change the behavior, but do change the internal layout
- **docs:** Purely documentation and thoughts updates
- **ci:** Changes to how the CI system works

## Process:

1. **Think about what changed:**
   - Review the conversation history and understand what was accomplished
   - Review the `git status -s` to get an idea of what files changed
   - Consider whether changes should be one commit or multiple logical commits
   - Use `git diff` on specific files if you need more context. Only do this if you have no knowledge of the changes in that file.

2. **Plan your commit(s):**
   - Identify which files belong together
   - **Select the appropriate commit type** from the list above based on the nature of the changes
   - Draft clear, descriptive commit messages using the format: `type: description`
   - Use imperative mood in commit messages
   - Focus on why the changes were made, not just what

3. **Present your plan to the user:**
   - List the files you plan to add for each commit
   - Show the commit message(s) you'll use (including the commit type prefix)
   - Ask: "I plan to create [N] commit(s) with these changes. Shall I proceed?"

4. **Execute upon confirmation:**
   - Use `git add` with specific files (never use `-A` or `.`)
   - Create commits with your planned messages
   - Show the result with `git log --oneline -n [N]`

## Release Notes

Note: During release generation, commits with `chore:`, `docs:`, and `ci:` prefixes are automatically filtered out from the changelog to focus on user-facing changes. Other prefixes like `fix:` and `feat:` are included.

## Remember:
- You have the full context of what was done in this session
- Group related changes together
- Keep commits focused and atomic when possible
- The user trusts your judgment - they asked you to commit
