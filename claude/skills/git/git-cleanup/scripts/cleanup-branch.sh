#!/bin/bash
# Refresh the default branch, then delete the merged feature branch (local + remote).
#
# REQUIRES --merge-verified as the third argument. Pass it ONLY after
# verify-merged.sh exited 0. The force-delete fallback below is licensed by that
# check and by nothing else.
#
# Usage: cleanup-branch.sh <branch> <default_branch> --merge-verified
# Exit:  0   done
#        1   usage / error
#        10  default branch could not fast-forward (diverged) — caller must resolve

set -e

BRANCH="$1"
DEFAULT_BRANCH="$2"
VERIFIED="$3"

if [[ -z "$BRANCH" || -z "$DEFAULT_BRANCH" ]]; then
    echo "Usage: $0 <branch> <default_branch> --merge-verified"
    exit 1
fi

if [[ "$VERIFIED" != "--merge-verified" ]]; then
    echo "ERROR: refusing to run without --merge-verified."
    echo "Run verify-merged.sh first and confirm it exited 0 (PR state MERGED)."
    exit 1
fi

if [[ "$BRANCH" == "$DEFAULT_BRANCH" ]]; then
    echo "ERROR: refusing to delete the default branch ($DEFAULT_BRANCH)"
    exit 1
fi

echo "=== Fetching origin (with --prune) ==="
# --prune drops the remote-tracking ref if GitHub auto-deleted the head branch on merge
git fetch origin --prune

echo ""
echo "=== Switching to $DEFAULT_BRANCH ==="
if git show-ref --verify --quiet "refs/heads/$DEFAULT_BRANCH"; then
    git switch "$DEFAULT_BRANCH"
else
    echo "No local $DEFAULT_BRANCH — creating it from origin/$DEFAULT_BRANCH"
    git switch -c "$DEFAULT_BRANCH" "origin/$DEFAULT_BRANCH"
fi

echo ""
echo "=== Pulling latest origin/$DEFAULT_BRANCH (fast-forward only) ==="
# --ff-only is deliberate: local default should only ever fast-forward.
# A plain pull could invent a surprise merge commit on the default branch.
if ! git pull --ff-only origin "$DEFAULT_BRANCH"; then
    echo ""
    echo "ERROR: fast-forward failed. Local $DEFAULT_BRANCH has diverged from origin/$DEFAULT_BRANCH."
    echo "Something was committed directly to local $DEFAULT_BRANCH."
    echo "Do NOT force this. Resolve it with the user (see git-sync's"
    echo "conflict procedure), then re-run this script."
    echo ""
    echo "Branch '$BRANCH' has NOT been deleted."
    exit 10
fi

echo ""
echo "=== Deleting local branch $BRANCH ==="
if git branch -d "$BRANCH" 2>/dev/null; then
    echo "deleted (fast-forward-merged, safe delete)"
else
    # -d refuses after a squash or rebase merge ("not fully merged") because the
    # branch commits are not ancestors of the default branch. gh already confirmed
    # state == MERGED, so the work IS upstream. Force-delete is safe HERE ONLY.
    git branch -D "$BRANCH"
    echo "deleted (squash/rebase merge — forced, licensed by the verified MERGED state)"
fi

echo ""
echo "=== Remote branch ==="
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    git push origin --delete "$BRANCH"
    echo "remote branch deleted"
else
    echo "remote branch already gone (auto-deleted on merge)"
fi

echo ""
echo "=== DONE ==="
echo "Now on: $(git branch --show-current)"
git log --oneline -1
