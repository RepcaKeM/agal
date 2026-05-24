# Postmortem: <title>

**Date of incident**: YYYY-MM-DD
**Severity**: SEV-?
**IC**: <name>
**Author**:
**Status**: draft / under review / final

## Summary
2–3 sentences. What happened, scope of impact, how it ended.

## Customer impact
- Affected users / regions / features
- Duration of user-visible impact
- SLA / SLO breach: yes / no, by how much

## Timeline (UTC)
| Time | Event |
|---|---|
| HH:MM | First symptom appeared in graphs |
| HH:MM | First alert fired |
| HH:MM | On-call acknowledged |
| HH:MM | Root-cause hypothesis identified |
| HH:MM | Mitigation deployed |
| HH:MM | Customer impact ended |
| HH:MM | Monitoring confirmed stable |

## Root cause
Plain language. What broke, in causal order.

## Contributing factors
- ...
- ... (each one is a thing the SYSTEM enabled; not a person's mistake)

## Detection
- How we knew
- Time from symptom → page
- Was the alert actionable? Did it tell on-call what to do?

## Response
- What worked
- Where time was lost
- What we tried that didn't help

## Action items (each must have owner + deadline)

| # | Type | Action | Owner | Deadline |
|---|---|---|---|---|
| 1 | prevention | <thing that would have prevented this> | @ | YYYY-MM-DD |
| 2 | detection | <thing that would have caught it faster> | @ | YYYY-MM-DD |
| 3 | response | <thing that would have shortened it> | @ | YYYY-MM-DD |

At minimum: one prevention or detection item. "Improve documentation" alone is not enough.

## What went well
List 2–3 things. Postmortems reinforce good behavior too.

## Blameless framing
This postmortem describes what the system enabled. Where a person made a call that turned out wrong, we describe the information available at that moment and the system that led to that call being made. Names appear only when someone wants credit for the recovery.
