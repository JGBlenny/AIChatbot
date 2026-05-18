# 🚀 快速開始指南

本指南將幫助你快速啟動 AIChatbot 知識庫管理系統。

---

## 📋 前置需求

- Docker & Docker Compose
- OpenAI API Key
- (可選) Node.js 18+ & Python 3.9+ (本地開發)

---

## 🎯 快速啟動（Docker）

### 1. 複製專案

```bash
git clone <your-repo>
cd AIChatbot
```

### 2. 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env，填入你的 OpenAI API Key
nano .env
```

**修改 `.env` 檔案：**
```env
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

### 3. 啟動所有服務

```bash
# 啟動所有服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f
```

### 4. 驗證服務

等待所有服務啟動（約 30-60 秒），然後檢查：

```bash
# 檢查 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT * FROM pg_extension WHERE extname='vector';"

# 應該看到 vector 擴充
```

---

## 🌐 存取服務

| 服務 | URL | 說明 |
|------|-----|------|
| 知識庫管理後台（開發） | http://localhost:8087 | Web 介面管理知識（熱重載） |
| 知識庫管理後台（正式） | http://localhost:8081 | 靜態檔案服務 |
| 知識管理 API | http://localhost:8000/docs | FastAPI 文件 |
| Embedding API | http://localhost:5001/docs | 向量生成 API |
| **RAG Orchestrator** ⭐ | http://localhost:8100/docs | 智能問答 API |
| pgAdmin | http://localhost:5050 | 資料庫管理工具 |
| PostgreSQL | localhost:5432 | 資料庫 |
| Redis | localhost:6381 | 快取 |

**預設帳號密碼：**
- pgAdmin: `admin@aichatbot.com` / `admin`
- PostgreSQL: `aichatbot` / `aichatbot_password`

---

## 📝 使用流程

### 1. 處理 LINE 對話記錄（首次使用）

```bash
# 確保你有 LINE 對話 txt 檔案在 data/ 目錄
ls data/[LINE]*.txt

# 執行對話分析腳本
OPENAI_API_KEY="your-key" python3 scripts/process_line_chats.py

# 結果會儲存在 data/客服QA整理_測試結果.xlsx
```

### 2. 開啟知識庫管理後台

```bash
# 瀏覽器開啟（開發模式）
open http://localhost:8087
```

### 3. 管理知識

**瀏覽知識列表：**
- 可搜尋、篩選分類
- 查看所有已建立的知識

**新增知識：**
1. 點擊「➕ 新增知識」
2. 填寫標題、分類、對象
3. 使用 Markdown 編輯內容
4. 點擊「💾 儲存並更新向量」
5. 系統自動生成向量並儲存

**編輯知識：**
1. 點擊「✏️ 編輯」
2. 修改內容
3. 儲存時會自動重新生成向量

**刪除知識：**
- 點擊「🗑️」按鈕
- 確認刪除

### 4. 測試 RAG 智能問答 ⭐ (含 Phase 3 LLM 優化)

**健康檢查：**
```bash
curl http://localhost:8100/api/v1/health

# 應該看到 Phase 3 服務
# "llm_answer_optimizer": "ready (Phase 3)"
```

**發送問題測試（多業者 + 自動 LLM 優化）：**
```bash
# 測試知識查詢 - 答案會經過 GPT-4o-mini 優化
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租要怎麼辦理？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user"
  }' | python3 -m json.tool

# 你會看到：
# - answer: 自然流暢的對話式回答（不是原始知識庫文字）
# - confidence_score: 信心度評分
# - requires_human: 是否需要人工處理
# - unclear_question_id: 中/低信心度問題的記錄 ID
```

**Phase 3 LLM 優化特色**:
- ✨ 自動將知識庫內容轉換成自然對話
- 🎯 根據信心度自動決定是否優化（高/中信心度）
- 💰 Token 追蹤與成本控制（每次最多 800 tokens）
- 🔄 API 失敗時自動降級使用原始答案

**查看未釐清問題：**
```bash
# 取得待處理問題
curl http://localhost:8100/api/v1/unclear-questions?status=pending

# 取得統計資訊
curl http://localhost:8100/api/v1/unclear-questions-stats
```

