# 回測框架環境變數參考

## 快速參考表

### 核心配置

```bash
# 必須配置
export BACKTEST_USE_DATABASE=true                    # 啟用資料庫模式
export PROJECT_ROOT=/path/to/AIChatbot              # 專案根目錄

# 策略選擇（推薦）
export BACKTEST_SELECTION_STRATEGY=incremental      # 測試選擇策略
export BACKTEST_QUALITY_MODE=basic                  # 品質評估模式
export BACKTEST_NON_INTERACTIVE=true                # 非互動模式
```

### 完整變數列表

| 變數 | 說明 | 預設值 | 範例 |
|-----|------|--------|------|
| **資料庫連線** | | | |
| `DB_HOST` | 資料庫主機 | `localhost` | `localhost` |
| `DB_PORT` | 資料庫埠 | `5432` | `5432` |
| `DB_USER` | 資料庫用戶 | `aichatbot` | `aichatbot` |
| `DB_PASSWORD` | 資料庫密碼 | `aichatbot_password` | `your_password` |
| `DB_NAME` | 資料庫名稱 | `aichatbot_admin` | `aichatbot_admin` |
| **回測配置** | | | |
| `BACKTEST_USE_DATABASE` | 啟用資料庫模式 | `true` | `true`, `false` |
| `BACKTEST_SELECTION_STRATEGY` | 測試策略 | `full` | `incremental`, `full`, `failed_only` |
| `BACKTEST_QUALITY_MODE` | 品質模式 | `basic` | `basic`, `detailed`, `hybrid` |
| `BACKTEST_NON_INTERACTIVE` | 非互動模式 | `false` | `true`, `false` |
| `BACKTEST_SAMPLE_SIZE` | 抽樣數量 | 無（全部） | `10`, `50`, `100` |
| **策略限制** | | | |
| `BACKTEST_INCREMENTAL_LIMIT` | Incremental 限制 | `100` | `50`, `100`, `200` |
| `BACKTEST_FAILED_LIMIT` | Failed Only 限制 | `50` | `20`, `50`, `100` |
| `BACKTEST_LIMIT` | 通用限制（覆蓋） | 無 | `30` |
| **向後相容** | | | |
| `BACKTEST_DIFFICULTY` | 難度篩選 | 無 | `easy`, `medium`, `hard` |
| `BACKTEST_PRIORITIZE_FAILED` | 優先失敗測試 | `true` | `true`, `false` |
| `BACKTEST_TYPE` | 測試類型 | `smoke` | `smoke`, `full`, `custom` |
| `BACKTEST_SCENARIOS_PATH` | Excel 路徑 | 自動 | `/path/to/scenarios.xlsx` |
| **RAG API** | | | |
| `RAG_API_URL` | RAG API 地址 | `http://localhost:8100` | `http://api.example.com` |
| `VENDOR_ID` | 業者 ID | `1` | `1`, `2`, `3` |
| `BACKTEST_DISABLE_ANSWER_SYNTHESIS` | 禁用答案合成 | `false` | `true`, `false` |
| **LLM 評估** | | | |
| `OPENAI_API_KEY` | OpenAI API Key | 無 | `sk-...` |
| **其他** | | | |
| `PROJECT_ROOT` | 專案根目錄 | 自動偵測 | `/Users/user/project` |

## 常用組合

### 1. 日常開發（快速）

```bash
export BACKTEST_SELECTION_STRATEGY=incremental
export BACKTEST_QUALITY_MODE=basic
export BACKTEST_NON_INTERACTIVE=true
export BACKTEST_SAMPLE_SIZE=30
export BACKTEST_USE_DATABASE=true
export PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

python3 scripts/knowledge_extraction/backtest_framework.py
```

**說明：** 快速測試最重要的 30 個測試案例

### 2. CI/CD 自動化

