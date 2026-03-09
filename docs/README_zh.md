# pwetl

一個基於 Pathway 的靈活 ETL（Extract, Transform, Load）框架。pwetl 讓你只需要編寫 Transform 類別和 YAML 配置檔，就能快速建立 ETL 服務。

## 特性

- **宣告式配置**：透過簡單的 YAML 配置檔定義 ETL pipeline
- **多源多匯**：支援多個資料源和多個輸出目標
- **豐富的資料源**：
  - 檔案：CSV、JSON、JSONL
  - API：REST API，支援 Static/Streaming 模式
  - 資料庫：任何 SQLAlchemy 相容的資料庫（PostgreSQL、MySQL、MSSQL 等）
- **多種輸出方式**：
  - 檔案：CSV、JSON、JSONL
  - 資料庫：任何 SQLAlchemy 相容的資料庫（PostgreSQL、MySQL、MSSQL 等）
  - API：POST/PUT 資料到 API endpoint
- **串流去重**：基於 Hash 的差異追蹤，搭配 `diff_ignore_fields` — 只發送新增/變更的記錄
- **資料驗證**：
  - 整合 Pydantic 驗證模型
  - 三種驗證模式：`none`（略過）、`sample`（警告）、`strict`（強制）
  - 自動類型轉換（datetime、數值等）
- **環境變數支援**：使用 `${VAR_NAME}` 語法安全管理敏感資訊，支援預設值
- **SSH 隧道**：透過 SSH 跳板安全連線到資料庫
- **可擴展**：輕鬆建立自訂 Source/Sink/Transform
- **基於 Pathway**：利用 Pathway 串流引擎，支援靜態和即時 pipeline

## 安裝

**重要**：Pathway 需要 Linux 環境，請在 WSL 或 Linux 中執行。

```bash
# 使用 uv（推薦）
uv sync

# 或使用 pip
pip install -e .

# 安裝資料庫支援（SQLAlchemy）
pip install -e ".[database]"

# 安裝 SSH 隧道支援
pip install -e ".[ssh]"

# 安裝全部選用依賴
pip install -e ".[all]"
```

詳細安裝說明請查看 [安裝指南](installation.md)。

## 快速開始

### 1. 定義 Transform

建立 `transform.py`：

```python
from pwetl.transforms import BaseTransform
import pathway as pw

class MyTransform(BaseTransform):
    def transform(self, tables):
        """處理資料。

        Args:
            tables: Dict[source_name, pw.Table]

        Returns:
            Dict[sink_name, pw.Table]
        """
        users = tables['users']

        result = users.select(
            id=pw.this.id,
            name=pw.this.name.str.upper(),
        )

        return {'output': result}
```

### 2. 建立配置檔

建立 `config.yaml`：

```yaml
sources:
  - name: users
    type: file
    path: users.csv
    format: csv
    schema:
      id: int
      name: str
      email: str

transform: transform.MyTransform

sinks:
  - name: output
    type: file
    path: output.csv
    format: csv
```

### 3. 執行

```bash
# 基本執行
pwetl --config config.yaml

# 詳細模式（DEBUG 日誌）
pwetl --config config.yaml --verbose

# 只驗證配置
pwetl --config config.yaml --dry-run

# 指定 .env 檔案
pwetl --config config.yaml --env-file .env.production

# 自訂日誌配置
pwetl --config config.yaml --log-config logging.yaml
```

## 資料源類型

### File Source

```yaml
sources:
  - name: data
    type: file          # 或 csv, json, jsonl
    path: data.csv
    format: csv         # csv, json, jsonl
    mode: static        # static（預設）或 streaming
    schema:
      id: int
      name: str
```

### API Source

```yaml
sources:
  - name: api_data
    type: api
    url: https://api.example.com/data
    method: GET
    headers:
      Authorization: "Bearer ${API_TOKEN}"
    params:
      limit: 100
    data_path: results.data    # JSON 路徑，提取巢狀資料
    timeout: 30
    mode: streaming
    refresh_interval: 60       # 輪詢間隔（秒）
    diff_ignore_fields:        # 偵測變更時忽略的欄位
      - updated_at
      - last_modified
    validation_mode: sample
    schema:
      id: int
      name: str
      value: float
```

### Database Source

```yaml
sources:
  - name: db_data
    type: database
    dsn: postgresql://user:pass@host:5432/mydb
    table: users               # 或使用 query_sql: query.sql
    mode: streaming
    refresh_interval: 60
    diff_ignore_fields:
      - modified_at
    schema:
      id: int
      name: str
    ssh_tunnel:                # 選用 SSH 隧道
      host: jump-server
      username: ssh_user
      private_key: ~/.ssh/id_rsa
```

## 輸出類型

### File Sink

```yaml
sinks:
  - name: output
    type: file
    path: output/result.csv
    format: csv                # csv, json, jsonl（可從副檔名自動偵測）
```

### API Sink

```yaml
sinks:
  - name: api_output
    type: api
    url: https://api.example.com/ingest
    method: POST
    headers:
      Authorization: "Bearer ${API_TOKEN}"
    batch_size: 100
    max_retry: 3
    timeout: 30
```

### Database Sink

```yaml
sinks:
  - name: db_output
    type: database
    dsn: postgresql://user:${DB_PASSWORD}@localhost:5432/mydb
    table: output_table
    write_mode: upsert         # insert（預設）或 upsert
    primary_key: [id]          # upsert 必填
    columns:                   # 選用：自動建表
      id: uuid, pk
      name: varchar(100)
      lat: float
      lng: float
    # init_sql: setup.sql      # 替代方案：從 SQL 檔案執行進階 DDL
    # dialect: postgresql       # 選用：覆寫自動偵測
    ssh_tunnel:                # 選用 SSH 隧道
      host: jump-server
      username: ssh_user
      private_key: ~/.ssh/id_rsa
```

