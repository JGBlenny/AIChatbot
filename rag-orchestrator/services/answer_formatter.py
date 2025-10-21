"""
答案格式化服務
提供快速路徑和模板格式化，避免不必要的 LLM 調用
"""
from typing import List, Dict


class AnswerFormatter:
    """答案格式化器 - 用於快速路徑"""

    @staticmethod
    def format_simple_answer(search_results: List[Dict]) -> Dict:
        """
        快速路徑：直接格式化最佳答案
        適用於：極高信心度 (>= 0.85) + 內容完整

        Args:
            search_results: 檢索結果列表

        Returns:
            格式化結果字典
        """
        if not search_results:
            return {
                "answer": "抱歉，未找到相關資訊。",
                "method": "empty",
                "processing_time_ms": 0
            }

        best_result = search_results[0]
        content = best_result.get('content', '')

        # 簡單格式化：確保有適當的段落和標點
        formatted_content = AnswerFormatter._clean_content(content)

        # 如果內容很短，添加來源說明
        if len(formatted_content) < 50:
            answer = f"{formatted_content}\n\n📚 此資訊來自知識庫：{best_result.get('title', '相關知識')}"
        else:
            answer = formatted_content

        return {
            "answer": answer,
            "method": "simple",
            "processing_time_ms": 0,
            "source": best_result.get('title', ''),
            "similarity": best_result.get('similarity', 0)
        }

    @staticmethod
    def format_with_template(
        question: str,
        search_results: List[Dict],
        intent_type: str = None
    ) -> Dict:
        """
        模板格式化：使用預定義模板組織答案
        適用於：高信心度 (0.70-0.85)

        Args:
            question: 使用者問題
            search_results: 檢索結果列表
            intent_type: 意圖類型

        Returns:
            格式化結果字典
        """
        if not search_results:
            return AnswerFormatter.format_simple_answer(search_results)

        best_result = search_results[0]
        content = AnswerFormatter._clean_content(best_result.get('content', ''))

        # 根據意圖類型選擇模板
        if intent_type == 'action':
            answer = AnswerFormatter._format_action_template(question, content, best_result)
        elif intent_type == 'data_query':
            answer = AnswerFormatter._format_data_query_template(question, content, best_result)
        elif intent_type == 'knowledge':
            answer = AnswerFormatter._format_knowledge_template(question, content, best_result)
        else:
            # 預設模板
            answer = AnswerFormatter._format_default_template(question, content, best_result)

        # 如果有多個相關結果，添加參考資訊
        if len(search_results) > 1:
            related_titles = [r.get('title', '') for r in search_results[1:3]]
            if related_titles:
                answer += f"\n\n💡 相關資訊：{', '.join(related_titles)}"

        return {
            "answer": answer,
            "method": "template",
            "processing_time_ms": 0,
            "source": best_result.get('title', ''),
            "similarity": best_result.get('similarity', 0)
        }

    @staticmethod
    def _clean_content(content: str) -> str:
        """清理和格式化內容"""
        if not content:
            return ""

        # 移除多餘空白
        content = ' '.join(content.split())

        # 確保結尾有句號
        if content and not content.endswith(('。', '！', '？', '.', '!', '?')):
            content += '。'

        return content

    @staticmethod
    def _format_action_template(question: str, content: str, result: Dict) -> str:
        """行動類問題模板（例如：怎麼辦、如何做）"""
        return f"關於「{question}」，以下是處理方式：\n\n{content}\n\n📋 資料來源：{result.get('title', '知識庫')}"

    @staticmethod
    def _format_data_query_template(question: str, content: str, result: Dict) -> str:
        """資料查詢類模板（例如：多少錢、什麼時候）"""
        return f"{content}\n\n📊 資料來源：{result.get('title', '知識庫')}"

    @staticmethod
    def _format_knowledge_template(question: str, content: str, result: Dict) -> str:
        """知識類問題模板（例如：是什麼、為什麼）"""
        return f"{content}\n\n💡 了解更多：{result.get('title', '相關知識')}"

    @staticmethod
    def _format_default_template(question: str, content: str, result: Dict) -> str:
        """預設模板"""
        return f"{content}\n\n📚 資料來源：{result.get('title', '知識庫')}"

    @staticmethod
    def is_content_complete(result: Dict) -> bool:
        """
        判斷內容是否完整

        判斷標準：
        1. 內容長度 >= 30 字
        2. 包含完整句子（有句號或問號）
        3. 不是純粹的標題或關鍵字

        Args:
            result: 檢索結果

        Returns:
            是否完整
        """
        content = result.get('content', '')

        if len(content) < 30:
            return False

        # 檢查是否包含標點符號（表示是完整句子）
        has_punctuation = any(p in content for p in ['。', '！', '？', '.', '!', '?'])
        if not has_punctuation:
            return False

        # 檢查是否只是標題或關鍵字（沒有空格或太短）
        if len(content) < 50 and ' ' not in content and '，' not in content:
            return False

        return True

    @staticmethod
    def should_use_fast_path(
        confidence_score: float,
        search_results: List[Dict],
        threshold: float = 0.85
    ) -> bool:
        """
        判斷是否應該使用快速路徑

        條件：
        1. 信心度分數 >= threshold (預設 0.85)
        2. 至少有一個結果
        3. 最佳結果的內容完整

        Args:
            confidence_score: 信心度分數
            search_results: 檢索結果
            threshold: 信心度閾值

        Returns:
            是否使用快速路徑
        """
        if confidence_score < threshold:
            return False

        if not search_results:
            return False

        return AnswerFormatter.is_content_complete(search_results[0])

    @staticmethod
    def should_use_template(
        confidence_score: float,
        confidence_level: str,
        search_results: List[Dict]
    ) -> bool:
        """
        判斷是否應該使用模板格式化

        條件：
        1. 信心度等級為 high 或 medium
        2. 信心度分數在配置範圍內
        3. 有檢索結果

        Args:
            confidence_score: 信心度分數
            confidence_level: 信心度等級
            search_results: 檢索結果

        Returns:
            是否使用模板
        """
        if not search_results:
            return False

        # 允許 high 和 medium 等級使用模板
        if confidence_level not in ['high', 'medium']:
            return False

        # 不做分數範圍檢查，由 LLM Optimizer 配置控制
        return True


