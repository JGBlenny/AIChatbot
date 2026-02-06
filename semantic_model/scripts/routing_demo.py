#!/usr/bin/env python3
"""
對話分流決策示範 - 清楚展示如何判斷
"""

class QueryAnalyzer:
    """查詢分析器 - 展示詳細的判斷過程"""

    def analyze_detailed(self, query: str):
        """詳細分析查詢並說明決策原因"""

        print(f"\n{'='*60}")
        print(f"查詢: '{query}'")
        print(f"{'='*60}")

        # 步驟 1: 分詞和檢查關鍵字
        print("\n📝 步驟1: 關鍵字檢測")
        keywords_found = self._check_keywords(query)

        # 步驟 2: 判斷是否需要表單
        print("\n🎯 步驟2: 表單需求判斷")
        needs_form = self._check_form_requirement(query, keywords_found)

        # 步驟 3: 判斷複雜度
        print("\n🧠 步驟3: 複雜度分析")
        complexity = self._analyze_complexity(query)

        # 步驟 4: 做出決策
        print("\n✅ 步驟4: 最終決策")
        decision = self._make_decision(needs_form, complexity, keywords_found)

        return decision

    def _check_keywords(self, query: str):
        """檢查關鍵字"""
        keywords = {
            "表單觸發詞": ["電費", "帳單", "寄送", "報修", "退租", "申請", "故障", "壞了"],
            "簡單查詢詞": ["電話", "地址", "時間", "多少", "押金", "租金"],
            "複雜查詢詞": ["為什麼", "怎麼", "如何", "流程", "步驟", "可以嗎"]
        }

        found = {}
        for category, words in keywords.items():
            found[category] = [w for w in words if w in query]
            if found[category]:
                print(f"  - 發現{category}: {', '.join(found[category])}")

        if not any(found.values()):
            print(f"  - 沒有發現特殊關鍵字")

        return found

    def _check_form_requirement(self, query: str, keywords_found: dict):
        """判斷是否需要觸發表單"""

        # 規則1: 電費+帳單+寄送 = 需要表單1296
        if "電費" in query and ("帳單" in query or "寄送" in query):
            print(f"  ✓ 符合規則: 電費帳單查詢 → 需要表單 ID 1296")
            return True

        # 規則2: 報修相關
        if "報修" in query or ("壞" in query and any(x in query for x in ["冷氣", "電燈", "水龍頭"])):
            print(f"  ✓ 符合規則: 設備報修 → 需要報修表單")
            return True

        # 規則3: 申請類
        if "申請" in query and any(x in query for x in ["退租", "停車", "異動"]):
            print(f"  ✓ 符合規則: 申請服務 → 需要申請表單")
            return True

        print(f"  ✗ 不需要觸發表單")
        return False

    def _analyze_complexity(self, query: str):
        """分析查詢複雜度"""

        # 簡單查詢特徵
        simple_patterns = ["電話", "地址", "時間", "多少錢", "幾號"]
        is_simple = any(p in query for p in simple_patterns) and len(query) < 10

        # 複雜查詢特徵
        complex_indicators = ["為什麼", "怎麼", "如何", "流程", "步驟"]
        is_complex = any(i in query for i in complex_indicators)

        if is_simple:
            print(f"  - 判定: 簡單查詢（直接答案）")
            return "simple"
        elif is_complex:
            print(f"  - 判定: 複雜查詢（需要解釋）")
            return "complex"
        else:
            print(f"  - 判定: 一般查詢")
            return "normal"

    def _make_decision(self, needs_form: bool, complexity: str, keywords: dict):
        """做出最終路由決策"""

        if needs_form:
            print(f"\n🎯 決策: 使用【語義模型】")
            print(f"  原因: 需要精確觸發表單，不能出錯")
            print(f"  預計延遲: 500ms")
            print(f"  流程: 查詢 → 語義模型評分所有知識點 → 返回最高分")
            return "semantic_model"

        elif complexity == "simple":
            print(f"\n⚡ 決策: 使用【向量檢索】")
            print(f"  原因: 簡單查詢，答案固定")
            print(f"  預計延遲: 50ms")
            print(f"  流程: 查詢 → 向量相似度計算 → 返回最相似")
            return "vector_search"

        elif complexity == "complex":
            print(f"\n⚖️ 決策: 使用【兩階段處理】")
            print(f"  原因: 複雜問題，需要理解但不觸發表單")
            print(f"  預計延遲: 300ms")
            print(f"  流程: 查詢 → 向量取前50 → 語義重排前5")
            return "two_stage"

        else:
            print(f"\n📊 決策: 使用【向量檢索】（預設）")
            print(f"  原因: 一般查詢")
            print(f"  預計延遲: 50ms")
            print(f"  流程: 查詢 → 向量相似度計算 → 返回最相似")
            return "vector_search"


def main():
    """執行分流示範"""

    print("\n" + "="*60)
    print("🚦 對話分流決策示範")
    print("="*60)
    print("\n展示每個查詢是如何被分析和路由的")

    analyzer = QueryAnalyzer()

    # 測試案例
    test_cases = [
        # 需要語義模型的
        "電費帳單寄送區間",
        "我要報修",
        "冷氣壞了",

        # 使用向量檢索的
        "客服電話多少",
        "營業時間",
        "押金多少錢",

        # 需要兩階段的
        "為什麼電費這麼貴",
        "如何申請退租流程",
        "可以養寵物嗎",
    ]

    # 統計
    results = {
        "semantic_model": [],
        "vector_search": [],
        "two_stage": []
    }

    for query in test_cases:
        decision = analyzer.analyze_detailed(query)
        results[decision].append(query)

    # 總結
    print("\n" + "="*60)
    print("📊 分流統計總結")
    print("="*60)

    print(f"\n🎯 語義模型處理 ({len(results['semantic_model'])}個):")
    for q in results['semantic_model']:
        print(f"  • {q}")

    print(f"\n⚡ 向量檢索處理 ({len(results['vector_search'])}個):")
    for q in results['vector_search']:
        print(f"  • {q}")

    print(f"\n⚖️ 兩階段處理 ({len(results['two_stage'])}個):")
    for q in results['two_stage']:
        print(f"  • {q}")

    # 流程圖
    print("\n" + "="*60)
    print("🔄 完整分流流程圖")
    print("="*60)
    print("""
    用戶輸入查詢
         ↓
    ┌─────────────┐
    │ 關鍵字檢測  │
    └─────────────┘
         ↓
    需要表單嗎？ ←─── 檢查: 電費+帳單、報修、申請退租
         ├─是─→ 【語義模型】500ms
         │      精確匹配表單ID
         ↓ 否
    查詢複雜嗎？ ←─── 檢查: 為什麼、如何、流程
         ├─複雜→ 【兩階段】300ms
         │       向量篩選+語義重排
         ↓ 簡單
    【向量檢索】50ms
    快速相似度匹配
    """)


if __name__ == "__main__":
    main()