# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

The `claude/` directory of [dotfiles](https://github.com/l0lxl0lw/dotfiles) — custom skills, agent personas, hooks, and a system prompts reference collection. Source of truth for `~/.claude/`; the `claude_merge_config` zsh function symlinks its contents there.

Previously lived in its own repo at `l0lxl0lw/claude-config`, merged into dotfiles (with history) in July 2026.

## Architecture

```
dotfiles/claude/
├── CLAUDE.md              # This file — guidance when working in this directory
├── skills/                # Custom skills (symlinked to ~/.claude/skills)
│   ├── impeccable/            # Design skills from pbakaus/impeccable
│   ├── omc/                   # Planning skills from oh-my-claudecode
│   ├── community/             # Skills from individual repos
│   ├── git/                   # Custom git workflow skills
│   ├── integrations/          # Custom integration skills
│   └── utilities/             # Custom utility skills
├── agents/                # Agent personas (.md files with frontmatter)
├── hooks/                 # Shell hooks (statusline.sh = context progress bar)
└── prompts/               # Read-only reference collection of system prompts (Anthropic, Google, OpenAI, etc.)
```

**Integration flow**: The `claude_merge_config()` zsh function (in `~/dotfiles/zsh/functions.zsh`) reads this directory and links it into `~/.claude/`:

- **skills** — finds every `SKILL.md` and symlinks its parent dir flat to `~/.claude/skills/<name>`
- **agents** — mirrors the dir tree, symlinks each `.md`
- **hooks** — symlinks top-level files from `hooks/` into `~/.claude/hooks`, then points `statusLine` at `statusline.sh` in `settings.json`

Caveats worth knowing:

- The function runs from a **`SessionStart` hook** in `~/.claude/settings.json`, so a skill added or renamed here is picked up at the start of the next Claude Code session. Editing the *contents* of an existing skill needs no re-run at all — the symlinks make it live immediately. Run it by hand to apply a rename without restarting.
- It **converges rather than rebuilds**: a link that is already correct is not touched, so the steady state is zero writes and no window where a concurrent session sees a missing skill. It prints nothing when there was nothing to do — anything a `SessionStart` hook prints lands in the session as context.
- Cleanup is surgical: the function only deletes symlinks that point back into this directory (or the legacy `~/workspace/claude-config` path). Real directories and symlinks owned by other installers are left alone.
- `~/.claude/skills` is shared with gstack, which installs its skills as real directories. Because skills are flattened to their basename, a name here that collides with a gstack skill is skipped with a warning rather than clobbering it.
- `deploy.sh` only handles `.zshrc`/`.vimrc`/`.tmux.conf` — it does **not** touch `~/.claude/`. The dotfiles repo is auto-pulled daily by `zsh/zshrc.conf`.
- The merge function only sets `statusLine` in `settings.json`, and only when the value differs. Everything else in `~/.claude/settings.json` is hand-maintained and untracked.
- `~/.claude/CLAUDE.md` is a standalone, untracked file. It does **not** import this one — this file is directory-scoped documentation, loaded by Claude Code when the working directory is inside `~/dotfiles/claude`.

## Adding Content

### Skills

Create `skills/<category>/<skill-name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: skill-name
description: What this skill does and when to use it
disable-model-invocation: true  # Optional: user-only invocation
allowed-tools: Bash, Read       # Optional: restrict tool access
---
```

Skills can include helper scripts in `skills/<category>/<skill-name>/scripts/`.

### Agents

Create `agents/<agent-name>.md` with YAML frontmatter:

```yaml
---
name: agent-name
description: When to use this agent
category: engineering|analysis|quality|planning
---
```

After adding either, run `claude_merge_config` to create the symlink.

## Conventions

- Skill names use kebab-case directories; agent names use kebab-case `.md` files
- The `prompts/` directory is a reference archive — organized by provider (Anthropic, Google, OpenAI, xAI, Perplexity, Misc). Read-only, not loaded by Claude Code
- `skills/git/` has four workflow-specific skills, each scoped to one scenario:
  - `git-commit-local-changes` — commit on the current branch, no push (Claude proposes a message, user confirms or edits)
  - `git-push-to-main` — only runs on the default branch; commits and pushes directly
  - `git-pr-from-main` — only runs on the default branch; creates a feature branch with one commit and opens a PR
  - `git-sync-main-and-commit` — only runs on a feature branch; fast-forwards local main from origin, merges main into the branch (resolves conflicts file-by-file with user confirmation), restores stashed work, commits, and pushes
- All git skills reject AI attribution at the script level (`Co-Authored-By`, `Generated with Claude Code`, robot emoji). `create-commit.sh` will refuse the commit if the message contains any forbidden pattern.
- Every git skill shows a proposed commit message (and branch name / PR body where applicable) and waits for user confirmation or a replacement before acting.
- Always run the analyze script from the **repo root** (not a subdirectory) so the README check works correctly.
- `.env` and `.google-credentials.json` are gitignored
