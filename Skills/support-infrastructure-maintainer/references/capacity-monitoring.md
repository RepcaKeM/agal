# Capacity headroom — predictive monitoring

## What to track per critical resource
- **CPU / memory** per node + per pod / container
- **DB connections** (used vs max, per service)
- **DB CPU + IOPS**
- **Disk usage** (and inode count — easy to miss)
- **Queue depth + age** for every queue / topic
- **Connection pool saturation** (HTTP client side, gRPC, DB driver)
- **Rate-limit headroom** at every external API integration

## Predictive headroom alerts
For each metric:
- **Warn** when trend predicts saturation in 14 days at current growth.
- **Page** when trend predicts saturation in 3 days, OR utilization > 80%.

Don't wait for "hit the wall" — predictive alerts give you time to act.

## Growth conversations
- Quarterly: review utilization trends per service. Force the question "do we need more capacity in the next quarter, or do we right-size down?"
- Annually: re-evaluate reserved / committed-use commitments against actual usage.

## Common silent killers
- Slow leak on a connection pool — utilization creeps from 30% → 100% over months
- Disk filling from old logs / temp files
- Inode exhaustion before disk space
- Queue consumer slow → message age climbs while throughput looks normal
- Cache hit rate degrading → DB load grows quietly

A monthly "what's growing 2× faster than traffic?" review catches most of these before they page.
