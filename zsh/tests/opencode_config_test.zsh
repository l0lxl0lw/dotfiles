#!/usr/bin/env zsh

setopt nounset pipe_fail
repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/opencode-config-test.XXXXXX") || exit 1
test_tmp=${test_tmp:a}
trap 'command rm -rf -- "$test_tmp"' EXIT
export HOME="$test_tmp/home"
unset XDG_CONFIG_HOME OPENCODE_CONFIG_DIR OPENCODE_WORKFLOW_ROOT OPENCODE_WORKFLOW_REVISION
unset OPENCODE_CONFIG_CONTENT OPENCODE_PRIVATE_SKILL_COMMANDS OPENCODE_SKILL_CATALOG
mkdir -p "$HOME/dotfiles/ai/opencode"
for name in commands agents runtime tui; do
  ln -s "$repo_root/ai/opencode/$name" "$HOME/dotfiles/ai/opencode/$name"
done
mkdir -p "$HOME/dotfiles/ai"
ln -s "$repo_root/ai/shared" "$HOME/dotfiles/ai/shared"
ln -s "$repo_root/ai/opencode/tui.json" "$HOME/dotfiles/ai/opencode/tui.json"
compdef() { :; }
source "$repo_root/zsh/functions.zsh"

fail() { print -u2 -- "FAIL: $1"; exit 1; }
assert_link_to() {
  [[ -L "$1" && "${1:A}" == "${2:A}" ]] || fail "unexpected link: $1 -> $2"
}

opencode_merge_config || fail "absent config sync"
[[ ! -e "$HOME/.config" ]] || fail "created absent global config"
mkdir -p "$HOME/.config/opencode"
opencode_merge_config || fail "default path sync"
assert_link_to "$HOME/.config/opencode/tui.json" "$repo_root/ai/opencode/tui.json"
assert_link_to "$HOME/.config/opencode/tui/skill-commands.js" "$repo_root/ai/opencode/tui/skill-commands.js"
for f in "$repo_root"/ai/opencode/agents/*.md; do
  assert_link_to "$HOME/.config/opencode/agents/${f:t}" "$f"
done
for f in "$repo_root"/ai/opencode/commands/*.md; do
  assert_link_to "$HOME/.config/opencode/commands/${f:t}" "$f"
done
for f in "$repo_root"/ai/shared/skills/git/*/SKILL.md; do
  [[ ! -e "$HOME/.config/opencode/commands/${f:h:t}.md" ]] || fail "redundant Git command link"
