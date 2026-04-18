"""
SOP 覆蓋率補齊工具函數
- deactivate_existing_sops: 停用現有 SOP
- create_categories_from_checklist: 批量建立分類
- checklist_to_gaps: 清單→SOPGenerator gaps 格式轉換
- init_db_pool / create_loop_record: DB helper
"""
import json
import asyncio
import asyncpg
import os
from typing import List, Dict, Optional
from datetime import datetime


# ============================================
# DB Helper
# ============================================

async def init_db_pool() -> asyncpg.Pool:
    """建立 asyncpg 連線池"""
    return await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=2,
        max_size=10,
    )


async def create_loop_record(
    db_pool: asyncpg.Pool,
    vendor_id: int,
    loop_name: str = "SOP Coverage Completion",
) -> int:
    """建立 knowledge_completion_loops 記錄，回傳 loop_id"""
    row = await db_pool.fetchrow(
        """
        INSERT INTO knowledge_completion_loops
            (loop_name, vendor_id, status, current_iteration,
             config, target_pass_rate, created_at, updated_at)
        VALUES ($1, $2, 'running', 1,
                '{"source": "sop_coverage_completion"}'::jsonb, 0.75, NOW(), NOW())
        RETURNING id
        """,
        loop_name,
        vendor_id,
    )
    return row["id"]


# ============================================
# Phase 2: 停用現有 SOP
# ============================================

async def deactivate_existing_sops(
    db_pool: asyncpg.Pool,
    vendor_id: int,
    exclude_ids: Optional[List[int]] = None,
) -> Dict:
    """
    停用指定業者的所有 SOP（is_active = false）

    Args:
        db_pool: asyncpg 連線池
        vendor_id: 業者 ID
        exclude_ids: 要保留的 SOP ID 列表（不停用）

    Returns:
        {"deactivated_count": int, "excluded_count": int, "deactivated_items": List[Dict]}
    """
    exclude_ids = exclude_ids or []

    # 先查詢要停用的項目（記錄用）
    if exclude_ids:
        rows = await db_pool.fetch(
            """
            SELECT id, item_name
            FROM vendor_sop_items
            WHERE vendor_id = $1 AND is_active = true AND id != ALL($2::int[])
            """,
            vendor_id,
            exclude_ids,
        )
    else:
        rows = await db_pool.fetch(
            """
            SELECT id, item_name
            FROM vendor_sop_items
            WHERE vendor_id = $1 AND is_active = true
            """,
            vendor_id,
        )

    deactivated_items = [{"id": r["id"], "item_name": r["item_name"]} for r in rows]

    # 執行停用
    if exclude_ids:
        result = await db_pool.execute(
            """
            UPDATE vendor_sop_items
            SET is_active = false, updated_at = NOW()
            WHERE vendor_id = $1 AND is_active = true AND id != ALL($2::int[])
            """,
            vendor_id,
            exclude_ids,
        )
    else:
        result = await db_pool.execute(
            """
            UPDATE vendor_sop_items
            SET is_active = false, updated_at = NOW()
            WHERE vendor_id = $1 AND is_active = true
            """,
            vendor_id,
        )

    deactivated_count = int(result.split()[-1]) if result else 0

    print(f"[停用 SOP] 停用 {deactivated_count} 筆, 排除 {len(exclude_ids)} 筆")
    for item in deactivated_items[:5]:
        print(f"  - [{item['id']}] {item['item_name']}")
    if len(deactivated_items) > 5:
        print(f"  ... 及其他 {len(deactivated_items) - 5} 筆")

    return {
        "deactivated_count": deactivated_count,
        "excluded_count": len(exclude_ids),
        "deactivated_items": deactivated_items,
    }


# ============================================
# Phase 2b: 清除舊的 loop_generated_knowledge
# ============================================

