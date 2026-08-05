#!/bin/sh
# gh-project-track.sh — track the current git branch as a card on a GitHub Project.
#
#   gh-project-track.sh <ready|in-progress|in-review|done>
#
# Reads the Claude Code hook JSON on stdin. Registered from each repo's committed
# .claude/settings.json, which guards every call with [ -x "$0" ] so a missing
# script is a silent no-op rather than a transcript error.
#
# OPT-IN GATE: does nothing at all unless ~/.claude/gh-project-track/config.json
# exists. That is what makes committing the hook registration to a shared repo
# safe for teammates who have not set this up.
#
# FAILURE POSTURE: this must never interfere with the user's work. Every failure
# path — no network, gh unauthed, rate limit, broken worktree, deleted issue,
# card removed from the board, stale option cache — exits 0. Exit code 2 (block)
# is never used. The EXIT trap enforces this even on an unexpected error.
#
# Transitions are MONOTONIC: an Edit late in a branch's life can never pull a
# card back from In review to In progress.

TRANSITION="$1"

ROOT="$HOME/.claude/gh-project-track"
CONFIG="$ROOT/config.json"
LOG="$ROOT/log"

# Always succeed. Nothing here is worth interrupting a session over.
trap 'exit 0' EXIT
trap 'exit 0' INT TERM HUP

# --- gate ------------------------------------------------------------------
[ -f "$CONFIG" ] || exit 0
command -v jq  >/dev/null 2>&1 || exit 0
command -v gh  >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

case "$TRANSITION" in
  ready|in-progress|in-review|done) : ;;
  *) exit 0 ;;
esac

cfg() { jq -r "$1 // empty" "$CONFIG" 2>/dev/null; }

GH_TIMEOUT=$(cfg '.gh_timeout_secs'); [ -n "$GH_TIMEOUT" ] || GH_TIMEOUT=12
IDS_TTL=$(cfg '.ids_ttl_secs');       [ -n "$IDS_TTL" ]   || IDS_TTL=86400
LOCK_STALE=$(cfg '.lock_stale_secs'); [ -n "$LOCK_STALE" ] || LOCK_STALE=60
LOG_MAX=$(cfg '.log_max_bytes');      [ -n "$LOG_MAX" ]   || LOG_MAX=1048576
QUIET_IP=$(cfg '.quiet_in_progress')
ASSIGNEE=$(cfg '.assignee')
ORCA_MIRROR=$(cfg '.orca')

PROJECT_ID=$(cfg '.project.id')
FIELD_ID=$(cfg '.project.status_field_id')
[ -n "$PROJECT_ID" ] && [ -n "$FIELD_ID" ] || exit 0

# --- logging ---------------------------------------------------------------
mkdir -p "$ROOT" 2>/dev/null
if [ -f "$LOG" ]; then
  sz=$(wc -c < "$LOG" 2>/dev/null | tr -d ' ')
  [ -n "$sz" ] && [ "$sz" -gt "$LOG_MAX" ] 2>/dev/null && mv -f "$LOG" "$LOG.1" 2>/dev/null
fi
SLUG="pending"
say() {
  printf '%s %-11s %-46s %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$TRANSITION" "$SLUG" "$1" >> "$LOG" 2>/dev/null
}

# --- hook payload ----------------------------------------------------------
PAYLOAD=$(cat 2>/dev/null)
HOOK_CWD=$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null)
[ -n "$HOOK_CWD" ] && [ -d "$HOOK_CWD" ] || HOOK_CWD="$PWD"

# --- resolve repo + branch -------------------------------------------------
# Orca renames both branch and directory (autoRenameBranchFromWork), so nothing
# may key on directory name — only on the branch git itself reports.
BRANCH=$(git -C "$HOOK_CWD" rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
[ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] || exit 0

REMOTE=$(git -C "$HOOK_CWD" remote get-url origin 2>/dev/null) || exit 0
REPO=$(printf '%s' "$REMOTE" \
  | sed -e 's#^git@[^:]*:##' -e 's#^https\{0,1\}://[^/]*/##' -e 's#\.git$##')
[ -n "$REPO" ] || exit 0

DEFAULT_BRANCH=$(git -C "$HOOK_CWD" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
[ -n "$DEFAULT_BRANCH" ] || DEFAULT_BRANCH=main
[ "$BRANCH" = "$DEFAULT_BRANCH" ] && exit 0

# repo must be opted in
jq -e --arg r "$REPO" '.repos | index($r)' "$CONFIG" >/dev/null 2>&1 || exit 0

SLUG="$REPO@$BRANCH"
WORKTREE=$(git -C "$HOOK_CWD" rev-parse --show-toplevel 2>/dev/null)
[ -n "$WORKTREE" ] || WORKTREE="$HOOK_CWD"

# --- rank ------------------------------------------------------------------
rank_of() {
  case "$1" in
    backlog) echo 1 ;; ready) echo 2 ;; in-progress) echo 3 ;;
    in-review) echo 4 ;; done) echo 5 ;;
    Backlog) echo 1 ;; Ready) echo 2 ;; "In progress") echo 3 ;;
    "In review") echo 4 ;; Done) echo 5 ;;
    *) echo 0 ;;
  esac
}
WANT_RANK=$(rank_of "$TRANSITION")

