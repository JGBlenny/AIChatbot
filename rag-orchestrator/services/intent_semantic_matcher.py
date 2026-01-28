"""
意圖語義匹配服務
根據意圖描述的語義相似度動態計算 intent_boost
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Tuple
import numpy as np

# 動態導入，支持直接運行和模組導入
try:
    from .embedding_utils import get_embedding_client
    from .db_utils import get_db_config
except ImportError:
    from embedding_utils import get_embedding_client
    from db_utils import get_db_config


class IntentSemanticMatcher:
    """意圖語義匹配器"""

    def __init__(self):
        """初始化語義匹配器"""
        self.embedding_client = get_embedding_client()
        self._intent_cache = {}  # 緩存意圖信息 {intent_id: {name, description, embedding}}

    def _get_db_connection(self):
        """建立資料庫連接"""
        db_config = get_db_config()
        return psycopg2.connect(**db_config)

    def _load_intent_info(self, intent_id: int) -> Optional[Dict]:
        """
        載入意圖信息（包含 embedding）

        Args:
            intent_id: 意圖 ID

        Returns:
            意圖信息字典，如果不存在則返回 None
        """
        # 檢查緩存
        if intent_id in self._intent_cache:
            return self._intent_cache[intent_id]

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, name, description, embedding
                FROM intents
                WHERE id = %s AND is_enabled = true
            """, (intent_id,))

            row = cursor.fetchone()
            cursor.close()

            if row:
                intent_info = dict(row)
                # 將 embedding 從字符串轉換為列表（如果是字符串）
                if intent_info.get('embedding') and isinstance(intent_info['embedding'], str):
                    # pgvector 返回的是字符串格式 '[0.1, 0.2, ...]'
                    embedding_str = intent_info['embedding'].strip('[]')
                    intent_info['embedding'] = [float(x) for x in embedding_str.split(',')]
                # 緩存結果
                self._intent_cache[intent_id] = intent_info
                return intent_info

            return None

        finally:
            conn.close()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        計算兩個向量的余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度（0-1）
        """
        if vec1 is None or vec2 is None:
            return 0.0

        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)

        # 計算余弦相似度
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # 確保在 0-1 範圍內
        return max(0.0, min(1.0, similarity))

    def calculate_semantic_boost(
        self,
        query_intent_id: int,
        knowledge_intent_id: int,
        intent_type: Optional[str] = None
    ) -> Tuple[float, str, float]:
        """
        基於語義相似度計算 intent_boost

        Args:
            query_intent_id: 問題的意圖 ID
            knowledge_intent_id: 知識的意圖 ID
            intent_type: 知識的意圖類型（primary/secondary）

        Returns:
            (boost 值, 計算原因, 語義相似度)
        """
        # 1. 精確匹配：直接返回預設 boost（階段 1：降低加成）
        if query_intent_id == knowledge_intent_id:
            if intent_type == 'primary':
                return 1.1, "精確匹配（主要意圖）", 1.0  # 從 1.3 降到 1.1
            elif intent_type == 'secondary':
                return 1.05, "精確匹配（次要意圖）", 1.0  # 從 1.15 降到 1.05
            else:
                return 1.1, "精確匹配", 1.0  # 從 1.3 降到 1.1

        # 2. 載入兩個意圖的信息
        query_intent = self._load_intent_info(query_intent_id)
        knowledge_intent = self._load_intent_info(knowledge_intent_id)

        # 3. 如果任一意圖沒有 embedding，返回默認值
        if not query_intent or not knowledge_intent:
            return 1.0, "缺少意圖信息，無法計算語義相似度", 0.0

        if query_intent.get('embedding') is None or knowledge_intent.get('embedding') is None:
            return 1.0, "意圖尚未生成 embedding，使用默認 boost", 0.0

        # 4. 計算語義相似度
        similarity = self._cosine_similarity(
            query_intent['embedding'],
            knowledge_intent['embedding']
        )

        # 5. 根據相似度映射到 boost 值（階段 1：降低加成）
        # 相似度閾值參考：
        # >= 0.85: 高度相關 -> 1.1x（階段 1：從 1.3 降到 1.1）
        # >= 0.70: 強相關 -> 1.08x（階段 1：從 1.2 降到 1.08）
        # >= 0.55: 中度相關 -> 1.05x（階段 1：從 1.1 降到 1.05）
        # >= 0.40: 弱相關 -> 1.02x（階段 1：從 1.05 降到 1.02）
        # < 0.40: 不相關 -> 1.0x

        if similarity >= 0.85:
            boost = 1.1  # 從 1.3 降到 1.1
            reason = f"高度語義相關（相似度: {similarity:.3f}）"
        elif similarity >= 0.70:
            boost = 1.08  # 從 1.2 降到 1.08
            reason = f"強語義相關（相似度: {similarity:.3f}）"
        elif similarity >= 0.55:
            boost = 1.05  # 從 1.1 降到 1.05
            reason = f"中度語義相關（相似度: {similarity:.3f}）"
        elif similarity >= 0.40:
            boost = 1.02  # 從 1.05 降到 1.02
            reason = f"弱語義相關（相似度: {similarity:.3f}）"
        else:
            boost = 1.0
            reason = f"語義不相關（相似度: {similarity:.3f}）"

        return boost, reason, similarity

    def batch_calculate_boosts(
        self,
        query_intent_id: int,
        knowledge_intents: List[Dict]
    ) -> Dict[int, Dict]:
        """
        批量計算多個知識的 intent_boost

        Args:
            query_intent_id: 問題的意圖 ID
            knowledge_intents: 知識意圖列表
                [
                    {'intent_id': 15, 'intent_type': 'primary'},
                    {'intent_id': 9, 'intent_type': 'secondary'},
                    ...
                ]

        Returns:
            意圖 boost 字典 {intent_id: {'boost': 1.2, 'reason': '...'}}
        """
        results = {}

        for item in knowledge_intents:
            intent_id = item.get('intent_id')
            intent_type = item.get('intent_type')

            if intent_id is None:
                continue

            boost, reason = self.calculate_semantic_boost(
                query_intent_id,
                intent_id,
                intent_type
            )

            results[intent_id] = {
                'boost': boost,
                'reason': reason
            }

        return results

    async def generate_and_save_intent_embeddings(self) -> Dict:
        """
        為所有意圖生成並保存 embedding

        Returns:
            統計信息 {'total': 38, 'success': 38, 'skipped': 0, 'failed': 0}
        """
        conn = self._get_db_connection()
        stats = {'total': 0, 'success': 0, 'skipped': 0, 'failed': 0}

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 1. 獲取所有啟用的意圖
            cursor.execute("""
                SELECT id, name, description, embedding
                FROM intents
                WHERE is_enabled = true
                ORDER BY id
            """)

            intents = cursor.fetchall()
            stats['total'] = len(intents)

            print(f"\n🔄 開始為 {stats['total']} 個意圖生成 embedding...")

            for intent in intents:
                intent_id = intent['id']
                intent_name = intent['name']
                description = intent['description']
                existing_embedding = intent['embedding']

                # 如果已有 embedding，跳過
                if existing_embedding is not None:
                    print(f"   ⏭️  意圖 {intent_id} ({intent_name}) 已有 embedding，跳過")
                    stats['skipped'] += 1
                    continue

                # 如果沒有描述，使用意圖名稱
                if not description:
                    description = f"關於{intent_name}的問題"
                    print(f"   ⚠️  意圖 {intent_id} ({intent_name}) 無描述，使用名稱生成")

                # 2. 生成 embedding
                try:
                    embedding = await self.embedding_client.get_embedding(
                        description,
                        verbose=False
                    )

                    if embedding is None:
                        print(f"   ❌ 意圖 {intent_id} ({intent_name}) embedding 生成失敗")
                        stats['failed'] += 1
                        continue

                    # 3. 保存到數據庫
                    update_cursor = conn.cursor()
                    update_cursor.execute("""
                        UPDATE intents
                        SET embedding = %s::vector,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (str(embedding), intent_id))
                    update_cursor.close()
                    conn.commit()

                    print(f"   ✅ 意圖 {intent_id} ({intent_name}) embedding 已生成並保存")
                    stats['success'] += 1

                    # 清除緩存
                    if intent_id in self._intent_cache:
                        del self._intent_cache[intent_id]

                except Exception as e:
                    print(f"   ❌ 意圖 {intent_id} ({intent_name}) 處理失敗: {str(e)}")
                    stats['failed'] += 1
                    continue

            cursor.close()

            print(f"\n📊 Embedding 生成完成:")
            print(f"   總計: {stats['total']}")
            print(f"   成功: {stats['success']}")
            print(f"   跳過: {stats['skipped']}")
            print(f"   失敗: {stats['failed']}")

            return stats

        except Exception as e:
            print(f"❌ 生成意圖 embedding 時發生錯誤: {str(e)}")
            raise
        finally:
            conn.close()

    def clear_cache(self):
        """清除意圖緩存"""
        self._intent_cache = {}


