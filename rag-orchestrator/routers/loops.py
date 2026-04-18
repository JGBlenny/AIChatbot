"""
迴圈管理 API 路由

提供知識完善迴圈的完整生命週期管理：
- 啟動迴圈
- 執行迭代（同步/非同步）
- 查詢狀態
- 驗證回測
- 暫停/恢復/取消
- 完成批次
- 啟動下一批次

Author: AI Assistant
Created: 2026-03-27
"""

import os
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import psycopg2.pool
from psycopg2.extras import RealDictCursor

# 導入服務層
from services.knowledge_completion_loop.models import (
    LoopStatus,
    LoopConfig,
    InvalidStateError,
    LoopNotFoundError
)
from services.knowledge_completion_loop.scenario_selector import (
    ScenarioSelector,
    SelectionStrategy,
    DifficultyDistribution
)
from services.knowledge_completion_loop.async_execution_manager import (
    AsyncExecutionManager,
    ConcurrentExecutionError
)

router = APIRouter()

# 全局連接池（同步）- 用於協調器
_sync_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
_async_execution_manager: Optional[AsyncExecutionManager] = None

def get_sync_pool() -> psycopg2.pool.SimpleConnectionPool:
    """取得同步資料庫連接池（用於 LoopCoordinator）"""
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.getenv("DB_HOST", "postgres"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "aichatbot_admin"),
            user=os.getenv("DB_USER", "aichatbot"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        )
    return _sync_pool

def get_async_execution_manager(req: Request) -> AsyncExecutionManager:
    """取得非同步執行管理器"""
    global _async_execution_manager
    if _async_execution_manager is None:
        # 使用 Request 物件取得 asyncpg pool
        db_pool = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')
        _async_execution_manager = AsyncExecutionManager(db_pool)
    return _async_execution_manager


# ============================================
# Request/Response Models
# ============================================

class LoopStartRequest(BaseModel):
    """
    啟動迴圈請求

    用於創建新的知識完善迴圈。系統會自動排除歷史回測已測過的題目。
    """
    loop_name: str = Field(..., description="迴圈名稱", max_length=200)
    vendor_id: int = Field(..., description="業者 ID", gt=0)
    batch_size: int = Field(50, description="批次大小", ge=1, le=3000)
    target_pass_rate: float = Field(0.85, description="目標通過率", ge=0.0, le=1.0)
    scenario_filters: Optional[Dict] = Field(None, description="測試情境篩選條件")
    budget_limit_usd: Optional[float] = Field(None, description="成本預算上限（USD）", ge=0)
    backtest_only: bool = Field(False, description="僅回測不生成知識")

    class Config:
        json_schema_extra = {
            "example": {
                "loop_name": "包租業知識完善-第1批",
                "vendor_id": 2,
                "batch_size": 50,
                "target_pass_rate": 0.85,
                "budget_limit_usd": 50.0
            }
        }


class LoopStartResponse(BaseModel):
    """
    啟動迴圈回應

    返回新建立的迴圈詳細資訊，包含選取的固定測試集。
    scenario_ids 在迴圈的所有迭代中保持不變，確保結果可比較性。
    """
    loop_id: int = Field(description="迴圈 ID")
    loop_name: str = Field(description="迴圈名稱")
    vendor_id: int = Field(description="業者 ID")
    status: str = Field(description="迴圈狀態（pending/running）")
    scenario_ids: List[int] = Field(description="固定測試集 ID 列表")
    scenario_selection_strategy: str = Field(description="選取策略（stratified_random/sequential/full_random）")
    difficulty_distribution: Dict[str, int] = Field(description="難度分布（easy/medium/hard 數量）")
    initial_statistics: Dict = Field(description="初始統計資訊")
    created_at: str = Field(description="創建時間（ISO 8601 格式）")


class ExecuteIterationRequest(BaseModel):
    """執行迭代請求"""
    async_mode: bool = Field(True, description="是否非同步執行")


class ExecuteIterationResponse(BaseModel):
    """執行迭代回應"""
    loop_id: int
    current_iteration: int
    status: str
    message: str
    backtest_result: Optional[Dict] = None  # 同步模式時返回完整結果
    execution_task_id: Optional[str] = None  # 非同步模式時返回任務 ID


class LoopStatusResponse(BaseModel):
    """迴圈狀態回應"""
    loop_id: int
    loop_name: str
    vendor_id: int
    status: str
    current_iteration: int
    current_pass_rate: Optional[float]
    target_pass_rate: float
    scenario_ids: List[int]
    total_scenarios: int
    progress: Dict  # {phase: str, percentage: float, message: str}
    created_at: str
    updated_at: str
    completed_at: Optional[str]


