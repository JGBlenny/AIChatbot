"""
未釐清問題管理服務
負責記錄、查詢和管理低信心度的未釐清問題

增強功能（Migration 34）：
- 組合策略：語義相似度 ≥ 0.80 OR 編輯距離 ≤ 2
- 拼音檢測：處理嚴重同音錯誤（語義 0.60-0.80 + 拼音相似度 ≥ 0.80）
"""
from typing import List, Dict, Optional
from datetime import datetime
from asyncpg.pool import Pool
import json
import os
from pypinyin import lazy_pinyin
from .embedding_utils import get_embedding_client


class UnclearQuestionManager:
    """未釐清問題管理器"""

    def __init__(self, db_pool: Pool):
        """
        初始化管理器

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        # 使用共用的 embedding 客戶端
        self.embedding_client = get_embedding_client()

    async def record_unclear_question(
        self,
        question: str,
        user_id: Optional[str] = None,
        intent_type: Optional[str] = None,
        similarity_score: Optional[float] = None,
        retrieved_docs: Optional[Dict] = None,
        semantic_similarity_threshold: float = 0.80,
        pinyin_similarity_threshold: float = 0.80
    ) -> int:
        """
        記錄未釐清問題（使用多層檢測去重）

        如果相同或相似的問題已存在，則更新頻率和最後詢問時間

        檢測策略（三層）：
        1. 精確匹配
        2. 組合檢測：語義相似度 ≥ 0.80 OR 編輯距離 ≤ 2
        3. 拼音檢測：語義 0.60-0.80 + 拼音相似度 ≥ 0.80（針對嚴重同音錯誤）

        Args:
            question: 問題內容
            user_id: 使用者 ID
            intent_type: 意圖類型
            similarity_score: 相似度分數
            retrieved_docs: 檢索到的文件
            semantic_similarity_threshold: 語義相似度閾值 (default: 0.80)
            pinyin_similarity_threshold: 拼音相似度閾值 (default: 0.80)

        Returns:
            問題 ID
        """
        # 1. 生成問題的向量表示
        question_embedding = await self._get_embedding(question)

        if not question_embedding:
            print(f"⚠️  無法生成問題向量，回退到精確匹配模式")
            # Fallback to exact match if embedding fails
            return await self._record_without_semantics(
                question, user_id, intent_type, similarity_score, retrieved_docs
            )

        # 2. 使用資料庫函數進行語義去重
        async with self.db_pool.acquire() as conn:
            # 將 embedding 轉換為 PostgreSQL vector 格式
            # question_embedding is a list of floats, convert to [x,y,z,...] format
            vector_str = '[' + ','.join(str(x) for x in question_embedding) + ']'

            # 序列化 retrieved_docs 為 JSON 字符串
            retrieved_docs_json = json.dumps(retrieved_docs) if retrieved_docs else None

            # 呼叫資料庫函數進行語義去重
            result = await conn.fetchrow("""
                SELECT * FROM record_unclear_question_with_semantics(
                    $1::TEXT,
                    $2::vector,
                    $3::VARCHAR(100),
                    $4::DECIMAL
                )
            """, question, vector_str, intent_type, semantic_similarity_threshold)

            unclear_question_id = result['unclear_question_id']
            is_new = result['is_new_question']
            matched_question = result['matched_similar_question']
            sim_score = result['sim_score']
            frequency = result['current_frequency']

            # 3. 如果是新問題，嘗試拼音檢測（針對嚴重同音錯誤）
            if is_new:
                print(f"🔍 新問題建立，檢查拼音相似度...")

                # 查詢所有現有問題進行拼音比對
                pinyin_candidates = await conn.fetch("""
                    SELECT
                        id,
                        question,
                        question_embedding,
                        frequency
                    FROM unclear_questions
                    WHERE id != $1
                        AND status != 'resolved'
                        AND question_embedding IS NOT NULL
                    ORDER BY frequency DESC
                    LIMIT 100
                """, unclear_question_id)

                best_pinyin_match = None
                best_pinyin_score = 0.0
                best_semantic_score = 0.0

                for candidate in pinyin_candidates:
                    # 計算拼音相似度
                    pinyin_sim = self._pinyin_similarity(question, candidate['question'])

                    # 計算語義相似度
                    # PostgreSQL pgvector 返回的是字符串格式 "[0.1,0.2,...]"
                    if candidate['question_embedding'] is not None:
                        try:
                            # asyncpg 返回 pgvector 為字符串，需要解析
                            emb_str = candidate['question_embedding']
                            if isinstance(emb_str, str):
                                # 移除首尾的方括號並按逗號分割
                                candidate_emb = [float(x) for x in emb_str.strip('[]').split(',')]
                            elif isinstance(emb_str, (list, tuple)):
                                # 如果已經是列表（某些情況下可能）
                                candidate_emb = [float(x) for x in emb_str]
                            else:
                                # 無法識別的格式，跳過
                                continue
                        except (TypeError, ValueError) as e:
                            # 如果轉換失敗，跳過此候選項
                            print(f"⚠️  向量轉換失敗 (ID: {candidate['id']}): {e}")
                            continue
                    else:
                        continue

                    semantic_sim = self._cosine_similarity(question_embedding, candidate_emb)

                    # 檢查是否符合拼音檢測條件：
                    # 語義相似度在 0.60-0.80 之間 AND 拼音相似度 >= 閾值
                    if (0.60 <= semantic_sim < semantic_similarity_threshold and
                        pinyin_sim >= pinyin_similarity_threshold):

                        if pinyin_sim > best_pinyin_score:
                            best_pinyin_match = candidate
                            best_pinyin_score = pinyin_sim
                            best_semantic_score = semantic_sim

                # 如果找到拼音匹配，合併到該問題
                if best_pinyin_match:
                    print(f"🎯 拼音檢測命中！")
                    print(f"   新問題: {question}")
                    print(f"   匹配問題: {best_pinyin_match['question']}")
                    print(f"   語義相似度: {best_semantic_score:.4f}")
                    print(f"   拼音相似度: {best_pinyin_score:.4f}")

                    # 刪除剛建立的新問題
                    await conn.execute("""
                        DELETE FROM unclear_questions WHERE id = $1
                    """, unclear_question_id)

                    # 更新匹配問題的頻率
                    await conn.execute("""
                        UPDATE unclear_questions
                        SET frequency = frequency + 1,
                            last_asked_at = NOW()
                        WHERE id = $1
                    """, best_pinyin_match['id'])

                    # 返回匹配問題的 ID
                    return best_pinyin_match['id']
                else:
                    print(f"✅ 記錄新的未釐清問題 (ID: {unclear_question_id}): {question}")
            elif matched_question == question:
                print(f"♻️  精確匹配已存在問題 (ID: {unclear_question_id}), 頻率: {frequency}")
            else:
                print(f"🔗 語義/編輯距離匹配已存在問題 (ID: {unclear_question_id})")
                print(f"   新問題: {question}")
                print(f"   相似問題: {matched_question}")
                print(f"   相似度: {sim_score:.4f}, 頻率: {frequency}")

            return unclear_question_id

    async def _record_without_semantics(
        self,
        question: str,
        user_id: Optional[str] = None,
        intent_type: Optional[str] = None,
        similarity_score: Optional[float] = None,
        retrieved_docs: Optional[Dict] = None
    ) -> int:
        """
        不使用語義相似度記錄問題（回退方案）

        僅進行精確文字匹配
        """
        async with self.db_pool.acquire() as conn:
            # 檢查是否已存在相同問題
            existing = await conn.fetchrow("""
                SELECT id, frequency
                FROM unclear_questions
                WHERE question = $1
                    AND status != 'resolved'
            """, question)

            if existing:
                # 更新頻率和最後詢問時間
                await conn.execute("""
                    UPDATE unclear_questions
                    SET frequency = frequency + 1,
                        last_asked_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, existing['id'])
                return existing['id']
            else:
                # 建立新記錄
                # 序列化 retrieved_docs 為 JSON 字符串
                retrieved_docs_json = json.dumps(retrieved_docs) if retrieved_docs else None

                # Use explicit column values to avoid ambiguity
                sim_score_value = similarity_score

                row = await conn.fetchrow("""
                    INSERT INTO unclear_questions (
                        question,
                        user_id,
                        intent_type,
                        similarity_score,
                        retrieved_docs,
                        status
                    ) VALUES ($1, $2, $3, $4::double precision, $5, 'pending')
                    RETURNING id
                """, question, user_id, intent_type, sim_score_value, retrieved_docs_json)
                return row['id']

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        呼叫 Embedding API 將文字轉換為向量

        Args:
            text: 要轉換的文字

        Returns:
            向量列表，如果失敗則返回 None
        """
        # 使用共用的 embedding 客戶端
        embedding = await self.embedding_client.get_embedding(text, verbose=False)

        if embedding:
            print(f"   ✅ 獲得問題向量: 維度 {len(embedding)}")

        return embedding

    def _pinyin_similarity(self, text1: str, text2: str) -> float:
        """
        計算拼音相似度（用於檢測嚴重同音錯誤）

        使用 Levenshtein 距離比較拼音字符串的相似度

        Args:
            text1: 第一個文字
            text2: 第二個文字

        Returns:
            拼音相似度分數 (0.0-1.0)
        """
        # 轉換為拼音（不帶音調）
        pinyin1 = ''.join(lazy_pinyin(text1))
        pinyin2 = ''.join(lazy_pinyin(text2))

        # 使用編輯距離計算相似度
        max_len = max(len(pinyin1), len(pinyin2))
        if max_len == 0:
            return 1.0

        # 簡單的編輯距離實現
        edit_dist = self._levenshtein_distance(pinyin1, pinyin2)

        # 轉換為相似度分數 (0.0-1.0)
        similarity = 1.0 - (edit_dist / max_len)

        return similarity

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        計算 Levenshtein 編輯距離

        Args:
            s1: 第一個字符串
            s2: 第二個字符串

        Returns:
            編輯距離
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        計算兩個向量的餘弦相似度

        Args:
            vec1: 第一個向量
            vec2: 第二個向量

        Returns:
            餘弦相似度 (0.0-1.0)
        """
        import numpy as np

        # 確保向量是 numpy 陣列
        try:
            v1 = np.array(vec1, dtype=float)
            v2 = np.array(vec2, dtype=float)
        except (TypeError, ValueError) as e:
            print(f"⚠️  向量轉換錯誤: {e}")
            print(f"   vec1 type: {type(vec1)}, vec2 type: {type(vec2)}")
            return 0.0

        # 計算點積
        dot_product = np.dot(v1, v2)

        # 計算向量長度
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        # 避免除以零
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def get_unclear_questions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "frequency"
    ) -> List[Dict]:
        """
        取得未釐清問題列表

        Args:
            status: 狀態篩選 (pending/in_progress/resolved/ignored)
            limit: 返回數量
            offset: 偏移量
            order_by: 排序欄位 (frequency/last_asked_at/created_at)

        Returns:
            問題列表
        """
        # 驗證排序欄位
        valid_order_fields = ['frequency', 'last_asked_at', 'created_at']
        if order_by not in valid_order_fields:
            order_by = 'frequency'

        async with self.db_pool.acquire() as conn:
            query = f"""
                SELECT
                    id,
                    question,
                    user_id,
                    intent_type,
                    similarity_score,
                    retrieved_docs,
                    frequency,
                    first_asked_at,
                    last_asked_at,
                    status,
                    assigned_to,
                    resolved_at,
                    resolution_note,
                    suggested_answers,
                    created_at,
                    updated_at
                FROM unclear_questions
                WHERE ($1::text IS NULL OR status = $1)
                ORDER BY {order_by} DESC
                LIMIT $2 OFFSET $3
            """

            results = await conn.fetch(query, status, limit, offset)

        return [dict(row) for row in results]

    async def get_unclear_question_by_id(self, question_id: int) -> Optional[Dict]:
        """
        根據 ID 取得未釐清問題

        Args:
            question_id: 問題 ID

        Returns:
            問題資料，如果找不到則返回 None
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id,
                    question,
                    user_id,
                    intent_type,
                    similarity_score,
                    retrieved_docs,
                    frequency,
                    first_asked_at,
                    last_asked_at,
                    status,
                    assigned_to,
                    resolved_at,
                    resolution_note,
                    suggested_answers,
                    created_at,
                    updated_at
                FROM unclear_questions
                WHERE id = $1
            """, question_id)

            return dict(row) if row else None

    async def update_unclear_question(
        self,
        question_id: int,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        resolution_note: Optional[str] = None,
        suggested_answers: Optional[List[str]] = None
    ) -> bool:
        """
        更新未釐清問題

        Args:
            question_id: 問題 ID
            status: 新狀態
            assigned_to: 指派給誰
            resolution_note: 解決說明
            suggested_answers: 建議答案

        Returns:
            是否更新成功
        """
        updates = []
        params = []
        param_count = 1

        if status is not None:
            updates.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

            # 如果狀態改為 resolved，設定 resolved_at
            if status == 'resolved':
                updates.append(f"resolved_at = CURRENT_TIMESTAMP")

        if assigned_to is not None:
            updates.append(f"assigned_to = ${param_count}")
            params.append(assigned_to)
            param_count += 1

        if resolution_note is not None:
            updates.append(f"resolution_note = ${param_count}")
            params.append(resolution_note)
            param_count += 1

        if suggested_answers is not None:
            updates.append(f"suggested_answers = ${param_count}")
            params.append(suggested_answers)
            param_count += 1

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(question_id)

        async with self.db_pool.acquire() as conn:
            query = f"""
                UPDATE unclear_questions
                SET {', '.join(updates)}
                WHERE id = ${param_count}
            """
            await conn.execute(query, *params)

        return True

    async def delete_unclear_question(self, question_id: int) -> bool:
        """
        刪除未釐清問題

        Args:
            question_id: 問題 ID

        Returns:
            是否刪除成功
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM unclear_questions
                WHERE id = $1
            """, question_id)

            return result != "DELETE 0"

    async def get_stats(self) -> Dict:
        """
        取得統計資訊

        Returns:
            統計資訊字典
        """
        async with self.db_pool.acquire() as conn:
            # 狀態統計
            status_stats = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM unclear_questions
                GROUP BY status
            """)

            stats = {
                "total": 0,
                "pending": 0,
                "in_progress": 0,
                "resolved": 0,
                "ignored": 0
            }

            for row in status_stats:
                stats[row['status']] = row['count']
                stats['total'] += row['count']

            # 最常見的問題 (top 10)
            top_questions = await conn.fetch("""
                SELECT
                    id,
                    question,
                    frequency,
                    status,
                    last_asked_at
                FROM unclear_questions
                WHERE status != 'ignored'
                ORDER BY frequency DESC
                LIMIT 10
            """)

            stats['top_questions'] = [
                {
                    "id": row['id'],
                    "question": row['question'],
                    "frequency": row['frequency'],
                    "status": row['status'],
                    "last_asked_at": row['last_asked_at'].isoformat() if row['last_asked_at'] else None
                }
                for row in top_questions
            ]

            # 平均相似度分數
            avg_score = await conn.fetchval("""
                SELECT AVG(similarity_score)
                FROM unclear_questions
                WHERE similarity_score IS NOT NULL
            """)

            stats['avg_similarity_score'] = float(avg_score) if avg_score else 0.0

        return stats

    async def search_unclear_questions(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        搜尋未釐清問題

        Args:
            keyword: 搜尋關鍵字
            limit: 返回數量

        Returns:
            搜尋結果
        """
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT
                    id,
                    question,
                    frequency,
                    status,
                    last_asked_at
                FROM unclear_questions
                WHERE question ILIKE $1
                ORDER BY frequency DESC
                LIMIT $2
            """, f"%{keyword}%", limit)

        return [dict(row) for row in results]


# 使用範例
if __name__ == "__main__":
    import asyncio
    import asyncpg
    import os

    async def test_unclear_question_manager():
        """測試未釐清問題管理器"""
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

        manager = UnclearQuestionManager(pool)

        # 測試記錄未釐清問題
        print("📝 記錄未釐清問題...")
        q_id = await manager.record_unclear_question(
            question="IOT 門鎖一直嗶嗶叫怎麼辦？",
            user_id="user123",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"   問題 ID: {q_id}")

        # 測試重複問題（應該更新頻率）
        q_id2 = await manager.record_unclear_question(
            question="IOT 門鎖一直嗶嗶叫怎麼辦？",
            user_id="user456",
            intent_type="unclear",
            similarity_score=0.63
        )
        print(f"   重複問題 ID: {q_id2} (應該與上面相同)")

        # 查詢問題
        print("\n🔍 查詢未釐清問題...")
        questions = await manager.get_unclear_questions(status="pending", limit=5)
        for q in questions:
            print(f"   - {q['question']} (頻率: {q['frequency']})")

        # 更新問題狀態
        print("\n✏️ 更新問題狀態...")
        await manager.update_unclear_question(
            question_id=q_id,
            status="in_progress",
            assigned_to="admin",
            resolution_note="正在處理中"
        )
        print("   狀態已更新為 in_progress")

        # 取得統計
        print("\n📊 統計資訊...")
        stats = await manager.get_stats()
        print(f"   總數: {stats['total']}")
        print(f"   待處理: {stats['pending']}")
        print(f"   處理中: {stats['in_progress']}")
        print(f"   已解決: {stats['resolved']}")
        print(f"   平均相似度: {stats['avg_similarity_score']:.2f}")

        # 關閉連接池
        await pool.close()

    # 執行測試
    asyncio.run(test_unclear_question_manager())
