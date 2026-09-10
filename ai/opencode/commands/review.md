---
description: Review implementation against a GitHub issue's plan and acceptance criteria.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Issue and optional PR URL: $ARGUMENTS

Read the issue, discussion, identified plan and actual branch/PR diff. Refresh
registered branch freshness before evaluating integration readiness. Check correctness,
acceptance criteria, regressions, and verification evidence. Run appropriate checks.
Publish a Review comment with findings ordered by severity, precise file/line
references, test results and remaining gaps. Review is read-only for application
code. Do not merge, close the issue, or mark Done simply because review passed.
