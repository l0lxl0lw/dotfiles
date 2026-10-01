install_component() {
  ensure_tool opencode opencode
  ensure_tool python3 python
  ensure_tool gh gh
  sync_ai opencode "${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
  say 'Run gh auth login for GitHub workflows. Configure provider access in OpenCode.'
  say 'Workflow profiles name specific models; inspect opencode/profiles.json for availability on your account.'
}
