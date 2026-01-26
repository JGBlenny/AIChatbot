#!/usr/bin/env python3
"""
建立並測試真實的租屋管理情境
包含：SOP 建立 → 表單建立 → 實際對話測試 → 完整驗證
"""

import asyncio
import httpx
import json
from typing import List, Dict

API_URL = "http://localhost:8100/api/v1"
VENDOR_ID = 2

# ============================================================
# 真實情境定義
# ============================================================

REAL_SCENARIOS = {
    # 情境 1: 冷氣不冷排查（排查型 + 表單）
    "air_conditioner": {
        "sop": {
            "category_id": 154,
            "item_number": 8001,
            "item_name": "冷氣不冷排查",
            "content": """🌡️ **冷氣不冷排查步驟**

您的冷氣不冷嗎？別擔心，讓我們先一步步排查問題：

**步驟 1：檢查基本設定 ⚙️**
□ 確認已切換到「冷氣模式」（不是送風或除濕）
□ 溫度設定是否低於目前室溫？建議設定 23-25°C
□ 風量是否開到最大？

**步驟 2：檢查濾網 🧹**
□ 打開冷氣面板，檢查濾網是否堵塞
□ 如果很髒，請用清水沖洗後晾乾
□ ⚠️ 堵塞的濾網會讓冷氣效率降低 50%

**步驟 3：檢查室外機 🏢**
□ 確認室外機是否有運轉（有無震動和聲音）
□ 檢查室外機周圍是否有雜物阻擋
□ 確認室外機散熱片是否乾淨

**步驟 4：測試效果 ❄️**
□ 完成上述步驟後，重新開機
□ 等待 10-15 分鐘，測試出風口溫度
□ 正常情況下，出風口溫度應比室溫低 8-10°C

如果以上步驟都試過了還是不冷，可能是以下問題：
• 冷媒不足（需要專業補充）
• 壓縮機故障
• 電子控制系統異常

這些需要專業技師處理。如果還是不冷，請告訴我「還是不冷」或「試過了」，我會協助您預約維修。""",
            "priority": 80,
            "trigger_mode": "manual",
            "next_action": "form_fill",
            "trigger_keywords": ["還是不冷", "試過了", "沒用", "不管用", "都試過了", "還是一樣"],
            "next_form_id": "ac_maintenance_form",
            "followup_prompt": "了解了，看來需要專業技師檢修。我來協助您填寫冷氣維修申請表。",
            "intent_ids": []
        },
        "form": {
            "form_id": "ac_maintenance_form",
            "form_name": "冷氣維修申請表",
            "description": "冷氣不冷、異音、漏水等維修申請",
            "vendor_id": VENDOR_ID,
            "is_active": True,
            "default_intro": "我來協助您填寫冷氣維修申請表。",
            "on_complete_action": "show_knowledge",
            "fields": [
                {
                    "field_name": "room_number",
                    "field_label": "房號",
                    "field_type": "text",
                    "prompt": "請提供您的房號（例如：A棟 301）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "issue_description",
                    "field_label": "問題描述",
                    "field_type": "text",
                    "prompt": "請描述冷氣的問題（例如：完全不冷、稍微涼但不夠冷、有異音）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "tried_steps",
                    "field_label": "已嘗試步驟",
                    "field_type": "text",
                    "prompt": "請告訴我您已經試過哪些步驟（例如：清洗濾網、調整溫度、重新開機）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "contact_phone",
                    "field_label": "聯絡電話",
                    "field_type": "text",
                    "prompt": "請提供您的手機號碼（維修人員會提前聯絡）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "preferred_time",
                    "field_label": "方便時段",
                    "field_type": "text",
                    "prompt": "請選擇方便維修的時段：1-平日上午(9-12)、2-平日下午(13-17)、3-週末",
                    "required": True,
                    "validation_type": "free_text"
                }
            ]
        }
    },

    # 情境 2: 水管漏水緊急處理（行動型 + 表單）
    "water_leak": {
        "sop": {
            "category_id": 154,
            "item_number": 8002,
            "item_name": "水管漏水緊急處理",
            "content": """💧 **水管漏水緊急處理指南**

發現漏水了嗎？請立即採取以下步驟：

**🚨 立即處置（防止災情擴大）**

1️⃣ **關閉水源**
   • 找到漏水位置附近的水龍頭
   • 如果是廚房/浴室：關閉該區域的止水閥
   • 如果找不到止水閥：關閉總水源（通常在廁所或廚房）

2️⃣ **保護物品**
   • 將漏水處下方的電器、家具移開
   • 用毛巾、水桶接住漏水
   • 如果漏水量大，用毛巾堵住防止擴散

3️⃣ **拍照記錄**
   • 拍攝漏水位置照片
   • 拍攝受損物品照片
   • 這些照片將用於後續保險理賠

**⚡ 特殊情況立即處理**
• 如果漏水影響到電器設備 → 立即切斷該區域電源
• 如果天花板漏水 → 立即通知樓上住戶
• 如果是深夜緊急狀況 → 撥打 24 小時緊急專線：0800-888-999

**📋 需要報修嗎？**
我可以立即為您安排緊急維修，通常 2 小時內會有師傅到場。需要嗎？""",
            "priority": 100,
            "trigger_mode": "immediate",
            "next_action": "form_fill",
            "immediate_prompt": "我可以立即為您安排緊急維修，通常 2 小時內會有師傅到場。需要嗎？",
            "next_form_id": "water_leak_emergency_form",
            "followup_prompt": "好的，我會立即安排緊急維修。請提供以下資訊：",
            "intent_ids": []
        },
        "form": {
            "form_id": "water_leak_emergency_form",
            "form_name": "漏水緊急報修表",
            "description": "水管漏水、天花板滴水等緊急報修",
            "vendor_id": VENDOR_ID,
            "is_active": True,
            "default_intro": "我會立即安排緊急維修。",
            "on_complete_action": "show_knowledge",
            "fields": [
                {
                    "field_name": "room_number",
                    "field_label": "房號",
                    "field_type": "text",
                    "prompt": "您的房號是？",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "leak_location",
                    "field_label": "漏水位置",
                    "field_type": "text",
                    "prompt": "請描述漏水位置（例如：廚房水槽下方、浴室天花板、馬桶旁邊）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "leak_severity",
                    "field_label": "漏水程度",
                    "field_type": "text",
                    "prompt": "請選擇漏水程度：1-輕微滴水、2-持續流水、3-大量湧水",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "water_shut_off",
                    "field_label": "是否已關水源",
                    "field_type": "text",
                    "prompt": "您是否已經關閉水源？（已關閉/找不到/不確定）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "contact_phone",
                    "field_label": "聯絡電話",
                    "field_type": "text",
                    "prompt": "請提供您的手機號碼（維修人員會立即聯絡）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "at_home",
                    "field_label": "是否在家",
                    "field_type": "text",
                    "prompt": "您目前在家嗎？（在家等待/不在家但可立即返回/不在家需預約）",
                    "required": True,
                    "validation_type": "free_text"
                }
            ]
        }
    },

    # 情境 3: 續約申請（行動型 + 表單）
    "lease_renewal": {
        "sop": {
            "category_id": 154,
            "item_number": 8003,
            "item_name": "租約續約申請",
            "content": """📄 **租約續約申請流程**

您想要續約嗎？以下是續約相關資訊：

**📅 續約時間**
• 建議於租約到期前 2 個月提出申請
• 最晚需在到期前 1 個月完成續約手續
• 避免影響您的居住權益

**💰 續約費用**
• 租金：依照新約內容（可能調整）
• 押金：通常不需要再繳（使用原押金）
• 手續費：免收
• 如有欠繳費用需先結清

**📝 續約流程**
1. 提交續約申請（線上表單）
2. 3 個工作日內通知是否同意續約
3. 雙方確認新約條件（租金、期限）
4. 簽訂新租約
5. 完成續約手續

**🎁 續約優惠**
• 續約滿 1 年：免費清潔服務 1 次
• 續約滿 2 年：贈送小家電 1 件
• 介紹新房客：折抵 1 個月租金

需要我協助您填寫續約申請表嗎？""",
            "priority": 60,
            "trigger_mode": "immediate",
            "next_action": "form_fill",
            "immediate_prompt": "需要我協助您填寫續約申請表嗎？",
            "next_form_id": "lease_renewal_form",
            "followup_prompt": "好的，我來協助您填寫續約申請表。",
            "intent_ids": []
        },
        "form": {
            "form_id": "lease_renewal_form",
            "form_name": "租約續約申請表",
            "description": "租約到期續約申請",
            "vendor_id": VENDOR_ID,
            "is_active": True,
            "default_intro": "我來協助您填寫續約申請表。",
            "on_complete_action": "show_knowledge",
            "fields": [
                {
                    "field_name": "room_number",
                    "field_label": "房號",
                    "field_type": "text",
                    "prompt": "您的房號是？",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "tenant_name",
                    "field_label": "承租人姓名",
                    "field_type": "text",
                    "prompt": "請提供承租人姓名（須與合約相同）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "current_lease_end",
                    "field_label": "目前租約到期日",
                    "field_type": "text",
                    "prompt": "請提供目前租約到期日（例如：2026-06-30）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "renewal_period",
                    "field_label": "續約期限",
                    "field_type": "text",
                    "prompt": "您希望續約多久？（1年/2年/3年）",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "contact_phone",
                    "field_label": "聯絡電話",
                    "field_type": "text",
                    "prompt": "請提供您的手機號碼",
                    "required": True,
                    "validation_type": "free_text"
                },
                {
                    "field_name": "special_requests",
                    "field_label": "特殊需求",
                    "field_type": "text",
                    "prompt": "是否有特殊需求或想討論的事項？（選填）",
                    "required": False,
                    "validation_type": "free_text"
                }
            ]
        }
    },

    # 情境 4: 垃圾分類規定（資訊型，無表單）
    "garbage_rules": {
        "sop": {
            "category_id": 154,
            "item_number": 8004,
            "item_name": "垃圾分類與收取規定",
            "content": """🗑️ **垃圾分類與收取規定**

為了環境整潔，請配合以下垃圾分類規定：

**📅 收取時間**

**一般垃圾** 🗑️
• 週一、三、五  19:00-20:00
• 請使用專用垃圾袋（超商可購買）
• 地點：1 樓垃圾集中區

**資源回收** ♻️
• 週二、四  19:00-20:00
• 分類：紙類 / 塑膠 / 金屬 / 玻璃
• 請洗淨瀝乾後再丟棄

**廚餘回收** 🥗
• 跟隨一般垃圾時間
• 分為生廚餘（可堆肥）和熟廚餘（已烹煮）
• 請使用廚餘桶，勿用塑膠袋

**大型垃圾** 📦
• 需提前 3 天預約
• 聯絡管理員：0912-345-678
• 費用依大小計算（200-500 元）

**⚠️ 重要注意事項**
• 逾時不收，請勿提早放置
• 違規丟棄將罰款 500-1000 元
• 禁止丟棄：有害廢棄物、醫療廢棄物
• 搬家清運需另外預約專業清潔公司

**♻️ 回收小提醒**
• 寶特瓶請壓扁
• 紙盒請拆平
• 瓶蓋和瓶身分開
• 鋁箔包請洗淨

如有任何問題，歡迎詢問管理員！""",
            "priority": 40,
            "trigger_mode": "none",
            "next_action": "none",
            "intent_ids": []
        },
        "form": None  # 無需表單
    }
}


