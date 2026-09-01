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

(( $+functions[_codex_stage_repo_claude_skills] )) || \
  fail "_codex_stage_repo_claude_skills is missing"
(( $+functions[_codex_cleanup_repo_claude_skills] )) || \
  fail "_codex_cleanup_repo_claude_skills is missing"

# Staging from a nested working directory must expose the whole Claude skill
# tree outside the repository and leave the repository itself untouched.
local import_repo="$test_tmp/import"
local codex_home="$test_tmp/codex-home"
mkdir -p "$import_repo/.claude/skills/alpha" \
  "$import_repo/.claude/skills/group/beta" \
  "$import_repo/service/nested" \
  "$codex_home/skills"
touch "$import_repo/.claude/skills/alpha/SKILL.md" \
  "$import_repo/.claude/skills/group/beta/SKILL.md"
command git -C "$import_repo" init -q

local stage
stage=$(
  cd "$import_repo/service/nested"
  CODEX_HOME="$codex_home" _codex_stage_repo_claude_skills
)
[[ "$stage" == "$codex_home/skills/repo-session."* ]] || \
  fail "stage was created at unexpected path: $stage"
assert_link_to "$stage/project" "$import_repo/.claude/skills"
[[ ! -e "$import_repo/.agents" ]] || fail "repository gained .agents"

CODEX_HOME="$codex_home" _codex_cleanup_repo_claude_skills "$stage"
[[ ! -e "$stage" ]] || fail "staged skills survived explicit cleanup"

# The wrapper must keep skills staged while Codex runs, remove them afterward,
# and preserve a failing Codex process's exit status.
local fake_bin="$test_tmp/bin"
local report="$test_tmp/fake-codex-report"
mkdir -p "$fake_bin"
cp "$repo_root/zsh/tests/fixtures/fake-codex" "$fake_bin/codex"
chmod +x "$fake_bin/codex"

codex_merge_config() { :; }
PATH="$fake_bin:$PATH"
rehash

if (
  cd "$import_repo/service/nested"
  CODEX_HOME="$codex_home" \
    FAKE_CODEX_REPORT="$report" \
    FAKE_CODEX_STATUS=23 \
    codex probe-argument
); then
  local wrapper_status=0
else
  local wrapper_status=$?
fi

[[ $wrapper_status -eq 23 ]] || \
  fail "wrapper returned $wrapper_status instead of Codex status 23"
[[ "$(<"$report")" == *$'argument=probe-argument\n'* ]] || \
  fail "wrapper did not pass arguments to Codex"
[[ "$(<"$report")" == *'project-skills=present' ]] || \
  fail "project skills were not staged while Codex ran"
[[ -z "$(find "$codex_home/skills" -mindepth 1 -maxdepth 1 -print -quit)" ]] || \
  fail "session staging survived after Codex exited"
[[ ! -e "$import_repo/.agents" ]] || fail "wrapper created .agents"

# Repositories without Claude skills should launch without creating staging.
local empty_repo="$test_tmp/empty"
local empty_report="$test_tmp/empty-report"
mkdir -p "$empty_repo"
command git -C "$empty_repo" init -q
(
  cd "$empty_repo"
  CODEX_HOME="$codex_home" \
    FAKE_CODEX_REPORT="$empty_report" \
    FAKE_CODEX_STATUS=0 \
    codex
)
[[ "$(<"$empty_report")" == *'project-skills=absent' ]] || \
  fail "empty repository unexpectedly staged project skills"

print -- "PASS: repository Claude skills are scoped to the Codex process"
