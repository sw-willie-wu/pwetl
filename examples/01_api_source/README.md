# Example 01: API Source - YouBike 2.0

This example demonstrates how to use the `api` source to fetch data from REST APIs. We use Taiwan's YouBike 2.0 real-time availability API as the data source.

## Features Demonstrated

- **API Source**: Fetch data from REST APIs
- **Environment Variables**: Use `.env` for sensitive configuration
- **Static Mode**: One-time data fetch and processing
- **Streaming Mode**: Continuous monitoring and updates
- **Schema Validation**: Three validation modes (none/sample/strict)
- **Multiple Output Formats**: CSV, JSON, JSONL
- **Custom Logging**: Use `--log-config` for custom log format

## Prerequisites

```bash
# Install pwetl
pip install pwetl

# Or install from source
cd /path/to/pwetl
pip install -e .
```

## Environment Variables Setup

Create a `.env` file in this directory:

```bash
# YouBike 2.0 API
YOUBIKE_API_URL=https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
```

The pwetl framework automatically loads `.env` from the current working directory. Use `${VAR_NAME}` syntax in YAML files to reference environment variables.

## Data Source

**YouBike 2.0 Real-time Availability API**  
URL: https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json

This API provides real-time information for all YouBike 2.0 stations in Taiwan, including:
- Station location and names
- Available bikes and parking spaces
- Last update time

## Data Fields

Key fields from the API response:

| Field | Type | Description |
|-------|------|-------------|
| sno | string | Station ID |
| sna | string | Station name (Chinese) |
| snaen | string | Station name (English) |
| tot | integer | Total parking spaces |
| available_rent_bikes | integer | Available bikes to rent |
| available_return_bikes | integer | Available spaces to return bikes |
| sarea | string | Administrative district (Chinese) |
| sareaen | string | Administrative district (English) |
| ar | string | Detailed address (Chinese) |
| aren | string | Detailed address (English) |
| lat | float | Latitude |
| lng | float | Longitude |
| act | string | Station status (1: active, 0: inactive) |
| updateTime | string | Last update time (ISO format) |

## Configuration Files

### 1. config.yaml - Basic Configuration

Static mode with schema validation:

```yaml
source:
  type: api
  config:
    url: ${YOUBIKE_API_URL}
    format: json
    mode: static
    
sink:
  - type: file
    config:
      path: output/youbike.csv
      format: csv
```

**Configuration Explanation:**

- **source.config.url**: Use environment variable for flexibility
- **source.config.format**: `json` - API returns JSON array
- **source.config.mode**: `static` - Fetch once and exit
- **sink.config.path**: Output file path
- **sink.config.format**: Output format (csv/json/jsonl)

### 2. config_static.yaml - Static Mode with Multiple Outputs

Fetch data once and output to multiple formats:

```yaml
source:
  type: api
  config:
    url: ${YOUBIKE_API_URL}
    format: json
    mode: static
    validation_mode: sample  # Validate first 100 records only
    schema:
      sno: str
      sna: str
      tot: int
      available_rent_bikes: int
      available_return_bikes: int
      lat: float
      lng: float
      updateTime: str
    
sink:
  - type: file
    config:
      path: output/youbike.csv
      format: csv
  - type: file
    config:
      path: output/youbike.json
      format: json
  - type: file
    config:
      path: output/youbike.jsonl
      format: jsonl

transform: transform.py
```

**Key Features:**
- Multiple output formats simultaneously
- Schema validation for data quality
- Custom transform script for data processing

### 3. config_streaming.yaml - Streaming Mode

Continuous monitoring with periodic fetching:

```yaml
source:
  type: api
  config:
    url: ${YOUBIKE_API_URL}
    format: json
    mode: streaming
    streaming:
      interval: 30  # Poll every 30 seconds
    validation_mode: none  # Skip validation in streaming mode
    
sink:
  - type: file
    config:
      path: output/youbike_stream.csv
      format: csv
      mode: streaming

transform: transform.py
```

**Streaming Configuration:**
- **mode**: `streaming` - Continuous operation
- **streaming.interval**: 30 seconds between API calls
- **validation_mode**: `none` - Skip validation for performance
- **sink.config.mode**: `streaming` - Continuously update output file

**Use Cases:**
- Real-time monitoring dashboards
- Alert systems based on availability
- Data collection for analytics

## Schema Validation Modes

The `validation_mode` parameter controls data validation behavior:

### 1. `validation_mode: none`
- **No validation** - Accept all data as-is
- **Best for**: Streaming mode, trusted APIs, performance-critical scenarios
- **Schema**: Not required

### 2. `validation_mode: sample`
- **Validate first 100 records** - Warn if errors found, but continue processing
- **Best for**: Development, testing, data exploration
- **Schema**: Required for validation
- **Behavior**: Logs warnings for invalid data but doesn't stop execution

### 3. `validation_mode: strict`
- **Validate all records** - Stop immediately on first error
- **Best for**: Production, critical data pipelines
- **Schema**: Required for validation
- **Behavior**: Raises exception and stops pipeline on invalid data

**Important**: Both `sample` and `strict` modes require a schema definition in the configuration.

## Transform Script

The `transform.py` script processes the raw API data:

