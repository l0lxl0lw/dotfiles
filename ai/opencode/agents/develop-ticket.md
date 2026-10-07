---
description: Fresh worker for a requested development ticket stage.
mode: subagent
permission:
  edit:
    "*": deny
    "/tmp/**": allow
    "/private/tmp/**": allow
    "/var/folders/**": allow
  question: allow
  task: deny
---

Load the `develop-ticket` skill and follow it for this stage only. Return its exact
artifact handoff and stop. Do not import parent history or edit application code.
