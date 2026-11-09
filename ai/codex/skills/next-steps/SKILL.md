---
name: next-steps
description: Suggest up to three contextual follow-up prompts after completed work or when asked what to do next. Handle selection of a previously suggested prompt as a draft.
---

# Next steps

Use the current conversation to suggest useful next prompts. Do not run tools,
spawn agents, or make extra model calls solely to generate suggestions.

## Suggestions

- Finish the user's authorized task first. Suggest optional continuations, never
  work that the current request still requires.
- Append `Next prompts:` and a numbered list of one to three short, ready-to-send
  prompts. Prefer specific continuations grounded in what just happened. Use fewer
  when fewer are useful; omit the block when there is no natural continuation.
- Mention an installed skill as `$skill-name arguments` only when its capability
  matches the follow-up. Never invent skill names, findings, failures, or unfinished
  work to fill the list.
- End the block with `Reply with a number for a draft, or 0 to dismiss.`
- Skip automatic suggestions after answers shorter than 80 characters, simple
  acknowledgments, pending questions or approvals, and draft selection or dismissal.
  Explicit requests for next steps may receive suggestions even after a short answer.
  Respect exact-output requests and workflows that require stopping without extras.

## Selection and controls

- Only interpret a message consisting solely of `1`, `2`, or `3` as a selection
  when the immediately preceding assistant message contains a `Next prompts:`
  block and that number exists in it. Return only the chosen prompt in a fenced
  text block so the user can copy, edit, and submit it. Do not execute it or fill
  the composer. If the number is absent, say it is unavailable without acting.
- Under the same conditions, `0` dismisses the suggestions. Briefly acknowledge
  without generating another list. Otherwise numbers retain their normal meaning.
- `next steps off` disables automatic suggestions for the rest of this
  conversation; `next steps on` enables them. Honor equivalent natural language.
  Acknowledge control changes without appending suggestions. Do not edit files to
  persist these controls or imply they apply to other conversations.
- An explicit `$next-steps` invocation or request for next prompts generates one
  list even while automatic suggestions are off; it does not re-enable them.
- Suggestions themselves authorize no actions. A number alone selects a draft;
  an explicit instruction to carry out a suggestion is a normal action request,
  subject to the permissions and scope of that action.
