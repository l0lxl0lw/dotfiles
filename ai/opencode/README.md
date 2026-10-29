# OpenCode Config

## Active catalog and ownership

The shared catalog contains 35 skills in `develop`, `write`, `learn`, `explain`, `git`, `use`,
`remember`, `respond`, `sentry`, and `orca`. Each skill name starts with its folder name, for example
`write/write-better` exposes `/write-better`. See the [full catalog](../shared/README.md#naming-and-catalog).

**Public skills live only in `ai/shared/skills/`.** There is no maintained
`ai/opencode/skills/` source directory. The launcher copies shared skills into immutable
runtime snapshots outside this repository; those generated copies are not editing targets.

This directory owns OpenCode-specific integration:

| Path | Purpose |
|---|---|
| `agents/` | Six research specialists and four internal planning/scoping/execution/review workers |
| `commands/` | `/track`, `/sync`, `/orca-coordinate`, `/orca-handoff` |
| `runtime/` | Resource snapshots, private/project skill discovery and execution overlay |
| `cli.json`, `settings/` | Portable global settings, browser instructions, explicit apply/import helper |
| `tracking/`, `schemas/`, `orca/`, `tests/` | Tracking/evidence helpers, record formats, Orca integration and verification |

The old six-stage workflow commands, workflow-* agents, model profiles and migration
utilities are retired. Development methods are shared skills, with native slash
commands `/develop-prepare` and `/develop-deliver`. OpenCode's built-in `/review`
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
It links shared skills and managed agents and commands into
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
python3 ~/dotfiles/ai/opencode/runtime/launch.py -- serve --hostname 127.0.0.1 --port 4096
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

OpenCode v2 exposes discovered skills through `@<name>` mentions, such as
`@sentry-bug-scan`, while built-in and explicit Markdown commands use `/<name>`.
New skills need only a `SKILL.md`, not a command file. The launcher does not generate
slash-command aliases or `/skill-<name>` fallbacks; use the native skill mention or
the skill tool, subject to normal permissions.
Nested launches remove legacy generated commands only when they exactly match
their ownership metadata, preserving edited or user-authored lookalikes. Shared
skill contents and sibling resources are included in the immutable snapshot.
Restart OpenCode from updated resources to use this behavior; running sessions
and old pinned snapshots are unchanged.

Global settings are installed as writable copies, not symlinks. See
[Global settings](#global-settings) for apply, conflict handling and explicit import.

### Learning and explanation

The `learn/` family supports crash courses, scenarios, foundations, learning plans,
gap detection, teach-back, quizzes and mental-model checks. Pass the topic or material,
goal and relevant repository path after the command. General learning stays in chat
unless a saved record is requested; codebase claims require inspecting actual source.

`/explain-code-flow` combines concept explanation and runtime tracing. Explain mode
introduces the concept before verified entry points and a call tree; debug mode follows
concrete side effects and suggests breakpoints. `/learn-quiz` and `/learn-check-model`
share grounding and teaching references with the explanation skills in `explain/_lib/`.

### Feature development and bug fixes

`@sentry-bug-scan [optional scope]` performs a read-only hunt for one concrete defect. It
uses the `codebase-analyzer` worker to challenge each candidate, independently checks
the decisive source, and reports nothing unless the trigger, expected behavior,
runtime path, impact, and missing guard are all supported by evidence.

The default path is **Prepare → Deliver**:

1. `/develop-prepare REQUEST` consolidates clarification, source research,
   requirements and implementation planning on main. It handles both new features
   and bug diagnosis/regression plans. Approve its result to publish the ticket,
   contract, research and plan.
2. **"Approved—publish and deliver through PR"**, or `/develop-deliver ISSUE_URL
   PLAN_URL` with explicit through-PR authorization, creates an Orca feature
   workspace and transfers ownership after receiver acknowledgement.
3. That owner runs fresh execution/review workers, at most three shared review/CI
   repair cycles, commits, pushes and opens a ready PR. It integrates origin/main
   by merge and waits for current-head required CI. Scope decisions or genuine
   blockers stop with the existing run key; no automatic PR merge.

See [delivery protocol](tracking/references/delivery.md) for journal commands and
recovery. Local Orca/shared filesystem is currently required.

See [the development cycle](../shared/skills/develop/README.md). Only Prepare and
Deliver register public development commands. Supporting methods are internal
Markdown references under `develop/_lib`. Brainstorming stays in main, supported
by focused research specialists and a fresh `develop-plan` worker. Only larger or
riskier preparations get an independent `develop-scope-review`. Execution and code
review remain separate workers, with code review mandatory for every delivery.
All four development agents load exact pinned methods and inherit native model
defaults. The old standalone stage commands, ticket/research stage agents and
the `/brainstorm` alias remain retired.

The ten research/development workers use `mode: subagent` without `hidden: true`.
OpenCode V2 excludes hidden agents from the model's subagent catalog, so hiding
these workers would prevent Prepare and Deliver from discovering them. Subagent
mode keeps them out of primary-agent selection without hiding them from callers.

Initial approval defines the delivery scope and Git authority; the owner advances
the cycle within that authorization and the shared three-repair budget. Outside
delivery, existing `git-*` skills still require their usual explicit requests.

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
python3 ~/dotfiles/ai/opencode/tracking/track.py configure
python3 ~/dotfiles/ai/opencode/tracking/track.py register ISSUE_URL
python3 ~/dotfiles/ai/opencode/tracking/track.py refresh
python3 ~/dotfiles/ai/opencode/tracking/track.py list
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
python3 ~/dotfiles/ai/opencode/tracking/install.py monitor
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

Published records display readable Markdown, with complete structured data retained
in hidden HTML metadata for handoffs and verification. Existing JSON-rendered comments
remain valid; new publications use the readable format.

## Orca integration

`/orca-handoff` dispatches a bounded task and returns its receipt.
`/orca-coordinate` supervises a Run and worker lifecycle when explicitly requested.
Both use [coordination rules](orca/COORDINATION.md) and the installed Orca CLI guides.

`orca/refresh_checkout.py` supports private checkout-refresh automation. `--check` is a
read-only precheck; `--apply` authorizes discarding tracked unstaged edits and a
fast-forward. It refuses staged work, local-only commits and incompatible repository
states; untracked and ignored files are preserved. Configure machine-specific targets
and schedules privately. See [Orca integration](orca/README.md).

## Global settings

The repository is the source of truth for **portable** global preferences:

| Source | Installed destination |
|---|---|
| `settings/opencode.json` | `$XDG_CONFIG_HOME/opencode/opencode.json` |
| `cli.json` | `$XDG_CONFIG_HOME/opencode/cli.json` |
| `settings/browser-preferences.md` | `$XDG_CONFIG_HOME/opencode/browser-preferences.md` |

`XDG_CONFIG_HOME` defaults to `~/.config`. JSON files and browser instructions are
writable copies: application changes cannot write through to Git. No global
`AGENTS.md` is installed. Portable preferences currently disable built-in web search
and select Google through Orca's browser using configured instructions.

```sh
opencode_settings status
opencode_settings apply
# After changing a preference inside OpenCode, explicitly select what to capture:
opencode_settings import --key /model
opencode_settings import --file cli.json --key /theme
```

The same helper works without the shell function:
`python3 -B ~/dotfiles/ai/opencode/settings/manage.py status`.
Import previews only the selected keys, asks for approval, and never commits.
`--yes` approves a preview without prompting. Whole-file import is intentionally
unavailable. Import is restricted to ordinary preference categories; integrations,
credentials and machine-specific paths must be reviewed and edited manually.
The checks are conservative safeguards, not a substitute for reviewing the Git diff.

Apply overlays tracked values while preserving unrelated local configuration.
Instruction, plugin, skill-path and watcher-ignore lists retain local/vendor entries
and add/remove only tracked contributions. Other arrays (such as ordered permission
rules) are managed as whole values, not merged as unordered sets.
Last-applied managed values are stored under
`${XDG_STATE_HOME:-~/.local/state}/dotfiles/opencode-settings/<config-id>/`.
That state excludes unrelated local settings. Backups of modified files are kept
in its `backups/` directory with mode 0600; backups may contain credentials and
must remain local. Restore one by inspecting it and copying it to its original
destination while OpenCode is stopped.

The shell wrapper and direct `runtime/launch.py` startup propagate safe changes
automatically. They preserve and report local drift instead of overwriting it.
Explicit apply stops on conflicts; use `apply --force` only to deliberately replace
changed managed values after backup. Initial migration of the old owned CLI
symlink also requires `apply --force`. Foreign settings symlinks are never replaced.
`deploy.sh --only opencode` offers a backed-up, explicit application/migration.

When both Git and OpenCode changed a managed value, choose whether to import the
local value or force-apply the tracked one. Removing a tracked key removes its
installed value only when the installed value still matches the last applied one.
**Import is never automatic.** Settings not yet tracked remain local; select a
key to import it or edit the tracked source to start managing it.

`{config_dir}` and `{repo}` in tracked JSON strings expand to installation paths.
The Orca status plugin is enabled only when its referenced local file exists;
Orca installs that plugin separately. Existing foreign plugins are preserved.
This does not install Orca or copy authentication state to a new machine.

If `opencode.jsonc` or `cli.jsonc` exists, the helper refuses settings changes rather
than stripping comments or creating a competing JSON file. Reconcile it into JSON
manually first. Invalid JSON and symlinked config directories also fail safely.
Status is read-only. Import/apply are serialized and apply checks for edits made
during confirmation before replacing files atomically.

Direct binary/desktop launches use the last installed files; use the launcher for
automatic propagation. Restart OpenCode after applying changes. Project configs,
environment overrides and managed system configuration can still override global
defaults; these are preferences, not enforced policies.

Shared skills use host-native tools and canonical resource paths. OpenCode-specific
agent/command model settings and terminal behavior live here. Skills requiring MCPs or
private adapters still require those integrations.

## Verification

```sh
zsh zsh/tests/opencode_config_test.zsh
python3 -B -m unittest discover -s ai/opencode/tests -p settings_test.py
node --test ai/opencode/tests/*.test.mjs
OPENCODE_CATALOG_SMOKE=1 python3 -B -m unittest discover -s ai/opencode/tests -p '*_test.py'
python3 -B ai/opencode/tests/catalog_smoke.py
# Opt-in live-model fresh-worker smoke (uses configured model/provider access):
python3 -B ai/opencode/tests/develop_smoke.py
```

The shell checks use an isolated HOME. Python tests cover real-Git snapshots, tracking,
handoff and evidence behavior; GitHub/Orca writes are mocked. The opt-in installed-binary
test exercises project discovery in an isolated HOME. The catalog smoke exposes this
checkout's shared skills to a temporary server without syncing the real HOME. Neither
of those checks makes model calls. The opt-in development smoke uses configured models
to prove Task-worker isolation, pinned skill loading, native worker questions and
missing-input stops. It uses read-only fixtures, not real issue publication or a full
implementation/review cycle. Real TUI appearance still needs a manual inspection.
