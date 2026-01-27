# 安裝指南

## 系統需求

- Python 3.12 或更高版本
- Linux 或 WSL 環境（Pathway 需要）

## 安裝方法

### 方法 1：開發模式安裝（推薦用於開發）

使用 uv（推薦）：

```bash
# 在 WSL 或 Linux 環境中
uv sync

# 驗證安裝
python test_install.py
```

使用 pip：

```bash
# 在 WSL 或 Linux 環境中
pip install -e .

# 驗證安裝
python test_install.py
```

### 方法 2：正式安裝

```bash
pip install .
```

### 方法 3：從原始碼建置

```bash
# 建置 wheel 套件
python -m build

# 安裝建置的套件
pip install dist/pwetl-0.1.0-py3-none-any.whl
```

## 驗證安裝

執行測試腳本驗證安裝是否成功：

```bash
python test_install.py
```

如果所有測試都通過，你應該會看到：

```
✓ All tests passed! pwetl is correctly installed.
```

你也可以在 Python 中測試：

```python
import pwetl
print(pwetl.__version__)  # 應該輸出: 0.1.0

from pwetl import ETLEngine
engine = ETLEngine("examples/config.yaml")
# 如果沒有錯誤，說明安裝成功
```

## 執行範例

```bash
# 執行基本範例
python -c "from pwetl import ETLEngine; ETLEngine('examples/config.yaml').execute()"

# 執行多源多目標範例
python examples/run_multi_examples.py
```

## 常見問題

### Q: 在 Windows 上安裝失敗

A: Pathway 需要 Linux 環境。請在 WSL（Windows Subsystem for Linux）中安裝和執行。

安裝 WSL：

```powershell
# 在 PowerShell（管理員模式）中執行
wsl --install
```

然後在 WSL 中進入專案目錄並安裝：

```bash
cd /mnt/c/Users/your_username/path/to/pwetl
uv sync
# 或
pip install -e .
```

### Q: import pwetl 失敗

A: 確保你已經安裝了套件（使用 `pip install -e .` 或 `uv sync`），並且在正確的虛擬環境中執行。

### Q: 找不到模組

A: 如果使用開發模式安裝（`pip install -e .`），確保你在專案根目錄中執行命令。

## 可選功能安裝

根據你的需求，可以安裝額外的功能支援：

### PostgreSQL 支援

```bash
# 使用 uv
uv sync --extra postgres

# 使用 pip
pip install -e ".[postgres]"
```

### MySQL 支援

```bash
# 使用 uv
uv sync --extra mysql

# 使用 pip
pip install -e ".[mysql]"
```

### 安裝所有資料庫支援

```bash
# 使用 uv
uv sync --extra database

# 使用 pip
pip install -e ".[database]"
```

### 安裝所有功能（包含開發工具）

```bash
# 使用 uv
uv sync --extra all

# 使用 pip
pip install -e ".[all]"
```

## 開發設定

如果你想為 pwetl 貢獻程式碼：

```bash
# 安裝開發相依套件
uv sync --extra dev
# 或
pip install -e ".[dev]"

# 執行測試（將來）
pytest

# 程式碼格式化
black src/

# 程式碼檢查
ruff check src/
```

## 解除安裝

```bash
pip uninstall pwetl
```
