# Steps 1–2: Get the numbers, then run the two gates

## Step 1: The six numbers

Ask for all six at once — the user will want to open one dashboard and answer everything.
For each, record **provenance**: measured, estimated, or assumed. Provenance goes in the
doc. A model built on six guesses is a story, and the user deserves to know which it is.

| # | Number | How to ask for it | Common wrong answer |
|---|--------|-------------------|---------------------|
| 1 | **Price** | "What does a new customer actually pay up front?" | The list price rather than the average after discounts |
| 2 | **Cost to deliver** | "What does it cost you to deliver that — labour, materials, software, payment fees? Not rent or salaries you'd pay anyway." | Including overhead. That's net profit, not gross. |
| 3 | **Total acquisition spend, last 30 days** | "Everything you spent to get customers — ad spend, agency fees, commissions, sales rep pay." | Ad spend only, omitting the salesperson |
| 4 | **New customers, last 30 days** | "How many new paying customers in the same window?" | Leads. Only paying customers count. |
| 5 | **What else they buy in the first 30 days** | "After the first purchase, does the average customer spend anything more within 30 days? How much, and what percentage do?" | "Some of them do sometimes" |
| 6 | **Repeat behaviour** | "How many times does the average customer buy in total, over what period, before they stop?" | A number pulled from the best customer |

**If they can't answer 3 or 4**, stop. The session's assignment becomes measurement, and
you say so plainly: *"You can't fix a ratio you can't see. This week: total acquisition
spend and new customers, for the last 30 days. Everything after that is guessing."* Then
continue with explicitly labelled estimates so they still leave with a model — just mark
every downstream figure as provisional.

## Step 2: Compute, then judge

### The definitions

**CAC — Customer Acquisition Cost**
```
CAC = total acquisition spend / new customers acquired
```
Include everything spent to get the customer: ads, agency, affiliate payouts, sales
commission, the loaded cost of the person making the calls. Excluding sales cost is the
most common error and it flatters the number badly.

**Gross profit**
```
gross profit = revenue - cost of delivering that revenue
```
Direct costs only. Not rent, not the founder's salary, not tooling they'd pay for anyway.
Every gate below uses gross profit, never revenue.

**30-day gross profit (GP30)** — gross profit collected from one customer within 30 days
of acquisition. The word doing the work is **collected**. Money invoiced on net-60 terms
is not 30-day cash and must not be counted here; ask about payment terms explicitly,
because this is where service businesses quietly fail the gate.

**LTGP — Lifetime Gross Profit** — total gross profit from one customer across the whole
relationship. Not lifetime *revenue*. If the user offers an LTV number, ask whether it's
revenue or profit; it's almost always revenue.

### Gate 1 — Client-Financed Acquisition

```
GP30 / CAC  >=  2.0
```

**Why 2×, specifically.** At 1× you break even and can only ever run in place — every
dollar back is spent getting the same customer again. At 2×, one customer's first 30 days
pays for itself *and* buys the next one, so the customer base compounds without external
capital. That is the entire mechanism the book is named after: **the customers fund the
acquisition.**

Failing this gate is the diagnosis for almost every business that feels stuck despite
being profitable. They're not unprofitable — they're slow, and slow means growth is capped
by whatever cash is already in the bank.

Present it as arithmetic, not a verdict handed down:

```
GP30  $210
CAC   $180
      210 / 180 = 1.17x        FAIL — floor is 2.0x

At 1.17x, each new customer returns $30 of spendable surplus in month one.
To add 10 customers next month you need $1,800 of cash you don't have.
```

### Gate 2 — Long-term health

```
LTGP / CAC  >=  3.0
```

The floor for a business that survives at all. Below 3:1 there's nothing left for
overhead, salaries, or profit once acquisition is paid for. Above 3:1 the model works
eventually — the question is only how fast.

### Reading the two together

| Gate 1 | Gate 2 | Diagnosis | Where to work |
|--------|--------|-----------|---------------|
| Pass | Pass | Healthy. Cash-limited only by nerve. | Go spend more — the constraint is `/100m-leads` |
| **Fail** | Pass | **The common case.** Sound business, money arrives too late. | Sequencing: upsells and front-loaded collection |
| Pass | Fail | Front-loaded but customers don't stay. Rare and unstable. | Retention and continuity, or a real product problem |
| Fail | Fail | The unit economics don't work. | Price and margin — go to `/100m-offers` before anything here |

**Say which cell they're in and what it means, in one sentence.** This is the single most
useful output of the whole session, and it should land before you offer any tactics.

### Payback window

Worth computing when Gate 1 fails, because it makes the abstraction concrete:

```
payback days ≈ 30 × (CAC / GP30)
```

Rough, and assumes gross profit accrues evenly — say so. But *"each customer ties up your
cash for about 45 days"* lands in a way a ratio doesn't, and it explains exactly why the
bank account never grows even as revenue does.

### Sensitivity — mandatory when inputs were estimated

If any input was estimated or assumed, recompute the gate at a plainly worse value and
show both. If the verdict flips, say so:

```
At the estimated 35% delivery cost:   GP30/CAC = 1.17x   FAIL
At 45% (if the estimate is optimistic): GP30/CAC = 0.96x  FAIL, worse

The verdict holds either way. But #2 is a guess — measure it this month.
```

A conclusion that survives the pessimistic case is worth acting on. One that doesn't
should be labelled as fragile, out loud, before the user makes a decision on it.
