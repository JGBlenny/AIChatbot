"""
Lookup API - 通用查詢服務

支持:
- 精確匹配
- 模糊匹配 (基於 difflib)
- 多租戶隔離
- 高性能查詢

作者: AI Chatbot Development Team
創建日期: 2026-02-04
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, Dict, Any, List
import logging
import json
from difflib import get_close_matches, SequenceMatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["lookup"])


@router.get("/lookup")
async def lookup(
    request: Request,
    category: str = Query(..., description="查詢類別 ID (如 billing_interval)"),
    key: str = Query(..., description="查詢鍵 (如地址)"),
    vendor_id: int = Query(..., description="業者 ID"),
    fuzzy: bool = Query(True, description="是否啟用模糊匹配"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="模糊匹配閾值 (0-1)")
) -> Dict[str, Any]:
    """
    通用 Lookup 查詢服務

    精確匹配優先，失敗則嘗試模糊匹配。

    Args:
        category: 查詢類別 (如 billing_interval, property_manager)
        key: 查詢鍵 (如地址、車牌號)
        vendor_id: 業者 ID
        fuzzy: 是否啟用模糊匹配 (默認 true)
        threshold: 模糊匹配閾值 0-1 (默認 0.6)

    Returns:
        {
            "success": True/False,
            "match_type": "exact" | "fuzzy" | "none",
            "value": 查詢結果,
            "metadata": 額外數據,
            "suggestions": 建議列表 (當未匹配時)
        }

    Examples:
        # 精確匹配
        GET /api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1

        # 模糊匹配（調低閾值）
        GET /api/lookup?category=billing_interval&key=新北市板橋區&vendor_id=1&threshold=0.5
    """

    logger.info(
        f"🔍 Lookup 查詢 | category={category}, key={key[:50]}{'...' if len(key) > 50 else ''}, "
        f"vendor_id={vendor_id}, fuzzy={fuzzy}, threshold={threshold}"
    )

    db_pool = request.app.state.db_pool

    try:
        # ===== 步驟 1: 精確匹配 =====
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT lookup_value, metadata
                FROM lookup_tables
                WHERE vendor_id = $1
                  AND category = $2
                  AND lookup_key = $3
                  AND is_active = true
            """, vendor_id, category, key)

            if row:
                logger.info(f"✅ 精確匹配成功 | value={row['lookup_value']}")

                # 從 metadata 讀取說明文字（完全配置化）
                metadata_raw = row['metadata']
                # asyncpg 可能返回字符串或字典，需要統一處理
                if isinstance(metadata_raw, str):
                    metadata_dict = json.loads(metadata_raw) if metadata_raw else {}
                elif isinstance(metadata_raw, dict):
                    metadata_dict = metadata_raw
                else:
                    metadata_dict = {}

                note = metadata_dict.get('note', '')

                return {
                    "success": True,
                    "match_type": "exact",
                    "category": category,
                    "key": key,
                    "value": row['lookup_value'],
                    "note": note,
                    "fuzzy_warning": "",  # 精確匹配無警告
                    "metadata": metadata_dict
                }

        # ===== 步驟 2: 模糊匹配 =====
        if fuzzy:
            logger.info(f"🔍 嘗試模糊匹配 | threshold={threshold}")

            async with db_pool.acquire() as conn:
                # 獲取所有該類別的 keys
                rows = await conn.fetch("""
                    SELECT lookup_key, lookup_value, metadata
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND is_active = true
                """, vendor_id, category)

                if not rows:
                    logger.warning(f"⚠️  類別 [{category}] 無數據")
                    return {
                        "success": False,
                        "error": "no_data",
                        "category": category,
                        "message": f"類別 [{category}] 暫無數據"
                    }

                # 使用 difflib 進行模糊匹配
                all_keys = [row['lookup_key'] for row in rows]

                logger.info(f"📊 待匹配數據: {len(all_keys)} 筆")

                matches = get_close_matches(
                    key,
                    all_keys,
                    n=5,  # 返回最多 5 個匹配
                    cutoff=threshold
                )

                if matches:
                    # 計算所有匹配的相似度分數
                    match_scores = [
                        {
                            "key": match,
                            "score": SequenceMatcher(None, key, match).ratio()
                        }
                        for match in matches
                    ]

                    # 按相似度降序排序
                    match_scores.sort(key=lambda x: x['score'], reverse=True)

                    best_score = match_scores[0]['score']
                    best_match = match_scores[0]['key']

                    # 檢查是否有多個相似度接近的匹配（差距小於 2%）
                    ambiguous_threshold = 0.02
                    similar_matches = [
                        m for m in match_scores
                        if abs(m['score'] - best_score) < ambiguous_threshold
                    ]

                    # 如果有多個相似度接近的匹配，要求提供完整地址
                    if len(similar_matches) > 1:
                        logger.warning(
                            f"⚠️  模糊匹配結果不明確 | 找到 {len(similar_matches)} 個相似度接近的匹配"
                        )

                        # 取得這些匹配對應的值
                        suggestion_list = []
                        for m in similar_matches[:5]:  # 最多顯示 5 個
                            matched_row = next(r for r in rows if r['lookup_key'] == m['key'])
                            suggestion_list.append({
                                "key": m['key'],
                                "score": round(m['score'], 2),
                                "value": matched_row['lookup_value']
                            })

                        return {
                            "success": False,
                            "error": "ambiguous_match",
                            "category": category,
                            "key": key,
                            "suggestions": suggestion_list,
                            "message": "您輸入的地址不夠完整，找到多個可能的匹配。請提供完整的地址（包含樓層等詳細資訊）。"
                        }

                    # 只有一個明確匹配，返回結果
                    matched_row = next(r for r in rows if r['lookup_key'] == best_match)

                    logger.info(
                        f"✅ 模糊匹配成功 | matched_key={best_match[:50]}, "
                        f"value={matched_row['lookup_value']}, score={best_score:.2f}"
                    )

                    # 從 metadata 讀取說明文字（與精確匹配相同）
                    metadata_raw = matched_row['metadata']
                    # asyncpg 可能返回字符串或字典，需要統一處理
                    if isinstance(metadata_raw, str):
                        metadata_dict = json.loads(metadata_raw) if metadata_raw else {}
                    elif isinstance(metadata_raw, dict):
                        metadata_dict = metadata_raw
                    else:
                        metadata_dict = {}

                    note = metadata_dict.get('note', '')

                    # 生成模糊匹配警告訊息
                    fuzzy_warning = (
                        f"⚠️ **注意**：您輸入的地址與資料庫記錄不完全相同（相似度 {round(best_score * 100)}%）\n"
                        f"📍 您輸入：{key}\n"
                        f"📍 實際匹配：**{best_match}**\n\n"
                        f"如果這不是您要查詢的地址，請提供完整正確的地址。"
                    )

                    return {
                        "success": True,
                        "match_type": "fuzzy",
                        "match_score": round(best_score, 2),
                        "category": category,
                        "key": key,
                        "matched_key": best_match,
                        "value": matched_row['lookup_value'],
                        "note": note,
                        "fuzzy_warning": fuzzy_warning,
                        "metadata": metadata_dict
                    }
                else:
                    # 返回建議（降低閾值）
                    suggestions = get_close_matches(
                        key,
                        all_keys,
                        n=5,
                        cutoff=max(0.3, threshold - 0.2)  # 降低閾值以提供建議
                    )

                    logger.info(f"⚠️  未找到匹配 | 返回 {len(suggestions)} 個建議")

                    suggestion_list = [
                        {
                            "key": s,
                            "score": round(SequenceMatcher(None, key, s).ratio(), 2)
                        }
                        for s in suggestions
                    ]

                    return {
                        "success": False,
                        "error": "no_match",
                        "category": category,
                        "key": key,
                        "suggestions": suggestion_list,
                        "message": "未找到完全匹配的記錄，以下是相似選項"
                    }

        # ===== 步驟 3: 無匹配（fuzzy=False） =====
        logger.warning(f"❌ 未找到匹配記錄（fuzzy=False）")
        return {
            "success": False,
            "error": "no_match",
            "category": category,
            "key": key,
            "message": "未找到匹配的記錄"
        }

    except Exception as e:
        logger.error(f"❌ Lookup 查詢失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@router.get("/lookup/categories")
async def list_categories(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID")
) -> Dict[str, Any]:
    """
    列出所有可用的查詢類別

    Args:
        vendor_id: 業者 ID

    Returns:
        {
            "success": True,
            "vendor_id": 1,
            "categories": [
                {
                    "category": "billing_interval",
                    "category_name": "電費寄送區間",
                    "record_count": 220
                },
                ...
            ],
            "total": 1
        }

    Example:
        GET /api/lookup/categories?vendor_id=1
    """

    logger.info(f"📋 查詢類別列表 | vendor_id={vendor_id}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT
                    category,
                    category_name,
                    COUNT(*) as record_count
                FROM lookup_tables
                WHERE vendor_id = $1
                  AND is_active = true
                GROUP BY category, category_name
                ORDER BY category
            """, vendor_id)

            categories = [
                {
                    "category": row['category'],
                    "category_name": row['category_name'],
                    "record_count": row['record_count']
                }
                for row in rows
            ]

            logger.info(f"✅ 找到 {len(categories)} 個類別")

            return {
                "success": True,
                "vendor_id": vendor_id,
                "categories": categories,
                "total": len(categories)
            }

    except Exception as e:
        logger.error(f"❌ 查詢類別失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@router.get("/lookup/stats")
async def get_stats(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID"),
    category: Optional[str] = Query(None, description="類別 ID（可選）")
) -> Dict[str, Any]:
    """
    獲取 Lookup 統計資料

    Args:
        vendor_id: 業者 ID
        category: 類別 ID（可選，不提供則顯示全部）

    Returns:
        統計資料

    Example:
        GET /api/lookup/stats?vendor_id=1&category=billing_interval
    """

    logger.info(f"📊 查詢統計資料 | vendor_id={vendor_id}, category={category}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            if category:
                # 特定類別統計
                rows = await conn.fetch("""
                    SELECT lookup_value, COUNT(*) as count
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND is_active = true
                    GROUP BY lookup_value
                    ORDER BY count DESC
                """, vendor_id, category)

                total = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND is_active = true
                """, vendor_id, category)

                return {
                    "success": True,
                    "vendor_id": vendor_id,
                    "category": category,
                    "total_records": total,
                    "value_distribution": [
                        {"value": row['lookup_value'], "count": row['count']}
                        for row in rows
                    ]
                }
            else:
                # 全部類別統計
                rows = await conn.fetch("""
                    SELECT
                        category,
                        category_name,
                        COUNT(*) as record_count,
                        COUNT(DISTINCT lookup_key) as unique_keys
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND is_active = true
                    GROUP BY category, category_name
                    ORDER BY record_count DESC
                """, vendor_id)

                return {
                    "success": True,
                    "vendor_id": vendor_id,
                    "categories": [
                        {
                            "category": row['category'],
                            "category_name": row['category_name'],
                            "record_count": row['record_count'],
                            "unique_keys": row['unique_keys']
                        }
                        for row in rows
                    ]
                }

    except Exception as e:
        logger.error(f"❌ 查詢統計失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")
