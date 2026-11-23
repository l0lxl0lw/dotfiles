# Hub agents

Each hub defines its workflow workers once, under `agents/src/`, and commits the
render for every host so a session started inside the hub finds them with no
linker. Edit only the sources, then:

```sh
python3 ~/dotfiles/agents/render.py --hub ~/zubot          # rewrite the committed renders
python3 ~/dotfiles/agents/render.py --hub ~/zubot --check  # fail on drift (run in the hub's tests)
```

| Generated file | Read by | Synced by `hubs_sync` as |
|---|---|---|
| `<hub>/.claude/agents/<name>.md` | Claude Code Agent tool | symlink |
| `<hub>/.codex/agents/<name>.toml` | Codex `spawn_agent` | copy, re-rendered with the machine tiers |
| `<hub>/.opencode/agents/<name>.md` | OpenCode subagents | copy, re-rendered with the machine tiers |

Codex cannot spawn symlinked roles, and OpenCode needs `provider/model` ids that
differ per machine, so those two are rendered again at sync time into the global
agent directories, carrying the render notice on their first line (after the
frontmatter fence for Markdown) so the linker recognises them as its own.

An agent file under `.claude/agents/` with no `agents/src/` entry is Claude-only:
committed as is, linked into `~/.claude/agents` with its subfolder, never rendered
for the other hosts.

## Source format

```yaml
---
name: codebase-locator        # must equal the file name
description: One line shown to the parent when it picks a worker.
tier: fast                    # fast | standard | strong | inherit
access: research              # research | draft | review | write
delegates: a, b               # write only: workers it may start
---

Prompt body, identical for every host.
```

`access` sets the permissions on each host:

| access | Claude Code | Codex | OpenCode |
|---|---|---|---|
| research | no Edit/Write/NotebookEdit | `sandbox_mode = "read-only"` | `permissions` denies `edit` |
| draft | same, plus no AskUserQuestion | read-only | denies `edit` (no documented action for questions) |
| review | no Edit/Write/NotebookEdit | parent sandbox | denies `edit` |
| write | all tools | parent sandbox | no rules |

## Model tiers

Agents name a tier; tiers files map each tier to a model per host. `inherit`,
or a tier a host does not map, uses the session's model.

```json
{
  "claude":   {"fast": {"model": "haiku"}, "standard": {"model": "sonnet"}, "strong": {"model": "opus"}},
  "codex":    {"fast": {"model": "gpt-6-luna", "effort": "medium"}},
  "opencode": {"fast": {"model": "openai/gpt-6-luna", "effort": "medium"}},
  "orca":     {"fast": {"model": "gpt-6-luna"}}
}
```

`<hub>/tiers.json` holds the hub's defaults. The machine-local
`${XDG_CONFIG_HOME:-~/.config}/dotfiles/tiers.json` overlays it host by host at
sync time, so a work machine can point OpenCode at one provider and a personal
machine at another with no commit in either hub. `--tiers FILE` on the renderer
applies the same overlay by hand. OpenCode's `effort` becomes the `#variant`
suffix. The `orca` host is read by hub skills that launch agents through
`orca agent launch --model`, not by the renderer.

`check_models.py` warns at Codex launch when a mapped Codex model is missing from
Codex's own model list (`~/.codex/models_cache.json`); fix the hub's `tiers.json`
or the machine overlay.
