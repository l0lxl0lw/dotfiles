# Shared Agent Config

Cross-tool configuration consumed by Claude, Codex, Grok, and OpenCode.

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
        ├── mattpocock/
        ├── omc/
        ├── understand/
        └── utilities/
```

`claude_merge_config`, `codex_merge_config`, `grok_merge_config` and
`opencode_merge_config` all flatten
`ai/shared/skills/**/SKILL.md` into their respective runtime skill directories. Tool-local
skills win by basename, so put a skill under `ai/claude/skills`, `ai/codex/skills`,
`ai/grok/skills` or `ai/opencode/skills` when it needs tool-specific behavior.

Discovery does not guarantee portability: some skills reference harness-specific
tools, plugins, models or commands. Keep shared contents intact and use tool-local
overrides when adapting those workflows.
