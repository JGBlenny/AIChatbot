#!/usr/bin/env python3
"""
綜合對話邏輯測試 - 100則多語意多情境問題
Date: 2026-02-12
Purpose: 全面測試對話系統的邏輯正確性
"""

import asyncio
import httpx
import json
import time
from typing import List, Dict
from datetime import datetime

# API 配置
API_BASE_URL = "http://localhost:8100"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/message"

# 測試問題集 - 100則涵蓋多語意、多情境
TEST_CASES = [
    # ===== 類別 1: 租金相關 (10題) =====
    {
        "id": 1,
        "question": "租金怎麼繳？",
        "category": "租金-繳費方式",
        "expected_type": "knowledge",
        "description": "基本租金繳費查詢"
    },
    {
        "id": 2,
        "question": "每個月幾號要繳房租",
        "category": "租金-繳費日期",
        "expected_type": "knowledge",
        "description": "繳費日期查詢"
    },
    {
        "id": 3,
        "question": "我忘記繳租金了會怎樣",
        "category": "租金-逾期處理",
        "expected_type": "knowledge/sop",
        "description": "逾期後果查詢"
    },
    {
        "id": 4,
        "question": "可以用信用卡付房租嗎",
        "category": "租金-繳費方式",
        "expected_type": "knowledge",
        "description": "特定繳費方式查詢"
    },
    {
        "id": 5,
        "question": "租金是多少錢",
        "category": "租金-金額查詢",
        "expected_type": "api_call",
        "description": "個人租金查詢（需API）"
    },
    {
        "id": 6,
        "question": "房租太貴了可以少一點嗎",
        "category": "租金-議價",
        "expected_type": "sop/direct",
        "description": "租金協商（多語意）"
    },
    {
        "id": 7,
        "question": "這個月還沒繳是不是",
        "category": "租金-繳費狀態",
        "expected_type": "api_call",
        "description": "繳費狀態查詢（需API）"
    },
    {
        "id": 8,
        "question": "我可以分期繳租金嗎",
        "category": "租金-繳費方式",
        "expected_type": "knowledge/sop",
        "description": "特殊繳費需求"
    },
    {
        "id": 9,
        "question": "租金包含水電費嗎",
        "category": "租金-包含項目",
        "expected_type": "knowledge",
        "description": "租金範圍查詢"
    },
    {
        "id": 10,
        "question": "之前繳的租金收據在哪裡",
        "category": "租金-收據查詢",
        "expected_type": "knowledge/api",
        "description": "收據查詢（多可能）"
    },

    # ===== 類別 2: 維修報修 (10題) =====
    {
        "id": 11,
        "question": "冷氣壞了怎麼辦",
        "category": "維修-報修",
        "expected_type": "sop",
        "description": "基本報修需求"
    },
    {
        "id": 12,
        "question": "馬桶堵住了",
        "category": "維修-緊急報修",
        "expected_type": "sop",
        "description": "緊急維修（簡短表達）"
    },
    {
        "id": 13,
        "question": "報修要錢嗎",
        "category": "維修-費用",
        "expected_type": "knowledge",
        "description": "維修費用查詢"
    },
    {
        "id": 14,
        "question": "我報修已經三天了還沒來修",
        "category": "維修-進度追蹤",
        "expected_type": "sop/api",
        "description": "維修進度查詢（含抱怨）"
    },
    {
        "id": 15,
        "question": "可以自己找師傅來修嗎",
        "category": "維修-自行維修",
        "expected_type": "knowledge",
        "description": "維修政策查詢"
    },
    {
        "id": 16,
        "question": "電燈一直閃",
        "category": "維修-故障描述",
        "expected_type": "sop",
        "description": "故障問題描述（需引導）"
    },
    {
        "id": 17,
        "question": "晚上可以報修嗎",
        "category": "維修-時間限制",
        "expected_type": "knowledge",
        "description": "報修時間查詢"
    },
    {
        "id": 18,
        "question": "上次報修的進度",
        "category": "維修-進度查詢",
        "expected_type": "api",
        "description": "歷史報修查詢"
    },
    {
        "id": 19,
        "question": "冷氣不冷",
        "category": "維修-故障",
        "expected_type": "sop",
        "description": "故障描述（需SOP引導）"
    },
    {
        "id": 20,
        "question": "報修電話是多少",
        "category": "維修-聯絡方式",
        "expected_type": "knowledge",
        "description": "聯絡資訊查詢"
    },

    # ===== 類別 3: 合約相關 (10題) =====
    {
        "id": 21,
        "question": "我想續約",
        "category": "合約-續約",
        "expected_type": "sop/form",
        "description": "續約需求"
    },
    {
        "id": 22,
        "question": "提前退租要怎麼辦",
        "category": "合約-退租",
        "expected_type": "sop/knowledge",
        "description": "提前解約查詢"
    },
    {
        "id": 23,
        "question": "合約什麼時候到期",
        "category": "合約-到期日",
        "expected_type": "api",
        "description": "合約資訊查詢"
    },
    {
        "id": 24,
        "question": "押金什麼時候退",
        "category": "合約-押金退還",
        "expected_type": "knowledge",
        "description": "押金政策查詢"
    },
    {
        "id": 25,
        "question": "可以換房間嗎",
        "category": "合約-換房",
        "expected_type": "sop/knowledge",
        "description": "換房需求"
    },
    {
        "id": 26,
        "question": "合約可以改成我朋友的名字嗎",
        "category": "合約-轉租",
        "expected_type": "knowledge/sop",
        "description": "轉租查詢"
    },
    {
        "id": 27,
        "question": "最短要租多久",
        "category": "合約-租期",
        "expected_type": "knowledge",
        "description": "租期政策查詢"
    },
    {
        "id": 28,
        "question": "我的合約書在哪裡",
        "category": "合約-文件查詢",
        "expected_type": "knowledge/api",
        "description": "合約文件查詢"
    },
    {
        "id": 29,
        "question": "提前退租押金會退嗎",
        "category": "合約-退租押金",
        "expected_type": "knowledge",
        "description": "複合查詢（退租+押金）"
    },
    {
        "id": 30,
        "question": "我想看我的租約內容",
        "category": "合約-查看",
        "expected_type": "api/knowledge",
        "description": "合約內容查詢"
    },

    # ===== 類別 4: 設施與服務 (10題) =====
    {
        "id": 31,
        "question": "有洗衣機嗎",
        "category": "設施-查詢",
        "expected_type": "knowledge",
        "description": "設施查詢"
    },
    {
        "id": 32,
        "question": "停車位在哪裡",
        "category": "設施-停車",
        "expected_type": "knowledge",
        "description": "停車資訊查詢"
    },
    {
        "id": 33,
        "question": "垃圾怎麼丟",
        "category": "設施-垃圾",
        "expected_type": "knowledge",
        "description": "垃圾處理查詢"
    },
    {
        "id": 34,
        "question": "wifi密碼是什麼",
        "category": "設施-網路",
        "expected_type": "knowledge/api",
        "description": "網路資訊查詢"
    },
    {
        "id": 35,
        "question": "可以養寵物嗎",
        "category": "政策-寵物",
        "expected_type": "knowledge",
        "description": "寵物政策查詢"
    },
    {
        "id": 36,
        "question": "電費怎麼算",
        "category": "費用-電費",
        "expected_type": "knowledge",
        "description": "電費計算查詢"
    },
    {
        "id": 37,
        "question": "管理費包含什麼",
        "category": "費用-管理費",
        "expected_type": "knowledge",
        "description": "費用項目查詢"
    },
    {
        "id": 38,
        "question": "可以開伙嗎",
        "category": "政策-開伙",
        "expected_type": "knowledge",
        "description": "開伙政策查詢"
    },
    {
        "id": 39,
        "question": "晚上幾點後不能吵",
        "category": "政策-安靜時間",
        "expected_type": "knowledge",
        "description": "社區規範查詢"
    },
    {
        "id": 40,
        "question": "可以帶朋友來住嗎",
        "category": "政策-訪客",
        "expected_type": "knowledge",
        "description": "訪客政策查詢"
    },

    # ===== 類別 5: 客服與聯絡 (10題) =====
    {
        "id": 41,
        "question": "客服電話是多少",
        "category": "聯絡-電話",
        "expected_type": "knowledge",
        "description": "客服資訊查詢"
    },
    {
        "id": 42,
        "question": "我要投訴",
        "category": "客服-投訴",
        "expected_type": "sop/form",
        "description": "投訴需求"
    },
    {
        "id": 43,
        "question": "管理員在哪裡",
        "category": "聯絡-管理員",
        "expected_type": "knowledge",
        "description": "管理員資訊查詢"
    },
    {
        "id": 44,
        "question": "line客服",
        "category": "聯絡-LINE",
        "expected_type": "knowledge",
        "description": "LINE客服查詢（簡短）"
    },
    {
        "id": 45,
        "question": "我有建議想反應",
        "category": "客服-建議",
        "expected_type": "sop/form",
        "description": "建議反饋"
    },
    {
        "id": 46,
        "question": "你們上班時間",
        "category": "聯絡-營業時間",
        "expected_type": "knowledge",
        "description": "營業時間查詢"
    },
    {
        "id": 47,
        "question": "可以email問問題嗎",
        "category": "聯絡-Email",
        "expected_type": "knowledge",
        "description": "Email聯絡查詢"
    },
    {
        "id": 48,
        "question": "緊急聯絡人電話",
        "category": "聯絡-緊急",
        "expected_type": "knowledge",
        "description": "緊急聯絡查詢"
    },
    {
        "id": 49,
        "question": "我想當面談",
        "category": "聯絡-預約",
        "expected_type": "sop/knowledge",
        "description": "預約諮詢"
    },
    {
        "id": 50,
        "question": "客服都不接電話",
        "category": "客服-抱怨",
        "expected_type": "sop",
        "description": "服務抱怨"
    },

    # ===== 類別 6: 多語意/模糊問題 (10題) =====
    {
        "id": 51,
        "question": "多少錢",
        "category": "模糊-費用",
        "expected_type": "unclear/form",
        "description": "極度模糊（需澄清）"
    },
    {
        "id": 52,
        "question": "這個可以嗎",
        "category": "模糊-許可",
        "expected_type": "unclear",
        "description": "缺乏上下文"
    },
    {
        "id": 53,
        "question": "租金跟押金加起來多少",
        "category": "複合-計算",
        "expected_type": "api/knowledge",
        "description": "複合計算問題"
    },
    {
        "id": 54,
        "question": "我想退租但還沒到期",
        "category": "複合-退租",
        "expected_type": "sop/knowledge",
        "description": "複合問題（退租+提前）"
    },
    {
        "id": 55,
        "question": "冷氣壞了可以自己修嗎還是要報修",
        "category": "複合-維修",
        "expected_type": "sop/knowledge",
        "description": "複合選擇問題"
    },
    {
        "id": 56,
        "question": "現在",
        "category": "模糊-時間",
        "expected_type": "unclear",
        "description": "過於簡短"
    },
    {
        "id": 57,
        "question": "怎麼辦",
        "category": "模糊-求助",
        "expected_type": "unclear",
        "description": "完全缺乏資訊"
    },
    {
        "id": 58,
        "question": "我想問一下關於租金和維修還有續約的問題",
        "category": "複合-多主題",
        "expected_type": "unclear/form",
        "description": "過於廣泛"
    },
    {
        "id": 59,
        "question": "能不能",
        "category": "模糊-詢問",
        "expected_type": "unclear",
        "description": "不完整問句"
    },
    {
        "id": 60,
        "question": "租金是每個月幾號繳還有可以用什麼方式付",
        "category": "複合-租金",
        "expected_type": "knowledge",
        "description": "複合問題（日期+方式）"
    },

    # ===== 類別 7: 錯字與同義詞 (10題) =====
    {
        "id": 61,
        "question": "房租怎麼交",
        "category": "同義詞-租金",
        "expected_type": "knowledge",
        "description": "租金（交=繳）"
    },
    {
        "id": 62,
        "question": "冷氣不會涼",
        "category": "同義詞-維修",
        "expected_type": "sop",
        "description": "冷氣（不會涼=不冷）"
    },
    {
        "id": 63,
        "question": "我要報修",
        "category": "簡化-報修",
        "expected_type": "sop/form",
        "description": "直接需求表達"
    },
    {
        "id": 64,
        "question": "電費帳單",
        "category": "簡化-電費",
        "expected_type": "knowledge/api",
        "description": "名詞查詢"
    },
    {
        "id": 65,
        "question": "水電",
        "category": "簡化-費用",
        "expected_type": "knowledge",
        "description": "極簡查詢"
    },
    {
        "id": 66,
        "question": "欠租",
        "category": "簡化-逾期",
        "expected_type": "knowledge/sop",
        "description": "單詞查詢（可能有多義）"
    },
    {
        "id": 67,
        "question": "aircon唔夠凍",
        "category": "方言-維修",
        "expected_type": "unclear/sop",
        "description": "粵語+英文混合"
    },
    {
        "id": 68,
        "question": "AC壞了",
        "category": "簡稱-維修",
        "expected_type": "sop",
        "description": "英文簡稱（AC=冷氣）"
    },
    {
        "id": 69,
        "question": "deposit",
        "category": "英文-押金",
        "expected_type": "knowledge",
        "description": "全英文查詢"
    },
    {
        "id": 70,
        "question": "租金幾多錢",
        "category": "方言-租金",
        "expected_type": "api/knowledge",
        "description": "粵語表達"
    },

    # ===== 類別 8: 帳務查詢 (10題) =====
    {
        "id": 71,
        "question": "我的帳單",
        "category": "帳務-帳單",
        "expected_type": "api",
        "description": "帳單查詢"
    },
    {
        "id": 72,
        "question": "這個月要繳多少",
        "category": "帳務-應繳金額",
        "expected_type": "api",
        "description": "應繳金額查詢"
    },
    {
        "id": 73,
        "question": "我有沒有欠費",
        "category": "帳務-欠費",
        "expected_type": "api",
        "description": "欠費狀態查詢"
    },
    {
        "id": 74,
        "question": "繳費記錄",
        "category": "帳務-記錄",
        "expected_type": "api",
        "description": "歷史記錄查詢"
    },
    {
        "id": 75,
        "question": "上個月的電費",
        "category": "帳務-電費",
        "expected_type": "api",
        "description": "特定月份查詢"
    },
    {
        "id": 76,
        "question": "我繳了沒有",
        "category": "帳務-繳費確認",
        "expected_type": "api",
        "description": "繳費確認"
    },
    {
        "id": 77,
        "question": "為什麼這個月特別貴",
        "category": "帳務-費用異常",
        "expected_type": "api/sop",
        "description": "費用疑問（需查詢+解釋）"
    },
    {
        "id": 78,
        "question": "可以分期付款嗎",
        "category": "帳務-分期",
        "expected_type": "knowledge/sop",
        "description": "付款方式詢問"
    },
    {
        "id": 79,
        "question": "發票",
        "category": "帳務-發票",
        "expected_type": "knowledge/api",
        "description": "發票查詢（簡短）"
    },
    {
        "id": 80,
        "question": "我想看去年的繳費紀錄",
        "category": "帳務-歷史",
        "expected_type": "api",
        "description": "長期歷史查詢"
    },

    # ===== 類別 9: 系統操作 (10題) =====
    {
        "id": 81,
        "question": "怎麼登入",
        "category": "系統-登入",
        "expected_type": "knowledge",
        "description": "系統操作查詢"
    },
    {
        "id": 82,
        "question": "忘記密碼",
        "category": "系統-密碼",
        "expected_type": "sop/knowledge",
        "description": "密碼問題"
    },
    {
        "id": 83,
        "question": "app在哪裡下載",
        "category": "系統-下載",
        "expected_type": "knowledge",
        "description": "App資訊查詢"
    },
    {
        "id": 84,
        "question": "如何修改個人資料",
        "category": "系統-資料修改",
        "expected_type": "knowledge/sop",
        "description": "資料修改流程"
    },
    {
        "id": 85,
        "question": "線上繳費教學",
        "category": "系統-繳費教學",
        "expected_type": "knowledge",
        "description": "操作教學"
    },
    {
        "id": 86,
        "question": "手機收不到驗證碼",
        "category": "系統-驗證碼",
        "expected_type": "sop/knowledge",
        "description": "驗證問題"
    },
    {
        "id": 87,
        "question": "如何綁定信用卡",
        "category": "系統-綁定",
        "expected_type": "knowledge/sop",
        "description": "綁定流程"
    },
    {
        "id": 88,
        "question": "系統一直當掉",
        "category": "系統-故障",
        "expected_type": "sop",
        "description": "技術問題"
    },
    {
        "id": 89,
        "question": "怎麼看我的租約",
        "category": "系統-查看租約",
        "expected_type": "knowledge",
        "description": "功能使用詢問"
    },
    {
        "id": 90,
        "question": "可以用電腦嗎還是只能手機",
        "category": "系統-平台",
        "expected_type": "knowledge",
        "description": "平台支援查詢"
    },

    # ===== 類別 10: 不相關/邊界 (10題) =====
    {
        "id": 91,
        "question": "今天天氣如何",
        "category": "不相關-天氣",
        "expected_type": "direct_answer",
        "description": "完全不相關"
    },
    {
        "id": 92,
        "question": "你是誰",
        "category": "閒聊-身份",
        "expected_type": "direct_answer",
        "description": "閒聊問題"
    },
    {
        "id": 93,
        "question": "你好",
        "category": "閒聊-打招呼",
        "expected_type": "direct_answer",
        "description": "打招呼"
    },
    {
        "id": 94,
        "question": "謝謝",
        "category": "禮貌-感謝",
        "expected_type": "direct_answer",
        "description": "禮貌用語"
    },
    {
        "id": 95,
        "question": "測試",
        "category": "測試-指令",
        "expected_type": "direct_answer/unclear",
        "description": "測試指令"
    },
    {
        "id": 96,
        "question": "........................",
        "category": "無效-符號",
        "expected_type": "unclear",
        "description": "無意義輸入"
    },
    {
        "id": 97,
        "question": "123456",
        "category": "無效-數字",
        "expected_type": "unclear",
        "description": "純數字輸入"
    },
    {
        "id": 98,
        "question": "asdfghjkl",
        "category": "無效-亂碼",
        "expected_type": "unclear",
        "description": "亂打字"
    },
    {
        "id": 99,
        "question": "我想問一個超級超級長的問題就是關於租房子的事情我不知道該怎麼辦才好因為有很多狀況發生包括租金還有維修還有合約等等很多問題不知道該從何問起",
        "category": "邊界-過長",
        "expected_type": "unclear/form",
        "description": "極長問題"
    },
    {
        "id": 100,
        "question": "a",
        "category": "邊界-過短",
        "expected_type": "unclear",
        "description": "極短問題"
    }
]


