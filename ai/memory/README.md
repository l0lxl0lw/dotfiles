# Life memory

One local Markdown vault shared by Claude Code, Codex and OpenCode. Obsidian is an optional
editor; it does not need to be installed or running for capture and retrieval. Code and instructions
are tracked here; personal notes, transcripts, client registrations and runtime state stay
outside dotfiles.

## Installed layout

- Vault: `vault` in `~/.config/life-memory/config.json` (the installer reuses this path)
- Default vault for a new setup: `~/Documents/Life`; existing configured vaults are reused
- Config: `~/.config/life-memory/config.json`
- Python/Basic Memory: `~/.local/share/life-memory-venv/bin/`
- State/queue/config backups/note history: `~/.local/state/life-memory/`
- Operational structured records: `raw_directory` in local config (legacy default: vault `.memory/raw/`)
- Optional compressed original/snapshot archives: `raw_archive` in local config
- Archive catalog: vault `.memory/archive-manifest.json`, mirrored to the archive root
- Readable conversation projections: vault `Sources/Conversations/`
- Daily ZIP backups (14 retained): configured `backup` folder; may be a Dropbox folder
- LaunchAgent: `~/Library/LaunchAgents/local.life-memory.maintenance.plist`

The portable skill is `../shared/skills/remember/remember-life/SKILL.md`. Claude/Codex
use their normal skill symlinks. OpenCode registers that particular directory through
native `skills.paths`, since the workflow launcher disables external skill discovery.
Its global JSON config also registers the plugin, vault reference, and MCP connection.

## Behavior

### Shared OpenCode MCP

OpenCode connects to `http://127.0.0.1:8766/mcp`. The Life plugin's config hook runs
`shared_mcp.py` before MCP initialization. It verifies the endpoint's MCP identity,
or serializes startup using a file lock and asks launchd to start
`local.life-memory.mcp`. Five OpenCode instances share one Basic Memory process.
The service is constrained to project `life`, forces local routing, and binds only
to loopback. Its LaunchAgent is registered lazily, with `RunAtLoad=false`.

The service stays available when a client closes. After a stop/crash, the next
OpenCode initialization starts it again; existing clients may need reconnecting.
There is no periodic health monitor. Logs are `shared-mcp.log` and
`shared-mcp-errors.log` in the configured state directory. An unrelated HTTP
service on the port is rejected rather than used. Startup waits up to 60 seconds
after requesting launchd startup; simultaneous callers wait on the startup lock.

Restart existing OpenCode instances after switching configuration: their old
stdio servers cannot be shared and exit with their owning clients. Claude/Codex
registrations are separate. Pure/plugin-disabled OpenCode can connect while the
shared service is up, but cannot perform the plugin's on-demand startup.

```sh
~/.local/share/life-memory-venv/bin/python ~/dotfiles/ai/memory/shared_mcp.py
~/.local/share/life-memory-venv/bin/python ~/dotfiles/ai/memory/smoke_shared_mcp.py
launchctl print gui/$(id -u)/local.life-memory.mcp
```

`memory.py hook claude|codex` reads JSON stdin from native lifecycle events. It preserves
unique structured transcript records, including tool data, and projects user/assistant
text to Markdown. A partial final JSONL record is deferred. Previously captured records
survive client compaction. The readable OpenCode projection uses the latest revision of
each message, while the raw archive retains prior versions. External attachments are not
copied. Original structured records aren't byte-identical copies of the native file.

OpenCode `info.summary.diffs` is **derived workspace metadata**, not message/tool
content. Both the plugin and receiver exclude it. Capturing a diff of the capture
file itself otherwise creates a recursive growth loop. Summary text, message
revisions, tool arguments/results, and other record fields remain preserved.
The receiver guard also protects already-running clients until their plugin reloads.

SessionStart/UserPromptSubmit adds a short orientation. Stop requests at most one memory
checkpoint per observed user-input revision and avoids recursive stop-hook blocking.
Agents use normal model access for synthesis, cross-links, and weekly reviews. No separate
unattended LLM service is installed. Pending synthesis is visible rather than reported as
successful memory. OpenCode uses instructions rather than a forced continuation loop.

`life-memory.js` captures OpenCode user/completed-assistant messages, idle events and
pre-compaction snapshots through the SDK. Captures serialize per session. Startup and
compaction reminders help the assistant maintain summaries. A process killed before an
event can still lose its uncaptured tail; this is not a guarantee of zero-loss journaling.

