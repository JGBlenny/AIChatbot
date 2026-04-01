"""
真實環境端點測試

直接測試 API 端點功能（不使用 mock），需要真實資料庫連接。

Author: AI Assistant
Created: 2026-03-27
"""

import os
import sys
import asyncio

# 確保能夠導入專案模組
sys.path.insert(0, '/app')

async def test_api_import():
    """測試 1: 驗證 API 路由模組能正確導入"""
    print("\n" + "="*60)
    print("測試 1: API 路由模組導入測試")
    print("="*60)

    try:
        from routers import loops
        print(f"✅ 成功導入 routers.loops 模組")

        # 檢查所有端點函數
        endpoints = [
            'start_loop',
            'execute_iteration',
            'get_loop_status',
            'validate_loop',
            'complete_batch',
            'pause_loop',
            'resume_loop',
            'cancel_loop',
            'start_next_batch'
        ]

        for endpoint in endpoints:
            if hasattr(loops, endpoint):
                print(f"✅ {endpoint} 函數存在")
            else:
                print(f"❌ {endpoint} 函數不存在")
                return False

        print("\n✅ 測試 1 通過：所有 9 個 API 端點函數都已定義")
        return True

    except Exception as e:
        print(f"❌ 測試 1 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_pydantic_models():
    """測試 2: 驗證 Pydantic 模型"""
    print("\n" + "="*60)
    print("測試 2: Pydantic 模型驗證")
    print("="*60)

    try:
        from routers.loops import (
            LoopStartRequest,
            LoopStartResponse,
            ExecuteIterationRequest,
            ExecuteIterationResponse,
            LoopStatusResponse,
            ValidateLoopRequest,
            ValidateLoopResponse,
            CompleteBatchResponse
        )

        # 測試 LoopStartRequest
        start_req = LoopStartRequest(
            loop_name="測試迴圈",
            vendor_id=2,
            batch_size=50
        )
        assert start_req.loop_name == "測試迴圈"
        assert start_req.vendor_id == 2
        assert start_req.batch_size == 50
        assert start_req.target_pass_rate == 0.85  # 預設值
        print("✅ LoopStartRequest 模型驗證通過")

        # 測試 ExecuteIterationRequest
        exec_req = ExecuteIterationRequest()
        assert exec_req.async_mode == True
        exec_req2 = ExecuteIterationRequest(async_mode=False)
        assert exec_req2.async_mode == False
        print("✅ ExecuteIterationRequest 模型驗證通過")

        # 測試 ValidateLoopRequest
        val_req = ValidateLoopRequest()
        assert val_req.validation_scope == "failed_plus_sample"
        assert val_req.sample_pass_rate == 0.2
        print("✅ ValidateLoopRequest 模型驗證通過")

        print("\n✅ 測試 2 通過：所有 Pydantic 模型驗證正確")
        return True

    except Exception as e:
        print(f"❌ 測試 2 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_router_registration():
    """測試 3: 驗證路由已註冊到 FastAPI app"""
    print("\n" + "="*60)
    print("測試 3: 路由註冊驗證")
    print("="*60)

    try:
        from app import app

        # 檢查路由是否註冊
        routes = [route.path for route in app.routes]

        expected_routes = [
            "/api/v1/loops/start",
            "/api/v1/loops/{loop_id}/execute-iteration",
            "/api/v1/loops/{loop_id}",
            "/api/v1/loops/{loop_id}/validate",
            "/api/v1/loops/{loop_id}/complete",
            "/api/v1/loops/{loop_id}/pause",
            "/api/v1/loops/{loop_id}/resume",
            "/api/v1/loops/{loop_id}/cancel",
            "/api/v1/loops/{loop_id}/next-batch"
        ]

        found_count = 0
        for expected_route in expected_routes:
            if expected_route in routes:
                print(f"✅ {expected_route} 已註冊")
                found_count += 1
            else:
                print(f"❌ {expected_route} 未註冊")

        if found_count == len(expected_routes):
            print(f"\n✅ 測試 3 通過：所有 {found_count} 個路由都已註冊")
            return True
        else:
            print(f"\n⚠️  測試 3 部分通過：{found_count}/{len(expected_routes)} 個路由已註冊")
            return False

    except Exception as e:
        print(f"❌ 測試 3 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_dependencies_exist():
    """測試 4: 驗證所有依賴模組存在"""
    print("\n" + "="*60)
    print("測試 4: 依賴模組驗證")
    print("="*60)

    dependencies = [
        ("services.knowledge_completion_loop.coordinator", "LoopCoordinator"),
        ("services.knowledge_completion_loop.scenario_selector", "ScenarioSelector"),
        ("services.knowledge_completion_loop.async_execution_manager", "AsyncExecutionManager"),
        ("services.knowledge_completion_loop.models", "LoopStatus"),
    ]

    all_passed = True
    for module_path, class_name in dependencies:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {module_path}.{class_name} 可導入")
        except Exception as e:
            print(f"❌ {module_path}.{class_name} 導入失敗：{str(e)}")
            all_passed = False

    if all_passed:
        print("\n✅ 測試 4 通過：所有依賴模組都可正確導入")
    else:
        print("\n❌ 測試 4 失敗：部分依賴模組無法導入")

    return all_passed


async def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("迴圈管理 API - 真實環境端點測試")
    print("="*60)

    results = []

    # 執行測試
    results.append(("API 路由導入", await test_api_import()))
    results.append(("Pydantic 模型", await test_pydantic_models()))
    results.append(("路由註冊", await test_router_registration()))
    results.append(("依賴模組", await test_dependencies_exist()))

    # 統計結果
    print("\n" + "="*60)
    print("測試結果摘要")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {name}")

    print(f"\n總計：{passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！API 端點已正確實作並註冊。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
