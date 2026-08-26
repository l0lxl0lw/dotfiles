# Auto-ls on directory change
chpwd() {
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
compdef _ca ca

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
compdef _claude_agents ccaa ccta

# ---------------------------------------------------------------------------
# Linking tracked config into ~/.claude, ~/.codex and ~/.grok
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
# remove. The second entry is the pre-migration home of the Claude config, kept
# so a machine that still has those links gets them cleaned up rather than
# orphaned.
typeset -ga _AGENTCFG_ROOTS=("$HOME/dotfiles" "$HOME/workspace/claude-config")
typeset -gi _AGENTCFG_LINKED=0 _AGENTCFG_REMOVED=0 _AGENTCFG_SKIPPED=0

_agentcfg_reset() { _AGENTCFG_LINKED=0; _AGENTCFG_REMOVED=0; _AGENTCFG_SKIPPED=0 }

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
  for root in $_AGENTCFG_ROOTS; do
    [[ "$target" == "$root"/* ]] && return 0
  done
  return 1
}

# _agentcfg_link <target> <dest> <label>
# Point dest at target, unless it already does. Refuses to clobber a real file
# or directory, or a symlink another installer owns.
_agentcfg_link() {
  local target="$1" dst="$2" what="$3"
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
  ln -sfn "$target" "$dst" && (( _AGENTCFG_LINKED++ ))
}

# _agentcfg_sync_skill_sources <dest-skills-dir> <src-skills-dir>...
# Both Claude and Codex discover skills as <dir>/<name>/SKILL.md, so each source
# tree may nest them under categories and they get flattened to their basename.
# Missing sources are skipped -- otherwise an absent source would prune every link
# and put nothing back, which is the data loss this design exists to prevent.
_agentcfg_sync_skill_sources() {
  local dst="$1" src f key parent nested
  local -A want
  shift
  (( $# )) || return 0
  mkdir -p "$dst"

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
      if (( ${+want[$key]} )); then
        echo "  duplicate skill '$key': keeping ${want[$key]}, ignoring ${f:h}" >&2
        (( _AGENTCFG_SKIPPED++ )); continue
      fi
      want[$key]="${f:h}"
    done
  done

  for f in "$dst"/*(N@); do
    _agentcfg_is_managed "$f" || continue
    (( ${+want[${f:t}]} )) && continue
    rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
  done
  for key in ${(ko)want}; do
    _agentcfg_link "${want[$key]}" "$dst/$key" "skill '$key'"
  done
}

# _agentcfg_sync_skills <src-skills-dir> <dest-skills-dir>
_agentcfg_sync_skills() {
  _agentcfg_sync_skill_sources "$2" "$1"
}

# True when $1 is one of the generated repository-skill links targeting $2.
# This deliberately has a narrower ownership boundary than
# _agentcfg_is_managed: repository links point outside the dotfiles roots.
_codex_repo_skill_is_managed() {
  [[ -L "$1" ]] || return 1
  local target
  target=$(readlink "$1")
  [[ "$target" == /* ]] || target="${1:h}/$target"
  [[ "${target:a}" == "${2:a}"/* ]]
}

# _codex_sync_repo_claude_skills [repo-root]
# Expose a repository's Claude skills through Codex's native .agents/skills
# discovery. With no explicit root, find the Git repository containing $PWD.
_codex_sync_repo_claude_skills() {
  emulate -L zsh
  setopt extended_glob

  local root="${1:-}"
  if [[ -z "$root" ]]; then
    (( $+commands[git] )) || return 0
    root=$(command git -C "$PWD" rev-parse --show-toplevel 2>/dev/null) || return 0
  fi

  local src="$root/.claude/skills"
  local dst="$root/.agents/skills"

  local f key parent nested target rel current
  local -A want
  for f in "$src"/**/SKILL.md(N-.); do
    # Match the global skill sync: nested SKILL.md files belong to the outer
    # skill, while category directories are flattened to the skill basename.
    nested=0; parent="${f:h:h}"
    while [[ "$parent" == "$src"/?* ]]; do
      [[ -f "$parent/SKILL.md" ]] && { nested=1; break }
      parent="${parent:h}"
    done
    (( nested )) && continue

    key="${f:h:t}"
    if (( ${+want[$key]} )); then
      echo "  duplicate repository skill '$key': keeping ${want[$key]}, ignoring ${f:h}" >&2
      (( _AGENTCFG_SKIPPED++ )); continue
    fi
    want[$key]="${f:h}"
  done

  # An empty source should not introduce .agents into a previously untouched
  # repository, but an existing destination still needs stale-link pruning.
  [[ -d "$dst" || ${#want} -gt 0 ]] || return 0
  mkdir -p "$dst" || return 1

  for f in "$dst"/*(N@); do
    _codex_repo_skill_is_managed "$f" "$src" || continue
    (( ${+want[${f:t}]} )) && continue
    rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
  done

  for key in ${(ko)want}; do
    target="${want[$key]}"
    rel="../../${target#"$root"/}"
    f="$dst/$key"

    if [[ -L "$f" ]]; then
      if _codex_repo_skill_is_managed "$f" "$src"; then
        current=$(readlink "$f")
        [[ "$current" == "$rel" ]] && continue
      else
        echo "  repository skill '$key': $f is owned by something else, leaving it" >&2
        (( _AGENTCFG_SKIPPED++ )); continue
      fi
    elif [[ -e "$f" ]]; then
      echo "  repository skill '$key': native Codex skill wins, leaving $f" >&2
      (( _AGENTCFG_SKIPPED++ )); continue
    fi

    ln -sfn "$rel" "$f" && (( _AGENTCFG_LINKED++ ))
  done

  return 0
}

# Silent when there was nothing to do.
_agentcfg_report() {
  (( _AGENTCFG_LINKED || _AGENTCFG_REMOVED || _AGENTCFG_SKIPPED )) && \
    echo "$1: $_AGENTCFG_LINKED linked, $_AGENTCFG_REMOVED stale removed, $_AGENTCFG_SKIPPED skipped"
  return 0
}

# Link ~/dotfiles/ai/claude into ~/.claude (skills, agents, hooks, statusline).
# Run by hand after adding or renaming a skill, agent, or hook. Existing linked
# files update immediately because they are symlinks.
claude_merge_config() {
  emulate -L zsh          # glob qualifiers work regardless of caller's options
  setopt extended_glob

  local claude_dir="$HOME/.claude"
  local repo="$HOME/dotfiles/ai/claude"
  if [[ ! -d "$repo" ]]; then
    echo "claude_merge_config: $repo not found" >&2
    return 1
  fi

  local f key dest
  local -A want_a want_h
  local -a emptied
  _agentcfg_reset

  # Skills. ~/.claude/skills is shared with gstack, which installs real dirs.
  # Claude-local skills win by name; ai/shared/skills holds cross-tool skills.
  _agentcfg_sync_skill_sources "$claude_dir/skills" \
    "$repo/skills" \
    "$HOME/dotfiles/ai/shared/skills"

  # Agents: mirror the repo tree, symlinking each .md
  if [[ -d "$repo/agents" ]]; then
    mkdir -p "$claude_dir/agents"
    for f in "$repo"/agents/**/*.md(N-.); do want_a[${f#"$repo"/agents/}]="$f"; done

    for f in "$claude_dir"/agents/**/*(N@); do
      _agentcfg_is_managed "$f" || continue
      (( ${+want_a[${f#"$claude_dir"/agents/}]} )) && continue
      rm -f -- "$f"; (( _AGENTCFG_REMOVED++ ))
    done
    for key in ${(ko)want_a}; do
      dest="$claude_dir/agents/$key"
      mkdir -p "${dest:h}"
      _agentcfg_link "${want_a[$key]}" "$dest" "agent '$key'"
    done
    # Drop category dirs left empty by a rename, deepest first. rmdir refuses
    # non-empty dirs, and (N/) never matches a symlink, so this cannot descend
    # into the repo.
    emptied=( "$claude_dir"/agents/**/*(N/) )
    for f in "${(Oa)emptied[@]}"; do rmdir "$f" 2>/dev/null; done
  fi

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

  # Point settings.json at the statusline hook. Only writes when the value
  # actually differs, and stages through a temp file that is validated as JSON
  # before the move, so a jq failure can never truncate settings.json.
  local settings="$claude_dir/settings.json"
  local want='sh ~/.claude/hooks/statusline.sh'
  if [[ -e "$claude_dir/hooks/statusline.sh" && -f "$settings" ]] && (( $+commands[jq] )); then
    local have tmp
    have=$(jq -r '.statusLine.command // ""' "$settings" 2>/dev/null)
    if [[ "$have" != "$want" ]]; then
      tmp=$(mktemp "${settings}.XXXXXX") || return 1
      if jq --arg cmd "$want" \
           '.statusLine = {"type":"command","command":$cmd}' "$settings" >"$tmp" \
         && [[ -s "$tmp" ]] && jq -e . "$tmp" >/dev/null 2>&1; then
        mv -f "$tmp" "$settings"
        echo "claude_merge_config: set statusLine in settings.json"
      else
        rm -f -- "$tmp"
        echo "claude_merge_config: jq failed, settings.json left untouched" >&2
      fi
    fi
  fi

  _agentcfg_report claude_merge_config
}

# Link ~/dotfiles/ai/codex into ~/.codex (skills, AGENTS.md).
#
# Codex has no hook mechanism, so this is driven by the codex() wrapper below --
# it runs just before the binary launches, which costs nothing on shells that
# never invoke codex.
codex_merge_config() {
  emulate -L zsh
  setopt extended_glob

  local codex_dir="$HOME/.codex"
  local repo="$HOME/dotfiles/ai/codex"
  [[ -d "$repo" ]] || { echo "codex_merge_config: $repo not found" >&2; return 1 }
  # Don't create ~/.codex; its absence means Codex isn't installed here.
  [[ -d "$codex_dir" ]] || return 0

  _agentcfg_reset

  # Skills. ~/.codex/skills also holds Codex's own .system/ and any bundled
  # runtime dirs as real directories -- same situation as gstack, left alone.
  #
  # Codex-local skills win by name; ai/shared/skills holds cross-tool skills.
  _agentcfg_sync_skill_sources "$codex_dir/skills" \
    "$repo/skills" \
    "$HOME/dotfiles/ai/shared/skills"

  # Global instructions: one file, Codex's equivalent of ~/.claude/CLAUDE.md.
  [[ -f "$repo/AGENTS.md" ]] && \
    _agentcfg_link "$repo/AGENTS.md" "$codex_dir/AGENTS.md" "AGENTS.md"

  # Codex discovers repository skills only under .agents/skills. Reuse any
  # .claude/skills in the current repository without copying or overwriting a
  # native Codex skill with the same name.
  _codex_sync_repo_claude_skills

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
  if [[ -f "$managed" && -f "$cfg" ]]; then
    local current desired tmp probe
    current=$(awk -v b="$beg" -v e="$fin" 'index($0,b){f=1;next} index($0,e){f=0;next} f' "$cfg")
    desired=$(<"$managed")
    if [[ "$current" != "$desired" ]]; then
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
        cp -p "$cfg" "$cfg.dotfiles.bak"
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

  _agentcfg_report codex_merge_config
}

# Sync tracked Codex config, then hand off to the real binary. Codex offers no
# SessionStart equivalent, so launch time is the one moment we know the config
# is about to be read.
codex() {
  codex_merge_config
  command codex "$@"
}

# Link ~/dotfiles/ai/grok into ~/.grok (skills, agents, hooks, AGENTS.md, settings).
#
# Driven from two places, on purpose: the grok() wrapper below (which is the one
# moment we know the config is about to be read), and a tracked SessionStart hook
# at ai/grok/hooks/dotfiles-sync.json, which covers launches that never touch this
# shell -- an IDE or ACP client running `grok agent stdio`. The sync converges and
# is silent when there is nothing to do, so running it twice costs nothing.
grok_merge_config() {
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
