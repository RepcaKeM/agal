# Observability bootstrap — what to set up day one

## RED metrics per service
- **R**ate — requests/sec per route + method
- **E**rrors — error rate per route (HTTP 5xx + handled-but-failed)
- **D**uration — p50, p95, p99 per route

## USE metrics per resource (DB, cache, queue)
- **U**tilization — % busy
- **S**aturation — queue depth, wait time
- **E**rrors — connection failures, timeouts

## Logs — required fields
Every log line: `ts`, `level`, `service`, `env`, `trace_id`, `span_id`, `user_id` (when applicable), `request_id`. JSON, not text.
Never log: passwords, tokens, full credit cards, full PII payloads. Truncate / redact at the logger.

## Traces
- Auto-instrument via OpenTelemetry SDK
- Propagate `traceparent` header at every service boundary AND queue boundary
- Sample at 1–10% in prod, 100% in staging

## Alerts that page (max 5 per service)
- Error rate > 2% for 5 min on a critical route
- p99 latency > SLO for 10 min
- Queue lag > N (defined per queue)
- Saturation > 90% for 5 min (DB connections, thread pool)
- Pipeline / deploy job failure on `main`

Everything else → dashboard widget or low-priority ticket, not a page.

## Runbook template (one per alert)
```
# Alert: <name>
**Severity**: page / ticket
**What it means**: <one sentence>
**First action**: <command or dashboard link>
**If that doesn't help**: <next step>
**Owner**: <team>
**Last reviewed**: YYYY-MM-DD
```
