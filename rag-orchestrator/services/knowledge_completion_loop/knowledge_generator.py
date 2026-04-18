"""
知識生成服務

使用 OpenAI API 生成知識內容，包含成本追蹤與錯誤處理
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from openai import OpenAI, AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIConnectionError
import httpx

# 編造內容檢測正則
_FABRICATED_PHONE_RE = re.compile(r'0[0-9]{1,3}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}')
_FABRICATED_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
_FABRICATED_URL_RE = re.compile(r'https?://[^\s]+')
_BANNED_TERMS = ['專屬管家', '客服專線', '客服電話']

# 模板變數佔位符偵測（scope=vendor 時使用）
_TEMPLATE_VAR_RE = re.compile(r'\{\{(\w+)\}\}')


class KnowledgeGeneratorClient:
    """知識生成器客戶端

    功能：
    1. 調用 OpenAI API 生成知識答案
    2. Prompt 工程（包含上下文、意圖、表單/API資訊）
    3. 批次生成（並發處理）
    4. 成本追蹤（記錄 token 使用量）
    5. 錯誤處理與重試
    6. 持久化到 loop_generated_knowledge 表
    """

    # OpenAI 知識生成 Prompt 模板
    KNOWLEDGE_GENERATION_PROMPT = """你是包租代管公司的資深客服，正在回答房客的問題。
回答對象是房客（租客），從房客的權益和需求角度回答。如果問題涉及稅務、費用、權益，重點說明房客可以享有的權利和優惠。

**房客問**：{question}

**失敗原因**：{failure_reason}
**優先級**：{priority}
**回應類型**：{suggested_action_type}
**意圖**：{intent_name}
**業者類型**：{vendor_type}

**現有相似知識（參考用）**：
{existing_knowledge}

{available_api_forms_section}

---

**回答規則**：

1. **你是客服在跟客人對話**，語氣自然親切
2. **第一句直接回答**，不要鋪陳或開場白
3. **只寫你確定的事實**，不確定的就說「請聯繫您的管理師確認」
4. 如果是 api_call 類型，回答中要告知客人「請提供您的物件地址，我幫您查詢」（引導進入表單收集資訊）
5. 繁體中文，100-300 字

**絕對禁止**：
- ❌ 編造電話號碼（如 0800-123-456、02-XXXX-XXXX）、Email、網址 — 任何數字格式的電話都不行
- ❌ 使用「專屬管家」「客服專線」「客服人員」等稱呼，統一用「管理師」
- ❌ 編造具體數字（天數、金額、百分比），不確定就不要寫
- ❌ 使用「在包租代管的過程中」「至關重要」「以下是關於...的說明」等廢話
- ❌ 回答「包租代管公司通常...」這種泛泛而談，要具體回答客人的問題
- ❌ 使用「SOP」「標準作業流程」等術語

**好的回答**：「押金會在退租點交完成後 30 天內退還到您的帳戶，如有扣款會提前告知明細。」
**不好的回答**：「在包租代管公司中，押金的退還是一個重要環節。通常包租代管公司會根據合約規定處理押金退還事宜。」

---

請以 JSON 格式回應：
{{
  "topic": "精簡主題標題（2-6字，例如：繳費紀錄、退租流程、押金退還、租金補助）",
  "answer": "客服回答內容",
  "keywords": ["搜尋關鍵字1", "關鍵字2", "關鍵字3", "問法變體1", "問法變體2"],
  "confidence_explanation": "答案依據（50字內）",
  "needs_verification": false
}}

**topic 規則**：提取問題的核心主題，不是問句。
- 「租客如何看自己的繳費紀錄？」→ "繳費紀錄"
- 「請問客服電話是多少？」→ "客服聯繫方式"
- 「逾期租金會通知嗎？」→ "逾期租金通知"
- 「我想找房」→ "找房服務"

**keywords 規則**：包含問題的各種問法變體，讓搜尋能命中。
- topic "繳費紀錄" → keywords: ["繳費紀錄", "繳費記錄", "付款紀錄", "哪裡看帳單", "查帳"]

