"""
AI 知識生成 API 路由
處理測試情境的知識檢查和 AI 生成
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import asyncio
import json
import os
import re
from services.embedding_utils import generate_embedding_with_pgvector

router = APIRouter()


def parse_intent_from_reasoning(reasoning: str) -> Optional[int]:
    """
    從 AI 生成的 reasoning 中解析推薦意圖 ID

    Args:
        reasoning: AI 生成的推理文本

    Returns:
        Optional[int]: 推薦的意圖 ID，如果沒有推薦則返回 None
    """
    if not reasoning:
        return None

    # 嘗試匹配【推薦意圖】區塊中的意圖 ID
    pattern = r'【推薦意圖】.*?意圖 ID:\s*(\d+)'
    match = re.search(pattern, reasoning, re.DOTALL)

    if match:
        try:
            return int(match.group(1))
        except (ValueError, AttributeError):
            return None

    return None

# 懶加載 KnowledgeGenerator
_knowledge_generator = None


def get_knowledge_generator():
    """獲取知識生成器實例"""
    global _knowledge_generator
    if _knowledge_generator is None:
        from services.knowledge_generator import KnowledgeGenerator
        _knowledge_generator = KnowledgeGenerator()
    return _knowledge_generator


# 已移至 services/embedding_utils.py，統一使用共用函數


# ============================================================
# Pydantic Models
# ============================================================

class CheckKnowledgeResponse(BaseModel):
    """檢查知識回應"""
    test_scenario_id: int
    test_question: str
    has_knowledge: bool
    matched_knowledge_ids: List[int]  # 相符的知識 ID 列表
    match_count: int
    highest_similarity: Optional[float]
    related_knowledge: List[Dict]
    can_generate: bool
    category_status: str  # safe, restricted, unknown


class GenerateKnowledgeRequest(BaseModel):
    """生成知識請求"""
    num_candidates: int = Field(2, ge=1, le=3, description="生成候選數量（1-3）")


class GenerateKnowledgeResponse(BaseModel):
    """生成知識回應"""
    test_scenario_id: int
    candidates_generated: int
    candidate_ids: List[int]
    message: str


class AIKnowledgeCandidate(BaseModel):
    """AI 知識候選"""
    id: int
    test_scenario_id: int
    test_question: str
    question: str
    generated_answer: str
    edited_question: Optional[str] = None
    edited_answer: Optional[str] = None
    intent_ids: Optional[List[int]] = None
    edit_summary: Optional[str] = None
    confidence_score: float
    ai_model: str
    warnings: List[str]
    sources_needed: List[str]
    status: str
    created_at: str
    has_edits: bool


class EditCandidateRequest(BaseModel):
    """編輯候選請求"""
    edited_question: Optional[str] = None
    edited_answer: str = Field(..., description="編輯後的答案")


class ReviewCandidateRequest(BaseModel):
    """審核候選請求"""
    action: str = Field(..., description="審核動作：approve, reject, needs_revision")
    review_notes: Optional[str] = None
    use_edited: bool = Field(True, description="是否使用編輯後的版本（僅限 approve）")


# ============================================================
# API 端點
# ============================================================

@router.post("/test-scenarios/{scenario_id}/check-knowledge", response_model=CheckKnowledgeResponse)
async def check_test_scenario_knowledge(
    scenario_id: int,
    req: Request,
    similarity_threshold: float = 0.75
):
    """
    檢查測試情境是否已有對應知識

    Args:
        scenario_id: 測試情境 ID
        similarity_threshold: 相似度閾值（預設 0.75）

    Returns:
        CheckKnowledgeResponse: 檢查結果
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 1. 取得測試情境資訊
            scenario = await conn.fetchrow("""
                SELECT id, test_question, status
                FROM test_scenarios
                WHERE id = $1
            """, scenario_id)

            if not scenario:
                raise HTTPException(status_code=404, detail=f"測試情境不存在: {scenario_id}")

            # 2. 呼叫檢查函數
            result = await conn.fetchrow("""
                SELECT * FROM check_test_scenario_has_knowledge($1, $2)
            """, scenario_id, similarity_threshold)

            # 3. 知識生成狀態（移除分類限制檢查）
            generator = get_knowledge_generator()
            category_status = "allowed"
            can_generate = True

            # 4. 解析相關知識
            related_knowledge_raw = result['related_knowledge']
            if related_knowledge_raw:
                related_knowledge = json.loads(related_knowledge_raw) if isinstance(related_knowledge_raw, str) else related_knowledge_raw
            else:
                related_knowledge = []

            return CheckKnowledgeResponse(
                test_scenario_id=scenario_id,
                test_question=scenario['test_question'],
                has_knowledge=result['has_knowledge'],
                matched_knowledge_ids=list(result['matched_knowledge_ids']) if result['matched_knowledge_ids'] else [],
                match_count=result['match_count'],
                highest_similarity=float(result['highest_similarity']) if result['highest_similarity'] else None,
                related_knowledge=related_knowledge if related_knowledge else [],
                can_generate=can_generate,
                category_status=category_status
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"檢查知識失敗: {str(e)}")