**開啟 API 文件：**
```bash
open http://localhost:8100/docs
```

---

## 🛠️ 本地開發

### 後端 API

```bash
cd knowledge-admin/backend

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=aichatbot_admin
export DB_USER=aichatbot
export DB_PASSWORD=aichatbot_password
export EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings

# 啟動
python app.py

# API 文件：http://localhost:8000/docs
```

### 前端

```bash
cd knowledge-admin/frontend

# 安裝依賴
npm install

# 開發模式
npm run dev

# 開啟：http://localhost:8087
```

### RAG Orchestrator

```bash
cd rag-orchestrator

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
export OPENAI_API_KEY=your-key-here
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=aichatbot_admin
export DB_USER=aichatbot
export DB_PASSWORD=aichatbot_password
export EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings

# 啟動
python app.py

# API 文件：http://localhost:8100/docs
```

---

## 🔧 常用指令

### Docker Compose

```bash
# 啟動所有服務
docker-compose up -d

# 啟動特定服務
docker-compose up -d postgres redis

# 停止所有服務
docker-compose stop

# 停止並移除容器
docker-compose down

# 停止並移除容器 + 資料卷（會刪除資料！）
docker-compose down -v

# 重新建置並啟動
docker-compose up -d --build

# 查看日誌
docker-compose logs -f
docker-compose logs -f knowledge-admin-api
```

### 資料庫操作

```bash
# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 在 psql 中：
\dt                          # 列出所有表
\d knowledge_base            # 查看表結構
SELECT COUNT(*) FROM knowledge_base;  # 統計知識數量

# 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup.sql

# 還原資料庫
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup.sql
```

---

## 🐛 故障排除

### 問題 1：容器無法啟動

```bash
# 查看容器狀態
docker-compose ps

# 查看日誌找出錯誤
docker-compose logs <service-name>

# 重新建置
docker-compose up -d --build
```

### 問題 2：API 連線失敗

**檢查環境變數：**
```bash
# 確認 .env 檔案存在且正確
cat .env

# 重新啟動服務
docker-compose restart embedding-api knowledge-admin-api
```

### 問題 3：PostgreSQL 初始化失敗

```bash
# 完全重置資料庫
docker-compose down -v
docker-compose up -d postgres

# 等待初始化完成
docker-compose logs -f postgres
```

### 問題 4：向量生成失敗

**檢查 OpenAI API Key：**
```bash
# 測試 API Key
curl -X POST http://localhost:5001/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"text": "測試"}'

# 如果失敗，檢查 .env 中的 OPENAI_API_KEY
```

---

## 📊 監控與維護

### 檢查服務健康狀態

```bash
# 健康檢查
curl http://localhost:8000/api/health
curl http://localhost:5001/api/v1/health

# 統計資訊
curl http://localhost:8000/api/stats
```

### 查看系統資源使用

```bash
# Docker 資源使用
docker stats

# 磁碟使用
docker system df
```

---

## 🔄 更新與升級

### 更新程式碼

```bash
# 拉取最新程式碼
git pull

# 重新建置並啟動
docker-compose up -d --build
```

### 資料庫遷移

```bash
# 備份舊資料
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d).sql

# 更新後檢查
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin
```

---

## 📚 下一步

- [系統架構文件](../../architecture/SYSTEM_ARCHITECTURE.md)
- [RAG 系統實作計畫](../../archive/implementation/RAG_IMPLEMENTATION_PLAN.md)
- [RAG Orchestrator 使用說明](./rag-orchestrator/README.md) ⭐
- [pgvector 設定說明](../deployment/PGVECTOR_SETUP.md)
- [知識庫管理說明](./knowledge-admin/README.md)

---

## 🆘 需要幫助？

- 查看架構文件了解系統設計
- 檢查 Docker 日誌找出問題
- 確認所有環境變數正確設定
- 確保 OpenAI API Key 有效

---

**維護者：** Claude Code
**最後更新：** 2025-10-10 (Phase 3 LLM 優化)
