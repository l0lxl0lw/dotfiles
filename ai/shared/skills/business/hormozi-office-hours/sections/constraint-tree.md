# The constraint tree

Read this during Phase 2. The goal is to walk down to **exactly one** leaf.

His premise: there is always *a* rate limiter, singular. Businesses stall because
owners work on three things at 30% instead of one thing at 100%, and because the
thing they *feel* is the constraint is rarely the thing that actually caps output.

## How to walk it

At each level, force a choice. When they say "both", ask which one, if fixed
tomorrow, would let them take more money this month. That question breaks almost
every tie.

```
                 Where does growth actually stop?
                               |
                     What's your net margin?
                      /                  \
              thin (<20%)              healthy
                    |                      |
         keep much of one more sale?   at capacity?
             /            \              /      \
            NO            YES         YES        NO
             |             |           |          |
          MARGIN      sub-scale --> DELIVERY  revenue stop
      underpriced /    volume fixes  need more  if you vanish?
      badly packaged   it: continue  capacity     /      \
             |          down tree        |      YES       NO
      +------+------+                +---+---+   |         |
      |             |                |       | OWNER    DEMAND
    PRICE      UTILIZATION         TALENT PROCESS |         |
  / PACKAGE      / COST                       see the  +----+----+
                                              playbook |         |
                                                     LEADS  CONVERSION
```

Two deliberate gates. **Margin first**, because you don't multiply a unit that
barely works. Then the **contribution test**, because thin-because-underpriced and
thin-because-sub-scale need opposite prescriptions. Only then does capacity get to
route anything — full-and-poor and full-and-profitable look identical until you have
the margin.

## Level 1 — the top split

Ask in this order. **Margin gates everything** — resolve it before you let a
capacity answer route anywhere, for the reason in the trap below.

1. **"What's your net margin?"** — ask this first, always, before any question
   about capacity, leads, or people.
   - **Thin (under ~20%)** → **MARGIN**, and stop. Whatever else is true, you do
     not multiply a unit that barely works. Check the contribution test below
     first, because there's one honest exception.
   - **Healthy** → continue.
2. **"Are you at or near capacity right now?"** — Yes → **DELIVERY**. They
   genuinely need capacity and can now afford to buy it.
3. **"If you disappeared for a month, what happens?"** — Revenue stops → **OWNER**.
4. Otherwise → **DEMAND**.

**Why margin goes first: you don't multiply a broken unit.** A thin-margin business
asking how to grow is asking to make the problem bigger, and every growth answer you
could give — more leads, more staff, another location — makes it worse. Fix the unit
to a healthy margin, *then* multiply it. Someone at 15% across three locations
wanting a fourth should be fixing the three to 35-40% first; the fourth site will
otherwise inherit the same economics and split their attention besides.

### The contribution test — the one honest exception

Thin margin has two very different causes, and they need opposite prescriptions:

- **Each unit of work is barely profitable** — underpriced, badly packaged,
  scope creeping. → MARGIN. Volume makes it worse, faster.
- **Each unit of work is fine; fixed overhead eats it** — the rent, the software,
  the salaried people are sized for a bigger business than they have. → volume
  genuinely does fix this, so treat the real constraint as DEMAND and keep going
  down the tree.

Discriminate with: **"On one more sale, how much of that revenue do you keep before
overhead?"** Healthy contribution with thin net margin means they're sub-scale.
Thin contribution means they're underpriced, and no amount of volume saves them.

Ask this before prescribing. Getting it backwards is the most expensive error in
this tree in either direction.

### The trap: full and poor

A business at capacity with a thin margin will tell you its constraint is people.
It is not. Asked "could you serve twice as many tomorrow?" they say no, entirely
honestly, and every instinct — theirs and yours — says hire. But hiring into a thin
margin buries it permanently: you add cost to serve work that was never priced to
carry it, and arrive at the same exhaustion with a bigger payroll.

The tell is the combination: **full, and poor.** Full and profitable is a delivery
problem and you should hire. Full and poor is a pricing problem wearing a staffing
problem's clothes — reprice to the outcome, then utilization, and only then talent,
which you can afford by that point.

So: never accept "we need more people" without the margin number. It changes the
answer completely, and it's the single most valuable question in this tree.

The other self-report to distrust is **DEMAND** — "I need more leads" is the most
comfortable answer and the easiest to buy a solution for. A business at capacity on
a 10% margin does not have a lead problem, and pouring leads on it makes everything
worse.

### Tie-break: owner-bound *and* demand-starved

Common presentation, and the ordering is counterintuitive. Someone closes every
deal personally *and* has no lead flow, so they conclude they must hire a
salesperson to free themselves up.

**Take DEMAND first, and keep them in the sales seat while you do it.** Two
reasons. Hiring salespeople into a business with no lead flow gives them nothing to
work and they quit, having cost you a year. And selling is the last thing a founder
should delegate — a founder who can't collect money doesn't have a business, time on
calls is what makes their marketing work, and they'll out-close any hire on
conviction and product knowledge alone.

