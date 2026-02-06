#!/usr/bin/env python3
"""
快速測試腳本 - 簡化版驗證
"""

import json
import time
from datetime import datetime

print("="*70)
print("語義模型系統 - 快速測試")
print("="*70)
print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 1. 載入知識庫
print("1. 載入知識庫...")
try:
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    print(f"   ✅ 載入 {len(knowledge_base)} 個知識點")
except Exception as e:
    print(f"   ❌ 載入失敗: {e}")
    exit(1)

# 2. 嘗試載入模型
print("\n2. 載入語義模型...")
print("   ⏳ 正在載入 BAAI/bge-reranker-base (可能需要 1-2 分鐘)...")

try:
    from sentence_transformers import CrossEncoder
    start_time = time.time()

    # 設定較短的超時
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)

    load_time = time.time() - start_time
    print(f"   ✅ 模型載入成功 (耗時: {load_time:.2f}秒)")

except Exception as e:
    print(f"   ❌ 模型載入失敗: {e}")
    print("\n   建議：")
    print("   1. 確認網路連線正常（需下載模型）")
    print("   2. 或使用離線模型")
    exit(1)

# 3. 測試關鍵查詢
print("\n3. 測試關鍵查詢...")
print("="*70)

test_queries = [
    "電費帳單寄送區間",
    "我要報修",
    "租金多少錢"
]

for query in test_queries:
    print(f"\n測試查詢: {query}")
    print("-" * 40)

    try:
        # 找出前5個最相關的知識點
        start_time = time.time()

        # 計算分數（簡化版：只測試前20個知識點）
        candidates = knowledge_base[:20]
        pairs = [[query, kb['content']] for kb in candidates]
        scores = model.predict(pairs)

        # 組合結果
        results = []
        for kb, score in zip(candidates, scores):
            results.append({
                'id': kb['id'],
                'title': kb['title'],
                'score': float(score),
                'action_type': kb.get('action_type'),
                'form_id': kb.get('form_id')
            })

        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)

        search_time = time.time() - start_time

        # 顯示前3個結果
        print(f"前3個匹配結果 (搜索耗時: {search_time:.2f}秒):")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. ID:{result['id']} | 分數:{result['score']:.3f}")
            print(f"     標題: {result['title'][:40]}...")
            if result['action_type']:
                print(f"     類型: {result['action_type']}")
            if result['form_id']:
                print(f"     表單: {result['form_id']}")

    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")

# 4. 特別測試：電費相關
print("\n" + "="*70)
print("4. 特別測試：電費帳單寄送區間")
print("="*70)

billing_query = "電費帳單寄送區間"
print(f"\n查詢: {billing_query}")

# 找出包含「電費」相關的知識點
relevant_kb = []
for kb in knowledge_base:
    title = kb.get('title', '').lower()
    content = kb.get('content', '').lower()
    keywords = ' '.join(kb.get('keywords', [])).lower()

    if '電費' in title or '電費' in content or '電費' in keywords:
        relevant_kb.append(kb)

print(f"\n找到 {len(relevant_kb)} 個電費相關知識點")

if relevant_kb:
    # 用模型評分
    print("\n使用語義模型評分...")
    pairs = [[billing_query, kb['content']] for kb in relevant_kb[:10]]
    scores = model.predict(pairs)

    # 顯示最相關的
    best_idx = scores.argmax()
    best_kb = relevant_kb[best_idx]
    best_score = scores[best_idx]

    print(f"\n最相關的知識點:")
    print(f"  ID: {best_kb['id']}")
    print(f"  標題: {best_kb['title']}")
    print(f"  分數: {best_score:.3f}")
    print(f"  類型: {best_kb.get('action_type')}")
    print(f"  表單: {best_kb.get('form_id')}")

    if best_kb.get('form_id') == 1296:
        print("\n✅ 成功！正確匹配到電費寄送區間查詢表單 (ID: 1296)")
    else:
        print(f"\n⚠️ 匹配到 ID {best_kb['id']}，但不是目標表單 1296")

print("\n" + "="*70)
print("✅ 快速測試完成！")
print("="*70)