@router.post("/test-scenarios/{scenario_id}/generate-knowledge", response_model=GenerateKnowledgeResponse)
async def generate_knowledge_for_scenario(
    scenario_id: int,
    request: GenerateKnowledgeRequest,
    req: Request
):
    """
    為測試情境生成 AI 知識候選

    Args:
        scenario_id: 測試情境 ID
        request: 生成請求（包含候選數量）

    Returns:
        GenerateKnowledgeResponse: 生成結果
    """
    try:
        db_pool = req.app.state.db_pool
        generator = get_knowledge_generator()

        async with db_pool.acquire() as conn:
            # 1. 取得測試情境資訊
            scenario = await conn.fetchrow("""
                SELECT id, test_question, status
                FROM test_scenarios
                WHERE id = $1
            """, scenario_id)

            if not scenario:
                raise HTTPException(status_code=404, detail=f"測試情境不存在: {scenario_id}")

            # 2. 檢查是否已有候選待審核
            existing = await conn.fetchval("""
                SELECT COUNT(*)
                FROM ai_generated_knowledge_candidates
                WHERE test_scenario_id = $1
                  AND status IN ('pending_review', 'needs_revision')
            """, scenario_id)

            if existing > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"此測試情境已有 {existing} 個待審核的知識候選，請先審核完成"
                )

            # 3. 檢查是否已標記為已請求生成（避免重複點擊）
            already_requested = await conn.fetchval("""
                SELECT knowledge_generation_requested
                FROM test_scenarios
                WHERE id = $1
            """, scenario_id)

            # 4. 取得相關知識作為參考（使用文字匹配）
            related = await conn.fetch("""
                SELECT
                    k.id,
                    k.question_summary as question,
                    k.answer,
                    0.70 as similarity  -- 預設相似度（簡化版本）
                FROM knowledge_base k
                CROSS JOIN test_scenarios ts
                WHERE ts.id = $1
                  AND k.question_summary IS NOT NULL
                  AND (
                      k.question_summary ILIKE '%' || ts.test_question || '%' OR
                      ts.test_question ILIKE '%' || k.question_summary || '%'
                  )
                ORDER BY k.updated_at DESC
                LIMIT 5
            """, scenario_id)

            context = {
                "related_knowledge": [dict(r) for r in related] if related else []
            }

            # 5. 呼叫 AI 生成
            print(f"📝 開始為測試情境 #{scenario_id} 生成知識候選...")
            print(f"   問題: {scenario['test_question']}")
            print(f"   候選數量: {request.num_candidates}")

            candidates = await generator.generate_knowledge_candidates(
                test_question=scenario['test_question'],
                intent_category=None,  # 不再使用預期分類
                num_candidates=request.num_candidates,
                context=context
            )

            # 5.5. 為問題生成 embedding（一次性生成，所有候選共用）
            print(f"🔮 為問題生成 embedding...")
            question_embedding = await generate_embedding_with_pgvector(scenario['test_question'], verbose=True)

            if question_embedding:
                print(f"✅ Embedding 已生成並轉換為 PostgreSQL vector 格式")
            else:
                print(f"⚠️ 未能生成 embedding，候選將不含向量（可能影響後續檢索）")

            # 6. 儲存候選到資料庫
            candidate_ids = []
            for candidate in candidates:
                # 解析 AI 推薦意圖
                reasoning = candidate.get('reasoning', '')
                intent_id = parse_intent_from_reasoning(reasoning)
                intent_ids = [intent_id] if intent_id else []

                candidate_id = await conn.fetchval("""
                    INSERT INTO ai_generated_knowledge_candidates (
                        test_scenario_id,
                        question,
                        question_embedding,
                        generated_answer,
                        confidence_score,
                        generation_prompt,
                        ai_model,
                        generation_reasoning,
                        suggested_sources,
                        warnings,
                        intent_ids,
                        status
                    ) VALUES ($1, $2, $3::vector, $4, $5, $6, $7, $8, $9, $10, $11, 'pending_review')
                    RETURNING id
                """,
                    scenario_id,
                    scenario['test_question'],
                    question_embedding,  # 🔧 新增：embedding 向量（已轉換為字串格式）
                    candidate['answer'],
                    candidate.get('confidence_score', 0.7),
                    None,  # generation_prompt（可選）
                    generator.model,
                    reasoning,
                    candidate.get('sources_needed', []),
                    candidate.get('warnings', []),
                    intent_ids  # 🔧 新增：從 AI 推薦意圖解析的 intent_ids
                )
                candidate_ids.append(candidate_id)

                if intent_ids:
                    print(f"   ✅ 候選 #{candidate_id} 已自動設定意圖 ID: {intent_ids}")

            # 7. 更新測試情境狀態
            await conn.execute("""
                UPDATE test_scenarios
                SET knowledge_generation_requested = TRUE,
                    knowledge_generation_requested_at = NOW()
                WHERE id = $1
            """, scenario_id)

            print(f"✅ 已生成 {len(candidates)} 個知識候選（ID: {candidate_ids}）")

            return GenerateKnowledgeResponse(
                test_scenario_id=scenario_id,
                candidates_generated=len(candidates),
                candidate_ids=candidate_ids,
                message=f"已成功生成 {len(candidates)} 個知識候選，請前往審核"
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成知識失敗: {str(e)}")


@router.get("/knowledge-candidates/stats")
async def get_generation_stats(req: Request):
    """
    取得 AI 知識生成統計資訊

    Returns:
        Dict: 統計資料（通過率、編輯率等）
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT * FROM v_ai_knowledge_generation_stats
            """)

            if not stats:
                return {
                    "pending_count": 0,
                    "needs_revision_count": 0,
                    "approved_count": 0,
                    "rejected_count": 0,
                    "avg_confidence_approved": 0.0,
                    "avg_confidence_rejected": 0.0,
                    "approved_with_edits": 0,
                    "approved_without_edits": 0,
                    "total_generated": 0,
                    "approval_rate": 0.0,
                    "edit_rate": 0.0
                }

            total = (stats['approved_count'] or 0) + (stats['rejected_count'] or 0)
            approval_rate = (stats['approved_count'] / total * 100) if total > 0 else 0.0
            edit_rate = ((stats['approved_with_edits'] or 0) / (stats['approved_count'] or 1) * 100) if stats['approved_count'] > 0 else 0.0

            return {
                "pending_count": stats['pending_count'] or 0,
                "needs_revision_count": stats['needs_revision_count'] or 0,
                "approved_count": stats['approved_count'] or 0,
                "rejected_count": stats['rejected_count'] or 0,
                "avg_confidence_approved": float(stats['avg_confidence_approved'] or 0.0),
                "avg_confidence_rejected": float(stats['avg_confidence_rejected'] or 0.0),
                "approved_with_edits": stats['approved_with_edits'] or 0,
                "approved_without_edits": stats['approved_without_edits'] or 0,
                "total_generated": total + (stats['pending_count'] or 0) + (stats['needs_revision_count'] or 0),
                "approval_rate": round(approval_rate, 2),
                "edit_rate": round(edit_rate, 2)
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗: {str(e)}")


@router.get("/knowledge-candidates")
async def get_candidates_by_status(
    req: Request,
    status: str = "pending_review",
    limit: int = 20,
    offset: int = 0
):
    """
    取得指定狀態的 AI 知識候選列表

    Args:
        status: 候選狀態 (pending_review, approved, rejected, needs_revision)
        limit: 每頁數量
        offset: 偏移量

    Returns:
        List[AIKnowledgeCandidate]: 候選列表
    """
    try:
        db_pool = req.app.state.db_pool

        # 驗證狀態參數
        valid_statuses = ['pending_review', 'approved', 'rejected', 'needs_revision']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"無效的狀態值。有效值: {', '.join(valid_statuses)}")

        async with db_pool.acquire() as conn:
            # 查詢指定狀態的候選
            rows = await conn.fetch("""
                SELECT
                    akc.id,
                    akc.test_scenario_id,
                    akc.question,
                    akc.generated_answer,
                    akc.confidence_score,
                    akc.ai_model,
                    akc.warnings,
                    akc.status,
                    akc.created_at,
                    akc.reviewed_at,
                    akc.reviewed_by,
                    akc.review_notes,
                    akc.edited_question,
                    akc.edited_answer,
                    akc.edit_summary,
                    ts.test_question as original_test_question,
                    ts.difficulty,
                    CASE
                        WHEN akc.edited_question IS NOT NULL OR akc.edited_answer IS NOT NULL
                        THEN true
                        ELSE false
                    END as has_edits
                FROM ai_generated_knowledge_candidates akc
                LEFT JOIN test_scenarios ts ON akc.test_scenario_id = ts.id
                WHERE akc.status = $1
                ORDER BY akc.created_at DESC
                LIMIT $2 OFFSET $3
            """, status, limit, offset)

            # 取得總數
            total = await conn.fetchval("""
                SELECT COUNT(*)
                FROM ai_generated_knowledge_candidates
                WHERE status = $1
            """, status)

            candidates = []
            for row in rows:
                candidates.append({
                    "id": row['id'],
                    "test_scenario_id": row['test_scenario_id'],
                    "test_question": row['original_test_question'],
                    "question": row['question'],
                    "generated_answer": row['generated_answer'],
                    "confidence_score": float(row['confidence_score']) if row['confidence_score'] else 0.0,
                    "ai_model": row['ai_model'],
                    "warnings": row['warnings'] or [],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                    "reviewed_at": row['reviewed_at'].isoformat() if row['reviewed_at'] else None,
                    "reviewed_by": row['reviewed_by'],
                    "review_notes": row['review_notes'],
                    "edited_question": row['edited_question'],
                    "edited_answer": row['edited_answer'],
                    "edit_summary": row['edit_summary'],
                    "has_edits": row['has_edits'],
                    "difficulty": row['difficulty']
                })

            return {
                "candidates": candidates,
                "total": total,
                "limit": limit,
                "offset": offset,
                "status": status
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得候選列表失敗: {str(e)}")


@router.get("/knowledge-candidates/pending")
async def get_pending_candidates(
    req: Request,
    limit: int = 20,
    offset: int = 0
):
    """
    取得待審核的 AI 知識候選列表（舊版端點，保留向後兼容）

    Args:
        limit: 每頁數量
        offset: 偏移量

    Returns:
        List[AIKnowledgeCandidate]: 候選列表
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 直接查詢表，包含編輯欄位
            # 使用 LEFT JOIN 以支援沒有 test_scenario_id 的外部匯入知識
            rows = await conn.fetch("""
                SELECT
                    kc.id AS candidate_id,
                    kc.test_scenario_id,
                    ts.test_question AS original_test_question,
                    ts.difficulty,
                    kc.question,
                    kc.generated_answer,
                    kc.edited_question,
                    kc.edited_answer,
                    kc.intent_ids,
                    kc.edit_summary,
                    kc.confidence_score,
                    kc.ai_model,
                    kc.warnings,
                    kc.status,
                    kc.created_at,
                    (kc.edited_answer IS NOT NULL) AS has_edits,
                    CASE
                        WHEN ts.source_question_id IS NOT NULL THEN (
                            SELECT frequency FROM unclear_questions WHERE id = ts.source_question_id
                        )
                        ELSE NULL
                    END AS source_question_frequency
                FROM ai_generated_knowledge_candidates kc
                LEFT JOIN test_scenarios ts ON kc.test_scenario_id = ts.id
                WHERE kc.status IN ('pending_review', 'needs_revision')
                ORDER BY kc.created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

            # 取得總數
            total = await conn.fetchval("""
                SELECT COUNT(*)
                FROM ai_generated_knowledge_candidates
                WHERE status IN ('pending_review', 'needs_revision')
            """)

            candidates = []
            for row in rows:
                candidates.append({
                    "id": row['candidate_id'],
                    "test_scenario_id": row['test_scenario_id'],
                    "test_question": row['original_test_question'],
                    "difficulty": row['difficulty'],
                    "question": row['question'],
                    "generated_answer": row['generated_answer'],
                    "edited_question": row['edited_question'],
                    "edited_answer": row['edited_answer'],
                    "intent_ids": row['intent_ids'] if row['intent_ids'] else [],
                    "edit_summary": row['edit_summary'],
                    "confidence_score": float(row['confidence_score']) if row['confidence_score'] else 0.0,
                    "ai_model": row['ai_model'],
                    "warnings": row['warnings'] or [],
                    "suggested_sources": [],  # 需要從完整記錄取得
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                    "has_edits": row['has_edits'],
                    "source_frequency": row['source_question_frequency']
                })

            return {
                "candidates": candidates,
                "total": total,
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得候選列表失敗: {str(e)}")


@router.get("/knowledge-candidates/{candidate_id}")
async def get_candidate_detail(candidate_id: int, req: Request):
    """
    取得 AI 知識候選詳情

    Args:
        candidate_id: 候選 ID

    Returns:
        Dict: 候選詳情（包含編輯記錄、審核記錄等）
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    kc.*,
                    ts.test_question as original_test_question
                FROM ai_generated_knowledge_candidates kc
                INNER JOIN test_scenarios ts ON kc.test_scenario_id = ts.id
                WHERE kc.id = $1
            """, candidate_id)

            if not row:
                raise HTTPException(status_code=404, detail=f"候選不存在: {candidate_id}")

            return {
                "id": row['id'],
                "test_scenario_id": row['test_scenario_id'],
                "test_question": row['original_test_question'],
                "question": row['question'],
                "generated_answer": row['generated_answer'],
                "confidence_score": float(row['confidence_score']) if row['confidence_score'] else 0.0,
                "ai_model": row['ai_model'],
                "generation_reasoning": row['generation_reasoning'],
                "suggested_sources": row['suggested_sources'] or [],
                "warnings": row['warnings'] or [],
                "status": row['status'],
                "reviewed_by": row['reviewed_by'],
                "reviewed_at": row['reviewed_at'].isoformat() if row['reviewed_at'] else None,
                "review_notes": row['review_notes'],
                "edited_question": row['edited_question'],
                "edited_answer": row['edited_answer'],
                "edit_summary": row['edit_summary'],
                "created_at": row['created_at'].isoformat(),
                "updated_at": row['updated_at'].isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得候選詳情失敗: {str(e)}")


@router.put("/knowledge-candidates/{candidate_id}/edit")
async def edit_candidate(
    candidate_id: int,
    request: EditCandidateRequest,
    req: Request
):
    """
    編輯 AI 知識候選

    Args:
        candidate_id: 候選 ID
        request: 編輯請求

    Returns:
        Dict: 更新後的候選
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 檢查候選是否存在且可編輯
            candidate = await conn.fetchrow("""
                SELECT id, status
                FROM ai_generated_knowledge_candidates
                WHERE id = $1
            """, candidate_id)

            if not candidate:
                raise HTTPException(status_code=404, detail=f"候選不存在: {candidate_id}")

            if candidate['status'] not in ('pending_review', 'needs_revision'):
                raise HTTPException(
                    status_code=400,
                    detail=f"只能編輯 pending_review 或 needs_revision 狀態的候選，當前狀態: {candidate['status']}"
                )

            # 更新編輯內容（包含意圖）
            await conn.execute("""
                UPDATE ai_generated_knowledge_candidates
                SET edited_question = $1,
                    edited_answer = $2,
                    updated_at = NOW()
                WHERE id = $3
            """,
                request.edited_question,
                request.edited_answer,
                candidate_id
            )

            print(f"✏️ 候選 #{candidate_id} 已編輯")

            return {
                "message": "編輯成功",
                "candidate_id": candidate_id
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"編輯候選失敗: {str(e)}")


@router.post("/knowledge-candidates/{candidate_id}/review")
async def review_candidate(
    candidate_id: int,
    request: ReviewCandidateRequest,
    req: Request,
    reviewed_by: str = "admin"
):
    """
    審核 AI 知識候選

    Args:
        candidate_id: 候選 ID
        request: 審核請求（approve/reject/needs_revision）
        reviewed_by: 審核者名稱

    Returns:
        Dict: 審核結果
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            if request.action == "approve":
                # 🔍 批准前檢查是否存在相似知識（提示但不阻止）
                candidate = await conn.fetchrow("""
                    SELECT question, question_embedding
                    FROM ai_generated_knowledge_candidates
                    WHERE id = $1
                """, candidate_id)

                similar_knowledge = None
                if candidate and candidate['question_embedding']:
                    # 檢查知識庫中是否有相似知識
                    similar = await conn.fetchrow("""
                        SELECT * FROM check_knowledge_exists_by_similarity($1::vector, $2)
                    """, candidate['question_embedding'], 0.85)

                    if similar and (similar['exists_in_knowledge_base'] or similar['exists_in_review_queue']):
                        similar_knowledge = {
                            "exists": True,
                            "source": similar['source_table'],
                            "matched_question": similar['matched_question'],
                            "similarity": float(similar['similarity_score']) if similar['similarity_score'] else 0.0
                        }
                        print(f"⚠️  警告：發現相似知識（相似度: {similar_knowledge['similarity']:.3f}）")
                        print(f"   來源: {similar_knowledge['source']}")
                        print(f"   相似問題: {similar_knowledge['matched_question'][:50]}...")

                # 批准並轉為正式知識（即使發現相似知識仍執行）
                new_knowledge_id = await conn.fetchval("""
                    SELECT approve_ai_knowledge_candidate($1, $2, $3, $4)
                """,
                    candidate_id,
                    reviewed_by,
                    request.review_notes,
                    request.use_edited
                )

                print(f"✅ 候選 #{candidate_id} 已批准")
                print(f"   新知識 ID: {new_knowledge_id}")

                result = {
                    "message": "已批准並加入知識庫",
                    "candidate_id": candidate_id,
                    "new_knowledge_id": new_knowledge_id,
                    "action": "approved"
                }

                # 如果發現相似知識，添加警告信息
                if similar_knowledge:
                    result["warning"] = {
                        "type": "similar_knowledge_exists",
                        "message": f"警告：知識庫中存在相似問題（相似度: {similar_knowledge['similarity']:.1%}）",
                        "details": similar_knowledge
                    }

                return result

            elif request.action == "reject":
                # 拒絕
                await conn.execute("""
                    UPDATE ai_generated_knowledge_candidates
                    SET status = 'rejected',
                        reviewed_by = $1,
                        reviewed_at = NOW(),
                        review_notes = $2,
                        updated_at = NOW()
                    WHERE id = $3
                """, reviewed_by, request.review_notes, candidate_id)

                print(f"❌ 候選 #{candidate_id} 已拒絕")
                print(f"   拒絕原因: {request.review_notes}")

                return {
                    "message": "已拒絕",
                    "candidate_id": candidate_id,
                    "action": "rejected"
                }

            elif request.action == "needs_revision":
                # 需要修訂
                await conn.execute("""
                    UPDATE ai_generated_knowledge_candidates
                    SET status = 'needs_revision',
                        review_notes = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, request.review_notes, candidate_id)

                print(f"⚠️ 候選 #{candidate_id} 需要修訂")
                print(f"   備註: {request.review_notes}")

                return {
                    "message": "已標記為需要修訂",
                    "candidate_id": candidate_id,
                    "action": "needs_revision"
                }

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"無效的審核動作: {request.action}（必須是 approve, reject, needs_revision）"
                )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"審核候選失敗: {str(e)}")


# ============================================================
# 迴圈生成知識審核 API（SOP 審核）
# ============================================================

class ReviewLoopKnowledgeRequest(BaseModel):
    """審核迴圈生成知識的請求模型"""
    action: str = Field(..., description="審核動作: approve, reject")
    review_notes: Optional[str] = Field(None, description="審核備註")
    reviewed_by: str = Field(..., description="審核者")
    vendor_id: Optional[int] = Field(None, description="業者 ID（僅 SOP 需要）")
    category_id: Optional[int] = Field(None, description="SOP 類別 ID（僅 SOP 需要）")
    group_id: Optional[int] = Field(None, description="SOP 群組 ID（僅 SOP 需要，選填）")


@router.get("/vendors")
async def get_vendors(req: Request):
    """
    取得業者列表
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            vendors = await conn.fetch("""
                SELECT id, name, short_name
                FROM vendors
                WHERE is_active = true
                ORDER BY id
            """)

            return {
                "vendors": [
                    {
                        "id": v['id'],
                        "name": v['name'],
                        "short_name": v['short_name']
                    }
                    for v in vendors
                ]
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得業者列表失敗: {str(e)}")


@router.get("/sop-categories")
async def get_sop_categories(req: Request, vendor_id: int = 1):
    """
    取得 SOP 類別列表
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            categories = await conn.fetch("""
                SELECT id, category_name, description, display_order
                FROM vendor_sop_categories
                WHERE vendor_id = $1 AND is_active = true
                ORDER BY display_order, id
            """, vendor_id)

            return {
                "categories": [
                    {
                        "id": cat['id'],
                        "name": cat['category_name'],
                        "description": cat['description'],
                        "display_order": cat['display_order']
                    }
                    for cat in categories
                ]
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得類別列表失敗: {str(e)}")


@router.get("/sop-groups")
async def get_sop_groups(req: Request, vendor_id: int, category_id: int):
    """
    取得 SOP 群組列表
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            groups = await conn.fetch("""
                SELECT id, group_name, description, display_order
                FROM vendor_sop_groups
                WHERE vendor_id = $1 AND category_id = $2 AND is_active = true
                ORDER BY display_order, id
            """, vendor_id, category_id)

            return {
                "groups": [
                    {
                        "id": g['id'],
                        "name": g['group_name'],
                        "description": g['description']
                    }
                    for g in groups
                ]
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得群組列表失敗: {str(e)}")


@router.get("/loop-knowledge/stats")
async def get_loop_knowledge_stats(req: Request):
    """
    取得迴圈生成知識統計資訊（包含 SOP）
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 統計各種狀態的知識數量
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
                    COUNT(*) FILTER (WHERE status = 'rejected') as rejected_count,
                    COUNT(*) FILTER (WHERE knowledge_type = 'sop' AND status = 'pending') as sop_pending_count,
                    COUNT(*) FILTER (WHERE knowledge_type = 'sop' AND status = 'approved') as sop_approved_count
                FROM loop_generated_knowledge
            """)

            return {
                "pending_count": stats['pending_count'] or 0,
                "approved_count": stats['approved_count'] or 0,
                "rejected_count": stats['rejected_count'] or 0,
                "sop_pending_count": stats['sop_pending_count'] or 0,
                "sop_approved_count": stats['sop_approved_count'] or 0,
                "total_count": (stats['pending_count'] or 0) + (stats['approved_count'] or 0) + (stats['rejected_count'] or 0)
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗: {str(e)}")


@router.get("/loop-knowledge/pending")
async def get_pending_loop_knowledge(
    req: Request,
    limit: int = 20,
    knowledge_type: Optional[str] = None,
    status: str = "pending"
):
    """
    取得迴圈生成知識列表

    Args:
        limit: 返回數量限制
        knowledge_type: 知識類型篩選（sop, general）
        status: 狀態篩選（pending, approved, rejected, synced）
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 構建查詢
            query = """
                SELECT
                    lk.id,
                    lk.loop_id,
                    lk.iteration,
                    lk.question,
                    lk.answer,
                    lk.knowledge_type,
                    lk.sop_config,
                    lk.action_type,
                    lk.keywords,
                    lk.status,
                    lk.created_at,
                    kcl.target_pass_rate,
                    kcl.started_at as loop_started_at
                FROM loop_generated_knowledge lk
                LEFT JOIN knowledge_completion_loops kcl ON lk.loop_id = kcl.id
                WHERE lk.status = $1
            """

            params = [status]

            if knowledge_type:
                query += f" AND lk.knowledge_type = ${len(params) + 1}"
                params.append(knowledge_type)

            query += " ORDER BY lk.created_at DESC"

            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)

            records = await conn.fetch(query, *params)

            items = []
            for record in records:
                item = {
                    "id": record['id'],
                    "loop_id": record['loop_id'],
                    "iteration": record['iteration'],
                    "question": record['question'],
                    "answer": record['answer'],
                    "knowledge_type": record['knowledge_type'],
                    "action_type": record['action_type'],
                    "keywords": record['keywords'],
                    "status": record['status'],
                    "created_at": record['created_at'].isoformat() if record['created_at'] else None,
                    "loop_info": {
                        "target_pass_rate": float(record['target_pass_rate']) if record['target_pass_rate'] else None,
                        "started_at": record['loop_started_at'].isoformat() if record['loop_started_at'] else None
                    }
                }

                # 如果是 SOP，添加 SOP 配置
                if record['sop_config']:
                    item['sop_config'] = record['sop_config']

                items.append(item)

            return {
                "items": items,
                "total": len(items)
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得待審核知識失敗: {str(e)}")


@router.get("/loop-knowledge/{knowledge_id}")
async def get_loop_knowledge_detail(knowledge_id: int, req: Request):
    """
    取得迴圈生成知識詳情
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            record = await conn.fetchrow("""
                SELECT
                    lk.*,
                    kcl.target_pass_rate,
                    kcl.started_at as loop_started_at,
                    kcl.status as loop_status
                FROM loop_generated_knowledge lk
                LEFT JOIN knowledge_completion_loops kcl ON lk.loop_id = kcl.id
                WHERE lk.id = $1
            """, knowledge_id)

            if not record:
                raise HTTPException(status_code=404, detail="知識不存在")

            detail = {
                "id": record['id'],
                "loop_id": record['loop_id'],
                "iteration": record['iteration'],
                "gap_analysis_id": record['gap_analysis_id'],
                "question": record['question'],
                "answer": record['answer'],
                "knowledge_type": record['knowledge_type'],
                "sop_config": record['sop_config'],
                "action_type": record['action_type'],
                "form_id": record['form_id'],
                "api_config": record['api_config'],
                "intent_id": record['intent_id'],
                "keywords": record['keywords'],
                "business_types": record['business_types'],
                "target_user": record['target_user'],
                "scope": record['scope'],
                "priority": record['priority'],
                "status": record['status'],
                "synced_to_kb": record['synced_to_kb'],
                "kb_id": record['kb_id'],
                "reviewed_by": record['reviewed_by'],
                "reviewed_at": record['reviewed_at'].isoformat() if record['reviewed_at'] else None,
                "created_at": record['created_at'].isoformat() if record['created_at'] else None,
                "loop_info": {
                    "target_pass_rate": float(record['target_pass_rate']) if record['target_pass_rate'] else None,
                    "started_at": record['loop_started_at'].isoformat() if record['loop_started_at'] else None,
                    "status": record['loop_status']
                }
            }

            return detail

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得知識詳情失敗: {str(e)}")


@router.post("/loop-knowledge/{knowledge_id}/review")
async def review_loop_knowledge(
    knowledge_id: int,
    request: ReviewLoopKnowledgeRequest,
    req: Request
):
    """
    審核迴圈生成的知識（包含 SOP）

    Args:
        knowledge_id: 知識 ID
        request: 審核請求（action, review_notes, reviewed_by）
    """
    try:
        db_pool = req.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 查詢知識詳情
            knowledge = await conn.fetchrow("""
                SELECT * FROM loop_generated_knowledge WHERE id = $1
            """, knowledge_id)

            if not knowledge:
                raise HTTPException(status_code=404, detail="知識不存在")

            if knowledge['status'] != 'pending':
                raise HTTPException(
                    status_code=400,
                    detail=f"此知識已審核過，狀態為: {knowledge['status']}"
                )

            # 確定使用的 vendor_id（如果前端有選擇就使用，否則為 None）
            vendor_id = request.vendor_id  # 可能是 None，表示不指定 vendor

            if request.action == "approve":
                # 🔧 檢查並生成缺失的 embedding
                current_embedding = knowledge['embedding']
                if current_embedding is None:
                    print(f"⚠️  知識 #{knowledge_id} 缺少 embedding，正在生成...")

                    # 生成文本：只用問題（keywords 透過獨立的關鍵字搜尋機制處理）
                    text_for_embedding = knowledge['question']

                    try:
                        # 使用共用的 embedding 生成函數
                        generated_embedding = await generate_embedding_with_pgvector(
                            text_for_embedding,
                            verbose=True
                        )

                        if generated_embedding:
                            # 更新 loop_generated_knowledge 記錄的 embedding
                            await conn.execute("""
                                UPDATE loop_generated_knowledge
                                SET embedding = $1::vector
                                WHERE id = $2
                            """, generated_embedding, knowledge_id)

                            # 更新當前使用的 embedding
                            current_embedding = generated_embedding
                            print(f"✅ 已生成並儲存 embedding 到知識 #{knowledge_id}")
                        else:
                            print(f"❌ 無法生成 embedding，審核將繼續但向量為空")
                    except Exception as e:
                        print(f"❌ 生成 embedding 時發生錯誤: {e}")
                        import traceback
                        traceback.print_exc()
                        print(f"⚠️  審核將繼續但向量為空")
                else:
                    print(f"✓ 知識 #{knowledge_id} 已有 embedding，無需生成")

                # 通過審核
                async with conn.transaction():
                    # 更新狀態為 approved
                    await conn.execute("""
                        UPDATE loop_generated_knowledge
                        SET status = 'approved',
                            reviewed_by = $1,
                            reviewed_at = NOW()
                        WHERE id = $2
                    """, request.reviewed_by, knowledge_id)

                    # 如果是 SOP，需要同步到 vendor_sop_items
                    if knowledge['knowledge_type'] == 'sop' and knowledge['sop_config']:
                        # 解析 sop_config（可能是 dict 或 JSON 字串）
                        sop_config = knowledge['sop_config']
                        if isinstance(sop_config, str):
                            import json
                            sop_config = json.loads(sop_config)
                        elif not isinstance(sop_config, dict):
                            sop_config = dict(sop_config) if sop_config else {}

                        # 映射 trigger_mode 到資料庫允許的值
                        trigger_mode_raw = sop_config.get('trigger_mode', 'keyword')
                        trigger_mode_map = {
                            'keyword': 'auto',  # keyword 觸發映射為 auto
                            'none': 'none',
                            'manual': 'manual',
                            'immediate': 'immediate',
                            'auto': 'auto'
                        }
                        trigger_mode = trigger_mode_map.get(trigger_mode_raw, 'auto')

                        # SOP 必須指定 vendor_id
                        sop_vendor_id = request.vendor_id or vendor_id
                        if not sop_vendor_id:
                            raise HTTPException(
                                status_code=400,
                                detail="SOP 必須指定 vendor_id"
                            )

                        # 插入 SOP 到 vendor_sop_items（不帶 embedding，由 sop_embedding_generator 統一生成）
                        sop_id = await conn.fetchval("""
                            INSERT INTO vendor_sop_items (
                                vendor_id,
                                category_id,
                                group_id,
                                item_name,
                                content,
                                trigger_mode,
                                trigger_keywords,
                                keywords,
                                next_action,
                                next_form_id,
                                immediate_prompt,
                                is_active,
                                created_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, true, NOW())
                            RETURNING id
                        """,
                            sop_vendor_id,
                            request.category_id,
                            request.group_id,
                            sop_config.get('item_name'),
                            knowledge['answer'],
                            trigger_mode,
                            knowledge.get('keywords', []),
                            knowledge.get('keywords', []),
                            sop_config.get('next_action', 'none'),
                            sop_config.get('next_form_id'),
                            sop_config.get('immediate_prompt')
                        )

                        # 統一使用 sop_embedding_generator 生成 embedding
                        from services.sop_embedding_generator import generate_sop_embeddings_async
                        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')
                        asyncio.create_task(generate_sop_embeddings_async(db_pool_async, sop_id))

                        # 更新 synced_to_kb 標記（這裡 kb_id 用來存 sop_id）
                        await conn.execute("""
                            UPDATE loop_generated_knowledge
                            SET synced_to_kb = true,
                                kb_id = $1,
                                synced_at = NOW()
                            WHERE id = $2
                        """, sop_id, knowledge_id)

                        print(f"✅ 知識 #{knowledge_id} 已通過審核並同步為 SOP #{sop_id}")

                    # 如果是一般知識，同步到 knowledge_base
                    elif knowledge['knowledge_type'] != 'sop':
                        # vendor_ids: 如果有選擇 vendor 則使用陣列，否則為 null
                        vendor_ids_value = [vendor_id] if vendor_id is not None else None

                        kb_id = await conn.fetchval("""
                            INSERT INTO knowledge_base (
                                question_summary,
                                answer,
                                action_type,
                                form_id,
                                keywords,
                                embedding,
                                vendor_ids,
                                is_active,
                                created_at,
                                source,
                                source_loop_knowledge_id,
                                source_loop_id
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, true, NOW(), 'loop', $8, $9)
                            RETURNING id
                        """,
                            knowledge['question'],
                            knowledge['answer'],
                            knowledge['action_type'],
                            knowledge['form_id'],
                            knowledge['keywords'],
                            current_embedding,  # 🔧 使用檢查後的 embedding（可能是新生成的）
                            vendor_ids_value,  # 可能是 [vendor_id] 或 None
                            knowledge_id,
                            knowledge['loop_id']
                        )

                        await conn.execute("""
                            UPDATE loop_generated_knowledge
                            SET synced_to_kb = true,
                                kb_id = $1,
                                synced_at = NOW()
                            WHERE id = $2
                        """, kb_id, knowledge_id)

                        print(f"✅ 知識 #{knowledge_id} 已通過審核並同步到知識庫 #{kb_id}")

                return {
                    "message": "已通過審核並同步",
                    "knowledge_id": knowledge_id,
                    "action": "approved",
                    "synced": True
                }

            elif request.action == "reject":
                # 拒絕審核
                await conn.execute("""
                    UPDATE loop_generated_knowledge
                    SET status = 'rejected',
                        reviewed_by = $1,
                        reviewed_at = NOW(),
                        rollback_reason = $2
                    WHERE id = $3
                """, request.reviewed_by, request.review_notes, knowledge_id)

                print(f"❌ 知識 #{knowledge_id} 已拒絕")
                print(f"   拒絕原因: {request.review_notes}")

                return {
                    "message": "已拒絕",
                    "knowledge_id": knowledge_id,
                    "action": "rejected"
                }

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"無效的審核動作: {request.action}（必須是 approve, reject）"
                )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"審核失敗: {str(e)}")
