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
# Surgical by design: it only ever deletes symlinks that point back into a
# managed root. Real directories (gstack installs its skills as real dirs) and
# foreign symlinks (caveman points at ~/.agents/skills) are left untouched.
# Idempotent -- safe to run as often as you like.
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
  # them entirely. Relative targets (caveman's ../../.agents/...) are made
  # absolute lexically, without touching the filesystem.
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

  local f name rel dest parent nested removed=0 linked=0 skipped=0
  local -A seen
  local -a emptied

  # Each section is guarded on its source dir. Without that, a section missing
  # from the repo would prune every managed link and put nothing back -- the
  # same data loss as the rm -rf this replaced, just quieter.

  # Skills: every SKILL.md's parent dir, flattened to ~/.claude/skills/<name>
  if [[ -d "$repo/skills" ]]; then
    mkdir -p "$claude_dir/skills"
    for f in "$claude_dir"/skills/*(N@); do
      _ccm_is_managed "$f" && { rm -f -- "$f"; (( removed++ )) }
    done
    for f in "$repo"/skills/**/SKILL.md(N-.); do
      # Ignore a SKILL.md nested inside another skill (examples, templates)
      nested=0; parent="${f:h:h}"
      while [[ "$parent" == "$repo"/skills/?* ]]; do
        [[ -f "$parent/SKILL.md" ]] && { nested=1; break }
        parent="${parent:h}"
      done
      (( nested )) && continue

      name="${f:h:t}"
      dest="$claude_dir/skills/$name"
      if (( ${+seen[$name]} )); then
        echo "claude_merge_config: duplicate skill '$name' -- keeping ${seen[$name]}, ignoring ${f:h}" >&2
        (( skipped++ )); continue
      fi
      seen[$name]="${f:h}"
      if [[ -e "$dest" && ! -L "$dest" ]]; then
        echo "claude_merge_config: skipping skill '$name' -- $dest is a real directory (owned by another installer)" >&2
        (( skipped++ )); continue
      fi
      ln -sfn "${f:h}" "$dest" && (( linked++ ))
    done
  fi

  # Agents: mirror the repo tree, symlinking each .md
  if [[ -d "$repo/agents" ]]; then
    mkdir -p "$claude_dir/agents"
    for f in "$claude_dir"/agents/**/*(N@); do
      _ccm_is_managed "$f" && { rm -f -- "$f"; (( removed++ )) }
    done
    for f in "$repo"/agents/**/*.md(N-.); do
      rel="${f#"$repo"/agents/}"
      dest="$claude_dir/agents/$rel"
      if [[ -e "$dest" && ! -L "$dest" ]]; then
        echo "claude_merge_config: skipping agent '$rel' -- $dest is not a symlink" >&2
        (( skipped++ )); continue
      fi
      mkdir -p "${dest:h}"
      ln -sfn "$f" "$dest" && (( linked++ ))
    done
    # Drop category dirs left empty by a rename, deepest first. rmdir refuses
    # non-empty dirs, and (N/) never matches a symlink, so this cannot descend
    # into the repo.
    emptied=( "$claude_dir"/agents/**/*(N/) )
    for f in "${(Oa)emptied[@]}"; do rmdir "$f" 2>/dev/null; done
  fi

  # Hooks: top-level files only. ~/.claude/hooks also holds real, plugin-owned
  # files (caveman-*.js) that settings.json depends on -- never overwrite one.
  if [[ -d "$repo/hooks" ]]; then
    mkdir -p "$claude_dir/hooks"
    for f in "$claude_dir"/hooks/*(N@); do
      _ccm_is_managed "$f" && { rm -f -- "$f"; (( removed++ )) }
    done
    for f in "$repo"/hooks/*(N-.); do
      dest="$claude_dir/hooks/${f:t}"
      if [[ -e "$dest" && ! -L "$dest" ]]; then
        echo "claude_merge_config: skipping hook '${f:t}' -- $dest is a real file (plugin-owned)" >&2
        (( skipped++ )); continue
      fi
      [[ -x "$f" ]] || chmod +x "$f"    # fix the source, and only if wrong
      ln -sfn "$f" "$dest" && (( linked++ ))
    done
  fi

  unset -f _ccm_is_managed

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

  echo "claude_merge_config: $linked linked, $removed stale removed, $skipped skipped"
}
# Not run on shell start -- invoke by hand after editing ~/dotfiles/claude.
