#!/usr/bin/env python3
"""
從 Excel 導入電費寄送區間數據到 lookup_tables

用法:
    python3 scripts/data_import/import_billing_intervals.py

需求:
    - pandas
    - openpyxl
    - asyncpg
"""

import pandas as pd
import asyncpg
import asyncio
import os
import sys
import json
from pathlib import Path

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXCEL_FILE = PROJECT_ROOT / 'data' / '全案場電錶.xlsx'

# 數據庫配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aichatbot_admin',
    'user': 'aichatbot',
    'password': 'aichatbot_password'
}


async def import_data():
    """主導入函數"""

    print("=" * 60)
    print("📊 電費寄送區間數據導入")
    print("=" * 60)

    # 1. 驗證 Excel 文件
    if not EXCEL_FILE.exists():
        print(f"❌ Excel 文件不存在: {EXCEL_FILE}")
        sys.exit(1)

    print(f"✅ 找到 Excel 文件: {EXCEL_FILE}")

    # 2. 讀取 Excel
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ 成功讀取 Excel，共 {len(df)} 筆記錄")
        print(f"📋 欄位: {list(df.columns)}")
    except Exception as e:
        print(f"❌ 讀取 Excel 失敗: {e}")
        sys.exit(1)

    # 3. 連接數據庫
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print(f"✅ 數據庫連接成功")
    except Exception as e:
        print(f"❌ 數據庫連接失敗: {e}")
        print(f"   請確認:")
        print(f"   - PostgreSQL 服務正在運行")
        print(f"   - docker-compose up -d")
        sys.exit(1)

    try:
        # 4. 清空舊的測試數據（保留真實數據）
        deleted = await conn.execute("""
            DELETE FROM lookup_tables
            WHERE category = 'billing_interval'
              AND lookup_key LIKE '測試地址%'
        """)
        print(f"🗑️  清理舊測試數據: {deleted}")

        # 5. 處理並插入數據
        inserted = 0
        skipped = 0
        errors = []

        print(f"\n開始導入數據...")
        print("-" * 60)

        for idx, row in df.iterrows():
            try:
                # 提取字段
                address = str(row['物件地址']).strip() if pd.notna(row['物件地址']) else ''
                interval = str(row['寄送區間:單月/雙月']).strip() if pd.notna(row['寄送區間:單月/雙月']) else ''
                electric_number = str(row['電號']).strip() if pd.notna(row['電號']) else ''

                # 驗證必填字段
                if not address or address == 'nan':
                    skipped += 1
                    continue

                # 驗證寄送區間欄位非空即可（不限定具體值）
                if not interval or interval == 'nan':
                    errors.append(f"行 {idx+2}: 寄送區間為空")
                    skipped += 1
                    continue

                # 準備 metadata
                metadata = {}
                if electric_number and electric_number != 'nan':
                    metadata['electric_number'] = electric_number

                # 插入或更新數據庫
                await conn.execute("""
                    INSERT INTO lookup_tables (
                        vendor_id, category, category_name,
                        lookup_key, lookup_value, metadata, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (vendor_id, category, lookup_key)
                    DO UPDATE SET
                        lookup_value = EXCLUDED.lookup_value,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    1,  # vendor_id
                    'billing_interval',
                    '電費寄送區間',
                    address,
                    interval,
                    json.dumps(metadata),
                    True
                )

                inserted += 1

                # 進度顯示
                if inserted % 50 == 0:
                    print(f"⏳ 已插入 {inserted} / {len(df)} 筆...")

            except Exception as e:
                errors.append(f"行 {idx+2}: {str(e)}")
                skipped += 1

        # 6. 輸出結果
        print("-" * 60)
        print(f"\n✅ 導入完成!")
        print(f"   - 成功插入: {inserted} 筆")
        print(f"   - 跳過: {skipped} 筆")

        if errors:
            print(f"\n⚠️  錯誤記錄 ({len(errors)} 筆):")
            for error in errors[:10]:  # 只顯示前 10 個錯誤
                print(f"   {error}")
            if len(errors) > 10:
                print(f"   ... 還有 {len(errors) - 10} 個錯誤")

        # 7. 驗證數據
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM lookup_tables
            WHERE category = 'billing_interval'
        """)
        print(f"\n📊 數據庫現有記錄: {count} 筆")

        # 8. 顯示樣本數據
        samples = await conn.fetch("""
            SELECT lookup_key, lookup_value, metadata
            FROM lookup_tables
            WHERE category = 'billing_interval'
              AND lookup_key NOT LIKE '測試地址%'
            ORDER BY id
            LIMIT 5
        """)

        if samples:
            print(f"\n📝 樣本數據（前 5 筆）:")
            print("-" * 60)
            for i, sample in enumerate(samples, 1):
                print(f"{i}. {sample['lookup_key'][:40]}... → {sample['lookup_value']}")
                if sample['metadata']:
                    print(f"   metadata: {sample['metadata']}")

        # 9. 統計資料
        stats = await conn.fetch("""
            SELECT lookup_value, COUNT(*) as count
            FROM lookup_tables
            WHERE category = 'billing_interval'
            GROUP BY lookup_value
            ORDER BY lookup_value
        """)

        print(f"\n📊 統計資料:")
        print("-" * 60)
        for stat in stats:
            print(f"   {stat['lookup_value']}: {stat['count']} 筆")

        print("=" * 60)
        print("✅ 全部完成!")
        print("=" * 60)

    finally:
        await conn.close()


if __name__ == '__main__':
    try:
        asyncio.run(import_data())
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
