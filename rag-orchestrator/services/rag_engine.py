"""
RAG 檢索引擎
負責向量相似度搜尋，從知識庫中檢索相關內容
"""
import os
import httpx
from typing import List, Dict, Optional
import asyncpg
from asyncpg.pool import Pool


class RAGEngine:
    """RAG 檢索引擎"""

    def __init__(self, db_pool: Pool):
        """
        初始化 RAG 引擎

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        self.embedding_api_url = os.getenv(
            "EMBEDDING_API_URL",
            "http://embedding-api:5000/api/v1/embeddings"
        )

    async def search(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        搜尋相關知識

        Args:
            query: 查詢問題
            limit: 返回結果數量
            similarity_threshold: 相似度閾值

        Returns:
            檢索結果列表，每個結果包含:
            - id: 知識 ID
            - title: 標題
            - content: 內容
            - category: 分類
            - similarity: 相似度分數 (0-1)
        """
        # 1. 將問題轉換為向量
        query_embedding = await self._get_embedding(query)

        if not query_embedding:
            return []

        # 2. 向量相似度搜尋
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT
                    id,
                    title,
                    answer as content,
                    category,
                    audience,
                    keywords,
                    1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                WHERE embedding IS NOT NULL
                    AND (1 - (embedding <=> $1::vector)) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, query_embedding, similarity_threshold, limit)

        # 3. 格式化結果
        search_results = []
        for row in results:
            search_results.append({
                "id": row['id'],
                "title": row['title'],
                "content": row['content'],
                "category": row['category'],
                "audience": row.get('audience'),
                "keywords": row.get('keywords', []),
                "similarity": float(row['similarity'])
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
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.embedding_api_url,
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                return data['embedding']
        except Exception as e:
            print(f"❌ Embedding API 呼叫失敗: {e}")
            return None

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
