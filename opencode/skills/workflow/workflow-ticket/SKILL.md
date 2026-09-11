---
name: workflow-ticket
description: Use for /ticket or an explicit request to create or refine a GitHub workflow issue. Scope the contract before research; preserve Project 4 and Orca tracking.
---

# Ticket: define the problem and boundaries

Read `~/dotfiles/opencode/tracking/WORKFLOW.md` once. This stage owns product scope,
not a repository-wide technical investigation. For a small task aim for 1–2 minutes,
one batch of 3–6 decision-bearing questions, and a short issue. These are planning
targets, not permission to omit a material question.

1. Identify the user-visible outcome and classify the work as small, medium, or
   large. A bounded change through API/service/DB using existing patterns can be
   small. Do a quick local lookup only to make questions concrete.
2. Ask only what changes implementation: interface/compatibility, identity and
   access scope, invalid/absent inputs, persistence/postconditions, and verification
   where relevant. Explain and label your recommendation. Do not invent requirements
   or repeatedly expand scope to force pushback. Follow up only on real ambiguity.
3. Capture a concise contract: outcome; included/excluded behavior; acceptance
   examples with observable outcomes; decisions and rationale; unresolved technical
   questions for research. Use valid identifiers in happy-path examples and distinct
   malformed-input examples when identifiers are involved. No proposed solution is
   required just to create a ticket.

## GitHub and Orca identity contract

Treat the request as a **new ticket** unless the user supplies the exact existing
issue or explicitly asks to update it. Similar issues are references, not permission
to edit them. Before every `gh issue edit`, show the candidate and ask with these
native choices: **Create a new ticket (Recommended)**, **Update the existing ticket**,
**Cancel**. Only the second answer authorizes updating the named issue.

For a new ticket use `gh issue create --assignee @me --body-file ...`. Add it to
https://github.com/orgs/opencfo-ai/projects/4, set Status **Backlog**, and run
`track.py sync-state ISSUE 'Not started'`. Then run:

```sh
python3 ~/dotfiles/opencode/tracking/track.py link-orca ISSUE
```

Use the exact URL returned by GitHub. Attempt Project 4 setup and Orca attachment
independently: neither downstream failure undoes the created issue or excuses
skipping the other outcome. Verify assignment and project fields. On an Orca link
conflict, ask **Keep existing link (Recommended)** or **Replace with new issue**;
only replacement authorizes the returned `--replace-existing EXISTING_NUMBER` retry.
`not_managed` is normal outside Orca. Report `orca_unavailable`/`failed` with the
helper's exact recovery command. Only `attached`/`already_attached` proves attachment.
After successful attachment, run `track.py checkpoint-orca ISSUE Backlog` to mirror
the new-ticket milestone (the earlier status call may have preceded attachment).

For an approved existing-ticket update, preserve useful content and later work;
do not reset status/assignees or invoke `link-orca`.

Return issue creation/update, assignee/Project 4 fields, and Orca attachment as
separate outcomes, plus one next command: `/research ISSUE_URL`. Stop here.
