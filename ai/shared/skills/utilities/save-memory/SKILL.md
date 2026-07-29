---
name: save-memory
description: Save working memory from the current chat session into MEMORY.md at the repo root. Use when context is about to overflow, the user asks to "remember everything", or before ending a long session. Captures topics, research, decisions, tools, file paths, preferences, and next steps.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash(git rev-parse --show-toplevel)
---

# Save Memory

Persist the current session's working knowledge to `MEMORY.md` at the repository root (next to `CLAUDE.md`), so it can be restored in a future session with `/load-memory`.

## What to Capture

Review the ENTIRE conversation history and extract:

| Section | What to include |
|---------|----------------|
| **Current State** | What's in progress, what's blocked, what's done this session |
| **Topics & Research** | What was discussed, findings, conclusions, URLs visited |
| **Decisions Made** | Choices and reasoning — why option A over B |
| **Key Files & Paths** | Important file locations discovered or created |
| **Tools & Commands** | Useful commands, workflows, scripts that worked |
| **User Preferences** | Workflow preferences, style choices, things the user likes/dislikes |
| **Architecture & Patterns** | System design, conventions, how things connect |
| **Next Steps** | What needs to happen next, unfinished work, blockers |

## Steps

### Phase 1: Determine Repo Root

1. Find the repository root:
   ```bash
   git rev-parse --show-toplevel
   ```
   Use this as the base path for MEMORY.md.

### Phase 2: Read Existing Memory

2. Read the existing `MEMORY.md` at repo root (if it exists). You will MERGE new information into it, not replace it wholesale. Preserve any existing content that is still relevant.

3. Also read `CLAUDE.md` at repo root to understand what's already documented there (avoid duplicating CLAUDE.md content in MEMORY.md).

### Phase 3: Extract Session Knowledge

4. Review the ENTIRE conversation from start to finish. For each message exchange, extract:
   - Topics discussed and conclusions reached
   - Research performed and findings
   - Decisions made with rationale
   - Files read, created, or modified
   - Commands that were run and their purpose
   - User preferences expressed (explicitly or implicitly)
   - Architectural understanding gained
   - What was left unfinished

5. Organize extracted knowledge into the sections from the table above. Be thorough but concise — capture the SUBSTANCE, not the conversation flow.

### Phase 4: Write MEMORY.md

6. Write the updated `MEMORY.md` at repo root with this structure:

```markdown
# Memory — [Project Name]

## Last Updated
YYYY-MM-DD — Brief description of what this session covered

## Current State
[What's in progress, blocked, or recently completed]

## Topics & Research
[Key findings, conclusions, URLs/sources consulted]

## Decisions Made
[Choices and reasoning]

## Key Files & Paths
[Important locations in the codebase]

## Tools & Commands
[Useful commands and workflows]

## User Preferences
[How the user likes to work]

## Architecture & Patterns
[System design understanding]

## Next Steps
[What to do next, unfinished work]
```

### Phase 5: Update CLAUDE.md (if warranted)

7. If any STABLE patterns emerged this session that should be permanent project instructions (not session-specific state), suggest adding them to CLAUDE.md. Only add things that are:
   - Confirmed across multiple interactions (not one-off)
   - Project conventions, not session context
   - Not already in CLAUDE.md

   Ask the user before modifying CLAUDE.md.

## Rules

- NEVER overwrite existing MEMORY.md blindly — always read first and merge
- Keep entries concise — this is reference material, not a transcript
- Use bullet points, not paragraphs
- Include dates for time-sensitive state
- Omit sections that have no content (don't write empty sections)
- If a section from a previous save is outdated, UPDATE it — don't keep stale info
- MEMORY.md should be useful to a FUTURE Claude session that has zero context about this conversation
- Do NOT duplicate content that already exists in CLAUDE.md
- Capture the user's ACTUAL preferences (what they did/said), not assumptions
