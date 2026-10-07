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

Load the `develop-execute` skill and follow it for this stage only. Require the exact
authorized plan and supplied repair review. Return its evidence handoff and stop.
