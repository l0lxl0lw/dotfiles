install_component() {
  local venv="$HOME/.local/share/life-memory-venv" vault clients backup_dir client missing=0
  ensure_tool python3.12 python@3.12
  if (( DRY_RUN )); then
    say 'Would ask for vault path, selected clients, backups, and launchd registration.'
    say 'Would install basic-memory==0.23.2 in an isolated venv and run ai/memory/setup.py.'
    return
  fi
  if [[ ! -x "$venv/bin/basic-memory" ]]; then
    ask 'Install the isolated Life memory environment and basic-memory==0.23.2?' || return 2
    mkdir -p "$(dirname "$venv")"
    if [[ ! -x "$venv/bin/python" ]]; then python3.12 -m venv "$venv"; fi
    "$venv/bin/pip" install --pre 'basic-memory==0.23.2'
  fi
  printf 'Clients to configure (comma separated: claude,codex,opencode): ' >&2
  IFS= read -r clients || die 'Input ended.'
  [[ -n "$clients" ]] || return 2
  local selected_clients=()
  IFS=',' read -r -a selected_clients <<< "$clients"
  for client in "${selected_clients[@]}"; do
    case "$client" in claude|codex|opencode) ;; *) die "Unknown memory client: $client";; esac
    command -v "$client" >/dev/null 2>&1 || { say "Install $client before configuring its memory integration."; return 2; }
  done
  printf 'Vault absolute path (blank reuses existing config, or ~/Documents/Life): ' >&2
  IFS= read -r vault || die 'Input ended.'
  local args=(--clients "$clients")
  [[ -z "$vault" ]] || args+=(--vault "$vault")
  printf 'Daily backup directory (absolute; blank keeps the existing/default local backup directory): ' >&2
  IFS= read -r backup_dir || die 'Input ended.'
  [[ -z "$backup_dir" ]] || args+=(--backup "$backup_dir")
  say 'Setup snapshots changed JSON settings and preserves existing notes. Review/trust Codex hooks in a fresh session.'
  ask 'Proceed with Life memory configuration (automatic config backups)?' || return 2
  "$venv/bin/python" "$ROOT/ai/memory/setup.py" "${args[@]}"
  vault=$("$venv/bin/python" -c 'from pathlib import Path; import json,os; print(json.loads(Path(os.environ.get("LIFE_MEMORY_CONFIG", "~/.config/life-memory/config.json")).expanduser().read_text())["vault"])')
  export BASIC_MEMORY_NO_PROMOS=1 BASIC_MEMORY_FORCE_LOCAL=true
  say "Register the vault if not already registered: $venv/bin/basic-memory project add life \"$vault\" --local --default"
  if ask 'Register Basic Memory now (skip if the life project already exists)?'; then
    "$venv/bin/basic-memory" project add life "$vault" --local --default
  fi
  "$venv/bin/basic-memory" config set auto_update false
  "$venv/bin/basic-memory" config set ensure_frontmatter_on_sync false
  for client in "${selected_clients[@]}"; do
    case "$client" in
      claude)
        if ask 'Register the life-memory MCP server with Claude using its native CLI?'; then
          approve_change "$HOME/.claude.json"
          local registration
          registration=$("$venv/bin/python" -c 'import json,sys; print(json.dumps({"type":"stdio","command":sys.argv[1],"args":["mcp","--project","life"],"env":{"BASIC_MEMORY_NO_PROMOS":"1","BASIC_MEMORY_FORCE_LOCAL":"true"}}))' "$venv/bin/basic-memory")
          run claude mcp add-json --scope user life-memory "$registration"
        else missing=1; fi;;
      codex)
        if ask 'Register the life-memory MCP server with Codex using its native CLI?'; then
          approve_change "${CODEX_HOME:-$HOME/.codex}/config.toml"
          run codex mcp add life-memory --env BASIC_MEMORY_NO_PROMOS=1 --env BASIC_MEMORY_FORCE_LOCAL=true -- "$venv/bin/basic-memory" mcp --project life
        else missing=1; fi;;
    esac
  done
  if ask 'Enable the five-minute user maintenance job?'; then
    if launchctl print "gui/$(id -u)/local.life-memory.maintenance" >/dev/null 2>&1; then
      say 'Maintenance is already loaded; restart it after changing paths.'
    else
      launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.life-memory.maintenance.plist"
    fi
  fi
  say 'Restart assistants. Review/trust Codex hooks with /hooks, then verify capture with ai/memory/README.md.'
  (( missing == 0 )) || return 2
}
