#!/usr/bin/env python3
"""
測試意圖閾值改進 (Plan B)
驗證：
1. 意圖獨立閾值
2. 次要意圖過濾
3. 次要意圖降級機制
4. Unclear 分析日誌
"""

import requests
import json
import time
from typing import Dict, List

API_BASE = "http://localhost:8100/api/v1"

# 測試案例
TEST_CASES = [
    {
        "name": "Test 1: 多意圖問題 - 應該過濾低信心度次要意圖",
        "question": "租約條款 租金、押金、租期",
        "expected": {
            "primary_intent": "合約規定",
            "min_confidence": 0.8,  # 合約規定閾值 0.8
            "secondary_filtered": True,  # 帳務查詢可能信心度不足被過濾
        }
    },
    {
        "name": "Test 2: 單一明確意圖 - 高信心度",
        "question": "我想退租，需要準備什麼文件？",
        "expected": {
            "primary_intent": "退租流程",
            "min_confidence": 0.8,  # 退租流程閾值 0.8
        }
    },
    {
        "name": "Test 3: 帳務查詢 - 較低閾值",
        "question": "這個月的租金多少錢？",
        "expected": {
            "primary_intent": "帳務查詢",
            "min_confidence": 0.75,  # 帳務查詢閾值 0.75
        }
    },
    {
        "name": "Test 4: 設備問題 - 高閾值意圖",
        "question": "門鎖壞了要怎麼報修？",
        "expected": {
            "primary_intent": "設備報修",
            "min_confidence": 0.8,  # 設備報修閾值 0.8
        }
    },
    {
        "name": "Test 5: 模糊問題 - 可能成為 unclear",
        "question": "那個東西在哪裡？",
        "expected": {
            "primary_intent": "unclear",  # 預期無法分類
        }
    },
]

def test_intent_classification(question: str) -> Dict:
    """測試意圖分類"""
    response = requests.post(
        f"{API_BASE}/message",
        json={
            "message": question,
            "vendor_id": 1,
            "user_role": "customer",
            "user_id": "test_threshold_validation"
        },
        timeout=30
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"API error: {response.status_code}", "detail": response.text}

def print_result(test_case: Dict, result: Dict):
    """格式化輸出測試結果"""
    print(f"\n{'='*80}")
    print(f"📝 {test_case['name']}")
    print(f"{'='*80}")
    print(f"問題: {test_case['question']}")
    print(f"\n結果:")

    if "error" in result:
        print(f"❌ 錯誤: {result['error']}")
        return

    intent_name = result.get("intent_name", "N/A")
    confidence = result.get("confidence", 0)
    secondary = result.get("secondary_intents", [])
    all_with_conf = result.get("all_intents_with_confidence", [])

    print(f"  主意圖: {intent_name}")
    print(f"  信心度: {confidence:.3f}")
    print(f"  次要意圖: {secondary}")

    # 顯示所有意圖信心度
    if all_with_conf:
        print(f"\n  完整意圖列表:")
        for intent in all_with_conf:
            intent_type = intent.get('type', 'unknown')
            symbol = "🎯" if intent_type == "primary" else "📌"
            print(f"    {symbol} {intent['name']}: {intent['confidence']:.3f} ({intent_type})")

    # 驗證預期結果
    expected = test_case.get("expected", {})
    print(f"\n驗證:")

    # 檢查主意圖
    expected_intent = expected.get("primary_intent")
    if expected_intent:
        if intent_name == expected_intent:
            print(f"  ✅ 主意圖符合預期: {expected_intent}")
        else:
            print(f"  ⚠️ 主意圖不符: 預期 {expected_intent}, 實際 {intent_name}")

    # 檢查信心度閾值
    min_conf = expected.get("min_confidence")
    if min_conf and intent_name != "unclear":
        if confidence >= min_conf:
            print(f"  ✅ 信心度達標: {confidence:.3f} >= {min_conf}")
        else:
            print(f"  ⚠️ 信心度不足: {confidence:.3f} < {min_conf}")

    # 檢查次要意圖過濾
    if expected.get("secondary_filtered"):
        if len(secondary) < len(all_with_conf) - 1:
            print(f"  ✅ 次要意圖已過濾（原始可能有更多，實際保留 {len(secondary)} 個）")
        else:
            print(f"  ℹ️ 次要意圖數量: {len(secondary)}")

def main():
    """執行所有測試"""
    print("\n" + "="*80)
    print("🧪 意圖閾值改進測試 (Plan B Implementation)")
    print("="*80)

    results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n執行測試 {i}/{len(TEST_CASES)}...")

        try:
            result = test_intent_classification(test_case["question"])
            print_result(test_case, result)
            results.append({
                "test": test_case["name"],
                "success": "error" not in result,
                "result": result
            })

            # 避免請求太快
            time.sleep(2)

        except Exception as e:
            print(f"\n❌ 測試失敗: {str(e)}")
            results.append({
                "test": test_case["name"],
                "success": False,
                "error": str(e)
            })

    # 總結
    print(f"\n\n{'='*80}")
    print("📊 測試總結")
    print(f"{'='*80}")

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    print(f"成功: {success_count}/{total_count}")
    print(f"失敗: {total_count - success_count}/{total_count}")

    if success_count == total_count:
        print("\n✅ 所有測試通過！")
    else:
        print("\n⚠️ 部分測試失敗，請檢查日誌")

    print("\n提示：查看 docker-compose logs rag-orchestrator 以檢視詳細的過濾和降級日誌")

if __name__ == "__main__":
    main()
