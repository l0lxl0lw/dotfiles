# Verification And Evidence Contract

Both entry skills use this contract. It defines portable workflow semantics, not
the schema of any repository's verification backend.

## Define Proof Before Implementation

Every acceptance ID needs concrete scenarios, fixtures, prerequisites, expected
observations, and a non-vacuity check. A green exit with zero selected tests, empty
input, skipped assertions, an unexercised path, or only a mocked boundary is not
proof of real behavior. Verify selection/counts and the intended path explicitly.

Pair cheap feedback with real proof at the boundary the AC actually promises.
Mocks/static checks may establish local logic, not service integration. For a
docs-only change, inspection and discovery checks can be the real proof; do not
invent infrastructure work. Explain non-applicable layers. Required but unavailable
proof is blocked, not excluded after the fact to make the result green.

## Cheap-Test Ladder And Bounded Repair

1. Inspect the scoped diff and run formatting/syntax/schema/static checks.
2. Run the smallest relevant unit/fixture/contract tests; confirm non-vacuity.
3. Check real-environment prerequisites read-only, including identity and safety.
4. Run targeted integration/real-system proof within the approved effect envelope.
5. Run broader or expensive suites only when the plan requires them and earlier
   gates pass. Do not repeat unaffected expensive proof without a reason.

Adapt irrelevant layers explicitly, not by silently skipping required proof. Before
each effectful run, match command, target, fixture, setup/cleanup, and remaining
attempt/time/cost budget to approval. Unavailable tools/credentials or denied
permissions are blockers, not permission to use a more powerful workaround.

On failure, capture evidence, form a specific hypothesis, and make a scoped repair.
Test the hypothesis with the cheapest discriminating check before another expensive
run. Count all expensive attempts, including failed/aborted runs. Two distinct
ineffective fixes for the same failure stop further repair attempts; budget or
safety limits may stop sooner. Record what each fix predicted and what happened.
Do not mask assertions, weaken an AC, replace required real proof with mocks, or
change unrelated code to obtain a green result.

## Repository-Local Adapter

Discover and read the target repository's local `ADAPTER.md`, especially beside
`.claude/skills/ocfo-verify-branch/`, plus relevant repository instructions. Resolve
multiple candidates through the local instructions; stop if the applicable contract
is ambiguous. Use its schema, fenced-block requirements, hash semantics, output
locations, and validation procedure. If missing, do not fabricate a contract or
install/build a backend. Non-adapter checks may proceed if approved; required
adapter proof remains blocked.

The known local CLI interface is:

```sh
python3 .claude/skills/ocfo-verify-branch/scripts/verify.py scope --base main [--spec path]
python3 .claude/skills/ocfo-verify-branch/scripts/verify.py run --plan PATH --approval approved-plan-sha256 --reviewed-diff scope-diff_sha256
```

These are invocation patterns, not literal commands with placeholder arguments.
Run from the target repo root. `scope` is read-only; use `--spec` only with the
appropriate spec identified by local docs. Read its output and review the scoped
diff, including the dirty inputs the local contract covers, before `run`. Replace
`PATH`, `approved-plan-sha256`, and `scope-diff_sha256` with the actual approved plan
path and hashes defined by the local adapter. Never invent a digest or use an old
review token after a relevant diff change. Re-scope and re-review when scope changes;
seek renewed approval only if the approved plan/effects materially change.

Explicit approval of the plan's **exact effects** suffices for the matching adapter
run. The `--approval` value binds the plan bytes; it does not itself create user
consent. Verify the approval record and matching digest first. No additional ritual
confirmation is required for unchanged approved effects, but local permissions,
prerequisites and budgets still apply. Do not bypass a refusing adapter, broaden
targets, or automatically perform git mutations to satisfy it.

## Durable Evidence

Record evidence in adjacent `progress.md` as work proceeds, not just in final chat.
Bind each proof to the plan hash, AC IDs, timestamp, repository root and tested
revision, staged/unstaged/untracked state, and content/diff fingerprints covering
relevant dirty and untracked inputs. HEAD alone does not identify dirty tested code.
Include cwd, exact command, environment/tool versions, service/fixture identity,
exit status, observed assertions/counts, durable artifact paths, effects/cleanup,
and budget consumption. Reference credentials without recording secrets.

After edits, identify which evidence is stale; re-run affected cheap checks and
required dependent proof within budget. Preserve historical results but do not
present them as proof of untested final code. If a final required rerun cannot fit
the budget, mark that AC blocked and ask for the smallest needed decision.

Use these outcome labels for each required proof and AC:

| Outcome | Meaning |
| --- | --- |
| verified | Executed on the identified state; required assertions and non-vacuity passed |
| failed | Executed and produced evidence contradicting the requirement |
| blocked | Required proof could not complete or is no longer applicable; give reason and next decision |

Track pending units in a checklist, not as evidence. "Not-run" is not an outcome;
unexecuted required verification is blocked with a reason. Explicit approved
exclusions are a separate list, never verified items. Mixed evidence must remain
visible: an AC cannot be verified while any of its required proofs fails or is
blocked. A review or successful adapter exit proves only what it actually checked.
