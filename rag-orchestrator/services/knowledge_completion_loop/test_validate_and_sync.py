"""
測試 LoopCoordinator - validate_and_sync 功能

整合測試：驗證迭代驗證與批次同步流程
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


async def test_validate_and_sync():
    """測試驗證與同步功能"""

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
        print("測試 validate_and_sync() 功能")
        print("=" * 60)

        # ============================================
        # 步驟 1：啟動迴圈
        # ============================================
        print("\n[步驟 1] 啟動迴圈...")

        coord = LoopCoordinator(
            db_pool=db_pool,
            vendor_id=1,
            loop_name="測試驗證同步迴圈"
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
        print(f"✅ 迴圈已啟動 (Loop ID: {start_result['loop_id']})")

        # ============================================
        # 步驟 2：執行第一輪迭代
        # ============================================
        print("\n[步驟 2] 執行第一輪迭代...")

        iteration_result = await coord.execute_iteration()

        print(f"✅ 第一輪迭代完成")
        print(f"   狀態: {iteration_result['status']}")
        print(f"   生成知識數: {iteration_result['generated_knowledge']['total_generated']}")

        # 驗證狀態為 REVIEWING
        assert iteration_result['status'] == LoopStatus.REVIEWING.value, \
            f"預期狀態為 REVIEWING，實際為 {iteration_result['status']}"

        # ============================================
        # 步驟 3：模擬人工審核（Stub 已自動設為 approved）
        # ============================================
        print("\n[步驟 3] 檢查審核狀態（Stub 已自動審核通過）...")

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) as approved_count
                    FROM loop_generated_knowledge
                    WHERE loop_id = %s
                      AND iteration = 1
                      AND status = 'approved'
                    """,
                    (start_result['loop_id'],)
                )
                approved_count = cur.fetchone()[0]
                print(f"✅ 審核通過的知識數: {approved_count}")

        finally:
            db_pool.putconn(conn)

        # ============================================
        # 步驟 4：執行驗證與同步
        # ============================================
        print("\n[步驟 4] 執行驗證與同步...")

        sync_result = await coord.validate_and_sync()

        print(f"✅ 驗證與同步完成")
        print(f"   狀態: {sync_result['status']}")
        print(f"   下一步動作: {sync_result['next_action']}")

        # 驗證結果
        if sync_result['validation_result']:
            validation = sync_result['validation_result']
            print(f"\n   驗證回測結果:")
            print(f"   - 通過率: {validation['pass_rate']:.1%}")
            print(f"   - 改善幅度: {validation['improvement']:.1%}")
            print(f"   - 測試總數: {validation['total_tested']}")

        # 同步結果
        sync_info = sync_result['sync_result']
        print(f"\n   同步結果:")
        print(f"   - 成功同步: {sync_info['synced_count']}")
        print(f"   - 失敗數: {sync_info['failed_count']}")

        # ============================================
        # 步驟 5：驗證資料庫狀態
        # ============================================
        print("\n[步驟 5] 驗證資料庫狀態...")

        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 檢查迴圈狀態
                cur.execute(
                    """
                    SELECT status, latest_pass_rate
                    FROM knowledge_completion_loops
                    WHERE id = %s
                    """,
                    (start_result['loop_id'],)
                )
                loop_status = cur.fetchone()
                print(f"✅ 迴圈狀態: {loop_status[0]}")
                print(f"   最新通過率: {loop_status[1]:.1%}")

                assert loop_status[0] == LoopStatus.RUNNING.value, \
                    f"預期狀態為 RUNNING，實際為 {loop_status[0]}"

                # 檢查 loop_generated_knowledge 同步狀態
                cur.execute(
                    """
                    SELECT COUNT(*) as synced_count
                    FROM loop_generated_knowledge
                    WHERE loop_id = %s
                      AND iteration = 1
                      AND status = 'synced'
                      AND synced_to_kb = true
                      AND kb_id IS NOT NULL
                    """,
                    (start_result['loop_id'],)
                )
                synced_count = cur.fetchone()[0]
                print(f"\n✅ 已標記為 synced 的知識數: {synced_count}")

                # 檢查 knowledge_base 新增的知識
                cur.execute(
                    """
                    SELECT COUNT(*) as kb_count
                    FROM knowledge_base
                    WHERE source = 'loop'
                      AND source_loop_id = %s
                    """,
                    (start_result['loop_id'],)
                )
                kb_count = cur.fetchone()[0]
                print(f"✅ knowledge_base 新增知識數: {kb_count}")

                assert kb_count == synced_count, \
                    f"knowledge_base 知識數 ({kb_count}) 應等於 synced 知識數 ({synced_count})"

        finally:
            db_pool.putconn(conn)

        # ============================================
        # 步驟 6：測試無審核通過知識的情況
        # ============================================
        print("\n[步驟 6] 測試無審核通過知識的情況...")

        # 執行第二輪迭代（會生成新知識）
        iteration_result2 = await coord.execute_iteration()
        print(f"✅ 第二輪迭代完成 (狀態: {iteration_result2['status']})")

        # 手動將所有知識設為 rejected
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE loop_generated_knowledge
                    SET status = 'rejected'
                    WHERE loop_id = %s
                      AND iteration = 2
                    """,
                    (start_result['loop_id'],)
                )
                conn.commit()
                print("✅ 已將第二輪知識設為 rejected")

        finally:
            db_pool.putconn(conn)

        # 執行驗證（應該返回 review_again）
        sync_result2 = await coord.validate_and_sync()
        print(f"\n✅ 無審核通過知識的驗證結果:")
        print(f"   狀態: {sync_result2['status']}")
        print(f"   下一步動作: {sync_result2['next_action']}")
        print(f"   訊息: {sync_result2['message']}")

        assert sync_result2['next_action'] == 'review_again', \
            f"預期 next_action 為 review_again，實際為 {sync_result2['next_action']}"

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)

        return sync_result

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_pool.closeall()


if __name__ == "__main__":
    asyncio.run(test_validate_and_sync())
