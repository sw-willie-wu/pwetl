# 使用指南

## CLI 使用

pwetl 提供命令列介面，讓你可以直接從終端機執行 ETL pipeline。

### 基本用法

```bash
pwetl --config config.yaml
```

在 WSL/Linux 環境中使用 Python 模組方式：

```bash
python -m pwetl.cli --config config.yaml
```

### 命令列選項

#### `--config` (必需)

指定 YAML 配置檔路徑。

```bash
pwetl --config config.yaml
pwetl --config examples/02_wra_waterlevel/config.yaml
```

#### `--verbose`, `-v`

啟用詳細輸出，顯示更多執行資訊。

```bash
pwetl --config config.yaml --verbose
pwetl --config config.yaml -v
```

#### `--dry-run`

驗證配置檔而不實際執行 pipeline（試運行模式）。

```bash
pwetl --config config.yaml --dry-run
```

這會檢查：
- 配置檔是否存在
- YAML 語法是否正確
- 必要欄位是否存在
- Transform 模組是否可以載入

#### `--env-file`

指定要載入的 .env 檔案路徑。

```bash
pwetl --config config.yaml --env-file .env.production
```

如果不指定，會自動嘗試載入當前目錄的 `.env` 檔案（如果存在）。

#### `--version`

顯示 pwetl 版本。

```bash
pwetl --version
# 輸出: pwetl 0.1.0
```

## 使用範例

### 範例 1：基本執行

```bash
cd examples/02_wra_waterlevel
python -m pwetl.cli --config config.yaml
```

### 範例 2：詳細模式

```bash
python -m pwetl.cli --config config.yaml --verbose
```

### 範例 3：驗證配置

```bash
# 只驗證配置，不執行
python -m pwetl.cli --config config.yaml --dry-run --verbose
```

### 範例 4：使用環境變數

```bash
# 載入特定的環境變數檔案
python -m pwetl.cli --config config.yaml --env-file .env.production
```

### 範例 5：多源多目標

```bash
# 執行多源多目標 pipeline
cd examples/03_multi_source
python -m pwetl.cli --config config.yaml --verbose
```

## 在 WSL 環境中執行

由於 Pathway 需要 Linux 環境，請務必在 WSL 中執行：

```bash
# 進入專案目錄
cd /mnt/c/Users/your_username/path/to/pwetl

# 啟動虛擬環境
source .venv/bin/activate

# 執行 ETL
python -m pwetl.cli --config config.yaml
```

## 退出碼

CLI 使用標準退出碼：

- `0` - 成功
- `1` - 一般錯誤（配置錯誤、執行失敗等）
- `130` - 使用者中斷（Ctrl+C）

## 常見問題

### Q: 命令找不到

```bash
$ pwetl --config config.yaml
pwetl: command not found
```

**解決方法**：

```bash
# 使用 Python 模組方式執行
python -m pwetl.cli --config config.yaml
```

### Q: 在 Windows 上執行失敗

A: Pathway 需要 Linux 環境。請在 WSL 中執行。詳見[安裝指南](installation.md)。

## 參考

- [安裝指南](installation.md)
- [環境變數配置](environment-variables.md)
- [多源多匯設計](multi-source-sink.md)
- [主文件](../README.md)
