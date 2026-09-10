---
description: Develop a GitHub issue implementation plan and publish it for approval.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Issue: $ARGUMENTS

Read requirements and all comments; identify and link the relevant Research comment.
Set Planning unless the work is already Implementing/In review. Inspect actual
code and clarify material choices with the user. Produce an Implementation plan
comment with the source commit, research link, approach, affected files, ordered
steps, acceptance criteria, automated checks, and manual verification.
If revising a plan, identify the superseded comment explicitly. Resolve material
unknowns before publishing a ready plan. Set Ready when prepared, without regressing
active work. Return the exact plan URL and stop. Do not implement or create a PR.
