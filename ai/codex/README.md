# Codex: what dotfiles still owns

Skills, agent roles and the global `~/.codex/AGENTS.md` now come from the hubs listed in
`~/.config/dotfiles/hubs`, linked or rendered by `hubs_sync` (see the main README, "Hubs").
Codex cannot spawn symlinked roles, so hub agents are rendered and copied into
`~/.codex/agents/`, each carrying the render notice so the linker recognizes its own files.

What remains here:

| Path | Purpose |
|---|---|
| `config.toml.managed` | Settings that must live inside `~/.codex/config.toml` (status line and friends), spliced in between `# >>> dotfiles managed >>>` markers and re-applied on each launch |

`codex()` in `zsh/functions.zsh` runs `hubs_sync`, splices the managed block, and stages the
current repository's `.claude/skills` for the session. `deploy.sh --only codex` installs Codex and
initializes the block. `CODEX_HOME`, when set, replaces `~/.codex` throughout.
