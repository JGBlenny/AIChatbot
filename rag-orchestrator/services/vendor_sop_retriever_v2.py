"""
業者 SOP 檢索服務 V2 - 統一架構版本
繼承 BaseRetriever，使用統一的檢索策略
Date: 2026-02-11
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from .base_retriever import BaseRetriever
from .db_utils import get_db_config


class VendorSOPRetrieverV2(BaseRetriever):
    """業者 SOP 檢索器 - 統一架構版本"""

    def __init__(self):
        """初始化 SOP 檢索器"""
        super().__init__()  # 調用基類初始化

        self._cache: Dict[int, Dict] = {}  # vendor_id -> vendor_info

        # SOP 特定配置
        import os
        self.sop_similarity_threshold = float(os.getenv("SOP_SIMILARITY_THRESHOLD", "0.75"))
        print(f"ℹ️  SOP 檢索器 V2 已初始化（相似度閾值: {self.sop_similarity_threshold}）")

    def get_vendor_info(self, vendor_id: int) -> Optional[Dict]:
        """獲取業者資訊"""
        if vendor_id in self._cache:
            return self._cache[vendor_id]

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, code, name,
                       business_types[1] as business_type,
                       cashflow_model, is_active
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

    async def _vector_search(
        self,
        query_embedding: List[float],
        vendor_id: int,
        top_k: int,
        similarity_threshold: float,
        **kwargs
    ) -> List[Dict]:
        """
        SOP 向量檢索實作
        """
        # 獲取額外參數
        intent_id = kwargs.get('intent_id')

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            vector_str = str(query_embedding)

            # SQL 查詢：向量相似度檢索
            cursor.execute("""
                SELECT
                    si.id,
                    si.vendor_id,
                    si.category_id,
                    sc.category_name,
                    si.group_id,
                    sg.group_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority,
                    si.keywords,
                    si.trigger_mode,
                    si.next_action,
                    si.next_form_id,
                    si.next_api_config,
                    si.trigger_keywords,
                    si.immediate_prompt,
                    si.followup_prompt,
                    vsii.intent_id,
                    -- 計算向量相似度
                    GREATEST(
                        COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
                        COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
                    ) as similarity,
                    -- Intent 加成
                    CASE
                        WHEN vsii.intent_id = %s THEN 1.3
                        ELSE 1.0
                    END as intent_boost
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                LEFT JOIN vendor_sop_item_intents vsii ON si.id = vsii.sop_item_id
                WHERE
                    si.vendor_id = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                    AND (si.primary_embedding IS NOT NULL OR si.fallback_embedding IS NOT NULL)
                    AND GREATEST(
                        COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
                        COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
                    ) >= %s
                ORDER BY
                    GREATEST(
                        COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
                        COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
                    ) * CASE WHEN vsii.intent_id = %s THEN 1.3 ELSE 1.0 END DESC,
                    si.priority DESC
                LIMIT %s
            """, (
                vector_str, vector_str,
                intent_id if intent_id else -1,
                vendor_id,
                vector_str, vector_str,
                similarity_threshold,
                vector_str, vector_str,
                intent_id if intent_id else -1,
                top_k
            ))

            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append(self._format_result(dict(row)))

            return results

        finally:
            conn.close()

    async def _keyword_search(
        self,
        query: str,
        vendor_id: int,
        limit: int,
        **kwargs
    ) -> List[Dict]:
        """
        SOP 關鍵字檢索實作
        """
        import jieba

        # 分詞處理查詢
        query_tokens = set(jieba.cut(query.lower()))

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 查詢有關鍵字的 SOP
            cursor.execute("""
                SELECT
                    si.id,
                    si.vendor_id,
                    si.category_id,
                    sc.category_name,
                    si.group_id,
                    sg.group_name,
                    si.item_number,
                    si.item_name,
                    si.content,
                    si.priority,
                    si.keywords,
                    si.trigger_mode,
                    si.next_action,
                    si.next_form_id,
                    si.next_api_config,
                    si.trigger_keywords,
                    si.immediate_prompt,
                    si.followup_prompt,
                    vsii.intent_id
                FROM vendor_sop_items si
                INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
                LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
                LEFT JOIN vendor_sop_item_intents vsii ON si.id = vsii.sop_item_id
                WHERE
                    si.vendor_id = %s
                    AND si.is_active = TRUE
                    AND sc.is_active = TRUE
                    AND si.keywords IS NOT NULL
                    AND array_length(si.keywords, 1) > 0
                ORDER BY
                    si.priority DESC,
                    si.item_number ASC
                LIMIT %s
            """, (vendor_id, limit * 3))

            all_rows = cursor.fetchall()
            cursor.close()

            # 篩選包含匹配關鍵字的 SOP
            keyword_matched_sops = []

            for row in all_rows:
                keywords = row.get('keywords', [])
                if not keywords:
                    continue

                # 計算關鍵字匹配
                matched_keywords = []
                match_score = 0.0

                for keyword in keywords:
                    keyword_tokens = set(jieba.cut(keyword.lower()))
                    intersection = query_tokens & keyword_tokens

                    if intersection:
                        matched_keywords.append(keyword)
                        match_score += len(intersection) / len(keyword_tokens)

                # 如果有匹配，加入結果
                if matched_keywords:
                    item = dict(row)
                    normalized_score = min(1.0, match_score / max(1, len(matched_keywords)))

                    result = self._format_result(item)
                    result['similarity'] = normalized_score
                    result['keyword_matches'] = matched_keywords
                    result['search_method'] = 'keyword'

                    keyword_matched_sops.append(result)

            # 按匹配度排序，取前 limit 個
            keyword_matched_sops.sort(key=lambda x: x['similarity'], reverse=True)
            return keyword_matched_sops[:limit]

        finally:
            conn.close()

    def _format_result(self, row: Dict) -> Dict:
        """
        格式化 SOP 檢索結果
        """
        return {
            'id': row['id'],
            'category_id': row.get('category_id'),
            'category_name': row.get('category_name'),
            'group_id': row.get('group_id'),
            'group_name': row.get('group_name'),
            'item_number': row.get('item_number'),
            'item_name': row.get('item_name'),
            'content': row.get('content'),
            'priority': row.get('priority'),
            'keywords': row.get('keywords', []),
            'trigger_mode': row.get('trigger_mode'),
            'next_action': row.get('next_action'),
            'next_form_id': row.get('next_form_id'),
            'next_api_config': row.get('next_api_config'),
            'trigger_keywords': row.get('trigger_keywords'),
            'immediate_prompt': row.get('immediate_prompt'),
            'followup_prompt': row.get('followup_prompt'),
            'similarity': row.get('similarity', 0),
            'search_method': row.get('search_method', 'vector')
        }

    # 便利方法：保持向後相容
    async def retrieve_sop_by_query(
        self,
        vendor_id: int,
        query: str,
        intent_id: Optional[int] = None,
        top_k: int = 5,
        similarity_threshold: float = None,
        include_keywords_boost: bool = True
    ) -> List[Dict]:
        """
        向後相容的介面
        調用統一的 retrieve 方法
        """
        return await self.retrieve(
            query=query,
            vendor_id=vendor_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold or self.sop_similarity_threshold,
            enable_keyword_fallback=True,
            enable_keyword_boost=include_keywords_boost,
            intent_id=intent_id
        )