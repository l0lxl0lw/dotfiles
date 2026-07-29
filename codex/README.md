# Codex Config

Tracked config for the [Codex CLI](https://github.com/openai/codex), symlinked into
`~/.codex/` by `codex_merge_config` (in `../zsh/functions.zsh`).

```
dotfiles/codex/
├── AGENTS.md            -> ~/.codex/AGENTS.md     # global instructions, every session
├── config.toml.managed  -> spliced into ~/.codex/config.toml between markers
└── skills/              -> ~/.codex/skills/<name> # one symlink per skill, flattened
```

## Settings (status line, etc.)

`config.toml.managed` is a TOML fragment spliced into the real `~/.codex/config.toml`
between `# >>> dotfiles managed >>>` markers. Everything outside the markers is left
untouched. Edit the fragment here, never the block in `~/.codex/config.toml` — the next
sync overwrites it.

The status line mirrors the Claude Code statusline — model, cwd, repo, branch, then usage:

```toml
[tui]
status_line = [
  "model-with-reasoning", "current-dir", "project-name", "git-branch",
  "context-used", "five-hour-limit", "weekly-limit",
]
status_line_use_colors = true
```

Full set of item ids, read out of the codex-cli 0.146.0 binary with their own descriptions:

| id | renders |
|---|---|
| `app-name` `project-name` `current-dir` `project-root` | app name; project name (falls back to dir name); cwd |
| `git-branch` | current branch (omitted when unavailable) |
| `run-state` `task-progress` `thread-title` `thread-id` `session-id` | Ready/Working/Thinking; latest `update_plan` progress; thread identity |
| `model-name` `model-with-reasoning` | model, with or without reasoning level |
| `context-used` `context-remaining` `context-window-size` | context window (omitted when unknown) |
| `used-tokens` `total-input-tokens` `total-output-tokens` | session tokens (`used-tokens` omitted when zero) |
| `five-hour-limit` `daily-limit` `weekly-limit` `monthly-limit` `annual-limit` | that specific usage window |
| `usage-limit` `secondary-usage-limit` | primary / secondary limit, whichever window the plan reports |
| `codex-version` | app version |

**Every usage-limit item is "omitted when unavailable."** Codex reads these from API response
headers — nothing is cached on disk — so an item silently disappears when the account isn't
reporting that window. A missing `five-hour-limit` usually means exactly that, not a
misconfiguration. `usage-limit` / `secondary-usage-limit` are the plan-agnostic alternative:
they render whatever limits the account actually has, labelled `primary` / `secondary`.

An unknown id is not a startup failure — Codex warns about "unknown item identifiers" in the
TUI and carries on. Neither `codex doctor` nor the parse check below catches it, since
unknown ids are still valid TOML. The table above is the authoritative list for this version.

### Why splice rather than symlink or profile

`config.toml` can't be a symlink to this repo — it also holds machine-local absolute paths
and a `[projects."…"]` trust list of private repos, and Codex writes to it.

Codex has no include directive. It does have `--profile`, which layers
`$CODEX_HOME/<name>.config.toml` over the base config, and that file *can* be a symlink
(verified). But it only applies when `-p` is passed, so it would cover the CLI through the
`codex()` wrapper and miss the desktop app and every other entry point. Splicing into the
base config reaches all of them.

The splice is re-applied on every launch, so it is self-healing: if Codex or a manual edit
clobbers the block, the next `codex` run restores it. Before swapping the file in, the
candidate is parsed by a real Codex process against a throwaway `CODEX_HOME` — if it
wouldn't load (a duplicate `[tui]` table, a typo in the fragment), the write is refused and
the working config is left alone. A copy of the previous file is kept at
`~/.codex/config.toml.dotfiles.bak`.

## Adding a skill

Codex uses the same `SKILL.md` format as Claude Code:

```
codex/skills/<skill-name>/SKILL.md
```

```yaml
---
name: skill-name
description: What this does and when Codex should reach for it
metadata:
  short-description: Short label
---
```

Categories are allowed (`skills/<category>/<name>/SKILL.md`) — skills are flattened to
their directory basename when linked, same as the Claude side.

Then run `codex_merge_config`, or just launch `codex` — the shell wrapper syncs first.

## How it loads

`~/.codex/skills` is a shared namespace: our symlinks sit next to Codex's own `.system/`
and bundled runtime directories, which are real dirs and are never touched. Codex resolves
symlinked skills normally — verified with `codex debug prompt-input`, which lists a linked
skill exactly like a bundled one and reports its real path.

Sync runs from a `codex()` shell wrapper rather than a hook, because Codex has no hook
mechanism (`codex --help` exposes `plugin` and `mcp`, nothing session-scoped). The wrapper
syncs and then execs the real binary, so it costs nothing on shells that never run Codex,
and the config is always current at launch. The tradeoff: a skill added *while* a Codex
session is already open needs `codex_merge_config` by hand.

## What is deliberately not tracked

`~/.codex/config.toml` itself stays local — only the managed block is tracked. The rest of
that file holds 15 absolute paths (`CODEX_HOME`, nvm binary paths, `NODE_REPL_NODE_PATH`)
and a `[projects."…"]` trust list naming private work repos, none of which belongs in a
public repo. Same reasoning as `~/.claude/settings.json`.

Also untracked, all Codex-managed runtime state: `auth.json` (credentials), the `*.sqlite`
databases, `sessions/`, `history.jsonl`, `cache/`, `plugins/`, `logs`.

Plugins are managed by Codex itself via `codex plugin` and its marketplaces, not from here.
