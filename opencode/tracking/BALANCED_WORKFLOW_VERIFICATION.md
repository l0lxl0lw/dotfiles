# Balanced workflow verification

Tested with OpenCode **1.18.30** using the installed dotfiles command/agent catalog.

## Automated checks

- `python3 -B -m unittest discover -s opencode/tests -p '*_test.py'`: **62 passed**.
  Includes existing branch/Orca tracking tests and new context selection, ambiguous
  plan handling, exact-issue reference validation, publication retry, empty-review
  rejection, and content/index/symlink fingerprint tests.
- `zsh zsh/tests/opencode_config_test.zsh`: **passed**, including 21 skill links,
  agents/commands, XDG/default paths, collision preservation, idempotence and keeping
  machine-local JSON unchanged by the sync.
- `git diff --check`: **passed**.

## Live routing smoke

`opencode/tests/workflow_smoke.py` used a temporary README fixture and fresh local
server with external plugins disabled. No GitHub mutations or application edits.

- All six commands resolved to their intended worker, model and `subtask: true`.
- Two invocations created two different stage child sessions.
- Parent-only context was absent from child messages; the first child's marker was
  absent from the second child's messages.
- Two native question requests originated in the stage children and were answered.
- One stage child successfully launched one codebase-locator grandchild.
- Actual stage inference used **GPT-6 Astra**; lookup used **GPT-5.6 Luna Fast**.
- Parent inference used **GPT-5.6 Luna Fast**, independently confirmed in recorded
  message usage. OpenCode also inserts zero-usage dispatch envelopes labeled with the
  child model; these are not parent model calls.

Recorded smoke parent: `ses_f6e6707ebffe5pxPJ82ZTQY1hK`.
Children: `ses_f6e670738ffecUGG77ZtDMB8hd`, `ses_f6e66b10affec44ZcXG3zP0tny`.

## Live read-only GitHub compatibility

The compact context helper successfully read backend issue #413 with exact legacy
plan and verification URLs: two selected artifacts, all six legacy discussion
comments preserved, no ambiguity. This verifies the real CLI/API response shape;
publication and mutation behavior are covered with mocks, not test issues on GitHub.

## Boundaries

The 15–25 minute small-feature target is **not yet a measured result**. These checks
prove configuration, context separation, dialogs, delegation and handoff behavior,
not a new feature implementation's quality or speed. The next performance experiment
should use the same baseline/task/acceptance suite with these bounded prompts and
fresh stage workers. Keep any timing/token claims separate from this smoke test.

Global machine-local configuration was explicitly set to `subagent_depth: 2` for
optional stage→specialist delegation. The sync itself does not edit that setting.
Quit and restart OpenCode to load the updated command/agent/skill catalog.
