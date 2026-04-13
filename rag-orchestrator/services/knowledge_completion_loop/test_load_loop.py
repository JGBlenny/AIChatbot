"""
測試 LoopCoordinator.load_loop() 方法

測試覆蓋：
- 成功載入已存在的迴圈
- 載入不存在的迴圈時拋出 LoopNotFoundError
- 正確初始化協調器狀態（loop_id, vendor_id, status, config）
- 正確初始化 cost_tracker 並關聯到生成器
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, MagicMock

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop')

# 直接導入 coordinator 模組
import importlib.util

# 載入 models 模組
spec_models = importlib.util.spec_from_file_location(
    "models",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/models.py"
)
models = importlib.util.module_from_spec(spec_models)
spec_models.loader.exec_module(models)

LoopStatus = models.LoopStatus
LoopConfig = models.LoopConfig
LoopNotFoundError = models.LoopNotFoundError


# 載入 coordinator 模組（需要 mock 依賴）
def create_mock_coordinator():
    """建立 mock coordinator 用於測試"""
    # Mock 所有依賴
    sys.modules['services.knowledge_completion_loop.gap_analyzer'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.backtest_client'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.action_type_classifier'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.knowledge_generator'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.cost_tracker'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.gap_classifier'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.sop_generator'] = MagicMock()

    spec_coord = importlib.util.spec_from_file_location(
        "coordinator",
        "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/coordinator.py"
    )
    coordinator = importlib.util.module_from_spec(spec_coord)
    spec_coord.loader.exec_module(coordinator)

    return coordinator.LoopCoordinator


def mock_db_pool():
    """建立 mock 資料庫連接池"""
    pool = Mock()

    # Mock connection
    conn = MagicMock()
    cursor = MagicMock()

    # 設定 cursor 的 fetchone 行為
    cursor.fetchone = Mock(return_value=None)
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)

    pool.getconn = Mock(return_value=conn)
    pool.putconn = Mock()

    return pool


async def test_load_loop_success():
    """測試 1: 成功載入已存在的迴圈"""
    print("\n[測試 1] 成功載入已存在的迴圈...")

    # Arrange
    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    loop_id = 123
    mock_loop_record = {
        "id": loop_id,
        "vendor_id": 2,
        "loop_name": "已存在的迴圈",
        "status": "running",
        "config": {
            "batch_size": 50,
            "max_iterations": 10,
            "target_pass_rate": 0.85,
            "action_type_mode": "ai_assisted",
            "filters": {},
            "backtest_config": {}
        },
        "current_iteration": 3,
        "created_at": datetime.now()
    }

    # Mock 資料庫查詢
    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = mock_loop_record

    # Act
    result = await coordinator.load_loop(loop_id)

    # Assert
    assert result["loop_id"] == loop_id, f"預期 loop_id={loop_id}，但得到 {result['loop_id']}"
    assert result["status"] == "running", f"預期 status='running'，但得到 {result['status']}"
    assert result["current_iteration"] == 3, f"預期 current_iteration=3，但得到 {result['current_iteration']}"
    assert "loaded_at" in result, "result 應包含 'loaded_at' 欄位"

    # 驗證協調器狀態已更新
    assert coordinator.loop_id == loop_id
    assert coordinator.vendor_id == 2
    assert coordinator.loop_name == "已存在的迴圈"
    assert coordinator.current_status == LoopStatus.RUNNING
    assert coordinator.config.batch_size == 50
    assert coordinator.config.max_iterations == 10
    assert coordinator.config.target_pass_rate == 0.85

    # 驗證 cost_tracker 已初始化
    assert coordinator.cost_tracker is not None

    print("✅ 測試 1 通過")


async def test_load_loop_not_found():
    """測試 2: 載入不存在的迴圈時拋出 LoopNotFoundError"""
    print("\n[測試 2] 載入不存在的迴圈時拋出 LoopNotFoundError...")

    # Arrange
    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    loop_id = 999

    # Mock 資料庫查詢返回 None
    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = None

    # Act & Assert
    try:
        await coordinator.load_loop(loop_id)
        assert False, "應該拋出 LoopNotFoundError"
    except LoopNotFoundError as e:
        assert f"Loop {loop_id} 不存在" in str(e), f"錯誤訊息應包含 'Loop {loop_id} 不存在'"
        print("✅ 測試 2 通過")


async def test_load_loop_handles_different_statuses():
    """測試 3: 載入不同狀態的迴圈"""
    print("\n[測試 3] 載入不同狀態的迴圈...")

    statuses_to_test = [
        ("pending", LoopStatus.PENDING),
        ("running", LoopStatus.RUNNING),
        ("reviewing", LoopStatus.REVIEWING),
        ("completed", LoopStatus.COMPLETED),
        ("paused", LoopStatus.PAUSED),
        ("failed", LoopStatus.FAILED)
    ]

    LoopCoordinator = create_mock_coordinator()

    for status_str, status_enum in statuses_to_test:
        # Arrange
        pool = mock_db_pool()
        coordinator = LoopCoordinator(
            db_pool=pool,
            vendor_id=2,
            loop_name="測試迴圈",
            openai_api_key="test-key"
        )

        loop_id = 123
        mock_loop_record = {
            "id": loop_id,
            "vendor_id": 2,
            "loop_name": f"測試迴圈 ({status_str})",
            "status": status_str,
            "config": {
                "batch_size": 50,
                "max_iterations": 10,
                "target_pass_rate": 0.85,
                "action_type_mode": "ai_assisted",
                "filters": {},
                "backtest_config": {}
            },
            "current_iteration": 1,
            "created_at": datetime.now()
        }

        conn = pool.getconn()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = mock_loop_record

        # Act
        result = await coordinator.load_loop(loop_id)

        # Assert
        assert coordinator.current_status == status_enum, f"狀態 {status_str} 應轉換為 {status_enum}，但得到 {coordinator.current_status}"
        print(f"  ✅ 狀態 {status_str} → {status_enum}")

    print("✅ 測試 3 通過")


async def main():
    """執行所有測試"""
    print("=" * 60)
    print("開始執行 load_loop 方法測試")
    print("=" * 60)

    try:
        await test_load_loop_success()
        await test_load_loop_not_found()
        await test_load_loop_handles_different_statuses()

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
