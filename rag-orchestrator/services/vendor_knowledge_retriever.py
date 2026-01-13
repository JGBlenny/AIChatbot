"""
業者知識檢索服務
根據業者 ID 和意圖檢索知識，自動處理模板變數替換
"""
import os
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from .vendor_parameter_resolver import VendorParameterResolver
from .embedding_utils import get_embedding_client
from .db_utils import get_db_config


class VendorKnowledgeRetriever:
    """業者知識檢索器"""

    def __init__(self):
        """初始化知識檢索器"""
        # 使用共用的 embedding 客戶端
        self.embedding_client = get_embedding_client()

        # 參數解析器
        self.param_resolver = VendorParameterResolver()

        # 意圖語義匹配器（方案2：語義化意圖匹配）
        from .intent_semantic_matcher import get_intent_semantic_matcher
        self.intent_matcher = get_intent_semantic_matcher()

    def _get_db_connection(self):
        """建立資料庫連接（使用共用配置）"""
        db_config = get_db_config()
        return psycopg2.connect(**db_config)

    def retrieve_knowledge(
        self,
        intent_id: int,
        vendor_id: int,
        top_k: int = 3
    ) -> List[Dict]:
        """
        檢索知識

        Args:
            intent_id: 意圖 ID
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識

        Returns:
            知識列表，按優先級排序
            [
                {
                    "id": 1,
                    "question_summary": "每月繳費日期",
                    "answer": "您的租金繳費日為每月 1 號...",
                    "scope": "global",
                    "priority": 1
                }
            ]
        """
        # 獲取 vendor 的業態類型
        vendor_info = self.param_resolver.get_vendor_info(vendor_id)
        vendor_business_types = vendor_info.get('business_types', [])

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 查詢策略：
            # 1. customized (vendor_id 匹配 + scope='customized') - 最高優先級
            # 2. vendor (vendor_id 匹配 + scope='vendor')
            # 3. global (vendor_id IS NULL + scope='global')
            #
            # 使用 CASE WHEN 設定優先級權重，再根據 priority 欄位排序

            # 使用 knowledge_intent_mapping 進行意圖關聯查詢
            cursor.execute("""
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.is_template,
                    kb.template_vars,
                    kb.vendor_id,
                    kb.business_types,
                    kb.created_at,
                    kb.video_url,
                    kb.video_file_size,
                    kb.video_duration,
                    kb.video_format,
                    kb.form_id,
                    kb.form_intro,
                    kb.trigger_form_condition,
                    -- 計算優先級權重
                    CASE
                        WHEN kb.scope = 'customized' AND kb.vendor_id = %s THEN 1000
                        WHEN kb.scope = 'vendor' AND kb.vendor_id = %s THEN 500
                        WHEN kb.scope = 'global' AND kb.vendor_id IS NULL THEN 100
                        ELSE 0
                    END as scope_weight
                FROM knowledge_base kb
                INNER JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                WHERE
                    kim.intent_id = %s
                    AND (
                        -- 業者客製化知識
                        (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
                        OR
                        -- 全域知識
                        (kb.vendor_id IS NULL AND kb.scope = 'global')
                    )
                    -- ✅ 業態類型過濾（新增）
                    AND (
                        kb.business_types IS NULL  -- 通用知識（適用所有業態）
                        OR kb.business_types && %s::text[]  -- 陣列重疊：知識的業態類型與業者的業態類型有交集
                    )
                ORDER BY
                    scope_weight DESC,  -- 先按範圍權重排序
                    kb.priority DESC,   -- 再按優先級排序
                    kb.created_at DESC  -- 最後按建立時間排序
                LIMIT %s
            """, (vendor_id, vendor_id, intent_id, vendor_id, vendor_business_types, top_k))

            rows = cursor.fetchall()
            cursor.close()

            # 處理結果
            results = []
            for row in rows:
                knowledge = dict(row)

                # 移除內部欄位
                knowledge.pop('scope_weight', None)

                results.append(knowledge)

            return results

        finally:
            conn.close()

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        呼叫 Embedding API 將文字轉換為向量

        Args:
            text: 要轉換的文字

        Returns:
            向量列表，如果失敗則返回 None
        """
        # 使用共用的 embedding 客戶端（verbose=False 保持簡潔）
        return await self.embedding_client.get_embedding(text, verbose=False)

    async def retrieve_knowledge_hybrid(
        self,
        query: str,
        intent_id: Optional[int],
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        all_intent_ids: Optional[List[int]] = None,
        target_user: str = 'tenant',
        return_debug_info: bool = False,
        use_semantic_boost: bool = True  # 新增：是否使用語義加成
    ) -> List[Dict]:
        """
        混合模式檢索：向量相似度 + 意圖加成排序（統一檢索路徑）

        這是統一的檢索方法，適用於所有查詢（包括 unclear）：
        1. 使用向量相似度過濾知識（主要依據）
        2. 意圖加成用於排序（輔助優化）
        3. 考慮 scope 優先級（customized > vendor > global）
        4. 支援 intent_id = None（unclear 情況，無意圖加成，boost = 1.0）

        Args:
            query: 使用者問題
            intent_id: 主要意圖 ID（None 表示 unclear，無意圖加成）
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識
            similarity_threshold: 相似度閾值
            all_intent_ids: 所有相關意圖 IDs（包含主要和次要）
            target_user: 目標用戶角色：tenant(租客), landlord(房東), property_manager(物管), system_admin(系統管理)
            return_debug_info: 是否返回調試信息（保留 intent_boost, scope_weight 等字段）

        Returns:
            知識列表，按相似度和優先級排序
        """
        # 定義允許的目標用戶角色
        ALLOWED_TARGET_USERS = ['tenant', 'landlord', 'property_manager', 'system_admin']

        # 0. 根據用戶角色決定業態類型和目標用戶過濾策略
        is_b2b_mode = (target_user in ['property_manager', 'system_admin'])

        # 0.1 業態類型過濾（business_types）
        if is_b2b_mode:
            # B2B 模式：業者員工/系統商，使用 system_provider 業態
            vendor_business_types = ['system_provider']
            # B2B 模式：不允許 NULL（通用知識），只允許明確標記為 system_provider 的知識
            business_type_filter_sql = "kb.business_types && %s::text[]"
            print(f"   📋 [B2B Mode] Using system_provider business type (strict filtering)")
        else:
            # B2C 模式：終端客戶，使用業者的業態類型
            vendor_info = self.param_resolver.get_vendor_info(vendor_id)
            vendor_business_types = vendor_info.get('business_types', [])
            # B2C 模式：允許 NULL（通用知識）或匹配業者業態
            business_type_filter_sql = "(kb.business_types IS NULL OR kb.business_types && %s::text[])"
            print(f"   📋 [B2C Mode] Using vendor {vendor_id} business types: {vendor_business_types}")

        # 0.2 目標用戶過濾（target_user）
        # 支援角色: tenant(租客), landlord(房東), property_manager(物業管理師), system_admin(系統管理員)
        target_user_roles = []
        if target_user in ALLOWED_TARGET_USERS:
            # 細分角色：只顯示該角色或通用知識
            target_user_roles = [target_user]
            target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"
            print(f"   👤 [Target User] Filtering for role: {target_user}")
        else:
            # 未知角色或向後兼容：默認為租客
            target_user_roles = ['tenant']
            target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"
            print(f"   ⚠️  [Target User] Unknown role '{target_user}', defaulting to 'tenant'")

        # 1. 獲取問題的向量
        query_embedding = await self._get_embedding(query)

        if not query_embedding:
            print("⚠️  向量生成失敗，降級使用純 intent-based 檢索")
            return self.retrieve_knowledge(intent_id, vendor_id, top_k)

        # 2. 準備 Intent IDs（支援多 Intent，支援 None）
        if intent_id is None:
            # unclear 情況：沒有意圖
            all_intent_ids = []
            intent_id_for_sql = -1  # 使用不存在的 ID，SQL 中所有 CASE WHEN 都不匹配
        else:
            all_intent_ids = all_intent_ids if all_intent_ids is not None else [intent_id]
            intent_id_for_sql = intent_id

        # 2. 執行混合檢索
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            vector_str = str(query_embedding)

            # ✅ 方案5：意圖作為軟過濾器
            # - 移除硬性意圖過濾，所有知識都參與檢索
            # - intent_boost 先用簡單邏輯（精確匹配 1.3，其他 1.0）
            # - 後續在 Python 中使用語義匹配器重新計算 boost（方案2）
            # ✅ 方案2：語義化意圖匹配（在 Python 中實現）
            # - SQL 查詢使用較低閾值（考慮最大 boost 1.3x）
            # - Python 中使用語義相似度重新計算 boost
            # - 加成後過濾 >= similarity_threshold
            # - 重新排序後取 top_k

            # 計算 SQL 查詢的最低閾值（考慮最大 boost 1.3x）
            # 如果 similarity_threshold = 0.65，且最大 boost = 1.3
            # 那麼 sql_threshold = 0.65 / 1.3 = 0.5
            sql_threshold = similarity_threshold / 1.3 if use_semantic_boost else similarity_threshold

            # 獲取更多候選以供語義匹配重排序
            candidate_limit = top_k * 3

            sql_query = f"""
                SELECT
                    kb.id,
                    kb.question_summary,
                    kb.answer,
                    kb.scope,
                    kb.priority,
                    kb.is_template,
                    kb.template_vars,
                    kb.vendor_id,
                    kb.business_types,
                    kb.target_user,
                    kb.created_at,
                    kb.video_url,
                    kb.video_file_size,
                    kb.video_duration,
                    kb.video_format,
                    kb.form_id,
                    kb.form_intro,
                    kb.trigger_form_condition,
                    kim.intent_id,
                    kim.intent_type,
                    -- 計算向量相似度
                    1 - (kb.embedding <=> %s::vector) as base_similarity,
                    -- Intent 匹配加成（簡化版，將在 Python 中用語義匹配替換）
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3          -- 精確匹配主要 Intent
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1  -- 精確匹配次要 Intent
                        ELSE 1.0                                  -- 其他（將用語義相似度替換）
                    END as sql_intent_boost,
                    -- 加成後的相似度（臨時，將在 Python 中重新計算）
                    (1 - (kb.embedding <=> %s::vector)) *
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1
                        ELSE 1.0
                    END as sql_boosted_similarity,
                    -- 計算 Scope 權重
                    CASE
                        WHEN kb.scope = 'customized' AND kb.vendor_id = %s THEN 1000
                        WHEN kb.scope = 'vendor' AND kb.vendor_id = %s THEN 500
                        WHEN kb.scope = 'global' AND kb.vendor_id IS NULL THEN 100
                        ELSE 0
                    END as scope_weight
                FROM knowledge_base kb
                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                WHERE
                    -- Scope 過濾
                    (
                        (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
                        OR
                        (kb.vendor_id IS NULL AND kb.scope = 'global')
                    )
                    -- 向量存在
                    AND kb.embedding IS NOT NULL
                    -- 相似度閾值（基於原始相似度，不含加成）
                    AND (1 - (kb.embedding <=> %s::vector)) >= %s
                    -- ✅ 方案5：移除硬性意圖過濾！
                    -- 之前：AND (kim.intent_id = ANY(intent_ids) OR kim.intent_id IS NULL)
                    -- 現在：所有知識都參與，無論意圖是否匹配
                    -- ✅ 業態類型過濾：B2B 嚴格過濾（只允許 system_provider），B2C 允許通用知識
                    AND {business_type_filter_sql}
                    -- ✅ 目標用戶過濾：確保知識適用於當前用戶角色（tenant/landlord/property_manager等）
                    AND {target_user_filter_sql}
                ORDER BY
                    scope_weight DESC,           -- 1st: Scope 優先級
                    sql_boosted_similarity DESC, -- 2nd: SQL 計算的加成相似度（臨時）
                    kb.priority DESC             -- 3rd: 人工優先級
                LIMIT %s
            """

            # 構建參數列表（支援 intent_id = None 的情況）
            query_params = [
                vector_str,
                intent_id_for_sql,  # 使用 -1 代替 None
                all_intent_ids if all_intent_ids else [],
                vector_str,
                intent_id_for_sql,
                all_intent_ids if all_intent_ids else [],
                vendor_id,
                vendor_id,
                vendor_id,
                vector_str,
                sql_threshold,  # ✅ 使用較低的 SQL 閾值
                vendor_business_types,  # ✅ 業態類型過濾參數
            ]

            # 如果有 target_user 過濾，添加參數
            if target_user_roles is not None:
                query_params.append(target_user_roles)

            query_params.append(candidate_limit)  # 獲取更多候選用於重排序

            cursor.execute(sql_query, tuple(query_params))

            rows = cursor.fetchall()
            cursor.close()

            print(f"\n🔍 [Hybrid Retrieval - Enhanced] Query: {query}")
            print(f"   Primary Intent ID: {intent_id}, All Intents: {all_intent_ids}, Vendor ID: {vendor_id}")
            print(f"   SQL threshold: {sql_threshold:.3f}, Target threshold: {similarity_threshold:.3f}")
            print(f"   Found {len(rows)} SQL candidates (will rerank and filter):")

            # ✅ 方案2：使用語義匹配器重新計算 intent_boost
            candidates = []
            filtered_count = 0
            for row in rows:
                knowledge = dict(row)
                knowledge_intent_id = knowledge.get('intent_id')
                knowledge_intent_type = knowledge.get('intent_type')

                # 使用語義匹配器計算 boost
                intent_semantic_similarity = None

                # unclear 情況（intent_id = None）：無意圖加成
                if intent_id is None:
                    boost = 1.0
                    reason = "無意圖（unclear）"
                    intent_semantic_similarity = 0.0
                elif use_semantic_boost and knowledge_intent_id:
                    boost, reason, intent_semantic_similarity = self.intent_matcher.calculate_semantic_boost(
                        intent_id,
                        knowledge_intent_id,
                        knowledge_intent_type
                    )
                else:
                    # 沒有意圖標註或不使用語義加成
                    if knowledge_intent_id == intent_id:
                        boost = 1.3
                        reason = "精確匹配"
                        intent_semantic_similarity = 1.0
                    elif knowledge_intent_id in all_intent_ids:
                        boost = 1.1
                        reason = "次要意圖匹配"
                        intent_semantic_similarity = 0.8
                    else:
                        boost = 1.0
                        reason = "無意圖匹配"
                        intent_semantic_similarity = 0.0

                # 重新計算加成後相似度
                base_similarity = knowledge['base_similarity']
                boosted_similarity = base_similarity * boost

                # ✅ 方案 A：只用向量相似度過濾，意圖純粹作為排序因子
                # 修改日期：2026-01-13
                # 修改原因：消除「意圖依賴區間」，使意圖變成純排序加分項而非過濾條件
                if base_similarity < similarity_threshold:
                    filtered_count += 1
                    continue

                # 更新 boost 和加成後相似度
                knowledge['intent_boost'] = boost
                knowledge['boosted_similarity'] = boosted_similarity
                knowledge['boost_reason'] = reason
                knowledge['intent_semantic_similarity'] = intent_semantic_similarity

                candidates.append(knowledge)

            print(f"   After semantic boost and filtering: {len(candidates)} candidates (filtered out: {filtered_count})")

            # ✅ 重新排序：scope_weight > boosted_similarity > priority
            candidates.sort(
                key=lambda x: (
                    -x['scope_weight'],           # 降序：scope 優先級高的在前
                    -x['boosted_similarity'],     # 降序：相似度高的在前
                    -x.get('priority', 0)         # 降序：人工優先級高的在前
                )
            )

            # ✅ 去重：對於多意圖知識，只保留最高分版本
            seen_ids = set()
            unique_candidates = []
            duplicates_removed = 0
            for candidate in candidates:
                knowledge_id = candidate['id']
                if knowledge_id not in seen_ids:
                    seen_ids.add(knowledge_id)
                    unique_candidates.append(candidate)
                else:
                    duplicates_removed += 1

            if duplicates_removed > 0:
                print(f"   ℹ️  去重：移除了 {duplicates_removed} 個重複的知識（多意圖知識的較低分版本）")

            # 取 top_k
            results = unique_candidates[:top_k]

            # 輸出結果
            for idx, knowledge in enumerate(results, 1):
                # 標記 Intent 匹配狀態
                if knowledge['intent_id'] == intent_id:
                    intent_marker = "★"  # 主要 Intent
                elif knowledge['intent_id'] in all_intent_ids:
                    intent_marker = "☆"  # 次要 Intent
                else:
                    intent_marker = "○"  # 其他

                print(f"   {idx}. {intent_marker} ID {knowledge['id']}: {knowledge['question_summary'][:40]}... "
                      f"(原始: {knowledge['base_similarity']:.3f}, "
                      f"boost: {knowledge['intent_boost']:.2f}x [{knowledge['boost_reason']}], "
                      f"加成後: {knowledge['boosted_similarity']:.3f}, "
                      f"intent: {knowledge['intent_id']})")

                # 保留原始相似度和加成後相似度
                # similarity: 加成後相似度（用於排序）
                # original_similarity: 原始相似度（用於完美匹配判斷）
                knowledge['similarity'] = knowledge['boosted_similarity']
                knowledge['original_similarity'] = knowledge['base_similarity']

                # 如果不是調試模式，移除內部欄位
                if not return_debug_info:
                    knowledge.pop('scope_weight', None)
                    knowledge.pop('base_similarity', None)
                    knowledge.pop('boosted_similarity', None)
                    knowledge.pop('intent_boost', None)
                    knowledge.pop('sql_intent_boost', None)
                    knowledge.pop('sql_boosted_similarity', None)
                    knowledge.pop('boost_reason', None)

            return results

        finally:
            conn.close()

    def retrieve_by_question(
        self,
        question: str,
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        根據問題文本檢索知識（使用語意相似度）

        Args:
            question: 使用者問題
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識
            similarity_threshold: 相似度閾值

        Returns:
            知識列表

        Note:
            這個方法需要 pgvector 或其他向量相似度搜尋功能
            目前使用簡單的關鍵字匹配作為示範
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 簡化版：使用 LIKE 匹配
            # 生產環境應該使用 pgvector 或 OpenAI embeddings
            cursor.execute("""
                SELECT
                    id,
                    question_summary,
                    answer,
                    scope,
                    priority,
                    is_template,
                    template_vars,
                    vendor_id,
                    CASE
                        WHEN scope = 'customized' AND vendor_id = %s THEN 1000
                        WHEN scope = 'vendor' AND vendor_id = %s THEN 500
                        WHEN scope = 'global' AND vendor_id IS NULL THEN 100
                        ELSE 0
                    END as scope_weight
                FROM knowledge_base
                WHERE
                    (
                        question_summary ILIKE %s
                        OR answer ILIKE %s
                    )
                    AND (
                        (vendor_id = %s AND scope IN ('customized', 'vendor'))
                        OR
                        (vendor_id IS NULL AND scope = 'global')
                    )
                ORDER BY
                    scope_weight DESC,
                    priority DESC,
                    created_at DESC
                LIMIT %s
            """, (
                vendor_id,
                vendor_id,
                f"%{question}%",
                f"%{question}%",
                vendor_id,
                top_k
            ))

            rows = cursor.fetchall()
            cursor.close()

            # 處理結果
            results = []
            for row in rows:
                knowledge = dict(row)
                knowledge.pop('scope_weight', None)
                results.append(knowledge)

            return results

        finally:
            conn.close()

    def get_knowledge_stats(self, vendor_id: Optional[int] = None) -> Dict:
        """
        獲取知識統計資訊

        Args:
            vendor_id: 業者 ID（None 表示全域統計）

        Returns:
            統計資訊
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if vendor_id:
                # 特定業者的知識統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_knowledge,
                        COUNT(CASE WHEN scope = 'global' THEN 1 END) as global_count,
                        COUNT(CASE WHEN scope = 'vendor' THEN 1 END) as vendor_count,
                        COUNT(CASE WHEN scope = 'customized' THEN 1 END) as customized_count
                    FROM knowledge_base
                    WHERE
                        vendor_id = %s OR vendor_id IS NULL
                """, (vendor_id,))
            else:
                # 全域統計
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_knowledge,
                        COUNT(CASE WHEN scope = 'global' THEN 1 END) as global_count,
                        COUNT(CASE WHEN scope = 'vendor' THEN 1 END) as vendor_count,
                        COUNT(CASE WHEN scope = 'customized' THEN 1 END) as customized_count
                    FROM knowledge_base
                """)

            stats = cursor.fetchone()
            cursor.close()

            return dict(stats)

        finally:
            conn.close()


