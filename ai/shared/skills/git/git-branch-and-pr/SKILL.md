---
name: git-branch-and-pr
description: On the default branch, move the uncommitted work onto a new feature branch as a single commit and open a pull request for it. Triggers — "branch this and open a PR", "I'm on main, make this a PR", "move this to a branch and PR it", "PR this instead of pushing to main", "get this reviewed".
allowed-tools: Bash(bash *), Bash(git *), Bash(gh *), Read, Edit
---

# Branch and PR

Take uncommitted changes sitting on the default branch, move them to a new feature branch as **one commit**, and open a pull request.

Related: `git-pr` opens a PR for a branch that already exists. `git-push-to-main` skips the PR entirely.

## Scripts

Helper scripts in `~/.claude/skills/git-branch-and-pr/scripts/`:

| Script | Purpose |
|--------|---------|
| `analyze-changes.sh` | Status, branch info, default-branch detection, diffs, untracked files, recent commits, repo-local pre-PR checks, README and PR template checks |
| `repo-check.sh list \| run <name>` | List the repo's own declared pre-PR checks, or run one and gate on its result |
| `stage-files.sh [files\|--all]` | Stage files with sensitive-file warnings |
| `create-commit.sh <msg> [--amend]` | Create commit or amend previous (rejects AI attribution) |

The repo declares its own consistency checks — spec drift, stale generated artifacts — in a
`pre-pr:` frontmatter block on one of its `.claude/skills/*/SKILL.md`. `git-pr` documents the
contract in full. Because this skill runs with the work still uncommitted, relevance is judged
against the working tree: staged, unstaged and untracked.

## Workflow

```dot
digraph branchandpr {
    "On the default branch?" [shape=diamond];
    "Stop — use git-pr" [shape=box];
    "Analyze" [shape=box];
    "Propose branch name" [shape=box];
    "User confirms?" [shape=diamond];
    "Revise name" [shape=box];
    "git checkout -b" [shape=box];
    "Propose commit message" [shape=box];
    "Message confirmed?" [shape=diamond];
    "Revise message" [shape=box];
    "Stage + single commit" [shape=box];
    "Run REQUIRED repo-local checks" [shape=box];
    "Drift clean?" [shape=diamond];
    "Stop — offer to close the drift" [shape=box];
    "Propose PR title + body" [shape=box];
    "PR confirmed?" [shape=diamond];
    "Revise PR text" [shape=box];
    "Push + gh pr create" [shape=box];
    "Report PR URL" [shape=box];

    "On the default branch?" -> "Stop — use git-pr" [label="on a branch"];
    "On the default branch?" -> "Analyze" [label="yes"];
    "Analyze" -> "Propose branch name";
    "Propose branch name" -> "User confirms?";
    "User confirms?" -> "Revise name" [label="no"];
    "Revise name" -> "User confirms?";
    "User confirms?" -> "git checkout -b" [label="yes"];
    "git checkout -b" -> "Propose commit message";
    "Propose commit message" -> "Message confirmed?";
    "Message confirmed?" -> "Revise message" [label="no"];
    "Revise message" -> "Message confirmed?";
    "Message confirmed?" -> "Stage + single commit" [label="yes"];
    "Stage + single commit" -> "Run REQUIRED repo-local checks";
    "Run REQUIRED repo-local checks" -> "Drift clean?";
    "Drift clean?" -> "Stop — offer to close the drift" [label="no"];
    "Drift clean?" -> "Propose PR title + body" [label="yes"];
    "Propose PR title + body" -> "PR confirmed?";
    "PR confirmed?" -> "Revise PR text" [label="no"];
    "Revise PR text" -> "PR confirmed?";
    "PR confirmed?" -> "Push + gh pr create" [label="yes"];
    "Push + gh pr create" -> "Report PR URL";
}
```

## Steps

### Phase 0: Verify On the Default Branch

1. Check the current branch. If it is NOT the default branch (`main` or `master`), **stop immediately**:
   > "This skill only runs on the default branch. You're on `<branch>`. Use `git-pr` to open a PR for a branch that already has commits."

   Do not proceed.

   **If this is a linked worktree, say so and route them properly.** Detect with:
   ```bash
   [[ "$(git rev-parse --absolute-git-dir)" != "$(git rev-parse --path-format=absolute --git-common-dir)" ]]
   ```
   A worktree-based setup (Orca ADE) puts you on a feature branch from the moment the workspace is
   created, so this skill is *never* reachable there — it is not a failure to work around. `git-pr`
   covers the whole flow instead, including the zero-commits-with-uncommitted-work state a fresh
   worktree starts in (its exit 5). Tell the user that rather than leaving them at a dead end.

### Phase 1: Analyze Repository State

2. Run the analysis script **from the repo root**:
   ```bash
   bash -c 'cd "$(git rev-parse --show-toplevel)" && bash ~/.claude/skills/git-branch-and-pr/scripts/analyze-changes.sh'
   ```

   It outputs git status and branch info, default-branch detection, staged and unstaged diffs, untracked files, recent commits (for style reference), and README / PR template existence.

### Phase 2: Propose and Create the Feature Branch

3. Generate a short, descriptive kebab-case branch name from the diff (e.g. `add-auth-middleware`, `fix-cache-eviction`).

