#!/usr/bin/env python3
"""
簡單的模型使用範例 - 直接使用預訓練模型
"""

from sentence_transformers import CrossEncoder
import json

def simple_example():
    """簡單使用範例"""

    print("="*60)
    print("語義模型使用範例")
    print("="*60)

    # 使用預訓練模型
    print("\n載入模型...")
    model = CrossEncoder('BAAI/bge-reranker-base', max_length=512)
    print("✅ 模型載入成功")

    # 載入知識庫的前10個
    print("\n載入知識庫...")
    with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
        knowledge = json.load(f)[:10]  # 只用前10個做示範
    print(f"✅ 載入 {len(knowledge)} 個知識點")

    # 測試查詢
    queries = [
        "我要報修",
        "電費怎麼算",
        "可以養寵物嗎"
    ]

    print("\n" + "="*60)
    print("測試語義匹配")
    print("="*60)

    for query in queries:
        print(f"\n查詢: {query}")
        print("-" * 40)

        # 計算與每個知識點的相關性
        scores = []
        for kb in knowledge:
            # 計算相關性分數
            pair = [[query, kb['content']]]
            score = model.predict(pair)[0]
            scores.append({
                'id': kb['id'],
                'title': kb['title'],
                'score': score,
                'action_type': kb.get('action_type')
            })

        # 排序
        scores.sort(key=lambda x: x['score'], reverse=True)

        # 顯示最佳匹配
        best = scores[0]
        print(f"最佳匹配:")
        print(f"  標題: {best['title']}")
        print(f"  分數: {best['score']:.3f}")
        print(f"  類型: {best['action_type']}")

        # 顯示前3個結果
        print(f"\n前3個相關結果:")
        for i, item in enumerate(scores[:3], 1):
            print(f"  {i}. {item['title'][:30]}... (分數: {item['score']:.3f})")

def integration_guide():
    """整合指南"""

    print("\n" + "="*60)
    print("如何整合到您的系統")
    print("="*60)

    print("""
1. 安裝依賴:
   pip install sentence-transformers

2. 在您的 ChatService 中加入:

```python
from sentence_transformers import CrossEncoder

class EnhancedChatService:
    def __init__(self):
        # 載入語義模型
        self.semantic_model = CrossEncoder('BAAI/bge-reranker-base')

    def enhance_search(self, query, candidates):
        # 計算語義相關性
        pairs = [[query, c['content']] for c in candidates]
        scores = self.semantic_model.predict(pairs)

        # 加入語義分數
        for i, candidate in enumerate(candidates):
            candidate['semantic_score'] = scores[i]

        return candidates
```

3. 結合向量檢索和 Reranker:
   - 向量檢索: 快速篩選 Top-K
   - 語義模型: 理解查詢意圖
   - Reranker: 精確排序

4. 綜合評分:
   final_score = vector_score * 0.3 + semantic_score * 0.4 + reranker_score * 0.3
""")

if __name__ == "__main__":
    # 執行範例
    simple_example()

    # 顯示整合指南
    integration_guide()

    print("\n" + "="*60)
    print("✅ 完成！您可以開始使用語義模型了")
    print("="*60)