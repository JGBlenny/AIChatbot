"""
測試 LoopCoordinator - 迴圈控制功能

測試 pause, resume, cancel, terminate 方法
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


async def test_loop_control():
    """測試迴圈控制功能"""

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
        print("測試迴圈控制功能")
        print("=" * 60)

        # ============================================
        # 測試 1：pause_loop() - 暫停迴圈
        # ============================================
        print("\n[測試 1] 測試 pause_loop()...")

        coord = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試控制迴圈"
        )

        config = LoopConfig(
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.8,
            action_type_mode="ai_assisted",
            filters={},
            backtest_config={}
        )

        # 啟動迴圈
        start_result = await coord.start_loop(config)
        print(f"✅ 迴圈已啟動 (Loop ID: {start_result['loop_id']}, 狀態: {start_result['status']})")

        # 暫停迴圈
        pause_result = await coord.pause_loop("測試暫停功能")
        print(f"✅ 迴圈已暫停")
        print(f"   狀態: {pause_result['status']}")
        print(f"   原因: {pause_result['reason']}")
        print(f"   暫停前狀態: {pause_result['previous_status']}")

        assert pause_result['status'] == LoopStatus.PAUSED.value, \
            f"預期狀態為 PAUSED，實際為 {pause_result['status']}"

        # 測試在 PAUSED 狀態不能再次暫停
        try:
            await coord.pause_loop("重複暫停")
            print("❌ 應該拋出 InvalidStateError")
        except models.InvalidStateError as e:
            print(f"✅ 正確拋出錯誤: {e.message}")

        # ============================================
        # 測試 2：resume_loop() - 恢復迴圈
        # ============================================
        print("\n[測試 2] 測試 resume_loop()...")

        resume_result = await coord.resume_loop()
        print(f"✅ 迴圈已恢復")
        print(f"   狀態: {resume_result['status']}")

        assert resume_result['status'] == LoopStatus.RUNNING.value, \
            f"預期狀態為 RUNNING，實際為 {resume_result['status']}"

        # 測試在 RUNNING 狀態不能恢復
        try:
            await coord.resume_loop()
            print("❌ 應該拋出 InvalidStateError")
        except models.InvalidStateError as e:
            print(f"✅ 正確拋出錯誤: {e.message}")

        # ============================================
        # 測試 3：cancel_loop() - 取消迴圈
        # ============================================
        print("\n[測試 3] 測試 cancel_loop()...")

        # 先暫停再取消
        await coord.pause_loop("準備取消")
        print(f"✅ 迴圈已暫停")

        cancel_result = await coord.cancel_loop("用戶主動取消測試")
        print(f"✅ 迴圈已取消")
        print(f"   狀態: {cancel_result['status']}")
        print(f"   原因: {cancel_result['reason']}")

        assert cancel_result['status'] == LoopStatus.CANCELLED.value, \
            f"預期狀態為 CANCELLED，實際為 {cancel_result['status']}"

        # 測試已取消的迴圈不能再取消
        try:
            await coord.cancel_loop("重複取消")
            print("❌ 應該拋出 InvalidStateError")
        except models.InvalidStateError as e:
            print(f"✅ 正確拋出錯誤: {e.message}")

        # ============================================
        # 測試 4：terminate_loop() - 終止迴圈（達到目標）
        # ============================================
        print("\n[測試 4] 測試 terminate_loop() - 達到目標通過率...")

        # 建立新迴圈
        coord2 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試終止迴圈-完成"
        )

        start_result2 = await coord2.start_loop(config)
        print(f"✅ 新迴圈已啟動 (Loop ID: {start_result2['loop_id']})")

        # 終止迴圈（達到目標）
        terminate_result = await coord2.terminate_loop("達到目標通過率 85%")
        print(f"✅ 迴圈已終止")
        print(f"   狀態: {terminate_result['status']}")
        print(f"   原因: {terminate_result['reason']}")

        assert terminate_result['status'] == LoopStatus.COMPLETED.value, \
            f"預期狀態為 COMPLETED，實際為 {terminate_result['status']}"

        # ============================================
        # 測試 5：terminate_loop() - 其他原因終止
        # ============================================
        print("\n[測試 5] 測試 terminate_loop() - 超過最大迭代次數...")

        # 建立新迴圈
        coord3 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試終止迴圈-超時"
        )

        start_result3 = await coord3.start_loop(config)
        print(f"✅ 新迴圈已啟動 (Loop ID: {start_result3['loop_id']})")

        # 終止迴圈（超過最大迭代次數）
        terminate_result2 = await coord3.terminate_loop("超過最大迭代次數 20 輪")
        print(f"✅ 迴圈已終止")
        print(f"   狀態: {terminate_result2['status']}")
        print(f"   原因: {terminate_result2['reason']}")

        assert terminate_result2['status'] == LoopStatus.TERMINATED.value, \
            f"預期狀態為 TERMINATED，實際為 {terminate_result2['status']}"

        # ============================================
        # 測試 6：驗證資料庫記錄
        # ============================================
        print("\n[測試 6] 驗證資料庫記錄...")

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 檢查第一個迴圈（已取消）
                cur.execute(
                    """
                    SELECT status, completed_at, paused_at
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (start_result['loop_id'],)
                )
                loop1 = cur.fetchone()
                print(f"✅ 迴圈 1 狀態: {loop1[0]}")
                print(f"   完成時間: {loop1[1]}")
                print(f"   暫停時間: {loop1[2]}")

                assert loop1[0] == LoopStatus.CANCELLED.value
                assert loop1[1] is not None, "completed_at 應該有值"
                assert loop1[2] is not None, "paused_at 應該有值"

                # 檢查第二個迴圈（已完成）
                cur.execute(
                    """
                    SELECT status, completed_at
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (start_result2['loop_id'],)
                )
                loop2 = cur.fetchone()
                print(f"\n✅ 迴圈 2 狀態: {loop2[0]}")
                print(f"   完成時間: {loop2[1]}")

                assert loop2[0] == LoopStatus.COMPLETED.value
                assert loop2[1] is not None

                # 檢查執行日誌
                cur.execute(
                    """
                    SELECT COUNT(*) as log_count
                    FROM loop_execution_logs
                    WHERE loop_id = %s
                      AND event_type IN ('loop_paused', 'loop_resumed', 'loop_cancelled')
                    """,
                    (start_result['loop_id'],)
                )
                log_count = cur.fetchone()[0]
                print(f"\n✅ 迴圈 1 控制事件日誌: {log_count} 條")
                assert log_count >= 3, "應該至少有 3 條控制事件（暫停、恢復、取消）"

        finally:
            db_pool.putconn(conn)

        # ============================================
        # 測試 7：暫停後恢復的狀態正確性
        # ============================================
        print("\n[測試 7] 測試暫停/恢復狀態保留...")

        coord4 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試狀態保留"
        )

        start_result4 = await coord4.start_loop(config)
        print(f"✅ 新迴圈已啟動")

        # 執行迭代到 REVIEWING 狀態
        iteration_result = await coord4.execute_iteration()
        print(f"✅ 執行迭代完成 (狀態: {iteration_result['status']})")

        # 在 REVIEWING 狀態暫停
        await coord4.pause_loop("在審核狀態暫停")
        print(f"✅ 在 REVIEWING 狀態暫停")

        # 恢復應該回到 REVIEWING
        resume_result4 = await coord4.resume_loop()
        print(f"✅ 恢復後狀態: {resume_result4['status']}")

        assert resume_result4['status'] == LoopStatus.REVIEWING.value, \
            f"預期恢復到 REVIEWING，實際為 {resume_result4['status']}"

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(test_loop_control())
