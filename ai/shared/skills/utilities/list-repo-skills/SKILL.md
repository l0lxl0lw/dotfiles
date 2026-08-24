---
name: list-repo-skills
description: Use when the user asks which skills belong to the repository they are in, as opposed to the ones they get everywhere. Triggers — "list repo skills", "/list-repo-skills", "what skills does this repo have", "project skills", "does this repo define any skills", "which skills are local to this project", "what skills ship with this codebase". For the full catalog including global skills use list-skills.
---

# List repo skills

Prints only the skills the current repository defines — the ones that exist because of
this checkout and travel with it. A repo skill is any `SKILL.md` under the git root's
`.claude/skills`, `.agents/skills`, `.codex/skills` or `.grok/skills`. Nothing from
`~/.claude`, dotfiles, gstack or plugins belongs in this answer.

## Run

```bash
bash ~/dotfiles/ai/shared/skills/utilities/_lib/list-skills.sh --repo
```

If that path does not exist (dotfiles cloned elsewhere), run `../_lib/list-skills.sh
--repo` relative to this skill's own directory — `..` resolves through the symlink to the
real dotfiles directory.

Run it from inside the repo in question. It resolves the git root itself, so a
subdirectory is fine; outside a git repo it falls back to the working directory and says
so.

## Your reply

The script's output, verbatim, in a fenced block. Nothing else — no line naming the repo,
no count restated, no summary. It is a list of things they can call, and the list is the
whole answer. A real caveat gets one line and no more.

`--desc` adds a description column if they ask what the skills are for.

## When the repo defines none

The script says so and that is the whole answer — most repos define none. Report it
plainly, do not fall back to listing global skills, and do not treat it as an error. Add
where one would go (`.claude/skills/<name>/SKILL.md` at the git root) only if they ask
how to add one.
