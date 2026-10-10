# Independent scoping review — internal preparation method

Used only when Prepare identifies a larger/riskier change or the user explicitly
requests it. Read [prepare-workers.md](prepare-workers.md). Be a fresh worker
independent of the planner/researchers. Review the proposed scope and plan;
implementation need not exist. Do not run the implementation-review gate.

1. Read user requirements, exclusions and agreed design before the plan. Trace
   each requirement through proposed changes and observable acceptance proof.
   Preserve decisions; distinguish missing decisions from choices you dislike.
2. Inspect critical source/test references. Challenge assumptions about callers,
   permissions/ownership, state transitions, migrations/rollback, concurrency,
   retries, failure behavior, public contracts and compatibility where relevant.
   State what breaks and why; do not generate generic hypothetical checklists.
3. Check that proposed tests would catch the intended failure and verify the
   real behavior. Identify invalid fixtures, test gaps, missing prerequisites or
   manual checks without concrete observations. A proposed check is not a test
   result. For bugs challenge unproven root cause and inadequate regression proof.
4. Check execution feasibility: exact affected components, dependencies, sequence,
   environment assumptions and unresolved decisions. Flag scope hidden in vague
   steps. Optional improvements are not new acceptance requirements.

Return:
- **ready**, **needs_revision**, or **blocked**, with the reason.
- Concrete findings: stable IDs, required/optional, affected requirement/plan
  section, decisive source evidence, expected vs proposed behavior and consequence.
- For each required finding, what evidence or decision would resolve it.
- On re-review, fixed/unresolved/disputed status of prior findings and any new
  regressions in the revised plan. Do not drop unresolved required findings.

Ready means the preparation is adequate for user approval, not that code is
implemented, tests passed or the user authorized delivery. Return to the owner
and stop; no edits, publication, additional agents or direct user questions.