```bash
export BACKTEST_SELECTION_STRATEGY=incremental
export BACKTEST_INCREMENTAL_LIMIT=100
export BACKTEST_QUALITY_MODE=basic
export BACKTEST_NON_INTERACTIVE=true
export BACKTEST_USE_DATABASE=true
export PROJECT_ROOT=${GITHUB_WORKSPACE}
export DB_HOST=${DB_HOST}
export DB_PASSWORD=${DB_PASSWORD}

python3 scripts/knowledge_extraction/backtest_framework.py
```

**說明：** CI/CD 環境使用環境變數注入敏感資訊

### 3. 週度完整測試

```bash
export BACKTEST_SELECTION_STRATEGY=full
export BACKTEST_QUALITY_MODE=basic
export BACKTEST_NON_INTERACTIVE=true
export BACKTEST_USE_DATABASE=true
export PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

python3 scripts/knowledge_extraction/backtest_framework.py
```

**說明：** 執行所有已批准的測試

### 4. 修復驗證

```bash
export BACKTEST_SELECTION_STRATEGY=failed_only
export BACKTEST_FAILED_LIMIT=20
export BACKTEST_QUALITY_MODE=basic
export BACKTEST_NON_INTERACTIVE=true
export BACKTEST_USE_DATABASE=true
export PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

python3 scripts/knowledge_extraction/backtest_framework.py
```

**說明：** 只測試之前失敗的案例

### 5. 高品質深度評估

```bash
export BACKTEST_SELECTION_STRATEGY=incremental
export BACKTEST_QUALITY_MODE=hybrid
export BACKTEST_NON_INTERACTIVE=true
export BACKTEST_SAMPLE_SIZE=20
export BACKTEST_USE_DATABASE=true
export OPENAI_API_KEY=sk-...
export PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

python3 scripts/knowledge_extraction/backtest_framework.py
```

**說明：** 使用 LLM 進行深度品質評估（需要 OpenAI API）

## Shell 腳本範例

### 創建 `.env` 文件

```bash
# backtest.env
BACKTEST_USE_DATABASE=true
BACKTEST_SELECTION_STRATEGY=incremental
BACKTEST_QUALITY_MODE=basic
BACKTEST_NON_INTERACTIVE=true
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot

# 資料庫配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
DB_NAME=aichatbot_admin

# RAG API
RAG_API_URL=http://localhost:8100
VENDOR_ID=1
```

### 使用方式

```bash
# 載入環境變數
source backtest.env

# 執行回測
python3 scripts/knowledge_extraction/backtest_framework.py

# 或一行命令
env $(cat backtest.env | xargs) python3 scripts/knowledge_extraction/backtest_framework.py
```

### 包裝腳本 (`run_backtest.sh`)

```bash
#!/bin/bash

# 設定預設值
: ${BACKTEST_STRATEGY:="incremental"}
: ${BACKTEST_MODE:="basic"}
: ${PROJECT_ROOT:=$(pwd)}

# 顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 開始回測${NC}"
echo "策略: $BACKTEST_STRATEGY"
echo "模式: $BACKTEST_MODE"
echo "專案: $PROJECT_ROOT"

# 執行回測
BACKTEST_SELECTION_STRATEGY=$BACKTEST_STRATEGY \
BACKTEST_QUALITY_MODE=$BACKTEST_MODE \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=$PROJECT_ROOT \
python3 scripts/knowledge_extraction/backtest_framework.py

# 檢查結果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 回測完成${NC}"

    # 顯示摘要
    cat output/backtest/backtest_results_summary.txt
else
    echo -e "${YELLOW}❌ 回測失敗${NC}"
    exit 1
fi
```

**使用方式：**

```bash
# 預設（incremental + basic）
./run_backtest.sh

# 自訂策略
BACKTEST_STRATEGY=full ./run_backtest.sh

# 自訂模式
BACKTEST_MODE=hybrid ./run_backtest.sh
```

## Docker 環境

### Dockerfile 範例

