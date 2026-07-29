---
name: notion
description: Search, read, create, and manage pages and databases in your Notion workspace. Use when the user wants to interact with Notion content.
---

# Notion Workspace

Interact with your Notion workspace — search, read, create, update, and organize pages and databases.

## Available Operations

| Operation | Tool | Description |
|-----------|------|-------------|
| Search | `mcp__notion__notion-search` | Find pages, databases, or users across workspace and connected sources |
| Fetch | `mcp__notion__notion-fetch` | Read full content of a page or database by URL or ID |
| Create pages | `mcp__notion__notion-create-pages` | Create one or more pages (standalone, under a page, or in a database) |
| Update page | `mcp__notion__notion-update-page` | Update properties or content of an existing page |
| Create database | `mcp__notion__notion-create-database` | Create a new database with a property schema |
| Comment | `mcp__notion__notion-create-comment` | Add a comment to a page |
| Get comments | `mcp__notion__notion-get-comments` | Retrieve all comments on a page |
| Duplicate | `mcp__notion__notion-duplicate-page` | Duplicate a page (async — result may take a moment) |
| Move pages | `mcp__notion__notion-move-pages` | Move pages or databases to a new parent |
| Get teams | `mcp__notion__notion-get-teams` | List teamspaces in the workspace |
| Get users | `mcp__notion__notion-get-users` | List workspace members |

## Steps

### Phase 1: Understand Intent

1. Determine what the user wants to do with Notion:
   - **Find something** → search, then optionally fetch
   - **Read a page** → fetch by URL or ID
   - **Create content** → create pages or database
   - **Update content** → fetch first to get current state, then update
   - **Organize** → move, duplicate, or comment

### Phase 2: Search & Discover

2. When the user references Notion content without a direct URL or ID:
   - Use `notion-search` with a descriptive query
   - For user lookups, set `query_type: "user"`
   - For workspace content, use `query_type: "internal"` (default)
   - Use filters when the user specifies date ranges or creators
   - To search within a database, first `fetch` the database to get the `collection://` data source URL, then pass it as `data_source_url`

### Phase 3: Read & Analyze

3. Before modifying any page:
   - Always `fetch` the page first to see its current content and structure
   - For databases, `fetch` returns the schema and data source IDs needed for creating entries
   - Note the Notion-flavored Markdown format — fetch the spec at `notion://docs/enhanced-markdown-spec` if needed

### Phase 4: Create or Update

4. When creating pages:
   - Always include a `title` property
   - For database entries, match property names exactly from the fetched schema
   - Use the correct parent type (`page_id`, `database_id`, or `data_source_id`)
   - Omit parent to create a standalone private page

5. When updating pages:
   - Use `update_properties` to change property values
   - Use `replace_content` to replace all page content
   - Use `replace_content_range` to replace a specific section
   - Use `insert_content_after` to add content after a specific location
   - For `selection_with_ellipsis`, provide ~10 chars from start, an ellipsis, and ~10 chars from end

6. When creating databases:
   - Define the property schema with appropriate types
   - Supported types: title, rich_text, number, select, multi_select, date, people, checkbox, url, email, phone_number, formula, relation, rollup, status

### Phase 5: Report

7. After completing the operation:
   - Confirm what was done (page created, updated, etc.)
   - Provide the Notion URL so the user can view the result
   - If a page was duplicated, note that it completes asynchronously

## Rules

- ALWAYS fetch a page before updating it to understand current content and avoid overwriting
- ALWAYS fetch a database before creating entries to get the correct schema and data source IDs
- NEVER delete child pages or databases without explicit user confirmation — if `allow_deleting_content` is needed, show the list and ask first
- When searching, use one focused query per search call for best results
- For date properties, use the expanded format: `date:{property}:start`, `date:{property}:end`, `date:{property}:is_datetime`
- For checkbox properties, use `__YES__` / `__NO__` (not true/false)
- Properties named "id" or "url" must be prefixed with `userDefined:`
- When a user provides a Notion URL, extract the ID and use `fetch` directly instead of searching
- Keep page content in Notion-flavored Markdown format — fetch the spec from `notion://docs/enhanced-markdown-spec` when unsure about syntax
