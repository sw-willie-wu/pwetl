# 範例 03：API Sink

此範例示範如何使用 pwetl 的 API Sink 將處理後的資料發送到 API endpoint。

## 概述

此範例處理感測器資料（溫度和濕度讀數），並將聚合結果發送到 REST API endpoint。適用於：

- 將處理後的資料發送到外部服務
- 與 webhook 整合
- 發送警報或通知
- 透過 HTTP 將資料傳送到其他系統

## 功能說明

1. **讀取**：從 CSV 檔案讀取感測器資料
2. **轉換**：計算每個位置的平均溫度和濕度
3. **發送**：透過 POST 請求將結果發送到 API endpoint

### 輸入資料

```csv
sensor_id,location,temperature,humidity,timestamp
S001,Room_A,22.5,45.2,2026-02-05T10:00:00
S002,Room_B,23.1,48.5,2026-02-05T10:00:00
...
```

### 輸出

結果同時發送到 API 並寫入本地檔案：
- **output/sensor_summary.csv** - CSV 格式
- **output/sensor_summary.jsonl** - JSONL 格式

### API 輸出格式

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

## 設定步驟

### 1. 取得測試 API Endpoint

測試時可使用免費服務如 [Postbin](https://www.toptal.com/developers/postbin/)：

1. 訪問 https://www.toptal.com/developers/postbin/
2. 點擊「Create Bin」並複製你的 bin URL（例如：`https://www.toptal.com/developers/postbin/1234567890`）
3. 建立 `.env` 檔案：

```bash
cp .env.example .env
# 編輯 .env 並貼上你的 URL
```

你的 `.env` 檔案應該像這樣：

```env
API_URL=https://www.toptal.com/developers/postbin/1234567890
```

### 2. 執行範例

```bash
cd examples/03_api_sink
pwetl --config config_static.yaml
```

### 3. 檢查結果

```bash
cat output/sensor_summary.csv
cat output/sensor_summary.jsonl
```

如有設定 Postbin，也可到 Postbin 頁面查看 POST 請求。

## 配置說明

### API Sink 選項

```yaml
sinks:
  - name: api_output
    type: api
    url: ${API_URL}              # API endpoint（必需）
    method: POST                 # HTTP 方法（預設：POST）
    headers:                     # 自訂標頭
      Content-Type: application/json
      Authorization: "Bearer ${API_TOKEN}"
    timeout: 30                  # 請求超時（秒）
    max_retry: 3                 # 最大重試次數
    retry_delay: 1               # 重試間隔（秒）
```

### 認證設定

根據需要添加認證標頭：

```yaml
headers:
  # Bearer token
  Authorization: "Bearer ${API_TOKEN}"
  
  # API key
  X-API-Key: "${API_KEY}"
  
  # Basic auth (base64 編碼)
  Authorization: "Basic ${AUTH_CREDENTIALS}"
```

## 實際應用場景

### 1. Webhook 整合

發送資料到 Slack、Discord 或自訂 webhook：

```yaml
sinks:
  - name: slack_notification
    type: api
    url: ${SLACK_WEBHOOK_URL}
    method: POST
    headers:
      Content-Type: application/json
```

### 2. REST API 整合

將資料發送到後端服務：

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

### 3. 第三方服務

與外部平台整合：

```yaml
sinks:
  - name: analytics_platform
    type: api
    url: https://analytics.example.com/ingest
    method: POST
    headers:
      X-API-Key: "${ANALYTICS_API_KEY}"
```

## 錯誤處理

API Sink 內建重試邏輯：

- **max_retry**：重試次數（預設：3）
- **retry_delay**：重試間隔秒數（預設：1）

失敗的請求會自動重試，並採用指數退避策略。

## 提示

- 使用環境變數管理敏感資料（URL、token）
- 正式環境前先用 postbin 或 httpbin.org 測試
- 在日誌中監控 API 回應狀態碼
- 為 API 設定適當的超時時間
- 使用 `max_retry` 處理暫時性網路錯誤
- 檢查 API 速率限制並相應調整

## 進階：自訂標頭和認證

### 多種認證方式

```yaml
# 方式 1：Bearer Token
headers:
  Authorization: "Bearer ${API_TOKEN}"

# 方式 2：API Key
headers:
  X-API-Key: "${API_KEY}"

# 方式 3：多個標頭
headers:
  Authorization: "Bearer ${API_TOKEN}"
  X-Request-ID: "unique-id-123"
  X-Client-Version: "1.0.0"
```

### 條件發送

使用 Transform 在發送前過濾資料：

```python
def transform(self, tables):
    data = tables['sensors']
    
    # 只發送高溫警報
    alerts = data.filter(pw.this.temperature > 25)
    
    return {'api_output': alerts}
```

## 參考

- [自訂 Sink 範例](../06_custom_sink/) - 建立自訂輸出處理器
- [API Source 範例](../01_api_source/) - 從 API 獲取資料
- [APISink 文件](../../src/pwetl/sinks/api.py)
