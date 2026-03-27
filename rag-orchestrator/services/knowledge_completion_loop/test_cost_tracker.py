"""
OpenAI 成本追蹤器測試

測試 OpenAICostTracker 的核心功能：
1. 成本計算準確性
2. 預算控制與告警
3. 成本統計與摘要
4. 預估功能
5. Stub 模式
"""

import asyncio
import datetime
import pytest
from cost_tracker import OpenAICostTracker, BudgetExceededError, TokenUsage


# ============================================
# 測試 1: 成本計算準確性
# ============================================

@pytest.mark.asyncio
async def test_cost_calculation():
    """測試成本計算是否準確"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    # 測試 gpt-3.5-turbo（$0.50 / 1M prompt, $1.50 / 1M completion）
    usage = await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500
    )

    # 預期成本：(1000/1M * 0.50) + (500/1M * 1.50) = 0.0005 + 0.00075 = 0.00125
    assert abs(usage.cost_usd - 0.00125) < 0.0001
    assert usage.total_tokens == 1500
    assert tracker.total_cost_usd == 0.00125

    print("✅ 成本計算測試通過")


@pytest.mark.asyncio
async def test_multiple_models():
    """測試不同模型的成本計算"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    # gpt-3.5-turbo
    usage1 = await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500
    )
    assert abs(usage1.cost_usd - 0.00125) < 0.0001

    # gpt-4o-mini（$0.15 / 1M prompt, $0.60 / 1M completion）
    usage2 = await tracker.track_api_call(
        operation="action_type_classification",
        model="gpt-4o-mini",
        prompt_tokens=500,
        completion_tokens=200
    )
    # 預期成本：(500/1M * 0.15) + (200/1M * 0.60) = 0.000075 + 0.00012 = 0.000195
    assert abs(usage2.cost_usd - 0.000195) < 0.0001

    # 累計成本
    expected_total = 0.00125 + 0.000195
    assert abs(tracker.total_cost_usd - expected_total) < 0.0001

    print("✅ 多模型成本計算測試通過")


# ============================================
# 測試 2: 預算控制
# ============================================

@pytest.mark.asyncio
async def test_budget_exceeded():
    """測試預算超支時是否拋出異常"""

    tracker = OpenAICostTracker.create_stub(loop_id=1, budget_limit_usd=0.01)

    # 第一次調用：應成功
    await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500
    )

    # 第二次調用：應拋出 BudgetExceededError
    with pytest.raises(BudgetExceededError):
        # 這次調用會使總成本超過 $0.01
        await tracker.track_api_call(
            operation="knowledge_generation",
            model="gpt-3.5-turbo",
            prompt_tokens=10000,
            completion_tokens=5000
        )

    print("✅ 預算超支測試通過")


@pytest.mark.asyncio
async def test_budget_warning():
    """測試預算警告（達到 80%）"""

    tracker = OpenAICostTracker.create_stub(loop_id=1, budget_limit_usd=0.01)

    # 調用 1：50% 預算（應該沒有警告）
    # 單次成本：(4000/1M * 0.50) + (2000/1M * 1.50) = 0.002 + 0.003 = 0.005
    await tracker.track_api_call(
        operation="test",
        model="gpt-3.5-turbo",
        prompt_tokens=4000,
        completion_tokens=2000
    )
    assert tracker.budget_warning_sent == False

    # 調用 2：達到 82% 預算（應該有警告但不超支）
    # 累計成本：0.005 + 0.0032 = 0.0082 (82%)
    await tracker.track_api_call(
        operation="test",
        model="gpt-3.5-turbo",
        prompt_tokens=2560,
        completion_tokens=1280
    )
    assert tracker.budget_warning_sent == True

    print("✅ 預算警告測試通過")


@pytest.mark.asyncio
async def test_no_budget_limit():
    """測試無預算限制時的行為"""

    tracker = OpenAICostTracker.create_stub(loop_id=1, budget_limit_usd=None)

    # 調用大量次數，應該不會拋出異常
    for i in range(100):
        await tracker.track_api_call(
            operation="test",
            model="gpt-3.5-turbo",
            prompt_tokens=1000,
            completion_tokens=500
        )

    # 應該累計了 100 次成本
    expected_cost = 0.00125 * 100
    assert abs(tracker.total_cost_usd - expected_cost) < 0.01

    print("✅ 無預算限制測試通過")


