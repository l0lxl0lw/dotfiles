# mattpocock skills

Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT — see `LICENSE`)
at commit `2ab9580`, 2026-07-28.

Every skill is prefixed `pocock-` to keep it separate from the rest of the skill set. The
prefix is applied in three places per skill: the directory name, the `name:` frontmatter
field, and every `/skill-name` cross-reference in the bodies. Upstream `agents/openai.yaml`
files (Codex-only metadata) were not copied.

| Local | Upstream path | Invocation |
| --- | --- | --- |
| `pocock-grill-me` | `skills/productivity/grill-me` | user-only |
| `pocock-grilling` | `skills/productivity/grilling` | model + user |
| `pocock-handoff` | `skills/productivity/handoff` | user-only |
| `pocock-teach` | `skills/productivity/teach` | user-only |
| `pocock-writing-great-skills` | `skills/productivity/writing-great-skills` | user-only |
| `pocock-wayfinder` | `skills/engineering/wayfinder` | user-only |
| `pocock-research` | `skills/engineering/research` | model + user |
| `pocock-domain-modeling` | `skills/engineering/domain-modeling` | model + user |
| `pocock-prototype` | `skills/engineering/prototype` | model + user |
| `pocock-setup` | `skills/engineering/setup-matt-pocock-skills` | user-only |

`setup-matt-pocock-skills` was shortened to `pocock-setup` rather than becoming
`pocock-setup-matt-pocock-skills`.

## Dependencies

`pocock-grill-me` is a one-line wrapper around `pocock-grilling`. `pocock-wayfinder` reaches
for `pocock-grilling`, `pocock-domain-modeling`, `pocock-prototype`, `pocock-research`, and
the tracker doc that `pocock-setup` writes (`docs/agents/issue-tracker.md`); without that doc
it falls back to a local-markdown tracker under `.scratch/`.

`pocock-setup/domain.md` still names two upstream skills that were not imported —
`/grill-with-docs` and `/improve-codebase-architecture`. It is a template written into target
repos, so the dangling names are cosmetic.

## Updating

Re-clone upstream, diff against these folders, then reapply the three prefix edits and the
attribution footer at the bottom of each `SKILL.md`.
