#!/usr/bin/env python3
"""
建立 6 個完整的測試 SOP 情境
涵蓋 3 種已實作模式：none, manual, immediate
"""

import asyncio
import httpx
import json
from typing import List, Dict

API_URL = "http://localhost:8100"
VENDOR_ID = 2  # 使用 vendor_id = 2 進行測試

# 測試 SOP 情境定義
TEST_SCENARIOS: List[Dict] = [
    # ========== 情境 1: 資訊型（none + none）==========
    {
        "category_id": 154,  # 租賃流程相關資訊
        "item_number": 9001,
        "item_name": "【測試】租金繳納說明",
        "content": """📝 **租金繳納方式**

**繳納日期**：
• 每月 5 日前繳納當月租金
• 逾期每日加收 50 元滯納金

**繳納方式**：
1️⃣ **銀行轉帳（推薦）**
   銀行：玉山銀行
   帳號：1234-5678-9012
   戶名：ABC 租賃管理公司

2️⃣ **現金繳納**
   地點：管理室（一樓）
   時間：週一至週五 09:00-18:00

3️⃣ **支票繳納**
   抬頭：ABC 租賃管理公司
   請於 3 日前交付管理室

**注意事項**：
⚠️ 轉帳後請保留收據
⚠️ 首次繳納請主動告知房號
⚠️ 如有任何問題請聯絡管理員 0912-345-678""",
        "priority": 50,
        "trigger_mode": "none",
        "next_action": "none",
        "intent_ids": []
    },

    # ========== 情境 2: 排查型（manual + form_fill）==========
    {
        "category_id": 154,
        "item_number": 9002,
        "item_name": "【測試】網路不通排查",
        "content": """🌐 **網路連線問題排查**

請先依照以下步驟排查：

**步驟 1：檢查實體連線**
□ 確認網路線是否插好（數據機 ↔ 路由器）
□ 檢查電源指示燈是否正常亮起
□ 嘗試拔插網路線重新連接

**步驟 2：重新啟動設備**
□ 關閉路由器電源，等待 30 秒
□ 重新開啟路由器，等待 2-3 分鐘
□ 重新啟動電腦/手機

**步驟 3：檢查帳號狀態**
□ 確認網路帳單是否已繳納
□ 檢查是否有其他設備可以連線

**步驟 4：測試連線**
□ 開啟瀏覽器訪問 www.google.com
□ 確認是否可以正常上網

如果以上步驟都試過了還是無法連線，請告訴我，我會協助您填寫報修表單。""",
        "priority": 60,
        "trigger_mode": "manual",
        "next_action": "form_fill",
        "trigger_keywords": ["還是不行", "試過了", "沒用", "不能用", "還是連不上", "都試過了"],
        "next_form_id": "maintenance_request",
        "followup_prompt": "好的，我來協助您填寫網路維修表單。",
        "intent_ids": []
    },

    # ========== 情境 3: 行動型（immediate + form_fill）==========
    {
        "category_id": 154,
        "item_number": 9003,
        "item_name": "【測試】門鎖故障緊急",
        "content": """🚪 **門鎖故障緊急處理**

**立即處理方式**：

1️⃣ **無法開門（從外面）**
   • 請聯絡管理員：0912-345-678
   • 管理員會攜帶備用鑰匙協助開門

2️⃣ **無法鎖門（從外面）**
   • 可暫時使用門把轉鎖
   • 盡快聯絡維修人員處理

3️⃣ **鑰匙卡失靈**
   • 請至管理室重新感應卡片
   • 若無法解決，可能需要更換卡片

**安全提醒**：
⚠️ 如果是深夜緊急狀況（22:00 後），請直接撥打緊急專線：0800-123-456
⚠️ 無法鎖門時請勿留貴重物品在室內

這是緊急維修狀況，我可以立即為您安排維修人員。需要嗎？""",
        "priority": 90,
        "trigger_mode": "immediate",
        "next_action": "form_fill",
        "immediate_prompt": "這是緊急維修狀況，我可以立即為您安排維修人員。需要嗎？",
        "next_form_id": "repair_request",
        "followup_prompt": "好的，請提供以下資訊，我會盡快安排維修人員。",
        "intent_ids": []
    },

    # ========== 情境 4: 排查型（manual + none）==========
    {
        "category_id": 154,
        "item_number": 9004,
        "item_name": "【測試】熱水器沒熱水",
        "content": """🚿 **熱水器無熱水排查**

請先依照以下步驟檢查：

**步驟 1：檢查電源和瓦斯**
□ 確認熱水器電源是否開啟（綠燈亮起）
□ 檢查瓦斯是否用完（看錶）
□ 確認瓦斯開關是否打開

**步驟 2：檢查水溫設定**
□ 確認溫度設定是否正確（建議 40-45°C）
□ 調整溫度後等待 1-2 分鐘
□ 測試水溫是否變化

**步驟 3：檢查水壓**
□ 確認水龍頭水量是否正常
□ 水量太小可能導致熱水器無法啟動
□ 嘗試開大水量測試

**步驟 4：重新啟動**
□ 關閉熱水器電源
□ 等待 10 秒後重新開啟
□ 等待 1 分鐘後測試

如果以上步驟都無法解決，可能是熱水器故障，請聯絡客服：0912-345-678（週一至週五 09:00-18:00）。""",
        "priority": 60,
        "trigger_mode": "manual",
        "next_action": "none",
        "trigger_keywords": ["還是沒熱水", "還是不熱", "試過了", "沒用", "都檢查過了"],
        "followup_prompt": "看來可能是熱水器本身的問題。建議您聯絡客服安排專業檢修：0912-345-678（週一至週五 09:00-18:00）。或者您也可以加客服 LINE: @abc_rental 線上諮詢。",
        "intent_ids": []
    },

    # ========== 情境 5: 行動型（immediate + none）==========
    {
        "category_id": 154,
        "item_number": 9005,
        "item_name": "【測試】查詢繳費記錄",
        "content": """💰 **租金繳費記錄查詢**

您可以透過以下方式查詢繳費記錄：

**線上查詢**：
1. 登入租客專區：https://tenant.abc-rental.com
2. 點選「繳費記錄」
3. 可查看近 12 個月的繳費明細

**電話查詢**：
• 客服專線：02-1234-5678
• 服務時間：週一至週五 09:00-18:00
• 請準備身分證後 4 碼進行身分驗證

**臨櫃查詢**：
• 地點：管理室（一樓）
• 時間：週一至週五 09:00-18:00
• 攜帶身分證即可查詢

**記錄內容**：
✓ 繳費日期
✓ 繳費金額
✓ 繳費方式
✓ 收據編號

需要我幫您查詢目前的繳費記錄嗎？""",
        "priority": 50,
        "trigger_mode": "immediate",
        "next_action": "none",
        "immediate_prompt": "需要我幫您查詢目前的繳費記錄嗎？",
        "followup_prompt": "好的，為了確認您的身分，請提供以下資訊：\n• 房號\n• 身分證後 4 碼\n\n（註：實際系統中會調用 API 查詢，目前為測試模式）",
        "intent_ids": []
    },

    # ========== 情境 6: 資訊型（none + none）==========
    {
        "category_id": 154,
        "item_number": 9006,
        "item_name": "【測試】公設使用規定",
        "content": """🏢 **公共設施使用規定**

**健身房**
📍 位置：B1
⏰ 開放時間：06:00-22:00
📝 使用規定：
  • 請穿著運動鞋
  • 使用後請擦拭器材
  • 禁止大聲喧嘩
  • 未滿 12 歲需家長陪同

**交誼廳**
📍 位置：1F
⏰ 開放時間：24 小時
📝 使用規定：
  • 可預約舉辦活動（需提前 7 天）
  • 使用後請整理環境
  • 22:00 後請降低音量
  • 禁止烹飪（僅可使用微波爐）

**洗衣房**
📍 位置：B1
⏰ 開放時間：06:00-23:00
💰 費用：洗衣 30 元/次，烘衣 20 元/次
📝 使用規定：
  • 使用悠遊卡付費
  • 洗衣完成請立即取出
  • 不得洗滌寵物用品

**頂樓花園**
📍 位置：RF
⏰ 開放時間：06:00-22:00
📝 使用規定：
  • 禁止烤肉
  • 禁止帶寵物
  • 請勿摘取植物

如有任何疑問，請聯絡管理員：0912-345-678""",
        "priority": 40,
        "trigger_mode": "none",
        "next_action": "none",
        "intent_ids": []
    }
]


