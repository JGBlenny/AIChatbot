"""
測試題庫管理 API 路由
提供測試情境的 CRUD 操作
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

router = APIRouter(prefix="/api/test", tags=["Test Scenarios"])

# 資料庫配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")


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

class TestScenarioCreate(BaseModel):
    """測試情境創建模型"""
    test_question: str = Field(..., min_length=1)
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")
    tags: List[str] = []
    priority: int = Field(50, description="優先級：30=低, 50=中, 80=高")
    expected_min_confidence: float = Field(0.6, ge=0.0, le=1.0)
    notes: Optional[str] = None
    test_purpose: Optional[str] = None
    expected_answer: Optional[str] = Field(None, description="標準答案（可選）用於 LLM 語義對比")
    min_quality_score: float = Field(3.0, ge=1.0, le=5.0, description="最低質量要求（1-5分）")

    @validator('priority')
    def validate_priority(cls, v):
        if v not in [30, 50, 80]:
            raise ValueError('priority 必須是 30（低）、50（中）或 80（高）')
        return v


class TestScenarioUpdate(BaseModel):
    """測試情境更新模型"""
    test_question: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    tags: Optional[List[str]] = None
    priority: Optional[int] = None
    expected_min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None
    test_purpose: Optional[str] = None
    is_active: Optional[bool] = None
    expected_answer: Optional[str] = None
    min_quality_score: Optional[float] = Field(None, ge=1.0, le=5.0)

    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and v not in [30, 50, 80]:
            raise ValueError('priority 必須是 30（低）、50（中）或 80（高）')
        return v


class TestScenarioReview(BaseModel):
    """測試情境審核模型"""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None


class UnclearQuestionConvert(BaseModel):
    """用戶問題轉換模型"""
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")


# ========== API 端點 ==========

# ---------- 測試情境管理 ----------

# ---------- 審核流程（需要放在 scenarios/{id} 之前）----------

@router.get("/scenarios/pending")
async def list_pending_scenarios():
    """列出待審核測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM v_pending_test_scenarios")
        scenarios = []

        for row in cur.fetchall():
            item = dict(row)
            # 轉換日期格式
            for date_field in ['created_at', 'first_asked_at']:
                if item.get(date_field):
                    item[date_field] = item[date_field].isoformat()
            scenarios.append(item)

        return {"scenarios": scenarios}

    finally:
        cur.close()
        conn.close()


