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
        # 建立查詢（加入意圖資訊）
        query = """
            SELECT
                kb.id, kb.title, kb.category, kb.audience, kb.answer as content,
                kb.keywords, kb.question_summary, kb.created_at, kb.updated_at,
                kb.intent_id, i.name as intent_name
            FROM knowledge_base kb
            LEFT JOIN intents i ON kb.intent_id = i.id
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

            result = {
                'test_id': int(row['test_id']),
                'test_question': row['test_question'],
                'expected_category': row['expected_category'],
                'actual_intent': actual_intent,
                'system_answer': system_answer,
                'confidence': float(row['confidence']),
                'score': float(row['score']),
                'passed': bool(row['passed']),
                'optimization_tips': optimization_tips,
                'difficulty': row.get('difficulty', 'medium'),
                'timestamp': row['timestamp']
            }
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

        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "statistics": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": round(pass_rate, 2),
                "avg_score": round(avg_score, 3),
                "avg_confidence": round(avg_confidence, 3)
            }
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


@app.post("/api/backtest/run")
async def run_backtest():
    """
    執行回測腳本

    這會在後台執行回測腳本並返回任務ID
    """
    import subprocess
    import threading

    # 檢查 smoke test scenarios 是否存在
    # 使用環境變數或相對於專案根目錄的路徑
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    test_scenarios_path = os.path.join(project_root, "test_scenarios_smoke.xlsx")

    if not os.path.exists(test_scenarios_path):
        raise HTTPException(
            status_code=404,
            detail=f"測試場景文件不存在: {test_scenarios_path}。請確認檔案已建立。"
        )

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
            env["BACKTEST_TYPE"] = "smoke"  # 預設使用 smoke tests
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

    return {
        "success": True,
        "message": "回測已開始執行，請稍後刷新頁面查看結果",
        "estimated_time": "約需 3-5 分鐘"
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


if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動知識庫管理 API...")
    print(f"📊 API 文件: http://localhost:8000/docs")
    print(f"💾 資料庫: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
