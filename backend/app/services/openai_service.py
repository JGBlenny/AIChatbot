"""
OpenAI API 整合服務
"""
import json
from typing import Dict, Any, List
from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIService:
    """OpenAI API 服務"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            organization=settings.OPENAI_ORG_ID,
        )
        self.chat_model = settings.CHAT_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL

    # ========== 對話品質評估 ==========

    async def evaluate_quality(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        評估對話品質

        Returns:
            {
                "score": 8,
                "reasoning": "對話完整且內容相關...",
                "suggestions": ["可以更具體說明..."]
            }
        """
        # 將對話轉換為文字
        conv_text = self._format_conversation(conversation)

        prompt = f"""請評估以下對話的品質（1-10分）。

評估標準：
- 完整性：對話是否完整，有問有答
- 相關性：是否與產品/服務相關
- 清晰度：表達是否清晰
- 準確性：資訊是否準確
- 實用性：對其他用戶是否有幫助

對話內容：
{conv_text}

請以 JSON 格式回覆：
{{
    "score": 1-10的整數,
    "reasoning": "評分理由",
    "suggestions": ["改進建議1", "改進建議2"]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一個專業的對話品質評估專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {
                "score": 5,
                "reasoning": f"評估失敗: {str(e)}",
                "suggestions": []
            }

    # ========== 對話分類 ==========

    async def categorize_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        對話自動分類

        Returns:
            {
                "primary": "技術支援",
                "secondary": ["功能詢問", "使用教學"],
                "confidence": 0.92
            }
        """
        conv_text = self._format_conversation(conversation)

        categories = [
            "產品功能",
            "技術支援",
            "使用教學",
            "故障排除",
            "計費問題",
            "功能請求",
            "客戶投訴",
            "一般諮詢",
            "其他"
        ]

        prompt = f"""請將以下對話分類到最合適的類別。

可用類別：{', '.join(categories)}

對話內容：
{conv_text}

請以 JSON 格式回覆：
{{
    "primary": "主要分類",
    "secondary": ["次要分類1", "次要分類2"],
    "confidence": 0.0-1.0的信心度
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一個專業的對話分類專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {
                "primary": "其他",
                "secondary": [],
                "confidence": 0.0
            }

    # ========== 內容清理與改寫 ==========

    async def clean_and_rewrite(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理對話並改寫為 Q&A 格式

        Returns:
            {
                "question": "用戶問題",
                "answer": "標準答案",
                "context": "重要上下文",
                "tags": ["標籤1", "標籤2"],
                "confidence": 0.95
            }
        """
        conv_text = self._format_conversation(conversation)

        prompt = f"""請將以下對話整理為清晰的 Q&A 格式。

要求：
1. 提取核心問題和答案
2. 保持原意和重要上下文
3. 移除無關閒聊，但保留重要的情感表達
4. 修正錯別字和語法錯誤
5. 使用清晰、專業的表達方式
6. 提取相關標籤（2-5個）

對話內容：
{conv_text}

請以 JSON 格式回覆：
{{
    "question": "整理後的用戶問題",
    "answer": "整理後的標準答案",
    "context": "重要的上下文資訊（如有）",
    "tags": ["標籤1", "標籤2", "標籤3"],
    "confidence": 0.0-1.0的信心度
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一個專業的對話編輯專家，擅長將對話整理為清晰的 Q&A 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {
                "question": "",
                "answer": "",
                "context": "",
                "tags": [],
                "confidence": 0.0
            }

    # ========== 提取關鍵資訊 ==========

    async def extract_entities(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取對話中的實體、意圖、情感

        Returns:
            {
                "entities": {
                    "products": ["產品A", "產品B"],
                    "features": ["功能1"],
                    "versions": ["v2.0"]
                },
                "intents": ["詢問", "求助"],
                "sentiment": "positive",
                "keywords": ["關鍵字1", "關鍵字2"]
            }
        """
        conv_text = self._format_conversation(conversation)

        prompt = f"""請從以下對話中提取關鍵資訊。

對話內容：
{conv_text}

請以 JSON 格式回覆：
{{
    "entities": {{
        "products": ["提及的產品"],
        "features": ["提及的功能"],
        "versions": ["版本號"]
    }},
    "intents": ["用戶意圖1", "用戶意圖2"],
    "sentiment": "positive/neutral/negative",
    "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一個專業的資訊提取專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {
                "entities": {},
                "intents": [],
                "sentiment": "neutral",
                "keywords": []
            }

    # ========== 批次處理 ==========

    async def process_conversation_batch(
        self,
        conversation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        批次處理對話（品質評估 + 分類 + 清理 + 提取）

        Returns:
            {
                "quality": {...},
                "category": {...},
                "cleaned": {...},
                "entities": {...}
            }
        """
        # 平行執行所有 AI 處理
        import asyncio

        results = await asyncio.gather(
            self.evaluate_quality(conversation),
            self.categorize_conversation(conversation),
            self.clean_and_rewrite(conversation),
            self.extract_entities(conversation),
            return_exceptions=True
        )

        return {
            "quality": results[0] if not isinstance(results[0], Exception) else {},
            "category": results[1] if not isinstance(results[1], Exception) else {},
            "cleaned": results[2] if not isinstance(results[2], Exception) else {},
            "entities": results[3] if not isinstance(results[3], Exception) else {},
        }

    # ========== 向量嵌入 ==========

    async def generate_embedding(self, text: str) -> List[float]:
        """生成文字向量嵌入"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            raise Exception(f"生成嵌入失敗: {str(e)}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批次生成向量嵌入"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]

        except Exception as e:
            raise Exception(f"批次生成嵌入失敗: {str(e)}")

    # ========== 輔助方法 ==========

    def _format_conversation(self, conversation: Dict[str, Any]) -> str:
        """將對話格式化為文字"""
        if "messages" not in conversation:
            return str(conversation)

        messages = conversation.get("messages", [])
        formatted = []

        for msg in messages:
            sender = msg.get("sender", "未知")
            message = msg.get("message", "")
            timestamp = msg.get("timestamp", "")

            formatted.append(f"[{timestamp}] {sender}: {message}")

        return "\n".join(formatted)


# 單例
openai_service = OpenAIService()
