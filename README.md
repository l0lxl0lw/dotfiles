# Dotfiles

Interactive macOS setup for Zsh, Vim, tmux, Spacemacs, and AI CLI integrations.
The installer offers each component separately and asks before installing missing
applications or replacing conflicting configuration.

## Fresh Mac

Install Apple's Command Line Tools if Git is not available:

```sh
xcode-select --install
# Finish Apple's installation dialog before continuing.
git clone https://github.com/l0lxl0lw/dotfiles.git ~/dotfiles
~/dotfiles/deploy.sh --dry-run
~/dotfiles/deploy.sh
```

Run as your normal user, not with `sudo`. Homebrew requests its own privileges if
needed. Both Apple Silicon and Intel Homebrew locations are recognized. Homebrew
and upstream applications determine which macOS releases they support; package
installation failures are reported rather than treated as success.

**Keep the clone at `~/dotfiles`.** Runtime hooks and documentation use that path;
the installer rejects other locations instead of producing broken integrations.
Git must be available to clone the repository. Bash, Zsh and curl ship with macOS;
Python and Node are not needed to start the wizard. Linux is not supported by it.

### What the wizard offers

| Component | Installation / configuration |
|---|---|
| `zsh` | Links `.zshrc` (respects `ZDOTDIR`), installs autosuggestions; does not change your login shell |
| `vim` | Links `.vimrc`; uses built-in features, without unused Pathogen downloads |
| `tmux` | Offers tmux; links config and installs TPM, sensible and yank |
| `emacs` | Offers Emacs and Spacemacs; copies a writable starter `.spacemacs`; first launch downloads Spacemacs packages |
| `claude` | Offers Homebrew `claude-code` and jq; initializes status-line settings and links skills/agents/hooks |
| `codex` | Offers Homebrew `codex`; initializes managed settings and links skills/instructions; respects `CODEX_HOME` |
| `grok` | Configures an existing Grok CLI, respecting `GROK_HOME`; missing CLI is reported for manual installation because no verified package is registered |
| `opencode` | Offers Homebrew `opencode`, Python and GitHub CLI; links its catalog under `XDG_CONFIG_HOME` |
| `private-config` | Optionally clones a user-supplied private Git URL into `~/dotfiles-private` |
| `life-memory` | Offers Python 3.12, isolated Basic Memory dependencies, vault/backup paths, selected-client hooks/MCP and optional launchd maintenance |

Homebrew is offered only when a missing selected dependency needs it. Existing
executables are reused. Declining a dependency skips the component. Ordinary
setup does not upgrade installed applications.

Setup does not transfer credentials. Launch selected assistants to sign in;
use `gh auth login` for GitHub workflows. Configure OpenCode models through its
native settings and the managed agent/command definitions. Quit and
restart OpenCode after changing its catalog. Codex memory hooks require native
review/trust through `/hooks` in a fresh session.

## Select, inspect, update

```sh
./deploy.sh --only codex,opencode
./deploy.sh --dry-run              # no downloads, writes, or prompts
./deploy.sh --doctor               # read-only executable/link inventory
git pull --ff-only                 # explicit repository update; resolve local conflicts yourself
./deploy.sh --update --only zsh,tmux,codex,opencode
```

`--update` offers upgrades for selected Homebrew-managed applications and
fast-forward pulls for selected plugin repositories. Foreign repositories,
symlinked plugin locations and dirty plugin checkouts are preserved and reported.
Non-Homebrew application installations keep their native update mechanism.
Private repositories and dotfiles itself are not pulled by this command.

Shell startup performs **no downloads, application installation, repository pulls,
or AI synchronization**. It loads tracked `zsh/*.zsh` and optional private
`~/dotfiles-private/zsh/*.zsh`. Missing autosuggestions and AWS completion are safe.

