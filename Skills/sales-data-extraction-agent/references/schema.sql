-- Minimal schema for the sales-data-extraction pipeline.
-- Three tables: imports (audit), metrics (the data), unmatched_rows (review queue).

CREATE TABLE imports (
    id              BIGSERIAL PRIMARY KEY,
    source_file     TEXT NOT NULL,
    file_hash       TEXT NOT NULL UNIQUE,      -- reprocess only on change
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('processing','completed','failed')),
    rows_in         INTEGER,
    rows_inserted   INTEGER,
    rows_failed     INTEGER,
    error           TEXT
);

CREATE TABLE metrics (
    id              BIGSERIAL PRIMARY KEY,
    import_id       BIGINT NOT NULL REFERENCES imports(id),
    row_index       INTEGER NOT NULL,           -- in the source sheet
    rep_email       TEXT NOT NULL,
    metric_type     TEXT NOT NULL CHECK (metric_type IN ('MTD','YTD','YE')),
    period          DATE NOT NULL,              -- normalized period start
    revenue_cents   BIGINT NOT NULL CHECK (revenue_cents >= 0),
    units           INTEGER,
    quota_cents     BIGINT,
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rep_email, metric_type, period)     -- update-semantics on re-import
);

CREATE INDEX metrics_by_period ON metrics (period DESC, metric_type);
CREATE INDEX metrics_by_rep    ON metrics (rep_email, period DESC);

CREATE TABLE unmatched_rows (
    id              BIGSERIAL PRIMARY KEY,
    import_id       BIGINT NOT NULL REFERENCES imports(id),
    row_index       INTEGER NOT NULL,
    reason          TEXT NOT NULL,              -- e.g. 'rep_not_found', 'ambiguous_name'
    raw_row         JSONB NOT NULL,             -- so a human can review the exact data
    reviewed_at     TIMESTAMPTZ,
    reviewed_by     TEXT
);
