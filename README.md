# pwetl

A flexible ETL (Extract, Transform, Load) framework based on Pathway. pwetl allows you to quickly build ETL services by simply writing Transform classes and YAML configuration files.

[中文文檔](docs/README_zh.md)

## Features

- **Declarative Configuration**: Define ETL pipelines through simple YAML configuration files
- **Multi-Source & Multi-Sink**: Support multiple data sources and output targets in a single pipeline
- **Rich Data Sources**:
  - Files: CSV, JSON, JSONL
  - API: REST API with Static/Streaming modes
  - Databases: Any SQLAlchemy-compatible database (PostgreSQL, MySQL, MSSQL, etc.)
- **Multiple Output Options**:
  - Files: CSV, JSON, JSONL
  - Databases: Any SQLAlchemy-compatible database (PostgreSQL, MySQL, MSSQL, etc.)
  - API: POST/PUT data to API endpoints
- **Streaming Deduplication**: Hash-based diff tracking with `diff_ignore_fields` — only emits new/changed records across polls
- **Data Validation**:
  - Integrated Pydantic validation models
  - Three validation modes: `none` (skip), `sample` (warn), `strict` (enforce)
  - Automatic type conversion (datetime, numeric, etc.)
- **Environment Variable Support**: Securely manage sensitive information using `${VAR_NAME}` syntax with defaults
- **SSH Tunneling**: Secure database connections through SSH jump hosts
- **Extensible**: Easily create custom Source/Sink/Transform
- **Powered by Pathway**: Leverage Pathway's streaming engine for both static and real-time pipelines

## Installation

**Important**: Pathway requires a Linux environment. Please run in WSL or Linux.

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .

# With database support (SQLAlchemy)
pip install -e ".[database]"

# With SSH tunnel support
pip install -e ".[ssh]"

# With all optional dependencies
pip install -e ".[all]"
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

# Verbose mode (DEBUG logging)
pwetl --config config.yaml --verbose

# Validate configuration only
pwetl --config config.yaml --dry-run

# Specify .env file
pwetl --config config.yaml --env-file .env.production

# Custom logging configuration
pwetl --config config.yaml --log-config logging.yaml
```

## Source Types

### File Source

```yaml
sources:
  - name: data
    type: file          # or csv, json, jsonl
    path: data.csv
    format: csv         # csv, json, jsonl
    mode: static        # static (default) or streaming
    schema:
      id: int
      name: str
```

### API Source

```yaml
sources:
  - name: api_data
    type: api
    url: https://api.example.com/data
    method: GET
    headers:
      Authorization: "Bearer ${API_TOKEN}"
    params:
      limit: 100
    data_path: results.data    # JSON path to extract data
    timeout: 30
    mode: streaming
    refresh_interval: 60       # seconds between polls
    diff_ignore_fields:        # fields to ignore when detecting changes
      - updated_at
      - last_modified
    validation_mode: sample
    schema:
      id: int
      name: str
      value: float
```

### Database Source

```yaml
sources:
  - name: db_data
    type: database
    dsn: postgresql://user:pass@host:5432/mydb
    table: users               # or use query_file: query.sql
    mode: streaming
    refresh_interval: 60
    diff_ignore_fields:
      - modified_at
    schema:
      id: int
      name: str
    ssh_tunnel:                # optional SSH tunnel
      host: jump-server
      username: ssh_user
      private_key: ~/.ssh/id_rsa
```

## Sink Types

### File Sink

```yaml
sinks:
  - name: output
    type: file
    path: output/result.csv
    format: csv                # csv, json, jsonl (auto-detected from extension)
```

### API Sink

```yaml
sinks:
  - name: api_output
    type: api
    url: https://api.example.com/ingest
    method: POST
    headers:
      Authorization: "Bearer ${API_TOKEN}"
    batch_size: 100
    max_retry: 3
    timeout: 30
```

### Database Sink

```yaml
sinks:
  - name: db_output
    type: database
    dsn: postgresql://user:${DB_PASSWORD}@localhost:5432/mydb
    table: output_table
    if_not_exists: create      # optional: 'error' (default) or 'create'
    ssh_tunnel:                # optional SSH tunnel
      host: jump-server
      username: ssh_user
      private_key: ~/.ssh/id_rsa
