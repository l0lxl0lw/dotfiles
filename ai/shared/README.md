# Shared Agent Config

Cross-tool configuration consumed by both Claude and Codex.

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

`claude_merge_config` and `codex_merge_config` both flatten `ai/shared/skills/**/SKILL.md`
into their respective runtime skill directories. Tool-local skills win by basename, so
put a skill under `ai/claude/skills` or `ai/codex/skills` when it needs tool-specific behavior.
