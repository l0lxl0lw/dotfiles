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

# Active hubs first, then the legacy roots: everything a managed link may
# point into.
_hubs_roots() {
  hubs_list 2>/dev/null
  print -rl -- $_HUBS_LEGACY_ROOTS
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
  mkdir -p "$dst"
  for f in "$dst"/**/*(N@); do
    _agentcfg_is_managed "$f" || continue
    (( ${+want[${f#"$dst"/}]} )) && continue
    rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
  done
  for key in ${(ko)want}; do
    mkdir -p "$dst/${key:h}"
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

  [[ -d "$claude_dir" ]] && _hubs_link_tree "$claude_dir/agents" .claude/agents "$@"

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
    if [[ -d "$codex_dir" ]]; then
      _hubs_copy_generated "$codex_dir/agents" '*.toml' "${codex_srcs[@]}"
      _hubs_warn_unknown_codex_models "$codex_dir" "$@"
    fi
    [[ -d "$opencode_dir" ]] && _hubs_copy_generated "$opencode_dir/agents" '*.md' "${opencode_srcs[@]}"
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
  [[ -d "$HOME/.claude" ]] && files+=("$HOME/.claude/CLAUDE.md")
  [[ -d "${CODEX_HOME:-$HOME/.codex}" ]] && files+=("${CODEX_HOME:-$HOME/.codex}/AGENTS.md")
  [[ -d "${XDG_CONFIG_HOME:-$HOME/.config}/opencode" ]] && files+=("${XDG_CONFIG_HOME:-$HOME/.config}/opencode/AGENTS.md")
  for file in "${files[@]}"; do
    _hubs_splice_block "$file" "$beg" "$fin" "$body" || true
  done
  return 0
}
