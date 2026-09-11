---
name: workflow-commit
description: Use for the /commit workflow command. Perform a compact issue/evidence handoff, then delegate Git mechanics to the existing git-commit skill.
---

# Commit: preserve the reviewed result

Read `~/dotfiles/opencode/tracking/WORKFLOW.md` once. If an issue is supplied, load
`handoff.py context ISSUE --stage commit` with any exact Review/Verification URLs.
Inspect unresolved findings and match the recorded review digest to the current
source snapshot. If code changed since review, the prior pass is stale: name the
delta and recommend fresh `/review` before declaring the task ready. Do not silently
carry a review pass across content changes or partial-index differences.

Use the existing **git-commit** skill at
`~/dotfiles/opencode/skills/git/git-commit/SKILL.md` for all Git mechanics and normal
native-question confirmation. Inspect status, the intended diff, and recent history;
stage only intended files. Do not re-read ticket research or re-run verified tests
when neither code nor assumptions changed. Small-task target: under a minute.

Default workflow order is review pass → commit. If the user explicitly requests an
earlier/WIP commit, honor the Git request but preserve outstanding findings and do
not describe it as review-ready. A plain `/commit` without an issue still uses the
Git skill; do not invent a ticket or new approval ceremony.

Return the commit SHA, associated issue/review links when present, and the actual
readiness state. A local commit is not a push, PR, merge, or Done status. GitHub PR
publication, merge and cleanup continue to use the existing separate Git skills.
