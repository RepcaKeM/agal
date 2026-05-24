-- Safe migration patterns. Always: add → backfill → switch → drop.
-- All examples assume PostgreSQL ≥11.

-- ============================================================
-- Add a nullable column (instant, safe)
-- ============================================================
ALTER TABLE orders ADD COLUMN tax_cents INTEGER;

-- ============================================================
-- Add a column with default — PG 11+: metadata-only, instant
-- ============================================================
ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'pending';

-- ============================================================
-- Add NOT NULL on a large existing column — multi-step
-- ============================================================
-- Step 1: add CHECK NOT VALID (no scan, no lock)
ALTER TABLE orders
    ADD CONSTRAINT orders_status_not_null CHECK (status IS NOT NULL) NOT VALID;

-- Step 2: validate in background (acquires SHARE UPDATE EXCLUSIVE, allows reads/writes)
ALTER TABLE orders VALIDATE CONSTRAINT orders_status_not_null;

-- Step 3: convert to a proper NOT NULL (now metadata-only since constraint exists)
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;
ALTER TABLE orders DROP CONSTRAINT orders_status_not_null;

-- ============================================================
-- Add an index without blocking writes
-- ============================================================
-- CONCURRENTLY cannot run inside a transaction; run it alone.
CREATE INDEX CONCURRENTLY idx_orders_status_created
    ON orders (status, created_at DESC);

-- If it fails halfway, you get an INVALID index — drop and retry:
-- DROP INDEX CONCURRENTLY idx_orders_status_created;

-- ============================================================
-- Rename a column with zero downtime (multi-deploy)
-- ============================================================
-- Deploy 1: add new column, dual-write in app code
ALTER TABLE orders ADD COLUMN total_cents INTEGER;
-- App writes BOTH `total` and `total_cents`; reads `total`.

-- Deploy 2: backfill in batches
UPDATE orders SET total_cents = total
    WHERE total_cents IS NULL AND id BETWEEN 1 AND 100000;
-- ... repeat in chunks ...

-- Deploy 3: switch reads to `total_cents`, keep dual-write
-- Deploy 4: stop writing `total`, drop the old column
ALTER TABLE orders DROP COLUMN total;

-- ============================================================
-- Drop an index safely
-- ============================================================
DROP INDEX CONCURRENTLY IF EXISTS idx_orders_legacy;
