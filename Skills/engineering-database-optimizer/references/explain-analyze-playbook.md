# Reading EXPLAIN ANALYZE — what each line means

Run with `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <query>`. Read bottom-up.

## What to look for first

| Pattern | Meaning | Likely fix |
|---|---|---|
| `Seq Scan on big_table` + high `actual time` | Table scan when an index could be used | Add index on filter column |
| `rows=10000` planned vs `rows=10` actual (×100+ off) | Stats stale or correlated columns | `ANALYZE table;`, extended stats, or restructure |
| `Sort Method: external merge Disk` | Sort spilled to disk — `work_mem` too small | Raise `work_mem` for the session, or add ORDER-BY-matching index |
| `Hash Join` with `Buckets: 1024 Batches: 8` | Hash table spilled to disk | Same — `work_mem`, or filter earlier |
| `Bitmap Heap Scan` with high `Heap Blocks: lossy=N` | `work_mem` too small for bitmap | Raise `work_mem` or use a more selective index |
| `Index Scan` but `Filter:` removing most rows | Index used but not selective | Multi-column or partial index that matches the filter |
| `Nested Loop` with high iteration count | Joining big × big without hash/merge | Force re-plan, add index, or rewrite |

## Cost vs time

Costs (`cost=0.00..123.45`) are the planner's model. **Always trust `actual time`** over `cost`. A query with low cost and high actual time has bad stats.

## BUFFERS — when to care

- `Buffers: shared hit=X read=Y` — `read` is cache miss (slow). If `read` dominates, your dataset is larger than RAM or this query touches cold data.
- `Buffers: ... temp written=Z` — sort/hash spilled to disk. Same fix as above.

## Quick reference: scan types ranked

1. **Index Only Scan** — best. Covering index, no heap read.
2. **Index Scan** — good. Reads index then heap.
3. **Bitmap Index Scan → Bitmap Heap Scan** — okay for ranges or OR-of-indexes.
4. **Seq Scan** — bad on large tables, fine on tiny ones (planner is usually right when table <10k rows).
