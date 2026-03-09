-- Sink init SQL: create table + index + trigger
-- 由 pwetl 的 init_sql config 執行，不依賴 Docker entrypoint
-- 示範 columns 無法表達的進階 DDL

-- 1. Create table
CREATE TABLE IF NOT EXISTS sales_summary_v3 (
    id           UUID PRIMARY KEY,
    product_id   TEXT,
    product_name TEXT,
    category     TEXT,
    total_sold   INTEGER,
    revenue      DOUBLE PRECISION,
    avg_price    DOUBLE PRECISION,
    time         TIMESTAMPTZ,          -- Collides with Pathway metadata, sink handles it
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Index
CREATE INDEX IF NOT EXISTS idx_sales_summary_v3_revenue
    ON sales_summary_v3 (revenue DESC);

-- 3. Trigger: auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sales_summary_v3_updated_at ON sales_summary_v3;
CREATE TRIGGER trg_sales_summary_v3_updated_at
    BEFORE INSERT OR UPDATE ON sales_summary_v3
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
