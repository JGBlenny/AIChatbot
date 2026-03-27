"""
回應類型判斷服務

使用 OpenAI API 判斷知識應採用的回應類型
"""

import json
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from models import ActionType, ActionTypeJudgment


class ActionTypeClassifier:
    """回應類型判斷器

    功能：
    1. 調用 OpenAI API 判斷回應類型
    2. 生成表單配置（form_id, pre_fill_data）
    3. 生成 API 配置（endpoint, method, params）
    4. 支援三種判斷模式（manual_only, ai_assisted, auto）
    5. 更新 loop_generated_knowledge 表
    """

    # OpenAI API 判斷 Prompt 模板
    CLASSIFICATION_PROMPT = """你是一個智能客服系統的回應類型判斷專家。

請根據以下資訊，判斷這個知識問答應該使用哪種回應類型：

**問題**：{question}

**答案**：{answer}

**可用表單清單**：
{available_forms}

**可用 API 清單**：
{available_apis}

---

**回應類型說明**：
1. **direct_answer**（純知識問答）：
   - 問題可以直接用文字回答，不需要互動
   - 例如：「租金每月幾號要繳？」→ 「每月 5 號前需繳納租金」

2. **form_fill**（表單+知識）：
   - 需要用戶填寫表單才能完成操作
   - 例如：「如何申請維修？」→ 顯示維修申請表單

3. **api_call**（API+知識）：
   - 需要調用 API 查詢即時資料
   - 例如：「我本月電費多少？」→ 調用電費查詢 API

4. **form_then_api**（表單+API+知識）：
   - 先填表單，再調用 API
   - 例如：「如何繳納租金？」→ 填寫繳費資訊 → 調用繳費 API

---

請以 JSON 格式回應，包含以下欄位：
{{
  "action_type": "direct_answer|form_fill|api_call|form_then_api",
  "confidence": 0.0-1.0,
  "reasoning": "判斷理由（繁體中文，50 字內）",
  "suggested_form_id": "表單 ID（如適用）",
  "required_form_fields": ["欄位1", "欄位2"],
  "suggested_api_id": "API ID（如適用）",
  "required_api_endpoint": "API endpoint（如適用）",
  "needs_manual_review": true|false
}}

**判斷原則**：
- 如果答案包含「請填寫」、「申請表單」→ form_fill
- 如果答案包含「即時查詢」、「目前狀態」→ api_call
- 如果答案是固定資訊（時間、規則、流程）→ direct_answer
- 信心度 < 0.8 時，設定 needs_manual_review = true
"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        db_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None,
        model: str = "gpt-4o-mini"
    ):
        """初始化分類器

        Args:
            openai_api_key: OpenAI API Key
            db_pool: PostgreSQL 連接池
            model: OpenAI 模型名稱
        """
        self.openai_api_key = openai_api_key
        self.db_pool = db_pool
        self.model = model
        self.available_forms = []  # 將從資料庫載入
        self.available_apis = []  # 將從資料庫載入

    async def classify_action_type(
        self,
        question: str,
        answer: str,
        vendor_id: int,
        mode: str = "ai_assisted"
    ) -> ActionTypeJudgment:
        """判斷回應類型

        Args:
            question: 問題內容
            answer: 答案內容
            vendor_id: 業者 ID
            mode: 判斷模式（manual_only, ai_assisted, auto）

        Returns:
            ActionTypeJudgment: 判斷結果
        """
        # 模式 1：manual_only - 不調用 AI，全部標記為需審核
        if mode == "manual_only":
            return ActionTypeJudgment(
                action_type=ActionType.DIRECT_ANSWER,
                confidence=0.0,
                reasoning="手動審核模式，需人工判斷",
                needs_manual_review=True
            )

        # 載入可用表單與 API
        await self._load_available_forms_and_apis(vendor_id)

        # 調用 OpenAI API 判斷
        judgment = await self._call_openai_api(question, answer)

        # 模式 2：ai_assisted - AI 判斷但需人工確認
        if mode == "ai_assisted":
            judgment.needs_manual_review = True

        # 模式 3：auto - 信心度 >= 0.8 時自動應用
        elif mode == "auto":
            if judgment.confidence < 0.8:
                judgment.needs_manual_review = True
            else:
                judgment.needs_manual_review = False

        return judgment

    async def _load_available_forms_and_apis(self, vendor_id: int):
        """載入業者可用的表單與 API

        從資料庫 form_schemas 和 api_endpoints 表讀取
        """
        if not self.db_pool:
            # 單元測試時使用預設清單
            self.available_forms = [
                {"form_id": "repair_form", "name": "維修申請表單"},
                {"form_id": "parking_form", "name": "停車位申請表單"},
                {"form_id": "complaint_form", "name": "客訴表單"}
            ]
            self.available_apis = [
                {"api_id": "electricity_bill", "name": "電費查詢 API", "endpoint": "/api/v1/electricity/bill"},
                {"api_id": "water_bill", "name": "水費查詢 API", "endpoint": "/api/v1/water/bill"},
                {"api_id": "rent_payment", "name": "租金繳納 API", "endpoint": "/api/v1/rent/payment"}
            ]
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 查詢表單（使用 form_schemas 表）
                cur.execute("""
                    SELECT form_id, form_name as name
                    FROM form_schemas
                    WHERE vendor_id = %s AND is_active = true
                    ORDER BY form_name
                """, (vendor_id,))
                self.available_forms = cur.fetchall()

                # 查詢 API（使用 api_endpoints 表）
                cur.execute("""
                    SELECT endpoint_id as api_id, endpoint_name as name, api_url as endpoint
                    FROM api_endpoints
                    WHERE vendor_id = %s AND is_active = true
                    ORDER BY endpoint_name
                """, (vendor_id,))
                self.available_apis = cur.fetchall()
        finally:
            self.db_pool.putconn(conn)

    async def _call_openai_api(
        self,
        question: str,
        answer: str
    ) -> ActionTypeJudgment:
        """調用 OpenAI API 進行判斷

        Args:
            question: 問題內容
            answer: 答案內容

        Returns:
            ActionTypeJudgment: 判斷結果
        """
        # 格式化可用表單與 API
        forms_text = "\n".join([
            f"- {form['form_id']}: {form['name']}"
            for form in self.available_forms
        ]) or "（無可用表單）"

        apis_text = "\n".join([
            f"- {api['api_id']}: {api['name']} ({api.get('endpoint', 'N/A')})"
            for api in self.available_apis
        ]) or "（無可用 API）"

        # 構建 Prompt
        prompt = self.CLASSIFICATION_PROMPT.format(
            question=question,
            answer=answer,
            available_forms=forms_text,
            available_apis=apis_text
        )

        # 如果沒有 API Key，使用簡單啟發式規則（Stub 模式）
        if not self.openai_api_key:
            return self._fallback_heuristic_classification(question, answer)

        # TODO: 調用 OpenAI API（實際實作）
        # 目前先使用 Stub 模式
        return self._fallback_heuristic_classification(question, answer)

    def _fallback_heuristic_classification(
        self,
        question: str,
        answer: str
    ) -> ActionTypeJudgment:
        """後備啟發式分類（當 OpenAI API 不可用時）

        簡單關鍵詞匹配邏輯
        """
        question_lower = question.lower()
        answer_lower = answer.lower()

        # 規則 1（優先）：答案包含「繳費」且提到「填寫」→ form_then_api
        if ('繳' in answer_lower or '支付' in answer_lower or '繳費' in answer_lower) and \
           ('填' in answer_lower or '表單' in answer_lower):
            return ActionTypeJudgment(
                action_type=ActionType.FORM_THEN_API,
                confidence=0.6,
                reasoning="需要先填寫資料再進行繳費",
                needs_manual_review=True
            )

        # 規則 2：答案包含「表單」、「申請」→ form_fill
        if any(keyword in answer_lower for keyword in ['表單', '申請書', '填寫']):
            # 嘗試匹配表單
            suggested_form_id = None
            for form in self.available_forms:
                if form['name'] in answer or form['form_id'] in answer_lower:
                    suggested_form_id = form['form_id']
                    break

            return ActionTypeJudgment(
                action_type=ActionType.FORM_FILL,
                confidence=0.7,
                reasoning="答案提到需要填寫表單",
                suggested_form_id=suggested_form_id,
                required_form_fields=[],
                needs_manual_review=True
            )

        # 規則 3：問題或答案包含「查詢」、「多少」、「即時」→ api_call
        if any(keyword in question_lower for keyword in ['查詢', '多少', '目前', '即時']):
            # 嘗試匹配 API
            suggested_api_id = None
            required_api_endpoint = None
            for api in self.available_apis:
                if api['name'] in answer or api['api_id'] in question_lower:
                    suggested_api_id = api['api_id']
                    required_api_endpoint = api.get('endpoint')
                    break

            # 特殊判斷：電費、水費
            if '電費' in question or '電費' in answer:
                suggested_api_id = "electricity_bill"
                required_api_endpoint = "/api/v1/electricity/bill"
            elif '水費' in question or '水費' in answer:
                suggested_api_id = "water_bill"
                required_api_endpoint = "/api/v1/water/bill"

            return ActionTypeJudgment(
                action_type=ActionType.API_CALL,
                confidence=0.7,
                reasoning="問題需要查詢即時資料",
                suggested_api_id=suggested_api_id,
                required_api_endpoint=required_api_endpoint,
                needs_manual_review=True
            )

        # 預設：direct_answer
        return ActionTypeJudgment(
            action_type=ActionType.DIRECT_ANSWER,
            confidence=0.8,
            reasoning="固定資訊，直接回答即可",
            needs_manual_review=False
        )

    async def update_knowledge_action_type(
        self,
        loop_knowledge_id: int,
        judgment: ActionTypeJudgment
    ):
        """更新 loop_generated_knowledge 表的 action_type 欄位

        Args:
            loop_knowledge_id: 迴圈知識 ID
            judgment: 判斷結果
        """
        if not self.db_pool:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 準備 ai_judgment_metadata
                metadata = {
                    "confidence": judgment.confidence,
                    "reasoning": judgment.reasoning,
                    "needs_manual_review": judgment.needs_manual_review,
                    "model": self.model
                }

                # 準備 form_config
                form_config = None
                if judgment.action_type in [ActionType.FORM_FILL, ActionType.FORM_THEN_API]:
                    form_config = {
                        "form_id": judgment.suggested_form_id,
                        "required_fields": judgment.required_form_fields or []
                    }

                # 準備 api_config
                api_config = None
                if judgment.action_type in [ActionType.API_CALL, ActionType.FORM_THEN_API]:
                    api_config = {
                        "api_id": judgment.suggested_api_id,
                        "endpoint": judgment.required_api_endpoint,
                        "method": "POST",
                        "params": {}
                    }

                # 更新資料庫
                cur.execute("""
                    UPDATE loop_generated_knowledge
                    SET
                        action_type = %s,
                        form_id = %s,
                        form_config = %s,
                        api_config = %s,
                        ai_judgment_metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    judgment.action_type.value,
                    judgment.suggested_form_id,
                    psycopg2.extras.Json(form_config) if form_config else None,
                    psycopg2.extras.Json(api_config) if api_config else None,
                    psycopg2.extras.Json(metadata),
                    loop_knowledge_id
                ))

                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    async def batch_classify(
        self,
        loop_id: int,
        iteration: int,
        vendor_id: int,
        mode: str = "ai_assisted"
    ) -> Dict:
        """批次判斷某次迭代生成的所有知識

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            vendor_id: 業者 ID
            mode: 判斷模式

        Returns:
            Dict: 統計資訊
        """
        if not self.db_pool:
            return {"total": 0, "classified": 0}

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 查詢待分類的知識
                cur.execute("""
                    SELECT id, question, answer
                    FROM loop_generated_knowledge
                    WHERE loop_id = %s
                      AND iteration = %s
                      AND action_type IS NULL
                    ORDER BY id
                """, (loop_id, iteration))

                knowledge_list = cur.fetchall()

                if not knowledge_list:
                    return {"total": 0, "classified": 0}

                # 逐條分類
                classified_count = 0
                for knowledge in knowledge_list:
                    judgment = await self.classify_action_type(
                        question=knowledge['question'],
                        answer=knowledge['answer'],
                        vendor_id=vendor_id,
                        mode=mode
                    )

                    await self.update_knowledge_action_type(
                        loop_knowledge_id=knowledge['id'],
                        judgment=judgment
                    )

                    classified_count += 1

                return {
                    "total": len(knowledge_list),
                    "classified": classified_count
                }

        finally:
            self.db_pool.putconn(conn)
