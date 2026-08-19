# Shared Agent Config

Cross-tool configuration consumed by Claude, Codex, and Grok.

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
        └── utilities/
```

`claude_merge_config`, `codex_merge_config` and `grok_merge_config` all flatten
`ai/shared/skills/**/SKILL.md` into their respective runtime skill directories. Tool-local
skills win by basename, so put a skill under `ai/claude/skills`, `ai/codex/skills` or
`ai/grok/skills` when it needs tool-specific behavior.
