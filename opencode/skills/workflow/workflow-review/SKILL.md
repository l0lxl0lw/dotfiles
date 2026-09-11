---
name: workflow-review
description: Use for /review on a GitHub issue. Independently check the actual committed/uncommitted diff against acceptance, then publish pass, changes_requested, or blocked.
---

# Review: independent acceptance gate

Read `~/dotfiles/opencode/tracking/WORKFLOW.md` once. Load compact review context with
the exact plan and optional prior Review pinned. Inspect the issue's contract and
plan before the author's claims. For an initial review, do not read previous review
bodies unless a concrete issue requires them. Work in this fresh context yourself;
no reviewer fan-out. Small-task target: 3–5 minutes, with extensions for real findings.

1. Identify the exact base/head and full intended change: committed diff, staged,
   unstaged, and untracked files. Do not miss uncommitted implementation because HEAD
   is unchanged. Inspect each changed behavior plus necessary caller/route/schema
   context. Separate user-owned unrelated changes and shared baseline defects.
2. Check each acceptance row against actual code. Look especially for a happy-path
   fixture hiding invalid input, a status-code mismatch, deletion/filter keys missing
   a scope dimension, and tests that assume one default value. Confirm production
   route wiring rather than treating a manually bound endpoint test as routing proof.
3. Read Verification evidence after forming your initial assessment. Check its
   source digest against the current snapshot. Reuse matching results; run missing,
   stale, or discriminating tests rather than rerunning every command reflexively.
   Required checks cannot be waived for speed. Do not charge unchanged baseline
   problems as introduced defects, and do not mistake optional coverage for a frozen
   acceptance requirement. A feature-specific reproduction is stronger than speculation.
4. Publish findings with severity, file/line, observed versus expected behavior, and
   the smallest corrective action. For re-review, verify previous findings against
   the new code and inspect the repair diff for regressions; do not restart broad research.

Publish **Review** using `handoff.py publish ... --verdict ... --input PLAN_URL`
and the Verification URL. Supersede the prior Review for a re-review. Verdicts:

- `pass`: required acceptance/checks satisfied for the recorded source state; no
  unresolved material findings. Non-blocking suggestions are clearly labeled.
- `changes_requested`: actionable introduced defect or missing required behavior/test.
- `blocked`: a required check or material decision cannot yet be resolved.

The comment must include source/base, acceptance coverage, evidence reused/newly run,
findings, remaining checks, and an exact next command. For changes requested, return
`/execute ISSUE_URL PLAN_URL REVIEW_URL`; for pass, `/commit ISSUE_URL REVIEW_URL`.
Never equate "review performed" with pass. No application edits, commits, or automatic
Done/issue closure. Final gate: fixes → fresh review → pass, not a summary of known bugs.
