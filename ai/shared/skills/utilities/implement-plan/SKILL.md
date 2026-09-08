---
name: implement-plan
description: Build an already-approved plan from ~/.claude/plans/ in a fresh session, on sonnet at low effort. The other half of brainstorm-then-plan — run it after /clear so none of the brainstorming transcript is in context. Triggers — "/implement-plan <path>", "build the approved plan", "implement the plan file".
disable-model-invocation: true
model: sonnet
effort: low
---

# Implement An Approved Plan

The plan is already approved. Your job is to build it, not to re-plan it.

## Steps

1. Read the plan file. If no path was given, list `~/.claude/plans/` and ask which one —
   do not guess at the newest.

2. Build a todo list from the plan's steps, then work through it. Read each file you are
   about to change before changing it; the plan's line numbers may have drifted.

3. Run the plan's stated verification commands. Report what passed and what failed, with
   the actual output.

## Rules

- **Do not re-open scope.** The plan's rejected alternatives were rejected on purpose. If
  the plan is genuinely wrong or impossible, say so in two sentences and stop — do not
  redesign it yourself.
- **Edit, don't rewrite.** Change files with `Edit`, or `sed`/`patch` in Bash. Never
  re-emit a whole file through a `cat > file <<EOF` heredoc for a partial change — the
  full text lands in context permanently, and twice if you do it again.
- **Read a file once.** Keep what you learned instead of re-reading to check.
- Do NOT dispatch implementation subagents. Write the code yourself.
- If the plan is large, `/clear` between independent milestones and re-enter with the plan
  file plus a one-line note of what is already done.

## Graph freshness

If the repo has a graphify graph, it is fine for orientation (who calls what, where a
symbol lives) but it is **stale the moment you edit**. The git hooks rebuild on commit and
checkout, not on an uncommitted edit. So:

- Query the graph to locate code; read the file to know what it currently says.
- Never quote the graph as evidence about code you have already changed this session.
- After a milestone lands, `graphify update .` re-extracts only what changed.
