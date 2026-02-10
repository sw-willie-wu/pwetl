# Example 06: Custom Sink

This example demonstrates how to create custom sinks in pwetl.

## Overview

This example includes two custom sinks:

1. **MarkdownReportSink**: Generates formatted Markdown reports with summary statistics
2. **JSONLSink**: Simple custom JSONL writer (demonstrates basic sink pattern)

Custom sinks are useful when you need to output data in formats or destinations not natively supported by pwetl.

## Custom Sink Implementations

### MarkdownReportSink

Generates a Markdown report with:
- Title and metadata
- Summary statistics (count, min, max, average)
- Formatted data table
- Limited to first 100 rows for readability

**Configuration Options:**
- `path` (required): Output file path
- `title` (optional): Report title (default: "Data Report")
- `include_summary` (optional): Whether to include statistics (default: true)

### JSONLSink

A simple example showing the basic sink pattern.

**Configuration Options:**
- `path` (required): Output file path

## Usage

### Run the Example

```bash
cd examples/06_custom_sink
pwetl --config config_static.yaml
```

### Expected Output

Two files will be created in the `output/` directory:

1. **report.md**: Markdown report with summary and table
2. **products.jsonl**: JSON Lines format data

### Sample Markdown Output

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

*Note: Avoid using `id` as column name (Pathway reserved word)*
```

## How to Create Your Own Custom Sink

### 1. Basic Sink Pattern

```python
from pwetl.sinks import BaseSink
import pathway as pw

class MyCustomSink(BaseSink):
    required_config = ['path']
    optional_config = {'param': 'default'}
    
    def write(self, table: pw.Table) -> None:
        # Your writing logic here
        pass
```

### 2. Use Pathway's Built-in Writers

```python
def write(self, table: pw.Table) -> None:
    output_path = self.config['path']
    
    # Use Pathway's writers
    pw.io.csv.write(table, output_path)
    # or
    pw.io.jsonlines.write(table, output_path)
```

### 3. Custom File Format

```python
def write(self, table: pw.Table) -> None:
    # Write to temp CSV first
    temp_csv = 'temp.csv'
    pw.io.csv.write(table, temp_csv)
    
    # Run Pathway to materialize
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)
    
    # Read and transform
    with open(temp_csv, 'r') as f:
        data = process_csv(f)
    
    # Write custom format
    with open(self.config['path'], 'w') as f:
        write_custom_format(f, data)
```

### 4. Use in config_static.yaml

```yaml
sinks:
  - name: my_output
    type: custom
    module: my_sink.MyCustomSink
    path: output.txt
    param: value
```

## Real-World Use Cases

Custom sinks are useful for:

1. **Reporting**: Generate HTML, PDF, Excel reports
2. **APIs**: POST data to REST APIs (see APISink)
3. **Databases**: Write to databases not natively supported
4. **Message Queues**: Send to Kafka, RabbitMQ, etc.
5. **Cloud Storage**: Upload to S3, Azure Blob, GCS
6. **Email**: Send data via email
7. **Notifications**: Send to Slack, Discord, etc.
8. **Custom Formats**: Write proprietary or specialized formats

## Advanced Patterns

### Multiple Output Files

```python
def write(self, table: pw.Table) -> None:
    base_path = self.config['path']
    
    # Write summary
    summary_table = compute_summary(table)
    pw.io.csv.write(summary_table, f"{base_path}_summary.csv")
    
    # Write detail
    pw.io.csv.write(table, f"{base_path}_detail.csv")
```

### Conditional Output

```python
def write(self, table: pw.Table) -> None:
    threshold = self.config.get('threshold', 100)
    
    # Filter before writing
    filtered = table.filter(pw.this.value > threshold)
    pw.io.csv.write(filtered, self.config['path'])
```

### Database Sink Pattern

```python
def setup(self) -> None:
    """Initialize database connection."""
    self.conn = create_db_connection(self.config)

def write(self, table: pw.Table) -> None:
    """Write to database."""
    # Convert to temp format
    temp_csv = 'temp.csv'
    pw.io.csv.write(table, temp_csv)
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)
    
    # Bulk insert to database
    with open(temp_csv, 'r') as f:
        reader = csv.DictReader(f)
        self.conn.bulk_insert(reader)
```

## Tips

- Use `self.config` to access configuration values
- Implement `setup()` for expensive initialization (connections, authentication)
- Use Pathway's built-in writers when possible
- Write to temp file first, then transform if needed
- Call `pw.run()` to materialize Pathway computations
- Handle errors gracefully with try/except
- Clean up temporary files in finally blocks

## See Also

- [Custom Source Example](../05_custom_source/)
- [API Source Example](../01_api_source/)
- [BaseSink Documentation](../../src/pwetl/sinks/base.py)
- [API Sink Example](../03_api_sink/)
