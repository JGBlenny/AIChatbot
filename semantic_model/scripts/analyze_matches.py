#!/usr/bin/env python3
"""
分析每個查詢實際匹配到什麼內容
"""

import json
from sentence_transformers import CrossEncoder

def analyze_what_matched():
    print("="*80)
    print("分析：每個查詢實際匹配到什麼")
    print("="*80)

    # 載入模型
    print("\n載入模型...")
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)

    # 載入知識庫
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)

    # 測試查詢
    test_queries = [
        "電費帳單寄送區間",
        "電費寄送區間",
        "電費幾號寄",
        "我要報修",  # 對照組
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"查詢: 「{query}」")
        print("="*80)

        # 對前50個知識點評分
        test_kb = knowledge_base[:50]
        pairs = [[query, kb['content']] for kb in test_kb]
        scores = model.predict(pairs)

        # 找出前3名
        top_indices = scores.argsort()[-3:][::-1]

        print("\n🔍 系統找到的前3個匹配：\n")
        for rank, idx in enumerate(top_indices, 1):
            kb = test_kb[idx]
            score = scores[idx]

            print(f"第{rank}名 (分數: {score:.3f})")
            print(f"├─ ID: {kb['id']}")
            print(f"├─ 標題: {kb['title'][:60]}...")
            print(f"├─ 內容預覽: {kb['content'][:100]}...")
            print(f"├─ 表單ID: {kb.get('form_id', '❌ 無表單')}")
            print(f"├─ 動作類型: {kb.get('action_type', 'direct_answer')}")

            # 分析為什麼會匹配
            content_lower = kb['content'].lower()
            title_lower = kb['title'].lower()
            matched_keywords = []

            if '電費' in content_lower or '電費' in title_lower:
                matched_keywords.append('電費')
            if '帳單' in content_lower or '帳單' in title_lower:
                matched_keywords.append('帳單')
            if '寄送' in content_lower or '寄送' in title_lower:
                matched_keywords.append('寄送')
            if '報修' in content_lower or '報修' in title_lower:
                matched_keywords.append('報修')

            print(f"└─ 匹配關鍵字: {matched_keywords if matched_keywords else '❌ 無明顯關鍵字匹配'}")
            print()

        # 檢查是否有表單1296
        print(f"⚠️  檢查：這些匹配中有表單1296嗎？")
        has_1296 = any(test_kb[idx].get('form_id') == 1296 for idx in top_indices)
        if has_1296:
            print(f"✅ 有！會正確觸發表單")
        else:
            print(f"❌ 沒有！不會觸發表單1296")

    # 專門搜尋表單1296
    print("\n" + "="*80)
    print("🔎 搜尋：知識庫中有表單1296嗎？")
    print("="*80)

    form_1296_found = False
    for kb in knowledge_base:
        if kb.get('form_id') == 1296:
            form_1296_found = True
            print(f"\n✅ 找到表單1296！")
            print(f"  ID: {kb['id']}")
            print(f"  標題: {kb['title']}")
            print(f"  內容: {kb['content'][:200]}...")
            break

    if not form_1296_found:
        print("\n❌ 整個知識庫都沒有表單1296的設定！")
        print("   這就是為什麼所有查詢都無法觸發表單的原因")

    # 分析ID 17的內容（最常被匹配到的）
    print("\n" + "="*80)
    print("📝 詳細分析：最常匹配到的 ID 17")
    print("="*80)

    id_17 = next((kb for kb in knowledge_base if kb['id'] == 17), None)
    if id_17:
        print(f"\nID 17 完整資訊：")
        print(f"標題: {id_17['title']}")
        print(f"內容: {id_17['content'][:300]}...")
        print(f"表單: {id_17.get('form_id', '無')}")
        print(f"動作: {id_17.get('action_type', 'direct_answer')}")
        print(f"\n為什麼會匹配？")
        print(f"→ 包含「電費」關鍵字: {'是' if '電費' in id_17['content'] else '否'}")
        print(f"→ 包含「儲值」關鍵字: {'是' if '儲值' in id_17['content'] else '否'}")
        print(f"→ 但沒有設定要觸發表單1296")

if __name__ == "__main__":
    analyze_what_matched()