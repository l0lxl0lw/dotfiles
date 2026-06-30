#!/bin/bash
# Analyze git state before syncing main into a feature branch
# Outputs: current branch, default branch, uncommitted summary, main divergence, merge state

set -e

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Not in a git repository"
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current)
echo "=== CURRENT BRANCH ==="
echo "$CURRENT_BRANCH"
echo ""

# Detect default branch
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || echo "")
if [[ -z "$DEFAULT_BRANCH" ]]; then
    if git show-ref --verify --quiet refs/heads/main 2>/dev/null; then
        DEFAULT_BRANCH="main"
    elif git show-ref --verify --quiet refs/heads/master 2>/dev/null; then
        DEFAULT_BRANCH="master"
    else
        DEFAULT_BRANCH="main"
    fi
fi
echo "=== DEFAULT BRANCH ==="
echo "$DEFAULT_BRANCH"
echo ""

if [[ "$CURRENT_BRANCH" == "$DEFAULT_BRANCH" ]]; then
    echo "ERROR: Currently on the default branch ($DEFAULT_BRANCH)."
    echo "This skill is for syncing main INTO a feature branch."
    echo "Use git-push-to-main or git-pr-from-main instead."
    exit 2
fi

# Merge-in-progress check
echo "=== MERGE STATE ==="
if [[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ]]; then
    echo "ERROR: A merge is already in progress."
    echo "Finish it (git merge --continue) or abort it (git merge --abort) before running this skill."
    exit 3
else
    echo "(no merge in progress)"
fi
echo ""

# Uncommitted summary
echo "=== UNCOMMITTED CHANGES ==="
PORCELAIN=$(git status --porcelain)
if [[ -n "$PORCELAIN" ]]; then
    echo "$PORCELAIN"
    echo ""
    echo "(will be stashed before sync, restored after)"
else
    echo "(no uncommitted changes — skill will just sync main into branch, no final commit)"
fi
echo ""

# Fetch to update remote refs for divergence comparison
echo "=== FETCHING ORIGIN ==="
git fetch origin --quiet 2>&1 || echo "WARNING: git fetch failed"
echo "(done)"
echo ""

# Local default vs origin default
echo "=== LOCAL $DEFAULT_BRANCH vs origin/$DEFAULT_BRANCH ==="
if git show-ref --verify --quiet "refs/heads/$DEFAULT_BRANCH"; then
    LOCAL_DEFAULT=$(git rev-parse "$DEFAULT_BRANCH")
    REMOTE_DEFAULT=$(git rev-parse "origin/$DEFAULT_BRANCH" 2>/dev/null || echo "")
    if [[ -z "$REMOTE_DEFAULT" ]]; then
        echo "WARNING: origin/$DEFAULT_BRANCH not found"
    elif [[ "$LOCAL_DEFAULT" == "$REMOTE_DEFAULT" ]]; then
        echo "Local $DEFAULT_BRANCH is up to date with origin/$DEFAULT_BRANCH"
    else
        AHEAD=$(git rev-list --count "origin/$DEFAULT_BRANCH..$DEFAULT_BRANCH" 2>/dev/null || echo "0")
        BEHIND=$(git rev-list --count "$DEFAULT_BRANCH..origin/$DEFAULT_BRANCH" 2>/dev/null || echo "0")
        echo "Ahead: $AHEAD, Behind: $BEHIND"
        if [[ "$AHEAD" -gt 0 && "$BEHIND" -gt 0 ]]; then
            echo "ERROR: Local $DEFAULT_BRANCH has diverged from origin/$DEFAULT_BRANCH."
            echo "Push or rebase your local $DEFAULT_BRANCH first. This skill will not overwrite your commits."
            exit 4
        elif [[ "$AHEAD" -gt 0 ]]; then
            echo "ERROR: Local $DEFAULT_BRANCH has $AHEAD unpushed commit(s)."
            echo "Push them first. This skill will not overwrite your commits."
            exit 4
        else
            echo "Local $DEFAULT_BRANCH is behind by $BEHIND commit(s) — will fast-forward."
        fi
    fi
else
    echo "No local $DEFAULT_BRANCH branch — will create it from origin/$DEFAULT_BRANCH"
fi
echo ""

# Feature branch upstream
echo "=== FEATURE BRANCH UPSTREAM ==="
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")
if [[ -n "$UPSTREAM" ]]; then
    echo "Upstream: $UPSTREAM"
else
    echo "(no upstream — first push will need 'git push -u origin $CURRENT_BRANCH')"
fi
echo ""

# Recent commits for style reference
echo "=== RECENT COMMITS (for style reference) ==="
git log --oneline -5 2>/dev/null || echo "(no commits yet)"
