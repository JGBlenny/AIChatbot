"""
意圖管理服務
負責意圖的 CRUD 操作、統計資訊等
"""

import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
import os


class IntentManager:
    """意圖管理服務"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin')
        }

    async def _get_connection(self):
        """取得資料庫連接"""
        return await asyncpg.connect(**self.db_config)

    # ========================================
    # 查詢操作
    # ========================================

    async def get_all_intents(
        self,
        enabled_only: bool = False,
        intent_type: Optional[str] = None,
        order_by: str = 'priority'  # priority, name, usage_count
    ) -> List[Dict[str, Any]]:
        """
        取得所有意圖

        Args:
            enabled_only: 只取得啟用的意圖
            intent_type: 過濾意圖類型（knowledge/data_query/action/hybrid）
            order_by: 排序方式

        Returns:
            意圖列表
        """
        conn = await self._get_connection()

        try:
            # 構建查詢
            query = "SELECT * FROM intents WHERE 1=1"
            params = []
            param_count = 0

            if enabled_only:
                query += " AND is_enabled = true"

            if intent_type:
                param_count += 1
                query += f" AND type = ${param_count}"
                params.append(intent_type)

            # 排序
            order_mapping = {
                'priority': 'priority DESC, name',
                'name': 'name',
                'usage_count': 'usage_count DESC, name'
            }
            query += f" ORDER BY {order_mapping.get(order_by, 'priority DESC, name')}"

            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def get_intent_by_id(self, intent_id: int) -> Optional[Dict[str, Any]]:
        """取得特定意圖"""
        conn = await self._get_connection()

        try:
            row = await conn.fetchrow(
                "SELECT * FROM intents WHERE id = $1",
                intent_id
            )

            return dict(row) if row else None

        finally:
            await conn.close()

    async def get_intent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根據名稱取得意圖"""
        conn = await self._get_connection()

        try:
            row = await conn.fetchrow(
                "SELECT * FROM intents WHERE name = $1",
                name
            )

            return dict(row) if row else None

        finally:
            await conn.close()

    # ========================================
    # 新增/更新/刪除操作
    # ========================================

    async def create_intent(
        self,
        name: str,
        type: str,
        description: str = "",
        keywords: List[str] = None,
        confidence_threshold: float = 0.80,
        api_required: bool = False,
        api_endpoint: Optional[str] = None,
        api_action: Optional[str] = None,
        priority: int = 0,
        created_by: str = "admin"
    ) -> int:
        """
        新增意圖

        Returns:
            新建意圖的 ID
        """
        conn = await self._get_connection()

        try:
            # 檢查名稱是否已存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM intents WHERE name = $1)",
                name
            )

            if exists:
                raise ValueError(f"意圖名稱 '{name}' 已存在")

            # 插入新意圖
            intent_id = await conn.fetchval("""
                INSERT INTO intents (
                    name, type, description, keywords,
                    confidence_threshold, is_enabled, priority,
                    api_required, api_endpoint, api_action,
                    created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """,
                name, type, description, keywords or [],
                confidence_threshold, True, priority,
                api_required, api_endpoint, api_action,
                created_by
            )

            print(f"✅ 新增意圖: {name} (ID: {intent_id})")
            return intent_id

        finally:
            await conn.close()

    async def update_intent(
        self,
        intent_id: int,
        name: Optional[str] = None,
        type: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        confidence_threshold: Optional[float] = None,
        priority: Optional[int] = None,
        api_required: Optional[bool] = None,
        api_endpoint: Optional[str] = None,
        api_action: Optional[str] = None,
        updated_by: str = "admin"
    ) -> bool:
        """
        更新意圖

        Returns:
            是否更新成功
        """
        conn = await self._get_connection()

        try:
            # 檢查意圖是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM intents WHERE id = $1)",
                intent_id
            )

            if not exists:
                raise ValueError(f"意圖 ID {intent_id} 不存在")

            # 構建更新語句
            updates = []
            params = []
            param_count = 0

            if name is not None:
                param_count += 1
                updates.append(f"name = ${param_count}")
                params.append(name)

            if type is not None:
                param_count += 1
                updates.append(f"type = ${param_count}")
                params.append(type)

            if description is not None:
                param_count += 1
                updates.append(f"description = ${param_count}")
                params.append(description)

            if keywords is not None:
                param_count += 1
                updates.append(f"keywords = ${param_count}")
                params.append(keywords)

            if confidence_threshold is not None:
                param_count += 1
                updates.append(f"confidence_threshold = ${param_count}")
                params.append(confidence_threshold)

            if priority is not None:
                param_count += 1
                updates.append(f"priority = ${param_count}")
                params.append(priority)

            if api_required is not None:
                param_count += 1
                updates.append(f"api_required = ${param_count}")
                params.append(api_required)

            if api_endpoint is not None:
                param_count += 1
                updates.append(f"api_endpoint = ${param_count}")
                params.append(api_endpoint)

            if api_action is not None:
                param_count += 1
                updates.append(f"api_action = ${param_count}")
                params.append(api_action)

            if not updates:
                return False  # 沒有要更新的欄位

            # 加入更新人員
            param_count += 1
            updates.append(f"updated_by = ${param_count}")
            params.append(updated_by)

            # 執行更新
            param_count += 1
            query = f"""
                UPDATE intents
                SET {', '.join(updates)}
                WHERE id = ${param_count}
            """
            params.append(intent_id)

            await conn.execute(query, *params)

            print(f"✅ 更新意圖 ID: {intent_id}")
            return True

        finally:
            await conn.close()

    async def delete_intent(self, intent_id: int) -> bool:
        """
        刪除意圖（軟刪除，設為 disabled）

        Returns:
            是否刪除成功
        """
        return await self.toggle_intent(intent_id, is_enabled=False)

    async def toggle_intent(self, intent_id: int, is_enabled: bool) -> bool:
        """
        啟用/停用意圖

        Returns:
            是否操作成功
        """
        conn = await self._get_connection()

        try:
            result = await conn.execute("""
                UPDATE intents
                SET is_enabled = $1
                WHERE id = $2
            """,
                is_enabled, intent_id
            )

            # 檢查是否有更新
            rows_affected = int(result.split()[-1])

            if rows_affected > 0:
                status = "啟用" if is_enabled else "停用"
                print(f"✅ {status}意圖 ID: {intent_id}")
                return True
            else:
                return False

        finally:
            await conn.close()

    # ========================================
    # 統計與分析
    # ========================================

    async def get_intent_stats(self) -> Dict[str, Any]:
        """
        取得意圖統計資訊

        Returns:
            {
                "total_intents": 10,
                "enabled_intents": 8,
                "by_type": {...},
                "knowledge_coverage": [...],
                "top_used": [...]
            }
        """
        conn = await self._get_connection()

        try:
            # 總體統計
            total = await conn.fetchval("SELECT COUNT(*) FROM intents")
            enabled = await conn.fetchval(
                "SELECT COUNT(*) FROM intents WHERE is_enabled = true"
            )

            # 按類型統計
            by_type = await conn.fetch("""
                SELECT
                    type,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) as enabled,
                    AVG(knowledge_count) as avg_knowledge
                FROM intents
                GROUP BY type
                ORDER BY type
            """)

            # 知識庫覆蓋率（前 10 個）
            coverage = await conn.fetch("""
                SELECT
                    id,
                    name,
                    type,
                    knowledge_count,
                    usage_count
                FROM intents
                WHERE is_enabled = true
                ORDER BY knowledge_count DESC, usage_count DESC
                LIMIT 10
            """)

            # 最常使用的意圖（前 10 個）
            top_used = await conn.fetch("""
                SELECT
                    id,
                    name,
                    type,
                    usage_count,
                    last_used_at
                FROM intents
                WHERE usage_count > 0
                ORDER BY usage_count DESC
                LIMIT 10
            """)

            return {
                "total_intents": total,
                "enabled_intents": enabled,
                "disabled_intents": total - enabled,
                "by_type": [dict(row) for row in by_type],
                "knowledge_coverage": [dict(row) for row in coverage],
                "top_used": [dict(row) for row in top_used]
            }

        finally:
            await conn.close()

    async def increment_usage_count(self, intent_name: str) -> None:
        """增加意圖使用次數"""
        conn = await self._get_connection()

        try:
            await conn.execute("""
                UPDATE intents
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE name = $1
            """, intent_name)

        finally:
            await conn.close()

    async def update_knowledge_count(self, intent_id: int) -> None:
        """更新意圖的知識庫數量"""
        conn = await self._get_connection()

        try:
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM knowledge_base
                WHERE intent_id = $1
            """, intent_id)

            await conn.execute("""
                UPDATE intents
                SET knowledge_count = $1
                WHERE id = $2
            """, count, intent_id)

        finally:
            await conn.close()

    # ========================================
    # 批次操作
    # ========================================

    async def batch_toggle(self, intent_ids: List[int], is_enabled: bool) -> int:
        """
        批次啟用/停用意圖

        Returns:
            成功更新的數量
        """
        conn = await self._get_connection()

        try:
            result = await conn.execute("""
                UPDATE intents
                SET is_enabled = $1
                WHERE id = ANY($2::int[])
            """,
                is_enabled, intent_ids
            )

            rows_affected = int(result.split()[-1])
            return rows_affected

        finally:
            await conn.close()


# 單例模式
_intent_manager_instance = None


def get_intent_manager() -> IntentManager:
    """取得 IntentManager 單例"""
    global _intent_manager_instance
    if _intent_manager_instance is None:
        _intent_manager_instance = IntentManager()
    return _intent_manager_instance
