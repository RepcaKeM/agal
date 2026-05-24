---
name: product-manager
description: Define what to build and why — requirements, prioritization, specs, stakeholder alignment, outcome metrics. Use when scoping a new feature, writing a PRD, prioritizing a backlog, picking a success metric, or aligning teams on a roadmap decision.
---

# Product Manager

## Overview

Most product failure isn't bad execution — it's clean execution on the wrong thing. This skill makes you write the desired outcome and the riskiest assumption before any feature spec.

## When to Use

- Scoping a new feature or initiative (PRD)
- Prioritizing a backlog or quarter
- Picking a success metric (and the guardrails)
- Resolving stakeholder conflict on what to build
- Writing the spec a delivery team will execute against

## Iron Law

```
EVERY FEATURE SPEC NAMES: (1) THE USER OUTCOME · (2) THE METRIC
THAT WILL MOVE · (3) THE GUARDRAIL THAT MUST NOT BREAK · (4) THE
RISKIEST ASSUMPTION.

If the metric is "ship it" or the assumption is "users will love it,"
you have a feature wish, not a product decision. Rewrite.

NO ROADMAP COMMITMENT WITHOUT NAMING THE OPPORTUNITY COST.
Every "yes" is implicit "no" to something else. Name it.
```

## Checklist (PRD / feature spec)

1. **User outcome in one sentence** — "<persona> can now <do thing> so that <benefit>." → check: a teammate could repeat it.
2. **Metric that moves** — one primary success metric with a target and a deadline. → check: existing dashboard or measurement plan named.
3. **Guardrail metrics** — what must NOT degrade (latency, churn, support load, error rate, revenue per other surface). → check: 1–3 named with thresholds.
4. **Riskiest assumption** — the belief that, if wrong, makes this a waste. → check: named, with a cheap way to test it before full build.
5. **Scope** — what's in, what's explicitly out for v1. → check: "out" list exists; otherwise scope creeps.
6. **Dependencies & sequencing** — what must land first; what blocks what. → check: per-dep owner and ETA.
7. **GTM / launch plan** — internal launch, customer comms, support readiness, dashboards live. → check: each item has an owner.

## Prioritization quick-pick

| Framework | Use when |
|---|---|
| **RICE** (Reach × Impact × Confidence ÷ Effort) | Large backlog, comparable items |
| **Opportunity scoring** (Importance − Satisfaction) | Pre-product or pre-redesign; survey-backed |
| **Kano** | Adding features to a mature product; what's basic vs delight |
| **WSJF** (Weighted Shortest Job First) | Deadline-driven environments, dependencies matter |

Don't pick a framework to perform rigor. Pick one to compare items honestly.

## Anti-Patterns

- **Output as outcome.** "We shipped X" ≠ "X moved Y." Track outcome.
- **Solution-first PRD.** Names the thing to build before the problem to solve. Rewrite from the user back.
- **Vanity metric.** "Signups" without retention is theater. Pair acquisition with retention/use metric.
- **Stakeholder satisfaction as success.** Internal applause ≠ customer value.
- **"Quick win" creep.** Each quick win is below-the-cut work that displaces a bigger bet. Audit quarterly.
- **Roadmap as commitment, not bet.** Commit to outcomes, bet on features. Allow swaps when bets fail.

## Related skills

- [[project-management-experiment-tracker]] — when the riskiest assumption needs a real A/B test
- [[design-ux-researcher]] — when the discovery phase needs structured user research
- [[product-trend-researcher]] — for the strategic / market framing of a new bet

## References

- `references/prd-template.md` — one-page PRD shape (outcome, metric, scope, risks, GTM)
- `references/launch-checklist.md` — readiness items before any user-facing release
- `references/stakeholder-1pager.md` — narrative format for decisions that need exec sign-off
