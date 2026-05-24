---
name: engineering-backend-architect
description: Backend architecture decisions — API contracts, service boundaries, schema design, distributed system trade-offs. Use when designing new services, choosing between monolith vs microservices, defining inter-service communication, or evaluating consistency vs availability trade-offs.
---

# Backend Architect

## Overview

Backend architecture is the choice of trade-offs you make BEFORE writing code. Wrong trade-offs are expensive to reverse; right trade-offs make future change cheap.

This skill enforces explicit trade-off analysis and reversibility-first decisions, not "best practices" cargo cult.

## When to Use

- Designing a new service or API
- Choosing between monolith / modular monolith / microservices
- Defining service boundaries or inter-service communication (REST / gRPC / events)
- Schema decisions with non-trivial impact (denormalization, sharding key, event log)
- Evaluating a third-party dependency that crosses a system boundary

## Iron Law

```
NO ARCHITECTURE DECISION WITHOUT A WRITTEN ADR.

Every non-trivial choice (the four bullets above) gets a short
Architecture Decision Record committed to the repo. If you can't
write the Context / Decision / Consequences in ten lines,
you don't understand the decision yet.
```

See `references/adr-template.md`.

## Checklist

1. **Name the problem in one sentence** → check: a teammate could repeat it back without reading code.
2. **List 2-3 candidate approaches with trade-offs** → check: each option has at least one named loss, not just gains.
3. **Pick the most reversible option that meets the requirement** → check: write the rollback path; if there isn't one, justify why.
4. **Write the ADR** → check: file in `docs/adr/NNNN-<topic>.md`, Context/Decision/Consequences sections filled.
5. **Identify the failure modes** → check: list at least three (network partition, dependency outage, data corruption) and what the system does in each.
6. **Define observability before shipping** → check: name the metric, the alert threshold, and the dashboard location.

## Anti-Patterns

- **Microservices for a 3-person team.** Coordination cost > scaling benefit. Use a modular monolith until team or domain forces split.
- **"We might need it later" abstractions.** Event bus, plugin system, multi-tenancy — only add when a real second consumer exists.
- **Strong consistency by default.** Most reads can tolerate seconds of staleness. Forcing strong consistency without need locks you out of caching, replicas, and async patterns.
- **Schema migrations without backwards-compatible intermediate state.** Always: add column → backfill → switch reads → drop old. Never one-shot.
- **Bespoke retry/circuit-breaker logic.** Use the platform primitive (sidecar, service mesh, library). Hand-rolled retry storms are an outage.

## Related skills

- [[engineering-database-optimizer]] — schema migration safety, index design, query plans
- [[engineering-devops-automator]] — deploy, rollback path, observability for the service you design
- [[engineering-software-architect]] — when the question is broader than service shape (DDD, patterns, ADRs)
- [[engineering-security-engineer]] — threat modeling for new auth / IAM / data flows

## References

- `references/adr-template.md` — ADR template
- `references/architecture-patterns.md` — when to pick microservices / modular monolith / event-driven / CQRS
- `references/schema-examples.sql` — schema patterns (soft delete, time travel, audit log)
- `references/api-skeleton.js` — Express + middleware skeleton with rate limit, auth, error envelope