# 全局單例
_intent_semantic_matcher = None


def get_intent_semantic_matcher() -> IntentSemanticMatcher:
    """獲取意圖語義匹配器單例"""
    global _intent_semantic_matcher
    if _intent_semantic_matcher is None:
        _intent_semantic_matcher = IntentSemanticMatcher()
    return _intent_semantic_matcher


# 測試用例
if __name__ == "__main__":
    import asyncio

    async def test_semantic_matching():
        matcher = get_intent_semantic_matcher()

        # 測試1：生成所有意圖的 embedding
        print("=" * 60)
        print("測試1：生成意圖 embedding")
        print("=" * 60)
        stats = await matcher.generate_and_save_intent_embeddings()

        # 測試2：計算語義相似度
        print("\n" + "=" * 60)
        print("測試2：計算意圖語義相似度")
        print("=" * 60)

        # 假設：問題被分類為"押金/退款" (ID: 15)
        query_intent_id = 15

        # 測試與不同意圖的相似度
        test_intents = [
            {'intent_id': 15, 'intent_type': 'primary'},   # 押金/退款（自己）
            {'intent_id': 9, 'intent_type': 'primary'},    # 租約變更/轉租
            {'intent_id': 2, 'intent_type': 'primary'},    # 退租流程
            {'intent_id': 13, 'intent_type': 'primary'},   # 租金繳納
            {'intent_id': 3, 'intent_type': 'primary'},    # 報修問題
        ]

        for item in test_intents:
            boost, reason = matcher.calculate_semantic_boost(
                query_intent_id,
                item['intent_id'],
                item['intent_type']
            )
            print(f"   意圖 {item['intent_id']}: boost={boost:.2f}x - {reason}")

    asyncio.run(test_semantic_matching())
