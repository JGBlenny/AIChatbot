"""
LLM 答案優化服務
使用 GPT 模型優化 RAG 檢索結果，生成更自然、更精準的答案
"""
import os
from typing import List, Dict, Optional
from openai import OpenAI
import time


class LLMAnswerOptimizer:
    """LLM 答案優化器"""

    def __init__(self, config: Dict = None):
        """
        初始化 LLM 答案優化器

        Args:
            config: 配置字典
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.config = config or {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 800,
            "enable_optimization": True,
            "optimize_for_confidence": ["high", "medium"],  # 只優化高/中信心度
            "fallback_on_error": True  # 錯誤時使用原始答案
        }

    def optimize_answer(
        self,
        question: str,
        search_results: List[Dict],
        confidence_level: str,
        intent_info: Dict
    ) -> Dict:
        """
        優化答案

        Args:
            question: 使用者問題
            search_results: RAG 檢索結果列表
            confidence_level: 信心度等級
            intent_info: 意圖資訊

        Returns:
            優化結果字典，包含:
            - optimized_answer: 優化後的答案
            - original_answer: 原始答案
            - optimization_applied: 是否使用了優化
            - tokens_used: 使用的 token 數
            - processing_time_ms: 處理時間
        """
        start_time = time.time()

        # 1. 檢查是否需要優化
        if not self._should_optimize(confidence_level, search_results):
            return self._create_fallback_response(search_results, start_time)

        # 2. 準備原始答案
        original_answer = self._create_original_answer(search_results)

        # 3. 嘗試 LLM 優化
        try:
            optimized_answer, tokens_used = self._call_llm(
                question=question,
                search_results=search_results,
                intent_info=intent_info
            )

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "optimized_answer": optimized_answer,
                "original_answer": original_answer,
                "optimization_applied": True,
                "tokens_used": tokens_used,
                "processing_time_ms": processing_time,
                "model": self.config["model"]
            }

        except Exception as e:
            print(f"❌ LLM 優化失敗: {e}")

            if self.config["fallback_on_error"]:
                # 錯誤時使用原始答案
                processing_time = int((time.time() - start_time) * 1000)
                return {
                    "optimized_answer": original_answer,
                    "original_answer": original_answer,
                    "optimization_applied": False,
                    "tokens_used": 0,
                    "processing_time_ms": processing_time,
                    "error": str(e)
                }
            else:
                raise

    def _should_optimize(self, confidence_level: str, search_results: List[Dict]) -> bool:
        """判斷是否應該優化"""
        if not self.config["enable_optimization"]:
            return False

        if not search_results:
            return False

        if confidence_level not in self.config["optimize_for_confidence"]:
            return False

        return True

    def _create_original_answer(self, search_results: List[Dict]) -> str:
        """建立原始答案（未優化）"""
        if not search_results:
            return ""

        best_result = search_results[0]
        return f"{best_result['title']}\n\n{best_result['content']}"

    def _create_fallback_response(self, search_results: List[Dict], start_time: float) -> Dict:
        """建立備用回應（不優化）"""
        original_answer = self._create_original_answer(search_results)
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "optimized_answer": original_answer,
            "original_answer": original_answer,
            "optimization_applied": False,
            "tokens_used": 0,
            "processing_time_ms": processing_time
        }

    def _call_llm(
        self,
        question: str,
        search_results: List[Dict],
        intent_info: Dict
    ) -> tuple[str, int]:
        """
        呼叫 LLM 優化答案

        Returns:
            (優化後的答案, 使用的 tokens 數)
        """
        # 1. 準備檢索結果上下文
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):  # 最多使用前 3 個結果
            context_parts.append(
                f"【參考資料 {i}】\n"
                f"標題：{result['title']}\n"
                f"分類：{result.get('category', 'N/A')}\n"
                f"內容：{result['content']}\n"
                f"相似度：{result['similarity']:.2f}"
            )

        context = "\n\n".join(context_parts)

        # 2. 建立優化 Prompt
        system_prompt = self._create_system_prompt(intent_info)
        user_prompt = self._create_user_prompt(question, context, intent_info)

        # 3. 呼叫 OpenAI API
        response = self.client.chat.completions.create(
            model=self.config["model"],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        optimized_answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return optimized_answer, tokens_used

    def _create_system_prompt(self, intent_info: Dict) -> str:
        """建立系統提示詞"""
        intent_type = intent_info.get('intent_type', 'knowledge')

        base_prompt = """你是一個專業、友善的客服助理。你的任務是根據知識庫的資訊，用自然、易懂的語言回答使用者的問題。

