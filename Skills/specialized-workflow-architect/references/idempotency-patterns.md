# Idempotency patterns

## Why
Distributed systems retry. Without idempotency keys, retries produce duplicates: double-charges, double-emails, double-orders.

## How (server side)
1. Client sends operation with a unique `Idempotency-Key` header (UUID, or stable per logical op).
2. Server checks a deduplication store keyed by `(Idempotency-Key, scope)`.
3. If not seen: process, store result with TTL, return result.
4. If seen and complete: return stored result (status code + body).
5. If seen and in-progress: return 409 or hold the request until completion (your call; document it).

## How (client side)
1. Generate the key BEFORE first send, persist it locally.
2. On retry: send the SAME key. Different key = duplicate.
3. Key scope: per business operation, not per HTTP call.

## Deduplication store
- Redis with TTL (simple, fast)
- DB unique constraint on `(idempotency_key, scope)` (durable; harder under high volume)
- Choose TTL > expected retry window + max client patience (e.g. 24h)

## Idempotency vs at-most-once vs exactly-once
- **At-most-once**: no retry. Loses data on any failure.
- **At-least-once + idempotency**: standard. Works for most cases.
- **Exactly-once**: requires coordination (e.g. Kafka transactional producer + dedup consumer). Expensive; use only when business requires.

## What's NOT idempotent
- `INSERT` without unique constraint
- "Add 1 to counter" (use SET to target value if possible)
- Fire-and-forget email / SMS without dedup at the provider
- Charging a card (use Stripe's idempotency_key field, or your own dedup)
