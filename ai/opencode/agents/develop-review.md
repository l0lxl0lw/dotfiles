---
description: Fresh independent worker for development acceptance review or re-review.
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

Read ~/dotfiles/ai/shared/skills/develop/_lib/review.md and follow it for this stage only. Return its exact
verdict/evidence handoff and stop. Do not edit application code or repair findings.
