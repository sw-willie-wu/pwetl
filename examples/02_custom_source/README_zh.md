# 範例 02：自訂資料源

此範例示範如何在 pwetl 中建立自訂資料源。

## 概述

自訂資料源（`RandomDataSource`）產生隨機測試資料。這在以下情況下非常有用：

- 需要測試資料但不想依賴外部資源
- 需要可重現的測試場景（使用 seed）
- 快速建立 Transform 原型

## 自訂資料源實作

### 關鍵組件

```python
class RandomDataSource(BaseSource):
    required_config = ['count']
    optional_config = {
        'seed': None,
        'min_value': 0,
        'max_value': 100,
    }
    
    def read(self) -> pw.Table:
        # 產生資料並返回 Pathway 表格
        pass
```

### 配置選項

- `count`（必需）：要產生的記錄數量
- `seed`（選填）：隨機種子，用於可重現性
- `min_value`（選填）：最小隨機值（預設：0）
- `max_value`（選填）：最大隨機值（預設：100）

## 使用方式

### 執行範例

```bash
cd examples/02_custom_source
pwetl --config config.yaml
```

### 預期輸出

將產生兩個 CSV 檔案：

1. `high_value_output.csv` - value >= 100 的記錄
2. `low_value_output.csv` - value < 100 的記錄

### 資料範例

```csv
id,name,value,category
1,Item_001,150,A
2,Item_002,75,B
3,Item_003,125,C
...
```

## 如何建立自己的自訂資料源

1. **繼承 BaseSource**：

```python
from pwetl.sources import BaseSource
import pathway as pw

class MyCustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default'}
```

2. **實作 `read()` 方法**：

```python
def read(self) -> pw.Table:
    # 你的資料獲取邏輯
    raw_data = fetch_data_somehow()
    
    # 轉換為 tuple 列表（table_from_rows 的要求）
    rows = [(row['field1'], row['field2']) for row in raw_data]
    
    # 取得 schema 並建立 Pathway 表格
    schema = self._get_schema()
    if schema is None:
        raise ValueError(f"Source '{self.name}' requires schema")
    
    table = pw.debug.table_from_rows(schema=schema, rows=rows)
    return table

def _get_schema(self):
    """從配置取得 Pathway schema。"""
    from pwetl.utils.schema import SchemaParser
    schema_config = self.config.get('schema')
    if schema_config:
        return SchemaParser.parse(schema_config)
    return None
```

3. **選填：實作 `setup()` 進行初始化**：

```python
def setup(self) -> None:
    # 初始化連線、驗證配置等
    pass
```

4. **在 config.yaml 中使用**：

```yaml
sources:
  - name: my_data
    type: custom
    module: my_source.MyCustomSource
    param1: value1
    schema:
      field1: str
      field2: int
```

## 實際應用場景

自訂資料源適用於：

1. **專有資料格式**：讀取自訂檔案格式的資料
2. **API 整合**：從原生不支援的 API 獲取資料
3. **資料庫連接器**：連接 PostgreSQL/MySQL 以外的資料庫
4. **訊息佇列**：從 Kafka、RabbitMQ 等讀取
5. **雲端儲存**：從 S3、Azure Blob、GCS 獲取資料
6. **網路爬蟲**：從網站擷取資料
7. **IoT 裝置**：直接讀取感測器資料

## 提示

- 使用 `self._get_schema()` 從配置取得 Pathway schema
- 使用 `self.config` 存取配置值
- `table_from_rows()` 需要 **tuple 列表**，不是 dict 列表
- Schema 必須符合 tuple 順序（第一個欄位 → 第一個元素，依此類推）
- 避免使用 `id` 作為欄位名（Pathway 保留字）
- 在 `setup()` 中進行昂貴的初始化（連線、認證）
- 對於批次/靜態資料使用 `pw.debug.table_from_rows()`
- 對於串流資料使用 connectors（參考 API source 實作）

## 參考

- [自訂 Sink 範例](../03_custom_sink/)
- [API Source 範例](../01_api_source/)
- [BaseSource 文件](../../src/pwetl/sources/base.py)
