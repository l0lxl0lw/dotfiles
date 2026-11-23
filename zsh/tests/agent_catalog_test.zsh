#!/usr/bin/env zsh
# The tool wrappers sync the active hubs before launching the real binary.

setopt err_return nounset pipe_fail

repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/agent-catalog-test.XXXXXX"); test_tmp=${test_tmp:a}
trap 'command rm -rf -- "$test_tmp"' EXIT

export HOME="$test_tmp/home" XDG_STATE_HOME="$test_tmp/state" XDG_CONFIG_HOME="$test_tmp/config"
unset CODEX_HOME
mkdir -p "$HOME/.codex" "$HOME/.claude" "$XDG_CONFIG_HOME/dotfiles"
ln -s "$repo_root" "$HOME/dotfiles"

compdef() { :; }
source "$repo_root/zsh/functions.zsh"
source "$repo_root/zsh/hubs.zsh"

fail() { print -u2 -- "FAIL: $1"; return 1 }
assert_link_to() {
  [[ -L "$1" ]] || fail "$1 is not a symlink"
  [[ "${1:A}" == "${2:A}" ]] || fail "$1 resolves to ${1:A}, expected ${2:A}"
}

# One hub with a skill and a rendered worker, listed as the only active hub.
local hub="$HOME/zubot"
mkdir -p "$hub/.agents/skills/develop-deliver" "$hub/agents/src"
print -- "---\nname: develop-deliver\ndescription: deliver\n---" > "$hub/.agents/skills/develop-deliver/SKILL.md"
print -- "---\nname: develop-plan\ndescription: plan\ntier: fast\naccess: research\n---\n\nPlan.\n" > "$hub/agents/src/develop-plan.md"
print -r -- '{"codex":{"fast":{"model":"gpt-6-luna"}}}' > "$hub/tiers.json"
python3 -B "$repo_root/agents/render.py" --hub "$hub" >/dev/null
print -r -- "$hub" > "$XDG_CONFIG_HOME/dotfiles/hubs"

# Codex: every role is a current copy; foreign roles stay; a tier model missing
# from Codex's catalog is reported without failing.
local agents="$HOME/.codex/agents"
mkdir -p "$agents"
print -r -- 'name = "vendor"' > "$agents/vendor.toml"
print -r -- '{"models": [{"slug": "gpt-6-astra"}]}' > "$HOME/.codex/models_cache.json"
local warnings
warnings=$(codex_merge_config 2>&1 >/dev/null)
[[ -f "$agents/develop-plan.toml" && ! -L "$agents/develop-plan.toml" ]] || fail "develop-plan.toml is not a real file"
grep -q 'model = "gpt-6-luna"' "$agents/develop-plan.toml" || fail "rendered role lacks its model"
[[ "$(<"$agents/vendor.toml")" == 'name = "vendor"' ]] || fail "foreign Codex role was not preserved"
[[ "$warnings" == *"tier 'fast'"*"tiers.json"* ]] || fail "missing unknown-model warning: $warnings"
local before=$(stat -f %i "$agents/develop-plan.toml")
codex_merge_config >/dev/null 2>&1
[[ "$(stat -f %i "$agents/develop-plan.toml")" == "$before" ]] || fail "unchanged role was rewritten"

# Claude: the wrapper syncs, forwards arguments and keeps the exit status.
local fake_bin="$test_tmp/bin" report="$test_tmp/claude-args"
mkdir -p "$fake_bin"
print -r -- "#!/bin/sh
printf '%s\n' \"\$@\" > '$report'
exit 7" > "$fake_bin/claude"
chmod +x "$fake_bin/claude"
path=("$fake_bin" $path)

local exit_code=0
claude --agent "two words" >/dev/null 2>&1 || exit_code=$?
(( exit_code == 7 )) || fail "claude wrapper returned $exit_code, expected 7"
[[ "$(<"$report")" == $'--agent\ntwo words' ]] || fail "claude wrapper changed arguments"
assert_link_to "$HOME/.claude/agents/develop-plan.md" "$hub/.claude/agents/develop-plan.md"
assert_link_to "$HOME/.claude/skills/develop-deliver" "$hub/.agents/skills/develop-deliver"

# A declined Claude component still launches but performs no sync.
command rm -rf -- "$HOME/.claude" "$report"
mkdir -p "$XDG_STATE_HOME/dotfiles/disabled-sync"
touch "$XDG_STATE_HOME/dotfiles/disabled-sync/claude"
exit_code=0
claude >/dev/null 2>&1 || exit_code=$?
(( exit_code == 7 )) || fail "disabled claude wrapper returned $exit_code"
[[ ! -e "$HOME/.claude" ]] || fail "disabled claude wrapper synced the catalog"

print -- "agent catalog tests passed"
