# 🚀 AIChatbot 後台管理系統 - 完整啟動指南

選擇你的啟動方式：
- **方式 1: Docker** - 推薦，無需安裝 PostgreSQL ⭐
- **方式 2: 本機安裝** - 需要手動安裝資料庫

---

## 🐳 方式 1: 使用 Docker（推薦）

### 為什麼選擇 Docker？
- ✅ 無需安裝 PostgreSQL
- ✅ 環境完全隔離
- ✅ 一鍵啟動和停止
- ✅ 包含 pgAdmin（資料庫管理介面）
- ✅ 易於清理和重置

---

### 📋 準備工作

#### 1. 安裝 Docker Desktop

**macOS**:
```bash
brew install --cask docker
# 或從官網下載：https://www.docker.com/products/docker-desktop
```

**Windows**:
下載並安裝：https://www.docker.com/products/docker-desktop

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# 啟動 Docker 服務
sudo systemctl start docker
```

#### 2. 啟動 Docker Desktop 並檢查

```bash
docker --version
docker-compose --version
```

---

### 🚀 快速啟動（5 步驟，10 分鐘）

#### 步驟 1: 啟動 Docker 服務

```bash
# 啟動 PostgreSQL + Redis + pgAdmin
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 應該看到：
# NAME                    STATUS    PORTS
# aichatbot-postgres      running   0.0.0.0:5432->5432/tcp
# aichatbot-redis         running   0.0.0.0:6379->6379/tcp
# aichatbot-pgadmin       running   0.0.0.0:5050->80/tcp
```

如果看到 `healthy` 或 `running`，代表成功！

---

#### 步驟 2: 設定 Python 環境

```bash
cd backend

# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt
```

---

#### 步驟 3: 設定環境變數

```bash
# 複製 Docker 配置檔
cp .env.docker .env

# 編輯 .env 檔案
nano .env  # 或用 VSCode: code .env
```

**⚠️ 必須修改這一行：**
```env
OPENAI_API_KEY=sk-your-api-key-here  # 改成你的真實 API Key
```

**如何取得 OpenAI API Key？**
1. 前往 https://platform.openai.com/api-keys
2. 點擊 "Create new secret key"
3. 複製並貼到 `.env` 檔案

**其他配置（可選）：**
```env
# 使用較便宜的模型（成本降低 10 倍）
CHAT_MODEL=gpt-3.5-turbo              # 預設是 gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small # 預設是 text-embedding-3-large
```

---

#### 步驟 4: 初始化資料庫

```bash
# 建立資料表
python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"

# 看到這個就成功了：
# CREATE TABLE conversations ...
# CREATE TABLE knowledge_files ...
```

---

#### 步驟 5: 啟動後端

```bash
uvicorn app.main:app --reload
```

**看到這個就成功了：**
```
🚀 AIChatbot Admin v1.0.0 啟動成功！
📝 API 文件: http://localhost:8000/docs
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### ✅ 測試系統

**保持後端運行，開啟新的終端機：**

```bash
cd backend
source venv/bin/activate  # 啟動虛擬環境

# 測試 1: 匯入並處理對話
python test_example.py

# 測試 2: 生成 Markdown 知識庫
python test_knowledge.py

# 測試 3: 查看生成的檔案
cd ../knowledge-base
ls -la
cat 產品功能.md  # 或其他分類
```

**測試結果應該顯示：**
```
✅ 匯入成功
✅ 處理成功
✅ 生成成功
檔案數: 2
對話數: 6
```

---

### 🔧 Docker 管理命令

```bash
# 啟動所有服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs
docker-compose logs postgres  # 特定服務

# 即時日誌
docker-compose logs -f

# 停止服務（保留資料）
docker-compose stop

# 重新啟動
docker-compose start

# 停止並移除容器（保留資料）
docker-compose down

# 停止並刪除所有資料（⚠️ 小心使用）
docker-compose down -v
```

---

### 🗄️ 資料庫管理

#### 方式 A: pgAdmin（GUI，推薦）

1. **開啟瀏覽器**：http://localhost:5050

2. **登入 pgAdmin**：
   - Email: `admin@aichatbot.com`
   - Password: `admin`

