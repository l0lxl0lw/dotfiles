---
name: develop-feature
description: Use when explicitly asked to run a feature-development stage in a fresh worker, or guide a task through ticket, research, plan, execute and independent review. Advances only at the user's request.
---

# Dispatch one development stage

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. You coordinate a single requested stage, not a supervised
background run. Do not research, implement or review in the dispatcher's context.

1. Identify the requested stage and exact issue/artifact URLs. If the user only asks
   to develop a feature, scope the next action with them; do not interpret that as
   issue creation or implementation approval. Ask for missing/ambiguous inputs.
2. Confirm execution authorization identifies the plan and, for repairs, the review.
   Ticket publication needs an explicit create/refine request. Honor no-publication
   and planning-only constraints. Stop on unresolved material product decisions.
3. Use the host's task tool to start exactly one NEW subagent named develop-ticket,
   develop-research, develop-plan, develop-execute, or develop-review for the
   selected stage. These are agent identifiers: do not prefix them with snapshot
   skill aliases. Never pass a prior task/session ID to resume a stage worker.
4. Send only the requested stage, repository/worktree, exact artifacts, authorization
   boundaries, relevant unresolved questions and repair round/history. Have the worker
   load its stage skill and return an evidence-backed handoff. Do not copy parent
   history or another worker's reasoning. If the host lacks that worker, stop and ask
   for a fresh session with the named stage skill; do not silently run it yourself.
5. Relay the result, exact URLs, verdict/blockers and next explicit action. Stop.
   Do not dispatch review after execute, repair after review, or Git after pass.

An automatic research/planning or execute-review-repair cycle is not enabled. After
two unsuccessful repair rounds, request one focused diagnosis before another repair.
