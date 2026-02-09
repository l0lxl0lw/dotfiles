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

# Merge Claude skills/agents/mcp from public + private repos
claude_merge_config() {
  local claude_dir="$HOME/.claude"
  local public_repo="$HOME/workspace/claude-config"
  local private_repo="$HOME/workspace/private/claude"
  local youtube_repo="$HOME/workspace/youtube-agents"

  # Merge skills (directories)
  rm -rf "$claude_dir/skills" && mkdir -p "$claude_dir/skills"
  for repo in "$public_repo" "$private_repo" "$youtube_repo"; do
    [[ -d "$repo/skills" ]] && \
      find "$repo/skills" -mindepth 1 -maxdepth 1 -type d -exec ln -sfn {} "$claude_dir/skills/" \;
  done

  # Merge agents (.md files and agent directories)
  rm -rf "$claude_dir/agents" && mkdir -p "$claude_dir/agents"
  for repo in "$public_repo" "$private_repo" "$youtube_repo"; do
    [[ -d "$repo/agents" ]] && \
      find "$repo/agents" -maxdepth 1 -name "*.md" -exec ln -sfn {} "$claude_dir/agents/" \;
    [[ -d "$repo/agents" ]] && \
      find "$repo/agents" -mindepth 1 -maxdepth 1 -type d -exec ln -sfn {} "$claude_dir/agents/" \;
  done

  # Render mcp.json from templates + .env secrets
  for repo in "$public_repo" "$private_repo" "$youtube_repo"; do
    [[ -f "$repo/.env" ]] && set -a && source "$repo/.env" && set +a
  done

  local merged="{}"
  for repo in "$public_repo" "$private_repo" "$youtube_repo"; do
    if [[ -f "$repo/mcp.json.tpl" ]]; then
      local rendered
      rendered=$(envsubst < "$repo/mcp.json.tpl")
      merged=$(echo "$merged" "$rendered" | jq -s '.[0] * .[1]')
    fi
  done

  if [[ "$merged" != "{}" ]]; then
    echo "$merged" | jq . > "$claude_dir/mcp.json"
  fi
}
claude_merge_config