The owner constraint then resolves as a consequence rather than as a project: they
build the lead channel and sell against it themselves, which produces the documented
process, and *then* the hire has something real to be dropped into. New process, old
person.

Check whether revenue would actually stop if they vanished, or merely growth. If
existing revenue is contracted or recurring and would survive a month, they're
demand-constrained with an owner-dependency risk, not owner-constrained. Only route
to OWNER when their absence stops the money.

## DEMAND → leads or conversion

The dividing question: **"Of the people who find out about you, what fraction
buy?"**

- They don't know → that gap is the finding. Instrument it before spending.
- Plenty of interest, few sales → **conversion**. Go to the next level.
- Barely anyone knows they exist → **leads**. → hand off to `/100m-leads`.

Before accepting "leads", check the leak. If they churn hard or nobody ever buys
twice, more leads just runs the bucket faster and hides the real problem. Retention
outranks acquisition in the fix order.

## CONVERSION → offer, sales motion, or traffic temperature

Fix in this order — **offer → sales motion → traffic** — because traffic against a
broken offer only costs more.

1. **Offer.** Are they selling a commodity unit (an hour, a session, a seat) or an
   outcome? Commodity units force price comparison and cap revenue per customer.
   → `/100m-offers`.
2. **Sales motion.** Ask them to walk you through the process end to end. A
   startling number of profitable businesses discover mid-sentence that they don't
   have one — inbound interest gets scheduled, not sold. "There isn't really one"
   *is* the diagnosis.
3. **Traffic temperature mismatch.** The most under-diagnosed conversion failure.
   See below.

### The warm-to-cold mismatch

A business built on referrals, word of mouth, or an existing audience runs a
**warm-traffic offer**: essentially "buy our thing", which works only on people
who already trust them or know someone who bought.

The moment they scale into cold traffic, everything appears broken at once and
they conclude the channel doesn't work. The channel is fine. The motion is wrong —
they're pointing a warm offer at cold people.

The counterintuitive fix: **add steps**. Cold traffic needs a lower-commitment
entry point, proof, and a heating sequence before the ask. You deliberately put
more friction into the process to generate the trust that referral traffic arrived
with for free.

Flag this whenever someone says a channel "doesn't work for our industry" and
their existing business is referral- or content-driven.

## DELIVERY → talent or process

- **Talent** — they know how the work should go, they don't have enough people who
  can do it. Constraint is hiring, training, and retention.
- **Process** — the work lives in someone's head, so every new hire fails and gets
  blamed for it.

**The rule that decides the order: new process, old person.** Never pair a new
process with a new hire — that's two unknowns, and when it fails you can't tell
which one broke. Someone who already knows the business builds and proves the
process; *then* you hand the finished process to a new person. Most "we hired and
it didn't work out" stories are this rule being violated.

Corollary for delegation: never outsource the three things that constitute the
business — **traffic, conversion, delivery**. Legal, accounting, insurance, and
bookkeeping are fine to hand off. The founder should be able to sell; a founder who
can't collect money doesn't have a business, and time on sales calls makes their
marketing better.

## MARGIN → price, utilization, or cost

The signature presentation: **fully booked and barely profitable.** Waitlists,
no marketing spend, exhausted owner, single-digit margin.

This is a **pricing and packaging** problem wearing a staffing problem's clothes.
The sequence:

1. **Price and package to the outcome**, not the unit. Selling sessions, hours, or
   seats invites comparison shopping and caps you at time available.
2. **Add recurring or membership structure.** Two effects, and the second is the
   underrated one: revenue retention improves, *and* predictable bookings let you
   optimize scheduling, which raises utilization per person per day without hiring
   anyone.
3. **Then raise utilization**, measured per unit that actually constrains you —
   per technician, per chair, per square foot, per engineer.
4. **Then backfill talent**, which you can now afford because margin exists.

Doing this in reverse — hiring first to relieve the pressure — is the standard
mistake, and it buries the margin permanently.

A margin floor worth stating: below ~20% net there's nothing left to fund growth,
absorb a bad quarter, or pay a manager enough to care. Treat it as a strong
default with reasoning, not a law.

## OWNER → the business can't run without you

Symptoms: they close every sale, every decision escalates, revenue tracks their
attention, and they cannot take two consecutive weeks off.

Note the distinction he insists on: *not being on the floor* is not the same as
*not running the place*. Plenty of owners have stopped doing the craft work and
still make every decision — that's still owner-constrained.

This blocks expansion absolutely, so if the presenting question was about opening
a second location, hiring a GM, or selling, this constraint outranks it. See the
expansion litmus test in `playbooks.md`.

## Landing it

Say it in one sentence and get agreement:

> "Your constraint is [X], not [Y]. Everything else waits. Agree?"

If they disagree, ask which number you have wrong. If a number genuinely
contradicts you, change your answer out loud — that's what the numbers were for.
