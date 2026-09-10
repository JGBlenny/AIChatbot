> 📦 **2026-09-10 歸檔（文件整理）：原位置 docs/guides/deployment/PGVECTOR_SETUP.md**——原因：自標歷史快照，已過時。

> ⚠️ **歷史快照（早期設定紀錄），內容已過時**：文中 `database/init/` 已於 2026-07-11 除役（現為 `init-legacy/`），新環境建置走 dump 還原（docs/deployment-runbook.md 附錄 A）。pgvector 映像與索引資訊僅供考據。

# ✅ pgvector + PostgreSQL 設定完成

## 📋 已完成的工作

### 1. Docker Compose 調整
- ✅ 映像檔改為 `pgvector/pgvector:pg16`
- ✅ 新增初始化腳本掛載點
- ✅ 保留原有設定（pgAdmin、Redis）

### 2. 初始化腳本
已建立在 `database/init/` 目錄：

```
database/init/
├── 01-enable-pgvector.sql      # 啟用 pgvector 擴充
└── 02-create-knowledge-base.sql # 建立知識庫表結構
```

### 3. 資料庫結構
- ✅ **knowledge_base** 表（知識庫 + 向量）
- ✅ **chat_history** 表（對話歷史）
- ✅ 向量索引（IVFFlat）
- ✅ 關鍵字索引（GIN）

---

## 🚀 啟動步驟

### 第一次啟動

```bash
# 1. 啟動 PostgreSQL（會自動下載映像檔 ~110MB）
docker-compose up -d postgres

# 2. 等待容器啟動（約 10-20 秒）
docker-compose logs -f postgres

# 看到以下訊息代表成功：
# ✅ database system is ready to accept connections
```

### 驗證 pgvector 安裝

```bash
# 連線到資料庫
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 在 psql 中執行：
SELECT * FROM pg_extension WHERE extname = 'vector';
# 應該看到 vector 擴充

\dt
# 應該看到 knowledge_base 和 chat_history 表

SELECT * FROM knowledge_base;
# 應該看到一筆測試資料
```

---

## 📊 資料庫連線資訊

**本地連線：**
```
主機: localhost
埠號: 5432
資料庫: aichatbot_admin
使用者: aichatbot
密碼: aichatbot_password
```

**Python 連線範例：**
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="aichatbot_admin",
    user="aichatbot",
    password="aichatbot_password"
)
```

**pgAdmin (GUI):**
```
URL: http://localhost:5050
Email: admin@aichatbot.com
Password: admin
```

---

## 🔍 測試向量搜尋

### Python 測試腳本

```python
from openai import OpenAI
import psycopg2
import numpy as np

# 1. 連線資料庫
conn = psycopg2.connect(
    host="localhost",
    database="aichatbot_admin",
    user="aichatbot",
    password="aichatbot_password"
)
cur = conn.cursor()

# 2. 建立 OpenAI 客戶端
client = OpenAI(api_key="你的API key")

# 3. 插入測試資料
text = "租金逾期時，系統會自動發送提醒給租客"
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
embedding = response.data[0].embedding

cur.execute("""
    INSERT INTO knowledge_base (title, answer, embedding, category, audience)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
""", (
    "租金逾期處理",
    text,
    embedding,
    "帳務問題",
    "管理師"
))
kb_id = cur.fetchone()[0]
conn.commit()
print(f"✅ 插入成功，ID: {kb_id}")

# 4. 測試向量搜尋
question = "房客沒繳錢怎麼辦？"
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=question
)
query_embedding = response.data[0].embedding

cur.execute("""
    SELECT
        id,
        title,
        answer,
        category,
        embedding <=> %s::vector AS distance
    FROM knowledge_base
    ORDER BY distance
    LIMIT 3
""", (query_embedding,))

print(f"\n查詢問題: {question}\n")
for row in cur.fetchall():
    id, title, answer, category, distance = row
    similarity = (1 - distance) * 100
    print(f"相似度: {similarity:.1f}%")
    print(f"標題: {title}")
    print(f"分類: {category}")
    print(f"答案: {answer[:50]}...")
    print()

cur.close()
conn.close()
```

---

## 📁 檔案結構

```
AIChatbot/
├── docker-compose.yml          # ✅ 已調整支援 pgvector
├── database/
│   ├── README.md              # 詳細說明文件
│   └── init/
│       ├── 01-enable-pgvector.sql      # ✅ 啟用擴充
│       └── 02-create-knowledge-base.sql # ✅ 建立表結構
├── scripts/
│   └── process_line_chats.py  # LINE 對話分析腳本
└── data/
    ├── 客服QA整理_測試結果.xlsx # 測試結果
    └── [LINE]*.txt            # 原始對話記錄
```

---

## 🎯 下一步

### 立即可做：

1. **啟動資料庫並驗證**
   ```bash
   docker-compose up -d postgres
   docker-compose logs -f postgres
   ```

2. **測試 pgvector 功能**
   ```bash
   docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin
   ```

### 後續開發：

3. **Excel → PostgreSQL 轉換**
   - 建立腳本讀取測試結果 Excel
   - 生成向量並存入資料庫

4. **RAG ChatBot**
   - 建立向量搜尋 API
   - 整合 OpenAI ChatCompletion
   - 建立前端界面

---

## ⚠️ 常見問題

### Q: 如何重新初始化資料庫？
```bash
docker-compose down -v  # 刪除 volume（資料會遺失）
docker-compose up -d postgres  # 重新啟動會執行初始化腳本
```

### Q: 如何備份資料？
```bash
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup.sql
```

### Q: 如何連線到資料庫？
```bash
# 方法 1: psql (需要安裝)
psql -h localhost -U aichatbot -d aichatbot_admin

# 方法 2: Docker exec
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 方法 3: pgAdmin (GUI)
# 瀏覽器開啟 http://localhost:5050
```

---

## 📞 技術支援

**Docker 映像檔來源：**
- https://hub.docker.com/r/pgvector/pgvector

**pgvector 文件：**
- https://github.com/pgvector/pgvector

**OpenAI Embeddings API：**
- https://platform.openai.com/docs/guides/embeddings
