"""
從 Excel 匯入 SOP 到資料庫
根據實際的 SOP 結構（20250305 real_estate_rental_knowledge_base SOP.xlsx）
"""
import pandas as pd
import psycopg2
import psycopg2.extras
import sys
import os

# 新增父目錄到 path（以便 import db_utils）
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag-orchestrator'))
from services.db_utils import get_db_config


def parse_sop_excel(excel_path: str) -> dict:
    """
    解析 SOP Excel 文件

    Returns:
        {
            'categories': [
                {
                    'name': '租賃流程相關資訊',
                    'description': '租賃申請流程：介紹如何申請租賃...',
                    'items': [
                        {
                            'number': 1,
                            'name': '申請步驟：',
                            'content': '租客首先需要在線提交租賃申請表...'
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    df = pd.read_excel(excel_path, sheet_name='Sheet1')

    # 清理欄位名稱
    df.columns = ['分類', '說明', '序號', '項目', '內容', 'JGB範本', '愛租屋管理制度', '備註']

    categories = []
    current_category = None

    for idx, row in df.iterrows():
        category = row['分類']
        description = row['說明']
        seq = row['序號']
        item = row['項目']
        content = row['內容']

        # 跳過標題行
        if category == '分類':
            continue

        # 遇到新分類
        if pd.notna(category) and category != current_category:
            current_category = {
                'name': category,
                'description': description if pd.notna(description) else '',
                'items': []
            }
            categories.append(current_category)

        # 添加項目
        if current_category and pd.notna(item):
            item_data = {
                'number': int(seq) if pd.notna(seq) else None,
                'name': str(item).strip(),
                'content': str(content).strip() if pd.notna(content) else ''
            }
            current_category['items'].append(item_data)

    return {'categories': categories}


def identify_cashflow_sensitive_items(item_name: str, content: str) -> dict:
    """
    識別是否需要金流模式判斷

    Returns:
        {
            'requires_cashflow': bool,
            'through_company': str or None,
            'direct_to_landlord': str or None
        }
    """
    # 金流敏感關鍵字
    cashflow_keywords = ['租金支付', '繳費', '收據', '發票', '遲付', '押金', '帳戶', '匯款']

    requires_cashflow = any(kw in item_name or kw in content for kw in cashflow_keywords)

    if not requires_cashflow:
        return {
            'requires_cashflow': False,
            'through_company': None,
            'direct_to_landlord': None
        }

    # 根據項目類型生成不同版本的內容
    versions = {}

    if '租金支付方式' in item_name:
        versions['through_company'] = "登入JGB系統查看公司收款帳號，可通過銀行轉帳、信用卡支付或超商代碼繳款。"
        versions['direct_to_landlord'] = "請向房東索取收款帳號，建議使用銀行轉帳並留存交易記錄。"

    elif '租金提醒通知' in item_name:
        versions['through_company'] = "JGB系統會根據租金帳單的截止日，提前透過email、LINE等發送繳租提醒，並在收款後主動通知您。"
        versions['direct_to_landlord'] = "JGB系統會根據租金帳單的截止日，提前透過email、LINE等發送繳租提醒。請您自行與房東確認收款狀態。"

    elif '收據或發票' in item_name:
        versions['through_company'] = "支付後，JGB系統會自動生成收據或電子發票，並通過郵件發送給您。您也可以登入管理系統查閱。"
        versions['direct_to_landlord'] = "請向房東索取收據，JGB系統僅保存繳款提醒記錄供您參考。"

    elif '遲付租金' in item_name or '遲付' in item_name:
        versions['through_company'] = "JGB系統會自動發送催繳通知並依約收取滯納金，請儘速完成繳款。"
        versions['direct_to_landlord'] = "房東會處理遲付事宜，JGB系統僅協助發送提醒通知。請您主動聯繫房東說明情況。"

    elif '押金' in item_name:
        versions['through_company'] = "押金由公司收取並專戶保管，租約結束後會根據房屋狀況於7個工作天內退還。"
        versions['direct_to_landlord'] = "押金由房東收取，租約結束後請與房東確認退還時間與方式。"

    elif '提前終止' in item_name:
        versions['through_company'] = "若需提前終止租約，請向公司提出申請，我們會依據合約計算賠償金額並協助辦理退租手續。"
        versions['direct_to_landlord'] = "若需提前終止租約，請與房東協商，JGB可提供合約條款參考與退租檢核表協助您完成程序。"

    else:
        # 其他項目：保持原內容
        versions['through_company'] = content
        versions['direct_to_landlord'] = content

    return {
        'requires_cashflow': True,
        'through_company': versions.get('through_company', content),
        'direct_to_landlord': versions.get('direct_to_landlord', content)
    }


def import_sop_to_db(sop_data: dict, vendor_id: int, conn):
    """匯入 SOP 到資料庫"""
    cursor = conn.cursor()

    print(f"\n📥 開始匯入 SOP 到資料庫（Vendor ID: {vendor_id}）")
    print("=" * 80)

    total_items = 0
    cashflow_sensitive_items = 0

    for cat_idx, category in enumerate(sop_data['categories'], 1):
        # 1. 插入分類
        cursor.execute("""
            INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (vendor_id, category['name'], category['description'], cat_idx))

        category_id = cursor.fetchone()[0]
        print(f"\n✅ 分類 {cat_idx}: {category['name']} (ID: {category_id})")

        # 2. 插入項目
        for item in category['items']:
            # 識別是否需要金流判斷
            cashflow_info = identify_cashflow_sensitive_items(item['name'], item['content'])

            cursor.execute("""
                INSERT INTO vendor_sop_items (
                    category_id,
                    vendor_id,
                    item_number,
                    item_name,
                    content,
                    requires_cashflow_check,
                    cashflow_through_company,
                    cashflow_direct_to_landlord
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                category_id,
                vendor_id,
                item['number'],
                item['name'],
                item['content'],
                cashflow_info['requires_cashflow'],
                cashflow_info['through_company'],
                cashflow_info['direct_to_landlord']
            ))

            item_id = cursor.fetchone()[0]
            total_items += 1

            if cashflow_info['requires_cashflow']:
                cashflow_sensitive_items += 1
                print(f"   🔄 項目 {item['number']}: {item['name']} (需金流判斷)")
            else:
                print(f"   ➡️  項目 {item['number']}: {item['name']}")

    conn.commit()

    print("\n" + "=" * 80)
    print(f"✅ SOP 匯入完成")
    print(f"   總分類數：{len(sop_data['categories'])}")
    print(f"   總項目數：{total_items}")
    print(f"   金流敏感項目：{cashflow_sensitive_items}")
    print("=" * 80)


def main():
    """主程式"""
    # 1. 讀取 Excel
    excel_path = 'data/20250305 real_estate_rental_knowledge_base SOP.xlsx'

    if not os.path.exists(excel_path):
        print(f"❌ 找不到檔案：{excel_path}")
        sys.exit(1)

    print(f"📄 讀取 Excel 檔案：{excel_path}")
    sop_data = parse_sop_excel(excel_path)

    print(f"\n✅ Excel 解析完成")
    print(f"   分類數：{len(sop_data['categories'])}")
    for cat in sop_data['categories']:
        print(f"   - {cat['name']}: {len(cat['items'])} 項")

    # 2. 連接資料庫
    print(f"\n🔌 連接資料庫...")
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)

    # 3. 匯入 SOP 給測試業者
    # Vendor 1: 甲山林包租代管股份有限公司（包租型，金流過我家）
    # Vendor 2: 信義包租代管股份有限公司（純代管型，金流不過我家）
    # Vendor 4: 永慶包租代管股份有限公司（純代管型，金流過我家）
    # Vendor 5: 台灣房屋包租代管股份有限公司（純代管型，混合型）
    test_vendors = [1, 2, 4, 5]

    for vendor_id in test_vendors:
        import_sop_to_db(sop_data, vendor_id, conn)
        print()  # 空行分隔

    conn.close()
    print("\n✅ 所有操作完成")


if __name__ == "__main__":
    main()
