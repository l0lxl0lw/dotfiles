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

# Symlink Claude skills/agents/hooks from ~/dotfiles/claude into ~/.claude.
#
# Surgical by design, on two axes:
#
#   * It only ever deletes symlinks that point back into a managed root. Real
#     directories (gstack installs its skills as real dirs) and symlinks owned
#     by other installers are left untouched.
#   * It converges rather than rebuilds -- a link that is already correct is
#     not touched. So the steady state is zero writes and no window in which a
#     concurrently running Claude session sees a missing skill.
#
# Silent when nothing changed, which makes it safe to wire into a SessionStart
# hook. Idempotent.
claude_merge_config() {
  emulate -L zsh          # glob qualifiers work regardless of caller's options
  setopt extended_glob

  local claude_dir="$HOME/.claude"
  local repo="$HOME/dotfiles/claude"
  # Roots we claim ownership of. The second is the pre-migration location, kept
  # so the first run after the move reaps its own stale links.
  local -a managed_roots=("$repo" "$HOME/workspace/claude-config")

  if [[ ! -d "$repo" ]]; then
    echo "claude_merge_config: $repo not found" >&2
    return 1
  fi

  # True if $1 is a symlink whose target lies under a managed root. Reads the
  # literal link target rather than testing -e, so broken links still match and
  # get cleaned up -- ${1:A} resolves a dangling link to itself and would miss
  # them entirely. Relative targets (other installers write links like
  # ../../elsewhere/skills/x) are made absolute lexically, no filesystem access.
  _ccm_is_managed() {
    [[ -L "$1" ]] || return 1
    local target root
    target=$(readlink "$1")
    [[ "$target" == /* ]] || target="${1:h}/$target"
    target="${target:a}"
    for root in $managed_roots; do
      [[ "$target" == "$root"/* ]] && return 0
    done
    return 1
  }

  local f key dest parent nested removed=0 linked=0 skipped=0
  local -A want_s want_a want_h
  local -a emptied

  # Link $2 -> $1 only if it isn't already exactly that. Refuses to touch a
  # real file/dir, or a symlink some other installer owns.
  _ccm_link() {
    local target="$1" dst="$2" what="$3"
    if [[ -L "$dst" ]]; then
      if _ccm_is_managed "$dst"; then
        [[ "$(readlink "$dst")" == "$target" ]] && return 0   # already correct
      else
        echo "claude_merge_config: $what -- $dst is a symlink owned by something else, leaving it" >&2
        (( skipped++ )); return 1
      fi
    elif [[ -e "$dst" ]]; then
      echo "claude_merge_config: $what -- $dst already exists and is not a symlink, leaving it" >&2
      (( skipped++ )); return 1
    fi
    ln -sfn "$target" "$dst" && (( linked++ ))
  }

  # Each section is guarded on its source dir. Without that, a section missing
  # from the repo would prune every managed link and put nothing back -- the
  # same data loss as the rm -rf this replaced, just quieter.

  # Skills: every SKILL.md's parent dir, flattened to ~/.claude/skills/<name>
  if [[ -d "$repo/skills" ]]; then
    mkdir -p "$claude_dir/skills"
    for f in "$repo"/skills/**/SKILL.md(N-.); do
      # Ignore a SKILL.md nested inside another skill (examples, templates)
      nested=0; parent="${f:h:h}"
      while [[ "$parent" == "$repo"/skills/?* ]]; do
        [[ -f "$parent/SKILL.md" ]] && { nested=1; break }
        parent="${parent:h}"
      done
      (( nested )) && continue

      key="${f:h:t}"
      if (( ${+want_s[$key]} )); then
        echo "claude_merge_config: duplicate skill '$key' -- keeping ${want_s[$key]}, ignoring ${f:h}" >&2
        (( skipped++ )); continue
      fi
      want_s[$key]="${f:h}"
    done

    for f in "$claude_dir"/skills/*(N@); do
      _ccm_is_managed "$f" || continue
      (( ${+want_s[${f:t}]} )) && continue
      rm -f -- "$f"; (( removed++ ))
    done
    for key in ${(ko)want_s}; do
      _ccm_link "${want_s[$key]}" "$claude_dir/skills/$key" "skill '$key'"
    done
  fi

  # Agents: mirror the repo tree, symlinking each .md
  if [[ -d "$repo/agents" ]]; then
    mkdir -p "$claude_dir/agents"
    for f in "$repo"/agents/**/*.md(N-.); do want_a[${f#"$repo"/agents/}]="$f"; done

    for f in "$claude_dir"/agents/**/*(N@); do
      _ccm_is_managed "$f" || continue
      (( ${+want_a[${f#"$claude_dir"/agents/}]} )) && continue
      rm -f -- "$f"; (( removed++ ))
    done
    for key in ${(ko)want_a}; do
      dest="$claude_dir/agents/$key"
      mkdir -p "${dest:h}"
      _ccm_link "${want_a[$key]}" "$dest" "agent '$key'"
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
      _ccm_is_managed "$f" || continue
      (( ${+want_h[${f:t}]} )) && continue
      rm -f -- "$f"; (( removed++ ))
    done
    for key in ${(ko)want_h}; do
      [[ -x "${want_h[$key]}" ]] || chmod +x "${want_h[$key]}"  # fix source, only if wrong
      _ccm_link "${want_h[$key]}" "$claude_dir/hooks/$key" "hook '$key'"
    done
  fi

  unset -f _ccm_is_managed _ccm_link

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

  # Silent when there was nothing to do -- this runs from a SessionStart hook,
  # and anything printed there lands in the session as context.
  (( linked || removed || skipped )) && \
    echo "claude_merge_config: $linked linked, $removed stale removed, $skipped skipped"
  return 0
}
# Run from the Claude Code SessionStart hook in ~/.claude/settings.json, so a
# skill added or renamed here is picked up at the start of the next session
# rather than silently dangling. Also fine to invoke by hand.
