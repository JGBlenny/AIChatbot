# 下一步行動指南

## ✅ 已完成

### 後端系統 (FastAPI + Python)

1. **專案架構** ✅
   - FastAPI 應用設定
   - PostgreSQL 資料庫模型
   - Pydantic Schemas
   - 環境配置管理

2. **核心功能** ✅
   - LINE 對話解析器（支援多種文字格式）
   - 對話匯入 API（JSON 和文字檔案）
   - 對話管理 API（CRUD、篩選、分頁、統計）
   - OpenAI API 整合服務
   - AI 處理 API（品質評估、分類、清理、提取）
   - 批次處理和背景任務
   - 審核功能（批准/拒絕）

3. **文件** ✅
   - README.md（專案概覽）
   - QUICKSTART.md（快速開始指南）
   - API_USAGE.md（完整 API 文件）
   - 測試範例腳本

---

## 🚀 立即開始

### 1. 設定後端環境（10 分鐘）

```bash
# 1. 建立資料庫
createdb aichatbot_admin

# 2. 進入後端目錄
cd backend

# 3. 建立虛擬環境
python -m venv venv
source venv/bin/activate

# 4. 安裝依賴
pip install -r requirements.txt

# 5. 設定環境變數
cp .env.example .env
# 編輯 .env，填入 OpenAI API Key 和資料庫連接

# 6. 初始化資料庫
python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"

# 7. 啟動後端
uvicorn app.main:app --reload
```

### 2. 測試 API（5 分鐘）

```bash
# 開啟另一個終端機

# 測試 1: 匯入測試對話
curl -X POST "http://localhost:8000/api/conversations/import/line/text" \
  -F "file=@test_conversation.txt"

# 測試 2: 執行完整測試腳本
python test_example.py
```

### 3. 查看 API 文件

開啟瀏覽器訪問：http://localhost:8000/docs

---

## 📋 待實作功能

### Phase 1: 基礎完善（建議優先）

#### 1.1 Markdown 知識庫生成器
**目的**: 將已批准的對話匯出為 MD 檔案

**位置**: `backend/app/services/markdown_generator.py`

**功能**:
- 按分類生成 MD 檔案
- Q&A 格式化
- 元數據標記
- 版本管理

**API 端點**:
```python
POST /api/knowledge/generate
POST /api/knowledge/export/{conversation_id}
GET /api/knowledge/files
```

#### 1.2 向量嵌入與 pgvector 整合
**目的**: 將 MD 內容向量化，支援 RAG 檢索

**功能**:
- 語義分塊（Semantic Chunking）
- 生成向量嵌入
- 儲存到 pgvector
- 相似度搜尋

**API 端點**:
```python
POST /api/vectors/embed/{file_id}
POST /api/vectors/search
```

#### 1.3 RAG 查詢介面
**目的**: 測試知識庫檢索效果

**功能**:
- 自然語言查詢
- 混合搜尋（語義 + 關鍵字）
- 結果排序和過濾

**API 端點**:
```python
POST /api/rag/query
GET /api/rag/test
```

---

### Phase 2: 前端管理介面（React）

#### 2.1 基礎設定
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

**技術棧**:
- React 18 + TypeScript
- Vite
- Ant Design 或 Material-UI
- React Query
- React Router

#### 2.2 主要頁面

1. **對話列表頁** (`/conversations`)
   - 表格顯示所有對話
   - 篩選（狀態、分類、來源）
   - 搜尋
   - 批次操作

2. **對話詳情頁** (`/conversations/:id`)
   - 原始對話顯示
   - AI 處理結果
   - 編輯功能
   - 審核操作

3. **匯入頁** (`/import`)
   - 上傳 LINE 文字檔
   - JSON 格式匯入
   - 批次匯入

4. **知識庫管理** (`/knowledge`)
   - MD 檔案列表
   - 預覽和編輯
   - 生成和匯出

5. **統計儀表板** (`/dashboard`)
   - 對話統計圖表
   - 品質分析
   - 分類分布

---

### Phase 3: 進階功能

#### 3.1 Celery 任務隊列
**目的**: 處理大量對話時不阻塞 API

**設定**:
```bash
# 安裝 Celery
pip install celery redis

# 啟動 Worker
celery -A app.tasks worker --loglevel=info
```

#### 3.2 WebSocket 即時更新
**目的**: 批次處理時即時顯示進度

#### 3.3 用戶認證與權限
**目的**: 多用戶管理

- JWT 認證
- 角色權限（Admin, Editor, Viewer）

#### 3.4 資料匯出
- Excel 報表
- JSON 備份
- MD 壓縮包下載

---

## 💰 成本優化建議

### 方案 A: 極省方案（適合測試/小資料量）

**配置**:
```env
CHAT_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
```

**成本**: ~$5-10/月（處理 500-1000 筆對話）

**向量資料庫**: pgvector（免費）

---

### 方案 B: 平衡方案（推薦）

**配置**:
```env
CHAT_MODEL=gpt-4o-mini  # 比 GPT-4 便宜 60%
EMBEDDING_MODEL=text-embedding-3-small
```

**成本**: ~$20-30/月（處理 2000-3000 筆對話）

**向量資料庫**: pgvector 或 Pinecone Starter

---

### 方案 C: 高品質方案

**配置**:
```env
CHAT_MODEL=gpt-4-turbo
EMBEDDING_MODEL=text-embedding-3-large
```

**成本**: ~$100-150/月（處理 5000+ 筆對話）

**向量資料庫**: Pinecone Standard

---

## 🎯 建議實作順序

### 第 1 週: 測試和優化後端
- [x] 完成後端設定
- [ ] 測試所有 API
- [ ] 用真實 LINE 對話測試
- [ ] 調整 AI Prompt 提升準確性

### 第 2 週: MD 生成和向量化
- [ ] 實作 MD 生成器
- [ ] 設定 pgvector
- [ ] 實作向量嵌入
- [ ] 測試 RAG 檢索

### 第 3-4 週: 前端開發
- [ ] React 專案設定
- [ ] 對話列表頁
- [ ] 對話詳情和編輯
- [ ] 匯入功能
- [ ] 統計儀表板

### 第 5 週: 整合和測試
- [ ] 前後端整合
- [ ] 完整工作流程測試
- [ ] 效能優化
- [ ] 部署準備

---

## 📚 參考資源

### FastAPI
- 官方文件: https://fastapi.tiangolo.com/
- 非同步資料庫: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

### LangChain
- Python 文件: https://python.langchain.com/docs/get_started/introduction
- RAG 教學: https://python.langchain.com/docs/use_cases/question_answering/

### pgvector
- GitHub: https://github.com/pgvector/pgvector
- 教學: https://github.com/pgvector/pgvector-python

### React
- Vite: https://vitejs.dev/
- React Query: https://tanstack.com/query/latest
- Ant Design: https://ant.design/

---

## 💡 提示

1. **先測試後端**：確保 API 運作正常再開始做前端
2. **使用經濟方案**：開發階段使用 GPT-3.5-Turbo 節省成本
3. **小批次測試**：先用 10-20 筆對話測試 AI 處理效果
4. **調整 Prompt**：根據你的實際對話內容調整 AI Prompt
5. **備份資料**：定期備份資料庫

---

## ❓ 需要幫助？

如果遇到問題，請確認：
1. Python 版本 >= 3.11
2. PostgreSQL 已啟動
3. OpenAI API Key 正確
4. 環境變數設定正確

查看詳細文件：
- [快速開始](docs/QUICKSTART.md)
- [API 使用說明](docs/API_USAGE.md)

---

**準備好了嗎？開始啟動後端吧！** 🚀

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```
