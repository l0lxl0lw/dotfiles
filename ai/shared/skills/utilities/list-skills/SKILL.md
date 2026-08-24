---
name: list-skills
description: Use when the user asks what skills exist rather than asking for one — the whole catalog, global plus whatever the current repo adds. Triggers — "list skills", "/list-skills", "what skills do I have", "show me my skills", "which skills are installed", "what skills are available", "do I have a skill for X", "how many skills do I have". For only the current repo's skills use list-repo-skills.
model: opus
effort: high
---

# List skills

Prints every skill on disk this machine can load as a lookup table of names to call,
grouped by where they come from: the current repo's own skills first, then each dotfiles
group, gstack, and each installed plugin. Repo skills shadow a global skill of the same
name — the listing marks that and drops the shadowed global, because the shadowed one
never loads.

## Run

```bash
bash ~/dotfiles/ai/shared/skills/utilities/_lib/list-skills.sh
```

If that path does not exist (dotfiles cloned elsewhere), run `../_lib/list-skills.sh`
relative to this skill's own directory — `..` resolves through the symlink to the real
dotfiles directory, so `bash ~/.claude/skills/list-skills/../_lib/list-skills.sh` works.

Run it from the directory the user is asking about; it scopes "this repo" to the git root
of the current working directory. `--desc` adds a description column, `--names` prints
bare names one per line for piping.

## Your reply

The script's output, verbatim, in a fenced block. Nothing else — no line naming the repo,
no count restated, no summary, no offer to explain any of them. It is a list of things
they can call, and the list is the whole answer.

The one exception is a real caveat, which gets one line and no more.

## Narrower asks

"Do I have a skill for X" is the same run with `--desc`: keep the group headers, print
only the rows whose name or description matches, and say how many rows you dropped. Match
on what the skill is for, not just the literal word they typed.

## What the listing cannot see

Skills the harness injects that are not files on disk — the built-ins this session lists
in its own skill list (`dataviz`, `artifact-design`, `init`, and similar). If the user is
reconciling the two lists, name those separately rather than pretending the script missed
them.
