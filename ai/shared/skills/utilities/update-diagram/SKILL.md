---
name: update-diagram
description: Scan the codebase and update existing diagram files to reflect the current state of the code. Use when diagrams need refreshing after code changes.
---

# Update Diagram

Scan the codebase and update existing diagram files to reflect the current state of the code.

## Overview

This skill finds all diagram markdown files (`*diagram.md` or `*diagrams.md`) in the workspace and updates them based on a deep analysis of the codebase. It preserves the existing diagram structure and style while adding, removing, or modifying elements to match the current code.

## Steps

### Phase 1: Discovery

1. Find all diagram files matching `*diagram.md` or `*diagrams.md` patterns in the workspace
2. Read each diagram file and analyze:
   - What type of diagram it is (architecture, database schema, call flow, component, sequence, etc.)
   - What format it uses (Mermaid, ASCII art, markdown tables, PlantUML, etc.)
   - What entities/components are currently documented
   - The styling conventions used (naming, layout, grouping)

### Phase 2: Codebase Analysis

3. Analyze the codebase thoroughly based on what each diagram documents:

   **For Architecture Diagrams:**
   - Scan directory structure for services, modules, packages
   - Identify main entry points and their dependencies
   - Map service-to-service communication patterns
   - Identify external integrations (APIs, databases, queues)

   **For Database Schema Diagrams:**
   - Find all schema definitions (SQL files, ORM models, migrations)
   - Extract table names, columns, types, and constraints
   - Identify foreign key relationships
   - Find indexes and their purposes

   **For Call Flow / Sequence Diagrams:**
   - Trace function/method call chains
   - Identify async operations and event flows
   - Map API endpoint handlers to their dependencies
   - Document request/response patterns

   **For Component Diagrams:**
   - Find all component/class definitions
   - Map imports and dependencies between components
   - Identify interfaces and contracts
   - Document component hierarchies

   **For API Diagrams:**
   - Find all route/endpoint definitions
   - Extract HTTP methods, paths, parameters
   - Document request/response schemas
   - Identify authentication requirements

### Phase 3: Diff Analysis

4. Compare current diagram content against codebase findings:
   - Identify new entities that need to be added
   - Identify removed entities that should be deleted
   - Identify changed entities that need updating
   - Identify new relationships/connections
   - Identify removed relationships/connections

### Phase 4: Update Diagrams

5. Update each diagram file:
   - Preserve the existing format and styling
   - Add new elements in a style consistent with existing elements
   - Remove elements that no longer exist in the code
   - Update changed elements (renamed, modified attributes)
   - Add new relationships/arrows/connections
   - Remove stale relationships
   - Maintain visual organization and grouping

6. After updating each diagram, summarize:
   - What was added
   - What was removed
   - What was modified

7. **Verify ASCII art alignment:** After finishing all updates to ASCII art diagrams, carefully check that all box borders and lines are properly aligned. Add or remove spaces as needed to ensure:
   - All vertical lines (`│`) in a column are aligned
   - All horizontal box edges (`┌`, `┐`, `└`, `┘`, `─`) connect properly
   - Text content doesn't overflow box boundaries
   - Nested boxes maintain consistent margins

## Rules

### ASCII Diagram Alignment

Before completing any ASCII diagram edit, verify alignment by checking:
- All rows in a box have identical character width
- Vertical bars (`│`) align in the same column across rows
- No content overflows cell boundaries

### General Rules

- NEVER replace entire diagrams with new content - always update incrementally
- ALWAYS preserve the existing diagram format (Mermaid, ASCII, etc.)
- ALWAYS match the existing naming conventions and styling
- NEVER add elements that don't exist in the actual codebase
- NEVER remove elements unless they truly no longer exist in code
- When adding new elements, place them logically near related existing elements
- Maintain visual consistency (indentation, spacing, grouping)
- If a diagram type cannot be determined, ask the user before proceeding
- If no diagram files are found, inform the user and do not create new ones

## Example Updates

**Adding a new database table:**
```
Before:
┌──────────┐     ┌──────────┐
│  users   │────>│  orders  │
└──────────┘     └──────────┘

After (added payments table):
┌──────────┐     ┌──────────┐     ┌──────────┐
│  users   │────>│  orders  │────>│ payments │
└──────────┘     └──────────┘     └──────────┘
```

**Adding a new service to Mermaid:**
```mermaid
# Before
graph LR
    A[Frontend] --> B[API]
    B --> C[Database]

# After (added Cache service)
graph LR
    A[Frontend] --> B[API]
    B --> C[Database]
    B --> D[Cache]
```

## Output

After completing all updates, provide a summary:
- Total diagram files processed
- Files updated (with change summary)
- Files unchanged (already up to date)
- Any warnings or items requiring manual review
