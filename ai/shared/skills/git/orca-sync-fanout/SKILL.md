---
name: orca-sync-fanout
description: When the default branch has moved, bring every Orca workspace up to date by dispatching git-sync into each agent that is behind. Surveys all Orca-managed worktrees for the current repo, reports how many commits behind each one is, waits for each agent to go idle, then sends /git-sync so it resolves its own conflicts. Triggers — "main moved, catch everyone up", "sync all my workspaces", "I just merged, update the other agents", "which workspaces are behind", "fan out the sync", "everyone rebase on main".
disable-model-invocation: true
allowed-tools: Bash(bash *), Bash(git *), Bash(gh *), Bash(orca *), Read
model: sonnet
effort: medium
---

# Orca sync fan-out

One PR lands on the default branch and every other Orca workspace is now stale. This surveys them
and hands each agent the job of catching itself up.

**Each agent syncs its own branch.** They are dispatched, not driven. An agent has the context for
its own conflicts — which of its changes matter, what it was mid-way through — and you do not. Never
resolve another workspace's conflicts from here.

## Prerequisite

`git-sync` must be worktree-safe. It is: `sync-main.sh` fast-forwards the default branch **by ref**
and integrates against `origin/<default>`, so nothing tries to check out a branch that another
worktree holds. If that ever regresses, this skill just multiplies the failure across every
workspace — fix `git-sync` first.

## Script

| Script | Purpose |
|--------|---------|
| `survey.sh [default]` | Fetch, then emit TSV: `path, display, branch, behind, terminal, issue` for every Orca worktree of this repo |

`terminal` is the Orca handle of that worktree's live agent, or `-` when none is running.
`survey.sh` scopes to the current repo by `repoId`, skips the main worktree, and writes its progress
to stderr so stdout stays parseable.

## Steps

### Phase 1: Survey

1. ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/orca-sync-fanout/scripts/survey.sh'
   ```

2. Show the user a table of every workspace with `behind > 0` — display name, branch, commits
   behind, linked issue, and whether an agent is live. **If nothing is behind, say so and stop.**
   Do not dispatch a sync that has nothing to do.

3. A `behind` of `?` means git could not read that worktree (removed on disk, or mid-creation).
   Report it; do not dispatch to it.

### Phase 2: Confirm

4. Dispatching types into other people's running agents. Confirm the list with `AskUserQuestion`
   before sending anything — all of them, a subset, or cancel. Never fan out unprompted.

### Phase 3: Dispatch

5. For each confirmed workspace **that has a live terminal**, wait for the agent to finish what it
   is doing, then send:

   ```bash
   orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 120000 --json
   orca terminal send --terminal <handle> --text "/git-sync" --enter --json
   ```

   Wait for idle rather than `--interrupt`. Interrupting cuts into work in flight, and a sync is
   almost never urgent enough to justify that. If the wait times out the agent is genuinely busy —
   report it as skipped and move on rather than forcing it.

   `/git-sync` is model-invocable, so the receiving agent runs it without needing the user to
   confirm the invocation itself. It still asks the user about every conflict it resolves.

6. For a workspace with **no live terminal** (`-`), do not spawn an agent silently. Report it with
   the command the user can run:

   ```bash
   orca terminal create --worktree <full-selector> --command "claude"
   ```

   Full selectors are the `<repo-id>::<abs-path>` values in `orca worktree list --json`.

### Phase 4: Report

7. One table: workspace, commits behind, and outcome — **dispatched**, **skipped (busy)**,
   **skipped (no agent)**, or **unreadable**.

8. State plainly that dispatch is not completion. Each agent still has to run its own sync, and any
   of them may hit conflicts that need that agent's user. Do not report the fleet as "synced".

## Rules

- Confirm before dispatching — always, via `AskUserQuestion`
- Wait for idle; never `--interrupt` unless the user explicitly asks
- Never resolve another workspace's conflicts from here
- Never spawn agents in workspaces that have none — surface the command instead
- Skip workspaces already at 0 behind; a no-op dispatch is noise in someone else's terminal
- Report dispatched ≠ synced

## Common mistakes

- **Dispatching before checking `git-sync` works in a worktree.** Five broken syncs instead of one.
- **Interrupting busy agents.** The sync is rarely worth the work you just cut off.
- **Reporting success after dispatch.** You sent a message; nothing is synced yet.
- **Fanning out to every repo.** `survey.sh` scopes by `repoId` — do not widen it by hand.
- **Resolving conflicts centrally "to save time."** You do not have the context, and the agent does.
