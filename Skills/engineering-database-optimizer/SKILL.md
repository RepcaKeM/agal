---
name: engineering-database-optimizer
description: Diagnose and fix slow queries, design indexes, and plan zero-downtime migrations on PostgreSQL/MySQL/Supabase/PlanetScale. Use when a query is slow, an index is wrong or missing, a schema change might lock the table, or before merging any non-trivial SQL.
---

# Database Optimizer

## Overview

Most database problems are diagnosable in 30 seconds with EXPLAIN ANALYZE — but only if you actually run it. This skill makes you run it before guessing.

## When to Use

- A query is reported slow, or you're about to add one to a hot path
- Adding, removing, or replacing an index
- Writing a migration that touches a table >100k rows
- Reviewing a PR that touches SQL or ORM query-building code
- Designing a schema for a workload with known query patterns

## Iron Law

```
NO QUERY OPTIMIZATION WITHOUT EXPLAIN ANALYZE OUTPUT.
NO PRODUCTION MIGRATION WITHOUT IT BEING TESTED ON A STAGING
COPY WITH PRODUCTION-LIKE ROW COUNTS.

If you change a query "to make it faster" without showing the
before-and-after EXPLAIN ANALYZE, you have not optimized anything —
you have guessed.
```

See `references/explain-analyze-playbook.md` for how to read the output.

## Checklist

1. **Capture the slow query and its plan** → check: `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` saved before changing anything.
2. **Identify the root cause from the plan** — Seq Scan on big table? Mis-estimated rows? Hash join spilling to disk? Sort exceeding `work_mem`? → check: you can name the line that's expensive, not "the query is slow."
3. **Pick the smallest intervention that addresses the cause** — index, query rewrite, schema change, `work_mem` bump, or "this is fine." → check: ranked from cheapest to most invasive.
4. **Apply, re-run EXPLAIN ANALYZE** → check: total time dropped or plan shape changed. If not, you treated the wrong symptom.
5. **For migrations: prove it on a prod-shaped table** → check: `CREATE INDEX CONCURRENTLY` does not block writes; `ALTER TABLE` with default does not rewrite (PG ≥11); rollback path written.
6. **Index every foreign key used in joins** → check: `SELECT conname FROM pg_constraint c LEFT JOIN pg_index i ON i.indrelid = c.conrelid AND c.conkey <@ i.indkey WHERE c.contype = 'f' AND i.indexrelid IS NULL;` returns empty.

## Anti-Patterns

- **Adding an index "just in case."** Every index slows writes and uses RAM. No query needs it → no index.
- **`SELECT *` in hot paths.** Forces the planner to read columns you don't use; defeats covering indexes.
- **N+1 hidden by ORM.** Eager-load or use a CTE/JOIN. Log queries-per-request in dev to surface it.
- **Migration that adds `NOT NULL` without a default on a large table** — full table rewrite + write lock. Do: add nullable, backfill in batches, then add the constraint.
- **`CREATE INDEX` (not `CONCURRENTLY`) on a busy table** — blocks writes until done.
- **Trusting pgAdmin's "estimated" cost.** It's a model; only `ANALYZE` runtime is truth.

## Related skills

- [[engineering-backend-architect]] — when schema choice affects service boundaries / API shape
- [[engineering-data-engineer]] — ETL / lakehouse layer that produces the data your DB serves
- [[systematic-debugging]] — when slowness has no obvious cause; root-cause analysis first

## References

- `references/explain-analyze-playbook.md` — how to read query plans line by line
- `references/migration-recipes.sql` — safe patterns: add column, add index, rename, drop, backfill
- `references/n-plus-one-fixes.md` — JOIN, CTE, dataloader, eager-load patterns
