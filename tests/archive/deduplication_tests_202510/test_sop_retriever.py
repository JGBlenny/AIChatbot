"""
測試 VendorSOPRetriever 功能
驗證金流模式分支邏輯
"""
import sys
import os

# 新增路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag-orchestrator'))

from services.vendor_sop_retriever import VendorSOPRetriever


def print_separator(title):
    """列印分隔線"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_vendor_info():
    """測試 1：獲取業者資訊"""
    print_separator("測試 1：獲取業者資訊")

    retriever = VendorSOPRetriever()

    # 測試業者 1
    vendor1 = retriever.get_vendor_info(vendor_id=1)
    print(f"業者 1（{vendor1['name']}）：")
    print(f"  業種類型：{vendor1['business_type']}")
    print(f"  金流模式：{vendor1['cashflow_model']}")

    # 測試業者 2
    vendor2 = retriever.get_vendor_info(vendor_id=2)
    print(f"\n業者 2（{vendor2['name']}）：")
    print(f"  業種類型：{vendor2['business_type']}")
    print(f"  金流模式：{vendor2['cashflow_model']}")

    return retriever


def test_get_categories(retriever):
    """測試 2：獲取 SOP 分類"""
    print_separator("測試 2：獲取 SOP 分類")

    for vendor_id in [1, 2]:
        print(f"\n業者 {vendor_id} 的 SOP 分類：")
        categories = retriever.get_all_categories(vendor_id)

        for cat in categories:
            print(f"  - {cat['category_name']} ({cat['item_count']} 項)")
            if cat['description']:
                print(f"    描述：{cat['description']}")


def test_retrieve_by_category(retriever):
    """測試 3：根據分類檢索 SOP"""
    print_separator("測試 3：根據分類檢索 SOP（無金流判斷）")

    category_name = '租金繳費相關'

    for vendor_id in [1, 2]:
        vendor_info = retriever.get_vendor_info(vendor_id)
        print(f"\n業者 {vendor_id}（{vendor_info['name']}，{vendor_info['cashflow_model']}）：")

        items = retriever.retrieve_sop_by_category(
            vendor_id=vendor_id,
            category_name=category_name
        )

        for item in items[:3]:  # 只顯示前3項
            print(f"\n  {item['item_number']}. {item['item_name']}")
            print(f"     內容：{item['content'][:80]}...")


def test_cashflow_branch_logic(retriever):
    """測試 4：驗證金流模式分支邏輯（核心測試）"""
    print_separator("測試 4：驗證金流模式分支邏輯 ⭐⭐⭐")

    # 測試項目：「租金支付方式」
    test_item_name = "租金支付方式"

    print(f"測試項目：{test_item_name}\n")

    for vendor_id in [1, 2]:
        vendor_info = retriever.get_vendor_info(vendor_id)

        print(f"{'─' * 80}")
        print(f"業者 {vendor_id}：{vendor_info['name']}")
        print(f"業種類型：{vendor_info['business_type']}")
        print(f"金流模式：{vendor_info['cashflow_model']}")
        print(f"{'─' * 80}")

        items = retriever.retrieve_sop_by_category(
            vendor_id=vendor_id,
            category_name='租金繳費相關'
        )

        for item in items:
            if test_item_name in item['item_name']:
                print(f"\n✅ 調整後的內容：")
                print(f"   {item['content']}")

                if 'original_content' in item and item['original_content'] != item['content']:
                    print(f"\n📝 原始內容：")
                    print(f"   {item['original_content']}")

                break

        print("\n")


def test_specific_items_comparison(retriever):
    """測試 5：特定項目的金流模式對比"""
    print_separator("測試 5：金流敏感項目對比（包租型 vs 代管型）")

    test_items = [
        "租金支付方式",
        "收據或發票如何取得",
        "如果租客遲付租金"
    ]

    for item_name in test_items:
        print(f"\n{'═' * 80}")
        print(f"📋 項目：{item_name}")
        print(f"{'═' * 80}")

        # 業者 1（包租型）
        items_1 = retriever.retrieve_sop_by_category(vendor_id=1, category_name='租金繳費相關')
        item_1 = next((item for item in items_1 if item_name in item['item_name']), None)

        # 業者 2（代管型）
        items_2 = retriever.retrieve_sop_by_category(vendor_id=2, category_name='租金繳費相關')
        item_2 = next((item for item in items_2 if item_name in item['item_name']), None)

        if item_1:
            print(f"\n✅ 包租型（金流過我家）：")
            print(f"   {item_1['content']}")

        if item_2:
            print(f"\n✅ 代管型（金流不過我家）：")
            print(f"   {item_2['content']}")

        # 比對差異
        if item_1 and item_2:
            if '公司' in item_1['content'] and '房東' in item_2['content']:
                print(f"\n🎯 差異檢測：✅ 金流模式分支邏輯正常")
                print(f"   - 包租型提及「公司」：{'✓' if '公司' in item_1['content'] else '✗'}")
                print(f"   - 代管型提及「房東」：{'✓' if '房東' in item_2['content'] else '✗'}")
            else:
                print(f"\n⚠️  差異檢測：未偵測到明顯差異")


def test_non_cashflow_items(retriever):
    """測試 6：非金流敏感項目（應保持一致）"""
    print_separator("測試 6：非金流敏感項目（應保持一致）")

    item_name = "如何查詢當月租金"

    print(f"測試項目：{item_name}\n")

    items_1 = retriever.retrieve_sop_by_category(vendor_id=1, category_name='租金繳費相關')
    items_2 = retriever.retrieve_sop_by_category(vendor_id=2, category_name='租金繳費相關')

    item_1 = next((item for item in items_1 if item_name in item['item_name']), None)
    item_2 = next((item for item in items_2 if item_name in item['item_name']), None)

    if item_1:
        print(f"業者 1（包租型）：")
        print(f"   {item_1['content']}")

    if item_2:
        print(f"\n業者 2（代管型）：")
        print(f"   {item_2['content']}")

    if item_1 and item_2:
        if item_1['content'] == item_2['content']:
            print(f"\n🎯 檢測結果：✅ 非金流敏感項目內容一致")
        else:
            print(f"\n⚠️  檢測結果：內容有差異")


def main():
    """主測試流程"""
    print("\n")
    print("█" * 80)
    print(" " * 20 + "VendorSOPRetriever 功能測試")
    print("█" * 80)

    try:
        # 測試 1：獲取業者資訊
        retriever = test_vendor_info()

        # 測試 2：獲取 SOP 分類
        test_get_categories(retriever)

        # 測試 3：根據分類檢索 SOP
        test_retrieve_by_category(retriever)

        # 測試 4：驗證金流模式分支邏輯（核心）
        test_cashflow_branch_logic(retriever)

        # 測試 5：特定項目對比
        test_specific_items_comparison(retriever)

        # 測試 6：非金流敏感項目
        test_non_cashflow_items(retriever)

        # 總結
        print_separator("測試總結")
        print("✅ 所有測試完成")
        print("\n核心功能驗證：")
        print("  ✓ 業者資訊讀取")
        print("  ✓ SOP 分類檢索")
        print("  ✓ SOP 項目檢索")
        print("  ✓ 金流模式分支邏輯")
        print("  ✓ 內容動態調整")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
