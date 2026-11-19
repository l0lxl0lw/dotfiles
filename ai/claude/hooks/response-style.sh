#!/bin/sh
# UserPromptSubmit hook: Claude Code adds stdout to the context of every turn,
# so the style cannot fade in a long session. Codex gets the same text from
# ../../codex/AGENTS.md.
cat >/dev/null 2>&1 || :
echo "Response style: Be direct and concrete. Show all intermediate states. Explain like I'm 12."
