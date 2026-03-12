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

from fastapi import APIRouter, Query, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional, Dict, Any, List
import logging
import json
import io
import pandas as pd
from difflib import get_close_matches, SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["lookup"])


def _parse_lookup_value(category: str, lookup_value: str):
    """
    解析 lookup_value，對於整合類別（如 utility_electricity, utility_water, utility_gas）會解析 JSON

    Args:
        category: 類別 ID
        lookup_value: 查詢值（可能是字串或 JSON 字串）

    Returns:
        解析後的值（字串或字典）
    """
    # 整合類別清單（這些類別的 lookup_value 儲存為 JSON）
    json_categories = ['utility_electricity', 'utility_water', 'utility_gas']

    if category in json_categories:
        try:
            return json.loads(lookup_value)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"⚠️  無法解析 {category} 的 JSON value: {lookup_value[:50]}")
            return lookup_value
    else:
        return lookup_value


@router.get("/lookup")
async def lookup(
    request: Request,
    category: str = Query(..., description="查詢類別 ID (如 billing_interval)"),
    key: str = Query(..., description="查詢鍵 (如地址)"),
    key2: Optional[str] = Query(None, description="第二查詢鍵（可選），與 key 組合為 {key}_{key2}（如車位號）"),
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

    # 檢查是否要查詢「全部」
    query_all = key2 and key2.strip() in ['全部', '所有', '全部設施', '所有設施', '全部資料', '所有資料', '全', '所', '*']

    # 組合最終查詢 key（支援複數 key）
    lookup_key = f"{key}-{key2}" if key2 and not query_all else key

    logger.info(
        f"🔍 Lookup 查詢 | category={category}, key={lookup_key[:50]}{'...' if len(lookup_key) > 50 else ''}, "
        f"vendor_id={vendor_id}, fuzzy={fuzzy}, threshold={threshold}, query_all={query_all}"
    )

    db_pool = request.app.state.db_pool

    try:
        # ===== 特殊情況: 查詢「全部」(key 下的所有記錄) =====
        if query_all:
            logger.info(f"📋 查詢全部 | key={key}, category={category}")
            async with db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT lookup_key, lookup_value, metadata
                    FROM lookup_tables
                    WHERE vendor_id = $1
                      AND category = $2
                      AND lookup_key LIKE $3
                      AND is_active = true
                    ORDER BY lookup_key
                """, vendor_id, category, f"{key}_%")

                if not rows:
                    logger.warning(f"⚠️  查無資料 | key={key}, category={category}")
                    return {
                        "success": False,
                        "match_type": "none",
                        "category": category,
                        "key": key,
                        "error": "no_data",
                        "message": f"找不到 [{key}] 的任何資料"
                    }

                # 返回所有匹配的記錄
                items = []
                for row in rows:
                    metadata_raw = row['metadata']
                    if isinstance(metadata_raw, str):
                        metadata_dict = json.loads(metadata_raw) if metadata_raw else {}
                    elif isinstance(metadata_raw, dict):
                        metadata_dict = metadata_raw
                    else:
                        metadata_dict = {}

                    # 解析 lookup_value
                    parsed_value = _parse_lookup_value(category, row['lookup_value'])

                    items.append({
                        "key": row['lookup_key'],
                        "value": parsed_value,
                        "metadata": metadata_dict
                    })

                logger.info(f"✅ 查詢全部成功 | 找到 {len(items)} 筆資料")
                return {
                    "success": True,
                    "match_type": "all",
                    "category": category,
                    "key": key,
                    "total": len(items),
                    "items": items
                }

        # ===== 步驟 1: 精確匹配 =====
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT lookup_value, metadata
                FROM lookup_tables
                WHERE vendor_id = $1
                  AND category = $2
                  AND lookup_key = $3
                  AND is_active = true
            """, vendor_id, category, lookup_key)

            if row:
                logger.info(f"✅ 精確匹配成功 | value={row['lookup_value'][:100] if len(row['lookup_value']) > 100 else row['lookup_value']}")

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

                # 解析 lookup_value（對於整合類別會解析 JSON）
                parsed_value = _parse_lookup_value(category, row['lookup_value'])

                return {
                    "success": True,
                    "match_type": "exact",
                    "category": category,
                    "key": key,
                    "value": parsed_value,
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
                    lookup_key,
                    all_keys,
                    n=5,  # 返回最多 5 個匹配
                    cutoff=threshold
                )

                if matches:
                    # 計算所有匹配的相似度分數
                    match_scores = [
                        {
                            "key": match,
                            "score": SequenceMatcher(None, lookup_key, match).ratio()
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
                        f"value={matched_row['lookup_value'][:100] if len(matched_row['lookup_value']) > 100 else matched_row['lookup_value']}, score={best_score:.2f}"
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

                    # 解析 lookup_value（對於整合類別會解析 JSON）
                    parsed_value = _parse_lookup_value(category, matched_row['lookup_value'])

                    # 生成模糊匹配警告訊息
                    fuzzy_warning = (
                        f"⚠️ **注意**：您輸入的資訊與資料庫記錄不完全相同（相似度 {round(best_score * 100)}%）\n"
                        f"📍 您輸入：{lookup_key}\n"
                        f"📍 實際匹配：**{best_match}**\n\n"
                        f"如果這不是您要查詢的記錄，請提供完整正確的資訊。"
                    )

                    return {
                        "success": True,
                        "match_type": "fuzzy",
                        "match_score": round(best_score, 2),
                        "category": category,
                        "key": key,
                        "matched_key": best_match,
                        "value": parsed_value,
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
                            "score": round(SequenceMatcher(None, lookup_key, s).ratio(), 2)
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


@router.get("/lookup/all")
async def lookup_all(
    request: Request,
    category: str = Query(..., description="查詢類別 ID (如 customer_service)"),
    vendor_id: int = Query(..., description="業者 ID"),
) -> Dict[str, Any]:
    """
    查詢某業者某類別的所有資料（不需要 key）

    用於 api_call 類型的知識條目，一次回傳整個類別的完整資料。
    適用於：客服聯絡方式、公共設施、包裹服務、配合廠商、服務時間、報修流程、繳費方式等。

    Args:
        category: 查詢類別 (如 customer_service, community_facilities)
        vendor_id: 業者 ID

    Returns:
        {
            "success": True/False,
            "category": "customer_service",
            "vendor_id": 1,
            "total": 5,
            "items": [
                {
                    "key": "客服專線",
                    "value": "02-2345-6789",
                    "metadata": {...}
                },
                ...
            ]
        }

    Example:
        GET /api/lookup/all?category=customer_service&vendor_id=2
    """

    logger.info(f"📋 Lookup All 查詢 | category={category}, vendor_id={vendor_id}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT lookup_key, lookup_value, metadata
                FROM lookup_tables
                WHERE vendor_id = $1
                  AND category = $2
                  AND is_active = true
                ORDER BY id
            """, vendor_id, category)

            if not rows:
                logger.warning(f"⚠️  查無資料 | category={category}, vendor_id={vendor_id}")
                return {
                    "success": False,
                    "error": "no_data",
                    "category": category,
                    "vendor_id": vendor_id,
                    "message": f"類別 [{category}] 目前無資料"
                }

            items = []
            for row in rows:
                metadata_raw = row['metadata']
                if isinstance(metadata_raw, str):
                    metadata_dict = json.loads(metadata_raw) if metadata_raw else {}
                elif isinstance(metadata_raw, dict):
                    metadata_dict = metadata_raw
                else:
                    metadata_dict = {}

                # 解析 lookup_value
                parsed_value = _parse_lookup_value(category, row['lookup_value'])

                items.append({
                    "key": row['lookup_key'],
                    "value": parsed_value,
                    "metadata": metadata_dict
                })

            logger.info(f"✅ Lookup All 成功 | category={category}, 共 {len(items)} 筆")

            return {
                "success": True,
                "category": category,
                "vendor_id": vendor_id,
                "total": len(items),
                "items": items
            }

    except Exception as e:
        logger.error(f"❌ Lookup All 查詢失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


# ========== CRUD 管理端點 ==========

from pydantic import BaseModel, Field


@router.get("/lookup/manage")
async def lookup_manage(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID"),
    category: Optional[str] = Query(None, description="類別篩選"),
) -> Dict[str, Any]:
    """
    管理端點：查詢業者的所有 Lookup 記錄（包含完整欄位，含停用記錄）

    用於後台管理介面顯示和編輯 Lookup 數據。

    Args:
        vendor_id: 業者 ID
        category: 可選的類別篩選

    Returns:
        {
            "success": True,
            "vendor_id": 2,
            "total": 50,
            "records": [
                {
                    "id": 123,
                    "vendor_id": 2,
                    "category": "billing_interval",
                    "category_name": "帳單週期",
                    "lookup_key": "...",
                    "lookup_value": "...",
                    "metadata": {...},
                    "is_active": true,
                    "created_at": "...",
                    "updated_at": "..."
                },
                ...
            ]
        }

    Example:
        GET /api/lookup/manage?vendor_id=2
        GET /api/lookup/manage?vendor_id=2&category=billing_interval
    """

    logger.info(f"🔧 Lookup 管理查詢 | vendor_id={vendor_id}, category={category}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 建立查詢條件
            where_clauses = ["vendor_id = $1"]
            params = [vendor_id]

            if category:
                where_clauses.append(f"category = ${len(params) + 1}")
                params.append(category)

            where_sql = " AND ".join(where_clauses)

            # 查詢所有記錄（包含停用的）
            query = f"""
                SELECT id, vendor_id, category, category_name, lookup_key, lookup_value,
                       metadata, is_active, created_at, updated_at
                FROM lookup_tables
                WHERE {where_sql}
                ORDER BY category, id
            """

            rows = await conn.fetch(query, *params)

            records = []
            for row in rows:
                metadata_raw = row['metadata']
                if isinstance(metadata_raw, str):
                    metadata_dict = json.loads(metadata_raw) if metadata_raw else None
                elif isinstance(metadata_raw, dict):
                    metadata_dict = metadata_raw
                else:
                    metadata_dict = None

                records.append({
                    "id": row['id'],
                    "vendor_id": row['vendor_id'],
                    "category": row['category'],
                    "category_name": row['category_name'],
                    "lookup_key": row['lookup_key'],
                    "lookup_value": row['lookup_value'],
                    "metadata": metadata_dict,
                    "is_active": row['is_active'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
                })

            logger.info(f"✅ Lookup 管理查詢成功 | 共 {len(records)} 筆")

            return {
                "success": True,
                "vendor_id": vendor_id,
                "category": category,
                "total": len(records),
                "records": records
            }

    except Exception as e:
        logger.error(f"❌ Lookup 管理查詢失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


class LookupCreateRequest(BaseModel):
    """建立 Lookup 請求"""
    vendor_id: int = Field(..., description="業者 ID")
    category: str = Field(..., description="類別 ID")
    category_name: Optional[str] = Field(None, description="類別顯示名稱")
    lookup_key: str = Field(..., description="查詢鍵")
    lookup_value: str = Field(..., description="查詢值")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")
    is_active: bool = Field(True, description="是否啟用")


class LookupUpdateRequest(BaseModel):
    """更新 Lookup 請求"""
    category_name: Optional[str] = Field(None, description="類別顯示名稱")
    lookup_key: Optional[str] = Field(None, description="查詢鍵")
    lookup_value: Optional[str] = Field(None, description="查詢值")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")
    is_active: Optional[bool] = Field(None, description="是否啟用")


@router.post("/lookup")
async def create_lookup(request: Request, data: LookupCreateRequest) -> Dict[str, Any]:
    """
    建立新的 Lookup 記錄

    Args:
        data: Lookup 資料

    Returns:
        {
            "success": True,
            "id": 123,
            "message": "建立成功"
        }
    """
    logger.info(f"➕ 建立 Lookup | vendor_id={data.vendor_id}, category={data.category}, key={data.lookup_key}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 檢查是否已存在相同的 key
            existing = await conn.fetchrow("""
                SELECT id FROM lookup_tables
                WHERE vendor_id = $1
                  AND category = $2
                  AND lookup_key = $3
            """, data.vendor_id, data.category, data.lookup_key)

            if existing:
                logger.warning(f"⚠️  Lookup 已存在 | id={existing['id']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"此 Lookup Key 已存在 (ID: {existing['id']})"
                )

            # 插入新記錄
            metadata_json = json.dumps(data.metadata) if data.metadata else None

            new_id = await conn.fetchval("""
                INSERT INTO lookup_tables (
                    vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, data.vendor_id, data.category, data.category_name, data.lookup_key,
                data.lookup_value, metadata_json, data.is_active)

            logger.info(f"✅ Lookup 建立成功 | id={new_id}")

            return {
                "success": True,
                "id": new_id,
                "message": "建立成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 建立 Lookup 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"建立失敗: {str(e)}")


@router.put("/lookup/{lookup_id}")
async def update_lookup(
    request: Request,
    lookup_id: int,
    data: LookupUpdateRequest
) -> Dict[str, Any]:
    """
    更新 Lookup 記錄

    Args:
        lookup_id: Lookup ID
        data: 更新資料（僅提供需要更新的欄位）

    Returns:
        {
            "success": True,
            "message": "更新成功"
        }
    """
    logger.info(f"✏️  更新 Lookup | id={lookup_id}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 檢查記錄是否存在
            existing = await conn.fetchrow("""
                SELECT id FROM lookup_tables WHERE id = $1
            """, lookup_id)

            if not existing:
                raise HTTPException(status_code=404, detail=f"Lookup ID {lookup_id} 不存在")

            # 建立更新語句
            update_fields = []
            update_values = []
            param_idx = 1

            if data.category_name is not None:
                update_fields.append(f"category_name = ${param_idx}")
                update_values.append(data.category_name)
                param_idx += 1

            if data.lookup_key is not None:
                update_fields.append(f"lookup_key = ${param_idx}")
                update_values.append(data.lookup_key)
                param_idx += 1

            if data.lookup_value is not None:
                update_fields.append(f"lookup_value = ${param_idx}")
                update_values.append(data.lookup_value)
                param_idx += 1

            if data.metadata is not None:
                update_fields.append(f"metadata = ${param_idx}")
                update_values.append(json.dumps(data.metadata))
                param_idx += 1

            if data.is_active is not None:
                update_fields.append(f"is_active = ${param_idx}")
                update_values.append(data.is_active)
                param_idx += 1

            if not update_fields:
                raise HTTPException(status_code=400, detail="未提供任何更新欄位")

            # 加入 updated_at
            update_fields.append(f"updated_at = NOW()")

            # 執行更新
            query = f"""
                UPDATE lookup_tables
                SET {', '.join(update_fields)}
                WHERE id = ${param_idx}
            """
            update_values.append(lookup_id)

            await conn.execute(query, *update_values)

            logger.info(f"✅ Lookup 更新成功 | id={lookup_id}")

            return {
                "success": True,
                "message": "更新成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新 Lookup 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")


@router.delete("/lookup/batch")
async def delete_all_lookup_by_vendor(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID"),
    auto_unlink_knowledge: bool = Query(False, description="是否自動解除知識庫關聯")
) -> Dict[str, Any]:
    """
    批量刪除指定 Vendor 的所有 Lookup 記錄

    Args:
        vendor_id: 業者 ID
        auto_unlink_knowledge: 是否自動解除該業者的知識庫關聯

    Returns:
        {
            "success": True,
            "deleted_count": 100,
            "message": "已刪除 100 筆記錄",
            "unlinked_knowledge_count": 5  # 解除關聯的知識庫數量
        }
    """
    logger.info(f"🗑️  批量刪除 Lookup | vendor_id={vendor_id}, auto_unlink={auto_unlink_knowledge}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 先查詢有多少筆
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM lookup_tables WHERE vendor_id = $1
            """, vendor_id)

            deleted_count = 0
            if count > 0:
                # 執行批量刪除
                result = await conn.execute("""
                    DELETE FROM lookup_tables WHERE vendor_id = $1
                """, vendor_id)

                deleted_count = int(result.split()[-1])
                logger.info(f"✅ 批量刪除成功 | vendor_id={vendor_id}, 刪除筆數={deleted_count}")
            else:
                logger.info(f"ℹ️  沒有需要刪除的 Lookup 記錄 | vendor_id={vendor_id}")

            # 自動解除知識庫關聯（不論是否有刪除記錄，只要使用者選擇解除關聯就執行）
            unlinked_knowledge_count = 0
            if auto_unlink_knowledge:
                try:
                    unlinked_knowledge_count = await _auto_unlink_knowledge_base(conn, vendor_id)
                    logger.info(f"🔓 自動解除知識庫關聯完成 | 解除數量: {unlinked_knowledge_count}")
                except Exception as e:
                    logger.error(f"❌ 自動解除知識庫關聯失敗: {e}", exc_info=True)

            # 組合訊息
            if deleted_count > 0 and unlinked_knowledge_count > 0:
                message = f"已刪除 {deleted_count} 筆記錄，解除 {unlinked_knowledge_count} 個知識庫關聯"
            elif deleted_count > 0:
                message = f"已刪除 {deleted_count} 筆記錄"
            elif unlinked_knowledge_count > 0:
                message = f"解除 {unlinked_knowledge_count} 個知識庫關聯"
            else:
                message = "沒有需要刪除的記錄"

            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": message,
                "unlinked_knowledge_count": unlinked_knowledge_count
            }

    except Exception as e:
        logger.error(f"❌ 批量刪除 Lookup 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量刪除失敗: {str(e)}")


@router.delete("/lookup/{lookup_id}")
async def delete_lookup(request: Request, lookup_id: int) -> Dict[str, Any]:
    """
    刪除 Lookup 記錄

    Args:
        lookup_id: Lookup ID

    Returns:
        {
            "success": True,
            "message": "刪除成功"
        }
    """
    logger.info(f"🗑️  刪除 Lookup | id={lookup_id}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 檢查記錄是否存在
            existing = await conn.fetchrow("""
                SELECT id FROM lookup_tables WHERE id = $1
            """, lookup_id)

            if not existing:
                raise HTTPException(status_code=404, detail=f"Lookup ID {lookup_id} 不存在")

            # 執行刪除
            await conn.execute("""
                DELETE FROM lookup_tables WHERE id = $1
            """, lookup_id)

            logger.info(f"✅ Lookup 刪除成功 | id={lookup_id}")

            return {
                "success": True,
                "message": "刪除成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 刪除 Lookup 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")


# ========== 批量匯入/匯出端點 ==========

@router.post("/lookup/import")
async def import_lookup_excel(
    request: Request,
    file: UploadFile = File(...),
    vendor_id: int = Query(..., description="業者 ID"),
    auto_link_knowledge: bool = Query(True, description="是否自動關聯知識庫")
) -> Dict[str, Any]:
    """
    批量匯入業務格式 Excel（多分頁）

    Args:
        file: 上傳的業務格式 Excel 檔案（多分頁）
        vendor_id: 業者 ID
        auto_link_knowledge: 是否自動將相關知識庫關聯到此業者

    Returns:
        {
            "success": True,
            "total": 100,
            "success_count": 95,
            "fail_count": 5,
            "errors": ["電費資訊-台北市...: key已存在", ...],
            "linked_knowledge_count": 5  # 關聯的知識庫數量
        }
    """
    logger.info(f"📥 批量匯入業務格式 Excel | vendor_id={vendor_id}, filename={file.filename}, auto_link={auto_link_knowledge}")

    db_pool = request.app.state.db_pool

    try:
        # 讀取檔案
        contents = await file.read()

        # 檢查檔案格式
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="僅支援 .xlsx, .xls 格式（業務格式多分頁 Excel）")

        # 轉換業務格式為 Lookup 格式
        logger.info(f"🔄 開始轉換業務格式為 Lookup 格式...")
        lookup_records = _convert_business_to_lookup_format(io.BytesIO(contents), vendor_id)
        logger.info(f"✅ 轉換完成，共 {len(lookup_records)} 筆記錄")

        if not lookup_records:
            raise HTTPException(status_code=400, detail="沒有可匯入的資料，請檢查 Excel 格式是否正確")

        total = len(lookup_records)
        success_count = 0
        fail_count = 0
        errors = []
        linked_knowledge_count = 0

        async with db_pool.acquire() as conn:
            for idx, record in enumerate(lookup_records):
                try:
                    category = record['category']
                    category_name = record['category_name']
                    lookup_key = record['lookup_key']
                    lookup_value = record['lookup_value']
                    metadata = record.get('metadata', '')
                    is_active = record.get('is_active', True)

                    # 檢查是否已存在
                    existing = await conn.fetchrow("""
                        SELECT id FROM lookup_tables
                        WHERE vendor_id = $1
                          AND category = $2
                          AND lookup_key = $3
                    """, vendor_id, category, lookup_key)

                    if existing:
                        errors.append(f"{category_name}-{lookup_key[:20]}: 已存在 (ID: {existing['id']})")
                        fail_count += 1
                        continue

                    # 插入新記錄
                    await conn.execute("""
                        INSERT INTO lookup_tables (
                            vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active)

                    success_count += 1

                except Exception as e:
                    error_msg = f"{record.get('category_name', 'Unknown')}-{record.get('lookup_key', '')[:20]}: {str(e)}"
                    errors.append(error_msg)
                    fail_count += 1
                    logger.error(f"❌ 匯入記錄失敗: {error_msg}")

            logger.info(f"✅ 批量匯入完成 | 成功: {success_count}, 失敗: {fail_count}")

            # 自動關聯知識庫 (移到 conn 作用域內)
            if auto_link_knowledge and success_count > 0:
                try:
                    linked_knowledge_count = await _auto_link_knowledge_base(conn, vendor_id, lookup_records)
                    logger.info(f"🔗 自動關聯知識庫完成 | 關聯數量: {linked_knowledge_count}")
                except Exception as e:
                    logger.error(f"❌ 自動關聯知識庫失敗: {e}", exc_info=True)
                    errors.append(f"自動關聯知識庫失敗: {str(e)}")

        return {
            "success": True,
            "total": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "errors": errors[:50],  # 最多返回50個錯誤訊息
            "linked_knowledge_count": linked_knowledge_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量匯入失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"匯入失敗: {str(e)}")


def _parse_multiline_value(value: str) -> Dict[str, str]:
    """
    解析多行格式的 lookup_value
    例如：
        房型：2房1廳1衛
        租金金額(元/月)：28000

    Returns:
        Dict[欄位名, 值]
    """
    if not value or pd.isna(value):
        return {}

    result = {}
    for line in str(value).split('\n'):
        line = line.strip()
        if '：' in line or ':' in line:
            # 支援中英文冒號
            parts = line.replace(':', '：').split('：', 1)
            if len(parts) == 2:
                key, val = parts
                result[key.strip()] = val.strip()
    return result


def _convert_business_to_lookup_format(excel_file: io.BytesIO, vendor_id: int) -> List[Dict[str, Any]]:
    """
    將業務格式（多分頁 Excel）轉換為 Lookup 格式記錄

    Args:
        excel_file: Excel 檔案 BytesIO
        vendor_id: 業者 ID

    Returns:
        List[Dict]: Lookup 記錄列表，每筆包含 {vendor_id, category, category_name, lookup_key, lookup_value, metadata}
    """
    lookup_records = []

    # 讀取所有分頁
    excel_data = pd.read_excel(excel_file, sheet_name=None)  # 讀取所有 sheet

    for sheet_name, df in excel_data.items():
        logger.info(f"🔄 處理分頁: {sheet_name}, 行數: {len(df)}")

        # 跳過範例行（第一行通常是範例）
        df = df[1:].reset_index(drop=True)

        # 根據分頁名稱判斷類別
        if '電費資訊' in sheet_name or sheet_name == '01_電費資訊⭐':
            # 電費資訊 - 整合處理，一行資料產生 ONE 筆整合記錄
            for _, row in df.iterrows():
                address = str(row.get('物件地址（必填）', '')).strip()
                if not address or pd.isna(address) or address == '' or address == 'nan':
                    continue

                # 提取所有欄位（寄送區間為必填，其他為選填）
                interval = str(row.get('寄送區間', '')).strip() if pd.notna(row.get('寄送區間')) else ''

                # 寄送區間是必填欄位，如果沒有就跳過這筆資料
                if not interval or interval == 'nan':
                    logger.warning(f"⚠️  跳過地址（缺少必填欄位 寄送區間）: {address}")
                    continue

                electric_number = str(row.get('電號', '')).strip() if pd.notna(row.get('電號')) else ''
                if electric_number == 'nan':
                    electric_number = ''

                method = str(row.get('計費方式', '')).strip() if pd.notna(row.get('計費方式')) else ''
                if method == 'nan':
                    method = ''

                rate = str(row.get('固定費率(元/度)', '')).strip() if pd.notna(row.get('固定費率(元/度)')) else ''
                if rate == 'nan':
                    rate = ''

                taipower_discount = str(row.get('台電優惠', '')).strip() if pd.notna(row.get('台電優惠')) else ''
                if taipower_discount == 'nan':
                    taipower_discount = ''

                sharing_method = str(row.get('分攤方式', '')).strip() if pd.notna(row.get('分攤方式')) else ''
                if sharing_method == 'nan':
                    sharing_method = ''

                reading_day = str(row.get('抄表日', '')).strip() if pd.notna(row.get('抄表日')) else ''
                if reading_day == 'nan':
                    reading_day = ''

                payment_day = str(row.get('繳費日', '')).strip() if pd.notna(row.get('繳費日')) else ''
                if payment_day == 'nan':
                    payment_day = ''

                note = str(row.get('備註', '')).strip() if pd.notna(row.get('備註')) else ''
                if note == 'nan':
                    note = ''

                # 建立整合的 JSON 資料結構
                electricity_data = {
                    "寄送區間": interval,  # MANDATORY
                    "電號": electric_number,
                    "計費方式": method,
                    "固定費率(元/度)": rate,
                    "台電優惠": taipower_discount,
                    "分攤方式": sharing_method,
                    "抄表日": reading_day,
                    "繳費日": payment_day,
                    "備註": note
                }

                # 建立友善的說明文字
                note_parts = [f"您的電費資訊：帳單每【{interval}】寄送"]
                if method:
                    note_parts.append(f"，計費方式為【{method}】")
                    if rate:
                        note_parts.append(f"（{rate} 元/度）")
                if reading_day:
                    note_parts.append(f"，抄表日為【{reading_day}】")
                if payment_day:
                    note_parts.append(f"，繳費日為【{payment_day}】")
                note_parts.append("。")

                friendly_note = ''.join(note_parts)

                # metadata 包含友善說明和電號
                metadata = {
                    "note": friendly_note,
                    "electric_number": electric_number
                }

                # 產生 ONE 筆整合記錄
                lookup_records.append({
                    'vendor_id': vendor_id,
                    'category': 'utility_electricity',
                    'category_name': '電費資訊',
                    'lookup_key': address,
                    'lookup_value': json.dumps(electricity_data, ensure_ascii=False),
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'is_active': True
                })

        elif '水費資訊' in sheet_name or sheet_name == '02_水費資訊⭐':
            # 水費資訊 - 整合處理，一行資料產生 ONE 筆整合記錄
            for _, row in df.iterrows():
                address = str(row.get('物件地址（必填）', '')).strip()
                if not address or pd.isna(address) or address == '' or address == 'nan':
                    continue

                # 提取所有欄位（寄送區間建議為必填，但不強制）
                water_meter = str(row.get('水表編號', '')).strip() if pd.notna(row.get('水表編號')) else ''
                if water_meter == 'nan':
                    water_meter = ''

                interval = str(row.get('寄送區間', '')).strip() if pd.notna(row.get('寄送區間')) else ''
                if interval == 'nan':
                    interval = ''

                method = str(row.get('計費方式', '')).strip() if pd.notna(row.get('計費方式')) else ''
                if method == 'nan':
                    method = ''

                rate = str(row.get('固定費率(元/度)', '')).strip() if pd.notna(row.get('固定費率(元/度)')) else ''
                if rate == 'nan':
                    rate = ''

                reading_day = str(row.get('抄表日', '')).strip() if pd.notna(row.get('抄表日')) else ''
                if reading_day == 'nan':
                    reading_day = ''

                payment_day = str(row.get('繳費日', '')).strip() if pd.notna(row.get('繳費日')) else ''
                if payment_day == 'nan':
                    payment_day = ''

                sharing_method = str(row.get('分攤方式', '')).strip() if pd.notna(row.get('分攤方式')) else ''
                if sharing_method == 'nan':
                    sharing_method = ''

                note = str(row.get('備註', '')).strip() if pd.notna(row.get('備註')) else ''
                if note == 'nan':
                    note = ''

                # 建立整合的 JSON 資料結構
                water_data = {
                    "水表編號": water_meter,
                    "寄送區間": interval,
                    "計費方式": method,
                    "固定費率(元/度)": rate,
                    "抄表日": reading_day,
                    "繳費日": payment_day,
                    "分攤方式": sharing_method,
                    "備註": note
                }

                # 建立友善的說明文字
                note_parts = []
                if interval:
                    note_parts.append(f"您的水費資訊：帳單每【{interval}】寄送")
                elif method:
                    note_parts.append(f"您的水費資訊：計費方式為【{method}】")
                else:
                    note_parts.append("您的水費資訊")

                if method and interval:
                    note_parts.append(f"，計費方式為【{method}】")
                    if rate:
                        note_parts.append(f"（{rate} 元/度）")
                if reading_day:
                    note_parts.append(f"，抄表日為【{reading_day}】")
                if payment_day:
                    note_parts.append(f"，繳費日為【{payment_day}】")
                note_parts.append("。")

                friendly_note = ''.join(note_parts)

                # metadata 包含友善說明和水表編號
                metadata = {
                    "note": friendly_note,
                    "water_meter_number": water_meter
                }

                # 產生 ONE 筆整合記錄
                lookup_records.append({
                    'vendor_id': vendor_id,
                    'category': 'utility_water',
                    'category_name': '水費資訊',
                    'lookup_key': address,
                    'lookup_value': json.dumps(water_data, ensure_ascii=False),
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'is_active': True
                })

        elif '瓦斯費資訊' in sheet_name or sheet_name == '03_瓦斯費資訊⭐':
            # 瓦斯費資訊 - 整合處理，一行資料產生 ONE 筆整合記錄
            for _, row in df.iterrows():
                address = str(row.get('物件地址（必填）', '')).strip()
                if not address or pd.isna(address) or address == '' or address == 'nan':
                    continue

                # 提取所有欄位（瓦斯公司為必填）
                gas_company = str(row.get('瓦斯公司', '')).strip() if pd.notna(row.get('瓦斯公司')) else ''

                # 瓦斯公司是必填欄位
                if not gas_company or gas_company == 'nan':
                    logger.warning(f"⚠️  跳過地址（缺少必填欄位 瓦斯公司）: {address}")
                    continue

                method = str(row.get('計費方式', '')).strip() if pd.notna(row.get('計費方式')) else ''
                if method == 'nan':
                    method = ''

                rate = str(row.get('固定費率(元/度)', '')).strip() if pd.notna(row.get('固定費率(元/度)')) else ''
                if rate == 'nan':
                    rate = ''

                reading_method = str(row.get('抄表方式', '')).strip() if pd.notna(row.get('抄表方式')) else ''
                if reading_method == 'nan':
                    reading_method = ''

                payment_day = str(row.get('繳費日', '')).strip() if pd.notna(row.get('繳費日')) else ''
                if payment_day == 'nan':
                    payment_day = ''

                gas_phone = str(row.get('瓦斯公司電話', '')).strip() if pd.notna(row.get('瓦斯公司電話')) else ''
                if gas_phone == 'nan':
                    gas_phone = ''

                note = str(row.get('備註', '')).strip() if pd.notna(row.get('備註')) else ''
                if note == 'nan':
                    note = ''

                # 建立整合的 JSON 資料結構
                gas_data = {
                    "瓦斯公司": gas_company,  # MANDATORY
                    "計費方式": method,
                    "固定費率(元/度)": rate,
                    "抄表方式": reading_method,
                    "繳費日": payment_day,
                    "瓦斯公司電話": gas_phone,
                    "備註": note
                }

                # 建立友善的說明文字
                note_parts = [f"您的瓦斯費資訊：瓦斯公司為【{gas_company}】"]
                if gas_phone:
                    note_parts.append(f"（電話：{gas_phone}）")
                if method:
                    note_parts.append(f"，計費方式為【{method}】")
                    if rate:
                        note_parts.append(f"（{rate} 元/度）")
                if payment_day:
                    note_parts.append(f"，繳費日為【{payment_day}】")
                note_parts.append("。")

                friendly_note = ''.join(note_parts)

                # metadata 包含友善說明和瓦斯公司資訊
                metadata = {
                    "note": friendly_note,
                    "gas_company": gas_company,
                    "gas_company_phone": gas_phone
                }

                # 產生 ONE 筆整合記錄
                lookup_records.append({
                    'vendor_id': vendor_id,
                    'category': 'utility_gas',
                    'category_name': '瓦斯費資訊',
                    'lookup_key': address,
                    'lookup_value': json.dumps(gas_data, ensure_ascii=False),
                    'metadata': json.dumps(metadata, ensure_ascii=False),
                    'is_active': True
                })

        else:
            # 其他類別 - 通用處理
            # 根據分頁名稱對應到 category
            sheet_to_category = {
                '02_水費資訊⭐': ('water_billing', '水費資訊', ['物件地址（必填）', '水表編號', '寄送區間', '計費方式', '固定費率(元/度)', '抄表日', '繳費日', '分攤方式', '備註']),
                '03_瓦斯費資訊⭐': ('gas_billing', '瓦斯費資訊', ['物件地址（必填）', '瓦斯公司', '計費方式', '固定費率(元/度)', '抄表方式', '繳費日', '瓦斯公司電話', '備註']),
                '04_租金資訊⭐': ('rent_info', '租金資訊', ['物件地址/房號（必填）', '房型', '租金金額(元/月)', '調整週期', '調整幅度上限', '繳納日', '繳費方式', '轉帳帳號', '滯納金(元/天)', '備註']),
                '05_押金資訊⭐': ('deposit_info', '押金資訊', ['物件地址/房號（必填）', '押金金額', '押金用途', '返還時機', '返還方式', '可扣抵項目', '不可扣抵項目', '備註']),
                '06_管理費資訊⭐⭐': ('management_fee', '管理費資訊', ['物件地址/房號（必填）', '管理費金額(元/月)', '計價方式', '單價(元/坪)', '包含項目', '不包含項目', '繳納方式', '調整規則', '備註']),
                '07_停車費資訊⭐': ('parking_fee', '停車費資訊', ['物件地址/停車場（必填）', '車位編號（必填）', '停車位類型', '月租費用(元/月)', '申請方式', '所需文件', '審核時間', '繳費方式', '臨時停車費用', '備註']),
                '08_客服聯絡方式⭐': ('customer_service', '客服聯絡方式', ['聯絡類型（必填）', '聯絡資訊', '適用問題類型', '服務時間', '回應時效', '備註']),
                '09_公共設施清單⭐⭐': ('community_facilities', '公共設施清單', ['社區/物件地址（必填）', '設施名稱（必填）', '位置(樓層)', '開放時間', '收費標準', '是否需預約', '預約方式', '使用規則重點', '容納人數/限制', '備註']),
                '10_包裹代收服務⭐⭐': ('parcel_service', '包裹代收服務', ['物件地址（必填）', '服務類型（必填）', '收件地址格式', '包裹室位置', '代收時間', '取件時間', '尺寸限制', '重量限制', '保管天數', '備註']),
                '11_配合廠商清單⭐⭐⭐': ('vendor_contacts', '配合廠商清單', ['服務類型（必填）', '廠商名稱', '聯絡電話', '服務範圍', '住戶優惠', '參考價格', '推薦原因', '備註']),
                '12_服務時間⭐⭐': ('service_hours', '服務時間', ['日期類型（必填）', '開始時間', '結束時間', '午休時間', '服務項目限制', '備註']),
                '13_維修流程⭐': ('maintenance_flow', '維修流程', ['維修類型（必填）', '報修方式', '受理時間', '處理流程', '完成時效', '費用負擔', '備註']),
                '14_繳費方式⭐⭐⭐': ('payment_methods', '繳費方式', ['繳費方式（必填）', '適用費用', '帳戶資訊', '繳費期限', '繳費地點/方式', '注意事項', '手續費', '備註'])
            }

            if sheet_name in sheet_to_category:
                category, category_name, columns = sheet_to_category[sheet_name]

                for _, row in df.iterrows():
                    # 第一個欄位是 lookup_key（必填）
                    lookup_key_part1 = str(row.get(columns[0], '')).strip()
                    if not lookup_key_part1 or pd.isna(lookup_key_part1) or lookup_key_part1 == '' or lookup_key_part1 == 'nan':
                        continue

                    # 特殊處理：有第二個「必填」欄位的類別，需要組合成唯一的 lookup_key
                    if category in ['parking_fee', 'community_facilities', 'parcel_service']:
                        # 這些類別有第二個必填欄位，需要組合以確保唯一性
                        lookup_key_part2 = str(row.get(columns[1], '')).strip()
                        if not lookup_key_part2 or pd.isna(lookup_key_part2) or lookup_key_part2 == '' or lookup_key_part2 == 'nan':
                            continue
                        lookup_key = f"{lookup_key_part1}-{lookup_key_part2}"
                        # value 從第三個欄位開始
                        value_start_index = 2
                    elif category == 'payment_methods':
                        # 繳費方式：用「方式 + 繳費地點」組合
                        payment_location = str(row.get('繳費地點/方式', '')).strip()
                        if payment_location and payment_location != 'nan' and payment_location != '':
                            lookup_key = f"{lookup_key_part1}-{payment_location}"
                        else:
                            # 如果沒有繳費地點，使用帳戶資訊作為區別
                            account_info = str(row.get('帳戶資訊', '')).strip()
                            if account_info and account_info != 'nan' and account_info != '':
                                # 取帳戶資訊的前20個字作為區別
                                lookup_key = f"{lookup_key_part1}-{account_info[:20]}"
                            else:
                                lookup_key = lookup_key_part1
                        value_start_index = 1
                    elif category == 'service_hours':
                        # 服務時間：用「日期類型 + 開始時間 + 服務項目限制」組合以確保唯一性
                        start_time = str(row.get('開始時間', '')).strip()
                        service_limit = str(row.get('服務項目限制', '')).strip()

                        key_parts = [lookup_key_part1]
                        if start_time and start_time != 'nan' and start_time != '':
                            key_parts.append(start_time)
                        if service_limit and service_limit != 'nan' and service_limit != '':
                            # 取服務項目限制的前15個字作為區別
                            key_parts.append(service_limit[:15])

                        lookup_key = '-'.join(key_parts)
                        value_start_index = 1
                    else:
                        lookup_key = lookup_key_part1
                        value_start_index = 1

                    # 將其他欄位組合成多行格式的 lookup_value
                    value_parts = []
                    for col in columns[value_start_index:]:  # 從適當的位置開始
                        if pd.notna(row.get(col)) and str(row.get(col)).strip() and str(row.get(col)).strip() != 'nan':
                            value_parts.append(f"{col}：{str(row.get(col)).strip()}")

                    if value_parts:  # 只有當有資料時才建立記錄
                        lookup_value = '\n'.join(value_parts)

                        lookup_records.append({
                            'vendor_id': vendor_id,
                            'category': category,
                            'category_name': category_name,
                            'lookup_key': lookup_key,
                            'lookup_value': lookup_value,
                            'metadata': '{}',
                            'is_active': True
                        })
            else:
                logger.warning(f"⚠️ 未知的分頁名稱: {sheet_name}，跳過處理")

    logger.info(f"✅ 業務格式轉換完成，共產生 {len(lookup_records)} 筆 Lookup 記錄")
    return lookup_records


def _convert_lookup_to_business_format(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    將 lookup 表格式轉換為業務格式（多分頁）

    Returns:
        Dict[str, pd.DataFrame]: sheet_name → DataFrame 的字典
    """
    sheets = {}

    # 如果 DataFrame 是空的，直接返回空字典
    if df.empty:
        logger.warning("⚠️ DataFrame 是空的，無法轉換")
        return sheets

    # 檢查必要的欄位是否存在
    required_columns = ['metadata_json', 'category', 'lookup_key', 'lookup_value']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"❌ DataFrame 缺少必要欄位: {missing_columns}")
        return sheets

    # 解析 metadata
    df['metadata_parsed'] = df['metadata_json'].apply(
        lambda x: json.loads(x) if x and x != '' else {}
    )

    # 解析多行格式的 lookup_value
    df['parsed_values'] = df['lookup_value'].apply(_parse_multiline_value)

    # 定義業務類別與對應的分頁名稱、欄位
    # 這裡只實作幾個主要類別作為示範，可以後續擴充

    # 1. 電費資訊（整合版）
    df_elec = df[df['category'] == 'utility_electricity'].copy()
    if not df_elec.empty:
        records = []
        for _, row in df_elec.iterrows():
            # lookup_value 是 JSON 字串，需要解析
            try:
                if isinstance(row['lookup_value'], str):
                    electricity_data = json.loads(row['lookup_value'])
                else:
                    electricity_data = row['lookup_value']
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"⚠️  無法解析電費資訊 JSON: {row['lookup_key']}")
                continue

            # 從 metadata 取得電號（若 JSON 中沒有）
            meta = row['metadata_parsed']
            electric_number = electricity_data.get('電號', '') or meta.get('electric_number', '')

            record = {
                '物件地址（必填）': row['lookup_key'],
                '電號': electric_number,
                '寄送區間': electricity_data.get('寄送區間', ''),
                '計費方式': electricity_data.get('計費方式', ''),
                '固定費率(元/度)': electricity_data.get('固定費率(元/度)', ''),
                '抄表日': electricity_data.get('抄表日', ''),
                '繳費日': electricity_data.get('繳費日', ''),
                '台電優惠': electricity_data.get('台電優惠', ''),
                '分攤方式': electricity_data.get('分攤方式', ''),
                '備註': electricity_data.get('備註', '')
            }

            records.append(record)

        if records:
            sheets['01_電費資訊⭐'] = pd.DataFrame(records)[
                ['物件地址（必填）', '電號', '寄送區間', '計費方式', '固定費率(元/度)', '抄表日', '繳費日', '台電優惠', '分攤方式', '備註']
            ]

    # 2. 水費資訊（整合版）
    df_water = df[df['category'] == 'utility_water'].copy()
    if not df_water.empty:
        records = []
        for _, row in df_water.iterrows():
            # lookup_value 是 JSON 字串，需要解析
            try:
                if isinstance(row['lookup_value'], str):
                    water_data = json.loads(row['lookup_value'])
                else:
                    water_data = row['lookup_value']
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"⚠️  無法解析水費資訊 JSON: {row['lookup_key']}")
                continue

            # 從 metadata 取得水表編號（若 JSON 中沒有）
            meta = row['metadata_parsed']
            water_meter = water_data.get('水表編號', '') or meta.get('water_meter_number', '')

            record = {
                '物件地址（必填）': row['lookup_key'],
                '水表編號': water_meter,
                '寄送區間': water_data.get('寄送區間', ''),
                '計費方式': water_data.get('計費方式', ''),
                '固定費率(元/度)': water_data.get('固定費率(元/度)', ''),
                '抄表日': water_data.get('抄表日', ''),
                '繳費日': water_data.get('繳費日', ''),
                '分攤方式': water_data.get('分攤方式', ''),
                '備註': water_data.get('備註', '')
            }

            records.append(record)

        if records:
            sheets['02_水費資訊⭐'] = pd.DataFrame(records)[
                ['物件地址（必填）', '水表編號', '寄送區間', '計費方式', '固定費率(元/度)', '抄表日', '繳費日', '分攤方式', '備註']
            ]

    # 3. 瓦斯費資訊（整合版）
    df_gas = df[df['category'] == 'utility_gas'].copy()
    if not df_gas.empty:
        records = []
        for _, row in df_gas.iterrows():
            # lookup_value 是 JSON 字串，需要解析
            try:
                if isinstance(row['lookup_value'], str):
                    gas_data = json.loads(row['lookup_value'])
                else:
                    gas_data = row['lookup_value']
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"⚠️  無法解析瓦斯費資訊 JSON: {row['lookup_key']}")
                continue

            # 從 metadata 取得瓦斯公司資訊（若 JSON 中沒有）
            meta = row['metadata_parsed']
            gas_company = gas_data.get('瓦斯公司', '') or meta.get('gas_company', '')
            gas_phone = gas_data.get('瓦斯公司電話', '') or meta.get('gas_company_phone', '')

            record = {
                '物件地址（必填）': row['lookup_key'],
                '瓦斯公司': gas_company,
                '計費方式': gas_data.get('計費方式', ''),
                '固定費率(元/度)': gas_data.get('固定費率(元/度)', ''),
                '抄表方式': gas_data.get('抄表方式', ''),
                '繳費日': gas_data.get('繳費日', ''),
                '瓦斯公司電話': gas_phone,
                '備註': gas_data.get('備註', '')
            }

            records.append(record)

        if records:
            sheets['03_瓦斯費資訊⭐'] = pd.DataFrame(records)[
                ['物件地址（必填）', '瓦斯公司', '計費方式', '固定費率(元/度)', '抄表方式', '繳費日', '瓦斯公司電話', '備註']
            ]

    # 4. 其他類別 - 通用處理（簡化版）
    category_mapping = {
        'water_billing': ('02_水費資訊⭐', ['物件地址（必填）', '水表編號', '寄送區間', '計費方式', '固定費率(元/度)', '抄表日', '繳費日', '分攤方式', '備註']),
        'gas_billing': ('03_瓦斯費資訊⭐', ['物件地址（必填）', '瓦斯公司', '計費方式', '固定費率(元/度)', '抄表方式', '繳費日', '瓦斯公司電話', '備註']),
        'rent_info': ('04_租金資訊⭐', ['物件地址/房號（必填）', '房型', '租金金額(元/月)', '調整週期', '調整幅度上限', '繳納日', '繳費方式', '轉帳帳號', '滯納金(元/天)', '備註']),
        'deposit_info': ('05_押金資訊⭐', ['物件地址/房號（必填）', '押金金額', '押金用途', '返還時機', '返還方式', '可扣抵項目', '不可扣抵項目', '備註']),
        'management_fee': ('06_管理費資訊⭐⭐', ['物件地址/房號（必填）', '管理費金額(元/月)', '計價方式', '單價(元/坪)', '包含項目', '不包含項目', '繳納方式', '調整規則', '備註']),
        'parking_fee': ('07_停車費資訊⭐', ['物件地址/停車場（必填）', '車位編號（必填）', '停車位類型', '月租費用(元/月)', '申請方式', '所需文件', '審核時間', '繳費方式', '臨時停車費用', '備註']),
        'customer_service': ('08_客服聯絡方式⭐', ['聯絡類型（必填）', '聯絡資訊', '適用問題類型', '服務時間', '回應時效', '備註']),
        'community_facilities': ('09_公共設施清單⭐⭐', ['社區/物件地址（必填）', '設施名稱（必填）', '位置(樓層)', '開放時間', '收費標準', '是否需預約', '預約方式', '使用規則重點', '容納人數/限制', '備註']),
        'parcel_service': ('10_包裹代收服務⭐⭐', ['物件地址（必填）', '服務類型（必填）', '收件地址格式', '包裹室位置', '代收時間', '取件時間', '尺寸限制', '重量限制', '保管天數', '備註']),
        'vendor_contacts': ('11_配合廠商清單⭐⭐⭐', ['服務類型（必填）', '廠商名稱', '聯絡電話', '服務範圍', '住戶優惠', '參考價格', '推薦原因', '備註']),
        'service_hours': ('12_服務時間⭐⭐', ['日期類型（必填）', '開始時間', '結束時間', '午休時間', '服務項目限制', '備註']),
        'payment_methods': ('14_繳費方式⭐⭐⭐', ['繳費方式（必填）', '適用費用', '帳戶資訊', '繳費期限', '繳費地點/方式', '注意事項', '手續費', '備註']),
        'maintenance_flow': ('13_維修流程⭐', ['維修類型（必填）', '報修方式', '受理時間', '處理流程', '完成時效', '費用負擔', '備註'])
    }

    for category, (sheet_name, columns) in category_mapping.items():
        df_cat = df[df['category'] == category].copy()
        if not df_cat.empty:
            records = []
            for _, row in df_cat.iterrows():
                record = {col: '' for col in columns}

                # 特殊處理：有組合 lookup_key 的類別需要拆分
                lookup_key = row['lookup_key']
                if category in ['parking_fee', 'community_facilities', 'parcel_service']:
                    # 這些類別的 lookup_key 格式為 "part1-part2"
                    if '-' in lookup_key:
                        parts = lookup_key.split('-', 1)  # 只分割第一個 '-'
                        record[columns[0]] = parts[0]
                        record[columns[1]] = parts[1] if len(parts) > 1 else ''
                    else:
                        record[columns[0]] = lookup_key
                        record[columns[1]] = ''
                elif category in ['payment_methods', 'service_hours']:
                    # 這些類別的 lookup_key 可能包含額外資訊，需要拆分
                    if '-' in lookup_key:
                        parts = lookup_key.split('-', 1)
                        record[columns[0]] = parts[0]
                        # 其他資訊會在 parsed_values 中
                    else:
                        record[columns[0]] = lookup_key
                else:
                    # 一般類別：第一個欄位是 key
                    record[columns[0]] = lookup_key

                # 使用解析後的 parsed_values 填充其他欄位
                parsed = row['parsed_values']
                start_col = 2 if category in ['parking_fee', 'community_facilities', 'parcel_service'] else 1
                for col in columns[start_col:]:  # 跳過已經填過的欄位
                    # 嘗試從 parsed_values 中找到對應的值
                    if col in parsed:
                        record[col] = parsed[col]

                records.append(record)

            if records:
                sheets[sheet_name] = pd.DataFrame(records)[columns]

    # 在每個分頁的第一行加入範例資料
    for sheet_name, sheet_df in sheets.items():
        # 建立範例行（所有欄位填入提示文字）
        example_row = {}
        for col in sheet_df.columns:
            if '必填' in col:
                example_row[col] = '請填寫（範例）'
            else:
                example_row[col] = '（範例）'

        # 將範例行插入到第一行
        example_df = pd.DataFrame([example_row])
        sheets[sheet_name] = pd.concat([example_df, sheet_df], ignore_index=True)

    return sheets if sheets else {'Lookup Data': df}


@router.get("/lookup/export")
async def export_lookup_excel(
    request: Request,
    vendor_id: int = Query(..., description="業者 ID"),
    category: Optional[str] = Query(None, description="類別篩選")
) -> StreamingResponse:
    """
    匯出 Lookup 數據為業務格式 Excel（多分頁）

    Args:
        vendor_id: 業者 ID
        category: 可選的類別篩選

    Returns:
        Excel 檔案流
    """
    logger.info(f"📤 匯出 Lookup | vendor_id={vendor_id}, category={category}")

    db_pool = request.app.state.db_pool

    try:
        async with db_pool.acquire() as conn:
            # 建立查詢
            where_clauses = ["vendor_id = $1"]
            params = [vendor_id]

            if category:
                where_clauses.append(f"category = ${len(params) + 1}")
                params.append(category)

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT id, vendor_id, category, category_name, lookup_key, lookup_value,
                       metadata, is_active, created_at, updated_at
                FROM lookup_tables
                WHERE {where_sql}
                ORDER BY category, id
            """

            rows = await conn.fetch(query, *params)

            # 轉換為 DataFrame
            data = []
            for row in rows:
                # 將 metadata 轉換為 JSON 字串
                metadata_json = ''
                if row['metadata']:
                    if isinstance(row['metadata'], dict):
                        metadata_json = json.dumps(row['metadata'], ensure_ascii=False)
                    elif isinstance(row['metadata'], str):
                        metadata_json = row['metadata']

                data.append({
                    'id': row['id'],
                    'category': row['category'],
                    'category_name': row['category_name'] or '',
                    'lookup_key': row['lookup_key'],
                    'lookup_value': row['lookup_value'],
                    'metadata_json': metadata_json,
                    'is_active': 'TRUE' if row['is_active'] else 'FALSE',
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
                })

            df = pd.DataFrame(data)

            # 如果沒有資料，返回友善的錯誤訊息
            if df.empty:
                logger.warning(f"⚠️ vendor_id={vendor_id} 沒有 Lookup 資料")
                raise HTTPException(
                    status_code=404,
                    detail="沒有可匯出的 Lookup 資料"
                )

            # 轉換為業務格式（多分頁）
            logger.info(f"🔄 開始轉換為業務格式，原始筆數：{len(df)}")
            sheets_dict = _convert_lookup_to_business_format(df)
            logger.info(f"✅ 轉換完成，生成 {len(sheets_dict)} 個分頁")

            # 如果轉換後沒有任何分頁，也返回錯誤
            if not sheets_dict:
                logger.warning(f"⚠️ vendor_id={vendor_id} 的資料無法轉換為業務格式")
                raise HTTPException(
                    status_code=500,
                    detail="資料轉換失敗：無法生成任何業務格式分頁"
                )

            # 建立 Excel 檔案（多分頁）
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for sheet_name, sheet_df in sheets_dict.items():
                    sheet_df.to_excel(writer, index=False, sheet_name=sheet_name)
                    logger.info(f"  - {sheet_name}: {len(sheet_df)} 筆")

            output.seek(0)

            # 設定檔名
            filename = f"vendor_knowledge_vendor{vendor_id}"
            if category:
                filename += f"_{category}"
            filename += f"_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx"

            logger.info(f"✅ 匯出完成 | 共 {len(data)} 筆 | {len(sheets_dict)} 個分頁")

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

    except HTTPException:
        # 直接重新拋出 HTTPException，保留原始狀態碼和訊息
        raise
    except Exception as e:
        logger.error(f"❌ 匯出失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")


@router.get("/lookup/template")
async def download_template() -> FileResponse:
    """
    下載 Lookup 資料匯入範本

    Returns:
        Excel 範本檔案
    """
    logger.info("📥 下載 Lookup 匯入範本")

    template_path = Path(__file__).parent.parent / "templates" / "Lookup匯入範本.xlsx"

    if not template_path.exists():
        logger.error(f"❌ 範本檔案不存在: {template_path}")
        raise HTTPException(status_code=404, detail="範本檔案不存在")

    return FileResponse(
        path=str(template_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Lookup匯入範本.xlsx"
    )


# ========== 知識庫自動關聯輔助函數 ==========

async def _auto_link_knowledge_base(conn, vendor_id: int, lookup_records: List[Dict[str, Any]]) -> int:
    """
    根據 Lookup 資料自動關聯知識庫

    Args:
        conn: 資料庫連接
        vendor_id: 業者 ID
        lookup_records: Lookup 記錄列表

    Returns:
        int: 關聯的知識庫數量
    """
    # Lookup 類別與知識庫表單的對應關係
    CATEGORY_TO_FORM_MAPPING = {
        'utility_electricity': ['billing_address_form_v2'],
        'utility_water': ['water_billing_form_v2'],
        'utility_gas': ['gas_billing_form_v2'],
        'rent_info': ['rent_info_form_v2'],
        'deposit_info': ['deposit_info_form_v2'],
        'management_fee': ['management_fee_form_v2'],
        'parking_fee': ['parking_fee_form_v2'],
        'community_facilities': ['community_facilities_form_v2'],
        'parcel_service': ['parcel_service_form_v2'],
    }

    # 收集已匯入的類別
    imported_categories = set(record.get('category') for record in lookup_records)

    # 找出需要關聯的表單
    form_ids_to_link = []
    for category in imported_categories:
        if category in CATEGORY_TO_FORM_MAPPING:
            form_ids_to_link.extend(CATEGORY_TO_FORM_MAPPING[category])

    if not form_ids_to_link:
        logger.info(f"📝 沒有需要關聯的知識庫")
        return 0

    # 查詢使用這些表單的知識庫
    knowledge_ids = await conn.fetch("""
        SELECT id, question_summary, vendor_ids, form_id
        FROM knowledge_base
        WHERE form_id = ANY($1)
          AND action_type IN ('form_fill', 'form_then_api', 'api_call')
    """, form_ids_to_link)

    linked_count = 0
    for kb in knowledge_ids:
        kb_id = kb['id']
        current_vendor_ids = kb['vendor_ids'] or []

        # 如果該 vendor_id 還沒關聯，則加入
        if vendor_id not in current_vendor_ids:
            new_vendor_ids = current_vendor_ids + [vendor_id]

            await conn.execute("""
                UPDATE knowledge_base
                SET vendor_ids = $1, updated_at = NOW()
                WHERE id = $2
            """, new_vendor_ids, kb_id)

            logger.info(f"🔗 關聯知識庫 ID={kb_id} ({kb['question_summary']}) 到 vendor_id={vendor_id}")
            linked_count += 1

    return linked_count


async def _auto_unlink_knowledge_base(conn, vendor_id: int) -> int:
    """
    移除業者的所有知識庫關聯

    Args:
        conn: 資料庫連接
        vendor_id: 業者 ID

    Returns:
        int: 解除關聯的知識庫數量
    """
    # 查詢所有包含該 vendor_id 的知識庫
    knowledge_list = await conn.fetch("""
        SELECT id, question_summary, vendor_ids
        FROM knowledge_base
        WHERE $1 = ANY(vendor_ids)
    """, vendor_id)

    unlinked_count = 0
    for kb in knowledge_list:
        kb_id = kb['id']
        current_vendor_ids = kb['vendor_ids'] or []

        # 移除該 vendor_id
        new_vendor_ids = [vid for vid in current_vendor_ids if vid != vendor_id]

        await conn.execute("""
            UPDATE knowledge_base
            SET vendor_ids = $1, updated_at = NOW()
            WHERE id = $2
        """, new_vendor_ids, kb_id)

        logger.info(f"🔓 解除知識庫 ID={kb_id} ({kb['question_summary']}) 與 vendor_id={vendor_id} 的關聯")
        unlinked_count += 1

    return unlinked_count
