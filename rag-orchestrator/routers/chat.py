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
from services.db_utils import get_db_config
from services.embedding_utils import get_embedding_client

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


# ==================== 輔助函數：答案清理與模板替換 ====================

def _clean_answer(answer: str, vendor_id: int, resolver) -> str:
    """
    清理答案並替換模板變數（兜底保護）

    處理兩種情況：
    1. 模板變數格式：{{service_hotline}} → 02-2345-6789
    2. 異常格式：@vendorA, @vendor_name 等 → 移除

    Args:
        answer: 原始答案
        vendor_id: 業者 ID
        resolver: 參數解析器

    Returns:
        清理後的答案
    """
    import re

    # 1. 替換明確的模板變數 {{xxx}}
    cleaned = resolver.resolve_template(answer, vendor_id, raise_on_missing=False)

    # 2. 清理異常格式（已停用，因為會誤刪真實 LINE ID）
    # 注意：@vendorA 可能是真實的 LINE ID，不應該移除
    # cleaned = re.sub(r'@vendor[A-Za-z0-9_]*', '', cleaned)  # ← 已停用

    # 3. 如果仍有未替換的模板變數，記錄警告
    if '{{' in cleaned:
        remaining_vars = re.findall(r'\{\{(\w+)\}\}', cleaned)
        print(f"⚠️  警告：答案中仍有未替換的模板變數: {remaining_vars}")

    return cleaned


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

    # RAG 檢索（使用較低閾值）
    fallback_similarity_threshold = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", "0.55"))
    rag_top_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_results = await rag_engine.search(
        query=request.message,
        limit=rag_top_k,
        similarity_threshold=fallback_similarity_threshold,
        vendor_id=request.vendor_id
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

    # 清理答案並替換模板變數（兜底保護）
    fallback_answer = f"我目前沒有找到符合您問題的資訊，但我可以協助您轉給客服處理。如需立即協助，請撥打客服專線 {service_hotline}。請問您方便提供更詳細的內容嗎？"
    final_answer = _clean_answer(fallback_answer, request.vendor_id, resolver)

    return VendorChatResponse(
        answer=final_answer,
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
    """
    記錄 unclear 問題到測試場景庫 + 意圖建議

    功能增強（語義去重）：
    - 相關度過濾：relevance_score >= 0.7
    - 語義去重：使用 embedding 檢測相似問題（similarity >= 0.80）
    - 編輯距離：Levenshtein Distance <= 2（數據庫層）
    """
    # 1. 使用意圖建議引擎分析問題相關性
    suggestion_engine = req.app.state.suggestion_engine
    analysis = suggestion_engine.analyze_unclear_question(
        question=request.message,
        vendor_id=request.vendor_id,
        user_id=request.user_id,
        conversation_context=None
    )

    # 獲取相關度評估結果
    is_relevant = analysis.get('is_relevant', False)
    relevance_score = analysis.get('relevance_score', 0.0)
    should_record = analysis.get('should_record', False)

    # 只記錄相關度高的問題 (relevance_score >= 0.7)
    if not should_record:
        print(f"⏭️  跳過記錄：問題相關度不足 (score: {relevance_score:.2f}, relevant: {is_relevant})")
        print(f"   問題: {request.message}")
        return

    # 2. 生成問題的 embedding（用於語義去重）
    embedding_client = get_embedding_client()
    question_embedding = await embedding_client.get_embedding(request.message, verbose=False)

    if not question_embedding:
        print(f"⚠️  無法生成問題向量，回退到精確匹配模式")
        # 後續仍會進行精確匹配檢查

    # 3. 記錄到測試場景庫（相關度過濾 + 語義去重）
    try:
        test_scenario_conn = psycopg2.connect(**get_db_config())
        test_scenario_cursor = test_scenario_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 3a. 精確匹配檢查（完全相同的問題）
        test_scenario_cursor.execute("""
            SELECT id, status FROM test_scenarios
            WHERE test_question = %s
              AND status IN ('pending_review', 'draft', 'approved')
              AND is_active = true
        """, (request.message,))
        exact_match = test_scenario_cursor.fetchone()

        if exact_match:
            scenario_id, existing_status = exact_match
            print(f"⏭️  跳過記錄：完全相同問題已存在 (Scenario ID: {scenario_id}, 狀態: {existing_status})")
            print(f"   問題: {request.message}")
            test_scenario_cursor.close()
            test_scenario_conn.close()
            return

        # 3b. 語義相似度檢查（使用 embedding 向量搜索）
        if question_embedding:
            vector_str = '[' + ','.join(map(str, question_embedding)) + ']'

            test_scenario_cursor.execute("""
                SELECT
                    id,
                    test_question,
                    status,
                    (1 - (question_embedding <=> %s::vector)) AS similarity
                FROM test_scenarios
                WHERE question_embedding IS NOT NULL
                  AND status IN ('pending_review', 'draft', 'approved')
                  AND is_active = true
                  AND test_question != %s
                  AND (1 - (question_embedding <=> %s::vector)) >= 0.80
                ORDER BY similarity DESC
                LIMIT 1
            """, (vector_str, request.message, vector_str))

            similar_match = test_scenario_cursor.fetchone()

            if similar_match:
                scenario_id = similar_match['id']
                similar_question = similar_match['test_question']
                similarity = similar_match['similarity']
                existing_status = similar_match['status']

                print(f"⏭️  跳過記錄：相似問題已存在 (Scenario ID: {scenario_id}, 狀態: {existing_status})")
                print(f"   原問題: {request.message}")
                print(f"   相似問題: {similar_question}")
                print(f"   相似度: {similarity:.3f}")

                test_scenario_cursor.close()
                test_scenario_conn.close()
                return

        # 4. 插入新的測試場景記錄（含 embedding）
        if question_embedding:
            vector_str = '[' + ','.join(map(str, question_embedding)) + ']'
            test_scenario_cursor.execute("""
                INSERT INTO test_scenarios (
                    test_question, status, source,
                    difficulty, priority, notes, test_purpose, created_by,
                    question_embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                RETURNING id
            """, (
                request.message, 'pending_review', 'user_question',
                'hard', 80,
                f"用戶問題意圖不明確（Vendor {request.vendor_id}），相關度: {relevance_score:.2f}",
                "追蹤意圖識別缺口，改善分類器",
                request.user_id or 'system',
                vector_str
            ))
        else:
            # 無 embedding 時仍插入記錄（但無法做語義去重）
            test_scenario_cursor.execute("""
                INSERT INTO test_scenarios (
                    test_question, status, source,
                    difficulty, priority, notes, test_purpose, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.message, 'pending_review', 'user_question',
                'hard', 80,
                f"用戶問題意圖不明確（Vendor {request.vendor_id}），相關度: {relevance_score:.2f}",
                "追蹤意圖識別缺口，改善分類器",
                request.user_id or 'system'
            ))

        scenario_id = test_scenario_cursor.fetchone()[0]
        test_scenario_conn.commit()

        embedding_status = "✅ 含向量" if question_embedding else "⚠️  無向量"
        print(f"✅ 記錄unclear問題到測試場景庫 (Scenario ID: {scenario_id}, 相關度: {relevance_score:.2f}, {embedding_status})")

        test_scenario_cursor.close()
        test_scenario_conn.close()
    except Exception as e:
        print(f"⚠️ 記錄測試場景失敗: {e}")
        import traceback
        traceback.print_exc()

    # 5. 記錄意圖建議
    suggested_intent_id = suggestion_engine.record_suggestion(
        question=request.message,
        analysis=analysis,
        user_id=request.user_id
    )
    if suggested_intent_id:
        print(f"✅ 發現新意圖建議: {analysis['suggested_intent']['name']} (ID: {suggested_intent_id})")


# ==================== 輔助函數：SOP 檢索 ====================

async def _retrieve_sop(request: VendorChatRequest, intent_result: dict) -> list:
    """檢索 SOP（SOP 優先於知識庫）- 使用 Hybrid 模式（Intent + 相似度）"""
    from routers.chat_shared import retrieve_sop_hybrid

    # 使用共用模組的 hybrid 版本（intent + 向量相似度過濾）
    all_intent_ids = intent_result.get('intent_ids', [])
    sop_similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.75"))
    sop_items = await retrieve_sop_hybrid(
        vendor_id=request.vendor_id,
        intent_ids=all_intent_ids,
        query=request.message,  # ← 傳入問題文本用於相似度計算
        top_k=request.top_k,
        similarity_threshold=sop_similarity_threshold
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

    # 獲取業者參數（保留完整資訊包含 display_name, unit 等）
    vendor_params = resolver.get_vendor_parameters(request.vendor_id)

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

    # 清理答案並替換模板變數（兜底保護）
    final_answer = _clean_answer(optimization_result['optimized_answer'], request.vendor_id, resolver)

    response = VendorChatResponse(
        answer=final_answer,
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

    # 獲取業者參數（保留完整資訊包含 display_name, unit 等）
    vendor_params = resolver.get_vendor_parameters(request.vendor_id)

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
            question_summary=r['question_summary'],
            answer=r['content'],
            scope='global',
            is_template=False
        ) for r in rag_results]

    # 清理答案並替換模板變數（兜底保護）
    final_answer = _clean_answer(optimization_result['optimized_answer'], request.vendor_id, resolver)

    response = VendorChatResponse(
        answer=final_answer,
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
    kb_similarity_threshold = float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.65"))

    knowledge_list = await retriever.retrieve_knowledge_hybrid(
        query=request.message,
        intent_id=intent_id,
        vendor_id=request.vendor_id,
        top_k=request.top_k,
        similarity_threshold=kb_similarity_threshold,
        resolve_templates=False,
        all_intent_ids=all_intent_ids,
        user_role=request.user_role
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
    """處理找不到知識的情況：參數答案 > RAG fallback + 測試場景記錄"""
    # Step 1: 優先檢查是否為參數型問題（沒有知識庫時的備選方案）
    from routers.chat_shared import check_param_question
    param_category, param_answer = await check_param_question(
        vendor_config_service=req.app.state.vendor_config_service,
        question=request.message,
        vendor_id=request.vendor_id
    )

    if param_answer:
        print(f"   ℹ️  知識庫無結果，使用參數型答案（category={param_category}）")
        response = VendorChatResponse(
            answer=param_answer['answer'],
            intent_name="參數查詢",
            intent_type="config_param",
            confidence=1.0,
            sources=[],
            source_count=0,
            vendor_id=request.vendor_id,
            mode=request.mode,
            timestamp=datetime.utcnow().isoformat() + "Z",
            video_url=None
        )
        return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.user_role)

    # Step 2: RAG fallback
    rag_engine = req.app.state.rag_engine
    fallback_similarity_threshold = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", "0.55"))
    rag_top_k = int(os.getenv("RAG_TOP_K", str(request.top_k)))
    rag_results = await rag_engine.search(
        query=request.message,
        limit=rag_top_k,
        similarity_threshold=fallback_similarity_threshold,
        vendor_id=request.vendor_id
    )

    # 如果 RAG 找到結果，返回優化答案
    if rag_results:
        print(f"   ✅ RAG fallback 找到 {len(rag_results)} 個相關知識")
        return await _build_rag_response(
            request, req, intent_result, rag_results,
            resolver, vendor_info, cache_service,
            confidence_level='high'
        )

    # Step 3: 如果 RAG 也找不到，記錄測試場景並返回兜底回應
    print(f"   ❌ RAG fallback 也沒有找到相關知識")
    await _record_no_knowledge_scenario(request, intent_result, req)

    params = resolver.get_vendor_parameters(request.vendor_id)
    service_hotline = params.get('service_hotline', {}).get('value', '客服')

    # 清理答案並替換模板變數（兜底保護）
    fallback_answer = f"我目前沒有找到關於「{intent_result['intent_name']}」的相關資訊，但我可以協助您轉給客服處理。如需立即協助，請撥打客服專線 {service_hotline}。請問您方便提供更詳細的內容嗎？"
    final_answer = _clean_answer(fallback_answer, request.vendor_id, resolver)

    return VendorChatResponse(
        answer=final_answer,
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
            test_scenario_cursor.execute("""
                INSERT INTO test_scenarios (
                    test_question, status, source,
                    difficulty, priority, notes, test_purpose, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.message,
                'pending_review', 'user_question', 'medium', 70,
                f"用戶真實問題（Vendor {request.vendor_id}），意圖: {intent_result.get('intent_name', 'unknown')}，系統無法提供答案",
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
    confidence_evaluator = req.app.state.confidence_evaluator

    # 獲取業者參數（保留完整資訊包含 display_name, unit 等）
    vendor_params = resolver.get_vendor_parameters(request.vendor_id)

    # 準備搜尋結果格式（使用實際的相似度或預設值）
    search_results = [{
        'id': k['id'],
        'question_summary': k['question_summary'],
        'content': k['answer'],
        'similarity': k.get('similarity', 0.9),  # 使用實際相似度，沒有則用預設值
        'keywords': k.get('keywords', [])        # 添加 keywords 供信心度評估
    } for k in knowledge_list]

    # 使用 ConfidenceEvaluator 評估信心度（與 /v1/chat/stream 統一）
    evaluation = confidence_evaluator.evaluate(
        search_results=search_results,
        question_keywords=intent_result.get('keywords', [])
    )

    confidence_level = evaluation['confidence_level']
    confidence_score = evaluation['confidence_score']

    print(f"📊 [知識庫信心度評估] level={confidence_level}, score={confidence_score:.3f}, decision={evaluation['decision']}")

    # LLM 優化（使用評估後的信心度）
    optimization_result = llm_optimizer.optimize_answer(
        question=request.message,
        search_results=search_results,
        confidence_level=confidence_level,
        confidence_score=confidence_score,  # 使用 ConfidenceEvaluator 計算的分數
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

    # 提取影片資訊（從第一個知識項目）
    video_url = None
    video_file_size = None
    video_duration = None
    video_format = None
    if knowledge_list:
        first_knowledge = knowledge_list[0]
        video_url = first_knowledge.get('video_url')
        video_file_size = first_knowledge.get('video_file_size')
        video_duration = first_knowledge.get('video_duration')
        video_format = first_knowledge.get('video_format')

    # 清理答案並替換模板變數（兜底保護）
    final_answer = _clean_answer(optimization_result['optimized_answer'], request.vendor_id, resolver)

    response = VendorChatResponse(
        answer=final_answer,
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
        timestamp=datetime.utcnow().isoformat(),
        video_url=video_url,
        video_file_size=video_file_size,
        video_duration=video_duration,
        video_format=video_format
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
    skip_sop: bool = Field(False, description="跳過 SOP 檢索，僅檢索知識庫（回測模式專用）")


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
    # 影片資訊
    video_url: Optional[str] = Field(None, description="教學影片 URL")
    video_file_size: Optional[int] = Field(None, description="影片檔案大小（bytes）")
    video_duration: Optional[int] = Field(None, description="影片長度（秒）")
    video_format: Optional[str] = Field(None, description="影片格式")


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

        # Step 6: 嘗試檢索 SOP（優先級最高）- 回測模式可跳過
        if not request.skip_sop:
            sop_items = await _retrieve_sop(request, intent_result)
            if sop_items:
                print(f"✅ 找到 {len(sop_items)} 個 SOP 項目，使用 SOP 流程")
                return await _build_sop_response(
                    request, req, intent_result, sop_items, resolver, vendor_info, cache_service
                )
            print(f"ℹ️  沒有找到 SOP，使用知識庫檢索")
        else:
            print(f"ℹ️  [回測模式] 跳過 SOP 檢索，僅使用知識庫")

        # Step 7: 檢索知識庫（混合模式：intent + 向量）
        knowledge_list = await _retrieve_knowledge(request, intent_id, intent_result)

        # Step 8: 如果知識庫沒有結果，嘗試參數答案或 RAG fallback
        if not knowledge_list:
            print(f"⚠️  意圖 '{intent_result['intent_name']}' (ID: {intent_id}) 沒有關聯知識，嘗試參數答案或 RAG fallback...")
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
