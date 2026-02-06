#!/usr/bin/env python3
"""
展示如何在實際系統中使用訓練好的語義模型
"""

from sentence_transformers import CrossEncoder
import json

class SemanticMatcher:
    """語義匹配器 - 整合到您的系統"""

    def __init__(self):
        # 載入訓練好的模型
        self.model = CrossEncoder('models/semantic_v1')

        # 載入知識庫
        with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

    def find_best_match(self, query):
        """找出最匹配的知識點"""

        # 準備所有候選
        candidates = []
        for kb in self.knowledge_base:
            candidates.append({
                'id': kb['id'],
                'title': kb['title'],
                'content': kb['content'],
                'action_type': kb.get('action_type'),
                'form_id': kb.get('form_id')
            })

        # 計算相關性分數
        pairs = [[query, c['content']] for c in candidates]
        scores = self.model.predict(pairs)

        # 找出最高分
        best_idx = scores.argmax()
        best_score = scores[best_idx]
        best_match = candidates[best_idx]

        return {
            'knowledge_id': best_match['id'],
            'title': best_match['title'],
            'content': best_match['content'],
            'score': float(best_score),
            'action_type': best_match['action_type'],
            'form_id': best_match['form_id']
        }

    def enhanced_search(self, query, top_k=5):
        """增強搜索：返回前K個最相關的結果"""

        # 準備候選
        candidates = []
        for kb in self.knowledge_base:
            candidates.append({
                'id': kb['id'],
                'title': kb['title'],
                'content': kb['content'],
                'action_type': kb.get('action_type'),
                'form_id': kb.get('form_id')
            })

        # 計算分數
        pairs = [[query, c['content']] for c in candidates]
        scores = self.model.predict(pairs)

        # 排序並返回前K個
        sorted_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in sorted_indices:
            results.append({
                'knowledge_id': candidates[idx]['id'],
                'title': candidates[idx]['title'],
                'score': float(scores[idx]),
                'action_type': candidates[idx]['action_type'],
                'form_id': candidates[idx]['form_id']
            })

        return results

def test_examples():
    """測試範例"""

    print("="*60)
    print("語義模型使用範例")
    print("="*60)

    # 初始化匹配器
    matcher = SemanticMatcher()

    # 測試查詢
    test_queries = [
        "我要報修",
        "電費怎麼算",
        "可以養寵物嗎",
        "租金多少錢",
        "退租流程"
    ]

    print("\n單一最佳匹配測試:")
    print("-" * 40)

    for query in test_queries[:3]:
        result = matcher.find_best_match(query)
        print(f"\n查詢: {query}")
        print(f"最佳匹配: {result['title']}")
        print(f"相關性分數: {result['score']:.3f}")
        print(f"動作類型: {result['action_type']}")
        if result['form_id']:
            print(f"表單ID: {result['form_id']}")

    print("\n\n多結果搜索測試:")
    print("-" * 40)

    query = "房租繳費"
    results = matcher.enhanced_search(query, top_k=3)

    print(f"\n查詢: {query}")
    print("前3個相關結果:")
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. {result['title']}")
        print(f"     分數: {result['score']:.3f}")
        print(f"     類型: {result['action_type']}")

def integration_example():
    """展示如何整合到現有系統"""

    print("\n" + "="*60)
    print("整合到現有系統的範例")
    print("="*60)

    code = '''
# backend/services/enhanced_chat_service.py

class EnhancedChatService:
    def __init__(self):
        # 載入語義模型
        self.semantic_model = CrossEncoder('models/semantic_v1')
        # 原有的 Reranker
        self.reranker = CrossEncoder('BAAI/bge-reranker-base')

    def process_query(self, query):
        # 1. 向量檢索（原有）
        vector_results = self.vector_search(query, top_k=10)

        # 2. 語義增強評分（新增）
        semantic_scores = []
        for result in vector_results:
            score = self.semantic_model.predict(
                [[query, result['content']]]
            )[0]
            semantic_scores.append(score)

        # 3. Reranker 評分（原有）
        reranker_scores = self.reranker.predict(
            [[query, r['content']] for r in vector_results]
        )

        # 4. 綜合評分
        for i, result in enumerate(vector_results):
            result['final_score'] = (
                result['vector_score'] * 0.3 +
                semantic_scores[i] * 0.3 +
                reranker_scores[i] * 0.4
            )

        # 5. 排序並返回最佳結果
        vector_results.sort(key=lambda x: x['final_score'], reverse=True)
        return vector_results[0]
    '''

    print(code)

if __name__ == "__main__":
    # 執行測試
    test_examples()

    # 顯示整合範例
    integration_example()

    print("\n" + "="*60)
    print("✅ 模型已準備就緒！")
    print("="*60)