# ============================================================
# 建立與測試函數
# ============================================================

async def create_real_scenarios():
    """建立真實情境的 SOP 和表單"""

    print("=" * 100)
    print("🏢 建立真實租屋管理情境")
    print("=" * 100)
    print(f"\n📊 總共 {len(REAL_SCENARIOS)} 個真實情境\n")

    created_data = {
        "sops": [],
        "forms": []
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for scenario_key, scenario in REAL_SCENARIOS.items():
            print(f"\n{'='*80}")
            print(f"📝 情境: {scenario['sop']['item_name']}")
            print(f"{'='*80}")

            # 建立表單（如果有）
            if scenario['form']:
                print(f"\n  📋 建立表單: {scenario['form']['form_name']}")
                try:
                    form_response = await client.post(
                        f"{API_URL}/forms",
                        json=scenario['form']
                    )
                    if form_response.status_code == 201:
                        form_data = form_response.json()
                        created_data['forms'].append({
                            'id': form_data['id'],
                            'form_id': scenario['form']['form_id'],
                            'form_name': scenario['form']['form_name']
                        })
                        print(f"    ✅ 表單建立成功！ID: {form_data['id']}")
                    else:
                        print(f"    ❌ 表單建立失敗: {form_response.status_code}")
                        print(f"    {form_response.text}")
                except Exception as e:
                    print(f"    ❌ 表單建立失敗: {e}")

            # 建立 SOP
            print(f"\n  📄 建立 SOP: {scenario['sop']['item_name']}")
            try:
                sop_response = await client.post(
                    f"{API_URL}/vendors/{VENDOR_ID}/sop/items",
                    json=scenario['sop']
                )
                if sop_response.status_code == 201:
                    sop_data = sop_response.json()
                    created_data['sops'].append({
                        'id': sop_data['id'],
                        'item_name': scenario['sop']['item_name'],
                        'trigger_mode': scenario['sop']['trigger_mode'],
                        'next_action': scenario['sop']['next_action']
                    })
                    print(f"    ✅ SOP 建立成功！ID: {sop_data['id']}")
                else:
                    print(f"    ❌ SOP 建立失敗: {sop_response.status_code}")
                    print(f"    {sop_response.text}")
            except Exception as e:
                print(f"    ❌ SOP 建立失敗: {e}")

    # 等待 embeddings 生成
    print(f"\n⏳ 等待背景任務完成（embeddings 生成）...")
    await asyncio.sleep(5)

    print(f"\n{'='*100}")
    print("✅ 真實情境建立完成！")
    print(f"{'='*100}\n")

    print(f"📊 建立結果：")
    print(f"  • SOP: {len(created_data['sops'])}/{len(REAL_SCENARIOS)}")
    print(f"  • 表單: {len(created_data['forms'])}/{sum(1 for s in REAL_SCENARIOS.values() if s['form'])}")

    return created_data


async def test_real_scenarios(created_data):
    """實際測試對話流程"""

    print(f"\n\n{'='*100}")
    print("🧪 開始實際對話測試")
    print(f"{'='*100}\n")

    test_cases = [
        {
            "scenario": "冷氣不冷排查",
            "user_questions": [
                "冷氣不冷",
                "都試過了還是不冷"  # 觸發關鍵詞
            ],
            "expected": {
                "first_response_contains": ["排查", "濾網", "溫度"],
                "second_response_contains": ["維修申請", "房號"]
            }
        },
        {
            "scenario": "水管漏水",
            "user_questions": [
                "水管漏水了"
            ],
            "expected": {
                "first_response_contains": ["關閉水源", "需要嗎", "緊急"]
            }
        },
        {
            "scenario": "續約申請",
            "user_questions": [
                "我想續約"
            ],
            "expected": {
                "first_response_contains": ["續約", "租金", "需要我協助"]
            }
        },
        {
            "scenario": "垃圾分類",
            "user_questions": [
                "垃圾怎麼丟"
            ],
            "expected": {
                "first_response_contains": ["週一", "資源回收", "19:00"]
            }
        }
    ]

    test_results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, test in enumerate(test_cases, 1):
            print(f"\n{'='*80}")
            print(f"🔍 測試 [{i}/{len(test_cases)}]: {test['scenario']}")
            print(f"{'='*80}\n")

            for q_idx, question in enumerate(test['user_questions'], 1):
                print(f"  👤 用戶問題 {q_idx}: {question}")

                try:
                    response = await client.post(
                        f"{API_URL}/chat/stream",
                        json={
                            "question": question,
                            "vendor_id": VENDOR_ID,
                            "user_role": "customer",
                            "user_id": f"test_user_{i}"
                        },
                        timeout=15.0
                    )

                    if response.status_code == 200:
                        # 解析 SSE 回應
                        answer = ""
                        for line in response.text.split('\n'):
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    if data.get('type') == 'content':
                                        answer += data.get('content', '')
                                except:
                                    pass

                        print(f"\n  🤖 系統回應:")
                        print(f"  {answer[:200]}{'...' if len(answer) > 200 else ''}\n")

                        # 驗證回應內容
                        expected_key = f"{'first' if q_idx == 1 else 'second'}_response_contains"
                        if expected_key in test['expected']:
                            contains_all = all(
                                keyword in answer
                                for keyword in test['expected'][expected_key]
                            )
                            if contains_all:
                                print(f"  ✅ 回應內容符合預期")
                                test_results.append({'test': test['scenario'], 'status': 'PASS'})
                            else:
                                print(f"  ⚠️  回應內容不完全符合預期")
                                missing = [k for k in test['expected'][expected_key] if k not in answer]
                                print(f"  缺少關鍵詞: {missing}")
                                test_results.append({'test': test['scenario'], 'status': 'PARTIAL'})
                    else:
                        print(f"  ❌ API 錯誤: {response.status_code}")
                        test_results.append({'test': test['scenario'], 'status': 'FAIL'})

                except Exception as e:
                    print(f"  ❌ 測試失敗: {e}")
                    test_results.append({'test': test['scenario'], 'status': 'ERROR'})

                # 每個問題間隔
                await asyncio.sleep(1)

    # 輸出測試結果
    print(f"\n\n{'='*100}")
    print("📊 測試結果摘要")
    print(f"{'='*100}\n")

    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    partial = sum(1 for r in test_results if r['status'] == 'PARTIAL')
    failed = sum(1 for r in test_results if r['status'] in ['FAIL', 'ERROR'])

    print(f"✅ 通過: {passed}/{len(test_results)}")
    print(f"⚠️  部分通過: {partial}/{len(test_results)}")
    print(f"❌ 失敗: {failed}/{len(test_results)}")

    return test_results


async def main():
    """主流程"""

    print("🚀 開始建立並測試真實情境\n")

    # 步驟 1: 建立 SOP 和表單
    created_data = await create_real_scenarios()

    # 步驟 2: 實際測試對話
    if created_data['sops']:
        test_results = await test_real_scenarios(created_data)
    else:
        print("\n❌ 沒有建立成功的 SOP，跳過測試")

    print(f"\n\n{'='*100}")
    print("✅ 所有流程完成！")
    print(f"{'='*100}\n")

    print("📖 詳細資訊：")
    print("  • 查看 SOP: http://localhost:8087/vendor-sop（Vendor ID: 2）")
    print("  • 查看表單: http://localhost:8087/forms")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
