# 知識庫管理後台

Web 介面管理客服知識庫，支援線上編輯並自動更新向量。

## 功能

- 📋 列表檢視（搜尋、篩選、分頁）
- ✏️  Markdown 編輯器 + 即時預覽
- 💾 儲存時自動重新生成向量
- ➕ 新增知識
- 🗑️ 刪除知識
- 📊 統計資訊

## 技術棧

**後端：**
- FastAPI
- psycopg2 (PostgreSQL)
- requests (呼叫 Embedding API)

**前端：**
- Vue.js 3
- Axios
- marked (Markdown 渲染)

## 本地開發

### 後端

```bash
cd backend

# 安裝依賴
pip install -r requirements.txt

# 啟動（確保 PostgreSQL 和 Embedding API 已啟動）
python app.py

# API 文件：http://localhost:8000/docs
```

### 前端

```bash
cd frontend

# 安裝依賴
npm install

# 開發模式
npm run dev

# 瀏覽器開啟：http://localhost:8080
```

## Docker 部署

```bash
# 從專案根目錄
docker-compose up -d knowledge-admin-api knowledge-admin-web

# 存取：http://localhost:8080
```

## 環境變數

```env
# 後端
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
EMBEDDING_API_URL=http://localhost:5000/api/v1/embeddings
```

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/knowledge` | GET | 列出所有知識 |
| `/api/knowledge/{id}` | GET | 取得單一知識 |
| `/api/knowledge` | POST | 新增知識 |
| `/api/knowledge/{id}` | PUT | 更新知識（自動重新生成向量） |
| `/api/knowledge/{id}` | DELETE | 刪除知識 |
| `/api/categories` | GET | 取得所有分類 |
| `/api/stats` | GET | 統計資訊 |

## 使用流程

1. **瀏覽知識列表**
   - 可搜尋、篩選分類

2. **編輯知識**
   - 點擊「編輯」按鈕
   - 修改內容（支援 Markdown）
   - 即時預覽效果

3. **儲存**
   - 點擊「儲存並更新向量」
   - 系統自動呼叫 Embedding API 生成新向量
   - 更新到資料庫

4. **完成**
   - RAG 系統立即使用新版本

## 架構

```
知識管理後台
    ↓
後端 API (FastAPI)
    ↓
┌─────────┴─────────┐
↓                   ↓
Embedding API    PostgreSQL
生成向量           儲存資料
```

## 注意事項

- 編輯知識時會重新生成向量，需確保 Embedding API 正常運作
- 刪除操作無法復原，請謹慎使用
- 支援 Markdown 格式，可使用標題、列表、程式碼等

## 相關文件

- [系統架構文件](../../docs/architecture/SYSTEM_ARCHITECTURE.md)
- [API 文件](http://localhost:8000/docs)
