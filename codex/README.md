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

Full set of item ids, verified present in codex-cli 0.146.0 by scanning the binary:

| Context | Usage |
|---|---|
| `current-dir` `project-root` `project-name` `git-branch` | `context-used` `context-remaining` `context-window-size` |
| `thread-title` `thread-id` `session-id` | `used-tokens` `total-input-tokens` `total-output-tokens` |
| `run-state` `task-progress` `model-with-reasoning` | `five-hour-limit` `weekly-limit` `codex-version` |

`model-name` circulates in docs and gists but does **not** exist in 0.146.0. Codex treats an
unknown id as a warning ("status line configuration contains unknown item identifiers"), not
a startup failure — so a typo degrades quietly. The parse check below will not catch it,
because unknown ids are valid TOML; only the id list above is authoritative.

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
