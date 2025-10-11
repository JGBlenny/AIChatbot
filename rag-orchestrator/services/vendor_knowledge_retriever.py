"""
業者知識檢索服務
根據業者 ID 和意圖檢索知識，自動處理模板變數替換
"""
import os
import httpx
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional
from .vendor_parameter_resolver import VendorParameterResolver


class VendorKnowledgeRetriever:
    """業者知識檢索器"""

    def __init__(self):
        """初始化知識檢索器"""
        # 資料庫配置
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin')
        }

        # Embedding API 配置
        self.embedding_api_url = os.getenv(
            "EMBEDDING_API_URL",
            "http://embedding-api:5000/api/v1/embeddings"
        )

        # 參數解析器
        self.param_resolver = VendorParameterResolver()

    def _get_db_connection(self):
        """建立資料庫連接"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database']
        )

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
            resolve_templates: 是否自動解析模板

        Returns:
            知識列表，按優先級排序
            [
                {
                    "id": 1,
                    "question_summary": "每月繳費日期",
                    "answer": "您的租金繳費日為每月 1 號...",  # 已解析
                    "original_answer": "您的租金繳費日為每月 {{payment_day}} 號...",  # 原始模板
                    "scope": "global",
                    "priority": 1,
                    "is_template": true
                }
            ]
        """
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
                    kb.created_at,
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
                ORDER BY
                    scope_weight DESC,  -- 先按範圍權重排序
                    kb.priority DESC,   -- 再按優先級排序
                    kb.created_at DESC  -- 最後按建立時間排序
                LIMIT %s
            """, (vendor_id, vendor_id, intent_id, vendor_id, top_k))

            rows = cursor.fetchall()
            cursor.close()

            # 處理結果
            results = []
            for row in rows:
                knowledge = dict(row)

                # 保留原始答案
                knowledge['original_answer'] = knowledge['answer']

                # 如果是模板且需要解析，自動替換變數
                if resolve_templates and knowledge['is_template']:
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        # 同時解析問題摘要中的變數
                        if knowledge['question_summary']:
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
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.embedding_api_url,
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get('embedding')
        except Exception as e:
            print(f"❌ Embedding API 呼叫失敗: {e}")
            return None

    async def retrieve_knowledge_hybrid(
        self,
        query: str,
        intent_id: int,
        vendor_id: int,
        top_k: int = 3,
        similarity_threshold: float = 0.6,
        resolve_templates: bool = True,
        all_intent_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        混合模式檢索：Intent 過濾 + 向量相似度排序

        這是推薦的檢索方法，結合了分類準確性和語義理解能力：
        1. 先根據 intent_id(s) 過濾出相關類別的知識
        2. 再使用向量相似度排序，找出最相關的答案
        3. 考慮 scope 優先級（customized > vendor > global）
        4. 支援多 Intent 檢索（主要 Intent 獲得 1.5x boost，次要 Intent 獲得 1.2x boost）

        Args:
            query: 使用者問題
            intent_id: 主要意圖 ID
            vendor_id: 業者 ID
            top_k: 返回前 K 筆知識
            similarity_threshold: 相似度閾值
            resolve_templates: 是否自動解析模板
            all_intent_ids: 所有相關意圖 IDs（包含主要和次要）

        Returns:
            知識列表，按相似度和優先級排序
        """
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
                    kb.created_at,
                    kim.intent_id,
                    -- 計算向量相似度
                    1 - (kb.embedding <=> %s::vector) as base_similarity,
                    -- Intent 匹配加成（多 Intent 支援）
                    CASE
                        WHEN kim.intent_id = %s THEN 1.5          -- 主要 Intent: 1.5x boost
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.2  -- 次要 Intent: 1.2x boost
                        ELSE 1.0                              -- 其他: 無加成
                    END as intent_boost,
                    -- 加成後的相似度 (用於排序)
                    (1 - (kb.embedding <=> %s::vector)) *
                    CASE
                        WHEN kim.intent_id = %s THEN 1.5
                        WHEN kim.intent_id = ANY(%s::int[]) THEN 1.2
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
                    -- 移除硬性 Intent 過濾，改為軟性權重
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
                ORDER BY
                    scope_weight DESC,        -- 1st: Scope 優先級
                    boosted_similarity DESC,  -- 2nd: 加成後的相似度
                    kb.priority DESC          -- 3rd: 人工優先級
                LIMIT %s
            """, (
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
                top_k
            ))

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

                print(f"   {idx}. {intent_marker} ID {knowledge['id']}: {knowledge['question_summary'][:40]}... "
                      f"(原始: {knowledge['base_similarity']:.3f}, "
                      f"boost: {knowledge['intent_boost']:.1f}x, "
                      f"加成後: {knowledge['boosted_similarity']:.3f}, "
                      f"intent: {knowledge['intent_id']})")

                # 保留原始答案
                knowledge['original_answer'] = knowledge['answer']

                # 如果是模板且需要解析，自動替換變數
                if resolve_templates and knowledge['is_template']:
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        if knowledge['question_summary']:
                            knowledge['question_summary'] = self.param_resolver.resolve_template(
                                knowledge['question_summary'],
                                vendor_id
                            )
                    except Exception as e:
                        print(f"⚠️  Template resolution failed for knowledge {knowledge['id']}: {e}")

                # 移除內部欄位，並將 base_similarity 作為標準 similarity
                knowledge['similarity'] = knowledge['base_similarity']
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

                # 自動解析模板
                if knowledge['is_template']:
                    try:
                        knowledge['answer'] = self.param_resolver.resolve_template(
                            knowledge['answer'],
                            vendor_id
                        )
                        if knowledge['question_summary']:
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

            if not knowledge['is_template']:
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
                ) if knowledge['question_summary'] else None,
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
