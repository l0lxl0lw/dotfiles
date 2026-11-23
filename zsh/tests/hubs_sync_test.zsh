#!/usr/bin/env zsh
# hubs_sync links every active hub's skills, agents and personas into each
# tool, later hub wins, and never touches what it does not own.

setopt err_return nounset pipe_fail

repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/hubs-sync-test.XXXXXX"); test_tmp=${test_tmp:a}
trap 'command rm -rf -- "$test_tmp"' EXIT

export HOME="$test_tmp/home" XDG_CONFIG_HOME="$test_tmp/config" XDG_STATE_HOME="$test_tmp/state"
unset CODEX_HOME
mkdir -p "$HOME" "$XDG_CONFIG_HOME/dotfiles"
ln -s "$repo_root" "$HOME/dotfiles"
hubs_file="$XDG_CONFIG_HOME/dotfiles/hubs"

compdef() { :; }
source "$repo_root/zsh/functions.zsh"
source "$repo_root/zsh/hubs.zsh"

fail() { print -u2 -- "FAIL: $1"; return 1 }
assert_link_to() {
  [[ -L "$1" ]] || fail "$1 is not a symlink"
  [[ "${1:A}" == "${2:A}" ]] || fail "$1 resolves to ${1:A}, expected ${2:A}"
}

# make_hub <path> <skill>...  creates .agents/skills/<skill>/SKILL.md for each
make_hub() {
  local hub="$1" s; shift
  for s in "$@"; do
    mkdir -p "$hub/.agents/skills/$s"
    print -- "---\nname: $s\ndescription: $s from ${hub:t}\n---" > "$hub/.agents/skills/$s/SKILL.md"
  done
}
fresh() { local d="$test_tmp/$1"; rm -rf "$d"; mkdir -p "$d"; print -r -- "$d" }

test_links_each_hub_skill_once() {
  local zubot="$HOME/h1/zubot" azubot="$HOME/h1/azubot" dest
  make_hub "$zubot" honest-check; make_hub "$azubot" ds-develop
  dest=$(fresh dest1)
  hubs_sync_skills "$dest" "$zubot" "$azubot" >/dev/null
  assert_link_to "$dest/honest-check" "$zubot/.agents/skills/honest-check"
  assert_link_to "$dest/ds-develop" "$azubot/.agents/skills/ds-develop"
  (( $(ls "$dest" | wc -l) == 2 )) || fail "expected exactly two links in $dest"
}

test_later_hub_wins_and_prints_override() {
  local zubot="$HOME/h2/zubot" azubot="$HOME/h2/azubot" dest out
  make_hub "$zubot" parallel-explore; make_hub "$azubot" parallel-explore
  dest=$(fresh dest2)
  out=$(hubs_sync_skills "$dest" "$zubot" "$azubot" 2>/dev/null)
  assert_link_to "$dest/parallel-explore" "$azubot/.agents/skills/parallel-explore"
  [[ "$out" == *"override skill 'parallel-explore': $azubot/.agents/skills/parallel-explore over $zubot/.agents/skills/parallel-explore"* ]] \
    || fail "override line missing, got: $out"
}

test_claude_skills_symlink_not_scanned() {
  local hub="$HOME/h3/azubot" dest
  make_hub "$hub" ds-develop
  mkdir -p "$hub/.claude"; ln -s ../.agents/skills "$hub/.claude/skills"
  dest=$(fresh dest3)
  hubs_sync_skills "$dest" "$hub" >/dev/null
  (( $(ls "$dest" | wc -l) == 1 )) || fail "expected one link, got: $(ls "$dest")"
}

test_empty_hub_list_removes_only_managed_links() {
  local dest stale="$HOME/workspace/azubot/.agents/skills/old"
  dest=$(fresh dest4)
  mkdir -p "$dest/aws-cdk" "$dest/.system"
  ln -s /opt/x/foreign "$dest/foreign"
  ln -s "$stale" "$dest/old"
  hubs_sync_skills "$dest" >/dev/null
  [[ -d "$dest/aws-cdk" && -d "$dest/.system" ]] || fail "real directories were removed"
  [[ -L "$dest/foreign" ]] || fail "foreign symlink was removed"
  [[ ! -e "$dest/old" && ! -L "$dest/old" ]] || fail "stale legacy link was not removed"
}

test_missing_hub_keeps_its_links() {
  local zubot="$HOME/h5/zubot" gone="$HOME/h5/gone" dest
  make_hub "$zubot" honest-check
  dest=$(fresh dest5)
  ln -s "$gone/.agents/skills/vanished" "$dest/vanished"
  print -rl -- "$zubot" "$gone" > "$hubs_file"
  hubs_sync_skills "$dest" ${(f)"$(hubs_list 2>/dev/null)"} >/dev/null
  [[ -L "$dest/vanished" ]] || fail "link into a missing hub was removed"
  assert_link_to "$dest/honest-check" "$zubot/.agents/skills/honest-check"
}


# make_hub_agents <hub> <name>...  one agents/src entry per name (fast/research),
# a tiers.json, and the committed three-way render.
make_hub_agents() {
  local hub="$1" n; shift
  mkdir -p "$hub/agents/src"
  for n in "$@"; do
    print -- "---\nname: $n\ndescription: $n from ${hub:t}\ntier: fast\naccess: research\n---\n\nBody of $n.\n" \
      > "$hub/agents/src/$n.md"
  done
  print -r -- '{"claude":{"fast":{"model":"haiku"}},"codex":{"fast":{"model":"gpt-6-luna"}},"opencode":{"fast":{"model":"openai/gpt-6-luna"}}}' \
    > "$hub/tiers.json"
  python3 -B "$repo_root/agents/render.py" --hub "$hub" >/dev/null
}
first_line() { head -n 2 -- "$1" }   # notice is line 1 (TOML) or line 2 after the fence (Markdown)

