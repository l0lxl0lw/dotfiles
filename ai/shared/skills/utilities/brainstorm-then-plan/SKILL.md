---
name: brainstorm-then-plan
description: Scope the work with superpowers:brainstorming, then plan it in plan mode (Claude or codex). Ends at the approved plan — implementation happens in a fresh session via implement-plan, not here.
disable-model-invocation: true
model: opus
effort: high
---

# Brainstorm, Then Plan

Scope the work, produce an approved plan, hand off. **This skill does not implement.**
Implementation runs in a fresh session under `implement-plan`, on a cheaper model, with none
of the brainstorming transcript in context.

## Steps

1. **Orient before asking.** If the repo has a graphify graph (`graph.json` at the repo root
   or a `graphify` MCP server), query it — `/graphify query`, `/graphify path A B`,
   `/graphify explain X` — to find the entry points, callers and neighbours you need.
   Read the specific files it points at. Do NOT dispatch exploration subagents to go
   read the codebase for you; if there is no graph, grep and read directly.

2. Invoke `superpowers:brainstorming` and work through it with the user until the shape of
   the change is settled: what problem, what approach, what is out of scope.

3. Ask the user which planner to use — Claude plan mode or codex:

   - **Claude plan mode** — call `EnterPlanMode`, write the plan in-session, present it with
     `ExitPlanMode` for approval.
   - **codex** — invoke the `codex` skill in planning mode and bring its plan back for approval.

4. On approval, **stop**. Confirm the plan file's path under `~/.claude/plans/`, then tell
   the user verbatim:

   > Plan approved and saved to `<path>`.
   > Run `/clear`, then `/implement-plan <path>` to build it.

   Do not write code, do not touch the working tree, do not offer to "just start".

## Writing the plan for a cold reader

The plan is the ONLY thing that survives into implementation. Nothing said during
brainstorming carries over. So the plan must stand alone:

- Name every file to touch by repo-relative path, and what changes in each.
- State what is explicitly **out of scope**, and the rejected alternatives with one line
  on why — otherwise the implementer re-litigates settled decisions.
- Spell out how to verify: the exact commands to run, and what passing looks like.
- No pronouns pointing at the conversation ("the approach we discussed", "as above").

## Rules

- Stop `superpowers:brainstorming` when scoping is done. It hands off to plan mode, nothing else.
- Do NOT use `superpowers:writing-plans`. The plan lives in plan mode, which writes the file.
- Do NOT use `superpowers:subagent-driven-development`.
- One approval gate: the plan. Do not re-ask for scope after the plan is approved.
