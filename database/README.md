# PostgreSQL + pgvector 設定說明

## 📦 已完成的調整

### 1. Docker Compose 調整
- ✅ 將 PostgreSQL 映像檔改為 `pgvector/pgvector:pg16`
- ✅ 新增初始化腳本掛載點

### 2. 資料庫初始化腳本
位於 `database/init/` 目錄：

- **01-enable-pgvector.sql** - 啟用 pgvector 擴充
- **02-create-knowledge-base.sql** - 建立知識庫表結構

## 🗄️ 資料庫結構

### knowledge_base 表
```sql
- id (主鍵)
- title (標題)
- category (分類：合約問題、物件問題、帳務問題等)
- question_summary (問題摘要)
- answer (標準回覆)
- audience (對象：房東、租客、管理師)
- keywords (關鍵字陣列)
- source_file (來源檔案)
- source_date (日期)
- embedding (向量，1536 維)
- created_at, updated_at
```

### chat_history 表
```sql
- id (主鍵)
- user_id (使用者 ID)
- user_role (角色)
- question (問題)
- answer (回答)
- related_kb_ids (相關知識庫 ID)
- feedback_score (評分 1-5)
- feedback_comment (評論)
- created_at
```

## 🚀 使用方式

### 1. 啟動資料庫
```bash
# 如果是第一次啟動或重新建立
docker-compose down -v  # 清除舊資料
docker-compose up -d postgres

# 檢查啟動狀態
docker-compose logs postgres
```

### 2. 連線到資料庫
```bash
# 方法 1: 使用 Docker exec
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 方法 2: 使用本地 psql
psql -h localhost -U aichatbot -d aichatbot_admin
# 密碼: aichatbot_password

# 方法 3: 使用 pgAdmin
# 瀏覽器開啟 http://localhost:5050
# Email: admin@aichatbot.com
# Password: admin
```

### 3. 驗證 pgvector 安裝
```sql
-- 檢查擴充是否啟用
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 檢查知識庫表是否建立
\dt

-- 查看測試資料
SELECT * FROM knowledge_base;
```

## 📊 資料庫連線資訊

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

## 🔍 向量搜尋範例

### 插入向量資料
```sql
INSERT INTO knowledge_base (title, answer, embedding)
VALUES (
    '租金逾期處理',
    '租金逾期時，系統會自動發送提醒...',
    '[0.1, 0.2, 0.3, ...]'::vector  -- 1536 維向量
);
```

### 相似度搜尋
```sql
-- 找出最相似的 5 筆知識
SELECT
    title,
    answer,
    embedding <=> '[查詢向量]'::vector AS distance
FROM knowledge_base
ORDER BY distance
LIMIT 5;
```

## 🛠️ 常用指令

### Docker 管理
```bash
# 啟動
docker-compose up -d postgres

# 停止
docker-compose stop postgres

# 重啟
docker-compose restart postgres

# 查看日誌
docker-compose logs -f postgres

# 完全移除（包含資料）
docker-compose down -v
```

### 資料庫備份與還原
```bash
# 備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup.sql

# 還原
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup.sql
```

## 📝 索引說明

### 向量索引 (IVFFlat)
```sql
CREATE INDEX idx_kb_embedding ON knowledge_base
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

- **lists**: 資料分群數量，建議設為 `sqrt(總資料筆數)`
- **vector_cosine_ops**: 使用餘弦距離計算相似度

### 效能建議
- < 1,000 筆資料: lists = 30-50
- 1,000-10,000 筆: lists = 100
- 10,000-100,000 筆: lists = 300-500

## 🔗 下一步

1. 執行 Excel → PostgreSQL 轉換腳本
2. 建立 RAG 查詢功能
3. 整合到 ChatBot API
