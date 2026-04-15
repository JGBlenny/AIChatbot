"""
回測框架客戶端

整合現有回測框架 V2，支援批次回測與迭代驗證回測
"""

import asyncio
import os
import sys
import datetime
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras


# 動態導入回測框架
# 統一使用 scripts/backtest/ 路徑
try:
    # Docker 環境
    sys.path.insert(0, '/app/scripts/backtest')
    from backtest_framework_async import AsyncBacktestFramework
except ImportError:
    # 本地開發環境
    scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../scripts/backtest'))
    sys.path.insert(0, scripts_path)
    from backtest_framework_async import AsyncBacktestFramework


class BacktestFrameworkClient:
    """回測框架客戶端

    功能：
    1. 批次回測執行（execute_batch_backtest）
    2. 迭代驗證回測（execute_validation_backtest）
    3. 結果持久化到 backtest_runs / backtest_results 表
    4. 進度追蹤
    5. 錯誤處理與重試
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8100",
        db_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None,
        concurrency: int = 5,
        timeout: int = 60,
        retry_times: int = 2
    ):
        """初始化回測客戶端

        Args:
            base_url: RAG API URL
            db_pool: PostgreSQL 連接池
            concurrency: 並發數
            timeout: 超時時間（秒）
            retry_times: 重試次數
        """
        self.base_url = base_url
        self.db_pool = db_pool
        self.concurrency = concurrency
        self.timeout = timeout
        self.retry_times = retry_times

        # 創建回測框架實例
        self.framework = AsyncBacktestFramework(
            base_url=base_url,
            quality_mode="detailed",
            use_database=True,
            concurrency=concurrency,
            default_timeout=timeout,
            default_retry_times=retry_times
        )

    async def execute_batch_backtest(
        self,
        loop_id: int,
        iteration: int,
        vendor_id: int,
        batch_size: int,
        filters: Dict = None,
        scenario_ids: List[int] = None
    ) -> Dict:
        """執行批次回測

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            vendor_id: 業者 ID
            batch_size: 批次大小
            filters: 篩選條件（source, difficulty, intent_ids）
            scenario_ids: 指定測試場景 ID 列表（優先於 batch_size + filters）

        Returns:
            Dict: 回測結果
            {
                "backtest_run_id": int,
                "total_tested": int,
                "passed": int,
                "failed": int,
                "pass_rate": float,
                "failed_scenarios": List[int],
                "duration": float
            }
        """
        if not self.db_pool:
            # Stub 模式：返回模擬數據
            return self._stub_batch_backtest(batch_size)

        start_time = datetime.datetime.now()

        # Step 1: 載入測試場景（優先使用指定的 scenario_ids）
        if scenario_ids:
            scenarios = await self._load_scenarios_by_ids(scenario_ids)
        else:
            scenarios = await self._load_scenarios(
                vendor_id=vendor_id,
                batch_size=batch_size,
                filters=filters
            )

        if not scenarios:
            return {
                "backtest_run_id": None,
                "total_tested": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "failed_scenarios": [],
                "duration": 0.0
            }

        # Step 2: 創建 backtest_runs 記錄
        backtest_run_id = await self._create_backtest_run(
            vendor_id=vendor_id,
            loop_id=loop_id,
            iteration=iteration,
            total_scenarios=len(scenarios),
            test_set_name=f"Loop {loop_id} - Iteration {iteration}"
        )

        # Step 3: 執行回測（使用正確的 vendor_id）
        # 🆕 修復：為每次回測設置正確的 vendor_id
        self.framework.vendor_id = vendor_id
        results = await self.framework.run_backtest_concurrent(
            test_scenarios=scenarios,
            show_progress=False  # 不顯示 tqdm 進度條（避免日誌污染）
        )

        # Step 4: 分析結果
        passed = sum(1 for r in results if r.get('passed') == True)
        failed = sum(1 for r in results if r.get('passed') == False)
        total_tested = len(results)
        pass_rate = passed / total_tested if total_tested > 0 else 0.0

        failed_scenarios = [
            r['scenario_id'] for r in results
            if r.get('passed') == False and r.get('scenario_id')
        ]

        # Step 5: 持久化結果到資料庫
        await self._save_backtest_results(
            backtest_run_id=backtest_run_id,
            results=results
        )

        # Step 6: 更新 backtest_runs 狀態
        duration = (datetime.datetime.now() - start_time).total_seconds()
        await self._complete_backtest_run(
            backtest_run_id=backtest_run_id,
            status="completed",
            executed_scenarios=total_tested,
            duration=duration
        )

        return {
            "backtest_run_id": backtest_run_id,
            "total_tested": total_tested,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "failed_scenarios": failed_scenarios,
            "duration": duration
        }

    async def execute_validation_backtest(
        self,
        loop_id: int,
        iteration: int,
        vendor_id: int,
        scenario_ids: List[int],
        use_temp_knowledge: bool = True
    ) -> Dict:
        """執行迭代驗證回測

        使用 UNION ALL 查詢合併臨時知識，驗證新增知識的效果

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            vendor_id: 業者 ID
            scenario_ids: 要測試的場景 ID 列表（失敗的測試案例）
            use_temp_knowledge: 是否使用臨時知識（UNION ALL 查詢）

        Returns:
            Dict: 驗證結果
            {
                "validation_run_id": int,
                "total_tested": int,
                "passed": int,
                "failed": int,
                "pass_rate": float,
                "improvement": float,  # 相比原始回測的提升幅度
                "duration": float
            }
        """
        if not self.db_pool:
            # Stub 模式
            return self._stub_validation_backtest(len(scenario_ids))

        start_time = datetime.datetime.now()

        # Step 1: 獲取原始通過率（baseline）
        baseline_pass_rate = await self._get_baseline_pass_rate(loop_id, iteration)

        # Step 2: 載入場景詳細資訊
        scenarios = await self._load_scenarios_by_ids(scenario_ids)

        if not scenarios:
            return {
                "validation_run_id": None,
                "total_tested": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "improvement": 0.0,
                "duration": 0.0
            }

        # Step 3: 創建驗證回測記錄
        validation_run_id = await self._create_backtest_run(
            vendor_id=vendor_id,
            loop_id=loop_id,
            iteration=iteration,
            total_scenarios=len(scenarios),
            test_set_name=f"Loop {loop_id} - Validation (Iteration {iteration})",
            description=f"迭代驗證回測（UNION ALL 模式: {use_temp_knowledge}）"
        )

        # Step 4: 如果啟用臨時知識，設定環境變數
        if use_temp_knowledge:
            # TODO: 實作 UNION ALL 查詢邏輯
            # 需要修改 RAG API 支援 loop_id 參數
            # 或者在回測框架中添加 UNION ALL 查詢支援
            pass

        # Step 5: 執行驗證回測
        results = await self.framework.run_backtest_concurrent(
            test_scenarios=scenarios,
            show_progress=False
        )

        # Step 6: 分析結果
        passed = sum(1 for r in results if r.get('passed') == True)
        failed = sum(1 for r in results if r.get('passed') == False)
        total_tested = len(results)
        pass_rate = passed / total_tested if total_tested > 0 else 0.0

        # 計算提升幅度
        improvement = pass_rate - baseline_pass_rate

        # Step 7: 持久化結果
        await self._save_backtest_results(validation_run_id, results)

        duration = (datetime.datetime.now() - start_time).total_seconds()
        await self._complete_backtest_run(
            backtest_run_id=validation_run_id,
            status="completed",
            executed_scenarios=total_tested,
            duration=duration
        )

        return {
            "validation_run_id": validation_run_id,
            "total_tested": total_tested,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "improvement": improvement,
            "duration": duration
        }

    # ============================================
    # 輔助方法
    # ============================================

    async def _load_scenarios(
        self,
        vendor_id: int,
        batch_size: int,
        filters: Dict = None
    ) -> List[Dict]:
        """從資料庫載入測試場景

        Args:
            vendor_id: 業者 ID
            batch_size: 批次大小
            filters: 篩選條件

        Returns:
            List[Dict]: 場景清單
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = """
                    SELECT id, test_question, expected_answer,
                           difficulty, source, expected_intent_id as intent_id
                    FROM test_scenarios
                    WHERE is_active = true
                """
                params = []

                # 添加篩選條件
                if filters:
                    if filters.get('source'):
                        query += " AND source = %s"
                        params.append(filters['source'])
                    if filters.get('difficulty'):
                        query += " AND difficulty = %s"
                        params.append(filters['difficulty'])
                    if filters.get('intent_ids'):
                        query += " AND intent_id = ANY(%s)"
                        params.append(filters['intent_ids'])

                query += " ORDER BY id LIMIT %s"
                params.append(batch_size)

                cur.execute(query, params)
                rows = cur.fetchall()

                return [dict(row) for row in rows]
        finally:
            self.db_pool.putconn(conn)

    async def _load_scenarios_by_ids(self, scenario_ids: List[int]) -> List[Dict]:
        """根據 ID 列表載入場景"""
        if not scenario_ids:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, test_question, expected_answer,
                           difficulty, source, expected_intent_id as intent_id
                    FROM test_scenarios
                    WHERE id = ANY(%s) AND is_active = true
                    ORDER BY id
                """, (scenario_ids,))

                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            self.db_pool.putconn(conn)

    async def _create_backtest_run(
        self,
        vendor_id: int,
        loop_id: int,
        iteration: int,
        total_scenarios: int,
        test_set_name: str,
        description: str = None
    ) -> int:
        """創建回測執行記錄

        Returns:
            int: backtest_run_id
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 匹配實際的 backtest_runs 表結構
                cur.execute("""
                    INSERT INTO backtest_runs (
                        vendor_id, test_type, quality_mode,
                        total_scenarios, executed_scenarios,
                        status, notes, rag_api_url, started_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    vendor_id,
                    "batch",  # test_type
                    "detailed",  # quality_mode
                    total_scenarios,
                    0,  # 初始 executed_scenarios
                    "running",
                    f"Knowledge Completion Loop {loop_id} - Iteration {iteration}",
                    self.base_url  # rag_api_url
                ))

                backtest_run_id = cur.fetchone()[0]
                conn.commit()

                return backtest_run_id
        finally:
            self.db_pool.putconn(conn)

    async def _save_backtest_results(
        self,
        backtest_run_id: int,
        results: List[Dict]
    ):
        """批次保存回測結果到資料庫"""
        if not results:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 準備批次插入數據（匹配實際表結構）
                values = []
                for result in results:
                    passed = result.get('status') == 'passed' or result.get('passed', False)
                    values.append((
                        backtest_run_id,  # run_id
                        result.get('scenario_id'),
                        result.get('test_question', ''),
                        result.get('expected_category'),
                        result.get('actual_intent'),
                        result.get('system_answer', ''),
                        result.get('confidence', 0.0),
                        result.get('score', 0.0),
                        result.get('overall_score', 0.0),
                        passed,
                        result.get('source_count', 0),
                        result.get('relevance'),
                        result.get('completeness'),
                        result.get('accuracy'),
                        result.get('intent_match'),
                        result.get('quality_overall'),
                        psycopg2.extras.Json(result.get('evaluation', {})),
                        psycopg2.extras.Json(result.get('response_metadata', {}))
                    ))

                # 批次插入
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO backtest_results (
                        run_id, scenario_id, test_question,
                        expected_category, actual_intent, system_answer,
                        confidence, score, overall_score, passed, source_count,
                        relevance, completeness, accuracy, intent_match, quality_overall,
                        evaluation, response_metadata, tested_at
                    )
                    VALUES %s
                    """,
                    values,
                    template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())"
                )

                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    async def _complete_backtest_run(
        self,
        backtest_run_id: int,
        status: str,
        executed_scenarios: int,
        duration: float
    ):
        """完成回測執行，更新狀態"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE backtest_runs
                    SET status = %s,
                        executed_scenarios = %s,
                        completed_at = NOW(),
                        duration_seconds = %s
                    WHERE id = %s
                """, (status, executed_scenarios, int(duration), backtest_run_id))

                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    async def _get_baseline_pass_rate(self, loop_id: int, iteration: int) -> float:
        """獲取原始回測的通過率（baseline）"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'passed') * 1.0 /
                        NULLIF(COUNT(*), 0) as pass_rate
                    FROM backtest_results br
                    JOIN backtest_runs run ON br.backtest_run_id = run.id
                    WHERE run.metadata->>'loop_id' = %s
                      AND run.metadata->>'iteration' = %s
                      AND run.description NOT LIKE '%%Validation%%'
                    ORDER BY run.created_at DESC
                    LIMIT 1
                """, (str(loop_id), str(iteration)))

                result = cur.fetchone()
                return result[0] if result and result[0] else 0.0
        finally:
            self.db_pool.putconn(conn)

    # ============================================
    # Stub 方法（用於測試）
    # ============================================

    def _stub_batch_backtest(self, batch_size: int) -> Dict:
        """Stub：模擬批次回測結果"""
        passed = int(batch_size * 0.6)
        failed = batch_size - passed

        return {
            "backtest_run_id": 999,
            "total_tested": batch_size,
            "passed": passed,
            "failed": failed,
            "pass_rate": 0.6,
            "failed_scenarios": list(range(1, failed + 1)),
            "duration": 15.5
        }

    def _stub_validation_backtest(self, scenario_count: int) -> Dict:
        """Stub：模擬驗證回測結果"""
        passed = int(scenario_count * 0.75)
        failed = scenario_count - passed

        return {
            "validation_run_id": 888,
            "total_tested": scenario_count,
            "passed": passed,
            "failed": failed,
            "pass_rate": 0.75,
            "improvement": 0.15,  # 提升 15%
            "duration": 8.2
        }
