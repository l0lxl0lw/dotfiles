---
name: develop-ticket
description: Use when explicitly asked to create or refine a development ticket and acceptance contract before technical research.
---

# Define the contract

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. This skill owns scope, not broad technical investigation.
Direct invocation runs here; use develop-feature for a fresh stage worker.

1. If a brainstorm handoff or reviewed design is supplied, read it first and carry
   forward its decisions, stable requirement IDs, acceptance examples, open questions,
   exact issue/artifact URLs and separate repository/Project destinations. Reconcile
   with the current issue/discussion; ask only unanswered or newly conflicting questions.
   Design approval alone does not authorize ticket publication or implementation.
   Establish the user-visible outcome and included/excluded behavior. Do only enough
   local lookup to ask concrete questions. Ask one focused batch about compatibility,
   identity/access, invalid/absent inputs, state postconditions and verification where
   relevant. Recommend the minimal repository-consistent option; do not invent scope.
2. Capture stable requirement IDs, observable acceptance examples, constraints,
   decisions/rationale and unresolved questions. Distinguish material product choices
   from technical unknowns research can answer. Use realistic valid success inputs.
3. For an explicit new-ticket request, create with `gh issue create --assignee @me
   --body-file FILE`, selecting the confirmed issue repository explicitly with
   `--repo OWNER/REPO` when supplied; never derive it from the Project board owner.
   If the destination is unclear, resolve it before creation. Treat similar issues as
   references. Before editing an existing
   issue, identify it and obtain explicit authorization to update that exact issue;
   offer create new/update existing/cancel when ambiguous. Preserve useful history.
4. Load `handoff.py packet ISSUE --stage ticket`. Reconcile covered issue/discussion
   before using its checkpoint candidate. Publish a v2 contract with stable IDs using
   `handoff.py record ISSUE contract --data FILE`; use `--supersedes OLD_URL` when
   replacing a contract. Follow schemas/contract.example.json, not invented digests.
5. For new tickets, follow references/operations.md for configured project setup,
   Backlog/Not started and `track.py link-orca ISSUE`. Attempt project setup and Orca
   attachment independently. Preserve conflicting links; only an explicit replacement
   choice authorizes a replace retry. `not_managed` is normal outside Orca. Report
   each downstream failure/recovery separately; issue creation may already have worked.
   Do not reset active status or attach a different issue on an existing-ticket update.

Return exact issue/contract URLs, publication and tracking outcomes separately, open
choices, and the suggested research invocation. Stop without starting research.