async def clear_old_generated_knowledge(
    db_pool: asyncpg.Pool,
    vendor_id: int,
) -> Dict:
    """
    清除指定業者的舊 loop_generated_knowledge 記錄（status != 'synced'）
    已同步的記錄保留，避免影響正式庫的來源追溯。

    Args:
        db_pool: asyncpg 連線池
        vendor_id: 業者 ID

    Returns:
        {"deleted_count": int}
    """
    # 透過 loop_id 關聯 vendor_id
    result = await db_pool.execute(
        """
        DELETE FROM loop_generated_knowledge
        WHERE status != 'synced'
          AND loop_id IN (
            SELECT id FROM knowledge_completion_loops WHERE vendor_id = $1
          )
        """,
        vendor_id,
    )
    deleted_count = int(result.split()[-1]) if result else 0
    print(f"[清除舊知識] 刪除 {deleted_count} 筆舊 loop_generated_knowledge（vendor_id={vendor_id}）")
    return {"deleted_count": deleted_count}


# ============================================
# Phase 3: 批量建立分類
# ============================================

async def create_categories_from_checklist(
    db_pool: asyncpg.Pool,
    vendor_id: int,
    checklist: List[Dict],
) -> Dict[str, int]:
    """
    根據流程清單批量建立 SOP 分類（已存在則跳過）

    Args:
        db_pool: asyncpg 連線池
        vendor_id: 業者 ID
        checklist: process_checklist.json 結構

    Returns:
        category_name → category_id 映射
    """
    category_map = {}

    for i, cat in enumerate(checklist):
        cat_name = cat["category_name"]

        # 先查是否已存在
        existing = await db_pool.fetchrow(
            """
            SELECT id FROM vendor_sop_categories
            WHERE vendor_id = $1 AND category_name = $2
            """,
            vendor_id,
            cat_name,
        )

        if existing:
            category_map[cat_name] = existing["id"]
            print(f"  [分類] {cat_name} — 已存在 (id={existing['id']})")
        else:
            row = await db_pool.fetchrow(
                """
                INSERT INTO vendor_sop_categories
                    (vendor_id, category_name, description, display_order)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                vendor_id,
                cat_name,
                cat.get("description", ""),
                i + 1,
            )
            category_map[cat_name] = row["id"]
            print(f"  [分類] {cat_name} — 新建 (id={row['id']})")

    print(f"[建立分類] 共 {len(category_map)} 個分類")
    return category_map


# ============================================
# Phase 4: 清單 → gaps 格式轉換
# ============================================

def checklist_to_gaps(
    checklist: List[Dict],
    category_map: Dict[str, int],
    exclude_topic_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """
    將流程清單子題轉換為 SOPGenerator 接受的 gaps 格式

    Args:
        checklist: process_checklist.json 結構
        category_map: category_name → category_id 映射
        exclude_topic_ids: 要排除的 topic_id 列表

    Returns:
        List[Dict] — SOPGenerator.generate_sop_items() 的 gaps 參數
    """
    exclude_topic_ids = set(exclude_topic_ids or [])
    gaps = []

    for cat in checklist:
        cat_name = cat["category_name"]
        category_id = category_map.get(cat_name)

        for subtopic in cat.get("subtopics", []):
            topic_id = subtopic["topic_id"]
            if topic_id in exclude_topic_ids:
                continue

            gaps.append({
                "test_question": subtopic["question"],
                "question": subtopic["question"],
                "gap_type": "sop_knowledge",
                "failure_reason": "COVERAGE_GAP",
                "priority": subtopic.get("priority", "p1"),
                "category_id": category_id,
                "keywords": subtopic.get("keywords", []),
                "business_type": subtopic.get("business_type", "both"),
                "cashflow_relevant": subtopic.get("cashflow_relevant", False),
                "topic_id": topic_id,
                "duplicate_threshold": 0.90,  # 覆蓋率補齊：只跳過幾乎完全相同的
            })

    print(f"[格式轉換] {len(gaps)} 筆 gaps（排除 {len(exclude_topic_ids)} 筆）")
    return gaps


# ============================================
# Helper: 載入 checklist
# ============================================

def load_checklist(path: str = "scripts/sop_coverage/process_checklist.json") -> List[Dict]:
    """載入 process_checklist.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
