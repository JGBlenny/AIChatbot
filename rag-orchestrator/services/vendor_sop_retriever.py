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
        intent_id: int,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[Tuple[Dict, float]]:
        """
        混合模式檢索：Intent 過濾 + 向量相似度排序

        類似 knowledge_base 的 hybrid 檢索，解決純意圖檢索可能的誤匹配問題

        Args:
            vendor_id: 業者 ID
            intent_id: 意圖 ID
            query: 使用者問題（用於計算相似度）
            top_k: 返回前 K 筆
            similarity_threshold: 相似度閾值（低於此值的將被過濾）

        Returns:
            [(sop_item, similarity), ...] 列表，按相似度降序排列
        """
        from .embedding_utils import get_embedding_client
        import numpy as np

        # 1. 使用意圖檢索獲取候選 SOP（檢索更多候選，稍後用相似度過濾）
        candidate_sops = self.retrieve_sop_by_intent(
            vendor_id=vendor_id,
            intent_id=intent_id,
            top_k=top_k * 2  # 檢索更多候選以便過濾
        )

        if not candidate_sops:
            print(f"   ⚠️  [SOP Hybrid] 意圖 {intent_id} 沒有找到任何 SOP")
            return []

        # 2. 生成 query 的 embedding
        embedding_client = get_embedding_client()
        query_embedding = await embedding_client.get_embedding(query)

        if not query_embedding:
            print(f"   ⚠️  [SOP Hybrid] Query embedding 生成失敗，降級為純意圖檢索")
            # 降級：返回原始結果但相似度設為 1.0
            return [(sop, 1.0) for sop in candidate_sops[:top_k]]

        # 3. 為每個 SOP 生成 embedding 並計算相似度
        results_with_similarity = []

        for sop in candidate_sops:
            # 使用 content 作為語義匹配的來源
            sop_text = sop['content']
            sop_embedding = await embedding_client.get_embedding(sop_text)

            if not sop_embedding:
                print(f"   ⚠️  [SOP Hybrid] SOP ID {sop['id']} embedding 生成失敗，跳過")
                continue

            # 計算余弦相似度
            similarity = self._cosine_similarity(
                np.array(query_embedding),
                np.array(sop_embedding)
            )

            # 過濾低相似度
            if similarity >= similarity_threshold:
                results_with_similarity.append((sop, similarity))

        # 4. 按相似度降序排序
        results_with_similarity.sort(key=lambda x: x[1], reverse=True)

        # 5. 限制返回數量
        results_with_similarity = results_with_similarity[:top_k]

        # 6. 日誌輸出
        print(f"\n🔍 [SOP Hybrid Retrieval]")
        print(f"   Query: {query}")
        print(f"   Intent ID: {intent_id}, Vendor ID: {vendor_id}")
        print(f"   候選數: {len(candidate_sops)} → 過濾後: {len(results_with_similarity)}")

        for idx, (sop, sim) in enumerate(results_with_similarity, 1):
            print(f"   {idx}. [ID {sop['id']}] {sop['item_name'][:40]} (相似度: {sim:.3f})")

        return results_with_similarity

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
