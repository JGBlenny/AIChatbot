"""
聊天 API 路由
處理使用者問題，整合意圖分類、RAG 檢索和信心度評估

Phase 1: 新增多業者支援（Multi-Vendor Chat API）
"""
from __future__ import annotations  # 允許類型提示的前向引用

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import time
import json
import os
import psycopg2
import psycopg2.extras
from services.business_scope_utils import get_allowed_audiences_for_scope
from services.db_utils import get_db_config

router = APIRouter()

# Phase 1: 多業者服務實例（懶加載）
_vendor_knowledge_retriever = None
_vendor_param_resolver = None
_vendor_sop_retriever = None


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


def get_vendor_sop_retriever():
    """獲取業者 SOP 檢索器"""
    global _vendor_sop_retriever
    if _vendor_sop_retriever is None:
        from services.vendor_sop_retriever import VendorSOPRetriever
        _vendor_sop_retriever = VendorSOPRetriever()
    return _vendor_sop_retriever


def cache_response_and_return(cache_service, vendor_id: int, question: str, response, user_role: str = "customer"):
    """
    緩存響應並返回（輔助函數）

    Args:
        cache_service: 緩存服務實例
        vendor_id: 業者 ID
        question: 用戶問題
        response: VendorChatResponse 實例
        user_role: 用戶角色

    Returns:
        原始 response
    """
    try:
        # 將響應轉換為字典並緩存
        response_dict = response.dict()
        cache_service.cache_answer(
            vendor_id=vendor_id,
            question=question,
            answer_data=response_dict,
            user_role=user_role
        )
    except Exception as e:
        # 緩存失敗不應影響正常響應
        print(f"⚠️  緩存存儲失敗: {e}")

    return response


# ==================== 輔助函數：業者驗證與緩存 ====================

def _validate_vendor(vendor_id: int, resolver) -> dict:
    """驗證業者狀態"""
    vendor_info = resolver.get_vendor_info(vendor_id)

    if not vendor_info:
        raise HTTPException(
            status_code=404,
            detail=f"業者不存在: {vendor_id}"
        )

    if not vendor_info['is_active']:
        raise HTTPException(
            status_code=403,
            detail=f"業者未啟用: {vendor_id}"
        )

    return vendor_info


def _check_cache(cache_service, vendor_id: int, question: str, user_role: str):
    """檢查緩存，如果命中則返回緩存的答案"""
    cached_answer = cache_service.get_cached_answer(
        vendor_id=vendor_id,
        question=question,
        user_role=user_role
    )

    if cached_answer:
        print(f"⚡ 緩存命中！直接返回答案（跳過 RAG 處理）")
        return VendorChatResponse(**cached_answer)

    return None


#==================== 輔助函數：Unclear 意圖處理 ====================

async def _handle_unclear_with_rag_fallback(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    resolver,
    vendor_info: dict,
    cache_service
):
    """處理 unclear 意圖：RAG fallback + 測試場景記錄 + 意圖建議"""
    rag_engine = req.app.state.rag_engine

    # 根據用戶角色決定業務範圍
    business_scope = "external" if request.user_role == "customer" else "internal"
    allowed_audiences = get_allowed_audiences_for_scope(business_scope)

    # RAG 檢索（使用較低閾值）
    rag_results = await rag_engine.search(
        query=request.message,
        limit=5,
        similarity_threshold=0.55,
        allowed_audiences=allowed_audiences
    )

    # 如果 RAG 找到結果，優化並返回答案
    if rag_results:
        return await _build_rag_response(
            request, req, intent_result, rag_results,
            resolver, vendor_info, cache_service,
            confidence_level='medium',
            intent_name="unclear"
        )

    # 如果 RAG 也沒找到，記錄問題並返回兜底回應
    await _record_unclear_question(request, req)

    params = resolver.get_vendor_parameters(request.vendor_id)
    service_hotline = params.get('service_hotline', {}).get('value', '客服')

    return VendorChatResponse(
        answer=f"抱歉，我不太理解您的問題。請您換個方式描述，或撥打客服專線 {service_hotline} 尋求協助。",
        intent_name="unclear",
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=None,
        source_count=0,
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat()
    )


