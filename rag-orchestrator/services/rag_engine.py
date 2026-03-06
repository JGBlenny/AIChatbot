"""
RAG 檢索引擎
負責向量相似度搜尋，從知識庫中檢索相關內容
"""
import os
from typing import List, Dict, Optional
import asyncpg
from asyncpg.pool import Pool
from .embedding_utils import get_embedding_client
from .semantic_reranker import get_semantic_reranker


class RAGEngine:
    """RAG 檢索引擎"""

    def __init__(self, db_pool: Pool):
        """
        初始化 RAG 引擎

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        # 使用共用的 embedding 客戶端
        self.embedding_client = get_embedding_client()
        # 讀取優先級加成值（固定加成，預設 0.15）
        self.priority_boost = float(os.getenv("PRIORITY_BOOST", "0.15"))
        # 讀取優先級品質門檻（只對高品質答案加分，預設 0.70）
        self.priority_quality_threshold = float(os.getenv("PRIORITY_QUALITY_THRESHOLD", "0.70"))
        # 初始化語義重排序器
        self.semantic_reranker = get_semantic_reranker()
        # 是否啟用語義重排序（預設關閉，可根據需求開啟）
        self.use_semantic_rerank = os.getenv("USE_SEMANTIC_RERANK", "false").lower() == "true"

    async def search(
        self,
        query: str,
        limit: int = None,
        similarity_threshold: float = 0.6,
        intent_ids: Optional[List[int]] = None,
        primary_intent_id: Optional[int] = None,
        target_users: Optional[List[str]] = None,
        vendor_id: Optional[int] = None
    ) -> List[Dict]:
        """
        搜尋相關知識（支援多意圖過濾與加成 + 目標用戶過濾 + 業態類型過濾）

        Args:
            query: 查詢問題
            limit: 返回結果數量
            similarity_threshold: 相似度閾值
            intent_ids: 所有相關意圖 IDs（用於過濾）
            primary_intent_id: 主要意圖 ID（用於加成排序）
            target_users: 目標用戶列表（用於角色隔離）：tenant, landlord, property_manager, system_admin
            vendor_id: 業者 ID（用於業態類型過濾）

        Returns:
            檢索結果列表，每個結果包含:
            - id: 知識 ID
            - title: 標題
            - content: 內容
            - category: 分類
            - similarity: 相似度分數 (0-1)
        """
        # 從環境變數讀取檢索條數（用於降低成本）
        if limit is None:
            limit = int(os.getenv("RAG_RETRIEVAL_LIMIT", "5"))

        # 獲取業者的業態類型（用於過濾）
        vendor_business_types = None
        if vendor_id:
            async with self.db_pool.acquire() as conn:
                vendor_row = await conn.fetchrow("""
                    SELECT business_types FROM vendors WHERE id = $1
                """, vendor_id)
                if vendor_row and vendor_row['business_types']:
                    vendor_business_types = vendor_row['business_types']

        print(f"\n🔍 [RAG Engine] 開始搜尋")
        print(f"   查詢: {query}")
        print(f"   閾值: {similarity_threshold}, 限制: {limit}")
        if intent_ids:
            print(f"   意圖過濾: {intent_ids}, 主要意圖: {primary_intent_id}")
        if target_users:
            print(f"   🔒 Target User 過濾: {target_users}")
        if vendor_business_types:
            print(f"   🏢 業態過濾: {vendor_business_types}")

        # 1. 將問題轉換為向量
        query_embedding = await self._get_embedding(query)

        if not query_embedding:
            print(f"   ❌ 向量生成失敗，返回空結果")
            return []

        # 2. 向量相似度搜尋（支援多意圖過濾與加成）
        # 將 Python list 轉換為 PostgreSQL vector 字符串格式
        vector_str = str(query_embedding)
        print(f"   向量長度: {len(query_embedding)}, 字串長度: {len(vector_str)}")

        async with self.db_pool.acquire() as conn:
            if intent_ids and primary_intent_id:
                # 多意圖模式：JOIN knowledge_intent_mapping 並使用加成策略
                # 包含 target_user 過濾（角色隔離）
                if target_users:
                    # 有 target_user 過濾
                    if vendor_business_types:
                        # 有業態過濾
                        results = await conn.fetch("""
                            SELECT * FROM (
                                SELECT DISTINCT ON (kb.id)
                                    kb.id,
                                    kb.question_summary,
                                    kb.answer as content,
                                    kb.target_user,
                                    kb.keywords,
                                    kb.business_types,
                                    kb.scope,
                                    kb.vendor_ids,
                                    kb.priority,
                                    kb.form_id,
                                    kb.trigger_form_condition,
                                    1 - (kb.embedding <=> $1::vector) as base_similarity,
                                    -- 意圖加成
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3  -- 主要意圖 1.3x boost
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1  -- 次要意圖 1.1x boost
                                        ELSE 1.0
                                    END as intent_boost,
                                    -- 優先級加成（單獨返回）
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $9
                                        THEN $8
                                        ELSE 0
                                    END as priority_boost,
                                    -- 加成後相似度（意圖加成為乘法，優先級加成為固定值）
                                    (1 - (kb.embedding <=> $1::vector)) *
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1
                                        ELSE 1.0
                                    END +
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $9
                                        THEN $8
                                        ELSE 0
                                    END as boosted_similarity
                                FROM knowledge_base kb
                                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                                WHERE kb.embedding IS NOT NULL
                                    AND (1 - (kb.embedding <=> $1::vector)) >= $2
                                    AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                                    AND (kb.target_user IS NULL OR kb.target_user && $6::text[])
                                    AND (kb.business_types IS NULL OR kb.business_types && $7::text[])
                                    AND (
                                        $10::int IS NULL OR
                                        array_length(kb.vendor_ids, 1) IS NULL OR
                                        kb.vendor_ids && ARRAY[$10]::int[]
                                    )
                                ORDER BY kb.id, boosted_similarity DESC
                            ) AS deduped
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids, target_users, vendor_business_types, self.priority_boost, self.priority_quality_threshold, vendor_id)
                    else:
                        # 無業態過濾
                        results = await conn.fetch("""
                            SELECT * FROM (
                                SELECT DISTINCT ON (kb.id)
                                    kb.id,
                                    kb.question_summary,
                                    kb.answer as content,
                                    kb.category,
                                    kb.target_user,
                                    kb.keywords,
                                    kb.scope,
                                    kb.vendor_ids,
                                    kb.priority,
                                    kb.form_id,
                                    kb.trigger_form_condition,
                                    1 - (kb.embedding <=> $1::vector) as base_similarity,
                                    -- 意圖加成
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3  -- 主要意圖 1.3x boost
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1  -- 次要意圖 1.1x boost
                                        ELSE 1.0
                                    END as intent_boost,
                                    -- 優先級加成（單獨返回）
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $8
                                        THEN $7
                                        ELSE 0
                                    END as priority_boost,
                                    -- 加成後相似度（意圖加成為乘法，優先級加成為固定值）
                                    (1 - (kb.embedding <=> $1::vector)) *
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1
                                        ELSE 1.0
                                    END +
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $8
                                        THEN $7
                                        ELSE 0
                                    END as boosted_similarity
                                FROM knowledge_base kb
                                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                                WHERE kb.embedding IS NOT NULL
                                    AND (1 - (kb.embedding <=> $1::vector)) >= $2
                                    AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                                    AND (kb.target_user IS NULL OR kb.target_user && $6::text[])
                                    AND (
                                        $9::int IS NULL OR
                                        array_length(kb.vendor_ids, 1) IS NULL OR
                                        kb.vendor_ids && ARRAY[$9]::int[]
                                    )
                                ORDER BY kb.id, boosted_similarity DESC
                            ) AS deduped
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids, target_users, self.priority_boost, self.priority_quality_threshold, vendor_id)
                else:
                    # 無 target_user 過濾（向後兼容）
                    if vendor_business_types:
                        # 有業態過濾
                        results = await conn.fetch("""
                            SELECT * FROM (
                                SELECT DISTINCT ON (kb.id)
                                    kb.id,
                                    kb.question_summary,
                                    kb.answer as content,
                                    kb.target_user,
                                    kb.keywords,
                                    kb.business_types,
                                    kb.scope,
                                    kb.vendor_ids,
                                    kb.priority,
                                    kb.form_id,
                                    kb.trigger_form_condition,
                                    1 - (kb.embedding <=> $1::vector) as base_similarity,
                                    -- 意圖加成
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3  -- 主要意圖 1.3x boost
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1  -- 次要意圖 1.1x boost
                                        ELSE 1.0
                                    END as intent_boost,
                                    -- 優先級加成（單獨返回）
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $8
                                        THEN $7
                                        ELSE 0
                                    END as priority_boost,
                                    -- 加成後相似度（意圖加成為乘法，優先級加成為固定值）
                                    (1 - (kb.embedding <=> $1::vector)) *
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1
                                        ELSE 1.0
                                    END +
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $8
                                        THEN $7
                                        ELSE 0
                                    END as boosted_similarity
                                FROM knowledge_base kb
                                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                                WHERE kb.embedding IS NOT NULL
                                    AND (1 - (kb.embedding <=> $1::vector)) >= $2
                                    AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                                    AND (kb.business_types IS NULL OR kb.business_types && $6::text[])
                                    AND (
                                        $9::int IS NULL OR
                                        array_length(kb.vendor_ids, 1) IS NULL OR
                                        kb.vendor_ids && ARRAY[$9]::int[]
                                    )
                                ORDER BY kb.id, boosted_similarity DESC
                            ) AS deduped
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids, vendor_business_types, self.priority_boost, self.priority_quality_threshold, vendor_id)
                    else:
                        # 無業態過濾
                        results = await conn.fetch("""
                            SELECT * FROM (
                                SELECT DISTINCT ON (kb.id)
                                    kb.id,
                                    kb.question_summary,
                                    kb.answer as content,
                                    kb.category,
                                    kb.target_user,
                                    kb.keywords,
                                    kb.scope,
                                    kb.vendor_ids,
                                    kb.priority,
                                    kb.form_id,
                                    kb.trigger_form_condition,
                                    1 - (kb.embedding <=> $1::vector) as base_similarity,
                                    -- 意圖加成
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3  -- 主要意圖 1.3x boost
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1  -- 次要意圖 1.1x boost
                                        ELSE 1.0
                                    END as intent_boost,
                                    -- 優先級加成（單獨返回）
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $7
                                        THEN $6
                                        ELSE 0
                                    END as priority_boost,
                                    -- 加成後相似度（意圖加成為乘法，優先級加成為固定值）
                                    (1 - (kb.embedding <=> $1::vector)) *
                                    CASE
                                        WHEN kim.intent_id = $4 THEN 1.3
                                        WHEN kim.intent_id = ANY($5::int[]) THEN 1.1
                                        ELSE 1.0
                                    END +
                                    CASE
                                        WHEN kb.priority > 0 AND (1 - (kb.embedding <=> $1::vector)) >= $7
                                        THEN $6
                                        ELSE 0
                                    END as boosted_similarity
                                FROM knowledge_base kb
                                LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                                WHERE kb.embedding IS NOT NULL
                                    AND (1 - (kb.embedding <=> $1::vector)) >= $2
                                    AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                                    AND (
                                        $8::int IS NULL OR
                                        array_length(kb.vendor_ids, 1) IS NULL OR
                                        kb.vendor_ids && ARRAY[$8]::int[]
                                    )
                                ORDER BY kb.id, boosted_similarity DESC
                            ) AS deduped
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids, self.priority_boost, self.priority_quality_threshold, vendor_id)

                # 去重並按加成後相似度排序
                seen_ids = set()
                unique_results = []
                for row in results:
                    if row['id'] not in seen_ids:
                        seen_ids.add(row['id'])
                        unique_results.append(row)
                results = sorted(unique_results, key=lambda x: x['boosted_similarity'], reverse=True)[:limit]

            else:
                # 純向量搜尋模式（向後兼容）+ target_user 過濾
                if target_users:
                    # 有 target_user 過濾
                    if vendor_business_types:
                        # 有業態過濾
                        results = await conn.fetch("""
                            SELECT
                                id,
                                question_summary,
                                answer as content,
                                target_user,
                                keywords,
                                business_types,
                                scope,
                                vendor_id,
                                priority,
                                1 - (embedding <=> $1::vector) as base_similarity,
                                1.0 as intent_boost,
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $7
                                    THEN $6
                                    ELSE 0
                                END as priority_boost,
                                (1 - (embedding <=> $1::vector)) +
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $7
                                    THEN $6
                                    ELSE 0
                                END as boosted_similarity
                            FROM knowledge_base
                            WHERE embedding IS NOT NULL
                                AND (1 - (embedding <=> $1::vector)) >= $2
                                AND (target_user IS NULL OR target_user && $4::text[])
                                AND (business_types IS NULL OR business_types && $5::text[])
                                AND (
                                    $8::int IS NULL OR
                                    vendor_id = $8 OR
                                    vendor_id IS NULL
                                )
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit, target_users, vendor_business_types, self.priority_boost, self.priority_quality_threshold, vendor_id)
                    else:
                        # 無業態過濾
                        results = await conn.fetch("""
                            SELECT
                                id,
                                question_summary,
                                answer as content,
                                target_user,
                                keywords,
                                scope,
                                vendor_id,
                                priority,
                                form_id,
                                trigger_form_condition,
                                1 - (embedding <=> $1::vector) as base_similarity,
                                1.0 as intent_boost,
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $6
                                    THEN $5
                                    ELSE 0
                                END as priority_boost,
                                (1 - (embedding <=> $1::vector)) +
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $6
                                    THEN $5
                                    ELSE 0
                                END as boosted_similarity
                            FROM knowledge_base
                            WHERE embedding IS NOT NULL
                                AND (1 - (embedding <=> $1::vector)) >= $2
                                AND (target_user IS NULL OR target_user && $4::text[])
                                AND (
                                    $7::int IS NULL OR
                                    vendor_id = $7 OR
                                    vendor_id IS NULL
                                )
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit, target_users, self.priority_boost, self.priority_quality_threshold, vendor_id)
                else:
                    # 無 target_user 過濾（向後兼容）
                    if vendor_business_types:
                        # 有業態過濾
                        results = await conn.fetch("""
                            SELECT
                                id,
                                question_summary,
                                answer as content,
                                target_user,
                                keywords,
                                business_types,
                                scope,
                                vendor_id,
                                priority,
                                1 - (embedding <=> $1::vector) as base_similarity,
                                1.0 as intent_boost,
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $6
                                    THEN $5
                                    ELSE 0
                                END as priority_boost,
                                (1 - (embedding <=> $1::vector)) +
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $6
                                    THEN $5
                                    ELSE 0
                                END as boosted_similarity
                            FROM knowledge_base
                            WHERE embedding IS NOT NULL
                                AND (1 - (embedding <=> $1::vector)) >= $2
                                AND (business_types IS NULL OR business_types && $4::text[])
                                AND (
                                    $7::int IS NULL OR
                                    vendor_id = $7 OR
                                    vendor_id IS NULL
                                )
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit, vendor_business_types, self.priority_boost, self.priority_quality_threshold, vendor_id)
                    else:
                        # 無業態過濾
                        results = await conn.fetch("""
                            SELECT
                                id,
                                question_summary,
                                answer as content,
                                target_user,
                                keywords,
                                scope,
                                vendor_id,
                                priority,
                                form_id,
                                trigger_form_condition,
                                1 - (embedding <=> $1::vector) as base_similarity,
                                1.0 as intent_boost,
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $5
                                    THEN $4
                                    ELSE 0
                                END as priority_boost,
                                (1 - (embedding <=> $1::vector)) +
                                CASE
                                    WHEN priority > 0 AND (1 - (embedding <=> $1::vector)) >= $5
                                    THEN $4
                                    ELSE 0
                                END as boosted_similarity
                            FROM knowledge_base
                            WHERE embedding IS NOT NULL
                                AND (1 - (embedding <=> $1::vector)) >= $2
                                AND (
                                    $6::int IS NULL OR
                                    vendor_id = $6 OR
                                    vendor_id IS NULL
                                )
                            ORDER BY boosted_similarity DESC
                            LIMIT $3
                        """, vector_str, similarity_threshold, limit, self.priority_boost, self.priority_quality_threshold, vendor_id)

        print(f"   💾 資料庫返回 {len(results)} 個結果")

        # 3. 格式化結果
        search_results = []
        for row in results:
            # 使用 base_similarity 作為標準相似度（不含意圖加成）
            similarity = float(row.get('base_similarity', row.get('similarity', 0)))
            intent_marker = ""
            if intent_ids:
                intent_marker = f" [boost: {float(row.get('intent_boost', 1.0)):.1f}x]"
            business_types_marker = ""
            if row.get('business_types'):
                business_types_marker = f" [業態: {row.get('business_types')}]"
            print(f"      - ID {row['id']}: {row['question_summary'][:40]}... (相似度: {similarity:.3f}{intent_marker}{business_types_marker})")

            search_results.append({
                "id": row['id'],
                "question_summary": row['question_summary'],
                "content": row['content'],
                "target_user": row.get('target_user'),
                "keywords": row.get('keywords', []),
                "business_types": row.get('business_types'),
                "scope": row.get('scope', 'global'),
                "vendor_ids": row.get('vendor_ids'),
                "similarity": similarity,
                "answer": row['content'],  # 為語義重排序準備
                "form_id": row.get('form_id'),
                "trigger_form_condition": row.get('trigger_form_condition'),
                "priority": row.get('priority', 0)
            })

        # 4. 語義重排序（可選）
        if self.use_semantic_rerank and search_results and self.semantic_reranker.is_available:
            print(f"   🧠 啟用語義重排序...")
            original_order = [r['id'] for r in search_results[:5]]

            # 使用語義模型重新排序
            reranked_results = self.semantic_reranker.rerank(
                query=query,
                candidates=search_results,
                top_k=min(limit, len(search_results))
            )

            # 如果重排序成功，使用新結果
            if reranked_results:
                new_order = [r['id'] for r in reranked_results[:5]]
                if original_order != new_order:
                    print(f"      原始順序: {original_order}")
                    print(f"      重排順序: {new_order}")
                search_results = reranked_results
            else:
                print(f"      ⚠️ 語義重排序失敗，使用原始順序")

        return search_results

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        呼叫 Embedding API 將文字轉換為向量

        Args:
            text: 要轉換的文字

        Returns:
            向量列表，如果失敗則返回 None
        """
        # 使用共用的 embedding 客戶端（verbose=True 保持詳細日誌）
        print(f"🔍 [RAG Engine] 呼叫 Embedding API")
        print(f"   查詢文字: {text[:50]}...")

        embedding = await self.embedding_client.get_embedding(text, verbose=True)

        if embedding:
            print(f"   ✅ 獲得向量: 維度 {len(embedding)}")

        return embedding

    async def get_knowledge_by_id(self, knowledge_id: int) -> Optional[Dict]:
        """
        根據 ID 取得知識

        Args:
            knowledge_id: 知識 ID

        Returns:
            知識內容，如果找不到則返回 None
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id,
                    question_summary,
                    answer as content,
                    audience,
                    keywords,
                    form_id,
                    trigger_form_condition,
                    created_at,
                    updated_at
                FROM knowledge_base
                WHERE id = $1
            """, knowledge_id)

            if not row:
                return None

            return {
                "id": row['id'],
                "question_summary": row['question_summary'],
                "content": row['content'],
                "target_user": row.get('target_user'),
                "keywords": row.get('keywords', []),
                "form_id": row.get('form_id'),
                "trigger_form_condition": row.get('trigger_form_condition'),
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }

    async def search_by_keywords(
        self,
        keywords: List[str],
        limit: int = 5
    ) -> List[Dict]:
        """
        根據關鍵字搜尋

        Args:
            keywords: 關鍵字列表
            limit: 返回結果數量

        Returns:
            搜尋結果列表
        """
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT
                    id,
                    question_summary,
                    answer as content,
                    category,
                    audience,
                    keywords,
                    form_id,
                    trigger_form_condition
                FROM knowledge_base
                WHERE keywords && $1::text[]
                ORDER BY
                    -- 計算匹配的關鍵字數量
                    (SELECT COUNT(*)
                     FROM unnest(keywords) k
                     WHERE k = ANY($1::text[])) DESC
                LIMIT $2
            """, keywords, limit)

        search_results = []
        for row in results:
            # 計算關鍵字匹配度
            matched_keywords = set(row['keywords']) & set(keywords)
            match_score = len(matched_keywords) / len(keywords) if keywords else 0

            search_results.append({
                "id": row['id'],
                "question_summary": row['question_summary'],
                "content": row['content'],
                "target_user": row.get('target_user'),
                "keywords": row.get('keywords', []),
                "matched_keywords": list(matched_keywords),
                "match_score": match_score
            })

        return search_results

    async def get_category_stats(self) -> Dict:
        """
        取得分類統計（已停用，因資料庫無 category 欄位）

        Returns:
            空字典
        """
        # 注意：knowledge_base 表已不使用 category 欄位
        # 改用 intent_id 進行分類
        return {}


# 使用範例
if __name__ == "__main__":
    import asyncio

    async def test_rag_engine():
        """測試 RAG 引擎"""
        # 建立資料庫連接
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "aichatbot_admin"),
            user=os.getenv("DB_USER", "aichatbot"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            min_size=2,
            max_size=10
        )

        engine = RAGEngine(pool)

        # 測試搜尋
        print("🔍 測試向量搜尋...")
        results = await engine.search("如何退租？", limit=3)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['question_summary']} (相似度: {result['similarity']:.2f})")
            print(f"   內容: {result['content'][:100]}...")

        # 測試關鍵字搜尋
        print("\n\n🔎 測試關鍵字搜尋...")
        results = await engine.search_by_keywords(["退租", "合約"], limit=3)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['question_summary']} (匹配度: {result['match_score']:.2f})")
            print(f"   匹配關鍵字: {', '.join(result['matched_keywords'])}")

        # 關閉連接池
        await pool.close()

    # 執行測試
    asyncio.run(test_rag_engine())
