#!/usr/bin/env zsh

setopt err_return nounset pipe_fail

repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/codex-repo-skills-test.XXXXXX")
trap 'command rm -rf -- "$test_tmp"' EXIT

# functions.zsh registers completions when sourced interactively.
compdef() { :; }
source "$repo_root/zsh/functions.zsh"

fail() {
  print -u2 -- "FAIL: $1"
  return 1
}

assert_link_to() {
  local link=$1 expected=$2
  [[ -L "$link" ]] || fail "$link is not a symlink"
  [[ "${link:A}" == "${expected:A}" ]] || \
    fail "$link resolves to ${link:A}, expected ${expected:A}"
}

(( $+functions[_codex_sync_repo_claude_skills] )) || \
  fail "_codex_sync_repo_claude_skills is missing"

# A repository without Claude skills must remain untouched.
local empty_repo="$test_tmp/empty"
mkdir -p "$empty_repo"
_codex_sync_repo_claude_skills "$empty_repo"
[[ ! -e "$empty_repo/.agents" ]] || fail "empty repository gained .agents"

# Top-level and nested Claude skills are flattened into Codex's repo catalog.
local import_repo="$test_tmp/import"
mkdir -p "$import_repo/.claude/skills/alpha" \
  "$import_repo/.claude/skills/group/beta"
touch "$import_repo/.claude/skills/alpha/SKILL.md" \
  "$import_repo/.claude/skills/group/beta/SKILL.md"
_codex_sync_repo_claude_skills "$import_repo"
assert_link_to "$import_repo/.agents/skills/alpha" \
  "$import_repo/.claude/skills/alpha"
assert_link_to "$import_repo/.agents/skills/beta" \
  "$import_repo/.claude/skills/group/beta"

# A native Codex skill wins a same-name collision and is never overwritten.
mkdir -p "$import_repo/.agents/skills/native" \
  "$import_repo/.claude/skills/native"
touch "$import_repo/.agents/skills/native/SKILL.md" \
  "$import_repo/.claude/skills/native/SKILL.md"
_codex_sync_repo_claude_skills "$import_repo" >/dev/null 2>&1
[[ -d "$import_repo/.agents/skills/native" && \
   ! -L "$import_repo/.agents/skills/native" ]] || \
  fail "native Codex skill was overwritten"

# A removed Claude skill prunes only the symlink previously imported for it.
mv "$import_repo/.claude/skills/alpha" "$test_tmp/removed-alpha"
_codex_sync_repo_claude_skills "$import_repo" >/dev/null 2>&1
[[ ! -e "$import_repo/.agents/skills/alpha" && \
   ! -L "$import_repo/.agents/skills/alpha" ]] || \
  fail "stale imported skill was not removed"
[[ -d "$import_repo/.agents/skills/native" ]] || \
  fail "stale-link cleanup removed a native Codex skill"

# Removing the entire Claude skill tree also removes generated links, while
# leaving a native .agents/skills directory untouched.
mv "$import_repo/.claude/skills" "$test_tmp/removed-skill-tree"
_codex_sync_repo_claude_skills "$import_repo" >/dev/null 2>&1
[[ ! -e "$import_repo/.agents/skills/beta" && \
   ! -L "$import_repo/.agents/skills/beta" ]] || \
  fail "generated link survived removal of .claude/skills"
[[ -d "$import_repo/.agents/skills/native" ]] || \
  fail "missing Claude skill tree removed a native Codex skill"

# With no explicit path, launch-time sync finds the repository from a nested CWD.
local cwd_repo="$test_tmp/from-cwd"
mkdir -p "$cwd_repo/.claude/skills/gamma" "$cwd_repo/service/nested"
touch "$cwd_repo/.claude/skills/gamma/SKILL.md"
command git -C "$cwd_repo" init -q
(
  cd "$cwd_repo/service/nested"
  _codex_sync_repo_claude_skills
)
assert_link_to "$cwd_repo/.agents/skills/gamma" \
  "$cwd_repo/.claude/skills/gamma"

print -- "PASS: repository Claude skills sync safely into Codex"