class ValidateLoopRequest(BaseModel):
    """驗證迴圈請求"""
    validation_scope: str = Field("failed_plus_sample", description="驗證範圍")
    sample_pass_rate: float = Field(0.2, description="抽樣比例", ge=0.0, le=1.0)


class ValidateLoopResponse(BaseModel):
    """驗證迴圈回應"""
    loop_id: int
    validation_result: Dict
    validation_passed: bool
    affected_knowledge_ids: List[int]
    regression_detected: bool
    regression_count: int
    next_action: str


class CompleteBatchResponse(BaseModel):
    """完成批次回應"""
    loop_id: int
    status: str
    summary: Dict
    message: str


# ============================================
# API Endpoints (骨架)
# ============================================

@router.post("/start", response_model=LoopStartResponse)
async def start_loop(request: LoopStartRequest, req: Request):
    """
    [需求 10.1, 10.4] 啟動新迴圈

    - 建立新的迴圈記錄
    - 選取固定測試集（分層隨機抽樣）
    - 初始化成本追蹤器
    """
    try:
        # Lazy import coordinator to avoid circular dependency
        from services.knowledge_completion_loop.coordinator import LoopCoordinator

        # 1. 初始化場景選取器（使用 asyncpg pool）
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')
        scenario_selector = ScenarioSelector(db_pool_async)

        # 2. 自動排除所有歷史回測已測過的題目
        exclude_scenario_ids = await scenario_selector.get_used_scenario_ids()

        # 3. 選取固定測試集（分層隨機抽樣）
        selection_result = await scenario_selector.select_scenarios(
            batch_size=request.batch_size,
            collection_id=None,  # 實際資料庫無 vendor_id，使用 collection_id
            strategy=SelectionStrategy.STRATIFIED_RANDOM,
            distribution=DifficultyDistribution(),  # 使用預設分布（easy 20%, medium 50%, hard 30%）
            exclude_scenario_ids=exclude_scenario_ids,
            filters=request.scenario_filters or {}  # 確保不傳遞 None
        )

        # 4. 初始化 LoopCoordinator（使用同步 pool）
        sync_pool = get_sync_pool()
        coordinator = LoopCoordinator(
            db_pool=sync_pool,
            vendor_id=request.vendor_id,
            loop_name=request.loop_name,
            backtest_base_url=os.getenv("BACKTEST_BASE_URL", "http://localhost:8100"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # 5. 創建迴圈配置
        loop_config = LoopConfig(
            vendor_id=request.vendor_id,
            batch_size=request.batch_size,
            target_pass_rate=request.target_pass_rate,
            scenario_ids=selection_result["scenario_ids"],
            selection_strategy=selection_result["selection_strategy"],
            difficulty_distribution=selection_result["difficulty_distribution"],
            budget_limit_usd=request.budget_limit_usd,
            filters=request.scenario_filters or {},  # 確保不傳遞 None
            backtest_only=request.backtest_only
        )

        # 6. 啟動迴圈（使用 to_thread 包裝同步 DB 操作的 async 方法）
        # 注意：coordinator 的 async 方法內部使用同步 psycopg2，需要用 to_thread 包裝
        import asyncio
        # 直接調用 async 方法（它內部會在線程池中執行同步 DB 操作）
        loop_result = await coordinator.start_loop(loop_config)

        # 7. 返回回應
        return LoopStartResponse(
            loop_id=loop_result["loop_id"],
            loop_name=loop_result["loop_name"],
            vendor_id=loop_result["vendor_id"],
            status=loop_result["status"],
            scenario_ids=selection_result["scenario_ids"],
            scenario_selection_strategy=selection_result["selection_strategy"],
            difficulty_distribution=selection_result["difficulty_distribution"],
            initial_statistics=loop_result["initial_statistics"],
            created_at=loop_result["created_at"]
        )

    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=f"狀態錯誤：{str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"參數錯誤：{str(e)}")
    except Exception as e:
        print(f"❌ 啟動迴圈失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"啟動迴圈失敗：{str(e)}")


@router.post("/{loop_id}/execute-iteration", response_model=ExecuteIterationResponse)
async def execute_iteration(
    loop_id: int,
    request: ExecuteIterationRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    [需求 10.2] 執行迭代

    - 支援非同步執行模式（預設）
    - 執行完整的 8 步驟流程
    - 防止並發執行
    """
    try:
        # Lazy import coordinator to avoid circular dependency
        from services.knowledge_completion_loop.coordinator import LoopCoordinator

        # 1. 載入迴圈
        sync_pool = get_sync_pool()
        coordinator = LoopCoordinator(
            db_pool=sync_pool,
            vendor_id=0,  # 將在 load_loop 時更新
            loop_name="",
            backtest_base_url=os.getenv("BACKTEST_BASE_URL", "http://localhost:8100"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # 載入現有迴圈
        # 注意：coordinator.load_loop() 是偽 async（使用同步 DB 但標記為 async）
        def load_loop_sync():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coordinator.load_loop(loop_id))
            finally:
                loop.close()

        load_result = await asyncio.to_thread(load_loop_sync)

        # 2. 檢查狀態是否為 RUNNING、PENDING 或 REVIEWING
        # 允許從 REVIEWING 狀態執行，因為審核完成後需要執行驗證回測
        if load_result["status"] not in ["running", "pending", "reviewing"]:
            raise HTTPException(
                status_code=409,
                detail=f"迴圈狀態必須為 RUNNING、PENDING 或 REVIEWING，當前為 {load_result['status']}"
            )

        # 3. 執行迭代
        if request.async_mode:
            # 非同步模式：立即返回，背景執行
            async_manager = get_async_execution_manager(req)

            # 檢查並發執行
            if async_manager.is_running(loop_id):
                raise HTTPException(
                    status_code=409,
                    detail=f"迴圈 {loop_id} 已在執行中，無法並發執行"
                )

            # 啟動背景任務
            task_id = await async_manager.start_iteration(coordinator, loop_id)

            return ExecuteIterationResponse(
                loop_id=loop_id,
                current_iteration=load_result["current_iteration"],
                status="RUNNING",
                message="迭代已在背景執行",
                execution_task_id=task_id
            )

        else:
            # 同步模式：等待執行完成
            # 注意：coordinator.execute_iteration() 是偽 async（使用同步 DB 但標記為 async）
            # 需要在新的 event loop 中執行
            def run_iteration_sync():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coordinator.execute_iteration())
                finally:
                    loop.close()

            iteration_result = await asyncio.to_thread(run_iteration_sync)

            return ExecuteIterationResponse(
                loop_id=loop_id,
                current_iteration=iteration_result.get("current_iteration", load_result["current_iteration"] + 1),
                status="REVIEWING",
                message="迭代執行完成，等待審核",
                backtest_result=iteration_result
            )

    except HTTPException:
        # HTTPException 直接重新拋出，保留原始 status_code 和 detail
        raise
    except ConcurrentExecutionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=f"狀態錯誤：{str(e)}")
    except LoopNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"迴圈不存在：{str(e)}")
    except Exception as e:
        print(f"❌ 執行迭代失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"執行迭代失敗：{str(e)}")


@router.get("/coverage-stats")
async def get_coverage_stats(req: Request):
    """
    取得回測覆蓋率統計

    返回題庫總題數、已測過的題數、覆蓋率百分比。
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            # 題庫中所有 active 題目數
            total_scenarios = await conn.fetchval("""
                SELECT COUNT(*) FROM test_scenarios WHERE is_active = true
            """)

            # 從 backtest_results 查實際測過的不重複題目數
            covered_scenarios = await conn.fetchval("""
                SELECT COUNT(DISTINCT scenario_id)
                FROM backtest_results
                WHERE scenario_id IS NOT NULL
            """)

            # 各迴圈（含 backtest_run）的覆蓋明細
            loop_details = await conn.fetch("""
                SELECT
                    kcl.id AS loop_id,
                    kcl.loop_name,
                    kcl.status,
                    COALESCE(sub.tested_count, 0) AS scenario_count,
                    kcl.current_pass_rate
                FROM knowledge_completion_loops kcl
                LEFT JOIN (
                    SELECT
                        CAST(substring(br.notes FROM 'Loop (\d+)') AS INTEGER) AS loop_id,
                        COUNT(DISTINCT bres.scenario_id) AS tested_count
                    FROM backtest_runs br
                    JOIN backtest_results bres ON bres.run_id = br.id
                    WHERE br.notes LIKE 'Knowledge Completion Loop %'
                      AND bres.scenario_id IS NOT NULL
                    GROUP BY substring(br.notes FROM 'Loop (\d+)')
                ) sub ON sub.loop_id = kcl.id
                ORDER BY kcl.id
            """)

            coverage_rate = (covered_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

            return {
                "total_scenarios": total_scenarios,
                "covered_scenarios": covered_scenarios,
                "uncovered_scenarios": total_scenarios - covered_scenarios,
                "coverage_rate": round(coverage_rate, 1),
                "loop_details": [
                    {
                        "loop_id": row["loop_id"],
                        "loop_name": row["loop_name"],
                        "status": row["status"],
                        "scenario_count": row["scenario_count"],
                        "current_pass_rate": float(row["current_pass_rate"]) if row["current_pass_rate"] else None
                    }
                    for row in loop_details
                ]
            }

    except Exception as e:
        print(f"❌ 取得覆蓋率統計失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得覆蓋率統計失敗：{str(e)}")


@router.get("/", response_model=List[LoopStatusResponse])
async def list_loops(
    req: Request,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    [新增] 列出所有迴圈

    - 支援按 vendor_id 和 status 篩選
    - 支援分頁（limit/offset）
    - 按更新時間倒序排列
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        # 構建查詢條件
        conditions = []
        params = []
        param_count = 1

        if vendor_id is not None:
            conditions.append(f"vendor_id = ${param_count}")
            params.append(vendor_id)
            param_count += 1

        if status is not None:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # 查詢迴圈列表
        async with db_pool_async.acquire() as conn:
            query = f"""
                SELECT
                    id, loop_name, vendor_id, status,
                    current_iteration,
                    current_pass_rate, target_pass_rate,
                    scenario_ids,
                    created_at, updated_at, completed_at
                FROM knowledge_completion_loops
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            params.extend([limit, offset])

            loop_records = await conn.fetch(query, *params)

            # 為每個迴圈構建回應
            results = []
            for loop_record in loop_records:
                # 查詢最新執行事件（取得進度資訊）
                latest_event = await conn.fetchrow("""
                    SELECT event_type, event_data, created_at
                    FROM loop_execution_logs
                    WHERE loop_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, loop_record["id"])

                # 構建進度資訊
                progress = {"phase": "unknown", "percentage": 0.0, "message": ""}
                if latest_event:
                    event_type = latest_event["event_type"]
                    phase_map = {
                        "loop_started": {"phase": "initialized", "percentage": 0.0},
                        "backtest_started": {"phase": "backtesting", "percentage": 10.0},
                        "backtest_completed": {"phase": "analyzing", "percentage": 30.0},
                        "gaps_analyzed": {"phase": "classifying", "percentage": 50.0},
                        "gaps_classified": {"phase": "generating", "percentage": 70.0},
                        "knowledge_generated": {"phase": "reviewing", "percentage": 90.0},
                        "iteration_completed": {"phase": "completed", "percentage": 100.0}
                    }
                    progress = phase_map.get(event_type, progress)
                    progress["message"] = event_type

                # 從 backtest_runs 取實際測試題數（scenario_ids 可能為 NULL）
                actual_scenario_ids = loop_record["scenario_ids"] or []
                if not actual_scenario_ids:
                    loop_id_str = str(loop_record["id"])
                    tested_count = await conn.fetchval("""
                        SELECT COALESCE(MAX(total_scenarios), 0)
                        FROM backtest_runs
                        WHERE notes LIKE 'Knowledge Completion Loop ' || $1 || ' - %'
                    """, loop_id_str)
                else:
                    tested_count = len(actual_scenario_ids)

                results.append(LoopStatusResponse(
                    loop_id=loop_record["id"],
                    loop_name=loop_record["loop_name"],
                    vendor_id=loop_record["vendor_id"],
                    status=loop_record["status"],
                    current_iteration=loop_record["current_iteration"] or 0,
                    current_pass_rate=float(loop_record["current_pass_rate"]) if loop_record["current_pass_rate"] else None,
                    target_pass_rate=float(loop_record["target_pass_rate"]) if loop_record["target_pass_rate"] else 0.85,
                    scenario_ids=actual_scenario_ids,
                    total_scenarios=tested_count,
                    progress=progress,
                    created_at=loop_record["created_at"].isoformat() if loop_record["created_at"] else "",
                    updated_at=loop_record["updated_at"].isoformat() if loop_record["updated_at"] else "",
                    completed_at=loop_record["completed_at"].isoformat() if loop_record["completed_at"] else None
                ))

            return results

    except Exception as e:
        print(f"❌ 列出迴圈失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"列出迴圈失敗：{str(e)}")


@router.get("/{loop_id}/iterations")
async def get_loop_iterations(
    loop_id: int,
    req: Request
):
    """
    [任務 11.2.3] 查詢迴圈迭代歷史（含回測結果）

    從 backtest_runs 和 loop_execution_logs 查詢每次迭代的詳細記錄
    """
    try:
        pool = req.app.state.db_pool
        async with pool.acquire() as conn:
            # 查詢迭代的回測記錄，從 backtest_results 即時計算通過/失敗數
            records = await conn.fetch("""
                SELECT
                    br.id as run_id,
                    CAST(SUBSTRING(br.notes FROM 'Iteration (\\d+)') AS INTEGER) as iteration,
                    br.total_scenarios,
                    br.executed_scenarios,
                    COALESCE(stats.passed_count, br.passed_count, 0) as passed_count,
                    COALESCE(stats.failed_count, br.failed_count, 0) as failed_count,
                    COALESCE(stats.calc_pass_rate, br.pass_rate, 0) as pass_rate,
                    COALESCE(stats.avg_score, br.avg_score, 0) as avg_score,
                    br.started_at,
                    br.completed_at,
                    br.status
                FROM backtest_runs br
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) FILTER (WHERE passed = true) as passed_count,
                        COUNT(*) FILTER (WHERE passed = false) as failed_count,
                        CASE WHEN COUNT(*) > 0
                            THEN COUNT(*) FILTER (WHERE passed = true)::float / COUNT(*)
                            ELSE 0 END as calc_pass_rate,
                        AVG(overall_score) as avg_score
                    FROM backtest_results
                    WHERE run_id = br.id
                ) stats ON true
                WHERE br.notes LIKE $1
                  AND br.status = 'completed'
                ORDER BY br.started_at ASC
            """, f'%Loop {loop_id}%')

            iterations = []
            for record in records:
                iter_num = record["iteration"] if record["iteration"] else 0

                # 查詢該迭代生成的知識數量
                knowledge_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM loop_generated_knowledge
                    WHERE loop_id = $1 AND iteration = $2
                """, loop_id, iter_num)

                iterations.append({
                    "run_id": record["run_id"],
                    "iteration": iter_num,
                    "total": record["total_scenarios"] or 0,
                    "passed": record["passed_count"] or 0,
                    "failed": record["failed_count"] or 0,
                    "pass_rate": float(record["pass_rate"]) if record["pass_rate"] else 0.0,
                    "avg_score": float(record["avg_score"]) if record["avg_score"] else 0.0,
                    "knowledge_generated": knowledge_count or 0,
                    "started_at": record["started_at"].isoformat() if record["started_at"] else None,
                    "completed_at": record["completed_at"].isoformat() if record["completed_at"] else None,
                    "status": record["status"]
                })

            return iterations

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢迭代歷史失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢迭代歷史失敗：{str(e)}")


@router.get("/{loop_id}/iterations/{iteration}/backtest-results")
async def get_iteration_backtest_results(
    loop_id: int,
    iteration: int,
    req: Request,
    limit: int = 100,
    offset: int = 0
):
    """
    查詢特定迭代的回測詳細結果

    Returns:
        包含回測結果列表和統計信息
    """
    try:
        pool = req.app.state.db_pool
        async with pool.acquire() as conn:
            # 查詢 backtest_run_id
            run_record = await conn.fetchrow("""
                SELECT id, passed_count, failed_count, pass_rate, total_scenarios
                FROM backtest_runs
                WHERE notes LIKE $1
                  AND notes LIKE $2
                LIMIT 1
            """, f'%Loop {loop_id}%', f'%Iteration {iteration}%')

            if not run_record:
                return {"results": [], "total": 0, "summary": None}

            run_id = run_record["id"]

            # 查詢回測結果（包含 evaluation 和 response_metadata）
            results = await conn.fetch("""
                SELECT
                    br.id,
                    br.scenario_id,
                    br.test_question,
                    br.system_answer,
                    br.passed,
                    br.confidence,
                    br.overall_score,
                    br.relevance,
                    br.completeness,
                    br.accuracy,
                    br.source_count,
                    br.tested_at,
                    br.evaluation,
                    br.actual_intent,
                    br.response_metadata
                FROM backtest_results br
                WHERE br.run_id = $1
                ORDER BY br.id
                LIMIT $2 OFFSET $3
            """, run_id, limit, offset)

            # 獲取總數
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM backtest_results WHERE run_id = $1
            """, run_id)

            result_list = []
            for r in results:
                # 從 evaluation JSON 提取 confidence_score, confidence_level
                # asyncpg 將 jsonb 解析為字串，需要手動 parse
                # 注意：某些情況下數據可能被雙重 JSON 編碼，需要處理
                evaluation = {}

                if r["evaluation"] and isinstance(r["evaluation"], str):
                    try:
                        parsed = json.loads(r["evaluation"])

                        # 如果第一次解碼後還是字串，說明被雙重編碼了，需要再解碼一次
                        if isinstance(parsed, str):
                            parsed = json.loads(parsed)

                        evaluation = parsed
                    except Exception as e:
                        print(f"⚠️ 解析 evaluation JSON 失敗 (ID={r['id']}): {e}")
                        evaluation = {}
                elif r["evaluation"] and isinstance(r["evaluation"], dict):
                    evaluation = r["evaluation"]

                # 優先使用 evaluation 的 confidence_score，否則 fallback 到 0（因為沒有 RAG 結果）
                # 注意：r["confidence"] 是意圖分類信心度，不應該用於 RAG 信心度
                confidence_score = float(evaluation.get("confidence_score", 0.0)) if isinstance(evaluation, dict) else 0.0

                # 根據 source_count 判斷信心度等級（如果 evaluation 沒有提供）
                if isinstance(evaluation, dict) and evaluation.get("confidence_level"):
                    confidence_level = evaluation.get("confidence_level")
                else:
                    # Fallback：根據 source_count 和 confidence_score 判斷
                    if r["source_count"] == 0:
                        confidence_level = "low"
                    elif confidence_score >= 0.85:
                        confidence_level = "high"
                    elif confidence_score >= 0.70:
                        confidence_level = "medium"
                    else:
                        confidence_level = "low"

                # 解析 response_metadata（處理流程詳情）
                response_metadata = {}
                if r["response_metadata"]:
                    if isinstance(r["response_metadata"], str):
                        try:
                            parsed = json.loads(r["response_metadata"])
                            if isinstance(parsed, str):
                                parsed = json.loads(parsed)
                            response_metadata = parsed
                        except:
                            response_metadata = {}
                    elif isinstance(r["response_metadata"], dict):
                        response_metadata = r["response_metadata"]

                result_list.append({
                    "id": r["id"],
                    "scenario_id": r["scenario_id"],
                    "test_question": r["test_question"] or "",
                    "system_answer": r["system_answer"] or "",
                    "expected_category": None,  # backtest_results 沒有這個欄位
                    "actual_intent": r["actual_intent"],
                    "passed": r["passed"],
                    "confidence": float(r["confidence"]) if r["confidence"] else 0.0,  # 意圖分類信心度
                    "confidence_score": confidence_score,  # RAG 檢索信心度（從 evaluation 提取）
                    "confidence_level": confidence_level,  # RAG 檢索信心度等級
                    "overall_score": float(r["overall_score"]) if r["overall_score"] else 0.0,
                    "relevance": float(r["relevance"]) if r["relevance"] else None,
                    "completeness": float(r["completeness"]) if r["completeness"] else None,
                    "accuracy": float(r["accuracy"]) if r["accuracy"] else None,
                    "source_count": r["source_count"] or 0,
                    "tested_at": r["tested_at"].isoformat() if r["tested_at"] else None,
                    "debug_info": response_metadata if response_metadata else None  # 處理流程詳情
                })

            return {
                "results": result_list,
                "total": total,
                "summary": {
                    "run_id": run_id,
                    "total": run_record["total_scenarios"] or 0,
                    "passed": run_record["passed_count"] or 0,
                    "failed": run_record["failed_count"] or 0,
                    "pass_rate": float(run_record["pass_rate"]) if run_record["pass_rate"] else 0.0,
                    "avg_score": 0.0  # 暫時設為 0，後續可從結果計算
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢回測結果失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢回測結果失敗：{str(e)}")


@router.get("/{loop_id}", response_model=LoopStatusResponse)
async def get_loop_status(loop_id: int, req: Request):
    """
    [需求 10.2] 查詢迴圈狀態

    - 返回當前狀態與進度
    - 前端輪詢使用
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        # 從資料庫查詢迴圈記錄
        async with db_pool_async.acquire() as conn:
            loop_record = await conn.fetchrow("""
                SELECT
                    id, loop_name, vendor_id, status,
                    current_iteration,
                    current_pass_rate, target_pass_rate,
                    scenario_ids,
                    created_at, updated_at, completed_at
                FROM knowledge_completion_loops
                WHERE id = $1
            """, loop_id)

            if not loop_record:
                raise HTTPException(status_code=404, detail=f"迴圈 {loop_id} 不存在")

            # 查詢最新執行事件（取得進度資訊）
            latest_event = await conn.fetchrow("""
                SELECT event_type, event_data, created_at
                FROM loop_execution_logs
                WHERE loop_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, loop_id)

            # 構建進度資訊
            progress = {"phase": "unknown", "percentage": 0.0, "message": ""}
            if latest_event:
                event_type = latest_event["event_type"]
                # 根據事件類型判斷進度
                phase_map = {
                    "loop_started": {"phase": "initialized", "percentage": 0.0},
                    "backtest_started": {"phase": "backtesting", "percentage": 10.0},
                    "backtest_completed": {"phase": "analyzing", "percentage": 30.0},
                    "gaps_analyzed": {"phase": "classifying", "percentage": 50.0},
                    "gaps_classified": {"phase": "generating", "percentage": 70.0},
                    "knowledge_generated": {"phase": "reviewing", "percentage": 90.0},
                    "iteration_completed": {"phase": "completed", "percentage": 100.0}
                }
                progress = phase_map.get(event_type, progress)
                progress["message"] = event_type

            return LoopStatusResponse(
                loop_id=loop_record["id"],
                loop_name=loop_record["loop_name"],
                vendor_id=loop_record["vendor_id"],
                status=loop_record["status"],
                current_iteration=loop_record["current_iteration"] or 0,
                current_pass_rate=float(loop_record["current_pass_rate"]) if loop_record["current_pass_rate"] else None,
                target_pass_rate=float(loop_record["target_pass_rate"]) if loop_record["target_pass_rate"] else 0.85,
                scenario_ids=loop_record["scenario_ids"] or [],
                total_scenarios=len(loop_record["scenario_ids"]) if loop_record["scenario_ids"] else 0,
                progress=progress,
                created_at=loop_record["created_at"].isoformat() if loop_record["created_at"] else "",
                updated_at=loop_record["updated_at"].isoformat() if loop_record["updated_at"] else "",
                completed_at=loop_record["completed_at"].isoformat() if loop_record["completed_at"] else None
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢迴圈狀態失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢迴圈狀態失敗：{str(e)}")


@router.post("/{loop_id}/validate", response_model=ValidateLoopResponse)
async def validate_loop(
    loop_id: int,
    request: ValidateLoopRequest,
    req: Request
):
    """
    [需求 9] 驗證效果回測（可選功能）

    - 執行驗證回測
    - 支援三種驗證範圍
    - 檢測 regression
    """
    try:
        # Lazy import to avoid import errors
        from services.knowledge_completion_loop.coordinator import LoopCoordinator
        from services.knowledge_completion_loop.models import InvalidStateError, LoopNotFoundError

        sync_pool = get_sync_pool()
        coordinator = LoopCoordinator(
            db_pool=sync_pool,
            vendor_id=0,
            loop_name="",
            backtest_base_url=os.getenv("BACKTEST_BASE_URL", "http://localhost:8100"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # 載入迴圈
        import asyncio
        await asyncio.to_thread(coordinator.load_loop, loop_id)

        # 執行驗證回測
        validation_result = await asyncio.to_thread(
            coordinator.validate_loop,
            validation_scope=request.validation_scope,
            sample_pass_rate=request.sample_pass_rate
        )

        return ValidateLoopResponse(
            loop_id=loop_id,
            validation_result=validation_result["validation_result"],
            validation_passed=validation_result["validation_passed"],
            affected_knowledge_ids=validation_result.get("affected_knowledge_ids", []),
            regression_detected=validation_result["regression_detected"],
            regression_count=validation_result["regression_count"],
            next_action=validation_result["next_action"]
        )

    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=f"狀態錯誤：{str(e)}")
    except LoopNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"迴圈不存在：{str(e)}")
    except Exception as e:
        print(f"❌ 驗證回測失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"驗證回測失敗：{str(e)}")


@router.post("/{loop_id}/complete-batch", response_model=CompleteBatchResponse)
async def complete_batch(loop_id: int, req: Request):
    """
    [需求 10.4] 完成批次

    - 標記迴圈為 COMPLETED
    - 返回統計摘要
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            # 更新狀態為 COMPLETED
            await conn.execute("""
                UPDATE knowledge_completion_loops
                SET status = $1, completed_at = NOW(), updated_at = NOW()
                WHERE id = $2
            """, "completed", loop_id)

            # 查詢統計摘要
            loop_record = await conn.fetchrow("""
                SELECT
                    loop_name, vendor_id, status,
                    current_iteration,
                    current_pass_rate, target_pass_rate,
                    scenario_ids, created_at, completed_at
                FROM knowledge_completion_loops
                WHERE id = $1
            """, loop_id)

            if not loop_record:
                raise HTTPException(status_code=404, detail=f"迴圈 {loop_id} 不存在")

            # 查詢生成的知識數量
            knowledge_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM loop_generated_knowledge
                WHERE loop_id = $1
            """, loop_id)

            # 記錄完成事件
            await conn.execute("""
                INSERT INTO loop_execution_logs (loop_id, event_type, event_data, created_at)
                VALUES ($1, $2, $3, NOW())
            """, loop_id, "batch_completed", {"message": "批次完成"})

            summary = {
                "total_iterations": loop_record["current_iteration"],
                "final_pass_rate": float(loop_record["current_pass_rate"]) if loop_record["current_pass_rate"] else 0.0,
                "target_pass_rate": float(loop_record["target_pass_rate"]) if loop_record["target_pass_rate"] else 0.85,
                "total_scenarios": len(loop_record["scenario_ids"]) if loop_record["scenario_ids"] else 0,
                "generated_knowledge_count": knowledge_count,
                "duration_seconds": (loop_record["completed_at"] - loop_record["created_at"]).total_seconds() if loop_record["completed_at"] else 0
            }

            return CompleteBatchResponse(
                loop_id=loop_id,
                status="completed",
                summary=summary,
                message=f"批次已完成，共執行 {summary['total_iterations']} 次迭代"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 完成批次失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"完成批次失敗：{str(e)}")


@router.post("/{loop_id}/pause")
async def pause_loop(loop_id: int, req: Request):
    """[需求 10.5] 暫停迴圈"""
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            await conn.execute("""
                UPDATE knowledge_completion_loops
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, "paused", loop_id)

            await conn.execute("""
                INSERT INTO loop_execution_logs (loop_id, event_type, event_data, created_at)
                VALUES ($1, $2, $3::jsonb, NOW())
            """, loop_id, "loop_paused", json.dumps({"message": "迴圈已暫停"}))

        return {"loop_id": loop_id, "status": "paused", "message": "迴圈已暫停"}

    except Exception as e:
        print(f"❌ 暫停迴圈失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=f"暫停迴圈失敗：{str(e)}")


@router.post("/{loop_id}/resume")
async def resume_loop(loop_id: int, req: Request):
    """[需求 10.5] 恢復迴圈"""
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            # 檢查當前狀態
            current_status = await conn.fetchval("""
                SELECT status FROM knowledge_completion_loops WHERE id = $1
            """, loop_id)

            if current_status != "paused":
                raise HTTPException(status_code=409, detail=f"只能恢復暫停的迴圈，當前狀態為 {current_status}")

            await conn.execute("""
                UPDATE knowledge_completion_loops
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, "running", loop_id)

            await conn.execute("""
                INSERT INTO loop_execution_logs (loop_id, event_type, event_data, created_at)
                VALUES ($1, $2, $3::jsonb, NOW())
            """, loop_id, "loop_resumed", json.dumps({"message": "迴圈已恢復"}))

        return {"loop_id": loop_id, "status": "running", "message": "迴圈已恢復"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 恢復迴圈失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=f"恢復迴圈失敗：{str(e)}")


@router.post("/{loop_id}/cancel")
async def cancel_loop(loop_id: int, req: Request):
    """[需求 10.5] 取消迴圈"""
    try:
        # 取消背景任務
        async_manager = get_async_execution_manager(req)
        await async_manager.cancel_task(loop_id)

        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            await conn.execute("""
                UPDATE knowledge_completion_loops
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, LoopStatus.CANCELLED.value, loop_id)

            await conn.execute("""
                INSERT INTO loop_execution_logs (loop_id, event_type, event_data, created_at)
                VALUES ($1, $2, $3::jsonb, NOW())
            """, loop_id, "loop_cancelled", json.dumps({"message": "迴圈已取消"}))

        return {"loop_id": loop_id, "status": LoopStatus.CANCELLED.value, "message": "迴圈已取消"}

    except Exception as e:
        print(f"❌ 取消迴圈失敗：{str(e)}")
        raise HTTPException(status_code=500, detail=f"取消迴圈失敗：{str(e)}")


@router.post("/start-next-batch", response_model=LoopStartResponse)
async def start_next_batch(
    request: LoopStartRequest,
    req: Request
):
    """
    [需求 10.4] 啟動下一批次

    - 創建新迴圈並關聯父迴圈
    - 自動選取未處理的測試情境
    """
    try:
        # 驗證父迴圈存在且已完成
        if not request.parent_loop_id:
            raise HTTPException(status_code=400, detail="必須提供 parent_loop_id")

        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            parent_loop = await conn.fetchrow("""
                SELECT status FROM knowledge_completion_loops WHERE id = $1
            """, request.parent_loop_id)

            if not parent_loop:
                raise HTTPException(status_code=404, detail=f"父迴圈 {request.parent_loop_id} 不存在")

            if parent_loop["status"] != "completed":
                raise HTTPException(
                    status_code=409,
                    detail=f"父迴圈必須為 COMPLETED 狀態，當前為 {parent_loop['status']}"
                )

        # 調用 start_loop 端點（內部會自動排除已使用的 scenario_ids）
        return await start_loop(request, req)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 啟動下一批次失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"啟動下一批次失敗：{str(e)}")