## 串流模式與去重

在串流模式下，資料源會定期輪詢。為避免重複發送未變更的記錄，可設定 `diff_ignore_fields` 排除易變欄位（如時間戳記）：

```yaml
sources:
  - name: youbike
    type: api
    url: https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
    mode: streaming
    refresh_interval: 60
    diff_ignore_fields:
      - mday
      - srcUpdateTime
      - updateTime
      - infoTime
      - infoDate
```

```
poll 1: 1733 筆 → 1733 筆新資料（首次輪詢，無前次可比對）
poll 2: 1733 筆 →    0 筆新資料（只有時間變更，跳過）
poll 3: 1733 筆 →    5 筆新資料（5 個站點的車輛數有變動）
```

## 資料驗證

每個資料源可獨立設定驗證模式：

| 模式 | 行為 |
|------|------|
| `none` | 完全跳過驗證 |
| `sample` | 驗證並警告錯誤，保留原始資料 |
| `strict` | 驗證全部記錄，遇錯即停 |

Schema 類型：`int`、`str`、`float`、`bool`、`datetime`、`dict`、`list`。加 `?` 表示選填欄位（如 `address: str?`）。

## 環境變數

在 YAML 配置中使用 `${VAR_NAME}` 語法，支援預設值 `${VAR_NAME:預設值}`。

```yaml
sources:
  - name: api
    type: api
    url: ${API_URL:https://fallback.example.com/data}
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

自動載入 `.env` 檔案，或使用 `--env-file` 指定。

## 擴展

### 自訂 Source

```python
from pwetl.sources import BaseSource
import pathway as pw

class CustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default_value'}

    def setup(self) -> None:
        pass  # 初始化資源

    def read(self) -> pw.Table:
        pass  # 回傳 pw.Table

    def teardown(self) -> None:
        pass  # 清理資源
```

### 自訂 Sink

```python
from pwetl.sinks import BaseSink
import pathway as pw

class CustomSink(BaseSink):
    required_config = ['param1']

    def write(self, table: pw.Table) -> None:
        pass  # 實作寫入邏輯
```

在 YAML 中使用 `type: custom` 註冊：

```yaml
sources:
  - name: data
    type: custom
    module: my_module.CustomSource
    param1: value1
```

## 範例

| 範例 | 說明 |
|------|------|
| [01_api_source](../examples/01_api_source/) | YouBike API — 靜態/串流模式、Schema 驗證、多格式輸出、`diff_ignore_fields` |
| [02_database_source](../examples/02_database_source/) | Database Source — 透過 SQLAlchemy DSN 從 PostgreSQL 讀取（附 Docker） |
| [03_api_sink](../examples/03_api_sink/) | API Sink — POST 處理後的資料到遠端 endpoint |
| [04_database_sink](../examples/04_database_sink/) | Database Sink — 透過 SQLAlchemy DSN 寫入 PostgreSQL（附 Docker） |
| [05_custom_source](../examples/05_custom_source/) | 自訂資料源 — 合成資料產生、多 Sink 路由 |
| [06_custom_sink](../examples/06_custom_sink/) | 自訂 Sink — Markdown 報表產生、自訂 JSONL 輸出 |

## 專案結構

```
src/pwetl/
├── cli.py                    # CLI 入口（pwetl 命令）
├── core/
│   ├── config.py             # 配置載入器
│   ├── engine.py             # ETL 引擎
│   ├── exceptions.py         # 自訂例外
│   ├── pipeline.py           # Pipeline 編排
│   ├── registry.py           # Source/Sink 註冊表與工廠
│   └── schema.py             # 配置 Schema 模型
├── sources/
│   ├── base.py               # BaseSource（含驗證框架）
│   ├── file.py               # FileSource（CSV/JSON/JSONL）
│   ├── api.py                # APISource（REST API）
│   ├── database.py           # DatabaseSource（SQLAlchemy + SSH 隧道）
│   └── connector/            # 串流 Connector 實作
│       ├── base.py           # HashDiffConnectorMixin（去重）
│       ├── api.py            # APIConnectorSubject
│       └── database.py       # DatabaseConnectorSubject
├── sinks/
│   ├── base.py               # BaseSink
│   ├── file.py               # FileSink（CSV/JSON/JSONL）
│   ├── api.py                # APISink（POST/PUT to API）
│   ├── database.py           # DatabaseSink（SQLAlchemy DSN + dialect 策略）
│   └── dialect/              # 資料庫 dialect 實作
│       ├── base.py           # BaseDialect（抽象介面）
│       ├── default.py        # DefaultDialect（raw SQL fallback）
│       └── postgres.py       # PostgresDialect（ON CONFLICT upsert）
├── transforms/
│   └── base.py               # BaseTransform
└── utils/
    ├── env.py                # 環境變數替換
    ├── loader.py             # 動態類別載入
    ├── logger.py             # 日誌配置
    └── schema.py             # Schema 解析（Pathway + Pydantic）
```

## 文件

- [安裝指南](installation.md)
- [使用指南](usage.md)
- [環境變數配置](environment-variables.md)
- [多源多匯設計](multi-source-sink.md)
- [更新日誌](CHANGELOG.md)

## 授權

MIT License
