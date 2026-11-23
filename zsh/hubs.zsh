# ---------------------------------------------------------------------------
# Hubs: the repositories whose skills, agents, personas and shell config this
# machine loads. The list is machine-local, never tracked:
#
#   ${XDG_CONFIG_HOME:-~/.config}/dotfiles/hubs    one path per line, ~ allowed,
#                                                  # comments and blank lines ignored
#
# A work machine lists a personal hub and a work hub; a personal machine lists
# one. Later lines win a name collision. HUBS_FILE overrides the location.
# ---------------------------------------------------------------------------

# Roots that earlier versions of this repo linked out of. Kept so stale links
# on an upgraded machine are recognized as ours and cleaned up, not orphaned.
typeset -ga _HUBS_LEGACY_ROOTS=(
  "$HOME/dotfiles" "$HOME/dotfiles-private" "$HOME/workspace/claude-config" "$HOME/workspace/azubot"
)

# The dotfiles checkout this file belongs to; the renderer lives beside it.
typeset -g _HUBS_DOTFILES="${${(%):-%x}:A:h:h}"
typeset -gi _HUBS_DRY=0            # set by hubs_sync --dry-run
typeset -ga _HUBS_TOOLS=()         # set by hubs_sync --tool; empty means every tool present

# _hubs_tool_on <tool> <dir>: selected (or no selection), enabled, and installed.
_hubs_tool_on() {
  (( ${#_HUBS_TOOLS} == 0 || ${_HUBS_TOOLS[(Ie)$1]} )) || return 1
  _agentcfg_enabled "$1" || return 1
  [[ -d "$2" ]]
}

_hubs_file() { print -r -- "${HUBS_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/hubs}" }

# Print each active hub as an absolute path, in file order, once. A listed
# path that does not exist is reported and skipped; its links are left alone
# by the sync, so a mistyped line never deletes anything.
hubs_list() {
  emulate -L zsh
  local file line path
  local -a seen
  file=$(_hubs_file)
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"; line="${line## }"; line="${line%% }"
    [[ -n "$line" ]] || continue
    path="$line"
    [[ "$path" == '~' || "$path" == '~/'* ]] && path="$HOME${path#\~}"
    path="${path:a}"                    # absolute, no trailing slash
    (( ${seen[(Ie)$path]} )) && continue
    seen+=("$path")
    if [[ -d "$path" ]]; then
      print -r -- "$path"
    else
      print -u2 -r -- "hubs: $path listed in $file does not exist, skipping"
    fi
  done < "$file"
}

# Hubs this machine has ever linked, so a hub dropped from the list still has
# its links recognised as ours and cleaned up rather than orphaned.
_hubs_seen_file() { print -r -- "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/hubs-seen" }
_hubs_remember() {
  local file seen hub
  file=$(_hubs_seen_file)
  mkdir -p "${file:h}"
  [[ -f "$file" ]] && seen=$(<"$file") || seen=""
  for hub in "$@"; do
    [[ "$seen" == *"$hub"* ]] && (( ${${(f)seen}[(Ie)$hub]} )) && continue
    print -r -- "$hub" >> "$file"
  done
}

# Active hubs first, then hubs seen before, this checkout and the legacy
# roots: everything a managed link may point into.
_hubs_roots() {
  local file
  hubs_list 2>/dev/null
  file=$(_hubs_seen_file)
  [[ -f "$file" ]] && cat "$file"
  print -rl -- "$_HUBS_DOTFILES" $_HUBS_LEGACY_ROOTS
}

# hubs_sync_skills <dest-skills-dir> <hub>...
# Link each hub's .agents/skills/<name> into the destination. Only
# .agents/skills is scanned: a hub's .claude/skills is a symlink to it.
hubs_sync_skills() {
  emulate -L zsh
  setopt extended_glob
  local dst="$1"; shift
  _agentcfg_sync_skill_sources "$dst" "${@/%//.agents/skills}"
}

# _hubs_link_tree <dest-dir> <subpath> <hub>...
# Symlink every <hub>/<subpath>/**/*.md into <dest-dir>, keeping subfolders.
# A later hub wins a relative name and the override is printed. Managed
# links the hubs no longer provide are removed; empty category dirs pruned.
_hubs_link_tree() {
  local dst="$1" sub="$2" hub f key
  shift 2
  local -A want
  local -a emptied
  for hub in "$@"; do
    [[ -d "$hub/$sub" ]] || continue
    for f in "$hub/$sub"/**/*.md(N-.); do
      key="${f#"$hub/$sub"/}"
      (( ${+want[$key]} )) && echo "override agent '$key': $f over ${want[$key]}"
      want[$key]="$f"
    done
  done
  (( ${_HUBS_DRY:-0} )) || mkdir -p "$dst"
  for f in "$dst"/**/*(N@); do
    _agentcfg_is_managed "$f" || continue
    (( ${+want[${f#"$dst"/}]} )) && continue
    _hubs_rm "$f"
  done
  for key in ${(ko)want}; do
    (( ${_HUBS_DRY:-0} )) || mkdir -p "$dst/${key:h}"
    _agentcfg_link "${want[$key]}" "$dst/$key" "agent '$key'"
  done
  emptied=( "$dst"/**/*(N/) )
  for f in "${(Oa)emptied[@]}"; do rmdir "$f" 2>/dev/null; done
}

# hubs_sync_agents <hub>...
# Claude: symlinks to each hub's committed .claude/agents (Claude-only agents
# included). Codex and OpenCode: rendered per hub with the machine tiers
# overlay, then copied in, later hub wins.
hubs_sync_agents() {
  emulate -L zsh
  setopt extended_glob
  local claude_dir="$HOME/.claude" codex_dir="${CODEX_HOME:-$HOME/.codex}"
  local opencode_dir="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
  local overlay="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/tiers.json"
  local hub stage i=0
  local -a codex_srcs opencode_srcs tiers_args
  [[ -f "$overlay" ]] && tiers_args=(--tiers "$overlay")

  _hubs_tool_on claude "$claude_dir" && _hubs_link_tree "$claude_dir/agents" .claude/agents "$@"

  stage=$(mktemp -d "${TMPDIR:-/tmp}/hubs-agents.XXXXXX") || return 1
  {
    for hub in "$@"; do
      [[ -d "$hub/agents/src" ]] || continue
      (( i++ ))
      python3 -B "$_HUBS_DOTFILES/agents/render.py" --hub "$hub" "${tiers_args[@]}" \
        --codex-out "$stage/codex/$i" --opencode-out "$stage/opencode/$i" >/dev/null || \
        echo "hubs_sync: render failed for $hub" >&2
      codex_srcs+=("$stage/codex/$i"); opencode_srcs+=("$stage/opencode/$i")
    done
    if _hubs_tool_on codex "$codex_dir"; then
      _hubs_copy_generated "$codex_dir/agents" '*.toml' "${codex_srcs[@]}"
      _hubs_warn_unknown_codex_models "$codex_dir" "$@"
    fi
    _hubs_tool_on opencode "$opencode_dir" && _hubs_copy_generated "$opencode_dir/agents" '*.md' "${opencode_srcs[@]}"
    true
  } always {
    command rm -rf -- "$stage"
  }
  return 0
}

# _hubs_splice_block <file> <begin-marker> <end-marker> <body>
# Replace (or append) the marked block, keeping everything around it. Only
# writes when the block differs. A managed symlink becomes a regular file; a
# foreign regular file without markers is left alone with a warning.
_hubs_splice_block() {
  local file="$1" beg="$2" fin="$3" body="$4" current tmp
  if [[ -L "$file" ]]; then
    if _agentcfg_is_managed "$file"; then
      if (( _HUBS_DRY )); then echo "would replace managed symlink $file with a file"; (( _AGENTCFG_LINKED++ )); return 0; fi
      rm -f -- "$file"
    else
      echo "hubs_sync: $file is a symlink owned by something else, leaving it" >&2
      (( _AGENTCFG_SKIPPED++ )); return 1
    fi
  fi
  if [[ -s "$file" ]] && ! command grep -qF -- "$beg" "$file"; then
    echo "hubs_sync: $file has content but no hubs markers, leaving it" >&2
    (( _AGENTCFG_SKIPPED++ )); return 1
  fi
  current=$([[ -f "$file" ]] && awk -v b="$beg" -v e="$fin" 'index($0,b){f=1;next} index($0,e){f=0;next} f' "$file")
  [[ "$current" == "$body" ]] && return 0
  if (( _HUBS_DRY )); then echo "would write the hubs block in $file"; (( _AGENTCFG_LINKED++ )); return 0; fi
  mkdir -p "${file:h}"
  local pre="" post=""
  if [[ -f "$file" ]]; then
    pre=$(awk -v b="$beg" 'index($0,b){exit} {print}' "$file")
    post=$(awk -v e="$fin" 'f{print} index($0,e){f=1}' "$file")
  fi
  tmp=$(mktemp "${file}.XXXXXX") || return 1
  {
    [[ -n "$pre" ]] && print -r -- "$pre"
    print -r -- "$beg"; print -r -- "$body"; print -r -- "$fin"
    [[ -n "$post" ]] && print -r -- "$post"
    true
  } > "$tmp" && mv -f "$tmp" "$file" && (( _AGENTCFG_LINKED++ )) || { rm -f -- "$tmp"; return 1 }
  return 0
}

# hubs_sync_instructions <hub>...
# One managed block in each tool's global instruction file, built from every
# hub's persona/global.md in hub order under a "## <hub>" heading.
hubs_sync_instructions() {
  emulate -L zsh
  setopt extended_glob
  local beg='<!-- >>> dotfiles hubs >>> -->' fin='<!-- <<< dotfiles hubs <<< -->'
  local hub body="" file
  local -a files
  for hub in "$@"; do
    [[ -f "$hub/persona/global.md" ]] || continue
    body+="## ${hub:t}"$'\n\n'"$(<"$hub/persona/global.md")"$'\n\n'
  done
  body="${body%%$'\n'##}"
  # No hub contributes a persona: do not create instruction files for an empty
  # block, but keep an existing block in step (emptied).
  local create=1; [[ -n "$body" ]] || create=0
  _hubs_tool_on claude "$HOME/.claude" && files+=("$HOME/.claude/CLAUDE.md")
  _hubs_tool_on codex "${CODEX_HOME:-$HOME/.codex}" && files+=("${CODEX_HOME:-$HOME/.codex}/AGENTS.md")
  _hubs_tool_on opencode "${XDG_CONFIG_HOME:-$HOME/.config}/opencode" && files+=("${XDG_CONFIG_HOME:-$HOME/.config}/opencode/AGENTS.md")
  for file in "${files[@]}"; do
    (( create )) || [[ -e "$file" || -L "$file" ]] || continue
    _hubs_splice_block "$file" "$beg" "$fin" "$body" || true
  done
  return 0
}

# hubs_doctor: the hubs file, each hub's state and render drift, per-tool
# counts of hub links and generated copies, and Orca's hook status.
hubs_doctor() {
  emulate -L zsh
  setopt extended_glob
  local file hub line tool dir n_links n_copies f orca
  file=$(_hubs_file)
  print -r -- "hubs file: $file$([[ -f "$file" ]] || print -r -- ' (absent)')"
  if [[ -f "$file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%%\#*}"; line="${line## }"; line="${line%% }"
      [[ -n "$line" ]] || continue
      hub="$line"; [[ "$hub" == '~' || "$hub" == '~/'* ]] && hub="$HOME${hub#\~}"; hub="${hub:a}"
      if [[ ! -d "$hub" ]]; then print -r -- "  $hub: missing"; continue; fi
      if [[ -d "$hub/agents/src" ]] && ! python3 -B "$_HUBS_DOTFILES/agents/render.py" --hub "$hub" --check >/dev/null 2>&1; then
        print -r -- "  $hub: render drift (run agents/render.py --hub $hub)"
      else
        print -r -- "  $hub: ok"
      fi
    done < "$file"
  fi
  for tool dir in claude "$HOME/.claude" codex "${CODEX_HOME:-$HOME/.codex}" opencode "${XDG_CONFIG_HOME:-$HOME/.config}/opencode"; do
    [[ -d "$dir" ]] || { print -r -- "  $tool: not installed"; continue }
    n_links=0; n_copies=0
    for f in "$dir"/skills/*(N@) "$dir"/agents/**/*(N@); do _agentcfg_is_managed "$f" && (( n_links++ )); done
    for f in "$dir"/agents/*(N-.); do _hubs_is_generated "$f" && (( n_copies++ )); done
    print -r -- "  $tool: $n_links hub links, $n_copies generated agents$([[ -d "$dir/skills/orca-cli" ]] && print -r -- ', orca-cli present')"
  done
  if [[ -n "${ORCA_CLI_COMMAND:-}" ]]; then orca="$ORCA_CLI_COMMAND"
  elif ! orca=$(command -v orca 2>/dev/null); then orca=/Applications/Orca.app/Contents/Resources/bin/orca; fi
  if [[ -x "$orca" ]]; then
    print -r -- "  orca hooks:"
    "$orca" agent hooks status 2>/dev/null | command grep -E '^(claude|codex|opencode):' | sed 's/^/    /'
  else
    print -r -- "  orca: not installed"
  fi
  return 0
}

# hubs_sync [--dry-run] [--hubs PATH,PATH] [--codex-home DIR] [--tool claude|codex|opencode]...
# Give every selected tool the active hubs' skills, agents and persona block,
# plus the tool-specific extras. Silent when nothing changes.
hubs_sync() {
  emulate -L zsh
  setopt extended_glob
  local -a hubs tools
  local arg dry=0 codex_home=""
  while (( $# )); do
    arg="$1"; shift
    case "$arg" in
      --dry-run) dry=1;;
      --hubs) for arg in ${(s:,:)1}; do
                [[ "$arg" == '~' || "$arg" == '~/'* ]] && arg="$HOME${arg#\~}"
                hubs+=("${arg:a}")
              done; shift;;
      --codex-home) codex_home="$1"; shift;;
      --tool) tools+=("$1"); shift;;
      *) echo "usage: hubs_sync [--dry-run] [--hubs PATH,PATH] [--codex-home DIR] [--tool claude|codex|opencode]..." >&2
         return 2;;
    esac
  done
  (( ${#hubs} )) || hubs=(${(f)"$(hubs_list)"})
  _HUBS_DRY=$dry; _HUBS_TOOLS=("${tools[@]}")
  (( dry )) || _hubs_remember "${hubs[@]}"
  local -x CODEX_HOME="${codex_home:-${CODEX_HOME:-$HOME/.codex}}"
  [[ -n "$codex_home" && ! ${_HUBS_DRY:-0} -eq 1 ]] && mkdir -p "$codex_home"
  local claude_dir="$HOME/.claude" codex_dir="$CODEX_HOME"
  local opencode_dir="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
  _agentcfg_reset

  _hubs_tool_on claude "$claude_dir" && hubs_sync_skills "$claude_dir/skills" "${hubs[@]}"
  _hubs_tool_on codex "$codex_dir" && hubs_sync_skills "$codex_dir/skills" "${hubs[@]}"
  _hubs_tool_on opencode "$opencode_dir" && hubs_sync_skills "$opencode_dir/skills" "${hubs[@]}"
  hubs_sync_agents "${hubs[@]}"
  hubs_sync_instructions "${hubs[@]}"
  _hubs_tool_on claude "$claude_dir" && _hubs_claude_settings "$claude_dir"
  _hubs_tool_on codex "$codex_dir" && _hubs_codex_config "$codex_dir"

  _HUBS_DRY=0; _HUBS_TOOLS=()
  _agentcfg_report hubs_sync
}
