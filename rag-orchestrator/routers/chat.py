"""
聊天 API 路由
處理使用者問題，整合意圖分類、RAG 檢索和信心度評估

Phase 1: 新增多業者支援（Multi-Vendor Chat API）
"""
from __future__ import annotations  # 允許類型提示的前向引用

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
import time
import json
import os
import asyncio
import psycopg2
import psycopg2.extras
from services.db_utils import get_db_config
from services.embedding_utils import get_embedding_client

router = APIRouter()

# 常量定義
TARGET_USER_ROLES = ['tenant', 'landlord', 'property_manager', 'system_admin']
BUSINESS_MODES = ['b2c', 'b2b']


def _generate_config_version() -> str:
    """
    生成配置版本字符串，用於緩存鍵的區分

    基於當前 LLM 優化器配置生成版本標識
    格式: pm{perfect_match}_st{synthesis_threshold}
    例如: pm90_st80 (perfect_match=0.90, synthesis_threshold=0.80)

    Returns:
        配置版本字符串
    """
    perfect_match = float(os.getenv("PERFECT_MATCH_THRESHOLD", "0.90"))
    synthesis = float(os.getenv("SYNTHESIS_THRESHOLD", "0.80"))

    # 轉換為整數（去掉小數點）
    pm_val = int(perfect_match * 100)
    st_val = int(synthesis * 100)

    return f"pm{pm_val}_st{st_val}"

# Phase 1: 多業者服務實例（懶加載）
_vendor_knowledge_retriever = None
_vendor_param_resolver = None
_vendor_sop_retriever = None


def get_vendor_knowledge_retriever():
    """獲取業者知識檢索器"""
    global _vendor_knowledge_retriever
    if _vendor_knowledge_retriever is None:
        from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
        _vendor_knowledge_retriever = VendorKnowledgeRetrieverV2()
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
        from services.vendor_sop_retriever_v2 import VendorSOPRetrieverV2
        _vendor_sop_retriever = VendorSOPRetrieverV2()
    return _vendor_sop_retriever


def cache_response_and_return(cache_service, vendor_id: int, question: str, response, target_user: str = "tenant"):
    """
    緩存響應並返回（輔助函數）

    Args:
        cache_service: 緩存服務實例
        vendor_id: 業者 ID
        question: 用戶問題
        response: VendorChatResponse 實例
        target_user: 目標用戶角色

    Returns:
        原始 response
    """
    try:
        # 生成配置版本
        config_version = _generate_config_version()

        # 將響應轉換為字典並緩存
        response_dict = response.dict()
        cache_service.cache_answer(
            vendor_id=vendor_id,
            question=question,
            answer_data=response_dict,
            target_user=target_user,
            config_version=config_version
        )
    except Exception as e:
        # 緩存失敗不應影響正常響應
        print(f"⚠️  緩存存儲失敗: {e}")

    return response


# ==================== 輔助函數：SOP 答案格式化 ====================

def _format_sop_answer(sop_items: list, group_name: str = None) -> str:
    """
    直接格式化SOP內容，不經過LLM重組

    保持原始的：
    - item_name（標題）
    - content（內容）
    - 順序

    Args:
        sop_items: SOP項目列表
        group_name: Group名稱（可選）

    Returns:
        格式化後的答案字串
    """
    if not sop_items:
        return "未找到相關的SOP資料。"

    # 構建答案
    parts = []

    # 如果有group_name，添加標題
    if group_name:
        parts.append(f"【{group_name}】\n")

    for idx, sop in enumerate(sop_items, 1):
        item_name = sop.get('item_name', '')
        content = sop.get('content', '').strip()

        # 轉義 Markdown 特殊字符（防止誤渲染）
        # 特別處理波浪號：1~15 不應該被渲染成刪除線
        content = content.replace('~', '\\~')
        item_name = item_name.replace('~', '\\~')

        # 格式化每條SOP（保持原始標題和內容）
        if len(sop_items) == 1:
            # 只有一條，不需要編號
            parts.append(f"{item_name}\n{content}")
        else:
            # 多條，添加編號方便閱讀
            parts.append(f"{idx}. {item_name}\n{content}")

    # 組合答案
    answer = "\n\n".join(parts)

    # 添加友好的結尾
    answer += "\n\n如有任何疑問，歡迎隨時諮詢！"

    return answer


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
    cleaned, _ = _clean_answer_with_tracking(answer, vendor_id, resolver)
    return cleaned


def _clean_answer_with_tracking(answer: str, vendor_id: int, resolver) -> tuple:
    """
    清理答案並替換模板變數（兜底保護），同時追蹤使用的參數

    Args:
        answer: 原始答案
        vendor_id: 業者 ID
        resolver: 參數解析器

    Returns:
        (清理後的答案, 使用的參數 key 列表)
    """
    import re

    # 1. 替換明確的模板變數 {{xxx}} 並追蹤使用的參數
    cleaned, used_params = resolver.resolve_template_with_tracking(answer, vendor_id, raise_on_missing=False)

    # 2. 清理異常格式（已停用，因為會誤刪真實 LINE ID）
    # 注意：@vendorA 可能是真實的 LINE ID，不應該移除
    # cleaned = re.sub(r'@vendor[A-Za-z0-9_]*', '', cleaned)  # ← 已停用

    # 3. 如果仍有未替換的模板變數，記錄警告
    if '{{' in cleaned:
        remaining_vars = re.findall(r'\{\{(\w+)\}\}', cleaned)
        print(f"⚠️  警告：答案中仍有未替換的模板變數: {remaining_vars}")

    return cleaned, used_params


def _remove_duplicate_question(answer: str, question: str) -> str:
    """
    移除答案開頭重複的問題

    有時 LLM 會在答案開頭重複用戶的問題，這個函數會檢測並移除重複的部分。

    Args:
        answer: 原始答案
        question: 用戶問題

    Returns:
        清理後的答案
    """
    if not answer or not question:
        return answer

    # 移除前後空白後比較
    answer_stripped = answer.strip()
    question_stripped = question.strip()

    # 檢查答案是否以問題開頭（允許一些空白差異）
    if answer_stripped.startswith(question_stripped):
        # 移除重複的問題部分
        remaining = answer_stripped[len(question_stripped):].strip()
        print(f"✂️  移除答案中重複的問題: {question_stripped[:50]}...")
        return remaining

    # 檢查是否有換行符分隔（例如：問題\n\n答案）
    lines = answer_stripped.split('\n')
    if lines and lines[0].strip() == question_stripped:
        # 移除第一行（重複的問題）
        remaining = '\n'.join(lines[1:]).strip()
        print(f"✂️  移除答案首行重複的問題: {question_stripped[:50]}...")
        return remaining

    # 沒有檢測到重複，返回原答案
    return answer


# ==================== 輔助函數：表單轉換 ====================

def _convert_form_result_to_response(
    form_result: dict,
    request: VendorChatRequest
) -> VendorChatResponse:
    """
    將表單處理結果轉換為標準 VendorChatResponse

    Args:
        form_result: FormManager 返回的結果字典
        request: 原始請求

    Returns:
        VendorChatResponse 實例
    """
    from datetime import datetime

    return VendorChatResponse(
        answer=form_result.get('answer', ''),
        intent_name=form_result.get('intent_name', '表單填寫'),
        intent_type='form_filling',
        confidence=1.0,  # 表單流程固定高置信度
        action_type='form_fill',
        sources=[] if request.include_sources else None,
        source_count=0,
        vendor_id=request.vendor_id,
        mode=request.mode or 'b2c',
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        # 表單專屬欄位
        form_triggered=form_result.get('form_triggered', False),
        form_completed=form_result.get('form_completed', False),
        form_cancelled=form_result.get('form_cancelled', False),
        form_id=form_result.get('form_id'),
        current_field=form_result.get('current_field'),
        progress=form_result.get('progress'),
        allow_resume=form_result.get('allow_resume', False)
    )


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


def _check_cache(cache_service, vendor_id: int, question: str, target_user: str):
    """檢查緩存，如果命中則返回緩存的答案"""
    # 生成配置版本
    config_version = _generate_config_version()

    cached_answer = cache_service.get_cached_answer(
        vendor_id=vendor_id,
        question=question,
        target_user=target_user,
        config_version=config_version
    )

    if cached_answer:
        print(f"⚡ 緩存命中！直接返回答案（跳過 RAG 處理）- 配置版本: {config_version}")
        return VendorChatResponse(**cached_answer)

    return None


# ==================== 串流輔助函數（2026-02-14）====================

