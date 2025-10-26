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
import pandas as pd
from datetime import datetime

# 導入測試情境路由
from routes_test_scenarios import router as test_scenarios_router

app = FastAPI(
    title="知識庫管理 API",
    description="管理客服知識庫，自動處理向量生成與更新",
    version="1.0.0"
)

# 包含測試情境路由
app.include_router(test_scenarios_router)

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

class IntentMapping(BaseModel):
    """意圖關聯模型"""
    intent_id: int
    intent_type: str = 'secondary'  # 'primary' 或 'secondary'
    confidence: float = 1.0

class KnowledgeUpdate(BaseModel):
    """知識更新模型"""
    title: str
    category: str
    audience: str
    content: str
    keywords: List[str] = []
    question_summary: Optional[str] = None
    intent_mappings: Optional[List[IntentMapping]] = []  # 多意圖支援
    business_types: Optional[List[str]] = None  # 業態類型（可選，NULL=通用）

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
        # 建立查詢（加入意圖資訊 - 使用 knowledge_intent_mapping）
        query = """
            SELECT DISTINCT
                kb.id, kb.title, kb.category, kb.audience, kb.answer as content,
                kb.keywords, kb.question_summary, kb.business_types, kb.created_at, kb.updated_at
            FROM knowledge_base kb
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND kb.category = %s"
            params.append(category)

        if search:
            query += " AND (kb.title ILIKE %s OR kb.answer ILIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

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

@app.get("/api/knowledge/{knowledge_id}")
async def get_knowledge(knowledge_id: int):
    """取得單一知識詳情（含關聯意圖）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 取得知識基本資訊
        cur.execute("""
            SELECT id, title, category, audience, answer as content,
                   keywords, question_summary, business_types, created_at, updated_at,
                   video_url, video_s3_key, video_file_size, video_duration, video_format
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
async def update_knowledge(knowledge_id: int, data: KnowledgeUpdate):
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
                business_types = %s,
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
            data.business_types,
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
    3. 插入意圖關聯（如有）
    4. 回傳新建資料
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
            (title, category, audience, answer, keywords, question_summary, embedding, business_types)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            data.title,
            data.category,
            data.audience,
            data.content,
            data.keywords,
            data.question_summary,
            embedding,
            data.business_types
        ))

        new_record = cur.fetchone()
        new_id = new_record['id']

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

@app.get("/api/intents")
async def list_intents():
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

@app.post("/api/knowledge/{knowledge_id}/intents")
async def add_knowledge_intent(knowledge_id: int, mapping: IntentMapping):
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
async def remove_knowledge_intent(knowledge_id: int, intent_id: int):
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

@app.get("/api/backtest/results")
async def get_backtest_results(
    status_filter: Optional[str] = Query(None, description="篩選狀態 (all/failed/passed)"),
    limit: int = Query(50, ge=1, le=200, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量")
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
            detail="回測結果文件不存在。請先執行回測：python3 scripts/knowledge_extraction/backtest_framework.py"
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
async def get_backtest_summary():
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
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    列出歷史回測執行記錄

    從資料庫查詢所有已完成的回測執行，包含統計摘要
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 查詢回測執行記錄
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
                duration_seconds,
                rag_api_url,
                vendor_id
            FROM backtest_runs
            WHERE status = 'completed'
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
    offset: int = Query(0, ge=0, description="偏移量")
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
                tested_at
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
    """回測執行請求模型"""
    quality_mode: Optional[str] = "detailed"  # detailed, hybrid
    test_strategy: Optional[str] = "full"  # full, incremental, failed_only

@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRunRequest = None):
    """
    執行回測腳本

    這會在後台執行回測腳本並返回任務ID

    參數:
    - quality_mode: 品質評估模式 (detailed/hybrid)
    - test_strategy: 測試策略 (full/incremental/failed_only)
    """
    import subprocess
    import threading

    # 如果沒有提供 request body，使用預設值
    if request is None:
        request = BacktestRunRequest()

    # 使用資料庫模式，不再需要 Excel 文件
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    # 檢查是否已有回測在運行
    backtest_lock_file = "/tmp/backtest_running.lock"
    if os.path.exists(backtest_lock_file):
        raise HTTPException(
            status_code=409,
            detail="回測已在執行中，請等待完成後再試"
        )

    def run_backtest_script():
        """在背景執行回測腳本"""
        try:
            # 創建鎖文件
            with open(backtest_lock_file, 'w') as f:
                f.write(str(datetime.now()))

            # 執行回測腳本
            script_path = os.path.join(project_root, "scripts/knowledge_extraction/backtest_framework.py")
            env = os.environ.copy()

            # 設定優化環境變數（用於降低回測成本）
            env["OPENAI_MODEL"] = "gpt-4o-mini"  # 使用更便宜的模型
            env["RAG_RETRIEVAL_LIMIT"] = "3"  # 減少檢索條數
            env["BACKTEST_SELECTION_STRATEGY"] = request.test_strategy  # 測試策略 (full/incremental/failed_only)
            env["BACKTEST_QUALITY_MODE"] = request.quality_mode  # 品質評估模式 (detailed/hybrid)
            env["BACKTEST_USE_DATABASE"] = "true"  # 使用資料庫模式
            env["PROJECT_ROOT"] = project_root  # 傳遞專案根目錄
            env["BACKTEST_NON_INTERACTIVE"] = "true"  # 非交互模式，不等待用戶輸入

            result = subprocess.run(
                ["python3", script_path],
                env=env,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=600  # 10 分鐘超時
            )

            # 記錄結果
            log_path = os.path.join(project_root, "output/backtest/backtest_log.txt")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== 回測執行時間: {datetime.now()} ===\n\n")
                f.write(f"返回碼: {result.returncode}\n\n")
                f.write("=== STDOUT ===\n")
                f.write(result.stdout)
                f.write("\n\n=== STDERR ===\n")
                f.write(result.stderr)

        except subprocess.TimeoutExpired:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write("\n\n❌ 錯誤: 回測執行超時 (10 分鐘)")
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

    # 根據品質模式和測試策略估計時間
    time_estimates = {
        'detailed': '約需 5-10 分鐘（使用 LLM 評估）',
        'hybrid': '約需 4-7 分鐘（混合評估）'
    }
    estimated_time = time_estimates.get(request.quality_mode, '約需 3-5 分鐘')

    # 如果是 incremental 策略，時間會更短
    if request.test_strategy == 'incremental':
        estimated_time = '約需 2-5 分鐘（僅測試新增和失敗的案例）'
    elif request.test_strategy == 'failed_only':
        estimated_time = '約需 1-3 分鐘（僅測試失敗的案例）'

    return {
        "success": True,
        "message": f"回測已開始執行（{request.quality_mode} 模式），請稍後刷新頁面查看結果",
        "quality_mode": request.quality_mode,
        "test_strategy": request.test_strategy,
        "estimated_time": estimated_time
    }


@app.get("/api/backtest/status")
async def get_backtest_status():
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
    include_inactive: bool = Query(False, description="是否包含已停用的分類")
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

    query += " ORDER BY display_order, display_name"

    cur.execute(query)
    categories = [dict(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return {"categories": categories}


@app.post("/api/category-config")
async def create_category(category: CategoryConfig):
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
async def update_category(category_id: int, category: CategoryConfig):
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
async def delete_category(category_id: int):
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
async def sync_category_usage():
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
