#!/usr/bin/env python3
"""
智能路由器 - 決定何時使用語義模型
"""

import time
import re
from typing import Dict, List, Optional
from enum import Enum

class QueryType(Enum):
    """查詢類型分類"""
    SIMPLE_FAQ = "simple_faq"        # 簡單常見問題
    FORM_TRIGGER = "form_trigger"    # 表單觸發
    COMPLEX_QUERY = "complex_query"  # 複雜查詢
    NAVIGATION = "navigation"        # 導航類
    GREETING = "greeting"            # 問候語

class SmartRouter:
    """
    智能路由器 - 根據查詢類型決定處理策略
    """

    def __init__(self):
        # 表單相關關鍵字（需要高準確度）
        self.form_keywords = [
            "帳單", "寄送", "區間", "查詢", "申請",
            "報修", "異動", "退租", "繳費", "電費"
        ]

        # 簡單問題模式（可用向量檢索）
        self.simple_patterns = [
            r"^(客服|電話|聯絡)",
            r"^(營業|上班|時間)",
            r"^(地址|位置|在哪)",
            r"^(你好|嗨|早安|晚安)"
        ]

        # 複雜查詢特徵
        self.complex_indicators = [
            "怎麼", "如何", "為什麼", "可以嗎",
            "流程", "步驟", "需要什麼"
        ]

    def analyze_query(self, query: str) -> Dict:
        """
        分析查詢並決定處理策略
        """
        query_lower = query.lower()

        # 1. 檢測查詢類型
        query_type = self._detect_type(query_lower)

        # 2. 決定處理策略
        strategy = self._decide_strategy(query_type, query_lower)

        # 3. 估算處理時間
        estimated_time = self._estimate_time(strategy)

        return {
            "query": query,
            "type": query_type.value,
            "strategy": strategy,
            "estimated_time_ms": estimated_time,
            "confidence": self._calculate_confidence(query_lower, query_type)
        }

    def _detect_type(self, query: str) -> QueryType:
        """檢測查詢類型"""

        # 問候語
        if any(greeting in query for greeting in ["你好", "嗨", "早安", "晚安"]):
            return QueryType.GREETING

        # 表單觸發類
        form_score = sum(1 for keyword in self.form_keywords if keyword in query)
        if form_score >= 2:  # 至少包含2個表單關鍵字
            return QueryType.FORM_TRIGGER

        # 簡單FAQ
        for pattern in self.simple_patterns:
            if re.match(pattern, query):
                return QueryType.SIMPLE_FAQ

        # 複雜查詢
        complex_score = sum(1 for indicator in self.complex_indicators if indicator in query)
        if complex_score >= 1:
            return QueryType.COMPLEX_QUERY

        # 導航類
        if any(nav in query for nav in ["在哪", "怎麼去", "位置"]):
            return QueryType.NAVIGATION

        # 預設為簡單FAQ
        return QueryType.SIMPLE_FAQ

    def _decide_strategy(self, query_type: QueryType, query: str) -> str:
        """
        根據類型決定處理策略
        """
        strategies = {
            QueryType.GREETING: "direct_response",      # 直接回應
            QueryType.SIMPLE_FAQ: "vector_search",      # 向量檢索
            QueryType.NAVIGATION: "vector_search",      # 向量檢索
            QueryType.FORM_TRIGGER: "semantic_model",   # 語義模型
            QueryType.COMPLEX_QUERY: "two_stage",       # 兩階段
        }

        # 特殊情況：如果包含"電費"且包含"寄送"，強制使用語義模型
        if "電費" in query and ("寄送" in query or "帳單" in query):
            return "semantic_model"

        return strategies.get(query_type, "vector_search")

    def _estimate_time(self, strategy: str) -> int:
        """估算處理時間（毫秒）"""
        time_map = {
            "direct_response": 10,
            "vector_search": 50,
            "semantic_model": 500,
            "two_stage": 300,
        }
        return time_map.get(strategy, 100)

    def _calculate_confidence(self, query: str, query_type: QueryType) -> float:
        """計算分類信心度"""
        if query_type == QueryType.GREETING:
            return 1.0
        elif query_type == QueryType.FORM_TRIGGER:
            # 根據關鍵字數量計算
            score = sum(1 for keyword in self.form_keywords if keyword in query)
            return min(score * 0.3, 1.0)
        else:
            return 0.7

    def route_query(self, query: str, knowledge_base: List[Dict]) -> Dict:
        """
        實際路由查詢到適當的處理器
        """
        analysis = self.analyze_query(query)
        strategy = analysis["strategy"]

        print(f"\n查詢: {query}")
        print(f"類型: {analysis['type']}")
        print(f"策略: {strategy}")
        print(f"預估時間: {analysis['estimated_time_ms']}ms")

        start_time = time.time()

        if strategy == "direct_response":
            # 直接回應（不需要檢索）
            result = self._direct_response(query)
        elif strategy == "vector_search":
            # 使用向量檢索（快速）
            result = self._vector_search(query, knowledge_base)
        elif strategy == "semantic_model":
            # 使用語義模型（準確）
            result = self._semantic_search(query, knowledge_base)
        elif strategy == "two_stage":
            # 兩階段檢索（平衡）
            result = self._two_stage_search(query, knowledge_base)
        else:
            result = {"error": "Unknown strategy"}

        actual_time = (time.time() - start_time) * 1000
        result["actual_time_ms"] = actual_time
        result["strategy_used"] = strategy

        return result

    def _direct_response(self, query: str) -> Dict:
        """直接回應（問候等）"""
        return {
            "response": "您好！有什麼可以幫助您的嗎？",
            "confidence": 1.0
        }

    def _vector_search(self, query: str, knowledge_base: List[Dict]) -> Dict:
        """模擬向量檢索"""
        # 實際應用中，這裡會調用向量檢索服務
        time.sleep(0.05)  # 模擬 50ms 延遲
        return {
            "results": knowledge_base[:5],
            "method": "vector_search",
            "confidence": 0.7
        }

    def _semantic_search(self, query: str, knowledge_base: List[Dict]) -> Dict:
        """模擬語義檢索"""
        # 實際應用中，這裡會調用語義模型服務
        time.sleep(0.5)  # 模擬 500ms 延遲
        return {
            "results": knowledge_base[:3],
            "method": "semantic_model",
            "confidence": 0.9
        }

    def _two_stage_search(self, query: str, knowledge_base: List[Dict]) -> Dict:
        """模擬兩階段檢索"""
        # 階段1: 向量檢索取得候選
        time.sleep(0.05)
        candidates = knowledge_base[:20]

        # 階段2: 語義重排
        time.sleep(0.25)
        reranked = candidates[:5]

        return {
            "results": reranked,
            "method": "two_stage",
            "confidence": 0.85
        }