async def _record_unclear_question(request: VendorChatRequest, req: Request):
    """記錄 unclear 問題到測試場景庫 + 意圖建議"""
    # 1. 記錄到測試場景庫
    try:
        test_scenario_conn = psycopg2.connect(**get_db_config())
        test_scenario_cursor = test_scenario_conn.cursor()

        test_scenario_cursor.execute(
            "SELECT id FROM test_scenarios WHERE test_question = %s AND status = 'pending_review'",
            (request.message,)
        )
        existing_scenario = test_scenario_cursor.fetchone()

        if not existing_scenario:
            test_scenario_cursor.execute("""
                INSERT INTO test_scenarios (
                    test_question, expected_category, status, source,
                    difficulty, priority, notes, test_purpose, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.message, 'unclear', 'pending_review', 'user_question',
                'hard', 80,
                f"用戶問題意圖不明確（Vendor {request.vendor_id}），系統無法識別並提供答案",
                "追蹤意圖識別缺口，改善分類器",
                request.user_id or 'system'
            ))
            scenario_id = test_scenario_cursor.fetchone()[0]
            test_scenario_conn.commit()
            print(f"✅ 記錄unclear問題到測試場景庫 (Scenario ID: {scenario_id})")

        test_scenario_cursor.close()
        test_scenario_conn.close()
    except Exception as e:
        print(f"⚠️ 記錄測試場景失敗: {e}")

    # 2. 使用意圖建議引擎
    suggestion_engine = req.app.state.suggestion_engine
    analysis = suggestion_engine.analyze_unclear_question(
        question=request.message,
        vendor_id=request.vendor_id,
        user_id=request.user_id,
        conversation_context=None
    )

    if analysis.get('should_record'):
        suggested_intent_id = suggestion_engine.record_suggestion(
            question=request.message,
            analysis=analysis,
            user_id=request.user_id
        )
        if suggested_intent_id:
            print(f"✅ 發現新意圖建議: {analysis['suggested_intent']['name']} (ID: {suggested_intent_id})")


# ==================== 輔助函數：SOP 檢索 ====================

def _retrieve_sop(request: VendorChatRequest, intent_result: dict) -> list:
    """檢索 SOP（SOP 優先於知識庫）- 使用共用模組"""
    from routers.chat_shared import retrieve_sop_sync

    # 使用共用模組的同步版本
    all_intent_ids = intent_result.get('intent_ids', [])
    sop_items = retrieve_sop_sync(
        vendor_id=request.vendor_id,
        intent_ids=all_intent_ids,
        top_k=request.top_k
    )

    return sop_items


async def _build_sop_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    sop_items: list,
    resolver,
    vendor_info: dict,
    cache_service
):
    """使用 SOP 構建回應 - 使用共用模組"""
    from routers.chat_shared import convert_sop_to_search_results, create_sop_optimization_params

    llm_optimizer = req.app.state.llm_answer_optimizer

    # 獲取業者參數
    vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)
    vendor_params = {key: param_info['value'] for key, param_info in vendor_params_raw.items()}

    # 使用共用函數轉換 SOP 為 search_results 格式（自動設定 similarity=1.0）
    search_results = convert_sop_to_search_results(sop_items)

    # 使用共用函數建立優化參數（自動設定 confidence=high, score=0.95）
    optimization_params = create_sop_optimization_params(
        question=request.message,
        search_results=search_results,
        intent_result=intent_result,
        vendor_params=vendor_params,
        vendor_info=vendor_info,
        enable_synthesis_override=False if request.disable_answer_synthesis else None
    )

    # LLM 優化
    optimization_result = llm_optimizer.optimize_answer(**optimization_params)

    # 構建來源列表
    sources = []
    if request.include_sources:
        sources = [KnowledgeSource(
            id=sop['id'],
            question_summary=sop['item_name'],
            answer=sop['content'],
            scope='vendor_sop',
            is_template=False
        ) for sop in sop_items]

    response = VendorChatResponse(
        answer=optimization_result['optimized_answer'],
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=sources if request.include_sources else None,
        source_count=len(sop_items),
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat()
    )

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.user_role)


# ==================== 輔助函數：RAG 回應構建 ====================

async def _build_rag_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    rag_results: list,
    resolver,
    vendor_info: dict,
    cache_service,
    confidence_level: str = 'medium',
    intent_name: str = None
):
    """使用 RAG 結果構建優化回應"""
    llm_optimizer = req.app.state.llm_answer_optimizer

    # 獲取業者參數
    vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)
    vendor_params = {key: param_info['value'] for key, param_info in vendor_params_raw.items()}

    # 根據 confidence_level 設定 confidence_score
    confidence_score_map = {
        'high': 0.85,
        'medium': 0.70,
        'low': 0.55
    }
    confidence_score = confidence_score_map.get(confidence_level, 0.70)

    # LLM 優化（添加 confidence_score 以確保參數注入）
    optimization_result = llm_optimizer.optimize_answer(
        question=request.message,
        search_results=rag_results,
        confidence_level=confidence_level,
        confidence_score=confidence_score,  # 根據 confidence_level 設定分數
        intent_info=intent_result,
        vendor_params=vendor_params,
        vendor_name=vendor_info['name'],
        vendor_info=vendor_info,  # 傳入完整業者資訊
        enable_synthesis_override=False if request.disable_answer_synthesis else None
    )

    # 構建來源列表
    sources = []
    if request.include_sources:
        sources = [KnowledgeSource(
            id=r['id'],
            question_summary=r['title'],
            answer=r['content'],
            scope='global',
            is_template=False
        ) for r in rag_results]

    response = VendorChatResponse(
        answer=optimization_result['optimized_answer'],
        intent_name=intent_name or intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=sources if request.include_sources else None,
        source_count=len(rag_results),
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat()
    )

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.user_role)


# ==================== 輔助函數：知識庫檢索 ====================

async def _retrieve_knowledge(
    request: VendorChatRequest,
    intent_id: int,
    intent_result: dict
):
    """檢索知識庫（混合模式：intent + 向量相似度）"""
    retriever = get_vendor_knowledge_retriever()
    all_intent_ids = intent_result.get('intent_ids', [intent_id])

    knowledge_list = await retriever.retrieve_knowledge_hybrid(
        query=request.message,
        intent_id=intent_id,
        vendor_id=request.vendor_id,
        top_k=request.top_k,
        similarity_threshold=0.6,
        resolve_templates=False,
        all_intent_ids=all_intent_ids
    )

    return knowledge_list


async def _handle_no_knowledge_found(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    resolver,
    cache_service,
    vendor_info: dict
):
    """處理找不到知識的情況：RAG fallback + 測試場景記錄"""
    from services.business_scope_utils import get_allowed_audiences_for_scope

    # 根據用戶角色決定業務範圍
    business_scope = "external" if request.user_role == "customer" else "internal"
    allowed_audiences = get_allowed_audiences_for_scope(business_scope)

    # RAG fallback
    rag_engine = req.app.state.rag_engine
    rag_results = await rag_engine.search(
        query=request.message,
        limit=request.top_k,
        similarity_threshold=0.60,
        allowed_audiences=allowed_audiences
    )

    # 如果 RAG 找到結果，返回優化答案
    if rag_results:
        print(f"   ✅ RAG fallback 找到 {len(rag_results)} 個相關知識")
        return await _build_rag_response(
            request, req, intent_result, rag_results,
            resolver, vendor_info, cache_service,
            confidence_level='high'
        )

    # 如果 RAG 也找不到，記錄測試場景並返回兜底回應
    print(f"   ❌ RAG fallback 也沒有找到相關知識")
    await _record_no_knowledge_scenario(request, intent_result, req)

    params = resolver.get_vendor_parameters(request.vendor_id)
    service_hotline = params.get('service_hotline', {}).get('value', '客服')

    return VendorChatResponse(
        answer=f"很抱歉，關於「{intent_result['intent_name']}」我目前沒有相關資訊。建議您撥打客服專線 {service_hotline} 獲取協助。",
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=None,
        source_count=0,
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat()
    )


async def _record_no_knowledge_scenario(request: VendorChatRequest, intent_result: dict, req: Request):
    """記錄找不到知識的場景到測試庫 + 意圖建議"""
    # 1. 記錄到測試場景庫
    try:
        test_scenario_conn = psycopg2.connect(**get_db_config())
        test_scenario_cursor = test_scenario_conn.cursor()

        test_scenario_cursor.execute(
            "SELECT id FROM test_scenarios WHERE test_question = %s AND status = 'pending_review'",
            (request.message,)
        )
        existing_scenario = test_scenario_cursor.fetchone()

        if not existing_scenario:
            intent_id = intent_result.get('intent_ids', [None])[0] if intent_result.get('intent_ids') else None
            test_scenario_cursor.execute("""
                INSERT INTO test_scenarios (
                    test_question, expected_category, expected_intent_id, status, source,
                    difficulty, priority, notes, test_purpose, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.message, intent_result['intent_name'], intent_id,
                'pending_review', 'user_question', 'medium', 70,
                f"用戶真實問題（Vendor {request.vendor_id}），系統無法提供答案",
                "驗證知識庫覆蓋率，追蹤用戶真實需求",
                request.user_id or 'system'
            ))
            scenario_id = test_scenario_cursor.fetchone()[0]
            test_scenario_conn.commit()
            print(f"✅ 記錄到測試場景庫 (Scenario ID: {scenario_id})")

        test_scenario_cursor.close()
        test_scenario_conn.close()
    except Exception as e:
        print(f"⚠️ 記錄測試場景失敗: {e}")

    # 2. 使用意圖建議引擎
    suggestion_engine = req.app.state.suggestion_engine
    analysis = suggestion_engine.analyze_unclear_question(
        question=request.message,
        vendor_id=request.vendor_id,
        user_id=request.user_id,
        conversation_context=None
    )

    if analysis.get('should_record'):
        suggested_intent_id = suggestion_engine.record_suggestion(
            question=request.message,
            analysis=analysis,
            user_id=request.user_id
        )
        if suggested_intent_id:
            print(f"✅ 發現知識缺口建議 (Vendor {request.vendor_id}): {analysis['suggested_intent']['name']} (建議ID: {suggested_intent_id})")


