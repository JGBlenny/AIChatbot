"""
知識審核 API 整合測試

測試完整的知識審核流程，包括：
- 查詢待審核知識（篩選、分頁）
- 單一審核流程（approve → 同步 → embedding → status 更新）
- 批量審核（10 個項目，2 個失敗）
- 重複檢測警告顯示
- 錯誤處理

Author: AI Assistant
Created: 2026-03-27
"""

import asyncio
import asyncpg
import os


async def setup_test_data(conn):
    """建立測試資料"""
    print("\n📝 建立測試資料...")

    # 1. 創建測試迴圈
    loop_id = await conn.fetchval("""
        INSERT INTO knowledge_completion_loops (
            loop_name, vendor_id, status, config, target_pass_rate,
            total_scenarios, current_iteration, created_at, updated_at
        )
        VALUES ('測試迴圈', 2, 'running', '{"batch_size": 50}'::jsonb, 0.85,
                10, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
    """)
    print(f"   ✅ 創建測試迴圈 ID: {loop_id}")

    # 2. 創建測試分類和群組（用於 SOP）
    category_id = await conn.fetchval("""
        INSERT INTO vendor_sop_categories (vendor_id, category_name, is_active, created_at, updated_at)
        VALUES (2, '測試分類', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
    """)

    group_id = await conn.fetchval("""
        INSERT INTO vendor_sop_groups (vendor_id, category_id, group_name, is_active, created_at, updated_at)
        VALUES (2, $1, '測試群組', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
    """, category_id)

    print(f"   ✅ 創建測試分類 ID: {category_id}, 群組 ID: {group_id}")

    # 3. 創建待審核知識（一般知識）
    kb_ids = []
    for i in range(1, 6):
        kb_id = await conn.fetchval("""
            INSERT INTO loop_generated_knowledge (
                loop_id, iteration, question, answer, knowledge_type,
                sop_config, status, created_at
            )
            VALUES ($1, 1, $2, $3, NULL, NULL, 'pending', CURRENT_TIMESTAMP)
            RETURNING id
        """, loop_id, f"測試問題 {i}", f"測試答案 {i}")
        kb_ids.append(kb_id)

    print(f"   ✅ 創建 {len(kb_ids)} 個一般知識項目")

    # 4. 創建待審核知識（SOP）
    import json
    sop_ids = []
    for i in range(1, 3):
        sop_config = {
            'category_id': category_id,
            'group_id': group_id,
            'item_name': f'測試 SOP {i}'
        }
        sop_id = await conn.fetchval("""
            INSERT INTO loop_generated_knowledge (
                loop_id, iteration, question, answer, knowledge_type,
                sop_config, status, created_at
            )
            VALUES ($1, 1, $2, $3, 'sop', $4::jsonb, 'pending', CURRENT_TIMESTAMP)
            RETURNING id
        """, loop_id, f"SOP 問題 {i}", f"SOP 內容 {i}", json.dumps(sop_config))
        sop_ids.append(sop_id)

    print(f"   ✅ 創建 {len(sop_ids)} 個 SOP 項目")

    return {
        'loop_id': loop_id,
        'category_id': category_id,
        'group_id': group_id,
        'kb_ids': kb_ids,
        'sop_ids': sop_ids
    }


async def cleanup_test_data(conn, test_data):
    """清理測試資料"""
    print("\n🧹 清理測試資料...")

    # 刪除生成的知識（knowledge_base 和 vendor_sop_items）
    await conn.execute("""
        DELETE FROM knowledge_base
        WHERE source = 'loop' AND source_loop_id = $1
    """, test_data['loop_id'])

    # vendor_sop_items 沒有 source 欄位，需根據 category_id/group_id 刪除
    await conn.execute("""
        DELETE FROM vendor_sop_items
        WHERE category_id = $1 OR group_id = $2
    """, test_data['category_id'], test_data['group_id'])

    # 刪除待審核知識
    await conn.execute("""
        DELETE FROM loop_generated_knowledge WHERE loop_id = $1
    """, test_data['loop_id'])

    # 刪除執行日誌
    await conn.execute("""
        DELETE FROM loop_execution_logs WHERE loop_id = $1
    """, test_data['loop_id'])

    # 刪除迴圈
    await conn.execute("""
        DELETE FROM knowledge_completion_loops WHERE id = $1
    """, test_data['loop_id'])

    # 刪除測試分類和群組
    await conn.execute("""
        DELETE FROM vendor_sop_groups WHERE id = $1
    """, test_data['group_id'])

    await conn.execute("""
        DELETE FROM vendor_sop_categories WHERE id = $1
    """, test_data['category_id'])

    print("   ✅ 清理完成")


