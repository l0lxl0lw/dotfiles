---
name: track
description: Inspect or repair the GitHub Project card for the current branch — the manual override for the gh-project-track hook. Use for "/track", "/track status", "/track link 123", "/track unlink", "/track set in-review", "why isn't my branch on the board", "the card is on the wrong issue", or when a card needs moving by hand.
disable-model-invocation: true
allowed-tools: Bash, Read
---

# Track

Manual control over the branch→board tracking that `gh-project-track.sh` normally does
automatically. This exists because without it there is no way to repair a mislinked card.

## Subcommands

| Invocation | Does |
|---|---|
| `/track` or `/track status` | Report the current branch's issue, card, column, and whether the hook is installed and opted in |
| `/track link <issue>` | Point this branch at an existing issue (writes state + the durable body marker) |
| `/track unlink` | Forget the local mapping. Does **not** delete the issue or the card |
| `/track set <column>` | Force the card to `backlog\|ready\|in-progress\|in-review\|done`, bypassing the monotonic guard |
| `/track repair` | Re-run the hook's own `in-review` path against the current branch |

## Layout

| Path | Holds |
|---|---|
| `~/.claude/gh-project-track/config.json` | Opt-in gate + project/field/option ids. **Absent ⇒ everything is a no-op** |
| `~/.claude/gh-project-track/state/<repo>@<branch>-<hash>/state.json` | issue, item id, rank, status |
| `~/.claude/gh-project-track/fast/<worktree>_<branch>` | rank only — the fast-path sentinel |
| `~/.claude/gh-project-track/log` | append-only audit |
| `~/.claude/hooks/gh-project-track.sh` | symlink to `~/dotfiles/ai/claude/hooks/gh-project-track.sh` |

`/` is flattened to `_` in **both** the worktree and the branch portion of those keys. A branch like
`azu/my-feature` would otherwise make the path a directory that does not exist.

## Status

1. Resolve `repo` from `git remote get-url origin`, `branch` from
   `git rev-parse --abbrev-ref HEAD` (never the directory name — Orca renames both).
2. Report, in order, so the failure is obvious at a glance:
   - is `~/.claude/hooks/gh-project-track.sh` executable? (missing ⇒ every hook silently no-ops)
   - does `config.json` exist, and does `.repos` contain this repo?
   - state file contents, if any
   - live column, read back from the API (below)

## Reading the live column

```bash
ITEM=$(jq -r .item_id ~/.claude/gh-project-track/state/<dir>/state.json)
gh api graphql -f query='
  query($i:ID!){ node(id:$i){ ... on ProjectV2Item {
    fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue { name } } } } }' \
  -f i="$ITEM" --jq '.data.node.fieldValueByName.name'
```

## Setting a column

```bash
PROJ=$(jq -r .project.id ~/.claude/gh-project-track/config.json)
FIELD=$(jq -r .project.status_field_id ~/.claude/gh-project-track/config.json)
OPT=$(jq -r '.project.status_options."in-review"' ~/.claude/gh-project-track/config.json)
gh api graphql -f query='
  mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
    updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){
      projectV2Item{ id } } }' \
  -f p="$PROJ" -f i="$ITEM" -f f="$FIELD" -f o="$OPT"
```

**Write once is not enough.** The board runs GitHub workflows that asynchronously overwrite Status
several seconds later — a PR↔issue link event resets a card to In progress. Read back and re-apply
at roughly 3s and 12s, exactly as the hook does. After `/track set`, verify before reporting success.

## Linking

The mapping's source of truth is a marker line in the issue body, so it survives cache loss and is
recoverable from GitHub alone:

```
<!-- track-branch: <owner>/<repo>@<branch> -->
```

`/track link <issue>` must append that marker if absent, then write `state.json`. Recover a lost
mapping with:

```bash
gh issue list --repo <repo> --state all --limit 50 \
  --search '"track-branch: <repo>@<branch>" in:body' --json number
```

## Rules

- Never delete an issue or remove a card — `unlink` clears only the local mapping
- Always confirm with the user before creating an issue or moving a column
- Do not set an assignee on an issue you create
- After any status write, read it back across the drift window before reporting success
- Everything is a no-op when `config.json` is absent; say so plainly rather than appearing to work
