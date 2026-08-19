# Grok Config

Tracked config for the [Grok CLI](https://github.com/xai-org), symlinked into
`~/.grok/` by `grok_merge_config` (in `~/dotfiles/zsh/functions.zsh`).

```
dotfiles/ai/grok/
├── AGENTS.md             -> ~/.grok/AGENTS.md             # global instructions, every session
├── managed_config.toml   -> ~/.grok/managed_config.toml   # tracked settings, below config.toml
├── agents/               -> ~/.grok/agents/<name>.md      # subagent definitions, flat
├── hooks/                -> ~/.grok/hooks/<name>.json     # session hooks, one file per concern
└── skills/               -> ~/.grok/skills/<name>         # Grok-local skills, flattened
```

`grok_merge_config` also imports cross-tool skills from `../shared/skills/` into the
same flattened Grok namespace. Grok-local skills win on name collisions.

## Settings

`managed_config.toml` is symlinked straight to `~/.grok/managed_config.toml` — no
splicing, no markers, none of the machinery the Codex side needs. Grok merges its
config files lowest-to-highest:

```
managed_config.toml  ->  config.toml  ->  GROK_CONFIG overlay  ->  requirements.toml / MDM
```

So this file supplies **defaults** and the machine-local `~/.grok/config.toml` overrides
them per key. That split is what makes a plain symlink safe: Grok only ever reads the
managed layer — the TUI writes solely to `config.toml` — so nothing here gets clobbered
by the app, and nothing machine-local (auth state, marketplace bookkeeping, remembered
modal sizes) leaks into the repo.

Nothing validates the file at link time, and a malformed one breaks startup. After
editing, run `grok inspect` — it prints the config sources it loaded and a
`Config Warnings` section for keys it did not recognize.

### Harness compatibility

The one thing set today is the `[compat.claude]` / `[compat.cursor]` block, pinned to
the values it already had by default. It is written down because the inheritance is a
decision:

- `~/.claude/skills` is where gstack installs its skills, as real directories. They are
  not tracked in this repo, and this scan is the only way Grok sees them.
- `~/.claude/CLAUDE.md` carries the global instructions shared with Claude Code, so
  `AGENTS.md` here holds only what is Grok-specific rather than a second copy.

`grok inspect` reports the resolved cells under `Harness Compatibility`, marked
`(config)` once this file supplies them instead of the built-in default.

## Adding a skill

Grok uses the same `SKILL.md` format as Claude Code and Codex:

```
ai/grok/skills/<skill-name>/SKILL.md
```

```yaml
---
name: skill-name
description: What this does and when Grok should reach for it
---
```

Categories are allowed (`skills/<category>/<name>/SKILL.md`) — skills are flattened to
their directory basename when linked, same as the other two tools.

Then run `grok_merge_config`, or just launch `grok` — the shell wrapper syncs first.

## Shared Skills

Grok imports shared skills from:

- `ai/shared/skills`

If a shared skill needs Grok-specific behavior, add a skill with the same basename under
`ai/grok/skills/`; the local Grok version takes precedence and the shared one is skipped
during sync.

Note that Grok would find those skills anyway, through the Claude-compat scan of
`~/.claude/skills` — that is how it saw them before this directory existed. Linking them
in directly is still worth it: it makes Grok's skill set explicit and independent of what
the Claude sync happens to have done, and Grok de-duplicates by skill name, so a skill
reachable through both paths is loaded once.

## Agents and hooks

`agents/*.md` are Grok subagent definitions, symlinked flat into `~/.grok/agents/` (Grok
does not recurse there). Grok's agent schema is its own — the Claude agent definitions in
`../claude/agents/` are not copied over, and the directory starts empty.

`hooks/*.json` are session hooks. Grok loads every `*.json` in `~/.grok/hooks/` by itself
and treats global hooks as trusted, so unlike the Claude side nothing has to be wired into
a settings file afterwards — dropping a file in this directory is the whole install.

`hooks/dotfiles-sync.json` is the `SessionStart` hook that re-runs `grok_merge_config`.

## How it loads

Sync runs from two places:

- The `grok()` shell wrapper, which syncs and then execs the real binary. This is what
  guarantees the config is current *before* Grok reads it.
- The tracked `SessionStart` hook, which covers launches that never touch this shell — an
  IDE or ACP client running `grok agent stdio`. A hook fires while the session is already
  coming up, so treat it as the safety net rather than the primary trigger.

Both are idempotent: the sync converges rather than rebuilding, and prints nothing when
there is nothing to do. The hook file itself is a symlink out of this repo, so it installs
on the first sync and self-heals afterwards — unlike Claude's, which lives in an untracked
`~/.claude/settings.json` and has to be reinstalled by hand on each machine.

`~/.grok/skills`, `~/.grok/agents` and `~/.grok/hooks` are shared namespaces. Our symlinks
sit next to real files other installers own (`hooks/orca-status.json`, for one) and those
are never touched: the sync only ever removes a symlink that points back into `~/dotfiles`.
Grok's own bundled skills live under `~/.grok/bundled/skills` and marketplace plugins under
`~/.grok/plugins`, neither of which this goes near.

Because it symlinks, editing a skill's contents takes effect immediately. Adding or
renaming one needs a re-sync.

## What is deliberately not tracked

`~/.grok/config.toml` itself stays local — it carries the privacy-banner acknowledgement,
marketplace bookkeeping and the TUI hints Grok rewrites as you use it. Tracked settings go
in `managed_config.toml` instead, which is exactly the layer that exists for this.

Also untracked, all Grok-managed runtime state: `auth.json` and `agent_id` (credentials and
identity), `trusted_folders.toml` (names private repos), `sessions/`, `worktrees.db`,
`logs/`, `memtrace/`, `marketplace-cache/`, `downloads/`, `relocations/`, and the shipped
`bundled/`, `vendor/`, `bin/`, `docs/`, `completions/`.

Plugins are managed by Grok itself through its marketplace, not from here.