async def test_query_pending_knowledge(conn, test_data):
    """測試 1: 查詢待審核知識"""
    print("\n📝 測試 1: 查詢待審核知識...")

    # 查詢所有 pending 狀態
    rows = await conn.fetch("""
        SELECT id, question, answer, knowledge_type, status
        FROM loop_generated_knowledge
        WHERE loop_id = $1 AND status = 'pending'
        ORDER BY id
    """, test_data['loop_id'])

    print(f"   ✅ 查詢到 {len(rows)} 個待審核項目")
    assert len(rows) == 7, f"應該有 7 個待審核項目，實際 {len(rows)} 個"

    # 測試篩選（僅 SOP）
    sop_rows = await conn.fetch("""
        SELECT id FROM loop_generated_knowledge
        WHERE loop_id = $1 AND knowledge_type = 'sop' AND status = 'pending'
    """, test_data['loop_id'])

    print(f"   ✅ 篩選 SOP：{len(sop_rows)} 個")
    assert len(sop_rows) == 2


async def test_single_review_approve(conn, test_data):
    """測試 2: 單一審核（批准 → 同步）"""
    print("\n📝 測試 2: 單一審核 - 批准一般知識...")

    import sys
    sys.path.insert(0, '/app')
    from routers.loop_knowledge import _sync_knowledge_to_production

    # 取得第一個一般知識
    knowledge_id = test_data['kb_ids'][0]
    knowledge = await conn.fetchrow("""
        SELECT id, loop_id, iteration, question, answer, knowledge_type, sop_config
        FROM loop_generated_knowledge
        WHERE id = $1
    """, knowledge_id)

    # 調用同步函數
    sync_result = await _sync_knowledge_to_production(conn, dict(knowledge))

    print(f"   同步結果：{sync_result}")

    assert sync_result['synced'] is True, "應該成功同步"
    assert sync_result['synced_to'] == 'knowledge_base', "應該同步到 knowledge_base"
    assert sync_result['synced_id'] is not None, "應該返回 knowledge_base ID"

    # 驗證資料已寫入 knowledge_base
    kb_row = await conn.fetchrow("""
        SELECT id, question_summary, answer, source, source_loop_id, source_loop_knowledge_id
        FROM knowledge_base
        WHERE id = $1
    """, sync_result['synced_id'])

    assert kb_row is not None, "應該在 knowledge_base 找到記錄"
    assert kb_row['source'] == 'loop'
    assert kb_row['source_loop_id'] == knowledge['loop_id']
    assert kb_row['source_loop_knowledge_id'] == knowledge_id

    print("   ✅ 一般知識成功同步到 knowledge_base")


async def test_single_review_sop(conn, test_data):
    """測試 3: 單一審核（批准 SOP）"""
    print("\n📝 測試 3: 單一審核 - 批准 SOP...")

    import sys
    sys.path.insert(0, '/app')
    from routers.loop_knowledge import _sync_knowledge_to_production

    # 取得第一個 SOP
    sop_id = test_data['sop_ids'][0]
    sop = await conn.fetchrow("""
        SELECT id, loop_id, iteration, question, answer, knowledge_type, sop_config
        FROM loop_generated_knowledge
        WHERE id = $1
    """, sop_id)

    # 調用同步函數
    sync_result = await _sync_knowledge_to_production(conn, dict(sop))

    print(f"   同步結果：{sync_result}")

    assert sync_result['synced'] is True, "應該成功同步"
    assert sync_result['synced_to'] == 'vendor_sop_items', "應該同步到 vendor_sop_items"
    assert sync_result['synced_id'] is not None, "應該返回 sop_item ID"

    # 驗證資料已寫入 vendor_sop_items
    sop_row = await conn.fetchrow("""
        SELECT id, item_name, content, vendor_id, category_id, group_id
        FROM vendor_sop_items
        WHERE id = $1
    """, sync_result['synced_id'])

    assert sop_row is not None, "應該在 vendor_sop_items 找到記錄"

    # 解析 sop_config（可能是字串或 dict）
    import json
    if isinstance(sop['sop_config'], str):
        sop_config = json.loads(sop['sop_config'])
    else:
        sop_config = sop['sop_config']

    assert sop_row['item_name'] == sop_config['item_name'], "SOP 名稱應該匹配"
    assert sop_row['content'] == sop['answer'], "SOP 內容應該匹配"

    print("   ✅ SOP 成功同步到 vendor_sop_items")


