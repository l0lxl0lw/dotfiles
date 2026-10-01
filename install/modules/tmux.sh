install_component() {
  ensure_tool tmux tmux
  clone_plugin https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
  clone_plugin https://github.com/tmux-plugins/tmux-sensible "$HOME/.tmux/plugins/tmux-sensible"
  clone_plugin https://github.com/tmux-plugins/tmux-yank "$HOME/.tmux/plugins/tmux-yank"
  link_file "$ROOT/tmux/tmux.conf" "$HOME/.tmux.conf"
}