@router.get("/scenarios")
async def list_test_scenarios(
    status: Optional[str] = Query(None, description="篩選狀態"),
    last_result: Optional[str] = Query(None, description="篩選測試結果：passed, failed, not_tested"),
    is_active: Optional[bool] = Query(None, description="篩選活躍狀態"),
    search: Optional[str] = Query(None, description="搜尋問題文字"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """列出測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                ts.id, ts.test_question, ts.difficulty,
                ts.tags, ts.priority, ts.status, ts.source, ts.is_active,
                ts.total_runs, ts.pass_count, ts.fail_count, ts.avg_score,
                ts.last_run_at, ts.last_result, ts.created_at,
                ts.has_knowledge, ts.linked_knowledge_ids,
                ts.notes, ts.expected_answer, ts.min_quality_score
            FROM test_scenarios ts
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND ts.status = %s"
            params.append(status)

        if last_result:
            if last_result == "not_tested":
                query += " AND ts.last_result IS NULL"
            else:
                query += " AND ts.last_result = %s"
                params.append(last_result)

        if is_active is not None:
            query += " AND ts.is_active = %s"
            params.append(is_active)

        if search:
            query += " AND ts.test_question ILIKE %s"
            params.append(f"%{search}%")

        query += """
            ORDER BY ts.priority DESC, ts.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        cur.execute(query, params)
        scenarios = []

        for row in cur.fetchall():
            item = dict(row)
            # 轉換日期格式
            for date_field in ['last_run_at', 'created_at']:
                if item.get(date_field):
                    item[date_field] = item[date_field].isoformat()

            scenarios.append(item)

        # 計算總數
        count_query = "SELECT COUNT(*) FROM test_scenarios ts WHERE 1=1"
        count_params = []

        if status:
            count_query += " AND ts.status = %s"
            count_params.append(status)
        if last_result:
            if last_result == "not_tested":
                count_query += " AND ts.last_result IS NULL"
            else:
                count_query += " AND ts.last_result = %s"
                count_params.append(last_result)
        if is_active is not None:
            count_query += " AND ts.is_active = %s"
            count_params.append(is_active)
        if search:
            count_query += " AND ts.test_question ILIKE %s"
            count_params.append(f"%{search}%")

        cur.execute(count_query, count_params)
        total = cur.fetchone()['count']

        return {
            "scenarios": scenarios,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()


@router.get("/scenarios/{scenario_id}")
async def get_test_scenario(scenario_id: int):
    """獲取測試情境詳情"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT ts.*
            FROM test_scenarios ts
            WHERE ts.id = %s
        """, (scenario_id,))

        scenario = cur.fetchone()

        if not scenario:
            raise HTTPException(status_code=404, detail="測試情境不存在")

        result = dict(scenario)

        # 轉換日期格式
        for date_field in ['created_at', 'updated_at', 'reviewed_at', 'last_run_at']:
            if result.get(date_field):
                result[date_field] = result[date_field].isoformat()

        return result

    finally:
        cur.close()
        conn.close()


@router.get("/scenarios/{scenario_id}/results")
async def get_scenario_test_results(scenario_id: int, limit: int = 20):
    """獲取測試情境的測試結果歷史"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查測試情境是否存在
        cur.execute("SELECT id FROM test_scenarios WHERE id = %s", (scenario_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="測試情境不存在")

        # 獲取測試結果（按時間倒序）
        cur.execute("""
            SELECT
                id,
                run_id,
                test_question,
                actual_intent,
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
                source_count,
                knowledge_sources,
                tested_at
            FROM backtest_results
            WHERE scenario_id = %s
            ORDER BY tested_at DESC
            LIMIT %s
        """, (scenario_id, limit))

        results = cur.fetchall()

        # 轉換為字典列表
        result_list = []
        for row in results:
            result_dict = dict(row)
            # 轉換時間格式
            if result_dict.get('tested_at'):
                result_dict['tested_at'] = result_dict['tested_at'].isoformat()
            result_list.append(result_dict)

        # 查詢該測試情境的知識候選狀態
        cur.execute("""
            SELECT
                id,
                status,
                created_at,
                reviewed_at
            FROM ai_generated_knowledge_candidates
            WHERE test_scenario_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (scenario_id,))

        knowledge_candidate = cur.fetchone()
        knowledge_status = None

        if knowledge_candidate:
            knowledge_status = {
                "candidate_id": knowledge_candidate['id'],
                "status": knowledge_candidate['status'],
                "created_at": knowledge_candidate['created_at'].isoformat() if knowledge_candidate['created_at'] else None,
                "reviewed_at": knowledge_candidate['reviewed_at'].isoformat() if knowledge_candidate['reviewed_at'] else None
            }

            # 如果已批准，查找對應的正式知識
            if knowledge_candidate['status'] == 'approved':
                cur.execute("""
                    SELECT id
                    FROM knowledge_base
                    WHERE question_summary = (
                        SELECT COALESCE(edited_question, question)
                        FROM ai_generated_knowledge_candidates
                        WHERE id = %s
                    )
                    LIMIT 1
                """, (knowledge_candidate['id'],))

                approved_knowledge = cur.fetchone()
                if approved_knowledge:
                    knowledge_status["knowledge_id"] = approved_knowledge['id']

        return {
            "results": result_list,
            "total": len(result_list),
            "knowledge_status": knowledge_status
        }

    finally:
        cur.close()
        conn.close()


@router.post("/scenarios")
async def create_test_scenario(data: TestScenarioCreate):
    """創建新測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 插入測試情境
        cur.execute("""
            INSERT INTO test_scenarios (
                test_question, difficulty, tags, priority,
                expected_min_confidence, notes, test_purpose,
                expected_answer, min_quality_score,
                status, source, created_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'approved', 'manual', 'api'
            )
            RETURNING id, created_at
        """, (
            data.test_question,
            data.difficulty,
            data.tags if data.tags else None,
            data.priority,
            data.expected_min_confidence,
            data.notes,
            data.test_purpose,
            data.expected_answer,
            data.min_quality_score
        ))

        result = cur.fetchone()
        scenario_id = result['id']

        conn.commit()

        return {
            "success": True,
            "message": "測試情境已創建",
            "id": scenario_id,
            "created_at": result['created_at'].isoformat()
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"創建失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.put("/scenarios/{scenario_id}")
async def update_test_scenario(scenario_id: int, data: TestScenarioUpdate):
    """更新測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 構建動態更新查詢
        update_fields = []
        params = []

        if data.test_question is not None:
            update_fields.append("test_question = %s")
            params.append(data.test_question)

        if data.difficulty is not None:
            update_fields.append("difficulty = %s")
            params.append(data.difficulty)

        if data.tags is not None:
            update_fields.append("tags = %s")
            params.append(data.tags if data.tags else None)

        if data.priority is not None:
            update_fields.append("priority = %s")
            params.append(data.priority)

        if data.expected_min_confidence is not None:
            update_fields.append("expected_min_confidence = %s")
            params.append(data.expected_min_confidence)

        if data.notes is not None:
            update_fields.append("notes = %s")
            params.append(data.notes)

        if data.test_purpose is not None:
            update_fields.append("test_purpose = %s")
            params.append(data.test_purpose)

        if data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(data.is_active)

        if data.expected_answer is not None:
            update_fields.append("expected_answer = %s")
            params.append(data.expected_answer)

        if data.min_quality_score is not None:
            update_fields.append("min_quality_score = %s")
            params.append(data.min_quality_score)

        if not update_fields:
            raise HTTPException(status_code=400, detail="沒有提供要更新的欄位")

        update_fields.append("updated_at = NOW()")
        params.append(scenario_id)

        query = f"""
            UPDATE test_scenarios
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, updated_at
        """

        cur.execute(query, params)
        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="測試情境不存在")

        conn.commit()

        return {
            "success": True,
            "message": "測試情境已更新",
            "id": result['id'],
            "updated_at": result['updated_at'].isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.delete("/scenarios/{scenario_id}")
async def delete_test_scenario(scenario_id: int):
    """刪除測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM test_scenarios
            WHERE id = %s
            RETURNING id
        """, (scenario_id,))

        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="測試情境不存在")

        conn.commit()

        return {
            "success": True,
            "message": "測試情境已刪除",
            "id": result['id']
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/scenarios/{scenario_id}/review")
async def review_test_scenario(scenario_id: int, data: TestScenarioReview):
    """審核測試情境（批准或拒絕）"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 直接更新狀態，不使用 SQL 函數（因為它依賴集合參數）
        new_status = 'approved' if data.action == 'approve' else 'rejected'

        cur.execute("""
            UPDATE test_scenarios
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = NOW(),
                review_notes = %s
            WHERE id = %s
            RETURNING id
        """, (
            new_status,
            'api_user',
            data.notes,
            scenario_id
        ))

        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="測試情境不存在")

        conn.commit()

        action_text = "已批准" if data.action == "approve" else "已拒絕"

        return {
            "success": True,
            "message": f"測試情境{action_text}",
            "scenario_id": scenario_id,
            "action": data.action
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"審核失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ---------- 用戶問題轉測試情境 ----------

@router.get("/unclear-questions/candidates")
async def list_unclear_question_candidates():
    """列出可轉為測試情境的用戶問題"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM v_unclear_question_candidates")
        candidates = []

        for row in cur.fetchall():
            item = dict(row)
            # 轉換日期格式
            for date_field in ['first_asked_at', 'last_asked_at']:
                if item.get(date_field):
                    item[date_field] = item[date_field].isoformat()
            candidates.append(item)

        return {"candidates": candidates}

    finally:
        cur.close()
        conn.close()


