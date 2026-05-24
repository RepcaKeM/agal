---
name: engineering-software-architect
description: System design and technology choices — DDD bounded contexts, architectural patterns, module boundaries, ADRs. Use when picking a technology, drawing service boundaries, evaluating coupling-vs-duplication trade-offs, or recording a decision worth referencing in six months.
---

# Software Architect

## Overview

Architecture is the set of decisions that are expensive to reverse. Most are not — call them implementation choices and don't ceremonialize them. The few that are reversible-at-high-cost deserve an ADR and a real trade-off analysis.

## When to Use

- Picking between substantively different technologies (e.g. SQL vs document store, monolith vs microservices, REST vs event-driven)
- Drawing or redrawing module / service boundaries
- Deciding what stays in-house vs which managed service to adopt
- Recording a non-obvious decision so the next maintainer doesn't redo the analysis

## Iron Law

```
EVERY ARCHITECTURE DECISION NAMES WHAT IT GIVES UP, NOT JUST WHAT IT BUYS.

If your "recommendation" only lists benefits, you have a sales pitch,
not a decision. Name the cost. Name the rollback path.

DOMAIN BEFORE TECHNOLOGY. Understand the business problem and the
forces (latency, consistency, team shape, budget) before naming tools.
```

## Checklist (any non-trivial decision)

1. **Problem statement in one sentence** — what's being solved, for whom, by when. → check: a teammate can repeat it.
2. **Forces and constraints** — team size, deadlines, existing infra, SLAs, regulatory. → check: at least three named.
3. **2–3 options with honest trade-offs** — each has at least one named loss. → check: not a 1-option memo dressed as analysis.
4. **Recommendation + reversibility** — favor reversible over "optimal." Name the rollback. → check: written.
5. **ADR committed** — `docs/adr/NNNN-<topic>.md` with Context / Decision / Consequences. → check: file exists and is the source of truth.
6. **What we measure** — what metric or signal will tell us we chose right (or wrong) in 6 months? → check: named, threshold set.

## Pattern picker (when domain is clear)

| Pattern | Use when | Avoid when |
|---|---|---|
| Modular monolith | Small team, unclear boundaries, early product | Independent per-module scaling required |
| Microservices | Clear bounded contexts, team-per-service, independent deploy | <10 engineers, no platform team |
| Event-driven | Loose coupling, async tolerable, real fan-out | Caller needs immediate result; cross-topic ordering matters |
| CQRS / read models | Write and read models genuinely diverge | Plain CRUD with simple queries |
| Saga (orchestration / choreography) | Multi-service workflows with compensation | Atomic write in one DB suffices |

## Anti-Patterns

- **Architecture astronautics.** Abstraction with no second user is just complexity. Wait for the third caller before extracting.
- **"Best practices" without naming the trade-off.** "Use microservices, they scale" — for whom, at what coordination cost?
- **Decisions in PR descriptions or chat.** A decision worth keeping is worth committing as an ADR.
- **One-way-door decisions made silently.** Vendor lock-in, data model that's hard to migrate, public API shape — these need a written, dated commitment.
- **"Future-proof" frameworks.** You don't know the future; you know the present requirement. Optimize for the present + ease of change.

## References

- `references/adr-template.md` — Context / Decision / Consequences
- `references/c4-quick-reference.md` — context / container / component / code — pick the level for the audience
