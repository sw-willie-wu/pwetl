# Changelog

All notable changes to pwetl will be documented in this file.

## [Unreleased] - 2026-02-12

### Added

- **DatabaseSink Dialect 策略模式**：
  - 新增 `sinks/dialect/` 子模組：`BaseDialect`（抽象介面）、`DefaultDialect`（raw SQL）、`PostgresDialect`（ON CONFLICT upsert）
  - Dialect 從 DSN 自動偵測（`engine.dialect.name`），也可透過 `dialect` config 覆寫
  - 新增 `write_mode` config：`insert`（預設）或 `upsert`（dialect-specific）
  - 新增 `columns` config：簡單建表（`<type>[?] [, pk]` 語法，如 `uuid, pk`、`float?`、`varchar(100)`）
  - 新增 `init_sql` config：進階 DDL 從 SQL 檔案執行（與 `columns` 互斥）
  - 新增 `primary_key` config：upsert 所需的 PK 欄位列表（也可從 columns 的 `pk` modifier 提取）
  - Pathway JSONL duplicate key 處理：使用 `object_pairs_hook` 正確分離使用者欄位與 Pathway metadata（`diff`、`time`），解決使用者定義 `time` 欄位被覆蓋的問題

### Changed

- **DatabaseSink 重構**：
  - 移除 `if_not_exists` config（改為 `columns` 或 `init_sql` 觸發建表）
  - INSERT 邏輯從 DatabaseSink 搬到 dialect 層
  - 透過 dialect strategy 自動處理 DB 專屬 SQL（PostgreSQL 用 `ON CONFLICT DO UPDATE`，其他用 `DELETE + INSERT` fallback）

- **`query_file` → `query_sql` 重命名**：
  - DatabaseSource 的 SQL 檔案 config 統一命名風格
  - 向後相容：仍接受 `query_file`，但會發出 deprecation warning

- **統一 Logging 與例外處理**：
  - 所有檔案頂層宣告 `LOGGER = get_logger(__name__)`，不在方法內 inline 建立
  - 訊息格式統一：`Source '<name>': ...`、`Sink '<name>': ...`、`Transform: ...`、`Pipeline ...`
  - `pipeline.py`：`RuntimeError` 全面替換為 `SourceError` / `TransformError` / `SinkError`
  - `pipeline.py`：新增 INFO log 標記關鍵進度點（starting → setup → read → transform → write → engine run → completed）
  - `pipeline.py`：teardown 清理失敗從 DEBUG 提升為 WARNING
  - `engine.py`：移除 `execute()` 中重複的 `LOGGER.error()`，避免同一錯誤輸出兩次
  - `engine.py`：`_build_pipeline()` Source/Sink/Transform 建立失敗改拋 `ConfigurationError`（原本包成 `RuntimeError`，CLI 無法分類顯示）
  - `engine.py`：`_load_config()` 移除多餘的 `RuntimeError` 包裝，`ConfigLoader` 已直接拋 `ConfigurationError`
  - `cli.py`：依例外類別輸出不同前綴（`[Source]`、`[Transform]`、`[Sink]`、`[Config]`）
  - `sources/base.py`：`warnings.warn()` 全部改用 `LOGGER.warning()`，移除 `import warnings`
  - `sources/file.py`、`sinks/file.py`：新增頂層 LOGGER 及 INFO log
  - `sources/api.py`、`sources/database.py`：`setup()` / `read()` / `teardown()` 加 INFO log
  - `sinks/api.py`：移除 `teardown()` 內的 inline logger，統一用頂層 LOGGER；格式從 `"APISink %s:"` 改為 `"Sink '%s':"`；`_send_batch` retry 加 WARNING
  - `connector/api.py`：移除多餘的 `fetch api` log，streaming 等待/重試從 INFO 降為 DEBUG
  - `connector/database.py`：streaming 等待/重試從 INFO 降為 DEBUG

### Examples

- **Example 04 (Database Sink) 改進**：
  - Transform 新增 UUID5 `id` 欄位（`pw.apply(uuid.uuid5)` + `_pw_id` prefix trick）
  - Transform 新增 `dt.strptime()` 解析 `order_date` 為 `DateTimeNaive`，寫入 DB 為 `TIMESTAMPTZ`
  - `init.sql`、`sink_init.sql`：`id` 改為 `UUID`，`time` 改為 `TIMESTAMPTZ`
  - `config_streaming.yaml` columns：`id: uuid, pk`、`time: timestamptz`

