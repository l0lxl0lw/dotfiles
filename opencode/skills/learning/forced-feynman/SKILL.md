---
name: forced-feynman
description: Use when explicitly asked to explain a recently studied topic back in simple language and have jargon, skipped reasoning, or misleading simplifications challenged. Diagnose gaps from the learner's own explanation.
---

# Forced Feynman

The learner explains first. This self-contained skill does not depend on any other
learning skill or shared teaching library.

## Set up teach-back

Ask for the topic or studied material if missing. Invite the learner to explain it
as if to a curious ten-year-old: plain language, concrete examples, and explicit
cause and effect. Do not give an introductory lecture or model answer first.

Establish the factual basis before judging. Read provided material; for a named
repository inspect relevant code and tests and cite verified file:line evidence in
feedback. For general topics use reliable knowledge or references and acknowledge
uncertainty. Do not mark an explanation wrong just because it differs from a preferred
analogy or from how another system implements the concept.

Chat cannot literally interrupt an unsent explanation. Invite one short paragraph
or reasoning step per turn for interruption-style coaching. If the learner sends a
complete explanation, assess it as received without claiming to have interrupted it.

## Challenge the reasoning

Break each submitted chunk into claims and check for:

- Jargon used without a clear meaning or operational example.
- A missing causal step between two otherwise plausible statements.
- A simplification that changes the rule or drops an essential condition.
- A correct conclusion reached through a false mechanism.

Quote the specific phrase and identify the earliest consequential gap. Ask the
learner to define it plainly, supply the missing step, or predict a counterexample.
Stop and wait for their repair before proceeding to the next gap. Technical words
are allowed when the learner can explain what they mean; plain language is a test
of understanding, not a ban on accurate terminology.

Assess the revised explanation, acknowledge what is now sound, and probe remaining
gaps. If they are stuck, provide a focused hint. Give a worked explanation when
requested, then ask for a fresh example to distinguish understanding from copying.
Do not require the assistant's exact wording or punish harmless imprecision.

## Finish with a foundation report

Summarize the actual mistakes and what each reveals: missing definition, missing
mechanism, boundary confusion, or unsupported assumption. Separate repaired gaps
from unresolved ones and list the strongest demonstrated reasoning.

Ask one new application question before concluding that the repaired idea transfers.
If the learner stops sooner, report the remaining uncertainty. Never invent mistakes
or claim complete mastery from one explanation. Teaching does not authorize editing
the learner's repository, publishing their explanations, or changing external state.
