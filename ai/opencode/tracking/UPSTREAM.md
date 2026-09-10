# Upstream provenance

Source: https://github.com/Cluster444/agentic

Reference commit: `3a3915310d3d03d4a45114b7b0c0a17c34bf0e8b` (master inspected 2026-09-10).

The six specialist roles and ticket → research → plan → execute → commit → review
workflow are adapted from upstream. These are deliberately rewritten personal
prompts, not byte-for-byte vendored files. Local ticket files are replaced with
GitHub Issues and comments; the distribution CLI is replaced with dotfiles sync;
model overrides are removed; permissions use current OpenCode syntax. The tracking
helper, explicit sync command and launchd monitor are local additions.

Retain LICENSE.agentic with derived prompts. Future upstream changes should be
reviewed selectively, not installed with `agentic pull -g` over managed links.
The migration utility preserves the pre-migration global files outside runtime
command/agent discovery directories and prints their hashes and upstream differences.
