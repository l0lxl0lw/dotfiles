#!/bin/bash
# Survey every Orca-managed worktree for this repo and report how far behind
# origin/<default> each one is, plus the live agent terminal handle for each.
#
# Usage: survey.sh [default_branch]
# Exit:  0  survey printed (even when nothing is behind)
#        1  not a git repo / orca CLI unavailable
#
# Output is TSV on stdout after a header line, so the caller can parse it:
#   path <TAB> display <TAB> branch <TAB> behind <TAB> terminal <TAB> issue
# terminal is the Orca terminal handle, or "-" when no live terminal exists.

set -e

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Not in a git repository" >&2
    exit 1
fi

if ! command -v orca >/dev/null 2>&1; then
    echo "ERROR: the 'orca' CLI is not on PATH — this skill only applies to Orca workspaces." >&2
    exit 1
fi

DEFAULT_BRANCH="$1"
if [[ -z "$DEFAULT_BRANCH" ]]; then
    DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || echo "main")
fi

echo "=== Fetching origin ===" >&2
git fetch origin --quiet 2>&1 >&2 || echo "WARNING: git fetch failed" >&2

if ! git rev-parse --verify --quiet "origin/$DEFAULT_BRANCH" >/dev/null; then
    echo "ERROR: origin/$DEFAULT_BRANCH does not exist." >&2
    exit 1
fi

TARGET=$(git rev-parse "origin/$DEFAULT_BRANCH")
echo "=== origin/$DEFAULT_BRANCH is at $(git log --oneline -1 "origin/$DEFAULT_BRANCH") ===" >&2

REPO_ID=$(orca worktree current --json 2>/dev/null | python3 -c "
import json,sys
try: print(json.load(sys.stdin)['result']['worktree']['repoId'])
except Exception: print('')
" || echo "")

python3 - "$REPO_ID" "$TARGET" "$DEFAULT_BRANCH" <<'PY'
import json, subprocess, sys

repo_id, target, default_branch = sys.argv[1], sys.argv[2], sys.argv[3]

# Fetched here rather than piped in: this script itself arrives on stdin via the
# heredoc, so a pipe into python3 would be swallowed by it.
data = json.loads(subprocess.run(
    ["orca", "worktree", "list", "--json"],
    capture_output=True, text=True, check=True).stdout)["result"]["worktrees"]

# Terminal handles, keyed by worktree id. A worktree can host several terminals;
# prefer one that is connected, since that is the one an agent is sitting in.
try:
    terms = json.loads(subprocess.run(
        ["orca", "terminal", "list", "--json"],
        capture_output=True, text=True, check=True).stdout)["result"]["terminals"]
except Exception:
    terms = []

by_worktree = {}
for t in terms:
    wid = t.get("worktreeId")
    if not wid:
        continue
    # A connected terminal beats a stale one; otherwise first seen wins.
    if wid not in by_worktree or (t.get("connected") and not by_worktree[wid].get("connected")):
        by_worktree[wid] = t

print("path\tdisplay\tbranch\tbehind\tterminal\tissue")
for w in data:
    if w.get("isMainWorktree"):
        continue
    if repo_id and w.get("repoId") != repo_id:
        continue

    path = w["path"]
    branch = (w.get("branch") or "").replace("refs/heads/", "")
    if branch == default_branch:
        continue

    try:
        behind = subprocess.run(
            ["git", "-C", path, "rev-list", "--count", f"HEAD..{target}"],
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        behind = "?"

    term = by_worktree.get(w["id"], {}).get("handle", "-")
    issue = w.get("linkedIssue") or "-"
    print(f"{path}\t{w.get('displayName','')}\t{branch}\t{behind}\t{term}\t{issue}")
PY
