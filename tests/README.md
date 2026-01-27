# pwetl 測試

## 執行測試

### 安裝測試依賴

```bash
# 使用 uv
uv pip install -e ".[dev]"

# 或使用 pip
pip install -e ".[dev]"
```

### 執行所有測試

```bash
pytest
```

### 執行特定測試檔案

```bash
pytest tests/test_installation.py
```

### 執行測試並顯示涵蓋率

```bash
pytest --cov=pwetl --cov-report=html
```

涵蓋率報告會產生在 `htmlcov/index.html`。

### 執行測試並顯示詳細輸出

```bash
pytest -vv
```

## 測試結構

```text
tests/
├── __init__.py
├── README.md
├── test_installation.py    # 安裝和基本 import 測試
├── test_env.py             # 環境變數替換測試
├── test_schema.py          # Schema 解析測試
├── test_loader.py          # 動態載入測試
├── test_config.py          # 配置載入測試
└── test_registry.py        # Registry 和 Factory 測試
```

## 測試涵蓋範圍

- **test_installation.py**: 驗證套件安裝和基本 import
- **test_env.py**: 環境變數替換工具（EnvVarSubstitution, load_env_file）
- **test_schema.py**: Pathway Schema 解析器（SchemaParser）
- **test_loader.py**: 動態類別載入（DynamicLoader, TransformLoader）
- **test_config.py**: YAML 配置載入和驗證（ConfigLoader）
- **test_registry.py**: Source/Sink 註冊和工廠（SourceFactory, SinkFactory）

## 添加新測試

新增測試檔案時，請遵循以下命名規則：

- 測試檔案：`test_*.py`
- 測試類別：`Test*`
- 測試函數：`test_*`

範例：

```python
def test_my_feature():
    """Test description."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    assert result == expected
```
