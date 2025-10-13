"""
知識庫自動分類服務
整合 IntentClassifier 自動為知識庫內容分配意圖
"""
import os
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .intent_classifier import IntentClassifier
from .db_utils import get_db_config


class KnowledgeClassifier:
    """知識庫自動分類器"""

    def __init__(self):
        """初始化知識庫分類器"""
        # 初始化意圖分類器
        self.intent_classifier = IntentClassifier(use_database=True)

    def _get_db_connection(self):
        """建立資料庫連接（使用共用配置）"""
        db_config = get_db_config()
        return psycopg2.connect(**db_config)

    def _get_intent_id_by_name(self, intent_name: str, cursor) -> Optional[int]:
        """根據意圖名稱查詢意圖 ID"""
        cursor.execute(
            "SELECT id FROM intents WHERE name = %s AND is_enabled = true",
            (intent_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def classify_single_knowledge(
        self,
        knowledge_id: int,
        question_summary: str,
        answer: str,
        assigned_by: str = 'auto'
    ) -> Dict:
        """
        分類單一知識條目（支援多意圖分配）

        Args:
            knowledge_id: 知識庫 ID
            question_summary: 問題摘要
            answer: 答案內容
            assigned_by: 分配方式 (auto/manual)

        Returns:
            分類結果，包含主要意圖和次要意圖資訊
        """
        # 使用問題摘要或答案的前段進行分類
        content_to_classify = question_summary or answer[:500]

        # 使用 IntentClassifier 進行分類（支援多意圖）
        classification = self.intent_classifier.classify(content_to_classify)

        # 如果分類為 unclear，設置 intent_id = NULL，並清除 mapping
        if classification['intent_name'] == 'unclear':
            conn = self._get_db_connection()
            try:
                cursor = conn.cursor()

                # 將 intent_id 設為 NULL，表示未分類
                cursor.execute("""
                    UPDATE knowledge_base
                    SET intent_id = NULL,
                        intent_confidence = %s,
                        intent_assigned_by = %s,
                        intent_classified_at = CURRENT_TIMESTAMP,
                        needs_reclassify = false
                    WHERE id = %s
                """, (classification['confidence'], assigned_by, knowledge_id))

                # 清除 knowledge_intent_mapping
                cursor.execute("""
                    DELETE FROM knowledge_intent_mapping
                    WHERE knowledge_id = %s
                """, (knowledge_id,))

                conn.commit()
                cursor.close()

                return {
                    'knowledge_id': knowledge_id,
                    'classified': False,
                    'intent_name': 'unclear',
                    'intent_id': None,
                    'confidence': classification['confidence'],
                    'all_intents': [],
                    'secondary_intents': [],
                    'reason': 'Low confidence or unclear intent - set to NULL'
                }
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        # 更新資料庫（支援多意圖）
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor()

            # 獲取主要意圖 ID
            primary_intent_id = self._get_intent_id_by_name(classification['intent_name'], cursor)

            if not primary_intent_id:
                return {
                    'knowledge_id': knowledge_id,
                    'classified': False,
                    'intent_name': classification['intent_name'],
                    'confidence': classification['confidence'],
                    'all_intents': classification.get('all_intents', []),
                    'secondary_intents': classification.get('secondary_intents', []),
                    'reason': 'Primary intent not found in database'
                }

            # 獲取所有意圖的 IDs（主要 + 次要）
            all_intent_ids = classification.get('intent_ids', [primary_intent_id])
            if primary_intent_id not in all_intent_ids:
                all_intent_ids.insert(0, primary_intent_id)

            print(f"\n🔍 [Knowledge Classifier] 知識 ID {knowledge_id} 分類結果:")
            print(f"   主要意圖: {classification['intent_name']} (ID: {primary_intent_id})")
            print(f"   次要意圖: {classification.get('secondary_intents', [])}")
            print(f"   所有意圖 IDs: {all_intent_ids}")
            print(f"   信心度: {classification['confidence']:.2f}")

            # 1. 更新 knowledge_base 主要意圖
            cursor.execute("""
                UPDATE knowledge_base
                SET intent_id = %s,
                    intent_confidence = %s,
                    intent_assigned_by = %s,
                    intent_classified_at = CURRENT_TIMESTAMP,
                    needs_reclassify = false
                WHERE id = %s
            """, (primary_intent_id, classification['confidence'], assigned_by, knowledge_id))

            # 2. 清除舊的 knowledge_intent_mapping 記錄
            cursor.execute("""
                DELETE FROM knowledge_intent_mapping
                WHERE knowledge_id = %s
            """, (knowledge_id,))

            # 3. 插入新的 knowledge_intent_mapping 記錄
            for i, intent_id in enumerate(all_intent_ids):
                intent_type = 'primary' if i == 0 else 'secondary'  # 第一個是主要意圖
                cursor.execute("""
                    INSERT INTO knowledge_intent_mapping (knowledge_id, intent_id, intent_type, assigned_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (knowledge_id, intent_id)
                    DO UPDATE SET intent_type = EXCLUDED.intent_type,
                                  assigned_by = EXCLUDED.assigned_by,
                                  updated_at = CURRENT_TIMESTAMP
                """, (knowledge_id, intent_id, intent_type, assigned_by))

            # 4. 更新所有相關意圖的 knowledge_count
            cursor.execute("""
                UPDATE intents
                SET knowledge_count = (
                    SELECT COUNT(*) FROM knowledge_base WHERE intent_id = intents.id
                )
                WHERE id = ANY(%s)
            """, (all_intent_ids,))

            conn.commit()
            cursor.close()

            return {
                'knowledge_id': knowledge_id,
                'classified': True,
                'intent_id': primary_intent_id,
                'intent_name': classification['intent_name'],
                'intent_type': classification['intent_type'],
                'confidence': classification['confidence'],
                'keywords': classification.get('keywords', []),
                'all_intents': classification.get('all_intents', [classification['intent_name']]),
                'secondary_intents': classification.get('secondary_intents', []),
                'all_intent_ids': all_intent_ids
            }

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def classify_batch(
        self,
        filters: Optional[Dict] = None,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> Dict:
        """
        批次分類知識庫

        Args:
            filters: 過濾條件
                - unclassified: 只處理未分類的知識 (intent_id IS NULL)
                - intent_ids: 只重新分類這些意圖的知識
                - max_confidence: 只重新分類信心度 < 此值的知識
                - assigned_by: 只重新分類特定分配方式 (auto/manual)
                - older_than_days: 只重新分類 N 天前的知識
                - needs_reclassify: 只處理標記為需要重新分類的
            batch_size: 每批處理數量
            dry_run: 是否為預覽模式（不實際更新）

        Returns:
            處理結果統計
        """
        conn = self._get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 構建查詢條件
            where_clauses = []
            params = []

            if filters:
                # 未分類過濾器：只選擇 intent_id 為 NULL 的知識
                if filters.get('unclassified'):
                    where_clauses.append("intent_id IS NULL")

                if filters.get('intent_ids'):
                    where_clauses.append("intent_id = ANY(%s)")
                    params.append(filters['intent_ids'])

                if filters.get('max_confidence'):
                    where_clauses.append("(intent_confidence IS NULL OR intent_confidence < %s)")
                    params.append(filters['max_confidence'])

                if filters.get('assigned_by'):
                    where_clauses.append("intent_assigned_by = %s")
                    params.append(filters['assigned_by'])

                if filters.get('older_than_days'):
                    where_clauses.append(
                        "(intent_classified_at IS NULL OR intent_classified_at < NOW() - INTERVAL '%s days')"
                    )
                    params.append(filters['older_than_days'])

                if filters.get('needs_reclassify'):
                    where_clauses.append("needs_reclassify = true")

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 獲取符合條件的知識數量
            cursor.execute(
                f"SELECT COUNT(*) as total FROM knowledge_base WHERE {where_clause}",
                params
            )
            total_count = cursor.fetchone()['total']

            if dry_run:
                # 預覽模式：返回統計 + 知識列表（限制數量避免大數據問題）
                preview_limit = 50  # 只返回前 50 筆作為示例

                cursor.execute(f"""
                    SELECT
                        id,
                        question_summary,
                        answer,
                        intent_id,
                        intent_confidence,
                        intent_assigned_by,
                        intent_classified_at
                    FROM knowledge_base
                    WHERE {where_clause}
                    ORDER BY intent_classified_at DESC NULLS FIRST
                    LIMIT %s
                """, params + [preview_limit])

                preview_items = cursor.fetchall()

                # 獲取意圖名稱
                preview_list = []
                for item in preview_items:
                    intent_name = None
                    if item['intent_id']:
                        cursor.execute(
                            "SELECT name FROM intents WHERE id = %s",
                            (item['intent_id'],)
                        )
                        intent_result = cursor.fetchone()
                        if intent_result:
                            intent_name = intent_result['name']

                    preview_list.append({
                        'id': item['id'],
                        'question_summary': item['question_summary'],
                        'answer': item['answer'][:100] + '...' if len(item['answer']) > 100 else item['answer'],
                        'current_intent_name': intent_name,
                        'current_confidence': float(item['intent_confidence']) if item['intent_confidence'] else None,
                        'assigned_by': item['intent_assigned_by'],
                        'classified_at': item['intent_classified_at'].isoformat() if item['intent_classified_at'] else None
                    })

                return {
                    'dry_run': True,
                    'total_to_process': total_count,
                    'estimated_batches': (total_count + batch_size - 1) // batch_size,
                    'preview_items': preview_list,
                    'preview_limit': preview_limit,  # 告訴前端這只是示例
                    'has_more': total_count > preview_limit  # 是否還有更多
                }

            # 獲取要處理的知識
            cursor.execute(f"""
                SELECT id, question_summary, answer
                FROM knowledge_base
                WHERE {where_clause}
                LIMIT %s
            """, params + [batch_size])

            knowledge_items = cursor.fetchall()
            cursor.close()

            # 統計結果
            results = {
                'total_processed': 0,
                'success_count': 0,
                'failed_count': 0,
                'unclear_count': 0,
                'details': []
            }

            # 批次處理
            for item in knowledge_items:
                try:
                    result = self.classify_single_knowledge(
                        knowledge_id=item['id'],
                        question_summary=item['question_summary'],
                        answer=item['answer'],
                        assigned_by='auto'
                    )

                    results['total_processed'] += 1

                    if result['classified']:
                        results['success_count'] += 1
                    elif result['intent_name'] == 'unclear':
                        results['unclear_count'] += 1
                    else:
                        results['failed_count'] += 1

                    results['details'].append(result)

                except Exception as e:
                    results['total_processed'] += 1
                    results['failed_count'] += 1
                    results['details'].append({
                        'knowledge_id': item['id'],
                        'classified': False,
                        'error': str(e)
                    })

            return results

        finally:
            conn.close()

    def mark_for_reclassify(
        self,
        intent_ids: Optional[List[int]] = None,
        all_knowledge: bool = False
    ) -> int:
        """
        標記知識需要重新分類

        Args:
            intent_ids: 要標記的意圖 ID 列表
            all_knowledge: 是否標記所有知識

        Returns:
            標記的知識數量
        """
        conn = self._get_db_connection()

        try:
            cursor = conn.cursor()

            if all_knowledge:
                cursor.execute("""
                    UPDATE knowledge_base
                    SET needs_reclassify = true
                    WHERE intent_id IS NOT NULL
                """)
            elif intent_ids:
                cursor.execute("""
                    UPDATE knowledge_base
                    SET needs_reclassify = true
                    WHERE intent_id = ANY(%s)
                """, (intent_ids,))
            else:
                return 0

            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()

            return affected_rows

        finally:
            conn.close()

    def get_classification_stats(self) -> Dict:
        """
        獲取分類統計資訊

        Returns:
            統計資訊
        """
        conn = self._get_db_connection()

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 總體統計
            cursor.execute("""
                SELECT
                    COUNT(*) as total_knowledge,
                    COUNT(intent_id) as classified_count,
                    COUNT(*) - COUNT(intent_id) as unclassified_count,
                    COUNT(CASE WHEN needs_reclassify THEN 1 END) as needs_reclassify_count,
                    AVG(CASE WHEN intent_confidence IS NOT NULL THEN intent_confidence END) as avg_confidence,
                    COUNT(CASE WHEN intent_confidence < 0.7 THEN 1 END) as low_confidence_count
                FROM knowledge_base
            """)

            overall_stats = cursor.fetchone()

            # 按意圖統計
            cursor.execute("""
                SELECT
                    i.id,
                    i.name,
                    i.type,
                    COUNT(kb.id) as knowledge_count,
                    AVG(kb.intent_confidence) as avg_confidence,
                    COUNT(CASE WHEN kb.needs_reclassify THEN 1 END) as needs_reclassify_count
                FROM intents i
                LEFT JOIN knowledge_base kb ON i.id = kb.intent_id
                WHERE i.is_enabled = true
                GROUP BY i.id, i.name, i.type
                ORDER BY knowledge_count DESC
            """)

            by_intent_stats = cursor.fetchall()
            cursor.close()

            return {
                'overall': dict(overall_stats),
                'by_intent': [dict(row) for row in by_intent_stats]
            }

        finally:
            conn.close()

    def reload_intents(self):
        """重新載入意圖配置"""
        return self.intent_classifier.reload_intents()


# 使用範例
if __name__ == "__main__":
    classifier = KnowledgeClassifier()

    # 獲取統計資訊
    stats = classifier.get_classification_stats()
    print("📊 知識庫分類統計:")
    print(f"  總知識數: {stats['overall']['total_knowledge']}")
    print(f"  已分類: {stats['overall']['classified_count']}")
    print(f"  未分類: {stats['overall']['unclassified_count']}")
    print(f"  需要重新分類: {stats['overall']['needs_reclassify_count']}")
    print(f"  平均信心度: {stats['overall']['avg_confidence']:.2f}")

    # 預覽批次分類
    print("\n🔍 預覽批次分類:")
    preview = classifier.classify_batch(
        filters={'max_confidence': 0.7},
        dry_run=True
    )
    print(f"  符合條件的知識: {preview['total_to_process']}")
    print(f"  預估批次數: {preview['estimated_batches']}")
