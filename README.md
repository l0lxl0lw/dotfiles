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
| `claude` | Offers Homebrew `claude-code` and jq; initializes status-line settings and links the active hubs into `~/.claude` |
| `codex` | Offers Homebrew `codex`; initializes managed settings and links the active hubs into `~/.codex`; respects `CODEX_HOME` |
| `opencode` | Offers Homebrew `opencode`; links the active hubs into `~/.config/opencode` |
| `hubs` | Links every active hub into every installed tool at once, then lets Orca install its hooks and bundled skills for the agents it detects |
| `grok` | Configures an existing Grok CLI, respecting `GROK_HOME`; missing CLI is reported for manual installation because no verified package is registered |
| `private-config` | Optionally clones a user-supplied private Git URL into `~/dotfiles-private` |
| `life-memory` | Offers Python 3.12, isolated Basic Memory dependencies, vault/backup paths, selected-client hooks/MCP and optional launchd maintenance |

Homebrew is offered only when a missing selected dependency needs it. Existing
executables are reused. Declining a dependency skips the component. Ordinary
setup does not upgrade installed applications.

Setup does not transfer credentials. Launch selected assistants to sign in;
use `gh auth login` for GitHub workflows. Codex memory hooks require native
review/trust through `/hooks` in a fresh session.

## Select, inspect, update

```sh
./deploy.sh --only claude,codex,opencode,hubs
./deploy.sh --dry-run              # no downloads, writes, or prompts
./deploy.sh --doctor               # read-only executable/link inventory
git pull --ff-only                 # explicit repository update; resolve local conflicts yourself
./deploy.sh --update --only zsh,tmux,claude,codex
```

`--update` offers upgrades for selected Homebrew-managed applications and
fast-forward pulls for selected plugin repositories. Foreign repositories,
symlinked plugin locations and dirty plugin checkouts are preserved and reported.
Non-Homebrew application installations keep their native update mechanism.
Private repositories and dotfiles itself are not pulled by this command.

Shell startup performs **no downloads, application installation, repository pulls,
or AI synchronization**. It loads tracked `zsh/*.zsh` and then `zsh/*.zsh` from each
active hub (see [Hubs](#hubs)). Missing autosuggestions and AWS completion are safe.

Claude Code, Codex and OpenCode synchronize the active hubs when launched through
their shell wrappers; `hubs_sync` can also be run directly. Grok keeps its own
sync and SessionStart hook. Synchronization preserves foreign files; use the
installer to review collisions.

## Hubs

AI content does not live in this repository. It lives in *hubs*: repositories
that follow one layout and are listed, per machine, in
`${XDG_CONFIG_HOME:-~/.config}/dotfiles/hubs`, one path per line, `~` allowed,
`#` comments ignored. A work machine lists a personal hub and a work hub; a
personal machine lists one:

```
~/personal/zubot
~/work/azubot
```

A hub provides:

```
<hub>/
  AGENTS.md, CLAUDE.md     entry points when a session starts inside the hub
  persona/global.md        what every tool should know about this hub everywhere
  .agents/skills/<name>/   the skills; .claude/skills is a symlink to it
  agents/src/<name>.md     one worker definition (name, description, tier, access)
  .claude/agents/          committed render for Claude Code, plus Claude-only agents
  .codex/agents/           committed render for Codex
  .opencode/agents/        committed render for OpenCode
  tiers.json               default tier -> model map; see agents/README.md
  zsh/*.zsh                optional shell config
```

`hubs_sync [--dry-run] [--hubs PATH,PATH] [--codex-home DIR] [--tool claude|codex|opencode]...`
links each hub's skills into each tool, symlinks Claude agents, renders Codex and
OpenCode agents with the machine's `~/.config/dotfiles/tiers.json` overlay and
copies them in, and writes one managed block of every hub's `persona/global.md`
into `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and `~/.config/opencode/AGENTS.md`.
A hub listed later wins a name collision, and every override is printed.
`--dry-run` narrates instead of acting; `--hubs` and `--codex-home` serve a single
hub into a private Codex home (an unattended bot, say); `--tool` limits the run.

What the linker never touches: real directories (other installers' skills,
Codex's `.system/`, Orca's `~/.agents/skills`), symlinks that do not point into a
hub or a former root, Orca's hooks, and any instruction file with content but no
hubs markers. A hub path that does not exist is skipped with a warning and its
links are left alone, even if the hub was synced before (a rename or a move in
progress loses nothing). Hubs the linker has synced are remembered in
`~/.local/state/dotfiles/hubs-seen` so a hub *removed from the list* is cleaned
up. No hubs file at all means "not configured yet": nothing is linked or removed
and the tool launches stay silent; an empty file means "no hubs" and removes
every hub link. A hub whose agents fail to render keeps its previous generated
agents and the failure is reported.

`./deploy.sh --doctor` prints the hubs file, each hub as `ok`, `missing` or
`render drift`, per-tool counts of hub links and generated agents, and Orca's hook
status. Skills, agents and personas live only in the hubs; this repository keeps
just `ai/claude/hooks` (the status line) and `ai/codex/config.toml.managed`.

The development workflow (`/develop-prepare`, `/develop-deliver`) and every other
shared skill now ship from the personal hub; see that hub's
`.agents/skills/develop/README.md`.

Declining an AI component disables its automatic catalog sync using a small marker
under `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/disabled-sync/`. A successful
`--only TOOL` setup reenables it. Components excluded by `--only` are unchanged.
Existing linked resources remain installed; skipping is not an uninstall.

## GitHub profiles

`ghp <profile>` switches the active `gh` account, the global git author and git's
HTTPS credentials (routed through `gh`) together; `ghp` shows the active profile and
`ghp list` the configured ones. Profiles are machine-local, outside the repo, in
`~/.config/dotfiles/github-profiles` — see [zsh/github-profile.zsh](zsh/github-profile.zsh)
for the format. Log in each account once with `gh auth login`. The shell prompt and
the Claude status line show `gh:<profile>`, in red with the owning profile when the
current repo's git email belongs to a different one.

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
| `agents/` | The hub agent renderer and Codex model check; [agent format and tiers](agents/README.md) |
| `ai/claude/hooks/`, `ai/codex/config.toml.managed` | Status line and the Codex settings block the linker applies |
| `ai/grok/` | Grok resources (Grok support is slated for removal) |
| `ai/memory/` | Optional local Life vault integration; [setup and operations](ai/memory/README.md) |

To add an application, add `install/modules/<name>.sh` implementing
`install_component`, store its configuration beside the other tools, and use the
shared dependency/link/backup helpers. The wizard discovers the module without
dispatcher edits. Keep authentication and machine-specific data out of Git.

The `private-config` component clones an optional private repository to
`~/dotfiles-private`; list it in the hubs file to load it. Life memory defaults to `~/Documents/Life` on a new machine;
existing configured vaults are reused. Dropbox, Obsidian and an off-device backup
service are optional separate installations.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p '*test.py' -v
zsh zsh/tests/codex_repo_skills_test.zsh
zsh zsh/tests/agent_catalog_test.zsh
zsh zsh/tests/hubs_list_test.zsh
zsh zsh/tests/hubs_sync_test.zsh
```

Installer tests use temporary homes, paths containing spaces and stubbed package
installers. They cover fresh setup, reruns, backups/restoration, missing tools,
failures, skipped collisions, startup without optional tools and memory client
selection. Real Homebrew installations, upstream authentication and clean Intel/
Apple Silicon acceptance still need testing on those machines.
