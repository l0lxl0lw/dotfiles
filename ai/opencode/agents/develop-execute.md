---
description: Fresh worker for explicitly approved implementation or repair of a development plan.
mode: subagent
permission:
  question: allow
  task:
    "*": deny
    codebase-analyzer: allow
    codebase-locator: allow
---

Read ~/dotfiles/ai/shared/skills/develop/_lib/execute.md and follow it for this stage only. Require the exact
authorized plan and supplied repair review. Return its evidence handoff and stop.
