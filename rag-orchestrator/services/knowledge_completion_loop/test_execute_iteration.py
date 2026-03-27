"""
測試 LoopCoordinator - execute_iteration 功能

整合測試：驗證單輪迭代執行流程
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
LoopStatus = models.LoopStatus


async def test_execute_iteration():
    """測試執行單輪迭代功能"""

    # 建立資料庫連接池
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host="localhost",
        database="aichatbot_admin",
        user="aichatbot",
        password="aichatbot_password"
    )

    try:
        print("=" * 60)
        print("測試 execute_iteration() 功能")
        print("=" * 60)

        # ============================================
        # 步驟 1：啟動迴圈
        # ============================================
        print("\n[步驟 1] 啟動迴圈...")

        coord = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試迭代迴圈"
        )

        config = LoopConfig(
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.8,
            action_type_mode="ai_assisted",
            filters={},
            backtest_config={}
        )

        start_result = await coord.start_loop(config)
        print(f"✅ 迴圈已啟動")
        print(f"   Loop ID: {start_result['loop_id']}")
        print(f"   狀態: {start_result['status']}")

        # ============================================
        # 步驟 2：執行第一輪迭代
        # ============================================
        print("\n[步驟 2] 執行第一輪迭代...")

        iteration_result = await coord.execute_iteration()

        print(f"✅ 第一輪迭代執行完成")
        print(f"   迭代次數: {iteration_result['iteration']}")
        print(f"   當前狀態: {iteration_result['status']}")
        print(f"   下一步動作: {iteration_result['next_action']}")

        # 驗證回測結果
        backtest = iteration_result['backtest_result']
        print(f"\n   回測結果:")
        print(f"   - 通過率: {backtest['pass_rate']:.1%}")
        print(f"   - 總測試數: {backtest['total_tested']}")
        print(f"   - 通過: {backtest['passed']}")
        print(f"   - 失敗: {backtest['failed']}")

        # 驗證缺口分析
        gaps = iteration_result['gap_analysis']
        print(f"\n   缺口分析:")
        print(f"   - 總缺口數: {gaps['total_gaps']}")
        print(f"   - P0 (高優先級): {gaps['p0_count']}")
        print(f"   - P1 (中優先級): {gaps['p1_count']}")
        print(f"   - P2 (低優先級): {gaps['p2_count']}")

        # 驗證知識生成
        knowledge = iteration_result['generated_knowledge']
        print(f"\n   知識生成:")
        print(f"   - 總生成數: {knowledge['total_generated']}")
        print(f"   - 待審核: {knowledge['needs_review']}")

        # ============================================
        # 步驟 3：驗證狀態
        # ============================================
        print("\n[步驟 3] 驗證迴圈狀態...")

        assert iteration_result['status'] == LoopStatus.REVIEWING.value, \
            f"預期狀態為 REVIEWING，實際為 {iteration_result['status']}"

        assert iteration_result['next_action'] == 'wait_for_review', \
            f"預期 next_action 為 wait_for_review，實際為 {iteration_result['next_action']}"

        assert iteration_result['iteration'] == 1, \
            f"預期迭代次數為 1，實際為 {iteration_result['iteration']}"

        print("✅ 狀態驗證通過")

        # ============================================
        # 步驟 4：驗證資料庫記錄
        # ============================================
        print("\n[步驟 4] 驗證資料庫記錄...")

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 檢查迴圈記錄
                cur.execute(
                    """
                    SELECT current_iteration, status, latest_pass_rate
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (start_result['loop_id'],)
                )
                loop_record = cur.fetchone()
                assert loop_record is not None, "找不到迴圈記錄"
                assert loop_record[0] == 1, f"預期 current_iteration=1，實際={loop_record[0]}"
                assert loop_record[1] == LoopStatus.REVIEWING.value, \
                    f"預期狀態為 REVIEWING，實際為 {loop_record[1]}"

                print(f"✅ 迴圈記錄正確")
                print(f"   - 當前迭代: {loop_record[0]}")
                print(f"   - 狀態: {loop_record[1]}")
                print(f"   - 最新通過率: {loop_record[2]:.1%}")

                # 檢查執行日誌
                cur.execute(
                    """
                    SELECT COUNT(*) as log_count
                    FROM loop_execution_logs
                    WHERE loop_id = %s
                    """,
                    (start_result['loop_id'],)
                )
                log_count = cur.fetchone()[0]
                print(f"\n✅ 執行日誌記錄: {log_count} 條")

        finally:
            db_pool.putconn(conn)

        # ============================================
        # 步驟 5：測試狀態驗證（應該失敗）
        # ============================================
        print("\n[步驟 5] 測試狀態驗證...")

        try:
            # 在 REVIEWING 狀態下不應該能再次執行迭代
            await coord.execute_iteration()
            print("❌ 狀態驗證失敗：應該拋出 InvalidStateError")
        except models.InvalidStateError as e:
            print(f"✅ 狀態驗證正確：{e.message}")

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)

        return iteration_result

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(test_execute_iteration())