async def _build_knowledge_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    knowledge_list: list,
    resolver,
    vendor_info: dict,
    cache_service
):
    """使用知識庫結果構建優化回應"""
    llm_optimizer = req.app.state.llm_answer_optimizer

    # 獲取業者參數
    vendor_params_raw = resolver.get_vendor_parameters(request.vendor_id)
    vendor_params = {key: param_info['value'] for key, param_info in vendor_params_raw.items()}

    # 準備搜尋結果格式
    search_results = [{
        'id': k['id'],
        'title': k['question_summary'],
        'content': k['answer'],
        'category': k.get('category', 'N/A'),
        'similarity': 0.9
    } for k in knowledge_list]

    # LLM 優化（添加 confidence_score 以確保參數注入）
    optimization_result = llm_optimizer.optimize_answer(
        question=request.message,
        search_results=search_results,
        confidence_level='high',
        confidence_score=0.90,  # 知識庫 intent 匹配，高信心度
        intent_info=intent_result,
        vendor_params=vendor_params,
        vendor_name=vendor_info['name'],
        vendor_info=vendor_info,  # 傳入完整業者資訊
        enable_synthesis_override=False if request.disable_answer_synthesis else None
    )

    # 構建來源列表
    sources = []
    if request.include_sources:
        sources = [KnowledgeSource(
            id=k['id'],
            question_summary=k['question_summary'],
            answer=k['answer'],
            scope=k['scope'],
            is_template=k['is_template']
        ) for k in knowledge_list]

    response = VendorChatResponse(
        answer=optimization_result['optimized_answer'],
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

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.user_role)


