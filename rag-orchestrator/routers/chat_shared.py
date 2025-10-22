"""
共用聊天邏輯模組
供 chat.py 和 chat_stream.py 共用，避免程式碼重複

包含：
- SOP 檢索邏輯
- 答案優化參數標準化
"""
from typing import Optional, Dict
import asyncio


# ==================== SOP 檢索共用邏輯 ====================

def get_vendor_sop_retriever():
    """獲取業者 SOP 檢索器（懶加載）"""
    from services.vendor_sop_retriever import VendorSOPRetriever
    return VendorSOPRetriever()


async def retrieve_sop_async(
    vendor_id: int,
    intent_ids: list,
    top_k: int = 5
) -> list:
    """
    檢索 SOP（異步版本，供 chat_stream 使用）

    Args:
        vendor_id: 業者 ID
        intent_ids: 意圖 ID 列表
        top_k: 返回結果數量

    Returns:
        SOP 項目列表（原始格式）
    """
    sop_retriever = get_vendor_sop_retriever()
    all_sop_items = []
    seen_ids = set()

    # 檢索所有相關 intent_ids 的 SOP 項目（支援複數意圖）
    for intent_id in intent_ids:
        items = await asyncio.to_thread(
            sop_retriever.retrieve_sop_by_intent,
            vendor_id=vendor_id,
            intent_id=intent_id,
            top_k=top_k
        )
        if items:
            # 去重：只添加未見過的項目
            new_items = [item for item in items if item['id'] not in seen_ids]
            all_sop_items.extend(new_items)
            seen_ids.update(item['id'] for item in new_items)
            print(f"📋 檢索到 {len(items)} 個 Vendor SOP 項目（Intent ID: {intent_id}，新增 {len(new_items)} 個）")

    if all_sop_items:
        print(f"✨ 複數意圖合併：共 {len(all_sop_items)} 個 SOP 項目（來自 {len(intent_ids)} 個意圖）")

    return all_sop_items


def retrieve_sop_sync(
    vendor_id: int,
    intent_ids: list,
    top_k: int = 5
) -> list:
    """
    檢索 SOP（同步版本，供 chat 使用）

    Args:
        vendor_id: 業者 ID
        intent_ids: 意圖 ID 列表
        top_k: 返回結果數量

    Returns:
        SOP 項目列表（原始格式）
    """
    sop_retriever = get_vendor_sop_retriever()
    all_sop_items = []
    seen_ids = set()

    # 檢索所有相關 intent_ids 的 SOP 項目（支援複數意圖）
    for intent_id in intent_ids:
        items = sop_retriever.retrieve_sop_by_intent(
            vendor_id=vendor_id,
            intent_id=intent_id,
            top_k=top_k
        )
        if items:
            # 去重：只添加未見過的項目
            new_items = [item for item in items if item['id'] not in seen_ids]
            all_sop_items.extend(new_items)
            seen_ids.update(item['id'] for item in new_items)
            print(f"📋 檢索到 {len(items)} 個 Vendor SOP 項目（Intent ID: {intent_id}，新增 {len(new_items)} 個）")

    if all_sop_items:
        print(f"✨ 複數意圖合併：共 {len(all_sop_items)} 個 SOP 項目（來自 {len(intent_ids)} 個意圖）")

    return all_sop_items


def convert_sop_to_search_results(sop_items: list) -> list:
    """
    將 SOP 項目轉換為標準 search_results 格式

    統一規則：
    - similarity=1.0（SOP 精準匹配）
    - scope='vendor_sop'

    Args:
        sop_items: SOP 項目列表（原始格式）

    Returns:
        標準 search_results 格式列表
    """
    return [{
        'id': sop['id'],
        'title': sop.get('item_name', sop.get('title', '')),
        'content': sop['content'],
        'similarity': 1.0,  # SOP 精準匹配，固定為 1.0
        'scope': 'vendor_sop'
    } for sop in sop_items]


def create_sop_optimization_params(
    question: str,
    search_results: list,
    intent_result: dict,
    vendor_params: Optional[Dict] = None,
    vendor_info: Optional[Dict] = None,
    enable_synthesis_override: Optional[bool] = None
) -> dict:
    """
    建立 SOP 答案優化的標準參數

    統一規則（與 chat.py._build_sop_response() 一致）：
    - confidence_level='high'
    - confidence_score=0.95（SOP 精準匹配）

    Args:
        question: 用戶問題
        search_results: 搜尋結果（已轉換為標準格式）
        intent_result: 意圖分類結果
        vendor_params: 業者參數（可選）
        vendor_info: 業者資訊（可選）
        enable_synthesis_override: 是否覆蓋合成設定（可選）

    Returns:
        llm_optimizer.optimize_answer() 的參數字典
    """
    params = {
        'question': question,
        'search_results': search_results,
        'confidence_level': 'high',  # SOP 精準匹配，固定為 high
        'confidence_score': 0.95,    # SOP 精準匹配，固定為 0.95
        'intent_info': intent_result,
    }

    # 可選參數
    if vendor_params is not None:
        params['vendor_params'] = vendor_params
    if vendor_info is not None:
        params['vendor_info'] = vendor_info
        if 'name' in vendor_info:
            params['vendor_name'] = vendor_info['name']
    if enable_synthesis_override is not None:
        params['enable_synthesis_override'] = enable_synthesis_override

    return params


def has_sop_results(search_results: list) -> bool:
    """
    檢查搜尋結果中是否包含 SOP 項目

    Args:
        search_results: 搜尋結果列表

    Returns:
        True if 包含 SOP，否則 False
    """
    return any(
        result.get('scope') == 'vendor_sop' and result.get('similarity') == 1.0
        for result in search_results
    )
