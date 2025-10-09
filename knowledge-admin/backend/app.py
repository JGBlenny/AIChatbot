"""
知識庫管理 API
提供知識的 CRUD 操作，並自動處理向量更新
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import os
from datetime import datetime

app = FastAPI(
    title="知識庫管理 API",
    description="管理客服知識庫，自動處理向量生成與更新",
    version="1.0.0"
)

# CORS 設定（允許前端跨域請求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應改為具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境變數設定
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:5000/api/v1/embeddings")

# 資料庫連線
def get_db_connection():
    """建立資料庫連線"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

# ========== 資料模型 ==========

class KnowledgeBase(BaseModel):
    """知識庫資料模型"""
    id: Optional[int] = None
    title: str
    category: str
    audience: str
    content: str
    keywords: List[str] = []
    question_summary: Optional[str] = None
    source_file: Optional[str] = None

class KnowledgeUpdate(BaseModel):
    """知識更新模型"""
    title: str
    category: str
    audience: str
    content: str
    keywords: List[str] = []
    question_summary: Optional[str] = None

class KnowledgeResponse(BaseModel):
    """知識回應模型"""
    id: int
    title: str
    category: str
    audience: str
    content: str
    keywords: List[str]
    question_summary: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

# ========== API 端點 ==========

@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "name": "知識庫管理 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """健康檢查"""
    try:
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/knowledge", response_model=dict)
async def list_knowledge(
    category: Optional[str] = Query(None, description="篩選分類"),
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    limit: int = Query(50, ge=1, le=100, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    列出所有知識

    - **category**: 篩選特定分類
    - **search**: 搜尋標題或內容
    - **limit**: 每頁顯示筆數 (1-100)
    - **offset**: 分頁偏移量
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 建立查詢
        query = """
            SELECT id, title, category, audience, answer as content,
                   keywords, question_summary, created_at, updated_at
            FROM knowledge_base
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND category = %s"
            params.append(category)

        if search:
            query += " AND (title ILIKE %s OR answer ILIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

        query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        results = cur.fetchall()

        # 轉換日期格式
        items = []
        for row in results:
            item = dict(row)
            item['content'] = item.pop('content', '')
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            if item.get('updated_at'):
                item['updated_at'] = item['updated_at'].isoformat()
            items.append(item)

        # 取得總數
        count_query = "SELECT COUNT(*) as total FROM knowledge_base WHERE 1=1"
        count_params = []
        if category:
            count_query += " AND category = %s"
            count_params.append(category)
        if search:
            count_query += " AND (title ILIKE %s OR answer ILIKE %s)"
            count_params.extend([f"%{search}%", f"%{search}%"])

        cur.execute(count_query, count_params)
        total = cur.fetchone()['total']

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()

@app.get("/api/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(knowledge_id: int):
    """取得單一知識詳情"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, title, category, audience, answer as content,
                   keywords, question_summary, created_at, updated_at
            FROM knowledge_base
            WHERE id = %s
        """, (knowledge_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="知識不存在")

        result = dict(row)
        result['content'] = result.pop('content', '')
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()

        return result

    finally:
        cur.close()
        conn.close()

@app.put("/api/knowledge/{knowledge_id}")
async def update_knowledge(knowledge_id: int, data: KnowledgeUpdate):
    """
    更新知識（自動重新生成向量）

    流程：
    1. 驗證知識存在
    2. 呼叫 Embedding API 生成新向量
    3. 更新資料庫（包含新向量）
    4. 回傳結果
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. 檢查知識是否存在
        cur.execute("SELECT id FROM knowledge_base WHERE id = %s", (knowledge_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="知識不存在")

        # 2. 生成新向量
        try:
            embedding_response = requests.post(
                EMBEDDING_API_URL,
                json={"text": data.content},
                timeout=30
            )

            if embedding_response.status_code != 200:
                raise Exception(f"Embedding API 錯誤: {embedding_response.text}")

            new_embedding = embedding_response.json()['embedding']

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f"無法連線到 Embedding API: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"生成向量失敗: {str(e)}"
            )

        # 3. 更新資料庫
        cur.execute("""
            UPDATE knowledge_base
            SET
                title = %s,
                category = %s,
                audience = %s,
                answer = %s,
                keywords = %s,
                question_summary = %s,
                embedding = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, title, updated_at
        """, (
            data.title,
            data.category,
            data.audience,
            data.content,
            data.keywords,
            data.question_summary,
            new_embedding,
            knowledge_id
        ))

        updated = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "message": "知識已更新，向量已重新生成",
            "id": updated['id'],
            "title": updated['title'],
            "updated_at": updated['updated_at'].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.post("/api/knowledge")
async def create_knowledge(data: KnowledgeUpdate):
    """
    新增知識

    流程：
    1. 生成向量
    2. 插入資料庫
    3. 回傳新建資料
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. 生成向量
        try:
            embedding_response = requests.post(
                EMBEDDING_API_URL,
                json={"text": data.content},
                timeout=30
            )

            if embedding_response.status_code != 200:
                raise Exception(f"Embedding API 錯誤: {embedding_response.text}")

            embedding = embedding_response.json()['embedding']

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f"無法連線到 Embedding API: {str(e)}"
            )

        # 2. 插入資料庫
        cur.execute("""
            INSERT INTO knowledge_base
            (title, category, audience, answer, keywords, question_summary, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            data.title,
            data.category,
            data.audience,
            data.content,
            data.keywords,
            data.question_summary,
            embedding
        ))

        new_record = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "message": "知識已新增",
            "id": new_record['id'],
            "created_at": new_record['created_at'].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"新增失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.delete("/api/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: int):
    """刪除知識"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM knowledge_base WHERE id = %s RETURNING id",
            (knowledge_id,)
        )
        deleted = cur.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="知識不存在")

        conn.commit()

        return {
            "success": True,
            "message": "知識已刪除",
            "id": deleted['id']
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.get("/api/categories")
async def list_categories():
    """取得所有分類"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT category
            FROM knowledge_base
            WHERE category IS NOT NULL
            ORDER BY category
        """)

        categories = [row['category'] for row in cur.fetchall()]

        return {"categories": categories}

    finally:
        cur.close()
        conn.close()

@app.get("/api/stats")
async def get_stats():
    """取得統計資訊"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 總知識數
        cur.execute("SELECT COUNT(*) as total FROM knowledge_base")
        total = cur.fetchone()['total']

        # 各分類數量
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM knowledge_base
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        by_category = [dict(row) for row in cur.fetchall()]

        # 最近更新
        cur.execute("""
            SELECT id, title, updated_at
            FROM knowledge_base
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        recent_updates = []
        for row in cur.fetchall():
            item = dict(row)
            item['updated_at'] = item['updated_at'].isoformat()
            recent_updates.append(item)

        return {
            "total_knowledge": total,
            "by_category": by_category,
            "recent_updates": recent_updates
        }

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動知識庫管理 API...")
    print(f"📊 API 文件: http://localhost:8000/docs")
    print(f"💾 資料庫: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
