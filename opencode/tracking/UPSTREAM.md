# Upstream provenance

Source: https://github.com/Cluster444/agentic

Reference commit: `3a3915310d3d03d4a45114b7b0c0a17c34bf0e8b` (master inspected 2026-09-10).

The six command and specialist roles were originally vendored in full. They are now
locally maintained derivatives: thin commands load stage skills, each stage gets a
fresh-context worker, specialist prompts are bounded, and GitHub issue/comment
artifacts replace local ticket files. The full original payload remains in Git
history before the balanced-workflow update. The tracking/handoff helpers, explicit
sync command, workflow dispatcher and launchd monitor are local additions.

Model roles are intentional local defaults: Astra for planning/analysis/review, Sol
for implementation, and Luna Fast for lookup/commit work. Do not reintroduce upstream
mandatory repeated research phases or whole-file/history reading rules on updates.

Retain LICENSE.agentic with vendored and derived prompts. Future upstream changes
should be reviewed and copied into dotfiles, not installed with `agentic pull -g`
over managed links.
The migration utility preserves the pre-migration global files outside runtime
command/agent discovery directories and prints their hashes and upstream differences.
