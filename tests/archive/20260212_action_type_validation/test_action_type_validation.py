#!/usr/bin/env python3
"""
action_type 完整驗證測試腳本
測試所有 action_type 相關功能
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List

# API 配置
API_BASE_URL = "http://localhost:8100"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/message"

# 測試案例：覆蓋所有 action_type 場景
TEST_CASES = [
    # 1. direct_answer - 一般知識查詢
    {
        "id": 1,
        "name": "direct_answer - 基本查詢",
        "message": "客服專線是多少",
        "expected_action_type": "direct_answer",
        "expected_source_count": ">0",
        "description": "測試一般知識查詢返回 direct_answer"
    },
    {
        "id": 2,
        "name": "direct_answer - 電費查詢",
        "message": "電費寄送區間查詢",
        "expected_action_type": "direct_answer",
        "expected_source_count": ">0",
        "description": "測試電費相關查詢"
    },

    # 2. direct_answer - 無知識 fallback
    {
        "id": 3,
        "name": "direct_answer - 無相關知識",
        "message": "今天天氣如何",
        "expected_action_type": "direct_answer",
        "expected_source_count": "0",
        "description": "測試無相關知識時的 fallback"
    },
    {
        "id": 4,
        "name": "direct_answer - 不相關問題",
        "message": "123456",
        "expected_action_type": "direct_answer",
        "expected_source_count": "0",
        "description": "測試無意義輸入"
    },

    # 3. form_fill - 表單相關（如果有的話）
    {
        "id": 5,
        "name": "可能的 form_fill",
        "message": "我想報修",
        "expected_action_type": "direct_answer,form_fill",  # 兩者都可能
        "expected_source_count": ">=0",
        "description": "測試可能觸發表單的問題"
    },

    # 4. api_call - API 查詢（如果有的話）
    {
        "id": 6,
        "name": "可能的 api_call",
        "message": "查詢我的帳單",
        "expected_action_type": "direct_answer,api_call",  # 兩者都可能
        "expected_source_count": ">=0",
        "description": "測試可能觸發 API 的問題"
    },
]

# 測試結果
results = []

async def test_single_case(client: httpx.AsyncClient, test_case: Dict) -> Dict:
    """測試單個案例"""
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

            # 檢查 action_type
            action_type = data.get("action_type")
            expected_types = test_case["expected_action_type"].split(",")
            action_type_match = action_type in expected_types

            # 檢查 source_count
            source_count = data.get("source_count", 0)
            expected_count = test_case["expected_source_count"]

            if expected_count == ">0":
                count_match = source_count > 0
            elif expected_count == "0":
                count_match = source_count == 0
            elif expected_count == ">=0":
                count_match = source_count >= 0
            else:
                count_match = True

            return {
                "id": test_case["id"],
                "name": test_case["name"],
                "status": "success",
                "action_type": action_type,
                "action_type_match": action_type_match,
                "source_count": source_count,
                "source_count_match": count_match,
                "intent_name": data.get("intent_name"),
                "intent_type": data.get("intent_type"),
                "confidence": data.get("confidence"),
                "has_sources": len(data.get("sources", [])) > 0 if data.get("sources") else False,
                "answer_length": len(data.get("answer", "")),
                "raw_response": data
            }
        else:
            return {
                "id": test_case["id"],
                "name": test_case["name"],
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "response": response.text
            }

    except Exception as e:
        return {
            "id": test_case["id"],
            "name": test_case["name"],
            "status": "error",
            "error": str(e)
        }

async def run_tests():
    """執行所有測試"""
    print("=" * 80)
    print("action_type 完整驗證測試")
    print("=" * 80)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"測試案例數: {len(TEST_CASES)}")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # 執行所有測試
        for test_case in TEST_CASES:
            print(f"\n[{test_case['id']}/{len(TEST_CASES)}] {test_case['name']}")
            result = await test_single_case(client, test_case)
            results.append(result)

            # 顯示結果
            if result["status"] == "success":
                status = "✅" if result.get("action_type_match") else "⚠️"
                print(f"  {status} action_type: {result['action_type']} (期望: {test_case['expected_action_type']})")
                print(f"     source_count: {result['source_count']} (期望: {test_case['expected_source_count']})")
                print(f"     intent: {result.get('intent_name')} ({result.get('intent_type')})")
            else:
                print(f"  ❌ 錯誤: {result['error']}")

    # 統計結果
    print("\n" + "=" * 80)
    print("測試結果統計")
    print("=" * 80)

    total = len(results)
    success = len([r for r in results if r["status"] == "success"])
    error = total - success

    action_type_match = len([r for r in results if r.get("action_type_match")])
    source_count_match = len([r for r in results if r.get("source_count_match")])

    print(f"\n📊 基本統計:")
    print(f"  總測試數: {total}")
    print(f"  成功: {success} ({success/total*100:.1f}%)")
    print(f"  失敗: {error} ({error/total*100:.1f}%)")

    if success > 0:
        print(f"\n✅ 驗證結果:")
        print(f"  action_type 符合: {action_type_match}/{success} ({action_type_match/success*100:.1f}%)")
        print(f"  source_count 符合: {source_count_match}/{success} ({source_count_match/success*100:.1f}%)")

    # action_type 分布
    action_types = {}
    for r in results:
        if r["status"] == "success":
            at = r.get("action_type")
            action_types[at] = action_types.get(at, 0) + 1

    print(f"\n📈 action_type 分布:")
    for at, count in sorted(action_types.items(), key=lambda x: -x[1]):
        at_str = str(at) if at is not None else "None"
        print(f"  {at_str:20s}: {count:3d} ({count/success*100:.1f}%)")

    # 問題案例
    print(f"\n⚠️  問題案例:")
    problems = [r for r in results if r["status"] == "success" and not r.get("action_type_match")]
    if problems:
        for p in problems:
            print(f"  - [{p['id']}] {p['name']}")
            print(f"    期望: {p.get('expected')}, 實際: {p.get('action_type')}")
    else:
        print("  無問題案例 ✅")

    # 保存結果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"action_type_test_results_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "success": success,
            "error": error,
            "action_type_distribution": action_types,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 結果已儲存: {output_file}")
    print("\n" + "=" * 80)
    print("✅ 測試完成！")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_tests())
