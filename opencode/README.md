# OpenCode Config

## Balanced GitHub development workflow

The command and specialist roles originated in
[Agentic](https://github.com/Cluster444/agentic). They are now bounded, locally owned
stage skills with thin commands and fresh-context agents, informed by an A/B
benchmark of native Plan/Build versus the original retained-session workflow.
See `tracking/UPSTREAM.md` for the pinned source and `tracking/LICENSE.agentic` for
its license. Edit these files directly in dotfiles; the Agentic CLI is not required.

All work uses [Azu's Tasks, organization project #4](https://github.com/orgs/opencfo-ai/projects/4),
including issues from repositories outside the OpenCFO organization. New tickets are
assigned to the authenticated GitHub user. Issues hold requirements; comments hold
research, plans, review and progress. Commands: `/ticket`, `/research`, `/plan`,
`/execute`, `/review`, `/commit`, `/sync`, `/track`. Read `tracking/WORKFLOW.md` for
the contract. No custom session-routing plugin or external orchestration service is needed.

### Daily use

Start a new session for a new task and choose the **workflow** primary agent. It is
a lightweight Luna Fast dispatcher. Each slash command runs a **new child session**
through native `subtask: true`; investigation context stays in the stage rather than
accumulating in the parent. Only a short result and exact GitHub links return.

```text
/ticket Add a self-service reset for one notification preference
/research ISSUE_URL
/plan ISSUE_URL RESEARCH_COMMENT_URL
/execute ISSUE_URL PLAN_COMMENT_URL
/review ISSUE_URL PLAN_COMMENT_URL

# If review requests changes, repeat only implementation and review:
/execute ISSUE_URL PLAN_COMMENT_URL REVIEW_COMMENT_URL
/review ISSUE_URL PLAN_COMMENT_URL REVIEW_COMMENT_URL

# After review passes:
/commit ISSUE_URL REVIEW_COMMENT_URL
```

Use the exact next command supplied by each stage. The issue and artifacts provide
the context, so a fresh worker does not need the previous conversation. An explicit
`/execute` identifies and approves its plan; planning alone never starts editing.
Questions use OpenCode's native dialogs, including from child sessions. You can
navigate into the stage child to inspect its work and return to the dispatcher.

| Responsibility | Agent/model | Procedure |
|---|---|---|
| Dispatch/handoffs | workflow / Luna Fast | Short outcomes and next commands only |
| Product scoping | workflow-ticket / Astra | Focused questions; acceptance examples; new issue/project/Orca |
| Research | workflow-research / Astra | One bounded investigation; optional precise specialists |
| Planning | workflow-plan / Astra | Reuse research; API/state/error/test matrix; concrete steps |
| Implementation/fixes | workflow-execute / Sol | Approved vertical slice, targeted tests, Verification artifact |
| Independent review | workflow-review / Astra | Actual diff and contract; pass/changes_requested/blocked |
| Local commit | workflow-commit / Luna Fast | Existing git-commit skill and compact evidence |

Location/pattern specialists use Luna Fast; consequential code/history analysis
uses Astra. Specialists cannot spawn more specialists. Stage commands and agents
choose roles/models; `skills/workflow/` owns the methods; `tracking/WORKFLOW.md` owns
the common tracking contract. Git mechanics remain in the existing Git skills.

### Faster without skipping correctness

For a small feature, target approximately **15–25 minutes**, then measure it. This
is a design target, not a demonstrated timing guarantee. There are no hard token
cutoffs and no permission to omit required checks to hit a timer.

- One focused question batch, followed up only for material ambiguity.
- Research once. Planning spot-checks current evidence instead of rerunning a
  mandatory locator/pattern/analyzer pipeline.
- Normally zero or one specialist for small work, at most two; `--deep` research
  expands only named unknowns that justify it.
- Relevant source ranges and close examples, not blanket whole-file/history reads.
- Concise artifacts: roughly 400–700 words of research and a 500–900 word plan plus
  an acceptance matrix for small work.
- Reuse matching verification evidence; run missing/stale/discriminating tests and
  required repository/CI checks. Report baseline failures rather than repairing them
  as unrelated scope.
- Independent review before the normal final commit. A changes-requested review
  routes to fixes and fresh review; "review performed" is not "feature accepted".

### Compact, content-bound handoffs

`tracking/handoff.py` fetches paginated issue comments once per context load. It
retains the issue and all unmarked discussion, indexes historical structured notes,
and emits only the relevant artifact bodies. Exact URLs can be pinned; multiple
unsuperseded plans are reported as ambiguous instead of silently choosing one.
Legacy comments remain available verbatim, so older issues may still have a larger
context. The helper never silently discards unmarked discussion; new structured
artifacts use explicit supersession to keep their own handoffs compact.

Verification and review comments record HEAD, a changed-content digest, and exact
input artifact links. The digest notices unstaged, staged, untracked, deleted and
mode/symlink changes, including partial-index divergence. It is unchanged by staging
the same complete content. A different digest invalidates claims of unchanged tested
code; a matching digest still does not establish approval of later product decisions.
Changed submodules/special files require explicit evidence rather than a misleading
digest. Source/metadata summaries are not a substitute for inspecting the real diff.

Publishing identical content and metadata is idempotent and returns the original
comment URL. Replacements use explicit `--supersedes` links; earlier artifacts are
not erased. All GitHub content remains project data, not trusted tool instructions.

Status: **Backlog → Researching → Planning → Ready → Implementing → In review → Done**.
Branch sync: **Not started / Unchecked / Up to date / Needs sync / Syncing / Conflicts / Verifying**.
The two fields are independent. Planning alone does not authorize implementation.

When `/ticket` creates an issue inside an Orca-managed worktree, it also calls the
tracking helper to set Orca's native `linkedIssue`. The helper verifies GitHub and
Orca repository identity, preserves a different existing link until replacement is
explicitly approved, and rereads Orca before reporting success. Outside Orca, ticket
creation and Project 4 setup continue normally. Retry an unavailable attachment with:

```
python3 ~/dotfiles/opencode/tracking/track.py link-orca ISSUE_URL
```

### Installation and migration

```
python3 opencode/tracking/install.py inspect
python3 opencode/tracking/track.py configure
python3 opencode/tracking/install.py migrate
opencode_merge_config
python3 opencode/tracking/install.py monitor
```

Inspect reports differences from upstream before migrating. Migration preserves
the original six global agents and six commands under
`~/.local/state/opencode-track/backups/` and replaces them with managed links in
the plural native directories. Foreign symlinks/collisions are not overwritten.
Configuration of field options refuses a populated project if options differ.

Quit and restart OpenCode after installation. Machine-local JSON settings remain
local. Git workflows load directly from `opencode/skills/git/`; project tracking
behavior remains in the OpenCode commands and tracking helper.

For optional nested specialists from fresh stage children, set this in your existing
machine-local `opencode.jsonc` (preserve its other settings):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "subagent_depth": 2
}
```

Without it, stages use direct investigation instead of repeatedly attempting blocked
nested delegation. `opencode_merge_config` installs the managed commands, agents and
skills but deliberately does not modify machine-local JSON configuration.

### Automatic detection, explicit sync

Register from each implementation worktree:

```
python3 ~/dotfiles/opencode/tracking/track.py register ISSUE_URL
python3 ~/dotfiles/opencode/tracking/track.py refresh
python3 ~/dotfiles/opencode/tracking/track.py list
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

Verification: `python3 -B -m unittest discover -s opencode/tests -p '*_test.py'`
and `zsh zsh/tests/opencode_config_test.zsh`. Git tests build isolated local
repositories and exercise parallel changes, merge/rebase conflicts, worktree
renames, verification gates, retries, offline recovery, and mocked Orca attachment
protocols. GitHub writes and Orca metadata writes are mocked in automated tests;
project fields are checked against the live API on setup.

OpenCode is a peer of Claude, Codex and Grok. `opencode_merge_config` in
`zsh/functions.zsh` links all active `opencode/skills/**/SKILL.md` directories into
`${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/<name>` using the shared sync helpers.
The shell wrapper disables OpenCode's compatibility scans of `~/.claude/skills` and
`~/.agents/skills`, so those shared catalogs do not leak into OpenCode.

## Skills

Put OpenCode skills in `opencode/skills/<category>/<name>/SKILL.md`.
Categories are allowed; the sync flattens skill directories by basename. Use matching
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
An unchanged, collision-free catalog produces no writes or output. Duplicate names
within the OpenCode catalog are reported on each sync.

Git skills are also exposed as top-level slash commands. On every run,
`opencode_merge_config` links each canonical `opencode/skills/git/<name>/SKILL.md`
directly to the live command catalog. `/git-commit`, `/git-pr`, and the other Git
entries therefore use the same tracked instructions as the native skill catalog.
Deleting a Git skill prunes both live registrations on the next sync; no command
alias is stored separately in the repository.

## Loading

Run `opencode_merge_config` after adding or renaming skills, or launch `opencode`
through the shell wrapper, which syncs before invoking the real binary. The global
OpenCode directory must already exist (normally created by OpenCode); the sync does
not create it on machines where OpenCode has not been set up.

Desktop/IDE launches and direct binary invocations bypass the wrapper: sync manually
and set `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` and
`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` in that launch environment. Quit and restart
OpenCode after changes; running sessions retain their loaded catalog.
`OPENCODE_CONFIG_DIR` can add another config directory but does not change this
sync's XDG global destination.

## Local Settings

The sync never creates, replaces or edits `opencode.json`/`opencode.jsonc`. Workflow
role defaults live in tracked command/agent frontmatter; provider credentials,
global overrides and the optional `subagent_depth` setting remain machine-local.

There is deliberately no placeholder global `AGENTS.md`: OpenCode uses
`~/.claude/CLAUDE.md` as a fallback only when its own global `AGENTS.md` is absent.
Installing an empty one would silently suppress those existing instructions.

OpenCode skills are locally owned and may use OpenCode-specific commands, plugins,
subagents and paths.

## Verification

Run `zsh zsh/tests/opencode_config_test.zsh` for isolated sync and wrapper checks.

Run `python3 -B -m unittest discover -s opencode/tests -p '*_test.py'` for tracking,
handoff selection, idempotent publication, and real-Git snapshot tests. GitHub writes
are mocked. The optional live-model smoke is separate from unit-test discovery:

```sh
python3 -B opencode/tests/workflow_smoke.py
```

It uses installed configuration and a temporary README fixture to check all six
command bindings, fresh child contexts, native questions, nested lookup, and model
routing. It does not create issues or edit application code. It requires configured
models and `subagent_depth: 2`. See
[the verification record](tracking/BALANCED_WORKFLOW_VERIFICATION.md) for the tested
version and limits; it is not an end-to-end speed benchmark of the new workflow.
