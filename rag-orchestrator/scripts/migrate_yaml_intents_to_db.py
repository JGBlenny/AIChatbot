#!/usr/bin/env python3
"""
將 YAML 意圖配置遷移到資料庫
"""

import yaml
import asyncpg
import asyncio
import os
from pathlib import Path


async def migrate_intents():
    """遷移 YAML 意圖到資料庫"""

    # 1. 讀取 YAML 配置
    yaml_path = Path(__file__).parent.parent / "config" / "intents.yaml"

    print(f"📖 讀取 YAML 配置: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    intents = config.get('intents', [])
    print(f"✅ 找到 {len(intents)} 個意圖")

    # 2. 連接資料庫
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'aichatbot'),
        password=os.getenv('DB_PASSWORD', 'aichatbot_password'),
        database=os.getenv('DB_NAME', 'aichatbot_admin')
    )

    print("✅ 資料庫連接成功")

    # 3. 檢查資料庫中是否已有意圖
    existing_count = await conn.fetchval("SELECT COUNT(*) FROM intents")

    if existing_count > 0:
        print(f"⚠️  資料庫中已有 {existing_count} 個意圖")
        response = input("是否要清空現有資料並重新導入？ (y/N): ")
        if response.lower() == 'y':
            await conn.execute("DELETE FROM intents")
            print("✅ 已清空現有意圖")
        else:
            print("❌ 取消導入")
            await conn.close()
            return

    # 4. 插入意圖到資料庫
    inserted_count = 0

    for intent in intents:
        try:
            await conn.execute("""
                INSERT INTO intents (
                    name,
                    type,
                    description,
                    keywords,
                    confidence_threshold,
                    api_required,
                    api_endpoint,
                    api_action,
                    is_enabled,
                    priority,
                    created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                intent['name'],
                intent['type'],
                intent.get('description', ''),
                intent.get('keywords', []),
                intent.get('confidence_threshold', 0.80),
                intent.get('api_required', False),
                intent.get('api_endpoint'),
                intent.get('api_action'),
                True,  # 預設啟用
                0,     # 預設優先級
                'migration_script'
            )

            inserted_count += 1
            print(f"  ✓ {intent['name']} ({intent['type']})")

        except Exception as e:
            print(f"  ✗ {intent['name']} - 錯誤: {e}")

    print(f"\n✅ 成功導入 {inserted_count}/{len(intents)} 個意圖")

    # 5. 顯示統計資訊
    stats = await conn.fetch("""
        SELECT
            type,
            COUNT(*) as count,
            SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) as enabled_count
        FROM intents
        GROUP BY type
        ORDER BY type
    """)

    print("\n📊 意圖統計:")
    print("─" * 50)
    for row in stats:
        print(f"  {row['type']}: {row['count']} 個 (啟用: {row['enabled_count']})")

    # 6. 關閉連接
    await conn.close()
    print("\n✅ 遷移完成！")


if __name__ == "__main__":
    asyncio.run(migrate_intents())