async def test_question(client: httpx.AsyncClient, test_case: Dict) -> Dict:
    """測試單一問題"""
    try:
        response = await client.post(
            CHAT_ENDPOINT,
            json={
                "message": test_case["question"],
                "vendor_id": 1,
                "target_user": "tenant",
                "mode": "b2c"
            },
            timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "id": test_case["id"],
                "question": test_case["question"],
                "category": test_case["category"],
                "expected_type": test_case["expected_type"],
                "description": test_case["description"],
                "status": "success",
                "response": {
                    "intent": result.get("intent"),
                    "answer": result.get("answer", "")[:200],  # 前200字
                    "knowledge_count": len(result.get("knowledge", [])),
                    "sop_count": len(result.get("sop_items", [])),
                    "action_type": result.get("action_type"),
                    "form_id": result.get("form_id"),
                    "confidence": result.get("confidence"),
                },
                "raw_response": result
            }
        else:
            return {
                "id": test_case["id"],
                "question": test_case["question"],
                "category": test_case["category"],
                "status": "error",
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "id": test_case["id"],
            "question": test_case["question"],
            "category": test_case["category"],
            "status": "error",
            "error": str(e)
        }


async def run_all_tests():
    """執行所有測試"""
    print("=" * 80)
    print("綜合對話邏輯測試 - 100則多語意多情境問題")
    print("=" * 80)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"測試問題數: {len(TEST_CASES)}")
    print("=" * 80)

    results = []

    async with httpx.AsyncClient() as client:
        # 批次執行測試（每批10個，避免過載）
        batch_size = 10
        for i in range(0, len(TEST_CASES), batch_size):
            batch = TEST_CASES[i:i + batch_size]
            print(f"\n執行批次 {i // batch_size + 1}/{(len(TEST_CASES) + batch_size - 1) // batch_size}")

            batch_results = await asyncio.gather(
                *[test_question(client, case) for case in batch]
            )
            results.extend(batch_results)

            # 進度顯示
            for result in batch_results:
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"  {status_icon} [{result['id']:3d}] {result['question'][:40]:40s} -> {result.get('response', {}).get('action_type', 'ERROR')}")

            # 避免過快
            if i + batch_size < len(TEST_CASES):
                await asyncio.sleep(1)

    return results


