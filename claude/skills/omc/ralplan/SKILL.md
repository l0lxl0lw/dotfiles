---
name: ralplan
description: Alias for /plan --consensus — iterative planning with Planner, Architect, and Critic agents
---

# Ralplan (Consensus Planning Alias)

Ralplan is a shorthand alias for `/plan --consensus`. It triggers iterative planning with Planner, Architect, and Critic agents until consensus is reached, with **RALPLAN-DR structured deliberation** (short mode by default, deliberate mode for high-risk work).

## Usage

```
/ralplan "task description"
```

## Flags

- `--interactive`: Enables user prompts at key decision points (draft review in step 2 and final approval in step 6). Without this flag the workflow runs fully automated — Planner -> Architect -> Critic loop — and outputs the final plan without asking for confirmation.
- `--deliberate`: Forces deliberate mode for high-risk work. Adds pre-mortem (3 scenarios) and expanded test planning (unit/integration/e2e/observability). Without this flag, deliberate mode can still auto-enable when the request explicitly signals high risk (auth/security, migrations, destructive changes, production incidents, compliance/PII, public API breakage).

## Behavior

This skill invokes the Plan skill in consensus mode:

```
/plan --consensus <arguments>
```

The consensus workflow:
1. **Planner** creates initial plan and a compact **RALPLAN-DR summary** before review:
   - Principles (3-5)
   - Decision Drivers (top 3)
   - Viable Options (>=2) with bounded pros/cons
   - If only one viable option remains, explicit invalidation rationale for alternatives
   - Deliberate mode only: pre-mortem (3 scenarios) + expanded test plan (unit/integration/e2e/observability)
2. **User feedback** *(--interactive only)*: If `--interactive` is set, use `AskUserQuestion` to present the draft plan **plus the Principles / Drivers / Options summary** before review (Proceed to review / Request changes / Skip review). Otherwise, automatically proceed to review.
3. **Architect** reviews for architectural soundness and must provide the strongest steelman antithesis, at least one real tradeoff tension, and (when possible) synthesis — **await completion before step 4**. In deliberate mode, Architect should explicitly flag principle violations.
4. **Critic** evaluates against quality criteria — run only after step 3 completes. Critic must enforce principle-option consistency, fair alternatives, risk mitigation clarity, testable acceptance criteria, and concrete verification steps. In deliberate mode, Critic must reject missing/weak pre-mortem or expanded test plan.
5. **Re-review loop** (max 5 iterations): Any non-`APPROVE` Critic verdict (`ITERATE` or `REJECT`) MUST run the same full closed loop:
   a. Collect Architect + Critic feedback
   b. Revise the plan with Planner
   c. Return to Architect review
   d. Return to Critic evaluation
   e. Repeat this loop until Critic returns `APPROVE` or 5 iterations are reached
   f. If 5 iterations are reached without `APPROVE`, present the best version to the user
6. On Critic approval *(--interactive only)*: If `--interactive` is set, use `AskUserQuestion` to present the plan with approval options (Approve and execute via ralph / Clear context and implement / Request changes / Reject). Final plan must include ADR (Decision, Drivers, Alternatives considered, Why chosen, Consequences, Follow-ups). Otherwise, output the final plan and stop.
7. *(--interactive only)* User chooses: Approve (ralph), Request changes, or Reject
8. *(--interactive only)* On approval: invoke `Skill("ralph")` for execution -- never implement directly

> **Important:** Steps 3 and 4 MUST run sequentially. Do NOT issue both agent calls in the same parallel batch. Always await the Architect result before issuing the Critic agent.

Follow the Plan skill's full documentation for consensus mode details.
