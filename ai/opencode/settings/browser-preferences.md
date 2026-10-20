# Global OpenCode preferences

## Settings ownership

- Portable global settings and instructions are maintained in the dotfiles repository under `ai/opencode/settings/` and `ai/opencode/cli.json`.
- Change the tracked source first, then use `opencode_settings apply` to propagate it. Do not make local-only preference fixes unless the user explicitly wants a local override.
- Changes made by OpenCode remain local until the user explicitly imports selected keys with `opencode_settings import`. Never import credentials or machine-specific configuration into the public repository.

## Web search and browser preferences

- Use Orca's embedded browser for web searches by default, with Google as the default search engine (`https://www.google.com/search?q=<URL-encoded query>`).
- Load the `orca-cli` skill and its browser reference before controlling Orca browser tabs. Follow its executable-selection, workspace/page targeting, and snapshot rules.
- Do not invoke OpenCode's built-in `websearch` tool or ask the user to select a search provider. It is intentionally disabled.
- Use another search engine or browser only when the user requests it. If Orca or Google is unavailable or blocked, explain the blocker and ask before switching.
- Direct HTTP fetches of known URLs, including official documentation, remain appropriate; they do not require a search provider.