3. **新增伺服器連接**：
   - 右鍵 "Servers" → "Register" → "Server"
   - General 標籤：
     - Name: `AIChatbot DB`
   - Connection 標籤：
     - Host: `localhost`
     - Port: `5432`
     - Database: `aichatbot_admin`
     - Username: `aichatbot`
     - Password: `aichatbot_password`

4. **查看資料**：
   - 展開：Servers → AIChatbot DB → Databases → aichatbot_admin → Schemas → public → Tables
   - 右鍵 `conversations` → "View/Edit Data" → "All Rows"

#### 方式 B: 命令列

```bash
# 進入 PostgreSQL 容器
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 查詢對話數量
SELECT COUNT(*) FROM conversations;

# 查看所有資料表
\dt

# 查看對話列表
SELECT id, primary_category, status FROM conversations LIMIT 5;

# 離開
\q
```

---

### 🐛 疑難排解

#### ❌ 問題 1: Docker 容器啟動失敗

```bash
# 檢查容器狀態
docker-compose ps

# 查看錯誤日誌
docker-compose logs postgres

# 確認端口未被佔用
lsof -i :5432  # macOS/Linux
netstat -ano | findstr :5432  # Windows

# 如果端口被佔用，停止佔用的程式或修改 docker-compose.yml 中的端口
```

#### ❌ 問題 2: 無法連接資料庫

```bash
# 確認 PostgreSQL 健康狀態
docker-compose ps
# 狀態應該是 "healthy" 或 "running"

# 如果是 "starting"，等待幾秒後重試

# 測試連接
docker exec aichatbot-postgres pg_isready -U aichatbot
# 應該顯示：accepting connections
```

#### ❌ 問題 3: OpenAI API 錯誤

```bash
# 檢查 API Key
cd backend
cat .env | grep OPENAI_API_KEY

# 測試 API Key 是否有效
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-你的API金鑰"

# 應該返回模型列表，而不是錯誤
```

#### ❌ 問題 4: 資料庫初始化失敗

```bash
# 完全重置資料庫
docker-compose down -v  # 刪除所有資料
docker-compose up -d    # 重新啟動

# 等待服務啟動完成
sleep 10

# 重新初始化
cd backend
source venv/bin/activate
python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"
```

---

### 📊 Docker 服務資訊

| 服務 | 端口 | 用途 | 登入資訊 |
|------|------|------|---------|
| **FastAPI 後端** | 8000 | API 服務 | - |
| **PostgreSQL** | 5432 | 資料庫 | user: `aichatbot`<br>pass: `aichatbot_password` |
| **Redis** | 6379 | 快取/任務隊列 | - |
| **pgAdmin** | 5050 | 資料庫管理介面 | email: `admin@aichatbot.com`<br>pass: `admin` |

---

## 💻 方式 2: 本機安裝

如果你不想用 Docker，可以選擇本機安裝。

### 📋 準備工作

#### 1. 安裝 PostgreSQL

**macOS**:
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install postgresql-16
sudo systemctl start postgresql
```

**Windows**:
下載安裝：https://www.postgresql.org/download/windows/

#### 2. 建立資料庫

```bash
# macOS/Linux
createdb aichatbot_admin

# 如果需要指定用戶
createdb -U postgres aichatbot_admin

# Windows (使用 psql)
psql -U postgres
CREATE DATABASE aichatbot_admin;
\q
```

---

### 🚀 快速啟動

```bash
# 1. 進入後端目錄
cd backend

# 2. 建立虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
nano .env  # 編輯填入資訊

# 需要修改的欄位：
# DATABASE_URL=postgresql+asyncpg://你的用戶名@localhost:5432/aichatbot_admin
# OPENAI_API_KEY=sk-你的API金鑰

# 5. 初始化資料庫
python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"

# 6. 啟動後端
uvicorn app.main:app --reload
```

---

## 🎯 完整工作流程

### 日常開發流程

```bash
# === 每次開始工作 ===

# 1. 啟動 Docker 服務（Docker 方式）
docker-compose up -d

# 或啟動 PostgreSQL（本機方式）
brew services start postgresql@16

# 2. 進入後端並啟動虛擬環境
cd backend
source venv/bin/activate

# 3. 啟動後端
uvicorn app.main:app --reload

