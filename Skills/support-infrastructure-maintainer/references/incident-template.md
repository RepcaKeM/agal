# Incident — first 15 minutes

## Channel opening (one message, pinned)
```
🚨 INCIDENT — <one-line description>
Severity: SEV-1 / SEV-2 / SEV-3
IC: @<name>
Start (UTC): YYYY-MM-DD HH:MM
Customer impact: <user-visible? region? %?>
Status page: <updated / pending / not affected>
Comms: @<name>
```

## Roles
- **IC (Incident Commander)** — decisions, comms, owns the channel
- **Tech lead** — drives diagnosis and fix
- **Comms lead** — status page, customer messages, internal updates
- **Scribe** — timestamped channel notes for the postmortem

For SEV-1: all four are different people. For SEV-3: IC + tech lead may be the same.

## Severity guide (adapt to your SLOs)

| Sev | Trigger | Page who | Comms |
|---|---|---|---|
| SEV-1 | Production down for everyone OR data loss | All on-call + leadership | Status page + customer email |
| SEV-2 | Major degradation or subset of users impacted | On-call rotation | Status page |
| SEV-3 | Minor degradation or internal-only impact | Primary on-call | Internal channel only |

## Decision rules
- **Recovery > root cause.** Roll back, failover, scale up FIRST. Diagnose AFTER stability.
- **Status page updates every 30 min minimum during an active SEV-1/2** — even "still investigating, no new info" beats silence.
- **Escalate early.** Pulling in extra hands costs nothing during business hours; saves the on-call's sleep overnight.

## Closing an incident
- User impact confirmed resolved
- Monitoring confirms baseline restored for ≥1h
- Final status page update
- Postmortem scheduled within 5 business days