```dockerfile
# 設定環境變數
ENV BACKTEST_USE_DATABASE=true
ENV BACKTEST_SELECTION_STRATEGY=incremental
ENV BACKTEST_QUALITY_MODE=basic
ENV BACKTEST_NON_INTERACTIVE=true
ENV PROJECT_ROOT=/app

# 執行回測
CMD ["python3", "scripts/knowledge_extraction/backtest_framework.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  backtest:
    build: .
    environment:
      - BACKTEST_USE_DATABASE=true
      - BACKTEST_SELECTION_STRATEGY=incremental
      - BACKTEST_QUALITY_MODE=basic
      - BACKTEST_NON_INTERACTIVE=true
      - PROJECT_ROOT=/app
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_USER=aichatbot
      - DB_PASSWORD=aichatbot_password
      - DB_NAME=aichatbot_admin
      - RAG_API_URL=http://rag-api:8100
    depends_on:
      - postgres
      - rag-api
    volumes:
      - ./output:/app/output

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_USER=aichatbot
      - POSTGRES_PASSWORD=aichatbot_password
      - POSTGRES_DB=aichatbot_admin
```

**使用方式：**

```bash
# 啟動並執行
docker-compose up backtest

# 自訂策略
docker-compose run -e BACKTEST_SELECTION_STRATEGY=full backtest
```

## 環境變數優先級

1. **命令行環境變數**（最高優先級）
   ```bash
   BACKTEST_STRATEGY=full python3 backtest_framework.py
   ```

2. **Shell 環境變數**
   ```bash
   export BACKTEST_STRATEGY=full
   python3 backtest_framework.py
   ```

3. **`.env` 文件**
   ```bash
   source .env
   python3 backtest_framework.py
   ```

4. **程式碼預設值**（最低優先級）
   ```python
   os.getenv("BACKTEST_STRATEGY", "full")  # "full" 是預設值
   ```

## 故障排除

### 變數未生效

```bash
# 檢查變數是否設定
echo $BACKTEST_SELECTION_STRATEGY

# 確認變數傳遞到 Python
python3 -c "import os; print(os.getenv('BACKTEST_SELECTION_STRATEGY'))"

# 使用 env 命令確保變數傳遞
env BACKTEST_SELECTION_STRATEGY=incremental python3 backtest_framework.py
```

### 敏感資訊安全

```bash
# ❌ 不要在命令行歷史中暴露密碼
export DB_PASSWORD=secret123

# ✅ 使用 .env 文件（加入 .gitignore）
echo "DB_PASSWORD=secret123" >> .env.local
source .env.local

# ✅ 使用密鑰管理服務
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id db-password --query SecretString --output text)
```

## 驗證配置

```bash
# 創建驗證腳本
cat > check_env.sh << 'EOF'
#!/bin/bash

echo "檢查回測環境變數配置"
echo "======================="

required_vars=(
    "BACKTEST_USE_DATABASE"
    "PROJECT_ROOT"
)

optional_vars=(
    "BACKTEST_SELECTION_STRATEGY"
    "BACKTEST_QUALITY_MODE"
    "DB_HOST"
    "DB_PASSWORD"
)

echo -e "\n必須變數:"
for var in "${required_vars[@]}"; do
    value="${!var}"
    if [ -z "$value" ]; then
        echo "  ❌ $var: 未設定"
    else
        echo "  ✅ $var: $value"
    fi
done

echo -e "\n選用變數:"
for var in "${optional_vars[@]}"; do
    value="${!var}"
    if [ -z "$value" ]; then
        echo "  ⚠️  $var: 使用預設值"
    else
        # 隱藏密碼
        if [[ $var == *"PASSWORD"* ]]; then
            echo "  ✅ $var: ****"
        else
            echo "  ✅ $var: $value"
        fi
    fi
done
EOF

chmod +x check_env.sh
./check_env.sh
```

## 相關文件

- [回測策略指南](./BACKTEST_STRATEGIES.md) - 詳細策略說明
- 資料庫配置 - 資料庫設定
- CI/CD 整合 - 持續整合配置
