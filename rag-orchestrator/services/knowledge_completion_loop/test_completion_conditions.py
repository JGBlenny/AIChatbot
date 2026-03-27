"""
測試 LoopCoordinator - check_completion_conditions 功能

測試迴圈完成條件判斷
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2.pool
import psycopg2.extras
from datetime import datetime, timedelta
import models
import coordinator

LoopCoordinator = coordinator.LoopCoordinator
LoopConfig = models.LoopConfig
LoopStatus = models.LoopStatus


async def test_completion_conditions():
    """測試完成條件判斷功能"""

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
        print("測試迴圈完成條件判斷")
        print("=" * 60)

        # ============================================
        # 測試 1：達到目標通過率
        # ============================================
        print("\n[測試 1] 測試達到目標通過率...")

        coord1 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試目標通過率"
        )

        config = LoopConfig(
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.8,
            action_type_mode="ai_assisted",
            filters={},
            backtest_config={}
        )

        start_result = await coord1.start_loop(config)
        loop_id_1 = start_result['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_1})")

        # 手動設定 latest_pass_rate 為 0.85（達到目標 0.8）
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET latest_pass_rate = 0.85, current_iteration = 3
                    WHERE id = %s
                    """,
                    (loop_id_1,)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        should_complete, reason = await coord1.check_completion_conditions()
        print(f"✅ 完成條件檢查結果:")
        print(f"   應該完成: {should_complete}")
        print(f"   原因: {reason}")

        assert should_complete == True, "應該達到目標通過率"
        assert "達到目標通過率" in reason, f"原因應包含達到目標通過率，實際為: {reason}"

        # ============================================
        # 測試 2：超過最大迭代次數
        # ============================================
        print("\n[測試 2] 測試超過最大迭代次數...")

        coord2 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試最大迭代次數"
        )

        start_result2 = await coord2.start_loop(config)
        loop_id_2 = start_result2['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_2})")

        # 手動設定 current_iteration 為 10（達到最大值）
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET current_iteration = 10, latest_pass_rate = 0.65
                    WHERE id = %s
                    """,
                    (loop_id_2,)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        should_complete2, reason2 = await coord2.check_completion_conditions()
        print(f"✅ 完成條件檢查結果:")
        print(f"   應該完成: {should_complete2}")
        print(f"   原因: {reason2}")

        assert should_complete2 == True, "應該超過最大迭代次數"
        assert "超過最大迭代次數" in reason2, f"原因應包含超過最大迭代次數，實際為: {reason2}"

        # ============================================
        # 測試 3：連續 2 輪無明顯改善
        # ============================================
        print("\n[測試 3] 測試連續 2 輪無明顯改善...")

        coord3 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試無改善"
        )

        start_result3 = await coord3.start_loop(config)
        loop_id_3 = start_result3['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_3})")

        # 手動插入 3 輪回測事件，模擬連續無改善
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 第 1 輪：通過率 0.60
                cur.execute(
                    """
                    INSERT INTO loop_execution_logs (
                        loop_id, event_type, event_data, created_at
                    ) VALUES (%s, %s, %s, NOW() - INTERVAL '6 hours')
                    """,
                    (
                        loop_id_3,
                        "backtest_completed",
                        psycopg2.extras.Json({
                            "iteration": 1,
                            "pass_rate": 0.60,
                            "total_tested": 50
                        })
                    )
                )

                # 第 2 輪：通過率 0.61（提升 1%）
                cur.execute(
                    """
                    INSERT INTO loop_execution_logs (
                        loop_id, event_type, event_data, created_at
                    ) VALUES (%s, %s, %s, NOW() - INTERVAL '3 hours')
                    """,
                    (
                        loop_id_3,
                        "backtest_completed",
                        psycopg2.extras.Json({
                            "iteration": 2,
                            "pass_rate": 0.61,
                            "total_tested": 50
                        })
                    )
                )

                # 第 3 輪：通過率 0.615（提升 0.5%）
                cur.execute(
                    """
                    INSERT INTO loop_execution_logs (
                        loop_id, event_type, event_data, created_at
                    ) VALUES (%s, %s, %s, NOW())
                    """,
                    (
                        loop_id_3,
                        "backtest_completed",
                        psycopg2.extras.Json({
                            "iteration": 3,
                            "pass_rate": 0.615,
                            "total_tested": 50
                        })
                    )
                )

                # 更新迴圈資訊
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET current_iteration = 3, latest_pass_rate = 0.615
                    WHERE id = %s
                    """,
                    (loop_id_3,)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        should_complete3, reason3 = await coord3.check_completion_conditions()
        print(f"✅ 完成條件檢查結果:")
        print(f"   應該完成: {should_complete3}")
        print(f"   原因: {reason3}")

        assert should_complete3 == True, "應該檢測到連續無明顯改善"
        assert "連續 2 輪無明顯改善" in reason3, f"原因應包含無明顯改善，實際為: {reason3}"

        # ============================================
        # 測試 4：執行時間超過 24 小時
        # ============================================
        print("\n[測試 4] 測試執行時間超過 24 小時...")

        coord4 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試執行時間"
        )

        start_result4 = await coord4.start_loop(config)
        loop_id_4 = start_result4['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_4})")

        # 手動設定 started_at 為 25 小時前
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                past_time = datetime.now() - timedelta(hours=25)
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET started_at = %s, current_iteration = 5
                    WHERE id = %s
                    """,
                    (past_time, loop_id_4)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        should_complete4, reason4 = await coord4.check_completion_conditions()
        print(f"✅ 完成條件檢查結果:")
        print(f"   應該完成: {should_complete4}")
        print(f"   原因: {reason4}")

        assert should_complete4 == True, "應該檢測到執行時間超過 24 小時"
        assert "執行時間超過 24 小時" in reason4, f"原因應包含執行時間超過，實際為: {reason4}"

        # ============================================
        # 測試 5：未達到任何完成條件
        # ============================================
        print("\n[測試 5] 測試未達到任何完成條件...")

        coord5 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試未完成"
        )

        start_result5 = await coord5.start_loop(config)
        loop_id_5 = start_result5['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_5})")

        # 設定正常狀態（未達成任何完成條件）
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET current_iteration = 3,
                        latest_pass_rate = 0.65,
                        started_at = NOW() - INTERVAL '2 hours'
                    WHERE id = %s
                    """,
                    (loop_id_5,)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        should_complete5, reason5 = await coord5.check_completion_conditions()
        print(f"✅ 完成條件檢查結果:")
        print(f"   應該完成: {should_complete5}")
        print(f"   原因: {reason5}")

        assert should_complete5 == False, "不應該達到任何完成條件"
        assert reason5 == "", f"原因應為空字串，實際為: {reason5}"

        # ============================================
        # 測試 6：整合測試 - 自動終止迴圈
        # ============================================
        print("\n[測試 6] 整合測試 - 檢查並自動終止...")

        coord6 = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試自動終止"
        )

        start_result6 = await coord6.start_loop(config)
        loop_id_6 = start_result6['loop_id']
        print(f"✅ 迴圈已啟動 (Loop ID: {loop_id_6})")

        # 設定達到目標通過率
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_completion_loops
                    SET latest_pass_rate = 0.85, current_iteration = 5
                    WHERE id = %s
                    """,
                    (loop_id_6,)
                )
                conn.commit()
        finally:
            db_pool.putconn(conn)

        # 檢查完成條件
        should_complete6, reason6 = await coord6.check_completion_conditions()
        print(f"✅ 檢測到應該完成: {should_complete6}")
        print(f"   原因: {reason6}")

        # 如果應該完成，則終止迴圈
        if should_complete6:
            terminate_result = await coord6.terminate_loop(reason6)
            print(f"✅ 迴圈已終止")
            print(f"   狀態: {terminate_result['status']}")
            print(f"   原因: {terminate_result['reason']}")

            assert terminate_result['status'] == LoopStatus.COMPLETED.value, \
                "達到目標通過率應標記為 COMPLETED"

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
    asyncio.run(test_completion_conditions())
