"""
非同步執行管理器（Async Execution Manager）

負責管理知識完善迴圈的背景執行任務，避免 HTTP 請求超時。

Author: AI Assistant
Created: 2026-03-27
"""

import asyncio
import traceback
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .coordinator import LoopCoordinator

try:
    from .models import LoopStatus
    from .cost_tracker import BudgetExceededError
except ImportError:
    from models import LoopStatus
    from cost_tracker import BudgetExceededError


class ConcurrentExecutionError(Exception):
    """並發執行錯誤：嘗試對同一迴圈同時執行多次"""
    pass


class AsyncExecutionManager:
    """
    非同步執行管理器

    負責管理長時間運行的迴圈迭代任務，支援：
    - 背景執行避免 HTTP 超時
    - 並發控制（同一迴圈不能同時執行多次）
    - 任務狀態查詢與取消
    - 錯誤處理與日誌記錄
    """

    def __init__(self, db_pool):
        """
        初始化非同步執行管理器

        Args:
            db_pool: asyncpg 連接池（用於記錄執行日誌）
        """
        self.db_pool = db_pool
        self.running_tasks: Dict[int, asyncio.Task] = {}

    async def start_iteration(
        self,
        coordinator: "LoopCoordinator",
        loop_id: int
    ) -> str:
        """
        啟動非同步迭代任務

        檢查並發控制，創建背景任務執行迭代流程。

        Args:
            coordinator: LoopCoordinator 實例
            loop_id: 迴圈 ID

        Returns:
            str: 任務 ID（格式：task_{loop_id}_{timestamp}）

        Raises:
            ConcurrentExecutionError: 當該迴圈已在執行中時
        """
        # 並發執行檢查
        if self.is_running(loop_id):
            raise ConcurrentExecutionError(
                f"Loop {loop_id} is already running. Cannot start concurrent execution."
            )

        # 創建背景任務
        task = asyncio.create_task(
            self._execute_iteration_background(coordinator, loop_id)
        )

        # 記錄到 running_tasks
        self.running_tasks[loop_id] = task

        # 生成任務 ID
        timestamp = int(datetime.now().timestamp() * 1000)
        task_id = f"task_{loop_id}_{timestamp}"

        return task_id

    async def _execute_iteration_background(
        self,
        coordinator: "LoopCoordinator",
        loop_id: int
    ):
        """
        背景執行迭代流程

        處理完整的迭代執行、錯誤捕獲、狀態更新與日誌記錄。

        Args:
            coordinator: LoopCoordinator 實例
            loop_id: 迴圈 ID
        """
        try:
            # 執行迭代
            result = await coordinator.execute_iteration()

            # 執行成功：更新狀態為 REVIEWING
            await self._update_loop_status(loop_id, LoopStatus.REVIEWING)

            # 記錄成功事件
            await self._log_event(
                loop_id=loop_id,
                event_type="iteration_completed",
                event_data={
                    "iteration": result.get("iteration"),
                    "gaps_analyzed": result.get("gaps_analyzed"),
                    "knowledge_generated": result.get("knowledge_generated"),
                    "message": "Iteration completed successfully, awaiting knowledge review"
                }
            )

        except BudgetExceededError as e:
            # 預算超支錯誤
            await self._update_loop_status(loop_id, LoopStatus.FAILED)
            await self._log_event(
                loop_id=loop_id,
                event_type="budget_exceeded",
                event_data={
                    "error": str(e),
                    "message": "Iteration failed due to budget exceeded"
                }
            )

        except Exception as e:
            # 其他異常
            await self._update_loop_status(loop_id, LoopStatus.FAILED)
            await self._log_event(
                loop_id=loop_id,
                event_type="iteration_failed",
                event_data={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "message": "Iteration failed due to unexpected error"
                }
            )

        finally:
            # 清理任務記錄
            self.running_tasks.pop(loop_id, None)

    async def _update_loop_status(self, loop_id: int, status: LoopStatus):
        """
        更新迴圈狀態

        Args:
            loop_id: 迴圈 ID
            status: 新狀態
        """
        query = """
            UPDATE knowledge_completion_loops
            SET status = $1, updated_at = NOW()
            WHERE id = $2
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, status.value, loop_id)

    async def _log_event(
        self,
        loop_id: int,
        event_type: str,
        event_data: Dict
    ):
        """
        記錄執行事件到 loop_execution_logs

        Args:
            loop_id: 迴圈 ID
            event_type: 事件類型
            event_data: 事件數據
        """
        import json
        query = """
            INSERT INTO loop_execution_logs (
                loop_id, event_type, event_data, created_at
            ) VALUES ($1, $2, $3::jsonb, NOW())
        """
        # 將 dict 轉為 JSON string
        event_data_json = json.dumps(event_data) if isinstance(event_data, dict) else event_data
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, loop_id, event_type, event_data_json)

    def is_running(self, loop_id: int) -> bool:
        """
        檢查迴圈是否正在執行

        Args:
            loop_id: 迴圈 ID

        Returns:
            bool: True 表示正在執行中
        """
        return loop_id in self.running_tasks

    async def cancel_task(self, loop_id: int) -> bool:
        """
        取消執行中的任務

        Args:
            loop_id: 迴圈 ID

        Returns:
            bool: True 表示成功取消，False 表示任務不存在
        """
        task = self.running_tasks.get(loop_id)

        if not task:
            return False

        # 取消任務
        task.cancel()

        # 清理記錄
        self.running_tasks.pop(loop_id, None)

        # 記錄取消事件
        await self._log_event(
            loop_id=loop_id,
            event_type="iteration_cancelled",
            event_data={
                "message": "Iteration task was cancelled by user request"
            }
        )

        return True
