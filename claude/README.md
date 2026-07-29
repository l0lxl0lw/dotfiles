# Claude Config

Global Claude Code configuration repository - custom skills and agents synced across machines.

> **Pulled by**: [`~/dotfiles`](https://github.com/l0lxl0lw/dotfiles) — the dotfiles repo clones/pulls this repo and loads its agents and skills into the shell environment.

## Structure

```
claude-config/
├── CLAUDE.md              # Global instructions (imported by ~/.claude/CLAUDE.md)
├── skills/                # Custom skills (symlinked to ~/.claude/skills)
│   ├── impeccable/                # 21 design skills from pbakaus/impeccable
│   │   ├── frontend-design/      #   Core design skill (+ 7 reference docs)
│   │   └── adapt/ animate/ ...   #   20 specialized design skills
│   ├── omc/                       # 3 skills from oh-my-claudecode
│   │   ├── plan/                  #   Strategic planning workflow
│   │   ├── ralph/                 #   Iterative task completion loop
│   │   └── ralplan/               #   Multi-agent planning consensus
│   ├── gstack/                    # 37 skills from l0lxl0lw/gstack (browse, ship, etc.)
│   │   ├── browse/ ship/ review/  #   Browser QA, ship workflow, PR review
│   │   └── ...                    #   See README "gstack" section
│   ├── community/                 # Skills from individual repos
│   │   ├── excalidraw-diagram-generator/  # from github/awesome-copilot
│   │   └── humanizer/            #   from blader/humanizer
│   ├── git/                       # Custom git workflow skills
│   │   ├── commit-local-changes/     #   Commit on current branch, no push
│   │   ├── push-to-main/             #   On main: commit + push directly
│   │   ├── pr-from-main/             #   On main: wrap into feature branch + PR
│   │   └── sync-main-and-commit/     #   On branch: sync main, merge, commit, push
│   ├── integrations/              # Custom integration skills
│   │   ├── elevenlabs/
│   │   ├── notion/
│   │   └── remotion/
│   └── utilities/                 # Custom utility skills
│       ├── load-memory/ save-memory/
│       ├── update-diagram/
│       └── readme/
├── agents/                # Specialized AI agent personas
│   ├── architecture/      # Architect agents (system, backend, frontend)
│   ├── communication/     # Learning guide, technical writer
│   ├── engineering/       # Executor, performance, refactoring
│   ├── planning/          # Analyst, planner, requirements
│   ├── research/          # Deep research, tech stack
│   └── review/            # Critic, security engineer
├── prompts/               # System prompts collection (reference)
│   ├── Anthropic/ Google/ OpenAI/
│   ├── Perplexity/ Proton/ xAI/ Misc/
└── context/               # Additional context files
```

## Skills

### Core

| Skill | Description | Model Invocable |
|-------|-------------|-----------------|
| `/push-to-main` | On the default branch: commit + push directly to remote | No |
| `/pr-from-main` | On the default branch: wrap changes into a feature branch with one commit and open a PR | No |
| `/sync-main-and-commit` | On a feature branch: pull latest main, merge it in, resolve conflicts, commit & push | No |
| `/commit-local-changes` | Analyze uncommitted changes and create a commit (no push, no PR) | No |
| `/make-resume` | Generate tailored resume and cover letter from job description | Yes |
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

The [`dotfiles`](https://github.com/l0lxl0lw/dotfiles) repo pulls this `claude-config` repo and loads its global agents/skills into the shell. For project-specific customizations, add skills and agents directly inside the project:

```
my-project/
├── .claude/
│   ├── skills/       # Project-specific skills
│   └── agents/       # Project-specific agents
└── ...
```

## How It Works

1. **Auto-sync**: Pulls from GitHub daily via `~/dotfiles/zsh/zshrc.conf`
2. **Global context**: `~/.claude/CLAUDE.md` imports this repo's `CLAUDE.md` using `@path` syntax
3. **Skills**: `~/.claude/skills` symlinks to this repo's `skills/`
4. **Agents**: Invoked automatically by Claude Code when specialized tasks match their descriptions

## Setup

1. Clone this repo to `~/workspace/claude-config`
2. Add to `~/.claude/CLAUDE.md`:
   ```markdown
   @~/workspace/claude-config/CLAUDE.md
   ```
3. Symlink skills:
   ```bash
   ln -s ~/workspace/claude-config/skills ~/.claude/skills
   ```

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
- **Context files**: Add to `context/` and import with `@~/workspace/claude-config/context/filename.md`

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
