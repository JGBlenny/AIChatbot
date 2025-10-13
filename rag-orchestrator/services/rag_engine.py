"""
RAG 檢索引擎
負責向量相似度搜尋，從知識庫中檢索相關內容
"""
import os
from typing import List, Dict, Optional
import asyncpg
from asyncpg.pool import Pool
from .embedding_utils import get_embedding_client


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

    async def search(
        self,
        query: str,
        limit: int = None,
        similarity_threshold: float = 0.6,
        intent_ids: Optional[List[int]] = None,
        primary_intent_id: Optional[int] = None,
        allowed_audiences: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        搜尋相關知識（支援多意圖過濾與加成 + 業務範圍 audience 過濾）

        Args:
            query: 查詢問題
            limit: 返回結果數量
            similarity_threshold: 相似度閾值
            intent_ids: 所有相關意圖 IDs（用於過濾）
            primary_intent_id: 主要意圖 ID（用於加成排序）
            allowed_audiences: 允許的受眾列表（用於 B2B/B2C 業務範圍隔離）

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

        print(f"\n🔍 [RAG Engine] 開始搜尋")
        print(f"   查詢: {query}")
        print(f"   閾值: {similarity_threshold}, 限制: {limit}")
        if intent_ids:
            print(f"   意圖過濾: {intent_ids}, 主要意圖: {primary_intent_id}")
        if allowed_audiences:
            print(f"   🔒 Audience 過濾: {allowed_audiences}")

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
                # 包含 audience 過濾（B2B/B2C 隔離）
                if allowed_audiences:
                    # 有 audience 過濾
                    results = await conn.fetch("""
                        SELECT DISTINCT ON (kb.id)
                            kb.id,
                            kb.title,
                            kb.answer as content,
                            kb.category,
                            kb.audience,
                            kb.keywords,
                            1 - (kb.embedding <=> $1::vector) as base_similarity,
                            -- 意圖加成
                            CASE
                                WHEN kim.intent_id = $4 THEN 1.5  -- 主要意圖 1.5x boost
                                WHEN kim.intent_id = ANY($5::int[]) THEN 1.2  -- 次要意圖 1.2x boost
                                ELSE 1.0
                            END as intent_boost,
                            -- 加成後相似度
                            (1 - (kb.embedding <=> $1::vector)) *
                            CASE
                                WHEN kim.intent_id = $4 THEN 1.5
                                WHEN kim.intent_id = ANY($5::int[]) THEN 1.2
                                ELSE 1.0
                            END as boosted_similarity
                        FROM knowledge_base kb
                        LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                        WHERE kb.embedding IS NOT NULL
                            AND (1 - (kb.embedding <=> $1::vector)) >= $2
                            AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                            AND (kb.audience IS NULL OR kb.audience = ANY($6::text[]))
                        ORDER BY kb.id, boosted_similarity DESC
                        LIMIT $3
                    """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids, allowed_audiences)
                else:
                    # 無 audience 過濾（向後兼容）
                    results = await conn.fetch("""
                        SELECT DISTINCT ON (kb.id)
                            kb.id,
                            kb.title,
                            kb.answer as content,
                            kb.category,
                            kb.audience,
                            kb.keywords,
                            1 - (kb.embedding <=> $1::vector) as base_similarity,
                            -- 意圖加成
                            CASE
                                WHEN kim.intent_id = $4 THEN 1.5  -- 主要意圖 1.5x boost
                                WHEN kim.intent_id = ANY($5::int[]) THEN 1.2  -- 次要意圖 1.2x boost
                                ELSE 1.0
                            END as intent_boost,
                            -- 加成後相似度
                            (1 - (kb.embedding <=> $1::vector)) *
                            CASE
                                WHEN kim.intent_id = $4 THEN 1.5
                                WHEN kim.intent_id = ANY($5::int[]) THEN 1.2
                                ELSE 1.0
                            END as boosted_similarity
                        FROM knowledge_base kb
                        LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
                        WHERE kb.embedding IS NOT NULL
                            AND (1 - (kb.embedding <=> $1::vector)) >= $2
                            AND (kim.intent_id = ANY($5::int[]) OR kim.intent_id IS NULL)
                        ORDER BY kb.id, boosted_similarity DESC
                        LIMIT $3
                    """, vector_str, similarity_threshold, limit * 2, primary_intent_id, intent_ids)

                # 去重並按加成後相似度排序
                seen_ids = set()
                unique_results = []
                for row in results:
                    if row['id'] not in seen_ids:
                        seen_ids.add(row['id'])
                        unique_results.append(row)
                results = sorted(unique_results, key=lambda x: x['boosted_similarity'], reverse=True)[:limit]

            else:
                # 純向量搜尋模式（向後兼容）+ audience 過濾
                if allowed_audiences:
                    # 有 audience 過濾
                    results = await conn.fetch("""
                        SELECT
                            id,
                            title,
                            answer as content,
                            category,
                            audience,
                            keywords,
                            1 - (embedding <=> $1::vector) as base_similarity
                        FROM knowledge_base
                        WHERE embedding IS NOT NULL
                            AND (1 - (embedding <=> $1::vector)) >= $2
                            AND (audience IS NULL OR audience = ANY($4::text[]))
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                    """, vector_str, similarity_threshold, limit, allowed_audiences)
                else:
                    # 無 audience 過濾（向後兼容）
                    results = await conn.fetch("""
                        SELECT
                            id,
                            title,
                            answer as content,
                            category,
                            audience,
                            keywords,
                            1 - (embedding <=> $1::vector) as base_similarity
                        FROM knowledge_base
                        WHERE embedding IS NOT NULL
                            AND (1 - (embedding <=> $1::vector)) >= $2
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                    """, vector_str, similarity_threshold, limit)

        print(f"   💾 資料庫返回 {len(results)} 個結果")

        # 3. 格式化結果
        search_results = []
        for row in results:
            # 使用 base_similarity 作為標準相似度（不含意圖加成）
            similarity = float(row.get('base_similarity', row.get('similarity', 0)))
            intent_marker = ""
            if intent_ids:
                intent_marker = f" [boost: {float(row.get('intent_boost', 1.0)):.1f}x]"
            print(f"      - ID {row['id']}: {row['title'][:40]}... (相似度: {similarity:.3f}{intent_marker})")

            search_results.append({
                "id": row['id'],
                "title": row['title'],
                "content": row['content'],
                "category": row['category'],
                "audience": row.get('audience'),
                "keywords": row.get('keywords', []),
                "similarity": similarity
            })

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
                    title,
                    answer as content,
                    category,
                    audience,
                    keywords,
                    created_at,
                    updated_at
                FROM knowledge_base
                WHERE id = $1
            """, knowledge_id)

            if not row:
                return None

            return {
                "id": row['id'],
                "title": row['title'],
                "content": row['content'],
                "category": row['category'],
                "audience": row.get('audience'),
                "keywords": row.get('keywords', []),
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
                    title,
                    answer as content,
                    category,
                    audience,
                    keywords
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
                "title": row['title'],
                "content": row['content'],
                "category": row['category'],
                "audience": row.get('audience'),
                "keywords": row.get('keywords', []),
                "matched_keywords": list(matched_keywords),
                "match_score": match_score
            })

        return search_results

    async def get_category_stats(self) -> Dict:
        """
        取得分類統計

        Returns:
            分類統計資訊
        """
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT
                    category,
                    COUNT(*) as count
                FROM knowledge_base
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)

        return {
            row['category']: row['count']
            for row in results
        }


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
            print(f"\n{i}. {result['title']} (相似度: {result['similarity']:.2f})")
            print(f"   分類: {result['category']}")
            print(f"   內容: {result['content'][:100]}...")

        # 測試關鍵字搜尋
        print("\n\n🔎 測試關鍵字搜尋...")
        results = await engine.search_by_keywords(["退租", "合約"], limit=3)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']} (匹配度: {result['match_score']:.2f})")
            print(f"   匹配關鍵字: {', '.join(result['matched_keywords'])}")

        # 關閉連接池
        await pool.close()

    # 執行測試
    asyncio.run(test_rag_engine())
