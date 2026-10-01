install_component() {
  ensure_tool vim vim
  link_file "$ROOT/vim/vimrc.conf" "$HOME/.vimrc"
  say 'Vim uses built-in features; no unused Pathogen plugins are downloaded.'
}
