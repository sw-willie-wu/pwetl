# 環境變數配置指南

pwetl 支援在 YAML 配置檔中使用環境變數，讓你可以安全地管理敏感資訊（如密碼、API token 等），而不需要將這些資訊硬編碼在配置檔中。

## 為什麼使用環境變數？

✅ **安全性**：避免在版本控制中提交敏感資訊
✅ **靈活性**：同一份配置檔可用於不同環境（開發、測試、正式環境）
✅ **最佳實踐**：符合 [12-Factor App](https://12factor.net/config) 配置管理原則

## 基本語法

pwetl 支援兩種環境變數語法：

### 1. 必需的環境變數

```yaml
${VAR_NAME}
```

如果環境變數 `VAR_NAME` 未設定，會拋出錯誤。

### 2. 帶預設值的環境變數

```yaml
${VAR_NAME:default_value}
```

如果環境變數 `VAR_NAME` 未設定，使用 `default_value`。

## 範例

### 基本範例

```yaml
pipeline:
  name: my_pipeline

  source:
    type: postgresql
    host: ${DB_HOST:localhost}     # 預設為 localhost
    port: ${DB_PORT:5432}           # 預設為 5432
    database: ${DB_NAME}            # 必須設定
    user: ${DB_USER}                # 必須設定
    password: ${DB_PASSWORD}        # 必須設定
    query: "SELECT * FROM users"

  sink:
    type: csv
    path: ${OUTPUT_PATH:output.csv}
```

### API 配置範例

```yaml
pipeline:
  name: api_pipeline

  source:
    type: api
    url: ${API_URL}
    auth:
      type: ${AUTH_TYPE:bearer}
      token: ${API_TOKEN}
    params:
      limit: ${API_LIMIT:100}

  sink:
    type: jsonl
    path: ${OUTPUT_FILE:data/output.jsonl}
```

## 設定環境變數的方法

### 方法 1：直接在 Python 中設定

```python
import os
from pwetl import ETLEngine

# 設定環境變數
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'mydb'
os.environ['DB_USER'] = 'myuser'
os.environ['DB_PASSWORD'] = 'mypassword'

# 執行 ETL
engine = ETLEngine("config.yaml")
engine.execute()
```

### 方法 2：使用命令列（Linux/Mac/WSL）

```bash
# 臨時設定（僅對當前命令有效）
DB_HOST=localhost DB_NAME=mydb DB_USER=myuser DB_PASSWORD=secret python main.py

# 或者先 export（對當前 shell 會話有效）
export DB_HOST=localhost
export DB_NAME=mydb
export DB_USER=myuser
export DB_PASSWORD=secret
python main.py
```

### 方法 3：使用命令列（Windows PowerShell）

```powershell
# 設定環境變數
$env:DB_HOST="localhost"
$env:DB_NAME="mydb"
$env:DB_USER="myuser"
$env:DB_PASSWORD="secret"

# 執行程式
python main.py
```

### 方法 4：使用 .env 檔案（推薦）

1. 安裝 `python-dotenv`：

```bash
pip install python-dotenv
```

2. 建立 `.env` 檔案：

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=my_secure_password
API_TOKEN=your_api_token_here
OUTPUT_PATH=data/output.csv
```

3. 在 Python 中載入：

```python
from dotenv import load_dotenv
from pwetl import ETLEngine

# 載入 .env 檔案
load_dotenv()

# 現在環境變數已經載入，可以執行 ETL
engine = ETLEngine("config_with_env.yaml")
engine.execute()
```

## .env 檔案最佳實踐

### 1. 永遠不要提交 .env 到版本控制

在 `.gitignore` 中加入：

```gitignore
.env
.env.local
.env.*.local
```

### 2. 提供 .env.example 範本

建立 `.env.example` 作為範本（不含真實的敏感資訊）：

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# API Configuration
API_URL=https://api.example.com
API_TOKEN=your_token_here
```

### 3. 在 README 中說明如何設定

```markdown
## 設定

1. 複製 `.env.example` 為 `.env`
2. 填入實際的配置值
3. 執行 pipeline
```

## 實際範例

### 範例 1：開發環境 vs 正式環境

**config.yaml**（同一份配置）

```yaml
pipeline:
  name: data_pipeline

  source:
    type: postgresql
    host: ${DB_HOST}
    database: ${DB_NAME}
    user: ${DB_USER}
    password: ${DB_PASSWORD}
    query: "SELECT * FROM users"

  sink:
    type: csv
    path: ${OUTPUT_PATH}
```

**開發環境 (.env.dev)**

```env
DB_HOST=localhost
DB_NAME=dev_db
DB_USER=dev_user
DB_PASSWORD=dev_pass
OUTPUT_PATH=output_dev.csv
```

**正式環境 (.env.prod)**

```env
DB_HOST=prod-db.company.com
DB_NAME=production
DB_USER=prod_user
DB_PASSWORD=secure_prod_pass
OUTPUT_PATH=/var/data/output_prod.csv
```

載入不同環境：

```python
from dotenv import load_dotenv
from pwetl import ETLEngine
import sys

# 根據參數載入不同環境
env = sys.argv[1] if len(sys.argv) > 1 else 'dev'
load_dotenv(f'.env.{env}')

engine = ETLEngine("config.yaml")
engine.execute()
```

### 範例 2：多個資料源使用環境變數

```yaml
pipeline:
  name: multi_source_with_env

  sources:
    - name: source_db
      type: postgresql
      host: ${SOURCE_DB_HOST}
      database: ${SOURCE_DB_NAME}
      user: ${SOURCE_DB_USER}
      password: ${SOURCE_DB_PASSWORD}
      query: "SELECT * FROM table1"

    - name: api_data
      type: api
      url: ${API_URL}
      auth:
        type: bearer
        token: ${API_TOKEN}

  transform:
    module: transforms
    function: merge_sources

  sink:
    type: postgresql
    host: ${TARGET_DB_HOST}
    database: ${TARGET_DB_NAME}
    user: ${TARGET_DB_USER}
    password: ${TARGET_DB_PASSWORD}
    table: ${TARGET_TABLE}
```

對應的 `.env`：

```env
# Source Database
SOURCE_DB_HOST=source.example.com
SOURCE_DB_NAME=source_db
SOURCE_DB_USER=reader
SOURCE_DB_PASSWORD=read_pass

# API
API_URL=https://api.example.com/data
API_TOKEN=api_token_here

# Target Database
TARGET_DB_HOST=target.example.com
TARGET_DB_NAME=warehouse
TARGET_DB_USER=writer
TARGET_DB_PASSWORD=write_pass
TARGET_TABLE=merged_data
```

## 常見問題

### Q: 環境變數中的值包含特殊字元怎麼辦？

A: 在 .env 檔案中使用引號：

```env
PASSWORD="p@ssw0rd!with$pecial"
URL="https://api.example.com/path?key=value&foo=bar"
```

### Q: 如何在環境變數中使用多行字串？

A: 環境變數不適合多行字串。對於複雜的 SQL 查詢，建議：

```yaml
# 將 query 保留在 YAML 中
source:
  type: postgresql
  host: ${DB_HOST}
  password: ${DB_PASSWORD}
  query: |
    SELECT
      id,
      name,
      email
    FROM users
    WHERE active = true
```

### Q: 必需的環境變數未設定時會發生什麼？

A: pwetl 會拋出明確的錯誤訊息：

```
ValueError: Environment variable 'DB_PASSWORD' is not set and no default value provided.
Set the variable or use syntax: ${VAR_NAME:default_value}
```

### Q: 如何驗證環境變數是否正確載入？

A: 在 Python 中檢查：

```python
import os
from dotenv import load_dotenv

load_dotenv()

# 檢查環境變數
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
```

## 安全建議

1. **永遠不要**提交包含敏感資訊的檔案到版本控制
2. **使用強密碼**作為環境變數值
3. **限制 .env 檔案權限**（Linux/Mac）：
   ```bash
   chmod 600 .env
   ```
4. **定期輪換**敏感憑證（密碼、API token）
5. **在 CI/CD 中**使用加密的環境變數或秘密管理服務

## 相關範例

- [config_with_env.yaml](examples/config_with_env.yaml) - 資料庫配置使用環境變數
- [config_api_with_env.yaml](examples/config_api_with_env.yaml) - API 配置使用環境變數
- [.env.example](examples/.env.example) - 環境變數範本
- [run_with_env.py](examples/run_with_env.py) - 執行範例

## 進階：Docker 中使用環境變數

在 Docker 中，可以透過 `-e` 或 `--env-file` 傳遞環境變數：

```bash
# 使用 -e 傳遞個別變數
docker run -e DB_HOST=db.example.com -e DB_PASSWORD=secret my-etl-image

# 使用 --env-file 傳遞整個 .env 檔案
docker run --env-file .env my-etl-image
```

Docker Compose 範例：

```yaml
version: '3.8'
services:
  etl:
    build: .
    env_file:
      - .env
    # 或者
    environment:
      - DB_HOST=${DB_HOST}
      - DB_PASSWORD=${DB_PASSWORD}
```
