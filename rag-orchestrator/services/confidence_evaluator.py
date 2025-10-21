"""
信心度評估系統
評估檢索結果的品質和信心度，決定如何處理使用者問題
"""
from typing import List, Dict, Tuple
import statistics


class ConfidenceEvaluator:
    """信心度評估器"""

    def __init__(self, config: Dict = None):
        """
        初始化信心度評估器

        Args:
            config: 配置字典，包含各種閾值設定
        """
        self.config = config or {
            "high_confidence_threshold": 0.70,
            "medium_confidence_threshold": 0.50,
            "min_results_for_high": 2,
            "keyword_match_weight": 0.2,
            "similarity_weight": 0.6,
            "result_count_weight": 0.2
        }

    def evaluate(
        self,
        search_results: List[Dict],
        question_keywords: List[str]
    ) -> Dict:
        """
        評估檢索結果的信心度

        Args:
            search_results: RAG 檢索結果列表
            question_keywords: 問題關鍵字列表

        Returns:
            評估結果字典，包含:
            - confidence_score: 整體信心度分數 (0-1)
            - confidence_level: 信心度等級 (high/medium/low)
            - decision: 決策 (direct_answer/needs_enhancement/unclear)
            - reasoning: 評估理由
            - metrics: 詳細評估指標
        """
        if not search_results:
            return {
                "confidence_score": 0.0,
                "confidence_level": "low",
                "decision": "unclear",
                "reasoning": "沒有找到相關知識",
                "metrics": {
                    "similarity_score": 0.0,
                    "result_count": 0,
                    "keyword_match_rate": 0.0
                }
            }

        # 1. 計算各項指標
        metrics = self._calculate_metrics(search_results, question_keywords)

        # 2. 計算加權信心度分數
        confidence_score = self._calculate_weighted_score(metrics)

        # 3. 判斷信心度等級
        confidence_level = self._determine_confidence_level(
            confidence_score,
            metrics['result_count']
        )

        # 4. 決定處理策略
        decision = self._make_decision(confidence_level, metrics)

        # 5. 生成評估理由
        reasoning = self._generate_reasoning(confidence_level, metrics)

        return {
            "confidence_score": round(confidence_score, 3),
            "confidence_level": confidence_level,
            "decision": decision,
            "reasoning": reasoning,
            "metrics": metrics
        }

    def _calculate_metrics(
        self,
        search_results: List[Dict],
        question_keywords: List[str]
    ) -> Dict:
        """計算評估指標"""
        # 1. 相似度分數
        similarities = [r['similarity'] for r in search_results]
        avg_similarity = statistics.mean(similarities)
        max_similarity = max(similarities)

        # 2. 結果數量
        result_count = len(search_results)

        # 3. 關鍵字匹配率
        keyword_match_rate = self._calculate_keyword_match_rate(
            search_results,
            question_keywords
        )

        # 4. 結果一致性 (標準差越小越好)
        similarity_std = statistics.stdev(similarities) if len(similarities) > 1 else 0
        consistency = 1 - min(similarity_std, 0.3) / 0.3  # 標準化到 0-1

        # 5. 最佳結果的內容長度
        best_result = search_results[0]
        content_length = len(best_result.get('content', ''))
        content_quality = min(content_length / 500, 1.0)  # 假設 500 字以上為完整

        return {
            "avg_similarity": round(avg_similarity, 3),
            "max_similarity": round(max_similarity, 3),
            "result_count": result_count,
            "keyword_match_rate": round(keyword_match_rate, 3),
            "consistency": round(consistency, 3),
            "content_quality": round(content_quality, 3)
        }

    def _calculate_keyword_match_rate(
        self,
        search_results: List[Dict],
        question_keywords: List[str]
    ) -> float:
        """計算關鍵字匹配率"""
        if not question_keywords:
            return 0.0

        # 收集所有結果的關鍵字
        result_keywords = set()
        for result in search_results:
            # 處理 keywords 可能為 None 的情況
            keywords = result.get('keywords') or []
            result_keywords.update(keywords)

        # 計算匹配的關鍵字數量
        matched = set(question_keywords) & result_keywords
        match_rate = len(matched) / len(question_keywords)

        return match_rate

    def _calculate_weighted_score(self, metrics: Dict) -> float:
        """計算加權信心度分數"""
        score = (
            metrics['max_similarity'] * self.config['similarity_weight'] +
            min(metrics['result_count'] / 5, 1.0) * self.config['result_count_weight'] +
            metrics['keyword_match_rate'] * self.config['keyword_match_weight']
        )
        return min(score, 1.0)

    def _determine_confidence_level(
        self,
        confidence_score: float,
        result_count: int
    ) -> str:
        """判斷信心度等級"""
        high_threshold = self.config['high_confidence_threshold']
        medium_threshold = self.config['medium_confidence_threshold']
        min_results = self.config['min_results_for_high']

        if confidence_score >= high_threshold and result_count >= min_results:
            return "high"
        elif confidence_score >= medium_threshold:
            return "medium"
        else:
            return "low"

    def _make_decision(self, confidence_level: str, metrics: Dict) -> str:
        """決定處理策略"""
        if confidence_level == "high":
            return "direct_answer"
        elif confidence_level == "medium":
            # 中等信心度：提供參考但需要人工確認
            return "needs_enhancement"
        else:
            return "unclear"

    def _generate_reasoning(self, confidence_level: str, metrics: Dict) -> str:
        """生成評估理由"""
        reasons = []

        # 相似度評估
        if metrics['max_similarity'] >= 0.85:
            reasons.append(f"最高相似度 {metrics['max_similarity']:.2f} (極高)")
        elif metrics['max_similarity'] >= 0.70:
            reasons.append(f"最高相似度 {metrics['max_similarity']:.2f} (中等)")
        else:
            reasons.append(f"最高相似度 {metrics['max_similarity']:.2f} (較低)")

        # 結果數量評估
        if metrics['result_count'] >= 3:
            reasons.append(f"找到 {metrics['result_count']} 個相關結果")
        elif metrics['result_count'] >= 1:
            reasons.append(f"僅找到 {metrics['result_count']} 個相關結果")
        else:
            reasons.append("沒有找到相關結果")

        # 關鍵字匹配評估
        if metrics['keyword_match_rate'] >= 0.7:
            reasons.append(f"關鍵字匹配度 {metrics['keyword_match_rate']:.0%} (良好)")
        elif metrics['keyword_match_rate'] >= 0.3:
            reasons.append(f"關鍵字匹配度 {metrics['keyword_match_rate']:.0%} (部分匹配)")
        else:
            reasons.append(f"關鍵字匹配度 {metrics['keyword_match_rate']:.0%} (較低)")

        # 一致性評估
        if metrics['consistency'] >= 0.8:
            reasons.append("結果一致性高")

        return "; ".join(reasons)

    def should_escalate_to_human(self, evaluation: Dict) -> bool:
        """
        判斷是否應該轉人工處理

        Args:
            evaluation: 評估結果

        Returns:
            是否應該轉人工
        """
        return (
            evaluation['confidence_level'] == 'low' or
            evaluation['decision'] == 'unclear'
        )

    def get_recommended_action(self, evaluation: Dict) -> str:
        """
        取得建議的處理動作

        Args:
            evaluation: 評估結果

        Returns:
            建議動作描述
        """
        decision = evaluation['decision']
        confidence_level = evaluation['confidence_level']

        actions = {
            ('direct_answer', 'high'): "直接使用檢索結果回答，無需額外處理",
            ('direct_answer', 'medium'): "使用檢索結果回答，建議稍加潤飾",
            ('needs_enhancement', 'medium'): "需要使用 LLM 重組答案以提高品質",
            ('unclear', 'low'): "記錄為未釐清問題，建議轉人工處理"
        }

        return actions.get(
            (decision, confidence_level),
            "未知的處理策略"
        )


