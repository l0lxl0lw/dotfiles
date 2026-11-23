# Auto-ls on directory change (interactive shells only; keeps `cd` output out
# of agent tool results, where it was polluting every Bash call)
chpwd() {
  [[ -o interactive && -z $CLAUDECODE ]] || return
  ls
}

# open a PR to main from the current branch (assumes commits are already pushed)
gpr() {
  if [[ -z "$1" ]]; then
    echo "Usage: gpr <pr-title>"
    return 1
  fi
  local branch
  branch=$(git branch --show-current)
  if [[ -z "$branch" ]]; then
    echo "Not on a branch (detached HEAD?)."
    return 1
  fi
  if [[ "$branch" == "main" || "$branch" == "master" ]]; then
    echo "Refusing to PR from $branch. Switch to a feature branch first (e.g. gcb my-feature)."
    return 1
  fi
  gh pr create --title "$1" --body "" --base main
}

# git checkout branch: switch to existing remote branch, or create a new one
gcb() {
  if [[ -z "$1" ]]; then
    echo "Usage: gcb <branch-name>"
    return 1
  fi
  git fetch origin
  if git show-ref --verify --quiet "refs/remotes/origin/$1"; then
    git switch "$1"
  else
    git switch -c "$1"
  fi
}

# after PR merged: switch to default branch, pull, delete the merged feature branch
gsync() {
  local branch base="${1:-main}"
  branch=$(git branch --show-current)
  git checkout "$base" && git pull --rebase --autostash --prune
  if [[ -n "$branch" && "$branch" != "$base" ]]; then
    git branch -d "$branch"   # safe delete, refuses if unmerged
  fi
}

# Claude agent selector
ca() {
  local agents_dir="$HOME/.claude/agents"
  local agent="$1"
  shift 2>/dev/null

  if [[ -z "$agent" ]]; then
    echo "Usage: ca <agent> [claude args...]"
    echo "Available agents:"
    for f in "$agents_dir"/*.md; do
      [[ -f "$f" ]] && echo "  ${${f:t}%.md}"
    done
    for d in "$agents_dir"/*/; do
      [[ -d "$d" ]] && echo "  ${${d:t}%/}"
    done
    return 1
  fi

  local prompt_file=""
  if [[ -f "$agents_dir/$agent.md" ]]; then
    prompt_file="$agents_dir/$agent.md"
  elif [[ -f "$agents_dir/$agent/CLAUDE.md" ]]; then
    prompt_file="$agents_dir/$agent/CLAUDE.md"
  else
    echo "Agent not found: $agent"
    return 1
  fi

  local prompt=$(cat "$prompt_file" | jq -Rs .)
  local agents_json="{\"$agent\":{\"description\":\"$agent agent\",\"prompt\":$prompt}}"

  claude --agents "$agents_json" --agent "$agent" "$@"
}

_ca() {
  local agents_dir="$HOME/.claude/agents"
  local agents=()
  for f in "$agents_dir"/*.md; do
    [[ -f "$f" ]] && agents+=("${${f:t}%.md}")
  done
  for d in "$agents_dir"/*/; do
    [[ -d "$d" ]] && agents+=("${${d:t}%/}")
  done
  _describe 'agent' agents
}
(( $+functions[compdef] )) && compdef _ca ca

# Claude --agent shortcuts with tab completion
ccaa() { claude --chrome --permission-mode auto --agent "${@##*/}"; }
ccta() { claude --dangerously-skip-permissions --chrome --agent "${@##*/}"; }

