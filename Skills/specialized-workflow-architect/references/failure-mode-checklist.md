# Failure modes per step (with default recovery)

For every step that touches external state or input, walk this list:

| Failure mode | Default recovery |
|---|---|
| Input invalid (schema fail) | Reject; log reason; do NOT retry |
| Input valid but business-rule fail | Reject; surface reason to caller; do NOT retry |
| Dependency timeout | Retry with backoff (max N); then fail or dead-letter |
| Dependency 5xx (transient) | Retry with backoff (max N); then fail |
| Dependency 4xx (permanent) | Fail; surface reason; do NOT retry |
| Partial success (some side effects done) | Compensate (undo) OR resume from checkpoint |
| Workflow crashed mid-step | Recover from checkpoint OR replay from idempotent start |
| Slow dependency without timeout | Add a timeout (you forgot one) |
| Race condition between two workflow runs | Use idempotency key; serialize per key |
| Rate-limited by downstream | Backoff respecting Retry-After; queue if rate-limit prolonged |
| Auth failure (token expired) | Refresh once; if still failing, fail with escalation |
| Network partition / region failure | Retry across regions; surface degraded mode if all regions fail |

## Anti-patterns in failure handling
- **Catching everything → log → continue.** Silent partial failure is the worst kind.
- **Unbounded retries.** You will create a retry storm under load.
- **Retry without backoff.** Hammers the recovering dependency, prolongs its outage.
- **Retry without idempotency key.** Duplicates downstream side effects.
- **Dead-letter queue nobody monitors.** It's a graveyard, not a recovery system.
