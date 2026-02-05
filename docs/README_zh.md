# pwetl

一個基於 Pathway 的靈活 ETL（Extract, Transform, Load）框架。pwetl 讓你只需要編寫 Transform 類別和 YAML 配置檔，就能快速建立 ETL 服務。

## 特性

- **宣告式配置**：透過簡單的 YAML 配置檔定義 ETL pipeline
- **多源多匯**：支援多個資料源和多個輸出目標
- **豐富的資料源**：
  - 檔案：CSV、JSON、JSONL（File Source）
  - API：REST API，支援 Static/Streaming 模式
  - 資料庫：PostgreSQL、MySQL
- **多種輸出方式**：
  - 檔案：CSV、JSON、JSONL（File Sink）
  - 資料庫：PostgreSQL、MySQL
  - API：POST JSON 資料到 API endpoint
- **資料驗證**：
  - 整合 Pydantic 驗證模型
  - 三種驗證模式：none（略過）、sample（警告）、strict（強制）
  - 自動類型轉換（datetime、數值等）
- **環境變數支援**：使用 `${VAR_NAME}` 語法安全管理敏感資訊
- **可擴展**：輕鬆建立自訂 Source/Sink/Transform
- **基於 Pathway**：利用 Pathway 強大的流式處理能力

## 安裝

**重要**：Pathway 需要 Linux 環境，請在 WSL 或 Linux 中執行。

```bash
# 使用 uv（推薦）
uv sync

# 或使用 pip
pip install -e .
```

詳細安裝說明請查看 [安裝指南](docs/installation.md)。

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

# 詳細模式
pwetl --config config.yaml --verbose

# 只驗證配置
pwetl --config config.yaml --dry-run
```

## 文件

- [安裝指南](docs/installation.md)
- [使用指南](docs/usage.md)
- [環境變數配置](docs/environment-variables.md)
- [多源多匯設計](docs/multi-source-sink.md)
- [更新日誌](docs/CHANGELOG.md)

## 範例

專案提供完整的範例展示各種使用場景：

### 範例 1：YouBike API 資料

[examples/01_api_source/](examples/01_api_source/)

從 YouBike API 讀取即時站點資料，示範：

- API Source 使用（Static/Streaming 模式）
- 環境變數配置（`.env` 檔案）
- 資料驗證（Pydantic + 驗證模式）
- Datetime 類型自動轉換
- 多格式輸出（CSV、JSON、JSONL）

每個範例都包含完整的配置檔案、Transform 邏輯和使用說明。

## 擴展

### 自訂 Source

```python
from pwetl.sources import BaseSource
import pathway as pw

class CustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default_value'}

    def read(self) -> pw.Table:
        # 實作讀取邏輯
        return table
```

在 YAML 中使用：

```yaml
sources:
  - name: data
    type: custom
    module: my_sources.py
    class: CustomSource
    param1: value1
```

### 自訂 Sink

```python
from pwetl.sinks import BaseSink
import pathway as pw

class CustomSink(BaseSink):
    required_config = ['param1']
    
    def write(self, table: pw.Table) -> None:
        # 實作寫入邏輯
        pass
```

在 YAML 中使用：

```yaml
sinks:
  - name: output
    type: custom
    module: my_sinks.py
    class: CustomSink
    param1: value1
```

## 專案結構

```
src/pwetl/
├── cli.py              # CLI 入口（pwetl 命令）
├── core/
│   ├── config.py       # 配置載入器
│   ├── engine.py       # ETL 引擎
│   ├── pipeline.py     # Pipeline 編排
│   └── registry.py     # Source/Sink Registry
├── sources/
│   ├── base.py         # BaseSource（含驗證框架）
│   ├── file.py         # FileSource（CSV/JSON/JSONL）
│   ├── api.py          # APISource（REST API）
│   └── database.py     # DatabaseSource（PostgreSQL/MySQL）
├── sinks/
│   ├── base.py         # BaseSink
│   ├── file.py         # FileSink（CSV/JSON/JSONL）
│   ├── api.py          # APISink（POST JSON）
│   └── database.py     # DatabaseSink（PostgreSQL/MySQL）
├── transforms/
│   └── base.py         # BaseTransform
└── utils/
    ├── env.py          # 環境變數處理
    ├── loader.py       # 動態載入
    └── schema.py       # Schema 解析（Pathway + Pydantic）
```

## 授權

MIT License