_claude_agents() {
  local -a usr_vals proj_vals
  local global_dir="$HOME/.claude/agents"
  local project_dir=".claude/agents"

  if [[ -d "$global_dir" ]]; then
    for f in "$global_dir"/**/*.md(N); do
      local rel="${f#$global_dir/}"
      usr_vals+=("${rel%.md}")
    done
  fi

  if [[ -d "$project_dir" ]]; then
    for f in "$project_dir"/**/*.md(N); do
      local rel="${f#$project_dir/}"
      proj_vals+=("${rel%.md}")
    done
  fi

  local -a usr_disp proj_disp
  for v in "${usr_vals[@]}"; do usr_disp+=($'\e[32m'"$v"$'\e[0m'); done
  for v in "${proj_vals[@]}"; do proj_disp+=($'\e[36m'"$v"$'\e[0m'); done

  (( ${#usr_vals} )) && compadd -l -V usr -X '== User Agents ==' -d usr_disp -a usr_vals
  (( ${#proj_vals} )) && compadd -l -V proj -X '== Project Agents ==' -d proj_disp -a proj_vals
}
(( $+functions[compdef] )) && compdef _claude_agents ccaa ccta

# ---------------------------------------------------------------------------
# Linking tracked config into Claude, Codex and Grok user directories
#
# Every tool reads a user-level directory that is a SHARED namespace: our
# symlinks live next to real directories installed by other tools (gstack under
# ~/.claude/skills, Codex's own .system/ under ~/.codex/skills, another vendor's
# hook JSON under ~/.grok/hooks). So the plumbing below is surgical on two axes:
#
#   * It only ever deletes a symlink that points back into a root we own.
#     Real directories and other installers' symlinks are never touched.
#   * It converges rather than rebuilds -- a link that is already correct is
#     left alone. The steady state is zero writes and zero output, so it is
#     safe to run from a hook or a command wrapper.
# ---------------------------------------------------------------------------

# Anything symlinked out of one of these was put there by us and is ours to
# remove. ~/dotfiles-private is the optional private overlay, whose skills and
# agents are linked alongside the public ones. The later entries are
# pre-migration homes (the personal ~/dotfiles clone and the old Claude config
# repo), kept so a machine that still has those links gets them re-pointed
# rather than orphaned.
typeset -g _AGENTCFG_PRIVATE="$HOME/dotfiles-private"
typeset -ga _AGENTCFG_ROOTS=("$HOME/dotfiles" "$_AGENTCFG_PRIVATE" "$HOME/dotfiles" "$HOME/workspace/claude-config")
typeset -gi _AGENTCFG_LINKED=0 _AGENTCFG_REMOVED=0 _AGENTCFG_SKIPPED=0

_agentcfg_reset() { _AGENTCFG_LINKED=0; _AGENTCFG_REMOVED=0; _AGENTCFG_SKIPPED=0 }

_agentcfg_enabled() {
  [[ "${DOTFILES_INSTALL:-}" == 1 || ! -f "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/disabled-sync/$1" ]]
}

# True if $1 is a symlink whose target lies under a root we own. Reads the
# literal link target rather than testing -e, so a DANGLING link still matches
# and gets cleaned up -- ${1:A} resolves a broken link to itself and would miss
# it entirely. Relative targets are made absolute lexically, no filesystem access.
_agentcfg_is_managed() {
  [[ -L "$1" ]] || return 1
  local target root
  target=$(readlink "$1")
  [[ "$target" == /* ]] || target="${1:h}/$target"
  target="${target:a}"
  # Active hubs plus legacy roots when zsh/hubs.zsh is loaded; legacy only otherwise.
  local -a roots=($_AGENTCFG_ROOTS)
  (( $+functions[_hubs_roots] )) && roots=(${(f)"$(_hubs_roots)"})
  for root in $roots; do
    [[ "$target" == "$root"/* ]] && return 0
  done
  return 1
}

# _agentcfg_link <target> <dest> <label>
# Point dest at target, unless it already does. Refuses to clobber a real file
# or directory, or a symlink another installer owns.
_agentcfg_link() {
  local target="$1" dst="$2" what="$3"
  if [[ "${DOTFILES_INSTALL:-}" == 1 ]]; then
    [[ -L "$dst" && "$(readlink "$dst")" == "$target" ]] && return 0
    local result
    bash "$DOTFILES_INSTALL_ROOT/install/link.sh" link "$target" "$dst"
    result=$?
    if (( result == 0 )); then
      (( _AGENTCFG_LINKED++ )); return 0
    elif (( result == 2 )); then
      (( _AGENTCFG_SKIPPED++ )); return 1
    else
      exit "$result"
    fi
  fi
  if [[ -L "$dst" ]]; then
    if _agentcfg_is_managed "$dst"; then
      [[ "$(readlink "$dst")" == "$target" ]] && return 0   # already correct
    else
      echo "  $what: $dst is a symlink owned by something else, leaving it" >&2
      (( _AGENTCFG_SKIPPED++ )); return 1
    fi
  elif [[ -e "$dst" ]]; then
    echo "  $what: $dst already exists and is not a symlink, leaving it" >&2
    (( _AGENTCFG_SKIPPED++ )); return 1
  fi
  if (( ${_HUBS_DRY:-0} )); then
    echo "would link $dst -> $target"; (( _AGENTCFG_LINKED++ )); return 0
  fi
  ln -sfn "$target" "$dst" && (( _AGENTCFG_LINKED++ ))
}

# Removal and copy go through these so --dry-run can narrate instead of act.
_hubs_rm() {
  if (( ${_HUBS_DRY:-0} )); then echo "would remove $1"; else rm -f -- "$1"; fi
  (( _AGENTCFG_REMOVED++ ))
}
_hubs_cp() {
  if (( ${_HUBS_DRY:-0} )); then echo "would copy $2 <- $1"; return 0; fi
  cp -- "$1" "$2"
}

# _agentcfg_sync_skill_sources <dest-skills-dir> <src-skills-dir>...
# Agent tools discover skills as <dir>/<name>/SKILL.md, so each source
# tree may nest them under categories and they get flattened to their basename.
# A later source wins a name and the override is printed, so a work hub can
# shadow a personal copy on purpose and the drift stays visible. Missing
# sources are skipped; links into them are not managed, so an absent source
# never prunes its own links -- the data loss this design exists to prevent.
_agentcfg_sync_skill_sources() {
  local dst="$1" src f key parent nested
  local -A want
  shift
  (( ${_HUBS_DRY:-0} )) || mkdir -p "$dst"

  for src in "$@"; do
    [[ -d "$src" ]] || continue
    for f in "$src"/**/SKILL.md(N-.); do
      # Ignore a SKILL.md nested inside another skill (examples, templates)
      nested=0; parent="${f:h:h}"
      while [[ "$parent" == "$src"/?* ]]; do
        [[ -f "$parent/SKILL.md" ]] && { nested=1; break }
        parent="${parent:h}"
      done
      (( nested )) && continue

      key="${f:h:t}"
      (( ${+want[$key]} )) && echo "override skill '$key': ${f:h} over ${want[$key]}"
      want[$key]="${f:h}"
    done
  done

  for f in "$dst"/*(N@); do
    _agentcfg_is_managed "$f" || continue
    (( ${+want[${f:t}]} )) && continue
    _hubs_rm "$f"
  done
  for key in ${(ko)want}; do
    _agentcfg_link "${want[$key]}" "$dst/$key" "skill '$key'"
  done
}

# _agentcfg_sync_skills <src-skills-dir> <dest-skills-dir>
_agentcfg_sync_skills() {
  _agentcfg_sync_skill_sources "$2" "$1"
}

# _codex_stage_repo_claude_skills [repo-root]
# Expose a repository's Claude skills through a temporary user-skill catalog.
# Skips staging when .claude/skills resolves to the repo's .agents/skills.
# The caller owns the returned directory and must remove it after Codex exits.
_codex_stage_repo_claude_skills() {
  emulate -L zsh
  setopt extended_glob

  local root="${1:-}"
  if [[ -z "$root" ]]; then
    (( $+commands[git] )) || return 0
    root=$(command git -C "$PWD" rev-parse --show-toplevel 2>/dev/null) || return 0
  fi

  local src="$root/.claude/skills"
  local native="$root/.agents/skills"
  # Codex already reads .agents/skills natively; staging it would list skills twice.
  [[ -d "$native" && "${src:A}" == "${native:A}" ]] && return 0
  local -a skill_files=("$src"/**/SKILL.md(N-.))
  (( ${#skill_files} )) || return 0

  local skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
  mkdir -p "$skills_dir" || return 1

  local stage
  stage=$(mktemp -d "$skills_dir/repo-session.XXXXXX") || return 1
  if ! ln -s "$src" "$stage/project"; then
    rmdir -- "$stage"
    return 1
  fi

  print -r -- "$stage"
}

# Remove only a staging directory created by the helper above. Avoid recursive
# deletion: a valid stage contains one symlink and then becomes empty.
_codex_cleanup_repo_claude_skills() {
  emulate -L zsh

  local stage="${1:-}"
  local skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
  [[ -n "$stage" && "$stage" == "$skills_dir"/repo-session.* ]] || return 1
  [[ -d "$stage" && -L "$stage/project" ]] || return 1

  rm -f -- "$stage/project" || return 1
  rmdir -- "$stage"
}

# _hubs_copy_generated <dest-dir> <glob> <src-dir>...
# Codex 0.166 lists symlinked ~/.codex/agents/*.toml but cannot spawn them
# ("agent type is currently not available"), so generated roles are copied;
# OpenCode agents get the same treatment so machine tiers can be baked in.
# A later source wins a name and the override is printed. A copy is ours when
# it starts with render.py's notice or is listed in .copied-roles from the
# previous sync; foreign files are never touched.
_hubs_copy_generated() {
  local dst="$1" glob="$2" f
  shift 2
  local ledger="$dst/.copied-roles" src
  local -A want
  for src in "$@"; do
    [[ -d "$src" ]] || continue
    for f in "$src"/${~glob}(N-.); do
      (( ${+want[${f:t}]} )) && echo "override agent '${f:t}': $f over ${want[${f:t}]}"
      want[${f:t}]="$f"
    done
  done
  local -a copied=()
  [[ -f "$ledger" ]] && copied=("${(@f)$(<"$ledger")}")
  (( ${_HUBS_DRY:-0} )) || mkdir -p "$dst"
  for f in "$dst"/${~glob}(N); do
    (( ${+want[${f:t}]} )) && continue
    if _agentcfg_is_managed "$f" || { [[ ! -L "$f" ]] && { _hubs_is_generated "$f" || (( ${copied[(Ie)${f:t}]} > 0 )) } }; then
      _hubs_rm "$f"
    fi
  done
  local -a now=()
  for f in ${(ok)want}; do
    local role="${want[$f]}" out="$dst/$f"
    if [[ -e "$out" || -L "$out" ]]; then
      if cmp -s -- "$role" "$out" && [[ ! -L "$out" ]]; then
        now+=("$f"); continue
      fi
      if ! _agentcfg_is_managed "$out" && { [[ -L "$out" ]] || { ! _hubs_is_generated "$out" && (( ${copied[(Ie)$f]} == 0 )) } }; then
        echo "  agent '$f': $out is not ours, leaving it" >&2
        (( _AGENTCFG_SKIPPED++ )); continue
      fi
      (( ${_HUBS_DRY:-0} )) || rm -f -- "$out"
    fi
    _hubs_cp "$role" "$out" && now+=("$f") && (( _AGENTCFG_LINKED++ ))
  done
  (( ${_HUBS_DRY:-0} )) || print -rl -- $now > "$ledger"
}

# True when the file opens with a render notice (old or new renderer), as the
# first line (TOML) or the line after the frontmatter fence (Markdown).
_hubs_is_generated() {
  local first second
  { IFS= read -r first; IFS= read -r second; } < "$1" 2>/dev/null
  [[ "$first" == '# Generated by '*'render.py'* ]] && return 0
  [[ "$first" == '---' && "$second" == '# Generated by '*'render.py'* ]]
}

# _codex_sync_agent_roles <dest-dir> <src-dir>...
# Legacy entry point: the first source wins, as the old merge functions
# expect, until hubs_sync replaces them.
_codex_sync_agent_roles() {
  local dst="$1"; shift
  local -a rev=("${(Oa)@}")
  _hubs_copy_generated "$dst" '*.toml' "${rev[@]}" >/dev/null
}

# Warn (never fail) when a Codex tier model in the merged tiers (each hub's
# tiers.json plus the machine overlay) is absent from the catalog Codex last
# fetched. Silent when the cache is missing or unreadable.
#   _hubs_warn_unknown_codex_models <codex-dir> <hub>...
_hubs_warn_unknown_codex_models() {
  local cache="$1/models_cache.json"; shift
  [[ -f "$cache" ]] && (( $+commands[python3] )) || return 0
  local overlay="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/tiers.json"
  python3 -B "${_HUBS_DOTFILES:-$HOME/dotfiles}/agents/check_models.py" "$cache" "$overlay" "$@" >&2
  return 0
}

# Legacy entry point used by codex_merge_config until hubs_sync replaces it:
# the ai/shared/agents tree carries its tiers.json like a hub does.
_codex_warn_unknown_tier_models() {
  local cache="$1/models_cache.json"
  [[ -f "$cache" ]] && (( $+commands[python3] )) || return 0
  python3 -B "${_HUBS_DOTFILES:-$HOME/dotfiles}/agents/check_models.py" "$cache" /nonexistent "$HOME/dotfiles/ai/shared/agents" >&2
  return 0
}

# Silent when there was nothing to do.
_agentcfg_report() {
  (( _AGENTCFG_LINKED || _AGENTCFG_REMOVED || _AGENTCFG_SKIPPED )) && \
    echo "$1: $_AGENTCFG_LINKED linked, $_AGENTCFG_REMOVED stale removed, $_AGENTCFG_SKIPPED skipped"
  return 0
}

# Claude-side extras that are not hub content: the statusline hook script and
# the settings.json repair that points at it. Hooks still live under
# ai/claude/hooks until plan 4 relocates them.
#   _hubs_claude_settings <claude-dir>
_hubs_claude_settings() {
  emulate -L zsh
  setopt extended_glob
  local claude_dir="$1" repo="${_HUBS_DOTFILES:-$HOME/dotfiles}/ai/claude" f key
  local -A want_h
  (( ${_HUBS_DRY:-0} )) && { echo "would check hooks and settings.json in $claude_dir"; return 0 }
  # Hooks: top-level files only. ~/.claude/hooks can also hold real,
  # plugin-owned scripts that settings.json depends on -- never overwrite one.
  if [[ -d "$repo/hooks" ]]; then
    mkdir -p "$claude_dir/hooks"
    for f in "$repo"/hooks/*(N-.); do want_h[${f:t}]="$f"; done

    for f in "$claude_dir"/hooks/*(N@); do
      _agentcfg_is_managed "$f" || continue
      (( ${+want_h[${f:t}]} )) && continue
      rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
    done
    for key in ${(ko)want_h}; do
      [[ -x "${want_h[$key]}" ]] || chmod +x "${want_h[$key]}"  # fix source, only if wrong
      _agentcfg_link "${want_h[$key]}" "$claude_dir/hooks/$key" "hook '$key'"
    done
  fi

  # Point settings.json at the statusline hook, and drop hook entries whose
  # script is gone. The hook links above are pruned when a script leaves the
  # repo, but its settings.json entry is not, so Claude would report a missing
  # file on every event. Only commands of the exact form
  # `sh ~/.claude/hooks/<file>` (the form this repo writes) are considered, and
  # only when <file> no longer exists, so working hooks and other tools'
  # commands are never touched. Only writes when something actually differs,
  # and stages through a temp file that is validated as JSON before the move,
  # so a jq failure can never truncate settings.json.
  local settings="$claude_dir/settings.json"
  local want='sh ~/.claude/hooks/statusline.sh'
  local hookre='^(?:ba)?sh (?:~|\$HOME)/\.claude/hooks/(?<n>[^/ ]+)$'
  if [[ -f "$settings" && ! -L "$settings" ]] && (( $+commands[jq] )); then
    local have tmp name filter='.'
    local -a dead changes
    have=$(jq -r '.statusLine.command // ""' "$settings" 2>/dev/null) || {
      echo "claude_merge_config: invalid settings.json; left untouched" >&2
      return 1
    }
    if [[ -e "$claude_dir/hooks/statusline.sh" && "$have" != "$want" ]]; then
      filter+=' | .statusLine = {"type":"command","command":$cmd}'
      changes+=("set statusLine")
    fi
    for name in ${(f)"$(jq -r --arg re "$hookre" '
        [.hooks // {} | .[] | arrays | .[] | .hooks // [] | .[]
         | .command // empty | strings | capture($re).n] | unique | .[]' "$settings")"}; do
      [[ -e "$claude_dir/hooks/$name" ]] || dead+=("$name")
    done
    if (( $#dead )); then
      filter+=' | .hooks |= with_entries(.value |= (map(.hooks |= map(select(
                  ([.command // "" | strings | capture($re).n] | first) as $n
                  | $n == null or ($n | IN($dead[]) | not))))
                | map(select(.hooks | length > 0))))
              | .hooks |= with_entries(select(.value | length > 0))
              | if .hooks == {} then del(.hooks) else . end'
      changes+=("removed hooks for missing ${(j:, :)dead}")
    fi
    if (( $#changes )); then
      if [[ "${DOTFILES_INSTALL:-}" == 1 ]]; then
        bash "$DOTFILES_INSTALL_ROOT/install/link.sh" approve "$settings"
        local approval=$?
        if (( approval == 2 )); then
          (( _AGENTCFG_SKIPPED++ )); return 0
        elif (( approval != 0 )); then
          exit "$approval"
        fi
      else
        echo "claude_merge_config: settings.json needs: ${(j:; :)changes}; run ~/dotfiles/deploy.sh --only claude to review" >&2
        (( _AGENTCFG_SKIPPED++ )); return 0
      fi
      tmp=$(mktemp "${settings}.XXXXXX") || return 1
      if jq --arg cmd "$want" --arg re "$hookre" --argjson dead "$(jq -nc '$ARGS.positional' --args -- $dead)" \
           "$filter" "$settings" >"$tmp" \
         && [[ -s "$tmp" ]] && jq -e . "$tmp" >/dev/null 2>&1; then
        mv -f "$tmp" "$settings"
        echo "claude_merge_config: ${(j:; :)changes} in settings.json"
      else
        rm -f -- "$tmp"
        echo "claude_merge_config: jq failed, settings.json left untouched" >&2
      fi
    fi
  fi

  return 0
}

# Codex-side extra: the managed block spliced into config.toml. The fragment
# still lives under ai/codex until plan 4 relocates it.
#   _hubs_codex_config <codex-dir>
_hubs_codex_config() {
  emulate -L zsh
  setopt extended_glob
  local codex_dir="$1" repo="${_HUBS_DOTFILES:-$HOME/dotfiles}/ai/codex"
  (( ${_HUBS_DRY:-0} )) && { echo "would check the managed block in $codex_dir/config.toml"; return 0 }
  # Settings that have to live inside config.toml (status_line and friends).
  #
  # config.toml can't be a symlink to the repo: it also carries machine-local
  # absolute paths and a [projects."..."] trust list of private repos, and Codex
  # rewrites it. Codex has no include directive either, and `--profile` only
  # applies when -p is passed, so it would miss the desktop app and any other
  # entry point. So a tracked fragment gets spliced into the real file between
  # markers instead, and re-applied on every launch -- self-healing if Codex
  # ever overwrites it.
  local managed="$repo/config.toml.managed"
  local cfg="$codex_dir/config.toml"
  local beg='# >>> dotfiles managed >>>'
  local fin='# <<< dotfiles managed <<<'
  if [[ -f "$managed" && -f "$cfg" && ! -L "$cfg" ]]; then
    local current desired tmp probe
    current=$(awk -v b="$beg" -v e="$fin" 'index($0,b){f=1;next} index($0,e){f=0;next} f' "$cfg")
    desired=$(<"$managed")
    if [[ "$current" != "$desired" ]]; then
      if [[ "${DOTFILES_INSTALL:-}" == 1 ]]; then
        bash "$DOTFILES_INSTALL_ROOT/install/link.sh" approve "$cfg"
        local approval=$?
        if (( approval == 2 )); then
          (( _AGENTCFG_SKIPPED++ )); return 0
        elif (( approval != 0 )); then
          exit "$approval"
        fi
      elif ! command grep -q '^# >>> dotfiles managed >>>$' "$cfg"; then
        echo "codex_merge_config: run ~/dotfiles/deploy.sh --only codex to approve managed settings" >&2
        (( _AGENTCFG_SKIPPED++ )); return 0
      fi
      tmp=$(mktemp "${cfg}.XXXXXX") || return 1
      {
        # Strip any previous block, then drop trailing blank lines so repeated
        # runs don't accumulate them.
        awk -v b="$beg" -v e="$fin" 'index($0,b){f=1;next} index($0,e){f=0;next} !f' "$cfg" |
          awk '{a[n++]=$0} END{while(n>0 && a[n-1]=="") n--; for(i=0;i<n;i++) print a[i]}'
        print -r -- ""
        print -r -- "$beg"
        print -r -- "$desired"
        print -r -- "$fin"
      } > "$tmp"

      # Prove the result is a config Codex will actually load before swapping it
      # in. A duplicate [tui] table, say, would otherwise brick every launch.
      # `command` is required here: bare `codex` is the wrapper below, and that
      # would recurse.
      probe="${tmp}.home"
      mkdir -p "$probe" && cp "$tmp" "$probe/config.toml"
      if CODEX_HOME="$probe" command codex debug prompt-input >/dev/null 2>&1; then
        if [[ "${DOTFILES_INSTALL:-}" != 1 ]]; then
          local backup
          backup=$(mktemp "${cfg}.dotfiles-backup.XXXXXX") || return 1
          cp -p "$cfg" "$backup" || return 1
        fi
        mv -f "$tmp" "$cfg"
        echo "codex_merge_config: updated managed block in config.toml"
      else
        rm -f -- "$tmp"
        echo "codex_merge_config: patched config.toml would not parse, left untouched" >&2
        (( _AGENTCFG_SKIPPED++ ))
      fi
      rm -rf -- "$probe"
    fi
  fi

  return 0
}

# Legacy names: the per-tool merge functions are now hubs_sync for one tool.
claude_merge_config() { hubs_sync --tool claude "$@" }
codex_merge_config() { hubs_sync --tool codex "$@" }

# Sync the active hubs into Codex, expose this repository's Claude skills only
# while the process is alive, then hand off to the real binary.
codex() {
  if ! _agentcfg_enabled codex; then command codex "$@"; return $?; fi
  hubs_sync --tool codex || return

  local stage="" exit_code=1
  stage=$(_codex_stage_repo_claude_skills) || return
  {
    command codex "$@"
    exit_code=$?
  } always {
    if [[ -n "$stage" ]]; then
      _codex_cleanup_repo_claude_skills "$stage" || \
        echo "codex: could not remove temporary skill catalog $stage" >&2
    fi
  }
  return $exit_code
}

# Sync the active hubs into Claude, then hand off to the real binary. Claude
# reads a repository's own .claude/ natively, so nothing is staged.
claude() {
  if ! _agentcfg_enabled claude; then command claude "$@"; return $?; fi
  hubs_sync --tool claude || return
  command claude "$@"
}

# Same for OpenCode, which reads ~/.config/opencode.
opencode() {
  if ! _agentcfg_enabled opencode; then command opencode "$@"; return $?; fi
  hubs_sync --tool opencode || return
  command opencode "$@"
}

# Link ~/dotfiles/ai/grok into ~/.grok (skills, agents, hooks, AGENTS.md, settings).
#
# Driven from two places, on purpose: the grok() wrapper below (which is the one
# moment we know the config is about to be read), and a tracked SessionStart hook
# at ai/grok/hooks/dotfiles-sync.json, which covers launches that never touch this
# shell -- an IDE or ACP client running `grok agent stdio`. The sync converges and
# is silent when there is nothing to do, so running it twice costs nothing.
grok_merge_config() {
  _agentcfg_enabled grok || return 0
  emulate -L zsh
  setopt extended_glob

  local grok_dir="${GROK_HOME:-$HOME/.grok}"
  local repo="$HOME/dotfiles/ai/grok"
  [[ -d "$repo" ]] || { echo "grok_merge_config: $repo not found" >&2; return 1 }
  # Don't create ~/.grok; its absence means Grok isn't installed here.
  [[ -d "$grok_dir" ]] || return 0

  local f key
  local -A want_a want_h
  _agentcfg_reset

  # Skills. ~/.grok/skills is ours alone -- Grok's own bundled skills live under
  # ~/.grok/bundled/skills and marketplace plugins under ~/.grok/plugins, neither
  # of which we touch. Grok-local skills win by name; ai/shared/skills holds
  # cross-tool skills.
  _agentcfg_sync_skill_sources "$grok_dir/skills" \
    "$repo/skills" \
    "$HOME/dotfiles/ai/shared/skills"

  # Global instructions: Grok's equivalent of ~/.claude/CLAUDE.md.
  [[ -f "$repo/AGENTS.md" ]] && \
    _agentcfg_link "$repo/AGENTS.md" "$grok_dir/AGENTS.md" "AGENTS.md"

  # Settings. Unlike Codex, Grok reads a second config file layered *below* the
  # one it writes to, so tracked defaults can just be a symlink: no marker splice,
  # no parse probe, no backup. ~/.grok/config.toml stays machine-local and wins on
  # any key it sets.
  [[ -f "$repo/managed_config.toml" ]] && \
    _agentcfg_link "$repo/managed_config.toml" "$grok_dir/managed_config.toml" "managed_config.toml"

  # Agents: flat *.md, since Grok reads ~/.grok/agents/*.md without recursing.
  if [[ -d "$repo/agents" ]]; then
    mkdir -p "$grok_dir/agents"
    for f in "$repo"/agents/*.md(N-.); do want_a[${f:t}]="$f"; done

    for f in "$grok_dir"/agents/*(N@); do
      _agentcfg_is_managed "$f" || continue
      (( ${+want_a[${f:t}]} )) && continue
      rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
    done
    for key in ${(ko)want_a}; do
      _agentcfg_link "${want_a[$key]}" "$grok_dir/agents/$key" "agent '$key'"
    done
  fi

  # Hooks: one JSON file per concern. Grok loads every *.json in ~/.grok/hooks
  # by itself, so unlike the Claude side nothing has to be wired into a settings
  # file afterwards. Other installers drop real files here (orca-status.json) and
  # those are never touched -- pruning only removes symlinks we own.
  if [[ -d "$repo/hooks" ]]; then
    mkdir -p "$grok_dir/hooks"
    for f in "$repo"/hooks/*.json(N-.); do want_h[${f:t}]="$f"; done

    for f in "$grok_dir"/hooks/*(N@); do
      _agentcfg_is_managed "$f" || continue
      (( ${+want_h[${f:t}]} )) && continue
      rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
    done
    for key in ${(ko)want_h}; do
      _agentcfg_link "${want_h[$key]}" "$grok_dir/hooks/$key" "hook '$key'"
    done
  fi

  _agentcfg_report grok_merge_config
}

# Sync tracked Grok config, then hand off to the real binary. Grok does have a
# SessionStart hook (and one is installed from ai/grok/hooks), but a hook fires
# once the session is already coming up, so this is what guarantees the config is
# current *before* it is read. `command` is required: bare `grok` is this wrapper.
grok() {
  grok_merge_config
  command grok "$@"
}

# hubs.zsh defines hubs_sync, which the wrappers above call; load it when this
# file is sourced on its own (tests, install/ai-sync.zsh).
(( $+functions[hubs_sync] )) || source "${${(%):-%x}:A:h}/hubs.zsh"
