# Example 03: API Sink

This example demonstrates how to send processed data to an API endpoint using pwetl's API Sink.

## Overview

The example processes sensor data (temperature and humidity readings) and sends aggregated results to a REST API endpoint. This is useful for:

- Sending processed data to external services
- Integrating with webhooks
- Posting alerts or notifications
- Feeding data into other systems via HTTP

## What This Example Does

1. **Read** sensor data from CSV file
2. **Transform** by calculating average temperature and humidity per location
3. **Send** results to API endpoint via POST request

### Input Data

```csv
sensor_id,location,temperature,humidity,timestamp
S001,Room_A,22.5,45.2,2026-02-05T10:00:00
S002,Room_B,23.1,48.5,2026-02-05T10:00:00
...
```

### Output

Results are sent to the API and also written to local files:
- **output/sensor_summary.csv** - CSV format
- **output/sensor_summary.jsonl** - JSONL format

### API Output Format

```json
[
  {
    "location": "Room_A",
    "avg_temperature": 22.825,
    "avg_humidity": 45.375,
    "sample_count": 4
  },
  {
    "location": "Room_B",
    "avg_temperature": 23.25,
    "avg_humidity": 48.425,
    "sample_count": 3
  },
  ...
]
```

## Setup

### 1. Get a Test API Endpoint

For testing, use a free service like [Postbin](https://www.toptal.com/developers/postbin/):

1. Visit https://www.toptal.com/developers/postbin/
2. Click "Create Bin" and copy your bin URL (e.g., `https://www.toptal.com/developers/postbin/1234567890`)
3. Create `.env` file:

```bash
cp .env.example .env
# Edit .env and paste your URL
```

Your `.env` file should look like:

```env
API_URL=https://www.toptal.com/developers/postbin/1234567890
```

### 2. Run the Example

```bash
cd examples/03_api_sink
pwetl --config config_static.yaml
```

### 3. Check Results

```bash
cat output/sensor_summary.csv
cat output/sensor_summary.jsonl
```

If you set up a Postbin, you can also check the POST request on the Postbin page.

## Configuration

### API Sink Options

```yaml
sinks:
  - name: api_output
    type: api
    url: ${API_URL}              # API endpoint (required)
    method: POST                 # HTTP method (default: POST)
    headers:                     # Custom headers
      Content-Type: application/json
      Authorization: "Bearer ${API_TOKEN}"
    timeout: 30                  # Request timeout in seconds
    max_retry: 3                 # Maximum retry attempts
    retry_delay: 1               # Delay between retries (seconds)
```

### Authentication

Add authentication headers as needed:

```yaml
headers:
  # Bearer token
  Authorization: "Bearer ${API_TOKEN}"
  
  # API key
  X-API-Key: "${API_KEY}"
  
  # Basic auth (base64 encoded)
  Authorization: "Basic ${AUTH_CREDENTIALS}"
```

## Real-World Use Cases

### 1. Webhook Integration

Send data to services like Slack, Discord, or custom webhooks:

```yaml
sinks:
  - name: slack_notification
    type: api
    url: ${SLACK_WEBHOOK_URL}
    method: POST
    headers:
      Content-Type: application/json
```

### 2. REST API Integration

Post data to your backend service:

```yaml
sinks:
  - name: backend_api
    type: api
    url: https://api.example.com/data
    method: POST
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      Content-Type: application/json
```

### 3. Third-Party Services

Integrate with external platforms:

```yaml
sinks:
  - name: analytics_platform
    type: api
    url: https://analytics.example.com/ingest
    method: POST
    headers:
      X-API-Key: "${ANALYTICS_API_KEY}"
```

## Error Handling

The API Sink includes built-in retry logic:

- **max_retry**: Number of retry attempts (default: 3)
- **retry_delay**: Wait time between retries in seconds (default: 1)

Failed requests will be automatically retried with exponential backoff.

## Tips

- Use environment variables for sensitive data (URLs, tokens)
- Test with postbin or httpbin.org before production
- Monitor API response codes in logs
- Set appropriate timeout values for your API
- Use `max_retry` for transient network errors
- Check API rate limits and adjust accordingly

## Advanced: Custom Headers and Authentication

### Multiple Authentication Methods

```yaml
# Option 1: Bearer Token
headers:
  Authorization: "Bearer ${API_TOKEN}"

# Option 2: API Key
headers:
  X-API-Key: "${API_KEY}"

# Option 3: Multiple Headers
headers:
  Authorization: "Bearer ${API_TOKEN}"
  X-Request-ID: "unique-id-123"
  X-Client-Version: "1.0.0"
```

### Conditional Sending

Use Transform to filter data before sending:

```python
def transform(self, tables):
    data = tables['sensors']
    
    # Only send alerts for high temperature
    alerts = data.filter(pw.this.temperature > 25)
    
    return {'api_output': alerts}
```

## See Also

- [Custom Sink Example](../06_custom_sink/) - Create custom output handlers
- [API Source Example](../01_api_source/) - Fetch data from APIs
- [APISink Documentation](../../src/pwetl/sinks/api.py)
