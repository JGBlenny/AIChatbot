"""
知識庫完善迴圈 - 協調器

LoopCoordinator 負責協調完整的迴圈流程，包含：
- 狀態機管理
- 迭代執行協調
- 批次同步控制
"""

import asyncio
import random
from typing import Dict, Optional, List
from datetime import datetime
import psycopg2.pool
from psycopg2.extras import RealDictCursor

try:
    from .models import (
        LoopStatus,
        LoopConfig,
        InvalidStateError,
        KnowledgeCompletionError,
        ErrorCategory,
        BacktestError,
        LoopNotFoundError,
    )
    from .clients import ActionTypeClassifier
    from .gap_analyzer import GapAnalyzer
    from .backtest_client import BacktestFrameworkClient
    from .action_type_classifier import ActionTypeClassifier as ActionTypeClassifierReal
    from .knowledge_generator import KnowledgeGeneratorClient
    from .cost_tracker import OpenAICostTracker, BudgetExceededError
    from .gap_classifier import GapClassifier
    from .sop_generator import SOPGenerator
except ImportError as import_error:
    # 如果相對 import 失敗，嘗試絕對 import（通常不應該發生）
    import sys
    print(f"⚠️ 相對 import 失敗，錯誤: {import_error}", file=sys.stderr)
    print(f"⚠️ Python 路徑: {sys.path}", file=sys.stderr)
    raise  # 直接拋出錯誤，不要使用錯誤的 import 路徑


