# Codex Config

Tracked config for the [Codex CLI](https://github.com/openai/codex), symlinked into
`~/.codex/` by `codex_merge_config` (in `../zsh/functions.zsh`).

```
dotfiles/codex/
├── AGENTS.md    -> ~/.codex/AGENTS.md     # global instructions, every session
└── skills/      -> ~/.codex/skills/<name> # one symlink per skill, flattened
```

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

`~/.codex/config.toml` stays local. It holds 15 absolute paths (`CODEX_HOME`, nvm binary
paths, an `NODE_REPL_NODE_PATH`) and a `[projects."…"]` trust list naming private work
repos — none of which belongs in a public repo, and all of which Codex rewrites on its own.
Same reasoning as `~/.claude/settings.json`.

Also untracked, all Codex-managed runtime state: `auth.json` (credentials), the `*.sqlite`
databases, `sessions/`, `history.jsonl`, `cache/`, `plugins/`, `logs`.

Plugins are managed by Codex itself via `codex plugin` and its marketplaces, not from here.
