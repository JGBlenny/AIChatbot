"""
審核超時監控服務

監控處於 REVIEWING 狀態的迴圈，避免無限期阻塞
"""

import asyncio
import datetime
from typing import Dict, Optional
from dataclasses import dataclass
import psycopg2.pool
import psycopg2.extras


# ============================================
# 配置模型
# ============================================

@dataclass
class ReviewTimeoutConfig:
    """審核超時配置"""
    timeout_seconds: int = 86400  # 預設 24 小時
    timeout_action: str = "skip"  # skip（跳過本次迭代）或 abort（中止迴圈）
    notification_before_timeout: int = 3600  # 超時前 1 小時通知

    def __post_init__(self):
        """驗證配置"""
        if self.timeout_seconds < 3600:
            raise ValueError("timeout_seconds 必須 >= 3600 (1 小時)")

        if self.timeout_action not in ["skip", "abort"]:
            raise ValueError("timeout_action 必須是 'skip' 或 'abort'")

        if self.notification_before_timeout < 0:
            raise ValueError("notification_before_timeout 必須 >= 0")


# ============================================
# 審核超時監控器
# ============================================

class ReviewTimeoutMonitor:
    """審核超時監控器

    功能：
    1. 檢查審核是否超時
    2. 發送超時前提醒通知
    3. 超時後執行指定動作（skip 或 abort）
    4. 背景監控任務（定期檢查所有 REVIEWING 狀態的迴圈）
    """

    def __init__(
        self,
        db_pool: psycopg2.pool.SimpleConnectionPool,
        default_config: Optional[ReviewTimeoutConfig] = None
    ):
        """初始化監控器

        Args:
            db_pool: PostgreSQL 連接池
            default_config: 預設配置（可被個別迴圈配置覆蓋）
        """
        self.db_pool = db_pool
        self.default_config = default_config or ReviewTimeoutConfig()
        self.monitoring = False  # 背景監控任務是否正在運行
        self.monitor_task: Optional[asyncio.Task] = None

    async def check_review_timeout(self, loop_id: int) -> bool:
        """檢查審核是否超時

        Args:
            loop_id: 迴圈 ID

        Returns:
            bool: True 表示已超時並處理，False 表示未超時

        處理邏輯：
        1. 查詢迴圈狀態與進入 REVIEWING 的時間
        2. 計算已等待時間
        3. 檢查是否需要發送提醒通知
        4. 檢查是否超時並執行對應動作
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 查詢迴圈資訊
                cur.execute("""
                    SELECT
                        loop_id, status, status_changed_at,
                        review_timeout_reminder_sent,
                        config
                    FROM knowledge_completion_loops
                    WHERE loop_id = %s
                """, (loop_id,))

                loop = cur.fetchone()

                if not loop:
                    return False

                # 只處理 REVIEWING 狀態的迴圈
                if loop['status'] != 'REVIEWING':
                    return False

                # 獲取配置（個別配置優先，否則使用預設配置）
                loop_config = loop.get('config') or {}
                review_timeout_config = loop_config.get('review_timeout', {})

                config = ReviewTimeoutConfig(
                    timeout_seconds=review_timeout_config.get(
                        'timeout_seconds', self.default_config.timeout_seconds
                    ),
                    timeout_action=review_timeout_config.get(
                        'timeout_action', self.default_config.timeout_action
                    ),
                    notification_before_timeout=review_timeout_config.get(
                        'notification_before_timeout',
                        self.default_config.notification_before_timeout
                    )
                )

                # 計算已等待時間
                now = datetime.datetime.now()
                status_changed_at = loop['status_changed_at']
                elapsed_seconds = (now - status_changed_at).total_seconds()

                # 檢查是否需要發送提醒通知
                remaining_seconds = config.timeout_seconds - elapsed_seconds

                if 0 < remaining_seconds < config.notification_before_timeout:
                    if not loop['review_timeout_reminder_sent']:
                        await self._send_reminder_notification(
                            cur, conn, loop_id, remaining_seconds
                        )

                # 檢查是否超時
                if elapsed_seconds > config.timeout_seconds:
                    await self._handle_timeout(
                        cur, conn, loop_id, config, elapsed_seconds
                    )
                    return True

                return False

        finally:
            self.db_pool.putconn(conn)

    async def _send_reminder_notification(
        self,
        cur,
        conn,
        loop_id: int,
        remaining_seconds: float
    ):
        """發送超時前提醒通知

        Args:
            cur: 資料庫游標
            conn: 資料庫連接
            loop_id: 迴圈 ID
            remaining_seconds: 剩餘時間（秒）
        """
        # 格式化剩餘時間
        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)

        message = f"⚠️  審核即將超時：剩餘 {hours} 小時 {minutes} 分鐘"
        print(f"[ReviewTimeoutMonitor] Loop {loop_id}: {message}")

        # 記錄事件
        cur.execute("""
            INSERT INTO loop_execution_logs (
                loop_id, event_type, event_data, created_at
            )
            VALUES (%s, %s, %s, NOW())
        """, (
            loop_id,
            "review_timeout_reminder",
            psycopg2.extras.Json({
                "remaining_seconds": remaining_seconds,
                "message": message
            })
        ))

        # 標記提醒已發送
        cur.execute("""
            UPDATE knowledge_completion_loops
            SET review_timeout_reminder_sent = TRUE,
                review_timeout_reminder_sent_at = NOW()
            WHERE loop_id = %s
        """, (loop_id,))

        conn.commit()

        # TODO: 整合告警系統（Email、Slack、Webhook）

    async def _handle_timeout(
        self,
        cur,
        conn,
        loop_id: int,
        config: ReviewTimeoutConfig,
        elapsed_seconds: float
    ):
        """處理審核超時

        Args:
            cur: 資料庫游標
            conn: 資料庫連接
            loop_id: 迴圈 ID
            config: 超時配置
            elapsed_seconds: 已等待時間（秒）
        """
        print(f"[ReviewTimeoutMonitor] Loop {loop_id}: 審核超時（已等待 {elapsed_seconds:.0f} 秒）")

        # 記錄超時事件
        cur.execute("""
            INSERT INTO loop_execution_logs (
                loop_id, event_type, event_data, created_at
            )
            VALUES (%s, %s, %s, NOW())
        """, (
            loop_id,
            "review_timeout",
            psycopg2.extras.Json({
                "elapsed_seconds": elapsed_seconds,
                "timeout_action": config.timeout_action
            })
        ))

        # 根據配置執行動作
        if config.timeout_action == "skip":
            # 跳過本次迭代，繼續下一輪
            cur.execute("""
                UPDATE knowledge_completion_loops
                SET status = 'RUNNING',
                    status_changed_at = NOW(),
                    status_message = '審核超時，跳過本次迭代'
                WHERE loop_id = %s
            """, (loop_id,))

            message = "⏭️  審核超時：已跳過本次迭代，開始下一輪回測"
            print(f"[ReviewTimeoutMonitor] Loop {loop_id}: {message}")

        elif config.timeout_action == "abort":
            # 中止迴圈
            cur.execute("""
                UPDATE knowledge_completion_loops
                SET status = 'TERMINATED',
                    status_changed_at = NOW(),
                    status_message = '審核超時，迴圈已中止',
                    completed_at = NOW()
                WHERE loop_id = %s
            """, (loop_id,))

            message = "❌ 審核超時：迴圈已中止"
            print(f"[ReviewTimeoutMonitor] Loop {loop_id}: {message}")

        conn.commit()

        # TODO: 整合告警系統（Email、Slack、Webhook）

    async def start_background_monitor(self, check_interval: int = 300):
        """啟動背景監控任務

        Args:
            check_interval: 檢查間隔（秒，預設 5 分鐘）
        """
        if self.monitoring:
            print("[ReviewTimeoutMonitor] 背景監控任務已在運行")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(
            self._background_monitor_loop(check_interval)
        )
        print(f"[ReviewTimeoutMonitor] 背景監控任務已啟動（間隔：{check_interval} 秒）")

    async def stop_background_monitor(self):
        """停止背景監控任務"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        print("[ReviewTimeoutMonitor] 背景監控任務已停止")

    async def _background_monitor_loop(self, check_interval: int):
        """背景監控迴圈

        定期檢查所有處於 REVIEWING 狀態的迴圈

        Args:
            check_interval: 檢查間隔（秒）
        """
        while self.monitoring:
            try:
                # 查詢所有 REVIEWING 狀態的迴圈
                reviewing_loops = await self._get_reviewing_loops()

                if reviewing_loops:
                    print(f"[ReviewTimeoutMonitor] 檢查 {len(reviewing_loops)} 個 REVIEWING 狀態的迴圈")

                    for loop in reviewing_loops:
                        try:
                            await self.check_review_timeout(loop['loop_id'])
                        except Exception as e:
                            print(f"[ReviewTimeoutMonitor] 檢查失敗 (loop_id={loop['loop_id']}): {e}")

            except Exception as e:
                print(f"[ReviewTimeoutMonitor] 背景監控任務錯誤: {e}")

            # 等待下次檢查
            await asyncio.sleep(check_interval)

    async def _get_reviewing_loops(self):
        """獲取所有 REVIEWING 狀態的迴圈"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT loop_id, status_changed_at
                    FROM knowledge_completion_loops
                    WHERE status = 'REVIEWING'
                    ORDER BY status_changed_at ASC
                """)

                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            self.db_pool.putconn(conn)

    def get_status(self) -> Dict:
        """獲取監控器狀態

        Returns:
            Dict: 監控器狀態資訊
        """
        return {
            "monitoring": self.monitoring,
            "default_config": {
                "timeout_seconds": self.default_config.timeout_seconds,
                "timeout_action": self.default_config.timeout_action,
                "notification_before_timeout": self.default_config.notification_before_timeout
            }
        }

    # ============================================
    # Stub 方法（用於測試）
    # ============================================

    @classmethod
    def create_stub(cls, default_config: Optional[ReviewTimeoutConfig] = None):
        """創建 Stub 模式的監控器（不連接資料庫）

        用於單元測試
        """
        return cls(db_pool=None, default_config=default_config)
