# Shared workflow agents

One definition per worker used by `develop-prepare` and `develop-deliver`,
rendered into each CLI's native format. Edit only the files here, then run:

```sh
python3 ai/shared/agents/render.py          # rewrite generated files
python3 ai/shared/agents/render.py --check  # fail on drift (tests run this)
```

| Generated file | Read by | Synced by |
|---|---|---|
| `ai/claude/agents/workflow/NAME.md` | Claude Code Agent tool | `claude_merge_config` |
| `ai/codex/agents/NAME.toml` | Codex `spawn_agent` | `codex_merge_config` (copies) |

Commit the generated files with their source, so the shell wrappers need no
renderer at launch. Claude Code gets symlinks. Codex
0.166 lists symlinked roles but cannot spawn them ("agent type is currently not
available"), so its sync copies each role and refreshes the copy when it changes.
A copy is recognized as managed by its first line, the render.py notice.

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

| access | Claude Code | Codex |
|---|---|---|
| research | no Edit/Write/NotebookEdit | `sandbox_mode = "read-only"` |
| draft | same, plus no AskUserQuestion | read-only |
| review | no Edit/Write/NotebookEdit | parent sandbox |
| write | all tools | parent sandbox |

Claude Code searches through Bash on some builds, so read-only roles there deny
the editing tools rather than listing the allowed ones; their prompts still
forbid changes. Review and write roles in Codex keep the parent's sandbox so
verification can write its private logs in the shared state directory.

## Model tiers

Model names change often, so agents name a tier and `tiers.json` maps each tier
to a model per host. `inherit`, or a tier a host doesn't map, means the worker
uses the session's model: the `develop-*` workers always do.

- **Claude Code** uses its own aliases (`haiku`, `sonnet`, `opus`), which follow
  new releases without edits.
- **Codex** needs exact model ids. When a provider renames a model,
  change that one line and run `render.py`. `codex_merge_config` warns at launch
  when a mapped Codex model is missing from Codex's own model list
  (`~/.codex/models_cache.json`).
