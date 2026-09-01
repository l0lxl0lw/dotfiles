# Codex Config

Tracked config for the [Codex CLI](https://github.com/openai/codex), symlinked into
`~/.codex/` by `codex_merge_config` (in `~/dotfiles/zsh/functions.zsh`).

```
dotfiles/ai/codex/
├── AGENTS.md            -> ~/.codex/AGENTS.md     # global instructions, every session
├── config.toml.managed  -> spliced into ~/.codex/config.toml between markers
└── skills/              -> ~/.codex/skills/<name> # Codex-local skills, flattened
```

`codex_merge_config` also imports cross-tool skills from `../shared/skills/` into the
same flattened Codex namespace. Codex-local skills win on name collisions.

At launch the `codex()` wrapper also exposes repository-local `.claude/skills` through a
temporary catalog under `~/.codex/skills`. The repository remains untouched, and the
catalog is removed when that Codex process exits.

## Settings (status line, etc.)

`config.toml.managed` is a TOML fragment spliced into the real `~/.codex/config.toml`
between `# >>> dotfiles managed >>>` markers. Everything outside the markers is left
untouched. Edit the fragment here, never the block in `~/.codex/config.toml` — the next
sync overwrites it.

The status line mirrors the Claude Code statusline — model, cwd, repo, branch, then usage:

```toml
[tui]
status_line = [
  "current-dir", "project-name", "git-branch",
  "context-used", "five-hour-limit", "weekly-limit",
  "model-with-reasoning",
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
| `codex-version` | app version |

**Not accepted, despite appearing in the binary:** `model-name`, `usage-limit`,
`secondary-usage-limit`. All three have description strings compiled in — `usage-limit` even
carries "Remaining usage on the primary usage limit (omitted when unavailable)" — but 0.146.0
answers them with `⚠ Ignored invalid status line items`. Presence in the string table is not
membership in the accepted id set. Confirm any addition in a running TUI: `codex debug
prompt-input` parses an invalid id without complaint, so the pre-swap probe in
`codex_merge_config` will not catch one either.

**Every usage-limit item is "omitted when unavailable."** Codex reads these from API response
headers — nothing is cached on disk — so an item silently disappears when the account isn't
reporting that window. A missing `five-hour-limit` usually means exactly that, not a
misconfiguration.

### Why `five-hour-limit` renders nothing here

Codex fills exactly two slots, from the `…-primary-window-minutes` and
`…-secondary-window-minutes` response headers. The *server* decides which windows land in
them; the client cannot synthesise one that wasn't sent. A named item matches on window
duration, so `five-hour-limit` renders only when a 300-minute window actually arrives.

What the server sends here, by plan:

| plan | primary | secondary |
|---|---|---|
| `plus` | 5-hour | weekly |
| `team` (until 2026-07) | 5-hour | weekly |
| `team` (current) | **weekly** | *none* |

Somewhere between 2026-06-04 and 2026-07-24 the server stopped sending a 5-hour window for
Team plans, and now sends a single weekly window as `primary` with `secondary: null`.
Verified against 159 `rate_limits` records in `~/.codex/sessions` — 5h appears in every
record before that gap and in none after, across a `plus` → `team` change that by itself did
not end it. So `weekly-limit` renders and `five-hour-limit` is silently omitted.

`five-hour-limit` is kept in the list regardless: it costs nothing while absent and returns
on its own if the plan ever reports that window again. The plan-agnostic `usage-limit` pair
would have made the omission visible instead of silent, but this build rejects those ids
(see above), so a silent gap plus this note is the available option.

To check what the account is being sent right now:

```sh
grep -roh '"window_minutes":[0-9]*' ~/.codex/sessions | sort | uniq -c
```

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
ai/codex/skills/<skill-name>/SKILL.md
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

## Repository Claude skills

When `codex` starts anywhere inside a Git repository, the shell wrapper finds the
repository root. If `<repo>/.claude/skills` contains skills, it creates a unique temporary
directory under `~/.codex/skills` and links the complete Claude skill tree into it. Codex
discovers top-level and categorized skills through that link, so they appear in the skill
catalog and `$` picker without creating `<repo>/.agents` or changing the worktree.

The temporary catalog exists only while the launched Codex process is alive. An `always`
cleanup block removes the link and its now-empty directory when the process exits,
including a nonzero exit, while preserving Codex's status. Repositories without
`.claude/skills` launch normally without creating a catalog.

The staging area is in the shared user skill namespace, so another Codex process launched
during that interval may also discover it. Unique staging directories keep lifecycle
cleanup independent; strict cross-session isolation is deliberately out of scope.

## Shared Skills

Codex imports shared skills from:

- `ai/shared/skills`

Shared skills currently include the git workflows, Impeccable design skills, OMC planning
skills, integrations, community skills, and utilities.

The same tree is imported by the Claude and Grok syncs, so a skill added there reaches
all three tools.

If a shared skill needs Codex-specific behavior, add a skill with the same basename
under `ai/codex/skills/`; the local Codex version takes precedence and the shared one is
skipped during sync.

### `model` and `effort` do not cross over

Some shared skills carry `model:` and `effort:` frontmatter — `ai/shared/skills/git/*` ask
for `sonnet`/`medium`, `ai/shared/skills/utilities/*` for `opus`/`high`. **Those two fields
are Claude-only.** Codex 0.149.1 reads exactly `name`, `description` and `metadata`
(`metadata.short-description`) out of a `SKILL.md`; its own bundled `skill-creator` says the
same, and its loader silently ignores everything else, so the fields cost nothing but buy
nothing here. Verified by loading a probe skill carrying both fields under a throwaway
`CODEX_HOME` — it appears in `codex debug prompt-input` with no warning and no effect.

Codex has no per-skill model or reasoning-effort hook at all. The only knobs are
session-wide (`model` / `model_reasoning_effort` in `config.toml`, `/model` in the TUI) or
subagent-wide (`default_subagent_model` / `default_subagent_reasoning_effort`). If a Codex
equivalent is ever wanted, it has to be a session choice before invoking the skill, not
something the skill declares.

## How it loads

`~/.codex/skills` is a shared namespace: our symlinks sit next to Codex's own `.system/`
and bundled runtime directories, which are real dirs and are never touched. Codex resolves
symlinked skills normally. Shared skills are symlinked directly from their source
directories, so editing their contents updates both tools immediately.

Sync runs from a `codex()` shell wrapper rather than a hook, because Codex has no hook
mechanism (`codex --help` exposes `plugin` and `mcp`, nothing session-scoped). The wrapper
syncs, stages repository skills, runs the real binary, and cleans up when it exits. This
costs nothing on shells that never run Codex, keeps global config current at launch, and
leaves the repository untouched.

## What is deliberately not tracked

`~/.codex/config.toml` itself stays local — only the managed block is tracked. The rest of
that file holds 15 absolute paths (`CODEX_HOME`, nvm binary paths, `NODE_REPL_NODE_PATH`)
and a `[projects."…"]` trust list naming private work repos, none of which belongs in a
public repo. Same reasoning as `~/.claude/settings.json`.

Also untracked, all Codex-managed runtime state: `auth.json` (credentials), the `*.sqlite`
databases, `sessions/`, `history.jsonl`, `cache/`, `plugins/`, `logs`.

Plugins are managed by Codex itself via `codex plugin` and its marketplaces, not from here.