```python
import pathway as pw

class YouBikeTransform:
    def transform(self, youbike: pw.Table) -> pw.Table:
        """Select and rename columns for output."""
        return youbike.select(
            站點編號=pw.this.sno,
            站點名稱=pw.this.sna,
            行政區=pw.this.sarea,
            可借車輛=pw.this.available_rent_bikes,
            可還空位=pw.this.available_return_bikes,
            緯度=pw.this.lat,
            經度=pw.this.lng,
            更新時間=pw.this.updateTime,
        )
```

**Transform Features:**
- Column selection and renaming
- Data type conversion
- Calculated fields (e.g., total capacity)

You can add custom calculations:

```python
result = youbike.select(
    站點名稱=pw.this.sna,
    可借車輛=pw.this.available_rent_bikes,
    可還空位=pw.this.available_return_bikes,
    總停車位=pw.this.available_rent_bikes + pw.this.available_return_bikes,
)
```

## Custom Logging Configuration

The `logging.yaml` file demonstrates custom log formatting:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  simple:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  detailed:
    format: '[%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout
  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: detailed
    filename: output/pwetl.log
    mode: w

loggers:
  pwetl:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  pathway_engine:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: DEBUG
  handlers: [console, file]
```

**Use custom logging:**
```bash
pwetl --config config_static.yaml --log-config logging.yaml
```

## Execution

### Static Mode (One-time Fetch)

```bash
# Basic execution
pwetl --config config.yaml

# With schema validation and multiple outputs
pwetl --config config_static.yaml

# With custom logging
pwetl --config config_static.yaml --log-config logging.yaml
```

**Expected Output:**
```
2024-01-15 10:30:00,123 - INFO - pwetl.engine - Starting pwetl engine...
2024-01-15 10:30:01,456 - INFO - pwetl.sources.api - Fetching data from API...
2024-01-15 10:30:02,789 - INFO - pwetl.sinks.file - Writing 1724 records to output/youbike.csv
2024-01-15 10:30:03,012 - INFO - pwetl.engine - Pipeline completed successfully
```

### Streaming Mode (Continuous Monitoring)

```bash
pwetl --config config_streaming.yaml
```

**Expected Behavior:**
- Fetches data every 30 seconds
- Updates output file continuously
- Runs until manually stopped (Ctrl+C)

**Sample Output:**
```
2024-01-15 10:30:00,123 - INFO - pwetl.engine - Starting pwetl engine in streaming mode...
2024-01-15 10:30:01,456 - INFO - pwetl.sources.api - Fetching data from API...
2024-01-15 10:30:02,789 - INFO - pwetl.sinks.file - Updated 1724 records
2024-01-15 10:30:32,890 - INFO - pwetl.sources.api - Fetching data from API...
2024-01-15 10:30:33,123 - INFO - pwetl.sinks.file - Updated 1726 records
...
```

To stop: Press `Ctrl+C`

## Output Examples

### CSV Output (youbike.csv)

```csv
站點編號,站點名稱,行政區,可借車輛,可還空位,緯度,經度,更新時間
500101001,捷運市政府站(3號出口),信義區,18,32,25.0408578889,121.567904444,2024-01-15T10:30:00+08:00
500101002,捷運國父紀念館站(2號出口),大安區,25,15,25.041254,121.557508,2024-01-15T10:30:00+08:00
```

### JSON Output (youbike.json)

```json
[
  {
    "站點編號": "500101001",
    "站點名稱": "捷運市政府站(3號出口)",
    "行政區": "信義區",
    "可借車輛": 18,
    "可還空位": 32,
    "緯度": 25.0408578889,
    "經度": 121.567904444,
    "更新時間": "2024-01-15T10:30:00+08:00"
  }
]
```

### JSONL Output (youbike.jsonl)

```jsonl
{"站點編號": "500101001", "站點名稱": "捷運市政府站(3號出口)", "行政區": "信義區", ...}
{"站點編號": "500101002", "站點名稱": "捷運國父紀念館站(2號出口)", "行政區": "大安區", ...}
```

## Important Notes

1. **Network Connection**: API source requires internet connectivity
2. **First Run**: Initial data fetch may take a few seconds
3. **API Changes**: If API response format changes, update schema definition
4. **Static Mode**: Executes once and exits automatically - ideal for testing or scheduled tasks
5. **Streaming Mode**: Runs continuously until manually stopped (Ctrl+C) - ideal for real-time monitoring
6. **File Updates**: In streaming mode, output files are continuously updated - monitor file changes to verify operation

## Troubleshooting

### Connection Errors

If you encounter connection errors, check:
- Network connectivity is working
- API URL is correct
- Firewall is not blocking the connection

### Schema Validation Errors

If data fields don't match the schema:
- Check if API response format has changed
- Update schema definition in config.yaml
- Consider using `validation_mode: none` or omitting schema for automatic inference

### Output File Already Exists

By default, existing files are overwritten. To preserve old files:
- Modify output filename (add timestamp)
- Manually backup old files before running

### Logging Issues

If custom logging configuration doesn't work:
- Verify YAML syntax is correct
- Check file paths in handlers are writable
- Ensure output directory exists
- Use `--log-config` parameter to specify config file

## Further Reading

- [pwetl Documentation](../../README.md)
- [Environment Variables Guide](../../docs/environment-variables.md)
- [API Source Configuration](../../docs/usage.md#api-source)
- [Streaming Mode Guide](../../docs/usage.md#streaming-mode)
