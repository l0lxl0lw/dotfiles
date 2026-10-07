---
description: Fresh worker for a requested development planning stage.
mode: subagent
permission:
  edit:
    "*": deny
    "/tmp/**": allow
    "/private/tmp/**": allow
    "/var/folders/**": allow
  question: allow
  task:
    "*": deny
    codebase-analyzer: allow
---

Load the `develop-plan` skill and follow it for this stage only. Return its exact
artifact handoff and stop. Do not import parent history or edit application code.
