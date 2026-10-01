install_component() {
  ensure_tool zsh zsh
  clone_plugin https://github.com/zsh-users/zsh-autosuggestions "$HOME/.zsh/zsh-autosuggestions"
  link_file "$ROOT/zsh/zshrc.conf" "${ZDOTDIR:-$HOME}/.zshrc"
  say 'Default shell is unchanged. If needed: chsh -s /bin/zsh'
}
