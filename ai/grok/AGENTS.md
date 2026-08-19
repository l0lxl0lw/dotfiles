# AGENTS.md

Global instructions for the [Grok CLI](https://github.com/xai-org), symlinked to
`~/.grok/AGENTS.md` by `grok_merge_config`. Grok reads this on every session, in
every project.

This is Grok's equivalent of `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` — it is
currently empty of real content. Add global preferences here rather than editing
`~/.grok/AGENTS.md` directly, so they stay tracked.

Note that Grok *also* reads `~/.claude/CLAUDE.md` through its Claude-compatibility
scanner, and that is left on deliberately (see `managed_config.toml`). So anything
already stated there applies to Grok too — put Grok-specific instructions here, not
a copy of the Claude ones.
