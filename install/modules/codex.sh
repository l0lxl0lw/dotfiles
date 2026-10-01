install_component() {
  ensure_tool codex codex cask
  sync_ai codex "${CODEX_HOME:-$HOME/.codex}"
}
