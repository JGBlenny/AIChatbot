"""
知識缺口分析服務

分析回測失敗案例，識別知識缺口並排定優先級
"""

import psycopg2.pool
import psycopg2.extras
from typing import List, Dict, Optional

try:
    from .models import FailureReason, GapPriority, KnowledgeGap
except ImportError:
    from services.knowledge_completion_loop.models import FailureReason, GapPriority, KnowledgeGap


class GapAnalyzer:
    """知識缺口分析器

    功能：
    1. 分析回測失敗案例
    2. 分類失敗原因
    3. 判斷缺口優先級
    4. 去重合併相似缺口
    5. 持久化分析結果
    """

    def __init__(self, db_pool: psycopg2.pool.SimpleConnectionPool):
        """初始化分析器

        Args:
            db_pool: PostgreSQL 連接池
        """
        self.db_pool = db_pool

    async def analyze_failures(
        self,
        loop_id: int,
        iteration: int,
        backtest_run_id: int
    ) -> List[Dict]:
        """分析回測失敗案例

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            backtest_run_id: 回測執行 ID

        Returns:
            知識缺口清單（字典格式）

        Workflow:
        1. 從 backtest_results 讀取失敗案例
        2. 分類失敗原因（使用啟發式規則）
        3. 判斷優先級（根據信心度與相似度）
        4. 去重合併相似缺口
        5. 寫入 knowledge_gap_analysis 表
        6. 返回缺口清單
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Step 1: 讀取失敗案例
                cur.execute("""
                    SELECT
                        br.scenario_id,
                        bs.test_question as question,
                        br.confidence as confidence_score,
                        br.overall_score as similarity_score,
                        br.overall_score as semantic_overlap_score,
                        0 as response_time_ms,
                        NULL as error_type,
                        bs.expected_intent_id as intent_id,
                        (SELECT name FROM intents WHERE id = bs.expected_intent_id) as intent_name
                    FROM backtest_results br
                    JOIN test_scenarios bs ON br.scenario_id = bs.id
                    WHERE br.run_id = %s
                      AND br.passed = false
                    ORDER BY br.scenario_id
                """, (backtest_run_id,))

                failed_scenarios = cur.fetchall()

                if not failed_scenarios:
                    return []

                # Step 2-3: 分類失敗原因與判斷優先級
                gaps = []
                for scenario in failed_scenarios:
                    gap = self._classify_and_prioritize(scenario)
                    gaps.append(gap)

                # Step 4: 去重合併相似缺口
                unique_gaps = self._deduplicate_gaps(gaps)

                # Step 5: 持久化到資料庫
                gap_ids = self._persist_gaps(
                    cur=cur,
                    loop_id=loop_id,
                    iteration=iteration,
                    gaps=unique_gaps
                )

                conn.commit()

                # Step 6: 返回缺口清單（附帶 gap_id）
                result = []
                for gap, gap_id in zip(unique_gaps, gap_ids):
                    gap_dict = {
                        "gap_id": gap_id,
                        "scenario_id": gap.scenario_id,
                        "question": gap.question,
                        "failure_reason": gap.failure_reason.value,
                        "priority": gap.priority.value,
                        "suggested_action_type": gap.suggested_action_type,
                        "confidence_score": gap.confidence_score,
                        "max_similarity": gap.max_similarity,
                        "intent_id": gap.intent_id,
                        "intent_name": gap.intent_name,
                        "frequency": gap.frequency
                    }
                    result.append(gap_dict)

                return result

        finally:
            self.db_pool.putconn(conn)

    def _classify_and_prioritize(self, scenario: Dict) -> KnowledgeGap:
        """分類失敗原因並判斷優先級

        啟發式規則：
        1. similarity_score < 0.6 → NO_MATCH
        2. confidence_score < 0.7 → LOW_CONFIDENCE
        3. semantic_overlap_score < 0.4 → SEMANTIC_MISMATCH
        4. error_type IS NOT NULL → SYSTEM_ERROR

        優先級規則：
        1. NO_MATCH → P0（最高優先級）
        2. LOW_CONFIDENCE & similarity >= 0.6 → P1（中優先級）
        3. SEMANTIC_MISMATCH / SYSTEM_ERROR → P2（低優先級）
        """
        # 分類失敗原因
        similarity = scenario.get('similarity_score') or 0.0
        confidence = scenario.get('confidence_score') or 0.0
        semantic_overlap = scenario.get('semantic_overlap_score') or 0.0
        error_type = scenario.get('error_type')

        if error_type:
            failure_reason = FailureReason.SYSTEM_ERROR
            priority = GapPriority.P2
        elif similarity < 0.6:
            failure_reason = FailureReason.NO_MATCH
            priority = GapPriority.P0
        elif semantic_overlap < 0.4:
            failure_reason = FailureReason.SEMANTIC_MISMATCH
            priority = GapPriority.P2
        elif confidence < 0.7:
            failure_reason = FailureReason.LOW_CONFIDENCE
            priority = GapPriority.P1
        else:
            # Fallback: 預設為信心度不足
            failure_reason = FailureReason.LOW_CONFIDENCE
            priority = GapPriority.P1

        # 建議回應類型（初步判斷，後續由 ActionTypeClassifier 確認）
        suggested_action_type = self._suggest_action_type(
            intent_name=scenario.get('intent_name'),
            failure_reason=failure_reason
        )

        return KnowledgeGap(
            scenario_id=scenario['scenario_id'],
            question=scenario['question'],
            failure_reason=failure_reason,
            priority=priority,
            suggested_action_type=suggested_action_type,
            confidence_score=confidence,
            max_similarity=similarity,
            intent_id=scenario.get('intent_id'),
            intent_name=scenario.get('intent_name'),
            frequency=1
        )

    def _suggest_action_type(
        self,
        intent_name: Optional[str],
        failure_reason: FailureReason
    ) -> str:
        """初步建議回應類型

        簡單啟發式規則：
        - 意圖包含「查詢」、「查看」 → direct_answer
        - 意圖包含「申請」、「填寫」 → form_fill
        - 意圖包含「繳費」、「計算」 → api_call
        - 預設 → direct_answer
        """
        if not intent_name:
            return "direct_answer"

        intent_lower = intent_name.lower()

        if any(keyword in intent_lower for keyword in ['申請', '填寫', '表單']):
            return "form_fill"
        elif any(keyword in intent_lower for keyword in ['繳費', '計算', '查詢電費', '查詢水費']):
            return "api_call"
        else:
            return "direct_answer"

    def _deduplicate_gaps(self, gaps: List[KnowledgeGap]) -> List[KnowledgeGap]:
        """去重合併相似缺口

        規則：
        1. 相同 scenario_id → 合併（保留最高優先級）
        2. 相同問題文字 → 合併（累加 frequency）

        簡化實作：目前只處理完全相同的 scenario_id
        TODO: 未來可加入文字相似度計算（使用 embedding）
        """
        seen = {}
        unique_gaps = []

        for gap in gaps:
            if gap.scenario_id in seen:
                # 合併：選擇更高優先級，累加頻率
                existing_gap = seen[gap.scenario_id]
                if self._priority_value(gap.priority) > self._priority_value(existing_gap.priority):
                    existing_gap.priority = gap.priority
                    existing_gap.failure_reason = gap.failure_reason
                existing_gap.frequency += 1
            else:
                seen[gap.scenario_id] = gap
                unique_gaps.append(gap)

        return unique_gaps

    def _priority_value(self, priority: GapPriority) -> int:
        """優先級數值化（用於比較）"""
        priority_map = {
            GapPriority.P0: 3,
            GapPriority.P1: 2,
            GapPriority.P2: 1
        }
        return priority_map.get(priority, 0)

    def _persist_gaps(
        self,
        cur,
        loop_id: int,
        iteration: int,
        gaps: List[KnowledgeGap]
    ) -> List[int]:
        """持久化缺口分析結果到資料庫

        Returns:
            List[int]: 插入的 gap_id 清單
        """
        gap_ids = []

        for gap in gaps:
            cur.execute("""
                INSERT INTO knowledge_gap_analysis (
                    loop_id,
                    iteration,
                    scenario_id,
                    question,
                    failure_reason,
                    priority,
                    suggested_action_type,
                    confidence_score,
                    max_similarity,
                    intent_id,
                    intent_name,
                    frequency,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                loop_id,
                iteration,
                gap.scenario_id,
                gap.question,
                gap.failure_reason.value,
                gap.priority.value,
                gap.suggested_action_type,
                gap.confidence_score,
                gap.max_similarity,
                gap.intent_id,
                gap.intent_name,
                gap.frequency
            ))

            gap_id = cur.fetchone()['id']
            gap_ids.append(gap_id)

        return gap_ids
