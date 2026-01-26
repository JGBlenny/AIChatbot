#!/usr/bin/env python3
"""清理測試表單"""

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
TEST_FORM_IDS = ['test_network_maintenance', 'test_door_lock_repair']


async def cleanup():
    """刪除測試表單"""

    print("=" * 80)
    print("🗑️  清理測試表單")
    print("=" * 80)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 查詢測試表單
        test_forms = await conn.fetch("""
            SELECT id, form_id, form_name, vendor_id
            FROM form_schemas
            WHERE vendor_id = $1
              AND form_id = ANY($2::text[])
            ORDER BY id
        """, VENDOR_ID, TEST_FORM_IDS)

        if not test_forms:
            print("\n✅ 沒有找到測試表單，無需清理。")
            return

        print(f"\n📋 找到 {len(test_forms)} 個測試表單：\n")
        for form in test_forms:
            print(f"  • ID {form['id']}: {form['form_name']} ({form['form_id']})")

        # 檢查是否有 SOP 引用這些表單
        sop_refs = await conn.fetch("""
            SELECT id, item_name, next_form_id
            FROM vendor_sop_items
            WHERE next_form_id = ANY($1::text[])
        """, TEST_FORM_IDS)

        if sop_refs:
            print(f"\n⚠️  警告：有 {len(sop_refs)} 個 SOP 引用這些表單：\n")
            for sop in sop_refs:
                print(f"  • SOP {sop['id']}: {sop['item_name']} → {sop['next_form_id']}")
            print("\n  建議先清理 SOP 或將 SOP 的 next_form_id 設為 NULL。")

            if input("\n是否繼續刪除表單？（這會導致 SOP 引用失效）[y/N]: ").lower() != 'y':
                print("\n已取消刪除。")
                return

        # 刪除測試表單
        print(f"\n🗑️  開始刪除...")

        deleted_count = await conn.execute("""
            DELETE FROM form_schemas
            WHERE vendor_id = $1
              AND form_id = ANY($2::text[])
        """, VENDOR_ID, TEST_FORM_IDS)

        print(f"  ✅ 成功刪除 {len(test_forms)} 個測試表單")

    finally:
        await conn.close()

    print("\n" + "=" * 80)
    print("✅ 清理完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(cleanup())