# === 開發中 ===
# 後端會自動重載，修改程式碼後自動更新

# === 測試功能 ===
# 開啟新終端
python test_example.py
python test_knowledge.py

# === 結束工作 ===

# 停止後端：Ctrl+C

# 停止 Docker（Docker 方式）
docker-compose stop  # 保留資料
# 或
docker-compose down  # 移除容器但保留資料
```

---

## 📖 API 使用

### 開啟 API 文件

啟動後端後，訪問：http://localhost:8000/docs

### 常用 API 端點

```bash
# 健康檢查
curl http://localhost:8000/health

# 匯入 LINE 對話
curl -X POST "http://localhost:8000/api/conversations/import/line/text" \
  -F "file=@test_conversation.txt"

# 查詢對話列表
curl http://localhost:8000/api/conversations/

# 處理對話
curl -X POST "http://localhost:8000/api/processing/{conversation_id}/process-all"

# 生成知識庫
curl -X POST "http://localhost:8000/api/knowledge/generate" \
  -H "Content-Type: application/json" \
  -d '{"min_quality_score": 7}'

# 查看統計
curl http://localhost:8000/api/conversations/stats/summary
```

---

## 💰 成本優化建議

### 開發階段（超省方案）

編輯 `backend/.env`：
```env
# 使用 GPT-3.5 Turbo（成本降低 10 倍）
CHAT_MODEL=gpt-3.5-turbo

# 使用較小的嵌入模型
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

**成本對比**：
| 模型組合 | 處理 100 筆對話 | 處理 1000 筆對話 |
|---------|----------------|-----------------|
| GPT-4 + large | ~$5 | ~$50 |
| GPT-3.5 + small | ~$0.5 | ~$5 |

---

## 🔄 下一步

完成啟動測試後：

### ✅ 已完成
1. 後台管理系統
2. LINE 對話匯入
3. AI 自動處理
4. Markdown 知識庫生成

### 📝 待實作
1. **向量化服務** - 將 MD 轉為向量
2. **RAG 查詢系統** - AI 問答功能
3. **React 前端**（選用）- 視覺化管理介面

查看詳細計畫：[NEXT_STEPS.md](NEXT_STEPS.md)

---

## 📚 相關文件

- **API 使用文件**：[docs/API_USAGE.md](docs/API_USAGE.md)
- **Markdown 生成指南**：[docs/MARKDOWN_GUIDE.md](docs/MARKDOWN_GUIDE.md)
- **專案技術文件**：[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- **下一步規劃**：[NEXT_STEPS.md](NEXT_STEPS.md)

---

## ❓ 常見問題

### Q1: 需要一直開著 Docker 嗎？

**A**: 只有在開發時需要。不用時可以停止：
```bash
docker-compose stop  # 停止但保留資料
```

### Q2: 資料會遺失嗎？

**A**: 不會！資料儲存在 Docker Volume 中，即使停止容器也會保留。
只有執行 `docker-compose down -v` 才會刪除資料。

### Q3: 可以同時用 Docker 和本機的 PostgreSQL 嗎？

**A**: 可以，但建議只用一種，避免端口衝突。

### Q4: OpenAI API 要錢嗎？

**A**: 是的，但有免費額度。新註冊用戶通常有 $5 USD 免費額度。
使用 GPT-3.5-turbo 處理 1000 筆對話約 $5。

### Q5: 如何備份資料？

**A**:
```bash
# Docker 方式
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup.sql

# 還原
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup.sql
```

---

## 🎉 恭喜！

如果你完成了測試，代表系統運作正常！

**接下來你可以：**

1. 📝 匯入你的真實 LINE 對話
2. 🔍 調整 AI Prompt 以符合你的需求
3. 🤖 實作向量化和 RAG 系統
4. 🎨 建立前端管理介面

---

## 📞 需要幫助？

如果遇到問題：

1. 檢查服務狀態：`docker-compose ps`
2. 查看日誌：`docker-compose logs`
3. 查看文件：[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
4. 重新初始化：`docker-compose down -v && docker-compose up -d`

---

**準備好了嗎？開始吧！** 🚀

```bash
# Docker 方式
docker-compose up -d

# 本機方式
brew services start postgresql@16
```

然後按照上面的步驟操作！
