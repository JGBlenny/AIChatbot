"""
知識庫完善迴圈 - 外部服務客戶端

提供與外部服務通訊的客戶端類別（Stub 實作）
"""

from typing import Dict, List, Optional
import asyncio


class BacktestFrameworkClient:
    """回測框架客戶端（Stub）"""

    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url

    async def execute_batch_backtest(
        self,
        vendor_id: int,
        batch_size: int,
        filters: Dict,
        config: Dict
    ) -> Dict:
        """
        執行批次回測

        Args:
            vendor_id: 業者 ID
            batch_size: 批次大小
            filters: 篩選條件
            config: 回測配置

        Returns:
            {
                "total_tested": int,
                "passed": int,
                "failed": int,
                "pass_rate": float,
                "failed_scenarios": List[Dict]
            }
        """
        # Stub 實作：模擬回測結果
        await asyncio.sleep(0.1)  # 模擬 API 延遲

        return {
            "total_tested": batch_size,
            "passed": int(batch_size * 0.6),  # 模擬 60% 通過率
            "failed": int(batch_size * 0.4),
            "pass_rate": 0.6,
            "failed_scenarios": [
                {
                    "scenario_id": i,
                    "question": f"測試問題 {i}",
                    "expected_answer": "預期答案",
                    "actual_answer": "實際答案",
                    "failure_reason": "no_match" if i % 2 == 0 else "low_confidence",
                    "confidence_score": 0.5,
                    "max_similarity": 0.55
                }
                for i in range(1, int(batch_size * 0.4) + 1)
            ]
        }

    async def execute_validation_backtest(
        self,
        vendor_id: int,
        scenario_ids: List[int],
        use_temp_knowledge: bool = True
    ) -> Dict:
        """
        執行迭代驗證回測（使用臨時知識）

        Args:
            vendor_id: 業者 ID
            scenario_ids: 要驗證的案例 ID 列表
            use_temp_knowledge: 是否使用臨時知識（UNION ALL 查詢）

        Returns:
            {
                "total_tested": int,
                "passed": int,
                "failed": int,
                "pass_rate": float,
                "improvement": float
            }
        """
        await asyncio.sleep(0.1)

        # Stub 實作：模擬驗證回測（假設通過率提升）
        return {
            "total_tested": len(scenario_ids),
            "passed": int(len(scenario_ids) * 0.75),  # 模擬 75% 通過率
            "failed": int(len(scenario_ids) * 0.25),
            "pass_rate": 0.75,
            "improvement": 0.15  # 模擬提升 15%
        }


class GapAnalyzer:
    """知識缺口分析器（Stub）"""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def analyze_failures(
        self,
        loop_id: int,
        failed_scenarios: List[Dict]
    ) -> List[Dict]:
        """
        分析失敗案例，識別知識缺口

        Args:
            loop_id: 迴圈 ID
            failed_scenarios: 失敗的測試案例

        Returns:
            List[Dict]: 知識缺口列表（已儲存到 knowledge_gap_analysis 表）
        """
        await asyncio.sleep(0.1)

        # Stub 實作：模擬缺口分析並寫入資料庫
        # 注意：實際實作應該調用真實的缺口分析邏輯
        gaps = []

        # 在真實實作中，這裡應該：
        # 1. 分析失敗原因（no_match, low_confidence, semantic_mismatch）
        # 2. 確定優先級（p0, p1, p2）
        # 3. 建議回應類型（direct_answer, form_fill, api_call）
        # 4. 將結果寫入 knowledge_gap_analysis 表

        for scenario in failed_scenarios:
            gap = {
                "gap_id": len(gaps) + 1,
                "scenario_id": scenario["scenario_id"],
                "question": scenario["question"],
                "failure_reason": scenario["failure_reason"],
                "priority": "p0" if scenario["failure_reason"] == "no_match" else "p1",
                "suggested_action_type": "direct_answer",
                "confidence_score": scenario.get("confidence_score", 0.0),
                "max_similarity": scenario.get("max_similarity", 0.0)
            }
            gaps.append(gap)

        return gaps


