install_component() {
  local url
  if exists "$HOME/dotfiles-private"; then
    say 'Using existing ~/dotfiles-private; Zsh loads its *.zsh files and OpenCode reads its config.json.'
    return 0
  fi
  if (( DRY_RUN )); then say 'Would ask for your private repository URL (optional).'; return; fi
  printf 'Private Git URL (blank to skip; do not embed credentials): ' >&2
  IFS= read -r url || die 'Input ended.'
  [[ -n "$url" ]] || return 2
  [[ "$url" != -* ]] || die 'Invalid repository URL.'
  run git clone -- "$url" "$HOME/dotfiles-private"
}
