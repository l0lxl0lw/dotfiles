# Template gallery — pick one, read it, build on it

These are the **templates** for make-html: the full set of self-contained examples from
[ThariqS/html-effectiveness](https://github.com/ThariqS/html-effectiveness) (Apache-2.0). There is
no generic house template — you pick the file whose shape fits the content, **read it**, and build
your page on its layout, palette, and type. All open offline, zero deps; the "Acme" data is
fictional placeholder — inherit the design, never the content.

## When this skill applies

make-html's job is **teaching/explaining** (concept, system, codebase, finding). The explainer
formats below are the core fit. The rest apply the same one-file/inline-SVG/self-contained
discipline — reach for them when the task is closer to communicating, prototyping, or building a
throwaway UI than to teaching.

## Explainers & research (the core fit)

| Format | File | Use when the deliverable is… |
|--------|------|------------------------------|
| **Concept explainer** | `15-research-concept-explainer.html` | Teaching one idea/mental model deeply, building intuition from zero. The closest thing to a "default" explainer. |
| **Feature explainer** | `14-research-feature-explainer.html` | Explaining what a specific feature does, its parts, how to use it. |
| **Codebase understanding** | `04-code-understanding.html` | Mapping an unfamiliar codebase/system — modules, call paths, data flow. |
| **Flowchart / process** | `13-flowchart-diagram.html` | The core thing IS a flow, decision tree, or state machine. Diagram-led. |
| **SVG-illustrations** | `10-svg-illustrations.html` | Visuals carry most of the load; many hand-drawn diagrams, little prose. |
| **Slide deck** | `09-slide-deck.html` | Sequential reveal / presentation pacing rather than one scroll. |
| **Implementation plan** | `16-implementation-plan.html` | Laying out proposed work — phases, tasks, sequencing, tradeoffs. |

## Code & review

| Format | File | Use when the deliverable is… |
|--------|------|------------------------------|
| **Exploration: code approaches** | `01-exploration-code-approaches.html` | Comparing 2–3 ways to implement something before committing. |
| **Code review / PR** | `03-code-review-pr.html` | Walking a diff with inline annotations and verdicts. |
| **PR write-up** | `17-pr-writeup.html` | Narrating a shipped change — what/why/how, for reviewers. |
| **Design system** | `05-design-system.html` | Documenting tokens, components, usage rules. |
| **Component variants** | `06-component-variants.html` | Showing a component across states/props side by side. |

## Communication & reporting

| Format | File | Use when the deliverable is… |
|--------|------|------------------------------|
| **Status report** | `11-status-report.html` | Progress / metrics snapshot for stakeholders. |
| **Incident report** | `12-incident-report.html` | Postmortem — timeline, impact, root cause, follow-ups. |

## Prototyping & design exploration

| Format | File | Use when the deliverable is… |
|--------|------|------------------------------|
| **Exploration: visual designs** | `02-exploration-visual-designs.html` | Comparing look/feel directions before building. |
| **Prototype: animation** | `07-prototype-animation.html` | Demoing a motion/transition idea live. |
| **Prototype: interaction** | `08-prototype-interaction.html` | Demoing an interaction pattern / micro-UX live. |

## Throwaway editor UIs (interactive, JS-heavy)

| Format | File | Use when the deliverable is… |
|--------|------|------------------------------|
| **Triage board** | `18-editor-triage-board.html` | A quick drag/sort UI over a fixed dataset. |
| **Feature flags** | `19-editor-feature-flags.html` | A toggle/config panel mock. |
| **Prompt tuner** | `20-editor-prompt-tuner.html` | An input-tweak-preview loop UI. |

## How to choose

1. **What must the reader walk away with?** A mental model → concept explainer. A map of code →
   codebase understanding. A decision/flow → flowchart. A plan → implementation plan. A comparison
   → an exploration format.
2. **Prose-heavy or visual-heavy?** Visual-heavy → svg-illustrations or flowchart. Balanced →
   concept explainer.
3. **One scroll or paced reveal?** Paced → slide deck. Otherwise a scroll page.
4. **Teach vs. interact?** If the reader needs to *do* something, an editor/prototype format; if
   they need to *understand*, an explainer.
5. When unsure, default to `15-research-concept-explainer.html`.

Keep the hard rules regardless of format: **one file, inline SVG, self-contained, zero prior
knowledge.** Inherit the chosen example's layout/SVG/CSS — don't copy its fictional content or pull
in anything external. The editor/prototype formats lean on more inline JS; that's fine for those use
cases, but explainers should stay JS-light. For a jump-menu on a long page, the optional
`../floating-toc.html` snippet drops in cleanly.
