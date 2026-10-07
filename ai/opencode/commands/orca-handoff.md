---
description: Explicitly hand a bounded task to another Orca workspace or terminal, then return its receipt.
agent: build
model: openai/gpt-6-astra
---

Load the `orca-handoff` skill and follow its deterministic helper workflow.
Resolve helper resources from the loaded skill's physical directory.
This invocation authorizes only the handoff described by the user.

Request: $ARGUMENTS