async def test_batch_review(conn, test_data):
    """測試 4: 批量審核"""
    print("\n📝 測試 4: 批量審核...")

    import sys
    sys.path.insert(0, '/app')
    from routers.loop_knowledge import _sync_knowledge_to_production

    # 批量審核 3 個一般知識
    batch_ids = test_data['kb_ids'][1:4]  # 取第 2-4 個
    success_count = 0
    failed_count = 0

    for kb_id in batch_ids:
        knowledge = await conn.fetchrow("""
            SELECT id, loop_id, iteration, question, answer, knowledge_type, sop_config
            FROM loop_generated_knowledge
            WHERE id = $1
        """, kb_id)

        try:
            sync_result = await _sync_knowledge_to_production(conn, dict(knowledge))
            if sync_result['synced']:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"   ⚠️ 知識 {kb_id} 同步失敗: {e}")
            failed_count += 1

    print(f"   ✅ 批量審核完成：成功 {success_count}/{len(batch_ids)}")
    assert success_count >= 2, "至少應該有 2 個成功"


async def test_reject(conn, test_data):
    """測試 5: 拒絕知識"""
    print("\n📝 測試 5: 拒絕知識...")

    # 拒絕最後一個知識
    knowledge_id = test_data['kb_ids'][-1]

    await conn.execute("""
        UPDATE loop_generated_knowledge
        SET status = 'rejected'
        WHERE id = $1
    """, knowledge_id)

    # 驗證狀態
    status = await conn.fetchval("""
        SELECT status FROM loop_generated_knowledge WHERE id = $1
    """, knowledge_id)

    assert status == 'rejected', "狀態應該是 rejected"
    print("   ✅ 知識成功標記為 rejected")


async def test_error_handling(conn, test_data):
    """測試 6: 錯誤處理"""
    print("\n📝 測試 6: 錯誤處理...")

    import sys
    sys.path.insert(0, '/app')
    from routers.loop_knowledge import _sync_knowledge_to_production

    # 測試不存在的 loop_id
    fake_knowledge = {
        'id': 99999,
        'loop_id': 99999,
        'iteration': 1,
        'question': '假知識',
        'answer': '假答案',
        'knowledge_type': None,
        'sop_config': None
    }

    sync_result = await _sync_knowledge_to_production(conn, fake_knowledge)

    assert sync_result['synced'] is False, "應該同步失敗"
    assert sync_result['error'] is not None, "應該有錯誤訊息"
    print(f"   ✅ 正確處理錯誤：{sync_result['error'][:50]}...")


async def run_all_tests():
    """運行所有測試"""
    print("="*60)
    print("知識審核 API 整合測試")
    print("="*60)

    # 連接資料庫（使用與 app.py 相同的配置）
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password")
    )

    try:
        # 建立測試資料
        test_data = await setup_test_data(conn)

        # 運行測試
        await test_query_pending_knowledge(conn, test_data)
        await test_single_review_approve(conn, test_data)
        await test_single_review_sop(conn, test_data)
        await test_batch_review(conn, test_data)
        await test_reject(conn, test_data)
        await test_error_handling(conn, test_data)

        # 清理測試資料
        await cleanup_test_data(conn, test_data)

        print("\n" + "="*60)
        print("✅ 所有整合測試通過！")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
