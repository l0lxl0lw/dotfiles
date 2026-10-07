# Upstream provenance

Source: https://github.com/Cluster444/agentic

Reference commit: `3a3915310d3d03d4a45114b7b0c0a17c34bf0e8b` (master inspected 2026-09-10).

The specialist prompts in `../agents/` are locally maintained derivatives of the
upstream roles. Their investigations are bounded to the question being answered.
The original stage commands and later dispatcher were retired; their source remains
in Git history. Tracking/evidence helpers, explicit sync and the launchd monitor
are local additions.

Agent and command frontmatter carries any model-specific settings; native OpenCode
configuration supplies user overrides. Do not reintroduce upstream mandatory repeated
research phases or whole-file/history reading rules on updates.

Retain LICENSE.agentic with vendored and derived prompts. Future upstream changes
should be reviewed and copied into dotfiles, not installed with `agentic pull -g`
over managed links.
