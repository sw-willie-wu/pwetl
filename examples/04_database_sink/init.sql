-- Create target table for the database sink example
-- Used by Docker entrypoint; config_static.yaml writes to this table
CREATE TABLE IF NOT EXISTS sales_summary (
    id           UUID,
    product_id   TEXT,
    product_name TEXT,
    category     TEXT,
    total_sold   INTEGER,
    revenue      DOUBLE PRECISION,
    avg_price    DOUBLE PRECISION,
    time         TIMESTAMPTZ             -- latest order date (demonstrates Pathway metadata collision handling)
);
