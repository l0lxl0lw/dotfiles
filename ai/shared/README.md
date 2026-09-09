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

All previously disabled skills are restored here, including their supporting files.
Discovery does not guarantee portability: some skills reference harness-specific tools,
plugins, models or commands. Keep shared contents intact and use tool-local overrides
when adapting those workflows.

## Plan And Implement

Two portable entry skills provide the shared workflow for Claude, Codex, Grok,
and OpenCode, without a planning plugin dependency:

- `brainstorm-then-plan`: inspect context, ask only unresolved important questions
  one at a time, define acceptance and bounded proof, then request one final plan
  approval and stop. Native plan tools are optional.
- `implement-plan <absolute-plan-path>`: start in a fresh session, verify approval
  and drift, implement inline with selective independent delegation, and record
  bounded verification evidence. Medium effort and Sonnet are hints, not requirements.

Plans live at `~/.agents/plans/<project>/<task>/plan.md`; adjacent `progress.md`
preserves approval provenance/hash and evidence for cold resumes. Exact approved
effects authorize matching verification runs, not scope expansion. There are no
automatic git mutations, worktrees, commits, or live synchronization steps.

The [plan template](skills/utilities/_lib/plan-template.md) and
[verification contract](skills/utilities/_lib/verification-contract.md) are shared
prose, not extra skills. Resolve a linked skill's source directory before reading
`../_lib/`. Existing skill-directory links expose content changes without a sync;
start a fresh session to reload instructions (quit and restart OpenCode).

Repository-specific verification stays local: discover/read that project's
`ADAPTER.md` and include its required fenced machine contract in the plan. This
repo does not define or install the backend schema. Missing required adapter or
real-environment proof is reported as blocked, never as a successful test.
