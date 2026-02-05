# 範例 03：自訂輸出目標

此範例示範如何在 pwetl 中建立自訂 Sink。

## 概述

此範例包含兩個自訂 Sink：

1. **MarkdownReportSink**：產生格式化的 Markdown 報告，包含統計摘要
2. **JSONLSink**：簡單的自訂 JSONL 寫入器（展示基本 Sink 模式）

當你需要將資料輸出到 pwetl 原生不支援的格式或目標時，自訂 Sink 非常有用。

## 自訂 Sink 實作

### MarkdownReportSink

產生 Markdown 報告，包含：
- 標題和元資料
- 統計摘要（數量、最小值、最大值、平均值）
- 格式化的資料表格
- 限制顯示前 100 筆記錄以提高可讀性

**配置選項：**
- `path`（必需）：輸出檔案路徑
- `title`（選填）：報告標題（預設：「Data Report」）
- `include_summary`（選填）：是否包含統計資訊（預設：true）

### JSONLSink

展示基本 Sink 模式的簡單範例。

**配置選項：**
- `path`（必需）：輸出檔案路徑

## 使用方式

### 執行範例

```bash
cd examples/03_custom_sink
pwetl --config config.yaml
```

### 預期輸出

將在 `output/` 目錄中產生兩個檔案：

1. **report.md**：包含摘要和表格的 Markdown 報告
2. **products.jsonl**：JSON Lines 格式資料

### Markdown 輸出範例

```markdown
# Product Sales Report

## Summary

- Total records: 15
- product_id: min=1.00, max=15.00, avg=8.00
- value: min=25.00, max=200.00, avg=107.67

## Data

| product_id | name | value | category | value_category |
| --- | --- | --- | --- | --- |
| 1 | Product_A | 150 | Electronics | High |
| 2 | Product_B | 45 | Books | Low |
...

*注意：避免使用 `id` 作為欄位名（Pathway 保留字）*
```

## 如何建立自己的自訂 Sink

### 1. 基本 Sink 模式

```python
from pwetl.sinks import BaseSink
import pathway as pw

class MyCustomSink(BaseSink):
    required_config = ['path']
    optional_config = {'param': 'default'}
    
    def write(self, table: pw.Table) -> None:
        # 你的寫入邏輯
        pass
```

### 2. 使用 Pathway 內建寫入器

```python
def write(self, table: pw.Table) -> None:
    output_path = self.config['path']
    
    # 使用 Pathway 寫入器
    pw.io.csv.write(table, output_path)
    # 或
    pw.io.jsonlines.write(table, output_path)
```

### 3. 自訂檔案格式

```python
def write(self, table: pw.Table) -> None:
    # 先寫入臨時 CSV
    temp_csv = 'temp.csv'
    pw.io.csv.write(table, temp_csv)
    
    # 執行 Pathway 以實體化
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)
    
    # 讀取並轉換
    with open(temp_csv, 'r') as f:
        data = process_csv(f)
    
    # 寫入自訂格式
    with open(self.config['path'], 'w') as f:
        write_custom_format(f, data)
```

### 4. 在 config.yaml 中使用

```yaml
sinks:
  - name: my_output
    type: custom
    module: my_sink.MyCustomSink
    path: output.txt
    param: value
```

## 實際應用場景

自訂 Sink 適用於：

1. **報告生成**：產生 HTML、PDF、Excel 報告
2. **API 整合**：將資料 POST 到 REST API（參考 APISink）
3. **資料庫**：寫入原生不支援的資料庫
4. **訊息佇列**：傳送到 Kafka、RabbitMQ 等
5. **雲端儲存**：上傳到 S3、Azure Blob、GCS
6. **電子郵件**：透過電子郵件傳送資料
7. **通知**：傳送到 Slack、Discord 等
8. **自訂格式**：寫入專有或特殊格式

## 進階模式

### 多個輸出檔案

```python
def write(self, table: pw.Table) -> None:
    base_path = self.config['path']
    
    # 寫入摘要
    summary_table = compute_summary(table)
    pw.io.csv.write(summary_table, f"{base_path}_summary.csv")
    
    # 寫入詳細資料
    pw.io.csv.write(table, f"{base_path}_detail.csv")
```

### 條件輸出

```python
def write(self, table: pw.Table) -> None:
    threshold = self.config.get('threshold', 100)
    
    # 寫入前先過濾
    filtered = table.filter(pw.this.value > threshold)
    pw.io.csv.write(filtered, self.config['path'])
```

### 資料庫 Sink 模式

```python
def setup(self) -> None:
    """初始化資料庫連線。"""
    self.conn = create_db_connection(self.config)

def write(self, table: pw.Table) -> None:
    """寫入資料庫。"""
    # 轉換為臨時格式
    temp_csv = 'temp.csv'
    pw.io.csv.write(table, temp_csv)
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)
    
    # 批次插入資料庫
    with open(temp_csv, 'r') as f:
        reader = csv.DictReader(f)
        self.conn.bulk_insert(reader)
```

## 提示

- 使用 `self.config` 存取配置值
- 在 `setup()` 中進行昂貴的初始化（連線、認證）
- 盡可能使用 Pathway 內建寫入器
- 如需要，先寫入臨時檔案再轉換
- 呼叫 `pw.run()` 以實體化 Pathway 計算
- 使用 try/except 優雅地處理錯誤
- 在 finally 區塊中清理臨時檔案

## 參考

- [自訂 Source 範例](../02_custom_source/)
- [API Source 範例](../01_api_source/)
- [BaseSink 文件](../../src/pwetl/sinks/base.py)
- [現有 Sink 實作](../../my-test/07_custom_sink/)
