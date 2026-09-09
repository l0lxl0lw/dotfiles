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

## Automatic Fresh Implementation

This integration is temporarily disabled in favor of Superpowers. Its command,
server plugin, and TUI config remain under `.disabled` filenames for restoration.

On **OpenCode 1.18.30**, the shared `brainstorm-then-plan` skill can finish with
one native popup approving the exact plan AND starting implementation in a fresh
root session. It only takes this path when `prepare_plan_handoff` is actually in
the tool catalog. Other harnesses keep the manual approval-and-stop workflow.

1. The preparation tool sends the plan/progress hashes, absolute path, source
   session/message IDs, directory and material effects to the visible local TUI.
   It returns immediately; the assistant must finish its turn. It does not approve,
   create a session, invoke a model, or wait for its own source to become idle.
2. The TUI requires tool-completion metadata AND source idle, checks that the source
   is still visible and unchanged, and verifies the command and Build agent. It
   then opens `DialogConfirm`. Confirm approves the displayed SHA-256 and effects,
   including the Plan-to-Build permission transition. Cancel/Escape starts nothing.
3. Only Confirm appends approval provenance to adjacent `progress.md`. The plan is
   never modified. The TUI navigates locally to `home`, like `/new`, and waits for
   the mounted native home prompt. It does not overwrite an unsent draft.
4. After one final hash/source/lifecycle check, the TUI sets only
   `/implement-plan <absolute-plan-path>` with empty parts and calls that prompt's
   native `submit()` once. Native OpenCode handles root creation, command parsing,
   model/variant selection and local navigation. There is no session API submission,
   broadcast `tui.selectSession`, fork, compaction, transcript copy, or worker.

The old transcript stays available. This uses **ordinary native submission
semantics**, not a fabricated session-hydration acknowledgment. Native OpenCode
dispatches the slash command before its delayed session-route navigation. We do not
add stronger guarantees than pressing Enter normally provides. The command must be
present in the native command catalog; preflight checks the server catalog. The
host's own command-cache loading, provider errors, submission guards and navigation
behavior still apply. Native `PromptRef.submit()` returns no completion result, so
an approval record is not evidence of a successful submission or implementation.
There is never an automatic retry or a switch to another submission mechanism.

### Files And Installation

| Tracked file | Purpose |
| --- | --- |
| `plugins/fresh-session.js` | Auto-discovered server plugin providing the preparation tool only |
| `handoff/transport.mjs` | Private Unix-socket preparation transport, no SDK broadcasts |
| `handoff/common.mjs` | Canonical path checks, snapshots, SHA-256 and approval recording |
| `handoff/native.mjs` | Single-use approval/native-prompt controller |
| `handoff/tui.mjs` | Public TUI module, prompt slots, events and disposal |
| `commands/implement-plan.md` | Explicit primary Build command, not a subtask; shared skill remains the implementation contract |
| `tui.json` | Default explicit TUI plugin registration |
| `tests/handoff.test.mjs` | Mocked controller and headless module/Unix-socket tests |

`opencode_merge_config` links the server plugin and command into the global native
directories, and the module directory as `dotfiles-handoff`. It links the default
`tui.json` **only when it does not collide with machine-local config**. TUI plugins
are not auto-discovered. If `tui.json` or `tui.jsonc` already belongs to the machine,
the helper preserves it and warns; add `./dotfiles-handoff/tui.mjs` to its `plugin`
array to opt in. Foreign command/plugin files and links are also preserved. A
conflicting command causes preflight to stop, not silently override its behavior.

Quit and restart OpenCode after syncing. Direct binary and IDE launches still need
manual sync. The server entry resolves `@opencode-ai/plugin` from the existing XDG
global installation, including when loaded through a dotfiles symlink. It adds no
dependencies and does not update the installed 1.18.11 SDK/plugin packages. The TUI
module uses host API components directly, without bundling Solid or OpenTUI.

### Safety Boundaries

