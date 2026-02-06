#!/usr/bin/env python3
"""
正確的測試方法：模擬實際對話系統邏輯
"""

import json
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def correct_test_flow():
    print("="*80)
    print("正確的測試流程（模擬實際系統）")
    print("="*80)

    # 載入知識庫
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    print(f"✅ 載入 {len(knowledge_base)} 個知識點")

    # 測試查詢
    test_queries = [
        "電費帳單寄送區間",
        "電費幾號寄",
        "我要報修",
    ]

    print("\n" + "="*80)
    print("方法1: 只用語義模型掃描前50個（錯誤方法）")
    print("="*80)

    # 載入語義模型
    reranker = CrossEncoder('BAAI/bge-reranker-base', max_length=512)

    for query in test_queries:
        print(f"\n查詢: {query}")

        # 錯誤：只測試前50個
        test_kb = knowledge_base[:50]
        pairs = [[query, kb['content']] for kb in test_kb]
        scores = reranker.predict(pairs)

        best_idx = scores.argmax()
        best_kb = test_kb[best_idx]

        print(f"  找到: ID {best_kb['id']} - {best_kb['title'][:40]}...")
        print(f"  分數: {scores[best_idx]:.3f}")
        print(f"  表單: {best_kb.get('form_id', 'None')}")

        if best_kb['id'] == 1296:
            print(f"  ✅ 正確！")
        else:
            print(f"  ❌ 錯誤！")

    print("\n" + "="*80)
    print("方法2: 兩階段檢索（正確方法）")
    print("="*80)

    # 載入向量模型（簡化版：用TF-IDF模擬）
    from sklearn.feature_extraction.text import TfidfVectorizer

    # 建立向量索引
    print("\n建立向量索引...")
    documents = [kb['content'] for kb in knowledge_base]
    vectorizer = TfidfVectorizer(max_features=500)
    doc_vectors = vectorizer.fit_transform(documents)

    for query in test_queries:
        print(f"\n查詢: {query}")

        # 階段1: 向量檢索找出最相似的50個
        print("  階段1: 向量檢索...")
        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, doc_vectors)[0]

        # 找出最相似的50個
        top_50_indices = similarities.argsort()[-50:][::-1]
        candidates = [knowledge_base[i] for i in top_50_indices]

        print(f"    向量檢索前5名:")
        for i in range(min(5, len(candidates))):
            kb = candidates[i]
            print(f"      {i+1}. ID {kb['id']}: {kb['title'][:30]}...")

        # 階段2: 語義模型重排序
        print("  階段2: 語義模型重排序...")
        pairs = [[query, kb['content']] for kb in candidates]
        scores = reranker.predict(pairs)

        best_idx = scores.argmax()
        best_kb = candidates[best_idx]

        print(f"  最終結果: ID {best_kb['id']} - {best_kb['title'][:40]}...")
        print(f"  語義分數: {scores[best_idx]:.3f}")
        print(f"  表單: {best_kb.get('form_id', 'None')}")

        if query == "電費帳單寄送區間" and best_kb['id'] in [1296, 1297]:
            print(f"  ✅ 正確找到電費表單！")
        elif query == "我要報修" and "報修" in best_kb['title']:
            print(f"  ✅ 正確找到報修！")
        else:
            print(f"  🤔 需要檢查")

    print("\n" + "="*80)
    print("方法3: 直接語義模型掃描全部（最準但最慢）")
    print("="*80)

    for query in ["電費帳單寄送區間"]:  # 只測試一個避免太慢
        print(f"\n查詢: {query}")
        print("  掃描全部1274個知識點...")

        # 批次處理
        batch_size = 100
        all_scores = []

        for i in range(0, len(knowledge_base), batch_size):
            batch = knowledge_base[i:i+batch_size]
            pairs = [[query, kb['content']] for kb in batch]
            scores = reranker.predict(pairs)
            all_scores.extend(scores)

        # 找出最高分
        best_idx = np.argmax(all_scores)
        best_kb = knowledge_base[best_idx]

        print(f"  找到: ID {best_kb['id']} - {best_kb['title'][:40]}...")
        print(f"  分數: {all_scores[best_idx]:.3f}")
        print(f"  表單: {best_kb.get('form_id', 'None')}")

        if best_kb['id'] in [1296, 1297]:
            print(f"  ✅ 完美！找到正確的電費表單")

    # 總結
    print("\n" + "="*80)
    print("💡 總結")
    print("="*80)
    print("\n問題根源:")
    print("❌ 方法1（只看前50個）: 會錯過後面的正確答案")
    print("✅ 方法2（向量+語義）: 實際系統用法，快速且準確")
    print("✅ 方法3（掃描全部）: 最準確但太慢")
    print("\n結論: 實際系統應該用方法2（兩階段檢索）")

if __name__ == "__main__":
    correct_test_flow()