4. **Propose the branch name** and put it to the user with **`AskUserQuestion`** — options: use it as-is, or one alternative you'd also accept; they type any other name via Other. Wait for the answer. Never create the branch without it.

5. ```bash
   git checkout -b <branch-name>
   ```
   The uncommitted changes come with you — no stash needed.

### Phase 3: Review and Propose a Commit Message

6. Summarize the changes: what files changed, what the changes do.

7. **Auto-propose a commit message** based on the diff. Show the full message as text, then put it to the user with **`AskUserQuestion`** — use it, or reword it (they type the replacement via Other). Wait for the answer.

8. If README.md exists, check whether the changes affect documented content and update it if so — only for meaningful user-visible changes.

### Phase 4: Stage and Commit (single commit)

9. Stage files:
   ```bash
   bash ~/.claude/skills/git-branch-and-pr/scripts/stage-files.sh --all
   ```
   Or name specific files.

10. Create the one commit:
    ```bash
    bash ~/.claude/skills/git-branch-and-pr/scripts/create-commit.sh "commit message here"
    ```
    The script rejects AI attribution.

### Phase 5: Check the Repo's Own Invariants

11. Run every repo-local check the analysis marked **REQUIRED**:
    ```bash
    bash ~/.claude/skills/git-branch-and-pr/scripts/repo-check.sh run <name>
    ```
    The script applies that check's `fail-on` regex: **0** passed, **1** FAILED, **2** not
    runnable (a gap, not a pass).

    On **1**, **STOP**. Print the report verbatim, then use `AskUserQuestion`: close the drift
    now (run the owning skill per its `fix` line, re-check, then amend the commit with the
    regenerated artifacts), open the PR anyway (only for pre-existing unrelated drift — record
    it in the body under `## Known drift`), or abort. Never close drift on your own; it
    rewrites checked-in artifacts.

    Skip this phase entirely when the analysis found no REQUIRED checks; do not invent one.

### Phase 6: Propose the PR Title and Body

12. Gather context:
    ```bash
    git log --oneline $(git merge-base <default> HEAD)..HEAD
    git diff <default>...HEAD --stat
    ```
    Use **three-dot** (`<default>...HEAD`) — that is what GitHub shows in the PR.

13. Draft:
    - **Title**: under 70 chars, describes the purpose of the change
    - **Body** — use the repo's PR template if one exists, otherwise:
      ```
      ## Summary
      <1-3 bullets explaining what changed and why>

      ## Changes
      <grouped list of specific changes — by file or area>

      ## Test plan
      <how to verify this works — manual steps, test commands>
      ```

14. **Show the title and full body** as text, then put it to the user with **`AskUserQuestion`** — open the PR with this, or edit it first (they type changes via Other). Wait for the answer before pushing anything.

### Phase 7: Push and Create the PR

15. Once confirmed:
    ```bash
    git push -u origin $(git branch --show-current)
    ```
    ```bash
    gh pr create --base <default> --title "<title>" --body-file <path>
    ```
    Write the confirmed body to a file rather than inlining a heredoc — it avoids quoting surprises in long bodies.

16. Output the PR URL.

## Rules

- Run only from the default branch — refuse in Phase 0 otherwise
- **Single commit**: this skill creates exactly one commit on the new branch. For more commits afterwards, use `git-push-branch` from that branch
- **Every decision goes through `AskUserQuestion`, never a question in prose.** A text question reads as a sign-off — the turn looks finished and the user can't tell anything is pending. The dialog renders as something to select and submit. This covers the branch name, the commit message, the PR title and body, and any fork in the workflow. Ordinary text is for showing the proposed content and for the final summary
- NEVER push or create the PR without asking for confirmation first
- NEVER open the PR with a REQUIRED repo-local check failing, unless the user explicitly picked "open anyway" and the drift is recorded in the PR body
- NEVER close drift on the user's behalf — running the fix rewrites checked-in artifacts, which needs their say-so
- NEVER include "Co-Authored-By" or any "Claude Code" / AI attribution in commits **or** in the PR body
- NEVER force-push
- Always propose the branch name and wait for the dialog answer before `git checkout -b`
- Always propose the commit message and wait for the dialog answer before committing
- Always propose the PR title and body and wait for the dialog answer before pushing
- The PR description must accurately reflect the full diff; group by area if the diff is large
- Keep Summary on the "why", Changes on the "what"
- Use conventional commit style if the repo uses it
- Only update README when changes meaningfully affect documented content
- Do not add `--draft` unless the user asks

## Common mistakes

- **Running this on a feature branch.** That is `git-pr`.
- **Two-dot vs three-dot diff.** Use `<default>...HEAD` to match what GitHub shows in the PR.
- **Fabricated description.** Summarize the real diff, not a guess at what the change probably does.
- **Creating the branch before confirming the name.** Renaming afterwards is avoidable churn.
- **Asking in prose instead of `AskUserQuestion`.** "Use this branch name?" at the end of a message looks like the turn is over; the user doesn't know a decision is waiting on them.
- **Expecting multiple commits.** This skill makes exactly one.
- **Skipping Phase 5 because the analysis output was long.** A REQUIRED repo-local check is the repo telling you this diff can break an invariant CI does not cover. Gate on `repo-check.sh run`'s exit code, not on how the report reads.
- **Putting AI attribution in the PR body.** The commit script blocks it in commits; the same rule applies to anything published to GitHub.
