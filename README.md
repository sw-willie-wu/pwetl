# pwetl

A flexible ETL (Extract, Transform, Load) framework based on Pathway. pwetl allows you to quickly build ETL services by simply writing Transform classes and YAML configuration files.

[中文文檔](docs/README_zh.md)

## Features

- **Declarative Configuration**: Define ETL pipelines through simple YAML configuration files
- **Multi-Source & Multi-Sink**: Support multiple data sources and output targets
- **Rich Data Sources**:
  - Files: CSV, JSON, JSONL (File Source)
  - API: REST API with Static/Streaming modes
  - Databases: PostgreSQL, MySQL
- **Multiple Output Options**:
  - Files: CSV, JSON, JSONL (File Sink)
  - Databases: PostgreSQL, MySQL
  - API: POST JSON data to API endpoints
- **Data Validation**:
  - Integrated Pydantic validation models
  - Three validation modes: none (skip), sample (warn), strict (enforce)
  - Automatic type conversion (datetime, numeric, etc.)
- **Environment Variable Support**: Securely manage sensitive information using `${VAR_NAME}` syntax
- **Extensible**: Easily create custom Source/Sink/Transform
- **Powered by Pathway**: Leverage Pathway's powerful streaming capabilities

## Installation

**Important**: Pathway requires a Linux environment. Please run in WSL or Linux.

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

For detailed installation instructions, see [Installation Guide](docs/installation.md).

## Quick Start

### 1. Define Transform

Create `transform.py`:

```python
from pwetl.transforms import BaseTransform
import pathway as pw

class MyTransform(BaseTransform):
    def transform(self, tables):
        """Process data.

        Args:
            tables: Dict[source_name, pw.Table]

        Returns:
            Dict[sink_name, pw.Table]
        """
        users = tables['users']

        # Transformation logic
        result = users.select(
            id=pw.this.id,
            name=pw.this.name.str.upper(),
        )

        return {'output': result}
```

### 2. Create Configuration

Create `config.yaml`:

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

### 3. Run

```bash
# Basic execution
pwetl --config config.yaml

# Verbose mode
pwetl --config config.yaml --verbose

# Validate configuration only
pwetl --config config.yaml --dry-run
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Environment Variables](docs/environment-variables.md)
- [Multi-Source & Multi-Sink Design](docs/multi-source-sink.md)
- [Changelog](docs/CHANGELOG.md)

## Examples

The project provides complete examples demonstrating various use cases:

### Example 1: YouBike API Data

[examples/01_api_source/](examples/01_api_source/)

Fetch real-time station data from YouBike API, demonstrating:

- API Source usage (Static/Streaming modes)
- Environment variable configuration (`.env` file)
- Data validation (Pydantic + validation modes)
- Automatic datetime type conversion
- Multiple output formats (CSV, JSON, JSONL)

Each example includes complete configuration files, Transform logic, and usage instructions.

## Extension

### Custom Source

```python
from pwetl.sources import BaseSource
import pathway as pw

class CustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default_value'}

    def read(self) -> pw.Table:
        # Implement read logic
        return table
```

Use in YAML:

```yaml
sources:
  - name: data
    type: custom
    module: my_sources.py
    class: CustomSource
    param1: value1
```

### Custom Sink

```python
from pwetl.sinks import BaseSink
import pathway as pw

class CustomSink(BaseSink):
    required_config = ['param1']
    
    def write(self, table: pw.Table) -> None:
        # Implement write logic
        pass
```

Use in YAML:

```yaml
sinks:
  - name: output
    type: custom
    module: my_sinks.py
    class: CustomSink
    param1: value1
```

For detailed extension guides, check the examples in [my-test/](my-test/).

## Project Structure

```
src/pwetl/
├── cli.py              # CLI entry point (pwetl command)
├── core/
│   ├── config.py       # Configuration loader
│   ├── engine.py       # ETL engine
│   ├── pipeline.py     # Pipeline orchestration
│   └── registry.py     # Source/Sink Registry
├── sources/
│   ├── base.py         # BaseSource (with validation framework)
│   ├── file.py         # FileSource (CSV/JSON/JSONL)
│   ├── api.py          # APISource (REST API)
│   └── database.py     # DatabaseSource (PostgreSQL/MySQL)
├── sinks/
│   ├── base.py         # BaseSink
│   ├── file.py         # FileSink (CSV/JSON/JSONL)
│   ├── api.py          # APISink (POST JSON)
│   └── database.py     # DatabaseSink (PostgreSQL/MySQL)
├── transforms/
│   └── base.py         # BaseTransform
└── utils/
    ├── env.py          # Environment variable handling
    ├── loader.py       # Dynamic loading
    └── schema.py       # Schema parsing (Pathway + Pydantic)
```

## License

MIT License