# ============================================
# 測試 3: 成本統計與摘要
# ============================================

@pytest.mark.asyncio
async def test_cost_summary():
    """測試成本摘要功能"""

    tracker = OpenAICostTracker.create_stub(loop_id=1, budget_limit_usd=1.0)

    # 知識生成：3 次調用
    for i in range(3):
        await tracker.track_api_call(
            operation="knowledge_generation",
            model="gpt-3.5-turbo",
            prompt_tokens=1000,
            completion_tokens=500
        )

    # 回應類型判斷：2 次調用
    for i in range(2):
        await tracker.track_api_call(
            operation="action_type_classification",
            model="gpt-4o-mini",
            prompt_tokens=500,
            completion_tokens=200
        )

    # 獲取成本摘要
    summary = tracker.get_cost_summary()

    # 驗證摘要內容
    assert summary["total_calls"] == 5
    assert summary["budget_limit_usd"] == 1.0

    # 驗證 by_operation
    assert summary["by_operation"]["knowledge_generation"]["calls"] == 3
    assert summary["by_operation"]["action_type_classification"]["calls"] == 2

    # 驗證總成本
    expected_total = (0.00125 * 3) + (0.000195 * 2)
    assert abs(summary["total_cost_usd"] - expected_total) < 0.001

    # 驗證預算使用百分比
    expected_percentage = expected_total / 1.0
    assert abs(summary["budget_used_percentage"] - expected_percentage) < 0.01

    print("✅ 成本摘要測試通過")


@pytest.mark.asyncio
async def test_usage_by_operation():
    """測試按操作分類的使用量記錄"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500
    )

    await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1200,
        completion_tokens=600
    )

    # 驗證記錄
    assert "knowledge_generation" in tracker.usage_by_operation
    assert len(tracker.usage_by_operation["knowledge_generation"]) == 2

    # 驗證第一筆記錄
    usage1 = tracker.usage_by_operation["knowledge_generation"][0]
    assert usage1.prompt_tokens == 1000
    assert usage1.completion_tokens == 500

    # 驗證第二筆記錄
    usage2 = tracker.usage_by_operation["knowledge_generation"][1]
    assert usage2.prompt_tokens == 1200
    assert usage2.completion_tokens == 600

    print("✅ 按操作分類測試通過")


# ============================================
# 測試 4: 成本預估
# ============================================

@pytest.mark.asyncio
async def test_estimate_iteration_cost_with_history():
    """測試基於歷史數據的成本預估"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    # 先執行 3 次調用建立歷史
    for i in range(3):
        await tracker.track_api_call(
            operation="knowledge_generation",
            model="gpt-3.5-turbo",
            prompt_tokens=800,
            completion_tokens=300
        )

    # 預估 10 個 gaps 的成本
    estimated_cost = await tracker.estimate_iteration_cost(
        gap_count=10,
        operation="knowledge_generation",
        model="gpt-3.5-turbo"
    )

    # 歷史平均：800 prompt + 300 completion
    # 單次成本：(800/1M * 0.50) + (300/1M * 1.50) = 0.0004 + 0.00045 = 0.00085
    # 10 次成本：0.00085 * 10 = 0.0085
    assert abs(estimated_cost - 0.0085) < 0.001

    print("✅ 基於歷史數據的成本預估測試通過")


