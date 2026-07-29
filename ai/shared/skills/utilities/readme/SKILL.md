---
name: readme
description: Read the README file in the current directory and execute the instructions or tasks described within it.
allowed-tools: Bash(bash *), Bash(sh *), Bash(npm *), Bash(yarn *), Bash(pnpm *), Bash(pip *), Bash(cargo *), Bash(make *), Bash(docker *), Bash(go *), Read
---

# Run README

Read the README file in the current directory, extract executable commands, and run them.

## Steps

### Phase 1: Extract Commands

Run the extraction script to find all executable commands:

```bash
bash ~/.claude/skills/readme/scripts/extract-commands.sh .
```

This script:
- Finds the README file (README.md, README, readme.md, etc.)
- Extracts fenced code blocks marked as `bash`, `sh`, `shell`, or `zsh`
- Extracts inline commands in backticks starting with common CLI tools
- Groups commands by purpose (setup, build, test, run, lint, deploy, cleanup)

### Phase 2: Analyze and Present

1. Review the extracted commands from the script output
2. Read the full README to understand context around each command
3. Present findings to the user:
   - Brief project summary
   - Commands grouped by purpose with context
   - Any required env vars or prerequisites mentioned
   - Warnings if present (especially for cleanup/deploy commands)

### Phase 3: Confirm and Execute

4. Ask user which command groups to execute (or specific commands)

5. Execute confirmed commands:
   - Run commands sequentially in the order they appear
   - Show output for each command
   - **Stop on first error** and report which command failed
   - Skip commands requiring missing env vars (inform user)

### Phase 4: Report

6. Report results:
   - Commands executed successfully
   - Any failures and their error output
   - Suggested next steps from the README

## Rules

- ALWAYS run the extraction script first before taking any action
- ALWAYS read the full README for context around commands
- NEVER execute destructive commands (`rm -rf`, `drop`, `delete`, `reset --hard`) without explicit user confirmation
- If commands require credentials or secrets, prompt the user rather than guessing
- For ambiguous commands, show context from the README and ask for clarification
- If no executable commands are found, summarize the README and ask what the user wants to do
