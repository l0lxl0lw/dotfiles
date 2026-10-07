# Deterministic Orca handoff helper

The skill owns scope and permissions; `scripts/handoff.py` owns create → inspect →
bounded readiness → send → receipt. It does not track worker completion.
Contract checked against installed Orca **1.4.206**, including its version-matched
`orca-cli` guide, create/send/wait help, and packaged CLI receipt/error formatting.
Standard library only; Python 3.9+, macOS/Linux.

From the dotfiles checkout:

```sh
python3 ai/shared/skills/orca/orca-handoff/scripts/handoff.py start \
  --key fix-login-20261007 --repo 'path:/Users/me/project with spaces' \
  --name fix-login --brief-file '/tmp/login brief.txt'

python3 ai/shared/skills/orca/orca-handoff/scripts/handoff.py inspect --key fix-login-20261007
python3 ai/shared/skills/orca/orca-handoff/scripts/handoff.py resume --key fix-login-20261007
```

`--terminal term_HANDLE` replaces `--repo`/`--name` for existing-terminal handoff.
`--agent` defaults to `opencode`. `--setup run|skip|inherit` is optional for creation;
omission preserves Orca's inherited policy. Independent creation omits
`--base-branch`; Orca chooses the configured repository default. No model flags,
`--prompt`, fallback shell creation, or settings changes are used.

`ORCA_CLI_COMMAND='/absolute/path with spaces/orca'` selects one executable,
never a shell expression. Otherwise `orca` is resolved on PATH. Explicit dev/Linux
selection uses this same variable after reading that build's guide. Remote target
environment variables are recorded and must match on resume. Resume uses the
recorded executable even if PATH or `ORCA_CLI_COMMAND` changes.

## State and recovery

Default location: `${XDG_STATE_HOME:-~/.local/state}/orca-handoff/KEY`.
`--state-dir /absolute/external/directory` overrides the root on every invocation.
Directories inside Git checkouts are refused. Files are private by default and
contain the full brief, remote selector/credentials if present, raw responses,
and exact argv. Do not publish them. Keep one key for each logical handoff.

The write-ahead state is atomically replaced and fsynced before mutations.
Raw stdout/stderr are captured to separate files so a parsed result can be
recovered after a helper crash. A per-key OS lock excludes concurrent helpers.

| Situation | Behavior / recovery |
|---|---|
| Create response complete | Resume consumes saved response, uses returned agent; no duplicate create |
| Create timed out, partial, malformed, or lost | Never create again automatically; list worktrees with the original repo selector and inspect terminals; explicitly adopt the verified workspace |
| One readiness wait unsatisfied | One larger retry (60s then 120s); each attempt persisted before execution |
| Both waits consumed, including crash/timeout | Fail closed; no send, no automatic reset; inspect the saved terminal manually |
| Accepted, without `turn_started` | Success with warning; stop. Resume returns saved receipt without another CLI send |
| Send failed ambiguously with durable ID | Resume reissues exact saved command plus `--retry-request ID`, once per resume; runtime owns replay semantics |
| Send lost without durable ID | Stop. Inspect logs and terminal output; no guessed request ID, unkeyed retry, or new-key workaround |
| Stale handle before initial send | Re-list; match original PTY then verify incarnation with `terminal show`; if identity was not yet saved, require one matching agent in the exact workspace |
| Handle/process replaced after send | Save re-list evidence and stop; do not redirect the accepted/ambiguous prompt |

Manual creation reconciliation (after verifying this is the exact workspace):

```sh
orca worktree list --repo 'path:/Users/me/project with spaces' --json
orca terminal list --worktree 'id:REPO_ID::/absolute/new workspace' --json
python3 ai/shared/skills/orca/orca-handoff/scripts/handoff.py adopt \
  --key fix-login-20261007 --worktree-id 'REPO_ID::/absolute/new workspace'
python3 ai/shared/skills/orca/orca-handoff/scripts/handoff.py resume --key fix-login-20261007
```

Substitute the originally selected executable for `orca`. Adoption records an
explicit operator decision; it does not infer ownership from a matching name.
There is no documented CLI create-retry flag in the checked version. Runtime
create-idempotency capability alone is insufficient to invent one.

Exit **0** means the requested action completed: start/resume obtained acceptance,
or inspect/adopt completed their read/reconciliation. Exit **2** means blocked;
JSON includes available identifiers and recovery instructions. `inspect` and
`adopt` never send. Only `receipt_stages` containing `turn_started` proves a turn
began. Top-level CLI envelope `id` is not a durable prompt request ID.

### Limits

This provides at most one **unkeyed send attempt per retained operation key**,
not a universal exactly-once guarantee. Orca's durable request/process identity
governs keyed replay. Killing the CLI before it reports its request ID, losing the
state directory, using a new key, external sends, or terminal process replacement
can make automatic recovery impossible. Unknown outcomes stay unknown. A crash
after persisting intent but before spawning the CLI deliberately requires
reconciliation even if the command never ran. No generic error is treated as
proof that a mutation failed.

## Verification and discovery

```sh
python3 -B -m unittest discover -s ai/shared/skills/orca/orca-handoff/tests -p '*_test.py'
python3 -B -m unittest discover -s ai/opencode/tests -p 'skill_catalog_test.py'
```

Tests use a separate fake executable, temporary state and argv logs; they never
launch real agents or change Orca settings. The shared catalog installer and
OpenCode snapshot loader include this skill's helper/resources. OpenCode's
`/orca-handoff` command routes to the shared skill. Sync configuration through the
normal launcher, then **quit and restart OpenCode** to discover the change.
