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
    print -r -- "---\nname: $s\ndescription: $s from ${hub:t}\n---" > "$hub/.agents/skills/$s/SKILL.md"
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

for t in ${(ok)functions[(I)test_*]}; do
  $t || exit 1
done
print "hubs_sync_test: ok"