@router.post("/unclear-questions/{question_id}/convert")
async def convert_unclear_question_to_scenario(
    question_id: int,
    data: UnclearQuestionConvert
):
    """將用戶問題轉為測試情境"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT create_test_scenario_from_unclear_question(%s, %s, %s)
        """, (
            question_id,
            data.difficulty,
            'api_user'
        ))

        scenario_id = cur.fetchone()[0]
        conn.commit()

        return {
            "success": True,
            "message": "已創建測試情境（待審核）",
            "scenario_id": scenario_id,
            "source_question_id": question_id
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"轉換失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ---------- 統計資訊 ----------

@router.get("/stats")
async def get_test_statistics():
    """獲取測試題庫統計資訊"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 總測試情境數
        cur.execute("SELECT COUNT(*) as total FROM test_scenarios")
        total = cur.fetchone()['total']

        # 按狀態統計
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM test_scenarios
            GROUP BY status
        """)
        by_status = [dict(row) for row in cur.fetchall()]

        # 按難度統計
        cur.execute("""
            SELECT difficulty, COUNT(*) as count
            FROM test_scenarios
            GROUP BY difficulty
            ORDER BY
                CASE difficulty
                    WHEN 'easy' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'hard' THEN 3
                END
        """)
        by_difficulty = [dict(row) for row in cur.fetchall()]

        # 待審核數量
        cur.execute("""
            SELECT COUNT(*) as count
            FROM test_scenarios
            WHERE status = 'pending_review'
        """)
        pending_count = cur.fetchone()['count']

        # 通過率統計
        cur.execute("""
            SELECT
                SUM(total_runs) as total_runs,
                SUM(pass_count) as total_passes,
                CASE
                    WHEN SUM(total_runs) > 0
                    THEN ROUND((SUM(pass_count)::numeric / SUM(total_runs)::numeric * 100), 2)
                    ELSE 0
                END as overall_pass_rate
            FROM test_scenarios
            WHERE total_runs > 0
        """)
        run_stats = dict(cur.fetchone())

        return {
            "total_scenarios": total,
            "by_status": by_status,
            "by_difficulty": by_difficulty,
            "pending_review_count": pending_count,
            "run_statistics": run_stats
        }

    finally:
        cur.close()
        conn.close()