回答要求：
1. 直接回答問題，不要重複問題內容
2. 使用繁體中文，語氣親切專業
3. 資訊必須來自提供的參考資料，不要編造
4. 如有步驟或流程，請清楚列出
5. 適當使用 Markdown 格式（標題、列表）使答案更易讀
6. 保持簡潔，避免冗長
7. 如果參考資料不足以回答，請誠實說明"""

        # 根據意圖類型調整提示
        if intent_type == "knowledge":
            base_prompt += "\n8. 這是知識查詢問題，請提供清楚的說明和步驟"
        elif intent_type == "data_query":
            base_prompt += "\n8. 這是資料查詢問題，如需查詢具體資料，請說明如何查詢"
        elif intent_type == "action":
            base_prompt += "\n8. 這是操作執行問題，請說明具體操作步驟"

        return base_prompt

    def _create_user_prompt(self, question: str, context: str, intent_info: Dict) -> str:
        """建立使用者提示詞"""
        keywords = intent_info.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "無"

        prompt = f"""使用者問題：{question}

意圖類型：{intent_info.get('intent_name', '未知')}
關鍵字：{keywords_str}

參考資料：
{context}

請根據以上參考資料，用自然、友善的語氣回答使用者的問題。"""

        return prompt

    def get_optimization_stats(self, optimizations: List[Dict]) -> Dict:
        """
        計算優化統計資訊

        Args:
            optimizations: 優化結果列表

        Returns:
            統計資訊字典
        """
        if not optimizations:
            return {
                "total_optimizations": 0,
                "successful_optimizations": 0,
                "total_tokens_used": 0,
                "avg_tokens_per_optimization": 0,
                "avg_processing_time_ms": 0
            }

        total = len(optimizations)
        successful = sum(1 for o in optimizations if o.get('optimization_applied', False))
        total_tokens = sum(o.get('tokens_used', 0) for o in optimizations)
        total_time = sum(o.get('processing_time_ms', 0) for o in optimizations)

        return {
            "total_optimizations": total,
            "successful_optimizations": successful,
            "success_rate": round(successful / total, 3) if total > 0 else 0,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_optimization": round(total_tokens / successful, 1) if successful > 0 else 0,
            "avg_processing_time_ms": round(total_time / total, 1) if total > 0 else 0
        }


# 使用範例
if __name__ == "__main__":
    import asyncio

    async def test_optimizer():
        """測試 LLM 答案優化器"""
        optimizer = LLMAnswerOptimizer()

        # 模擬檢索結果
        search_results = [
            {
                "id": 1,
                "title": "退租流程說明",
                "category": "合約問題",
                "content": """# 退租流程

## 步驟說明

1. **提前通知**：請於退租日前30天以書面方式通知房東
2. **繳清費用**：確認所有租金、水電費已繳清
3. **房屋檢查**：與房東約定時間進行房屋檢查
4. **押金退還**：確認房屋狀況良好後，7個工作天內退還押金

## 注意事項
- 需提前30天通知
- 需繳清所有費用
- 房屋需恢復原狀""",
                "similarity": 0.89
            }
        ]

        intent_info = {
            "intent_name": "退租流程",
            "intent_type": "knowledge",
            "keywords": ["退租", "辦理"]
        }

        # 測試優化
        print("🔄 開始優化答案...")
        result = optimizer.optimize_answer(
            question="請問如何辦理退租手續？",
            search_results=search_results,
            confidence_level="high",
            intent_info=intent_info
        )

        print(f"\n✅ 優化完成")
        print(f"使用優化：{result['optimization_applied']}")
        print(f"Token 使用：{result['tokens_used']}")
        print(f"處理時間：{result['processing_time_ms']}ms")
        print(f"\n{'='*60}")
        print("原始答案：")
        print(result['original_answer'][:200] + "...")
        print(f"\n{'='*60}")
        print("優化後答案：")
        print(result['optimized_answer'])
        print(f"{'='*60}")

    # 執行測試
    asyncio.run(test_optimizer())
