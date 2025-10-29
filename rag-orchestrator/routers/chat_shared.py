"""
共用聊天邏輯模組
供 chat.py 和 chat_stream.py 共用，避免程式碼重複

包含：
- SOP 檢索邏輯
- 答案優化參數標準化
"""
from typing import Optional, Dict
import asyncio
import os


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


async def retrieve_sop_hybrid(
    vendor_id: int,
    intent_ids: list,
    query: str,
    top_k: int = 5,
    similarity_threshold: float = None
) -> list:
    """
    混合檢索 SOP（Async版本，供 chat 使用）

    使用意圖加成策略 + 向量相似度，對齊 KB 設計：
    - 主要意圖（第一個）：1.5x 加成
    - 次要意圖：1.2x 加成
    - 其他意圖：1.0x（軟過濾）

    Args:
        vendor_id: 業者 ID
        intent_ids: 意圖 ID 列表（按重要性排序，第一個為主要意圖）
        query: 使用者問題（用於計算相似度）
        top_k: 返回結果數量
        similarity_threshold: 相似度閾值

    Returns:
        SOP 項目列表（包含 similarity 欄位）
    """
    # 如果沒有傳入閾值，從環境變數讀取
    if similarity_threshold is None:
        similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.60"))

    sop_retriever = get_vendor_sop_retriever()

    # 提取主要意圖（第一個意圖通常是最高置信度）
    primary_intent_id = intent_ids[0] if intent_ids else None

    # 使用 hybrid 方法：intent boosting + 向量相似度（一次性檢索）
    items_with_sim = await sop_retriever.retrieve_sop_hybrid(
        vendor_id=vendor_id,
        query=query,
        intent_ids=intent_ids,
        primary_intent_id=primary_intent_id,
        top_k=top_k,
        similarity_threshold=similarity_threshold
    )

    # 將相似度添加到 item dict 中
    all_sop_items = []
    for item, similarity in items_with_sim:
        item_with_sim = {**item, 'similarity': similarity}
        all_sop_items.append(item_with_sim)

    if all_sop_items:
        print(f"✨ Intent Boosting 檢索：共 {len(all_sop_items)} 個 SOP 項目（來自 {len(intent_ids)} 個意圖，主要意圖: {primary_intent_id}）")

    return all_sop_items


def convert_sop_to_search_results(sop_items: list) -> list:
    """
    將 SOP 項目轉換為標準 search_results 格式

    統一規則：
    - similarity: 使用 hybrid 檢索的加成後相似度（用於排序，若無則默認 1.0）
    - original_similarity: 原始相似度（未經意圖加成，用於判斷完美匹配）
    - scope='vendor_sop'

    Args:
        sop_items: SOP 項目列表（原始格式，可能包含 similarity 和 original_similarity 欄位）

    Returns:
        標準 search_results 格式列表
    """
    return [{
        'id': sop['id'],
        'title': sop.get('item_name', sop.get('title', '')),
        'content': sop['content'],
        'similarity': sop.get('similarity', 1.0),  # 加成後相似度（用於排序）
        'original_similarity': sop.get('original_similarity', sop.get('similarity', 1.0)),  # 原始相似度（用於完美匹配判斷）
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
