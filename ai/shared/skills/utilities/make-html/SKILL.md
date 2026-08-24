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
model: opus
effort: high
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
   Small interaction helpers (collapsible code, a TOC scrollspy, tab toggles) are fine when they
   serve the explanation and have no external deps.
5. **Match form to content, and don't ship slop.** There is no house template — pick the layout and
   visual language that fit *this* content (see Process). A bland single-column page with one blue
   accent and system fonts is the failure mode. The examples earn their keep precisely because they
   vary: serif display type, distinct palettes, sidebars, grids, collapsibles. Inherit that.

## Process

Create one TodoWrite item per step.

1. **Investigate first.** Understand the concept properly before writing — read the code, run the
   commands, trace the flow. The HTML reflects real findings, not guesses. (If the user already had
   you investigate, reuse that.)
2. **Find the spine.** Decide the single mental model the reader must walk away with. Everything in
   the page serves that. Write the one-sentence "if you remember one thing" up top.
3. **Pick a template from `examples/` — this is mandatory, not optional.** There is no generic
   scaffold to fall back on; the 20 files in `examples/` *are* the templates. Read
   `examples/README.md` (the gallery with a "use when" per file), choose the 1–2 whose shape fits
   what this content must *do* (teach a concept, map a codebase, compare options, report an incident,
   present as slides, …), then **actually open and read those files**. Don't write from memory of
   what an explainer "usually" looks like.
   - mental model / concept → `15-research-concept-explainer.html`
   - a feature, its parts + usage → `14-research-feature-explainer.html`
   - unfamiliar codebase / call flow → `04-code-understanding.html`
   - a process / decision / state machine → `13-flowchart-diagram.html`
   - visual-heavy, little prose → `10-svg-illustrations.html`
   - paced reveal / presentation → `09-slide-deck.html`
   - proposed work, phases, tasks → `16-implementation-plan.html`
   - metrics / status snapshot → `11-status-report.html`
   - postmortem / timeline → `12-incident-report.html`
   - comparing approaches → `01-exploration-code-approaches.html`

   If none fit cleanly, combine two — but still base the visual language on a real example, never on
   a from-scratch generic page.
4. **Plan the visuals.** Pick 1–4 diagrams that each carry a distinct idea: a flow, a structure/box
   diagram, a before→after, a sequence. A diagram that only restates the prose is waste — cut it.
5. **Pick the output path** (see below) and the slug.
6. **Write the HTML, building on the chosen example.** Copy the example as your starting point and
   adapt it to the real content: keep its layout, palette, type choices, and component patterns;
   replace its fictional "Acme" content with the real material. The output should look like a sibling
   of that example, not like a generic AI explainer. Author each SVG by hand; keep prose tight.
   - **Optional:** for a long page that benefits from a jump-menu, paste in the floating sidebar from
     `floating-toc.html` (auto-builds from your `<h2>`/`<h3>`, scrollspy, hides below 1160px) and
     retheme its colors to match. Skip it for slide decks, short pages, or layouts with a sidebar.
   - Never copy an example's fictional content; pull in nothing external.
7. **Self-contain check.** Grep the file for `http://`, `https://`, `src=`, `<link`, `@import`,
   `url(` — any external reference fails the skill. Inline data-URIs are acceptable only if
   unavoidable.
8. **Open it.** Print the absolute path. On macOS offer `open <path>`. Summarize in one line what
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
- It looks intentional and **distinct** — clearly built on its chosen example's design, not the
  generic single-column-blue-accent-system-font look. If you can't tell which example it descends
  from, you skipped step 3.

Files in this skill dir:
- `examples/` — the 20 templates (whole-page formats) + `README.md` gallery for picking one. **Start here.**
- `floating-toc.html` — optional drop-in jump-menu sidebar for long pages.
