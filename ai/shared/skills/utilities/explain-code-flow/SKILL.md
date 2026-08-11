---
name: explain-code-flow
description: Explain the concept like I'm a college student, then show the call path and call tree of how it actually runs in this codebase.
disable-model-invocation: true
---

# Explain Code Flow

Explain the concept like I'm a college student.

Then show how it actually runs in this codebase, in this order:

1. **Call path** — the `## Entry points (N)` table: every trigger that reaches this code.
2. **Call tree** — the indented tree, ordered the way execution happens.

**REQUIRED SUB-SKILL:** Use `trace-callpath` for both. It owns the rendering contract — the
two-column spine, the fixed description column, file hops as indent levels, SQL at the leaf.
Do not invent a layout.

Every node carries a full relative `path/to/file.ext:LINE` so I can click straight into it.
