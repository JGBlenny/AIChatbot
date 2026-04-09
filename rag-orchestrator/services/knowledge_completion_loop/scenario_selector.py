"""
測試情境選取器（Scenario Selector）

負責實作測試情境選取策略，支援：
- 分層隨機抽樣（按難度分層）
- 順序選取
- 完全隨機選取
- 批次間避免重複

Author: AI Assistant
Created: 2026-03-27
"""

from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field
import random


class SelectionStrategy(str, Enum):
    """測試情境選取策略"""
    STRATIFIED_RANDOM = "stratified_random"  # 分層隨機抽樣（預設）
    SEQUENTIAL = "sequential"  # 順序選取
    FULL_RANDOM = "full_random"  # 完全隨機


class DifficultyDistribution(BaseModel):
    """難度分布配置"""
    easy: float = Field(0.2, description="簡單題比例", ge=0, le=1)
    medium: float = Field(0.5, description="中等題比例", ge=0, le=1)
    hard: float = Field(0.3, description="困難題比例", ge=0, le=1)

    def validate_sum(self):
        """驗證比例總和是否為 1"""
        total = self.easy + self.medium + self.hard
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"難度比例總和必須為 1.0，當前為 {total}")


class ScenarioSelector:
    """
    測試情境選取器

    負責從 test_scenarios 表選取測試情境，支援多種選取策略。
    """

    def __init__(self, db_pool):
        """
        初始化選取器

        Args:
            db_pool: asyncpg 連接池
        """
        self.db_pool = db_pool

    async def select_scenarios(
        self,
        batch_size: int,
        collection_id: Optional[int] = None,
        strategy: SelectionStrategy = SelectionStrategy.STRATIFIED_RANDOM,
        distribution: Optional[DifficultyDistribution] = None,
        exclude_scenario_ids: Optional[List[int]] = None,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        選取測試情境

        根據指定策略選取測試情境，支援排除已使用的情境 ID。

        Args:
            batch_size: 批次大小（要選取的情境數量）
            collection_id: 情境集合 ID（可選，不指定則選取所有）
            strategy: 選取策略（預設為分層隨機抽樣）
            distribution: 難度分布配置（僅在分層抽樣時使用）
            exclude_scenario_ids: 排除的情境 ID 列表（避免重複選取）
            filters: 額外篩選條件（預留擴展）

        Returns:
            Dict: {
                "scenario_ids": List[int],           # 選取的情境 ID 列表
                "selection_strategy": str,           # 使用的選取策略
                "difficulty_distribution": Dict,     # 實際難度分布
                "total_available": int               # 可用情境總數
            }

        Raises:
            ValueError: 當 batch_size 無效或可用情境不足時
        """
        # 參數驗證
        if batch_size <= 0:
            raise ValueError(f"batch_size 必須大於 0，當前為 {batch_size}")

        # 根據策略選取情境
        if strategy == SelectionStrategy.STRATIFIED_RANDOM:
            return await self._stratified_random_sampling(
                collection_id, batch_size, distribution, exclude_scenario_ids, filters
            )
        elif strategy == SelectionStrategy.SEQUENTIAL:
            return await self._sequential_selection(
                collection_id, batch_size, exclude_scenario_ids, filters
            )
        else:  # FULL_RANDOM
            return await self._full_random_selection(
                collection_id, batch_size, exclude_scenario_ids, filters
            )

    async def _stratified_random_sampling(
        self,
        collection_id: Optional[int],
        batch_size: int,
        distribution: Optional[DifficultyDistribution],
        exclude_scenario_ids: Optional[List[int]],
        filters: Optional[Dict]
    ) -> Dict:
        """
        分層隨機抽樣

        按難度等級分層，每層按比例隨機選取測試情境。
        確保測試覆蓋不同難度等級。

        Args:
            collection_id: 情境集合 ID（可選）
            batch_size: 批次大小
            distribution: 難度分布配置（如未提供則使用預設值）
            exclude_scenario_ids: 排除的情境 ID 列表
            filters: 額外篩選條件

        Returns:
            Dict: 選取結果（含 scenario_ids, strategy, distribution, total_available）
        """
        # 使用預設分布或驗證提供的分布
        if not distribution:
            distribution = DifficultyDistribution()
        else:
            distribution.validate_sum()

        # 計算每個難度的目標數量
        target_easy = int(batch_size * distribution.easy)
        target_medium = int(batch_size * distribution.medium)
        target_hard = batch_size - target_easy - target_medium  # 確保總和正確

        selected_ids = []
        actual_distribution = {"easy": 0, "medium": 0, "hard": 0}

        # 對每個難度等級進行抽樣
        for difficulty, target_count in [
            ("easy", target_easy),
            ("medium", target_medium),
            ("hard", target_hard)
        ]:
            if target_count == 0:
                continue

            # 查詢該難度的可用情境
            query = """
                SELECT id FROM test_scenarios
                WHERE difficulty = $1
                  AND status = 'approved'
                  AND ($2::INTEGER IS NULL OR collection_id = $2)
                  AND ($3::INTEGER[] IS NULL OR NOT (id = ANY($3)))
                ORDER BY RANDOM()
                LIMIT $4
            """

            rows = await self.db_pool.fetch(
                query,
                difficulty,
                collection_id,
                exclude_scenario_ids if exclude_scenario_ids else None,
                target_count
            )

            ids = [row["id"] for row in rows]
            selected_ids.extend(ids)
            actual_distribution[difficulty] = len(ids)

        # 計算總可用情境數量（用於統計）
        total_query = """
            SELECT COUNT(*) as total FROM test_scenarios
            WHERE status = 'approved'
              AND ($1::INTEGER IS NULL OR collection_id = $1)
              AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
        """
        total_row = await self.db_pool.fetchrow(
            total_query,
            collection_id,
            exclude_scenario_ids if exclude_scenario_ids else None
        )
        total_available = total_row["total"]

        return {
            "scenario_ids": selected_ids,
            "selection_strategy": "stratified_random",
            "difficulty_distribution": actual_distribution,
            "total_available": total_available
        }

    async def _sequential_selection(
        self,
        collection_id: Optional[int],
        batch_size: int,
        exclude_scenario_ids: Optional[List[int]],
        filters: Optional[Dict]
    ) -> Dict:
        """
        順序選取

        按 test_scenarios.id 順序選取前 N 個測試情境。

        Args:
            collection_id: 情境集合 ID（可選）
            batch_size: 批次大小
            exclude_scenario_ids: 排除的情境 ID 列表
            filters: 額外篩選條件

        Returns:
            Dict: 選取結果
        """
        query = """
            SELECT id, difficulty FROM test_scenarios
            WHERE status = 'approved'
              AND ($1::INTEGER IS NULL OR collection_id = $1)
              AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
            ORDER BY id ASC
            LIMIT $3
        """

        rows = await self.db_pool.fetch(
            query,
            collection_id,
            exclude_scenario_ids if exclude_scenario_ids else None,
            batch_size
        )

        selected_ids = [row["id"] for row in rows]

        # 計算實際難度分布
        actual_distribution = {"easy": 0, "medium": 0, "hard": 0}
        for row in rows:
            difficulty = row["difficulty"]
            if difficulty in actual_distribution:
                actual_distribution[difficulty] += 1

        # 計算總可用情境數量
        total_query = """
            SELECT COUNT(*) as total FROM test_scenarios
            WHERE status = 'approved'
              AND ($1::INTEGER IS NULL OR collection_id = $1)
              AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
        """
        total_row = await self.db_pool.fetchrow(
            total_query,
            collection_id,
            exclude_scenario_ids if exclude_scenario_ids else None
        )
        total_available = total_row["total"]

        return {
            "scenario_ids": selected_ids,
            "selection_strategy": "sequential",
            "difficulty_distribution": actual_distribution,
            "total_available": total_available
        }

    async def _full_random_selection(
        self,
        collection_id: Optional[int],
        batch_size: int,
        exclude_scenario_ids: Optional[List[int]],
        filters: Optional[Dict]
    ) -> Dict:
        """
        完全隨機選取

        使用 ORDER BY RANDOM() 完全隨機選取 N 個測試情境。
        不考慮難度分布。

        Args:
            collection_id: 情境集合 ID（可選）
            batch_size: 批次大小
            exclude_scenario_ids: 排除的情境 ID 列表
            filters: 額外篩選條件

        Returns:
            Dict: 選取結果
        """
        query = """
            SELECT id, difficulty FROM test_scenarios
            WHERE status = 'approved'
              AND ($1::INTEGER IS NULL OR collection_id = $1)
              AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
            ORDER BY RANDOM()
            LIMIT $3
        """

        rows = await self.db_pool.fetch(
            query,
            collection_id,
            exclude_scenario_ids if exclude_scenario_ids else None,
            batch_size
        )

        selected_ids = [row["id"] for row in rows]

        # 計算實際難度分布
        actual_distribution = {"easy": 0, "medium": 0, "hard": 0}
        for row in rows:
            difficulty = row["difficulty"]
            if difficulty in actual_distribution:
                actual_distribution[difficulty] += 1

        # 計算總可用情境數量
        total_query = """
            SELECT COUNT(*) as total FROM test_scenarios
            WHERE status = 'approved'
              AND ($1::INTEGER IS NULL OR collection_id = $1)
              AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
        """
        total_row = await self.db_pool.fetchrow(
            total_query,
            collection_id,
            exclude_scenario_ids if exclude_scenario_ids else None
        )
        total_available = total_row["total"]

        return {
            "scenario_ids": selected_ids,
            "selection_strategy": "full_random",
            "difficulty_distribution": actual_distribution,
            "total_available": total_available
        }

    async def get_used_scenario_ids(self) -> List[int]:
        """
        取得所有歷史回測中已測過的測試情境 ID

        從 backtest_results 查詢所有曾經測過的 scenario_id，
        用於新建迴圈時自動排除，避免重複選取。

        Returns:
            List[int]: 已使用的測試情境 ID 列表（不重複）
        """
        query = """
            SELECT DISTINCT scenario_id
            FROM backtest_results
            WHERE scenario_id IS NOT NULL
        """
        rows = await self.db_pool.fetch(query)
        return [row["scenario_id"] for row in rows]
