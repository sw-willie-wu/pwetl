# 使用指南

## CLI 使用

pwetl 提供命令列介面，讓你可以直接從終端機執行 ETL pipeline。

### 基本用法

```bash
pwetl --config config.yaml
```

### 命令列選項

#### `--config` (必需)

指定 YAML 配置檔路徑。

```bash
pwetl --config config.yaml
pwetl --config examples/01_api_source/config_static.yaml
```

#### `--verbose`, `-v`

啟用詳細輸出，顯示更多執行資訊。

```bash
pwetl --config config.yaml --verbose
pwetl --config config.yaml -v
```

#### `--dry-run`

驗證配置檔而不實際執行 pipeline（試運行模式）。

```bash
pwetl --config config.yaml --dry-run
```

這會檢查：
- 配置檔是否存在
- YAML 語法是否正確
- 必要欄位是否存在
- Transform 模組是否可以載入

## 配置檔結構

### 基本結構

```yaml
# 資料源配置（單個或多個）
sources:
  - name: users               # Source 名稱
    type: file                # Source 類型
    path: users.csv           # 檔案路徑
    format: csv               # 檔案格式
    schema:                   # 資料結構定義
      id: int
      name: str
      email: str

# Transform 配置
transform: transform.MyTransform  # Transform 類別路徑

# 輸出目標配置（單個或多個）
sinks:
  - name: output              # Sink 名稱
    type: file                # Sink 類型
    path: output.csv          # 輸出路徑
    format: csv               # 輸出格式
```

### Source 類型

#### File Source

```yaml
sources:
  - name: data
    type: file
    path: data.csv            # 檔案路徑或 glob pattern
    format: csv               # csv, json, jsonl
    schema:
      id: int
      name: str
```

#### API Source

```yaml
sources:
  - name: api_data
    type: api
    url: ${API_URL}           # API endpoint
    mode: static              # static 或 streaming
    refresh_interval: 60      # streaming 模式的更新間隔（秒）
    validation_mode: sample   # none, sample, strict
    pydantic_model: models.MyModel
    schema:
      id: int
      value: str
```

#### Database Source

```yaml
sources:
  - name: db_data
    type: postgres            # 或 mysql
    host: ${DB_HOST}
    port: 5432
    database: ${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    query: "SELECT * FROM users"
    schema:
      id: int
      name: str
```

### Sink 類型

#### File Sink

```yaml
sinks:
  - name: output
    type: file
    path: output.csv
    format: csv               # csv, json, jsonl
```

#### Database Sink

```yaml
sinks:
  - name: db_output
    type: postgres            # 或 mysql
    host: localhost
    port: 5432
    database: mydb
    username: user
    password: pass
    table: output_table
```

#### API Sink

```yaml
sinks:
  - name: api_output
    type: api
    url: https://api.example.com/data
    method: POST
```

### Schema 定義

支援的型別：

```yaml
schema:
  # 基本型別
  id: int
  name: str
  price: float
  active: bool
  
  # 日期時間（會轉換為字串，因為 Pathway 的限制）
  created_at: str
  
  # Optional 型別（使用 Pydantic 驗證時）
  address: str?             # Optional[str]
  age: int?                 # Optional[int]
```

### 資料驗證

使用 Pydantic 模型進行資料驗證：

```yaml
sources:
  - name: data
    type: api
    url: ${API_URL}
    validation_mode: sample   # none, sample, strict
    pydantic_model: models.MyModel
```

**驗證模式：**
- `none`: 跳過驗證
- `sample`: 驗證第一筆資料，失敗時警告但繼續
- `strict`: 驗證所有資料，失敗時中斷執行

## 使用範例

### 範例 1：基本 CSV 轉換

```bash
cd my-test/01_basic_csv
pwetl --config config.yaml
```

### 範例 2：API 資料處理（靜態模式）

```bash
cd examples/01_api_source
pwetl --config config_static.yaml
```

### 範例 3：API 資料處理（串流模式）

```bash
cd examples/01_api_source
pwetl --config config_streaming.yaml
```

### 範例 4：驗證配置

```bash
pwetl --config config.yaml --dry-run --verbose
```

### 範例 5：使用環境變數

```bash
# 確保 .env 檔案存在
pwetl --config config.yaml
```

## 環境變數

在配置檔中使用環境變數：

```yaml
sources:
  - name: api_data
    type: api
    url: ${API_URL}           # 必須設定
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

詳細說明請參考 [環境變數配置指南](environment-variables.md)。

## Transform 編寫

Transform 類別必須繼承 `BaseTransform` 並實作 `transform` 方法：

```python
from pwetl.transforms import BaseTransform
import pathway as pw

class MyTransform(BaseTransform):
    def transform(self, tables):
        """處理資料。

        Args:
            tables: Dict[source_name, pw.Table] - 來自所有 sources 的資料表

        Returns:
            Dict[sink_name, pw.Table] - 輸出到各個 sinks 的資料表
        """
        # 單一 source
        data = tables['data']
        
        # 資料轉換
        result = data.select(
            id=pw.this.id,
            name=pw.this.name.str.upper(),
        )
        
        # 單一 sink
        return {'output': result}
```

### 多 Source 多 Sink

```python
def transform(self, tables):
    # 處理多個 sources
    source1 = tables['source1']
    source2 = tables['source2']
    
    # 合併或 join
    combined = source1.join(source2, ...)
    
    # 輸出到多個 sinks
    return {
        'sink1': result1,
        'sink2': result2,
    }
```

## 進階主題

- [多資料源和多輸出目標](multi-source-sink.md)
- [環境變數配置](environment-variables.md)
- [自訂 Source/Sink](../README.md#擴展)
