---
name: explain-code-flow
description: >-
  Explain a concept at college level, then show the call path and call tree of how it actually
  runs in this codebase — every entry point that reaches it, then the execution-ordered tree, with
  a clickable path/to/file.ext:LINE on every node. Triggers — "explain X and show me how it runs",
  "explain the flow of X", "how does X work end to end".
disable-model-invocation: true
---

# Explain Code Flow

`explain-college-level` plus the runtime path: what the thing is, then how it executes.

## Step 1 — Ground yourself in the real implementation

**REQUIRED: read `../_lib/grounding.md` and follow it first.** It owns topic and path resolution,
the read order, and what to extract.

## Step 2 — Explain the concept

**REQUIRED: follow `../_lib/explaining.md`.** Real mechanism, terminology defined inline, nothing
watered down, `relative/path.ext:LINE` on every claim.

## Step 3 — Show how it runs, in this order

1. **Call path** — the `## Entry points (N)` table: every trigger that reaches this code.
2. **Call tree** — the indented tree, ordered the way execution happens.

**REQUIRED SUB-SKILL:** Use `trace-callpath` for both. It owns the rendering contract — the
two-column spine, the fixed description column, file hops as indent levels, SQL at the leaf.
Do not invent a layout.

Every node carries a full relative `path/to/file.ext:LINE` so I can click straight into it.
