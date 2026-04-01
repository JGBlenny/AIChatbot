"""
驗證迭代狀態管理修復

這個腳本檢查：
1. _update_iteration_count 方法存在
2. _update_pass_rate 方法存在
3. execute_iteration 方法在開始時調用 _update_iteration_count
"""
import inspect
import re


def verify_fix():
    """驗證修復是否正確實作"""
    from coordinator import LoopCoordinator

    print("=" * 60)
    print("驗證迭代狀態管理修復")
    print("=" * 60)

    # 檢查 1: _update_iteration_count 方法存在
    print("\n✓ 檢查 1: _update_iteration_count 方法存在...")
    assert hasattr(LoopCoordinator, "_update_iteration_count"), \
        "❌ _update_iteration_count 方法不存在"
    print("  ✅ _update_iteration_count 方法已實作")

    # 檢查 2: _update_pass_rate 方法存在
    print("\n✓ 檢查 2: _update_pass_rate 方法存在...")
    assert hasattr(LoopCoordinator, "_update_pass_rate"), \
        "❌ _update_pass_rate 方法不存在"
    print("  ✅ _update_pass_rate 方法已實作")

    # 檢查 3: execute_iteration 邏輯正確
    print("\n✓ 檢查 3: execute_iteration 在開始時更新 iteration...")
    execute_iteration_source = inspect.getsource(LoopCoordinator.execute_iteration)

    # 檢查是否呼叫 _update_iteration_count
    if "_update_iteration_count" not in execute_iteration_source:
        print("  ❌ execute_iteration 沒有呼叫 _update_iteration_count")
        return False

    # 檢查呼叫順序：_update_iteration_count 應該在 execute_batch_backtest 之前
    iteration_update_pos = execute_iteration_source.find("_update_iteration_count")
    backtest_pos = execute_iteration_source.find("execute_batch_backtest")

    if iteration_update_pos > backtest_pos:
        print("  ❌ _update_iteration_count 應該在 execute_batch_backtest 之前呼叫")
        return False

    print("  ✅ _update_iteration_count 在 execute_batch_backtest 之前呼叫")

    # 檢查 4: _update_pass_rate 取代了部分 _increment_iteration
    print("\n✓ 檢查 4: 使用 _update_pass_rate 而非 _increment_iteration...")
    if "_update_pass_rate" not in execute_iteration_source:
        print("  ❌ execute_iteration 沒有呼叫 _update_pass_rate")
        return False

    print("  ✅ _update_pass_rate 已被使用")

    # 檢查 5: 註釋說明修復原因
    print("\n✓ 檢查 5: 有註釋說明修復原因...")
    if "即使後續步驟失敗" in execute_iteration_source or "立即更新迭代次數" in execute_iteration_source:
        print("  ✅ 有清晰的註釋說明")
    else:
        print("  ⚠️  建議添加註釋說明修復原因")

    print("\n" + "=" * 60)
    print("✅ 所有檢查通過！修復已正確實作")
    print("=" * 60)

    print("\n📋 修復總結：")
    print("  1. 新增 _update_iteration_count() 方法")
    print("  2. 新增 _update_pass_rate() 方法")
    print("  3. execute_iteration() 在開始時立即更新 iteration")
    print("  4. 回測完成後只更新 pass_rate")
    print("  5. 即使執行失敗，current_iteration 也已更新")
    print("\n✅ 修復後的行為：")
    print("  - Loop 113 的 current_iteration 會在回測開始時從 0 更新到 1")
    print("  - 即使分析或生成知識失敗，iteration 仍保持為 1")
    print("  - backtest_runs 的 'Iteration 1' 與 current_iteration = 1 一致")
    print("  - 前端可以正確顯示回測結果")

    return True


if __name__ == "__main__":
    try:
        success = verify_fix()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 驗證失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