The five-minute maintenance job catches up **registered** Claude/Codex transcript paths,
refreshes full-text indexing, and creates one daily local backup. It doesn't bulk-import
old chats or crawl unrelated projects. OpenCode capture requires its plugin to be active.
Backup copies are local until the configured cloud client finishes uploading them;
writing into a Dropbox folder does not itself verify off-device durability.

Runtime `read-note`/`write-note` implement optimistic concurrency (expected SHA-256 plus a
shared lock) for agent writes. Do not bypass this with MCP writes or direct edits to
synthesized notes. Manual Obsidian edits aren't lock-coordinated; agents must reread before
writing and avoid concurrent manual editing of the same note. Raw sources are rejected
by the synthesized-note writer. Earlier note bytes are retained in note-history.

## Setup on another Mac

The guided route is `~/dotfiles/deploy.sh --only life-memory`. It offers Python
3.12 and an isolated Basic Memory environment, asks for selected installed clients,
vault and daily-backup paths, and offers native MCP registration and launchd.
It obtains consent before setup; changed JSON settings and launchd definitions get
content-addressed backups under `~/.local/state/life-memory/config-backups`.
Those backups are separate from `deploy.sh --restore`.

For manual setup, Python 3.12+ and installed/authenticated assistant CLIs are
required. Use `--clients claude,codex,opencode` to select integrations and
`--vault /absolute/path` / `--backup /absolute/path` to choose storage. A fresh setup
defaults to `~/Documents/Life`; an existing vault cannot be relocated through setup.
Dropbox is optional; install/sync it first if selecting a Dropbox path.
OpenCode JSONC and settings symlinks require manual reconciliation; setup fails
before creating notes/hooks in those cases. `XDG_CONFIG_HOME` and `CODEX_HOME`
are respected for the corresponding clients.

```sh
python3.12 -m venv ~/.local/share/life-memory-venv
~/.local/share/life-memory-venv/bin/pip install --pre 'basic-memory==0.23.2'
python3.12 ~/dotfiles/ai/memory/setup.py --clients claude,codex,opencode --vault "$HOME/Documents/Life"
BASIC_MEMORY_NO_PROMOS=1 ~/.local/share/life-memory-venv/bin/basic-memory project add life "$HOME/Documents/Life" --local --default
BASIC_MEMORY_NO_PROMOS=1 ~/.local/share/life-memory-venv/bin/basic-memory config set auto_update false
BASIC_MEMORY_NO_PROMOS=1 ~/.local/share/life-memory-venv/bin/basic-memory config set ensure_frontmatter_on_sync false
```

`setup.py` preserves seed edits and unrelated JSON settings, snapshots changed configs,
and refuses skill collisions. It registers Claude/Codex hooks and OpenCode fully. Register
Basic Memory with Claude and Codex separately using their native `mcp add`/`add-json` commands:
command is the absolute `basic-memory` binary, args are `mcp --project life`, environment is
`BASIC_MEMORY_NO_PROMOS=1` and `BASIC_MEMORY_FORCE_LOCAL=true`. This avoids reading/writing
their mixed credential files ourselves. Claude's variadic `--env` parser is easiest avoided
using `mcp add-json --scope user`.

The Basic Memory core is pinned to 0.23.2 (its required FastMCP dependency is prerelease).
The installed dependency versions on this Mac are recorded in local state
`requirements-installed.txt`; the repository does not lock all transitive dependencies.
`ensure_frontmatter_on_sync=false` prevents indexing from rewriting source files.

