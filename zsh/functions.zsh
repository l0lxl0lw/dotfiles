# Auto-ls on directory change
chpwd() {
  ls
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
cca() { claude --agent "${@##*/}"; }
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
compdef _claude_agents cca ccta

# Merge Claude skills/agents/mcp from public + private repos
claude_merge_config() {
  local claude_dir="$HOME/.claude"
  local public_repo="$HOME/workspace/claude-config"

  # Merge skills (directories)
  rm -rf "$claude_dir/skills" && mkdir -p "$claude_dir/skills"
  for repo in "$public_repo"; do
    [[ -d "$repo/skills" ]] && \
      find "$repo/skills" -mindepth 1 -maxdepth 1 -type d -exec ln -sfn {} "$claude_dir/skills/" \;
  done

  # Merge agents (.md files and agent directories)
  rm -rf "$claude_dir/agents" && mkdir -p "$claude_dir/agents"
  for repo in "$public_repo"; do
    [[ -d "$repo/agents" ]] && \
      find "$repo/agents" -maxdepth 1 -name "*.md" -exec ln -sfn {} "$claude_dir/agents/" \;
    [[ -d "$repo/agents" ]] && \
      find "$repo/agents" -mindepth 1 -maxdepth 1 -type d -exec ln -sfn {} "$claude_dir/agents/" \;
  done

  # Render mcp.json from templates + .env secrets
  for repo in "$public_repo"; do
    [[ -f "$repo/.env" ]] && set -a && source "$repo/.env" && set +a
  done

  local merged="{}"
  for repo in "$public_repo"; do
    if [[ -f "$repo/mcp.json.tpl" ]]; then
      local rendered
      rendered=$(envsubst < "$repo/mcp.json.tpl")
      merged=$(echo "$merged" "$rendered" | jq -s '.[0] * .[1]')
    fi
  done

  if [[ "$merged" != "{}" ]]; then
    echo "$merged" | jq . > "$claude_dir/mcp.json"
  fi

  # Merge hooks (symlink executable scripts)
  mkdir -p "$claude_dir/hooks"
  for repo in "$public_repo"; do
    [[ -d "$repo/hooks" ]] && \
      find "$repo/hooks" -maxdepth 1 -type f -exec ln -sfn {} "$claude_dir/hooks/" \;
  done

  # Patch statusLine into settings.json if hook exists
  if [[ -f "$claude_dir/hooks/statusline.sh" ]]; then
    chmod +x "$claude_dir/hooks/statusline.sh"
    if [[ -f "$claude_dir/settings.json" ]]; then
      local updated
      updated=$(jq '.statusLine = {"type": "command", "command": "sh ~/.claude/hooks/statusline.sh"}' "$claude_dir/settings.json")
      echo "$updated" > "$claude_dir/settings.json"
    fi
  fi
}
claude_merge_config
