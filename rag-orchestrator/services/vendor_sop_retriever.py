"""
業者 SOP 檢索服務
根據業者的金流模式與業種類型，動態檢索並調整 SOP 內容
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
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
        根據意圖檢索 SOP 項目

        Args:
            vendor_id: 業者 ID
            intent_id: 意圖 ID
            top_k: 返回前 K 筆

        Returns:
            SOP 項目列表（已根據金流模式與業種類型調整）
        """
        # 1. 獲取業者資訊
        vendor_info = self.get_vendor_info(vendor_id)
        if not vendor_info:
            return []

        cashflow_model = vendor_info.get('cashflow_model', 'direct_to_landlord')
        business_type = vendor_info.get('business_type', 'property_management')

        # 2. 檢索 SOP 項目
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    si.id,
                    si.category_id,
                    sc.category_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                WHERE
                    si.vendor_id = %s
                    AND si.related_intent_id = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                ORDER BY si.priority DESC, si.item_number ASC
                LIMIT %s
            """, (vendor_id, intent_id, top_k))

            rows = cursor.fetchall()
            cursor.close()

            # 3. 處理結果（簡化版：直接返回內容，不做動態調整）
            results = []
            for row in rows:
                item = dict(row)
                results.append({
                    'id': item['id'],
                    'category_name': item['category_name'],
                    'item_number': item['item_number'],
                    'item_name': item['item_name'],
                    'content': item['content'],
                    'priority': item['priority']
                })

            return results

        finally:
            conn.close()

    def retrieve_sop_by_category(
        self,
        vendor_id: int,
        category_name: str
    ) -> List[Dict]:
        """
        根據分類檢索 SOP 項目

        Args:
            vendor_id: 業者 ID
            category_name: 分類名稱（如：「租賃流程相關資訊」）

        Returns:
            SOP 項目列表
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
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                WHERE
                    si.vendor_id = %s
                    AND sc.category_name = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                ORDER BY si.item_number ASC
            """, (vendor_id, category_name))

            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                item = dict(row)
                results.append({
                    'id': item['id'],
                    'category_name': item['category_name'],
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
        獲取業者的所有 SOP 分類

        Returns:
            [
                {'id': 1, 'category_name': '租賃流程相關資訊', 'description': '...', 'item_count': 15},
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
                    COUNT(si.id) AS item_count
                FROM vendor_sop_categories sc
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
