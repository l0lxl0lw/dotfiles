# Installer modules

`deploy.sh` sources `lib.sh`; each selected module runs in a separate Bash process
with `set -euo pipefail`. Use syntax compatible with macOS Bash 3.2 (no associative
arrays). Modules are discovered by filename; the built-in order puts memory after
applications, and new modules follow automatically.

```bash
# install/modules/example.sh
install_component() {
  ensure_tool example verified-homebrew-package  # optional third arg: cask
  link_file "$ROOT/ai/example/settings" "$HOME/.example/settings"
}
```

Verify the upstream executable and installation package before registering it.
Do not put downloaded installer commands or package names in an `eval` string.
`ensure_tool` reuses an executable, asks before installation, and checks it became
available. It offers Homebrew bootstrap only when needed. `--update` offers a
Homebrew upgrade only if that package is installed by Homebrew.

## Shared helpers

- `ask QUESTION`: yes/no, default no; EOF aborts.
- `run COMMAND ARGS...`: displays the command; does not execute during dry-run.
- `link_file SOURCE DESTINATION`: no-op for a correct link; conflict choice and
  unique backup before replacement. Handles files, directories and broken links.
- `copy_file SOURCE DESTINATION`: like linking, but copies writable defaults;
  identical regular files are a no-op.
- `approve_change PATH`: consent/backup before a tool-specific mutation. Use only
  once you know a change is required. Does not itself change the target.
- `clone_plugin URL DESTINATION`: staged clone, preserving a failed installation's
  destination; existing repositories must match the URL. Updates are ff-only and
  reject dirty checkouts.
- `sync_ai NAME CONFIG_DIRECTORY`: initializes selected config, then invokes the
  existing Zsh synchronization adapter without interactive startup files.

`ROOT`, `HOME`, `DRY_RUN`, and `MODE` (`install`/`update`) are available. Always quote
paths. Every write/download must be guarded by `DRY_RUN` or routed through a helper.
Return 0 for success, 2 for skipped/manual work, other nonzero for failure; 130
cancels the entire wizard. Do not call the entire module in an `if`/`||` condition:
that disables Bash's implicit error handling inside the function.

The AI linker calls `install/link.sh` only with `DOTFILES_INSTALL=1`. Ordinary
application launches keep the noninteractive, foreign-file-preserving behavior.
The adapter uses existing sync functions as the single catalog source of truth;
it does not duplicate lists of skills/agents/commands. Config-specific merges
must validate before swapping files and return a failure or skipped result.

## New-module acceptance

Add an isolated-home test to `tests/install_test.py`: missing executable and
declined installation, successful fake installer, initial config, rerun without
extra writes, conflicting destination, and dry-run. Mock all network/package
commands. Update the root component table and the tool's README.

Do not store tokens, private URLs, absolute machine-specific paths, or generated
application state in the module or repository. A new module should not require
editing shell startup, the backup implementation, or unrelated application code.
