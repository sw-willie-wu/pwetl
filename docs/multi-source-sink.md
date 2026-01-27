# 多資料源和多輸出目標指南

pwetl 支援從多個資料源讀取資料，並將結果寫入多個目標。這在以下場景中非常有用：

- 合併多個資料源（例如：合併多年的銷售資料）
- 將資料按不同維度分割輸出（例如：按類別分別輸出）
- 複雜的 ETL 流程（例如：從多個源 join 後輸出到多個報表）

## 使用場景

### 場景 1：多資料源 → 單一輸出

從多個資料源讀取資料，合併或 join 後輸出到一個地方。

**設定範例** ([config_multi_source.yaml](examples/config_multi_source.yaml)):

```yaml
pipeline:
  name: multi_source_pipeline

  # 定義多個資料源
  sources:
    - name: sales_2023        # 必須指定每個源的名稱
      type: csv
      path: data/sales_2023.csv

    - name: sales_2024
      type: csv
      path: data/sales_2024.csv

  # Transform 函數接收字典類型的參數
  transform:
    module: my_transforms
    function: merge_sales_data

  # 單一輸出
  sink:
    type: csv
    path: data/merged_sales.csv
```

**Transform 函數簽章**:

```python
def merge_sales_data(tables: Dict[str, pw.Table]) -> pw.Table:
    """
    Args:
        tables: {'sales_2023': table1, 'sales_2024': table2}

    Returns:
        Merged table
    """
    # 合併所有表
    result = tables['sales_2023'].concat(tables['sales_2024'])
    return result
```

### 場景 2：單一資料源 → 多輸出

從一個資料源讀取，按不同條件分割後輸出到多個地方。

**設定範例** ([config_multi_sink.yaml](examples/config_multi_sink.yaml)):

```yaml
pipeline:
  name: multi_sink_pipeline

  # 單一資料源
  source:
    type: csv
    path: data/input.csv

  # Transform 返回多個表
  transform:
    module: my_transforms
    function: split_by_category

  # 多個輸出目標
  sinks:
    - name: electronics       # 必須指定每個目標的名稱
      type: csv
      path: data/output_electronics.csv

    - name: books
      type: csv
      path: data/output_books.csv
```

**Transform 函數簽章**:

```python
def split_by_category(table: pw.Table) -> Dict[str, pw.Table]:
    """
    Args:
        table: Input table

    Returns:
        Dict of tables: {'electronics': table1, 'books': table2}
    """
    electronics = table.filter(pw.this.category == 'Electronics')
    books = table.filter(pw.this.category == 'Books')

    return {
        'electronics': electronics,
        'books': books
    }
```

### 場景 3：多資料源 → 多輸出

從多個資料源讀取，join/merge 後分割到多個輸出。

**設定範例** ([config_multi_both.yaml](examples/config_multi_both.yaml)):

```yaml
pipeline:
  name: multi_source_multi_sink_pipeline

  # 多個資料源
  sources:
    - name: products
      type: csv
      path: data/products.csv

    - name: inventory
      type: csv
      path: data/inventory.csv

  # Transform 處理多源並返回多表
  transform:
    module: my_transforms
    function: join_and_split

  # 多個輸出
  sinks:
    - name: low_stock
      type: csv
      path: data/low_stock_report.csv

    - name: full_report
      type: json
      path: data/inventory_report.jsonl
```

**Transform 函數簽章**:

```python
def join_and_split(tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]:
    """
    Args:
        tables: {'products': table1, 'inventory': table2}

    Returns:
        Dict of tables: {'low_stock': table1, 'full_report': table2}
    """
    products = tables['products']
    inventory = tables['inventory']

    # Join 資料
    full_report = products.join(
        inventory,
        pw.left.product_id == pw.right.product_id
    ).select(...)

    # 建立低庫存報告
    low_stock = full_report.filter(pw.this.stock_level < 10)

    return {
        'low_stock': low_stock,
        'full_report': full_report
    }
```

## Transform 函數簽章總結

| 場景 | 輸入類型 | 輸出類型 | 函數簽章 |
|------|---------|---------|----------|
| 單源 → 單目標 | `pw.Table` | `pw.Table` | `func(table: pw.Table) -> pw.Table` |
| 多源 → 單目標 | `Dict[str, pw.Table]` | `pw.Table` | `func(tables: Dict[str, pw.Table]) -> pw.Table` |
| 單源 → 多目標 | `pw.Table` | `Dict[str, pw.Table]` | `func(table: pw.Table) -> Dict[str, pw.Table]` |
| 多源 → 多目標 | `Dict[str, pw.Table]` | `Dict[str, pw.Table]` | `func(tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]` |

## 常見操作範例

### 合併多個表 (Union)

```python
def merge_tables(tables: Dict[str, pw.Table]) -> pw.Table:
    all_tables = list(tables.values())
    result = all_tables[0]
    for table in all_tables[1:]:
        result = result.concat(table)
    return result
```

### Join 多個表

```python
def join_tables(tables: Dict[str, pw.Table]) -> pw.Table:
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
    return result
```

### 按條件分割表

```python
def split_table(table: pw.Table) -> Dict[str, pw.Table]:
    high_value = table.filter(pw.this.value > 100)
    low_value = table.filter(pw.this.value <= 100)

    return {
        'high_value': high_value,
        'low_value': low_value
    }
```

### 聚合多個源

```python
def aggregate_sources(tables: Dict[str, pw.Table]) -> pw.Table:
    # 合併所有源
    combined = merge_tables(tables)

    # 按類別聚合
    aggregated = combined.groupby(pw.this.category).reduce(
        category=pw.this.category,
        total=pw.reducers.sum(pw.this.value),
        count=pw.reducers.count()
    )

    return aggregated
```

## 執行範例

查看並執行範例程式碼：

```bash
# 查看範例設定
cat examples/config_multi_source.yaml
cat examples/config_multi_sink.yaml
cat examples/config_multi_both.yaml

# 執行所有範例
python examples/run_multi_examples.py
```

## 注意事項

1. **源和目標的名稱**：在多源或多目標設定中，必須為每個源/目標指定唯一的 `name` 欄位

2. **Transform 返回值必須匹配**：
   - 多目標時，transform 必須返回字典，且鍵名與 sink 的 name 匹配
   - 單目標時，transform 必須返回單一 Table

3. **字典鍵名匹配**：Transform 函數返回的字典的鍵必須與設定中的 sink name 一致

4. **向後相容**：舊的單源單目標設定完全相容，無需修改

## 更多範例

查看 [examples/transforms_multi.py](examples/transforms_multi.py) 取得更多 transform 函數範例。
