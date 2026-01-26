#!/usr/bin/env python3
"""建立測試表單，對應測試 SOP 情境"""

import asyncio
import httpx
import json

API_URL = "http://localhost:8100/api/v1"  # rag-orchestrator API
VENDOR_ID = 2

# 測試表單定義
TEST_FORMS = [
    # ========== 表單 1: 網路維修申請表 ==========
    {
        "form_id": "test_network_maintenance",
        "form_name": "【測試】網路維修申請表",
        "description": "用於測試網路不通排查 SOP 的表單",
        "vendor_id": VENDOR_ID,
        "is_active": True,
        "default_intro": "好的，我來協助您填寫網路維修表單。",
        "on_complete_action": "show_knowledge",
        "fields": [
            {
                "field_name": "room_number",
                "field_label": "房號",
                "field_type": "text",
                "prompt": "請提供您的房號（例如：A101）",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "issue_description",
                "field_label": "問題描述",
                "field_type": "text",
                "prompt": "請描述網路連線問題（例如：完全無法連線、速度很慢、斷斷續續）",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "troubleshooting_steps",
                "field_label": "已嘗試的排查步驟",
                "field_type": "text",
                "prompt": "請告訴我您已經嘗試過哪些步驟（例如：重啟路由器、檢查網路線）",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "contact_phone",
                "field_label": "聯絡電話",
                "field_type": "text",
                "prompt": "請提供您的聯絡電話",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "preferred_time",
                "field_label": "方便聯絡時間",
                "field_type": "text",
                "prompt": "請告訴我您方便接聽電話的時間（例如：平日上午、週末全天）",
                "required": False,
                "validation_type": "free_text"
            }
        ]
    },

    # ========== 表單 2: 門鎖緊急維修表 ==========
    {
        "form_id": "test_door_lock_repair",
        "form_name": "【測試】門鎖緊急維修表",
        "description": "用於測試門鎖故障緊急 SOP 的表單",
        "vendor_id": VENDOR_ID,
        "is_active": True,
        "default_intro": "好的，請提供以下資訊，我會盡快安排維修人員。",
        "on_complete_action": "show_knowledge",
        "fields": [
            {
                "field_name": "room_number",
                "field_label": "房號",
                "field_type": "text",
                "prompt": "請提供您的房號（例如：A101）",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "issue_type",
                "field_label": "問題類型",
                "field_type": "text",
                "prompt": "請選擇問題類型：1-無法開門、2-無法鎖門、3-鑰匙卡失靈",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "urgency_level",
                "field_label": "緊急程度",
                "field_type": "text",
                "prompt": "請選擇緊急程度：1-一般（可等待）、2-緊急（當日處理）、3-非常緊急（立即處理）",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "contact_phone",
                "field_label": "聯絡電話",
                "field_type": "text",
                "prompt": "請提供您的聯絡電話",
                "required": True,
                "validation_type": "free_text"
            },
            {
                "field_name": "waiting_at_home",
                "field_label": "是否在家等待",
                "field_type": "text",
                "prompt": "您目前是否在家等待維修人員？（是/否）",
                "required": True,
                "validation_type": "free_text"
            }
        ]
    }
]


async def create_test_forms():
    """建立測試表單"""

    print("=" * 100)
    print("📋 建立測試表單")
    print("=" * 100)
    print(f"\n📊 總共 {len(TEST_FORMS)} 個測試表單")
    print(f"🎯 Vendor ID: {VENDOR_ID}")
    print(f"🔗 API URL: {API_URL}\n")

    created_forms = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, form_data in enumerate(TEST_FORMS, 1):
            print(f"\n{'='*80}")
            print(f"📝 [{i}/{len(TEST_FORMS)}] {form_data['form_name']}")
            print(f"{'='*80}")
            print(f"  表單 ID: {form_data['form_id']}")
            print(f"  欄位數: {len(form_data['fields'])}")
            print(f"  說明: {form_data['description']}")

            try:
                response = await client.post(
                    f"{API_URL}/forms",
                    json=form_data
                )

                if response.status_code == 201:
                    data = response.json()
                    created_forms.append({
                        'id': data.get('id'),
                        'form_id': form_data['form_id'],
                        'form_name': form_data['form_name'],
                        'field_count': len(form_data['fields'])
                    })
                    print(f"  ✅ 建立成功！ID: {data.get('id')}")
                else:
                    print(f"  ❌ 建立失敗: {response.status_code}")
                    print(f"  錯誤: {response.text}")

            except Exception as e:
                print(f"  ❌ 建立失敗: {e}")

    # 輸出結果摘要
    print(f"\n{'='*100}")
    print(f"✅ 測試表單建立完成！")
    print(f"{'='*100}\n")

    print(f"📊 成功建立 {len(created_forms)}/{len(TEST_FORMS)} 個測試表單\n")

    if created_forms:
        print("📋 **建立的測試表單列表**：\n")
        for form in created_forms:
            print(f"  • {form['form_name']}")
            print(f"    表單 ID: {form['form_id']}")
            print(f"    欄位數: {form['field_count']}")
            print()

    # 更新 SOP 以使用新表單
    print(f"\n{'='*80}")
    print("🔄 接下來需要更新測試 SOP，讓它們使用新建立的表單")
    print(f"{'='*80}\n")
    print("需要更新的 SOP：")
    print("  • SOP 1673（網路不通排查）: maintenance_request → test_network_maintenance")
    print("  • SOP 1674（門鎖故障緊急）: repair_request → test_door_lock_repair")
    print()
    print("請執行: python3 update_test_sop_forms.py")

    print(f"\n{'='*100}\n")

    return created_forms


if __name__ == "__main__":
    asyncio.run(create_test_forms())
