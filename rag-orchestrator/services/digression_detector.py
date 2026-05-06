"""
離題偵測器（Digression Detector）
負責偵測用戶是否離題或想跳出表單填寫流程

偵測策略（多層級）：
1. 明確關鍵字偵測（優先級：高）
2. 意圖轉移偵測（優先級：中）
3. 語義相似度偵測（優先級：低）
4. 連續驗證失敗（優先級：中）
"""
from typing import Tuple, Optional, Dict
from services.embedding_utils import get_embedding_client


class DigressionType:
    """離題類型枚舉"""
    EXPLICIT_EXIT = "explicit_exit"  # 明確退出（"取消"、"不填了"）
    QUESTION = "question"  # 用戶問問題（"為什麼"、"如何"）
    INTENT_SHIFT = "intent_shift"  # 意圖轉移（檢測到不相關的高置信度意圖）
    IRRELEVANT_RESPONSE = "irrelevant_response"  # 不相關回答


class DigressionDetector:
    """離題偵測器"""

    def __init__(self):
        self.embedding_client = get_embedding_client()

        # 明確退出關鍵字
        self.exit_keywords = [
            "取消", "不填了", "算了", "不想填", "停止",
            "退出", "離開", "結束", "exit", "cancel", "stop"
        ]

        # 問題關鍵字
        self.question_keywords = [
            "為什麼", "如何", "怎麼", "什麼", "哪裡",
            "多少", "幾", "嗎", "?", "？"
        ]

    async def detect(
        self,
        user_message: str,
        current_field: Dict,
        form_schema: Dict,
        intent_result: Optional[Dict] = None,
        has_images: bool = False
    ) -> Tuple[bool, Optional[str], float]:
        """
        偵測用戶是否離題

        Args:
            user_message: 用戶輸入
            current_field: 當前欄位配置
            form_schema: 表單定義
            intent_result: 意圖分類結果（可選）
            has_images: 是否包含圖片（圖片輸入不應被視為離題）

        Returns:
            (is_digression, digression_type, confidence)
            - is_digression: 是否離題
            - digression_type: 離題類型
            - confidence: 置信度（0-1）
        """
        # 策略 1：明確關鍵字檢測（優先級最高，即使有圖片仍檢查）
        result = self._check_explicit_keywords(user_message)
        if result[0]:
            return result

        # 圖片輸入：跳過語義/意圖檢查，圖片不應被視為離題
        if has_images:
            return (False, None, 0.0)

        # 策略 2：問題關鍵字檢測
        result = self._check_question_keywords(user_message)
        if result[0]:
            return result

        # 策略 3：意圖轉移檢測（如果提供了意圖分類結果）
        if intent_result:
            result = self._check_intent_shift(intent_result, form_schema, user_message)
            if result[0]:
                return result

        # 策略 4：語義相似度檢測（與當前欄位提示的相關性）
        result = await self._check_semantic_similarity(user_message, current_field)
        if result[0]:
            return result

        # 沒有檢測到離題
        return (False, None, 0.0)

    def _check_explicit_keywords(self, user_message: str) -> Tuple[bool, Optional[str], float]:
        """
        檢查明確退出關鍵字

        Args:
            user_message: 用戶輸入

        Returns:
            (is_digression, digression_type, confidence)
        """
        message_lower = user_message.lower()

        for keyword in self.exit_keywords:
            if keyword.lower() in message_lower:
                print(f"🚪 [離題偵測] 明確退出關鍵字：{keyword}")
                return (True, DigressionType.EXPLICIT_EXIT, 1.0)

        return (False, None, 0.0)

    def _check_question_keywords(self, user_message: str) -> Tuple[bool, Optional[str], float]:
        """
        檢查問題關鍵字

        Args:
            user_message: 用戶輸入

        Returns:
            (is_digression, digression_type, confidence)
        """
        # 如果消息太短（< 5字），可能不是問題
        if len(user_message) < 5:
            return (False, None, 0.0)

        for keyword in self.question_keywords:
            if keyword in user_message:
                print(f"❓ [離題偵測] 問題關鍵字：{keyword}")
                return (True, DigressionType.QUESTION, 0.8)

        return (False, None, 0.0)

    def _check_intent_shift(
        self,
        intent_result: Dict,
        form_schema: Dict,
        user_message: str = ""
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查意圖轉移

        如果檢測到高置信度的不相關意圖，視為離題

        Args:
            intent_result: 意圖分類結果
            form_schema: 表單定義
            user_message: 用戶輸入（用於判斷是否為短答案）

        Returns:
            (is_digression, digression_type, confidence)
        """
        intent_name = intent_result.get('intent_name', '')
        confidence = intent_result.get('confidence', 0.0)

        # 意圖不明確，不判定為離題
        if intent_name == 'unclear':
            return (False, None, 0.0)

        # 如果用戶輸入很短（<= 15字），可能是簡單回答（如姓名、電話、地址），跳過意圖轉移檢查
        if user_message and len(user_message) <= 15:
            print(f"ℹ️  [離題偵測] 用戶輸入較短（{len(user_message)}字），跳過意圖轉移檢查")
            return (False, None, 0.0)

        # 檢查是否為表單相關意圖
        trigger_intents = form_schema.get('trigger_intents', [])
        if intent_name not in trigger_intents and confidence > 0.7:
            print(f"🔀 [離題偵測] 意圖轉移：{intent_name} (置信度: {confidence:.2f})")
            return (True, DigressionType.INTENT_SHIFT, confidence)

        return (False, None, 0.0)

    async def _check_semantic_similarity(
        self,
        user_message: str,
        current_field: Dict
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查語義相似度（與當前欄位提示的相關性）

        如果相似度過低，可能是不相關的回答

        Args:
            user_message: 用戶輸入
            current_field: 當前欄位配置

        Returns:
            (is_digression, digression_type, confidence)
        """
        # 如果用戶輸入很短（<= 10字），可能是簡單回答（如姓名、電話），不進行語義相似度檢查
        if len(user_message) <= 10:
            print(f"ℹ️  [離題偵測] 用戶輸入較短（{len(user_message)}字），跳過語義相似度檢查")
            return (False, None, 0.0)

        try:
            # 獲取欄位提示
            field_prompt = current_field.get('prompt', '')

            # 計算語義相似度
            user_embedding = await self.embedding_client.get_embedding(user_message, verbose=False)
            prompt_embedding = await self.embedding_client.get_embedding(field_prompt, verbose=False)

            if not user_embedding or not prompt_embedding:
                # 無法計算相似度，不判定為離題
                return (False, None, 0.0)

            # 計算餘弦相似度
            similarity = self._cosine_similarity(user_embedding, prompt_embedding)

            # 相似度過低（< 0.25）視為不相關（降低閾值，更寬容）
            if similarity < 0.25:
                print(f"📉 [離題偵測] 語義相似度過低：{similarity:.3f}")
                return (True, DigressionType.IRRELEVANT_RESPONSE, 0.6)

        except Exception as e:
            print(f"⚠️  [離題偵測] 語義相似度計算失敗: {e}")
            # 計算失敗，不判定為離題
            return (False, None, 0.0)

        return (False, None, 0.0)

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """
        計算餘弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度（0-1）
        """
        import numpy as np

        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        dot_product = np.dot(vec1_np, vec2_np)
        norm_vec1 = np.linalg.norm(vec1_np)
        norm_vec2 = np.linalg.norm(vec2_np)

        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0

        return dot_product / (norm_vec1 * norm_vec2)
