# 安裝指南

## 系統需求

- Python 3.12 或更高版本
- Linux 或 WSL 環境（Pathway 需要）

## 安裝方法

### 使用 uv（推薦）

```bash
# 在 WSL 或 Linux 環境中
uv sync
```

### 使用 pip

```bash
# 開發模式安裝
pip install -e .

# 或正式安裝
pip install .
```

## 驗證安裝

在 Python 中測試：

```python
import pwetl
print(pwetl.__version__)  # 應該輸出: 0.1.0

from pwetl import ETLEngine
# 如果沒有錯誤，說明安裝成功
```

或執行測試：

```bash
pytest tests/
```

## 執行範例

```bash
# 執行 YouBike API 範例
cd examples/01_api_source
pwetl --config config_static.yaml
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
```

### Q: Python 版本不符

A: pwetl 需要 Python 3.12 或更高版本。請使用以下指令檢查版本：

```bash
python --version
```

如需安裝 Python 3.12+：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12

# 或使用 pyenv
pyenv install 3.12.0
pyenv local 3.12.0
```

### Q: 安裝 Pathway 時出現錯誤

A: 確保你在 Linux 或 WSL 環境中，並且系統已更新：

```bash
sudo apt update
sudo apt upgrade
```

### Q: 如何使用虛擬環境？

A: 使用 uv 會自動管理虛擬環境。如果使用 pip：

```bash
# 創建虛擬環境
python -m venv .venv

# 啟用虛擬環境
source .venv/bin/activate  # Linux/Mac/WSL
# 或
.venv\Scripts\activate  # Windows (不建議，Pathway 不支援)

# 安裝
pip install -e .
```

## 開發環境設定

如果你要開發 pwetl：

```bash
# 安裝開發依賴
uv sync

# 執行測試
pytest tests/

# 執行測試並檢查覆蓋率
pytest --cov=src/pwetl tests/
```
