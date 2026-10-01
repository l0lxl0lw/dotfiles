install_component() {
  if ! command -v grok >/dev/null 2>&1; then
    say 'Grok CLI is missing. No verified package is registered; install your intended vendor CLI, then rerun --only grok.'
    say 'This avoids substituting an unrelated third-party package with the same name.'
    return 2
  fi
  sync_ai grok "${GROK_HOME:-$HOME/.grok}"
}
