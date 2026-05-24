# Alert tuning — keep / tune / delete

For each alert (look at last 30–90 days):

| Action rate | Verdict | What to do |
|---|---|---|
| > 80% acted on | KEEP | Make sure runbook is current |
| 30–80% | TUNE | Raise threshold, add hysteresis (n-of-m), or scope to fewer cases |
| < 30% | DELETE or TUNE HARD | "Just informational" is what dashboards are for; alerts that don't page someone aren't alerts |
| 0% in 90 days | DELETE | Either it never fires (delete) or it fires and is auto-ignored (delete the practice that does that) |

## Symptom vs cause
Page on **user-visible symptoms** (error rate, latency, queue lag).
Don't page on **diagnostic signals** (CPU, memory, disk usage) unless they're a leading indicator with a defined action.

## Per-alert runbook (required to keep an alert)
```
# Alert: <name>
**What it means**: <one sentence>
**Who acks**: <team / rotation>
**First action**: <command, dashboard link, or "page <other team>">
**If that didn't help**: <next step>
**Escalation**: <who to wake>
**Last reviewed**: YYYY-MM-DD
```

If you can't fill in "first action" with something specific, the alert isn't actionable yet — fix that or delete.

## Quarterly hygiene
- All alerts reviewed; verdicts applied
- Top noisy alerts (>10 pages/quarter, <50% action) prioritized
- Pages-per-on-call-shift trend reported to leadership; capped target enforced
