# OpenCode Config

## GitHub issue workflow

The complete command and agent payload from
[Agentic](https://github.com/Cluster444/agentic) is vendored into `commands/` and
`agents/`, with personal GitHub-workflow instructions layered into those files.
See `tracking/UPSTREAM.md` for the pinned source and `tracking/LICENSE.agentic` for
its license. Edit these files directly in dotfiles; the Agentic CLI is not required.

OpenCFO work uses [Azu's Tasks, organization project #4](https://github.com/orgs/opencfo-ai/projects/4).
Other repositories require an explicit project mapping; the current helper refuses
to put them on the OpenCFO board. Issues hold requirements; comments hold research,
plans, review and progress. Commands: `/ticket`, `/research`, `/plan`, `/execute`,
`/review`, `/commit`, `/sync`, `/track`. Read `tracking/WORKFLOW.md` for the contract.

Status: **Backlog → Researching → Planning → Ready → Implementing → In review → Done**.
Branch sync: **Not started / Unchecked / Up to date / Needs sync / Syncing / Conflicts / Verifying**.
The two fields are independent. Planning alone does not authorize implementation.

### Installation and migration

```
python3 ai/opencode/tracking/install.py inspect
python3 ai/opencode/tracking/track.py configure
python3 ai/opencode/tracking/install.py migrate
opencode_merge_config
python3 ai/opencode/tracking/install.py monitor
```

Inspect reports differences from upstream before migrating. Migration preserves
the original six global agents and six commands under
`~/.local/state/opencode-track/backups/` and replaces them with managed links in
the plural native directories. Foreign symlinks/collisions are not overwritten.
Configuration of field options refuses a populated project if options differ.

Quit and restart OpenCode after installation. Machine-local JSON settings remain
local. Git workflows load directly from `ai/shared/skills/git/`; project tracking
behavior remains in the OpenCode commands and tracking helper.

### Automatic detection, explicit sync

Register from each implementation worktree:

```
python3 ~/dotfiles/ai/opencode/tracking/track.py register ISSUE_URL
python3 ~/dotfiles/ai/opencode/tracking/track.py refresh
python3 ~/dotfiles/ai/opencode/tracking/track.py list
```

The macOS LaunchAgent `dev.dotfiles.opencode-track` checks every five minutes and
on load while logged in. It fetches only the target origin branch, compares Git
ancestry and updates Branch sync. It never switches branches, merges, rebases,
stashes, commits or pushes. No registrations means no network work. It catches up
on its next run after sleep/offline time. It observes registered local branches,
not every remote branch in the organization, and uses each repo's default branch.

Runtime registry and logs live under `~/.local/state/opencode-track/`; branch
registrations and local paths are not committed. Worktree directory renames are
recovered; branch renames require `/track` repair. Unresolvable branches become
Unchecked. Offline failures are recorded locally; GitHub may retain the last known
state until access recovers. Closed issues are skipped, not automatically called Done.

Request `/sync ISSUE_URL` to integrate the target branch. Conflicts are resolved
with you. After integration, Verifying remains until the workflow records actual
check results. An ancestry check cannot clear a pending verification. Normal
Up to date observations outside sync describe ancestry, not test success.

To stop monitoring:
`launchctl bootout gui/$(id -u)/dev.dotfiles.opencode-track`.
To retire a completed branch: `track.py unregister ISSUE_URL` via Python.
Re-run `install.py monitor` to load the monitor again. Tracking works while this
machine is running; it is not a server-side GitHub Action.

Verification: `python3 -B -m unittest discover -s ai/opencode/tests -p '*_test.py'`
and `zsh zsh/tests/opencode_config_test.zsh`. Git tests build isolated local
repositories and exercise parallel changes, merge/rebase conflicts, worktree
renames, verification gates, retries and offline recovery. GitHub writes are
mocked in automated tests; project fields are checked against the live API on setup.

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
providers, permissions and credentials remain machine-local. External
skill compatibility scans remain unchanged and may expose overlapping skill names.

There is deliberately no placeholder global `AGENTS.md`: OpenCode uses
`~/.claude/CLAUDE.md` as a fallback only when its own global `AGENTS.md` is absent.
Installing an empty one would silently suppress those existing instructions.

Shared skills are exposed as written, not translated. Harness-specific commands,
plugins, subagents and model references may need OpenCode-local overrides before
their workflows can execute successfully.

Runtime names come from frontmatter: the existing `remotion` and `plan` directories
are advertised as `remotion-best-practices` and `omc-plan`. The sync's override keys
are still directory basenames, as for the other tools.

## Verification

Run `zsh zsh/tests/opencode_config_test.zsh` for isolated sync and wrapper checks.
