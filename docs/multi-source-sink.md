# 多資料源和多輸出目標指南

pwetl 支援從多個資料源讀取資料，並將結果寫入多個目標。這在以下場景中非常有用：

- 合併多個資料源（例如：合併多年的銷售資料）
- 將資料按不同維度分割輸出（例如：按類別分別輸出）
- 複雜的 ETL 流程（例如：從多個源 join 後輸出到多個報表）

## Transform 函數簽章

根據配置中的 sources 和 sinks 數量，Transform 的 \`transform\` 方法有不同的簽章：

| 場景 | 輸入類型 | 輸出類型 | 函數簽章 |
|------|---------|---------|----------|
| 單源 → 單目標 | \`pw.Table\` | \`pw.Table\` | \`transform(table: pw.Table) -> pw.Table\` |
| 多源 → 單/多目標 | \`Dict[str, pw.Table]\` | \`pw.Table\` 或 \`Dict[str, pw.Table]\` | \`transform(tables: Dict[str, pw.Table]) -> ...\` |

### 說明

- **單一 source**：Transform 接收單一 \`pw.Table\`
- **多個 sources**：Transform 接收 \`Dict[source_name, pw.Table]\`
- **單一 sink**：Transform 返回單一 \`pw.Table\`
- **多個 sinks**：Transform 返回 \`Dict[sink_name, pw.Table]\`

## 使用場景

### 場景 1：單一資料源 → 單一輸出

最簡單的情況，輸入和輸出都是單一表。

\`\`\`yaml
sources:
  - name: users
    type: file
    path: users.csv
    format: csv
    schema:
      id: int
      name: str

transform: transform.MyTransform

sinks:
  - name: output
    type: file
    path: output.csv
    format: csv
\`\`\`

Transform：

\`\`\`python
from pwetl.transforms import BaseTransform
import pathway as pw

class MyTransform(BaseTransform):
    def transform(self, tables):
        # tables 是 dict，即使只有一個 source
        data = tables['users']
        
        result = data.select(
            id=pw.this.id,
            name=pw.this.name.str.upper(),
        )
        
        # 返回 dict，即使只有一個 sink
        return {'output': result}
\`\`\`

### 場景 2：多資料源 → 單一輸出

從多個資料源讀取資料，合併或 join 後輸出到一個地方。

\`\`\`yaml
sources:
  - name: sales_2023
    type: file
    path: sales_2023.csv
    format: csv
    schema:
      id: int
      amount: float

  - name: sales_2024
    type: file
    path: sales_2024.csv
    format: csv
    schema:
      id: int
      amount: float

transform: transform.MergeSales

sinks:
  - name: output
    type: file
    path: merged_sales.csv
    format: csv
\`\`\`

Transform：

\`\`\`python
class MergeSales(BaseTransform):
    def transform(self, tables):
        # 取得多個 sources
        sales_2023 = tables['sales_2023']
        sales_2024 = tables['sales_2024']
        
        # 合併
        merged = sales_2023.concat(sales_2024)
        
        # 返回單一輸出
        return {'output': merged}
\`\`\`

### 場景 3：單一資料源 → 多輸出

從一個資料源讀取，按不同條件分割後輸出到多個地方。

\`\`\`yaml
sources:
  - name: products
    type: file
    path: products.csv
    format: csv
    schema:
      id: int
      category: str
      price: float

transform: transform.SplitByCategory

sinks:
  - name: electronics
    type: file
    path: electronics.csv
    format: csv

  - name: books
    type: file
    path: books.csv
    format: csv
\`\`\`

Transform：

\`\`\`python
class SplitByCategory(BaseTransform):
    def transform(self, tables):
        products = tables['products']
        
        # 分割資料
        electronics = products.filter(pw.this.category == 'Electronics')
        books = products.filter(pw.this.category == 'Books')
        
        # 返回多個輸出（dict 鍵名必須匹配 sink names）
        return {
            'electronics': electronics,
            'books': books
        }
\`\`\`

### 場景 4：多資料源 → 多輸出

從多個資料源讀取，join/merge 後分割到多個輸出。

\`\`\`yaml
sources:
  - name: products
    type: file
    path: products.csv
    format: csv
    schema:
      product_id: int
      name: str

  - name: inventory
    type: file
    path: inventory.csv
    format: csv
    schema:
      product_id: int
      stock_level: int

transform: transform.JoinAndSplit

sinks:
  - name: low_stock
    type: file
    path: low_stock.csv
    format: csv

  - name: full_report
    type: file
    path: full_report.jsonl
    format: jsonl
\`\`\`

Transform：

\`\`\`python
class JoinAndSplit(BaseTransform):
    def transform(self, tables):
        products = tables['products']
        inventory = tables['inventory']
        
        # Join 資料
        full_report = products.join(
            inventory,
            pw.left.product_id == pw.right.product_id
        ).select(
            product_id=pw.left.product_id,
            name=pw.left.name,
            stock_level=pw.right.stock_level
        )
        
        # 建立低庫存報告
        low_stock = full_report.filter(pw.this.stock_level < 10)
        
        return {
            'low_stock': low_stock,
            'full_report': full_report
        }
\`\`\`

## 常見操作範例

### 合併多個表 (Union)

\`\`\`python
def transform(self, tables):
    all_tables = list(tables.values())
    result = all_tables[0]
    for table in all_tables[1:]:
        result = result.concat(table)
    return {'output': result}
\`\`\`

### Join 多個表

\`\`\`python
def transform(self, tables):
    left = tables['table1']
    right = tables['table2']
    
    result = left.join(
        right,
        pw.left.id == pw.right.id
    ).select(
        id=pw.left.id,
        name=pw.left.name,
        value=pw.right.value
    )
    
    return {'output': result}
\`\`\`

### 按條件分割表

\`\`\`python
def transform(self, tables):
    data = tables['data']
    
    high_value = data.filter(pw.this.value > 100)
    low_value = data.filter(pw.this.value <= 100)
    
    return {
        'high_value': high_value,
        'low_value': low_value
    }
\`\`\`

### 聚合多個源

\`\`\`python
def transform(self, tables):
    # 合併所有源
    all_data = None
    for table in tables.values():
        if all_data is None:
            all_data = table
        else:
            all_data = all_data.concat(table)
    
    # 按類別聚合
    aggregated = all_data.groupby(pw.this.category).reduce(
        category=pw.this.category,
        total=pw.reducers.sum(pw.this.value),
        count=pw.reducers.count()
    )
    
    return {'output': aggregated}
\`\`\`

## 注意事項

1. **一致性**：Transform 的 \`transform\` 方法總是：
   - 接收 \`tables: Dict[str, pw.Table]\`
   - 返回 \`Dict[str, pw.Table]\`
   
2. **名稱匹配**：
   - \`tables\` 的鍵名對應 sources 的 \`name\`
   - 返回的 dict 鍵名必須對應 sinks 的 \`name\`

3. **必須使用 name**：配置中的每個 source 和 sink 都必須有 \`name\` 欄位

4. **錯誤處理**：如果返回的 dict 鍵名與 sink 名稱不匹配，會拋出錯誤

## 參考範例

查看專案中的範例：

- [my-test/01_basic_csv/](../my-test/01_basic_csv/) - 單源單目標
- [my-test/03_multi_source/](../my-test/03_multi_source/) - 多源範例
- [examples/01_api_source/](../examples/01_api_source/) - API 資料源
