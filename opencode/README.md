# OpenCode Config

## Active catalog and ownership

The shared catalog contains 30 skills in `write`, `learn`, `explain`, `git`, `use`,
`remember`, and `respond`. Each skill name starts with its folder name, for example
`write/write-better` exposes `/write-better`. See the [full catalog](../ai/shared/README.md#naming-and-catalog).

**Public skills live only in `ai/shared/skills/`.** There is no maintained
`opencode/skills/` source directory. The launcher copies shared skills into immutable
runtime snapshots outside this repository; those generated copies are not editing targets.

This directory owns OpenCode-specific integration:

| Path | Purpose |
|---|---|
| `agents/` | Six research specialists |
| `commands/` | `/track`, `/sync`, `/orca-coordinate`, `/orca-handoff` |
| `runtime/` | Resource snapshots, private/project skill discovery and command fallbacks |
| `tui/`, `tui.json` | Skill slash commands and command-palette integration |
| `tracking/`, `schemas/`, `orca/`, `tests/` | Tracking/evidence helpers, record formats, Orca integration and verification |

The old six-stage workflow commands, dependent agents, model profiles and migration
utilities are retired. Their history is available in Git. OpenCode's built-in `/review`
may still appear; it is not the former workflow command. Use `/git-commit` and the
other shared Git skills for Git operations.

## Setup and loading

Run `~/dotfiles/deploy.sh --only opencode`. The wizard offers missing OpenCode,
Python and GitHub CLI installations, creates the initial configuration directory,
and synchronizes tracked resources with backup/skip choices for collisions.
It respects `XDG_CONFIG_HOME`. Sign in to your provider inside OpenCode and run
`gh auth login` for GitHub workflows. Check model settings in the managed agents
and commands against your provider access. See the [root README](../README.md)
for updates, restoration and optional memory.

The shell `opencode` wrapper runs `opencode_merge_config`, then starts the launcher.
It links shared skills and managed agents, commands and TUI files into
`${XDG_CONFIG_HOME:-$HOME/.config}/opencode`. The destination must already exist;
sync does not create configuration for an assistant that has not been set up.
Foreign files and symlinks are preserved. Only retired links owned by dotfiles are
pruned. An unchanged, collision-free catalog produces no writes or output.

```sh
opencode_merge_config
opencode_workflow --prepare
opencode_workflow --doctor
opencode_workflow --doctor --github
```

`opencode_workflow` is the shell entry point for launcher diagnostics. There is no
`--profile` option: model selection uses native OpenCode settings and agent/command
frontmatter. `--prepare` prints snapshot identity without starting a model;
`--doctor --github` also checks GitHub authentication without writes.

Quit and restart OpenCode after changing configuration or the catalog. Existing
sessions and nested launches retain their original resource snapshots. Snapshots
live under `~/.local/state/opencode-workflow/` (or `OPENCODE_WORKFLOW_STATE`).
The launcher retains real HOME and credentials and preserves custom config directories,
including Orca hooks. It fails on conflicting managed/custom definitions.

Desktop/IDE launches and direct binaries bypass the shell wrapper. Configure them
to invoke the launcher for the same snapshot and skill-discovery behavior:

```sh
python3 ~/dotfiles/opencode/runtime/launch.py -- serve --hostname 127.0.0.1 --port 4096
```

Use `--live -- ...` for live catalogs without a snapshot. `OPENCODE_CONFIG_DIR`
does not change the symlink sync's XDG destination.

## Shared and project skills

Put public skills in `ai/shared/skills/<verb>/<verb>-<task>/SKILL.md`, with matching
`name` and `description` frontmatter. `git` is the deliberate tool-name exception.
Whole skill directories are symlinked by basename, preserving scripts, templates and
references. Helper directories are not registered as skills. Duplicate names within
a discovery source are rejected by the launcher.

The wrapper disables home-directory compatibility scans of `~/.claude/skills` and
`~/.agents/skills`. The launcher explicitly discovers project-local skills in
`.claude`, `.agents`, and `.opencode` between the worktree root and launch directory.
Nearer directories win; within a directory `.opencode` wins over `.agents`, then
`.claude`. Project definitions override the shared catalog without global installs.
`runtime/project-skills.js` enforces the selected definition at execution time because
native duplicate discovery can finish out of order. Native permission checks and
custom commands are preserved. Raw `debug skill` metadata can reflect another duplicate;
OpenCode's `--pure` mode disables the plugin overlay.

`tui/skill-commands.js` exposes discovered skills as slash commands and a Skills entry
in the command palette. Internal `wf-<hash>-*` snapshot aliases are hidden from both
menus but remain available by explicit reference. Existing custom/MCP commands and
TUI names or aliases take priority. Selecting a skill inserts `/<name> ` so arguments
can be entered before submission. New skills need only a `SKILL.md`, not a command file.

The launcher also generates `/skill-<name>` fallbacks referencing the exact selected
skill file, adding another `skill-` prefix if needed to avoid a collision. Shared
skill contents and sibling resources are included in the immutable snapshot.

The sync installs `tui.json` when no machine-local config occupies that path and no
`tui.jsonc` exists. For a custom TUI config, add `"./tui/skill-commands.js"` to its
`plugin` array. Restart OpenCode to load changes.

### Learning and explanation

The `learn/` family supports crash courses, scenarios, foundations, learning plans,
gap detection, teach-back, quizzes and mental-model checks. Pass the topic or material,
goal and relevant repository path after the command. General learning stays in chat
unless a saved record is requested; codebase claims require inspecting actual source.

`/explain-code-flow` combines concept explanation and runtime tracing. Explain mode
introduces the concept before verified entry points and a call tree; debug mode follows
concrete side effects and suggests breakpoints. `/learn-quiz` and `/learn-check-model`
share grounding and teaching references with the explanation skills in `explain/_lib/`.

## Private configuration

The launcher reads `~/dotfiles-private/opencode/config.json`, or the explicit
`OPENCODE_PRIVATE_CONFIG` file. This is our helper's format, not native OpenCode config:

```json
{"version":1,"skills_paths":["skills"],"tracking":{"owner":"example-org","number":1}}
```

Paths are relative to the private config file. Private skills use native `skills.paths`;
each also gets a `/<skill-name>` command containing a skill-tool reference and
`$ARGUMENTS`, not the private skill body. Duplicate private/public names and existing
command-name collisions fail explicitly. Nested launches preserve unchanged wrappers;
removed registrations lose their generated wrappers, while custom edits are preserved
and conflicts reported. Custom agent/plugin/command directories are not privately synced
through this interface.

Missing optional private config leaves the launcher usable; project mutations require
an explicit tracking target. Private files are not copied into public snapshots.
Keep credentials out of skill bodies, command arguments, public artifacts and this
configuration interface; resolve them within private adapters. Invoking a private skill
still loads its instructions into model context. Restart after registration changes.

## Tracking and evidence helpers

`/track` inspects, registers, refreshes or repairs GitHub issue/branch tracking.
`/sync ISSUE_URL` explicitly integrates a registered work branch with its target
branch using the shared Git sync skill. See [the common contract](tracking/WORKFLOW.md)
and [operations](tracking/references/operations.md) for identity, status, authorization
and partial-failure rules.

```sh
python3 ~/dotfiles/opencode/tracking/track.py configure
python3 ~/dotfiles/opencode/tracking/track.py register ISSUE_URL
python3 ~/dotfiles/opencode/tracking/track.py refresh
python3 ~/dotfiles/opencode/tracking/track.py list
```

Configuration uses the privately selected GitHub project and refuses incompatible
field options on a populated project. Sync resolves conflicts with the user, then runs
the repository's relevant checks. An ancestry check cannot clear pending verification.
Ordinary “Up to date” observations describe ancestry, not test success.

The optional macOS monitor checks registered branches every five minutes while logged
in. It fetches the target origin branch and updates Branch sync; it never switches
branches, merges, rebases, stashes, commits or pushes. No registrations means no network
work. Sleep/offline time is recovered on the next run. Registry and logs live in
`~/.local/state/opencode-track/`. Worktree renames are recovered; branch renames need
explicit repair. Closed issues are skipped, not automatically marked Done.

```sh
python3 ~/dotfiles/opencode/tracking/install.py monitor
launchctl list dev.dotfiles.opencode-track
# Stop monitoring:
launchctl bootout gui/$(id -u)/dev.dotfiles.opencode-track
```

Reinstall the monitor after moving the dotfiles checkout. Use `track.py unregister
ISSUE_URL` to retire a registration; deleting a workspace does not close its issue.
`install.py` only installs the monitor. Managed configuration uses the normal sync.

For explicitly requested structured evidence, `handoff.py` loads compact issue packets,
publishes records and evaluates readiness gates. `verify.py` runs approved check manifests
and records real exits, source/environment fingerprints and log references. See
[record formats](tracking/references/records.md) and `schemas/`. GitHub holds authoritative
records; local evidence caches do not replace them. Missing or stale proof requires
verification. A readiness gate does not authorize Git operations. These helpers do not
install stage commands or automatically start a multi-agent workflow.

## Orca integration

`/orca-handoff` dispatches a bounded task and returns its receipt.
`/orca-coordinate` supervises a Run and worker lifecycle when explicitly requested.
Both use [coordination rules](orca/COORDINATION.md) and the installed Orca CLI guides.

`orca/refresh_checkout.py` supports private checkout-refresh automation. `--check` is a
read-only precheck; `--apply` authorizes discarding tracked unstaged edits and a
fast-forward. It refuses staged work, local-only commits and incompatible repository
states; untracked and ignored files are preserved. Configure machine-specific targets
and schedules privately. See [Orca integration](orca/README.md).

## Local settings

Sync never creates, replaces or edits `opencode.json`/`opencode.jsonc`. Provider
credentials, global model overrides and optional `subagent_depth` remain machine-local.
There is deliberately no placeholder global `AGENTS.md`: OpenCode falls back to
`~/.claude/CLAUDE.md` only when its own global `AGENTS.md` is absent.

Shared skills use host-native tools and canonical resource paths. OpenCode-specific
agent/command model settings and terminal behavior live here. Skills requiring MCPs or
private adapters still require those integrations.

## Verification

```sh
zsh zsh/tests/opencode_config_test.zsh
node --test opencode/tests/*.test.mjs
python3 -B -m unittest discover -s opencode/tests -p '*_test.py'
OPENCODE_CATALOG_SMOKE=1 python3 -B -m unittest discover -s opencode/tests -p 'skill_catalog_test.py'
python3 -B opencode/tests/catalog_smoke.py
```

The shell checks use an isolated HOME. Python tests cover real-Git snapshots, tracking,
handoff and evidence behavior; GitHub/Orca writes are mocked. The opt-in installed-binary
test exercises project discovery in an isolated HOME. The final catalog smoke uses a
temporary local server to check the installed skill/command catalog after syncing.
Neither installed-binary check makes model calls.
