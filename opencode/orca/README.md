# Orca integration

The installed Orca runtime owns workspaces, terminals, schedules, and its injected
OpenCode status plugin. Dotfiles owns the workflow card bridge, explicit coordination
commands, and deterministic checkout-refresh script.

## Weekday UI refresh

The existing local automation `[daily-9am] opencfo-ui repo pull` runs weekdays at
09:00 America/Los_Angeles with OpenCode and a fresh session, in the existing checkout
`/Users/azulee/workspace/opencfo/opencfo-ui`. Its configured exact origin is
`https://github.com/opencfo-ai/opencfo-ui.git`, branch `main`.

Precheck (read-only, no network or discard):

```sh
python3 /Users/azulee/dotfiles/opencode/orca/refresh_checkout.py \
  --path /Users/azulee/workspace/opencfo/opencfo-ui \
  --origin https://github.com/opencfo-ai/opencfo-ui.git --branch main --check
```

The prompt directs the agent to run that same command with `--apply` instead of
`--check`, report its JSON outcome and HEAD, and stop on failure without substituting
another Git operation or editing the script. `--apply` explicitly authorizes
discarding tracked unstaged edits in this one checkout. It refuses staged changes,
wrong branch/origin/root, unfinished Git operations, and local-only commits/divergence.
Submodule repositories require a separate policy. Untracked and ignored files are
preserved, including collisions with incoming tracked files. If fast-forward fails
after the tracked edits were discarded, the error explicitly reports that partial
outcome. Duplicate helper runs are locked; this is not a lock against humans or
other tools concurrently editing the checkout.

To reproduce installation on another host, choose its exact checkout and remote,
then load `orca skills get orca-cli --reference references/automations.md` and inspect
`orca automations edit --help`. Edit the existing automation's `--precheck` and
`--prompt`, keeping its workspace target, timezone/schedule, provider, and enabled
state. Use `--fresh-session`. Reread with `orca automations show ID --json` and run
the read-only precheck before relying on the schedule. Do not test by launching a
discarding refresh against a developer checkout unless that run is requested.

Tests use temporary real Git repositories and exercise staged/local-commit
preservation, branch/remote identity, and untracked/ignored-file collisions:

```sh
python3 -B -m unittest discover -s opencode/tests -p 'orca_refresh_test.py'
```

## Cross-workspace work

- `/orca-handoff`: deliver a task and stop after the accepted receipt.
- `/orca-coordinate`: supervise a Run and its worker lifecycle.

Both load [COORDINATION.md](COORDINATION.md) and live CLI guides. No general-purpose
Orca skill installation is required for these explicitly invoked commands.
