#!/usr/bin/env python3
"""
SOP 資料遷移工具：舊架構 → 新架構

用途：
1. 分析舊 SOP 資料（vendor_sop_categories, vendor_sop_items）
2. 識別共通模式，建立平台範本
3. 將業者特定內容轉為覆寫記錄
4. 保留舊資料，不刪除（向後兼容）

使用方式：
    python scripts/migrate_sop_to_templates.py [--dry-run] [--vendor-id VENDOR_ID]

選項：
    --dry-run       : 只分析不執行，顯示將要建立的範本
    --vendor-id N   : 只遷移特定業者（用於測試）
    --auto-approve  : 自動批准所有建立的範本（不詢問）
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from difflib import SequenceMatcher


# 資料庫連接配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'aichatbot_admin'),
    'user': os.getenv('DB_USER', 'aichatbot'),
    'password': os.getenv('DB_PASSWORD', 'aichatbot_password')
}


def get_db_connection():
    """建立資料庫連接"""
    return psycopg2.connect(**DB_CONFIG)


def similarity(a, b):
    """計算兩個字串的相似度（0-1）"""
    return SequenceMatcher(None, a, b).ratio()


def analyze_old_sop_data(conn, vendor_id=None):
    """分析舊 SOP 資料，識別共通模式"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 載入所有 SOP 資料
    if vendor_id:
        cursor.execute("""
            SELECT
                si.id,
                si.vendor_id,
                v.name AS vendor_name,
                sc.category_name,
                sc.description AS category_description,
                sc.display_order AS category_display_order,
                si.item_number,
                si.item_name,
                si.content,
                si.requires_cashflow_check,
                si.cashflow_through_company,
                si.cashflow_direct_to_landlord,
                si.related_intent_id,
                si.priority
            FROM vendor_sop_items si
            INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
            INNER JOIN vendors v ON si.vendor_id = v.id
            WHERE si.is_active = TRUE
              AND sc.is_active = TRUE
              AND si.vendor_id = %s
            ORDER BY sc.category_name, si.item_number
        """, (vendor_id,))
    else:
        cursor.execute("""
            SELECT
                si.id,
                si.vendor_id,
                v.name AS vendor_name,
                sc.category_name,
                sc.description AS category_description,
                sc.display_order AS category_display_order,
                si.item_number,
                si.item_name,
                si.content,
                si.requires_cashflow_check,
                si.cashflow_through_company,
                si.cashflow_direct_to_landlord,
                si.related_intent_id,
                si.priority
            FROM vendor_sop_items si
            INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
            INNER JOIN vendors v ON si.vendor_id = v.id
            WHERE si.is_active = TRUE
              AND sc.is_active = TRUE
            ORDER BY sc.category_name, si.item_number
        """)

    all_items = cursor.fetchall()
    cursor.close()

    # 按分類和項目名稱分組
    grouped = defaultdict(list)
    for item in all_items:
        key = (item['category_name'], item['item_name'])
        grouped[key].append(item)

    return grouped, all_items


def identify_templates(grouped_items, similarity_threshold=0.85):
    """
    識別可以建立為平台範本的 SOP 項目

    策略：
    - 如果多個業者有相同的 category_name + item_name
    - 且內容相似度高於閾值
    - 則建立為平台範本
    """
    templates = []

    for (category_name, item_name), items in grouped_items.items():
        if len(items) < 2:
            # 只有一個業者有此項目，直接作為覆寫
            continue

        # 計算內容相似度
        contents = [item['content'] for item in items if item['content']]
        if not contents:
            continue

        # 使用第一個業者的內容作為基準
        base_content = contents[0]
        similarities = [similarity(base_content, c) for c in contents[1:]]

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        if avg_similarity >= similarity_threshold:
            # 相似度高，建立為範本
            # 使用最常見的值
            template = {
                'category_name': category_name,
                'category_description': items[0]['category_description'],
                'category_display_order': items[0]['category_display_order'],
                'item_number': items[0]['item_number'],
                'item_name': item_name,
                'content': base_content,
                'requires_cashflow_check': items[0]['requires_cashflow_check'],
                'cashflow_through_company': items[0]['cashflow_through_company'],
                'cashflow_direct_to_landlord': items[0]['cashflow_direct_to_landlord'],
                'related_intent_id': items[0]['related_intent_id'],
                'priority': items[0]['priority'],
                'vendor_count': len(items),
                'similarity_score': avg_similarity,
                'template_notes': f'此範本基於 {len(items)} 個業者的共通內容建立',
                'customization_hint': '如需調整，請建立覆寫記錄'
            }
            templates.append(template)

    return templates


