# Example 02: Custom Source

This example demonstrates how to create a custom data source in pwetl.

## Overview

The custom source (`RandomDataSource`) generates random data for testing purposes. This is useful when you need:

- Test data without external dependencies
- Reproducible test scenarios (using seed)
- Quick prototyping of transforms

## Custom Source Implementation

### Key Components

```python
class RandomDataSource(BaseSource):
    required_config = ['count']
    optional_config = {
        'seed': None,
        'min_value': 0,
        'max_value': 100,
    }
    
    def read(self) -> pw.Table:
        # Generate data and return Pathway table
        pass
```

### Configuration Options

- `count` (required): Number of records to generate
- `seed` (optional): Random seed for reproducibility
- `min_value` (optional): Minimum random value (default: 0)
- `max_value` (optional): Maximum random value (default: 100)

## Usage

### Run the Example

```bash
cd examples/02_custom_source
pwetl --config config.yaml
```

### Expected Output

Two CSV files will be created:

1. `high_value_output.csv` - Records with value >= 100
2. `low_value_output.csv` - Records with value < 100

### Sample Data

```csv
id,name,value,category
1,Item_001,150,A
2,Item_002,75,B
3,Item_003,125,C
...
```

## How to Create Your Own Custom Source

1. **Inherit from BaseSource**:

```python
from pwetl.sources import BaseSource
import pathway as pw

class MyCustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default'}
```

2. **Implement the `read()` method**:

```python
def read(self) -> pw.Table:
    # Your data fetching logic
    raw_data = fetch_data_somehow()
    
    # Convert to list of tuples (required by table_from_rows)
    rows = [(row['field1'], row['field2']) for row in raw_data]
    
    # Get schema and create Pathway table
    schema = self._get_schema()
    if schema is None:
        raise ValueError(f"Source '{self.name}' requires schema")
    
    table = pw.debug.table_from_rows(schema=schema, rows=rows)
    return table

def _get_schema(self):
    """Get Pathway schema from config."""
    from pwetl.utils.schema import SchemaParser
    schema_config = self.config.get('schema')
    if schema_config:
        return SchemaParser.parse(schema_config)
    return None
```

3. **Optional: Implement `setup()` for initialization**:

```python
def setup(self) -> None:
    # Initialize connections, validate config, etc.
    pass
```

4. **Use in config.yaml**:

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

## Real-World Use Cases

Custom sources are useful for:

1. **Proprietary Data Formats**: Reading data from custom file formats
2. **API Integration**: Fetching data from APIs not natively supported
3. **Database Connectors**: Connecting to databases beyond PostgreSQL/MySQL
4. **Message Queues**: Reading from Kafka, RabbitMQ, etc.
5. **Cloud Storage**: Fetching from S3, Azure Blob, GCS
6. **Web Scraping**: Extracting data from websites
7. **IoT Devices**: Reading sensor data directly

## Tips

- Use `self._get_schema()` to get Pathway schema from config
- Use `self.config` to access configuration values
- `table_from_rows()` requires **list of tuples**, not list of dicts
- Schema must match tuple order (first field → first element, etc.)
- Avoid using `id` as column name (Pathway reserved word)
- Implement `setup()` for expensive initialization (connections, authentication)
- Use `pw.debug.table_from_rows()` for batch/static data
- Use connectors for streaming data (see API source implementation)

## See Also

- [Custom Sink Example](../03_custom_sink/)
- [API Source Example](../01_api_source/)
- [BaseSource Documentation](../../src/pwetl/sources/base.py)
