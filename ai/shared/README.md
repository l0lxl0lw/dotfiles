# Shared Agent Config

Canonical public skills consumed by Claude, Codex, Grok, and OpenCode. Skill
instructions, scripts, references, and shared libraries live here. OpenCode's
agents, command routing, launcher, and terminal plugins remain in `opencode/`.

```
ai/
└── shared/
    └── skills/
        ├── business/
        ├── codebase/
        ├── community/
        ├── git/
        ├── impeccable/
        ├── integrations/
        ├── learning/
        ├── mattpocock/
        ├── omc/
        ├── understand/
        ├── utilities/
        └── workflow/
```

`claude_merge_config`, `codex_merge_config`, `grok_merge_config`, and
`opencode_merge_config` flatten
`ai/shared/skills/**/SKILL.md` into their respective runtime skill directories.
Tool-local skills win by basename, so put a skill under `ai/claude/skills`,
`ai/codex/skills`, or `ai/grok/skills` when it needs tool-specific behavior.
OpenCode has no separately maintained public skill catalog.

## Portability

Use the host's available tools: `AskUserQuestion` means its question dialog (or a
chat question if unavailable). Model/effort frontmatter can remain as Claude hints;
OpenCode's workflow routing lives in its profiles/agents/commands. Resolve scripts
and sibling libraries from the physical skill directory so symlinks and pinned
snapshots work. Git skills share `_lib/portability.md` for these conventions.

Some skills require integrations: OMC skills need OMC agents/state tools; integration
skills need the named MCP/application; workflow skills need the helpers in
`opencode/tracking/`. Discovery exposes their instructions, not missing dependencies.
Private adapters stay in private configuration and are never copied into public bundles.

## OpenCode commands and project skills

Launch through the `opencode` shell wrapper to sync before startup. Every resolved
skill has its native slash command unless another command owns that name. The launcher
also supplies `/skill-<name>` fallback commands pointing at the exact selected file;
if that name is occupied, another `skill-` prefix is added. This preserves custom
commands while keeping colliding skills callable. Internal `wf-<hash>-*` snapshots
stay hidden from the terminal menu.

Project skills are discovered between the worktree root and launch directory.
Prefer `.agents/skills/<name>/SKILL.md` for cross-tool project skills. Existing
`.opencode/skills` and `.claude/skills` work too. Nearer directories override ancestors;
within one directory, `.opencode` wins over `.agents`, which wins over `.claude`.
Project skills override the shared catalog. Duplicate names within one source are
errors. External home-directory compatibility scans remain disabled; project paths
are added explicitly. Repository skills never become global symlinks.

Because native duplicate discovery can finish out of order, the launcher's
`runtime/project-skills.js` plugin enforces the chosen project file when the skill
tool or native skill command executes. Explicit custom commands keep their behavior.
Raw `opencode debug skill` metadata may show a different duplicate; fallback commands
and execution use the selected project file. `--pure` disables this execution plugin.

OpenCode's workflow snapshot includes the shared library and helper resources. Its
content identity changes when shared resources change; existing workflow children
retain their pinned resources. Restart OpenCode to discover newly added skills.
