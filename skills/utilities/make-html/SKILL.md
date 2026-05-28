---
name: make-html
description: >-
  Produce a single self-contained HTML page that explains a concept, system, codebase, or
  investigation finding to someone who knows nothing about it — with inline SVG diagrams that
  carry the explanation, not just decorate it. Use this INSTEAD of writing a Markdown explainer
  whenever the deliverable is meant to teach or document understanding: "explain X", "write this
  up", "document how this works", "make an explainer", "visualize this", "create a diagram of",
  or any time you would otherwise reach for a `.md` summary of how something works. Do NOT use for
  commit messages, plans, code files, or READMEs that belong in the repo as Markdown by convention.
---

# Make HTML

Turn an explanation into **one** self-contained `.html` file with **inline SVG** visuals, written
so a person with zero prior context can follow it.

## When this fires

The default output format for *explanatory* documents is HTML, not Markdown. If you are about to
write a `.md` file whose purpose is to explain/teach/document how something works, stop and produce
a visual-explainer HTML instead. (Commit messages, plans, code, and convention-bound READMEs stay
Markdown — this skill is only for teaching documents.)

## Hard rules

1. **One file.** Everything — CSS, SVG, any JS — lives inside a single `.html`. No external
   stylesheets, no CDN links, no `<img src="...">` to local or remote files, no web fonts. It must
   render correctly opened directly from disk with no network.
2. **Diagrams are inline SVG.** Never raster, never a linked image, never an external `.svg` file.
   Hand-author `<svg>` in the document. The diagram must *do explanatory work* — show flow,
   structure, relationships, before/after, or sequence — not decorate.
3. **Assume zero prior knowledge.** The reader does not know the jargon, the file names, or why any
   of this matters. Define terms on first use. Lead with the "what is this and why care" before
   mechanism.
4. **Self-contained means self-contained.** If you embed JS, keep it tiny and inline. Prefer no JS.

## Process

Create one TodoWrite item per step.

1. **Investigate first.** Understand the concept properly before writing — read the code, run the
   commands, trace the flow. The HTML reflects real findings, not guesses. (If the user already had
   you investigate, reuse that.)
2. **Find the spine.** Decide the single mental model the reader must walk away with. Everything in
   the page serves that. Write the one-sentence "if you remember one thing" up top.
3. **Plan the visuals.** Pick 1–4 diagrams that each carry a distinct idea: e.g. a flow diagram, a
   structure/box diagram, a before→after, a sequence. A diagram that only restates the prose is
   waste — cut it.
4. **Pick the output path** (see below) and the slug.
5. **Write the HTML.** Start from `template.html` in this skill's directory (read it, copy its
   structure). Fill the sections. Author each SVG by hand. Keep prose tight; let visuals carry load.
6. **Self-contain check.** Grep the file for `http://`, `https://`, `src=`, `<link`, `@import`,
   `url(` — any external reference fails the skill. Inline data-URIs are acceptable only if
   unavoidable.
7. **Open it.** Print the absolute path. On macOS offer `open <path>`. Summarize in one line what
   the page teaches.

## Output location

- **In a git repo:** write to `explainers/<slug>.html` at the **repo root** (run
  `git rev-parse --show-toplevel` to find it). Create the `explainers/` dir if missing.
- **Not in a repo:** write to `~/explainers/<slug>.html` (create the dir).
- `<slug>` is the kebab-case concept name, e.g. `how-skills-sync.html`.
- If the target file already exists, show the user and confirm before overwriting.

## SVG authoring guidance

- Use a `viewBox` and let the SVG scale; don't hardcode pixel width/height on the `<svg>` root.
- Label everything with real `<text>` — a box with no label teaches nothing.
- Use `currentColor` or CSS variables so diagrams follow the page's light/dark theme.
- Show direction with arrowheads (`<marker>`), grouping with rounded `<rect>`, relationships with
  lines/paths. Keep stroke widths and font sizes consistent across diagrams.
- Add `role="img"` and `<title>`/`<desc>` inside each SVG for accessibility.
- If a diagram needs more than ~60 elements, it's probably two diagrams.

## Quality bar

- A newcomer reads top-to-bottom once and can explain the concept back.
- Removing any diagram would lose information that the prose doesn't already give.
- The file opens offline with no broken anything.
- It looks intentional — consistent spacing, readable measure (~65ch), works light and dark.

See `template.html` (in this skill directory) for the starting scaffold.
