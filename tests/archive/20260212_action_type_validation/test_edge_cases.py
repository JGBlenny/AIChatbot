#!/usr/bin/env python3
"""
邊界情況和異常處理測試腳本
測試各種極端輸入和異常情況
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List

# API 配置
API_BASE_URL = "http://localhost:8100"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/message"

# 邊界測試案例
EDGE_TEST_CASES = [
    # 1. 空輸入測試
    {
        "id": 1,
        "name": "空字串",
        "message": "",
        "should_fail": True,
        "description": "測試空輸入處理"
    },
    {
        "id": 2,
        "name": "純空白",
        "message": "   ",
        "should_fail": False,
        "description": "測試純空白輸入"
    },

    # 2. 極長輸入測試
    {
        "id": 3,
        "name": "極長文字",
        "message": "租金" * 500,  # 1000 字元
        "should_fail": False,
        "description": "測試極長輸入處理"
    },

    # 3. 特殊字元測試
    {
        "id": 4,
        "name": "特殊符號",
        "message": "租金!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "should_fail": False,
        "description": "測試特殊符號處理"
    },
    {
        "id": 5,
        "name": "SQL 注入嘗試",
        "message": "租金'; DROP TABLE knowledge_base; --",
        "should_fail": False,
        "description": "測試 SQL 注入防護"
    },
    {
        "id": 6,
        "name": "XSS 嘗試",
        "message": "<script>alert('XSS')</script>租金",
        "should_fail": False,
        "description": "測試 XSS 防護"
    },

    # 4. Unicode 和 Emoji 測試
    {
        "id": 7,
        "name": "Emoji 輸入",
        "message": "租金 😀😃😄😁",
        "should_fail": False,
        "description": "測試 Emoji 處理"
    },
    {
        "id": 8,
        "name": "多語言混合",
        "message": "租金 rent 租金 かきん",
        "should_fail": False,
        "description": "測試多語言處理"
    },
    {
        "id": 9,
        "name": "特殊 Unicode",
        "message": "租金\u0000\u0001\u0002",
        "should_fail": False,
        "description": "測試特殊 Unicode 字元"
    },

    # 5. 換行和格式測試
    {
        "id": 10,
        "name": "多行輸入",
        "message": "租金\n怎麼繳\n多少錢",
        "should_fail": False,
        "description": "測試多行輸入"
    },
    {
        "id": 11,
        "name": "Tab 字元",
        "message": "租金\t\t怎麼繳",
        "should_fail": False,
        "description": "測試 Tab 字元"
    },

    # 6. 數字極值測試
    {
        "id": 12,
        "name": "純數字",
        "message": "123456789",
        "should_fail": False,
        "description": "測試純數字輸入"
    },
    {
        "id": 13,
        "name": "超大數字",
        "message": "9" * 100,
        "should_fail": False,
        "description": "測試超大數字"
    },
]

# 測試結果
results = []

async def test_edge_case(client: httpx.AsyncClient, test_case: Dict) -> Dict:
    """測試單個邊界案例"""
    try:
        response = await client.post(
            CHAT_ENDPOINT,
            json={
                "message": test_case["message"],
                "vendor_id": 1,
                "target_user": "tenant",
                "mode": "b2c"
            },
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()

            # 檢查 action_type 存在
            has_action_type = "action_type" in data and data["action_type"] is not None

            return {
                "id": test_case["id"],
                "name": test_case["name"],
                "status": "success",
                "should_fail": test_case["should_fail"],
                "action_type": data.get("action_type"),
                "has_action_type": has_action_type,
                "answer_length": len(data.get("answer", "")),
                "has_answer": bool(data.get("answer")),
                "error_in_answer": "error" in data.get("answer", "").lower() or "錯誤" in data.get("answer", ""),
                "raw_response": data
            }
        elif response.status_code == 422 and test_case["should_fail"]:
            # 預期的失敗
            return {
                "id": test_case["id"],
                "name": test_case["name"],
                "status": "expected_fail",
                "should_fail": test_case["should_fail"],
                "http_status": response.status_code
            }
        else:
            return {
                "id": test_case["id"],
                "name": test_case["name"],
                "status": "error",
                "http_status": response.status_code,
                "error": response.text[:200]
            }

    except Exception as e:
        return {
            "id": test_case["id"],
            "name": test_case["name"],
            "status": "exception",
            "error": str(e)
        }

async def run_edge_tests():
    """執行所有邊界測試"""
    print("=" * 80)
    print("邊界情況和異常處理測試")
    print("=" * 80)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"測試案例數: {len(EDGE_TEST_CASES)}")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # 執行所有測試
        for test_case in EDGE_TEST_CASES:
            print(f"\n[{test_case['id']}/{len(EDGE_TEST_CASES)}] {test_case['name']}")
            result = await test_edge_case(client, test_case)
            results.append(result)

            # 顯示結果
            if result["status"] == "success":
                action_type_status = "✅" if result.get("has_action_type") else "❌"
                print(f"  ✅ 處理成功")
                print(f"  {action_type_status} action_type: {result['action_type']}")
                print(f"     answer_length: {result['answer_length']}")
            elif result["status"] == "expected_fail":
                print(f"  ✅ 預期失敗 (HTTP {result['http_status']})")
            elif result["status"] == "error":
                print(f"  ⚠️  HTTP 錯誤: {result.get('http_status')}")
            else:
                print(f"  ❌ 異常: {result.get('error', 'Unknown')[:100]}")

    # 統計結果
    print("\n" + "=" * 80)
    print("測試結果統計")
    print("=" * 80)

    total = len(results)
    success = len([r for r in results if r["status"] == "success"])
    expected_fail = len([r for r in results if r["status"] == "expected_fail"])
    error = len([r for r in results if r["status"] == "error"])
    exception = len([r for r in results if r["status"] == "exception"])

    print(f"\n📊 基本統計:")
    print(f"  總測試數: {total}")
    print(f"  成功處理: {success} ({success/total*100:.1f}%)")
    print(f"  預期失敗: {expected_fail} ({expected_fail/total*100:.1f}%)")
    print(f"  錯誤: {error} ({error/total*100:.1f}%)")
    print(f"  異常: {exception} ({exception/total*100:.1f}%)")

    # action_type 檢查
    success_results = [r for r in results if r["status"] == "success"]
    if success_results:
        has_action_type = len([r for r in success_results if r.get("has_action_type")])
        print(f"\n✅ action_type 驗證:")
        print(f"  包含 action_type: {has_action_type}/{len(success_results)} ({has_action_type/len(success_results)*100:.1f}%)")

    # 問題案例
    problem_cases = [r for r in results if r["status"] == "error" or r["status"] == "exception"]
    if problem_cases:
        print(f"\n⚠️  問題案例 ({len(problem_cases)} 個):")
        for p in problem_cases:
            print(f"  - [{p['id']}] {p['name']}")
            print(f"    狀態: {p['status']}")
            if 'error' in p:
                print(f"    錯誤: {p['error'][:100]}")
    else:
        print(f"\n✅ 無問題案例")

    # 保存結果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"edge_case_test_results_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "success": success,
            "expected_fail": expected_fail,
            "error": error,
            "exception": exception,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 結果已儲存: {output_file}")
    print("\n" + "=" * 80)
    print("✅ 邊界測試完成！")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_edge_tests())
