# Shared installer operations. Modules return 2 when deliberately skipped.
DRY_RUN=0
MODE=install
ONLY=""
BACKUP_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/backups"
export BACKUP_ROOT
RESULTS=()

say() { printf '%s\n' "$*"; }
die() { say "Error: $*" >&2; exit 1; }
exists() { [[ -e "$1" || -L "$1" ]]; }
ask() {
  local answer
  printf '%s [y/N] ' "$*" >&2
  IFS= read -r answer || die 'Input ended; stopped without assuming consent.'
  [[ "$answer" == y || "$answer" == Y || "$answer" == yes ]]
}
run() {
  printf '  '; printf '%q ' "$@"; printf '\n'
  if (( ! DRY_RUN )); then "$@"; fi
}
safe_path() {
  [[ "$1" == /* && "$1" != / && "$1" != "$HOME" && "$1" != */.. && "$1" != */. && "$1" != *$'\n'* && "$1" != *$'\t'* && "$1" != *'/../'* ]] || die "Unsupported path: $1"
}
check_parents() {
  local parent
  parent=$(dirname "$1")
  while [[ "$parent" != / && "$parent" != "$HOME" ]]; do
    [[ ! -L "$parent" ]] || { say "Symlinked parent requires manual setup: $parent" >&2; return 2; }
    parent=$(dirname "$parent")
  done
}
backup() {
  local path="$1" slot
  safe_path "$path"
  if (( DRY_RUN )); then say "Would back up $path"; return; fi
  mkdir -p "$BACKUP_ROOT"
  chmod 700 "$BACKUP_ROOT"
  if [[ -z "${BACKUP_RUN:-}" ]]; then
    BACKUP_RUN=$(mktemp -d "$BACKUP_ROOT/$(date +%Y%m%d-%H%M%S).XXXXXX")
    export BACKUP_RUN
  fi
  slot=$(mktemp -d "$BACKUP_RUN/item.XXXXXX")
  cp -pPR "$path" "$slot/original"
  printf '%s\t%s\n' "${slot##*/}" "$path" >> "$BACKUP_RUN/manifest.tsv"
  say "Backup: $slot/original"
}
# Permission to change an existing target; backups copy, never move, the original.
approve_change() {
  local path="$1" answer
  exists "$path" || return 0
  if (( DRY_RUN )); then say "Would ask before changing $path (backup / skip / no backup / cancel)"; return; fi
  while true; do
    printf 'Change %s? [b]ack up first / [s]kip / [n]o backup / [c]ancel [b]: ' "$path" >&2
    IFS= read -r answer || die 'Input ended; no change authorized.'
    case "$answer" in
      ''|b|B) backup "$path"; return 0;;
      s|S) return 2;;
      n|N) return 0;;
      c|C) say 'Cancelled.' >&2; exit 130;;
    esac
  done
}
link_file() {
  local src="$1" dst="$2" tmp
  [[ -e "$src" ]] || die "Missing source: $src"
  safe_path "$dst"
  check_parents "$dst" || return $?
  [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]] && return 0
  approve_change "$dst" || return $?
  if (( DRY_RUN )); then say "Would link $dst -> $src"; return; fi
  mkdir -p "$(dirname "$dst")"
  tmp=$(mktemp -d "$(dirname "$dst")/.dotfiles-link.XXXXXX")
  ln -s "$src" "$tmp/link"
  # A directory cannot be atomically replaced by a symlink.
  if [[ -L "$dst" || -d "$dst" ]]; then rm -rf -- "$dst"; fi
  mv -f "$tmp/link" "$dst"
  rmdir "$tmp"
}
copy_file() {
  local src="$1" dst="$2" tmp
  safe_path "$dst"
  check_parents "$dst" || return $?
  if [[ -f "$dst" && ! -L "$dst" ]] && cmp -s "$src" "$dst"; then return 0; fi
  approve_change "$dst" || return $?
  if (( DRY_RUN )); then say "Would copy $src -> $dst"; return; fi
  mkdir -p "$(dirname "$dst")"
  tmp=$(mktemp "$(dirname "$dst")/.dotfiles-copy.XXXXXX")
  cp "$src" "$tmp"
  if [[ -L "$dst" || -d "$dst" ]]; then rm -rf -- "$dst"; fi
  mv -f "$tmp" "$dst"
}
brew_path() {
  local candidate
  if command -v brew >/dev/null 2>&1; then return; fi
  for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [[ -x "$candidate" ]]; then export PATH="$(dirname "$candidate"):$PATH"; return; fi
  done
  return 1
}
ensure_brew() {
  brew_path && return 0
  (( DRY_RUN )) && { say 'Would offer Homebrew installation (brew.sh).'; return 0; }
  ask 'Homebrew is missing. Install it from Homebrew/install?' || return 2
  local script
  script=$(mktemp "${TMPDIR:-/tmp}/dotfiles-brew.XXXXXX")
  if ! curl -fL --retry 2 https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$script"; then
    rm -f "$script"; return 1
  fi
  /bin/bash "$script" || { rm -f "$script"; return 1; }
  rm -f "$script"
  brew_path
}
ensure_tool() {
  local exe="$1" package="$2" kind="${3:-formula}"
  if command -v "$exe" >/dev/null 2>&1; then
    if [[ "$MODE" == update ]] && brew_path && brew list "--$kind" "$package" >/dev/null 2>&1; then
      if (( DRY_RUN )) || ask "Upgrade Homebrew $package?"; then run brew upgrade "--$kind" "$package"; fi
    fi
    return 0
  fi
  if (( ! DRY_RUN )); then
    ask "$exe is missing. Install with brew install --$kind $package?" || return 2
  fi
  ensure_brew || return $?
  run brew install "--$kind" "$package"
  (( DRY_RUN )) || command -v "$exe" >/dev/null 2>&1
}
clone_plugin() {
  local url="$1" dst="$2" stage
  check_parents "$dst" || return $?
  if exists "$dst"; then
    [[ -d "$dst/.git" && ! -L "$dst" ]] || { say "Existing non-repository/plugin link preserved: $dst"; return 2; }
    [[ "$(git -C "$dst" remote get-url origin)" == "$url" ]] || { say "Foreign repository, preserved: $dst"; return 2; }
    if [[ "$MODE" == update ]]; then
      [[ -z "$(git -C "$dst" status --porcelain)" ]] || { say "Dirty repository, preserved: $dst"; return 2; }
      approve_change "$dst" || return $?
      run git -C "$dst" pull --ff-only
    else
      say "Keeping existing plugin: $dst"
    fi
    return
  fi
  if (( DRY_RUN )); then say "Would clone $url -> $dst"; return; fi
  mkdir -p "$(dirname "$dst")"
  stage=$(mktemp -d "$(dirname "$dst")/.dotfiles-clone.XXXXXX")
  if git clone --depth 1 "$url" "$stage/repo"; then
    mv "$stage/repo" "$dst"
    rmdir "$stage"
  else
    rm -rf -- "$stage"
    return 1
  fi
}
sync_ai() {
  local name="$1" dir="$2"
  check_parents "$dir/settings" || return $?
  run mkdir -p "$dir"
  case "$name" in
    claude) prepare_settings "$dir/settings.json" "$ROOT/install/defaults/claude.json" || return $?;;
    codex) prepare_settings "$dir/config.toml" /dev/null || return $?;;
  esac
  run env DOTFILES_INSTALL=1 DOTFILES_INSTALL_ROOT="$ROOT" BACKUP_ROOT="$BACKUP_ROOT" \
    zsh -f "$ROOT/install/ai-sync.zsh" "$name"
  say "$name: launch the app to sign in; restart existing sessions to reload configuration."
}
prepare_settings() {
  local dst="$1" seed="$2"
  if ! exists "$dst"; then copy_file "$seed" "$dst"; return; fi
  if [[ -L "$dst" || ! -f "$dst" ]]; then
    say "Settings must be a local regular file; preserved: $dst"; return 2
  fi
  # The adapter asks before an actual settings merge.
}
restore_backup() {
  local id="$1" slot dst
  [[ "$id" != */* && -f "$BACKUP_ROOT/$id/manifest.tsv" ]] || die 'Unknown backup ID.'
  while IFS=$'\t' read -r slot dst <&3; do
    [[ "$slot" == item.* && "$slot" != */* ]] || die 'Invalid backup manifest.'
    safe_path "$dst"
    check_parents "$dst" || return $?
    say "Restore $dst from $id/$slot?"
    ask 'Restore this item (current content will be backed up first)?' || continue
    if exists "$dst"; then backup "$dst"; fi
    mkdir -p "$(dirname "$dst")"
    rm -rf -- "$dst"
    cp -pPR "$BACKUP_ROOT/$id/$slot/original" "$dst"
  done 3< "$BACKUP_ROOT/$id/manifest.tsv"
}
doctor() {
  local exe pair
  say "Platform: $(uname -s) $(uname -m); repository: $ROOT"
  for exe in git zsh vim tmux jq python3 claude codex grok opencode gh; do
    if command -v "$exe" >/dev/null 2>&1; then say "$exe: $(command -v "$exe")"
    else say "$exe: missing (optional unless selected)"; fi
  done
  for pair in '.zshrc:zsh/zshrc.conf' '.vimrc:vim/vimrc.conf' '.tmux.conf:tmux/tmux.conf'; do
    local dst="$HOME/${pair%%:*}" src="$ROOT/${pair#*:}"
    [[ "$pair" != .zshrc:* ]] || dst="${ZDOTDIR:-$HOME}/.zshrc"
    if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then say "$dst: linked"
    else say "$dst: not managed by this installer"; fi
  done
  say 'Authentication: run gh auth status; launch each selected assistant to verify provider access.'
  say 'OpenCode workflow: opencode_workflow --doctor (writes temporary runtime state).'
  say 'Life memory: ~/.local/share/life-memory-venv/bin/python ~/dotfiles/ai/memory/memory.py doctor'
}
usage() {
  say 'Usage: ./deploy.sh [--only zsh,vim,tmux,emacs,claude,codex,grok,opencode,life-memory,private-config] [--dry-run] [--update]'
  say '       ./deploy.sh --doctor | --restore BACKUP_ID | --help'
  say 'All install/overwrite choices are interactive. Dry-run and doctor make no changes.'
}
sync_selection() {
  # Remember declined AI integrations so shell wrappers cannot enable them later.
  local id="$1" enabled="$2" dir="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/disabled-sync"
  case "$id" in claude|codex|grok|opencode) ;; *) return 0;; esac
  (( DRY_RUN )) && return 0
  if [[ "$enabled" == yes ]]; then
    if [[ -f "$dir/$id" ]]; then rm -f "$dir/$id"; fi
  else
    mkdir -p "$dir"
    touch "$dir/$id"
  fi
}
main() {
  local module id status selected=() known=',' failures=0
  while (( $# )); do
    case "$1" in
      --only) [[ $# -ge 2 && -n "$2" ]] || die '--only needs component names'; ONLY="$2"; shift;;
      --dry-run) DRY_RUN=1;;
      --update) MODE=update;;
      --doctor) MODE=doctor;;
      --restore) [[ $# -eq 2 && "$MODE" == install && "$DRY_RUN" == 0 && -z "$ONLY" ]] || die '--restore must be used alone with one backup ID'; restore_backup "$2"; return;;
      --help|-h) usage; return;;
      *) die "Unknown option: $1";;
    esac
    shift
  done
  brew_path || true
  export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"
  if [[ "$MODE" == doctor ]]; then doctor; return; fi
  [[ "$(uname -s)" == Darwin ]] || die 'This installer supports macOS only.'
  [[ "$ROOT" == "$(cd "$HOME" && pwd -P)/dotfiles" ]] || die 'Clone this repository at ~/dotfiles; runtime integrations currently require that location.'
  if (( ! DRY_RUN )); then
    xcode-select -p >/dev/null 2>&1 || die 'Install Command Line Tools with xcode-select --install, then rerun setup.'
  fi
  for module in "$ROOT"/install/modules/*.sh; do
    id="${module##*/}"; id="${id%.sh}"; known="$known$id,"
  done
  if [[ -n "$ONLY" ]]; then
    local requested requests=()
    IFS=',' read -r -a requests <<< "$ONLY"
    for requested in "${requests[@]}"; do [[ "$known" == *",$requested,"* ]] || die "Unknown component: $requested"; done
  fi
  if [[ "$MODE" == update ]]; then
    say 'Update plugins and optionally selected Homebrew packages. Update dotfiles first with git pull --ff-only, then rerun this command.'
  fi
  selected=(zsh vim tmux emacs claude codex grok opencode private-config life-memory)
  for module in "$ROOT"/install/modules/*.sh; do
    id="${module##*/}"; id="${id%.sh}"
    [[ " ${selected[*]} " == *" $id "* ]] || selected+=("$id")
  done
  for id in "${selected[@]}"; do
    [[ -z "$ONLY" || ",$ONLY," == *",$id,"* ]] || continue
    if (( ! DRY_RUN )) && ! ask "Set up $id?"; then
      sync_selection "$id" no
      RESULTS+=("$id: skipped"); continue
    fi
    say "=== $id ==="
    # Separate Bash processes keep errexit effective inside modules.
    set +e
    ROOT="$ROOT" DRY_RUN="$DRY_RUN" MODE="$MODE" /bin/bash "$ROOT/install/module.sh" "$id"
    status=$?
    set -e
    case "$status" in
      0) sync_selection "$id" yes; if (( DRY_RUN )); then RESULTS+=("$id: preview only"); else RESULTS+=("$id: completed"); fi;;
      2) sync_selection "$id" no; RESULTS+=("$id: skipped / action needed");;
      130) say 'Installation cancelled.'; exit 130;;
      *) RESULTS+=("$id: FAILED ($status)"); failures=$((failures + 1));;
    esac
  done
  say ''; say 'Summary:'; printf '  %s\n' "${RESULTS[@]}"
  say "Backups (when requested): $BACKUP_ROOT"
  say 'Start a new terminal. Sign in to selected apps; restart OpenCode to reload its catalog.'
  (( failures == 0 ))
}