Load launchd, then quit/restart assistants:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.life-memory.maintenance.plist
```

In Codex, use `/hooks` to review/trust the installed definitions. Do not fake or bypass
native hook trust. Open the configured `vault` path as a folder vault in Obsidian.

The vault can live in a Dropbox folder. Update the runtime `vault` setting,
Basic Memory project path (`basic-memory project move life NEW_PATH`), OpenCode
reference and Obsidian vault registration together. Keep the central vault available
offline for local indexing. Update saved assistant workspace/session directories and
current vault guidance too, then verify capture and retrieval before removing an old
compatibility symlink. Restart clients that cached the previous path. Git is optional:
do not copy `.git` or its LFS cache into the
Dropbox vault. Cloud folder synchronization is separate from dated backups and does
not supply the runtime lock across different computers; avoid simultaneous agent
writes from multiple Macs.

## Operations

```sh
python3.12 ~/dotfiles/ai/memory/memory.py status
python3.12 ~/dotfiles/ai/memory/memory.py pending
python3.12 ~/dotfiles/ai/memory/memory.py doctor
python3.12 ~/dotfiles/ai/memory/memory.py maintenance
python3.12 ~/dotfiles/ai/memory/memory.py backup
python3.12 ~/dotfiles/ai/memory/memory.py migrate-raw
python3.12 ~/dotfiles/ai/memory/memory.py archive-raw
python3.12 ~/dotfiles/ai/memory/memory.py archive-list [SESSION_KEY]
python3.12 ~/dotfiles/ai/memory/memory.py archive-verify
python3.12 ~/dotfiles/ai/memory/memory.py restore-raw FULL_SHA256 /absolute/new/file.jsonl
python3.12 ~/dotfiles/ai/memory/import_video.py VIDEO_ID
```

`doctor` validates file-level wikilink targets and identifies Wiki orphans. Heading/block
references, aliases, semantic relevance and contradictory claims need agent review. Source
quotations and templates are excluded from asserted graph edges. Video import stores the
full original VTT and metadata plus a timestamped readable projection; caption quality is
explicit. Existing archived videos aren't overwritten on rerun.

`backup` refreshes today's snapshot immediately, useful after a bulk import; normal
maintenance creates one snapshot per day without replacing that day's existing copy.

## Raw evidence storage and migration

For a lightweight Git vault, configure `raw_directory` **outside** the vault
(for example, a `raw` directory under the configured runtime state) and `raw_archive`
to a local, writable archive root (optionally inside Dropbox). Keep the live notes
at the same vault path. Never put credentials in these settings.

`migrate-raw` runs under the shared capture lock. For each legacy `.memory/raw/*.jsonl`
it creates a content-addressed gzip of the **exact original bytes**, decompresses it
and verifies SHA-256 and byte count, publishes catalogs, writes deduplicated
operational records with derived OpenCode diffs removed, updates session state,
then removes the redundant legacy file. Resumed sessions auto-migrate if necessary.
Existing operational records are merged rather than overwritten on a retry.
Unchanged messages and readable conversation text are retained; old source headers
may still name the historical raw path, whose basename resolves via `archive-list`.

`archive-raw` writes immutable, content-addressed **per-session snapshots**, not a
single growing ZIP. Identical bytes reuse an existing archive. Changed snapshots
are retained without automatic deletion; archive growth/retention remains explicit.
Daily backup invokes this before packaging the vault. It includes readable notes,
transcripts and the catalog, excludes `.git`, Obsidian cache and separately archived
raw data, then checks the ZIP CRC. Large ordinary attachments remain in the ZIP.
Raw originals/snapshots live beside the ZIPs, not inside them. Keep both for recovery.

`archive-list` provides session keys, checksums, kinds, relative paths and sizes.
`restore-raw` accepts a full checksum and a new absolute destination, verifies the
archive, refuses overwrite, and verifies the restored bytes. Normal recall searches
local Markdown; raw archives are for targeted evidence recovery, not routine search.
On a replacement machine, restore the vault and archive root, configure their paths,
install the runtime, and rebuild the disposable search index. Operational raw files
can be restored from the latest `operational-snapshot` entries if needed.

Remove legacy raw paths from the vault Git index with `git rm -r --cached --
.memory/raw/`, ignore that directory, and remove its LFS attribute only after archive
verification. Existing Git/LFS history remains intact. Do not rewrite published
history or remove remote objects as part of routine migration. A verified LFS prune
can reclaim eligible local cached objects separately.

Pause using `enabled: false` in local config and restart clients, or launch one process
with `LIFE_MEMORY_DISABLED=1`. That flag also needs to be set on a long-running server
hosting the session. Pausing does not delete existing records or disable read access.

To uninstall wiring: unload the LaunchAgent; remove only commands containing this runtime
from Claude/Codex hooks; remove the `life-memory` MCP registrations, OpenCode plugin/reference/
skill-path entries, and skill symlinks. Keep the vault and state until explicitly unwanted.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.local/share/life-memory-venv/bin/python -m unittest discover -s ai/memory -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3.12 ai/memory/smoke_opencode.py
node --check ai/memory/life-memory.js
```

The live OpenCode smoke uses the installed server/plugin with an isolated temporary vault
and `noReply`; it tests actual event capture with **zero model calls**. Unit tests cover
duplicate capture, compaction preservation, revised messages, partial records, stale writes,
path bounds, pause, graph targets and stop-loop prevention. Native hook activation and
agent-authored recall/checkpoints must also be checked in newly started client sessions.

Design sources: [Basic Memory](https://github.com/basicmachines-co/basic-memory),
[Claude hooks](https://code.claude.com/docs/en/hooks),
[Codex hooks](https://developers.openai.com/codex/hooks),
[OpenCode plugins](https://opencode.ai/docs/plugins/). The three user-supplied videos and
their evidence-linked synthesis are in the local vault, not the public repo.

## Granola meeting import

The official remote MCP endpoint is `https://mcp.granola.ai/mcp`, registered as
`granola` in local OpenCode config. Browser authorization is handled by
`opencode mcp auth granola`. No Granola API key or copied app credentials are used.

Use the installed venv Python for the following tools:

- `granola_mcp.py tools`: discover the server's actual input schemas.
- `granola_mcp.py get_account_info --save account`: verify the active workspace.
- `granola_mcp.py list_meetings --args '<JSON matching discovered schema>' --save meeting-inventory`:
  explicitly select the desired date and involvement scope.
- `granola_import.py inventory`: parse the returned inventory and verify its count.
- `granola_import.py fetch`: fetch notes in batches of at most 10, then individual transcripts.
  `--refresh` refetches instead of reusing staging. Tool errors and missing transcripts remain visible.
- Review source notes and write `~/.local/state/life-memory/granola/synthesis.json` with
  meeting-specific `title`, `kind`, `gist`, `project`, `organizations`, `people`, and `topics`,
  plus descriptions under `projects` and `topics`. Keep private content out of this repository.
- `granola_publish.py`: verify inventory/notes/synthesis ID agreement, preserve original
  source revisions, and create linked meeting/project/person/organization/concept notes.
  Repeated publication keeps existing meeting text and human edits, appending new source
  revisions when necessary. It does not silently regenerate stale summaries; review them
  with the memory skill after a source refresh.

The bridge reads only the exact `granola` grant from OpenCode's private OAuth store, checks
its server URL and expiry, and sends the token only to the official server. It never prints
or copies credentials. Expiry requires native reauthentication; there is no custom refresh
token logic. Responses live in private staging, and sources in vault `Sources/Granola/`.

Meeting summaries reflect source notes, not an independent verification of everything in
the transcript. Source-provided speaker labels are preserved; a microphone channel does
not prove speaker identity. Unknown follow-up completion remains unknown. The import is
scoped to the active workspace and its accessible results; it does not prove all historical
meetings were available. No periodic Granola synchronization is installed.

## Layered, offline recall

Use the venv Python (includes PyYAML) for `recall.py` and `granola_layers.py`.
The protocol is in [retrieval-guide.md](retrieval-guide.md), also seeded into the vault as
`System/Retrieval guide.md` and required by the shared memory skill.

```sh
~/.local/share/life-memory-venv/bin/python ai/memory/recall.py search "question or keywords"
~/.local/share/life-memory-venv/bin/python ai/memory/recall.py read "Wiki/Projects/Job search.md"
~/.local/share/life-memory-venv/bin/python ai/memory/recall.py context "Wiki/Projects/Job search.md"
~/.local/share/life-memory-venv/bin/python ai/memory/recall.py search "precise evidence" --scope transcript
~/.local/share/life-memory-venv/bin/python ai/memory/granola_layers.py
```

Local recall defaults to canonical/meeting summaries, with section menus and bounded
reads; original outlines, transcripts, and session logs require explicit scope expansion.
It uses a disposable SQLite FTS index in private state, refreshes changed files on search,
and makes no network or model calls. Semantic/hybrid Basic Memory search remains available
for paraphrases, filtered by `retrieval_layer` where appropriate. Exact local context
resolution refuses fuzzy substitutions. Search results require evidence verification.

`granola_layers.py` reconciles existing meeting IDs against staged Granola responses,
archives full transcripts, verifies every projected paragraph, and embeds the complete
original outline as actual text at the bottom of each meeting. The gist and discussion
stay above the source detail. It preserves source revisions and human writing; edits to
managed blocks cause a conflict instead of being overwritten. A changed source revision
marks synthesis as needing review. Missing/unavailable transcripts prevent a completeness
claim; resolve or document the gap before finishing the import.

For an updated inventory, save a scoped `list_meetings` response and pass its filename stem
to `granola_import.py inventory --inventory <stem>` or `fetch --inventory <stem>`.
Fetch stores refreshed notes by meeting ID, avoiding stale positional batches. Review and
update private synthesis before `granola_publish.py`; it now finishes with layered
publication. No transcript/outline retrieval from Granola is needed for normal recall
after a successful import. Rerun the local publisher to verify source completeness.

`verify_retrieval.py` checks archived transcript equality, inline outline completeness,
and file/heading/block citations. Pass `--cases <private-json>` for source-ranking and
support-term regression cases; keep personal queries and expected notes in private state.
These checks establish local completeness and tested retrieval behavior, not universal
answer accuracy. Use explicit source review for uncertain or conflicting claims.
