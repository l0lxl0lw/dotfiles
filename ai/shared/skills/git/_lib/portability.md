# Host tools and paths

Use the current assistant's native tools. `AskUserQuestion` means its interactive
question tool (OpenCode: `question`); if none exists, ask in chat and wait for the
answer. `Bash`, `Read`, `Edit`, and `Task` mean the corresponding available tools,
not a requirement to install Claude. Only delegate to agents the host actually has.
Model/effort frontmatter is a host hint; OpenCode routing belongs to its configuration.

The examples use the canonical `~/dotfiles/ai/shared/skills/git` location. If the
skill is loaded from another checkout or a pinned snapshot, substitute that
physical skill directory, retaining its `scripts/` and sibling `_lib/` resources.
Resolve directory symlinks before accessing siblings. Run Git helpers with the
target repository as the working directory, not the dotfiles or skill directory.

Workflow tracking/Orca features require the installed tracking/Orca integrations.
Report an unavailable required integration instead of inventing tool names,
claims of background execution, or successful verification.
