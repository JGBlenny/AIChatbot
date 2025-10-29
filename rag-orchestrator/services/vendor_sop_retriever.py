"""
業者 SOP 檢索服務
根據業者的金流模式與業種類型，動態檢索並調整 SOP 內容
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Tuple
from .db_utils import get_db_config


class VendorSOPRetriever:
    """業者 SOP 檢索器"""

    def __init__(self):
        """初始化 SOP 檢索器"""
        self._cache: Dict[int, Dict] = {}  # vendor_id -> vendor_info

    def _get_db_connection(self):
        """建立資料庫連接"""
        return psycopg2.connect(**get_db_config())

    def get_vendor_info(self, vendor_id: int) -> Optional[Dict]:
        """
        獲取業者資訊（包含業種類型與金流模式）

        Returns:
            {
                'id': 1,
                'name': '愛租屋',
                'business_type': 'full_service',
                'cashflow_model': 'through_company'
            }
        """
        # 檢查快取
        if vendor_id in self._cache:
            return self._cache[vendor_id]

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    code,
                    name,
                    business_type,
                    cashflow_model,
                    is_active
                FROM vendors
                WHERE id = %s
            """, (vendor_id,))

            row = cursor.fetchone()
            cursor.close()

            if row:
                vendor_info = dict(row)
                self._cache[vendor_id] = vendor_info
                return vendor_info

            return None

        finally:
            conn.close()

    def retrieve_sop_by_intent(
        self,
        vendor_id: int,
        intent_id: int,
        top_k: int = 5
    ) -> List[Dict]:
        """
        根據意圖檢索 SOP 項目（支援 3 層結構）

        Args:
            vendor_id: 業者 ID
            intent_id: 意圖 ID
            top_k: 返回前 K 筆

        Returns:
            SOP 項目列表，包含分類、群組、項目資訊
        """
        # 1. 獲取業者資訊
        vendor_info = self.get_vendor_info(vendor_id)
        if not vendor_info:
            return []

        cashflow_model = vendor_info.get('cashflow_model', 'direct_to_landlord')
        business_type = vendor_info.get('business_type', 'property_management')

        # 2. 檢索 SOP 項目（支援 3 層結構）
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 使用新的多意圖關聯表查詢
            cursor.execute("""
                SELECT
                    si.id,
                    si.category_id,
                    sc.category_name,
                    si.group_id,
                    sg.group_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                INNER JOIN vendor_sop_item_intents vsii ON si.id = vsii.sop_item_id
                WHERE
                    si.vendor_id = %s
                    AND vsii.intent_id = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                ORDER BY si.priority DESC, si.item_number ASC
                LIMIT %s
            """, (vendor_id, intent_id, top_k))

            rows = cursor.fetchall()
            cursor.close()

            # DEBUG: 記錄實際檢索結果
            print(f"🔍 [VendorSOPRetriever] fetchall() 返回 {len(rows)} 行 (top_k={top_k})")
            if rows:
                print(f"   項目 IDs: {[row['id'] for row in rows]}")

            # 3. 處理結果（包含群組資訊）
            results = []
            for row in rows:
                item = dict(row)
                results.append({
                    'id': item['id'],
                    'category_id': item['category_id'],
                    'category_name': item['category_name'],
                    'group_id': item['group_id'],
                    'group_name': item['group_name'],
                    'item_number': item['item_number'],
                    'item_name': item['item_name'],
                    'content': item['content'],
                    'priority': item['priority']
                })

            return results

        finally:
            conn.close()

    async def retrieve_sop_hybrid(
        self,
        vendor_id: int,
        query: str,
        intent_ids: List[int] = None,
        primary_intent_id: int = None,
        top_k: int = 5,
        similarity_threshold: float = None
    ) -> List[Tuple[Dict, float]]:
        """
        混合模式檢索（優化版）：預存 Embedding + 意圖加成策略

        策略：
        1. 優先使用預存 primary_embedding (group_name + item_name) - 精準匹配
        2. 降級使用 fallback_embedding (content) - 細節查詢
        3. 意圖加成：匹配主要意圖 1.5x，次要意圖 1.2x（對齊 KB 設計）
        4. 最後降級為即時生成（< 5% 情況）

        Args:
            vendor_id: 業者 ID
            query: 使用者問題（用於計算相似度）
            intent_ids: 所有相關意圖 IDs（用於加成）
            primary_intent_id: 主要意圖 ID（用於 1.3x 加成）
            top_k: 返回前 K 筆
            similarity_threshold: 相似度閾值（低於此值的將被過濾）

        Returns:
            [(sop_item, similarity), ...] 列表，按加成後相似度降序排列
        """
        from .embedding_utils import get_embedding_client
        import numpy as np
        import os

        # 閾值配置
        if similarity_threshold is None:
            similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.60"))

        primary_threshold = 0.60  # Primary embedding 閾值（較高，確保精準）
        fallback_threshold = 0.50  # Fallback embedding 閾值（較低，確保召回）

        # 1. 生成 query 的 embedding
        embedding_client = get_embedding_client()
        query_embedding = await embedding_client.get_embedding(query)

        if not query_embedding:
            print(f"   ⚠️  [SOP Hybrid] Query embedding 生成失敗，降級為純意圖檢索")
            if intent_ids and len(intent_ids) > 0:
                candidate_sops = self.retrieve_sop_by_intent(vendor_id, intent_ids[0], top_k)
                return [(sop, 1.0) for sop in candidate_sops]
            else:
                return []

        # 轉換為 pgvector 格式
        query_vector_str = embedding_client.to_pgvector_format(query_embedding)

        # 2. 使用預存 embeddings 進行向量搜索（PostgreSQL vector search）
        conn = self._get_db_connection()
        results_with_similarity = []

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 查詢：使用預存 primary 和 fallback embeddings + 意圖加成策略
            # 準備 intent 參數
            intent_filter = intent_ids if intent_ids else []
            primary_intent = primary_intent_id if primary_intent_id else -1

            cursor.execute("""
                WITH sop_candidates AS (
                    SELECT DISTINCT ON (si.id)
                        si.*,
                        sg.group_name,
                        -- Primary embedding 相似度（1 - 餘弦距離）
                        CASE
                            WHEN si.primary_embedding IS NOT NULL
                            THEN 1 - (si.primary_embedding <=> %s::vector)
                            ELSE NULL
                        END as primary_similarity,
                        -- Fallback embedding 相似度
                        CASE
                            WHEN si.fallback_embedding IS NOT NULL
                            THEN 1 - (si.fallback_embedding <=> %s::vector)
                            ELSE NULL
                        END as fallback_similarity,
                        -- 意圖加成策略（調整為 1.3x 以平衡意圖與內容相似度）
                        CASE
                            WHEN sii.intent_id = %s THEN 1.3  -- 主要意圖 1.3x
                            WHEN sii.intent_id = ANY(%s::int[]) THEN 1.1  -- 次要意圖 1.1x
                            ELSE 1.0  -- 其他意圖 1.0x（軟過濾）
                        END as intent_boost,
                        sii.intent_id as matched_intent_id
                    FROM vendor_sop_items si
                    LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                    LEFT JOIN vendor_sop_item_intents sii ON si.id = sii.sop_item_id
                    WHERE
                        si.vendor_id = %s
                        AND si.is_active = TRUE
                        AND (
                            si.primary_embedding IS NOT NULL
                            OR si.fallback_embedding IS NOT NULL
                        )
                        -- 軟過濾：允許無意圖標籤或匹配任一相關意圖的 SOP
                        AND (
                            sii.intent_id IS NULL
                            OR sii.intent_id = ANY(%s::int[])
                            OR array_length(%s::int[], 1) IS NULL
                        )
                )
                SELECT *,
                    -- 計算加成後的最終相似度
                    GREATEST(
                        COALESCE(primary_similarity, 0),
                        COALESCE(fallback_similarity, 0)
                    ) * intent_boost as boosted_similarity
                FROM sop_candidates
                WHERE
                    (primary_similarity >= %s OR fallback_similarity >= %s)
                ORDER BY boosted_similarity DESC
                LIMIT %s
            """, (
                query_vector_str, query_vector_str,   # Query vector for both embeddings
                primary_intent,                        # Primary intent for 1.5x boost
                intent_filter,                         # Secondary intents for 1.2x boost
                vendor_id,                             # Vendor filter
                intent_filter,                         # Intent soft filter
                intent_filter,                         # Check if intent_filter is empty
                primary_threshold, fallback_threshold, # Thresholds
                top_k * 2                              # Fetch more for filtering
            ))

            sops_with_precomputed = cursor.fetchall()

            # 3. 處理有預存 embedding 的 SOP（已包含意圖加成）
            for sop in sops_with_precomputed:
                # SQL 已經計算好 boosted_similarity（包含意圖加成）
                boosted_sim = sop.get('boosted_similarity', 0)
                primary_sim = sop.get('primary_similarity')
                fallback_sim = sop.get('fallback_similarity')
                intent_boost = sop.get('intent_boost', 1.0)

                # 確定使用的策略和原始相似度
                strategy = 'primary' if (primary_sim and primary_sim >= (fallback_sim or 0)) else 'fallback'
                original_sim = primary_sim if strategy == 'primary' else fallback_sim

                # 使用加成後的相似度
                if boosted_sim >= similarity_threshold:
                    # 將原始相似度添加到 sop dict 中
                    sop_with_original = dict(sop)
                    sop_with_original['original_similarity'] = original_sim
                    results_with_similarity.append((sop_with_original, boosted_sim, strategy, intent_boost))

            # 4. 如果結果不足，降級為即時生成（極少發生）
            if len(results_with_similarity) < top_k:
                print(f"   ⚠️  [SOP Hybrid] 預存結果不足 ({len(results_with_similarity)}/{top_k})，嘗試即時生成補充")

                # 查詢沒有 embedding 的 SOP（使用軟過濾）
                cursor.execute("""
                    SELECT DISTINCT ON (si.id) si.*, sg.group_name
                    FROM vendor_sop_items si
                    LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                    LEFT JOIN vendor_sop_item_intents sii ON si.id = sii.sop_item_id
                    WHERE
                        si.vendor_id = %s
                        AND si.is_active = TRUE
                        AND si.primary_embedding IS NULL
                        AND si.fallback_embedding IS NULL
                        -- 軟過濾：允許無意圖或匹配相關意圖
                        AND (
                            sii.intent_id IS NULL
                            OR sii.intent_id = ANY(%s::int[])
                            OR array_length(%s::int[], 1) IS NULL
                        )
                    LIMIT %s
                """, (vendor_id, intent_filter, intent_filter, top_k * 2))

                sops_without_embedding = cursor.fetchall()

                # 即時生成 embedding 並計算相似度（預設無意圖加成）
                for sop in sops_without_embedding:
                    sop_text = sop['content']
                    sop_embedding = await embedding_client.get_embedding(sop_text)

                    if sop_embedding:
                        similarity = self._cosine_similarity(
                            np.array(query_embedding),
                            np.array(sop_embedding)
                        )

                        if similarity >= similarity_threshold:
                            # Realtime 生成的 SOP 無意圖加成（1.0x）
                            sop_with_original = dict(sop)
                            sop_with_original['original_similarity'] = similarity
                            results_with_similarity.append((sop_with_original, similarity, 'realtime', 1.0))

        finally:
            conn.close()

        # 5. 按相似度降序排序並限制數量
        results_with_similarity.sort(key=lambda x: x[1], reverse=True)
        results_with_similarity = results_with_similarity[:top_k]

        # 6. 日誌輸出
        print(f"\n🔍 [SOP Hybrid Retrieval - Intent Boosting]")
        print(f"   Query: {query}")
        print(f"   Intent IDs: {intent_ids}, Primary: {primary_intent_id}, Vendor ID: {vendor_id}")
        print(f"   結果數: {len(results_with_similarity)}")

        for idx, (sop, sim, strategy, boost) in enumerate(results_with_similarity, 1):
            strategy_emoji = {'primary': '🎯', 'fallback': '🔄', 'realtime': '⚡'}
            boost_indicator = f"×{boost:.1f}" if boost > 1.0 else ""
            print(f"   {idx}. {strategy_emoji.get(strategy, '')} [ID {sop['id']}] {sop['item_name'][:40]} (相似度: {sim:.3f}{boost_indicator}, {strategy})")

        # 返回格式轉換（移除 strategy 和 boost）
        return [(sop, sim) for sop, sim, _, _ in results_with_similarity]

    def _cosine_similarity(self, vec1, vec2):
        """計算余弦相似度"""
        dot_product = float(vec1.dot(vec2))
        norm1 = float((vec1 ** 2).sum() ** 0.5)
        norm2 = float((vec2 ** 2).sum() ** 0.5)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def retrieve_sop_by_category(
        self,
        vendor_id: int,
        category_name: str
    ) -> List[Dict]:
        """
        根據分類檢索 SOP 項目（支援 3 層結構）

        Args:
            vendor_id: 業者 ID
            category_name: 分類名稱（如：「租賃流程相關資訊」）

        Returns:
            SOP 項目列表（包含群組資訊）
        """
        vendor_info = self.get_vendor_info(vendor_id)
        if not vendor_info:
            return []

        cashflow_model = vendor_info.get('cashflow_model', 'direct_to_landlord')
        business_type = vendor_info.get('business_type', 'property_management')

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    si.id,
                    si.category_id,
                    sc.category_name,
                    si.group_id,
                    sg.group_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                WHERE
                    si.vendor_id = %s
                    AND sc.category_name = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                ORDER BY sg.display_order, si.item_number ASC
            """, (vendor_id, category_name))

            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                item = dict(row)
                results.append({
                    'id': item['id'],
                    'category_id': item['category_id'],
                    'category_name': item['category_name'],
                    'group_id': item['group_id'],
                    'group_name': item['group_name'],
                    'item_number': item['item_number'],
                    'item_name': item['item_name'],
                    'content': item['content'],
                    'priority': item['priority']
                })

            return results

        finally:
            conn.close()

    def get_all_categories(self, vendor_id: int) -> List[Dict]:
        """
        獲取業者的所有 SOP 分類（包含群組數）

        Returns:
            [
                {'id': 1, 'category_name': '租賃流程相關資訊', 'description': '...',
                 'group_count': 4, 'item_count': 15},
                ...
            ]
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    sc.id,
                    sc.category_name,
                    sc.description,
                    sc.display_order,
                    COUNT(DISTINCT sg.id) AS group_count,
                    COUNT(si.id) AS item_count
                FROM vendor_sop_categories sc
                LEFT JOIN vendor_sop_groups sg ON sc.id = sg.category_id AND sg.is_active = TRUE
                LEFT JOIN vendor_sop_items si ON sc.id = si.category_id AND si.is_active = TRUE
                WHERE
                    sc.vendor_id = %s
                    AND sc.is_active = TRUE
                GROUP BY sc.id, sc.category_name, sc.description, sc.display_order
                ORDER BY sc.display_order, sc.id
            """, (vendor_id,))

            rows = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_all_groups(self, vendor_id: int, category_id: Optional[int] = None) -> List[Dict]:
        """
        獲取業者的所有 SOP 群組

        Args:
            vendor_id: 業者 ID
            category_id: 可選，限定分類

        Returns:
            [
                {'id': 1, 'category_id': 1, 'category_name': '租賃流程相關資訊',
                 'group_name': '租賃申請流程...', 'item_count': 4},
                ...
            ]
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if category_id:
                cursor.execute("""
                    SELECT
                        sg.id,
                        sg.category_id,
                        sc.category_name,
                        sg.group_name,
                        sg.description,
                        sg.display_order,
                        COUNT(si.id) AS item_count
                    FROM vendor_sop_groups sg
                    INNER JOIN vendor_sop_categories sc ON sg.category_id = sc.id
                    LEFT JOIN vendor_sop_items si ON sg.id = si.group_id AND si.is_active = TRUE
                    WHERE
                        sg.vendor_id = %s
                        AND sg.category_id = %s
                        AND sg.is_active = TRUE
                        AND sc.is_active = TRUE
                    GROUP BY sg.id, sg.category_id, sc.category_name, sg.group_name,
                             sg.description, sg.display_order
                    ORDER BY sg.display_order, sg.id
                """, (vendor_id, category_id))
            else:
                cursor.execute("""
                    SELECT
                        sg.id,
                        sg.category_id,
                        sc.category_name,
                        sg.group_name,
                        sg.description,
                        sg.display_order,
                        COUNT(si.id) AS item_count
                    FROM vendor_sop_groups sg
                    INNER JOIN vendor_sop_categories sc ON sg.category_id = sc.id
                    LEFT JOIN vendor_sop_items si ON sg.id = si.group_id AND si.is_active = TRUE
                    WHERE
                        sg.vendor_id = %s
                        AND sg.is_active = TRUE
                        AND sc.is_active = TRUE
                    GROUP BY sg.id, sg.category_id, sc.category_name, sg.group_name,
                             sg.description, sg.display_order
                    ORDER BY sc.display_order, sg.display_order, sg.id
                """, (vendor_id,))

            rows = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def retrieve_sop_by_group(self, vendor_id: int, group_id: int) -> List[Dict]:
        """
        根據群組檢索 SOP 項目

        Args:
            vendor_id: 業者 ID
            group_id: 群組 ID

        Returns:
            SOP 項目列表
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    si.id,
                    si.category_id,
                    sc.category_name,
                    si.group_id,
                    sg.group_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                INNER JOIN vendor_sop_groups sg ON si.group_id = sg.id
                WHERE
                    si.vendor_id = %s
                    AND si.group_id = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                    AND sg.is_active = TRUE
                ORDER BY si.item_number ASC
            """, (vendor_id, group_id))

            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                item = dict(row)
                results.append({
                    'id': item['id'],
                    'category_id': item['category_id'],
                    'category_name': item['category_name'],
                    'group_id': item['group_id'],
                    'group_name': item['group_name'],
                    'item_number': item['item_number'],
                    'item_name': item['item_name'],
                    'content': item['content'],
                    'priority': item['priority']
                })

            return results

        finally:
            conn.close()

    def clear_cache(self):
        """清除快取"""
        self._cache.clear()


