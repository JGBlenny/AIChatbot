"""
聊天 API 路由
處理使用者問題，整合意圖分類、RAG 檢索和信心度評估

Phase 1: 新增多業者支援（Multi-Vendor Chat API）
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import time
import json
import os
import psycopg2
import psycopg2.extras

router = APIRouter()

# Phase 1: 多業者服務實例（懶加載）
_vendor_knowledge_retriever = None
_vendor_param_resolver = None


def get_vendor_knowledge_retriever():
    """獲取業者知識檢索器"""
    global _vendor_knowledge_retriever
    if _vendor_knowledge_retriever is None:
        from services.vendor_knowledge_retriever import VendorKnowledgeRetriever
        _vendor_knowledge_retriever = VendorKnowledgeRetriever()
    return _vendor_knowledge_retriever


def get_vendor_param_resolver():
    """獲取業者參數解析器"""
    global _vendor_param_resolver
    if _vendor_param_resolver is None:
        from services.vendor_parameter_resolver import VendorParameterResolver
        _vendor_param_resolver = VendorParameterResolver()
    return _vendor_param_resolver


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
    is_new_intent_suggested: bool = False
    suggested_intent_id: Optional[int] = None


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
        llm_optimizer = req.app.state.llm_answer_optimizer
        suggestion_engine = req.app.state.suggestion_engine

        # 1. 意圖分類
        intent_result = intent_classifier.classify(request.question)

        # 2. RAG 檢索（對所有問題都嘗試檢索，包括 unclear）
        # 即使意圖不明確，也可能在知識庫中找到相關答案
        search_results = []

        # 對於 unclear 意圖，降低相似度閾值，以增加檢索機會
        similarity_threshold = 0.55 if intent_result['intent_type'] == 'unclear' else 0.65

        search_results = await rag_engine.search(
            query=request.question,
            limit=5,
            similarity_threshold=similarity_threshold
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
        optimization_result = None
        is_new_intent_suggested = False
        suggested_intent_id = None

        if evaluation['decision'] == 'direct_answer' and search_results:
            # 高信心度：使用 LLM 優化答案 (Phase 3)
            optimization_result = llm_optimizer.optimize_answer(
                question=request.question,
                search_results=search_results,
                confidence_level=evaluation['confidence_level'],
                intent_info=intent_result
            )
            answer = optimization_result['optimized_answer']

        elif evaluation['decision'] == 'needs_enhancement' and search_results:
            # 中等信心度：使用 LLM 優化答案，但仍建議確認並記錄以便改善
            # 記錄為待改善問題
            unclear_question_id = await unclear_manager.record_unclear_question(
                question=request.question,
                user_id=request.user_id,
                intent_type=intent_result['intent_type'],
                similarity_score=evaluation['confidence_score'],
                retrieved_docs={"results": search_results} if search_results else None
            )

            # 使用 LLM 優化答案 (Phase 3)
            optimization_result = llm_optimizer.optimize_answer(
                question=request.question,
                search_results=search_results,
                confidence_level=evaluation['confidence_level'],
                intent_info=intent_result
            )

            # 在優化後的答案後附加警告訊息
            answer = (
                f"{optimization_result['optimized_answer']}\n\n"
                f"⚠️ 注意：此答案信心度為中等（{evaluation['confidence_score']:.2f}），建議您聯繫客服人員進一步確認。\n"
                f"您的問題已記錄，我們會持續改善答案品質。"
            )
            requires_human = True

        elif evaluation['decision'] == 'unclear':
            # 低信心度：記錄未釐清問題
            unclear_question_id = await unclear_manager.record_unclear_question(
                question=request.question,
                user_id=request.user_id,
                intent_type=intent_result['intent_type'],
                similarity_score=evaluation['confidence_score'],
                retrieved_docs={"results": search_results} if search_results else None
            )

            # Phase B: 使用 OpenAI 分析是否為業務範圍內的新意圖
            if intent_result['intent_name'] == 'unclear' or intent_result['intent_type'] == 'unclear':
                # 取得對話上下文（如果有）
                context_text = None
                if request.context:
                    context_text = json.dumps(request.context, ensure_ascii=False)

                # 分析問題
                analysis = suggestion_engine.analyze_unclear_question(
                    question=request.question,
                    user_id=request.user_id,
                    conversation_context=context_text
                )

                # 如果屬於業務範圍，記錄建議意圖
                if analysis.get('should_record'):
                    suggested_intent_id = suggestion_engine.record_suggestion(
                        question=request.question,
                        analysis=analysis,
                        user_id=request.user_id
                    )
                    if suggested_intent_id:
                        is_new_intent_suggested = True
                        print(f"✅ 發現新意圖建議: {analysis['suggested_intent']['name']} (建議ID: {suggested_intent_id})")

            answer = (
                "抱歉，我對這個問題不太確定如何回答。\n\n"
                "您的問題已經記錄下來，我們會盡快處理。\n"
                "如需立即協助，請聯繫客服人員。"
            )
            requires_human = True

        # 5. 記錄對話到資料庫
        processing_time = int((time.time() - start_time) * 1000)

        # 準備 JSON 欄位
        retrieved_docs_json = json.dumps(
            {"results": [{"id": r['id'], "title": r['title']} for r in search_results]}
        )

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
                    escalated_to_human,
                    suggested_intent_id,
                    is_new_intent_suggested
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                request.user_id,
                request.question,
                intent_result['intent_type'],
                intent_result.get('sub_category'),
                intent_result['keywords'],
                retrieved_docs_json,
                [r['similarity'] for r in search_results],
                evaluation['confidence_score'],
                answer,
                evaluation['decision'],
                processing_time,
                requires_human,
                suggested_intent_id,
                is_new_intent_suggested
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
            unclear_question_id=unclear_question_id,
            is_new_intent_suggested=is_new_intent_suggested,
            suggested_intent_id=suggested_intent_id
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


# ========================================
# Phase 1: 多業者聊天 API
# ========================================

class VendorChatRequest(BaseModel):
    """多業者聊天請求"""
    message: str = Field(..., description="使用者訊息", min_length=1, max_length=2000)
    vendor_id: int = Field(..., description="業者 ID", ge=1)
    mode: str = Field("tenant", description="模式：tenant (B2C) 或 customer_service (B2B)")
    session_id: Optional[str] = Field(None, description="會話 ID（用於追蹤）")
    user_id: Optional[str] = Field(None, description="使用者 ID（租客 ID 或客服 ID）")
    top_k: int = Field(3, description="返回知識數量", ge=1, le=10)
    include_sources: bool = Field(True, description="是否包含知識來源")


class KnowledgeSource(BaseModel):
    """知識來源"""
    id: int
    question_summary: str
    answer: str
    scope: str
    is_template: bool


class VendorChatResponse(BaseModel):
    """多業者聊天回應"""
    answer: str = Field(..., description="回答內容")
    intent_name: Optional[str] = Field(None, description="意圖名稱")
    intent_type: Optional[str] = Field(None, description="意圖類型")
    confidence: Optional[float] = Field(None, description="分類信心度")
    all_intents: Optional[List[str]] = Field(None, description="所有相關意圖名稱（主要 + 次要）")
    secondary_intents: Optional[List[str]] = Field(None, description="次要相關意圖")
    intent_ids: Optional[List[int]] = Field(None, description="所有意圖 IDs")
    sources: Optional[List[KnowledgeSource]] = Field(None, description="知識來源列表")
    source_count: int = Field(0, description="知識來源數量")
    vendor_id: int
    mode: str
    session_id: Optional[str] = None
    timestamp: str


@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    """
    多業者通用聊天端點（Phase 1: B2C 模式）

    流程：
    1. 驗證業者
    2. 意圖分類
    3. 根據意圖 + 業者 ID → 檢索知識
    4. 模板變數替換
    5. 返回答案

    Phase 2 將支援 customer_service 模式（需要租客辨識 + 外部 API）
    """
    try:
        # 驗證業者
        resolver = get_vendor_param_resolver()
        vendor_info = resolver.get_vendor_info(request.vendor_id)

        if not vendor_info:
            raise HTTPException(
                status_code=404,
                detail=f"業者不存在: {request.vendor_id}"
            )

        if not vendor_info['is_active']:
            raise HTTPException(
                status_code=403,
                detail=f"業者未啟用: {request.vendor_id}"
            )

        # Step 1: 意圖分類
        intent_classifier = req.app.state.intent_classifier
        intent_result = intent_classifier.classify(request.message)

        # Step 1.5: 對於 unclear 意圖，先嘗試 RAG 檢索
        # 即使意圖不明確，也可能在知識庫中找到相關答案
        if intent_result['intent_name'] == 'unclear':
            rag_engine = req.app.state.rag_engine

            # 使用更低的相似度閾值嘗試檢索
            rag_results = await rag_engine.search(
                query=request.message,
                limit=5,
                similarity_threshold=0.55
            )

            # 如果 RAG 檢索到相關知識，使用 LLM 優化答案
            if rag_results:
                llm_optimizer = req.app.state.llm_answer_optimizer

                # 獲取業者參數
                vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)
                vendor_params = {
                    key: param_info['value']
                    for key, param_info in vendor_params_raw.items()
                }

                # 使用 LLM 優化答案
                optimization_result = llm_optimizer.optimize_answer(
                    question=request.message,
                    search_results=rag_results,
                    confidence_level='medium',  # unclear 但找到知識，設為中等信心度
                    intent_info=intent_result,
                    vendor_params=vendor_params,
                    vendor_name=vendor_info['name']
                )

                answer = optimization_result['optimized_answer']

                # 準備來源列表
                sources = []
                if request.include_sources:
                    for r in rag_results:
                        sources.append(KnowledgeSource(
                            id=r['id'],
                            question_summary=r['title'],
                            answer=r['content'],
                            scope='global',  # RAG 檢索的是全局知識
                            is_template=False
                        ))

                return VendorChatResponse(
                    answer=answer,
                    intent_name="unclear",
                    intent_type="unclear",
                    confidence=intent_result['confidence'],
                    sources=sources if request.include_sources else None,
                    source_count=len(rag_results),
                    vendor_id=request.vendor_id,
                    mode=request.mode,
                    session_id=request.session_id,
                    timestamp=datetime.utcnow().isoformat()
                )

            # 如果 RAG 也找不到相關知識，才返回兜底回應
            params = resolver.get_vendor_parameters(request.vendor_id)
            service_hotline = params.get('service_hotline', {}).get('value', '客服')

            return VendorChatResponse(
                answer=f"抱歉，我不太理解您的問題。請您換個方式描述，或撥打客服專線 {service_hotline} 尋求協助。",
                intent_name="unclear",
                confidence=intent_result['confidence'],
                sources=None,
                source_count=0,
                vendor_id=request.vendor_id,
                mode=request.mode,
                session_id=request.session_id,
                timestamp=datetime.utcnow().isoformat()
            )

        # Step 2: 獲取意圖 ID
        db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin')
        }

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM intents WHERE name = %s AND is_enabled = true",
            (intent_result['intent_name'],)
        )
        result = cursor.fetchone()
        intent_id = result[0] if result else None
        cursor.close()
        conn.close()

        if not intent_id:
            raise HTTPException(
                status_code=500,
                detail=f"資料庫中找不到意圖: {intent_result['intent_name']}"
            )

        # Step 3: 檢索知識（Phase 1 擴展：使用混合模式，結合 intent 過濾和向量相似度）
        # 支援多 Intent 檢索
        retriever = get_vendor_knowledge_retriever()
        all_intent_ids = intent_result.get('intent_ids', [intent_id])

        knowledge_list = await retriever.retrieve_knowledge_hybrid(
            query=request.message,
            intent_id=intent_id,
            vendor_id=request.vendor_id,
            top_k=request.top_k,
            similarity_threshold=0.6,
            resolve_templates=False,  # Phase 1 擴展：不使用模板，改用 LLM
            all_intent_ids=all_intent_ids  # 傳遞所有相關 Intent IDs
        )

        # Step 3.5: 如果基於意圖找不到知識，fallback 到 RAG 向量搜尋
        if not knowledge_list:
            print(f"⚠️  意圖 '{intent_result['intent_name']}' (ID: {intent_id}) 沒有關聯知識，嘗試 RAG fallback...")

            rag_engine = req.app.state.rag_engine
            rag_results = await rag_engine.search(
                query=request.message,
                limit=request.top_k,
                similarity_threshold=0.60  # 使用標準閾值
            )

            # 如果 RAG 檢索到相關知識，使用 LLM 優化答案
            if rag_results:
                print(f"   ✅ RAG fallback 找到 {len(rag_results)} 個相關知識")

                llm_optimizer = req.app.state.llm_answer_optimizer

                # 獲取業者參數
                vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)
                vendor_params = {
                    key: param_info['value']
                    for key, param_info in vendor_params_raw.items()
                }

                # 使用 LLM 優化答案
                optimization_result = llm_optimizer.optimize_answer(
                    question=request.message,
                    search_results=rag_results,
                    confidence_level='high',  # RAG 高相似度，設為高信心度
                    intent_info=intent_result,
                    vendor_params=vendor_params,
                    vendor_name=vendor_info['name']
                )

                answer = optimization_result['optimized_answer']

                # 準備來源列表
                sources = []
                if request.include_sources:
                    for r in rag_results:
                        sources.append(KnowledgeSource(
                            id=r['id'],
                            question_summary=r['title'],
                            answer=r['content'],
                            scope='global',  # RAG 檢索的是全局知識
                            is_template=False
                        ))

                return VendorChatResponse(
                    answer=answer,
                    intent_name=intent_result['intent_name'],
                    intent_type=intent_result.get('intent_type'),
                    confidence=intent_result['confidence'],
                    sources=sources if request.include_sources else None,
                    source_count=len(rag_results),
                    vendor_id=request.vendor_id,
                    mode=request.mode,
                    session_id=request.session_id,
                    timestamp=datetime.utcnow().isoformat()
                )

            # 如果 RAG 也找不到，才返回兜底回應
            print(f"   ❌ RAG fallback 也沒有找到相關知識")
            params = resolver.get_vendor_parameters(request.vendor_id)
            service_hotline = params.get('service_hotline', {}).get('value', '客服')

            return VendorChatResponse(
                answer=f"很抱歉，關於「{intent_result['intent_name']}」我目前沒有相關資訊。建議您撥打客服專線 {service_hotline} 獲取協助。",
                intent_name=intent_result['intent_name'],
                intent_type=intent_result.get('intent_type'),
                confidence=intent_result['confidence'],
                sources=None,
                source_count=0,
                vendor_id=request.vendor_id,
                mode=request.mode,
                session_id=request.session_id,
                timestamp=datetime.utcnow().isoformat()
            )

        # Step 4: Phase 1 擴展 - 使用 LLM 動態注入業者參數
        # 獲取業者參數
        vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)

        # 轉換為簡單的 dict（提取 value）
        vendor_params = {
            key: param_info['value']
            for key, param_info in vendor_params_raw.items()
        }

        # 使用 LLM 優化器進行參數注入
        llm_optimizer = req.app.state.llm_answer_optimizer

        # 準備搜尋結果格式（與原 RAG 引擎格式一致）
        search_results = []
        for k in knowledge_list:
            search_results.append({
                'id': k['id'],
                'title': k['question_summary'],
                'content': k['answer'],
                'category': k.get('category', 'N/A'),
                'similarity': 0.9  # 從意圖檢索，假設高相似度
            })

        # 使用 LLM 優化並注入參數
        optimization_result = llm_optimizer.optimize_answer(
            question=request.message,
            search_results=search_results,
            confidence_level='high',  # 從意圖檢索，信心度高
            intent_info=intent_result,
            vendor_params=vendor_params,
            vendor_name=vendor_info['name']
        )

        answer = optimization_result['optimized_answer']

        # 準備來源列表
        sources = []
        if request.include_sources:
            for k in knowledge_list:
                sources.append(KnowledgeSource(
                    id=k['id'],
                    question_summary=k['question_summary'],
                    answer=k['answer'],
                    scope=k['scope'],
                    is_template=k['is_template']
                ))

        # Step 5: 返回回應
        return VendorChatResponse(
            answer=answer,
            intent_name=intent_result['intent_name'],
            intent_type=intent_result.get('intent_type'),
            confidence=intent_result['confidence'],
            all_intents=intent_result.get('all_intents', []),
            secondary_intents=intent_result.get('secondary_intents', []),
            intent_ids=intent_result.get('intent_ids', []),
            sources=sources if request.include_sources else None,
            source_count=len(knowledge_list),
            vendor_id=request.vendor_id,
            mode=request.mode,
            session_id=request.session_id,
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"處理聊天請求失敗: {str(e)}"
        )


@router.get("/vendors/{vendor_id}/test")
async def test_vendor_config(vendor_id: int):
    """
    測試業者配置

    用於檢查業者的參數是否正確設定
    """
    try:
        resolver = get_vendor_param_resolver()

        # 獲取業者資訊
        vendor_info = resolver.get_vendor_info(vendor_id)
        if not vendor_info:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 獲取業者參數
        params = resolver.get_vendor_parameters(vendor_id)

        # 測試模板解析
        test_template = "繳費日為 {{payment_day}}，逾期費 {{late_fee}}。"
        resolved = resolver.resolve_template(test_template, vendor_id)

        return {
            "vendor": vendor_info,
            "param_count": len(params),
            "parameters": params,
            "test_template": {
                "original": test_template,
                "resolved": resolved
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_vendor_services():
    """
    重新載入多業者服務

    用於意圖或知識更新後重新載入
    """
    try:
        global _vendor_param_resolver

        # 清除參數快取
        if _vendor_param_resolver:
            _vendor_param_resolver.clear_cache()

        return {
            "success": True,
            "message": "多業者服務已重新載入",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重新載入失敗: {str(e)}"
        )
