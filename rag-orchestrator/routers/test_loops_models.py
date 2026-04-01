"""
測試 loops.py 的 Pydantic 請求/回應模型

驗收標準：
- 所有模型定義正確
- Field 驗證規則正確
- 必填與選填欄位正確
- 資料類型驗證正確
"""

import sys
sys.path.insert(0, '/app')

import pytest
from pydantic import ValidationError
from datetime import datetime


def test_loop_start_request_valid():
    """測試 1: LoopStartRequest 有效資料"""
    from routers.loops import LoopStartRequest

    request = LoopStartRequest(
        loop_name="測試迴圈",
        vendor_id=2,
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    assert request.loop_name == "測試迴圈"
    assert request.vendor_id == 2
    assert request.batch_size == 50
    assert request.max_iterations == 10
    assert request.target_pass_rate == 0.85
    assert request.parent_loop_id is None
    assert request.budget_limit_usd is None
    print("✅ 測試 1 通過：LoopStartRequest 有效資料")


def test_loop_start_request_validation():
    """測試 2: LoopStartRequest 驗證規則"""
    from routers.loops import LoopStartRequest

    # vendor_id 必須 > 0
    with pytest.raises(ValidationError) as exc_info:
        LoopStartRequest(
            loop_name="測試",
            vendor_id=0,
            batch_size=50
        )
    assert "greater than 0" in str(exc_info.value)

    # batch_size 必須在 1-3000 範圍
    with pytest.raises(ValidationError) as exc_info:
        LoopStartRequest(
            loop_name="測試",
            vendor_id=2,
            batch_size=5000
        )
    assert "less than or equal to 3000" in str(exc_info.value)

    # target_pass_rate 必須在 0.0-1.0 範圍
    with pytest.raises(ValidationError) as exc_info:
        LoopStartRequest(
            loop_name="測試",
            vendor_id=2,
            target_pass_rate=1.5
        )
    assert "less than or equal to 1" in str(exc_info.value)

    print("✅ 測試 2 通過：LoopStartRequest 驗證規則")


def test_loop_start_response_structure():
    """測試 3: LoopStartResponse 結構"""
    from routers.loops import LoopStartResponse

    response = LoopStartResponse(
        loop_id=123,
        loop_name="測試迴圈",
        vendor_id=2,
        status="pending",
        scenario_ids=[1, 2, 3, 4, 5],
        scenario_selection_strategy="stratified_random",
        difficulty_distribution={"easy": 1, "medium": 3, "hard": 1},
        initial_statistics={"total_scenarios": 5},
        created_at="2026-03-27T10:00:00Z"
    )

    assert response.loop_id == 123
    assert len(response.scenario_ids) == 5
    assert response.scenario_selection_strategy == "stratified_random"
    assert response.difficulty_distribution["medium"] == 3
    print("✅ 測試 3 通過：LoopStartResponse 結構")


def test_execute_iteration_request_defaults():
    """測試 4: ExecuteIterationRequest 預設值"""
    from routers.loops import ExecuteIterationRequest

    # 預設 async_mode=True
    request = ExecuteIterationRequest()
    assert request.async_mode == True

    # 可設定為 False
    request_sync = ExecuteIterationRequest(async_mode=False)
    assert request_sync.async_mode == False

    print("✅ 測試 4 通過：ExecuteIterationRequest 預設值")


def test_execute_iteration_response_async_mode():
    """測試 5: ExecuteIterationResponse 非同步模式"""
    from routers.loops import ExecuteIterationResponse

    response = ExecuteIterationResponse(
        loop_id=123,
        current_iteration=1,
        status="running",
        message="迭代已啟動（非同步模式）",
        execution_task_id="task_123_1711523400"
    )

    assert response.execution_task_id is not None
    assert response.backtest_result is None
    print("✅ 測試 5 通過：ExecuteIterationResponse 非同步模式")


def test_execute_iteration_response_sync_mode():
    """測試 6: ExecuteIterationResponse 同步模式"""
    from routers.loops import ExecuteIterationResponse

    response = ExecuteIterationResponse(
        loop_id=123,
        current_iteration=1,
        status="completed",
        message="迭代完成",
        backtest_result={
            "pass_rate": 0.75,
            "total": 50,
            "passed": 37,
            "failed": 13
        }
    )

    assert response.backtest_result is not None
    assert response.execution_task_id is None
    assert response.backtest_result["pass_rate"] == 0.75
    print("✅ 測試 6 通過：ExecuteIterationResponse 同步模式")


def test_loop_status_response_complete():
    """測試 7: LoopStatusResponse 完整資料"""
    from routers.loops import LoopStatusResponse

    response = LoopStatusResponse(
        loop_id=123,
        loop_name="測試迴圈",
        vendor_id=2,
        status="running",
        current_iteration=2,
        max_iterations=10,
        current_pass_rate=0.72,
        target_pass_rate=0.85,
        scenario_ids=[1, 2, 3, 4, 5],
        total_scenarios=5,
        progress={
            "phase": "generating_knowledge",
            "percentage": 0.45,
            "message": "正在生成知識（第 2 次迭代）"
        },
        created_at="2026-03-27T10:00:00Z",
        updated_at="2026-03-27T10:30:00Z",
        completed_at=None
    )

    assert response.current_iteration == 2
    assert response.current_pass_rate == 0.72
    assert response.progress["phase"] == "generating_knowledge"
    assert response.completed_at is None
    print("✅ 測試 7 通過：LoopStatusResponse 完整資料")


def test_validate_loop_request_defaults():
    """測試 8: ValidateLoopRequest 預設值"""
    from routers.loops import ValidateLoopRequest

    request = ValidateLoopRequest()
    assert request.validation_scope == "failed_plus_sample"
    assert request.sample_pass_rate == 0.2

    # 自訂參數
    request_custom = ValidateLoopRequest(
        validation_scope="all",
        sample_pass_rate=0.3
    )
    assert request_custom.validation_scope == "all"
    assert request_custom.sample_pass_rate == 0.3

    print("✅ 測試 8 通過：ValidateLoopRequest 預設值")


def test_validate_loop_response_with_regression():
    """測試 9: ValidateLoopResponse 有 regression"""
    from routers.loops import ValidateLoopResponse

    response = ValidateLoopResponse(
        loop_id=123,
        validation_result={
            "pass_rate": 0.78,
            "total": 50,
            "passed": 39,
            "failed": 11
        },
        validation_passed=False,
        affected_knowledge_ids=[10, 11, 12],
        regression_detected=True,
        regression_count=3,
        next_action="adjust_knowledge"
    )

    assert response.regression_detected == True
    assert response.regression_count == 3
    assert response.validation_passed == False
    assert len(response.affected_knowledge_ids) == 3
    print("✅ 測試 9 通過：ValidateLoopResponse 有 regression")


def test_complete_batch_response():
    """測試 10: CompleteBatchResponse 結構"""
    from routers.loops import CompleteBatchResponse

    response = CompleteBatchResponse(
        loop_id=123,
        status="completed",
        summary={
            "total_iterations": 5,
            "final_pass_rate": 0.88,
            "total_knowledge_generated": 25,
            "total_cost_usd": 12.50
        },
        message="批次已完成"
    )

    assert response.status == "completed"
    assert response.summary["total_iterations"] == 5
    assert response.summary["final_pass_rate"] == 0.88
    print("✅ 測試 10 通過：CompleteBatchResponse 結構")


def test_all_required_fields():
    """測試 11: 必填欄位驗證"""
    from routers.loops import LoopStartRequest, LoopStartResponse

    # LoopStartRequest 缺少必填欄位
    with pytest.raises(ValidationError) as exc_info:
        LoopStartRequest()
    errors = exc_info.value.errors()
    required_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    assert "loop_name" in required_fields
    assert "vendor_id" in required_fields

    # LoopStartResponse 缺少必填欄位
    with pytest.raises(ValidationError) as exc_info:
        LoopStartResponse(loop_id=123)
    errors = exc_info.value.errors()
    required_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    assert "loop_name" in required_fields
    assert "scenario_ids" in required_fields

    print("✅ 測試 11 通過：必填欄位驗證")


if __name__ == "__main__":
    """執行所有測試"""
    print("=" * 60)
    print("開始測試 loops.py Pydantic 模型")
    print("=" * 60)

    # 這些測試會失敗，因為模型尚未實作（RED 階段）
    try:
        test_loop_start_request_valid()
        test_loop_start_request_validation()
        test_loop_start_response_structure()
        test_execute_iteration_request_defaults()
        test_execute_iteration_response_async_mode()
        test_execute_iteration_response_sync_mode()
        test_loop_status_response_complete()
        test_validate_loop_request_defaults()
        test_validate_loop_response_with_regression()
        test_complete_batch_response()
        test_all_required_fields()

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！(11/11)")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()
