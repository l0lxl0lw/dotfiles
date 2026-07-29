# Dotfiles

## Setup
- run `./deploy.sh` initially — writes `source` stubs into `~/.zshrc`, `~/.vimrc`, `~/.tmux.conf`
- open a new shell, then run `claude_merge_config` to link `claude/` into `~/.claude`

## Layout

| Path | What |
|------|------|
| `zsh/` | shell config; `zshrc.conf` is the entry point, sources every other `*.zsh` |
| `claude/` | Claude Code skills, agents, hooks, and a system-prompt reference archive — see [claude/README.md](claude/README.md) |
| `vim/` `tmux/` `emacs/` | editor and multiplexer config (`emacs/` is manual, not wired into `deploy.sh`) |

Machine-specific and secret config lives in a separate private repo at `~/dotfiles-private`;
`zsh/zshrc.conf` sources `~/dotfiles-private/zsh/*` if that directory exists.

This repo git-pulls itself once a day on shell start.