def create_platform_categories(conn, templates, dry_run=False):
    """建立平台 SOP 分類"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 取得唯一的分類
    categories = {}
    for template in templates:
        cat_name = template['category_name']
        if cat_name not in categories:
            categories[cat_name] = {
                'category_name': cat_name,
                'description': template['category_description'],
                'display_order': template['category_display_order'],
                'template_notes': f'從舊架構遷移而來，共有 {template["vendor_count"]} 個業者使用'
            }

    if dry_run:
        print(f"\n將建立 {len(categories)} 個平台分類：")
        for cat in categories.values():
            print(f"  - {cat['category_name']} (順序: {cat['display_order']})")
        cursor.close()
        return categories

    # 實際建立分類
    category_ids = {}
    for cat_name, cat_data in categories.items():
        cursor.execute("""
            INSERT INTO platform_sop_categories (
                category_name, description, display_order, template_notes
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (category_name) DO UPDATE
                SET description = EXCLUDED.description,
                    display_order = EXCLUDED.display_order,
                    template_notes = EXCLUDED.template_notes
            RETURNING id
        """, (
            cat_data['category_name'],
            cat_data['description'],
            cat_data['display_order'],
            cat_data['template_notes']
        ))
        category_ids[cat_name] = cursor.fetchone()['id']
        print(f"✅ 已建立分類: {cat_name} (ID: {category_ids[cat_name]})")

    cursor.close()
    conn.commit()
    return category_ids


def create_platform_templates(conn, templates, category_ids, dry_run=False, auto_approve=False):
    """建立平台 SOP 範本"""
    if dry_run:
        print(f"\n將建立 {len(templates)} 個平台範本：")
        for t in templates:
            print(f"  - {t['category_name']} / {t['item_name']}")
            print(f"    (業者數: {t['vendor_count']}, 相似度: {t['similarity_score']:.2%})")
        return {}

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    template_ids = {}

    for t in templates:
        if not auto_approve:
            print(f"\n建立範本: {t['category_name']} / {t['item_name']}")
            print(f"  內容: {t['content'][:100]}...")
            print(f"  業者數: {t['vendor_count']}, 相似度: {t['similarity_score']:.2%}")
            response = input("  確認建立? (y/n): ")
            if response.lower() != 'y':
                print("  跳過")
                continue

        cursor.execute("""
            INSERT INTO platform_sop_templates (
                category_id, item_number, item_name, content,
                requires_cashflow_check, cashflow_through_company,
                cashflow_direct_to_landlord,
                related_intent_id, priority,
                template_notes, customization_hint
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            category_ids[t['category_name']],
            t['item_number'],
            t['item_name'],
            t['content'],
            t['requires_cashflow_check'],
            t['cashflow_through_company'],
            t['cashflow_direct_to_landlord'],
            t['related_intent_id'],
            t['priority'],
            t['template_notes'],
            t['customization_hint']
        ))

        template_id = cursor.fetchone()['id']
        key = (t['category_name'], t['item_name'])
        template_ids[key] = template_id
        print(f"✅ 已建立範本: {t['category_name']} / {t['item_name']} (ID: {template_id})")

    cursor.close()
    conn.commit()
    return template_ids


