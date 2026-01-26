#!/usr/bin/env python3
"""
測試 Vendor SOP 檢索涵蓋率
模擬常見租客問題，檢查是否能正確檢索到相關 SOP
"""

import requests
import json
import time
from typing import Dict, List
import uuid

# API 設定
API_URL = "http://localhost:8100/api/v1/message"
VENDOR_ID = 2

# 測試結果統計
results = {
    "total": 0,
    "success": 0,  # 有找到 SOP
    "failed": 0,   # 沒找到 SOP
    "error": 0,    # API 錯誤
    "details": []
}

def test_question(category: str, question: str, session_id: str) -> Dict:
    """測試單一問題"""
    payload = {
        "vendor_id": VENDOR_ID,
        "message": question,
        "session_id": session_id,
        "user_id": f"test_user_{int(time.time())}"
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 檢查是否找到 SOP
        has_sources = data.get("sources") is not None and len(data.get("sources", [])) > 0
        source_count = data.get("source_count", 0)

        # 提取 SOP 資訊
        sop_info = []
        if has_sources:
            for src in data.get("sources", []):
                sop_info.append({
                    "id": src.get("id", 0),
                    "item_name": src.get("question_summary", ""),
                    "scope": src.get("scope", ""),
                    "similarity": src.get("similarity", 0)
                })

        result = {
            "category": category,
            "question": question,
            "status": "success" if has_sources else "failed",
            "source_count": source_count,
            "sop_info": sop_info,
            "answer_preview": data.get("answer", "")[:100] + "..."
        }

        return result

    except Exception as e:
        return {
            "category": category,
            "question": question,
            "status": "error",
            "error": str(e)
        }

def main():
    """執行測試"""
    print("=" * 80)
    print("🧪 Vendor SOP 檢索涵蓋率測試")
    print("=" * 80)
    print()

    # 載入測試問題
    with open('test_tenant_questions.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # 為每次測試生成唯一 session_id
    session_id = str(uuid.uuid4())

    # 執行測試
    for test_case in test_data['test_cases']:
        category = test_case['category']
        questions = test_case['questions']

        print(f"\n📂 類別: {category}")
        print("-" * 80)

        for question in questions:
            results['total'] += 1
            print(f"\n❓ 問題 {results['total']}: {question}")

            # 測試問題
            result = test_question(category, question, session_id)
            results['details'].append(result)

            # 顯示結果
            if result['status'] == 'success':
                results['success'] += 1
                print(f"   ✅ 找到 {result['source_count']} 個相關 SOP")
                for sop in result['sop_info']:
                    print(f"      - [ID {sop['id']}] {sop['item_name']}")
            elif result['status'] == 'failed':
                results['failed'] += 1
                print(f"   ❌ 未找到相關 SOP")
                print(f"      回答: {result['answer_preview']}")
            else:
                results['error'] += 1
                print(f"   ⚠️  API 錯誤: {result.get('error', 'Unknown')}")

            # 避免請求過快
            time.sleep(0.5)

    # 顯示統計結果
    print("\n" + "=" * 80)
    print("📊 測試結果統計")
    print("=" * 80)
    print(f"總測試問題數: {results['total']}")
    print(f"✅ 成功檢索: {results['success']} ({results['success']/results['total']*100:.1f}%)")
    print(f"❌ 未找到 SOP: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print(f"⚠️  API 錯誤: {results['error']} ({results['error']/results['total']*100:.1f}%)")

    # 分析未找到 SOP 的問題
    if results['failed'] > 0:
        print("\n" + "=" * 80)
        print("❌ 未涵蓋的問題清單")
        print("=" * 80)
        for detail in results['details']:
            if detail['status'] == 'failed':
                print(f"• [{detail['category']}] {detail['question']}")

    # 儲存詳細結果
    with open('test_sop_coverage_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📄 詳細結果已儲存至: test_sop_coverage_results.json")
    print()

if __name__ == "__main__":
    main()