### Documentation

- 新增 `docs/logging.md`：Logging 與例外處理規範（Logger 宣告、訊息格式、等級規則、自訂例外、新增元件 Checklist）

---

## [0.2.0] - 2026-02-05

### Added

- **統一驗證框架**：在 BaseSource 中新增 `_validate_record()` 和 `_validate_batch()` 方法
  - 支援三種驗證模式：`none`（略過）、`sample`（警告）、`strict`（強制）
  - 整合 Pydantic 驗證模型，自動類型轉換
  - 驗證成功時，sample 和 strict 模式都會正規化資料（如 datetime 轉換）
  - 差異：strict 在驗證失敗時中止，sample 只顯示警告

- **API Source 重構**：
  - 將 APIConnectorSubject 提升為模組級別類別
  - Connector 現在是自包含的，不依賴 source 方法
  - Connector 在 setup() 階段初始化，而非 read() 階段
  - 驗證函數作為回調傳遞給 connector

- **File Source/Sink 改進**：
  - 統一使用 `type: file` + `format: csv/json/jsonl` 配置
  - 自動從檔案副檔名偵測格式（如果未指定 format）
  - 移除 Parquet 支援（Pathway 未提供 pw.io.parquet）

- **Database Source 驗證**：
  - MySQL source 現在使用 `_validate_batch()` 進行資料驗證
  - 確保所有 source 類型統一使用驗證框架

- **範例專案**：
  - 新增 `examples/01_api_source/` - YouBike 2.0 API 範例
  - 示範 Static/Streaming 模式
  - 環境變數配置（`.env` 檔案）
  - Datetime 類型處理
  - 三種輸出格式（CSV、JSON、JSONL）

### Changed

- **CLI 命令格式**：
  - 從 `python -m pwetl.cli run config.yaml` 改為 `pwetl --config config.yaml`
  - 更簡潔直觀的命令介面

- **配置格式標準化**：
  - File Source: `type: file` + `format: csv/json/jsonl`（不再是 `type: csv`）
  - API Source: 使用 `refresh_interval` 參數（streaming 模式）
  - 所有 source 支援 `validation_mode` 配置

- **驗證邏輯改進**：
  - `_validate_record()`: 驗證成功時一律回傳 `model_dump()`
  - `_validate_batch()`: sample 模式也會轉換成功的記錄
  - 移除 `_validate_schema_data_sample()` 方法，整合到 `_process_data_with_validation()`

### Removed

- **Parquet 支援**：
  - 從 FileSource 和 FileSink 移除 Parquet 相關代碼
  - 從 SOURCE_REGISTRY 和 SINK_REGISTRY 移除 'parquet'
  - 更新文檔移除 Parquet 提及

- **舊的配置方式**：
  - 不再支援 `type: csv/json/jsonl` 直接作為 source/sink 類型
  - 統一使用 `type: file` + `format` 組合

### Fixed

- **Datetime 處理**：
  - 修正 API Source 在 streaming 模式下 datetime 解析問題
  - Pydantic 驗證後的 datetime 物件現在可以正確傳遞給 Pathway
  - sample 和 strict 模式都會進行 Pydantic 轉換，確保 datetime 正確處理

- **API Source 配置**：
  - 修正 `interval` 參數名稱為 `refresh_interval`
  - 確保與 APIConnectorSubject 參數一致

### Documentation

- 更新 README.md：
  - 移除過時的配置方式
  - 更新特性列表（增加驗證說明）
  - 簡化範例專案列表
  - 更新專案結構說明
  - 修正執行命令為 `pwetl --config`

- 新增範例文檔：
  - `examples/01_api_source/README.md` - 完整的 YouBike API 範例說明
  - 包含環境變數配置、驗證模式、Static/Streaming 差異

### Technical Details

- **驗證模式行為**：
  ```
  none:   跳過驗證 → 回傳原始資料
  sample: Pydantic 驗證 → 成功則 model_dump()，失敗則警告 + 回傳原始資料
  strict: Pydantic 驗證 → 成功則 model_dump()，失敗則拋出錯誤
  ```

- **Datetime 轉換流程**：
  ```
  API 回應 "2026-02-05 14:46:52"
  → Pydantic 驗證轉換為 datetime 物件
  → model_dump() 保留為 datetime 物件
  → Pathway 接受並處理
  → 輸出為 ISO 8601 格式 "2026-02-05T14:46:52"
  ```

## [Previous Versions]

See git history for changes before this changelog was created.
