# Upstream provenance

Source: https://github.com/Cluster444/agentic

Reference commit: `3a3915310d3d03d4a45114b7b0c0a17c34bf0e8b` (master inspected 2026-09-10).

The complete bodies of the six distributed commands and six specialist agents are
vendored into `../commands/` and `../agents/`. Local instructions are layered above
the upstream bodies: GitHub Issues and comments replace local ticket artifacts, the
distribution CLI is replaced with dotfiles sync, model overrides are removed, and
permissions use current OpenCode syntax. The tracking helper, explicit sync command
and launchd monitor are local additions.

Retain LICENSE.agentic with vendored and derived prompts. Future upstream changes
should be reviewed and copied into dotfiles, not installed with `agentic pull -g`
over managed links.
The migration utility preserves the pre-migration global files outside runtime
command/agent discovery directories and prints their hashes and upstream differences.
