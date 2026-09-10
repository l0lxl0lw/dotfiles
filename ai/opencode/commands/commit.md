---
description: Commit requested work using the existing git-commit workflow.
agent: build
---
Input: $ARGUMENTS

Use the git-commit skill for this explicitly requested commit. Read its instructions
and use scripts under `~/dotfiles/ai/shared/skills/git/git-commit/` instead of
Claude-specific paths. Use the native question tool for questions. Inspect status,
diff and recent history first; stage only intended files. Do not push unless asked.
If this branch is registered in `~/dotfiles/ai/opencode/tracking/track.py list`,
include the associated issue reference in the completion report. Committing alone
does not advance the project to In review or Done.