# 使用範例
if __name__ == "__main__":
    evaluator = ConfidenceEvaluator()

    # 模擬檢索結果
    test_cases = [
        {
            "name": "高信心度案例",
            "results": [
                {"similarity": 0.92, "keywords": ["退租", "流程"], "content": "退租流程說明..." * 100},
                {"similarity": 0.88, "keywords": ["退租", "申請"], "content": "退租申請方式..." * 100},
                {"similarity": 0.85, "keywords": ["解約"], "content": "解約須知..." * 100}
            ],
            "keywords": ["退租", "流程"]
        },
        {
            "name": "中信心度案例",
            "results": [
                {"similarity": 0.75, "keywords": ["租約"], "content": "租約相關..." * 50},
                {"similarity": 0.72, "keywords": ["合約"], "content": "合約說明..." * 50}
            ],
            "keywords": ["退租", "流程"]
        },
        {
            "name": "低信心度案例",
            "results": [
                {"similarity": 0.65, "keywords": ["其他"], "content": "其他內容..." * 20}
            ],
            "keywords": ["退租", "流程"]
        }
    ]

    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"測試案例: {test_case['name']}")
        print(f"{'='*60}")

        evaluation = evaluator.evaluate(
            test_case['results'],
            test_case['keywords']
        )

        print(f"信心度分數: {evaluation['confidence_score']}")
        print(f"信心度等級: {evaluation['confidence_level']}")
        print(f"決策: {evaluation['decision']}")
        print(f"評估理由: {evaluation['reasoning']}")
        print(f"建議動作: {evaluator.get_recommended_action(evaluation)}")
        print(f"\n詳細指標:")
        for key, value in evaluation['metrics'].items():
            print(f"  - {key}: {value}")
