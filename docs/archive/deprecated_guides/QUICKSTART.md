# 快速開始指南

## 準備工作

### 1. 安裝 Python 3.11+

```bash
python --version  # 確認版本 >= 3.11
```

### 2. 安裝 PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**建立資料庫:**
```bash
createdb aichatbot_admin
```

### 3. 安裝 Redis (選用，批次處理需要)

```bash
brew install redis
brew services start redis
```

---

## 後端設定

### 1. 進入後端目錄

```bash
cd backend
```

### 2. 建立虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env` 檔案，填入必要資訊：

```env
# 資料庫（修改為你的設定）
DATABASE_URL=postgresql+asyncpg://YOUR_USER@localhost:5432/aichatbot_admin
SYNC_DATABASE_URL=postgresql://YOUR_USER@localhost:5432/aichatbot_admin

# OpenAI API Key（必填）
OPENAI_API_KEY=sk-your-api-key-here

# 安全密鑰（隨機生成）
SECRET_KEY=your-random-secret-key-change-me

# 其他使用預設值即可
```

### 5. 初始化資料庫

```bash
# 建立資料表
python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"
```

### 6. 啟動後端

```bash
# 開發模式（自動重載）
uvicorn app.main:app --reload

# 或直接執行
python -m app.main
```

後端啟動後訪問：
- API 文件：http://localhost:8000/docs
- API：http://localhost:8000

---

## 測試 API

### 1. 匯入 LINE 對話（文字格式）

建立測試檔案 `test_conversation.txt`：

```
2024/01/15 14:30 客戶: 你好，請問如何使用這個功能？
2024/01/15 14:31 客服: 您好！使用方式很簡單
2024/01/15 14:32 客戶: 好的，謝謝
```

使用 cURL 測試：

```bash
curl -X POST "http://localhost:8000/api/conversations/import/line/text" \
  -F "file=@test_conversation.txt"
```

### 2. 查看對話列表

```bash
curl http://localhost:8000/api/conversations/
```

### 3. AI 處理對話

取得對話 ID 後：

```bash
# 完整處理（品質評估 + 分類 + 清理 + 提取）
curl -X POST "http://localhost:8000/api/processing/{conversation_id}/process-all"
```

---

## 成本優化方案（適合小資料量）

### 選項 1：使用免費向量資料庫

**pgvector (推薦)**：使用現有 PostgreSQL，零額外成本

1. 安裝 pgvector 擴展：
```bash
# macOS
brew install pgvector

# 在 PostgreSQL 中啟用
psql aichatbot_admin
CREATE EXTENSION vector;
```

2. 修改 `requirements.txt`：
```
# 加入
pgvector==0.2.4
```

### 選項 2：降低 AI API 成本

**使用較便宜的模型**：

編輯 `backend/.env`：

```env
# 使用 GPT-3.5-Turbo（成本降低 10 倍）
CHAT_MODEL=gpt-3.5-turbo

# 使用較小的嵌入模型
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

**成本對比（處理 1,000 筆對話）**：

| 方案 | 模型 | 月費 |
|------|------|------|
| 標準 | GPT-4 Turbo | ~$450 |
| 經濟 | GPT-3.5 Turbo | ~$45 |
| 超省 | 僅必要功能 | ~$10 |

**超省方案設定**：只做分類和清理，不做品質評估

---

## 常見問題

### Q1: 資料庫連接失敗

確認 PostgreSQL 是否啟動：
```bash
brew services list
```

確認資料庫存在：
```bash
psql -l | grep aichatbot
```

### Q2: OpenAI API 錯誤

檢查 API Key 是否正確：
```bash
echo $OPENAI_API_KEY
```

測試 API Key：
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Q3: 模組找不到

確認虛擬環境已啟動：
```bash
which python  # 應該指向 venv/bin/python
```

重新安裝依賴：
```bash
pip install -r requirements.txt --force-reinstall
```

---

## 下一步

1. ✅ 後端 API 已完成，可以開始測試匯入對話
2. 📱 建立前端管理介面（React）
3. 📝 實作 Markdown 知識庫生成
4. 🔍 整合 RAG 檢索系統

查看完整文件：[README.md](../README.md)
