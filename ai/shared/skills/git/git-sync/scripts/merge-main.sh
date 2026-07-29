#!/bin/bash
# Merge the default branch into the current feature branch.
# Reports whether the merge completed cleanly or left conflicts.
# Usage: merge-main.sh <default_branch>

set +e  # we want to inspect exit code, not abort

DEFAULT_BRANCH="$1"

if [[ -z "$DEFAULT_BRANCH" ]]; then
    echo "Usage: $0 <default_branch>"
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "$DEFAULT_BRANCH" ]]; then
    echo "ERROR: currently on default branch ($DEFAULT_BRANCH); refusing to merge into itself"
    exit 1
fi

echo "=== Merging $DEFAULT_BRANCH into $CURRENT_BRANCH ==="
git merge --no-edit "$DEFAULT_BRANCH"
MERGE_EXIT=$?

echo ""
if [[ $MERGE_EXIT -eq 0 ]]; then
    echo "=== RESULT: clean merge ==="
    exit 0
fi

# Non-zero: check if it's a conflict or something else
CONFLICTED=$(git diff --name-only --diff-filter=U)
if [[ -n "$CONFLICTED" ]]; then
    echo "=== RESULT: merge produced conflicts ==="
    echo "Conflicted files:"
    echo "$CONFLICTED"
    echo ""
    echo "Resolve each file, git add it, then 'git commit --no-edit' to finalize the merge."
    exit 10  # sentinel: conflicts
fi

echo "=== RESULT: merge failed (not a conflict) ==="
echo "git merge exit code: $MERGE_EXIT"
exit $MERGE_EXIT
