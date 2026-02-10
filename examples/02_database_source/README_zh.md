# 範例 02：Database Source

使用 SQLAlchemy DSN 從資料庫讀取資料。本範例從 PostgreSQL 讀取員工資料表，按部門聚合後，輸出為 CSV 和 JSONL。

## 特性

- **Database Source**：透過 DSN 讀取任何 SQLAlchemy 相容的資料庫
- **Docker**：一鍵啟動 PostgreSQL，含種子資料
- **Static / Streaming**：執行一次或定期輪詢偵測變更
- **多 Sink 輸出**：同一個 transform 同時輸出 CSV 摘要 + JSONL 明細

## 快速開始

### 1. 啟動 PostgreSQL

```bash
docker compose up -d
```

會建立 `pwetl_demo` 資料庫，並透過 `init.sql` 新增 12 筆範例員工資料。

### 2. 安裝依賴

```bash
# 在專案根目錄
pip install -e ".[database]"
# 或
uv sync --extra database
```

### 3. 執行

```bash
cd examples/02_database_source

# Static 模式 — 執行一次後結束
pwetl --config config_static.yaml

# Streaming 模式 — 每 60 秒輪詢，僅發送變更記錄
pwetl --config config_streaming.yaml

# 自訂 SQL 查詢檔
pwetl --config config_query_file.yaml
```

### 4. 檢查結果

```bash
cat output/static/department_summary.csv
cat output/static/employees.jsonl
```

### 5. 清理

```bash
docker compose down -v
```

## 配置說明

### config_static.yaml — Static 模式

```yaml
sources:
  - name: employees
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5435/pwetl_demo
    table: employees
    mode: static
```

### config_streaming.yaml — Streaming 模式

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

### config_query_file.yaml — 自訂 SQL

```yaml
sources:
  - name: employees
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5435/pwetl_demo
    query_file: query.sql
```

## Pipeline 流程

```
PostgreSQL (employees) --> DepartmentSummaryTransform --> department_summary.csv
                           (按部門聚合，                     employees.jsonl
                            人數 / 平均 / 最高薪資)
```

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `docker-compose.yaml` | PostgreSQL 16 容器 |
| `init.sql` | 建立並填入 `employees` 資料表（12 筆） |
| `query.sql` | 自訂 SQL：薪資 >= 80000 的員工 |
| `transform.py` | 按部門聚合 |
| `config_static.yaml` | Static 模式（執行一次） |
| `config_streaming.yaml` | Streaming 模式（每 60 秒輪詢） |
| `config_query_file.yaml` | 自訂 SQL 查詢檔 |
| `.env.example` | 環境變數範本 |

## 使用其他資料庫

修改 DSN 即可讀取任何 SQLAlchemy 相容的資料庫：

```yaml
# MySQL
dsn: mysql+pymysql://user:pass@localhost:3306/mydb

# MSSQL
dsn: mssql+pyodbc://user:pass@localhost:1433/mydb?driver=ODBC+Driver+18+for+SQL+Server

# SQLite（不需 Docker）
dsn: sqlite:///local.db
```
