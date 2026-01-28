# Auto-ls on directory change
chpwd() {
  ls
}

# Claude agent selector
ca() {
  local agents_dir="$HOME/workspace/claude-config/agents"
  local agent="$1"
  shift 2>/dev/null

  if [[ -z "$agent" ]]; then
    echo "Usage: ca <agent> [claude args...]"
    echo "Available agents:"
    for f in "$agents_dir"/*.md; do
      [[ -f "$f" ]] && echo "  ${${f:t}%.md}"
    done
    return 1
  fi

  if [[ ! -f "$agents_dir/$agent.md" ]]; then
    echo "Agent not found: $agent"
    return 1
  fi

  local prompt=$(cat "$agents_dir/$agent.md" | jq -Rs .)
  local agents_json="{\"$agent\":{\"description\":\"$agent agent\",\"prompt\":$prompt}}"

  claude --agents "$agents_json" --agent "$agent" "$@"
}

_ca() {
  local agents_dir="$HOME/workspace/claude-config/agents"
  local agents=()
  for f in "$agents_dir"/*.md; do
    [[ -f "$f" ]] && agents+=("${${f:t}%.md}")
  done
  _describe 'agent' agents
}
compdef _ca ca

# Merge Claude skills/agents from public + private repos
claude_merge_config() {
  local claude_dir="$HOME/.claude"
  local public_repo="$HOME/workspace/claude-config"
  local private_repo="$HOME/workspace/private"

  # Merge skills (directories)
  rm -rf "$claude_dir/skills" && mkdir -p "$claude_dir/skills"
  for repo in "$public_repo" "$private_repo"; do
    [[ -d "$repo/skills" ]] && \
      find "$repo/skills" -mindepth 1 -maxdepth 1 -type d -exec ln -sf {} "$claude_dir/skills/" \;
  done

  # Merge agents (.md files)
  rm -rf "$claude_dir/agents" && mkdir -p "$claude_dir/agents"
  for repo in "$public_repo" "$private_repo"; do
    [[ -d "$repo/agents" ]] && \
      find "$repo/agents" -maxdepth 1 -name "*.md" -exec ln -sf {} "$claude_dir/agents/" \;
  done
}
claude_merge_config
