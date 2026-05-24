# Picking a rollout strategy

| Strategy | When | Rollback | Cost |
|---|---|---|---|
| **Rolling update** | Stateless service, backwards-compatible change | Replace pods with previous tag | Low |
| **Blue-green** | Need instant cutover + instant rollback (e.g. cache schema swap) | Flip router back | 2× capacity during cutover |
| **Canary (5% → 25% → 100%)** | Risky change, need real-traffic signal before full rollout | Stop rollout, drain canary | Slight infra overhead |
| **Feature flag** | Per-user toggle, gradual exposure, A/B | Flip flag off | Code complexity |

## Canary checklist
1. Route 5% of traffic to new version.
2. **Bake** for ≥10 min (or 100k requests, whichever first).
3. Auto-compare error rate + p99 latency vs baseline. Halt if regressed.
4. Step to 25%, bake, compare. Then 100%.
5. Keep previous version warm for ≥1h after full rollout (instant rollback).

## Blue-green checklist
1. Deploy `green` alongside `blue`. Run smoke tests against `green` directly.
2. Switch router: 0% → 100% to `green`.
3. Watch RED metrics for 10 min.
4. If bad: flip router back to `blue` (single command). Decommission `green`.
5. If good: decommission `blue` after a safety window.

## Feature flag rules
- Default OFF in prod.
- Auto-cleanup TODO with date (e.g., `// FLAG cleanup by 2026-08-01`).
- Don't use flags as long-lived config — that's what env config is for.
