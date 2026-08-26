# Dotfiles

## Setup
- run `./deploy.sh` initially — writes `source` stubs into `~/.zshrc`, `~/.vimrc`, `~/.tmux.conf`
- open a new shell, then run `claude_merge_config`, `codex_merge_config` and `grok_merge_config` once
- rerun `claude_merge_config` manually after adding or renaming Claude skills, agents, or hooks

## Layout

| Path | What |
|------|------|
| `zsh/` | shell config; `zshrc.conf` is the entry point, sources every other `*.zsh` |
| `ai/claude/` | Claude Code skills, agents, hooks, and a system-prompt reference archive — see [ai/claude/README.md](ai/claude/README.md) |
| `ai/codex/` | Codex CLI skills and global `AGENTS.md` — see [ai/codex/README.md](ai/codex/README.md) |
| `ai/grok/` | Grok CLI skills, agents, hooks, global `AGENTS.md`, and tracked settings — see [ai/grok/README.md](ai/grok/README.md) |
| `ai/shared/` | Skills shared by Claude, Codex, Grok, and future agent tools |
| `vim/` `tmux/` `emacs/` | editor and multiplexer config (`emacs/` is manual, not wired into `deploy.sh`) |

All three agent configs are symlinked into their user-level directories (`~/.claude`,
`~/.codex`, `~/.grok`) by shared plumbing in `zsh/functions.zsh`. It only ever removes
symlinks pointing back into this repo, so tools that install into the same directories —
gstack, Codex's own bundled skills, another vendor's Grok hooks — are left alone.

Claude is synced manually with `claude_merge_config`. Codex syncs from a `codex()` shell
wrapper since it has no hook mechanism. Grok syncs from both its wrapper and a tracked
`SessionStart` hook (the wrapper guarantees the config is current before launch; the hook
covers sessions started outside the shell).

Machine-specific and secret config lives in a separate private repo at `~/dotfiles-private`;
`zsh/zshrc.conf` sources `~/dotfiles-private/zsh/*` if that directory exists.

This repo git-pulls itself once a day on shell start.