def create_vendor_overrides(conn, grouped_items, template_ids, dry_run=False):
    """建立業者覆寫記錄"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    override_count = 0

    for (category_name, item_name), items in grouped_items.items():
        template_key = (category_name, item_name)

        if template_key not in template_ids:
            # 沒有建立範本，跳過
            continue

        template_id = template_ids[template_key]

        # 取得範本內容（用於比對）
        cursor.execute("""
            SELECT content, cashflow_through_company, cashflow_direct_to_landlord
            FROM platform_sop_templates
            WHERE id = %s
        """, (template_id,))
        template = cursor.fetchone()

        for item in items:
            # 檢查業者的內容是否與範本不同
            has_override = False
            override_fields = {}

            if item['content'] != template['content']:
                has_override = True
                override_fields['content'] = item['content']

            if item['cashflow_through_company'] != template['cashflow_through_company']:
                has_override = True
                override_fields['cashflow_through_company'] = item['cashflow_through_company']

            if item['cashflow_direct_to_landlord'] != template['cashflow_direct_to_landlord']:
                has_override = True
                override_fields['cashflow_direct_to_landlord'] = item['cashflow_direct_to_landlord']

            if not has_override:
                # 完全相同，不需要覆寫
                continue

            if dry_run:
                print(f"  將建立覆寫: 業者 {item['vendor_name']} / {category_name} / {item_name}")
                continue

            # 建立覆寫記錄
            cursor.execute("""
                INSERT INTO vendor_sop_overrides (
                    vendor_id, template_id, override_type,
                    content, cashflow_through_company, cashflow_direct_to_landlord,
                    override_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (vendor_id, template_id) DO UPDATE
                    SET content = EXCLUDED.content,
                        cashflow_through_company = EXCLUDED.cashflow_through_company,
                        cashflow_direct_to_landlord = EXCLUDED.cashflow_direct_to_landlord,
                        override_reason = EXCLUDED.override_reason
            """, (
                item['vendor_id'],
                template_id,
                'partial_override',
                override_fields.get('content'),
                override_fields.get('cashflow_through_company'),
                override_fields.get('cashflow_direct_to_landlord'),
                '從舊架構自動遷移'
            ))
            override_count += 1

    cursor.close()
    if not dry_run:
        conn.commit()
        print(f"\n✅ 已建立 {override_count} 個覆寫記錄")

    return override_count


def main():
    parser = argparse.ArgumentParser(description='遷移 SOP 資料從舊架構到新架構')
    parser.add_argument('--dry-run', action='store_true', help='只分析不執行')
    parser.add_argument('--vendor-id', type=int, help='只遷移特定業者')
    parser.add_argument('--auto-approve', action='store_true', help='自動批准所有範本')
    parser.add_argument('--similarity', type=float, default=0.85, help='相似度閾值 (0-1)')

    args = parser.parse_args()

    print("=" * 60)
    print("SOP 資料遷移工具：舊架構 → 新架構")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN 模式：只分析，不執行實際遷移")

    try:
        conn = get_db_connection()
        print("✅ 已連接到資料庫")

        # 步驟 1: 分析舊資料
        print("\n步驟 1: 分析舊 SOP 資料...")
        grouped_items, all_items = analyze_old_sop_data(conn, args.vendor_id)
        print(f"  找到 {len(all_items)} 個 SOP 項目")
        print(f"  共有 {len(grouped_items)} 個不同的分類/項目組合")

        # 步驟 2: 識別範本
        print("\n步驟 2: 識別可建立為平台範本的項目...")
        templates = identify_templates(grouped_items, args.similarity)
        print(f"  識別出 {len(templates)} 個可建立為範本的項目")

        if not templates:
            print("\n⚠️  沒有找到適合建立為範本的項目")
            print("提示：可能所有業者的 SOP 都不同，或相似度太低")
            return

        # 步驟 3: 建立平台分類
        print("\n步驟 3: 建立平台 SOP 分類...")
        category_ids = create_platform_categories(conn, templates, args.dry_run)

        # 步驟 4: 建立平台範本
        print("\n步驟 4: 建立平台 SOP 範本...")
        template_ids = create_platform_templates(
            conn, templates, category_ids,
            args.dry_run, args.auto_approve
        )

        # 步驟 5: 建立業者覆寫
        print("\n步驟 5: 建立業者覆寫記錄...")
        override_count = create_vendor_overrides(
            conn, grouped_items, template_ids,
            args.dry_run
        )

        print("\n" + "=" * 60)
        print("遷移完成！")
        print("=" * 60)
        print(f"建立的分類數: {len(category_ids)}")
        print(f"建立的範本數: {len(template_ids)}")
        print(f"建立的覆寫數: {override_count}")

        if args.dry_run:
            print("\n⚠️  這是 DRY RUN，沒有實際修改資料庫")
        else:
            print("\n✅ 資料已成功遷移到新架構")
            print("注意：舊資料仍保留在 vendor_sop_categories 和 vendor_sop_items 表中")

        conn.close()

    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