async def create_test_scenarios():
    """建立所有測試 SOP"""

    print("=" * 100)
    print("🧪 建立測試 SOP 情境")
    print("=" * 100)
    print(f"\n📊 總共 {len(TEST_SCENARIOS)} 個測試情境")
    print(f"🎯 Vendor ID: {VENDOR_ID}")
    print(f"🔗 API URL: {API_URL}\n")

    created_ids = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n{'='*80}")
            print(f"📝 [{i}/{len(TEST_SCENARIOS)}] {scenario['item_name']}")
            print(f"{'='*80}")
            print(f"  觸發模式: {scenario['trigger_mode']}")
            print(f"  後續動作: {scenario['next_action']}")

            if scenario['trigger_mode'] == 'manual':
                print(f"  關鍵詞: {', '.join(scenario['trigger_keywords'])}")
            elif scenario['trigger_mode'] == 'immediate':
                print(f"  提示詞: {scenario['immediate_prompt']}")

            if scenario['next_action'] == 'form_fill':
                print(f"  表單 ID: {scenario['next_form_id']}")

            try:
                response = await client.post(
                    f"{API_URL}/api/v1/vendors/{VENDOR_ID}/sop/items",
                    json=scenario
                )

                if response.status_code == 201:
                    data = response.json()
                    sop_id = data.get('id')
                    created_ids.append({
                        'id': sop_id,
                        'name': scenario['item_name'],
                        'trigger_mode': scenario['trigger_mode'],
                        'next_action': scenario['next_action']
                    })
                    print(f"  ✅ 建立成功！ID: {sop_id}")
                else:
                    print(f"  ❌ 建立失敗: {response.status_code}")
                    print(f"  錯誤: {response.text}")

            except Exception as e:
                print(f"  ❌ 建立失敗: {e}")

    # 等待背景任務完成（embeddings 生成）
    print(f"\n⏳ 等待背景任務完成（embeddings 生成）...")
    await asyncio.sleep(5)

    # 輸出結果摘要
    print(f"\n{'='*100}")
    print(f"✅ 測試 SOP 建立完成！")
    print(f"{'='*100}\n")

    print(f"📊 成功建立 {len(created_ids)}/{len(TEST_SCENARIOS)} 個測試 SOP\n")

    print("📋 **建立的測試 SOP 列表**：\n")
    for item in created_ids:
        print(f"  • ID {item['id']}: {item['name']}")
        print(f"    模式: {item['trigger_mode']} + {item['next_action']}")

    print(f"\n{'='*100}")
    print("📖 **測試對話腳本**：請參考 test_sop_scenarios_dialogue.md")
    print("🗑️  **清理測試數據**：執行 cleanup_test_sop.py")
    print(f"{'='*100}\n")

    return created_ids


if __name__ == "__main__":
    asyncio.run(create_test_scenarios())
