# Example 02: Database Source

Read data from a database using SQLAlchemy DSN. This example reads an employees table from PostgreSQL, aggregates by department, and outputs to CSV and JSONL.

## Features

- **Database Source**: Read from any SQLAlchemy-compatible database via DSN
- **Docker**: One-command PostgreSQL setup with seed data
- **Static / Streaming**: Run once or poll periodically for changes
- **Multi-sink output**: Same transform feeds CSV summary + JSONL detail

## Quick Start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

This creates a `pwetl_demo` database with 12 sample employees (via `init.sql`).

### 2. Install Dependencies

```bash
# From project root
pip install -e ".[database]"
# or
uv sync --extra database
```

### 3. Run

```bash
cd examples/02_database_source

# Static mode — run once and exit
pwetl --config config_static.yaml

# Streaming mode — poll every 60s, only emit changed records
pwetl --config config_streaming.yaml

# Custom SQL query file
pwetl --config config_query_file.yaml
```

### 4. Check Output

```bash
cat output/static/department_summary.csv
cat output/static/employees.jsonl
```

### 5. Cleanup

```bash
docker compose down -v
```

## Configuration

### config_static.yaml — Static mode

```yaml
sources:
  - name: employees
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5435/pwetl_demo
    table: employees
    mode: static
```

### config_streaming.yaml — Streaming mode

```yaml
sources:
  - name: employees
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5435/pwetl_demo
    table: employees
    mode: streaming
    refresh_interval: 60
    diff_ignore_fields:
      - hire_date
```

### config_query_file.yaml — Custom SQL

```yaml
sources:
  - name: employees
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5435/pwetl_demo
    query_file: query.sql
```

## Pipeline Flow

```
PostgreSQL (employees) --> DepartmentSummaryTransform --> department_summary.csv
                           (group by department,          employees.jsonl
                            count / avg / max salary)
```

## Files

| File | Description |
|------|-------------|
| `docker-compose.yaml` | PostgreSQL 16 container |
| `init.sql` | Creates and seeds `employees` table (12 rows) |
| `query.sql` | Custom SQL: employees with salary >= 80000 |
| `transform.py` | Aggregates by department |
| `config_static.yaml` | Static mode (run once) |
| `config_streaming.yaml` | Streaming mode (poll every 60s) |
| `config_query_file.yaml` | Custom SQL query file |
| `.env.example` | Environment variable template |

## Using Other Databases

Change the DSN to any SQLAlchemy-compatible database:

```yaml
# MySQL
dsn: mysql+pymysql://user:pass@localhost:3306/mydb

# MSSQL
dsn: mssql+pyodbc://user:pass@localhost:1433/mydb?driver=ODBC+Driver+18+for+SQL+Server

# SQLite (no Docker needed)
dsn: sqlite:///local.db
```