# --- fast path -------------------------------------------------------------
# Edit|Write fires on EVERY file edit, so the common case must be a couple of
# stat calls and an exit with no network at all.
hashed() { printf '%s' "$1" | shasum 2>/dev/null | cut -c1-10; }
FAST_DIR="$ROOT/fast"
# Both halves must have '/' flattened: a branch like "azu/my-feature" would
# otherwise make this a path into a directory that does not exist.
FAST_KEY=$(printf '%s' "$WORKTREE" | tr '/' '_')
FAST_BRANCH=$(printf '%s' "$BRANCH" | tr '/' '_')
FAST="$FAST_DIR/${FAST_KEY}_${FAST_BRANCH}"
mkdir -p "$FAST_DIR" 2>/dev/null
if [ -f "$FAST" ]; then
  have=$(cat "$FAST" 2>/dev/null | tr -d ' \n')
  case "$have" in ''|*[!0-9]*) have=0 ;; esac
  if [ "$have" -ge "$WANT_RANK" ] 2>/dev/null; then
    [ "$TRANSITION" = "in-progress" ] && [ "$QUIET_IP" = "true" ] && exit 0
    say "no-op: board already at rank $have >= $WANT_RANK"
    exit 0
  fi
fi

# --- lock ------------------------------------------------------------------
STATE_DIR="$ROOT/state/$(printf '%s' "$REPO" | tr '/' '-')@${FAST_BRANCH}-$(hashed "$WORKTREE")"
LOCK="$ROOT/locks/$(hashed "$SLUG$WORKTREE").lock"
mkdir -p "$ROOT/locks" "$STATE_DIR" 2>/dev/null
if ! mkdir "$LOCK" 2>/dev/null; then
  # steal a stale lock
  if [ -d "$LOCK" ]; then
    now=$(date +%s)
    mt=$(stat -f %m "$LOCK" 2>/dev/null || stat -c %Y "$LOCK" 2>/dev/null)
    if [ -n "$mt" ] && [ $((now - mt)) -gt "$LOCK_STALE" ] 2>/dev/null; then
      rm -rf "$LOCK" 2>/dev/null; mkdir "$LOCK" 2>/dev/null || exit 0
    else
      exit 0
    fi
  else
    exit 0
  fi
fi
cleanup() { rm -rf "$LOCK" 2>/dev/null; exit 0; }
trap cleanup EXIT INT TERM HUP

STATE="$STATE_DIR/state.json"
st() { [ -f "$STATE" ] && jq -r "$1 // empty" "$STATE" 2>/dev/null; }

ghq() { timeout "$GH_TIMEOUT" gh "$@" 2>/dev/null; }

# --- resolve status option ids --------------------------------------------
opt_id() { cfg ".project.status_options.\"$1\""; }
WANT_OPT=$(opt_id "$TRANSITION")
[ -n "$WANT_OPT" ] || cleanup

# --- find or create the issue ---------------------------------------------
MARKER="<!-- track-branch: ${REPO}@${BRANCH} -->"
ISSUE=$(st '.issue')

if [ -z "$ISSUE" ]; then
  # Recover from the durable marker before creating anything — the mapping must
  # survive cache loss and be recoverable from GitHub alone.
  ISSUE=$(ghq issue list --repo "$REPO" --state all --limit 50 \
            --search "\"track-branch: ${REPO}@${BRANCH}\" in:body" \
            --json number --jq '.[0].number')
fi

TITLE_SOURCE="branch"
if [ -z "$ISSUE" ]; then
  # Lazy creation: no issue exists until something actually happens on the
  # branch, so throwaway branches never clutter the board.
  TITLE=$(printf '%s' "$BRANCH" | sed -e 's#^[a-z]*/##' -e 's/[-_]/ /g')
  BODY_FILE=$(mktemp 2>/dev/null) || cleanup
  printf '%s\n\n---\n%s\n' "Tracking branch \`$BRANCH\` in \`$REPO\`." "$MARKER" > "$BODY_FILE"

  set -- issue create --repo "$REPO" --title "$TITLE" --body-file "$BODY_FILE"
  [ -n "$ASSIGNEE" ] && set -- "$@" --assignee "$ASSIGNEE"
  URL=$(ghq "$@")
  rm -f "$BODY_FILE" 2>/dev/null
  ISSUE=$(printf '%s' "$URL" | sed -n 's#.*/issues/\([0-9][0-9]*\).*#\1#p')
  [ -n "$ISSUE" ] || { say "could not create issue"; cleanup; }
  say "created issue #$ISSUE (title from $TITLE_SOURCE)"
fi

# --- ensure the card is on the board --------------------------------------
ITEM=$(st '.item_id')
if [ -z "$ITEM" ]; then
  NODE=$(ghq issue view "$ISSUE" --repo "$REPO" --json id --jq '.id')
  [ -n "$NODE" ] || { say "issue #$ISSUE not readable"; cleanup; }
  ITEM=$(ghq api graphql -f query='
    mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p,contentId:$c}){ item{ id } } }' \
    -f p="$PROJECT_ID" -f c="$NODE" --jq '.data.addProjectV2ItemById.item.id')
  [ -n "$ITEM" ] || { say "could not add #$ISSUE to the board"; cleanup; }
  say "added #$ISSUE to the board"
