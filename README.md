# Dotfiles

## Setup
- run `./deploy.sh` initially — writes `source` stubs into `~/.zshrc`, `~/.vimrc`, `~/.tmux.conf`
- open a new shell, then run `claude_merge_config` and `codex_merge_config` once
- install the Claude `SessionStart` hook so renames self-heal — see [claude/README.md](claude/README.md#setup)
  (`~/.claude/settings.json` is machine-local and not tracked here)

## Layout

| Path | What |
|------|------|
| `zsh/` | shell config; `zshrc.conf` is the entry point, sources every other `*.zsh` |
| `claude/` | Claude Code skills, agents, hooks, and a system-prompt reference archive — see [claude/README.md](claude/README.md) |
| `codex/` | Codex CLI skills and global `AGENTS.md` — see [codex/README.md](codex/README.md) |
| `vim/` `tmux/` `emacs/` | editor and multiplexer config (`emacs/` is manual, not wired into `deploy.sh`) |

Both agent configs are symlinked into their user-level directories (`~/.claude`, `~/.codex`)
by shared plumbing in `zsh/functions.zsh`. It only ever removes symlinks pointing back into
this repo, so tools that install into the same directories — gstack, Codex's own bundled
skills — are left alone. Claude syncs from a `SessionStart` hook; Codex from a `codex()`
shell wrapper, since it has no hook mechanism.

Machine-specific and secret config lives in a separate private repo at `~/dotfiles-private`;
`zsh/zshrc.conf` sources `~/dotfiles-private/zsh/*` if that directory exists.

This repo git-pulls itself once a day on shell start.
