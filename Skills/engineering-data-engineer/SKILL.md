---
name: engineering-data-engineer
description: Build and operate ETL/ELT pipelines, lakehouse layers (Bronze/Silver/Gold), and streaming jobs with explicit schema contracts and idempotency. Use when ingesting a new source, debugging a broken pipeline, designing a Spark/dbt model, or moving from full-refresh to incremental.
---

# Data Engineer

## Overview

Pipelines that aren't idempotent silently corrupt data. Pipelines without schema contracts break at midnight. This skill forces both up-front.

## When to Use

- Adding a new data source (Kafka topic, REST API, SaaS export, DB CDC)
- Writing or modifying a Spark / dbt / Airflow / Dagster job
- Designing or refactoring a lakehouse layer (Bronze → Silver → Gold)
- Switching a job from full-refresh to incremental
- Debugging silent data corruption, duplicates, or stale gold tables

## Iron Law

```
NO PIPELINE WITHOUT (1) IDEMPOTENT WRITES, (2) AN EXPLICIT SCHEMA
CONTRACT THAT ALERTS ON DRIFT, AND (3) FRESHNESS + ROW-COUNT MONITORING.

If rerunning the job produces duplicates, OR a new upstream column
lands without an alert, OR the gold table can go stale without paging
someone — it is not done.
```

## Layer contracts

- **Bronze** = raw, immutable, append-only. Never transform in place. Capture `_ingested_at`, `_source_system`, `_source_file`.
- **Silver** = cleansed, deduplicated, conformed types. SCD2 for slowly-changing dims. Must be joinable across domains.
- **Gold** = business-ready, aggregated, SLA-backed. Optimized for known query patterns. Consumers MUST NOT read Bronze or Silver.

## Checklist

1. **Define the data contract before writing pipeline code** — schema, PK, expected nullability, freshness SLA, owner, downstream consumers. → check: written in `contracts/<dataset>.yml` (dbt model contract or equivalent), committed.
2. **Decide ingestion mode** — full / incremental by timestamp / CDC. → check: cost estimate for each, written reason for the choice.
3. **Make writes idempotent** — `MERGE` on PK, or `replaceWhere` partition overwrite, or upsert via Iceberg/Delta. → check: rerun the job on the same input window twice; row counts identical.
4. **Add schema-drift detection** — `mergeSchema=true` + alert on new columns; `enforced contract` for required ones. → check: a deliberately-injected extra field triggers an alert in dev.
5. **Add freshness + row-count monitors** — `dbt_utils.recency`, Great Expectations, or platform-native check. → check: name the alert channel and threshold.
6. **Write a runbook** — what breaks, how to diagnose, how to backfill. → check: `runbooks/<pipeline>.md` exists; covers at least failure-to-start, upstream schema change, and bad-data backfill.

## Anti-Patterns

- **Transform-in-place on Bronze.** You lose the ability to replay history. Bronze stays append-only forever.
- **`DROP TABLE; CREATE TABLE; INSERT`** as a "refresh" — readers see empty data mid-run, and rollback is gone.
- **`SELECT DISTINCT` for dedup.** Hides which duplicate won. Use a window function ordered by event_time/ingested_at.
- **Implicit null propagation into Gold.** Decide per-field: impute, flag, or reject. "Just leave it null" is a decision someone else pays for later.
- **`failOnDataLoss=false` left enabled in prod streaming.** Masks topic offset loss. Use only during a known reset; revert immediately.
- **Schema-on-read in Silver and Gold.** Silver/Gold must have enforced contracts. Schema-on-read belongs only in Bronze.
- **One giant DAG.** Split per source / per domain. Failure blast radius matters more than fewer Airflow files.

## Related skills

- [[engineering-database-optimizer]] — when the Gold/Silver query layer needs index/plan work
- [[engineering-ai-engineer]] — when downstream consumes features for models / RAG
- [[engineering-backend-architect]] — for serving APIs on top of analytics layers

## References

- `references/medallion-pyspark.py` — Bronze/Silver/Gold patterns with Delta MERGE and dedup
- `references/dbt-contract.yml` — model contract + tests (recency, uniqueness, FK, value range)
- `references/streaming-kafka.py` — Spark Structured Streaming with checkpoints and schema parsing
- `references/great-expectations-suite.py` — validation harness wired to fail the run