done
skills=("$repo_root"/ai/shared/skills/**/SKILL.md(N.))
(( ${#skills} > 0 )) || fail "empty OpenCode catalog"
for f in "${skills[@]}"; do
  assert_link_to "$HOME/.config/opencode/skills/${f:h:t}" "${f:h}"
done
[[ ! -e "$HOME/.config/opencode/skills/_lib" ]] || fail "helper directory became a skill"
assert_link_to "$HOME/.config/opencode/skills/write-better" "$repo_root/ai/shared/skills/write/write-better"
assert_link_to "$HOME/.config/opencode/skills/learn-quiz" "$repo_root/ai/shared/skills/learn/learn-quiz"
[[ -z "$(opencode_merge_config)" ]] || fail "default sync not idempotent"

# Existing installs still point at the former top-level directory. The sync must
# repair dangling managed links after the move, without a compatibility symlink.
for entry in tui.json tui/skill-commands.js agents/codebase-analyzer.md commands/track.md; do
  rm "$HOME/.config/opencode/$entry"
  ln -s "$HOME/dotfiles/opencode/$entry" "$HOME/.config/opencode/$entry"
done
opencode_merge_config || fail "relocated catalog sync"
for entry in tui.json tui/skill-commands.js agents/codebase-analyzer.md commands/track.md; do
  assert_link_to "$HOME/.config/opencode/$entry" "$repo_root/ai/opencode/$entry"
done

# A path containing spaces must be honored without touching the default tree.
export XDG_CONFIG_HOME="$test_tmp/xdg config"
dst="$XDG_CONFIG_HOME/opencode"
mkdir -p "$dst"
print -r -- '{"$schema":"https://opencode.ai/config.json","model":"local/keep"}' > "$dst/opencode.jsonc"
cp "$dst/opencode.jsonc" "$test_tmp/config-before"
opencode_merge_config || fail "XDG sync"
for f in "${skills[@]}"; do
  assert_link_to "$dst/skills/${f:h:t}" "${f:h}"
done
[[ ! -e "$dst/AGENTS.md" && ! -e "$dst/opencode.json" ]] || fail "created unrelated config"

# Prune only managed links, preserving real directories and foreign symlinks.
ln -s "$HOME/dotfiles/missing" "$dst/skills/stale"
mkdir -p "$dst/skills/vendor"
ln -s "$test_tmp/missing-vendor" "$dst/skills/foreign"
rm "$dst/skills/git-commit"
mkdir "$dst/skills/git-commit"
opencode_merge_config || fail "collision sync"
[[ ! -L "$dst/skills/stale" ]] || fail "stale link survived"
[[ -d "$dst/skills/vendor" && -L "$dst/skills/foreign" ]] || fail "vendor entry removed"
[[ -d "$dst/skills/git-commit" && ! -L "$dst/skills/git-commit" ]] || fail "real directory overwritten"
rmdir "$dst/skills/git-commit"
ln -s "$test_tmp/missing-vendor" "$dst/skills/git-commit"
opencode_merge_config || fail "foreign collision sync"
[[ "$(readlink "$dst/skills/git-commit")" == "$test_tmp/missing-vendor" ]] || fail "foreign link overwritten"
rm "$dst/skills/git-commit"
opencode_merge_config || fail "restore sync"
before=$(stat -f %m "$dst/skills/git-commit")
sleep 1
[[ -z "$(opencode_merge_config)" ]] || fail "XDG sync not silent"
[[ "$(stat -f %m "$dst/skills/git-commit")" == "$before" ]] || fail "unchanged link rewritten"
cmp -s "$dst/opencode.jsonc" "$test_tmp/config-before" || fail "JSONC modified"

# Retired links intentionally use the old top-level path to verify cleanup.
# Retired handoff links are removed, while matching real files and foreign links
# remain untouched.
mkdir -p "$dst/commands" "$dst/plugins"
ln -s "$HOME/dotfiles/opencode/handoff" "$dst/dotfiles-handoff"
ln -s "$HOME/dotfiles/opencode/commands/implement-plan.md" "$dst/commands/implement-plan.md"
ln -s "$HOME/dotfiles/opencode/skills/git/retired/SKILL.md" "$dst/commands/git-retired.md"
ln -s "$HOME/dotfiles/opencode/skills/git/git-commit/SKILL.md" "$dst/commands/git-commit.md"
ln -s "$HOME/dotfiles/opencode/commands/quiz-me.md" "$dst/commands/quiz-me.md"
ln -s "$HOME/dotfiles/ai/shared/skills/workflow/workflow-execute" "$dst/skills/workflow-execute"
ln -s "$HOME/dotfiles/opencode/commands/execute.md" "$dst/commands/execute.md"
ln -s "$HOME/dotfiles/opencode/agents/workflow-execute.md" "$dst/agents/workflow-execute.md"
ln -s "$HOME/dotfiles/ai/shared/skills/writing/clear-message" "$dst/skills/clear-message"
ln -s "$HOME/dotfiles/ai/shared/skills/integrations/life-memory" "$dst/skills/life-memory"
ln -s "$test_tmp/vendor-plugin" "$dst/plugins/fresh-session.js"
rm "$dst/tui.json"
print -r -- '{"theme":"my-theme","plugin":["vendor"]}' > "$dst/tui.json"
opencode_merge_config || fail "retired handoff cleanup"
[[ ! -L "$dst/dotfiles-handoff" && ! -L "$dst/commands/implement-plan.md" && ! -L "$dst/commands/git-retired.md" ]] || fail "retired managed links survived"
[[ ! -L "$dst/commands/git-commit.md" && ! -L "$dst/commands/quiz-me.md" ]] || fail "redundant skill command links survived"
[[ ! -L "$dst/skills/workflow-execute" && ! -L "$dst/commands/execute.md" && ! -L "$dst/agents/workflow-execute.md" ]] || fail "retired workflow links survived"
[[ ! -L "$dst/skills/clear-message" && ! -L "$dst/skills/life-memory" ]] || fail "renamed skill links survived"
[[ "$(readlink "$dst/plugins/fresh-session.js")" == "$test_tmp/vendor-plugin" ]] || fail "foreign plugin removed"
[[ -f "$dst/tui.json" && ! -L "$dst/tui.json" ]] || fail "machine-local TUI config removed"

# The wrapper syncs before launch, forwards arguments and returns binary status.
mkdir -p "$test_tmp/bin"
cp "$repo_root/zsh/tests/fixtures/fake-opencode" "$test_tmp/bin/opencode"
chmod +x "$test_tmp/bin/opencode"
export PATH="$test_tmp/bin:$PATH"
rehash
rm "$dst/skills/git-commit"
opencode 'argument with spaces'
result=$?
[[ $result == 23 ]] || fail "wrapper status/arguments/pre-launch sync: $result"
opencode_workflow -- 'argument with spaces'
[[ $? == 23 ]] || fail "explicit launcher argument forwarding"
print -- "PASS: ${#skills} OpenCode skills, XDG/default paths, external-skill isolation, safe pruning, config preservation, idempotence and wrapper"
