---
name: sentry-bug-scan
description: Find one reliable, previously unreported bug in the current codebase and explain the concrete failure with source evidence. Use only when the user invokes /sentry-bug-scan or explicitly asks for a focused bug hunt.
disable-model-invocation: true
compatibility: OpenCode with the codebase-analyzer subagent
---

# Bug Sentry

Find one real bug and explain it. This is a read-only investigation: do not edit
application code, create a fix, or perform Git writes.

## Scope the hunt

1. Confirm the current directory is a repository and read its applicable agent
   instructions. Treat arguments after `/sentry-bug-scan` as the preferred subsystem,
   symptom, or path. Otherwise choose one bounded runtime subsystem from its entry
   points, tests, and error boundaries. Exclude generated code, vendored code,
   fixtures, and purely stylistic concerns.
2. Inspect enough source to form one concrete candidate. Favor externally observable
   failures: incorrect results, crashes, data loss, authorization mistakes, broken
   error handling, or violated public contracts. A TODO, suspicious line, stale
   comment, theoretical race, or missing test is not itself a bug.
3. Do not treat unrelated uncommitted changes as defects. Do not reveal secrets from
   configuration or environment files.

## Verify with the analyzer

Delegate each candidate to a fresh `codebase-analyzer` subagent. Investigate at most
three candidates, one at a time, and stop at the first verified defect. Give the
worker a single bounded question and the decisive files already found. Require this
contract in the task prompt:

```text
Verify or reject this specific bug candidate in the current code. Trace the concrete
runtime path and establish expected versus actual behavior from callers, tests,
schema, documentation, or an invariant enforced elsewhere. Identify a realistic
trigger and observable consequence. Return VERIFIED_BUG only when every claim has
path:line evidence; otherwise return NOT_VERIFIED with the missing or contradictory
evidence. Do not propose a redesign, edit files, or investigate a different bug.
```

Use the analyzer's result as evidence, not authority. Re-read every decisive source
range yourself. When safe and practical, run the narrowest existing test or read-only
reproduction that can demonstrate the failure. Never report a candidate contradicted
by a test, validation layer, caller precondition, feature flag, or unreachable path.

## Reliability bar

A reportable bug must include all of the following:

- A specific input, state, or event that reaches the faulty path.
- The expected behavior, grounded in codebase evidence rather than preference.
- The actual behavior and user, data, security, or operational impact.
- An execution path with precise `relative/path:line` references.
- Confirmation that an existing guard does not prevent the trigger.

If no candidate clears this bar within three attempts, say that no reliable bug was
verified in the bounded search. Never weaken the standard to force a finding.

## Report

Lead with exactly one of these verdicts:

```text
VERIFIED BUG: <short title>
NO VERIFIED BUG
```

For a verified bug, report:

1. **What is wrong** — expected versus actual behavior in plain language.
2. **How to trigger it** — the smallest realistic input or state.
3. **Why it happens** — the execution path and faulty assumption, with source lines.
4. **Impact** — who or what is affected, without inflating severity.
5. **Verification** — test/reproduction result, or the exact reason execution was not
   practical.

Keep the report concise. Do not include a fix unless the user asks for one afterward.
