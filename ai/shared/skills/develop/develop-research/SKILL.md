---
name: develop-research
description: Use to investigate a development issue's concrete technical unknowns and publish bounded, source-pinned research for planning.
---

# Answer the unknowns once

Resolve this skill's physical directory (follow installation symlinks) before reading
`../_lib/workflow.md` from there. Load `handoff.py packet ISSUE --stage research` with
supplied artifact URLs. Reconcile changed decisions. Set Researching only when doing
so does not regress active implementation/review. Direct invocation uses this session.

1. Identify the few technical questions blocking a plan. Trace the relevant entry
   point, logic and persistence; find a close implementation/test analogue. Expand
   source reads only to resolve consequential invariants, not to tour the repository.
2. Prefer direct investigation. Delegate only a named unresolved question to an
   available specialist; small work normally needs zero or one. No mandatory fan-out
   or Locate → Patterns → Analyze pipeline. If nested delegation is unavailable, work
   directly instead of retrying it or claiming another worker ran.
3. Verify source claims: real route/caller wiring, ownership keys, state changes,
   defaults/NULL behavior, errors and test prerequisites where relevant. Record known
   baseline evidence; run a targeted baseline check only when needed. Ask product
   questions rather than silently answering them with technical assumptions.
4. Stop once implementation and verification paths are clear. Publish one v2 Research
   record using schemas/research.example.json with stable fact IDs, decisive source
   locations and unresolved technical questions. Use `handoff.py record ISSUE research
   --data FILE --input CONTRACT_URL`, explicitly superseding any replaced record.
   Helpers bind file hashes; do not paste transcripts or invent provenance.

Return Research URL, relevant prerequisites/blockers and the suggested plan invocation.
Do not implement, publish a second technical plan, or start planning automatically.