# 使用範例
if __name__ == "__main__":
    retriever = VendorKnowledgeRetriever()

    print("📚 測試知識檢索")
    print("=" * 60)

    # 假設「帳務查詢」意圖的 ID 為 1
    # 實際使用時需要從資料庫查詢

    # 測試業者 A
    print("\n業者 A 的知識:")
    knowledge_a = retriever.retrieve_knowledge(
        intent_id=1,  # 帳務查詢
        vendor_id=1,
        top_k=5
    )
    for k in knowledge_a:
        print(f"\n【{k['scope']}】{k['question_summary']}")
        print(f"原始: {k['original_answer'][:100]}...")
        print(f"解析: {k['answer'][:100]}...")

    # 測試業者 B
    print("\n" + "=" * 60)
    print("業者 B 的知識:")
    knowledge_b = retriever.retrieve_knowledge(
        intent_id=1,  # 帳務查詢
        vendor_id=2,
        top_k=5
    )
    for k in knowledge_b:
        print(f"\n【{k['scope']}】{k['question_summary']}")
        print(f"原始: {k['original_answer'][:100]}...")
        print(f"解析: {k['answer'][:100]}...")

    # 測試統計
    print("\n" + "=" * 60)
    print("知識統計:")
    stats = retriever.get_knowledge_stats()
    print(f"總知識數: {stats['total_knowledge']}")
    print(f"全域知識: {stats['global_count']}")
    print(f"業者專屬: {stats['vendor_count']}")
    print(f"客製化: {stats['customized_count']}")
    print(f"模板數: {stats['template_count']}")
