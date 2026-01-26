#!/usr/bin/env python3
"""清理測試 SOP 數據"""

import asyncio
import asyncpg

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aichatbot_admin",
    "user": "aichatbot",
    "password": "aichatbot_password"
}

VENDOR_ID = 2
TEST_ITEM_NUMBERS = [9001, 9002, 9003, 9004, 9005, 9006]


async def cleanup():
    """刪除測試 SOP"""

    print("=" * 80)
    print("🗑️  清理測試 SOP 數據")
    print("=" * 80)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 查詢測試 SOP
        test_sops = await conn.fetch("""
            SELECT id, item_name, item_number
            FROM vendor_sop_items
            WHERE vendor_id = $1
              AND item_number = ANY($2::int[])
            ORDER BY item_number
        """, VENDOR_ID, TEST_ITEM_NUMBERS)

        if not test_sops:
            print("\n✅ 沒有找到測試 SOP，無需清理。")
            return

        print(f"\n📋 找到 {len(test_sops)} 個測試 SOP：\n")
        for sop in test_sops:
            print(f"  • ID {sop['id']}: {sop['item_name']} (#{sop['item_number']})")

        # 刪除測試 SOP
        print(f"\n🗑️  開始刪除...")

        deleted_count = await conn.execute("""
            DELETE FROM vendor_sop_items
            WHERE vendor_id = $1
              AND item_number = ANY($2::int[])
        """, VENDOR_ID, TEST_ITEM_NUMBERS)

        print(f"  ✅ 成功刪除 {len(test_sops)} 個測試 SOP")

    finally:
        await conn.close()

    print("\n" + "=" * 80)
    print("✅ 清理完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(cleanup())
