# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

The `ai/claude/` directory of [dotfiles](https://github.com/l0lxl0lw/dotfiles) — custom skills, agent personas, hooks, and a system prompts reference collection. Source of truth for `~/.claude/`; the `claude_merge_config` zsh function symlinks its contents there.

Previously lived in its own repo at `l0lxl0lw/claude-config`, merged into dotfiles (with history) in July 2026.

## Architecture

```
dotfiles/ai/claude/
├── CLAUDE.md              # This file — guidance when working in this directory
├── skills/                # Claude-specific skill overrides, if needed
├── agents/                # Agent personas (.md files with frontmatter)
├── hooks/                 # Shell hooks (statusline.sh = context progress bar, explain-level.sh = per-prompt context injection)
└── prompts/               # Read-only reference collection of system prompts (Anthropic, Google, OpenAI, etc.)

dotfiles/ai/shared/
└── skills/
    ├── community/         # Skills from individual repos
    ├── git/               # Custom git workflow skills
    ├── impeccable/        # Design skills from pbakaus/impeccable
    ├── integrations/      # Custom integration skills
    ├── omc/               # Planning skills from oh-my-claudecode
    └── utilities/         # Custom utility skills
```

**Integration flow**: The `claude_merge_config()` zsh function (in `~/dotfiles/zsh/functions.zsh`) reads this directory and links it into `~/.claude/`:

- **skills** — finds every `SKILL.md` in `ai/claude/skills` and `ai/shared/skills`, then symlinks its parent dir flat to `~/.claude/skills/<name>`; `ai/claude/skills` is only for Claude-specific overrides
- **agents** — mirrors the dir tree, symlinks each `.md`
- **hooks** — symlinks top-level files from `hooks/` into `~/.claude/hooks`, then points `statusLine` at `statusline.sh` in `settings.json`. `statusLine` is the *only* entry it writes; every other hook here (currently `explain-level.sh`) needs its `settings.json` entry added by hand, so adding a script to `hooks/` is never sufficient on its own

Caveats worth knowing:

- The function runs from a **`SessionStart` hook** in `~/.claude/settings.json`, so a skill added or renamed here is picked up at the start of the next Claude Code session. Editing the *contents* of an existing skill needs no re-run at all — the symlinks make it live immediately. Run it by hand to apply a rename without restarting.
- It **converges rather than rebuilds**: a link that is already correct is not touched, so the steady state is zero writes and no window where a concurrent session sees a missing skill. It prints nothing when there was nothing to do — anything a `SessionStart` hook prints lands in the session as context.
- Cleanup is surgical: the function only deletes symlinks that point back into this directory (or the legacy `~/workspace/claude-config` path). Real directories and symlinks owned by other installers are left alone.
- `~/.claude/skills` is shared with gstack, which installs its skills as real directories. Because skills are flattened to their basename, a name here that collides with a gstack skill is skipped with a warning rather than clobbering it.
- `deploy.sh` only handles `.zshrc`/`.vimrc`/`.tmux.conf` — it does **not** touch `~/.claude/`. The dotfiles repo is auto-pulled daily by `zsh/zshrc.conf`.
- The merge function only sets `statusLine` in `settings.json`, and only when the value differs. Everything else in `~/.claude/settings.json` is hand-maintained and untracked.
- `~/.claude/CLAUDE.md` is a standalone, untracked file. It does **not** import this one — this file is directory-scoped documentation, loaded by Claude Code when the working directory is inside `~/dotfiles/ai/claude`.

## Adding Content

### Skills

Create shared skills in `../shared/skills/<category>/<skill-name>/SKILL.md`.
Use `skills/<category>/<skill-name>/SKILL.md` only for Claude-specific overrides.

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name
description: What this skill does and when to use it
disable-model-invocation: true  # Optional: user-only invocation
allowed-tools: Bash, Read       # Optional: restrict tool access
---
```

Skills can include helper scripts in `<skill-name>/scripts/`.

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
- `ai/shared/skills/git/` has eight workflow-specific skills covering the whole branch lifecycle, each scoped to one scenario, plus two read-only explainers. Skills are named for **what they do**; the branch they require is enforced in their first phase.

  | Skill | Runs on | Does |
  |---|---|---|
  | `git-commit` | anywhere | Commits on the current branch. Never pushes |
  | `git-push-branch` | feature branch | Commits and pushes; updates the open PR. Reports its CI checks |
  | `git-push-to-main` | default branch | Pulls if behind, then commits and pushes directly |
  | `git-branch-and-pr` | default branch | Moves the work to a new branch as one commit and opens a PR |
  | `git-pr` | feature branch | Opens a PR for a branch that already has commits |
  | `git-sync` | feature branch | Brings the default branch in — rebase preferred, merge as fallback. Committing and pushing are opt-in |
  | `git-merge-pr` | feature branch | Merges the open PR once it is genuinely mergeable |
  | `git-cleanup` | feature branch | After a verified merge: deletes the branch and refreshes the default branch |

  The lifecycle: `git-branch-and-pr` or (`git-commit` → `git-pr`) → `git-push-branch` for review fixes → `git-merge-pr` → `git-cleanup`. `git-sync` slots in whenever the default branch moves.

  Two read-only skills sit beside the lifecycle rather than in it. They mutate nothing (`git-explain-branch` fetches, which only moves remote-tracking refs) and are the only model-invocable skills in this directory:

  | Skill | Scope | Does |
  |---|---|---|
  | `git-explain-diff` | working tree | Explains staged + unstaged + **untracked** changes, grouped by behavioral change, and flags unupdated callers and accidental content |
  | `git-explain-branch` | `merge-base..HEAD` | Explains the branch as before/after against main, then a risk pass: contracts, migrations, blast radius, and what main gained on the same files |

  Both share one rendering contract — a two-column call-flow tree with descriptions pinned to column 90, and a boxed BEFORE/AFTER leaf on every changed path. It is duplicated verbatim in the two `SKILL.md` files, which say so; **change both together.**

- Conventions the git skills share, worth preserving when adding another:
  - **A gate script that exits non-zero, and a table in SKILL.md mapping every exit code to an action.** Refusals live in the script so they cannot be reasoned around.
  - **Destructive operations require a proof-carrying flag.** `cleanup-branch.sh` refuses to run without `--merge-verified`, which is only legitimate after `verify-merged.sh` exits 0.
  - **Never show the user git's raw `ours`/`theirs`** — they invert between merge and rebase. Say "your branch" and "main".
  - **A `## Common mistakes` section** at the end of every SKILL.md, and a `Triggers — "phrase", "phrase"` list in the description.
  - **A graphviz `digraph` workflow block** showing the decision points.
- All git skills reject AI attribution at the script level (`Co-Authored-By`, `Generated with Claude Code`, robot emoji). `create-commit.sh` will refuse the commit if the message contains any forbidden pattern, and `create-pr.sh` applies the same rule to the PR title and body.
- Every git skill shows a proposed commit message (and branch name / PR body where applicable) and waits for user confirmation or a replacement before acting.
- Always run the analyze script from the **repo root** (not a subdirectory) so the README check works correctly.
- `.env` and `.google-credentials.json` are gitignored
