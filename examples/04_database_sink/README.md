# Example 04: Database Sink

Write processed data to a database using SQLAlchemy DSN. This example reads sales orders from CSV, aggregates them by product, and inserts the summary into PostgreSQL.

## Features

- **Database Sink**: Write to any SQLAlchemy-compatible database via DSN
- **Docker**: One-command PostgreSQL setup for local testing
- **Static / Streaming**: Run once or watch a directory for new files
- **Environment Variables**: DSN parameters configurable via `${VAR}` with defaults

## Quick Start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

This creates a `pwetl_demo` database with a `sales_summary` table (via `init.sql`).

### 2. Install Dependencies

```bash
# From project root
pip install -e ".[database]"
# or
uv sync --extra database
```

### 3. Run

```bash
cd examples/04_database_sink

# Static mode — read CSV once, insert into DB
pwetl --config config_static.yaml

# Streaming mode — watch CSV for changes, auto-create table
pwetl --config config_streaming.yaml
```

### 4. Verify

```bash
# Check file output
cat output/sales_summary.csv

# Check database
docker exec pwetl_postgres psql -U pwetl -d pwetl_demo -c "SELECT * FROM sales_summary ORDER BY revenue DESC;"
```

Expected output (6 products aggregated from 15 orders):

```
 product_id | product_name      | category    | total_sold | revenue | avg_price
------------+-------------------+-------------+------------+---------+-----------
 P05        | Mechanical Keyboard| Electronics |          3 |  269.97 |     89.99
 P01        | Wireless Mouse    | Electronics |          6 |  179.94 |     29.99
 P02        | Python Cookbook    | Books       |          4 |  180.00 |     45.00
 P03        | USB-C Hub         | Electronics |          5 |  199.95 |     39.99
 P06        | Desk Lamp         | Electronics |          4 |  140.00 |     35.00
 P04        | Notebook A5       | Stationery  |         23 |  126.50 |      5.50
```

### 5. Cleanup

```bash
docker compose down -v
```

## Configuration

### config_static.yaml

```yaml
sinks:
  - name: db_output
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5436/pwetl_demo
    table: sales_summary
```

### config_streaming.yaml

Watches `sales_data.csv` for changes. Writes to `sales_summary_v2` with `columns` — the table is auto-created if it doesn't exist.

### config_init_sql.yaml

Uses `init_sql: init.sql` to execute custom DDL before writing. Useful when you need advanced DDL control (indexes, triggers, etc.) that `columns` can't express.

## Pipeline Flow

```
sales_data.csv --> SalesTransform --> PostgreSQL (sales_summary)
                   (group by product,
                    sum quantity/revenue,
                    avg price)
```

## Files

| File | Description |
|------|-------------|
| `docker-compose.yaml` | PostgreSQL 16 container |
| `init.sql` | Creates `sales_summary` table (Docker entrypoint) |
| `sink_init.sql` | Creates `sales_summary_v3` table + index (pwetl `init_sql`) |
| `sales_data.csv` | 15 sample sales orders |
| `transform.py` | Aggregates orders by product |
| `config_static.yaml` | Static mode (table must exist) |
| `config_streaming.yaml` | Streaming mode (auto-create table via `columns`) |
| `config_init_sql.yaml` | Static mode (auto-create table via `init_sql`) |
| `.env.example` | Environment variable template |

## Using Other Databases

Change the DSN to target any SQLAlchemy-compatible database:

```yaml
# MySQL
dsn: mysql+pymysql://user:pass@localhost:3306/mydb

# MSSQL
dsn: mssql+pyodbc://user:pass@localhost:1433/mydb?driver=ODBC+Driver+18+for+SQL+Server

# SQLite (for quick local testing, no Docker needed)
dsn: sqlite:///local.db
```
