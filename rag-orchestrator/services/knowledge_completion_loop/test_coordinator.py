"""
測試 LoopCoordinator - start_loop 功能

簡單的整合測試，驗證迴圈啟動流程
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2.pool
import models
import coordinator

LoopCoordinator = coordinator.LoopCoordinator
LoopConfig = models.LoopConfig


async def test_start_loop():
    """測試啟動迴圈功能"""

    # 建立資料庫連接池
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host="localhost",
        database="aichatbot_admin",
        user="aichatbot",
        password="aichatbot_password"
    )

    try:
        # 建立協調器
        coordinator = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試迴圈"
        )

        # 建立配置
        config = LoopConfig(
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.8,
            action_type_mode="ai_assisted",
            filters={},
            backtest_config={}
        )

        # 啟動迴圈
        print("啟動迴圈...")
        result = await coordinator.start_loop(config)

        print("\n✅ 迴圈啟動成功！")
        print(f"Loop ID: {result['loop_id']}")
        print(f"狀態: {result['status']}")
        print(f"總測試案例數: {result['initial_statistics']['total_scenarios']}")
        print(f"預估迭代次數: {result['initial_statistics']['estimated_iterations']}")
        print(f"目標通過率: {result['initial_statistics']['target_pass_rate']}")

        return result

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(test_start_loop())
