---
description: Fresh worker for a requested development research stage.
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
    codebase-locator: allow
    codebase-pattern-finder: allow
    codebase-analyzer: allow
    web-search-researcher: allow
---

Load the `develop-research` skill and follow it for this stage only. Return its exact
artifact handoff and stop. Do not import parent history or edit application code.
