#!/bin/sh
# UserPromptSubmit hook: re-state the explanation depth I want on every turn.
#
# This lives here rather than in CLAUDE.md because CLAUDE.md is read once at
# session start and drifts out of attention over a long conversation, whereas
# additionalContext is re-injected with each prompt.
#
# Symlinked into ~/.claude/hooks by claude_merge_config (zsh/functions.zsh);
# wired up under hooks.UserPromptSubmit in ~/.claude/settings.json.

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Explain technical concepts at a college level: assume the reader is a capable adult who wants the real mechanism, not a simplified analogy. Use correct terminology and define it inline. Do not water things down or skip the parts that are hard - the full explanation is easier to understand than a vague one."
  },
  "suppressOutput": true
}
JSON
