#!/usr/bin/env zsh

setopt nounset pipe_fail
repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/opencode-config-test.XXXXXX") || exit 1
test_tmp=${test_tmp:a}
trap 'command rm -rf -- "$test_tmp"' EXIT
export HOME="$test_tmp/home"
unset XDG_CONFIG_HOME
mkdir -p "$HOME/dotfiles/ai/opencode/skills" "$HOME/dotfiles/ai/shared"
ln -s "$repo_root/ai/shared/skills" "$HOME/dotfiles/ai/shared/skills"
for name in handoff plugins commands tui.json; do
  ln -s "$repo_root/ai/opencode/$name" "$HOME/dotfiles/ai/opencode/$name"
done
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
assert_link_to "$HOME/.config/opencode/dotfiles-handoff" "$repo_root/ai/opencode/handoff"
for disabled in \
  "$HOME/.config/opencode/tui.json" \
  "$HOME/.config/opencode/plugins/fresh-session.js" \
  "$HOME/.config/opencode/commands/implement-plan.md" \
  "$HOME/.config/opencode/skills/brainstorm-then-plan" \
  "$HOME/.config/opencode/skills/implement-plan"; do
  [[ ! -e "$disabled" && ! -L "$disabled" ]] || fail "disabled workflow installed: $disabled"
done
skills=("$repo_root"/ai/shared/skills/**/SKILL.md(N.))
(( ${#skills} > 0 )) || fail "empty shared catalog"
for f in "${skills[@]}"; do
  assert_link_to "$HOME/.config/opencode/skills/${f:h:t}" "${f:h}"
done
[[ ! -e "$HOME/.config/opencode/skills/_lib" ]] || fail "helper directory became a skill"
[[ -z "$(opencode_merge_config)" ]] || fail "default sync not idempotent"

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

# Local overrides win; removing them restores the shared target.
override="$HOME/dotfiles/ai/opencode/skills/readme"
mkdir -p "$override"
touch "$override/SKILL.md"
opencode_merge_config || fail "override sync"
assert_link_to "$dst/skills/readme" "$override"
rm "$override/SKILL.md"
rmdir "$override"
opencode_merge_config || fail "override removal sync"
assert_link_to "$dst/skills/readme" "$repo_root/ai/shared/skills/utilities/readme"

# Prune only managed links, preserving real directories and foreign symlinks.
ln -s "$HOME/dotfiles/missing" "$dst/skills/stale"
mkdir -p "$dst/skills/vendor"
ln -s "$test_tmp/missing-vendor" "$dst/skills/foreign"
rm "$dst/skills/readme"
mkdir "$dst/skills/readme"
opencode_merge_config || fail "collision sync"
[[ ! -L "$dst/skills/stale" ]] || fail "stale link survived"
[[ -d "$dst/skills/vendor" && -L "$dst/skills/foreign" ]] || fail "vendor entry removed"
[[ -d "$dst/skills/readme" && ! -L "$dst/skills/readme" ]] || fail "real directory overwritten"
rmdir "$dst/skills/readme"
ln -s "$test_tmp/missing-vendor" "$dst/skills/readme"
opencode_merge_config || fail "foreign collision sync"
[[ "$(readlink "$dst/skills/readme")" == "$test_tmp/missing-vendor" ]] || fail "foreign link overwritten"
rm "$dst/skills/readme"
opencode_merge_config || fail "restore sync"
before=$(stat -f %m "$dst/skills/readme")
sleep 1
[[ -z "$(opencode_merge_config)" ]] || fail "XDG sync not silent"
[[ "$(stat -f %m "$dst/skills/readme")" == "$before" ]] || fail "unchanged link rewritten"
cmp -s "$dst/opencode.jsonc" "$test_tmp/config-before" || fail "JSONC modified"

# Never replace a machine-local TUI config or another installer's command/plugin.
print -r -- '{"theme":"my-theme","plugin":["vendor"]}' > "$dst/tui.jsonc"
cp "$dst/tui.jsonc" "$test_tmp/tui-before"
opencode_merge_config || fail "existing tui.jsonc sync"
cmp -s "$dst/tui.jsonc" "$test_tmp/tui-before" || fail "TUI JSONC modified"
[[ ! -e "$dst/tui.json" ]] || fail "created competing TUI JSON"
mv "$dst/tui.jsonc" "$dst/tui.json"
mkdir -p "$dst/commands" "$dst/plugins"
print -r -- 'keep command' > "$dst/commands/implement-plan.md"
ln -s "$test_tmp/vendor-plugin" "$dst/plugins/fresh-session.js"
opencode_merge_config || fail "foreign handoff files sync"
cmp -s "$dst/tui.json" "$test_tmp/tui-before" || fail "TUI JSON modified"
[[ "$(<"$dst/commands/implement-plan.md")" == 'keep command' ]] || fail "command overwritten"
[[ "$(readlink "$dst/plugins/fresh-session.js")" == "$test_tmp/vendor-plugin" ]] || fail "plugin overwritten"
rm "$dst/tui.json" "$dst/commands/implement-plan.md" "$dst/plugins/fresh-session.js"
opencode_merge_config || fail "disabled handoff sync"
for disabled in "$dst/tui.json" "$dst/commands/implement-plan.md" "$dst/plugins/fresh-session.js"; do
  [[ ! -e "$disabled" && ! -L "$disabled" ]] || fail "disabled handoff entry restored: $disabled"
done

# The wrapper syncs before launch, forwards arguments and returns binary status.
mkdir -p "$test_tmp/bin"
cp "$repo_root/zsh/tests/fixtures/fake-opencode" "$test_tmp/bin/opencode"
chmod +x "$test_tmp/bin/opencode"
export PATH="$test_tmp/bin:$PATH"
rehash
rm "$dst/skills/readme"
opencode 'argument with spaces'
result=$?
[[ $result == 23 ]] || fail "wrapper status/arguments/pre-launch sync: $result"
print -- "PASS: ${#skills} shared skills, XDG/default paths, overrides, safe pruning, config preservation, idempotence and wrapper"