fi

# --- current status, monotonic guard --------------------------------------
read_status() {
  ghq api graphql -f query='
    query($i:ID!){ node(id:$i){ ... on ProjectV2Item {
      fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue { name } } } } }' \
    -f i="$ITEM" --jq '.data.node.fieldValueByName.name'
}
apply_status() {
  ghq api graphql -f query='
    mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
      updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){
        projectV2Item{ id } } }' \
    -f p="$PROJECT_ID" -f i="$ITEM" -f f="$FIELD_ID" -f o="$WANT_OPT" >/dev/null
}

CUR_NAME=$(read_status)
CUR_RANK=$(rank_of "$CUR_NAME")

if [ "$CUR_RANK" -ge "$WANT_RANK" ] 2>/dev/null; then
  [ "$TRANSITION" = "in-progress" ] && [ "$QUIET_IP" = "true" ] || \
    say "no-op: board already at rank $CUR_RANK ('$CUR_NAME') >= $WANT_RANK"
else
  apply_status
  say "status rank $CUR_RANK -> $WANT_RANK"
fi

# --- in-review: link the PR ------------------------------------------------
# Resolved from repo+branch rather than scraped from command output. Scraping is
# fragile in both directions: it misses PRs opened through a wrapper script (the
# git-pr skill runs create-pr.sh, so "gh pr create" never appears in the command
# string), and a URL in the output may name a DIFFERENT repo than the one cwd
# resolves to — a hook's cwd is the session worktree, so a `cd` inside a command
# is invisible and a cross-repo PR number would be applied to the wrong repo.
if [ "$TRANSITION" = "in-review" ]; then
  PR=$(ghq pr list --repo "$REPO" --head "$BRANCH" --state open --limit 1 --json number --jq '.[0].number')
  if [ -z "$PR" ]; then
    say "no open PR for $BRANCH; not linking"
  else
    PRBODY=$(ghq pr view "$PR" --repo "$REPO" --json body --jq '.body')
    if printf '%s' "$PRBODY" | grep -qiE "(closes|fixes|resolves) #${ISSUE}\b"; then
      say "PR #$PR already links #$ISSUE"
    else
      BF=$(mktemp 2>/dev/null) || cleanup
      printf '%s\n\nCloses #%s\n' "$PRBODY" "$ISSUE" > "$BF"
      if ghq pr edit "$PR" --repo "$REPO" --body-file "$BF" >/dev/null; then
        say "linked 'Closes #$ISSUE' into PR #$PR"
      fi
      rm -f "$BF" 2>/dev/null
    fi
  fi
fi

# --- re-apply across the drift window -------------------------------------
# The board runs GitHub workflows that asynchronously overwrite Status a few
# seconds after a write — notably a PR<->issue link event resets a card to
# In progress. Writing once is not enough; read back and re-apply.
if [ "$WANT_RANK" -ge 4 ] 2>/dev/null; then
  for delay in 3 9; do
    sleep "$delay"
    now_name=$(read_status)
    now_rank=$(rank_of "$now_name")
    if [ "$now_rank" -lt "$WANT_RANK" ] 2>/dev/null; then
      apply_status
      say "board drifted to '$now_name'; re-applied rank $WANT_RANK"
    fi
  done
fi

# --- persist ---------------------------------------------------------------
FINAL_NAME=$(read_status)
FINAL_RANK=$(rank_of "$FINAL_NAME")
[ "$FINAL_RANK" -lt "$WANT_RANK" ] 2>/dev/null && FINAL_RANK="$WANT_RANK"

printf '%s' "$FINAL_RANK" > "$FAST" 2>/dev/null
jq -n --arg repo "$REPO" --arg branch "$BRANCH" --arg wt "$WORKTREE" \
      --argjson issue "${ISSUE:-0}" --arg item "$ITEM" \
      --argjson rank "$FINAL_RANK" --arg status "$FINAL_NAME" \
      --arg ts "$(date +%s)" \
  '{repo:$repo,branch:$branch,worktree:$wt,issue:$issue,item_id:$item,
    rank:$rank,status_name:$status,updated_at:($ts|tonumber)}' \
  > "$STATE" 2>/dev/null

# --- mirror onto Orca's own workspace board -------------------------------
if [ "$ORCA_MIRROR" = "true" ] && command -v orca >/dev/null 2>&1; then
  case "$TRANSITION" in
    ready)       ows=todo ;;
    in-progress) ows=in-progress ;;
    in-review)   ows=in-review ;;
    done)        ows=completed ;;
    *)           ows= ;;
  esac
  [ -n "$ows" ] && timeout "$GH_TIMEOUT" orca worktree set \
    --worktree "path:$WORKTREE" --issue "$ISSUE" --workspace-status "$ows" >/dev/null 2>&1
fi

cleanup
