"""
SOP 關鍵字處理服務
用於處理 SOP 系統的 keywords（檢索用）和 trigger_keywords（觸發用）

Date: 2026-02-11
Author: Claude Code Assistant
"""

import logging
from typing import List, Dict, Optional, Set
import jieba
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

logger = logging.getLogger(__name__)


class SOPKeywordsHandler:
    """
    SOP 關鍵字處理器
    負責處理檢索關鍵字匹配和分數加成
    """

    def __init__(self):
        """初始化關鍵字處理器"""
        self.keyword_boost_factor = 0.1  # 每個匹配關鍵字的加成係數
        self.max_boost = 0.3  # 最大加成上限

        # 載入繁體中文詞典
        try:
            jieba.load_userdict('/app/data/custom_dict.txt')
        except:
            logger.info("使用預設 jieba 詞典")

    async def apply_keywords_boost(
        self,
        results: List[Dict],
        query: str,
        boost_enabled: bool = True
    ) -> List[Dict]:
        """
        根據關鍵字匹配情況調整檢索結果分數

        Args:
            results: 原始檢索結果
            query: 用戶查詢
            boost_enabled: 是否啟用關鍵字加成

        Returns:
            調整後的結果列表
        """
        if not boost_enabled or not results:
            return results

        # 分詞處理查詢
        query_tokens = self._tokenize(query)

        for result in results:
            # 獲取 SOP 的檢索關鍵字
            keywords = result.get('keywords', [])
            if not keywords:
                continue

            # 計算關鍵字匹配
            matched_keywords = self._calculate_keyword_matches(
                query_tokens, keywords
            )

            if matched_keywords:
                # 計算加成分數
                boost = min(
                    self.max_boost,
                    len(matched_keywords) * self.keyword_boost_factor
                )

                # 更新相似度分數
                original_score = result.get('similarity', 0.0)
                result['similarity'] = original_score * (1 + boost)

                # 記錄匹配的關鍵字
                result['keyword_matches'] = list(matched_keywords)
                result['keyword_boost'] = boost

                logger.debug(
                    f"SOP {result.get('id')} 關鍵字加成: "
                    f"原始分數={original_score:.3f}, "
                    f"加成={boost:.3f}, "
                    f"最終分數={result['similarity']:.3f}, "
                    f"匹配關鍵字={matched_keywords}"
                )

        # 重新排序
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)

    def _tokenize(self, text: str) -> Set[str]:
        """
        對文本進行分詞

        Args:
            text: 要分詞的文本

        Returns:
            分詞後的集合
        """
        if not text:
            return set()

        # 轉小寫並分詞
        tokens = set()

        # 保留原始文本（用於精確匹配）
        tokens.add(text.lower())

        # jieba 分詞
        tokens.update(jieba.cut(text.lower()))

        # 移除空白和單字符（除了數字）
        tokens = {
            t.strip()
            for t in tokens
            if t.strip() and (len(t.strip()) > 1 or t.strip().isdigit())
        }

        return tokens

    def _calculate_keyword_matches(
        self,
        query_tokens: Set[str],
        keywords: List[str]
    ) -> Set[str]:
        """
        計算查詢與關鍵字的匹配

        Args:
            query_tokens: 查詢分詞集合
            keywords: SOP 關鍵字列表

        Returns:
            匹配的關鍵字集合
        """
        if not keywords:
            return set()

        matched = set()

        for keyword in keywords:
            keyword_tokens = self._tokenize(keyword)

            # 檢查是否有交集
            intersections = query_tokens & keyword_tokens
            if intersections:
                matched.add(keyword)

        return matched

    async def get_sop_by_keywords(
        self,
        db: AsyncSession,
        vendor_id: int,
        keywords: List[str],
        limit: int = 10
    ) -> List[Dict]:
        """
        透過關鍵字直接查詢 SOP（使用 PostgreSQL 陣列操作）

        Args:
            db: 資料庫連線
            vendor_id: 業者 ID
            keywords: 要搜尋的關鍵字列表
            limit: 返回結果數量限制

        Returns:
            匹配的 SOP 列表
        """
        from ...models import VendorSOPItem  # 延遲導入避免循環依賴

        # 建立查詢條件
        conditions = [
            VendorSOPItem.vendor_id == vendor_id,
            VendorSOPItem.is_active == True
        ]

        # 建立關鍵字匹配條件（使用 PostgreSQL 的 && 操作符）
        if keywords:
            # 任一關鍵字匹配
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(
                    func.array_to_string(VendorSOPItem.keywords, ' ').ilike(f'%{keyword}%')
                )
            conditions.append(or_(*keyword_conditions))

        # 執行查詢
        query = (
            select(VendorSOPItem)
            .where(and_(*conditions))
            .limit(limit)
        )

        result = await db.execute(query)
        sop_items = result.scalars().all()

        # 轉換為字典格式
        return [
            {
                'id': item.id,
                'item_name': item.item_name,
                'content': item.content,
                'keywords': item.keywords,
                'trigger_keywords': item.trigger_keywords,
                'trigger_mode': item.trigger_mode,
                'next_action': item.next_action
            }
            for item in sop_items
        ]

    def check_trigger_keywords(
        self,
        user_message: str,
        trigger_keywords: Optional[List[str]]
    ) -> bool:
        """
        檢查用戶訊息是否匹配觸發關鍵字

        Args:
            user_message: 用戶訊息
            trigger_keywords: 觸發關鍵字列表

        Returns:
            是否匹配
        """
        if not trigger_keywords or not user_message:
            return False

        # 分詞處理
        message_tokens = self._tokenize(user_message)

        # 檢查每個觸發關鍵字
        for trigger_keyword in trigger_keywords:
            trigger_tokens = self._tokenize(trigger_keyword)

            # 如果所有 trigger token 都在 message 中，則匹配
            if trigger_tokens.issubset(message_tokens):
                logger.info(
                    f"觸發關鍵字匹配: '{trigger_keyword}' in '{user_message}'"
                )
                return True

        return False

    async def suggest_keywords(
        self,
        item_name: str,
        content: str,
        existing_keywords: Optional[List[str]] = None
    ) -> List[str]:
        """
        根據 SOP 名稱和內容建議關鍵字

        Args:
            item_name: SOP 項目名稱
            content: SOP 內容
            existing_keywords: 現有關鍵字

        Returns:
            建議的關鍵字列表
        """
        suggestions = set()

        # 從標題提取關鍵字
        if item_name:
            # 分詞
            title_tokens = jieba.cut(item_name)
            for token in title_tokens:
                if len(token) > 1:  # 排除單字
                    suggestions.add(token)

        # 從內容提取高頻詞（簡單實現）
        if content:
            content_tokens = list(jieba.cut(content))
            # 計算詞頻
            word_freq = {}
            for token in content_tokens:
                if len(token) > 1:  # 排除單字
                    word_freq[token] = word_freq.get(token, 0) + 1

            # 取前 5 個高頻詞
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            suggestions.update([word for word, _ in top_words])

        # 保留現有關鍵字
        if existing_keywords:
            suggestions.update(existing_keywords)

        return list(suggestions)[:10]  # 限制最多 10 個關鍵字


# 單例模式
_handler_instance = None


def get_sop_keywords_handler() -> SOPKeywordsHandler:
    """
    獲取 SOP 關鍵字處理器單例

    Returns:
        SOPKeywordsHandler 實例
    """
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = SOPKeywordsHandler()
    return _handler_instance