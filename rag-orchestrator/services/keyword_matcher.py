"""
關鍵詞匹配引擎（Keyword Matcher）
用於檢測用戶訊息是否包含 SOP 觸發關鍵詞

功能：
1. 精確匹配：完全相同
2. 模糊匹配：包含關係
3. 同義詞匹配：擴展匹配範圍
4. 組合匹配：多個關鍵詞邏輯組合

支援場景：
- manual 模式：自定義關鍵詞（如：「還是不行」、「試過了」）
- immediate 模式：通用肯定詞（如：「是」、「要」、「好」）
"""
from typing import List, Dict, Optional, Tuple
import re


class KeywordMatcher:
    """
    關鍵詞匹配器

    支援多種匹配策略：
    1. 精確匹配（exact）
    2. 包含匹配（contains）
    3. 正則匹配（regex）
    4. 同義詞匹配（synonyms）
    """

    def __init__(self):
        """初始化關鍵詞匹配器"""
        # 預定義同義詞表（可擴展）
        self.synonyms = {
            # 肯定詞
            '是': ['好', '要', '可以', '需要', '對', '是的', '沒錯', '確認', 'ok', 'yes'],
            '要': ['需要', '想要', '希望', '麻煩'],
            '好': ['可以', '沒問題', '行', 'OK'],

            # 否定詞
            '不': ['不要', '不用', '不需要', '不行', '不可以', '不好'],
            '取消': ['算了', '放棄', '不要了', '作罷'],

            # 排查相關
            '還是不行': ['試過了還是不行', '還是沒用', '沒有用', '沒效果', '還是有問題'],
            '試過了': ['試過', '嘗試過了', '已經試過', '做過了'],
            '需要維修': ['要維修', '請幫我修', '需要修理', '請人來修'],

            # 繼續相關
            '繼續': ['繼續填', '繼續寫', '接著填', '往下'],
            '稍後': ['等等', '待會', '晚點', '之後再說'],
        }

        # 否定詞前綴（用於檢測否定句）
        self.negation_prefixes = [
            '不', '別', '沒', '無', '非', '未', '莫', '勿'
        ]

    def _is_negated(self, user_message: str, keyword: str) -> bool:
        """
        檢測關鍵詞是否被否定

        Args:
            user_message: 用戶訊息
            keyword: 匹配到的關鍵詞

        Returns:
            True 如果關鍵詞前面有否定詞

        範例：
        - "我不要" + "要" → True (被否定)
        - "我要" + "要" → False (未被否定)
        - "不好" + "好" → True (被否定)
        """
        # 找到關鍵詞在訊息中的位置
        keyword_index = user_message.find(keyword)
        if keyword_index == -1:
            return False

        # 檢查關鍵詞前面是否有否定詞
        for neg in self.negation_prefixes:
            # 檢查否定詞是否緊鄰關鍵詞前面（允許 0-2 個字符的間隔）
            for offset in range(3):  # 檢查前 0-2 個字符
                neg_index = keyword_index - len(neg) - offset
                if neg_index >= 0:
                    text_before = user_message[neg_index:keyword_index]
                    if text_before.startswith(neg):
                        # 確認否定詞和關鍵詞之間沒有其他實質內容
                        between = text_before[len(neg):]
                        if len(between.strip()) <= 1:  # 允許一個字符（如「我不要」中的「不」和「要」之間沒有字符）
                            return True

        return False

    def match(
        self,
        user_message: str,
        keywords: List[str],
        match_type: str = "contains",
        case_sensitive: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        檢查用戶訊息是否匹配關鍵詞

        Args:
            user_message: 用戶訊息
            keywords: 關鍵詞列表
            match_type: 匹配類型 (exact/contains/regex/synonyms)
            case_sensitive: 是否區分大小寫

        Returns:
            (是否匹配, 匹配到的關鍵詞)
        """
        if not keywords:
            return False, None

        if not case_sensitive:
            user_message = user_message.lower()
            keywords = [kw.lower() if isinstance(kw, str) else kw for kw in keywords]

        # 根據匹配類型選擇策略
        if match_type == "exact":
            return self._exact_match(user_message, keywords)
        elif match_type == "contains":
            return self._contains_match(user_message, keywords)
        elif match_type == "regex":
            return self._regex_match(user_message, keywords)
        elif match_type == "synonyms":
            return self._synonyms_match(user_message, keywords)
        else:
            # 預設使用 contains
            return self._contains_match(user_message, keywords)

    def _exact_match(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        精確匹配：用戶訊息完全等於某個關鍵詞

        範例：
        - user_message: "是"
        - keywords: ["是", "要", "好"]
        - 結果：✅ 匹配（完全相同）
        """
        user_message_clean = user_message.strip()

        for keyword in keywords:
            if user_message_clean == keyword.strip():
                return True, keyword

        return False, None

    def _contains_match(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        包含匹配：用戶訊息包含某個關鍵詞（排除被否定的情況）

        範例：
        - user_message: "試過了還是不行"
        - keywords: ["還是不行", "試過了"]
        - 結果：✅ 匹配（包含「還是不行」）

        - user_message: "我不要"
        - keywords: ["要"]
        - 結果：❌ 不匹配（「要」被「不」否定）
        """
        for keyword in keywords:
            if keyword in user_message:
                # 檢查是否被否定
                if not self._is_negated(user_message, keyword):
                    return True, keyword

        return False, None

    def _regex_match(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        正則匹配：使用正則表達式匹配

        範例：
        - user_message: "還是不太行"
        - keywords: ["還是不.*行"]
        - 結果：✅ 匹配（正則：還是不 + 任意字符 + 行）
        """
        for keyword in keywords:
            try:
                pattern = re.compile(keyword)
                if pattern.search(user_message):
                    return True, keyword
            except re.error:
                # 正則表達式錯誤，跳過
                continue

        return False, None

    def _synonyms_match(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        同義詞匹配：關鍵詞 + 同義詞一起匹配（排除被否定的情況）

        範例：
        - user_message: "沒問題"
        - keywords: ["好"]
        - synonyms: {"好": ["可以", "沒問題", "行"]}
        - 結果：✅ 匹配（「沒問題」是「好」的同義詞）
        """
        for keyword in keywords:
            # 先檢查關鍵詞本身
            if keyword in user_message:
                # 檢查是否被否定
                if not self._is_negated(user_message, keyword):
                    return True, keyword

            # 再檢查同義詞
            if keyword in self.synonyms:
                for synonym in self.synonyms[keyword]:
                    if synonym in user_message:
                        # 檢查同義詞是否被否定
                        if not self._is_negated(user_message, synonym):
                            return True, f"{keyword} (同義詞: {synonym})"

        return False, None

    def match_any(
        self,
        user_message: str,
        keywords: List[str],
        match_types: List[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        多策略匹配：嘗試多種匹配策略，任一成功即返回

        Args:
            user_message: 用戶訊息
            keywords: 關鍵詞列表
            match_types: 匹配策略列表（預設：contains, synonyms）

        Returns:
            (是否匹配, 匹配到的關鍵詞, 使用的策略)
        """
        if match_types is None:
            match_types = ["contains", "synonyms"]

        for match_type in match_types:
            is_match, keyword = self.match(user_message, keywords, match_type)
            if is_match:
                return True, keyword, match_type

        return False, None, None

    def get_match_score(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Dict[str, float]:
        """
        計算匹配分數（用於多個關鍵詞的優先級排序，排除被否定的關鍵詞）

        Args:
            user_message: 用戶訊息
            keywords: 關鍵詞列表

        Returns:
            {keyword: score} 字典
        """
        scores = {}

        for keyword in keywords:
            score = 0.0

            # 精確匹配：最高分
            if user_message.strip() == keyword.strip():
                score = 1.0

            # 完整包含：高分
            elif keyword in user_message:
                # 檢查是否被否定
                if not self._is_negated(user_message, keyword):
                    # 計算相似度（關鍵詞長度 / 訊息長度）
                    score = len(keyword) / len(user_message)

            # 同義詞匹配：中等分數
            elif keyword in self.synonyms:
                for synonym in self.synonyms[keyword]:
                    if synonym in user_message:
                        # 檢查同義詞是否被否定
                        if not self._is_negated(user_message, synonym):
                            score = max(score, 0.8 * len(synonym) / len(user_message))

            scores[keyword] = score

        return scores

    def get_best_match(
        self,
        user_message: str,
        keywords: List[str]
    ) -> Optional[Tuple[str, float]]:
        """
        獲取最佳匹配關鍵詞

        Args:
            user_message: 用戶訊息
            keywords: 關鍵詞列表

        Returns:
            (關鍵詞, 分數) 或 None
        """
        scores = self.get_match_score(user_message, keywords)

        if not scores:
            return None

        # 找出最高分
        best_keyword = max(scores, key=scores.get)
        best_score = scores[best_keyword]

        if best_score > 0:
            return best_keyword, best_score
        else:
            return None


# 使用範例
if __name__ == "__main__":
    matcher = KeywordMatcher()

    print("=" * 80)
    print("測試 1：manual 模式 - 排查型關鍵詞")
    print("=" * 80)

    manual_keywords = ['還是不行', '試過了', '需要維修']
    test_messages = [
        "試過了還是不行",
        "還是不太行",
        "我已經試過了",
        "都試過了還是有問題",
        "需要人來修理",
        "冷氣還是很熱"
    ]

    for msg in test_messages:
        # 嘗試多種匹配策略
        is_match, keyword, match_type = matcher.match_any(msg, manual_keywords)

        print(f"\n訊息: {msg}")
        print(f"  匹配結果: {'✅ 匹配' if is_match else '❌ 不匹配'}")
        if is_match:
            print(f"  匹配關鍵詞: {keyword}")
            print(f"  匹配策略: {match_type}")

        # 顯示分數
        scores = matcher.get_match_score(msg, manual_keywords)
        if any(score > 0 for score in scores.values()):
            print(f"  匹配分數: {scores}")

    print("\n" + "=" * 80)
    print("測試 2：immediate 模式 - 通用肯定詞")
    print("=" * 80)

    immediate_keywords = ['是', '要', '好', '可以', '需要']
    test_messages = [
        "是",
        "好的",
        "可以啊",
        "要",
        "我要",
        "不要",
        "沒問題",
        "OK"
    ]

    for msg in test_messages:
        is_match, keyword, match_type = matcher.match_any(msg, immediate_keywords)

        print(f"\n訊息: {msg}")
        print(f"  匹配結果: {'✅ 匹配' if is_match else '❌ 不匹配'}")
        if is_match:
            print(f"  匹配關鍵詞: {keyword}")
            print(f"  匹配策略: {match_type}")

    print("\n" + "=" * 80)
    print("測試 3：最佳匹配（多個關鍵詞都匹配時）")
    print("=" * 80)

    msg = "試過了還是不行，需要維修"
    best_match = matcher.get_best_match(msg, manual_keywords)

    print(f"\n訊息: {msg}")
    print(f"關鍵詞列表: {manual_keywords}")
    if best_match:
        keyword, score = best_match
        print(f"最佳匹配: {keyword} (分數: {score:.3f})")

    print("\n" + "=" * 80)
    print("測試 4：精確匹配 vs 包含匹配")
    print("=" * 80)

    keywords = ['是', '要']
    test_cases = [
        ("是", "exact"),
        ("是的", "contains"),
        ("我要", "contains"),
        ("要", "exact")
    ]

    for msg, expected_type in test_cases:
        # 精確匹配
        exact_match, exact_kw = matcher.match(msg, keywords, "exact")
        # 包含匹配
        contains_match, contains_kw = matcher.match(msg, keywords, "contains")

        print(f"\n訊息: '{msg}'")
        print(f"  精確匹配: {'✅ ' + exact_kw if exact_match else '❌'}")
        print(f"  包含匹配: {'✅ ' + contains_kw if contains_match else '❌'}")
        print(f"  預期: {expected_type}")
