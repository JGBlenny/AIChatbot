#!/usr/bin/env python3
"""
調試：為什麼會匹配到不相關的內容
"""

import json
from sentence_transformers import CrossEncoder

def debug_why_wrong_matches():
    print("="*80)
    print("調試：為什麼匹配到錯誤內容")
    print("="*80)

    # 載入模型
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)

    # 載入知識庫
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)

    query = "電費帳單寄送區間"

    # 問題1: 只測試前50個可能錯過真正相關的
    print("\n🔍 問題1: 測試範圍是否太小？")
    print("-" * 40)

    # 擴大範圍測試所有知識點中的電費相關
    electricity_related = []
    for kb in knowledge_base:
        content = (kb.get('content', '') + kb.get('title', '')).lower()
        if '電費' in content or '電' in content or '帳單' in content:
            electricity_related.append(kb)

    print(f"找到 {len(electricity_related)} 個可能相關的知識點")

    if electricity_related:
        # 測試前10個電費相關
        test_kb = electricity_related[:10]
        pairs = [[query, kb['content']] for kb in test_kb]
        scores = model.predict(pairs)

        print("\n電費相關知識點的分數：")
        for kb, score in zip(test_kb, scores):
            print(f"  ID {kb['id']:4d} (分數: {score:.3f}): {kb['title'][:40]}...")

    # 問題2: 為什麼ID 43會得高分？
    print("\n🔍 問題2: 為什麼 ID 43 會得高分？")
    print("-" * 40)

    id_43 = next((kb for kb in knowledge_base if kb['id'] == 43), None)
    if id_43:
        print(f"ID 43 內容：")
        print(f"標題: {id_43['title']}")
        print(f"內容: {id_43['content']}")

        # 測試不同查詢對ID 43的分數
        test_queries = [
            "電費帳單寄送區間",
            "如何避免干擾",
            "同事操作",
            "隨便的查詢"
        ]

        print("\n不同查詢對 ID 43 的分數：")
        for q in test_queries:
            score = model.predict([[q, id_43['content']]])[0]
            print(f"  '{q}': {score:.3f}")

    # 問題3: 模型是否對中文理解有問題？
    print("\n🔍 問題3: 測試模型的中文理解")
    print("-" * 40)

    # 創建明顯相關的測試內容
    test_contents = [
        "電費帳單會在每個月的單月或雙月寄送，具體寄送區間依據您的用電地址。",  # 高度相關
        "關於電費帳單的寄送時間和區間查詢，請填寫表單。",  # 相關
        "租金繳費期限是每月5號。",  # 不相關
        "如何避免同事操作時互相干擾資料？建議分配不同範圍。",  # ID 43的內容
    ]

    print("測試明顯相關內容的分數：")
    for content in test_contents:
        score = model.predict([[query, content]])[0]
        print(f"  分數 {score:.3f}: {content[:50]}...")

    # 問題4: 檢查是否有更好的匹配在後面
    print("\n🔍 問題4: 完整掃描所有1274個知識點")
    print("-" * 40)

    # 測試所有知識點
    all_pairs = [[query, kb['content']] for kb in knowledge_base]

    print("正在評分所有知識點（可能需要幾分鐘）...")

    # 分批處理
    batch_size = 100
    all_scores = []
    for i in range(0, len(knowledge_base), batch_size):
        batch = knowledge_base[i:i+batch_size]
        batch_pairs = [[query, kb['content']] for kb in batch]
        batch_scores = model.predict(batch_pairs)
        all_scores.extend(batch_scores)
        print(f"  已處理 {min(i+batch_size, len(knowledge_base))}/{len(knowledge_base)}")

    # 找出前10名
    top_10_indices = sorted(range(len(all_scores)), key=lambda i: all_scores[i], reverse=True)[:10]

    print("\n全知識庫前10名匹配：")
    for rank, idx in enumerate(top_10_indices, 1):
        kb = knowledge_base[idx]
        score = all_scores[idx]
        print(f"\n第{rank}名 - ID {kb['id']} (分數: {score:.3f})")
        print(f"  標題: {kb['title'][:60]}...")
        print(f"  內容: {kb['content'][:100]}...")
        print(f"  表單: {kb.get('form_id', 'None')}")

        # 分析為什麼會匹配
        if '電費' in kb['content'] or '電費' in kb['title']:
            print(f"  ✓ 包含「電費」")
        if '帳單' in kb['content'] or '帳單' in kb['title']:
            print(f"  ✓ 包含「帳單」")
        if '寄送' in kb['content'] or '寄送' in kb['title']:
            print(f"  ✓ 包含「寄送」")

    # 結論
    print("\n" + "="*80)
    print("💡 診斷結論")
    print("="*80)

    if all_scores[top_10_indices[0]] < 0.5:
        print("1. 分數都很低（< 0.5），表示知識庫確實缺少相關內容")

    if '電費' not in knowledge_base[top_10_indices[0]]['content']:
        print("2. 最高分的內容甚至不包含「電費」，模型可能有問題")

    print("\n可能原因：")
    print("- 知識庫缺少電費帳單寄送的專門內容")
    print("- 預訓練模型對這類專業查詢理解不佳")
    print("- 需要新增專門的知識點或進行模型微調")

if __name__ == "__main__":
    debug_why_wrong_matches()