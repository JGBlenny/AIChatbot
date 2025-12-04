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
                    business_types[1] as business_type,
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
        混合模式檢索（Group隔離版）：預存 Embedding + 意圖加成 + Group隔離

        三階段策略：
        1. 階段1: Group識別 - 找到最相關的Group
        2. 階段2: Group內檢索 - 在該Group內檢索所有項目
        3. 階段3: 偏向判斷 - 根據相似度判斷是否有偏向

        **Group隔離規則：**
        - Group A 底下有 4條知識，不會混到 Group B
        - 如果問題偏向 Group A 中的 2條知識，返回這 2條
        - 如果問題符合 Group A 但沒有偏向，返回 Group A 所有 4條

        Args:
            vendor_id: 業者 ID
            query: 使用者問題（用於計算相似度）
            intent_ids: 所有相關意圖 IDs（用於加成）
            primary_intent_id: 主要意圖 ID（用於 1.3x 加成）
            top_k: 返回前 K 筆（用於限制偏向項目數量）
            similarity_threshold: 相似度閾值（低於此值的將被過濾）

        Returns:
            [(sop_item, similarity), ...] 列表，來自單一Group
        """
        from .embedding_utils import get_embedding_client
        import numpy as np
        import os

        # 閾值配置
        if similarity_threshold is None:
            similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.60"))

        primary_threshold = 0.60  # Primary embedding 閾值
        fallback_threshold = 0.50  # Fallback embedding 閾值
        bias_threshold = 0.80  # 偏向判斷閾值（高於此值視為有偏向）
        bias_min_count = 3  # 最少需要幾條高相似度項目才算偏向

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

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 準備 intent 參數
            intent_filter = intent_ids if intent_ids else []
            primary_intent = primary_intent_id if primary_intent_id else -1

            # ==================== 階段1: Group識別 ====================
            print(f"\n🔍 [SOP Group Isolation] 階段1: 識別最相關的Group（使用Group Embedding）")
            print(f"   Query: {query[:50]}...")
            print(f"   Intent IDs: {intent_ids}, Primary: {primary_intent_id}")

            # 優先使用Group embedding進行識別（更準確更快）
            cursor.execute("""
                SELECT
                    vsg.id as group_id,
                    vsg.group_name,
                    1 - (vsg.group_embedding <=> %s::vector) as group_similarity,
                    (
                        SELECT COUNT(*)
                        FROM vendor_sop_items vsi
                        WHERE vsi.group_id = vsg.id
                          AND vsi.is_active = TRUE
                    ) as item_count
                FROM vendor_sop_groups vsg
                WHERE
                    vsg.vendor_id = %s
                    AND vsg.is_active = TRUE
                    AND vsg.group_embedding IS NOT NULL
                ORDER BY group_similarity DESC
                LIMIT 1
            """, (
                query_vector_str,
                vendor_id
            ))

            best_group = cursor.fetchone()

            if not best_group:
                print(f"   ❌ 沒有找到符合條件的Group")
                return []

            best_group_id = best_group['group_id']
            best_group_name = best_group['group_name']
            group_item_count = best_group['item_count']
            group_similarity = best_group['group_similarity']

            print(f"   ✅ 最相關Group: [{best_group_id}] {best_group_name[:60]}")
            print(f"      - 該Group共 {group_item_count} 條知識")
            print(f"      - Group相似度: {group_similarity:.3f}")

            # 分層決策判斷是否進入該Group
            can_enter_group = False
            decision_path = ""

            # 步驟1: 高置信度 - Group > 0.75 直接進入
            if group_similarity > 0.75:
                can_enter_group = True
                decision_path = "步驟1: Group相似度 > 0.75，直接進入"
                print(f"   ✅ {decision_path}")

            # 步驟2: 中等置信度 - 0.65 < Group ≤ 0.75，計算混合分數
            elif group_similarity > 0.65:
                print(f"   🔍 步驟2: 0.65 < Group相似度 ≤ 0.75，計算混合分數...")

                # 獲取該Group內最高的Item相似度
                cursor.execute("""
                    SELECT MAX(
                        GREATEST(
                            COALESCE(1 - (primary_embedding <=> %s::vector), 0),
                            COALESCE(1 - (fallback_embedding <=> %s::vector), 0)
                        )
                    ) as max_item_similarity
                    FROM vendor_sop_items
                    WHERE
                        vendor_id = %s
                        AND group_id = %s
                        AND is_active = TRUE
                        AND (primary_embedding IS NOT NULL OR fallback_embedding IS NOT NULL)
                """, (query_vector_str, query_vector_str, vendor_id, best_group_id))

                max_item_result = cursor.fetchone()
                max_item_similarity = max_item_result['max_item_similarity'] if max_item_result else 0

                # 計算混合分數：30% Group + 70% Item
                hybrid_score = 0.3 * group_similarity + 0.7 * max_item_similarity

                print(f"      - Item最高相似度: {max_item_similarity:.3f}")
                print(f"      - 混合分數: 0.3×{group_similarity:.3f} + 0.7×{max_item_similarity:.3f} = {hybrid_score:.3f}")

                if hybrid_score > 0.75:
                    can_enter_group = True
                    decision_path = f"步驟2: 混合分數 {hybrid_score:.3f} > 0.75，通過驗證"
                    print(f"   ✅ {decision_path}")
                else:
                    decision_path = f"步驟2: 混合分數 {hybrid_score:.3f} ≤ 0.75，拒絕進入"
                    print(f"   ❌ {decision_path}")

            # 步驟3: 低置信度 - Group ≤ 0.65 直接拒絕
            else:
                decision_path = "步驟3: Group相似度 ≤ 0.65，直接拒絕"
                print(f"   ❌ {decision_path}")

            # 如果無法進入Group，返回空結果
            if not can_enter_group:
                return []

            # ==================== 階段2: Group內檢索 ====================
            print(f"\n🔍 [SOP Group Isolation] 階段2: 獲取Group內所有項目")

            cursor.execute("""
                WITH group_items AS (
                    SELECT DISTINCT ON (si.id)
                        si.*,
                        sg.group_name,
                        -- Primary embedding 相似度
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
                        -- 意圖加成
                        CASE
                            WHEN sii.intent_id = %s THEN 1.3
                            WHEN sii.intent_id = ANY(%s::int[]) THEN 1.1
                            ELSE 1.0
                        END as intent_boost,
                        sii.intent_id as matched_intent_id
                    FROM vendor_sop_items si
                    LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                    LEFT JOIN vendor_sop_item_intents sii ON si.id = sii.sop_item_id
                    WHERE
                        si.vendor_id = %s
                        AND si.group_id = %s
                        AND si.is_active = TRUE
                        AND (
                            si.primary_embedding IS NOT NULL
                            OR si.fallback_embedding IS NOT NULL
                        )
                )
                SELECT *,
                    GREATEST(
                        COALESCE(primary_similarity, 0),
                        COALESCE(fallback_similarity, 0)
                    ) * intent_boost as boosted_similarity
                FROM group_items
                ORDER BY boosted_similarity DESC
            """, (
                query_vector_str, query_vector_str,
                primary_intent,
                intent_filter,
                vendor_id,
                best_group_id
            ))

            items_in_group = cursor.fetchall()

            print(f"   ✅ Group內共獲取 {len(items_in_group)} 條項目（該Group全部項目）")

            # ==================== 階段3: 偏向判斷 ====================
            print(f"\n🔍 [SOP Group Isolation] 階段3: 偏向判斷（閾值: {bias_threshold}）")

            results_with_similarity = []
            high_similarity_items = []

            for item in items_in_group:
                boosted_sim = item.get('boosted_similarity', 0)
                primary_sim = item.get('primary_similarity')
                fallback_sim = item.get('fallback_similarity')
                intent_boost = item.get('intent_boost', 1.0)

                # 確定策略和原始相似度
                strategy = 'primary' if (primary_sim and primary_sim >= (fallback_sim or 0)) else 'fallback'
                original_sim = primary_sim if strategy == 'primary' else fallback_sim

                item_dict = dict(item)
                item_dict['original_similarity'] = original_sim

                results_with_similarity.append((item_dict, boosted_sim, strategy, intent_boost))

                # 收集高相似度項目
                if boosted_sim >= bias_threshold:
                    high_similarity_items.append((item_dict, boosted_sim, strategy, intent_boost))

            # 判斷是否有偏向（多種判斷策略）
            has_bias = False
            bias_reason = ""

            if high_similarity_items:
                total_items = len(results_with_similarity)
                high_sim_ratio = len(high_similarity_items) / total_items if total_items > 0 else 0

                # 策略0：如果高相似度項占比過高（> 70%），說明是泛化查詢，返回全部
                if high_sim_ratio > 0.7 and total_items >= 3:
                    has_bias = False
                    bias_reason = f"高相似度項占比過高 ({len(high_similarity_items)}/{total_items} = {high_sim_ratio*100:.1f}%)，判定為泛化查詢"
                    print(f"   🔍 策略0檢查: {bias_reason}")

                # 策略1：有足夠多的高相似度項目，但占比不高（原邏輯）
                elif len(high_similarity_items) >= bias_min_count:
                    has_bias = True
                    bias_reason = f"有 {len(high_similarity_items)} 條高相似度項 >= {bias_threshold}（占比 {high_sim_ratio*100:.1f}%）"

                # 策略2：只有1-2條高相似度項，但第1名顯著突出
                elif len(high_similarity_items) >= 1:
                    # 獲取所有items按相似度排序
                    all_items_sorted = sorted(results_with_similarity, key=lambda x: x[1], reverse=True)
                    top1_sim = all_items_sorted[0][1]

                    # 如果第1名 >= bias_threshold
                    if top1_sim >= bias_threshold:
                        if len(all_items_sorted) >= 2:
                            top2_sim = all_items_sorted[1][1]
                            gap = top1_sim - top2_sim

                            # 策略2a：第1名和第2名差距顯著（> 0.10）
                            if gap > 0.10:
                                has_bias = True
                                bias_reason = f"最高相似度 {top1_sim:.3f} 顯著高於第2名 {top2_sim:.3f}（差距 {gap:.3f}）"

                            # 策略2b：第2名 < 0.75
                            elif top2_sim < 0.75:
                                has_bias = True
                                bias_reason = f"最高相似度 {top1_sim:.3f} >= {bias_threshold}，第2名 {top2_sim:.3f} < 0.75"
                        else:
                            # 只有1個item
                            has_bias = True
                            bias_reason = f"唯一項目，相似度 {top1_sim:.3f} >= {bias_threshold}"

            if has_bias:
                # 有偏向：返回高相似度項目
                results_with_similarity = high_similarity_items[:top_k]
                print(f"   ✅ 檢測到偏向：{bias_reason}，返回 {len(results_with_similarity)} 條項目")
            else:
                # 無偏向：返回該Group所有項目
                if high_similarity_items:
                    print(f"   ✅ 無明顯偏向：高相似度項目不足且不突出，返回該Group所有 {len(results_with_similarity)} 條項目")
                else:
                    print(f"   ✅ 無明顯偏向：無高相似度項目（>= {bias_threshold}），返回該Group所有 {len(results_with_similarity)} 條項目")

            # 按相似度排序
            results_with_similarity.sort(key=lambda x: x[1], reverse=True)

            # 日誌輸出
            print(f"\n📋 [最終結果] Group [{best_group_id}] {best_group_name[:50]}")
            for idx, (sop, sim, strategy, boost) in enumerate(results_with_similarity, 1):
                strategy_emoji = {'primary': '🎯', 'fallback': '🔄', 'realtime': '⚡'}
                boost_indicator = f"×{boost:.1f}" if boost > 1.0 else ""
                print(f"   {idx}. {strategy_emoji.get(strategy, '')} [ID {sop['id']}] {sop['item_name'][:40]} (相似度: {sim:.3f}{boost_indicator})")

        finally:
            conn.close()

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
