---
name: ghp-personal
description: Switch to the personal GitHub profile — the active gh account, the global git author and git's HTTPS credentials together — then report the result. User-invoked only. Triggers — "ghp personal", "switch to my personal GitHub", "use the personal profile".
disable-model-invocation: true
allowed-tools: Bash(zsh *)
model: haiku
effort: low
---

# Switch to the personal GitHub profile

Run exactly this, nothing else:

```bash
zsh -c 'source ~/dotfiles/zsh/github-profile.zsh && ghp personal && echo && ghp'
```

Then report the active profile, gh user and git author in one or two lines.

`ghp` is defined in `~/dotfiles/zsh/github-profile.zsh`; profiles are read from
`${XDG_CONFIG_HOME:-~/.config}/dotfiles/github-profiles`.

## Common mistakes

- **Retrying a failed switch with other commands.** If `ghp` says gh has no login
  for the account, relay its `gh auth login` instruction to the user and stop —
  login is interactive and only the user can complete it.
- **Editing git config or running `gh auth switch` directly.** `ghp` keeps the gh
  account, git author and credential helper in step; doing one by hand leaves them
  disagreeing.
- **Switching to work.** That is `/ghp-work`.