- Local Unix TUI only. A private mode-0700 directory under
  `/tmp/opencode-handoff-<uid>` holds unique per-TUI sockets. Successful Unix-socket
  communication proves co-location; matching paths, localhost URLs, or remote
  filesystem content do not. Multiple visible local clients cause preparation to
  fail. Only the confirming TUI navigates; no other client's route is changed.
- Only root sources without `workspaceID` or session-specific permission rules,
  whose directory exactly matches the native home destination. Remote workspaces,
  subagents and moved sessions with differing destinations are rejected.
- The command must match the tracked template, use `build`, and have `subtask:
  false` with no model override. Build must be visible and primary, without its
  own model/variant override. The currently selected native model/variant and TUI
  permission mode remain native-owned; the popup explicitly approves Build rules
  replacing Plan restrictions. No permission grants are copied or bypassed.
- Plans must be regular, non-symlink files under
  `~/.agents/plans/<project>/<task>/plan.md`. Plan/progress files are capped at
  512 KiB and must not be hardlinked. Paths use ASCII letters/digits, spaces,
  dots, underscores, slashes and hyphens, excluding command-template shell or
  attachment syntax. Both plan and progress changes invalidate preparation.
- One preparation per source assistant message, ten-minute expiry, and a
  three-second home-prompt availability limit. Nothing is replayed on restart.
  Closing a popup, changing source/user turn/directory/configuration, deactivating
  the plugin, or losing the native prompt stops the handoff without retry.
- The native confirmation dialog does not scroll. Approval text must fit the
  terminal (checked conservatively before opening the extra-wide dialog). Keep
  the effects summary concise; if it does not fit, enlarge the terminal or shorten
  the summary and explicitly prepare again. Hidden/clipped effects are not approved.
- The plugin wraps `home_prompt` and `session_prompt` with the same native Prompt
  component, forwarding normal callbacks and right-hand slots. During an approved
  home arrival only, it suppresses the host Home ref callback, which could otherwise
  seed and auto-submit an old CLI `--prompt`. It does not copy that startup input.
  Other prompt-replacement plugins can conflict; missing refs stop the handoff.
- A failure after approval may leave an approval record or native input but starts
  no alternate workflow. Once native submit is called, native user semantics own
  its in-flight work. The implementation skill rechecks approval and hash on entry.
  Fix the reported problem before explicitly preparing again in a new user turn.
- Clean shutdown removes the socket. A crash may leave an inert socket; stale
  sockets are never trusted or automatically unlinked by another TUI. If more than
  64 accumulate, preparation stops and asks for manual cleanup.

### Verification And Sources

Run `node --test ai/opencode/tests/handoff.test.mjs` (also supported by
`bun test ai/opencode/tests/handoff.test.mjs`) and
`zsh zsh/tests/opencode_config_test.zsh`. Tests cover approval provenance,
cancel/Escape, missing UI, changed plan/progress, duplicate events, source drift,
navigation failures, drafts, lifecycle disposal, local socket selection, unsupported
permissions/workspaces, template-safe paths and no direct session API/context copy.
The real TUI module is initialized/disposed with a mocked host, not a model session.
These tests do not prove physical popup rendering or successful provider execution.
No live implementation session is part of automated verification.

Authoritative v1.18.30 sources used for this integration:

- [Public TUI types](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/plugin/src/tui.ts): no top-level `api.prompt`; refs are acquired through prompt slots and `api.ui.Prompt`.
- [Native prompt](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/tui/src/component/prompt/index.tsx): `set`/`submit`, reentrancy guard, slash parsing, session creation and delayed local navigation.
- [Home](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/tui/src/routes/home.tsx): `home_prompt` slot and startup `--prompt` seeding.
- [App commands](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/tui/src/app.tsx): `session.new` navigates home and clears dialogs.
- [Command resolution](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/session/prompt.ts): command agent/model precedence and argument/template expansion.
- [TUI plugin specification](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/specs/tui-plugins.md): explicit `tui.json` registration and default `{ id, tui }` export.
- [Published TUI schema](https://opencode.ai/tui.json) and [config schema](https://opencode.ai/config.json): plugin array and command fields.

The TUI plugin refuses other host versions until their native path is reviewed.
