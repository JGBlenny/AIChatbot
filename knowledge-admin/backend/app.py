"""
知識庫管理 API
提供知識的 CRUD 操作，並自動處理向量更新
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import requests
import os
import pandas as pd
from datetime import datetime

# 導入測試情境路由
from routes_test_scenarios import router as test_scenarios_router
# 導入認證路由和認證依賴
from routes_auth import router as auth_router, get_current_user
# 導入管理員管理路由
from routes_admins import router as admins_router
# 導入角色管理路由
from routes_roles import router as roles_router

app = FastAPI(
    title="知識庫管理 API",
    description="管理客服知識庫，自動處理向量生成與更新",
    version="1.0.0"
)

# 包含測試情境路由
app.include_router(test_scenarios_router)
# 包含認證路由
app.include_router(auth_router)
# 包含管理員管理路由
app.include_router(admins_router)
# 包含角色管理路由
app.include_router(roles_router)

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
    question_summary: str
    content: str
    keywords: List[str] = []
    source_file: Optional[str] = None

class IntentMapping(BaseModel):
    """意圖關聯模型"""
    intent_id: int
    intent_type: str = 'secondary'  # 'primary' 或 'secondary'
    confidence: float = 1.0

class KnowledgeUpdate(BaseModel):
    """知識更新模型"""
    question_summary: str
    content: str
    keywords: List[str] = []
    intent_mappings: Optional[List[IntentMapping]] = []  # 多意圖支援
    business_types: Optional[List[str]] = None  # 業態類型（可選，NULL=通用）
    target_user: Optional[List[str]] = None  # 目標用戶（可選，NULL=通用）tenant/landlord/property_manager/system_admin
    priority: Optional[int] = 0  # 優先級加成（0=未啟用，1=已啟用）
    vendor_ids: Optional[List[int]] = None  # 業者 ID 列表（可選，NULL=全域知識）
    form_id: Optional[str] = None  # 表單關聯 ID（可選）
    action_type: Optional[str] = 'direct_answer'  # 動作類型：'direct_answer', 'form_fill', 'api_call', 'form_then_api'
    api_config: Optional[dict] = None  # API 配置（JSONB）：{ endpoint, params, combine_with_knowledge }
    # 🆕 表單觸發模式（統一 SOP 邏輯）
    trigger_mode: Optional[str] = None  # 表單觸發模式：'manual', 'immediate'（null 表示不需要觸發）
    immediate_prompt: Optional[str] = None  # immediate 模式的確認提示詞

class KnowledgeResponse(BaseModel):
    """知識回應模型"""
    id: int
    question_summary: str
    content: str
    keywords: List[str]
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
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    business_types: Optional[str] = Query(None, description="業態類型過濾（逗號分隔）"),
    universal_only: Optional[str] = Query(None, description="只顯示通用知識"),
    limit: int = Query(50, ge=1, le=100, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user)
):
    """
    列出所有知識

    - **search**: 搜尋標題或內容
    - **business_types**: 業態類型過濾（如：full_service,property_management）
    - **universal_only**: 只顯示通用知識（true/false）
    - **limit**: 每頁顯示筆數 (1-100)
    - **offset**: 分頁偏移量
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 建立查詢（加入意圖資訊 - 使用 knowledge_intent_mapping，並加入業者資訊、API 配置）
        query = """
            SELECT DISTINCT
                kb.id, kb.question_summary, kb.answer as content,
                kb.keywords, kb.business_types, kb.target_user, kb.priority, kb.created_at, kb.updated_at,
                (kb.embedding IS NOT NULL) as has_embedding,
                kb.vendor_ids,
                kb.form_id,
                kb.action_type,
                kb.api_config,
                v.name as vendor_name
            FROM knowledge_base kb
            LEFT JOIN vendors v ON v.id = ANY(kb.vendor_ids)
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (kb.question_summary ILIKE %s OR kb.answer ILIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

        # 業態類型過濾
        if business_types:
            type_list = [t.strip() for t in business_types.split(',')]
            # 使用 @> 運算符檢查陣列包含關係
            query += " AND kb.business_types && %s"
            params.append(type_list)

        # 只顯示通用知識（business_types 為 NULL 或空陣列）
        if universal_only and universal_only.lower() == 'true':
            query += " AND (kb.business_types IS NULL OR kb.business_types = '{}')"

        query += " ORDER BY kb.updated_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        results = cur.fetchall()

        # 轉換日期格式並加載意圖關聯
        items = []
        for row in results:
            item = dict(row)
            item['content'] = item.pop('content', '')
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            if item.get('updated_at'):
                item['updated_at'] = item['updated_at'].isoformat()

            # 獲取關聯的意圖
            cur.execute("""
                SELECT
                    kim.intent_id,
                    i.name as intent_name,
                    kim.intent_type,
                    kim.confidence
                FROM knowledge_intent_mapping kim
                JOIN intents i ON kim.intent_id = i.id
                WHERE kim.knowledge_id = %s
                ORDER BY
                    CASE kim.intent_type
                        WHEN 'primary' THEN 1
                        WHEN 'secondary' THEN 2
                    END,
                    kim.confidence DESC
            """, (item['id'],))

            intents = [dict(intent_row) for intent_row in cur.fetchall()]
            item['intent_mappings'] = intents

            items.append(item)

        # 取得總數
        count_query = "SELECT COUNT(*) as total FROM knowledge_base WHERE 1=1"
        count_params = []
        if search:
            count_query += " AND (question_summary ILIKE %s OR answer ILIKE %s)"
            count_params.extend([f"%{search}%", f"%{search}%"])

        # 業態類型過濾（總數查詢也要包含）
        if business_types:
            type_list = [t.strip() for t in business_types.split(',')]
            count_query += " AND business_types && %s"
            count_params.append(type_list)

        # 只顯示通用知識
        if universal_only and universal_only.lower() == 'true':
            count_query += " AND (business_types IS NULL OR business_types = '{}')"

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

@app.get("/api/knowledge/{knowledge_id}")
async def get_knowledge(knowledge_id: int, user: dict = Depends(get_current_user)):
    """取得單一知識詳情（含關聯意圖）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 取得知識基本資訊（加入業者資訊、表單關聯、API 配置）
        cur.execute("""
            SELECT kb.id, kb.question_summary, kb.answer as content,
                   kb.keywords, kb.business_types, kb.target_user, kb.priority, kb.created_at, kb.updated_at,
                   kb.video_url, kb.video_s3_key, kb.video_file_size, kb.video_duration, kb.video_format,
                   kb.vendor_ids,
                   kb.form_id,
                   kb.action_type,
                   kb.api_config,
                   kb.trigger_mode,
                   kb.immediate_prompt,
                   v.name as vendor_name
            FROM knowledge_base kb
            LEFT JOIN vendors v ON v.id = ANY(kb.vendor_ids)
            WHERE kb.id = %s
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

        # 取得關聯的意圖
        cur.execute("""
            SELECT
                kim.intent_id,
                i.name as intent_name,
                kim.intent_type,
                kim.confidence
            FROM knowledge_intent_mapping kim
            JOIN intents i ON kim.intent_id = i.id
            WHERE kim.knowledge_id = %s
            ORDER BY
                CASE kim.intent_type
                    WHEN 'primary' THEN 1
                    WHEN 'secondary' THEN 2
                END,
                kim.confidence DESC
        """, (knowledge_id,))

        intents = [dict(row) for row in cur.fetchall()]
        result['intent_mappings'] = intents

        return result

    finally:
        cur.close()
        conn.close()

@app.put("/api/knowledge/{knowledge_id}")
async def update_knowledge(knowledge_id: int, data: KnowledgeUpdate, user: dict = Depends(get_current_user)):
    """
    更新知識（自動重新生成向量）

    流程：
    1. 驗證知識存在
    2. 呼叫 Embedding API 生成新向量
    3. 更新資料庫（包含新向量）
    4. 更新意圖關聯
    5. 回傳結果
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. 檢查知識是否存在
        cur.execute("SELECT id FROM knowledge_base WHERE id = %s", (knowledge_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="知識不存在")

        # 2. 生成新向量（使用 question_summary + keywords 以提高檢索準確度）
        try:
            # ✅ 方案 A：將 keywords 融入 embedding
            keywords_str = ", ".join(data.keywords) if data.keywords else ""
            text_for_embedding = f"{data.question_summary}. 關鍵字: {keywords_str}" if keywords_str else data.question_summary

            embedding_response = requests.post(
                EMBEDDING_API_URL,
                json={"text": text_for_embedding},
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
                question_summary = %s,
                answer = %s,
                keywords = %s,
                embedding = %s,
                business_types = %s,
                target_user = %s,
                priority = %s,
                vendor_ids = %s,
                form_id = %s,
                action_type = %s,
                api_config = %s,
                trigger_mode = %s,
                immediate_prompt = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, question_summary, updated_at
        """, (
            data.question_summary,
            data.content,
            data.keywords,
            new_embedding,
            data.business_types,
            data.target_user,
            data.priority,
            data.vendor_ids,  # 使用 vendor_ids 陣列，支援 None 值
            data.form_id,
            data.action_type,
            Json(data.api_config) if data.api_config else None,
            data.trigger_mode,
            data.immediate_prompt,
            knowledge_id
        ))

        updated = cur.fetchone()

        # 4. 更新意圖關聯
        # 如果有提供 intent_mappings，先刪除舊的，再插入新的
        if data.intent_mappings is not None:
            # 刪除舊的關聯
            cur.execute("""
                DELETE FROM knowledge_intent_mapping
                WHERE knowledge_id = %s
            """, (knowledge_id,))

            # 插入新的關聯
            for mapping in data.intent_mappings:
                cur.execute("""
                    INSERT INTO knowledge_intent_mapping
                    (knowledge_id, intent_id, intent_type, confidence, assigned_by)
                    VALUES (%s, %s, %s, %s, 'manual')
                    ON CONFLICT (knowledge_id, intent_id) DO UPDATE
                    SET intent_type = EXCLUDED.intent_type,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                """, (knowledge_id, mapping.intent_id, mapping.intent_type, mapping.confidence))

        conn.commit()

        # 🔥 Phase 3: 緩存失效通知 - 通知 RAG Orchestrator 清除相關緩存
        try:
            rag_api_url = os.getenv("RAG_API_URL", "http://rag-orchestrator:8100")
            invalidation_payload = {
                "type": "knowledge_update",
                "knowledge_id": knowledge_id,
                "intent_ids": [m.intent_id for m in data.intent_mappings or []]
            }

            invalidation_response = requests.post(
                f"{rag_api_url}/api/v1/cache/invalidate",
                json=invalidation_payload,
                timeout=3
            )

            if invalidation_response.status_code == 200:
                result = invalidation_response.json()
                print(f"✅ 緩存失效通知成功: 清除 {result.get('invalidated_count', 0)} 條緩存")
            else:
                print(f"⚠️  緩存失效通知失敗: {invalidation_response.status_code}")

        except requests.exceptions.RequestException as e:
            # 緩存失效失敗不應阻擋知識更新，僅記錄警告
            print(f"⚠️  緩存失效通知失敗（網絡錯誤）: {e}")
        except Exception as e:
            print(f"⚠️  緩存失效通知失敗: {e}")

        return {
            "success": True,
            "message": "知識已更新，向量已重新生成",
            "id": updated['id'],
            "question_summary": updated['question_summary'],
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
async def create_knowledge(data: KnowledgeUpdate, user: dict = Depends(get_current_user)):
    """
    新增知識

    流程：
    1. 生成向量
    2. 插入資料庫
    3. 插入意圖關聯（如有）
    4. 回傳新建資料
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. 生成向量（使用 question_summary + keywords 以提高檢索準確度）
        try:
            # ✅ 方案 A：將 keywords 融入 embedding
            keywords_str = ", ".join(data.keywords) if data.keywords else ""
            text_for_embedding = f"{data.question_summary}. 關鍵字: {keywords_str}" if keywords_str else data.question_summary

            print(f"🔄 正在呼叫 Embedding API: {EMBEDDING_API_URL}")
            print(f"📝 文字內容: {text_for_embedding[:100]}...")

            embedding_response = requests.post(
                EMBEDDING_API_URL,
                json={"text": text_for_embedding},
                timeout=30
            )

            print(f"📊 Embedding API 回應狀態: {embedding_response.status_code}")

            if embedding_response.status_code != 200:
                error_detail = f"Embedding API 錯誤 (狀態碼: {embedding_response.status_code}): {embedding_response.text}"
                print(f"❌ {error_detail}")
                raise Exception(error_detail)

            embedding = embedding_response.json()['embedding']
            print(f"✅ 向量生成成功，維度: {len(embedding)}")

        except requests.exceptions.RequestException as e:
            error_msg = f"無法連線到 Embedding API: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

        # 2. 插入資料庫
        print(f"💾 開始插入資料庫...")
        print(f"📋 資料: question_summary={data.question_summary}, business_types={data.business_types}, target_user={data.target_user}")

        cur.execute("""
            INSERT INTO knowledge_base
            (question_summary, answer, keywords, embedding, business_types, target_user, priority, vendor_ids, form_id, action_type, api_config, trigger_mode, immediate_prompt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            data.question_summary,
            data.content,
            data.keywords,
            embedding,
            data.business_types,
            data.target_user,
            data.priority,
            data.vendor_ids,  # 使用 vendor_ids 陣列，支援 None 值
            data.form_id,
            data.action_type,
            Json(data.api_config) if data.api_config else None,
            data.trigger_mode,
            data.immediate_prompt
        ))

        new_record = cur.fetchone()
        new_id = new_record['id']
        print(f"✅ 知識已插入，ID: {new_id}")

        # 3. 插入意圖關聯
        if data.intent_mappings:
            for mapping in data.intent_mappings:
                cur.execute("""
                    INSERT INTO knowledge_intent_mapping
                    (knowledge_id, intent_id, intent_type, confidence, assigned_by)
                    VALUES (%s, %s, %s, %s, 'manual')
                    ON CONFLICT (knowledge_id, intent_id) DO UPDATE
                    SET intent_type = EXCLUDED.intent_type,
                        confidence = EXCLUDED.confidence,
                        updated_at = NOW()
                """, (new_id, mapping.intent_id, mapping.intent_type, mapping.confidence))

        conn.commit()

        return {
            "success": True,
            "message": "知識已新增",
            "id": new_id,
            "created_at": new_record['created_at'].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ 新增知識失敗:")
        print(error_traceback)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"新增失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.delete("/api/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, user: dict = Depends(get_current_user)):
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

        # 🔥 Phase 3: 緩存失效通知 - 刪除知識時清除緩存
        try:
            rag_api_url = os.getenv("RAG_API_URL", "http://rag-orchestrator:8100")
            invalidation_payload = {
                "type": "knowledge_update",
                "knowledge_id": knowledge_id
            }

            invalidation_response = requests.post(
                f"{rag_api_url}/api/v1/cache/invalidate",
                json=invalidation_payload,
                timeout=3
            )

            if invalidation_response.status_code == 200:
                result = invalidation_response.json()
                print(f"✅ 緩存失效通知成功（知識刪除）: 清除 {result.get('invalidated_count', 0)} 條緩存")
            else:
                print(f"⚠️  緩存失效通知失敗: {invalidation_response.status_code}")

        except Exception as e:
            print(f"⚠️  緩存失效通知失敗: {e}")

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

@app.post("/api/knowledge/regenerate-embeddings")
async def regenerate_all_embeddings(user: dict = Depends(get_current_user)):
    """批量重新生成所有缺失的 embedding"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 1. 查询所有没有 embedding 的知识
        cur.execute("""
            SELECT id, question_summary, answer, keywords
            FROM knowledge_base
            WHERE embedding IS NULL
            ORDER BY id
        """)

        rows = cur.fetchall()
        total = len(rows)

        if total == 0:
            return {
                "success": True,
                "message": "所有知识已有向量",
                "total": 0,
                "generated": 0
            }

        # 2. 逐笔生成 embedding
        success_count = 0
        failed_ids = []

        for row in rows:
            kb_id = row['id']
            question = row['question_summary']
            answer = row['answer']
            keywords = row.get('keywords', [])

            # ✅ 方案 A：將 keywords 融入 embedding
            keywords_str = ", ".join(keywords) if keywords else ""
            base_text = question if question else answer[:200]
            text_for_embedding = f"{base_text}. 關鍵字: {keywords_str}" if keywords_str else base_text

            try:
                embedding_response = requests.post(
                    EMBEDDING_API_URL,
                    json={"text": text_for_embedding},
                    timeout=30
                )

                if embedding_response.status_code == 200:
                    embedding = embedding_response.json()['embedding']

                    # 更新数据库
                    cur.execute("""
                        UPDATE knowledge_base
                        SET embedding = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (embedding, kb_id))

                    success_count += 1
                else:
                    failed_ids.append(kb_id)

            except Exception as e:
                print(f"⚠️  生成 embedding 失败 (ID {kb_id}): {e}")
                failed_ids.append(kb_id)

        conn.commit()

        return {
            "success": True,
            "message": f"批量生成完成：成功 {success_count}/{total}",
            "total": total,
            "generated": success_count,
            "failed": len(failed_ids),
            "failed_ids": failed_ids
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.get("/api/intents")
async def list_intents(user: dict = Depends(get_current_user)):
    """取得所有意圖"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, name, description
            FROM intents
            WHERE is_enabled = TRUE
            ORDER BY name
        """)

        intents = [dict(row) for row in cur.fetchall()]

        return {"intents": intents}

    finally:
        cur.close()
        conn.close()

@app.get("/api/vendors")
async def list_vendors(user: dict = Depends(get_current_user)):
    """取得所有業者"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, name
            FROM vendors
            ORDER BY id
        """)

        vendors = [dict(row) for row in cur.fetchall()]

        return {"vendors": vendors}

    finally:
        cur.close()
        conn.close()

@app.get("/api/target-users")
async def list_target_users(user: dict = Depends(get_current_user)):
    """取得所有目標用戶類型（僅啟用）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT user_value, display_name, description, icon, display_order
            FROM target_user_config
            WHERE is_active = TRUE
            ORDER BY id
        """)

        target_users = [dict(row) for row in cur.fetchall()]

        return {"target_users": target_users}

    finally:
        cur.close()
        conn.close()


# ==================== Target User Config Management ====================

@app.get("/api/target-users-config")
async def list_target_users_config(is_active: Optional[bool] = None, user: dict = Depends(get_current_user)):
    """取得目標用戶類型配置（管理介面用）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT id, user_value, display_name, description, icon,
                   display_order, is_active, created_at, updated_at
            FROM target_user_config
        """
        params = []

        if is_active is not None:
            query += " WHERE is_active = %s"
            params.append(is_active)

        query += " ORDER BY id"

        cur.execute(query, params)
        target_users = [dict(row) for row in cur.fetchall()]

        return {"target_users": target_users}

    finally:
        cur.close()
        conn.close()


class TargetUserConfigCreate(BaseModel):
    user_value: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0


class TargetUserConfigUpdate(BaseModel):
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    is_active: Optional[bool] = None


@app.post("/api/target-users-config")
async def create_target_user_config(data: TargetUserConfigCreate, user: dict = Depends(get_current_user)):
    """新增目標用戶類型"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查 user_value 是否已存在
        cur.execute(
            "SELECT user_value FROM target_user_config WHERE user_value = %s",
            (data.user_value,)
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="此用戶類型值已存在")

        # 新增記錄
        cur.execute("""
            INSERT INTO target_user_config
            (user_value, display_name, description, icon, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING id, user_value, display_name, created_at
        """, (
            data.user_value,
            data.display_name,
            data.description,
            data.icon,
            data.display_order
        ))

        result = dict(cur.fetchone())
        conn.commit()

        return {"message": "目標用戶類型已新增", "target_user": result}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.put("/api/target-users-config/{user_value}")
async def update_target_user_config(user_value: str, data: TargetUserConfigUpdate, user: dict = Depends(get_current_user)):
    """更新目標用戶類型"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查是否存在
        cur.execute(
            "SELECT id FROM target_user_config WHERE user_value = %s",
            (user_value,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="目標用戶類型不存在")

        # 更新記錄
        update_fields = []
        params = []

        update_fields.append("display_name = %s")
        params.append(data.display_name)

        if data.description is not None:
            update_fields.append("description = %s")
            params.append(data.description)

        if data.icon is not None:
            update_fields.append("icon = %s")
            params.append(data.icon)

        update_fields.append("display_order = %s")
        params.append(data.display_order)

        if data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(data.is_active)

        update_fields.append("updated_at = NOW()")
        params.append(user_value)

        query = f"""
            UPDATE target_user_config
            SET {', '.join(update_fields)}
            WHERE user_value = %s
            RETURNING id, user_value, display_name, updated_at
        """

        cur.execute(query, params)
        result = dict(cur.fetchone())
        conn.commit()

        return {"message": "目標用戶類型已更新", "target_user": result}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.delete("/api/target-users-config/{user_value}")
async def delete_target_user_config(user_value: str, user: dict = Depends(get_current_user)):
    """停用目標用戶類型（軟刪除）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查是否存在
        cur.execute(
            "SELECT id, is_active FROM target_user_config WHERE user_value = %s",
            (user_value,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="目標用戶類型不存在")

        # 停用（軟刪除）
        cur.execute("""
            UPDATE target_user_config
            SET is_active = FALSE, updated_at = NOW()
            WHERE user_value = %s
        """, (user_value,))

        conn.commit()

        return {"message": "目標用戶類型已停用"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/api/knowledge/{knowledge_id}/intents")
async def add_knowledge_intent(knowledge_id: int, mapping: IntentMapping, user: dict = Depends(get_current_user)):
    """為知識新增意圖關聯"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查知識是否存在
        cur.execute("SELECT id FROM knowledge_base WHERE id = %s", (knowledge_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="知識不存在")

        # 檢查意圖是否存在
        cur.execute("SELECT id FROM intents WHERE id = %s", (mapping.intent_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="意圖不存在")

        # 新增或更新關聯
        cur.execute("""
            INSERT INTO knowledge_intent_mapping
            (knowledge_id, intent_id, intent_type, confidence, assigned_by)
            VALUES (%s, %s, %s, %s, 'manual')
            ON CONFLICT (knowledge_id, intent_id) DO UPDATE
            SET intent_type = EXCLUDED.intent_type,
                confidence = EXCLUDED.confidence,
                updated_at = NOW()
            RETURNING id
        """, (knowledge_id, mapping.intent_id, mapping.intent_type, mapping.confidence))

        mapping_id = cur.fetchone()['id']
        conn.commit()

        return {
            "success": True,
            "message": "意圖關聯已新增",
            "mapping_id": mapping_id
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"新增失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.delete("/api/knowledge/{knowledge_id}/intents/{intent_id}")
async def remove_knowledge_intent(knowledge_id: int, intent_id: int, user: dict = Depends(get_current_user)):
    """移除知識的意圖關聯"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM knowledge_intent_mapping
            WHERE knowledge_id = %s AND intent_id = %s
            RETURNING id
        """, (knowledge_id, intent_id))

        deleted = cur.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="意圖關聯不存在")

        conn.commit()

        return {
            "success": True,
            "message": "意圖關聯已移除"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"移除失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()

@app.get("/api/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    """取得統計資訊"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 總知識數
        cur.execute("SELECT COUNT(*) as total FROM knowledge_base")
        total = cur.fetchone()['total']

        # 按來源類型統計
        cur.execute("""
            SELECT
                COALESCE(source_type, 'manual') as source_type,
                COUNT(*) as count
            FROM knowledge_base
            GROUP BY source_type
            ORDER BY count DESC
        """)
        by_source_type = [dict(row) for row in cur.fetchall()]

        # 按業態類型統計
        cur.execute("""
            SELECT
                UNNEST(business_types) as business_type,
                COUNT(*) as count
            FROM knowledge_base
            WHERE business_types IS NOT NULL
            GROUP BY business_type
            ORDER BY count DESC
        """)
        by_business_type = [dict(row) for row in cur.fetchall()]

        # 按意圖統計（前 10 個）- 使用 knowledge_intent_mapping
        cur.execute("""
            SELECT
                COALESCE(i.name, '未分類') as intent_name,
                COUNT(DISTINCT COALESCE(kim.knowledge_id, kb.id)) as count
            FROM knowledge_base kb
            LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id AND kim.intent_type = 'primary'
            LEFT JOIN intents i ON kim.intent_id = i.id
            GROUP BY i.name
            ORDER BY count DESC
            LIMIT 10
        """)
        by_intent = [dict(row) for row in cur.fetchall()]

        # Embedding 覆蓋率統計
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as has_embedding,
                COUNT(*) - COUNT(embedding) as missing_embedding,
                ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as coverage_rate
            FROM knowledge_base
        """)
        embedding_stats = dict(cur.fetchone())

        # 最近更新
        cur.execute("""
            SELECT id, question_summary, updated_at
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
            "by_source_type": by_source_type,
            "by_business_type": by_business_type,
            "by_intent": by_intent,
            "embedding_stats": embedding_stats,
            "recent_updates": recent_updates
        }

    finally:
        cur.close()
        conn.close()

@app.get("/api/backtest/results")
async def get_backtest_results(
    status_filter: Optional[str] = Query(None, description="篩選狀態 (all/failed/passed)"),
    limit: int = Query(50, ge=1, le=200, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user)
):
    """
    取得回測結果

    讀取最新的回測結果 Excel 文件，並提供過濾和分頁功能
    """
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    backtest_path = os.path.join(project_root, "output/backtest/backtest_results.xlsx")

    if not os.path.exists(backtest_path):
        raise HTTPException(
            status_code=404,
            detail="回測結果文件不存在。請先通過管理後台的「回測」頁面執行回測，或使用 API: POST /api/backtest/run"
        )

    try:
        # 讀取 Excel 文件
        df = pd.read_excel(backtest_path, engine='openpyxl')

        # 過濾狀態
        if status_filter == "failed":
            df = df[df['passed'] == False]
        elif status_filter == "passed":
            df = df[df['passed'] == True]
        # status_filter == "all" 或 None 則顯示全部

        total = len(df)

        # 分頁
        df_page = df.iloc[offset:offset+limit]

        # 轉換為 dict
        import math
        results = []
        for _, row in df_page.iterrows():
            # 處理 NaN 值
            actual_intent = row['actual_intent']
            if isinstance(actual_intent, float) and math.isnan(actual_intent):
                actual_intent = None

            system_answer = row['system_answer']
            if isinstance(system_answer, float) and math.isnan(system_answer):
                system_answer = None

            optimization_tips = row.get('optimization_tips', '')
            if isinstance(optimization_tips, float) and math.isnan(optimization_tips):
                optimization_tips = ''

            # 處理知識來源欄位
            knowledge_sources = row.get('knowledge_sources', '')
            if isinstance(knowledge_sources, float) and math.isnan(knowledge_sources):
                knowledge_sources = ''

            source_ids = row.get('source_ids', '')
            if isinstance(source_ids, float) and math.isnan(source_ids):
                source_ids = ''

            knowledge_links = row.get('knowledge_links', '')
            if isinstance(knowledge_links, float) and math.isnan(knowledge_links):
                knowledge_links = ''

            batch_url = row.get('batch_url', '')
            if isinstance(batch_url, float) and math.isnan(batch_url):
                batch_url = ''

            source_count = row.get('source_count', 0)
            if isinstance(source_count, float) and math.isnan(source_count):
                source_count = 0

            # 處理 expected_category（舊結果可能有，新結果為 NULL）
            expected_category = row.get('expected_category', '') or ''

            result = {
                'test_id': int(row['test_id']),
                'test_question': row['test_question'],
                'expected_category': expected_category,  # 保留用於向後兼容，新結果為空字符串
                'actual_intent': actual_intent,
                'system_answer': system_answer,
                'confidence': float(row['confidence']),
                'score': float(row['score']),
                'passed': bool(row['passed']),
                'optimization_tips': optimization_tips,
                'knowledge_sources': knowledge_sources,
                'source_ids': source_ids,
                'source_count': int(source_count) if source_count else 0,
                'knowledge_links': knowledge_links,
                'batch_url': batch_url,
                'difficulty': row.get('difficulty', 'medium'),
                'timestamp': row['timestamp']
            }

            # 添加品質評估欄位（如果存在）
            if 'relevance' in row:
                quality_data = {}
                for field in ['relevance', 'completeness', 'accuracy', 'intent_match', 'quality_overall']:
                    val = row.get(field, 0)
                    quality_data[field] = float(val) if not (isinstance(val, float) and math.isnan(val)) else 0

                quality_reasoning = row.get('quality_reasoning', '')
                if isinstance(quality_reasoning, float) and math.isnan(quality_reasoning):
                    quality_reasoning = ''
                quality_data['quality_reasoning'] = quality_reasoning

                overall_score = row.get('overall_score', row['score'])
                quality_data['overall_score'] = float(overall_score) if not (isinstance(overall_score, float) and math.isnan(overall_score)) else float(row['score'])

                result['quality'] = quality_data

            results.append(result)

        # 計算統計
        import math
        total_tests = len(df)
        passed_tests = len(df[df['passed'] == True])
        failed_tests = len(df[df['passed'] == False])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        avg_score = df['score'].mean() if total_tests > 0 else 0
        avg_confidence = df['confidence'].mean() if total_tests > 0 else 0

        # 處理 NaN 值
        if math.isnan(avg_score):
            avg_score = 0
        if math.isnan(avg_confidence):
            avg_confidence = 0

        statistics = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": round(pass_rate, 2),
            "avg_score": round(avg_score, 3),
            "avg_confidence": round(avg_confidence, 3)
        }

        # 計算品質統計（如果有的話）
        if 'relevance' in df.columns:
            quality_df = df[df['relevance'].notna()]
            if len(quality_df) > 0:
                quality_stats = {
                    'count': len(quality_df),
                    'avg_relevance': round(quality_df['relevance'].mean(), 2),
                    'avg_completeness': round(quality_df['completeness'].mean(), 2),
                    'avg_accuracy': round(quality_df['accuracy'].mean(), 2),
                    'avg_intent_match': round(quality_df['intent_match'].mean(), 2),
                    'avg_quality_overall': round(quality_df['quality_overall'].mean(), 2)
                }

                # 添加整體評分（如果有）
                if 'overall_score' in df.columns:
                    overall_df = df[df['overall_score'].notna()]
                    if len(overall_df) > 0:
                        quality_stats['avg_overall_score'] = round(overall_df['overall_score'].mean(), 3)

                statistics['quality'] = quality_stats

        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "statistics": statistics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取回測結果失敗: {str(e)}")

@app.get("/api/backtest/summary")
async def get_backtest_summary(user: dict = Depends(get_current_user)):
    """取得回測摘要統計"""
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    summary_path = os.path.join(project_root, "output/backtest/backtest_results_summary.txt")

    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()
            return {"summary": summary_text}
        except Exception as e:
            return {"summary": f"無法讀取摘要：{str(e)}"}
    else:
        return {"summary": "尚無回測摘要"}


@app.get("/api/backtest/runs")
async def list_backtest_runs(
    limit: int = Query(10, ge=1, le=50, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user)
):
    """
    列出歷史回測執行記錄

    從資料庫查詢所有已完成的回測執行，包含統計摘要
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 查詢回測執行記錄（包含 completed 和 running 狀態，以及 cancelled）
        cur.execute("""
            SELECT
                id,
                quality_mode,
                test_type,
                total_scenarios,
                executed_scenarios,
                passed_count,
                failed_count,
                pass_rate,
                avg_score,
                avg_confidence,
                avg_relevance,
                avg_completeness,
                avg_accuracy,
                avg_intent_match,
                avg_quality_overall,
                ndcg_score,
                started_at,
                completed_at,
                CASE
                    WHEN status = 'running' THEN EXTRACT(EPOCH FROM (NOW() - started_at))::int
                    ELSE duration_seconds
                END as duration_seconds,
                status,
                rag_api_url,
                vendor_id
            FROM backtest_runs
            WHERE status IN ('completed', 'running', 'cancelled')
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        runs = []
        for row in cur.fetchall():
            run = dict(row)
            # 轉換日期格式
            if run.get('started_at'):
                run['started_at'] = run['started_at'].isoformat()
            if run.get('completed_at'):
                run['completed_at'] = run['completed_at'].isoformat()
            runs.append(run)

        # 取得總數
        cur.execute("""
            SELECT COUNT(*) as total
            FROM backtest_runs
            WHERE status = 'completed'
        """)
        total = cur.fetchone()['total']

        return {
            "runs": runs,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢回測記錄失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()


@app.get("/api/backtest/runs/{run_id}/results")
async def get_backtest_run_results(
    run_id: int,
    status_filter: Optional[str] = Query(None, description="篩選狀態 (all/failed/passed)"),
    limit: int = Query(50, ge=1, le=200, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user)
):
    """
    取得特定回測執行的詳細結果

    從資料庫查詢指定回測執行的所有測試結果
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 先檢查 run 是否存在
        cur.execute("""
            SELECT id, quality_mode, test_type, started_at, completed_at,
                   passed_count, failed_count, pass_rate, avg_score, avg_confidence
            FROM backtest_runs
            WHERE id = %s
        """, (run_id,))

        run_info = cur.fetchone()
        if not run_info:
            raise HTTPException(status_code=404, detail=f"回測執行 ID {run_id} 不存在")

        run_info = dict(run_info)
        if run_info.get('started_at'):
            run_info['started_at'] = run_info['started_at'].isoformat()
        if run_info.get('completed_at'):
            run_info['completed_at'] = run_info['completed_at'].isoformat()

        # 建立查詢（移除已刪除字段：expected_category, category_match, keyword_coverage）
        # 從 evaluation JSONB 提取 V2 欄位：confidence_score, confidence_level, semantic_overlap, max_similarity, result_count, keyword_match_rate, failure_reason
        query = """
            SELECT
                id,
                scenario_id,
                test_question,
                actual_intent,
                all_intents,
                system_answer,
                confidence,
                score,
                overall_score,
                passed,
                relevance,
                completeness,
                accuracy,
                intent_match,
                quality_overall,
                quality_reasoning,
                source_ids,
                source_count,
                knowledge_sources,
                optimization_tips,
                tested_at,
                evaluation->>'confidence_score' as confidence_score,
                evaluation->>'confidence_level' as confidence_level,
                evaluation->>'max_similarity' as max_similarity,
                evaluation->>'result_count' as result_count,
                evaluation->>'keyword_match_rate' as keyword_match_rate,
                evaluation->>'failure_reason' as failure_reason
            FROM backtest_results
            WHERE run_id = %s
        """
        params = [run_id]

        # 過濾狀態
        if status_filter == "failed":
            query += " AND passed = FALSE"
        elif status_filter == "passed":
            query += " AND passed = TRUE"

        # 查詢總數（用於分頁）
        count_query = f"SELECT COUNT(*) as total FROM backtest_results WHERE run_id = %s"
        count_params = [run_id]
        if status_filter == "failed":
            count_query += " AND passed = FALSE"
        elif status_filter == "passed":
            count_query += " AND passed = TRUE"

        cur.execute(count_query, count_params)
        total = cur.fetchone()['total']

        # 分頁
        query += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        results = []
        for row in cur.fetchall():
            result = dict(row)
            # 轉換日期格式
            if result.get('tested_at'):
                result['tested_at'] = result['tested_at'].isoformat()
            # 添加 expected_category 用於向後兼容（新結果此字段已刪除，設為空字符串）
            result['expected_category'] = ''

            # 轉換 V2 欄位為數字類型（PostgreSQL ->> 返回字串）
            for field in ['confidence_score', 'max_similarity', 'keyword_match_rate']:
                if result.get(field) is not None and result[field] != '':
                    try:
                        result[field] = float(result[field])
                    except (ValueError, TypeError):
                        result[field] = None

            # result_count 轉為整數
            if result.get('result_count') is not None and result['result_count'] != '':
                try:
                    result['result_count'] = int(result['result_count'])
                except (ValueError, TypeError):
                    result['result_count'] = None

            results.append(result)

        # 計算統計（基於過濾後的結果）
        stats_query = """
            SELECT
                COUNT(*) as total_tests,
                COUNT(*) FILTER (WHERE passed = TRUE) as passed_tests,
                COUNT(*) FILTER (WHERE passed = FALSE) as failed_tests,
                AVG(score) as avg_score,
                AVG(confidence) as avg_confidence,
                AVG(relevance) as avg_relevance,
                AVG(completeness) as avg_completeness,
                AVG(accuracy) as avg_accuracy,
                AVG(intent_match) as avg_intent_match,
                AVG(quality_overall) as avg_quality_overall
            FROM backtest_results
            WHERE run_id = %s
        """
        stats_params = [run_id]
        if status_filter == "failed":
            stats_query += " AND passed = FALSE"
        elif status_filter == "passed":
            stats_query += " AND passed = TRUE"

        cur.execute(stats_query, stats_params)
        stats = dict(cur.fetchone())

        # 計算通過率
        if stats['total_tests'] > 0:
            stats['pass_rate'] = round((stats['passed_tests'] / stats['total_tests']) * 100, 2)
        else:
            stats['pass_rate'] = 0

        # 四捨五入數值
        for key in ['avg_score', 'avg_confidence', 'avg_relevance', 'avg_completeness',
                    'avg_accuracy', 'avg_intent_match', 'avg_quality_overall']:
            if stats.get(key) is not None:
                stats[key] = round(float(stats[key]), 3)

        return {
            "run_info": run_info,
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "statistics": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢回測結果失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()


class BacktestRunRequest(BaseModel):
    """回測執行請求模型（已廢棄 - 僅供參考）"""
    quality_mode: Optional[str] = "detailed"  # detailed, hybrid

class SmartBatchRequest(BaseModel):
    """智能分批回測請求模型"""
    batch_size: int = 200  # 每批題數
    batch_number: int = 1  # 第幾批 (1-based)
    quality_mode: Optional[str] = "hybrid"  # detailed, hybrid, basic
    vendor_id: Optional[int] = 1  # 測試業者 ID
    # 可選篩選條件
    status: Optional[str] = None  # pending_review, approved, rejected
    source: Optional[str] = None  # imported, manual, user_question
    difficulty: Optional[str] = None  # easy, medium, hard

class CountRequest(BaseModel):
    """題數統計請求模型"""
    status: Optional[str] = None
    source: Optional[str] = None
    difficulty: Optional[str] = None

class ContinuousBatchRequest(BaseModel):
    """連續分批回測請求模型"""
    batch_size: int = 50  # 每批題數
    quality_mode: Optional[str] = "hybrid"  # detailed, hybrid, basic
    vendor_id: Optional[int] = 1  # 測試業者 ID
    # 可選篩選條件
    status: Optional[str] = None
    source: Optional[str] = None
    difficulty: Optional[str] = None

# ========================================================================
# 舊版執行端點 POST /api/backtest/run 已移除
# 原因：功能已被 /api/backtest/run/smart-batch 和 /api/backtest/run/continuous-batch 取代
# 移除日期：2026-03-14
# ========================================================================


@app.post("/api/backtest/cancel")
async def cancel_backtest(user: dict = Depends(get_current_user)):
    """
    中斷當前運行的回測

    功能：
    1. 更新資料庫狀態為 cancelled
    2. 清除鎖文件
    3. 保留已完成的結果

    注意：由於回測運行在子進程中，無法直接終止進程，
    但更新資料庫狀態後，回測腳本會檢測到並自行停止。
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 查找正在運行的回測
        cur.execute("""
            SELECT id, executed_scenarios, started_at
            FROM backtest_runs
            WHERE status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """)

        running_run = cur.fetchone()

        if not running_run:
            cur.close()
            conn.close()
            return {"success": False, "message": "沒有正在運行的回測"}

        run_id = running_run['id']
        executed = running_run['executed_scenarios']

        # 更新狀態為 cancelled
        cur.execute("""
            UPDATE backtest_runs
            SET status = 'cancelled',
                completed_at = NOW()
            WHERE id = %s
        """, (run_id,))

        conn.commit()
        cur.close()
        conn.close()

        # 清除鎖文件
        backtest_lock_file = "/tmp/backtest_running.lock"
        if os.path.exists(backtest_lock_file):
            os.remove(backtest_lock_file)

        return {
            "success": True,
            "message": f"回測已中斷 (Run ID: {run_id}, 已完成 {executed} 個測試)",
            "run_id": run_id,
            "executed_scenarios": executed
        }

    except Exception as e:
        return {"success": False, "message": f"中斷失敗: {str(e)}"}


@app.get("/api/backtest/status")
async def get_backtest_status(user: dict = Depends(get_current_user)):
    """
    檢查回測執行狀態
    """
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    backtest_lock_file = "/tmp/backtest_running.lock"
    backtest_results_file = os.path.join(project_root, "output/backtest/backtest_results.xlsx")
    log_file = os.path.join(project_root, "output/backtest/backtest_log.txt")

    # 檢查是否正在執行
    is_running = os.path.exists(backtest_lock_file)

    # 檢查結果文件
    has_results = os.path.exists(backtest_results_file)
    last_run_time = None
    if has_results:
        last_run_time = datetime.fromtimestamp(
            os.path.getmtime(backtest_results_file)
        ).isoformat()

    # 讀取最新日誌
    log_content = None
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except:
            pass

    return {
        "is_running": is_running,
        "has_results": has_results,
        "last_run_time": last_run_time,
        "log": log_content
    }


@app.post("/api/test-scenarios/count")
async def count_test_scenarios(request: CountRequest = None):
    """
    統計符合條件的測試題數

    NOTE: 此 API 不需要認證，因為只是統計數量用於顯示 UI 資訊

    參數:
    - status: 篩選狀態 (pending_review, approved, rejected)
    - source: 篩選來源 (imported, manual, user_question)
    - difficulty: 篩選難度 (easy, medium, hard)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 建立查詢
        query = "SELECT COUNT(*) as total FROM test_scenarios WHERE 1=1"
        params = []

        # 添加篩選條件
        if request and request.status:
            query += " AND status = %s"
            params.append(request.status)

        if request and request.source:
            query += " AND source = %s"
            params.append(request.source)

        if request and request.difficulty:
            query += " AND difficulty = %s"
            params.append(request.difficulty)

        cur.execute(query, params)
        result = cur.fetchone()
        # 處理不同的 cursor 類型（dict 或 tuple）
        # SQL 使用 COUNT(*) as total，所以欄位名稱是 'total'
        if result:
            total = result['total'] if isinstance(result, dict) else result[0]
        else:
            total = 0

        cur.close()
        conn.close()

        return {
            "success": True,
            "total": total,
            "filters": {
                "status": request.status if request else None,
                "source": request.source if request else None,
                "difficulty": request.difficulty if request else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"統計失敗: {str(e)}")


@app.post("/api/backtest/run/smart-batch")
async def run_smart_batch(request: SmartBatchRequest, user: dict = Depends(get_current_user)):
    """
    智能分批回測

    範例:
    - batch_size=200, batch_number=1 → 測試第 1-200 題
    - batch_size=100, batch_number=3 → 測試第 201-300 題

    參數:
    - batch_size: 每批題數 (50/100/200/500)
    - batch_number: 第幾批 (1-based)
    - quality_mode: 品質評估模式 (detailed/hybrid/basic)
    - status: 可選，篩選狀態
    - source: 可選，篩選來源
    - difficulty: 可選，篩選難度
    """
    import subprocess
    import threading

    # 檢查是否已有回測在運行
    backtest_lock_file = "/tmp/backtest_running.lock"
    if os.path.exists(backtest_lock_file):
        raise HTTPException(
            status_code=409,
            detail="回測已在執行中，請等待完成後再試"
        )

    # 驗證參數
    if request.batch_size not in [50, 100, 200, 500]:
        raise HTTPException(status_code=400, detail="batch_size 必須為 50, 100, 200 或 500")

    if request.batch_number < 1:
        raise HTTPException(status_code=400, detail="batch_number 必須 >= 1")

    # 計算 offset 和 limit
    offset = (request.batch_number - 1) * request.batch_size
    limit = request.batch_size

    # 查詢符合條件的總題數
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        count_query = "SELECT COUNT(*) as total FROM test_scenarios WHERE 1=1"
        count_params = []

        if request.status:
            count_query += " AND status = %s"
            count_params.append(request.status)

        if request.source:
            count_query += " AND source = %s"
            count_params.append(request.source)

        if request.difficulty:
            count_query += " AND difficulty = %s"
            count_params.append(request.difficulty)

        cur.execute(count_query, count_params)
        result = cur.fetchone()
        # 處理不同的 cursor 類型（dict 或 tuple）
        total_scenarios = result['total'] if isinstance(result, dict) else result[0]

        cur.close()
        conn.close()

        # 檢查是否超出範圍
        if offset >= total_scenarios:
            raise HTTPException(
                status_code=400,
                detail=f"批次超出範圍：符合條件的題目共 {total_scenarios} 題，第 {request.batch_number} 批（offset={offset}）超出範圍"
            )

        # 計算實際會測試的題數（可能不足一批）
        actual_count = min(limit, total_scenarios - offset)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢題數失敗: {str(e)}")

    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    def run_backtest_script():
        """在背景執行分批回測腳本"""
        log_path = os.path.join(project_root, "output/backtest/backtest_log.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        try:
            # 創建鎖文件
            with open(backtest_lock_file, 'w') as f:
                f.write(str(datetime.now()))

            # 執行回測腳本（使用 docker exec 在 rag-orchestrator 容器中執行）
            # 構建環境變數設定
            env_vars = [
                f"OPENAI_MODEL=gpt-4o-mini",
                f"RAG_RETRIEVAL_LIMIT=3",
                f"BACKTEST_QUALITY_MODE={request.quality_mode}",
                f"BACKTEST_USE_DATABASE=true",
                f"BACKTEST_NON_INTERACTIVE=true",
                f"BACKTEST_CONCURRENCY=5",
                f"BACKTEST_DELAY=2.0",
                f"VENDOR_ID={request.vendor_id}",
                f"RAG_API_URL=http://localhost:8100",
                f"DB_HOST=aichatbot-postgres",
                f"DB_PORT=5432",
                f"DB_NAME=aichatbot_admin",
                f"DB_USER=aichatbot",
                f"DB_PASSWORD={os.getenv('DB_PASSWORD', 'aichatbot_password')}",
                f"BACKTEST_BATCH_OFFSET={offset}",
                f"BACKTEST_BATCH_LIMIT={limit}"
            ]

            # 篩選條件（如果有）
            if request.status:
                env_vars.append(f"BACKTEST_FILTER_STATUS={request.status}")
            if request.source:
                env_vars.append(f"BACKTEST_FILTER_SOURCE={request.source}")
            if request.difficulty:
                env_vars.append(f"BACKTEST_FILTER_DIFFICULTY={request.difficulty}")

            # 構建 docker exec 命令
            env_str = " && ".join([f"export {var}" for var in env_vars])
            docker_cmd = [
                "docker", "exec", "aichatbot-rag-orchestrator",
                "bash", "-c",
                f"{env_str} && cd /app && python3 run_backtest_db.py"
            ]

            # 根據批量大小動態計算超時時間（給予 3 倍緩衝）
            base_timeout_per_question = 5  # 每題預估 5 秒
            calculated_timeout = actual_count * base_timeout_per_question * 3
            # 最小 10 分鐘，最大 2 小時
            timeout_seconds = max(600, min(7200, calculated_timeout))

            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            # 記錄結果
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== 分批回測執行時間: {datetime.now()} ===\n")
                f.write(f"批次: {request.batch_number}, 批量: {request.batch_size}\n")
                f.write(f"範圍: 第 {offset + 1}-{offset + actual_count} 題\n")
                f.write(f"篩選條件: status={request.status}, source={request.source}, difficulty={request.difficulty}\n")
                f.write(f"Timeout 設定: {timeout_seconds} 秒 ({timeout_seconds/60:.1f} 分鐘)\n\n")
                f.write(f"返回碼: {result.returncode}\n\n")
                f.write("=== STDOUT ===\n")
                f.write(result.stdout)
                f.write("\n\n=== STDERR ===\n")
                f.write(result.stderr)

        except subprocess.TimeoutExpired:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n❌ 錯誤: 分批回測執行超時 ({timeout_seconds} 秒 = {timeout_seconds/60:.1f} 分鐘)\n")
                f.write(f"   建議：如果測試題目較多或網路較慢，可能需要調整 timeout 設定")
        except Exception as e:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n❌ 錯誤: {str(e)}")
        finally:
            # 移除鎖文件
            if os.path.exists(backtest_lock_file):
                os.remove(backtest_lock_file)

    # 在背景線程執行
    thread = threading.Thread(target=run_backtest_script)
    thread.daemon = True
    thread.start()

    # 估計執行時間（基於批量大小）
    time_per_question = 0.04 if request.quality_mode == 'basic' else 0.06 if request.quality_mode == 'hybrid' else 0.08
    estimated_minutes = (actual_count * time_per_question) / 60

    if estimated_minutes < 1:
        estimated_time = f"約需 {int(estimated_minutes * 60)} 秒"
    else:
        estimated_time = f"約需 {int(estimated_minutes)}-{int(estimated_minutes * 1.5)} 分鐘"

    return {
        "success": True,
        "message": f"分批回測已開始執行（{request.quality_mode} 模式）",
        "batch_info": {
            "batch_number": request.batch_number,
            "batch_size": request.batch_size,
            "actual_count": actual_count,
            "range": f"第 {offset + 1}-{offset + actual_count} 題",
            "total_available": total_scenarios
        },
        "filters": {
            "status": request.status,
            "source": request.source,
            "difficulty": request.difficulty
        },
        "quality_mode": request.quality_mode,
        "estimated_time": estimated_time
    }


@app.post("/api/backtest/run/continuous-batch")
async def run_continuous_batch(request: ContinuousBatchRequest, user: dict = Depends(get_current_user)):
    """
    連續分批回測 - 自動執行多個批次直到測完所有題目

    範例：batch_size=50 → 自動執行 60 批（假設總共 3000 題）

    執行流程：
    1. 立即返回（不會 timeout）
    2. 背景執行所有批次
    3. 前端輪詢進度
    4. 完成後顯示完整報告
    """
    import subprocess
    import threading

    # 檢查是否已有回測在運行
    backtest_lock_file = "/tmp/backtest_running.lock"
    if os.path.exists(backtest_lock_file):
        raise HTTPException(
            status_code=409,
            detail="回測已在執行中，請等待完成後再試"
        )

    # 驗證參數
    if request.batch_size not in [50, 100, 200, 500]:
        raise HTTPException(status_code=400, detail="batch_size 必須為 50, 100, 200 或 500")

    # 查詢符合條件的總題數
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        count_query = "SELECT COUNT(*) as total FROM test_scenarios WHERE 1=1"
        count_params = []

        if request.status:
            count_query += " AND status = %s"
            count_params.append(request.status)

        if request.source:
            count_query += " AND source = %s"
            count_params.append(request.source)

        if request.difficulty:
            count_query += " AND difficulty = %s"
            count_params.append(request.difficulty)

        cur.execute(count_query, count_params)
        result = cur.fetchone()
        total_scenarios = result['total'] if isinstance(result, dict) else result[0]

        if total_scenarios == 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail="沒有符合條件的測試題目")

        # 計算總批次數
        total_batches = math.ceil(total_scenarios / request.batch_size)

        # 創建 backtest_run 記錄
        cur.execute("""
            INSERT INTO backtest_runs (
                quality_mode, test_type, total_scenarios, executed_scenarios,
                status, total_batches, completed_batches,
                rag_api_url, vendor_id, started_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            ) RETURNING id
        """, (
            request.quality_mode, 'continuous_batch', total_scenarios, 0,
            'running', total_batches, 0,
            'http://localhost:8100', request.vendor_id
        ))

        result = cur.fetchone()
        run_id = result['id'] if isinstance(result, dict) else result[0]
        conn.commit()
        cur.close()
        conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失敗: {str(e)}")

    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    def execute_continuous_batches():
        """背景執行連續批次"""
        log_path = os.path.join(project_root, "output/backtest/backtest_log.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        try:
            # 創建鎖文件
            with open(backtest_lock_file, 'w') as f:
                f.write(str(datetime.now()))

            # 記錄開始
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== 連續分批回測開始: {datetime.now()} ===\n")
                f.write(f"總題數: {total_scenarios}\n")
                f.write(f"批量大小: {request.batch_size}\n")
                f.write(f"總批次數: {total_batches}\n")
                f.write(f"品質模式: {request.quality_mode}\n")
                f.write(f"Run ID: {run_id}\n\n")

            # 執行每個批次
            for batch_num in range(1, total_batches + 1):
                try:
                    offset = (batch_num - 1) * request.batch_size
                    limit = min(request.batch_size, total_scenarios - offset)

                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n--- Batch {batch_num}/{total_batches} 開始 ({datetime.now()}) ---\n")
                        f.write(f"範圍: 第 {offset + 1}-{offset + limit} 題\n")

                    # 執行回測腳本
                    script_path = os.path.join(project_root, "scripts/backtest/run_backtest_with_db_progress.py")
                    env = os.environ.copy()

                    # 基本設定
                    env["OPENAI_MODEL"] = "gpt-4o-mini"
                    env["RAG_RETRIEVAL_LIMIT"] = "3"
                    env["BACKTEST_QUALITY_MODE"] = request.quality_mode
                    env["BACKTEST_USE_DATABASE"] = "true"
                    env["PROJECT_ROOT"] = project_root
                    env["BACKTEST_NON_INTERACTIVE"] = "true"
                    env["BACKTEST_CONCURRENCY"] = "5"
                    env["VENDOR_ID"] = str(request.vendor_id)
                    env["RAG_API_URL"] = os.getenv("RAG_API_URL", "http://rag-orchestrator:8100")

                    # 資料庫連接參數
                    env["DB_HOST"] = os.getenv("DB_HOST", "postgres")
                    env["DB_PORT"] = os.getenv("DB_PORT", "5432")
                    env["DB_NAME"] = os.getenv("DB_NAME", "aichatbot_admin")
                    env["DB_USER"] = os.getenv("DB_USER", "aichatbot")
                    env["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "")

                    # 分批參數
                    env["BACKTEST_BATCH_OFFSET"] = str(offset)
                    env["BACKTEST_BATCH_LIMIT"] = str(limit)
                    env["BACKTEST_PARENT_RUN_ID"] = str(run_id)  # 傳遞 parent run_id

                    # 篩選條件
                    if request.status:
                        env["BACKTEST_FILTER_STATUS"] = request.status
                    if request.source:
                        env["BACKTEST_FILTER_SOURCE"] = request.source
                    if request.difficulty:
                        env["BACKTEST_FILTER_DIFFICULTY"] = request.difficulty

                    # 動態計算 timeout
                    base_timeout_per_question = 5
                    calculated_timeout = limit * base_timeout_per_question * 3
                    timeout_seconds = max(600, min(7200, calculated_timeout))

                    result = subprocess.run(
                        ["python3", script_path],
                        env=env,
                        capture_output=True,
                        text=True,
                        cwd=project_root,
                        timeout=timeout_seconds
                    )

                    with open(log_path, 'a', encoding='utf-8') as f:
                        if result.returncode == 0:
                            f.write(f"✅ Batch {batch_num} 完成\n")
                        else:
                            f.write(f"❌ Batch {batch_num} 失敗 (返回碼: {result.returncode})\n")
                            f.write(f"STDERR: {result.stderr[:500]}\n")

                    # 更新完成批次數
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE backtest_runs
                        SET completed_batches = %s
                        WHERE id = %s
                    """, (batch_num, run_id))
                    conn.commit()
                    cur.close()
                    conn.close()

                    # 檢查是否被取消
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT status FROM backtest_runs WHERE id = %s", (run_id,))
                    result = cur.fetchone()
                    status = result['status'] if isinstance(result, dict) else result[0]
                    cur.close()
                    conn.close()

                    if status == 'cancelled':
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write(f"\n⚠️ 用戶取消執行 (已完成 {batch_num}/{total_batches} 批)\n")
                        break

                except subprocess.TimeoutExpired:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"❌ Batch {batch_num} 超時 ({timeout_seconds} 秒)\n")
                    # 繼續下一批次
                except Exception as e:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"❌ Batch {batch_num} 錯誤: {str(e)}\n")
                    # 繼續下一批次

            # 更新最終狀態
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE backtest_runs
                SET status = 'completed',
                    completed_at = NOW()
                WHERE id = %s
            """, (run_id,))
            conn.commit()
            cur.close()
            conn.close()

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n=== 連續分批回測完成: {datetime.now()} ===\n")
                f.write(f"Run ID: {run_id}\n")

        except Exception as e:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n❌ 嚴重錯誤: {str(e)}\n")

            # 更新狀態為失敗
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE backtest_runs
                    SET status = 'failed',
                        completed_at = NOW()
                    WHERE id = %s
                """, (run_id,))
                conn.commit()
                cur.close()
                conn.close()
            except:
                pass

        finally:
            # 移除鎖文件
            if os.path.exists(backtest_lock_file):
                os.remove(backtest_lock_file)

    # 在背景線程執行
    thread = threading.Thread(target=execute_continuous_batches)
    thread.daemon = True
    thread.start()

    # 估計總執行時間
    time_per_batch = request.batch_size * 0.06 / 60  # 分鐘
    total_minutes = total_batches * time_per_batch

    if total_minutes < 60:
        estimated_time = f"約需 {int(total_minutes)}-{int(total_minutes * 1.5)} 分鐘"
    else:
        estimated_hours = total_minutes / 60
        estimated_time = f"約需 {estimated_hours:.1f}-{estimated_hours * 1.5:.1f} 小時"

    return {
        "success": True,
        "message": f"連續分批回測已啟動（背景執行中）",
        "run_id": run_id,
        "total_scenarios": total_scenarios,
        "batch_size": request.batch_size,
        "total_batches": total_batches,
        "quality_mode": request.quality_mode,
        "estimated_time": estimated_time,
        "note": "系統會自動執行所有批次，您可以關閉此頁面，稍後再回來查看結果"
    }


# ==================== Category 配置管理 API ====================

class CategoryConfig(BaseModel):
    """Category 配置模型"""
    category_value: str
    display_name: str
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


@app.get("/api/category-config")
async def get_category_config(
    include_inactive: bool = Query(False, description="是否包含已停用的分類"),
    user: dict = Depends(get_current_user)
):
    """
    取得所有 Category 配置

    Args:
        include_inactive: 是否包含已停用的分類（預設 false）

    Returns:
        categories: Category 配置列表
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            id, category_value, display_name, description,
            display_order, is_active, usage_count,
            created_at, updated_at
        FROM category_config
    """

    if not include_inactive:
        query += " WHERE is_active = true"

    query += " ORDER BY id"

    cur.execute(query)
    categories = [dict(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return {"categories": categories}


@app.post("/api/category-config")
async def create_category(category: CategoryConfig, user: dict = Depends(get_current_user)):
    """
    新增 Category 配置

    Args:
        category: Category 配置資料

    Returns:
        id: 新建的 Category ID
        message: 成功訊息
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 檢查 category_value 是否已存在
        cur.execute(
            "SELECT id FROM category_config WHERE category_value = %s",
            (category.category_value,)
        )

        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Category '{category.category_value}' 已存在"
            )

        # 插入新 category
        cur.execute("""
            INSERT INTO category_config
            (category_value, display_name, description, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            category.category_value,
            category.display_name,
            category.description,
            category.display_order,
            category.is_active
        ))

        category_id = cur.fetchone()['id']

        conn.commit()
        cur.close()
        conn.close()

        return {
            "id": category_id,
            "message": f"Category '{category.display_name}' 已新增"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.put("/api/category-config/{category_id}")
async def update_category(category_id: int, category: CategoryConfig, user: dict = Depends(get_current_user)):
    """
    更新 Category 配置

    Args:
        category_id: Category ID
        category: 更新的資料

    Returns:
        message: 成功訊息
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 檢查 category 是否存在
        cur.execute("SELECT id FROM category_config WHERE id = %s", (category_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Category 不存在")

        # 更新 category
        cur.execute("""
            UPDATE category_config
            SET display_name = %s,
                description = %s,
                display_order = %s,
                is_active = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            category.display_name,
            category.description,
            category.display_order,
            category.is_active,
            category_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": f"Category '{category.display_name}' 已更新"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.delete("/api/category-config/{category_id}")
async def delete_category(category_id: int, user: dict = Depends(get_current_user)):
    """
    刪除 Category 配置（軟刪除）

    如果該 category 被知識使用中，則只停用不刪除

    Args:
        category_id: Category ID

    Returns:
        message: 操作結果訊息
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 檢查 category 是否存在
        cur.execute(
            "SELECT category_value FROM category_config WHERE id = %s",
            (category_id,)
        )

        category = cur.fetchone()
        if not category:
            raise HTTPException(status_code=404, detail="Category 不存在")

        # 檢查是否有知識使用此 category
        cur.execute(
            "SELECT COUNT(*) as count FROM knowledge_base WHERE category = %s",
            (category['category_value'],)
        )

        usage = cur.fetchone()['count']

        if usage > 0:
            # 有使用中的知識，只能停用不能刪除
            cur.execute(
                "UPDATE category_config SET is_active = false, updated_at = NOW() WHERE id = %s",
                (category_id,)
            )
            message = f"Category 已停用（有 {usage} 筆知識使用中，無法刪除）"
        else:
            # 沒有使用，可以真刪除
            cur.execute("DELETE FROM category_config WHERE id = %s", (category_id,))
            message = "Category 已刪除"

        conn.commit()
        cur.close()
        conn.close()

        return {"message": message, "usage_count": usage}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/api/category-config/sync-usage")
async def sync_category_usage(user: dict = Depends(get_current_user)):
    """
    同步 Category 使用次數

    從 knowledge_base 表統計每個 category 的使用次數，並更新到 category_config

    Returns:
        message: 操作結果
        updated_count: 更新的 category 數量
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 同步使用次數
        cur.execute("""
            UPDATE category_config cc
            SET usage_count = (
                SELECT COUNT(*)
                FROM knowledge_base kb
                WHERE kb.category = cc.category_value
            ),
            updated_at = NOW()
        """)

        updated_rows = cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"已同步 {updated_rows} 個 Category 的使用次數",
            "updated_count": updated_rows
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動知識庫管理 API...")
    print(f"📊 API 文件: http://localhost:8000/docs")
    print(f"💾 資料庫: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
