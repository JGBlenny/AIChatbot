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

    def _has_template_variables(self, text: str) -> bool:
        """
        檢測文本是否包含模板變數 {{variable}}

        Args:
            text: 要檢測的文本

        Returns:
            True 如果包含模板變數，否則 False
        """
        import re
        if not text:
            return False
        return bool(re.search(r'\{\{.+?\}\}', text))

    def _get_db_connection(self):
        """建立資料庫連接（使用共用配置）"""
        db_config = get_db_config()
        return psycopg2.connect(**db_config)

    def retrieve_knowledge(
        self,
        intent_id: int,
        vendor_id: int,
        top_k: int = 3,
        resolve_templates: bool = True
    ) -> List[Dict]:
        """
        檢索知識並自動處理模板變數

        Args:
            intent_id: 意圖 ID
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識
            resolve_templates: 是否自動解析模板（自動檢測 {{variable}} 模式）

        Returns:
            知識列表，按優先級排序
            [
                {
                    "id": 1,
                    "question_summary": "每月繳費日期",
                    "answer": "您的租金繳費日為每月 1 號...",  # 已解析（自動檢測到 {{payment_day}} 並替換）
                    "original_answer": "您的租金繳費日為每月 {{payment_day}} 號...",  # 原始模板
                    "scope": "global",
                    "priority": 1
                }
            ]

        Note:
            系統會自動檢測答案中的 {{variable}} 模式並進行替換，
            不再依賴 is_template 欄位
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

                # 保留原始答案
                knowledge['original_answer'] = knowledge['answer']

                # 自動檢測模板變數並解析（使用動態檢測替代 is_template 欄位）
                if resolve_templates and self._has_template_variables(knowledge['answer']):
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        # 同時解析問題摘要中的變數
                        if knowledge['question_summary'] and self._has_template_variables(knowledge['question_summary']):
                            knowledge['question_summary'] = self.param_resolver.resolve_template(
                                knowledge['question_summary'],
                                vendor_id
                            )
                    except Exception as e:
                        print(f"⚠️  Template resolution failed for knowledge {knowledge['id']}: {e}")
                        # 解析失敗，保留原始模板

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
        intent_id: int,
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        resolve_templates: bool = True,
        all_intent_ids: Optional[List[int]] = None,
        user_role: str = 'customer'
    ) -> List[Dict]:
        """
        混合模式檢索：Intent 過濾 + 向量相似度排序

        這是推薦的檢索方法，結合了分類準確性和語義理解能力：
        1. 先根據 intent_id(s) 過濾出相關類別的知識
        2. 再使用向量相似度排序，找出最相關的答案
        3. 考慮 scope 優先級（customized > vendor > global）
        4. 支援多 Intent 檢索（主要 Intent 獲得 1.3x boost，次要 Intent 獲得 1.1x boost）

        Args:
            query: 使用者問題
            intent_id: 主要意圖 ID
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識
            similarity_threshold: 相似度閾值
            resolve_templates: 是否自動解析模板
            all_intent_ids: 所有相關意圖 IDs（包含主要和次要）
            user_role: 用戶角色 ('customer' = B2C 終端客戶, 'staff' = B2B 業者員工/系統商)

        Returns:
            知識列表，按相似度和優先級排序
        """
        # 0. 根據用戶角色決定業態類型和目標用戶過濾策略
        is_b2b_mode = (user_role == 'staff')

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
        # 支援角色: tenant(租客), landlord(房東), property_manager(物業管理師), system_admin(系統管理員), staff(B2B員工)
        target_user_roles = []
        if user_role in ['tenant', 'landlord', 'property_manager', 'system_admin']:
            # 細分角色：只顯示該角色或通用知識
            target_user_roles = [user_role]
            target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"
            print(f"   👤 [Target User] Filtering for role: {user_role}")
        elif user_role == 'staff':
            # B2B 員工：可能需要看所有後台操作知識
            target_user_roles = ['property_manager', 'system_admin']
            target_user_filter_sql = "(kb.target_user IS NULL OR kb.target_user && %s::text[])"
            print(f"   👤 [Target User] B2B staff mode - showing management knowledge")
        else:
            # customer 或其他：顯示通用知識（但不指定特定角色）
            target_user_roles = None
            target_user_filter_sql = "TRUE"  # 不過濾
            print(f"   👤 [Target User] Generic customer mode - no target_user filtering")

        # 1. 獲取問題的向量
        query_embedding = await self._get_embedding(query)

        if not query_embedding:
            print("⚠️  向量生成失敗，降級使用純 intent-based 檢索")
            return self.retrieve_knowledge(intent_id, vendor_id, top_k, resolve_templates)

        # 2. 準備 Intent IDs（支援多 Intent）
        if all_intent_ids is None:
            all_intent_ids = [intent_id]

        # 2. 執行混合檢索
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            vector_str = str(query_embedding)

            # Phase 1 擴展：使用 knowledge_intent_mapping 進行多意圖檢索
            # 包含 business_types 和 target_user 雙重過濾
            # 動態構建過濾條件（safe: filter_sql 僅來自預定義值）
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
                    kim.intent_id,
                    -- 計算向量相似度
                    1 - (kb.embedding <=> %s::vector) as base_similarity,
                    -- Intent 匹配加成（多 Intent 支援，調整為 1.3x 以平衡意圖與內容相似度）
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3          -- 主要 Intent: 1.3x boost
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1  -- 次要 Intent: 1.1x boost
                        ELSE 1.0                              -- 其他: 無加成
                    END as intent_boost,
                    -- 加成後的相似度 (用於排序)
                    (1 - (kb.embedding <=> %s::vector)) *
                    CASE
                        WHEN kim.intent_id = %s THEN 1.3
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.1
                        ELSE 1.0
                    END as boosted_similarity,
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
                    -- Intent 過濾（多意圖支援）
                    AND (kim.intent_id = ANY(%s::int[]) OR kim.intent_id IS NULL)
                    -- ✅ 業態類型過濾：B2B 嚴格過濾（只允許 system_provider），B2C 允許通用知識
                    AND {business_type_filter_sql}
                    -- ✅ 目標用戶過濾：確保知識適用於當前用戶角色（tenant/landlord/property_manager等）
                    AND {target_user_filter_sql}
                ORDER BY
                    scope_weight DESC,        -- 1st: Scope 優先級
                    boosted_similarity DESC,  -- 2nd: 加成後的相似度
                    kb.priority DESC          -- 3rd: 人工優先級
                LIMIT %s
            """

            # 構建參數列表
            query_params = [
                vector_str,
                intent_id,
                all_intent_ids,
                vector_str,
                intent_id,
                all_intent_ids,
                vendor_id,
                vendor_id,
                vendor_id,
                vector_str,
                similarity_threshold,
                all_intent_ids,
                vendor_business_types,  # ✅ 業態類型過濾參數
            ]

            # 如果有 target_user 過濾，添加參數
            if target_user_roles is not None:
                query_params.append(target_user_roles)

            query_params.append(top_k)

            cursor.execute(sql_query, tuple(query_params))

            rows = cursor.fetchall()
            cursor.close()

            print(f"\n🔍 [Hybrid Retrieval] Query: {query}")
            print(f"   Primary Intent ID: {intent_id}, All Intents: {all_intent_ids}, Vendor ID: {vendor_id}")
            print(f"   Found {len(rows)} results:")

            # 處理結果
            results = []
            for idx, row in enumerate(rows, 1):
                knowledge = dict(row)

                # 標記 Intent 匹配狀態
                if knowledge['intent_id'] == intent_id:
                    intent_marker = "★"  # 主要 Intent
                elif knowledge['intent_id'] in all_intent_ids:
                    intent_marker = "☆"  # 次要 Intent
                else:
                    intent_marker = "○"  # 其他

                audience_str = f", audience: {knowledge.get('audience', 'NULL')}"
                print(f"   {idx}. {intent_marker} ID {knowledge['id']}: {knowledge['question_summary'][:40]}... "
                      f"(原始: {knowledge['base_similarity']:.3f}, "
                      f"boost: {knowledge['intent_boost']:.1f}x, "
                      f"加成後: {knowledge['boosted_similarity']:.3f}, "
                      f"intent: {knowledge['intent_id']}{audience_str})")

                # 保留原始答案
                knowledge['original_answer'] = knowledge['answer']

                # 自動檢測模板變數並解析（使用動態檢測替代 is_template 欄位）
                if resolve_templates and self._has_template_variables(knowledge['answer']):
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        if knowledge['question_summary'] and self._has_template_variables(knowledge['question_summary']):
                            knowledge['question_summary'] = self.param_resolver.resolve_template(
                                knowledge['question_summary'],
                                vendor_id
                            )
                    except Exception as e:
                        print(f"⚠️  Template resolution failed for knowledge {knowledge['id']}: {e}")

                # 保留原始相似度和加成後相似度
                # similarity: 加成後相似度（用於排序）
                # original_similarity: 原始相似度（用於完美匹配判斷）
                knowledge['similarity'] = knowledge['boosted_similarity']
                knowledge['original_similarity'] = knowledge['base_similarity']
                knowledge.pop('scope_weight', None)
                knowledge.pop('base_similarity', None)
                knowledge.pop('boosted_similarity', None)
                knowledge.pop('intent_boost', None)

                results.append(knowledge)

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
                knowledge['original_answer'] = knowledge['answer']

                # 自動檢測模板變數並解析（使用動態檢測替代 is_template 欄位）
                if self._has_template_variables(knowledge['answer']):
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        if knowledge['question_summary'] and self._has_template_variables(knowledge['question_summary']):
                            knowledge['question_summary'] = self.param_resolver.resolve_template(
                                knowledge['question_summary'],
                                vendor_id
                            )
                    except Exception as e:
                        print(f"⚠️  Template resolution failed: {e}")

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
                        COUNT(CASE WHEN scope = 'customized' THEN 1 END) as customized_count,
                        COUNT(CASE WHEN is_template THEN 1 END) as template_count
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
                        COUNT(CASE WHEN scope = 'customized' THEN 1 END) as customized_count,
                        COUNT(CASE WHEN is_template THEN 1 END) as template_count
                    FROM knowledge_base
                """)

            stats = cursor.fetchone()
            cursor.close()

            return dict(stats)

        finally:
            conn.close()

    def preview_template_resolution(
        self,
        knowledge_id: int,
        vendor_id: int
    ) -> Dict:
        """
        預覽模板解析結果（用於測試）

        Args:
            knowledge_id: 知識 ID
            vendor_id: 業者 ID

        Returns:
            預覽結果
        """
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    id,
                    question_summary,
                    answer,
                    is_template,
                    template_vars
                FROM knowledge_base
                WHERE id = %s
            """, (knowledge_id,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                return {"error": "Knowledge not found"}

            knowledge = dict(row)

            # 自動檢測模板變數（使用動態檢測替代 is_template 欄位）
            has_template = self._has_template_variables(knowledge['answer'])

            if not has_template:
                return {
                    "is_template": False,
                    "original": knowledge['answer'],
                    "resolved": knowledge['answer']
                }

            # 解析模板
            resolved_answer = self.param_resolver.resolve_template(
                knowledge['answer'],
                vendor_id
            )

            # 驗證模板
            validation = self.param_resolver.validate_template(
                knowledge['answer'],
                vendor_id
            )

            return {
                "is_template": True,
                "original_question": knowledge['question_summary'],
                "original_answer": knowledge['answer'],
                "resolved_question": self.param_resolver.resolve_template(
                    knowledge['question_summary'],
                    vendor_id
                ) if knowledge['question_summary'] and self._has_template_variables(knowledge['question_summary']) else knowledge['question_summary'],
                "resolved_answer": resolved_answer,
                "template_vars": knowledge['template_vars'],
                "validation": validation
            }

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
