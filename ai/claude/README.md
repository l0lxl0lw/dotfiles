# Claude Config

Global Claude Code configuration — custom skills and agents synced across machines.

> **Lives in**: [`~/dotfiles/ai/claude`](https://github.com/l0lxl0lw/dotfiles). The `claude_merge_config` zsh function in `~/dotfiles/zsh/functions.zsh` symlinks this directory into `~/.claude/`. Formerly the standalone `l0lxl0lw/claude-config` repo, merged into dotfiles in July 2026.

## Structure

```
dotfiles/ai/claude/
├── CLAUDE.md              # Guidance when working in this directory
├── skills/                # Claude-specific skill overrides, if needed
├── agents/                # Specialized AI agent personas
│   ├── architecture/      # Architect agents (system, backend, frontend)
│   ├── communication/     # Learning guide, technical writer
│   ├── engineering/       # Executor, performance, refactoring
│   ├── planning/          # Analyst, planner, requirements
│   ├── research/          # Deep research, tech stack
│   └── review/            # Critic, security engineer
└── prompts/               # System prompts collection (reference)
    ├── Anthropic/ Google/ OpenAI/
    └── Perplexity/ Proton/ xAI/ Misc/

dotfiles/ai/shared/
└── skills/
    ├── community/         # Skills from individual repos
    ├── git/               # Custom git workflow skills
    ├── impeccable/        # Design skills from pbakaus/impeccable
    ├── integrations/      # Custom integration skills
    ├── omc/               # Planning skills from oh-my-claudecode
    └── utilities/         # Custom utility skills
```

`claude_merge_config` imports both `ai/claude/skills` and `ai/shared/skills`, flattening each
skill directory into `~/.claude/skills/<name>`. Put new portable skills in `ai/shared/skills`;
use `ai/claude/skills` only for Claude-specific overrides. gstack installs its own skills
separately into `~/.claude/skills` as real directories. They aren't tracked here;
`claude_merge_config` leaves them alone.

## Status line

`hooks/statusline.sh` renders a single dot-separated line, deliberately kept in lockstep
with the Codex status line in [`../codex/config.toml.managed`](../codex/config.toml.managed):

```
~/dotfiles · dotfiles · main* · Context 29% used · 5h 91% left · weekly 61% left · Opus 5 xhigh
```

Order is location first (what changes most often), model last. Codex's status line is a
fixed list of item ids, so it is the constrained side — it cannot render progress bars, a
second line, a different separator, or the dirty marker. This script stays inside what
Codex can express and only adds what Codex silently omits.

**The line is flat on purpose.** Every item is `label value`, separated by ` · `, nested
nowhere. That uniformity is the thing that makes it scannable: the eye tracks one separator
and never switches parsing modes. Reset countdowns — `5h 91% left (↻ 3.7h)` — broke it in
three of seven items, and put two different h-quantities inside one item. On identical input
they cost 29 of the line's 130 visible characters and 3 of its 8 numeric tokens; digits
force a fixation each, so that is the part that actually hurt. Removed, along with the
`(1M context)` qualifier on the model name — the line is now 101 characters and 5 numbers,
against Codex's 86 and 3. Put a countdown in `/usage`, not here.

**Two colour groups, separated by chroma.** Saturated green/gold/blue mark *where you are*
(dir, repo, branch), following Codex. The muted green→red scale marks *how heavy things are*
(usage items and effort). Dim grey is separators; the model is bold and uncoloured.

Green and yellow therefore appear in both groups, which is only safe because the groups sit
at different saturations — the eye separates by intensity before hue. Codex doesn't have
this problem: its quota renders pink, so it has no green or yellow in its data channel and
can spend them freely on location. **Don't dull a location colour toward the data scale.**
That collapses the separation, and a green path starts reading as "quota healthy" — exactly
what the old green branch did, back when it was byte-identical to the green `pct_color`
returns below 40%.

**Usage items are coloured whole**, not as a dim label around a bright number: `Context 12%
used` is one green band. Colouring only the digit left it an isolated bright dot with
nothing tying it to its label, so the eye had to travel back to read what it meant.

**The scale is muted, and deliberately not the stock Dracula neons.** A whole item in
`#50FA7B` is a wall of the brightest thing on screen, and green — the resting state — is
what you look at ~90% of the time, so it has to recede. Saturation rises with severity
instead: green is nearly grey-green, red stays hot enough to alarm. Don't "fix" green to
match red's intensity; the gradient is the signal.

**Model and effort mirror Codex's `model-with-reasoning`** — `Opus 5 xhigh`, from
`.effort.level`. Effort is coloured on the *same* `pct_color` scale rather than a second
palette (`low` green → `medium` yellow → `high` orange → `xhigh`/`max` red, unknown dim):
higher effort burns quota faster, so it answers the same "how hot is this" question as the
percentages, and one source of truth keeps the two from drifting. The numbers passed to
`pct_color` in `effort_color` are just indexes into the scale, not percentages.

The status line JSON also carries `.fast_mode`, `.thinking.enabled`, `.output_style.name`
and `.cost.total_cost_usd` if any of those are ever wanted; capture the full payload by
teeing stdin at the top of the script.

**"used" vs "left" is intentional.** Context is a ceiling you fill, so it reads as *used*
and a high number is bad. Quotas are a budget you spend down, so they read as *left* and a
**low** number is bad. Codex words them the same way and offers no way to change it. Note
`pct_color` is fed the *consumed* percentage in both cases, so `8% left` renders red rather
than green — changing one without the other inverts the colour scale.

Change the order or items in both files together, or they drift.

## Skills

### Core

| Skill | Description | Model Invocable |
|-------|-------------|-----------------|
| `/git-push-to-main` | On the default branch: commit + push directly to remote | No |
| `/git-pr-from-main` | On the default branch: wrap changes into a feature branch with one commit and open a PR | No |
| `/git-sync-main-and-commit` | On a feature branch: pull latest main, merge it in, resolve conflicts, commit & push | No |
| `/git-commit-local-changes` | Analyze uncommitted changes and create a commit (no push, no PR) | No |
| `/git-explain-diff` | Explain the uncommitted working tree — staged, unstaged and untracked — grouped by behavioral change. Read-only | Yes |
| `/git-explain-branch` | Explain what this branch changes vs the default branch, with a contract/migration/collision risk pass. Read-only | Yes |
| `/make-html` | Generate standalone HTML documents (Dracula theme, 20 example templates) | Yes |
| `/readme` | Read README in current directory and execute instructions | Yes |
| `/update-diagram` | Scan codebase and update existing diagram files | Yes |
| `/notion` | Search, read, create, and manage Notion workspace content | Yes |
| `/elevenlabs` | Generate speech, sound effects, music, clone voices, transcribe audio, manage AI agents | Yes |
| `/remotion` | Best practices for Remotion video creation in React | Yes |
| `/humanizer` | Remove signs of AI-generated writing from text | Yes |
| `/load-memory` | Restore working memory from MEMORY.md at session start | Yes |
| `/save-memory` | Save working memory from the current session into MEMORY.md | Yes |
| `/plan` | Strategic planning with optional interview workflow | Yes |
| `/ralph` | Self-referential loop until task completion with configurable reviewer | Yes |
| `/ralplan` | Iterative planning with Planner, Architect, and Critic agents | Yes |
| `/excalidraw-diagram-generator` | Generate Excalidraw diagrams from natural language descriptions | Yes |

### Frontend Design — [Impeccable](https://github.com/pbakaus/impeccable)

Design-focused skills for building polished, production-grade interfaces.

| Skill | Description |
|-------|-------------|
| `/frontend-design` | Create distinctive frontend interfaces with high design quality (includes 7 reference docs) |
| `/adapt` | Adapt designs across screen sizes, devices, and platforms |
| `/animate` | Enhance features with purposeful animations and micro-interactions |
| `/arrange` | Improve layout, spacing, and visual rhythm |
| `/audit` | Comprehensive interface quality audit with severity ratings |
| `/bolder` | Amplify safe designs to be more visually impactful |
| `/clarify` | Improve UX copy, error messages, and microcopy |
| `/colorize` | Add strategic color to monochromatic interfaces |
| `/critique` | Evaluate design effectiveness with actionable UX feedback |
| `/delight` | Add moments of joy and personality to interfaces |
| `/distill` | Strip designs to their essence, removing unnecessary complexity |
| `/extract` | Extract reusable components and design tokens into a design system |
| `/harden` | Improve resilience: error handling, i18n, text overflow, edge cases |
| `/normalize` | Normalize design to match your design system |
| `/onboard` | Design onboarding flows, empty states, and first-time experiences |
| `/optimize` | Improve interface performance: loading, rendering, animations, bundle size |
| `/overdrive` | Push interfaces past conventional limits with ambitious implementations |
| `/polish` | Final quality pass — alignment, spacing, consistency, and details |
| `/quieter` | Tone down overly bold or visually aggressive designs |
| `/teach-impeccable` | One-time setup to gather and persist design context for your project |
| `/typeset` | Improve typography: font choices, hierarchy, sizing, and readability |

### gstack — [l0lxl0lw/gstack](https://github.com/l0lxl0lw/gstack)

Browser automation, QA, planning reviews, shipping workflow, and safety guardrails. Requires the gstack toolchain installed at `~/.hermes/skills/gstack/` (skills invoke binaries from there).

**Not tracked in this repo** — gstack installs these itself as real directories under `~/.claude/skills`. Listed here for reference only. They were vendored here once and removed in commit `281e58a`.

| Skill | Description |
|-------|-------------|
| `/autoplan` | Run the full CEO/design/eng/DX review pipeline sequentially with auto-decisions |
| `/benchmark` | Performance regression detection: page load, Core Web Vitals, bundle size |
| `/browse` | Fast headless browser for QA, screenshots, state diffs, and dogfooding |
| `/canary` | Post-deploy monitoring: watches the live app for errors and regressions |
| `/careful` | Warn before destructive commands (rm -rf, DROP TABLE, force-push, etc.) |
| `/checkpoint` | Save and resume working state across sessions and branch switches |
| `/codex` | OpenAI Codex CLI wrapper: code review, adversarial challenge, consult |
| `/connect-chrome` | Alias for `/open-gstack-browser` — launch AI-controlled Chromium |
| `/cso` | Chief Security Officer audit: secrets, supply chain, CI/CD, OWASP, STRIDE |
| `/design-consultation` | Build a design system from scratch; create `DESIGN.md` source of truth |
| `/design-html` | Generate production-quality Pretext-native HTML/CSS from approved designs |
| `/design-review` | Designer's eye QA on a live site — finds and fixes visual issues |
| `/design-shotgun` | Generate multiple AI design variants and iterate with structured feedback |
| `/devex-review` | Live DX audit: navigates docs, times TTHW, scorecard with evidence |
| `/document-release` | Post-ship docs update: README, ARCHITECTURE, CHANGELOG, TODOS |
| `/freeze` | Restrict edits to a specific directory for the session |
| `/gstack-upgrade` | Upgrade gstack to the latest version |
| `/guard` | Full safety mode: `/careful` + `/freeze` combined |
| `/health` | Code quality dashboard: type check, lint, tests, dead code — composite score |
| `/investigate` | Systematic debugging: investigate → analyze → hypothesize → implement |
| `/land-and-deploy` | Merge PR, wait for CI and deploy, verify production health |
| `/learn` | Review, search, prune, and export learnings across sessions |
| `/office-hours` | YC-style forcing questions / brainstorming for new product ideas |
| `/open-gstack-browser` | Launch GStack Browser — AI-controlled Chromium with sidebar extension |
| `/pair-agent` | Pair a remote AI agent with your browser via scoped access keys |
| `/plan-ceo-review` | CEO/founder-mode plan review: scope expansion and 10-star product thinking |
| `/plan-design-review` | Designer's eye plan review — rates and improves design dimensions |
| `/plan-devex-review` | Interactive DX plan review: personas, benchmarks, magical moments |
| `/plan-eng-review` | Eng-manager plan review: architecture, data flow, edge cases, perf |
| `/qa` | Systematic QA testing that also fixes bugs found (commit per fix) |
| `/qa-only` | Report-only QA testing — structured bug report, no code changes |
| `/retro` | Weekly engineering retrospective with commit history and trends |
| `/review` | Pre-landing PR review: SQL safety, LLM trust, side effects |
| `/setup-browser-cookies` | Import cookies from your real browser into the headless session |
| `/setup-deploy` | Configure deployment settings for `/land-and-deploy` |
| `/ship` | Ship workflow: tests, VERSION bump, CHANGELOG, commit, push, open PR |
| `/unfreeze` | Clear the edit boundary set by `/freeze` |

## Agents

Specialized AI agent personas that provide focused expertise for different development tasks.

### Architecture & Planning

| Agent | Purpose |
|-------|---------|
| `tech-stack-researcher` | Technology choice recommendations with trade-offs analysis |
| `system-architect` | Scalable system architecture design |
| `backend-architect` | Backend systems with data integrity and security focus |
| `frontend-architect` | Performant, accessible UI architecture |
| `requirements-analyst` | Transform ideas into concrete specifications |

### Code Quality

| Agent | Purpose |
|-------|---------|
| `refactoring-expert` | Systematic refactoring and clean code practices |
| `performance-engineer` | Measurement-driven optimization |
| `security-engineer` | Vulnerability identification and security standards |

### Documentation & Research

| Agent | Purpose |
|-------|---------|
| `technical-writer` | Clear, comprehensive documentation |
| `learning-guide` | Teaching programming concepts progressively |
| `deep-research-agent` | Comprehensive research with adaptive strategies |

### Integrations

| Agent | Purpose |
|-------|---------|
| `notion` | Search and interact with Notion workspace via MCP |

## Global vs. Project-Specific

| Scope | Location | Purpose |
|-------|----------|---------|
| **Global** | `~/dotfiles` → `~/.claude/skills` & `~/.claude/agents` | Shared across all projects (this repo) |
| **Project-specific** | `.claude/skills/` & `.claude/agents/` within a project | Scoped to that project only |

For project-specific customizations, add skills and agents directly inside the project:

```
my-project/
├── .claude/
│   ├── skills/       # Project-specific skills
│   └── agents/       # Project-specific agents
└── ...
```

## How It Works

1. **Auto-sync**: `~/dotfiles/zsh/zshrc.conf` pulls the dotfiles repo from GitHub daily
2. **Skills**: `claude_merge_config` symlinks each tool-local or shared `skills/**/SKILL.md` parent dir flat to `~/.claude/skills/<name>`
3. **Agents**: each `agents/**/*.md` is symlinked into a mirrored tree under `~/.claude/agents`, and invoked automatically by Claude Code when a task matches their descriptions
4. **Hooks**: `hooks/statusline.sh` is symlinked into `~/.claude/hooks` and wired into `settings.json` as the statusline command

Because it symlinks, editing a skill's contents takes effect immediately. Adding or renaming one requires re-running `claude_merge_config`.

## Setup

1. Clone dotfiles to `~/dotfiles` and run `./deploy.sh`
2. Open a new shell, then run `claude_merge_config` once
3. Wire it into a `SessionStart` hook so renames self-heal. `~/.claude/settings.json` is
   not tracked in this repo (it holds machine-local paths and personal toggles), so this
   step is manual on a new machine:

   ```bash
   jq '.hooks.SessionStart = [{"hooks":[{
         "type": "command",
         "command": "zsh -c '"'"'source ~/dotfiles/zsh/functions.zsh 2>/dev/null; claude_merge_config'"'"'",
         "timeout": 10,
         "statusMessage": "Syncing Claude config from dotfiles..."
       }]}]' ~/.claude/settings.json > /tmp/s.json \
     && jq -e . /tmp/s.json >/dev/null && mv /tmp/s.json ~/.claude/settings.json
   ```

Why a `SessionStart` hook and not shell startup: it fires once per Claude session instead of
once per shell, at the only moment the result matters. It costs ~0.3s, and the function is
silent and writes nothing when everything is already correct.

Safe to re-run at any time — it only removes symlinks it owns, and leaves gstack's skills alone.

## Adding Content

- **Instructions**: Edit `CLAUDE.md` with global preferences
- **Skills**: Add a directory to `skills/<skill-name>/SKILL.md` with frontmatter:
  ```yaml
  ---
  name: skill-name
  description: What this skill does and when to use it
  disable-model-invocation: true  # Optional: prevents Claude from auto-invoking
  allowed-tools: Read, Grep       # Optional: restrict available tools
  ---

  Your skill instructions here...
  ```
- **Agents**: Add `.md` files to `agents/` with frontmatter:
  ```yaml
  ---
  name: agent-name
  description: When to use this agent
  category: analysis|quality|planning
  ---
  ```

Run `claude_merge_config` after adding either, to create the symlink.

## Skill Sources

Some skills in this repo were sourced from open-source projects:

| Source | Skills | Description |
|--------|--------|-------------|
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | `frontend-design`, `adapt`, `animate`, `arrange`, `audit`, `bolder`, `clarify`, `colorize`, `critique`, `delight`, `distill`, `extract`, `harden`, `normalize`, `onboard`, `optimize`, `overdrive`, `polish`, `quieter`, `teach-impeccable`, `typeset` | Design-focused skills for building polished frontend interfaces |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | `excalidraw-diagram-generator` | Generate Excalidraw diagrams from natural language descriptions |
| [blader/humanizer](https://github.com/blader/humanizer) | `humanizer` | Remove signs of AI-generated writing from text |
| [oh-my-claudecode](https://github.com/anthropics/oh-my-claudecode) | `plan`, `ralph`, `ralplan` | Planning and iterative task completion agents |
| [l0lxl0lw/gstack](https://github.com/l0lxl0lw/gstack) | `browse`, `ship`, `review`, `qa`, `investigate`, `office-hours`, `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `plan-devex-review`, `design-consultation`, `design-html`, `design-review`, `design-shotgun`, `devex-review`, `canary`, `benchmark`, `land-and-deploy`, `document-release`, `retro`, `checkpoint`, `cso`, `codex`, `careful`, `guard`, `freeze`, `unfreeze`, `health`, `learn`, `open-gstack-browser`, `connect-chrome`, `pair-agent`, `qa-only`, `setup-browser-cookies`, `setup-deploy`, `gstack-upgrade` | Browser automation, QA, planning reviews, shipping, and safety guardrails |

## Useful References

| Resource | Description |
|----------|-------------|
| [Claude Usage Tracker](https://github.com/hamed-elfayome/Claude-Usage-Tracker) | Native macOS menu bar app to monitor Claude AI usage limits in real-time — tracks session, weekly, and Opus-specific consumption |
| [Context Window Progress Bar](https://gist.github.com/davidamo9/764415aff29959de21f044dbbfd00cd9) | Custom status line script showing real-time context window usage with color-coded progress bar, session cost, model indicator, and git branch |
