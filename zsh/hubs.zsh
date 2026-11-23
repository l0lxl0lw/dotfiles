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
