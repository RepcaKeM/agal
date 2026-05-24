# POC mutual plan

**Account**: <name>
**Champion**: <name, title>
**Economic buyer**: <name, title>
**Start date**: YYYY-MM-DD
**Decision date**: YYYY-MM-DD (≤4 weeks out for typical SaaS)

## Success criteria (signed by champion)
Specific, measurable. If criteria are met → company moves to procurement.

| # | Criterion | How we'll measure | Threshold |
|---|---|---|---|
| 1 | e.g. ingest the prospect's data and produce report X in <30 min | live demo against their data | report generated, accuracy ≥95% |
| 2 | e.g. integrate with their auth system | working SSO login | one round-trip, no errors |
| 3 | e.g. handle their peak load | load test at 2× current volume | p95 latency < 200ms |

## In scope
- ...
- ...

## Out of scope (explicit)
- ...
- ... (any of these become a follow-up, NOT a POC blocker)

## Mutual commitments

| Owner | Commitment | Deadline |
|---|---|---|
| Vendor | Provide trial env, sample data adapter | Day 0 |
| Vendor | Weekly check-in with results | Days 7, 14, 21 |
| Prospect | Provide sanitized sample data | Day 3 |
| Prospect | Provide IT access for SSO config | Day 7 |
| Prospect | Schedule decision review | Day 28 |

## What happens at decision date
- Criteria all met → proceed to procurement / contract
- Criteria partially met → defined next step (paid pilot, extended POC with new criteria, or no-go)
- Criteria not met → mutual no-go with documented learnings

Signed: ____________________ (champion)   ____________________ (vendor SE)
Date: ____________________
