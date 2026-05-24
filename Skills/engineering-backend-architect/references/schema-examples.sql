-- Patterns referenced by SKILL.md. Adapt to your domain; do not copy verbatim.

-- ============================================================
-- Soft-delete with partial unique index
-- ============================================================
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,           -- bcrypt
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ NULL
);

-- Email uniqueness only among live rows — lets a deleted user re-register.
CREATE UNIQUE INDEX users_email_live_unique
    ON users (email)
    WHERE deleted_at IS NULL;

-- ============================================================
-- Append-only audit log (event sourcing lite)
-- ============================================================
CREATE TABLE order_events (
    id           BIGSERIAL PRIMARY KEY,
    order_id     UUID NOT NULL,
    event_type   TEXT NOT NULL,                    -- 'created', 'paid', 'refunded'
    payload      JSONB NOT NULL,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor        TEXT                              -- user id or 'system'
);

CREATE INDEX order_events_by_order
    ON order_events (order_id, occurred_at);

-- ============================================================
-- Time-travel / slowly changing dimension (SCD type 2)
-- ============================================================
CREATE TABLE product_prices (
    product_id   UUID NOT NULL,
    price_cents  INTEGER NOT NULL CHECK (price_cents >= 0),
    valid_from   TIMESTAMPTZ NOT NULL,
    valid_to     TIMESTAMPTZ,                       -- NULL = current
    PRIMARY KEY (product_id, valid_from)
);

CREATE UNIQUE INDEX product_prices_current
    ON product_prices (product_id)
    WHERE valid_to IS NULL;

-- ============================================================
-- Full-text search column
-- ============================================================
CREATE INDEX products_name_fts
    ON products
    USING gin (to_tsvector('english', name));