# 使用範例
if __name__ == "__main__":
    formatter = AnswerFormatter()

    # 測試案例 1: 快速路徑
    test_results_high = [
        {
            "id": 1,
            "title": "租金繳納規定",
            "content": "租金繳納日期為每月 5 號前，可透過銀行轉帳或臨櫃繳納。逾期將收取滯納金。",
            "similarity": 0.92
        }
    ]

    print("=" * 60)
    print("測試 1: 快速路徑（高信心度 0.92）")
    print("=" * 60)
    result1 = formatter.format_simple_answer(test_results_high)
    print(f"方法: {result1['method']}")
    print(f"答案:\n{result1['answer']}\n")

    # 測試案例 2: 模板格式化
    print("=" * 60)
    print("測試 2: 模板格式化（中等信心度 0.75）")
    print("=" * 60)
    result2 = formatter.format_with_template(
        question="冷氣壞了怎麼辦？",
        search_results=test_results_high,
        intent_type="action"
    )
    print(f"方法: {result2['method']}")
    print(f"答案:\n{result2['answer']}\n")

    # 測試案例 3: 完整度判斷
    print("=" * 60)
    print("測試 3: 內容完整度判斷")
    print("=" * 60)
    print(f"完整內容: {formatter.is_content_complete(test_results_high[0])}")
    print(f"應使用快速路徑 (0.92): {formatter.should_use_fast_path(0.92, test_results_high)}")
    print(f"應使用模板 (0.75): {formatter.should_use_template(0.75, 'high', test_results_high)}")
