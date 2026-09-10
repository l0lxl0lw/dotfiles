---
description: Investigate a GitHub ticket and publish evidence as an issue comment.
agent: build
---
Read `~/dotfiles/ai/opencode/tracking/WORKFLOW.md` and follow its contract.

Issue: $ARGUMENTS

Read the issue and all comments. Add it to the project if missing. Set Researching
unless implementation/review is already underway. Investigate actual code and
relevant primary documentation, using read-only specialist agents when useful.
Publish a Research comment with the investigated commit, findings with file/line
references, relevant patterns, unanswered questions and implications for the ticket.
Return the comment URL. Do not modify application code or advance to planning on
your own. No local thoughts/tickets or agentic CLI dependency.
