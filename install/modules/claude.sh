install_component() {
  ensure_tool claude claude-code cask
  ensure_tool jq jq
  sync_ai claude "$HOME/.claude"
}
