"""
業者知識庫檢索服務 V2 - 統一架構版本
繼承 BaseRetriever，使用統一的檢索策略
Date: 2026-02-11
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from .base_retriever import BaseRetriever
from .vendor_parameter_resolver import VendorParameterResolver as VendorParamResolver
from .retrieval_types import make_default_result


class VendorKnowledgeRetrieverV2(BaseRetriever):
    """業者知識庫檢索器 - 統一架構版本"""

    def __init__(self):
        """初始化知識庫檢索器"""
        super().__init__()  # 調用基類初始化

        # 參數解析器
        self.param_resolver = VendorParamResolver()

        print("ℹ️  知識庫檢索器 V2 已初始化（支援關鍵字備選）")

    async def _vector_search(
        self,
        query_embedding: List[float],
        vendor_id: int,
        top_k: int,
        similarity_threshold: float,
        **kwargs
    ) -> List[Dict]:
        """
        知識庫向量檢索（task 3.1）

        變更（與 SOP retriever 對稱）：
        - SQL 不在 WHERE 端用 `>= threshold` 過濾（保留低分候選供 debug 顯示）
          → similarity_threshold 參數保留簽章但不在 SQL 端使用
        - SELECT alias 改為 `as vector_similarity`（純向量分數，不含 intent_boost）
        - LIMIT 預設 100（KB 資料量大於 SOP，可由 kwargs['vector_limit'] 覆寫）
        - intent_boost 仍用於 ORDER BY 排序，但不寫入 vector_similarity
        """
        # 獲取額外參數
        intent_id = kwargs.get('intent_id')
        all_intent_ids = kwargs.get('all_intent_ids', [])
        target_user = kwargs.get('target_user', 'tenant')
        mode = kwargs.get('mode', 'b2c')
        vector_limit = kwargs.get('vector_limit', 20)

        # 根據用戶角色或模式決定業態類型
        is_b2b_mode = (target_user in ['property_manager', 'system_admin']) or (mode == 'b2b')

        if is_b2b_mode:
            vendor_business_types = ['system_provider']
            business_type_filter_sql = "kb.business_types && %s::text[]"
        else:
            vendor_info = self.param_resolver.get_vendor_info(vendor_id)
            vendor_business_types = vendor_info.get('business_types', [])
            business_type_filter_sql = "(kb.business_types IS NULL OR kb.business_types && %s::text[])"

        # 目標用戶過濾 - target_user 是陣列欄位，使用 && 運算子檢查重疊
        target_user_roles = None
        if target_user in ['tenant', 'landlord', 'property_manager', 'system_admin']:
            target_user_roles = ['all_users', target_user]
            target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"
        else:
            target_user_filter_sql = "(kb.target_user IS NULL OR 'all_users' = ANY(kb.target_user))"

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            vector_str = str(query_embedding)

            # 建構 SQL 查詢（不在 SQL 端 threshold 過濾）
            sql_query = f"""
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.vendor_ids,
                    kb.business_types,
                    kb.target_user,
                    kb.keywords,
                    kb.video_url,
                    kb.form_id,
                    kb.action_type,
                    kb.api_config,
                    kim.intent_id,
                    -- 計算純向量相似度（不含 intent_boost）
                    1 - (kb.embedding <=> %s::vector) as vector_similarity,
                    -- Intent 加成（僅供 ORDER BY 排序使用）
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1
                        ELSE 1.0
                    END as intent_boost
                FROM knowledge_base kb
                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                WHERE
                    (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])
                    AND kb.embedding IS NOT NULL
                    AND kb.is_active = TRUE
                    AND {business_type_filter_sql}
                    AND {target_user_filter_sql}
                ORDER BY
                    (1 - (kb.embedding <=> %s::vector)) *
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1
                        ELSE 1.0
                    END DESC,
                    kb.priority DESC
                LIMIT %s
            """

            # 構建參數列表（已移除 similarity_threshold）
            query_params = [
                vector_str,
                intent_id if intent_id else -1,
                all_intent_ids if all_intent_ids else [],
                [vendor_id],  # 用於 kb.vendor_ids && %s::int[]
                vendor_business_types,
            ]

            if target_user_roles is not None:
                query_params.append(target_user_roles)

            query_params.extend([
                vector_str,
                intent_id if intent_id else -1,
                all_intent_ids if all_intent_ids else [],
                vector_limit
            ])

            cursor.execute(sql_query, tuple(query_params))
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
        知識庫關鍵字檢索實作
        """
        import jieba

        # 分詞處理查詢
        query_tokens = set(jieba.cut(query.lower()))
        # 過濾空白與單字（單字 noise 太多）
        query_tokens_for_sql = [t for t in query_tokens if t.strip() and len(t) > 1]

        # 獲取額外參數
        target_user = kwargs.get('target_user', 'tenant')

        # 安全上限
        max_rows = 1000

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 通用 SELECT 與 WHERE
            base_sql = """
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.vendor_ids,
                    kb.business_types,
                    kb.target_user,
                    kb.keywords,
                    kb.video_url,
                    kb.form_id,
                    kb.action_type,
                    kb.api_config,
                    kim.intent_id
                FROM knowledge_base kb
                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                WHERE
                    (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && %s::int[])
                    AND kb.is_active = TRUE
                    AND kb.keywords IS NOT NULL
                    AND array_length(kb.keywords, 1) > 0
            """

            all_rows = []

            # 快速路徑：SQL 用 keywords && query_tokens 過濾（精確配對）
            if query_tokens_for_sql:
                cursor.execute(
                    base_sql + " AND kb.keywords && %s::text[] ORDER BY kb.priority DESC, kb.id DESC LIMIT %s",
                    ([vendor_id], query_tokens_for_sql, max_rows)
                )
                all_rows = cursor.fetchall()

            # Fallback：精確配對 0 結果時撈全部，讓 Python jieba 處理多字詞 keyword
            if not all_rows:
                cursor.execute(
                    base_sql + " ORDER BY kb.priority DESC, kb.id DESC LIMIT %s",
                    ([vendor_id], max_rows)
                )
                all_rows = cursor.fetchall()

            cursor.close()

            # 篩選包含匹配關鍵字的知識
            keyword_matched_knowledge = []

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
                    # task 3.2：keyword 路徑寫入獨立欄位
                    # vector_similarity 預設 0.0（代表「向量沒命中、純靠 keyword 找到」）
                    result['keyword_score'] = normalized_score
                    result['vector_similarity'] = 0.0
                    result['original_similarity'] = 0.0  # alias 同步
                    result['similarity'] = 0.0  # 待 _finalize_scores 重算
                    result['keyword_matches'] = matched_keywords
                    result['search_method'] = 'keyword'

                    keyword_matched_knowledge.append(result)

            # 按 keyword_score 排序，取前 limit 個（final similarity 由 _finalize_scores 算）
            keyword_matched_knowledge.sort(key=lambda x: x.get('keyword_score') or 0, reverse=True)
            return keyword_matched_knowledge[:limit]

        finally:
            conn.close()

    def _format_result(self, row: Dict) -> Dict:
        """
        格式化知識庫檢索結果（task 3.3）

        欄位來源（與 SOP retriever 對稱）：
        - vector_similarity：vector path 從 row['vector_similarity']（SQL alias）讀；
          keyword path（row 無此欄位）預設 0.0
        - keyword_score / rerank_score：預設 None
        - keyword_boost：預設 1.0
        - similarity：暫時 = vector_similarity，由 _finalize_scores 依公式重算
        - original_similarity：向後相容 alias = vector_similarity
        """
        defaults = make_default_result()
        vector_similarity = row.get('vector_similarity', defaults['vector_similarity'])

        return {
            'id': row['id'],
            'question_summary': row.get('question_summary'),
            'answer': row.get('answer'),
            'scope': row.get('scope'),
            'priority': row.get('priority'),
            'vendor_ids': row.get('vendor_ids'),
            'business_types': row.get('business_types'),
            'target_user': row.get('target_user'),
            'keywords': row.get('keywords', []),
            'video_url': row.get('video_url'),
            'form_id': row.get('form_id'),
            'action_type': row.get('action_type'),
            'api_config': row.get('api_config'),
            'intent_id': row.get('intent_id'),
            # ─── 分數欄位（task 3.3） ───
            'vector_similarity': vector_similarity,
            'keyword_score': defaults['keyword_score'],
            'keyword_boost': defaults['keyword_boost'],
            'rerank_score': defaults['rerank_score'],
            'similarity': vector_similarity,  # 暫時值，由 _finalize_scores 重算
            'score_source': defaults['score_source'],
            'keyword_matches': list(defaults['keyword_matches']),
            'original_similarity': vector_similarity,  # 向後相容 alias
            # ─── 既有 metadata ───
            'search_method': row.get('search_method', 'vector'),
        }

    # 便利方法：保持向後相容
    async def retrieve_knowledge_hybrid(
        self,
        query: str,
        intent_id: Optional[int],
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        all_intent_ids: Optional[List[int]] = None,
        target_user: str = 'tenant',
        mode: str = 'b2c',
        return_debug_info: bool = False,
        use_semantic_boost: bool = True,
        return_unfiltered: bool = False,
        precomputed_embedding=None,
        precomputed_rewrites=None
    ) -> List[Dict]:
        """
        向後相容的介面
        調用統一的 retrieve 方法

        Args:
            return_unfiltered: debug 旁路（followup-debug-visibility 選項 A）。
                透傳到 retrieve()，True 時跳過 threshold 過濾，
                供 chat-test 顯示完整候選。
            precomputed_embedding: 預計算的查詢向量（避免重複呼叫 API）
            precomputed_rewrites: 預計算的改寫查詢（避免重複呼叫 LLM）
        """
        results = await self.retrieve(
            query=query,
            vendor_id=vendor_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            enable_keyword_fallback=True,  # 啟用關鍵字備選
            enable_keyword_boost=True,      # 啟用關鍵字加成
            return_unfiltered=return_unfiltered,
            intent_id=intent_id,
            all_intent_ids=all_intent_ids,
            target_user=target_user,
            mode=mode,
            precomputed_embedding=precomputed_embedding,
            precomputed_rewrites=precomputed_rewrites
        )

        # 如果不需要 debug info，移除內部欄位
        if not return_debug_info:
            for result in results:
                result.pop('search_method', None)
                result.pop('keyword_matches', None)
                result.pop('keyword_boost', None)
                result.pop('original_similarity', None)
                result.pop('rerank_score', None)

        return results