class ActionTypeClassifier:
    """回應類型判斷器（Stub）"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key

    async def classify_action_type(
        self,
        question: str,
        mode: str = "ai_assisted"
    ) -> Dict:
        """
        判斷問題的回應類型

        Args:
            question: 問題內容
            mode: 判斷模式（manual_only, ai_assisted, auto）

        Returns:
            {
                "action_type": str,
                "confidence": float,
                "reasoning": str,
                "needs_manual_review": bool,
                "required_form_fields": Optional[List[str]],
                "suggested_form_id": Optional[str],
                "required_api_endpoint": Optional[str],
                "suggested_api_id": Optional[str]
            }
        """
        await asyncio.sleep(0.05)

        # Stub 實作：簡單的啟發式判斷
        if "申請" in question or "表單" in question:
            action_type = "form_fill"
        elif "查詢" in question or "API" in question:
            action_type = "api_call"
        else:
            action_type = "direct_answer"

        return {
            "action_type": action_type,
            "confidence": 0.85,
            "reasoning": f"根據關鍵字判斷為 {action_type}",
            "needs_manual_review": False,
            "required_form_fields": None,
            "suggested_form_id": None,
            "required_api_endpoint": None,
            "suggested_api_id": None
        }


class KnowledgeGeneratorClient:
    """知識生成器客戶端（Stub）"""

    def __init__(self, openai_api_key: Optional[str] = None, db_pool=None):
        self.openai_api_key = openai_api_key
        self.db_pool = db_pool

    async def generate_knowledge(
        self,
        loop_id: int,
        gaps: List[Dict],
        action_type_judgments: Dict[int, Dict],
        iteration: int
    ) -> List[Dict]:
        """
        生成知識並儲存到 loop_generated_knowledge 表

        Args:
            loop_id: 迴圈 ID
            gaps: 知識缺口列表
            action_type_judgments: 缺口 ID 到回應類型判斷的映射
            iteration: 迭代次數

        Returns:
            List[Dict]: 生成的知識列表（已儲存到資料庫）
        """
        await asyncio.sleep(0.2)

        # Stub 實作：模擬知識生成並寫入資料庫
        # 注意：實際實作應該調用 OpenAI API 生成答案內容
        generated = []

        if self.db_pool is None:
            # 如果沒有資料庫連接，只返回記憶體資料
            for gap in gaps:
                gap_id = gap["gap_id"]
                judgment = action_type_judgments.get(gap_id, {})

                knowledge = {
                    "loop_knowledge_id": len(generated) + 1,
                    "gap_id": gap_id,
                    "question": gap["question"],
                    "answer": f"這是針對「{gap['question']}」生成的答案內容",
                    "action_type": judgment.get("action_type", "direct_answer"),
                    "status": "approved",
                    "needs_review": False
                }
                generated.append(knowledge)
            return generated

        # 寫入資料庫
        conn = self.db_pool.getconn()
        try:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                for gap in gaps:
                    gap_id = gap["gap_id"]
                    judgment = action_type_judgments.get(gap_id, {})

                    # 插入到 loop_generated_knowledge 表
                    cur.execute(
                        """
                        INSERT INTO loop_generated_knowledge (
                            loop_id,
                            iteration,
                            question,
                            answer,
                            action_type,
                            status,
                            reviewed_by,
                            reviewed_at,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING id, question, answer, action_type, status
                        """,
                        (
                            loop_id,
                            iteration,
                            gap["question"],
                            f"這是針對「{gap['question']}」生成的答案內容",
                            judgment.get("action_type", "direct_answer"),
                            "approved",  # Stub 直接設為 approved
                            "system"
                        )
                    )
                    result = cur.fetchone()
                    generated.append(dict(result))

                conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"生成知識寫入資料庫失敗: {str(e)}")
            raise
        finally:
            self.db_pool.putconn(conn)

        return generated
