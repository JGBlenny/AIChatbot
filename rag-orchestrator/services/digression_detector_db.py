"""
離題偵測器（Digression Detector）- 資料庫配置版本
負責偵測用戶是否離題或想跳出表單填寫流程

方案 B：支援多業者、多語言、動態調整
配置從資料庫 digression_config 表讀取，支援緩存
"""
from typing import Tuple, Optional, Dict
from services.embedding_utils import get_embedding_client
from datetime import datetime, timedelta
import asyncpg


class DigressionType:
    """離題類型枚舉"""
    EXPLICIT_EXIT = "explicit_exit"  # 明確退出（"取消"、"不填了"）
    QUESTION = "question"  # 用戶問問題（"為什麼"、"如何"）
    INTENT_SHIFT = "intent_shift"  # 意圖轉移（檢測到不相關的高置信度意圖）
    IRRELEVANT_RESPONSE = "irrelevant_response"  # 不相關回答


class DigressionDetectorDB:
    """離題偵測器（資料庫配置版本）"""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        初始化離題偵測器

        Args:
            db_pool: 資料庫連接池
        """
        self.db_pool = db_pool
        self.embedding_client = get_embedding_client()

        # 配置緩存
        self._config_cache = {}
        self._cache_ttl = timedelta(minutes=5)  # 緩存 5 分鐘

        # 默認配置（當資料庫查詢失敗時使用）
        self._default_exit_keywords = [
            "取消", "不填了", "算了", "不想填", "停止",
            "退出", "離開", "結束", "exit", "cancel", "stop"
        ]
        self._default_question_keywords = [
            "為什麼", "如何", "怎麼", "什麼", "哪裡",
            "多少", "幾", "嗎", "?", "？"
        ]
        self._default_thresholds = {
            "intent_shift_threshold": 0.7,
            "semantic_similarity_threshold": 0.25,
            "short_answer_length_intent": 15,
            "short_answer_length_semantic": 10
        }

    async def _load_config(self, vendor_id: int, language: str = 'zh-TW') -> Dict:
        """
        從資料庫載入配置（含緩存）

        Args:
            vendor_id: 業者 ID
            language: 語言代碼（zh-TW, en, zh-CN 等）

        Returns:
            配置字典 {
                'exit': [...],
                'question': [...],
                'thresholds': {...}
            }
        """
        # 生成緩存鍵
        cache_key = f"{vendor_id}:{language}"

        # 檢查緩存
        if cache_key in self._config_cache:
            cached_config, cached_time = self._config_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                print(f"🔧 [配置] 使用緩存配置（vendor={vendor_id}, lang={language}）")
                return cached_config

        # 從資料庫載入
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT ON (keyword_type)
                        keyword_type,
                        keywords,
                        thresholds
                    FROM digression_config
                    WHERE is_active = true
                      AND (vendor_id = $1 OR vendor_id IS NULL)
                      AND (language = $2 OR language IS NULL)
                    ORDER BY keyword_type,
                             vendor_id NULLS LAST,      -- 業者配置優先於全局配置
                             priority DESC,              -- 高優先級優先
                             created_at DESC             -- 最新配置優先
                """, vendor_id, language)

            # 解析配置
            import json
            config = {
                'exit': self._default_exit_keywords.copy(),
                'question': self._default_question_keywords.copy(),
                'thresholds': self._default_thresholds.copy()
            }

            for row in rows:
                keyword_type = row['keyword_type']

                # 處理 keywords（可能是字串或列表）
                if keyword_type == 'exit' and row['keywords']:
                    keywords_data = row['keywords']
                    if isinstance(keywords_data, str):
                        config['exit'] = json.loads(keywords_data)
                    else:
                        config['exit'] = keywords_data

                elif keyword_type == 'question' and row['keywords']:
                    keywords_data = row['keywords']
                    if isinstance(keywords_data, str):
                        config['question'] = json.loads(keywords_data)
                    else:
                        config['question'] = keywords_data

                elif keyword_type == 'thresholds' and row['thresholds']:
                    thresholds_data = row['thresholds']
                    if isinstance(thresholds_data, str):
                        config['thresholds'] = json.loads(thresholds_data)
                    else:
                        config['thresholds'] = thresholds_data

            # 緩存配置
            self._config_cache[cache_key] = (config, datetime.now())

            print(f"✅ [配置] 已載入配置（vendor={vendor_id}, lang={language}）")
            print(f"   退出關鍵字: {len(config['exit'])} 個")
            print(f"   問題關鍵字: {len(config['question'])} 個")
            print(f"   意圖轉移閾值: {config['thresholds'].get('intent_shift_threshold')}")

            return config

        except Exception as e:
            print(f"⚠️  [配置] 載入失敗，使用默認配置: {e}")
            # 返回默認配置
            return {
                'exit': self._default_exit_keywords,
                'question': self._default_question_keywords,
                'thresholds': self._default_thresholds
            }

    def clear_cache(self):
        """清空配置緩存（用於測試或強制重新載入）"""
        self._config_cache.clear()
        print("🗑️  [配置] 緩存已清空")

    async def detect(
        self,
        user_message: str,
        current_field: Dict,
        form_schema: Dict,
        intent_result: Optional[Dict] = None,
        vendor_id: int = 1,
        language: str = 'zh-TW'
    ) -> Tuple[bool, Optional[str], float]:
        """
        偵測用戶是否離題

        Args:
            user_message: 用戶輸入
            current_field: 當前欄位配置
            form_schema: 表單定義
            intent_result: 意圖分類結果（可選）
            vendor_id: 業者 ID（用於載入專屬配置）
            language: 語言代碼（用於載入對應語言的關鍵字）

        Returns:
            (is_digression, digression_type, confidence)
            - is_digression: 是否離題
            - digression_type: 離題類型
            - confidence: 置信度（0-1）
        """
        # 載入配置
        config = await self._load_config(vendor_id, language)

        # 策略 1：明確關鍵字檢測（優先級最高）
        result = self._check_explicit_keywords(user_message, config['exit'])
        if result[0]:
            return result

        # 策略 2：問題關鍵字檢測
        result = self._check_question_keywords(user_message, config['question'])
        if result[0]:
            return result

        # 策略 3：意圖轉移檢測（如果提供了意圖分類結果）
        if intent_result:
            result = self._check_intent_shift(
                intent_result,
                form_schema,
                user_message,
                config['thresholds']
            )
            if result[0]:
                return result

        # 策略 4：語義相似度檢測（與當前欄位提示的相關性）
        result = await self._check_semantic_similarity(
            user_message,
            current_field,
            config['thresholds']
        )
        if result[0]:
            return result

        # 沒有檢測到離題
        return (False, None, 0.0)

    def _check_explicit_keywords(
        self,
        user_message: str,
        exit_keywords: list
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查明確退出關鍵字

        Args:
            user_message: 用戶輸入
            exit_keywords: 退出關鍵字列表

        Returns:
            (is_digression, digression_type, confidence)
        """
        message_lower = user_message.lower()

        for keyword in exit_keywords:
            if keyword.lower() in message_lower:
                print(f"🚪 [離題偵測] 明確退出關鍵字：{keyword}")
                return (True, DigressionType.EXPLICIT_EXIT, 1.0)

        return (False, None, 0.0)

    def _check_question_keywords(
        self,
        user_message: str,
        question_keywords: list
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查問題關鍵字

        Args:
            user_message: 用戶輸入
            question_keywords: 問題關鍵字列表

        Returns:
            (is_digression, digression_type, confidence)
        """
        # 如果消息太短（< 5字），可能不是問題
        if len(user_message) < 5:
            return (False, None, 0.0)

        for keyword in question_keywords:
            if keyword in user_message:
                print(f"❓ [離題偵測] 問題關鍵字：{keyword}")
                return (True, DigressionType.QUESTION, 0.8)

        return (False, None, 0.0)

    def _check_intent_shift(
        self,
        intent_result: Dict,
        form_schema: Dict,
        user_message: str,
        thresholds: Dict
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查意圖轉移

        如果檢測到高置信度的不相關意圖，視為離題

        Args:
            intent_result: 意圖分類結果
            form_schema: 表單定義
            user_message: 用戶輸入
            thresholds: 閾值配置

        Returns:
            (is_digression, digression_type, confidence)
        """
        intent_name = intent_result.get('intent_name', '')
        confidence = intent_result.get('confidence', 0.0)

        # 意圖不明確，不判定為離題
        if intent_name == 'unclear':
            return (False, None, 0.0)

        # 從配置讀取短答案長度閾值
        short_length = thresholds.get('short_answer_length_intent', 15)

        # 如果用戶輸入很短（<= short_length 字），跳過意圖轉移檢查
        if user_message and len(user_message) <= short_length:
            print(f"ℹ️  [離題偵測] 用戶輸入較短（{len(user_message)}字），跳過意圖轉移檢查")
            return (False, None, 0.0)

        # 從配置讀取意圖轉移閾值
        intent_threshold = thresholds.get('intent_shift_threshold', 0.7)

        # 檢查是否為表單相關意圖
        trigger_intents = form_schema.get('trigger_intents') or []
        if trigger_intents and intent_name not in trigger_intents and confidence > intent_threshold:
            print(f"🔀 [離題偵測] 意圖轉移：{intent_name} (置信度: {confidence:.2f}, 閾值: {intent_threshold})")
            return (True, DigressionType.INTENT_SHIFT, confidence)

        return (False, None, 0.0)

    async def _check_semantic_similarity(
        self,
        user_message: str,
        current_field: Dict,
        thresholds: Dict
    ) -> Tuple[bool, Optional[str], float]:
        """
        檢查語義相似度（與當前欄位提示的相關性）

        如果相似度過低，可能是不相關的回答

        Args:
            user_message: 用戶輸入
            current_field: 當前欄位配置
            thresholds: 閾值配置

        Returns:
            (is_digression, digression_type, confidence)
        """
        # 從配置讀取短答案長度閾值
        short_length = thresholds.get('short_answer_length_semantic', 10)

        # 如果用戶輸入很短（<= short_length 字），跳過語義相似度檢查
        if len(user_message) <= short_length:
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

            # 從配置讀取語義相似度閾值
            similarity_threshold = thresholds.get('semantic_similarity_threshold', 0.25)

            # 相似度過低視為不相關
            if similarity < similarity_threshold:
                print(f"📉 [離題偵測] 語義相似度過低：{similarity:.3f}（閾值：{similarity_threshold}）")
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