async def _generate_sse_event(event_type: str, data: dict) -> str:
    """生成 Server-Sent Events (SSE) 格式的事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_cached_answer(cached_data: Dict):
    """
    快速串流輸出緩存答案

    當緩存命中時，逐字輸出答案以提供即時反饋
    比直接返回 JSON 更好的用戶體驗

    Args:
        cached_data: 緩存的完整答案數據（VendorChatResponse 格式）

    Yields:
        SSE 格式的事件流
    """
    try:
        # 發送開始事件（標記為緩存）
        yield await _generate_sse_event("start", {
            "cached": True,
            "message": "緩存命中，快速返回答案"
        })

        # 逐字輸出答案
        answer = cached_data.get('answer', '')
        if answer:
            # 按字符分割（中文按字，英文按詞）
            import re
            # 將文本分成詞（中文字、英文詞、標點符號）
            tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+|[^\w\s]|\s+', answer)

            for i, token in enumerate(tokens):
                yield await _generate_sse_event("answer_chunk", {"chunk": token})
                # 輕微延遲以模擬打字效果（10ms）
                await asyncio.sleep(0.01)

        # 發送元數據
        metadata = cached_data.get('metadata', {})
        metadata['cache_hit'] = True
        yield await _generate_sse_event("metadata", metadata)

        # 發送完成事件
        yield await _generate_sse_event("done", {
            "success": True,
            "cached": True,
            "message": "答案輸出完成（來自緩存）"
        })

    except Exception as e:
        print(f"⚠️  串流輸出緩存答案失敗: {e}")
        yield await _generate_sse_event("error", {
            "success": False,
            "error": str(e),
            "message": "串流輸出失敗"
        })


async def stream_response_wrapper(response_dict: dict):
    """
    將 JSON 響應包裝為串流格式

    Args:
        response_dict: VendorChatResponse 的 dict 格式

    Yields:
        SSE 格式的事件流
    """
    try:
        # 發送開始事件
        yield await _generate_sse_event("start", {
            "cached": False,
            "message": "開始輸出答案..."
        })

        # 發送意圖信息
        yield await _generate_sse_event("intent", {
            "intent_type": response_dict.get('intent_type'),
            "intent_name": response_dict.get('intent_name', 'unknown'),
            "confidence": response_dict.get('confidence', 0)
        })

        # 逐字輸出答案
        answer = response_dict.get('answer', '')
        if answer:
            import re
            tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+|[^\w\s]|\s+', answer)

            for token in tokens:
                yield await _generate_sse_event("answer_chunk", {"chunk": token})
                await asyncio.sleep(0.015)  # 15ms 延遲

        # 發送元數據
        metadata = {
            'confidence': response_dict.get('confidence', 0),
            'source_count': response_dict.get('source_count', 0),
            'cache_hit': False,
            'intent_type': response_dict.get('intent_type'),
            'action_type': response_dict.get('action_type'),
            'vendor_id': response_dict.get('vendor_id'),
            'mode': response_dict.get('mode')
        }

        # 添加其他可選字段
        optional_fields = ['video_url', 'video_file_size', 'video_duration', 'video_format',
                          'form_triggered', 'form_completed', 'form_cancelled',
                          'form_id', 'current_field', 'progress', 'allow_resume',
                          'quick_replies', 'sources', 'debug_info']
        for field in optional_fields:
            if field in response_dict and response_dict[field] is not None:
                metadata[field] = response_dict[field]

        yield await _generate_sse_event("metadata", metadata)

        # 發送完成事件
        yield await _generate_sse_event("done", {
            "success": True,
            "cached": False,
            "message": "答案輸出完成"
        })

    except Exception as e:
        print(f"⚠️  串流輸出失敗: {e}")
        yield await _generate_sse_event("error", {
            "success": False,
            "error": str(e),
            "message": "串流輸出失敗"
        })


async def generate_answer_stream(request: 'VendorChatRequest', app_state, intent_result: dict, processing_result: dict):
    """
    生成串流答案（完整 RAG 處理）

    當緩存未命中時，執行完整的 RAG 流程並實時輸出進度

    Args:
        request: 用戶請求
        app_state: FastAPI app state
        intent_result: 意圖分類結果
        processing_result: RAG 處理結果（包含 answer, sources等）

    Yields:
        SSE 格式的事件流
    """
    try:
        # 發送開始事件
        yield await _generate_sse_event("start", {
            "cached": False,
            "message": "開始處理問題..."
        })

        # 發送意圖分類結果
        yield await _generate_sse_event("intent", {
            "intent_type": intent_result.get('intent_type'),
            "intent_name": intent_result.get('intent_name', 'unknown'),
            "confidence": intent_result.get('confidence', 0)
        })

        # 發送檢索進度
        source_count = processing_result.get('source_count', 0)
        yield await _generate_sse_event("search", {
            "source_count": source_count,
            "has_results": source_count > 0
        })

        # 逐字輸出答案
        answer = processing_result.get('answer', '')
        if answer:
            import re
            tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+|[^\w\s]|\s+', answer)

            for token in tokens:
                yield await _generate_sse_event("answer_chunk", {"chunk": token})
                await asyncio.sleep(0.02)  # 20ms 延遲模擬 LLM 生成

        # 發送元數據
        metadata = {
            'confidence': processing_result.get('confidence', 0),
            'source_count': source_count,
            'cache_hit': False,
            'intent_type': intent_result.get('intent_type'),
            'action_type': processing_result.get('action_type')
        }
        yield await _generate_sse_event("metadata", metadata)

        # 發送完成事件
        yield await _generate_sse_event("done", {
            "success": True,
            "cached": False,
            "message": "答案生成完成"
        })

    except Exception as e:
        print(f"⚠️  串流生成答案失敗: {e}")
        yield await _generate_sse_event("error", {
            "success": False,
            "error": str(e),
            "message": "答案生成失敗"
        })


# ==================== 輔助函數：調試資訊構建 ====================

def _build_debug_info(
    processing_path: str,
    intent_result: dict,
    llm_strategy: str = "none",
    sop_candidates: list = None,
    knowledge_candidates: list = None,
    synthesis_info: dict = None,
    vendor_params: dict = None,
    thresholds: dict = None,
    used_param_keys: list = None,  # 實際被使用的參數 key 列表
    system_config: dict = None,  # 額外的系統配置資訊
    comparison_metadata: dict = None  # 🆕 2026-01-28: SOP 與知識庫比較資訊
) -> DebugInfo:
    """構建調試資訊對象"""
    print(f"🔍 [_build_debug_info] sop_candidates received: {type(sop_candidates)}, length: {len(sop_candidates) if sop_candidates else 0}")

    # 構建意圖詳情
    intent_details = IntentDetail(
        primary_intent=intent_result.get('intent_name', ''),
        primary_confidence=intent_result.get('confidence', 0.0),
        secondary_intents=intent_result.get('secondary_intents', []),
        all_intents_with_confidence=intent_result.get('all_intents_with_confidence', [])
    )

    # 構建 SOP 候選列表
    sop_candidates_list = None
    if sop_candidates:
        sop_candidates_list = []
        for candidate in sop_candidates:
            # 兼容兩種格式：資料庫格式(id, item_name) 和 Context 格式(sop_id, sop_name)
            sop_id = candidate.get('id') or candidate.get('sop_id')
            sop_name = candidate.get('item_name') or candidate.get('sop_name')

            # 跳過無效的候選（id 或 item_name 為 None）
            if sop_id is None or sop_name is None:
                continue

            sop_candidates_list.append(CandidateSOP(
                id=sop_id,
                item_name=sop_name,
                group_name=candidate.get('group_name'),
                base_similarity=candidate.get('base_similarity', candidate.get('original_similarity', 0.0)),
                intent_boost=candidate.get('intent_boost', 1.0),
                boosted_similarity=candidate.get('boosted_similarity', candidate.get('similarity', 0.0)),
                rerank_score=candidate.get('rerank_score'),
                is_selected=candidate.get('is_selected', False)
            ))

    # 構建知識庫候選列表
    knowledge_candidates_list = None
    if knowledge_candidates:
        knowledge_candidates_list = []
        for k in knowledge_candidates:
            knowledge_candidates_list.append(CandidateKnowledge(
                id=k.get('id'),
                question_summary=k.get('question_summary', ''),
                scope=k.get('scope', ''),
                base_similarity=k.get('base_similarity', k.get('original_similarity', 0.0)),
                rerank_score=k.get('rerank_score'),
                intent_boost=k.get('intent_boost', 1.0),
                intent_semantic_similarity=k.get('intent_semantic_similarity'),
                priority=k.get('priority'),
                priority_boost=k.get('priority_boost', 0.0),
                boosted_similarity=k.get('boosted_similarity', k.get('similarity', 0.0)),
                intent_type=k.get('intent_type'),
                is_selected=k.get('is_selected', False)
            ))

    # 構建合成資訊
    synthesis_info_obj = None
    if synthesis_info:
        synthesis_info_obj = SynthesisInfo(**synthesis_info)

    # 構建業者參數列表（只顯示實際被注入的參數）
    vendor_params_injected = []
    if vendor_params:
        # 如果有指定 used_param_keys，只顯示被使用的參數
        if used_param_keys is not None:
            for key in used_param_keys:
                if key in vendor_params:
                    param = vendor_params[key]
                    if isinstance(param, dict) and param.get('value'):
                        vendor_params_injected.append(VendorParamInjected(
                            param_key=key,
                            display_name=param.get('display_name', key),
                            value=str(param.get('value', '')),
                            unit=param.get('unit')
                        ))
        else:
            # 如果沒有指定，顯示所有有值的參數（向後兼容）
            for key, param in vendor_params.items():
                if isinstance(param, dict) and param.get('value'):
                    vendor_params_injected.append(VendorParamInjected(
                        param_key=key,
                        display_name=param.get('display_name', key),
                        value=str(param.get('value', '')),
                        unit=param.get('unit')
                    ))

    # 構建閾值資訊
    if thresholds is None:
        thresholds = {
            'sop_threshold': float(os.getenv('SOP_SIMILARITY_THRESHOLD', '0.75')),
            'knowledge_retrieval_threshold': float(os.getenv('KB_SIMILARITY_THRESHOLD', '0.55')),
            'high_quality_threshold': float(os.getenv('HIGH_QUALITY_THRESHOLD', '0.8'))
        }

    # 構建系統配置狀態
    system_config_default = {
        'llm_strategies': {
            'perfect_match': {
                'enabled': True,
                'threshold': float(os.getenv('PERFECT_MATCH_THRESHOLD', '0.90'))
            },
            'synthesis': {
                'enabled': os.getenv('ENABLE_ANSWER_SYNTHESIS', 'true').lower() == 'true',
                'threshold': float(os.getenv('SYNTHESIS_THRESHOLD', '0.80'))
            },
            'fast_path': {
                'enabled': True,  # 預設啟用
                'threshold': float(os.getenv('FAST_PATH_THRESHOLD', '0.75'))
            },
            'template': {
                'enabled': True  # 預設啟用
            },
            'llm': {
                'enabled': True  # 總是啟用
            }
        },
        'processing_paths': {
            'sop': {'enabled': True, 'threshold': float(os.getenv('SOP_SIMILARITY_THRESHOLD', '0.75'))},
            'knowledge': {'enabled': True, 'threshold': float(os.getenv('KB_SIMILARITY_THRESHOLD', '0.55'))},
            'unclear': {'enabled': True},
            'param_answer': {'enabled': True},
            'no_knowledge_found': {'enabled': True}
        }
    }

    # 合併外部傳入的 system_config
    if system_config:
        system_config_default.update(system_config)

    return DebugInfo(
        processing_path=processing_path,
        sop_candidates=sop_candidates_list,
        knowledge_candidates=knowledge_candidates_list,
        intent_details=intent_details,
        llm_strategy=llm_strategy,
        synthesis_info=synthesis_info_obj,
        vendor_params_injected=vendor_params_injected,
        thresholds=thresholds,
        system_config=system_config_default,
        comparison_metadata=comparison_metadata  # 🆕 2026-01-28: 比較資訊
    )


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


# ==================== 智能檢索：SOP 與知識庫同時檢索 + 分數比較 ====================

async def _smart_retrieval_with_comparison(
    request: VendorChatRequest,
    intent_result: dict,
    sop_orchestrator,
    resolver
) -> dict:
    """
    智能檢索：SOP 與知識庫同時檢索 + 分數比較

    核心規則：
    1. SOP 和知識庫永遠不混合
    2. 答案合成只用於知識庫
    3. SOP 有後續動作時優先處理
    4. 使用 Reranker 後的分數進行公平比較

    Args:
        request: 聊天請求
        intent_result: 意圖分類結果
        sop_orchestrator: SOP 編排器
        resolver: 參數解析器

    Returns:
        {
            'type': 'sop' | 'knowledge' | 'none',
            'sop_result': SOP 結果 (或 None),
            'knowledge_list': 知識列表 (或 None),
            'reason': 決策原因,
            'comparison': {
                'sop_score': float,
                'knowledge_score': float,
                'gap': float,
                'sop_candidates': int,
                'knowledge_candidates': int,
                'decision_case': str
            }
        }
    """
    import asyncio

    # ==================== Step 1: 同時檢索 ====================
    print(f"\n{'='*80}")
    print(f"🔍 [智能檢索] 同時檢索 SOP 和知識庫")
    print(f"{'='*80}")

    # 獲取意圖 ID
    intent_id = None
    if intent_result['intent_name'] != 'unclear':
        try:
            intent_id = _get_intent_id(intent_result['intent_name'])
        except:
            intent_id = None

    primary_intent_id = intent_result.get('intent_ids', [None])[0] if intent_result.get('intent_ids') else None

    # 並行執行 SOP 和知識庫檢索
    sop_task = sop_orchestrator.process_message(
        user_message=request.message,
        session_id=request.session_id,
        user_id=request.user_id or "unknown",
        vendor_id=request.vendor_id,
        intent_id=primary_intent_id,
        intent_ids=intent_result.get('intent_ids', [])
    )

    knowledge_task = _retrieve_knowledge(
        request=request,
        intent_id=intent_id,
        intent_result=intent_result
    )

    # 等待兩個都完成
    sop_result, knowledge_list = await asyncio.gather(
        sop_task,
        knowledge_task
    )

    # ==================== Step 2: 提取最高分 ====================
    sop_score = 0.0
    sop_has_action = False
    sop_has_response = False

    if sop_result and sop_result.get('has_sop'):
        sop_item = sop_result.get('sop_item', {})
        sop_score = sop_item.get('similarity', 0.0)
        sop_has_response = sop_result.get('response') is not None

        # 檢查是否有後續動作
        next_action = sop_item.get('next_action')
        sop_has_action = next_action in ['form_fill', 'api_call', 'form_then_api']

    knowledge_score = 0.0
    knowledge_count = 0
    high_quality_count = 0  # 用於判斷是否合成

    if knowledge_list:
        knowledge_score = knowledge_list[0].get('similarity', 0.0)
        knowledge_count = len(knowledge_list)
        # 統計高品質結果（相似度 > 0.8）
        high_quality_count = len([k for k in knowledge_list if k.get('similarity', 0) > 0.8])

    # ==================== Step 3: 決策邏輯 ====================
    SCORE_GAP_THRESHOLD = 0.15  # 差距閾值
    SOP_MIN_THRESHOLD = 0.55
    KNOWLEDGE_MIN_THRESHOLD = 0.6

    print(f"\n📊 [分數比較]")
    print(f"   SOP:      {sop_score:.3f} (有後續動作: {sop_has_action}, 有回應: {sop_has_response})")
    print(f"   知識庫:   {knowledge_score:.3f} (數量: {knowledge_count}, 高品質: {high_quality_count})")
    print(f"   差距:     {abs(sop_score - knowledge_score):.3f}")

    # 🆕 特殊情況 0A：SOP 被用戶取消（cancelled）
    if sop_result and sop_result.get('has_sop'):
        trigger_result = sop_result.get('trigger_result', {})
        if trigger_result.get('cancelled'):
            print(f"🚫 [特殊情況] 用戶取消 SOP 動作，返回禮貌回應")
            return {
                'type': 'sop',
                'sop_result': sop_result,
                'knowledge_list': knowledge_list,
                'reason': '用戶取消 SOP 動作',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': abs(sop_score - knowledge_score),
                    'sop_candidates': len(sop_result.get('all_sop_candidates', [])) if sop_result else 0,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'sop_cancelled_by_user'
                }
            }

    # 🆕 特殊情況 0B：SOP 已觸發並執行後續動作（action_result 存在）
    # 這種情況下，無論 similarity 分數如何，都應該優先返回 SOP 的結果（包括錯誤訊息）
    if sop_result and sop_result.get('has_sop') and sop_result.get('action_result'):
        trigger_result = sop_result.get('trigger_result', {})
        if trigger_result.get('matched'):
            print(f"⚡ [特殊情況] SOP 已觸發並執行後續動作，優先返回 SOP 結果")
            return {
                'type': 'sop',
                'sop_result': sop_result,
                'knowledge_list': knowledge_list,
                'reason': 'SOP 關鍵詞匹配並已執行後續動作',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': abs(sop_score - knowledge_score),
                    'sop_candidates': len(sop_result.get('all_sop_candidates', [])) if sop_result else 0,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'sop_triggered_action_executed'
                }
            }

    # 特殊情況：SOP 等待關鍵詞（response 為 None）
    if sop_result and sop_result.get('has_sop') and not sop_has_response:
        print(f"⏸️  [特殊情況] SOP 等待關鍵詞中，繼續其他流程")
        # 這種情況下，即使 SOP 分數高，也應該讓知識庫回答
        gap = abs(knowledge_score - sop_score)
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
            return {
                'type': 'knowledge',
                'sop_result': sop_result,  # ✅ 保留 SOP 結果用於比較顯示
                'knowledge_list': knowledge_list,
                'reason': f'SOP 等待關鍵詞，使用知識庫 ({knowledge_score:.3f})',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': gap,
                    'sop_candidates': sop_candidates,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'sop_waiting_for_keyword_use_knowledge'
                }
            }
        else:
            return {
                'type': 'none',
                'sop_result': sop_result,  # ✅ 保留 SOP 結果用於比較顯示
                'knowledge_list': knowledge_list,  # ✅ 保留知識庫結果用於比較顯示
                'reason': 'SOP 等待關鍵詞且知識庫未達標',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': gap,
                    'sop_candidates': sop_candidates,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'sop_waiting_both_below_threshold'
                }
            }

    # Case 1: SOP 顯著更高
    if (sop_score >= SOP_MIN_THRESHOLD and
        sop_score > knowledge_score + SCORE_GAP_THRESHOLD):
        print(f"✅ [決策] SOP 顯著更相關 ({sop_score:.3f} > {knowledge_score:.3f} + 0.15)")

        gap = sop_score - knowledge_score
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        return {
            'type': 'sop',
            'sop_result': sop_result,
            'knowledge_list': knowledge_list,  # ✅ 保留知識庫結果用於比較顯示
            'reason': f'SOP 分數顯著更高 ({sop_score:.3f} vs {knowledge_score:.3f})',
            'comparison': {
                'sop_score': sop_score,
                'knowledge_score': knowledge_score,
                'gap': gap,
                'sop_candidates': sop_candidates,
                'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                'decision_case': 'sop_significantly_higher'
            }
        }

    # Case 2: 知識庫顯著更高
    if (knowledge_score >= KNOWLEDGE_MIN_THRESHOLD and
        knowledge_score > sop_score + SCORE_GAP_THRESHOLD):
        print(f"✅ [決策] 知識庫顯著更相關 ({knowledge_score:.3f} > {sop_score:.3f} + 0.15)")
        print(f"   將進行答案合成判斷（高品質數量: {high_quality_count}）")

        gap = knowledge_score - sop_score
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        return {
            'type': 'knowledge',
            'sop_result': sop_result,  # ✅ 保留 SOP 結果用於比較顯示
            'knowledge_list': knowledge_list,
            'reason': f'知識庫分數顯著更高 ({knowledge_score:.3f} vs {sop_score:.3f})',
            'comparison': {
                'sop_score': sop_score,
                'knowledge_score': knowledge_score,
                'gap': gap,
                'sop_candidates': sop_candidates,
                'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                'decision_case': 'knowledge_significantly_higher'
            }
        }

    # Case 3: 分數接近（差距 < 0.15）
    if (sop_score >= SOP_MIN_THRESHOLD and
        knowledge_score >= KNOWLEDGE_MIN_THRESHOLD):
        gap = abs(sop_score - knowledge_score)
        print(f"⚖️  [決策] 分數接近 (差距: {gap:.3f} < 0.15)")

        # 3.1: SOP 有後續動作 → 優先 SOP
        if sop_has_action:
            sop_item = sop_result.get('sop_item', {})
            print(f"✅ [優先級] SOP 有後續動作，優先處理 ({sop_item.get('next_action')})")

            sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

            return {
                'type': 'sop',
                'sop_result': sop_result,
                'knowledge_list': knowledge_list,  # ✅ 保留知識庫結果
                'reason': f'SOP 有後續動作 ({sop_item.get("next_action")})',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': gap,
                    'sop_candidates': sop_candidates,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'close_scores_sop_has_action'
                }
            }

        # 3.2: SOP 無動作 → 選分數更高的
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        if sop_score > knowledge_score:
            print(f"✅ [比較] SOP 分數略高 ({sop_score:.3f} > {knowledge_score:.3f})")
            return {
                'type': 'sop',
                'sop_result': sop_result,
                'knowledge_list': knowledge_list,  # ✅ 保留知識庫結果
                'reason': f'分數接近但 SOP 略高 ({sop_score:.3f} vs {knowledge_score:.3f})',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': gap,
                    'sop_candidates': sop_candidates,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'close_scores_sop_slightly_higher'
                }
            }
        else:
            print(f"✅ [比較] 知識庫分數略高 ({knowledge_score:.3f} > {sop_score:.3f})")
            return {
                'type': 'knowledge',
                'sop_result': sop_result,  # ✅ 保留 SOP 結果
                'knowledge_list': knowledge_list,
                'reason': f'分數接近但知識庫略高 ({knowledge_score:.3f} vs {sop_score:.3f})',
                'comparison': {
                    'sop_score': sop_score,
                    'knowledge_score': knowledge_score,
                    'gap': gap,
                    'sop_candidates': sop_candidates,
                    'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                    'decision_case': 'close_scores_knowledge_slightly_higher'
                }
            }

    # Case 4: 只有 SOP 達標
    if sop_score >= SOP_MIN_THRESHOLD:
        print(f"✅ [決策] 只有 SOP 達標 ({sop_score:.3f} >= 0.55)")

        gap = abs(sop_score - knowledge_score)
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        return {
            'type': 'sop',
            'sop_result': sop_result,
            'knowledge_list': knowledge_list,  # ✅ 保留知識庫結果
            'reason': f'只有 SOP 達標 ({sop_score:.3f})',
            'comparison': {
                'sop_score': sop_score,
                'knowledge_score': knowledge_score,
                'gap': gap,
                'sop_candidates': sop_candidates,
                'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                'decision_case': 'only_sop_qualified'
            }
        }

    # Case 5: 只有知識庫達標
    if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
        print(f"✅ [決策] 只有知識庫達標 ({knowledge_score:.3f} >= 0.6)")

        gap = abs(knowledge_score - sop_score)
        sop_candidates = len(sop_result.get('all_sop_candidates', [])) if sop_result else 0

        return {
            'type': 'knowledge',
            'sop_result': sop_result,  # ✅ 保留 SOP 結果
            'knowledge_list': knowledge_list,
            'reason': f'只有知識庫達標 ({knowledge_score:.3f})',
            'comparison': {
                'sop_score': sop_score,
                'knowledge_score': knowledge_score,
                'gap': gap,
                'sop_candidates': sop_candidates,
                'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
                'decision_case': 'only_knowledge_qualified'
            }
        }

    # Case 6: 都不達標
    print(f"⚠️  [決策] SOP ({sop_score:.3f}) 和知識庫 ({knowledge_score:.3f}) 都未達標")

    gap = abs(sop_score - knowledge_score)
    sop_candidates = len(sop_result.get('retrieved_sops', [])) if sop_result else 0

    return {
        'type': 'none',
        'sop_result': sop_result,  # ✅ 保留兩邊結果供前端顯示
        'knowledge_list': knowledge_list,
        'reason': '都未達到最低閾值',
        'comparison': {
            'sop_score': sop_score,
            'knowledge_score': knowledge_score,
            'gap': gap,
            'sop_candidates': sop_candidates,
            'knowledge_candidates': len(knowledge_list) if knowledge_list else 0,
            'decision_case': 'both_below_threshold'
        }
    }


async def _build_orchestrator_response(
    request: VendorChatRequest,
    req: Request,
    orchestrator_result: dict,
    resolver,
    vendor_info: dict,
    cache_service,
    decision: dict = None  # 🆕 智能檢索決策資訊（包含比較元數據）
):
    """
    使用 SOP Orchestrator 結果構建回應

    支持：
    1. none 模式：純資訊回應
    2. manual/immediate 模式：等待用戶確認或後續匹配
    3. 觸發後續動作：form_fill / api_call / form_then_api
    """
    sop_item = orchestrator_result.get('sop_item', {}) or {}
    trigger_result = orchestrator_result.get('trigger_result', {}) or {}
    action_result = orchestrator_result.get('action_result', {}) or {}

    # 構建回應訊息
    response_text = orchestrator_result.get('response', '')

    # 處理參數替換
    if response_text:
        final_answer, used_param_keys = _clean_answer_with_tracking(
            response_text, request.vendor_id, resolver
        )
    else:
        final_answer = "SOP 處理完成。"
        used_param_keys = []

    # 構建來源資訊
    sources = []
    if request.include_sources and sop_item and sop_item.get('id'):
        sources = [KnowledgeSource(
            id=sop_item.get('id'),
            question_summary=sop_item.get('item_name', 'SOP'),
            answer=sop_item.get('content', ''),
            scope='vendor_sop'
        )]

    # 構建調試資訊
    debug_info = None
    if request.include_debug_info:
        vendor_params = resolver.get_vendor_parameters(request.vendor_id)

        # 構建 Orchestrator 特定的調試資訊
        orchestrator_info = {
            'trigger_mode': trigger_result.get('trigger_mode'),
            'action': trigger_result.get('action'),
            'context_saved': trigger_result.get('context_saved'),
            'next_action': action_result.get('action_type') if action_result else None
        }

        # 🆕 獲取所有候選結果（包含 Reranker 分數）
        all_sop_candidates = orchestrator_result.get('all_sop_candidates', [])
        selected_id = sop_item.get('id')

        sop_candidates_debug = []
        for idx, candidate in enumerate(all_sop_candidates):
            debug_item = {
                'id': candidate.get('id'),
                'item_name': candidate.get('item_name'),
                'group_name': candidate.get('group_name', ''),
                'base_similarity': candidate.get('original_similarity', candidate.get('similarity', 0)),  # 原始向量相似度
                'intent_boost': 1.0,  # SOP 不使用意圖加成
                'boosted_similarity': candidate.get('similarity', 0),  # Reranker 加成後的最終分數
                'is_selected': candidate.get('id') == selected_id
            }
            # 🆕 只在有 Reranker 分數時才添加（避免 None 導致前端混淆）
            if 'rerank_score' in candidate and candidate['rerank_score'] is not None:
                debug_item['rerank_score'] = candidate['rerank_score']
            sop_candidates_debug.append(debug_item)

        # 🆕 如果有 decision，從中提取 comparison_metadata
        comparison_metadata = None
        knowledge_candidates_debug = None
        if decision:
            comparison_metadata = decision.get('comparison')
            # 如果有知識庫候選，也一併提供（即使選擇了 SOP）
            if decision.get('knowledge_list'):
                knowledge_candidates_debug = []
                for k in decision['knowledge_list']:
                    knowledge_candidates_debug.append({
                        'id': k.get('id'),
                        'question_summary': k.get('question_summary', ''),
                        'scope': k.get('scope', 'global'),
                        'base_similarity': k.get('base_similarity', 0.0),
                        'rerank_score': k.get('rerank_score'),
                        'intent_boost': k.get('intent_boost', 1.0),
                        'intent_semantic_similarity': k.get('intent_semantic_similarity'),
                        'priority': k.get('priority', 0),
                        'priority_boost': k.get('priority_boost', 0.0),
                        'boosted_similarity': k.get('similarity', 0.0),
                        'intent_type': k.get('intent_type'),
                        'is_selected': False  # SOP 被選中，知識庫未被選中
                    })

        debug_info = _build_debug_info(
            processing_path='sop_orchestrator',
            intent_result={'intent_name': 'sop', 'confidence': 1.0},
            llm_strategy='orchestrated',
            sop_candidates=sop_candidates_debug if sop_candidates_debug else [{
                'id': sop_item.get('id'),
                'item_name': sop_item.get('item_name'),
                'group_name': sop_item.get('group_name', ''),
                'base_similarity': sop_item.get('similarity', 1.0),
                'intent_boost': 1.0,
                'boosted_similarity': sop_item.get('similarity', 1.0),
                'is_selected': True
            }] if sop_item else [],
            knowledge_candidates=knowledge_candidates_debug,  # 🆕 添加知識庫候選
            vendor_params=vendor_params,
            used_param_keys=used_param_keys,
            system_config={'orchestrator': orchestrator_info},
            comparison_metadata=comparison_metadata  # 🆕 添加比較元數據
        )

    # 獲取意圖資訊（從檢索結果或使用預設）
    intent_classifier = req.app.state.intent_classifier
    intent_result = intent_classifier.classify(request.message)

    # 提取表單資訊（如果有）
    form_triggered = False
    form_id = None
    current_field = None
    progress = None

    if action_result:
        action_type = action_result.get('action_type')

        # 如果是表單相關的動作類型
        if action_type in ['form_fill', 'form_then_api']:
            form_session = action_result.get('form_session')
            if form_session:
                form_triggered = True
                form_id = form_session.get('form_id')
                current_field = action_result.get('current_field')

                # 計算進度
                if form_session.get('current_field_index') is not None and form_session.get('total_fields'):
                    current_index = form_session['current_field_index']
                    total_fields = form_session['total_fields']
                    progress = f"{current_index + 1}/{total_fields}"

    # 構建快速回復按鈕（immediate 模式）
    quick_replies = None
    if orchestrator_result.get('next_step') == 'waiting_for_confirmation':
        quick_replies = [
            QuickReply(text="✅ 要，立即處理", value="要", style="primary"),
            QuickReply(text="❌ 不用，謝謝", value="不用", style="secondary")
        ]

    response = VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        action_type='direct_answer',
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=sources if request.include_sources else None,
        source_count=1 if sop_item else 0,
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        form_triggered=form_triggered,
        form_id=form_id,
        current_field=current_field,
        progress=progress,
        quick_replies=quick_replies,
        debug_info=debug_info
    )

    return cache_response_and_return(
        cache_service, request.vendor_id, request.message, response, request.target_user
    )


async def _build_sop_response(
    request: VendorChatRequest,
    req: Request,
    intent_result: dict,
    sop_items: list,
    resolver,
    vendor_info: dict,
    cache_service
):
    """使用 SOP 構建回應 - 直接返回原始SOP，不經過LLM重組"""

    # 提取group_name（Group隔離後所有SOP都來自同一個Group）
    group_name = None
    if sop_items and sop_items[0].get('group_name'):
        group_name = sop_items[0]['group_name']

    # 直接格式化SOP內容，保持原始標題和內容
    raw_answer = _format_sop_answer(sop_items, group_name)

    # 清理答案並替換模板變數（處理 {{service_hotline}} 等參數），同時追蹤使用的參數
    final_answer, used_param_keys = _clean_answer_with_tracking(raw_answer, request.vendor_id, resolver)

    # 構建來源列表
    sources = []
    if request.include_sources:
        sources = [KnowledgeSource(
            id=sop['id'],
            question_summary=sop['item_name'],
            answer=sop['content'],
            scope='vendor_sop'
        ) for sop in sop_items]

    # 構建調試資訊（如果請求了）
    debug_info = None
    if request.include_debug_info:
        # 獲取業者參數
        vendor_params = resolver.get_vendor_parameters(request.vendor_id)

        # 構建 SOP 候選列表
        sop_candidates_debug = []
        for sop in sop_items:
            similarity = sop.get('similarity', 1.0)
            sop_candidates_debug.append({
                'id': sop['id'],
                'item_name': sop['item_name'],
                'group_name': sop.get('group_name', ''),
                'base_similarity': similarity,
                'intent_boost': 1.0,  # SOP 不使用意圖加成
                'boosted_similarity': similarity,  # 與 base_similarity 相同（boost=1.0）
                'is_selected': True  # SOP 全部選取
            })

        # 構建 SOP 合成資訊（多個 SOP 項目組合）
        synthesis_info_dict = None
        if len(sop_items) > 1:
            synthesis_info_dict = {
                'sources_count': len(sop_items),
                'sources_ids': [sop['id'] for sop in sop_items],
                'synthesis_reason': f'組合 {len(sop_items)} 個 SOP 項目（{group_name}）'
            }

        debug_info = _build_debug_info(
            processing_path='sop',
            intent_result=intent_result,
            llm_strategy='direct',  # SOP 直接返回，不經過 LLM
            sop_candidates=sop_candidates_debug,
            synthesis_info=synthesis_info_dict,
            vendor_params=vendor_params,
            used_param_keys=used_param_keys  # ✅ 只顯示實際被注入的參數
        )

    response = VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        action_type='direct_answer',
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=sources if request.include_sources else None,
        source_count=len(sop_items),
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        debug_info=debug_info
    )

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.target_user)


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
            scope=r.get('scope', 'global'),  # ✅ 使用實際 scope
            vendor_ids=r.get('vendor_ids'),  # ✅ 添加 vendor_ids
            target_users=r.get('target_user')  # ✅ 添加 target_users
        ) for r in rag_results]

    # 清理答案並替換模板變數（兜底保護），同時追蹤使用的參數
    final_answer, used_param_keys = _clean_answer_with_tracking(optimization_result['optimized_answer'], request.vendor_id, resolver)

    # 移除答案中重複的問題（LLM 有時會在答案開頭重複問題）
    final_answer = _remove_duplicate_question(final_answer, request.message)

    # 構建調試資訊（如果請求了）
    debug_info = None
    if request.include_debug_info:
        # 標記哪些知識被選取了
        selected_ids = {r['id'] for r in rag_results[:optimization_result.get('sources_used', len(rag_results))]}
        knowledge_candidates_debug = []
        for r in rag_results:
            knowledge_candidates_debug.append({
                'id': r['id'],
                'question_summary': r.get('question_summary', ''),
                'scope': r.get('scope', 'global'),
                'base_similarity': r.get('similarity', 0.0),
                'rerank_score': r.get('rerank_score'),  # ← 新增：Rerank 分數
                'intent_boost': 1.0,  # RAG fallback 沒有 intent boost
                'boosted_similarity': r.get('similarity', 0.0),
                'intent_type': r.get('intent_type'),
                'priority': r.get('priority'),
                'is_selected': r['id'] in selected_ids
            })

        # 構建合成資訊
        synthesis_info_dict = None
        if optimization_result.get('synthesis_applied'):
            synthesis_info_dict = {
                'sources_count': len(rag_results),
                'sources_ids': [r['id'] for r in rag_results],
                'synthesis_reason': 'RAG fallback 使用答案合成'
            }

        debug_info = _build_debug_info(
            processing_path='rag_fallback',
            intent_result=intent_result,
            llm_strategy=optimization_result.get('optimization_method', 'unknown'),
            knowledge_candidates=knowledge_candidates_debug,
            synthesis_info=synthesis_info_dict,
            vendor_params=vendor_params,
            used_param_keys=used_param_keys  # ✅ 只顯示實際被注入的參數
        )

    response = VendorChatResponse(
        answer=final_answer,
        intent_name=intent_name or intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        action_type='direct_answer',
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        sources=sources if request.include_sources else None,
        source_count=len(rag_results),
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        debug_info=debug_info
    )

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.target_user)


# ==================== 輔助函數：知識庫檢索 ====================

async def _retrieve_knowledge(
    request: VendorChatRequest,
    intent_id: Optional[int],
    intent_result: dict
):
    """
    檢索知識庫（混合模式：intent + 向量相似度 + 語義匹配）

    ✅ 選項1實施：統一檢索路徑
    - 降低閾值到 0.55（原 RAG fallback 的閾值）
    - 使用語義匹配動態計算 intent_boost
    - 不再需要獨立的 RAG fallback 路徑
    - 支持 intent_id = None（unclear 情況，無意圖加成）
    """
    retriever = get_vendor_knowledge_retriever()
    # unclear 時 intent_id = None，all_intent_ids = []
    all_intent_ids = intent_result.get('intent_ids', [] if intent_id is None else [intent_id])

    # ✅ 選項1：統一閾值為 0.55（涵蓋原 knowledge + rag_fallback 範圍）
    # 環境變數向後兼容，但默認值改為 0.55
    kb_similarity_threshold = float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.55"))

    knowledge_list = await retriever.retrieve_knowledge_hybrid(
        query=request.message,
        intent_id=intent_id,
        vendor_id=request.vendor_id,
        top_k=request.top_k,
        similarity_threshold=kb_similarity_threshold,
        all_intent_ids=all_intent_ids,
        target_user=request.target_user,
        return_debug_info=request.include_debug_info
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
    """
    處理找不到知識的情況：參數答案 > 兜底回應

    ✅ 選項1實施：移除獨立的 RAG fallback 路徑
    - Knowledge 路徑已降低閾值到 0.55（涵蓋原 RAG fallback 範圍）
    - 使用語義匹配確保相關知識不會被遺漏
    - 簡化流程：參數答案 → 兜底回應

    ⭐ 設計原則：內容優先於資料收集
    - 需要表單的場景應在知識庫中配置 action_type=form_fill
    - 不在此處進行意圖表單映射（避免繞過知識庫內容）
    """
    # Step 1: 優先檢查是否為參數型問題（沒有知識庫時的備選方案）
    from routers.chat_shared import check_param_question
    param_category, param_answer = await check_param_question(
        vendor_config_service=req.app.state.vendor_config_service,
        question=request.message,
        vendor_id=request.vendor_id
    )

    if param_answer:
        print(f"   ℹ️  知識庫無結果，使用參數型答案（category={param_category}）")

        # 構建調試資訊（如果請求了）
        debug_info = None
        if request.include_debug_info:
            # 獲取業者參數
            vendor_params = resolver.get_vendor_parameters(request.vendor_id)

            debug_info = _build_debug_info(
                processing_path='param_answer',
                intent_result=intent_result,
                llm_strategy='param_query',  # 參數查詢
                vendor_params=vendor_params
            )

        response = VendorChatResponse(
            answer=param_answer['answer'],
            intent_name="參數查詢",
            intent_type="config_param",
            confidence=1.0,
            action_type='direct_answer',
            sources=[],
            source_count=0,
            vendor_id=request.vendor_id,
            mode=request.mode,
            timestamp=datetime.utcnow().isoformat() + "Z",
            video_url=None,
            debug_info=debug_info
        )
        return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.target_user)

    # ✅ 選項1：移除 Step 2 (RAG fallback)
    # 原因：Knowledge 路徑已降低閾值到 0.55 並使用語義匹配
    # 不再需要獨立的降級檢索路徑

    # Step 2: 記錄測試場景並返回兜底回應
    print(f"   ❌ 知識庫沒有找到相關知識（閾值: 0.55，已含語義匹配）")
    await _record_no_knowledge_scenario(request, intent_result, req)

    params = resolver.get_vendor_parameters(request.vendor_id)

    # 使用模板格式以便追蹤參數使用
    fallback_answer = "我目前沒有找到符合您問題的資訊，但我可以協助您轉給客服處理。如需立即協助，請撥打客服專線 {{service_hotline}}。請問您方便提供更詳細的內容嗎？"

    # 清理答案並追蹤使用的參數
    final_answer, used_param_keys = _clean_answer_with_tracking(fallback_answer, request.vendor_id, resolver)

    # 構建調試資訊（如果請求了）
    debug_info = None
    if request.include_debug_info:
        debug_info = _build_debug_info(
            processing_path='no_knowledge_found',
            intent_result=intent_result,
            llm_strategy='fallback',  # 兜底回應
            vendor_params=params,
            used_param_keys=used_param_keys  # ✅ 只顯示實際被注入的參數
        )

    return VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        action_type='direct_answer',
        sources=[] if request.include_sources else None,
        source_count=0,
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        debug_info=debug_info
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
    cache_service,
    decision: dict = None  # 🆕 智能檢索決策資訊（包含 SOP 結果和比較元數據）
):
    """使用知識庫結果構建優化回應"""
    llm_optimizer = req.app.state.llm_answer_optimizer
    confidence_evaluator = req.app.state.confidence_evaluator

    # ⭐ 步驟 1：優先檢查表單類型（表單直接使用，不需閾值）
    if knowledge_list:
        best_knowledge = knowledge_list[0]  # 已按相似度排序
        action_type = best_knowledge.get('action_type', 'direct_answer')
        form_id = best_knowledge.get('form_id')

        # 如果最高順位是表單類型，直接使用
        if action_type == 'form_fill' or form_id:
            print(f"📝 [表單優先] 最高順位知識 ID {best_knowledge['id']} 是表單類型，直接使用")
            print(f"   action_type={action_type}, form_id={form_id}, similarity={best_knowledge.get('similarity', 0):.3f}")
            filtered_knowledge_list = [best_knowledge]  # 直接使用，無需閾值檢查
        else:
            # ⭐ 步驟 2：非表單知識才需要質量檢查
            high_quality_threshold = float(os.getenv("HIGH_QUALITY_THRESHOLD", "0.8"))
            filtered_knowledge_list = [k for k in knowledge_list if k.get('similarity', 0) >= high_quality_threshold]

            if len(filtered_knowledge_list) < len(knowledge_list):
                print(f"🔍 [高質量過濾] 原始: {len(knowledge_list)} 個候選知識, 過濾後: {len(filtered_knowledge_list)} 個 (閾值: {high_quality_threshold})")
                for k in knowledge_list[:3]:  # 只顯示前3個
                    status = "✅" if k.get('similarity', 0) >= high_quality_threshold else "❌"
                    print(f"   {status} ID {k['id']}: similarity={k.get('similarity', 0):.3f}")
    else:
        filtered_knowledge_list = []

    # 如果過濾後沒有知識，返回找不到知識的響應
    if not filtered_knowledge_list:
        print(f"⚠️  沒有符合條件的知識，嘗試參數答案或兜底回應...")
        return await _handle_no_knowledge_found(
            request, req, intent_result, resolver, cache_service, vendor_info
        )

    # ⭐ 步驟 3：處理過濾後的知識（可能是表單或一般知識）
    best_knowledge = filtered_knowledge_list[0]
    action_type = best_knowledge.get('action_type', 'direct_answer')
    print(f"🎯 [action_type] 知識 {best_knowledge['id']} 的 action_type: {action_type}, similarity: {best_knowledge.get('similarity', 0):.3f}")

    # 處理不同的 action_type
    if action_type == 'form_fill' or (action_type == 'direct_answer' and best_knowledge.get('form_id')):
        # 場景 B: 表單 + 知識答案
        # 或向後兼容：檢查 form_id（舊架構）
        form_id = best_knowledge.get('form_id')
        trigger_mode = best_knowledge.get('trigger_mode', 'auto')  # 默認為 auto（保持向後兼容）

        if not form_id:
            print(f"⚠️  action_type={action_type} 但缺少 form_id，降級為 direct_answer")
            action_type = 'direct_answer'  # 明確降級
        elif not request.session_id or not request.user_id:
            print(f"⚠️  知識 {best_knowledge['id']} 需要表單，但缺少 session_id 或 user_id，降級為 direct_answer")
            action_type = 'direct_answer'  # 明確降級
        else:
            print(f"📝 [表單觸發] 知識 {best_knowledge['id']} 關聯表單 {form_id}，trigger_mode={trigger_mode}")

            # ========================================
            # 根據 trigger_mode 處理表單觸發
            # ========================================

            if trigger_mode in ['manual', 'immediate']:
                # 排查型/行動型：使用 SOP Orchestrator 處理關鍵詞匹配
                print(f"   ✅ 使用 SOP Orchestrator 處理 trigger_mode={trigger_mode}")

                # 將知識庫項目轉換為 SOP 格式
                knowledge_as_sop = {
                    'id': best_knowledge['id'],
                    'item_name': best_knowledge.get('question_summary', ''),
                    'content': best_knowledge.get('answer', ''),
                    'trigger_mode': trigger_mode,
                    'next_action': 'form_fill',
                    'next_form_id': form_id,
                    'next_api_config': None,
                    'trigger_keywords': best_knowledge.get('trigger_keywords', []),
                    'immediate_prompt': best_knowledge.get('immediate_prompt', ''),
                    'followup_prompt': None
                }

                # 使用 SOP Orchestrator 處理
                sop_orchestrator = req.app.state.sop_orchestrator
                result = await sop_orchestrator.handle_knowledge_trigger(
                    knowledge_item=knowledge_as_sop,
                    user_message=request.message,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    vendor_id=request.vendor_id
                )

                # 根據結果返回
                if result.get('action') == 'triggered':
                    # 觸發表單
                    form_manager = req.app.state.form_manager
                    form_result = await form_manager.trigger_form_by_knowledge(
                        knowledge_id=best_knowledge['id'],
                        form_id=form_id,
                        session_id=request.session_id,
                        user_id=request.user_id,
                        vendor_id=request.vendor_id,
                        trigger_question=request.message
                    )
                    return _convert_form_result_to_response(form_result, request)
                else:
                    # 返回等待狀態的回應
                    return VendorChatResponse(
                        answer=result.get('response', best_knowledge.get('answer', '')),
                        action_type='form_fill',
                        vendor_id=request.vendor_id,
                        mode=request.mode,
                        session_id=request.session_id,
                        timestamp=datetime.utcnow().isoformat(),
                        source_count=0
                    )

            else:  # trigger_mode == 'auto' 或其他值
                # 自動觸發：直接觸發表單
                form_manager = req.app.state.form_manager
                form_result = await form_manager.trigger_form_by_knowledge(
                    knowledge_id=best_knowledge['id'],
                    form_id=form_id,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    vendor_id=request.vendor_id,
                    trigger_question=request.message
                )

                return _convert_form_result_to_response(form_result, request)

    elif action_type == 'api_call':
        # 場景 C/F: 直接調用 API（已登入用戶）
        api_config = best_knowledge.get('api_config')
        if not api_config:
            print(f"⚠️  action_type=api_call 但缺少 api_config，降級為 direct_answer")
            action_type = 'direct_answer'
        else:
            return await _handle_api_call(
                best_knowledge, request, req, resolver, cache_service
            )

    elif action_type == 'form_then_api':
        # 場景 D/E: 先填表單，表單完成後調用 API
        form_id = best_knowledge.get('form_id')
        if not form_id:
            print(f"⚠️  action_type=form_then_api 但缺少 form_id，降級為 direct_answer")
            action_type = 'direct_answer'
        elif not request.session_id:
            print(f"⚠️  需要表單但缺少 session_id，降級為 direct_answer")
            action_type = 'direct_answer'
        else:
            print(f"📝 [表單+API] 知識 {best_knowledge['id']} 需要先填表單再調用 API")

            # 觸發表單（API 會在表單完成後由 FormManager 調用）
            form_manager = req.app.state.form_manager
            form_result = await form_manager.trigger_form_by_knowledge(
                knowledge_id=best_knowledge['id'],
                form_id=form_id,
                session_id=request.session_id,
                user_id=request.user_id,
                vendor_id=request.vendor_id,
                trigger_question=request.message
            )

            return _convert_form_result_to_response(form_result, request)

    # ⭐ 步驟 3：direct_answer 流程（降級或原本就是 direct_answer）
    # 獲取業者參數（保留完整資訊包含 display_name, unit 等）
    vendor_params = resolver.get_vendor_parameters(request.vendor_id)

    # 準備搜尋結果格式（使用過濾後的高質量知識）
    search_results = [{
        'id': k['id'],
        'question_summary': k['question_summary'],
        'content': k['answer'],
        'similarity': k.get('similarity', 0.9),  # 使用實際相似度，沒有則用預設值
        'keywords': k.get('keywords', [])        # 添加 keywords 供信心度評估
    } for k in filtered_knowledge_list]

    # 使用 ConfidenceEvaluator 評估信心度
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
            vendor_ids=k.get('vendor_ids'),
            target_users=k.get('target_user')
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

    # 清理答案並替換模板變數（兜底保護），同時追蹤使用的參數
    final_answer, used_param_keys = _clean_answer_with_tracking(optimization_result['optimized_answer'], request.vendor_id, resolver)

    # 移除答案中重複的問題（LLM 有時會在答案開頭重複問題）
    final_answer = _remove_duplicate_question(final_answer, request.message)

    # 構建調試資訊（如果請求了）
    debug_info = None
    if request.include_debug_info:
        # 標記哪些知識被選取了（使用過濾後的高質量列表）
        selected_ids = {k['id'] for k in filtered_knowledge_list[:optimization_result.get('sources_used', len(filtered_knowledge_list))]}
        knowledge_candidates_debug = []
        # 顯示所有候選知識，但只標記高質量的為被選取
        for k in knowledge_list:
            knowledge_candidates_debug.append({
                'id': k['id'],
                'question_summary': k.get('question_summary', ''),
                'scope': k.get('scope', ''),
                'base_similarity': k.get('original_similarity', k.get('similarity', 0.0)),
                'rerank_score': k.get('rerank_score'),  # ← 新增：Rerank 分數
                'intent_boost': k.get('intent_boost', 1.0),
                'intent_semantic_similarity': k.get('intent_semantic_similarity'),
                'boosted_similarity': k.get('similarity', 0.0),
                'intent_type': k.get('intent_type'),
                'priority': k.get('priority'),
                'is_selected': k['id'] in selected_ids
            })

        # 🆕 構建 SOP 候選資訊（如果有 decision）
        sop_candidates_debug = None
        if decision and decision.get('sop_result'):
            sop_result = decision['sop_result']
            # ✅ 修復：使用正確的鍵名 'all_sop_candidates'
            sop_candidates_list = sop_result.get('all_sop_candidates', [])
            print(f"🔍 [Debug] sop_result keys: {list(sop_result.keys()) if sop_result else 'None'}")
            print(f"🔍 [Debug] all_sop_candidates length: {len(sop_candidates_list)}")
            if sop_candidates_list:
                print(f"🔍 [Debug] Building sop_candidates_debug with {len(sop_candidates_list)} items")
                sop_candidates_debug = []
                for sop_item in sop_candidates_list:
                    sop_candidates_debug.append({
                        'id': sop_item.get('id'),
                        'item_name': sop_item.get('title', sop_item.get('item_name', '')),  # ✅ 使用 item_name 鍵
                        'title': sop_item.get('title', sop_item.get('item_name', '')),  # 保留 title 供前端使用
                        'content': sop_item.get('content', '')[:200],  # 限制內容長度
                        'similarity': sop_item.get('similarity', 0.0),
                        'boosted_similarity': sop_item.get('similarity', 0.0),  # ✅ 添加 boosted_similarity
                        'intent_ids': sop_item.get('intent_ids', [])
                    })
                print(f"🔍 [Debug] sop_candidates_debug final length: {len(sop_candidates_debug)}")
            else:
                print(f"⚠️  [Debug] sop_candidates_list is empty or None")

        # 構建合成資訊（使用過濾後的高質量列表）
        synthesis_info_dict = None
        if optimization_result.get('synthesis_applied'):
            synthesis_info_dict = {
                'sources_count': len(filtered_knowledge_list),
                'sources_ids': [k['id'] for k in filtered_knowledge_list],
                'synthesis_reason': f'多個高品質結果（>= {high_quality_threshold}），使用答案合成'
            }

        # 🆕 提取比較元數據
        comparison_metadata = decision.get('comparison') if decision else None

        debug_info = _build_debug_info(
            processing_path='knowledge',
            intent_result=intent_result,
            llm_strategy=optimization_result.get('optimization_method', 'unknown'),
            knowledge_candidates=knowledge_candidates_debug,
            sop_candidates=sop_candidates_debug,  # 🆕 加入 SOP 候選
            synthesis_info=synthesis_info_dict,
            vendor_params=vendor_params,
            used_param_keys=used_param_keys,  # ✅ 只顯示實際被注入的參數
            comparison_metadata=comparison_metadata  # 🆕 加入比較元數據
        )

    response = VendorChatResponse(
        answer=final_answer,
        intent_name=intent_result['intent_name'],
        intent_type=intent_result.get('intent_type'),
        confidence=intent_result['confidence'],
        all_intents=intent_result.get('all_intents', []),
        secondary_intents=intent_result.get('secondary_intents', []),
        intent_ids=intent_result.get('intent_ids', []),
        action_type=action_type,
        sources=sources if request.include_sources else None,
        source_count=len(knowledge_list),
        vendor_id=request.vendor_id,
        mode=request.mode,
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat(),
        video_url=video_url,
        video_file_size=video_file_size,
        video_duration=video_duration,
        video_format=video_format,
        debug_info=debug_info
    )

    return cache_response_and_return(cache_service, request.vendor_id, request.message, response, request.target_user)


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
# 2. /api/v1/chat/stream - 流式聊天端點 (已移除)
#    - 已於 2026-02 移除
#    - 統一使用 /api/v1/message 端點
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


async def _handle_api_call(
    best_knowledge: dict,
    request: VendorChatRequest,
    req: Request,
    resolver,
    cache_service
) -> VendorChatResponse:
    """
    處理 API 調用場景 (action_type = 'api_call')

    適用場景 C 和 F：
    - C: 已登入用戶直接調用 API + 知識答案
    - F: 純 API 調用（不含知識答案）
    """
    from services.api_call_handler import get_api_call_handler

    api_config = best_knowledge.get('api_config', {})
    knowledge_answer = best_knowledge.get('answer')

    print(f"🔌 [API調用] endpoint={api_config.get('endpoint')}, combine_with_knowledge={api_config.get('combine_with_knowledge', True)}")

    # 準備 session 數據
    session_data = {
        'user_id': request.user_id,
        'vendor_id': request.vendor_id,
        'session_id': request.session_id
    }

    # 檢查是否缺少必要參數
    params = api_config.get('params', {})
    missing_params = []
    for param_name, param_value in params.items():
        if isinstance(param_value, str) and '{session.' in param_value:
            # 檢查 session 參數是否存在
            field = param_value.replace('{session.', '').replace('}', '')
            if not session_data.get(field):
                missing_params.append(field)

    if missing_params:
        error_message = f"⚠️ 缺少必要的參數：{', '.join(missing_params)}\n\n"
        if knowledge_answer and api_config.get('combine_with_knowledge', True):
            error_message += knowledge_answer

        return VendorChatResponse(
            answer=error_message,
            intent_name='API查詢',
            intent_type='knowledge',
            confidence=0.5,
            action_type='api_call',
            sources=[],
            source_count=0,
            vendor_id=request.vendor_id,
            mode=request.mode or 'b2c',
            session_id=request.session_id,
            timestamp=datetime.utcnow().isoformat()
        )

    # 調用 API（傳遞 db_pool 以支持動態配置的 API）
    db_pool = req.app.state.db_pool
    api_handler = get_api_call_handler(db_pool)

    # 合併 static_params（與 form_manager.py 保持一致）
    form_data = api_config.get('static_params', {})

    api_result = await api_handler.execute_api_call(
        api_config=api_config,
        session_data=session_data,
        form_data=form_data,
        knowledge_answer=knowledge_answer
    )

    # 獲取格式化的響應
    formatted_response = api_result.get('formatted_response', '')

    # 保存對話歷史
    try:
        if request.session_id:
            await cache_service.save_conversation(
                session_id=request.session_id,
                user_id=request.user_id,
                user_role=request.user_role,
                question=request.message,
                answer=formatted_response,
                related_kb_ids=[best_knowledge['id']],
                vendor_id=request.vendor_id
            )
    except Exception as e:
        print(f"⚠️  保存對話歷史失敗: {e}")

    # 返回響應
    return VendorChatResponse(
        answer=formatted_response,
        intent_name=best_knowledge.get('intent_name', 'API查詢'),
        intent_type='knowledge',
        confidence=best_knowledge.get('similarity', 0.9),
        action_type='api_call',
        sources=[{
            'id': best_knowledge['id'],
            'question_summary': best_knowledge.get('question_summary', ''),
            'answer': knowledge_answer or '',
            'similarity': best_knowledge.get('similarity', 0),
            'scope': best_knowledge.get('scope'),
            'vendor_id': best_knowledge.get('vendor_id'),
            'target_users': best_knowledge.get('target_users')
        }],
        source_count=1,
        vendor_id=request.vendor_id,
        mode=request.mode or 'b2c',
        session_id=request.session_id,
        timestamp=datetime.utcnow().isoformat()
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

    # ✅ 新欄位（推薦使用）
    target_user: Optional[str] = Field(
        None,
        description="目標用戶角色：tenant(租客), landlord(房東), property_manager(物管), system_admin(系統管理)"
    )
    mode: Optional[str] = Field(
        'b2c',
        description="業務模式：b2c(終端用戶), b2b(業者員工)"
    )

    # ⚠️ 舊欄位（向後兼容，已廢棄，將於 2026-03 移除）
    user_role: Optional[str] = Field(
        None,
        description="[已廢棄，將於 2026-03 移除] 請使用 target_user 替代"
    )

    session_id: Optional[str] = Field(None, description="會話 ID（用於追蹤）")
    user_id: Optional[str] = Field(None, description="使用者 ID（租客 ID 或客服 ID）")
    top_k: int = Field(5, description="返回知識數量", ge=1, le=10)
    include_sources: bool = Field(True, description="是否包含知識來源")
    include_debug_info: bool = Field(False, description="是否包含調試資訊（處理流程詳情）")
    disable_answer_synthesis: bool = Field(False, description="禁用答案合成（回測模式專用）")
    skip_sop: bool = Field(False, description="跳過 SOP 檢索，僅檢索知識庫（回測模式專用）")

    # 🆕 串流模式參數（2026-02-14）
    stream: bool = Field(False, description="是否使用串流模式（Server-Sent Events）")

    @validator('target_user', always=True)
    def migrate_user_role(cls, v, values):
        """自動從舊欄位遷移到新欄位"""
        if v:
            # 已提供新欄位，驗證並返回
            if v not in TARGET_USER_ROLES:
                raise ValueError(f"target_user 必須是 {TARGET_USER_ROLES} 之一，當前值：{v}")
            return v

        # 向後兼容：從舊欄位轉換
        old_user_role = values.get('user_role')
        mode = values.get('mode', 'b2c')

        if old_user_role:
            print(f"⚠️  [DEPRECATED] 使用了已廢棄的 user_role 參數：'{old_user_role}'，請改用 target_user（將於 2026-03 移除）")
            # 舊值轉換邏輯
            if old_user_role == 'staff':
                return 'property_manager'  # B2B 默認為物管
            elif old_user_role == 'customer':
                return 'tenant'  # B2C 默認為租客
            elif old_user_role in TARGET_USER_ROLES:
                return old_user_role  # 已經是新格式

        # 默認值：根據 mode 判斷
        if mode in ['b2b', 'customer_service']:
            return 'property_manager'
        else:
            return 'tenant'

    @validator('mode')
    def normalize_mode(cls, v):
        """標準化業務模式"""
        if v == 'tenant':  # 舊值
            return 'b2c'
        elif v == 'customer_service':  # 舊值
            return 'b2b'
        elif v in BUSINESS_MODES:
            return v
        else:
            return 'b2c'  # 默認 B2C


class KnowledgeSource(BaseModel):
    """知識來源"""
    id: int
    question_summary: str
    answer: str
    scope: str = Field(..., description="知識範圍：global(全域), vendor(業者專屬), customized(客製化)")
    vendor_ids: Optional[List[int]] = Field(None, description="業者 ID 列表（如為業者專屬知識）")
    target_users: Optional[List[str]] = Field(None, description="目標用戶列表")


# ========================================
# 調試資訊模型（Debug Info Models）
# ========================================

class CandidateKnowledge(BaseModel):
    """候選知識項目（用於調試）"""
    id: int
    question_summary: str
    scope: str
    base_similarity: float = Field(..., description="基礎向量相似度")
    rerank_score: Optional[float] = Field(None, description="Reranker 分數 (10/90 混合)")
    intent_boost: float = Field(..., description="意圖加成係數")
    intent_semantic_similarity: Optional[float] = Field(None, description="意圖語義相似度")
    priority: Optional[int] = Field(None, description="人工優先級")
    priority_boost: float = Field(0.0, description="優先級加成值")
    boosted_similarity: float = Field(..., description="加成後相似度")
    intent_type: Optional[str] = Field(None, description="意圖類型：primary/secondary")
    is_selected: bool = Field(..., description="是否被選取")


class CandidateSOP(BaseModel):
    """候選 SOP 項目（用於調試）"""
    id: int
    item_name: str
    group_name: Optional[str] = None
    base_similarity: float = Field(..., description="基礎向量相似度")
    intent_boost: float = Field(..., description="意圖加成係數")
    boosted_similarity: float = Field(..., description="加成後相似度")
    rerank_score: Optional[float] = Field(None, description="Reranker 分數（0-1）")
    is_selected: bool = Field(..., description="是否被選取")


class IntentDetail(BaseModel):
    """意圖分析詳情（用於調試）"""
    primary_intent: str
    primary_confidence: float
    secondary_intents: Optional[List[str]] = None
    all_intents_with_confidence: Optional[List[Dict]] = None


class SynthesisInfo(BaseModel):
    """答案合成資訊（用於調試）"""
    sources_count: int
    sources_ids: List[int]
    synthesis_reason: str


class VendorParamInjected(BaseModel):
    """已注入的業者參數（用於調試）"""
    param_key: str
    display_name: str
    value: str
    unit: Optional[str] = None


class DebugInfo(BaseModel):
    """調試資訊（完整處理流程細節）"""
    processing_path: str = Field(..., description="處理路徑：sop | knowledge | fallback")

    # SOP 檢索結果
    sop_candidates: Optional[List[CandidateSOP]] = Field(None, description="SOP 候選項目列表")

    # 知識庫檢索結果
    knowledge_candidates: Optional[List[CandidateKnowledge]] = Field(None, description="知識庫候選項目列表")

    # 意圖分類詳情
    intent_details: IntentDetail = Field(..., description="意圖分析詳情")

    # LLM 優化策略
    llm_strategy: str = Field(..., description="LLM 優化策略：perfect_match | synthesis | fast_path | template | full_optimization")

    # 答案合成資訊
    synthesis_info: Optional[SynthesisInfo] = Field(None, description="答案合成資訊（如果有）")

    # 業者參數注入
    vendor_params_injected: List[VendorParamInjected] = Field(default_factory=list, description="已注入的業者參數")

    # 相似度閾值資訊
    thresholds: Dict = Field(default_factory=dict, description="相似度閾值配置")

    # 系統配置狀態
    system_config: Optional[Dict] = Field(None, description="系統配置狀態（啟用的策略等）")

    # 智能檢索比較資訊（2026-01-28 新增）
    comparison_metadata: Optional[Dict] = Field(None, description="SOP 與知識庫比較資訊（分數、候選數、決策依據等）")


class QuickReply(BaseModel):
    """快速回复按钮"""
    text: str = Field(..., description="按钮显示文字")
    value: str = Field(..., description="点击后发送的值")
    style: Optional[str] = Field(None, description="按钮样式：primary, secondary, success, danger")


class VendorChatResponse(BaseModel):
    """多業者聊天回應"""
    answer: str = Field(..., description="回答內容")
    intent_name: Optional[str] = Field(None, description="意圖名稱")
    intent_type: Optional[str] = Field(None, description="意圖類型")
    confidence: Optional[float] = Field(None, description="分類信心度")
    all_intents: Optional[List[str]] = Field(None, description="所有相關意圖名稱（主要 + 次要）")
    secondary_intents: Optional[List[str]] = Field(None, description="次要相關意圖")
    intent_ids: Optional[List[int]] = Field(None, description="所有意圖 IDs")
    action_type: Optional[str] = Field(None, description="對話流程類型（direct_answer/form_fill/api_call/form_then_api）")
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
    # 表單填寫資訊（Phase X: 表單填寫對話功能）
    form_triggered: Optional[bool] = Field(None, description="表單是否被觸發")
    form_completed: Optional[bool] = Field(None, description="表單是否已完成")
    form_cancelled: Optional[bool] = Field(None, description="表單是否已取消")
    form_id: Optional[str] = Field(None, description="表單 ID")
    current_field: Optional[str] = Field(None, description="當前欄位名稱")
    progress: Optional[str] = Field(None, description="填寫進度（如：2/4）")
    allow_resume: Optional[bool] = Field(None, description="是否允許恢復表單填寫")
    # 快速回复按钮（SOP Next Action 功能）
    quick_replies: Optional[List[QuickReply]] = Field(None, description="快速回复按钮列表")
    # 調試資訊
    debug_info: Optional[DebugInfo] = Field(None, description="調試資訊（處理流程詳情）")


@router.post("/message", response_model=VendorChatResponse)
async def vendor_chat_message(request: VendorChatRequest, req: Request):
    """
    多業者通用聊天端點（Phase 1: B2C 模式）- 已重構

    流程：
    0. 檢查表單會話（Phase X: 表單填寫功能）
    1. 驗證業者狀態
    2. 檢查緩存
    3. 意圖分類
    3.5. 檢查表單觸發（Phase X: 表單填寫功能）
    4. 根據意圖處理：unclear → SOP → 知識庫 → RAG fallback
    5. LLM 優化並返回答案

    重構：單一職責原則（Single Responsibility Principle）
    - 主函數作為編排器（Orchestrator）
    - 各功能模塊獨立為輔助函數
    """
    try:
        # DEBUG: 檢查 session_id 是否被正確接收
        print(f"🔍 [DEBUG] vendor_chat_message received - session_id: {request.session_id}, user_id: {request.user_id}")

        # Step 0: 檢查表單會話（Phase X: 表單填寫功能）
        if request.session_id:
            form_manager = req.app.state.form_manager
            session_state = await form_manager.get_session_state(request.session_id)

            # 處理 REVIEWING 狀態（審核確認）
            if session_state and session_state['state'] == 'REVIEWING':
                user_choice = request.message.strip()

                # 確認提交
                if user_choice.lower() in ["確認", "confirm", "ok", "提交", "submit"]:
                    print(f"📋 用戶確認提交表單")
                    # 完成表單
                    form_schema = await form_manager.get_form_schema(
                        session_state['form_id'],
                        request.vendor_id
                    )
                    form_result = await form_manager._complete_form(
                        session_state,
                        form_schema,
                        session_state['collected_data']
                    )
                    response = _convert_form_result_to_response(form_result, request)

                    # 🆕 如果啟用串流模式，轉換為串流輸出
                    if request.stream:
                        print(f"📡 [串流模式] 將表單完成響應轉換為串流輸出")
                        return StreamingResponse(
                            stream_response_wrapper(response.dict()),
                            media_type="text/event-stream",
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-Accel-Buffering": "no"
                            }
                        )
                    return response

                # 取消表單
                elif user_choice.lower() in ["取消", "cancel", "放棄"]:
                    print(f"📋 用戶取消表單")
                    form_result = await form_manager.cancel_form(request.session_id)

                    # 清除 SOP trigger context，避免再次詢問時直接觸發表單
                    sop_orchestrator = req.app.state.sop_orchestrator
                    sop_orchestrator.trigger_handler.delete_context(request.session_id)
                    print(f"🧹 已清除 trigger context")

                    response = _convert_form_result_to_response(form_result, request)

                    # 🆕 如果啟用串流模式，轉換為串流輸出
                    if request.stream:
                        print(f"📡 [串流模式] 將表單取消響應轉換為串流輸出")
                        return StreamingResponse(
                            stream_response_wrapper(response.dict()),
                            media_type="text/event-stream",
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-Accel-Buffering": "no"
                            }
                        )
                    return response

                # 修改欄位
                else:
                    print(f"📋 用戶要求修改欄位：{user_choice}")
                    form_result = await form_manager.handle_edit_request(
                        session_id=request.session_id,
                        user_input=request.message,
                        vendor_id=request.vendor_id
                    )
                    response = _convert_form_result_to_response(form_result, request)

                    # 🆕 如果啟用串流模式，轉換為串流輸出
                    if request.stream:
                        print(f"📡 [串流模式] 將欄位修改響應轉換為串流輸出")
                        return StreamingResponse(
                            stream_response_wrapper(response.dict()),
                            media_type="text/event-stream",
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-Accel-Buffering": "no"
                            }
                        )
                    return response

            # 處理 EDITING 狀態（編輯欄位）
            if session_state and session_state['state'] == 'EDITING':
                print(f"📋 用戶輸入編輯後的欄位值")
                form_result = await form_manager.collect_edited_field(
                    session_id=request.session_id,
                    user_message=request.message,
                    vendor_id=request.vendor_id
                )
                return _convert_form_result_to_response(form_result, request)

            # 處理 COLLECTING、DIGRESSION 和 PAUSED 狀態（收集欄位）
            if session_state and session_state['state'] in ['COLLECTING', 'DIGRESSION', 'PAUSED']:
                # 用戶正在填寫表單 → 走表單收集流程
                # PAUSED 狀態：表單暫停（例如 SOP form_then_api），用戶訊息可能是要恢復表單
                print(f"📋 檢測到進行中的表單會話（{session_state['form_id']}, 狀態: {session_state['state']}），使用表單收集流程")

                intent_classifier = req.app.state.intent_classifier
                intent_result = intent_classifier.classify(request.message)

                form_result = await form_manager.collect_field_data(
                    user_message=request.message,
                    session_id=request.session_id,
                    intent_result=intent_result,
                    vendor_id=request.vendor_id,
                    language='zh-TW'  # TODO: 從 request 或用戶設定讀取語言
                )

                # 如果用戶選擇回答問題或取消表單，繼續處理待處理的問題
                if form_result.get('form_cancelled'):
                    # 清除 SOP trigger context，避免再次詢問時直接觸發表單
                    sop_orchestrator = req.app.state.sop_orchestrator
                    sop_orchestrator.trigger_handler.delete_context(request.session_id)
                    print(f"🧹 已清除 trigger context")

                    pending_question = form_result.get('pending_question')
                    if pending_question:
                        print(f"📋 用戶取消表單，繼續處理待處理的問題：{pending_question}")
                        # 替換 request.message 為待處理的問題
                        request.message = pending_question
                        # 繼續往下走正常流程
                    else:
                        print(f"📋 用戶取消表單，但沒有待處理的問題")
                        # 沒有待處理的問題，直接返回取消訊息
                        response = _convert_form_result_to_response(form_result, request)

                        # 🆕 如果啟用串流模式，轉換為串流輸出
                        if request.stream:
                            return StreamingResponse(
                                stream_response_wrapper(response.dict()),
                                media_type="text/event-stream",
                                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
                            )
                        return response
                else:
                    # 將表單結果轉換為 VendorChatResponse 格式
                    response = _convert_form_result_to_response(form_result, request)

                    # 🆕 如果啟用串流模式，轉換為串流輸出
                    if request.stream:
                        print(f"📡 [串流模式] 將表單響應轉換為串流輸出")
                        return StreamingResponse(
                            stream_response_wrapper(response.dict()),
                            media_type="text/event-stream",
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-Accel-Buffering": "no"
                            }
                        )

                    return response

        # Step 1: 驗證業者
        resolver = get_vendor_param_resolver()
        vendor_info = _validate_vendor(request.vendor_id, resolver)

        # Step 2: 緩存檢查（表單期間不使用緩存）
        cache_service = req.app.state.cache_service

        # 🆕 串流模式：檢查緩存時返回不同格式
        print(f"🔍 [DEBUG] stream參數值: {request.stream}, 類型: {type(request.stream)}")
        if request.stream:
            # 串流模式：檢查緩存並返回 SSE
            config_version = _generate_config_version()
            cached_answer = cache_service.get_cached_answer(
                vendor_id=request.vendor_id,
                question=request.message,
                target_user=request.target_user,
                config_version=config_version
            )
            if cached_answer:
                print(f"⚡ 緩存命中！使用串流模式輸出 - 配置版本: {config_version}")
                return StreamingResponse(
                    stream_cached_answer(cached_answer),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"  # 禁用 nginx 緩衝
                    }
                )
        else:
            # 非串流模式：正常返回 JSON
            cached_response = _check_cache(cache_service, request.vendor_id, request.message, request.target_user)
            if cached_response:
                return cached_response

        # Step 3: 意圖分類
        intent_classifier = req.app.state.intent_classifier
        intent_result = intent_classifier.classify(request.message)

        # Step 4: 智能檢索（SOP 與知識庫同時檢索 + 分數比較）
        # 🆕 2026-01-28: 替換原有的先 SOP 後知識庫的邏輯
        # 新邏輯：
        #   1. 同時檢索 SOP 和知識庫（並行執行）
        #   2. 比較 Reranker 分數，選擇最相關的
        #   3. SOP 和知識庫永遠不混合
        #   4. 答案合成只用於知識庫
        if not request.skip_sop:
            sop_orchestrator = req.app.state.sop_orchestrator

            # 使用智能檢索
            decision = await _smart_retrieval_with_comparison(
                request=request,
                intent_result=intent_result,
                sop_orchestrator=sop_orchestrator,
                resolver=resolver
            )

            print(f"🎯 [最終決策] {decision['type']} - {decision['reason']}")

            # 根據決策類型返回回應
            if decision['type'] == 'sop':
                # 返回 SOP 回應（不涉及知識庫）
                response = await _build_orchestrator_response(
                    request, req, decision['sop_result'],
                    resolver, vendor_info, cache_service,
                    decision=decision  # 🆕 傳遞決策資訊（包含 comparison_metadata）
                )

                # 🆕 串流模式：將 JSON 響應轉換為串流
                if request.stream:
                    print(f"📡 [串流模式] 將 SOP 響應轉換為串流輸出")
                    return StreamingResponse(
                        stream_response_wrapper(response.dict()),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Accel-Buffering": "no"
                        }
                    )
                return response

            elif decision['type'] == 'knowledge':
                # 返回知識庫回應（會進行答案合成判斷）
                # ✅ 答案合成只在這裡發生，不會混入 SOP
                response = await _build_knowledge_response(
                    request, req, intent_result, decision['knowledge_list'],
                    resolver, vendor_info, cache_service,
                    decision=decision  # 🆕 傳遞完整決策資訊（包含 SOP 結果和比較元數據）
                )

                # 🆕 串流模式：將 JSON 響應轉換為串流
                if request.stream:
                    print(f"📡 [串流模式] 將知識庫響應轉換為串流輸出")
                    return StreamingResponse(
                        stream_response_wrapper(response.dict()),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Accel-Buffering": "no"
                        }
                    )
                return response

            elif decision['type'] == 'none':
                # 無結果，進入 RAG fallback
                response = await _handle_no_knowledge_found(
                    request, req, intent_result, resolver,
                    cache_service, vendor_info
                )

                # 🆕 串流模式：將 JSON 響應轉換為串流
                if request.stream:
                    print(f"📡 [串流模式] 將無結果響應轉換為串流輸出")
                    return StreamingResponse(
                        stream_response_wrapper(response.dict()),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Accel-Buffering": "no"
                        }
                    )
                return response

        else:
            # 回測模式：只使用知識庫
            print(f"ℹ️  [回測模式] 跳過 SOP 檢索，僅使用知識庫")

            # 獲取意圖 ID
            intent_id = None if intent_result['intent_name'] == 'unclear' else _get_intent_id(intent_result['intent_name'])

            # 檢索知識庫
            knowledge_list = await _retrieve_knowledge(request, intent_id, intent_result)

            # 如果知識庫沒有結果
            if not knowledge_list:
                return await _handle_no_knowledge_found(
                    request, req, intent_result, resolver,
                    cache_service, vendor_info
                )

            # 返回知識庫回應
            return await _build_knowledge_response(
                request, req, intent_result, knowledge_list,
                resolver, vendor_info, cache_service
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
