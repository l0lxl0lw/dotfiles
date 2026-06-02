#!/usr/bin/env bash
#
# journal-stop.sh — Stop hook that asks Claude to append a learnings journal
# entry at the end of *substantive* responses.
#
# Mechanism (inline): a shell script cannot summarize a conversation, so instead
# of writing the file itself this hook emits a `decision: "block"` with
# instructions, which re-prompts the same Claude (full context) to write the
# entry. On the second invocation `stop_hook_active` is true and we step aside,
# so there is no infinite loop.
#
# Journal layout (chosen for easy lookup later):
#   ~/Library/CloudStorage/Dropbox/sync/claude/journals/YYYY/MM/
#       YYYY-MM-DD_HHMMSS_<host>_<slug>.md
#   with searchable YAML frontmatter (date, host, cwd, repo, branch,
#   category, tags, title).
#
# Paths use ~/ / $HOME so this works on any machine, not just one home dir.

set -euo pipefail

input=$(cat)

# Loop guard: if we already blocked once this turn, allow the stop to proceed.
stop_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false')
if [ "$stop_active" = "true" ]; then
  exit 0
fi

read -r -d '' reason <<'EOF' || true
END-OF-TURN JOURNAL (this instruction comes from the journal-stop hook).

Decide first: did THIS turn contain something worth journaling? Worth it =
a fix, a pain point you hit, something you missed or got wrong (and corrected),
or a concrete learning for next time. NOT worth it = greetings, a simple
lookup/answer, a clarifying question with no work, or a turn whose only action
was writing a previous journal entry.

If NOT worth it: do not write a file. Reply with one short line ("No journal:
trivial turn.") and stop. The hook will not block again.

If worth it: gather context in ONE bash call, then Write the entry.

  TS_DIR=$(date "+%Y/%m")
  TS_FILE=$(date "+%Y-%m-%d_%H%M%S")
  TS_ISO=$(date "+%Y-%m-%dT%H:%M:%S%z")
  HOST=$(hostname -s)
  CWD_TILDE="${PWD/#$HOME/~}"
  REPO=$(git rev-parse --show-toplevel 2>/dev/null | xargs -r basename || echo none)
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo none)
  DIR="$HOME/Library/CloudStorage/Dropbox/sync/claude/journals/$TS_DIR"
  mkdir -p "$DIR"
  # final path: $DIR/${TS_FILE}_${HOST}_<slug>.md

Choose <slug>: 2-5 word kebab-case topic of the turn (e.g. add-stop-hook-journaling).

Write the file with this exact shape (clear plain English in the body — this is
for a human to read later, so do NOT write the body in caveman style). Fill only
the sections that apply; keep each to a few lines. Omit empty sections.

  ---
  date: <TS_ISO>
  host: <HOST>
  cwd: <CWD_TILDE>          # use ~/ form, never /Users/<name>/
  repo: <REPO>
  branch: <BRANCH>
  category: <fix|pain-point|missed|learning>
  tags: [<short>, <tags>]
  title: <short human title>
  ---

  ## What happened
  ## Pain point / what was missed
  ## What was fixed
  ## Learning for next time

Rules:
- Any path written inside the file must use ~/ (or $HOME), never /Users/<name>/.
- One file per turn. Do not overwrite earlier entries (the HHMMSS timestamp keeps
  them unique).
- After writing, stop normally. Do not summarize the journal back to the user
  beyond a one-line confirmation with the file path.
EOF

jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
