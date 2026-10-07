---
name: orca-handoff
description: Hand off a bounded task to another Orca workspace or existing agent terminal, report its delivery receipt, and stop. Use for explicit full handoffs, not supervised coordination or ordinary local delegation.
---

# Orca handoff

Transfer ownership, deliver the brief, report the receipt, then stop. Do not create
Run/task tracking, dispatch a supervised worker, poll completion, or treat idle as
proof of completed work. Supervision requires the separate coordination workflow.

## Decide scope before running the helper

1. Confirm the repository/current worktree, requested outcome, owned paths,
   acceptance checks, exact source refs and artifact/issue URLs (if any), and
   authorized edits/Git operations. Ask only about material missing scope.
   Handoff authorization does not authorize commits, pushes, PRs, issue creation,
   or transferring uncommitted patches. A new worktree does not contain those edits.
2. Default to an independent worktree, configured repo base, and OpenCode's
   configured launch defaults. No model/effort overrides. Use a different installed
   agent only when requested. Stacked/base-specific work is outside this helper's
   independent-create mode; consult the live contract rather than silently changing
   lineage. Preserve setup `inherit` unless explicitly overridden.
3. Write a self-contained brief with ownership, context, acceptance checks,
   permissions, and the requirement to report actual implementation/verification
   results to the user. Do not add a supervised lifecycle contract.
4. Choose one stable, unique operation key **before any mutation** and retain it
   in the conversation. Never start another key to recover the same handoff.

## Load the live contract

Resolve `ORCA_CLI_COMMAND` as a single executable; otherwise use installed `orca`
on PATH. Only explicitly selected dev/Linux sessions may set it to the appropriate
`orca-dev`, worktree dev launcher, or `orca-ide` supported by their live guide.
Never interpret the variable as shell code or automatically switch runtimes.

Read that executable's `status --json`, `skills get orca-cli`,
`worktree create --help`, and `terminal send --help`. The installed guide overrides
version-dependent commands and envelopes. If incompatible, stop and report; do
not invent a fallback. The helper also checks and journals these reads on start
and resume. It requires durable prompt delivery support.

## Execute from the physical skill directory

Resolve this loaded SKILL.md's physical directory (including symlinks or pinned
snapshots); use its [scripts/handoff.py](scripts/handoff.py). All subprocess calls
use literal argv. Python 3.9+ on macOS/Linux is required.

```sh
python3 /absolute/skill/directory/scripts/handoff.py start \
  --key login-fix-20261007 --repo 'path:/absolute/repo path' \
  --name login-fix --brief-file '/absolute/login brief.txt'
```

The helper creates agent-first with `--no-parent --agent opencode`, without a
prompt or base override. It extracts the complete worktree ID and one agent
handle, inspects the terminal, waits for `tui-idle` for 60 seconds and at most one
120-second retry, then sends text+Enter with `--wait-submit 10 --json`.

For a user-identified existing agent, first use `terminal show` and `terminal read`
to judge whether handing it this task is appropriate. The helper repeats those
reads, validates the agent/process, and waits before sending:

```sh
python3 /absolute/skill/directory/scripts/handoff.py start \
  --key existing-login-fix-20261007 --terminal term_EXACT_HANDLE \
  --brief-file '/absolute/login brief.txt'
```

## Recovery and reporting

Read [README.md](README.md) for recovery invocations and limitations.
State is outside source repositories under `${XDG_STATE_HOME:-~/.local/state}/orca-handoff/KEY`.
It contains the brief, target, raw CLI responses, and mutation intents; preserve
it, and treat it as private data. Use `inspect` or `resume` with the **same key**.

- A lost create response is not permission to create again. Reconcile with
  documented worktree/terminal listing; `adopt` requires an explicitly identified
  full workspace ID and never creates a terminal.
- A send timeout or silence is not permission to send again. With a known durable
  ID, resume replays only the exact send plus `--retry-request ID`. Without an ID,
  stop and give identifiers/log locations and manual inspection instructions.
- Re-list stale handles. Before initial send, select only one matching process;
  never dual-deliver. After a send attempt, never move the prompt to a replacement
  handle/process. If exact-command replay cannot be proven safe, stop.
- Readiness exhaustion is a blocker, not a reason to bypass waiting. No prompt was
  sent; report the saved terminal and wait results for manual inspection.

Return workspace path/full ID, branch, agent handle, state key/directory, durable
request ID, receipt stages and warnings. Say **input accepted** when `accepted`
is true; say **turn started** only when the receipt includes `turn_started`.
Accepted-but-unproven is still the end of the full handoff. Do not promise
exactly-once runtime execution or claim the task itself is finished.

After installing this skill or changing its routing, quit and restart OpenCode.
