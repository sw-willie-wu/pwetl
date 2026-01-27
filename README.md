# pwetl

一個基於 Pathway 的靈活 ETL（Extract, Transform, Load）框架。pwetl 讓你只需要編寫 Transform 類別和 YAML 配置檔，就能快速建立 ETL 服務。

## ✨ 特性

- **宣告式配置**：透過簡單的 YAML 配置檔定義 ETL pipeline
- **多源多匯**：支援多個資料源和多個輸出目標
- **豐富的資料源**：
  - 檔案：CSV、JSON、JSONL、Parquet
  - API：REST API（支援自訂 Headers、參數等）
  - 資料庫：PostgreSQL、MySQL
- **多種輸出方式**：
  - 檔案：CSV、JSON、JSONL、Parquet
  - 資料庫：PostgreSQL、MySQL
  - **API：POST JSON 資料到 API endpoint**（支援重試、自訂 Headers）
- **環境變數支援**：使用 `${VAR_NAME}` 語法安全管理敏感資訊
- **可擴展**：輕鬆建立自訂 Source/Sink/Transform
- **型態安全**：使用 Pathway Schema 驗證資料
- **基於 Pathway**：利用 Pathway 強大的流式處理能力

## 📦 安裝

**重要**：Pathway 需要 Linux 環境，請在 WSL 或 Linux 中執行。

```bash
# 使用 uv（推薦）
uv sync

# 或使用 pip
pip install -e .
```

詳細安裝說明請查看 [安裝指南](docs/installation.md)。

## 🚀 快速開始

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

        # 轉換邏輯
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
    type: csv
    path: users.csv
    schema:
      id: int
      name: str
      email: str

transform: transform.MyTransform

sinks:
  - name: output
    type: csv
    path: output.csv
```

### 3. 執行

```bash
# 在 WSL/Linux 環境中執行
python -m pwetl.cli --config config.yaml

# 詳細模式
python -m pwetl.cli --config config.yaml --verbose

# 只驗證配置
python -m pwetl.cli --config config.yaml --dry-run
```

## 📖 文件

- [安裝指南](docs/installation.md)
- [使用指南](docs/usage.md)
- [環境變數配置](docs/environment-variables.md)
- [多源多匯設計](docs/multi-source-sink.md)

## 🎯 範例

專案提供完整的範例展示各種使用場景：

### 範例 1：基本 CSV 轉換

[examples/01_basic_csv/](examples/01_basic_csv/)

基礎的 CSV 檔案讀取、轉換、輸出流程。

### 範例 2：水利署 API 資料

[examples/02_wra_waterlevel/](examples/02_wra_waterlevel/)

從台灣水利署 API 讀取即時水位資料，示範：

- API Source 使用
- Static 和 Streaming 模式
- 資料 Schema 定義
- CSV 輸出

### 範例 3：多源資料整合

[examples/03_multi_source/](examples/03_multi_source/)

整合多個資料源（API + File + Database），示範：

- 多個資料源 (API、CSV、PostgreSQL)
- 資料 JOIN 操作
- 多個輸出目標 (CSV、API、Database)
- 環境變數配置

### 範例 4：資料夾監測與檔案過濾

[examples/04_folder_monitor/](examples/04_folder_monitor/)

監測資料夾並過濾特定檔案，示範：

- 資料夾監測（批次/串流模式）
- 正則表達式過濾檔名
- Glob Pattern 過濾
- 自動處理新檔案

每個範例都包含完整的配置檔案、Transform 邏輯和使用說明。

## 🔧 擴展

### 自訂 Source

```python
from pwetl.sources import BaseSource
import pathway as pw

class MongoDBSource(BaseSource):
    required_config = ['uri', 'collection']

    def read(self):
        # 實作讀取邏輯
        return table

# 註冊
from pwetl import SOURCE_REGISTRY
SOURCE_REGISTRY['mongodb'] = MongoDBSource
```

或在 YAML 中動態載入：

```yaml
sources:
  - name: data
    type: custom
    module: my_sources.py
    class: MongoDBSource
    uri: mongodb://localhost
    collection: my_collection
```

### 自訂 Sink

```python
from pwetl.sinks import BaseSink

class CustomSink(BaseSink):
    def write(self, table):
        # 實作寫入邏輯
        pass
```

## 🏗️ 專案結構

```
pwetl/
├── src/pwetl/
│   ├── __init__.py
│   ├── cli.py              # CLI 入口
│   ├── core/
│   │   ├── config.py       # 配置載入器
│   │   ├── engine.py       # ETL 引擎
│   │   ├── pipeline.py     # Pipeline 編排
│   │   └── registry.py     # Source/Sink Registry
│   ├── sources/
│   │   ├── base.py         # BaseSource
│   │   ├── file.py         # FileSource
│   │   ├── api.py          # APISource
│   │   └── database.py     # DatabaseSource
│   ├── sinks/
│   │   ├── base.py         # BaseSink
│   │   ├── file.py         # FileSink
│   │   ├── api.py          # APISink ⭐ 新增
│   │   └── database.py     # DatabaseSink
│   ├── transforms/
│   │   └── base.py         # BaseTransform
│   └── utils/
│       ├── env.py          # 環境變數處理
│       ├── loader.py       # 動態載入
│       └── schema.py       # Schema 解析
├── examples/               # 範例
└── docs/                   # 文件
```

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## 💡 設計理念

1. **簡單優先** - 常見場景要簡單直接
2. **可擴展** - 但不過度設計
3. **宣告式** - YAML 配置優於程式碼
4. **型態安全** - 用 Schema 確保正確性

## ⚙️ 技術棧

- **Pathway**: 流式資料處理引擎
- **PyYAML**: YAML 配置解析
- **Requests**: HTTP 請求（API Source/Sink）
- **psycopg2**: PostgreSQL 連接
- **mysql-connector-python**: MySQL 連接
