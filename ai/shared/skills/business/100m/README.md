# $100M — Hormozi's three books as three skills

Three sibling skills distilled from Alex Hormozi's `$100M Offers` (2021), `$100M Leads`
(2023), and `$100M Money Models` (2025). Each one interviews you, pushes back on vague
answers, and ends by writing a document with your actual numbers in it.

| Skill | The question it answers | The book |
|-------|-------------------------|----------|
| `/100m-offers` | What do I sell and what do I charge? | $100M Offers |
| `/100m-leads` | How do I get strangers to know I exist? | $100M Leads |
| `/100m-money` | Why do I have customers and no cash? | $100M Money Models |

## Which one

They map onto three distinct failures, and each skill opens by checking you're in the
right room before doing anything else:

```
not enough people see it       -> /100m-leads
they see it and don't buy      -> /100m-offers
they buy and there's no cash   -> /100m-money
```

If you pick wrong, the skill says so and points at its sibling. There is deliberately no
router skill — the scope check inside each one does that job in a single question.

## What a session looks like

One question at a time, via AskUserQuestion. Push-back on anything vague. Smart-skip for
anything you've already answered, and an escape hatch if you'd rather not be interviewed —
though the questions are most of the value, and the skills say so.

Sessions end by writing to `~/business/<slug>/YYYY-MM-DD-<kind>.md`, or to
`business/<slug>-<kind>.md` in a git repo if you'd rather keep it with the project. Later
sessions read the most recent doc first and open with what changed — specifically, whether
the number you committed to moved.

## Structure

```
100m/
├── 100m-offers/
│   ├── SKILL.md                        router, voice, interview rules, output contract
│   └── sections/
│       ├── market-and-price.md         starving crowd gate, commodity vs Grand Slam
│       ├── value-equation-and-build.md the four terms, problems -> solutions -> stack
│       └── enhancers.md                scarcity, urgency, bonuses, guarantees, MAGIC
├── 100m-leads/
│   ├── SKILL.md
│   └── sections/
│       ├── lead-magnet.md              engaged leads, the six-step build
│       ├── core-four.md                warm, content, cold, paid — pick one
│       └── scale.md                    Rule of 100, More/Better/New, Lead Getters
└── 100m-money/
    ├── SKILL.md
    └── sections/
        ├── metrics.md                  CAC, GP30, LTGP, the two gates
        ├── plays.md                    attraction / upsell / downsell / continuity menus
        └── sequencing.md               the 30-day table, stress test, the assignment
```

Skeletons stay scannable; the book depth sits in `sections/` and is read on demand when a
step needs it. The taxonomies are specific enough that working from memory silently drops
half of them, so each SKILL.md says to read the section rather than recall it.

The **Voice**, **Scope check**, and **Output contract** blocks are duplicated across all
three SKILL.md files. They're deliberately identical — change all three together.

## Notes on the source material

These are distillations for working through your own business, not summaries of the books.
Where the books give a threshold — 2× CAC within 30 days, LTGP:CAC of 3:1, the Rule of 100
— the skills carry it as a strong default with the reasoning attached, and say out loud
that it's a heuristic rather than a law.

The skills are instructed never to invent benchmarks, conversion rates, platform costs, or
case studies. Anything unknown gets written into the doc as an open number, which is
usually the most useful section in it.
