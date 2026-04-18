"""
查詢改寫服務 (Query Rewriter)
用 LLM 將租戶口語查詢改寫為更貼近 SOP item_name 的檢索用語，
提升向量檢索的匹配率。

成本：~$0.001/次（gpt-3.5-turbo, ~200 tokens I/O）
延遲：~300-500ms
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    查詢改寫器

    將租戶的口語化問題改寫為更精確的物業管理用語，
    讓向量檢索更容易匹配到正確的 SOP 項目。

    範例：
        「垃圾怎麼分」→「資源回收分類方式」
        「冷氣壞了」→「冷氣故障報修」
        「怎麼繳房租」→「租金繳納方式」
    """

    REWRITE_PROMPT = """你是物業管理查詢改寫助手。將租戶的口語化問題改寫為更精確的物業管理用語。

規則：
1. 保留原始意圖，不要改變問題的意思
2. 使用物業管理的正式用語（如：報修、繳納、申請、規範）
3. 補充隱含的關鍵詞（如：「冷氣壞了」→ 加入「故障」「報修」）
4. 輸出 1-2 個改寫版本，用換行分隔
5. 每個版本控制在 15 字以內
6. 只輸出改寫結果，不要解釋

範例：
輸入：垃圾怎麼分
輸出：
資源回收分類方式
垃圾分類規範

輸入：冷氣壞了怎麼辦
輸出：
冷氣故障報修
空調維修申請

輸入：可以養狗嗎
輸出：
寵物飼養規範
養寵物規定"""

    def __init__(self):
        self.enabled = os.getenv("ENABLE_QUERY_REWRITE", "false").lower() == "true"
        self.model = os.getenv("QUERY_REWRITE_MODEL", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
        self.temperature = float(os.getenv("QUERY_REWRITE_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("QUERY_REWRITE_MAX_TOKENS", "100"))
        self._provider = None

        if self.enabled:
            try:
                from .llm_provider import get_llm_provider
                self._provider = get_llm_provider(service_name="query_rewriter")
                logger.info(f"✅ Query Rewriter 已啟用（model={self.model}）")
            except Exception as e:
                logger.warning(f"⚠️ Query Rewriter 初始化失敗: {e}")
                self.enabled = False

    def rewrite(self, query: str) -> list[str]:
        """
        改寫查詢，回傳改寫後的查詢列表。

        Args:
            query: 原始查詢

        Returns:
            改寫後的查詢列表（不含原始查詢）。
            若改寫失敗或未啟用，回傳空列表。
        """
        if not self.enabled or not self._provider:
            return []

        # 太短的查詢不改寫（單字、打招呼等）
        if len(query.strip()) < 3:
            return []

        try:
            result = self._provider.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.REWRITE_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = result.get("content", "").strip()
            if not content:
                return []

            # 解析改寫結果（每行一個）
            rewrites = []
            for line in content.split("\n"):
                line = line.strip()
                if line and line != query:
                    rewrites.append(line)

            if rewrites:
                logger.info(f"🔄 Query Rewrite: 「{query}」→ {rewrites}")

            return rewrites

        except Exception as e:
            logger.warning(f"⚠️ Query Rewrite 失敗: {e}")
            return []


# 全局實例
_query_rewriter: Optional[QueryRewriter] = None


def get_query_rewriter() -> QueryRewriter:
    """取得 QueryRewriter 單例"""
    global _query_rewriter
    if _query_rewriter is None:
        _query_rewriter = QueryRewriter()
    return _query_rewriter
