-- Create target table for the database sink example
CREATE TABLE IF NOT EXISTS sales_summary (
    product_id   INTEGER,
    product_name TEXT,
    category     TEXT,
    total_sold   INTEGER,
    revenue      DOUBLE PRECISION,
    avg_price    DOUBLE PRECISION
);
