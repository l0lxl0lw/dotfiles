---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design against the codebase, which also creates docs (GLOSSARY.md and ADRs) as we go. Invoke with /grill-with-docs.
disable-model-invocation: true
license: MIT
---

# grill-with-docs

Source: [mattpocock/skills — grill-with-docs](https://github.com/mattpocock/skills/tree/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/engineering/grill-with-docs)
at revision `5863806dd4e15c63174bee4e7515a4256792ecfa` (MIT; see `../_lib/LICENSE.mattpocock`).
Upstream calls the `grilling` and `domain-modeling` skills; locally both methods live in `_lib` instead of being separate slash commands.

Resolve these paths relative to this skill's physical directory, read both, and follow them together for the whole session:

1. **REQUIRED: `../_lib/grilling.md`** runs the interview: rounds over the design-tree frontier.
2. **REQUIRED: `../_lib/domain-modeling/domain-modeling.md`** keeps the domain model honest while you grill: challenge terms against `GLOSSARY.md`, cross-check claims with the code, update the glossary inline, and offer ADRs sparingly. Its `GLOSSARY-FORMAT.md` and `ADR-FORMAT.md` sit beside it.

Glossary and ADR files go in the repository being discussed, never in this skill directory.
