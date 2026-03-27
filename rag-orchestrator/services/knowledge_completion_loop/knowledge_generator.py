"""
知識生成服務

使用 OpenAI API 生成知識內容，包含成本追蹤與錯誤處理
"""

import asyncio
import json
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from openai import OpenAI, AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIConnectionError


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
    KNOWLEDGE_GENERATION_PROMPT = """你是一個專業的知識庫內容撰寫專家，專門為智能客服系統撰寫準確、清晰的知識問答。

**任務**：根據以下資訊，為這個問題生成一個完整、準確的答案。

---

**問題**：{question}

**失敗原因**：{failure_reason}
- no_match: 知識庫中沒有相關知識
- low_confidence: 知識庫有部分匹配但信心度不足
- semantic_mismatch: 語義不符合

**優先級**：{priority}
- p0: 高優先級（高頻問題且無匹配知識）
- p1: 中優先級（信心度不足但有部分匹配）
- p2: 低優先級（邊緣案例或系統錯誤）

**建議回應類型**：{suggested_action_type}
- direct_answer: 純知識問答
- form_fill: 需要填寫表單
- api_call: 需要調用 API 查詢即時資料
- form_then_api: 先填表單再調用 API

**意圖**：{intent_name}

**業者類型**：{vendor_type}
- 包租/代管公司
- 提供租賃管理、維修服務、帳務管理等

---

**現有相似知識（參考用）**：
{existing_knowledge}

---

**撰寫要求**：
1. **準確性**：答案必須準確，不能胡亂編造
2. **完整性**：涵蓋問題的所有要點
3. **清晰性**：使用簡潔易懂的語言
4. **繁體中文**：使用台灣常用的繁體中文表達
5. **專業性**：符合包租代管行業的專業用語
6. **操作性**：如涉及流程，清楚說明步驟

**特殊說明**：
- 如果是 form_fill 類型，答案中應引導用戶填寫表單
- 如果是 api_call 類型，答案中應說明會查詢即時資料
- 如果資訊不足或不確定，說明「建議聯繫客服確認」

---

請以 JSON 格式回應：
{{
  "answer": "完整的答案內容（繁體中文，100-300 字）",
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"],
  "confidence_explanation": "為什麼認為這個答案是準確的（50字內）",
  "needs_verification": false
}}

只輸出 JSON，不要其他說明。
"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        db_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None,
        model: str = "gpt-3.5-turbo",
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

        # 初始化 OpenAI 客戶端
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
            self.async_client = AsyncOpenAI(api_key=openai_api_key)
        else:
            self.client = None
            self.async_client = None

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

        # 過濾錯誤結果
        generated_knowledge = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"⚠️  知識生成失敗 (gap_id={gaps[i]['gap_id']}): {result}")
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
        from models import ActionTypeJudgment
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

            return {
                "gap_id": gap["gap_id"],
                "question": gap["question"],
                "answer": result.get("answer", ""),
                "keywords": result.get("keywords", []),
                "confidence_explanation": result.get("confidence_explanation", ""),
                "needs_verification": result.get("needs_verification", False),
                "action_type": action_type
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
        from models import ActionTypeJudgment
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

        # 填充模板
        prompt = self.KNOWLEDGE_GENERATION_PROMPT.format(
            question=gap["question"],
            failure_reason=gap.get("failure_reason", "no_match"),
            priority=gap.get("priority", "p1"),
            suggested_action_type=suggested_action_type,
            intent_name=gap.get("intent_name", "未知"),
            vendor_type="包租代管公司",
            existing_knowledge=knowledge_text
        )

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

                    # 插入到 loop_generated_knowledge 表
                    cur.execute("""
                        INSERT INTO loop_generated_knowledge (
                            loop_id, iteration,
                            question, answer, keywords,
                            action_type, status,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id, question, answer, action_type, status
                    """, (
                        loop_id,
                        iteration,
                        question,
                        knowledge["answer"],
                        knowledge.get("keywords", []),
                        knowledge.get("action_type", "direct_answer"),
                        "pending"  # 等待審核
                    ))

                    result = cur.fetchone()
                    saved.append(dict(result))

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
        from models import ActionTypeJudgment
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

            knowledge = {
                "gap_id": gap_id,
                "question": gap["question"],
                "answer": f"這是針對「{gap['question']}」生成的答案內容（Stub 模式）",
                "keywords": ["關鍵字1", "關鍵字2"],
                "action_type": action_type,
                "confidence_explanation": "Stub 模式生成",
                "needs_verification": True
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
