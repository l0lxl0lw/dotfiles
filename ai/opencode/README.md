# OpenCode Config

OpenCode is a peer of Claude, Codex and Grok. `opencode_merge_config` in
`zsh/functions.zsh` links all active `ai/shared/skills/**/SKILL.md` directories into
`${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/<name>` using the shared sync helpers.
It does not depend on OpenCode's compatibility scans of `~/.claude/skills` or
`~/.agents/skills`.

## Overrides

Put OpenCode-only skills or replacements in `ai/opencode/skills/<name>/SKILL.md`.
Categories are allowed; the sync flattens skill directories by basename. Local
skills take precedence over shared skills of the same basename. Use matching
`name` and `description` frontmatter, for example:

```yaml
---
name: my-skill
description: What this does and when to use it.
---
```

Whole skill directories are symlinked, preserving scripts, templates and references.
The helper only replaces/prunes symlinks owned by dotfiles; existing real files,
directories and other installers' symlinks are left alone with a warning on collisions.
An unchanged, collision-free catalog produces no writes or output. The shared helper
reports name collisions (including intentional overrides) on each sync.

## Loading

Run `opencode_merge_config` after adding or renaming skills, or launch `opencode`
through the shell wrapper, which syncs before invoking the real binary. The global
OpenCode directory must already exist (normally created by OpenCode); the sync does
not create it on machines where OpenCode has not been set up.

Desktop/IDE launches and direct binary invocations bypass the wrapper: sync manually
first. Quit and restart OpenCode after changes; running sessions retain their loaded
catalog. `OPENCODE_CONFIG_DIR` can add another config directory but does not change
this sync's XDG global destination.

## Local Settings

Neither `opencode.json` nor `opencode.jsonc` is created, replaced or edited. Models,
providers, permissions, plugins and credentials remain machine-local. External
skill compatibility scans remain unchanged and may expose overlapping skill names.

There is deliberately no placeholder global `AGENTS.md`: OpenCode uses
`~/.claude/CLAUDE.md` as a fallback only when its own global `AGENTS.md` is absent.
Installing an empty one would silently suppress those existing instructions.

All shared skills are exposed unchanged, not translated. Harness-specific commands,
plugins, subagents and model references may need OpenCode-local overrides before
their workflows can execute successfully.

Runtime names come from frontmatter: the existing `remotion` and `plan` directories
are advertised as `remotion-best-practices` and `omc-plan`. The sync's override keys
are still directory basenames, as for the other tools.

## Verification

Run `zsh zsh/tests/opencode_config_test.zsh` for isolated sync and wrapper checks.