```

## Streaming Mode & Deduplication

In streaming mode, sources poll data periodically. To avoid re-emitting unchanged records, configure `diff_ignore_fields` to exclude volatile fields (e.g. timestamps) from change detection:

```yaml
sources:
  - name: youbike
    type: api
    url: https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
    mode: streaming
    refresh_interval: 60
    diff_ignore_fields:
      - mday
      - srcUpdateTime
      - updateTime
      - infoTime
      - infoDate
```

```
poll 1: 1733 records → 1733 new (first poll, nothing to compare)
poll 2: 1733 records →    0 new (only timestamps changed, skipped)
poll 3: 1733 records →    5 new (5 stations had bike count changes)
```

## Data Validation

Three validation modes controlled per source:

| Mode | Behavior |
|------|----------|
| `none` | Skip validation entirely |
| `sample` | Validate and warn on errors, keep original data |
| `strict` | Validate all records, fail on first error |

Schema types: `int`, `str`, `float`, `bool`, `datetime`, `dict`, `list`. Append `?` for optional fields (e.g. `address: str?`).

## Environment Variables

Use `${VAR_NAME}` syntax in YAML config. Supports defaults with `${VAR_NAME:default_value}`.

```yaml
sources:
  - name: api
    type: api
    url: ${API_URL:https://fallback.example.com/data}
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

Load from `.env` files automatically or specify with `--env-file`.

## Extension

### Custom Source

```python
from pwetl.sources import BaseSource
import pathway as pw

class CustomSource(BaseSource):
    required_config = ['param1']
    optional_config = {'param2': 'default_value'}

    def setup(self) -> None:
        pass  # initialize resources

    def read(self) -> pw.Table:
        pass  # return pw.Table

    def teardown(self) -> None:
        pass  # cleanup
```

### Custom Sink

```python
from pwetl.sinks import BaseSink
import pathway as pw

class CustomSink(BaseSink):
    required_config = ['param1']

    def write(self, table: pw.Table) -> None:
        pass  # implement write logic
```

Register in YAML with `type: custom`:

```yaml
sources:
  - name: data
    type: custom
    module: my_module.CustomSource
    param1: value1
```

## Examples

| Example | Description |
|---------|-------------|
| [01_api_source](examples/01_api_source/) | YouBike API — static/streaming modes, schema validation, multi-format output, `diff_ignore_fields` |
| [02_database_source](examples/02_database_source/) | Database source — SQLAlchemy DSN read from PostgreSQL (Docker included) |
| [03_api_sink](examples/03_api_sink/) | API sink — POST processed data to remote endpoints |
| [04_database_sink](examples/04_database_sink/) | Database sink — SQLAlchemy DSN write to PostgreSQL (Docker included) |
| [05_custom_source](examples/05_custom_source/) | Custom data source — synthetic data generation, multi-sink routing |
| [06_custom_sink](examples/06_custom_sink/) | Custom sink — Markdown report generation, custom JSONL output |

## Project Structure

```
src/pwetl/
├── cli.py                    # CLI entry point (pwetl command)
├── core/
│   ├── config.py             # Configuration loader
│   ├── engine.py             # ETL engine
│   ├── exceptions.py         # Custom exceptions
│   ├── pipeline.py           # Pipeline orchestration
│   ├── registry.py           # Source/Sink registry & factory
│   └── schema.py             # Configuration schema models
├── sources/
│   ├── base.py               # BaseSource (with validation framework)
│   ├── file.py               # FileSource (CSV/JSON/JSONL)
│   ├── api.py                # APISource (REST API)
│   ├── database.py           # DatabaseSource (SQLAlchemy + SSH tunnel)
│   └── connector/            # Streaming connector implementations
│       ├── base.py           # HashDiffConnectorMixin (dedup)
│       ├── api.py            # APIConnectorSubject
│       └── database.py       # DatabaseConnectorSubject
├── sinks/
│   ├── base.py               # BaseSink
│   ├── file.py               # FileSink (CSV/JSON/JSONL)
│   ├── api.py                # APISink (POST/PUT to API)
│   └── database.py           # DatabaseSink (SQLAlchemy DSN)
├── transforms/
│   └── base.py               # BaseTransform
└── utils/
    ├── env.py                # Environment variable substitution
    ├── loader.py             # Dynamic class loading
    ├── logger.py             # Logging configuration
    └── schema.py             # Schema parsing (Pathway + Pydantic)
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Environment Variables](docs/environment-variables.md)
- [Multi-Source & Multi-Sink Design](docs/multi-source-sink.md)
- [Changelog](docs/CHANGELOG.md)

## License

MIT License