class LoopCoordinator:
    """完善迴圈協調器（狀態機）"""

    def __init__(
        self,
        db_pool: psycopg2.pool.SimpleConnectionPool,
        vendor_id: int,
        loop_name: str = "知識庫完善迴圈",
        backtest_base_url: str = "http://localhost:8100",
        openai_api_key: Optional[str] = None
    ):
        """
        初始化協調器

        Args:
            db_pool: 資料庫連接池
            vendor_id: 業者 ID
            loop_name: 迴圈名稱
            backtest_base_url: 回測服務 URL
            openai_api_key: OpenAI API Key
        """
        self.db_pool = db_pool
        self.vendor_id = vendor_id
        self.loop_name = loop_name
        self.loop_id: Optional[int] = None
        self.current_status: LoopStatus = LoopStatus.PENDING
        self.config: Optional[LoopConfig] = None

        # 初始化客戶端
        self.backtest_client = BacktestFrameworkClient(
            base_url=backtest_base_url,
            db_pool=db_pool
        )
        self.gap_analyzer = GapAnalyzer(db_pool)
        self.action_classifier = ActionTypeClassifierReal(openai_api_key, db_pool)
        self.gap_classifier = GapClassifier(
            openai_api_key=openai_api_key,
            model="gpt-4o-mini"  # 使用較經濟的模型進行分類
        )

        # cost_tracker 將在 start_loop 時初始化（需要 loop_id 和 budget_limit）
        self.cost_tracker: Optional[OpenAICostTracker] = None

        self.knowledge_generator = KnowledgeGeneratorClient(
            openai_api_key=openai_api_key,
            db_pool=db_pool,
            cost_tracker=self.cost_tracker  # 稍後會通過 setter 更新
        )

        self.sop_generator = SOPGenerator(
            db_pool=db_pool,
            openai_api_key=openai_api_key,
            cost_tracker=self.cost_tracker,  # 稍後會通過 setter 更新
            model="gpt-4o-mini"
        )

    async def start_loop(self, config: LoopConfig) -> Dict:
        """
        [需求 1.1] 啟動完善迴圈

        Args:
            config: 迴圈配置

        Returns:
            {
                "loop_id": int,
                "loop_name": str,
                "vendor_id": int,
                "status": str,
                "initial_statistics": {
                    "total_scenarios": int,
                    "estimated_iterations": int,
                    "target_pass_rate": float
                },
                "created_at": str
            }

        Raises:
            InvalidStateError: 當前狀態不允許啟動
            KnowledgeCompletionError: 資料庫操作失敗
        """
        # 驗證狀態
        if self.loop_id is not None:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state=LoopStatus.RUNNING.value
            )

        self.config = config

        # 計算初始統計資訊
        total_scenarios = await self._count_test_scenarios(config.filters)
        estimated_iterations = self._estimate_iterations(
            total_scenarios,
            config.batch_size,
            config.target_pass_rate
        )

        # 建立迴圈記錄
        loop_id = await self._create_loop_record(
            config=config,
            total_scenarios=total_scenarios
        )

        self.loop_id = loop_id
        self.current_status = LoopStatus.PENDING

        # 初始化成本追蹤器
        budget_limit = getattr(config, 'budget_limit_usd', None)
        self.cost_tracker = OpenAICostTracker(
            loop_id=loop_id,
            db_pool=self.db_pool,
            budget_limit_usd=budget_limit
        )

        # 更新 knowledge_generator 的 cost_tracker
        self.knowledge_generator.cost_tracker = self.cost_tracker

        # 記錄事件（保持 PENDING 狀態，等使用者手動執行迭代才變 RUNNING）
        await self._log_event(
            event_type="loop_started",
            event_data={
                "config": config.dict(),
                "total_scenarios": total_scenarios,
                "estimated_iterations": estimated_iterations
            }
        )

        return {
            "loop_id": self.loop_id,
            "loop_name": self.loop_name,
            "vendor_id": self.vendor_id,
            "status": LoopStatus.PENDING.value,
            "initial_statistics": {
                "total_scenarios": total_scenarios,
                "estimated_iterations": estimated_iterations,
                "target_pass_rate": config.target_pass_rate
            },
            "created_at": datetime.now().isoformat()
        }

    async def load_loop(self, loop_id: int) -> Dict:
        """
        [需求 10.6.1] 載入已存在的迴圈

        從資料庫載入迴圈記錄並初始化協調器狀態，支援跨 session 續接。

        Args:
            loop_id: 迴圈 ID

        Returns:
            {
                "loop_id": int,
                "status": str,
                "current_iteration": int,
                "loaded_at": str
            }

        Raises:
            LoopNotFoundError: 迴圈不存在
            KnowledgeCompletionError: 資料庫操作失敗
        """
        # 從資料庫載入迴圈資訊
        loop_record = await self._fetch_loop_record(loop_id)
        if not loop_record:
            raise LoopNotFoundError(loop_id)

        # 初始化協調器狀態
        self.loop_id = loop_id
        self.vendor_id = loop_record["vendor_id"]
        self.loop_name = loop_record["loop_name"]
        self.current_status = LoopStatus(loop_record["status"])

        # 初始化配置
        config_dict = loop_record.get("config", {})
        self.config = LoopConfig(**config_dict)

        # 初始化成本追蹤器
        budget_limit = loop_record.get("budget_limit_usd")
        self.cost_tracker = OpenAICostTracker(
            loop_id=loop_id,
            db_pool=self.db_pool,
            budget_limit_usd=budget_limit
        )

        # 更新生成器的 cost_tracker
        self.knowledge_generator.cost_tracker = self.cost_tracker
        self.sop_generator.cost_tracker = self.cost_tracker

        # 記錄載入事件
        await self._log_event(
            event_type="loop_loaded",
            event_data={
                "loaded_from_status": self.current_status.value,
                "current_iteration": loop_record.get("current_iteration", 0),
                "vendor_id": self.vendor_id
            }
        )

        return {
            "loop_id": self.loop_id,
            "status": self.current_status.value,
            "current_iteration": loop_record.get("current_iteration", 0),
            "loaded_at": datetime.now().isoformat()
        }

    async def _fetch_loop_record(self, loop_id: int) -> Optional[Dict]:
        """
        從資料庫讀取迴圈記錄

        Args:
            loop_id: 迴圈 ID

        Returns:
            迴圈記錄字典，若不存在則返回 None
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT
                        id, vendor_id, loop_name, status, config,
                        current_iteration, budget_limit_usd, created_at
                    FROM knowledge_completion_loops
                    WHERE id = %s
                """
                cursor.execute(query, (loop_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        finally:
            self.db_pool.putconn(conn)

    async def validate_loop(
        self,
        validation_scope: str = "failed_plus_sample",
        sample_pass_rate: float = 0.2
    ) -> Dict:
        """
        [需求 9] 驗證效果回測（可選功能）

        執行驗證回測以檢驗已審核知識的效果，支援三種驗證範圍。

        Args:
            validation_scope: 驗證範圍（failed_only/all/failed_plus_sample）
            sample_pass_rate: 抽樣比例（僅在 failed_plus_sample 時使用）

        Returns:
            {
                "validation_result": Dict,  # 回測結果
                "validation_passed": bool,  # 驗證是否通過
                "improvement": float,  # 改善幅度
                "regression_detected": bool,  # 是否檢測到 regression
                "regression_count": int,  # regression 案例數量
                "next_action": str  # 下一步建議（continue/adjust_knowledge）
            }

        Raises:
            InvalidStateError: 當前狀態不為 REVIEWING
        """
        # 驗證狀態
        if self.current_status != LoopStatus.REVIEWING:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="validate"
            )

        # 取得固定測試集
        scenario_ids = await self._get_scenario_ids()

        # 根據驗證範圍選取測試案例
        if validation_scope == "failed_only":
            # 只測試失敗案例
            test_scenario_ids = await self._get_failed_scenario_ids(
                iteration=await self._get_current_iteration()
            )
        elif validation_scope == "all":
            # 測試所有案例
            test_scenario_ids = scenario_ids
        else:  # failed_plus_sample
            # 失敗案例 + 抽樣通過案例
            current_iteration = await self._get_current_iteration()
            failed_ids = await self._get_failed_scenario_ids(
                iteration=current_iteration
            )
            passed_ids = [sid for sid in scenario_ids if sid not in failed_ids]

            # 隨機抽樣通過案例
            sample_size = int(len(passed_ids) * sample_pass_rate)
            sampled_passed_ids = random.sample(passed_ids, min(sample_size, len(passed_ids)))

            test_scenario_ids = failed_ids + sampled_passed_ids

        # 執行驗證回測
        await self._update_loop_status(LoopStatus.VALIDATING)

        validation_result = await self.backtest_client.execute_backtest(
            vendor_id=self.vendor_id,
            scenario_ids=test_scenario_ids,
            run_name=f"Validation_{self.loop_id}_Iter{await self._get_current_iteration()}"
        )

        # 檢測 regression（如果測試了通過案例）
        regression_detected = False
        regression_count = 0
        if validation_scope in ["all", "failed_plus_sample"]:
            regression_count = await self._detect_regression(
                validation_result,
                scenario_ids
            )
            regression_detected = regression_count > 0

        # 獲取上次通過率
        current_iteration = await self._get_current_iteration()
        last_pass_rate = await self._get_last_pass_rate(current_iteration)

        # 判斷驗證是否通過
        improvement = validation_result["pass_rate"] - last_pass_rate
        validation_passed = (
            (improvement >= 0.05 or validation_result["pass_rate"] >= 0.7)
            and not regression_detected
        )

        # 更新知識狀態（如果驗證未通過）
        if not validation_passed:
            await self._mark_knowledge_need_improvement()

        # 記錄驗證事件
        await self._log_event(
            event_type="validation_completed",
            event_data={
                "validation_scope": validation_scope,
                "test_count": len(test_scenario_ids),
                "pass_rate": validation_result["pass_rate"],
                "last_pass_rate": last_pass_rate,
                "improvement": improvement,
                "regression_detected": regression_detected,
                "regression_count": regression_count,
                "validation_passed": validation_passed
            }
        )

        # 更新狀態回 RUNNING
        await self._update_loop_status(LoopStatus.RUNNING)

        return {
            "validation_result": validation_result,
            "validation_passed": validation_passed,
            "improvement": improvement,
            "regression_detected": regression_detected,
            "regression_count": regression_count,
            "next_action": "continue" if validation_passed else "adjust_knowledge"
        }

    async def _get_scenario_ids(self) -> List[int]:
        """
        獲取迴圈的固定測試集 ID 列表

        Returns:
            測試情境 ID 列表
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT scenario_ids
                    FROM knowledge_completion_loops
                    WHERE id = %s
                """
                cursor.execute(query, (self.loop_id,))
                result = cursor.fetchone()
                return result["scenario_ids"] if result and result["scenario_ids"] else []
        finally:
            self.db_pool.putconn(conn)

    async def _get_last_pass_rate(self, current_iteration: int) -> float:
        """
        獲取上一次迭代的通過率

        Args:
            current_iteration: 當前迭代次數

        Returns:
            上次通過率，若無則返回 0.0
        """
        if current_iteration <= 1:
            return 0.0

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT event_data->>'pass_rate' as pass_rate
                    FROM loop_execution_logs
                    WHERE loop_id = %s
                      AND event_type = 'iteration_completed'
                      AND (event_data->>'iteration')::int = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(query, (self.loop_id, current_iteration - 1))
                result = cursor.fetchone()
                return float(result["pass_rate"]) if result and result["pass_rate"] else 0.0
        finally:
            self.db_pool.putconn(conn)

    async def _detect_regression(
        self,
        validation_result: Dict,
        original_scenario_ids: List[int]
    ) -> int:
        """
        檢測 regression（原本通過現在失敗的案例）

        Args:
            validation_result: 驗證回測結果
            original_scenario_ids: 原始測試集 ID

        Returns:
            regression 案例數量
        """
        # 查詢原本通過的案例
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 獲取當前迭代
                current_iteration = await self._get_current_iteration()

                # 查詢上一次迭代通過的案例
                query = """
                    SELECT DISTINCT scenario_id
                    FROM backtest_results
                    WHERE loop_id = %s
                      AND iteration = %s
                      AND passed = true
                      AND scenario_id = ANY(%s)
                """
                cursor.execute(query, (self.loop_id, current_iteration - 1, original_scenario_ids))
                previously_passed = cursor.fetchall()
                previously_passed_ids = [row["scenario_id"] for row in previously_passed]

                # 檢查驗證結果中有哪些原本通過的案例現在失敗了
                regression_count = 0
                validation_results = validation_result.get("results", [])

                for result in validation_results:
                    scenario_id = result.get("scenario_id")
                    passed = result.get("passed", False)

                    if scenario_id in previously_passed_ids and not passed:
                        regression_count += 1

                # 記錄 regression 事件
                if regression_count > 0:
                    await self._log_event(
                        event_type="regression_detected",
                        event_data={
                            "regression_count": regression_count,
                            "validation_scope": "validate_loop"
                        }
                    )

                return regression_count
        finally:
            self.db_pool.putconn(conn)

    async def _mark_knowledge_need_improvement(self):
        """
        標記本次迭代生成的知識為需要改善

        更新 knowledge_base 和 vendor_sop_items 的 review_status='need_improvement'
        """
        current_iteration = await self._get_current_iteration()

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # 更新一般知識
                update_knowledge = """
                    UPDATE knowledge_base
                    SET review_status = 'need_improvement',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE source_loop_id = %s
                      AND source_loop_iteration = %s
                      AND review_status = 'approved'
                """
                cursor.execute(update_knowledge, (self.loop_id, current_iteration))
                knowledge_count = cursor.rowcount

                # 更新 SOP 知識
                update_sop = """
                    UPDATE vendor_sop_items
                    SET review_status = 'need_improvement',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE source_loop_id = %s
                      AND source_loop_iteration = %s
                      AND review_status = 'approved'
                """
                cursor.execute(update_sop, (self.loop_id, current_iteration))
                sop_count = cursor.rowcount

                conn.commit()

                # 記錄標記事件
                await self._log_event(
                    event_type="knowledge_marked_need_improvement",
                    event_data={
                        "knowledge_count": knowledge_count,
                        "sop_count": sop_count,
                        "iteration": current_iteration
                    }
                )
        finally:
            self.db_pool.putconn(conn)

    # ============================================
    # 私有方法：資料庫操作
    # ============================================

    async def _count_test_scenarios(self, filters: Dict) -> int:
        """
        計算符合篩選條件的測試案例總數

        Args:
            filters: 篩選條件

        Returns:
            測試案例總數
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 基礎查詢（test_scenarios 表沒有 vendor_id 欄位）
                query = """
                    SELECT COUNT(*) as count
                    FROM test_scenarios
                    WHERE is_active = true
                """
                params = []

                # 套用篩選條件
                if filters.get("source"):
                    query += " AND source = %s"
                    params.append(filters["source"])

                if filters.get("difficulty"):
                    query += " AND difficulty = %s"
                    params.append(filters["difficulty"])

                if filters.get("intent_ids"):
                    query += " AND intent_id = ANY(%s)"
                    params.append(filters["intent_ids"])

                cur.execute(query, params)
                result = cur.fetchone()
                return result["count"]
        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"查詢測試案例數量失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"filters": filters}
            )
        finally:
            self.db_pool.putconn(conn)

    def _estimate_iterations(
        self,
        total_scenarios: int,
        batch_size: int,
        target_pass_rate: float
    ) -> int:
        """
        估算迭代次數

        Args:
            total_scenarios: 總測試案例數
            batch_size: 每批回測題數
            target_pass_rate: 目標通過率

        Returns:
            估算的迭代次數
        """
        # 簡化估算公式：假設每輪迭代提升 5% 通過率
        # 實際公式可以更複雜，考慮學習曲線
        initial_pass_rate = 0.5  # 假設初始通過率 50%
        pass_rate_gain_per_iteration = 0.05

        if target_pass_rate <= initial_pass_rate:
            return 1

        iterations_needed = int(
            (target_pass_rate - initial_pass_rate) / pass_rate_gain_per_iteration
        ) + 1

        return min(iterations_needed, 20)  # 最多 20 輪

    async def _create_loop_record(
        self,
        config: LoopConfig,
        total_scenarios: int
    ) -> int:
        """
        建立迴圈記錄

        Args:
            config: 迴圈配置
            total_scenarios: 總測試案例數

        Returns:
            loop_id
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_completion_loops (
                        loop_name,
                        vendor_id,
                        status,
                        config,
                        target_pass_rate,
                        total_scenarios,
                        current_iteration,
                        budget_limit_usd,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (
                        self.loop_name,
                        self.vendor_id,
                        LoopStatus.PENDING.value,
                        psycopg2.extras.Json(config.dict()),
                        config.target_pass_rate,
                        total_scenarios,
                        0,
                        config.dict().get("budget_limit_usd", 100.0)
                    )
                )
                result = cur.fetchone()
                conn.commit()
                return result["id"]
        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"建立迴圈記錄失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"config": config.dict()}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _update_loop_status(self, new_status: LoopStatus) -> None:
        """
        更新迴圈狀態

        Args:
            new_status: 新狀態
        """
        if self.loop_id is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state=new_status.value
            )

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (new_status.value, self.loop_id)
                )
                conn.commit()
                self.current_status = new_status
        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"更新迴圈狀態失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "new_status": new_status.value}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _log_event(self, event_type: str, event_data: Dict) -> None:
        """
        記錄事件到 loop_execution_logs

        Args:
            event_type: 事件類型
            event_data: 事件資料
        """
        if self.loop_id is None:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO loop_execution_logs (
                        loop_id, event_type, event_data, created_at
                    ) VALUES (%s, %s, %s, NOW())
                    """,
                    (
                        self.loop_id,
                        event_type,
                        psycopg2.extras.Json(event_data)
                    )
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            # 日誌失敗不影響主流程，僅記錄錯誤
            print(f"記錄事件失敗: {str(e)}")
        finally:
            self.db_pool.putconn(conn)

    async def _get_current_iteration(self) -> int:
        """
        獲取當前迭代次數

        Returns:
            當前迭代次數
        """
        if self.loop_id is None:
            return 0

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT current_iteration
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (self.loop_id,)
                )
                result = cur.fetchone()
                return result["current_iteration"] if result else 0
        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"查詢當前迭代次數失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _update_iteration_count(self, iteration: int) -> None:
        """
        更新迭代次數（不更新通過率）

        在迭代開始時立即調用，確保即使後續步驟失敗，
        current_iteration 也能與 backtest_runs 的記錄保持一致

        Args:
            iteration: 新的迭代次數
        """
        if self.loop_id is None:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET
                        current_iteration = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (iteration, self.loop_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"更新迭代次數失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "iteration": iteration}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _update_pass_rate(self, pass_rate: float) -> None:
        """
        更新當前迭代的通過率（不更新迭代次數）

        在回測完成後調用，記錄本次迭代的通過率

        Args:
            pass_rate: 通過率 (0.0-1.0)
        """
        if self.loop_id is None:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET
                        current_pass_rate = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (pass_rate, self.loop_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"更新通過率失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "pass_rate": pass_rate}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _increment_iteration(self, latest_pass_rate: float) -> None:
        """
        遞增迭代次數並更新通過率

        Args:
            latest_pass_rate: 最新通過率
        """
        if self.loop_id is None:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET
                        current_iteration = current_iteration + 1,
                        current_pass_rate = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (latest_pass_rate, self.loop_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"更新迭代次數失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "latest_pass_rate": latest_pass_rate}
            )
        finally:
            self.db_pool.putconn(conn)

    def _calculate_gap_statistics(self, gaps: List[Dict]) -> Dict:
        """
        計算知識缺口統計資訊

        Args:
            gaps: 知識缺口列表

        Returns:
            {
                "total_gaps": int,
                "p0_count": int,
                "p1_count": int,
                "p2_count": int
            }
        """
        stats = {
            "total_gaps": len(gaps),
            "p0_count": 0,
            "p1_count": 0,
            "p2_count": 0
        }

        for gap in gaps:
            priority = gap.get("priority", "p2")
            if priority == "p0":
                stats["p0_count"] += 1
            elif priority == "p1":
                stats["p1_count"] += 1
            elif priority == "p2":
                stats["p2_count"] += 1

        return stats

    async def _get_approved_knowledge(self, iteration: int) -> List[Dict]:
        """
        獲取審核通過的臨時知識

        Args:
            iteration: 迭代次數

        Returns:
            審核通過的知識列表
        """
        if self.loop_id is None:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        question,
                        answer,
                        action_type,
                        form_id,
                        api_config,
                        intent_id,
                        keywords,
                        embedding,
                        business_types,
                        target_user,
                        scope,
                        priority,
                        reviewed_by
                    FROM loop_generated_knowledge
                    WHERE loop_id = %s
                      AND iteration = %s
                      AND status = 'approved'
                      AND synced_to_kb = false
                    ORDER BY id
                    """,
                    (self.loop_id, iteration)
                )
                results = cur.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"查詢審核通過的知識失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "iteration": iteration}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _get_failed_scenario_ids(self, iteration: int) -> List[int]:
        """
        獲取本輪迭代失敗的測試案例 ID

        Args:
            iteration: 迭代次數

        Returns:
            失敗的測試案例 ID 列表
        """
        if self.loop_id is None:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT scenario_id
                    FROM knowledge_gap_analysis
                    WHERE loop_id = %s
                      AND iteration = %s
                    ORDER BY scenario_id
                    """,
                    (self.loop_id, iteration)
                )
                results = cur.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"查詢失敗案例 ID 失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={"loop_id": self.loop_id, "iteration": iteration}
            )
        finally:
            self.db_pool.putconn(conn)

    async def _batch_sync_knowledge(
        self,
        iteration: int,
        approved_knowledge: List[Dict],
        new_pass_rate: float
    ) -> Dict:
        """
        批次同步知識到 knowledge_base（事務處理）

        Args:
            iteration: 迭代次數
            approved_knowledge: 審核通過的知識列表
            new_pass_rate: 新的通過率

        Returns:
            {
                "synced_count": int,
                "failed_count": int
            }
        """
        if self.loop_id is None or not approved_knowledge:
            return {"synced_count": 0, "failed_count": 0}

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 開始事務
                cur.execute("BEGIN;")

                # 步驟 1：批次插入到 knowledge_base
                insert_query = """
                    INSERT INTO knowledge_base (
                        vendor_ids,
                        question_summary,
                        answer,
                        action_type,
                        form_id,
                        api_config,
                        intent_id,
                        keywords,
                        embedding,
                        business_types,
                        target_user,
                        scope,
                        priority,
                        source,
                        source_loop_id,
                        source_loop_knowledge_id,
                        created_by,
                        created_at
                    )
                    SELECT
                        ARRAY[(SELECT vendor_id FROM knowledge_completion_loops WHERE id = %s)] AS vendor_ids,
                        %s AS question_summary,
                        %s AS answer,
                        %s AS action_type,
                        %s AS form_id,
                        %s AS api_config,
                        %s AS intent_id,
                        %s AS keywords,
                        %s AS embedding,
                        %s AS business_types,
                        %s AS target_user,
                        %s AS scope,
                        %s AS priority,
                        'loop' AS source,
                        %s AS source_loop_id,
                        %s AS source_loop_knowledge_id,
                        %s AS created_by,
                        NOW() AS created_at
                    RETURNING id, source_loop_knowledge_id
                """

                synced_count = 0
                kb_id_mapping = {}  # loop_knowledge_id -> kb_id

                for knowledge in approved_knowledge:
                    try:
                        cur.execute(
                            insert_query,
                            (
                                self.loop_id,  # 用於查詢 vendor_id
                                knowledge["question"],
                                knowledge["answer"],
                                knowledge["action_type"],
                                knowledge.get("form_id"),
                                psycopg2.extras.Json(knowledge.get("api_config")) if knowledge.get("api_config") else None,
                                knowledge.get("intent_id"),
                                knowledge.get("keywords"),
                                knowledge.get("embedding"),
                                knowledge.get("business_types"),
                                knowledge.get("target_user"),
                                knowledge.get("scope"),
                                knowledge.get("priority"),
                                self.loop_id,
                                knowledge["id"],
                                knowledge.get("reviewed_by", "system")
                            )
                        )
                        result = cur.fetchone()
                        kb_id_mapping[knowledge["id"]] = result["id"]
                        synced_count += 1
                    except Exception as e:
                        print(f"同步知識失敗 (loop_knowledge_id={knowledge['id']}): {str(e)}")
                        continue

                # 步驟 2：更新 loop_generated_knowledge 的同步狀態
                update_query = """
                    UPDATE loop_generated_knowledge
                    SET status = 'synced',
                        synced_to_kb = true,
                        kb_id = %s,
                        synced_at = NOW()
                    WHERE id = %s
                """

                for loop_knowledge_id, kb_id in kb_id_mapping.items():
                    cur.execute(update_query, (kb_id, loop_knowledge_id))

                # 步驟 3：更新迴圈記錄
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET latest_pass_rate = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (new_pass_rate, self.loop_id)
                )

                # 提交事務
                conn.commit()

                return {
                    "synced_count": synced_count,
                    "failed_count": len(approved_knowledge) - synced_count
                }

        except Exception as e:
            conn.rollback()
            raise KnowledgeCompletionError(
                message=f"批次同步知識失敗: {str(e)}",
                category=ErrorCategory.DATABASE_ERROR,
                details={
                    "loop_id": self.loop_id,
                    "iteration": iteration,
                    "knowledge_count": len(approved_knowledge)
                }
            )
        finally:
            self.db_pool.putconn(conn)

    # ============================================
    # 公開方法：待實作
    # ============================================

    async def execute_iteration(self) -> Dict:
        """
        [需求 1.2-1.5] 執行單輪迭代

        工作流程：
        1. 狀態轉換：RUNNING → BACKTESTING
        2. 執行回測
        3. 狀態轉換：BACKTESTING → ANALYZING
        4. 分析缺口
        5. 狀態轉換：ANALYZING → GENERATING
        6. 生成知識
        7. 狀態轉換：GENERATING → REVIEWING
        8. 返回控制權（等待人工審核）

        Returns:
            {
                "iteration": int,
                "status": str,
                "backtest_result": {
                    "pass_rate": float,
                    "total_tested": int,
                    "passed": int,
                    "failed": int
                },
                "gap_analysis": {
                    "total_gaps": int,
                    "p0_count": int,
                    "p1_count": int,
                    "p2_count": int
                },
                "generated_knowledge": {
                    "total_generated": int,
                    "needs_review": int
                },
                "next_action": "wait_for_review"
            }

        Raises:
            InvalidStateError: 當前狀態不允許執行迭代
            BacktestError: 回測執行失敗
            KnowledgeCompletionError: 其他執行錯誤
        """
        # 驗證狀態：PENDING、RUNNING 或 REVIEWING 狀態可以開始迭代
        if self.current_status not in [LoopStatus.PENDING, LoopStatus.RUNNING, LoopStatus.REVIEWING]:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="execute_iteration",
                message="只能在 PENDING、RUNNING 或 REVIEWING 狀態執行迭代"
            )

        # PENDING → RUNNING 狀態轉換
        if self.current_status == LoopStatus.PENDING:
            await self._update_loop_status(LoopStatus.RUNNING)

        if self.loop_id is None or self.config is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="execute_iteration"
            )

        try:
            # 獲取當前迭代次數
            current_iteration = await self._get_current_iteration()
            next_iteration = current_iteration + 1

            # ============================================
            # 重要：立即更新迭代次數
            # ============================================
            # 在執行任何可能失敗的操作前，先更新 current_iteration
            # 這樣即使後續步驟失敗，current_iteration 也與 backtest_runs 記錄一致
            await self._update_iteration_count(next_iteration)

            # ============================================
            # 階段 1：執行回測
            # ============================================
            await self._log_event(
                "iteration_started",
                {"iteration": next_iteration}
            )

            # 狀態轉換：RUNNING → BACKTESTING
            await self._update_loop_status(LoopStatus.BACKTESTING)

            backtest_result = await self.backtest_client.execute_batch_backtest(
                loop_id=self.loop_id,
                iteration=next_iteration,
                vendor_id=self.vendor_id,
                batch_size=self.config.batch_size,
                filters=self.config.filters
            )

            await self._log_event(
                "backtest_completed",
                {
                    "iteration": next_iteration,
                    "pass_rate": backtest_result["pass_rate"],
                    "total_tested": backtest_result["total_tested"],
                    "failed_count": backtest_result["failed"]
                }
            )

            # 如果沒有失敗案例，可能已達標
            if backtest_result["failed"] == 0:
                await self._log_event(
                    "no_failures_detected",
                    {"iteration": next_iteration, "pass_rate": backtest_result["pass_rate"]}
                )
                # 更新通過率並返回 RUNNING（iteration 已經在前面更新）
                await self._update_pass_rate(backtest_result["pass_rate"])
                await self._update_loop_status(LoopStatus.RUNNING)
                return {
                    "iteration": next_iteration,
                    "status": LoopStatus.RUNNING.value,
                    "backtest_result": backtest_result,
                    "gap_analysis": {"total_gaps": 0},
                    "generated_knowledge": {"total_generated": 0},
                    "next_action": "check_completion"
                }

            # ============================================
            # 階段 2：分析知識缺口
            # ============================================
            await self._update_loop_status(LoopStatus.ANALYZING)

            gaps = await self.gap_analyzer.analyze_failures(
                loop_id=self.loop_id,
                iteration=next_iteration,
                backtest_run_id=backtest_result["backtest_run_id"]
            )

            # 統計缺口優先級
            gap_stats = self._calculate_gap_statistics(gaps)

            await self._log_event(
                "gap_analysis_completed",
                {
                    "iteration": next_iteration,
                    "total_gaps": gap_stats["total_gaps"],
                    "priority_distribution": gap_stats
                }
            )

            # ============================================
            # 階段 2.5：智能分類和過濾知識缺口
            # ============================================
            print(f"\n🤖 開始智能分類 {len(gaps)} 個知識缺口...")

            # 執行分類
            classification_result = await self.gap_classifier.classify_gaps(gaps)

            # 記錄分類結果
            summary = classification_result.get("summary", {})
            await self._log_event(
                "gap_classification_completed",
                {
                    "iteration": next_iteration,
                    "total_gaps": len(gaps),
                    "sop_knowledge_count": summary.get("sop_knowledge_count", 0),
                    "api_query_count": summary.get("api_query_count", 0),
                    "form_fill_count": summary.get("form_fill_count", 0),
                    "system_config_count": summary.get("system_config_count", 0),
                    "should_generate_count": summary.get("should_generate_count", 0),
                }
            )

            print(f"📊 分類結果：")
            print(f"   - SOP 知識: {summary.get('sop_knowledge_count', 0)} 題")
            print(f"   - API 查詢: {summary.get('api_query_count', 0)} 題（不生成靜態知識）")
            print(f"   - 表單填寫: {summary.get('form_fill_count', 0)} 題")
            print(f"   - 系統配置: {summary.get('system_config_count', 0)} 題")
            print(f"   → 需要生成知識: {summary.get('should_generate_count', 0)}/{len(gaps)} 題")

            # 使用聚類功能合併相似問題，減少碎片化 SOP
            filtered_gaps = self.gap_classifier.get_clusters_for_generation(gaps, classification_result)

            print(f"✅ 過濾完成：{len(gaps)} 題 → {len(filtered_gaps)} 題需要生成知識")

            # 如果沒有需要生成的知識，記錄並繼續
            if not filtered_gaps:
                await self._log_event(
                    "no_knowledge_to_generate",
                    {
                        "iteration": next_iteration,
                        "reason": "所有失敗案例都是 API 查詢類型，不需要生成靜態知識"
                    }
                )
                # 更新通過率並返回 RUNNING（iteration 已經在前面更新）
                await self._update_pass_rate(backtest_result["pass_rate"])
                await self._update_loop_status(LoopStatus.RUNNING)
                return {
                    "iteration": next_iteration,
                    "status": LoopStatus.RUNNING.value,
                    "backtest_result": backtest_result,
                    "gap_analysis": gap_stats,
                    "classification_result": summary,
                    "generated_knowledge": {"total_generated": 0},
                    "next_action": "check_completion"
                }

            # ============================================
            # 階段 3：生成知識（只針對過濾後的缺口）
            # ============================================
            await self._update_loop_status(LoopStatus.GENERATING)

            # 分離 SOP 類型和一般知識類型
            sop_gaps = [gap for gap in filtered_gaps if gap.get('gap_type') in ['sop_knowledge', 'form_fill']]
            knowledge_gaps = [gap for gap in filtered_gaps if gap.get('gap_type') not in ['sop_knowledge', 'form_fill']]

            print(f"\n🔀 知識類型路由：")
            print(f"   - SOP 類型（sop_knowledge + form_fill）: {len(sop_gaps)} 題")
            print(f"   - 一般知識類型: {len(knowledge_gaps)} 題")

            generated_knowledge = []
            generated_sops = []

            # 處理 SOP 類型（不需要 action_type 判斷）
            if sop_gaps:
                print(f"\n📝 開始生成 SOP...")
                generated_sops = await self.sop_generator.generate_sop_items(
                    loop_id=self.loop_id,
                    vendor_id=self.vendor_id,
                    gaps=sop_gaps,
                    iteration=next_iteration,
                    batch_size=5
                )
                print(f"✅ 已生成 {len(generated_sops)} 筆 SOP")

            # 處理一般知識類型（需要 action_type 判斷）
            if knowledge_gaps:
                print(f"\n📚 開始生成一般知識...")

                # 判斷回應類型（只針對一般知識缺口）
                action_type_judgments = {}
                for gap in knowledge_gaps:
                    judgment = await self.action_classifier.classify_action_type(
                        question=gap["question"],
                        answer="",  # 此階段尚未生成答案，提供空字串
                        vendor_id=self.vendor_id,
                        mode=self.config.action_type_mode
                    )
                    action_type_judgments[gap["gap_id"]] = judgment

                # 生成知識（使用過濾後的一般知識缺口）
                generated_knowledge = await self.knowledge_generator.generate_knowledge(
                    loop_id=self.loop_id,
                    gaps=knowledge_gaps,
                    action_type_judgments=action_type_judgments,
                    iteration=next_iteration
                )
                print(f"✅ 已生成 {len(generated_knowledge)} 筆一般知識")

            knowledge_stats = {
                "total_generated": len(generated_knowledge) + len(generated_sops),
                "knowledge_count": len(generated_knowledge),
                "sop_count": len(generated_sops),
                "needs_review": sum(1 for k in generated_knowledge if k.get("needs_review", True))
            }

            print(f"\n✅ 知識生成總結：")
            print(f"   - 一般知識：{knowledge_stats['knowledge_count']} 筆")
            print(f"   - SOP：{knowledge_stats['sop_count']} 筆")
            print(f"   - 總計：{knowledge_stats['total_generated']} 筆")

            await self._log_event(
                "knowledge_generation_completed",
                {
                    "iteration": next_iteration,
                    "total_generated": knowledge_stats["total_generated"],
                    "knowledge_count": knowledge_stats["knowledge_count"],
                    "sop_count": knowledge_stats["sop_count"],
                    "needs_review": knowledge_stats["needs_review"]
                }
            )

            # ============================================
            # 階段 4：進入人工審核狀態
            # ============================================
            await self._update_loop_status(LoopStatus.REVIEWING)
            # 更新通過率（iteration 已經在前面更新）
            await self._update_pass_rate(backtest_result["pass_rate"])

            await self._log_event(
                "waiting_for_review",
                {
                    "iteration": next_iteration,
                    "generated_count": knowledge_stats["total_generated"]
                }
            )

            return {
                "iteration": next_iteration,
                "status": LoopStatus.REVIEWING.value,
                "backtest_result": {
                    "pass_rate": backtest_result["pass_rate"],
                    "total_tested": backtest_result["total_tested"],
                    "passed": backtest_result["passed"],
                    "failed": backtest_result["failed"]
                },
                "gap_analysis": gap_stats,
                "generated_knowledge": knowledge_stats,
                "next_action": "wait_for_review"
            }

        except BacktestError as e:
            await self._log_event(
                "backtest_error",
                {"iteration": next_iteration, "error": str(e)}
            )
            await self._update_loop_status(LoopStatus.FAILED)
            raise

        except Exception as e:
            await self._log_event(
                "iteration_error",
                {"iteration": next_iteration, "error": str(e), "error_type": type(e).__name__}
            )
            await self._update_loop_status(LoopStatus.FAILED)
            raise KnowledgeCompletionError(
                message=f"迭代執行失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"iteration": next_iteration, "loop_id": self.loop_id}
            )

    async def validate_and_sync(self) -> Dict:
        """
        [需求 3.3] 迭代驗證與批次同步

        審核完成後執行驗證回測，通過則批次同步知識到 knowledge_base

        工作流程：
        1. 狀態轉換：REVIEWING → VALIDATING
        2. 執行迭代驗證回測（使用 UNION ALL 合併臨時知識）
        3. 判斷驗證結果：
           - 如通過：批次同步 → SYNCING → RUNNING
           - 如失敗：返回 REVIEWING 狀態

        Returns:
            {
                "validation_result": {
                    "pass_rate": float,
                    "improvement": float,
                    "total_tested": int
                },
                "sync_result": {
                    "synced_count": int,
                    "failed_count": int
                },
                "status": str,
                "next_action": "continue" | "review_again"
            }

        Raises:
            InvalidStateError: 當前狀態不允許驗證
            KnowledgeCompletionError: 驗證或同步失敗
        """
        # 驗證狀態：只有 REVIEWING 狀態可以執行驗證
        if self.current_status != LoopStatus.REVIEWING:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="validate_and_sync"
            )

        if self.loop_id is None or self.config is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="validate_and_sync"
            )

        try:
            current_iteration = await self._get_current_iteration()

            # ============================================
            # 階段 1：獲取審核通過的知識
            # ============================================
            approved_knowledge = await self._get_approved_knowledge(current_iteration)

            if not approved_knowledge:
                # 沒有審核通過的知識，返回 REVIEWING 要求重新審核
                await self._log_event(
                    "validation_skipped_no_approved_knowledge",
                    {"iteration": current_iteration}
                )
                return {
                    "validation_result": None,
                    "sync_result": {"synced_count": 0, "failed_count": 0},
                    "status": LoopStatus.REVIEWING.value,
                    "next_action": "review_again",
                    "message": "無審核通過的知識，請重新審核"
                }

            # ============================================
            # 階段 2：執行迭代驗證回測
            # ============================================
            await self._update_loop_status(LoopStatus.VALIDATING)

            # 獲取原本失敗的案例 ID
            failed_scenario_ids = await self._get_failed_scenario_ids(current_iteration)

            validation_result = await self.backtest_client.execute_validation_backtest(
                vendor_id=self.vendor_id,
                scenario_ids=failed_scenario_ids,
                use_temp_knowledge=True  # 使用 UNION ALL 查詢
            )

            await self._log_event(
                "validation_backtest_completed",
                {
                    "iteration": current_iteration,
                    "pass_rate": validation_result["pass_rate"],
                    "improvement": validation_result["improvement"],
                    "total_tested": validation_result["total_tested"]
                }
            )

            # ============================================
            # 階段 3：判斷驗證結果
            # ============================================

            # 驗證通過條件：改善幅度 > 5% 或 通過率 > 0.7
            validation_passed = (
                validation_result["improvement"] >= 0.05 or
                validation_result["pass_rate"] >= 0.7
            )

            if not validation_passed:
                # 驗證失敗，返回 REVIEWING 狀態
                await self._update_loop_status(LoopStatus.REVIEWING)
                await self._log_event(
                    "validation_failed",
                    {
                        "iteration": current_iteration,
                        "reason": "improvement_insufficient",
                        "improvement": validation_result["improvement"],
                        "pass_rate": validation_result["pass_rate"]
                    }
                )
                return {
                    "validation_result": validation_result,
                    "sync_result": {"synced_count": 0, "failed_count": 0},
                    "status": LoopStatus.REVIEWING.value,
                    "next_action": "review_again",
                    "message": f"驗證未通過（改善幅度 {validation_result['improvement']:.1%}），請調整知識內容"
                }

            # ============================================
            # 階段 4：批次同步知識到 knowledge_base
            # ============================================
            await self._update_loop_status(LoopStatus.SYNCING)

            sync_result = await self._batch_sync_knowledge(
                current_iteration,
                approved_knowledge,
                validation_result["pass_rate"]
            )

            await self._log_event(
                "knowledge_sync_completed",
                {
                    "iteration": current_iteration,
                    "synced_count": sync_result["synced_count"],
                    "new_pass_rate": validation_result["pass_rate"]
                }
            )

            # ============================================
            # 階段 5：返回 RUNNING 狀態
            # ============================================
            await self._update_loop_status(LoopStatus.RUNNING)

            return {
                "validation_result": validation_result,
                "sync_result": sync_result,
                "status": LoopStatus.RUNNING.value,
                "next_action": "continue",
                "message": f"成功同步 {sync_result['synced_count']} 條知識"
            }

        except Exception as e:
            await self._log_event(
                "validation_sync_error",
                {"iteration": current_iteration, "error": str(e), "error_type": type(e).__name__}
            )
            await self._update_loop_status(LoopStatus.FAILED)
            raise KnowledgeCompletionError(
                message=f"驗證或同步失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"iteration": current_iteration, "loop_id": self.loop_id}
            )

    async def pause_loop(self, reason: str) -> Dict:
        """
        [需求 1.6] 暫停迴圈

        Args:
            reason: 暫停原因

        Returns:
            {
                "loop_id": int,
                "status": "paused",
                "reason": str,
                "paused_at": str
            }

        Raises:
            InvalidStateError: 當前狀態不允許暫停
        """
        # 可暫停的狀態：RUNNING, REVIEWING, VALIDATING
        pausable_states = [LoopStatus.RUNNING, LoopStatus.REVIEWING, LoopStatus.VALIDATING]

        if self.current_status not in pausable_states:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="pause"
            )

        if self.loop_id is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="pause"
            )

        try:
            # 記錄暫停前的狀態
            previous_status = self.current_status

            # 更新狀態為 PAUSED
            await self._update_loop_status(LoopStatus.PAUSED)

            # 記錄暫停事件
            await self._log_event(
                "loop_paused",
                {
                    "reason": reason,
                    "previous_status": previous_status.value,
                    "paused_at": datetime.now().isoformat()
                }
            )

            # 更新資料庫記錄暫停原因
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE knowledge_completion_loops
                        SET paused_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (self.loop_id,)
                    )
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)

            return {
                "loop_id": self.loop_id,
                "status": LoopStatus.PAUSED.value,
                "reason": reason,
                "previous_status": previous_status.value,
                "paused_at": datetime.now().isoformat()
            }

        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"暫停迴圈失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"loop_id": self.loop_id, "reason": reason}
            )

    async def resume_loop(self) -> Dict:
        """
        [需求 1.6] 恢復迴圈

        Returns:
            {
                "loop_id": int,
                "status": str,
                "resumed_at": str
            }

        Raises:
            InvalidStateError: 當前狀態不允許恢復（只有 PAUSED 可以恢復）
        """
        # 只有 PAUSED 狀態可以恢復
        if self.current_status != LoopStatus.PAUSED:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="resume"
            )

        if self.loop_id is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="resume"
            )

        try:
            # 查詢暫停前的狀態（從最後一個 loop_paused 事件）
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT event_data->'previous_status' as previous_status
                        FROM loop_execution_logs
                        WHERE loop_id = %s
                          AND event_type = 'loop_paused'
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (self.loop_id,)
                    )
                    result = cur.fetchone()
                    if result and result["previous_status"]:
                        # 移除 JSON 字串的引號
                        previous_status_str = str(result["previous_status"]).strip('"')
                        previous_status = LoopStatus(previous_status_str)
                    else:
                        # 預設恢復為 RUNNING
                        previous_status = LoopStatus.RUNNING
            finally:
                self.db_pool.putconn(conn)

            # 恢復到暫停前的狀態
            await self._update_loop_status(previous_status)

            # 記錄恢復事件
            await self._log_event(
                "loop_resumed",
                {
                    "resumed_to_status": previous_status.value,
                    "resumed_at": datetime.now().isoformat()
                }
            )

            return {
                "loop_id": self.loop_id,
                "status": previous_status.value,
                "resumed_at": datetime.now().isoformat()
            }

        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"恢復迴圈失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"loop_id": self.loop_id}
            )

    async def cancel_loop(self, reason: str) -> Dict:
        """
        [需求 1.6] 取消迴圈

        取消迴圈（用戶主動取消，可隨時執行）

        Args:
            reason: 取消原因

        Returns:
            {
                "loop_id": int,
                "status": "cancelled",
                "reason": str,
                "cancelled_at": str
            }
        """
        if self.loop_id is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="cancel"
            )

        # 不允許取消已完成或已終止的迴圈
        final_states = [LoopStatus.COMPLETED, LoopStatus.CANCELLED, LoopStatus.TERMINATED]
        if self.current_status in final_states:
            raise InvalidStateError(
                current_state=self.current_status.value,
                target_state="cancel"
            )

        try:
            # 更新狀態為 CANCELLED
            await self._update_loop_status(LoopStatus.CANCELLED)

            # 記錄取消事件
            await self._log_event(
                "loop_cancelled",
                {
                    "reason": reason,
                    "previous_status": self.current_status.value,
                    "cancelled_at": datetime.now().isoformat()
                }
            )

            # 更新資料庫記錄完成時間
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE knowledge_completion_loops
                        SET completed_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (self.loop_id,)
                    )
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)

            return {
                "loop_id": self.loop_id,
                "status": LoopStatus.CANCELLED.value,
                "reason": reason,
                "cancelled_at": datetime.now().isoformat()
            }

        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"取消迴圈失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"loop_id": self.loop_id, "reason": reason}
            )

    async def terminate_loop(self, reason: str) -> Dict:
        """
        終止迴圈

        終止迴圈（系統自動終止，達到完成條件）

        Args:
            reason: 終止原因

        Returns:
            {
                "loop_id": int,
                "status": "completed" | "terminated",
                "reason": str,
                "terminated_at": str
            }
        """
        if self.loop_id is None:
            raise InvalidStateError(
                current_state="UNINITIALIZED",
                target_state="terminate"
            )

        try:
            # 根據原因判斷終止狀態
            # 如果達到目標通過率，標記為 COMPLETED
            # 其他原因標記為 TERMINATED
            if "達到目標通過率" in reason or "target_pass_rate" in reason:
                final_status = LoopStatus.COMPLETED
            else:
                final_status = LoopStatus.TERMINATED

            # 更新狀態
            await self._update_loop_status(final_status)

            # 記錄終止事件
            await self._log_event(
                "loop_terminated",
                {
                    "reason": reason,
                    "final_status": final_status.value,
                    "terminated_at": datetime.now().isoformat()
                }
            )

            # 更新資料庫記錄完成時間
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE knowledge_completion_loops
                        SET completed_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (self.loop_id,)
                    )
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)

            return {
                "loop_id": self.loop_id,
                "status": final_status.value,
                "reason": reason,
                "terminated_at": datetime.now().isoformat()
            }

        except Exception as e:
            raise KnowledgeCompletionError(
                message=f"終止迴圈失敗: {str(e)}",
                category=ErrorCategory.SYSTEM_ERROR,
                details={"loop_id": self.loop_id, "reason": reason}
            )

    async def check_completion_conditions(self) -> tuple[bool, str]:
        """
        [需求 1.5] 檢查迴圈完成條件

        Returns:
            (should_complete, reason)
            - should_complete: 是否應完成迴圈
            - reason: 完成原因

        終止條件：
        1. 達到目標通過率（>= target_pass_rate）
        2. 達到最大迭代次數（>= max_iterations）
        3. 連續 2 輪通過率提升 < 2%（無改善）
        4. 執行時間超過 24 小時
        """
        if self.loop_id is None or self.config is None:
            return False, ""

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查詢迴圈資訊
                cur.execute(
                    """
                    SELECT
                        current_iteration,
                        latest_pass_rate,
                        created_at,
                        started_at
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (self.loop_id,)
                )
                loop_info = cur.fetchone()

                if not loop_info:
                    return False, ""

                current_iteration = loop_info["current_iteration"]
                latest_pass_rate = loop_info["latest_pass_rate"] or 0.0
                started_at = loop_info["started_at"]

                # ============================================
                # 條件 1：達到目標通過率
                # ============================================
                if latest_pass_rate >= self.config.target_pass_rate:
                    return True, f"達到目標通過率 {latest_pass_rate:.1%} (目標: {self.config.target_pass_rate:.1%})"

                # ============================================
                # 條件 2：達到最大迭代次數
                # ============================================
                if current_iteration >= self.config.max_iterations:
                    return True, f"超過最大迭代次數 {current_iteration}/{self.config.max_iterations}"

                # ============================================
                # 條件 3：連續 2 輪通過率提升 < 2%
                # ============================================
                if current_iteration >= 2:
                    # 查詢最近 2 輪的通過率
                    cur.execute(
                        """
                        SELECT event_data->>'iteration' as iteration,
                               (event_data->>'pass_rate')::float as pass_rate
                        FROM loop_execution_logs
                        WHERE loop_id = %s
                          AND event_type = 'backtest_completed'
                        ORDER BY created_at DESC
                        LIMIT 2
                        """,
                        (self.loop_id,)
                    )
                    recent_results = cur.fetchall()

                    if len(recent_results) >= 2:
                        # 計算最近兩輪的改善幅度
                        current_pass_rate = float(recent_results[0]["pass_rate"])
                        previous_pass_rate = float(recent_results[1]["pass_rate"])
                        improvement = current_pass_rate - previous_pass_rate

                        # 如果連續 2 輪改善都小於 2%
                        if improvement < 0.02:
                            # 檢查前一輪的改善幅度
                            if len(recent_results) >= 2:
                                cur.execute(
                                    """
                                    SELECT event_data->>'pass_rate' as pass_rate
                                    FROM loop_execution_logs
                                    WHERE loop_id = %s
                                      AND event_type = 'backtest_completed'
                                    ORDER BY created_at DESC
                                    OFFSET 2 LIMIT 1
                                    """,
                                    (self.loop_id,)
                                )
                                prev_result = cur.fetchone()

                                if prev_result:
                                    prev_prev_pass_rate = float(prev_result["pass_rate"])
                                    prev_improvement = previous_pass_rate - prev_prev_pass_rate

                                    if prev_improvement < 0.02:
                                        return True, f"連續 2 輪無明顯改善（改善幅度 < 2%）"

                # ============================================
                # 條件 4：執行時間超過 24 小時
                # ============================================
                if started_at:
                    from datetime import datetime, timedelta
                    elapsed_time = datetime.now() - started_at
                    max_duration = timedelta(hours=24)

                    if elapsed_time > max_duration:
                        hours = elapsed_time.total_seconds() / 3600
                        return True, f"執行時間超過 24 小時（已執行 {hours:.1f} 小時）"

                # 未達到任何完成條件
                return False, ""

        except Exception as e:
            # 檢查失敗不影響流程，記錄錯誤並返回 False
            print(f"檢查完成條件失敗: {str(e)}")
            return False, ""
        finally:
            self.db_pool.putconn(conn)
