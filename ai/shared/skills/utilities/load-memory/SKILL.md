---
name: load-memory
description: Restore working memory from MEMORY.md and CLAUDE.md at the repo root. Use at the start of a new session to pick up where you left off, or when the user says "load memory", "restore context", or "what were we working on".
disable-model-invocation: true
allowed-tools: Read, Bash(git rev-parse --show-toplevel)
---

# Load Memory

Read `MEMORY.md` and `CLAUDE.md` from the repository root to restore context from a previous session.

## Steps

### Phase 1: Locate and Read Memory Files

1. Find the repository root:
   ```bash
   git rev-parse --show-toplevel
   ```

2. Read both files from the repo root (in parallel):
   - `MEMORY.md` — session memory from previous `/save-memory`
   - `CLAUDE.md` — project instructions and conventions

   If MEMORY.md does not exist, tell the user there's no saved memory for this project and suggest using `/save-memory` to create one.

### Phase 2: Present Restored Context

3. Present a concise summary to the user organized as:

   **Last session** — date and what was covered (from MEMORY.md header)

   **Current state** — what's in progress, blocked, or needs attention

   **Key context** — most important decisions, patterns, and preferences to be aware of

   **Next steps** — what was planned to happen next

   Keep the summary SHORT (aim for 10-20 lines). The user can ask for details on any section.

### Phase 3: Ready to Continue

4. Ask the user: "Want to continue from the next steps, or work on something else?"

## Rules

- Read MEMORY.md and CLAUDE.md in parallel for speed
- Present a CONCISE summary — don't dump the entire file contents
- Highlight anything marked as blocked or urgent
- If MEMORY.md has a "Next Steps" section, lead with that — it's what the user most likely wants to continue
- Do NOT modify any files — this skill is read-only
- If both MEMORY.md and CLAUDE.md exist, synthesize them — don't present them separately
