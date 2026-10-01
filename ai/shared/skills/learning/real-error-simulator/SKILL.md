---
name: real-error-simulator
description: Use when explicitly asked to practice a concept through realistic mistakes or simulated situations. Present a scenario first, probe faulty reasoning, and let the learner retry before revealing a solution.
---

# Real Error Simulator

Start with application rather than a lecture. This skill is self-contained and
does not invoke other learning skills or shared teaching libraries.

## Prepare a fair simulation

Use the named concept and context. If absent, ask what the learner wants to practice.
For codebase-specific practice, inspect the relevant implementation and tests; cite
source locations in the debrief. For general topics, establish the correct mechanism
from reliable knowledge or references and disclose uncertainties.

Choose a plausible situation where misunderstanding the concept changes a decision
or outcome. Label it as simulated; do not imply an invented incident occurred.
Determine the expected reasoning, valid alternative answers, and key misconception
before presenting the scenario. Supply the information needed to solve it, or make
requesting missing evidence part of the task. Avoid trick questions and hidden facts.

## Interactive loop

1. Present one concrete situation, its constraints, and a decision to make. Ask
   what the learner would do or predict and why. Do not explain the concept first.
2. Stop and wait for their answer. Assess the reasoning, not merely the conclusion.
3. On a mistake, quote the relevant assumption and ask a question that helps them
   find the contradiction. Do not reveal the answer in the question or its options.
4. Allow a second substantive attempt. If still wrong, provide a more focused clue
   or counterexample, then explain the answer and its mechanism after that attempt.
5. Present a changed scenario testing the same principle without copying the answer.

The default is two attempts before a worked solution. Honor an explicit request
to reveal, skip, pause, or stop. Do not keep the learner trapped in a guessing loop.
Correct reasoning gets concise confirmation and a harder transfer case, not an
unnecessary lecture. Treat defensible alternatives as correct when they satisfy
the scenario's constraints.

## Demonstration and boundaries

Look for two fresh cases answered correctly with sound reasoning and no hints.
Report observed independence; do not infer fluency from response speed or claim
retention from a single session. Summarize recurring mistakes and one next exercise.

Run simulations in chat by default. Do not inject failures into a real service,
edit a repository, or execute a destructive operation for practice. If the learner
requests hands-on execution, agree on an isolated fixture and scope first.
