#!/usr/bin/env python3
"""
測試 IntentManager 服務和資料庫功能
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from services.intent_manager import IntentManager


async def test_intent_manager():
    """測試 IntentManager 所有功能"""

    manager = IntentManager()

    print("=" * 80)
    print("測試 IntentManager 服務")
    print("=" * 80)
    print()

    # Test 1: 取得所有意圖
    print("📋 Test 1: 取得所有意圖")
    intents = await manager.get_all_intents()
    print(f"✅ 找到 {len(intents)} 個意圖")
    for intent in intents[:3]:
        print(f"  - {intent['name']} ({intent['type']}) - 知識庫: {intent['knowledge_count']} - 使用次數: {intent['usage_count']}")
    print()

    # Test 2: 取得特定意圖
    print("📋 Test 2: 取得特定意圖 (ID=1)")
    intent = await manager.get_intent_by_id(1)
    if intent:
        print(f"✅ 意圖名稱: {intent['name']}")
        print(f"   類型: {intent['type']}")
        print(f"   關鍵字: {', '.join(intent['keywords'][:5])}")
    print()

    # Test 3: 根據名稱取得意圖
    print("📋 Test 3: 根據名稱取得意圖 (退租流程)")
    intent = await manager.get_intent_by_name("退租流程")
    if intent:
        print(f"✅ 找到意圖 ID: {intent['id']}")
        print(f"   描述: {intent['description']}")
    print()

    # Test 4: 新增測試意圖
    print("📋 Test 4: 新增測試意圖")
    try:
        new_id = await manager.create_intent(
            name="測試意圖_寵物政策",
            type="knowledge",
            description="詢問租屋處寵物飼養相關規定",
            keywords=["寵物", "貓", "狗", "飼養"],
            confidence_threshold=0.80,
            created_by="test_script"
        )
        print(f"✅ 成功新增意圖，ID: {new_id}")
    except Exception as e:
        print(f"⚠️ 新增失敗（可能已存在）: {e}")
    print()

    # Test 5: 更新意圖
    print("📋 Test 5: 更新測試意圖")
    test_intent = await manager.get_intent_by_name("測試意圖_寵物政策")
    if test_intent:
        success = await manager.update_intent(
            intent_id=test_intent['id'],
            description="【更新】詢問租屋處寵物飼養相關規定和收費標準",
            priority=10,
            updated_by="test_script"
        )
        print(f"✅ 更新成功: {success}")
    print()

    # Test 6: 停用意圖
    print("📋 Test 6: 停用測試意圖")
    if test_intent:
        success = await manager.toggle_intent(test_intent['id'], is_enabled=False)
        print(f"✅ 停用成功: {success}")
    print()

    # Test 7: 取得統計資訊
    print("📋 Test 7: 取得意圖統計資訊")
    stats = await manager.get_intent_stats()
    print(f"✅ 總意圖數: {stats['total_intents']}")
    print(f"   啟用意圖: {stats['enabled_intents']}")
    print(f"   停用意圖: {stats['disabled_intents']}")
    print()
    print("   按類型統計:")
    for type_stat in stats['by_type']:
        print(f"   - {type_stat['type']}: {type_stat['total']} 個 (啟用: {type_stat['enabled']})")
    print()
    print("   知識庫覆蓋率 (前5個):")
    for intent in stats['knowledge_coverage'][:5]:
        print(f"   - {intent['name']}: {intent['knowledge_count']} 條知識")
    print()

    # Test 8: 啟用意圖
    print("📋 Test 8: 啟用測試意圖")
    if test_intent:
        success = await manager.toggle_intent(test_intent['id'], is_enabled=True)
        print(f"✅ 啟用成功: {success}")
    print()

    # Test 9: 刪除測試意圖
    print("📋 Test 9: 刪除測試意圖")
    if test_intent:
        success = await manager.delete_intent(test_intent['id'])
        print(f"✅ 刪除成功（軟刪除）: {success}")
    print()

    # Test 10: 驗證刪除
    print("📋 Test 10: 驗證刪除結果")
    deleted_intent = await manager.get_intent_by_id(test_intent['id'])
    if deleted_intent:
        print(f"✅ 意圖仍存在，is_enabled = {deleted_intent['is_enabled']}")
    print()

    print("=" * 80)
    print("✅ 所有測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_intent_manager())
