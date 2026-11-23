# Claude Code: what dotfiles still owns

Skills, agents and the global `~/.claude/CLAUDE.md` now come from the hubs listed in
`~/.config/dotfiles/hubs`, linked by `hubs_sync` (see the main README, "Hubs").
Agents that used to live here are in the personal hub's `.claude/agents/`.

What remains here:

| Path | Purpose |
|---|---|
| `hooks/statusline.sh` | Claude Code status line (model, branch, `gh:<profile>`, account); linked into `~/.claude/hooks/` and set as `statusLine` in `~/.claude/settings.json` |

`claude()` in `zsh/functions.zsh` runs `hubs_sync` before each launch; `deploy.sh --only claude`
installs Claude Code and initializes the settings. `~/.claude/CLAUDE.md` carries a generated block
between hub markers; text outside the markers is yours.