Claude catalog synchronization is explicit (`claude_merge_config`). Codex, Grok
and OpenCode synchronize managed resources when launched through their shell
wrappers. Grok also has a SessionStart sync hook. Normal synchronization preserves
foreign files; use the installer to review collisions. OpenCode's wrapper launches
the snapshot-based workflow described in [ai/opencode/README.md](ai/opencode/README.md).

Declining an AI component disables its automatic catalog sync using a small marker
under `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/disabled-sync/`. A successful
`--only TOOL` setup reenables it. Components excluded by `--only` are unchanged.
Existing linked resources remain installed; skipping is not an uninstall.

## Conflicts and backups

Already-correct links are left alone. Before a conflicting file, directory or
symlink changes, choose:

- **Back up first** (Enter): preserve the original, then apply the change.
- **Skip**: leave that target unchanged; the summary reports action needed.
- **No backup**: explicitly authorize replacement without saving the original.
- **Cancel**: stop the wizard.

Backups preserve symlinks, including dangling links, without copying their targets.
They live in `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/backups/<ID>/` with a
`manifest.tsv` mapping originals to destinations. Each backup directory is private
to the user; names are unique and previous backups are never reused. A run may
produce multiple IDs as components and individual AI resources are processed.

```sh
./deploy.sh --restore BACKUP_ID
```

Restore asks per item and backs up the current destination first, so later edits
are preserved. It restores recorded configuration only; it does not uninstall
packages, delete newly created files, or undo external installer effects. The
installer is resumable rather than an all-or-nothing transaction. Stop concurrent
configuration editing while deploying/restoring.

Settings JSON/TOML is merged using each tool's existing adapter. Invalid Codex
candidates are rejected by its CLI parser; an existing unrelated `[tui]` table
may require manual reconciliation. Settings symlinks and symlinked parent
directories require manual reconciliation rather than writes through them.

Life memory has a separate content-addressed backup mechanism for changed JSON
settings and its launchd definition under `~/.local/state/life-memory/config-backups`;
the wizard obtains consent before running that setup. Native MCP registrations
also prompt before changing existing client configuration. Memory setup refuses
an existing OpenCode JSONC file rather than guessing how to merge comments.

All mutating setup is interactive; there is no blanket `--yes` switch. EOF does
not authorize replacement. Failed components produce a nonzero final status;
declined components and unresolved collisions appear as “skipped / action needed”.
Review the summary, fix a failed component, and rerun with `--only`.

## Layout and adding integrations

| Path | Purpose |
|---|---|
| `install/` | Wizard helpers and auto-discovered component modules; [extension contract](install/README.md) |
| `zsh/` | Shell startup, functions, aliases and optional completions |
| `vim/`, `tmux/`, `emacs/` | Editor/multiplexer settings |
| `ai/claude/`, `ai/codex/`, `ai/grok/` | Tool-specific resources and documentation |
| `ai/shared/` | Canonical cross-tool skills, flattened by the sync helpers |
| `ai/opencode/` | OpenCode agents, commands, TUI and workflow runtime |
| `ai/memory/` | Optional local Life vault integration; [setup and operations](ai/memory/README.md) |

To add an application, add `install/modules/<name>.sh` implementing
`install_component`, store its configuration beside the other tools, and use the
shared dependency/link/backup helpers. The wizard discovers the module without
dispatcher edits. Keep authentication and machine-specific data out of Git.

The optional private repository supplies shell configuration and
`opencode/config.json` (private skill paths/tracking). It is not required for the
public setup to work. Life memory defaults to `~/Documents/Life` on a new machine;
existing configured vaults are reused. Dropbox, Obsidian and an off-device backup
service are optional separate installations.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p '*test.py' -v
zsh zsh/tests/opencode_config_test.zsh
zsh zsh/tests/codex_repo_skills_test.zsh
```

Installer tests use temporary homes, paths containing spaces and stubbed package
installers. They cover fresh setup, reruns, backups/restoration, missing tools,
failures, skipped collisions, startup without optional tools and memory client
selection. Real Homebrew installations, upstream authentication and clean Intel/
Apple Silicon acceptance still need testing on those machines.
