#!/usr/bin/env zsh
# hubs_list reads the machine-local hub list: tilde expansion, comments,
# missing paths skipped with a warning, duplicates collapsed.

setopt err_return nounset pipe_fail

repo_root=${0:A:h:h:h}
test_tmp=$(mktemp -d "${TMPDIR:-/tmp}/hubs-list-test.XXXXXX"); test_tmp=${test_tmp:a}
trap 'command rm -rf -- "$test_tmp"' EXIT

export HOME="$test_tmp/home" XDG_CONFIG_HOME="$test_tmp/config"
mkdir -p "$HOME/zubot" "$HOME/azubot" "$XDG_CONFIG_HOME/dotfiles"
hubs_file="$XDG_CONFIG_HOME/dotfiles/hubs"

source "$repo_root/zsh/hubs.zsh"

fail() { print -u2 -- "FAIL: $1"; return 1 }

test_expands_tilde_and_skips_comments() {
  print -rl -- '# comment' '' '~/zubot' "$HOME/azubot" > "$hubs_file"
  local out; out=$(hubs_list 2>/dev/null)
  [[ "$out" == "$HOME/zubot"$'\n'"$HOME/azubot" ]] || fail "expected two absolute paths, got: $out"
}

test_missing_hub_warns_and_is_skipped() {
  print -rl -- '~/zubot' '~/absent' > "$hubs_file"
  local out err
  out=$(hubs_list 2>"$test_tmp/err"); err=$(<"$test_tmp/err")
  [[ "$out" == "$HOME/zubot" ]] || fail "expected only zubot, got: $out"
  [[ "$err" == *absent* ]] || fail "expected a warning naming the absent hub, got: $err"
}

test_duplicate_hub_lines_collapse() {
  print -rl -- '~/zubot' '~/zubot/' > "$hubs_file"
  local out; out=$(hubs_list 2>/dev/null)
  [[ "$out" == "$HOME/zubot" ]] || fail "expected one line, got: $out"
}

test_no_file_prints_nothing() {
  rm -f "$hubs_file"
  local out; out=$(hubs_list 2>&1)
  [[ -z "$out" ]] || fail "expected no output, got: $out"
}

test_hubs_file_env_overrides_location() {
  print -rl -- '~/azubot' > "$test_tmp/other-hubs"
  local out; out=$(HUBS_FILE="$test_tmp/other-hubs" hubs_list 2>/dev/null)
  [[ "$out" == "$HOME/azubot" ]] || fail "expected azubot from HUBS_FILE, got: $out"
}

test_hubs_roots_lists_hubs_then_legacy() {
  print -rl -- '~/zubot' > "$hubs_file"
  local out; out=$(_hubs_roots 2>/dev/null)
  [[ "${${(f)out}[1]}" == "$HOME/zubot" ]] || fail "first root should be the hub, got: ${${(f)out}[1]}"
  [[ "$out" == *"$HOME/dotfiles"* && "$out" == *"$HOME/workspace/azubot"* ]] || fail "legacy roots missing: $out"
}

for t in ${(k)functions[(I)test_*]}; do
  $t || exit 1
done
print "hubs_list_test: ok"