@pytest.mark.asyncio
async def test_estimate_iteration_cost_without_history():
    """測試無歷史數據時使用預設值預估"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    # 預估 5 個 gaps 的成本（無歷史數據，使用預設值）
    estimated_cost = await tracker.estimate_iteration_cost(
        gap_count=5,
        operation="knowledge_generation",
        model="gpt-3.5-turbo"
    )

    # 預設值：600 prompt + 200 completion
    # 單次成本：(600/1M * 0.50) + (200/1M * 1.50) = 0.0003 + 0.0003 = 0.0006
    # 5 次成本：0.0006 * 5 = 0.003
    assert abs(estimated_cost - 0.003) < 0.001

    print("✅ 無歷史數據的成本預估測試通過")


# ============================================
# 測試 5: Reset 功能
# ============================================

@pytest.mark.asyncio
async def test_reset():
    """測試重置功能"""

    tracker = OpenAICostTracker.create_stub(loop_id=1, budget_limit_usd=1.0)

    # 執行一些調用
    for i in range(5):
        await tracker.track_api_call(
            operation="test",
            model="gpt-3.5-turbo",
            prompt_tokens=1000,
            completion_tokens=500
        )

    assert tracker.total_cost_usd > 0
    assert len(tracker.usage_by_operation["test"]) == 5

    # 重置
    tracker.reset()

    # 驗證已重置
    assert tracker.total_cost_usd == 0.0
    assert len(tracker.usage_by_operation) == 0
    assert tracker.budget_warning_sent == False

    print("✅ Reset 功能測試通過")


# ============================================
# 測試 6: TokenUsage 資料模型
# ============================================

@pytest.mark.asyncio
async def test_token_usage_model():
    """測試 TokenUsage 資料模型"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    usage = await tracker.track_api_call(
        operation="knowledge_generation",
        model="gpt-3.5-turbo",
        prompt_tokens=1000,
        completion_tokens=500
    )

    # 驗證欄位
    assert isinstance(usage, TokenUsage)
    assert usage.operation == "knowledge_generation"
    assert usage.model == "gpt-3.5-turbo"
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.cost_usd > 0
    assert isinstance(usage.timestamp, datetime.datetime)

    print("✅ TokenUsage 資料模型測試通過")


# ============================================
# 測試 7: 未知模型的處理
# ============================================

@pytest.mark.asyncio
async def test_unknown_model():
    """測試未知模型時使用預設定價"""

    tracker = OpenAICostTracker.create_stub(loop_id=1)

    # 使用未知模型
    usage = await tracker.track_api_call(
        operation="test",
        model="unknown-model",
        prompt_tokens=1000,
        completion_tokens=500
    )

    # 應該使用 gpt-4o-mini 的定價
    expected_cost = (1000 / 1_000_000 * 0.150) + (500 / 1_000_000 * 0.600)
    assert abs(usage.cost_usd - expected_cost) < 0.0001

    print("✅ 未知模型處理測試通過")


# ============================================
# 主函數：執行所有測試
# ============================================

async def run_all_tests():
    """執行所有測試"""

    print("\n" + "="*60)
    print("開始測試 OpenAICostTracker")
    print("="*60 + "\n")

    # 測試 1: 成本計算
    print("測試 1: 成本計算準確性")
    await test_cost_calculation()
    print()

    print("測試 2: 多模型成本計算")
    await test_multiple_models()
    print()

    # 測試 2: 預算控制
    print("測試 3: 預算超支")
    await test_budget_exceeded()
    print()

    print("測試 4: 預算警告")
    await test_budget_warning()
    print()

    print("測試 5: 無預算限制")
    await test_no_budget_limit()
    print()

    # 測試 3: 成本統計
    print("測試 6: 成本摘要")
    await test_cost_summary()
    print()

    print("測試 7: 按操作分類")
    await test_usage_by_operation()
    print()

    # 測試 4: 成本預估
    print("測試 8: 基於歷史數據的成本預估")
    await test_estimate_iteration_cost_with_history()
    print()

    print("測試 9: 無歷史數據的成本預估")
    await test_estimate_iteration_cost_without_history()
    print()

    # 測試 5: Reset
    print("測試 10: Reset 功能")
    await test_reset()
    print()

    # 測試 6: 資料模型
    print("測試 11: TokenUsage 資料模型")
    await test_token_usage_model()
    print()

    # 測試 7: 未知模型
    print("測試 12: 未知模型處理")
    await test_unknown_model()
    print()

    print("="*60)
    print("✅ 所有測試通過！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
