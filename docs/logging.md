# Logging 與例外處理規範

本文件定義 pwetl 專案中 logging 與自訂例外的使用慣例，供開發者在新增或修改元件時參照。

---

## Logger 宣告

每個檔案在頂層宣告一個模組級 `LOGGER`，**不要**在方法內 inline 建立：

```python
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)
```

---

## 訊息格式

依元件類型使用統一前綴，方便從 log 追蹤問題來源：

| 元件類型 | 格式 | 範例 |
|----------|------|------|
| Source | `"Source '<name>': <動作>"` | `LOGGER.info("Source '%s': reading %s", self.name, path)` |
| Sink | `"Sink '<name>': <動作>"` | `LOGGER.info("Sink '%s': writing %s to %s", self.name, fmt, path)` |
| Transform | `"Transform: <動作>"` | `LOGGER.info("Transform: processing complete")` |
| Pipeline | `"Pipeline <動作>"` | `LOGGER.info("Pipeline starting...")` |

- Source / Sink 名稱用單引號包裹。
- Pipeline 全域只有一個，不帶引號。
- Transform 同理，不帶名稱。

---

## Log 等級規則

| 等級 | 用途 | 範例場景 |
|------|------|----------|
| **ERROR** | 只在 CLI 統一輸出（依例外類別加 `[Source]` / `[Sink]` 等前綴）；元件內部的最終失敗（如 API retry 耗盡）也可 ERROR | `logger.error("[Source] %s", e)` |
| **WARNING** | teardown 清理失敗、retry 中、資料驗證有問題但不中斷執行 | `LOGGER.warning("Source '%s' cleanup failed: %s", name, e)` |
| **INFO** | 關鍵進度點：初始化完成、讀取完成、寫入排程、teardown 完成 | `LOGGER.info("Pipeline setup complete")` |
| **DEBUG** | 輪詢等待、內部細節 | `LOGGER.debug("Streaming mode: waiting %d seconds...", interval)` |

### 重點原則

1. **元件內部不要 `LOGGER.error()`** — 遇到錯誤時拋出對應的自訂例外，由 CLI 層統一輸出 ERROR。
2. **避免重複 log** — Engine 層不再 log error，Pipeline 拋例外後由 CLI 的 `except` 區塊負責顯示。
3. **`warnings.warn()` 一律改用 `LOGGER.warning()`** — 統一由 logging 系統控制輸出。

---

## 自訂例外

定義在 `pwetl.core.exceptions`，依階段分類：

| 例外類別 | 使用場景 |
|----------|----------|
| `SourceError` | Source 初始化失敗、讀取失敗 |
| `TransformError` | Transform 初始化失敗、處理失敗、回傳值型別錯誤、未產出 Sink 所需的 table |
| `SinkError` | Sink 初始化失敗、寫入失敗 |
| `ConfigurationError` | 設定檔格式或內容錯誤 |

### Pipeline 層使用方式

Pipeline 是例外的產生點，將底層 `Exception` 包裝成對應的自訂例外：

```python
from pwetl.core.exceptions import SourceError, TransformError, SinkError

# Source 階段
except Exception as e:
    raise SourceError(f"Source '{name}' initialization failed: {e}") from e

# Transform 階段
except Exception as e:
    raise TransformError(f"Transform processing failed: {e}") from e

# Sink 階段
except Exception as e:
    raise SinkError(f"Sink '{name}' write failed: {e}") from e
```

### CLI 層使用方式

CLI 是例外的消費點，依類別輸出不同前綴：

```python
from pwetl.core.exceptions import SourceError, TransformError, SinkError, ConfigurationError

except SourceError as e:
    logger.error("[Source] %s", e)
except TransformError as e:
    logger.error("[Transform] %s", e)
except SinkError as e:
    logger.error("[Sink] %s", e)
except ConfigurationError as e:
    logger.error("[Config] %s", e)
except Exception as e:
    logger.error("Execution failed: %s", e)
```

---

## 新增元件時的 Checklist

1. 檔案頂層加 `LOGGER = get_logger(__name__)`。
2. `setup()` 結束時 log `INFO`。
3. `read()` / `write()` 開頭或結束時 log `INFO`。
4. `teardown()` 清理失敗用 `WARNING`，成功可選擇性 log `INFO`。
5. 不要在元件內用 `LOGGER.error()` — 拋例外讓上層處理。
6. 不要用 `warnings.warn()` — 用 `LOGGER.warning()`。
7. 不要在方法內 `import logging` 或 inline 建立 logger。
