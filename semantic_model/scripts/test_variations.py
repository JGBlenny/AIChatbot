#!/usr/bin/env python3
"""
測試「帳單寄送區間」的各種變化型
"""

import json
from sentence_transformers import CrossEncoder
import time

def test_billing_variations():
    print("="*70)
    print("測試「帳單寄送區間」變化型匹配")
    print("="*70)

    # 載入模型
    print("\n載入語義模型...")
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)

    # 載入知識庫
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)

    # 測試變化型
    test_queries = [
        # 應該成功的
        "電費帳單寄送區間",
        "電費寄送區間",
        "查詢電費寄送區間",

        # 其他變化
        "電費帳單寄送",
        "電費帳單發送",
        "電費單寄送時間",
        "電費幾號寄",
        "何時寄電費帳單",
        "單月電費寄送",
        "雙月電費寄送",
    ]

    # 先找出所有包含表單1296的知識點
    print("\n尋找表單 ID 1296 的知識點...")
    form_1296_kb = []
    for kb in knowledge_base:
        if kb.get('form_id') == 1296:
            form_1296_kb.append(kb)
            print(f"  找到: ID {kb['id']} - {kb['title'][:50]}...")

    if not form_1296_kb:
        print("  ⚠️ 警告：知識庫中沒有表單 ID 1296 的知識點！")
        print("\n這是問題根源：知識庫需要新增或修正表單 1296 的對應")

    # 找出電費相關知識點
    print("\n尋找電費相關知識點...")
    electricity_kb = []
    for kb in knowledge_base:
        content_lower = (kb.get('content', '') + kb.get('title', '')).lower()
        if '電費' in content_lower or '電' in content_lower:
            electricity_kb.append(kb)

    print(f"  找到 {len(electricity_kb)} 個電費相關知識點")

    # 測試每個查詢
    print("\n開始測試各種變化型...")
    print("-"*70)

    results = []
    for query in test_queries:
        print(f"\n測試: {query}")

        # 對前20個知識點評分
        test_kb = knowledge_base[:50]  # 測試前50個
        pairs = [[query, kb['content']] for kb in test_kb]
        scores = model.predict(pairs)

        # 找出最高分
        best_idx = scores.argmax()
        best_kb = test_kb[best_idx]
        best_score = scores[best_idx]

        print(f"  最高分: ID {best_kb['id']} (分數: {best_score:.3f})")
        print(f"  標題: {best_kb['title'][:50]}...")
        print(f"  表單: {best_kb.get('form_id', 'None')}")

        # 判斷是否正確
        if best_kb.get('form_id') == 1296:
            print(f"  ✅ 正確匹配到表單 1296")
            status = "成功"
        elif best_kb.get('form_id'):
            print(f"  ⚠️ 錯誤：匹配到表單 {best_kb.get('form_id')}")
            status = "錯誤表單"
        else:
            print(f"  ❌ 失敗：沒有匹配到任何表單")
            status = "無表單"

        results.append({
            'query': query,
            'matched_id': best_kb['id'],
            'score': best_score,
            'form_id': best_kb.get('form_id'),
            'status': status
        })

    # 統計結果
    print("\n" + "="*70)
    print("測試結果統計")
    print("="*70)

    success_count = sum(1 for r in results if r['status'] == '成功')
    error_form = sum(1 for r in results if r['status'] == '錯誤表單')
    no_form = sum(1 for r in results if r['status'] == '無表單')

    print(f"\n總測試數: {len(results)}")
    print(f"✅ 成功: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"⚠️ 錯誤表單: {error_form} ({error_form/len(results)*100:.1f}%)")
    print(f"❌ 無表單: {no_form} ({no_form/len(results)*100:.1f}%)")

    # 解決方案
    print("\n" + "="*70)
    print("💡 解決方案")
    print("="*70)

    if success_count < len(results) * 0.5:  # 成功率低於50%
        print("\n問題診斷：")
        print("1. 知識庫中可能缺少表單 1296 的正確對應")
        print("2. 知識點的 content 可能沒有包含足夠的關鍵字")

        print("\n建議解決步驟：")
        print("1. 立即執行：")
        print("   UPDATE knowledge_base")
        print("   SET form_id = 1296")
        print("   WHERE question_summary LIKE '%電費%' ")
        print("     AND (question_summary LIKE '%寄送%' OR question_summary LIKE '%帳單%');")

        print("\n2. 新增知識點：")
        print("   INSERT INTO knowledge_base (question_summary, answer, form_id, action_type)")
        print("   VALUES ('電費帳單寄送區間查詢', '請填寫表單查詢...', 1296, 'form_fill');")

        print("\n3. 確保知識點包含所有變化關鍵字：")
        print("   - 電費、帳單、寄送、區間")
        print("   - 單月、雙月、週期")
        print("   - 查詢、何時、幾號")

    return results

if __name__ == "__main__":
    results = test_billing_variations()