# ========================================
# /api/v1/chat 端點已於 2025-10-21 移除
# ========================================
#
# 移除原因：功能已由更強大的端點替代
#
# 替代方案：
# 1. /api/v1/message - 多業者通用端點
#    - 支持 SOP 整合
#    - 支持業者參數配置
#    - 支持多 Intent 檢索
#
# 2. /api/v1/chat/stream - 流式聊天端點
#    - 提供即時反饋
#    - 更好的用戶體驗
#
# 詳見：
# - docs/api/CHAT_ENDPOINT_REMOVAL_AUDIT.md (盤查報告)
# - docs/api/CHAT_API_MIGRATION_GUIDE.md (遷移指南)
#
# 已移除的項目：
# - class ChatRequest
# - class ChatResponse
# - POST /chat 端點函數
#
# ========================================


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
    user_role: str = Field("customer", description="用戶角色：customer (終端客戶) 或 staff (業者員工/系統商)")
    mode: str = Field("tenant", description="模式：tenant (B2C) 或 customer_service (B2B)")
    session_id: Optional[str] = Field(None, description="會話 ID（用於追蹤）")
    user_id: Optional[str] = Field(None, description="使用者 ID（租客 ID 或客服 ID）")
    top_k: int = Field(5, description="返回知識數量", ge=1, le=10)
    include_sources: bool = Field(True, description="是否包含知識來源")
    disable_answer_synthesis: bool = Field(False, description="禁用答案合成（回測模式專用）")


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
    多業者通用聊天端點（Phase 1: B2C 模式）- 已重構

    流程：
    1. 驗證業者狀態
    2. 檢查緩存
    3. 意圖分類
    4. 根據意圖處理：unclear → SOP → 知識庫 → RAG fallback
    5. LLM 優化並返回答案

    重構：單一職責原則（Single Responsibility Principle）
    - 主函數作為編排器（Orchestrator）
    - 各功能模塊獨立為輔助函數
    """
    try:
        # Step 1: 驗證業者
        resolver = get_vendor_param_resolver()
        vendor_info = _validate_vendor(request.vendor_id, resolver)

        # Step 2: 緩存檢查
        cache_service = req.app.state.cache_service
        cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.user_role)
        if cached_response:
            return cached_response

        # Step 3: 意圖分類
        intent_classifier = req.app.state.intent_classifier
        intent_result = intent_classifier.classify(request.message)

        # Step 4: 處理 unclear 意圖（RAG fallback + 測試場景記錄）
        if intent_result['intent_name'] == 'unclear':
            return await _handle_unclear_with_rag_fallback(
                request, req, intent_result, resolver, vendor_info, cache_service
            )

        # Step 5: 獲取意圖 ID
        intent_id = _get_intent_id(intent_result['intent_name'])

        # Step 6: 嘗試檢索 SOP（優先級最高）
        sop_items = _retrieve_sop(request, intent_result)
        if sop_items:
            print(f"✅ 找到 {len(sop_items)} 個 SOP 項目，使用 SOP 流程")
            return await _build_sop_response(
                request, req, intent_result, sop_items, resolver, vendor_info, cache_service
            )

        # Step 7: 檢索知識庫（混合模式：intent + 向量）
        print(f"ℹ️  沒有找到 SOP，使用知識庫檢索")
        knowledge_list = await _retrieve_knowledge(request, intent_id, intent_result)

        # Step 8: 如果知識庫沒有結果，嘗試 RAG fallback
        if not knowledge_list:
            print(f"⚠️  意圖 '{intent_result['intent_name']}' (ID: {intent_id}) 沒有關聯知識，嘗試 RAG fallback...")
            return await _handle_no_knowledge_found(
                request, req, intent_result, resolver, cache_service, vendor_info
            )

        # Step 9: 使用知識庫結果構建優化回應
        return await _build_knowledge_response(
            request, req, intent_result, knowledge_list, resolver, vendor_info, cache_service
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


def _get_intent_id(intent_name: str) -> int:
    """獲取意圖 ID"""
    conn = psycopg2.connect(**get_db_config())
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM intents WHERE name = %s AND is_enabled = true",
        (intent_name,)
    )
    result = cursor.fetchone()
    intent_id = result[0] if result else None
    cursor.close()
    conn.close()

    if not intent_id:
        raise HTTPException(
            status_code=500,
            detail=f"資料庫中找不到意圖: {intent_name}"
        )

    return intent_id


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