def analyze_results(results: List[Dict]):
    """分析測試結果"""
    print("\n" + "=" * 80)
    print("測試結果分析")
    print("=" * 80)

    # 基本統計
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    error = total - success

    print(f"\n📊 基本統計:")
    print(f"  總測試數: {total}")
    print(f"  成功: {success} ({success/total*100:.1f}%)")
    print(f"  失敗: {error} ({error/total*100:.1f}%)")

    # Action Type 分布
    action_types = {}
    for r in results:
        if r["status"] == "success":
            action = r["response"].get("action_type", "unknown")
            action_types[action] = action_types.get(action, 0) + 1

    print(f"\n📈 Action Type 分布:")
    for action, count in sorted(action_types.items(), key=lambda x: -x[1]):
        action_str = str(action) if action is not None else "None"
        print(f"  {action_str:20s}: {count:3d} ({count/success*100:.1f}%)")

    # Intent 分布
    intents = {}
    for r in results:
        if r["status"] == "success":
            intent = r["response"].get("intent", "unknown")
            intents[intent] = intents.get(intent, 0) + 1

    print(f"\n🎯 Intent 分布:")
    for intent, count in sorted(intents.items(), key=lambda x: -x[1])[:10]:
        intent_str = str(intent) if intent is not None else "None"
        print(f"  {intent_str:30s}: {count:3d}")

    # 類別統計
    categories = {}
    for r in results:
        cat = r["category"].split("-")[0]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r["status"] == "success":
            categories[cat]["success"] += 1

    print(f"\n📚 類別統計:")
    for cat, stats in sorted(categories.items()):
        success_rate = stats["success"] / stats["total"] * 100
        print(f"  {cat:15s}: {stats['success']:2d}/{stats['total']:2d} ({success_rate:.0f}%)")

    # 檢索統計
    knowledge_used = sum(1 for r in results if r.get("response", {}).get("knowledge_count", 0) > 0)
    sop_used = sum(1 for r in results if r.get("response", {}).get("sop_count", 0) > 0)

    print(f"\n🔍 檢索統計:")
    if success > 0:
        print(f"  使用知識庫: {knowledge_used}/{success} ({knowledge_used/success*100:.1f}%)")
        print(f"  使用 SOP: {sop_used}/{success} ({sop_used/success*100:.1f}%)")
    else:
        print(f"  使用知識庫: {knowledge_used}/{success}")
        print(f"  使用 SOP: {sop_used}/{success}")

    # 問題案例
    print(f"\n⚠️  潛在問題:")
    unclear_count = sum(1 for r in results if r.get("response", {}).get("action_type") == "unclear")
    print(f"  Unclear 問題: {unclear_count} 個")

    fallback_count = sum(1 for r in results if r.get("response", {}).get("action_type") == "direct_answer")
    print(f"  Fallback 到 LLM: {fallback_count} 個")

    return {
        "total": total,
        "success": success,
        "error": error,
        "action_types": action_types,
        "intents": intents,
        "categories": categories,
        "knowledge_used": knowledge_used,
        "sop_used": sop_used
    }


def save_results(results: List[Dict], analysis: Dict):
    """儲存結果"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"/Users/lenny/jgb/AIChatbot/tests/dialogue_test_results_{timestamp}.json"

    output = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "analysis": analysis,
        "results": results
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 結果已儲存: {filename}")
    return filename


async def main():
    """主程式"""
    print("\n🚀 開始執行綜合對話邏輯測試...\n")

    # 執行測試
    results = await run_all_tests()

    # 分析結果
    analysis = analyze_results(results)

    # 儲存結果
    filename = save_results(results, analysis)

    print("\n" + "=" * 80)
    print("✅ 測試完成！")
    print("=" * 80)

    return results, analysis


if __name__ == "__main__":
    asyncio.run(main())