不確定答案正確性時，設 needs_verification = true。只輸出 JSON。
"""

    async def _verify_content_quality(self, question: str, content: str) -> Dict:
        """用第二次 AI call 驗證生成內容的品質

        檢查三項：編造資訊、空泛、是否對所有租客適用

        Args:
            question: 原始問題
            content: 生成的內容

        Returns:
            {"passed": bool, "reasons": List[str]}
        """
        if not self.async_client:
            return {"passed": True, "reasons": []}

        prompt = (
            "你是品質審查員，檢查以下 AI 生成的知識內容是否合格。\n\n"
            f"**原始問題**：{question}\n\n"
            f"**生成內容**：\n{content}\n\n"
            "**檢查項目**（全部通過才合格）：\n\n"
            "1. **是否編造資訊？**\n"
            "   - 是否包含看起來像真實但可能是編造的電話號碼、Email、網址？\n"
            "   - 是否編造了具體的天數、金額、百分比等數字？（如「30天內退還」「扣除10%」）\n"
            "   - 注意：「請聯繫管理師確認」不算編造\n\n"
            "2. **是否空泛？**\n"
            "   - 內容是否只是在重複問題或說廢話？\n"
            "   - 去掉「請聯繫管理師」等話，剩下的內容是否有實質資訊？\n"
            "   - 實質內容是否少於 30 字？\n\n"
            "3. **是否完全無法通用？**\n"
            "   - 注意：業務流程、政策規範、操作說明本質上是通用的，即使細節因業者而異也算通用\n"
            "   - 只有回答明確針對「某一個特定租客」或「某一個特定物件」的個人資料才算不通用\n"
            "   - 例如「您的租金是 15,000 元」不通用，但「租金繳費方式有匯款和信用卡」是通用的\n"
            "   - 寧可判定為通用，不要過度攔截\n\n"
            '**輸出 JSON**：\n'
            '{\n'
            '  "fabricated": false,\n'
            '  "vague": false,\n'
            '  "not_universal": false,\n'
            '  "passed": true,\n'
            '  "reasons": []\n'
            '}\n\n'
            "如果任何一項為 true，passed 必須為 false，並在 reasons 中說明原因。\n"
            "只輸出 JSON。"
        )

        try:
            response = await self.async_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            if self.cost_tracker:
                await self.cost_tracker.track_api_call(
                    model="gpt-4o-mini",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    operation='quality_verification'
                )

            result = json.loads(response.choices[0].message.content)
            return {
                "passed": result.get("passed", True),
                "reasons": result.get("reasons", [])
            }
        except Exception as e:
            print(f"   ⚠️  品質驗證失敗，預設通過: {e}")
            return {"passed": True, "reasons": []}

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        db_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None,
        model: str = "gpt-4o-mini",
        cost_tracker=None
    ):
        """初始化知識生成器

        Args:
            openai_api_key: OpenAI API Key
            db_pool: PostgreSQL 連接池
            model: OpenAI 模型名稱
            cost_tracker: 成本追蹤器
        """
        self.openai_api_key = openai_api_key
        self.db_pool = db_pool
        self.model = model
        self.cost_tracker = cost_tracker
        self.embedding_api_url = os.getenv('EMBEDDING_API_URL', 'http://aichatbot-embedding-api:5000/api/v1/embeddings')
        self._api_forms_cache = None  # API 查詢表單快取

        # 初始化 OpenAI 客戶端
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
            self.async_client = AsyncOpenAI(api_key=openai_api_key)
        else:
            self.client = None
            self.async_client = None

    def _load_api_forms(self) -> List[Dict]:
        """從資料庫載入 API 查詢表單清單（快取）"""
        if self._api_forms_cache is not None:
            return self._api_forms_cache

        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT form_id, form_name, description, fields::text
                FROM form_schemas
                WHERE is_active = true AND on_complete_action = 'call_api'
                ORDER BY id
            """)
            rows = cur.fetchall()
            forms = []
            for row in rows:
                field_names = []
                try:
                    import json as _json
                    fields = _json.loads(row[3]) if row[3] else []
                    field_names = [f.get('field_label', f.get('field_name', '')) for f in fields]
                except (ValueError, TypeError):
                    pass
                forms.append({
                    'form_id': row[0],
                    'form_name': row[1],
                    'description': row[2] or '',
                    'field_names': field_names,
                })
            self._api_forms_cache = forms
            return forms
        finally:
            self.db_pool.putconn(conn)

    def _build_available_api_forms_section(self) -> str:
        """組裝 API 查詢表單清單文字，供 Knowledge prompt 注入"""
        forms = self._load_api_forms()
        if not forms:
            return ""

        lines = [
            "**系統可用的 API 查詢表單（參考用）**：",
            "如果客人的問題屬於以下查詢類型，回答時引導客人提供所需資訊。",
            ""
        ]
        for f in forms:
            fields_str = "、".join(f['field_names'][:4]) if f['field_names'] else ''
            desc = f"（{f['description']}）" if f['description'] else ''
            lines.append(f"- `{f['form_id']}` → {f['form_name']}{desc}（需提供：{fields_str}）")
        lines.append("")
        return "\n".join(lines)

    async def generate_knowledge(
        self,
        loop_id: int,
        gaps: List[Dict],
        action_type_judgments: Dict[int, Dict],
        iteration: int,
        vendor_id: int = 1
    ) -> List[Dict]:
        """批次生成知識

        Args:
            loop_id: 迴圈 ID
            gaps: 知識缺口列表
            action_type_judgments: 缺口 ID 到回應類型判斷的映射
            iteration: 迭代次數
            vendor_id: 業者 ID

        Returns:
            List[Dict]: 生成的知識列表（已儲存到資料庫）
        """
        if not gaps:
            return []

        # 如果沒有 OpenAI API Key，使用 Stub 模式
        if not self.openai_api_key or not self.async_client:
            return await self._stub_generate_knowledge(
                loop_id, gaps, action_type_judgments, iteration
            )

        # 批次並發生成知識
        tasks = []
        for gap in gaps:
            task = self._generate_single_knowledge(
                gap=gap,
                action_type_judgment=action_type_judgments.get(gap["gap_id"], {}),
                vendor_id=vendor_id
            )
            tasks.append(task)

        # 並發執行（限制並發數為 5）
        results = []
        for i in range(0, len(tasks), 5):
            batch = tasks[i:i+5]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)

        # 過濾錯誤結果和被攔截的結果（None）
        generated_knowledge = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                import traceback
                print(f"⚠️  知識生成失敗 (gap_id={gaps[i]['gap_id']}): {result}")
                traceback.print_exception(type(result), result, result.__traceback__)
                continue
            if result is None:
                continue
            generated_knowledge.append(result)

        # 持久化到資料庫
        if self.db_pool:
            saved_knowledge = await self._save_to_database(
                loop_id=loop_id,
                iteration=iteration,
                knowledge_list=generated_knowledge,
                gaps=gaps,
                action_type_judgments=action_type_judgments
            )

            # 🔍 記錄重複檢測統計
            await self._log_duplicate_detection_stats(
                loop_id=loop_id,
                iteration=iteration,
                knowledge_type='knowledge',
                generated_items=saved_knowledge
            )

            return saved_knowledge

        return generated_knowledge

    async def _generate_single_knowledge(
        self,
        gap: Dict,
        action_type_judgment: Dict,
        vendor_id: int
    ) -> Dict:
        """生成單個知識

        Args:
            gap: 知識缺口
            action_type_judgment: 回應類型判斷（可能是 Dict 或 ActionTypeJudgment 物件）
            vendor_id: 業者 ID

        Returns:
            Dict: 生成的知識
        """
        # 處理 action_type_judgment：可能是 ActionTypeJudgment 物件或空字典
        # 統一轉換為可安全存取的格式
        from .models import ActionTypeJudgment
        if isinstance(action_type_judgment, ActionTypeJudgment):
            action_type = action_type_judgment.action_type.value
        elif isinstance(action_type_judgment, dict):
            action_type = action_type_judgment.get("action_type", "direct_answer")
        else:
            action_type = "direct_answer"

        # 獲取現有相似知識（作為參考）
        existing_knowledge = await self._get_similar_knowledge(
            question=gap["question"],
            vendor_id=vendor_id,
            top_k=3
        )

        # 構建 Prompt
        prompt = self._build_prompt(
            gap=gap,
            action_type_judgment=action_type_judgment,
            existing_knowledge=existing_knowledge,
            vendor_id=vendor_id
        )

        # 調用 OpenAI API
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個專業的知識庫內容撰寫專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            # 解析回應
            content = response.choices[0].message.content
            result = json.loads(content)

            # 追蹤成本
            if self.cost_tracker:
                await self.cost_tracker.track_api_call(
                    operation="knowledge_generation",
                    model=self.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens
                )

            # 後處理品質檢查：攔截編造內容
            answer_text = result.get("answer", "")
            fabricated = []
            if _FABRICATED_PHONE_RE.search(answer_text):
                fabricated.append('電話號碼')
            if _FABRICATED_EMAIL_RE.search(answer_text):
                fabricated.append('Email')
            if _FABRICATED_URL_RE.search(answer_text):
                fabricated.append('網址')
            if fabricated:
                print(f"   ⛔ 攔截知識（內容包含編造的 {', '.join(fabricated)}）: {gap['question']}")
                return None
            # 替換禁用稱呼
            for term in _BANNED_TERMS:
                if term in answer_text:
                    result['answer'] = result['answer'].replace(term, '管理師')
                    print(f"   🔄 已將「{term}」替換為「管理師」")

            # 品質檢查：標記空泛回答（不攔截，讓人工審核決定）
            content_stripped = re.sub(r'(請|可以|建議|隨時).*?(聯繫|聯絡|詢問|洽詢).*?管理師.*', '', result['answer'])
            content_stripped = re.sub(r'(如果|若).*?(問題|疑問|需要).*', '', content_stripped)
            meaningful_chars = len(content_stripped.strip())
            if meaningful_chars < 30:
                print(f"   ⚠️  知識內容偏短（{meaningful_chars} 字），標記待人工審核: {gap['question']}")

            # 🔍 AI 品質驗證（第二次 AI call）
            quality_result = await self._verify_content_quality(
                question=gap["question"],
                content=result.get("answer", "")
            )
            if not quality_result["passed"]:
                reasons = ", ".join(quality_result["reasons"])
                print(f"   ⛔ 品質驗證未通過: {gap['question'][:30]}... — {reasons}")
                return None

            # 使用 AI 生成的 topic 作為精簡標題，原始問題加入 keywords
            topic = result.get("topic", "").strip()
            if not topic:
                topic = gap["question"]  # fallback

            keywords = result.get("keywords", [])
            # 確保原始問題也在 keywords 中（擴充搜尋覆蓋）
            if gap["question"] not in keywords:
                keywords.append(gap["question"])

            # 從 gap metadata 讀取 category 與 scope（向後相容：預設 None / "global"）
            category = self._resolve_category(gap)
            scope = gap.get("scope", "global")

            # scope=vendor 時，標記為模板並提取佔位符變數
            is_template = (scope == "vendor")
            template_vars = self._extract_template_vars(answer_text) if is_template else None

            return {
                "gap_id": gap["gap_id"],
                "question": topic,
                "original_question": gap["question"],
                "answer": result.get("answer", ""),
                "keywords": keywords,
                "confidence_explanation": result.get("confidence_explanation", ""),
                "needs_verification": result.get("needs_verification", False),
                "action_type": action_type,
                "category": category,
                "scope": scope,
                "is_template": is_template,
                "template_vars": template_vars,
            }

        except RateLimitError as e:
            print(f"⚠️  OpenAI API 速率限制: {e}")
            await asyncio.sleep(5)  # 等待 5 秒後重試
            raise

        except APIConnectionError as e:
            print(f"⚠️  OpenAI API 連線錯誤: {e}")
            raise

        except OpenAIError as e:
            print(f"❌ OpenAI API 錯誤: {e}")
            raise

        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗: {e}")
            print(f"   原始回應: {content}")
            raise

    @staticmethod
    def _resolve_category(gap: Dict) -> Optional[str]:
        """從 gap metadata 取得 category（向後相容）

        優先使用 gap["category"]，其次由 dimension 推導：
        - "general" → "general"
        - "industry" → "industry"
        - 其他 / 缺失 → None
        """
        if gap.get("category"):
            return gap["category"]
        dimension = gap.get("dimension")
        if dimension in ("general", "industry"):
            return dimension
        return None

    @staticmethod
    def _extract_template_vars(text: str) -> Optional[List[Dict[str, Any]]]:
        """掃描文字中的 {{variable}} 佔位符，組裝 template_vars

        Returns:
            佔位符列表，如 [{"name": "company_phone", "required": True}]；
            找不到任何佔位符時回傳 None。
        """
        matches = _TEMPLATE_VAR_RE.findall(text)
        if not matches:
            return None
        # 去重但保留首次出現順序
        seen: set = set()
        template_vars: List[Dict[str, Any]] = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                template_vars.append({"name": m, "required": True})
        return template_vars

    @staticmethod
    def _build_category_context(category: Optional[str], scope: str) -> str:
        """根據 category 與 scope 產生提示前綴，引導 LLM 生成正確風格的回答

        Returns:
            提示前綴字串；無需特殊引導時回傳空字串。
        """
        if scope == "vendor":
            return (
                "【知識類型：業者專屬知識】\n"
                "這是業者專屬的知識，回答中需要業者才能提供的具體資訊（如電話、地址、收費標準）"
                "請使用 {{變數名稱}} 作為佔位符，例如 {{company_phone}}、{{service_email}}。\n"
            )
        if category == "industry":
            return (
                "【知識類型：產業知識】\n"
                "這是包租代管產業的專業知識，請從產業實務角度回答，"
                "說明業界慣例與規則，避免過於泛泛的租屋常識。\n"
            )
        if category == "general":
            return (
                "【知識類型：一般租屋知識】\n"
                "這是一般性租屋知識，請根據台灣租賃相關法規與常識回答，"
                "確保內容穩定正確、適用於所有租客。\n"
            )
        return ""

    def _build_prompt(
        self,
        gap: Dict,
        action_type_judgment: Dict,
        existing_knowledge: List[Dict],
        vendor_id: int
    ) -> str:
        """構建知識生成 Prompt

        Args:
            gap: 知識缺口
            action_type_judgment: 回應類型判斷
            existing_knowledge: 現有相似知識
            vendor_id: 業者 ID

        Returns:
            str: 完整的 Prompt
        """
        # 處理 action_type_judgment：可能是 ActionTypeJudgment 物件或字典
        from .models import ActionTypeJudgment
        if isinstance(action_type_judgment, ActionTypeJudgment):
            suggested_action_type = action_type_judgment.action_type.value
        elif isinstance(action_type_judgment, dict):
            suggested_action_type = action_type_judgment.get("action_type", "direct_answer")
        else:
            suggested_action_type = "direct_answer"

        # 格式化現有知識
        if existing_knowledge:
            knowledge_text = "\n".join([
                f"{i+1}. Q: {k['question']}\n   A: {k['answer'][:100]}..."
                for i, k in enumerate(existing_knowledge)
            ])
        else:
            knowledge_text = "（無相似知識）"

        # 填充模板（注入可用 API 查詢表單清單）
        available_api_forms_section = self._build_available_api_forms_section()
        prompt = self.KNOWLEDGE_GENERATION_PROMPT.format(
            question=gap["question"],
            failure_reason=gap.get("failure_reason", "no_match"),
            priority=gap.get("priority", "p1"),
            suggested_action_type=suggested_action_type,
            intent_name=gap.get("intent_name", "未知"),
            vendor_type="包租代管公司",
            existing_knowledge=knowledge_text,
            available_api_forms_section=available_api_forms_section
        )

        # 注入 category context，讓 LLM 區分一般知識 vs 產業知識
        category = self._resolve_category(gap)
        scope = gap.get("scope", "global")
        category_context = self._build_category_context(category, scope)
        if category_context:
            prompt = category_context + "\n" + prompt

        return prompt

    async def _get_similar_knowledge(
        self,
        question: str,
        vendor_id: int,
        top_k: int = 3
    ) -> List[Dict]:
        """獲取相似的現有知識（作為生成參考）

        Args:
            question: 問題
            vendor_id: 業者 ID
            top_k: 返回前 K 個相似知識

        Returns:
            List[Dict]: 相似知識列表
        """
        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 簡單的關鍵字匹配（實際應使用向量相似度）
                # TODO: 整合 embedding 向量搜尋
                cur.execute("""
                    SELECT question_summary as question, answer
                    FROM knowledge_base
                    WHERE %s = ANY(vendor_ids)
                      AND question_summary ILIKE %s
                    LIMIT %s
                """, (vendor_id, f"%{question[:20]}%", top_k))

                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            self.db_pool.putconn(conn)

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """使用 Embedding API 生成向量

        Args:
            text: 要生成向量的文本

        Returns:
            向量列表或 None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.embedding_api_url,
                    json={"text": text}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get('embedding')
                else:
                    print(f"   ⚠️  Embedding API 錯誤: {response.status_code}")
                    return None
        except Exception as e:
            print(f"   ⚠️  生成 embedding 失敗: {e}")
            return None

    async def _detect_duplicate_knowledge(
        self,
        vendor_id: int,
        question_summary: str
    ) -> Optional[Dict]:
        """使用 pgvector 向量相似度檢測重複的一般知識

        Args:
            vendor_id: 業者 ID
            question_summary: 問題摘要

        Returns:
            重複檢測結果，格式：
            {
                "detected": bool,
                "items": [
                    {
                        "id": int,
                        "source_table": str,  # "knowledge_base" or "loop_generated_knowledge"
                        "question_summary": str,
                        "similarity_score": float
                    }
                ]
            }
        """
        # 生成問題摘要的 embedding
        query_embedding = await self._generate_embedding(question_summary)

        if not query_embedding:
            print("   ⚠️  無法生成 embedding，跳過重複檢測")
            return {"detected": False, "items": []}

        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            similar_items = []

            # 檢測 1: 搜尋 knowledge_base 表（正式知識）
            # 使用 pgvector 的 cosine similarity (<=> 運算子)
            # 閾值：similarity > 0.90 視為相似（距離 < 0.10）
            cur.execute("""
                SELECT
                    id,
                    question_summary,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM knowledge_base
                WHERE vendor_ids @> ARRAY[%s]
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) > 0.90
                ORDER BY embedding <=> %s::vector ASC
                LIMIT 3
            """, (query_embedding, vendor_id, query_embedding, query_embedding))

            for row in cur.fetchall():
                similar_items.append({
                    "id": row['id'],
                    "source_table": "knowledge_base",
                    "question_summary": row['question_summary'],
                    "similarity_score": float(row['similarity_score'])
                })

            # 檢測 2: 搜尋 loop_generated_knowledge 表（待審核知識）
            cur.execute("""
                SELECT
                    id,
                    question,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM loop_generated_knowledge
                WHERE knowledge_type IS NULL
                  AND status IN ('pending', 'approved')
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) > 0.90
                ORDER BY embedding <=> %s::vector ASC
                LIMIT 3
            """, (query_embedding, query_embedding, query_embedding))

            for row in cur.fetchall():
                similar_items.append({
                    "id": row['id'],
                    "source_table": "loop_generated_knowledge",
                    "question_summary": row['question'],
                    "similarity_score": float(row['similarity_score'])
                })

            # 按相似度排序，取前 3 個
            similar_items.sort(key=lambda x: x['similarity_score'], reverse=True)
            similar_items = similar_items[:3]

            if similar_items:
                print(f"   🔍 檢測到 {len(similar_items)} 個相似知識:")
                for item in similar_items:
                    print(f"      - [{item['source_table']}] {item['question_summary'][:50]}... (相似度: {item['similarity_score']:.1%})")

            return {
                "detected": len(similar_items) > 0,
                "items": similar_items
            }

        except Exception as e:
            print(f"   ⚠️  重複檢測失敗: {e}")
            import traceback
            traceback.print_exc()
            return {"detected": False, "items": []}
        finally:
            cur.close()
            self.db_pool.putconn(conn)

    async def _log_duplicate_detection_stats(
        self,
        loop_id: int,
        iteration: int,
        knowledge_type: str,
        generated_items: List[Dict]
    ) -> None:
        """記錄重複檢測統計到 loop_execution_logs

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            knowledge_type: 知識類型 ('sop' or 'knowledge')
            generated_items: 生成的知識項目列表
        """
        if not self.db_pool:
            return

        # 收集統計資訊
        total_generated = len(generated_items)
        detected_duplicates = sum(
            1 for item in generated_items
            if item.get('similar_knowledge') and item.get('similar_knowledge', {}).get('detected', False)
        )

        # 收集相似度分布
        similarity_scores = []
        for item in generated_items:
            similar_knowledge = item.get('similar_knowledge')
            if similar_knowledge and similar_knowledge.get('detected'):
                for similar_item in similar_knowledge.get('items', []):
                    similarity_scores.append(similar_item.get('similarity_score', 0))

        # 計算相似度統計
        stats = {
            'total_generated': total_generated,
            'detected_duplicates': detected_duplicates,
            'duplicate_rate': f"{detected_duplicates / total_generated * 100:.1f}%" if total_generated > 0 else "0%",
            'similarity_scores': {
                'count': len(similarity_scores),
                'avg': sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0,
                'max': max(similarity_scores) if similarity_scores else 0,
                'min': min(similarity_scores) if similarity_scores else 0
            }
        }

        print(f"\n🔍 重複檢測統計 ({knowledge_type}):")
        print(f"   總生成數：{stats['total_generated']}")
        print(f"   檢測到重複：{stats['detected_duplicates']} ({stats['duplicate_rate']})")
        if similarity_scores:
            print(f"   相似度範圍：{stats['similarity_scores']['min']:.1%} - {stats['similarity_scores']['max']:.1%}")
            print(f"   平均相似度：{stats['similarity_scores']['avg']:.1%}")

        # 記錄到資料庫
        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO loop_execution_logs (
                    loop_id,
                    event_type,
                    event_data,
                    created_at
                ) VALUES (%s, %s, %s, NOW())
            """, (
                loop_id,
                f'duplicate_detection_{knowledge_type}',
                json.dumps(stats, ensure_ascii=False)
            ))
            conn.commit()
            print(f"   ✅ 統計已記錄到 loop_execution_logs")
        except Exception as e:
            conn.rollback()
            print(f"   ⚠️  統計記錄失敗: {e}")
        finally:
            cur.close()
            self.db_pool.putconn(conn)

    async def _save_to_database(
        self,
        loop_id: int,
        iteration: int,
        knowledge_list: List[Dict],
        gaps: List[Dict],
        action_type_judgments: Dict
    ) -> List[Dict]:
        """將生成的知識保存到資料庫

        Args:
            loop_id: 迴圈 ID
            iteration: 迭代次數
            knowledge_list: 生成的知識列表
            gaps: 原始缺口列表
            action_type_judgments: 回應類型判斷

        Returns:
            List[Dict]: 已儲存的知識（包含 ID）
        """
        if not knowledge_list:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                saved = []

                for knowledge in knowledge_list:
                    gap_id = knowledge.get("gap_id")
                    judgment = action_type_judgments.get(gap_id, {}) if gap_id else {}
                    question = knowledge["question"]

                    # 【去重檢查 1】檢查是否已存在於 loop_generated_knowledge
                    cur.execute("""
                        SELECT 1 FROM loop_generated_knowledge
                        WHERE question = %s LIMIT 1
                    """, (question,))
                    if cur.fetchone():
                        print(f"⚠️  跳過重複知識（已在待審核列表）: {question}")
                        continue

                    # 【去重檢查 2】檢查是否已存在於 knowledge_base
                    cur.execute("""
                        SELECT 1 FROM knowledge_base
                        WHERE question_summary = %s LIMIT 1
                    """, (question,))
                    if cur.fetchone():
                        print(f"⚠️  跳過重複知識（已在知識庫）: {question}")
                        continue

                    # 🔍 執行向量相似度重複檢測（使用 pgvector）
                    # 需要先找到 vendor_id（從 gaps 中獲取）
                    gap = next((g for g in gaps if g.get('gap_id') == gap_id), {})
                    vendor_id = gap.get('vendor_id', 1)  # 預設為 1

                    similar_knowledge = None
                    duplicate_check = await self._detect_duplicate_knowledge(
                        vendor_id=vendor_id,
                        question_summary=question
                    )
                    if duplicate_check and duplicate_check['detected']:
                        # 檢查最高相似度，超過 0.75 直接跳過不生成
                        max_sim = max(
                            item.get('similarity_score', 0)
                            for item in duplicate_check.get('items', [])
                        ) if duplicate_check.get('items') else 0
                        if max_sim >= 0.75:
                            most_similar = duplicate_check['items'][0]
                            print(f"   ⛔ 跳過重複知識（向量相似度 {max_sim:.1%}）: {question}")
                            print(f"      相似項: {most_similar.get('item_name', '')}")
                            continue
                        similar_knowledge = duplicate_check

                    # 組裝 category / scope / is_template / template_vars
                    kb_category = knowledge.get("category")
                    kb_scope = knowledge.get("scope", "global")
                    kb_is_template = knowledge.get("is_template", False)
                    kb_template_vars = knowledge.get("template_vars")

                    # 插入到 loop_generated_knowledge 表
                    cur.execute("""
                        INSERT INTO loop_generated_knowledge (
                            loop_id, iteration,
                            question, answer, keywords,
                            action_type, similar_knowledge, status,
                            scope, category, is_template, template_vars,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id, question, answer, action_type, status
                    """, (
                        loop_id,
                        iteration,
                        question,
                        knowledge["answer"],
                        knowledge.get("keywords", []),
                        knowledge.get("action_type", "direct_answer"),
                        json.dumps(similar_knowledge) if similar_knowledge else None,  # 重複檢測結果
                        "pending",  # 等待審核
                        kb_scope,
                        kb_category,
                        kb_is_template,
                        json.dumps(kb_template_vars, ensure_ascii=False) if kb_template_vars else None,
                    ))

                    result = cur.fetchone()
                    saved_item = dict(result)
                    # 附加 similar_knowledge 到返回值，以便後續統計
                    saved_item['similar_knowledge'] = similar_knowledge
                    saved.append(saved_item)

                conn.commit()
                return saved

        except Exception as e:
            conn.rollback()
            print(f"❌ 知識保存失敗: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    # ============================================
    # Stub 方法（用於測試）
    # ============================================

    async def _stub_generate_knowledge(
        self,
        loop_id: int,
        gaps: List[Dict],
        action_type_judgments: Dict,
        iteration: int
    ) -> List[Dict]:
        """Stub：模擬知識生成"""
        from .models import ActionTypeJudgment
        generated = []

        for gap in gaps:
            gap_id = gap["gap_id"]
            judgment = action_type_judgments.get(gap_id, {})

            # 處理 judgment：可能是 ActionTypeJudgment 物件或空字典
            if isinstance(judgment, ActionTypeJudgment):
                action_type = judgment.action_type.value
            elif isinstance(judgment, dict):
                action_type = judgment.get("action_type", "direct_answer")
            else:
                action_type = "direct_answer"

            # 從 gap metadata 讀取 category 與 scope（向後相容）
            category = self._resolve_category(gap)
            scope = gap.get("scope", "global")
            is_template = (scope == "vendor")
            answer_text = f"這是針對「{gap['question']}」生成的答案內容（Stub 模式）"
            template_vars = self._extract_template_vars(answer_text) if is_template else None

            knowledge = {
                "gap_id": gap_id,
                "question": gap["question"],
                "answer": answer_text,
                "keywords": ["關鍵字1", "關鍵字2"],
                "action_type": action_type,
                "confidence_explanation": "Stub 模式生成",
                "needs_verification": True,
                "category": category,
                "scope": scope,
                "is_template": is_template,
                "template_vars": template_vars,
            }
            generated.append(knowledge)

        # 如果有資料庫，依然寫入
        if self.db_pool:
            return await self._save_to_database(
                loop_id=loop_id,
                iteration=iteration,
                knowledge_list=generated,
                gaps=gaps,
                action_type_judgments=action_type_judgments
            )

        return generated