def demo():
    """示範智能路由"""

    print("="*60)
    print("智能路由器示範")
    print("="*60)

    router = SmartRouter()

    # 測試各種查詢
    test_queries = [
        "你好",                      # 問候語
        "客服電話多少",              # 簡單FAQ
        "電費帳單寄送區間",          # 表單觸發（需要高準確度）
        "我要報修",                  # 表單觸發
        "如何申請退租",              # 複雜查詢
        "營業時間",                  # 簡單FAQ
        "為什麼電費這麼貴",          # 複雜查詢
        "繳費方式有哪些",            # 簡單FAQ
    ]

    # 模擬知識庫
    mock_kb = [{"id": i, "content": f"知識點{i}"} for i in range(100)]

    results = []
    for query in test_queries:
        result = router.route_query(query, mock_kb)
        results.append({
            "query": query,
            "strategy": result.get("strategy_used"),
            "time": result.get("actual_time_ms", 0)
        })
        print(f"實際耗時: {result.get('actual_time_ms', 0):.1f}ms\n")

    # 統計分析
    print("="*60)
    print("統計分析")
    print("="*60)

    # 按策略分組
    strategy_stats = {}
    for r in results:
        strategy = r["strategy"]
        if strategy not in strategy_stats:
            strategy_stats[strategy] = {"count": 0, "total_time": 0}
        strategy_stats[strategy]["count"] += 1
        strategy_stats[strategy]["total_time"] += r["time"]

    print("\n策略使用統計:")
    for strategy, stats in strategy_stats.items():
        avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
        print(f"  {strategy:20s}: {stats['count']} 次, 平均 {avg_time:.1f}ms")

    # 總體統計
    total_queries = len(results)
    total_time = sum(r["time"] for r in results)
    avg_time = total_time / total_queries if total_queries > 0 else 0

    print(f"\n總體統計:")
    print(f"  查詢總數: {total_queries}")
    print(f"  總耗時: {total_time:.1f}ms")
    print(f"  平均耗時: {avg_time:.1f}ms")

    # 對比全部使用語義模型
    semantic_only_time = total_queries * 500
    print(f"\n效能對比:")
    print(f"  智能路由: {total_time:.1f}ms")
    print(f"  全語義模型: {semantic_only_time:.1f}ms")
    print(f"  節省時間: {semantic_only_time - total_time:.1f}ms ({(1 - total_time/semantic_only_time)*100:.1f}%)")


if __name__ == "__main__":
    demo()