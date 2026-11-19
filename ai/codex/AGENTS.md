# AGENTS.md

Global instructions for Codex, symlinked to `~/.codex/AGENTS.md` by
`codex_merge_config`. Edit this tracked file rather than the symlink.

## Response style

Apply this to every response: Be direct and concrete. Show all intermediate
states. Explain like I'm 12.

Claude Code gets the same text on every prompt from
`~/dotfiles/ai/claude/hooks/response-style.sh`; keep the two in step.

## Next prompts

Next-prompt suggestions are enabled by default. After completing a substantive
turn, use the installed `next-steps` skill to append up to three useful follow-up
prompts when there is a natural continuation. Its tracked source is
`~/dotfiles/ai/codex/skills/next-steps/SKILL.md`; if the installed skill is absent,
read that source when available. If neither is available, omit suggestions.

Suggestions are optional follow-ups after the authorized work is complete; never
defer requested work into a suggestion. Follow the skill's draft-only number
selection and conversation-local on/off controls. Omit suggestions when the user
requests an exact output format or another instruction requires stopping without
additional output.
