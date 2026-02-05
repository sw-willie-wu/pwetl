# YouBike 2.0 API 範例

這個範例展示如何使用 `pwetl` 從 REST API 讀取資料，並輸出成多種格式。同時示範如何使用環境變數管理 API 配置。

## 環境變數配置

### 設定步驟

1. 複製 `.env.example` 為 `.env`：
```bash
cp .env.example .env
```

2. 編輯 `.env` 檔案（已包含預設值，可直接使用）：
```bash
YOUBIKE_API_URL=https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
```

3. pwetl 會自動載入 `.env` 檔案中的環境變數

### 為什麼使用環境變數？

- **安全性**：避免在版本控制中提交 API 網址或 token
- **靈活性**：不同環境可使用不同的 API 端點
- **最佳實踐**：符合 12-Factor App 配置管理原則

## 資料來源

使用台北市公共自行車（YouBike 2.0）的即時站點資訊 API：
- API 網址: https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
- 資料格式: JSON 陣列
- 更新頻率: 約每 1 分鐘更新一次

## 資料欄位

原始 API 回傳的完整欄位：

**基本資訊**
- `sno`: 站點代碼
- `sna`: 站點名稱（中文）
- `snaen`: 站點名稱（英文）
- `sarea`: 行政區（中文）
- `sareaen`: 行政區（英文）
- `ar`: 地址（中文）
- `aren`: 地址（英文）

**車位資訊**
- `available_rent_bikes`: 可借車輛數
- `available_return_bikes`: 可還空位數
- `Quantity`: 總停車位數

**位置資訊**
- `latitude`: 緯度
- `longitude`: 經度

**時間資訊**
- `mday`: 站點維護時間（datetime，API 格式："YYYY-MM-DD HH:MM:SS"）
- `updateTime`: 資料更新時間（datetime）
- `srcUpdateTime`: 來源資料更新時間（datetime）
- `infoTime`: 資訊時間（datetime）
- `infoDate`: 資訊日期（字串格式 YYYY-MM-DD）

注意：API 回傳的時間格式為 `"2026-02-05 14:46:52"`，Pydantic 會自動轉換成 datetime 物件，輸出時會格式化為 ISO 8601 格式 `"2026-02-05T14:46:52"`。

**狀態**
- `act`: 站點啟用狀態（1=啟用）

## 設定檔說明

專案提供兩種設定檔：

### 1. config_static.yaml - 靜態模式
- 執行一次後結束
- 取得當下的即時資料快照
- 適合：定時任務、資料備份、單次查詢
- `validation_mode: strict` - 嚴格驗證，資料格式錯誤會中止

### 2. config_streaming.yaml - 串流模式
- 持續運行，定期輪詢 API
- 每 60 秒更新一次資料（`refresh_interval: 60`）
- 適合：即時監控、資料儀表板、持續追蹤
- `validation_mode: sample` - 只警告，不中斷執行
- 需要手動停止（Ctrl+C）

### 驗證模式說明

- **none**: 略過驗證，直接使用原始資料
- **sample**: Pydantic 驗證並轉換資料，失敗時顯示警告但繼續執行
- **strict**: Pydantic 驗證並轉換資料，失敗時立即中止

驗證成功時，sample 和 strict 模式都會將資料正規化（例如 datetime 轉換），差別只在於失敗時的處理方式。

## 執行方式

### Static 模式（執行一次）

```bash
cd examples/01_api_source
pwetl --config config_static.yaml
```

### Streaming 模式（持續運行）

```bash
pwetl --config config_streaming.yaml
# 按 Ctrl+C 停止
```

### 使用 Python 模組方式

```bash
python -m pwetl.cli --config config_static.yaml
# 或
python -m pwetl.cli --config config_streaming.yaml
```

## 輸出檔案

### Static 模式輸出

執行 `config_static.yaml` 後會產生：
- **youbike_static_output.csv** - CSV 格式
- **youbike_static_output.json** - JSON 格式
- **youbike_static_output.jsonl** - JSON Lines 格式

### Streaming 模式輸出

執行 `config_streaming.yaml` 後會產生（並持續更新）：
- **youbike_streaming_output.csv** - CSV 格式
- **youbike_streaming_output.json** - JSON 格式
- **youbike_streaming_output.jsonl** - JSON Lines 格式

### 格式說明

- **CSV**: 表格式資料，適合用 Excel 開啟，欄位以逗號分隔
- **JSON**: JSON 陣列格式，適合直接讀取整個資料集
- **JSONL**: 每行一筆 JSON 記錄，適合串流處理或大型資料集

### 資料過濾

在 `transform.py` 中可以加入過濾條件，例如只保留特定區域：

```python
# 只保留大安區的站點
result = youbike.filter(pw.this.sarea == "大安區")
```

### 計算衍生欄位

可以計算新的欄位，例如總停車位：

```python
result = youbike.select(
    站點名稱=pw.this.sna,
    可借車輛=pw.this.available_rent_bikes,
    可還空位=pw.this.available_return_bikes,
    總停車位=pw.this.available_rent_bikes + pw.this.available_return_bikes,
)
```

## 注意事項

1. API 來源需要網路連線
2. 首次執行會下載資料，可能需要幾秒鐘
3. 如果 API 回應格式改變，需要更新 schema 定義
4. **Static 模式**: 執行一次後自動結束，適合測試或定時任務
5. **Streaming 模式**: 會持續運行直到手動停止（Ctrl+C），適合即時監控
6. Streaming 模式下，輸出檔案會持續更新，建議觀察檔案變化確認運作正常

## 疑難排解

### 連線錯誤

如果出現連線錯誤，檢查：
- 網路連線是否正常
- API 網址是否正確
- 防火牆是否阻擋

### Schema 錯誤

如果資料欄位與 schema 不符：
- 檢查 API 回應格式是否改變
- 更新 config.yaml 中的 schema 定義
- 可以先不定義 schema，讓系統自動推斷

### 輸出檔案已存在

預設會覆蓋現有檔案。如果需要保留舊檔案：
- 修改輸出檔名（加上時間戳記）
- 或手動備份舊檔案
