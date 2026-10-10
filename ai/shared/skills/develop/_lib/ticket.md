# Ticket and acceptance contract — internal preparation method

Read [workflow.md](workflow.md); resolve ROOT using the sibling resolve-root.py.
Use this inside `develop-prepare`, not as a separate session/approval stage.

Draft the outcome, stable requirement IDs, exclusions, constraints and observable
acceptance checks from the user's answers and verified research. Preserve prior
IDs, choices and exact issue references. Ask only unresolved product questions.
For bug fixes include expected vs actual behavior, affected cases, reproduction
evidence and root-cause confidence. Do not promote hypotheses to facts.

After approval of the full preparation result:

1. Create an issue using `gh issue create --assignee @me --repo OWNER/REPO
   --body-file FILE`, or update the explicitly selected existing issue. Preserve
   human text. Approval to publish the result authorizes this mutation; do not
   ask again. A bare existing issue URL or design discussion is not publication
   authority. Confirm missing issue repository; Project configuration does not
   select it. Similar issues are references, not permission to edit them.
2. Load `handoff.py packet ISSUE --stage ticket`. Reconcile issue/discussion and
   the current contract. Use schemas/contract.example.json and the actual
   checkpoint candidate, not invented digests. Publish `handoff.py record ISSUE
   contract --data FILE`, explicitly superseding a replaced contract.
3. Follow ROOT/tracking/references/operations.md for Project setup, authenticated
   assignee, Backlog and `track.py link-orca ISSUE`. Project/Orca updates are
   independent outcomes; preserve conflicting links, active statuses and user
   notes. Unmanaged cwd is normal. Report failures without duplicating an issue
   that already exists. Reconcile publication outcomes before retrying.

Return the actual issue/contract URLs to the Prepare owner so it can publish the
approved research and plan without extra stage confirmations. If publication is
unavailable, retain the draft and report the missing prerequisite honestly.
