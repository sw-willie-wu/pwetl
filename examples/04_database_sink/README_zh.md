# 範例 04：Database Sink

使用 SQLAlchemy DSN 將處理後的資料寫入資料庫。本範例從 CSV 讀取銷售訂單，按產品聚合後，將摘要寫入 PostgreSQL。

## 特性

- **Database Sink**：透過 DSN 寫入任何 SQLAlchemy 相容的資料庫
- **Docker**：一鍵啟動 PostgreSQL，方便本地測試
- **Static / Streaming**：執行一次或持續監聽目錄中的新檔案
- **環境變數**：DSN 參數支援 `${VAR}` 語法及預設值

## 快速開始

### 1. 啟動 PostgreSQL

```bash
docker compose up -d
```

會建立 `pwetl_demo` 資料庫，並透過 `init.sql` 建立 `sales_summary` 資料表。

### 2. 安裝依賴

```bash
# 在專案根目錄
pip install -e ".[database]"
# 或
uv sync --extra database
```

### 3. 執行

```bash
cd examples/04_database_sink

# Static 模式 — 讀取 CSV 一次，寫入資料庫
pwetl --config config_static.yaml

# Streaming 模式 — 持續監聽 CSV 變更，自動建表
pwetl --config config_streaming.yaml
```

### 4. 驗證結果

```bash
# 檢查檔案輸出
cat output/sales_summary.csv

# 檢查資料庫
docker exec pwetl_postgres psql -U pwetl -d pwetl_demo -c "SELECT * FROM sales_summary ORDER BY revenue DESC;"
```

預期輸出（15 筆訂單聚合為 6 個產品）：

```
 product_id | product_name       | category    | total_sold | revenue | avg_price
------------+--------------------+-------------+------------+---------+-----------
 P05        | Mechanical Keyboard| Electronics |          3 |  269.97 |     89.99
 P01        | Wireless Mouse     | Electronics |          6 |  179.94 |     29.99
 P02        | Python Cookbook     | Books       |          4 |  180.00 |     45.00
 P03        | USB-C Hub          | Electronics |          5 |  199.95 |     39.99
 P06        | Desk Lamp          | Electronics |          4 |  140.00 |     35.00
 P04        | Notebook A5        | Stationery  |         23 |  126.50 |      5.50
```

### 5. 清理

```bash
docker compose down -v
```

## 配置說明

### config_static.yaml

```yaml
sinks:
  - name: db_output
    type: database
    dsn: postgresql://pwetl:pwetl_pass@localhost:5436/pwetl_demo
    table: sales_summary
```

### config_streaming.yaml

持續監聽 `sales_data.csv`，有變更時寫入 `sales_summary_v2`，搭配 `columns` 自動建表 — 資料表不需要事先存在。

### config_init_sql.yaml

使用 `init_sql: sink_init.sql` 執行自訂 DDL（CREATE TABLE + INDEX + TRIGGER）。適合需要進階 DDL 控制的場景（`columns` 無法表達的）。

## Pipeline 流程

```
sales_data.csv --> SalesTransform --> PostgreSQL (sales_summary)
                   (按產品聚合，
                    加總數量/營收，
                    平均單價)
```

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `docker-compose.yaml` | PostgreSQL 16 容器 |
| `init.sql` | 建立 `sales_summary` 資料表（Docker entrypoint） |
| `sink_init.sql` | 建立 `sales_summary_v3` 資料表 + index（pwetl `init_sql`） |
| `sales_data.csv` | 15 筆範例銷售訂單 |
| `transform.py` | 按產品聚合訂單 |
| `config_static.yaml` | Static 模式（資料表需存在） |
| `config_streaming.yaml` | Streaming 模式（透過 `columns` 自動建表） |
| `config_init_sql.yaml` | Static 模式（透過 `init_sql` 自動建表） |
| `.env.example` | 環境變數範本 |

## 使用其他資料庫

修改 DSN 即可寫入任何 SQLAlchemy 相容的資料庫：

```yaml
# MySQL
dsn: mysql+pymysql://user:pass@localhost:3306/mydb

# MSSQL
dsn: mssql+pyodbc://user:pass@localhost:1433/mydb?driver=ODBC+Driver+18+for+SQL+Server

# SQLite（快速本地測試，不需 Docker）
dsn: sqlite:///local.db
```
