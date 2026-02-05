# 環境變數配置指南

pwetl 支援在 YAML 配置檔中使用環境變數，讓你可以安全地管理敏感資訊（如密碼、API token 等），而不需要將這些資訊硬編碼在配置檔中。

## 為什麼使用環境變數？

- **安全性**：避免在版本控制中提交敏感資訊
- **靈活性**：同一份配置檔可用於不同環境（開發、測試、正式環境）
- **最佳實踐**：符合 [12-Factor App](https://12factor.net/config) 配置管理原則

## 基本語法

pwetl 支援兩種環境變數語法：

### 1. 必需的環境變數

\`\`\`yaml
\${VAR_NAME}
\`\`\`

如果環境變數 \`VAR_NAME\` 未設定，會拋出錯誤。

### 2. 帶預設值的環境變數

\`\`\`yaml
\${VAR_NAME:default_value}
\`\`\`

如果環境變數 \`VAR_NAME\` 未設定，使用 \`default_value\`。

## 範例

### 基本範例

\`\`\`yaml
sources:
  - name: db_data
    type: postgres
    host: \${DB_HOST:localhost}     # 預設為 localhost
    port: \${DB_PORT:5432}           # 預設為 5432
    database: \${DB_NAME}            # 必須設定
    username: \${DB_USER}            # 必須設定
    password: \${DB_PASSWORD}        # 必須設定
    query: "SELECT * FROM users"
    schema:
      id: int
      name: str

sinks:
  - name: output
    type: file
    path: \${OUTPUT_PATH:output.csv}
    format: csv
\`\`\`

### API 配置範例

\`\`\`yaml
sources:
  - name: api_data
    type: api
    url: \${API_URL}
    headers:
      Authorization: "Bearer \${API_TOKEN}"
    mode: \${API_MODE:static}
    refresh_interval: \${REFRESH_INTERVAL:60}
    pydantic_model: models.MyModel
    schema:
      id: int
      value: str

sinks:
  - name: output
    type: file
    path: \${OUTPUT_FILE:data/output.jsonl}
    format: jsonl
\`\`\`

## 設定環境變數的方法

### 方法 1：使用 .env 檔案（推薦）

pwetl 會自動載入當前目錄的 \`.env\` 檔案。

1. 建立 \`.env\` 檔案：

\`\`\`env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=my_secure_password

# API Configuration
API_URL=https://data.taipei/api/v1/dataset/youbike
API_TOKEN=your_api_token_here

# Output Configuration
OUTPUT_PATH=data/output.csv
\`\`\`

2. 執行 pwetl：

\`\`\`bash
pwetl --config config.yaml
\`\`\`

環境變數會自動從 \`.env\` 檔案載入。

### 方法 2：直接在命令列設定（Linux/Mac/WSL）

\`\`\`bash
# 臨時設定（僅對當前命令有效）
DB_HOST=localhost DB_NAME=mydb pwetl --config config.yaml

# 或者先 export（對當前 shell 會話有效）
export DB_HOST=localhost
export DB_NAME=mydb
export DB_USER=myuser
export DB_PASSWORD=secret
pwetl --config config.yaml
\`\`\`

### 方法 3：在 Python 中設定

\`\`\`python
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
\`\`\`

## .env 檔案最佳實踐

### 1. 永遠不要提交 .env 到版本控制

在 \`.gitignore\` 中加入：

\`\`\`gitignore
.env
.env.local
.env.*.local
\`\`\`

### 2. 提供 .env.example 範本

建立 \`.env.example\` 作為範本（不含真實的敏感資訊）：

\`\`\`env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# API Configuration
API_URL=https://api.example.com
API_TOKEN=your_token_here
\`\`\`

### 3. 在 README 中說明如何設定

\`\`\`markdown
## 設定

1. 複製 \`.env.example\` 為 \`.env\`
2. 填入實際的配置值
3. 執行 pipeline
\`\`\`

## 實際範例

查看 [examples/01_api_source/](../examples/01_api_source/) 範例，展示如何：

- 使用 \`.env\` 檔案管理 API URL
- 設定帶預設值的環境變數
- 在 Transform 中存取環境變數

### 環境變數範例

\`.env\` 檔案：

\`\`\`env
API_URL=https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json
\`\`\`

\`config.yaml\` 檔案：

\`\`\`yaml
sources:
  - name: youbike
    type: api
    url: \${API_URL}
    mode: static
    validation_mode: sample
    pydantic_model: transform.YouBikeStation
    schema:
      sno: str
      sna: str
      tot: int
      sbi: int
      # ...
\`\`\`

## 常見問題

### Q: 環境變數未被替換

A: 確保：
1. \`.env\` 檔案在當前工作目錄
2. 環境變數名稱拼寫正確
3. 使用正確的語法：\`\${VAR_NAME}\` 或 \`\${VAR_NAME:default}\`

### Q: 如何使用不同的 .env 檔案？

A: 在執行前手動載入：

\`\`\`bash
# 使用不同的 .env 檔案
export $(cat .env.production | xargs)
pwetl --config config.yaml
\`\`\`

### Q: 如何在 Transform 中存取環境變數？

A: 使用 Python 的 \`os.environ\`：

\`\`\`python
import os

class MyTransform(BaseTransform):
    def transform(self, tables):
        api_key = os.getenv('API_KEY', 'default_key')
        # ...
\`\`\`

## 安全建議

1. **永遠不要在程式碼中硬編碼敏感資訊**
2. **不要提交 .env 檔案到版本控制**
3. **使用強密碼和定期輪換 token**
4. **在正式環境使用專門的密鑰管理服務**（如 AWS Secrets Manager、Azure Key Vault）
5. **限制環境變數的存取權限**
