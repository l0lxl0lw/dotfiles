#!/bin/bash
# Fast-forward local default branch from origin, then return to the feature branch.
# Usage: sync-main.sh <default_branch> <feature_branch>

set -e

DEFAULT_BRANCH="$1"
FEATURE_BRANCH="$2"

if [[ -z "$DEFAULT_BRANCH" || -z "$FEATURE_BRANCH" ]]; then
    echo "Usage: $0 <default_branch> <feature_branch>"
    exit 1
fi

if [[ "$DEFAULT_BRANCH" == "$FEATURE_BRANCH" ]]; then
    echo "ERROR: default branch and feature branch are the same ($DEFAULT_BRANCH)"
    exit 1
fi

echo "=== Fetching origin ==="
git fetch origin

echo ""
echo "=== Switching to $DEFAULT_BRANCH ==="
if git show-ref --verify --quiet "refs/heads/$DEFAULT_BRANCH"; then
    git checkout "$DEFAULT_BRANCH"
else
    echo "Creating local $DEFAULT_BRANCH tracking origin/$DEFAULT_BRANCH"
    git checkout -b "$DEFAULT_BRANCH" "origin/$DEFAULT_BRANCH"
fi

echo ""
echo "=== Fast-forwarding $DEFAULT_BRANCH from origin/$DEFAULT_BRANCH ==="
if ! git merge --ff-only "origin/$DEFAULT_BRANCH"; then
    echo ""
    echo "ERROR: fast-forward failed. Local $DEFAULT_BRANCH has diverged from origin/$DEFAULT_BRANCH."
    echo "Returning to $FEATURE_BRANCH."
    git checkout "$FEATURE_BRANCH"
    exit 2
fi

echo ""
echo "=== Returning to $FEATURE_BRANCH ==="
git checkout "$FEATURE_BRANCH"

echo ""
echo "=== Done. Local $DEFAULT_BRANCH is now at origin/$DEFAULT_BRANCH ==="
git log --oneline -1 "$DEFAULT_BRANCH"
