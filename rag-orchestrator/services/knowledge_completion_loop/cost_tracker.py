"""
OpenAI API 成本追蹤服務

追蹤所有 OpenAI API 調用的 token 使用量與成本，支援預算控制與超支告警
"""

import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
import psycopg2.pool
import psycopg2.extras


# ============================================
# 資料模型
# ============================================

@dataclass
class TokenUsage:
    """Token 使用量與成本"""
    operation: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime.datetime


class BudgetExceededError(Exception):
    """預算超支錯誤"""
    pass


# ============================================
# OpenAI 成本追蹤器
# ============================================

class OpenAICostTracker:
    """OpenAI API 成本追蹤器

    功能：
    1. 追蹤 API 調用的 token 使用量
    2. 計算每次調用的成本（基於 OpenAI 定價）
    3. 累計迴圈總成本
    4. 預算控制（超過限制時拋出異常）
    5. 預算警告（達到 80% 時發送警告）
    6. 持久化到 openai_cost_tracking 表
    7. 成本統計與分析
    """

    # OpenAI 定價表（USD per 1M tokens）
    # 來源：https://openai.com/api/pricing/
    # 更新日期：2026-03
    PRICING = {
        "gpt-3.5-turbo": {
            "prompt": 0.50,      # $0.50 / 1M prompt tokens
            "completion": 1.50   # $1.50 / 1M completion tokens
        },
        "gpt-4o-mini": {
            "prompt": 0.150,     # $0.15 / 1M prompt tokens
            "completion": 0.600  # $0.60 / 1M completion tokens
        },
        "gpt-4o": {
            "prompt": 2.50,      # $2.50 / 1M prompt tokens
            "completion": 10.00  # $10.00 / 1M completion tokens
        },
        "gpt-4": {
            "prompt": 30.00,     # $30.00 / 1M prompt tokens
            "completion": 60.00  # $60.00 / 1M completion tokens
        }
    }

    def __init__(
        self,
        loop_id: int,
        db_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None,
        budget_limit_usd: Optional[float] = None
    ):
        """初始化成本追蹤器

        Args:
            loop_id: 迴圈 ID
            db_pool: PostgreSQL 連接池
            budget_limit_usd: 預算上限（USD），None 表示無限制
        """
        self.loop_id = loop_id
        self.db_pool = db_pool
        self.budget_limit_usd = budget_limit_usd
        self.total_cost_usd = 0.0
        self.usage_by_operation: Dict[str, List[TokenUsage]] = {}
        self.budget_warning_sent = False  # 是否已發送預算警告

    async def track_api_call(
        self,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> TokenUsage:
        """追蹤單次 API 呼叫

        Args:
            operation: 操作名稱（如 "knowledge_generation", "action_type_classification"）
            model: 模型名稱
            prompt_tokens: Prompt tokens 數量
            completion_tokens: Completion tokens 數量

        Returns:
            TokenUsage: 本次調用的使用量與成本

        Raises:
            BudgetExceededError: 超過預算限制
        """
        total_tokens = prompt_tokens + completion_tokens

        # 計算成本
        cost_usd = self._calculate_cost(model, prompt_tokens, completion_tokens)

        # 創建 TokenUsage 物件
        usage = TokenUsage(
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.datetime.now()
        )

        # 更新累計成本
        self.total_cost_usd += cost_usd

        # 記錄到操作清單
        if operation not in self.usage_by_operation:
            self.usage_by_operation[operation] = []
        self.usage_by_operation[operation].append(usage)

        # 持久化到資料庫
        if self.db_pool:
            await self._save_to_database(usage)

        # 檢查預算限制（在持久化之後）
        budget_limit = float(self.budget_limit_usd) if self.budget_limit_usd else None
        if budget_limit and self.total_cost_usd > budget_limit:
            raise BudgetExceededError(
                f"迴圈 {self.loop_id} 已超過預算限制：${self.total_cost_usd:.4f} > ${budget_limit:.2f}"
            )

        # 預算警告（達到 80%）
        if budget_limit and not self.budget_warning_sent:
            usage_percentage = self.total_cost_usd / budget_limit
            if usage_percentage >= 0.8:
                self._send_budget_warning(usage_percentage)
                self.budget_warning_sent = True

        return usage

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """計算單次 API 調用的成本

        Args:
            model: 模型名稱
            prompt_tokens: Prompt tokens 數量
            completion_tokens: Completion tokens 數量

        Returns:
            float: 成本（USD）
        """
        # 獲取定價（如果模型不在定價表中，使用 gpt-4o-mini 作為預設）
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o-mini"])

        # 計算成本：(tokens / 1,000,000) * price_per_million
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]

        return prompt_cost + completion_cost

    async def _save_to_database(self, usage: TokenUsage):
        """持久化到資料庫

        寫入 openai_cost_tracking 表，並更新 knowledge_completion_loops 表的累計成本
        """
        if not self.db_pool:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 插入 openai_cost_tracking 記錄
                cur.execute("""
                    INSERT INTO openai_cost_tracking (
                        loop_id, operation, model,
                        prompt_tokens, completion_tokens, cost_usd,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.loop_id,
                    usage.operation,
                    usage.model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.cost_usd,
                    usage.timestamp
                ))

                # 更新 knowledge_completion_loops 表的累計成本
                cur.execute("""
                    UPDATE knowledge_completion_loops
                    SET total_openai_cost_usd = %s
                    WHERE id = %s
                """, (self.total_cost_usd, self.loop_id))

                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ 成本追蹤資料保存失敗: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    def _send_budget_warning(self, usage_percentage: float):
        """發送預算警告

        Args:
            usage_percentage: 預算使用百分比（0.0-1.0）
        """
        print(f"⚠️  預算警告：迴圈 {self.loop_id} 已使用 {usage_percentage * 100:.1f}% 預算")
        print(f"   已使用：${self.total_cost_usd:.4f} / ${self.budget_limit_usd:.2f}")

        # TODO: 整合告警系統（Email、Slack、Webhook）

    async def estimate_iteration_cost(
        self,
        gap_count: int,
        operation: str = "knowledge_generation",
        model: str = "gpt-3.5-turbo"
    ) -> float:
        """預估單次迭代成本

        基於歷史數據預估平均成本

        Args:
            gap_count: 知識缺口數量
            operation: 操作名稱
            model: 模型名稱

        Returns:
            float: 預估成本（USD）
        """
        # 獲取歷史平均 token 使用量
        if operation in self.usage_by_operation and self.usage_by_operation[operation]:
            # 使用歷史數據計算平均值
            history = self.usage_by_operation[operation]
            avg_prompt_tokens = sum(u.prompt_tokens for u in history) / len(history)
            avg_completion_tokens = sum(u.completion_tokens for u in history) / len(history)
        else:
            # 使用經驗值（知識生成）
            if operation == "knowledge_generation":
                avg_prompt_tokens = 600   # 平均 600 tokens prompt
                avg_completion_tokens = 200  # 平均 200 tokens completion
            elif operation == "action_type_classification":
                avg_prompt_tokens = 400
                avg_completion_tokens = 100
            else:
                avg_prompt_tokens = 500
                avg_completion_tokens = 150

        # 計算單次成本
        single_cost = self._calculate_cost(
            model,
            int(avg_prompt_tokens),
            int(avg_completion_tokens)
        )

        # 預估總成本
        estimated_cost = single_cost * gap_count

        return estimated_cost

    def get_cost_summary(self) -> Dict:
        """獲取成本摘要

        Returns:
            Dict: 成本統計資訊
            {
                "total_cost_usd": float,
                "total_calls": int,
                "total_tokens": int,
                "by_operation": {
                    "knowledge_generation": {
                        "calls": int,
                        "cost_usd": float,
                        "tokens": int
                    },
                    ...
                },
                "budget_limit_usd": float | None,
                "budget_used_percentage": float | None
            }
        """
        total_calls = sum(len(usages) for usages in self.usage_by_operation.values())
        total_tokens = sum(
            u.total_tokens
            for usages in self.usage_by_operation.values()
            for u in usages
        )

        by_operation = {}
        for operation, usages in self.usage_by_operation.items():
            by_operation[operation] = {
                "calls": len(usages),
                "cost_usd": sum(u.cost_usd for u in usages),
                "tokens": sum(u.total_tokens for u in usages),
                "prompt_tokens": sum(u.prompt_tokens for u in usages),
                "completion_tokens": sum(u.completion_tokens for u in usages)
            }

        summary = {
            "total_cost_usd": self.total_cost_usd,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "by_operation": by_operation,
            "budget_limit_usd": self.budget_limit_usd,
            "budget_used_percentage": (
                self.total_cost_usd / self.budget_limit_usd
                if self.budget_limit_usd else None
            )
        }

        return summary

    async def get_cost_history(
        self,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> List[Dict]:
        """從資料庫獲取成本歷史記錄

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[Dict]: 歷史記錄清單
        """
        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = """
                    SELECT
                        id, operation, model,
                        prompt_tokens, completion_tokens, cost_usd,
                        created_at
                    FROM openai_cost_tracking
                    WHERE loop_id = %s
                """
                params = [self.loop_id]

                if start_date:
                    query += " AND created_at >= %s"
                    params.append(start_date)
                if end_date:
                    query += " AND created_at <= %s"
                    params.append(end_date)

                query += " ORDER BY created_at DESC"

                cur.execute(query, params)
                rows = cur.fetchall()

                return [dict(row) for row in rows]
        finally:
            self.db_pool.putconn(conn)

    def reset(self):
        """重置追蹤器（清空記憶體中的累計資料）

        注意：不會刪除資料庫中的歷史記錄
        """
        self.total_cost_usd = 0.0
        self.usage_by_operation = {}
        self.budget_warning_sent = False

    # ============================================
    # Stub 方法（用於測試）
    # ============================================

    @classmethod
    def create_stub(cls, loop_id: int, budget_limit_usd: Optional[float] = None):
        """創建 Stub 模式的追蹤器（不連接資料庫）

        用於單元測試或開發環境
        """
        return cls(loop_id=loop_id, db_pool=None, budget_limit_usd=budget_limit_usd)
