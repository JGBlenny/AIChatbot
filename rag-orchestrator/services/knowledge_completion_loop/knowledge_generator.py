"""
知識生成服務

使用 OpenAI API 生成知識內容，包含成本追蹤與錯誤處理
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from openai import OpenAI, AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIConnectionError
import httpx


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
        self.embedding_api_url = os.getenv('EMBEDDING_API_URL', 'http://aichatbot-embedding-api:5000/api/v1/embeddings')

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
                import traceback
                print(f"⚠️  知識生成失敗 (gap_id={gaps[i]['gap_id']}): {result}")
                traceback.print_exception(type(result), result, result.__traceback__)
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
                        similar_knowledge = duplicate_check  # 儲存完整的檢測結果

                    # 插入到 loop_generated_knowledge 表
                    cur.execute("""
                        INSERT INTO loop_generated_knowledge (
                            loop_id, iteration,
                            question, answer, keywords,
                            action_type, similar_knowledge, status,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id, question, answer, action_type, status
                    """, (
                        loop_id,
                        iteration,
                        question,
                        knowledge["answer"],
                        knowledge.get("keywords", []),
                        knowledge.get("action_type", "direct_answer"),
                        json.dumps(similar_knowledge) if similar_knowledge else None,  # 重複檢測結果
                        "pending"  # 等待審核
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