test_agents_claude_linked_with_subfolders() {
  local hub="$HOME/a1/azubot"
  make_hub_agents "$hub" ds-locator
  mkdir -p "$hub/.claude/agents/persona"
  print -- "---\nname: azubot\ndescription: persona\n---\nhand" > "$hub/.claude/agents/persona/azubot.md"
  rm -rf "$HOME/.claude"; mkdir -p "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  hubs_sync_agents "$hub" >/dev/null
  assert_link_to "$HOME/.claude/agents/ds-locator.md" "$hub/.claude/agents/ds-locator.md"
  assert_link_to "$HOME/.claude/agents/persona/azubot.md" "$hub/.claude/agents/persona/azubot.md"
}

test_agents_codex_and_opencode_are_generated_copies() {
  local hub="$HOME/a2/azubot" f
  make_hub_agents "$hub" ds-locator
  rm -rf "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  mkdir -p "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  hubs_sync_agents "$hub" >/dev/null
  for f in "$HOME/.codex/agents/ds-locator.toml" "$XDG_CONFIG_HOME/opencode/agents/ds-locator.md"; do
    [[ -f "$f" && ! -L "$f" ]] || fail "$f is not a regular file"
    [[ "$(first_line "$f")" == *"Generated by render.py"* ]] || fail "$f lacks the render notice"
  done
  grep -q 'model = "gpt-6-luna"' "$HOME/.codex/agents/ds-locator.toml" || fail "codex model missing"
}

test_agents_machine_tiers_change_opencode_model() {
  local hub="$HOME/a3/azubot"
  make_hub_agents "$hub" ds-locator
  rm -rf "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  mkdir -p "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  print -r -- '{"opencode":{"fast":{"model":"openrouter/zed"}}}' > "$XDG_CONFIG_HOME/dotfiles/tiers.json"
  hubs_sync_agents "$hub" >/dev/null
  grep -q 'model: openrouter/zed' "$XDG_CONFIG_HOME/opencode/agents/ds-locator.md" || fail "machine tier not applied"
  grep -q 'model: openai/gpt-6-luna' "$hub/.opencode/agents/ds-locator.md" || fail "committed render was changed"
  rm -f "$XDG_CONFIG_HOME/dotfiles/tiers.json"
}

test_agents_foreign_files_survive() {
  local hub="$HOME/a4/azubot"
  make_hub_agents "$hub" ds-locator
  rm -rf "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  mkdir -p "$HOME/.claude/agents/vendor" "$HOME/.codex/agents" "$XDG_CONFIG_HOME/opencode/agents"
  print -r -- 'vendor' > "$HOME/.claude/agents/vendor/x.md"
  print -r -- 'name = "vendor"' > "$HOME/.codex/agents/vendor.toml"
  print -r -- 'name = "foreign"' > "$HOME/.codex/agents/ds-locator.toml"
  print -- '---\nmine\n---' > "$XDG_CONFIG_HOME/opencode/agents/mine.md"
  hubs_sync_agents "$hub" 2>/dev/null >/dev/null
  [[ "$(<"$HOME/.claude/agents/vendor/x.md")" == vendor ]] || fail "foreign claude agent removed"
  [[ "$(<"$HOME/.codex/agents/vendor.toml")" == 'name = "vendor"' ]] || fail "foreign codex role removed"
  [[ "$(<"$HOME/.codex/agents/ds-locator.toml")" == 'name = "foreign"' ]] || fail "foreign same-name role replaced"
  [[ -f "$XDG_CONFIG_HOME/opencode/agents/mine.md" ]] || fail "foreign opencode agent removed"
}

test_agents_later_hub_wins_name() {
  local zubot="$HOME/a5/zubot" azubot="$HOME/a5/azubot" out
  make_hub_agents "$zubot" locator; make_hub_agents "$azubot" locator
  rm -rf "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  mkdir -p "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  out=$(hubs_sync_agents "$zubot" "$azubot" 2>/dev/null)
  assert_link_to "$HOME/.claude/agents/locator.md" "$azubot/.claude/agents/locator.md"
  grep -q 'locator from azubot' "$HOME/.codex/agents/locator.toml" || fail "codex copy is not azubot's"
  grep -q 'locator from azubot' "$XDG_CONFIG_HOME/opencode/agents/locator.md" || fail "opencode copy is not azubot's"
  [[ "$out" == *"override agent 'locator.md'"* ]] || fail "override line missing: $out"
}

test_agents_unknown_codex_tier_model_warns() {
  local hub="$HOME/a6/azubot" err
  make_hub_agents "$hub" ds-locator
  rm -rf "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  mkdir -p "$HOME/.claude" "$HOME/.codex" "$XDG_CONFIG_HOME/opencode"
  print -r -- '{"models": [{"slug": "gpt-6-astra"}]}' > "$HOME/.codex/models_cache.json"
  err=$(hubs_sync_agents "$hub" 2>&1 >/dev/null)
  [[ "$err" == *"gpt-6-luna"* ]] || fail "expected a warning naming gpt-6-luna, got: $err"
  rm -f "$HOME/.codex/models_cache.json"
}

for t in ${(ok)functions[(I)test_*]}; do
  $t || exit 1
done
print "hubs_sync_test: ok"