# 使用範例
if __name__ == "__main__":
    retriever = VendorSOPRetriever()

    # 測試：獲取業者資訊
    print("=" * 80)
    print("測試：獲取業者資訊")
    print("=" * 80)

    vendor_info = retriever.get_vendor_info(vendor_id=1)
    print(f"\n業者資訊：")
    print(f"  名稱：{vendor_info['name']}")
    print(f"  業種類型：{vendor_info['business_type']}")
    print(f"  金流模式：{vendor_info['cashflow_model']}")

    # 測試：獲取所有分類
    print("\n" + "=" * 80)
    print("測試：獲取所有 SOP 分類")
    print("=" * 80)

    categories = retriever.get_all_categories(vendor_id=1)
    for cat in categories:
        print(f"\n{cat['category_name']} ({cat['item_count']} 項)")
        if cat['description']:
            print(f"  描述：{cat['description']}")

    # 測試：根據分類檢索
    if categories:
        print("\n" + "=" * 80)
        print(f"測試：檢索分類「{categories[0]['category_name']}」")
        print("=" * 80)

        items = retriever.retrieve_sop_by_category(
            vendor_id=1,
            category_name=categories[0]['category_name']
        )

        for item in items[:5]:  # 只顯示前5項
            print(f"\n{item['item_number']}. {item['item_name']}")
            print(f"   {item['content'][:100]}...")
