# Step 4: Sequence the plays across 30 days, then re-run the math

A money model is not a list of offers. It's an **order**, with timing. The same four
offers arranged differently pass or fail Gate 1.

## The shape

```
Day 0    Attraction offer          low friction, low/no margin — buy the customer
Day 0+   Immediate upsell          the moment after purchase, while trust is peak
Day 0+   Downsell on rejection     never let a no end the conversation
Day 1-7  Fast win delivered        earns the right to the next ask
Day 7-14 Second upsell / expand    triggered by a delivered result
Day 14+  Continuity begins         converts the customer into recurring gross profit
```

Not every business needs all six moments. But the user should be able to say what happens
at each one, and *"nothing"* is a legitimate and revealing answer.

## Building the table

Fill this in with the user. Every take rate is an estimate — label them as such, in the
doc, every time.

```
Day  Offer                        Price   GP    Take    GP/customer
───────────────────────────────────────────────────────────────────
0    Roof Audit (attraction)       $97   $80    100%         $80
0    → Priority Repair upsell     $900  $540     35%        $189
0    → Payment plan (downsell)    $900  $520     15%         $78
10   Maintenance plan (continuity) $89/mo $71    25%   $18/mo → $18 in 30d
                                                      ─────────────
                                          30-day gross profit      $365
```

Notes on getting this right:

- **Take rates are guesses until measured.** Ask the user for their instinct, then use
  something more conservative, and show both. If the plan only works at the optimistic
  rate, that is the finding.
- **Downsell take rate applies to the people who said no**, not to everyone. Getting this
  wrong inflates the model badly — check the denominator each time.
- **Continuity within 30 days is usually one payment, sometimes zero.** Don't let twelve
  months of subscription revenue leak into a 30-day figure. This is the most common way
  these tables lie.
- **Gross profit, not price, in every row.** Ask the delivery cost for each new component;
  don't reuse the main offer's margin.

## Re-run the gates

```
Before                          After
GP30  $210                      GP30  $365
CAC   $180                      CAC   $180
      1.17x  FAIL                     2.03x  PASS  (floor 2.0x)
```

Then immediately stress it, because a plan that only passes at the assumed take rates
hasn't really passed:

```
At half the assumed take rates:
GP30  $80 + $95 + $39 + $9 = $223  ->  1.24x   still FAIL

Read: the upsell take rate is the whole plan. Everything depends on
one number nobody has measured. Ship the upsell, measure it for two
weeks, and don't spend more on ads until it clears 25%.
```

This is the most valuable paragraph in the document. It tells the user which single number
to go measure, and gives them permission not to act until they have it.

## Sanity checks before writing the doc

Run these explicitly. Each one has sunk a plausible-looking model.

- **Does anything here need cash before it produces cash?** Inventory, a hire, a build. If
  so, that's a real constraint the ratios don't show, and it belongs in the doc.
- **Can they actually deliver the increased volume?** A model that works at 3× customers
  and breaks the delivery team is a worse outcome than the status quo. Ask about capacity
  before celebrating.
- **Is the attraction offer being sold before its upsell exists?** If yes, stop — that
  sequence loses money on every customer, faster.
- **Are the payment terms real?** Invoiced on net-30 means the money lands on day 60. Gate
  1 is about collected cash. Ask when the money actually hits the account.
- **Does the sequence exhaust the customer?** Four offers in the first hour reads as a
  pitch machine and costs the relationship. Two well-placed asks beat five.
- **Is the continuity honest?** Back to the question from `plays.md` — what do they get in
  month two?

## The assignment

One change. Always one.

Rank the candidate changes by **(effect on GP30) ÷ (effort to ship)** and take the top
one. In practice, the immediate post-purchase upsell wins this ranking most of the time —
it's the largest single lever and it takes an afternoon.

Write it with the number attached:

```
## Assignment (this week)
Add the $900 Priority Repair offer to the call script, immediately after
the audit is paid for — not in the follow-up.

Measure: take rate over the next 20 audits.
Target: >= 25%. Below that, the model doesn't close and we look at price
        instead of sequence.
Do not increase ad spend until this number exists.
```

That last line matters. Passing a gate on projected take rates is not passing it, and the
user should leave knowing exactly which measurement converts the projection into a fact.
