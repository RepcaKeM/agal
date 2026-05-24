---
name: support-infrastructure-maintainer
description: Operate and harden running infrastructure — monitoring, incident response, capacity, cost, on-call hygiene. Use during an incident, when reviewing alert noise, planning capacity, auditing cloud spend, or hardening a service against the failure mode you just learned about.
---

# Infrastructure Maintainer

## Overview

Most outages aren't novel — they're predictable failure modes nobody hardened against, or they're noise-blind on-call missing real signal. This skill keeps you on the boring habits that prevent both: runbooks per alert, blameless postmortems, capacity headroom, cost guardrails.

## When to Use

- During or after an incident — triage, recovery, postmortem
- Reviewing on-call alert noise (any alert with low action rate)
- Capacity / scaling planning (peak load, growth)
- Cloud cost audit / right-sizing / spot/reserved decisions
- Hardening a service against a failure mode you just experienced

## Iron Law

```
EVERY ALERT THAT PAGES HAS A RUNBOOK. EVERY ALERT WITHOUT A
RUNBOOK GETS TUNED OR DELETED — not "we'll write it later."

EVERY INCIDENT GETS A BLAMELESS POSTMORTEM WITHIN 5 BUSINESS DAYS,
WITH AT LEAST ONE ACTION ITEM THAT WOULD PREVENT THE RECURRENCE OR
SHORTEN THE NEXT DETECTION.

CAPACITY HEADROOM ≥30% ON CRITICAL RESOURCES (CPU, MEM, DB CONN,
DISK, QUEUE DEPTH). If you're at 80%+, you're already in the
"surprise outage" zone, you just don't know when.
```

## Checklist (during an incident)

1. **Declare it.** Open the incident channel, name the IC (incident commander), state severity. → check: a person is IC; everyone else helps.
2. **Stop the bleeding before diagnosing.** Roll back, failover, rate-limit, scale up — recovery first. → check: user-visible impact decreasing.
3. **Pin the timeline** as you go. Timestamps + actions in the channel. → check: postmortem doesn't have to be reconstructed from memory.
4. **Communicate externally** if SLA / status-page tier is breached. → check: customers/stakeholders informed, not surprised.
5. **Resolve, then write up.** Don't immediately move on — fresh memory makes the postmortem useful.

## Checklist (postmortem, blameless)

1. **What happened** — timeline with timestamps.
2. **What broke** — root cause + contributing factors (a system that depends on one human being awake is a contributing factor).
3. **Detection** — how we knew, how fast, was the alert useful?
4. **Response** — what worked, what didn't, where did we lose time?
5. **Action items** — each with owner + deadline. At least one item from: prevention / faster detection / faster mitigation. → check: no "do better next time."
6. **Blameless framing** — people did reasonable things given what they knew. The system enabled the mistake; that's what we fix.

## Checklist (alert noise audit)

1. **Pull alert volume** + action rate per alert (acknowledged + acted on vs auto-resolved). → check: data, not vibes.
2. For each alert:
   - Acts on alert > 80% of pages → KEEP
   - Acts on alert < 30% → TUNE threshold or DELETE
   - "Investigate" with no clear action → write a runbook OR delete
3. **Cap pages per on-call shift.** If a shift averages > 5 pages in business hours or > 1 overnight, the SLO/alert design is broken — fix that, not the on-call rota.

## Checklist (capacity / cost)

1. **Top 10 spend lines** identified; owners assigned; each has a target trend (flat / down / explained growth). → check: monthly review.
2. **Spot / reserved / committed-use** applied where workload is steady. → check: actually saving the documented %.
3. **Headroom alerts BEFORE saturation alerts.** Page on "trending toward limit in 14 days," not on "limit hit." → check: predictive alert exists.
4. **Stale resources reaped** — unattached disks, old snapshots, idle environments. → check: monthly sweep automated.

## Anti-Patterns

- **"P99 is fine" — looking only at the median.** P99 is where users are angry; track it.
- **Postmortem with no action items.** It was a learning exercise, not a fix.
- **Naming a person in a postmortem.** Blameless means the system enabled the action, not "the human did it."
- **Auto-resolving alerts before anyone looked.** You taught the system that the alert was noise; deleting it is more honest.
- **On-call rotation with no escalation path.** When the primary is stuck, who do they wake?
- **Cost optimization as a one-time project.** Without an owner and a monthly review, savings drift back within 6 months.
- **Backups that are never restored.** A backup you haven't restored is a hope, not a backup. Test restores quarterly.

## References

- `references/incident-template.md` — channel template, IC role, comms cadence
- `references/postmortem-template.md` — blameless format with action-item criteria
- `references/alert-tuning-rubric.md` — keep / tune / delete decision tree
- `references/capacity-monitoring.md` — headroom alerts, predictive thresholds
