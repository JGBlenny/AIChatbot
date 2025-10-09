"""
聊天 API 路由
處理使用者問題，整合意圖分類、RAG 檢索和信心度評估
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import time

router = APIRouter()


class ChatRequest(BaseModel):
    """聊天請求"""
    question: str = Field(..., min_length=1, max_length=1000, description="使用者問題")
    user_id: Optional[str] = Field(None, description="使用者 ID")
    context: Optional[Dict] = Field(None, description="對話上下文")


class ChatResponse(BaseModel):
    """聊天回應"""
    conversation_id: Optional[str] = None
    question: str
    answer: str
    confidence_score: float
    confidence_level: str
    intent: Dict
    retrieved_docs: List[Dict]
    processing_time_ms: int
    requires_human: bool
    unclear_question_id: Optional[int] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """
    處理使用者問題

    流程：
    1. 意圖分類
    2. RAG 檢索（如果是知識查詢類）
    3. 信心度評估
    4. 根據信心度決定回應策略
    5. 記錄對話
    """
    start_time = time.time()

    try:
        # 取得服務實例
        intent_classifier = req.app.state.intent_classifier
        rag_engine = req.app.state.rag_engine
        confidence_evaluator = req.app.state.confidence_evaluator
        unclear_manager = req.app.state.unclear_question_manager

        # 1. 意圖分類
        intent_result = intent_classifier.classify(request.question)

        # 2. RAG 檢索（僅對知識查詢類進行檢索）
        search_results = []
        if intent_result['intent_type'] in ['knowledge', 'hybrid']:
            search_results = await rag_engine.search(
                query=request.question,
                limit=5,
                similarity_threshold=0.65
            )

        # 3. 信心度評估
        evaluation = confidence_evaluator.evaluate(
            search_results=search_results,
            question_keywords=intent_result['keywords']
        )

        # 4. 決定回應策略
        answer = ""
        requires_human = False
        unclear_question_id = None

        if evaluation['decision'] == 'direct_answer' and search_results:
            # 高信心度：直接使用檢索結果
            best_result = search_results[0]
            answer = f"{best_result['title']}\n\n{best_result['content']}"

        elif evaluation['decision'] == 'needs_enhancement' and search_results:
            # 中等信心度：提示需要優化（Phase 3 實作）
            best_result = search_results[0]
            answer = f"根據我們的知識庫，{best_result['content']}\n\n（註：此答案信心度為中等，建議進一步確認）"

        elif evaluation['decision'] == 'unclear':
            # 低信心度：記錄未釐清問題
            unclear_question_id = await unclear_manager.record_unclear_question(
                question=request.question,
                user_id=request.user_id,
                intent_type=intent_result['intent_type'],
                similarity_score=evaluation['confidence_score'],
                retrieved_docs={"results": search_results} if search_results else None
            )

            answer = (
                "抱歉，我對這個問題不太確定如何回答。\n\n"
                "您的問題已經記錄下來，我們會盡快處理。\n"
                "如需立即協助，請聯繫客服人員。"
            )
            requires_human = True

        # 5. 記錄對話到資料庫
        processing_time = int((time.time() - start_time) * 1000)

        async with req.app.state.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO conversation_logs (
                    user_id,
                    question,
                    intent_type,
                    sub_category,
                    keywords,
                    retrieved_docs,
                    similarity_scores,
                    confidence_score,
                    final_answer,
                    answer_source,
                    processing_time_ms,
                    escalated_to_human
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                request.user_id,
                request.question,
                intent_result['intent_type'],
                intent_result.get('sub_category'),
                intent_result['keywords'],
                {"results": [{"id": r['id'], "title": r['title']} for r in search_results]},
                [r['similarity'] for r in search_results],
                evaluation['confidence_score'],
                answer,
                evaluation['decision'],
                processing_time,
                requires_human
            )

        # 6. 返回回應
        return ChatResponse(
            question=request.question,
            answer=answer,
            confidence_score=evaluation['confidence_score'],
            confidence_level=evaluation['confidence_level'],
            intent=intent_result,
            retrieved_docs=search_results,
            processing_time_ms=processing_time,
            requires_human=requires_human,
            unclear_question_id=unclear_question_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"處理問題時發生錯誤: {str(e)}"
        )


@router.get("/conversations")
async def get_conversations(
    req: Request,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    intent_type: Optional[str] = None
):
    """
    取得對話記錄列表
    """
    try:
        async with req.app.state.db_pool.acquire() as conn:
            query = """
                SELECT
                    id,
                    user_id,
                    question,
                    intent_type,
                    confidence_score,
                    final_answer,
                    user_rating,
                    escalated_to_human,
                    created_at
                FROM conversation_logs
                WHERE ($1::text IS NULL OR user_id = $1)
                  AND ($2::text IS NULL OR intent_type = $2)
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """

            results = await conn.fetch(query, user_id, intent_type, limit, offset)

        return {
            "conversations": [dict(row) for row in results],
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得對話記錄失敗: {str(e)}"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, req: Request):
    """
    取得特定對話的詳細資訊
    """
    try:
        async with req.app.state.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT *
                FROM conversation_logs
                WHERE id = $1
            """, conversation_id)

            if not row:
                raise HTTPException(status_code=404, detail="對話記錄不存在")

            return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得對話詳情失敗: {str(e)}"
        )


class FeedbackRequest(BaseModel):
    """反饋請求"""
    rating: int = Field(..., ge=1, le=5, description="評分 1-5")
    feedback: Optional[str] = Field(None, max_length=1000, description="反饋內容")


@router.post("/conversations/{conversation_id}/feedback")
async def submit_feedback(
    conversation_id: int,
    feedback: FeedbackRequest,
    req: Request
):
    """
    提交對話反饋
    """
    try:
        async with req.app.state.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE conversation_logs
                SET user_rating = $1,
                    user_feedback = $2
                WHERE id = $3
            """, feedback.rating, feedback.feedback, conversation_id)

            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="對話記錄不存在")

            return {
                "message": "反饋提交成功",
                "conversation_id": conversation_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"提交反饋失敗: {str(e)}"
        )
