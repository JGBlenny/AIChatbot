"""
Target User Configuration API
提供目標用戶類型配置查詢
"""
from fastapi import APIRouter, Request
from typing import List, Dict, Any

router = APIRouter()


@router.get("/api/v1/target-users-config", response_model=List[Dict[str, Any]])
async def get_target_users_config(request: Request):
    """
    獲取所有啟用的目標用戶類型配置

    Returns:
        List[Dict]: 目標用戶配置列表
        [
            {
                "id": 1,
                "user_value": "tenant",
                "display_name": "租客",
                "description": "承租人 - 租屋的一方",
                "icon": "👤",
                "display_order": 1
            },
            ...
        ]
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                id,
                user_value,
                display_name,
                description,
                icon,
                display_order
            FROM target_user_config
            WHERE is_active = true
            ORDER BY display_order ASC
        """)

        return [dict(row) for row in rows]
