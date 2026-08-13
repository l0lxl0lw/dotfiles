---
name: brainstorm-then-plan
description: Scope the work with superpowers:brainstorming, then plan and implement in plan mode (Claude or codex) — not with superpowers:writing-plans or subagent-driven-development.
disable-model-invocation: true
---

# Brainstorm, Then Plan Mode

Use `superpowers:brainstorming` to scope the work. Use plan mode to plan and carry out the
implementation.

## Steps

1. Invoke `superpowers:brainstorming` and work through it with the user until the shape of
   the change is settled: what problem, what approach, what is out of scope.

2. Ask the user which planner to use — Claude plan mode or codex:

   - **Claude plan mode** — call `EnterPlanMode`, write the plan in-session, present it with
     `ExitPlanMode` for approval.
   - **codex** — invoke the `codex` skill in planning mode and bring its plan back for approval.

3. Implement the approved plan directly in this session.

## Rules

- Stop `superpowers:brainstorming` when scoping is done. It hands off to plan mode, nothing else.
- Do NOT use `superpowers:writing-plans`. The plan lives in plan mode, not in a plan file.
- Do NOT use `superpowers:subagent-driven-development` or dispatch implementation subagents.
  Write the code yourself.
- One approval gate: the plan. Do not re-ask for scope after the plan is approved.
