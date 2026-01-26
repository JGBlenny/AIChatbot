#!/usr/bin/env python3
"""測試 SOP 檢索功能"""

import asyncio
import httpx

API_URL = "http://localhost:8100"
VENDOR_ID = 2

# 測試查詢與預期匹配的 SOP
TEST_QUERIES = [
    {
        "query": "租金怎麼繳？",
        "expected_sop": "【測試】租金繳納說明",
        "expected_mode": "none",
        "expected_action": "none",
        "description": "資訊型查詢"
    },
    {
        "query": "網路連不上",
        "expected_sop": "【測試】網路不通排查",
        "expected_mode": "manual",
        "expected_action": "form_fill",
        "expected_keywords": ["還是不行", "試過了", "沒用"],
        "description": "排查型 + 表單"
    },
    {
        "query": "門鎖壞了",
        "expected_sop": "【測試】門鎖故障緊急",
        "expected_mode": "immediate",
        "expected_action": "form_fill",
        "expected_prompt": "這是緊急維修狀況",
        "description": "行動型 + 表單"
    },
    {
        "query": "熱水器沒熱水",
        "expected_sop": "【測試】熱水器沒熱水",
        "expected_mode": "manual",
        "expected_action": "none",
        "description": "排查型 + 無表單"
    },
    {
        "query": "查繳費記錄",
        "expected_sop": "【測試】查詢繳費記錄",
        "expected_mode": "immediate",
        "expected_action": "none",
        "expected_prompt": "需要我幫您查詢",
        "description": "行動型 + 無表單"
    },
    {
        "query": "健身房怎麼用",
        "expected_sop": "【測試】公設使用規定",
        "expected_mode": "none",
        "expected_action": "none",
        "description": "資訊型查詢"
    }
]


async def test_retrieval():
    """測試 SOP 檢索"""

    print("=" * 100)
    print("🧪 測試 SOP 檢索功能")
    print("=" * 100)
    print(f"\n📊 總共 {len(TEST_QUERIES)} 個測試查詢\n")

    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, test in enumerate(TEST_QUERIES, 1):
            print(f"\n{'='*80}")
            print(f"🔍 測試 [{i}/{len(TEST_QUERIES)}]: {test['description']}")
            print(f"{'='*80}")
            print(f"  問題: {test['query']}")
            print(f"  預期 SOP: {test['expected_sop']}")
            print(f"  預期模式: {test['expected_mode']} + {test['expected_action']}")

            try:
                # 模擬對話請求（實際會經過 intent 識別和 SOP 檢索）
                response = await client.post(
                    f"{API_URL}/api/v1/chat",
                    json={
                        "question": test['query'],
                        "vendor_id": VENDOR_ID,
                        "user_role": "customer",
                        "user_id": f"test_user_{i}"
                    },
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get('answer', '')

                    # 檢查是否匹配預期 SOP
                    sop_matched = test['expected_sop'] in answer or test['expected_sop'].replace('【測試】', '') in answer

                    result = {
                        'test': test['description'],
                        'query': test['query'],
                        'expected': test['expected_sop'],
                        'matched': sop_matched,
                        'answer_preview': answer[:200] + '...' if len(answer) > 200 else answer
                    }

                    if sop_matched:
                        print(f"\n  ✅ 檢索成功！")
                        print(f"  📝 回應預覽: {result['answer_preview'][:100]}...")

                        # 檢查流程配置提示
                        if test['expected_mode'] == 'immediate':
                            if 'expected_prompt' in test and test['expected_prompt'] in answer:
                                print(f"  ✅ immediate 提示詞正確: 「{test['expected_prompt']}」")
                            else:
                                print(f"  ⚠️  未找到 immediate 提示詞")

                        if test['expected_mode'] == 'manual':
                            if 'expected_keywords' in test:
                                print(f"  📌 觸發關鍵詞: {', '.join(test['expected_keywords'])}")

                        result['status'] = 'PASS'
                    else:
                        print(f"\n  ❌ 檢索失敗！")
                        print(f"  📝 實際回應: {answer[:200]}...")
                        result['status'] = 'FAIL'

                    results.append(result)

                else:
                    print(f"\n  ❌ API 錯誤: {response.status_code}")
                    print(f"  錯誤訊息: {response.text[:200]}")
                    results.append({
                        'test': test['description'],
                        'query': test['query'],
                        'expected': test['expected_sop'],
                        'matched': False,
                        'status': 'ERROR',
                        'error': response.text[:200]
                    })

            except Exception as e:
                print(f"\n  ❌ 測試失敗: {e}")
                results.append({
                    'test': test['description'],
                    'query': test['query'],
                    'expected': test['expected_sop'],
                    'matched': False,
                    'status': 'ERROR',
                    'error': str(e)
                })

    # 輸出測試結果摘要
    print(f"\n\n{'='*100}")
    print("📊 測試結果摘要")
    print(f"{'='*100}\n")

    passed = sum(1 for r in results if r.get('status') == 'PASS')
    failed = sum(1 for r in results if r.get('status') == 'FAIL')
    errors = sum(1 for r in results if r.get('status') == 'ERROR')

    print(f"✅ 通過: {passed}/{len(results)}")
    print(f"❌ 失敗: {failed}/{len(results)}")
    print(f"⚠️  錯誤: {errors}/{len(results)}")

    success_rate = (passed / len(results)) * 100 if results else 0
    print(f"\n📈 成功率: {success_rate:.1f}%")

    if failed > 0 or errors > 0:
        print(f"\n\n❌ **失敗的測試**：\n")
        for r in results:
            if r.get('status') in ['FAIL', 'ERROR']:
                print(f"  • {r['test']}: {r['query']}")
                print(f"    預期: {r['expected']}")
                if 'error' in r:
                    print(f"    錯誤: {r['error'][:100]}")
                print()

    print(f"\n{'='*100}")
    print("📖 詳細測試對話請參考: test_sop_scenarios_dialogue.md")
    print(f"{'='*100}\n")

    return results


if __name__ == "__main__":
    asyncio.run(test_retrieval())
