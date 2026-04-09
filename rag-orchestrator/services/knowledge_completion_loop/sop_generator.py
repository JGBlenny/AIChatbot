"""
SOP 生成服務

使用 OpenAI API 生成 SOP（標準作業流程）內容到 vendor_sop_items 表
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from openai import AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIConnectionError
import httpx


class SOPGenerator:
    """SOP 生成器

    功能：
    1. 根據知識缺口生成 SOP 內容
    2. 調用 OpenAI API 生成流程說明
    3. 自動判斷 trigger_mode 和 next_action
    4. 持久化到 vendor_sop_items 表
    5. 支援表單填寫類型的 SOP（form_fill）
    """

    # SOP 生成 Prompt 模板
    SOP_GENERATION_PROMPT = """你是一個專業的 SOP（標準作業流程）撰寫專家，專門為包租代管公司撰寫清晰、結構化的操作流程。

**任務**：根據以下資訊，生成一個完整的 SOP 項目。

---

**代表性問題**：{question}

{related_questions}

**問題類型**：{gap_type}
- sop_knowledge: 標準操作流程（需要步驟說明）
- form_fill: 需要引導用戶填寫表單

**失敗原因**：{failure_reason}

**優先級**：{priority}

---

**輸出要求**：

請以 JSON 格式輸出，包含以下欄位：

```json
{{
  "item_name": "SOP 項目名稱（簡短、描述性，30字以內）",
  "content": "完整的 SOP 內容（清晰的步驟說明或引導文字，200-500字）",
  "trigger_mode": "觸發模式（none, manual, immediate, auto）",
  "trigger_keywords": ["關鍵字1", "關鍵字2", "關鍵字3"],
  "next_action": "下一步動作（none, form_fill, api_call, form_then_api）",
  "next_form_id": "表單ID（如果 next_action 是 form_fill，可選）",
  "immediate_prompt": "立即提示文字（給用戶的簡短回應，50字以內）",
  "keywords": ["搜尋關鍵字1", "關鍵字2", "關鍵字3"]
}}
```

**SOP 內容撰寫指南**：

1. **精準匹配原則**（非常重要！）：
   - **SOP 名稱必須與內容精準匹配**，避免過於籠統
   - **每個 SOP 只處理一個具體流程或政策**，不要合併不相關的主題
   - 如果提供了「相關問題」，這些問題應該是高度相關且屬於同一個具體流程
   - ❌ 錯誤範例：「租約續約及退租流程」（合併了續約和退租兩個不同流程）
   - ✅ 正確範例：「租約續約流程」（只處理續約）或「退租解約流程」（只處理退租）
   - ✅ 正確範例：「雙人入住政策」（只處理雙人入住）或「訪客過夜規範」（只處理訪客）

2. **sop_knowledge 類型**：
   - 提供清晰的步驟說明（使用編號或項目符號）
   - 包含必要的注意事項和時間點
   - 語氣專業但友善
   - 範例：
     ```
     如何續約：

     1. 續約時機：請在合約到期前 30 天提出續約申請
     2. 聯繫客服：可透過以下方式聯繫：
        - 線上客服系統
        - 客服電話：0800-XXX-XXX
        - 電子郵件：service@example.com
     3. 提供資料：準備以下文件...
     4. 審核流程：通常需要 3-5 個工作天...
     5. 簽約與繳費：...
     ```

2. **form_fill 類型**：
   - 說明為什麼需要填寫表單
   - 引導用戶準備必要資料
   - 說明填寫後的流程
   - 設定 next_action = "form_fill"
   - 提供適當的 next_form_id（如有）
   - 範例：
     ```
     我們需要了解您的需求以提供最適合的服務。請填寫以下表單，我們會盡快與您聯繫。

     需要準備的資料：
     - 期望租期
     - 預算範圍
     - 其他特殊需求

     填寫完成後，我們會在 1 個工作天內與您聯繫。
     ```

3. **trigger_mode 判斷**：
   - 如果問題很明確且需要自動觸發 → trigger_mode = "auto"
   - 如果需要手動選擇 → trigger_mode = "manual"
   - 如果需要立即執行 → trigger_mode = "immediate"
   - 一般情況 → trigger_mode = "none"

4. **next_action 判斷**：
   - 如果需要用戶提供資訊 → next_action = "form_fill"
   - 如果需要查詢即時資料 → next_action = "api_call"
   - 其他情況 → next_action = "none"

---

**重要提醒**：
- 所有文字使用繁體中文
- SOP 內容要實用、清晰、易懂
- 避免使用過於技術性的術語
- 語氣要專業但友善
"""

    def __init__(
        self,
        db_pool: psycopg2.pool.ThreadedConnectionPool,
        openai_api_key: str,
        cost_tracker: Optional[object] = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 3
    ):
        """初始化 SOP 生成器

        Args:
            db_pool: 資料庫連接池
            openai_api_key: OpenAI API Key
            cost_tracker: 成本追蹤器
            model: OpenAI 模型名稱
            max_retries: 最大重試次數
        """
        self.db_pool = db_pool
        self.client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self.cost_tracker = cost_tracker
        self.model = model
        self.max_retries = max_retries
        self.embedding_api_url = os.getenv('EMBEDDING_API_URL', 'http://aichatbot-embedding-api:5000/api/v1/embeddings')

    async def _get_or_create_default_category(self, vendor_id: int) -> int:
        """獲取或創建默認的 AI 生成知識分類

        Args:
            vendor_id: 業者 ID

        Returns:
            分類 ID
        """
        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()

            # 嘗試獲取現有的「AI 生成知識」分類
            cur.execute("""
                SELECT id FROM vendor_sop_categories
                WHERE vendor_id = %s
                AND category_name = 'AI 生成知識'
                AND is_active = TRUE
            """, (vendor_id,))

            result = cur.fetchone()
            if result:
                return result[0]

            # 創建新分類
            cur.execute("""
                INSERT INTO vendor_sop_categories (
                    vendor_id,
                    category_name,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (%s, 'AI 生成知識', TRUE, NOW(), NOW())
                RETURNING id
            """, (vendor_id,))

            category_id = cur.fetchone()[0]
            conn.commit()
            print(f"   ✅ 創建新分類: AI 生成知識 (ID: {category_id})")
            return category_id
        except Exception as e:
            conn.rollback()
            print(f"   ❌ 獲取/創建分類失敗: {e}")
            raise
        finally:
            cur.close()
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

    async def generate_sop_items(
        self,
        loop_id: int,
        vendor_id: int,
        gaps: List[Dict],
        iteration: int = 1,
        batch_size: int = 5
    ) -> List[Dict]:
        """批次生成 SOP 項目

        Args:
            loop_id: 迴圈 ID
            vendor_id: 業者 ID
            gaps: 知識缺口列表（已分類為 sop_knowledge 或 form_fill）
            iteration: 迭代次數
            batch_size: 批次大小

        Returns:
            生成的 SOP 項目列表
        """
        if not self.client:
            print("❌ OpenAI API Key 未設定，無法生成 SOP")
            return []

        print(f"\n📝 開始生成 SOP 項目...")
        print(f"   知識缺口數：{len(gaps)}")
        print(f"   批次大小：{batch_size}")

        generated_sops = []

        # 批次處理
        for i in range(0, len(gaps), batch_size):
            batch = gaps[i:i + batch_size]
            print(f"\n   處理批次 {i // batch_size + 1}/{(len(gaps) + batch_size - 1) // batch_size}")

            # 並發生成
            tasks = [
                self._generate_single_sop(
                    loop_id=loop_id,
                    vendor_id=vendor_id,
                    gap=gap,
                    iteration=iteration
                )
                for gap in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 處理結果
            for gap, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"   ❌ 生成失敗: {gap.get('question', 'Unknown')} - {result}")
                elif result:
                    generated_sops.append(result)
                    print(f"   ✅ 已生成: {result.get('item_name', 'Unknown')}")

        print(f"\n✅ SOP 生成完成：共 {len(generated_sops)} 筆")

        # 🔍 收集重複檢測統計
        await self._log_duplicate_detection_stats(
            loop_id=loop_id,
            iteration=iteration,
            knowledge_type='sop',
            generated_items=generated_sops
        )

        return generated_sops

    async def _enrich_trigger_keywords(
        self,
        llm_keywords: List[str],
        question: str,
        represents_questions: List[str]
    ) -> List[str]:
        """使用 OpenAI LLM 智能生成檢索關鍵字

        基於問題內容和 LLM 生成的關鍵字，智能補充更多搜尋變體

        Args:
            llm_keywords: LLM 生成的關鍵字列表
            question: 代表性問題
            represents_questions: 聚類的相關問題列表

        Returns:
            智能生成的關鍵字列表（最多 15 個）
        """
        # 構建問題列表文字
        all_questions = [question]
        if represents_questions and len(represents_questions) > 1:
            all_questions.extend(represents_questions)

        questions_text = "\n".join([f"- {q}" for q in all_questions])

        # 構建 Prompt 讓 LLM 生成關鍵字
        prompt = f"""你是一個關鍵字生成專家，專門為包租代管系統的 SOP 生成「問題匹配型」關鍵字。

**目標**：生成能夠匹配用戶實際問題的關鍵字，而不是技術詞彙或正式用語。

**問題列表**：
{questions_text}

**已有關鍵字**：
{', '.join(llm_keywords) if llm_keywords else '無'}

**關鍵字生成原則**：
1. ❌ 避免：正式用語、技術詞彙、書面語
   - 錯誤示例：「訪客身份驗證」、「居住時限」、「租約終止流程」

2. ✅ 優先：用戶實際會問的口語化詞組
   - 正確示例：「帶朋友」、「可以住人嗎」、「什麼時候搬家」

3. 思考用戶會怎麼問這個問題：
   - 「可以...嗎」、「是否...」、「能不能...」、「怎麼...」
   - 動作詞：「帶」、「留宿」、「住」、「過夜」、「繳」、「付」
   - 對象詞：「朋友」、「家人」、「客人」、「租金」

4. 包含各種說法變體：
   - 正式+口語：「繳費」→「付錢」、「收費」、「租金繳了沒」
   - 同義詞：「修理」→「修」、「壞了」、「不能用」

5. 限制 2-6 個字的詞組

**輸出格式**：只輸出 JSON 陣列，例如：
["帶朋友", "可以住人嗎", "是否可以帶朋友", ...]

不要輸出其他說明文字，直接輸出 JSON 陣列即可。"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # 使用 mini 版本節省成本
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個專業的搜尋關鍵字生成專家，專門為包租代管業務生成精準的檢索關鍵字。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 較低的溫度確保結果穩定
                max_tokens=200
            )

            # 解析回應
            content = response.choices[0].message.content.strip()

            # 移除可能的 markdown 代碼塊標記
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            content = content.strip()

            # 解析 JSON
            generated_keywords = json.loads(content)

            # 合併 LLM 關鍵字和生成的關鍵字，去重
            all_keywords = set(llm_keywords or [])
            all_keywords.update(generated_keywords)

            # 限制最多 15 個關鍵字
            final_keywords = list(all_keywords)[:15]

            return final_keywords

        except Exception as e:
            # 如果 LLM 生成失敗，回退到原始的 LLM 關鍵字
            print(f"   ⚠️  關鍵字生成失敗，使用原始 LLM 關鍵字: {e}")
            return llm_keywords or []

    async def _select_category_with_llm(
        self,
        vendor_id: int,
        question: str,
        sop_name: str,
        sop_content: str
    ) -> Optional[int]:
        """使用 LLM 自動選擇 SOP 類別

        Args:
            vendor_id: 業者 ID
            question: 代表性問題
            sop_name: SOP 名稱
            sop_content: SOP 內容

        Returns:
            選擇的 category_id 或 None（失敗時）
        """
        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()

            # 查詢可用的類別列表
            cur.execute("""
                SELECT id, category_name, description
                FROM vendor_sop_categories
                WHERE vendor_id = %s
                ORDER BY id
            """, (vendor_id,))

            categories = cur.fetchall()

            if not categories:
                print(f"   ⚠️  業者 {vendor_id} 沒有可用的 SOP 類別")
                return None

            # 構建類別列表文字
            categories_text = ""
            for cat_id, cat_name, cat_desc in categories:
                desc_text = f"（{cat_desc}）" if cat_desc else ""
                categories_text += f"{cat_id}. {cat_name}{desc_text}\n"

            # 構建 Prompt
            prompt = f"""你是一個 SOP 分類專家。請根據以下 SOP 的內容，選擇最合適的類別。

**SOP 名稱**：{sop_name}

**代表性問題**：{question}

**SOP 內容摘要**：
{sop_content[:500]}...

**可用類別**：
{categories_text}

請分析 SOP 的主題和內容，選擇一個最合適的類別 ID。

**輸出格式**：只輸出類別 ID 數字，例如：43

不要輸出其他文字，只輸出數字即可。"""

            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一個專業的 SOP 分類專家，專門為包租代管業務的 SOP 選擇最合適的類別。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # 更低的溫度確保穩定性
                    max_tokens=10
                )

                # 解析回應
                content = response.choices[0].message.content.strip()

                # 提取數字
                category_id = int(content)

                # 驗證類別 ID 是否有效
                valid_ids = [cat[0] for cat in categories]
                if category_id not in valid_ids:
                    print(f"   ⚠️  LLM 返回的類別 ID {category_id} 無效，使用預設類別")
                    return valid_ids[0] if valid_ids else None

                # 獲取類別名稱用於顯示
                category_name = next((cat[1] for cat in categories if cat[0] == category_id), "Unknown")
                print(f"   🏷️  自動選擇類別: {category_name} (ID: {category_id})")

                return category_id

            except (ValueError, json.JSONDecodeError) as e:
                print(f"   ⚠️  無法解析 LLM 返回的類別 ID: {content}, 錯誤: {e}")
                # 回退到第一個類別
                return categories[0][0] if categories else None
            except Exception as e:
                print(f"   ⚠️  LLM 類別選擇失敗: {e}")
                return categories[0][0] if categories else None

        except Exception as e:
            print(f"   ❌ 查詢類別列表失敗: {e}")
            return None
        finally:
            self.db_pool.putconn(conn)

    async def _select_group_with_llm(
        self,
        vendor_id: int,
        category_id: int,
        question: str,
        sop_name: str,
        sop_content: str
    ) -> Optional[int]:
        """使用 LLM 自動選擇 SOP 群組

        Args:
            vendor_id: 業者 ID
            category_id: 已選擇的類別 ID
            question: 代表性問題
            sop_name: SOP 名稱
            sop_content: SOP 內容

        Returns:
            選擇的 group_id 或 None（失敗時）
        """
        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()

            # 查詢該類別下的群組列表
            cur.execute("""
                SELECT id, group_name, description
                FROM vendor_sop_groups
                WHERE vendor_id = %s AND category_id = %s
                ORDER BY id
            """, (vendor_id, category_id))

            groups = cur.fetchall()

            if not groups:
                print(f"   ⚠️  類別 {category_id} 下沒有可用的 SOP 群組")
                return None

            # 構建群組列表文字
            groups_text = ""
            for group_id, group_name, group_desc in groups:
                desc_text = f"（{group_desc}）" if group_desc else ""
                groups_text += f"{group_id}. {group_name}{desc_text}\n"

            # 構建 Prompt
            prompt = f"""你是一個 SOP 分類專家。請根據以下 SOP 的內容，選擇最合適的群組。

**SOP 名稱**：{sop_name}

**代表性問題**：{question}

**SOP 內容摘要**：
{sop_content[:500]}...

**可用群組**：
{groups_text}

請分析 SOP 的主題和內容，選擇一個最合適的群組 ID。

**輸出格式**：只輸出群組 ID 數字，例如：101

不要輸出其他文字，只輸出數字即可。"""

            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一個專業的 SOP 分類專家，專門為包租代管業務的 SOP 選擇最合適的群組。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=10
                )

                # 解析回應
                content = response.choices[0].message.content.strip()

                # 提取數字
                group_id = int(content)

                # 驗證群組 ID 是否有效
                valid_ids = [grp[0] for grp in groups]
                if group_id not in valid_ids:
                    print(f"   ⚠️  LLM 返回的群組 ID {group_id} 無效，使用預設群組")
                    return valid_ids[0] if valid_ids else None

                # 獲取群組名稱用於顯示
                group_name = next((grp[1] for grp in groups if grp[0] == group_id), "Unknown")
                print(f"   📁 自動選擇群組: {group_name} (ID: {group_id})")

                return group_id

            except (ValueError, json.JSONDecodeError) as e:
                print(f"   ⚠️  無法解析 LLM 返回的群組 ID: {content}, 錯誤: {e}")
                # 回退到第一個群組
                return groups[0][0] if groups else None
            except Exception as e:
                print(f"   ⚠️  LLM 群組選擇失敗: {e}")
                return groups[0][0] if groups else None

        except Exception as e:
            print(f"   ❌ 查詢群組列表失敗: {e}")
            return None
        finally:
            self.db_pool.putconn(conn)

    async def _detect_duplicate_sops(
        self,
        vendor_id: int,
        sop_title: str,
        sop_content: str
    ) -> Optional[Dict]:
        """使用 pgvector 向量相似度檢測重複的 SOP

        Args:
            vendor_id: 業者 ID
            sop_title: SOP 標題
            sop_content: SOP 內容

        Returns:
            重複檢測結果，格式：
            {
                "detected": bool,
                "items": [
                    {
                        "id": int,
                        "source_table": str,  # "vendor_sop_items" or "loop_generated_knowledge"
                        "item_name": str,
                        "similarity_score": float
                    }
                ]
            }
        """
        # 生成 SOP 標題的 embedding
        combined_text = f"{sop_title}\n\n{sop_content[:200]}"  # 限制內容長度避免過長
        query_embedding = await self._generate_embedding(combined_text)

        if not query_embedding:
            print("   ⚠️  無法生成 embedding，跳過重複檢測")
            return {"detected": False, "items": []}

        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            similar_items = []

            # 檢測 1: 搜尋 vendor_sop_items 表（正式 SOP）
            # 使用 pgvector 的 cosine similarity (<=> 運算子)
            # 閾值：similarity > 0.85 視為相似（距離 < 0.15）
            cur.execute("""
                SELECT
                    id,
                    item_name,
                    1 - (primary_embedding <=> %s::vector) AS similarity_score
                FROM vendor_sop_items
                WHERE vendor_id = %s
                  AND primary_embedding IS NOT NULL
                  AND 1 - (primary_embedding <=> %s::vector) > 0.85
                ORDER BY primary_embedding <=> %s::vector ASC
                LIMIT 3
            """, (query_embedding, vendor_id, query_embedding, query_embedding))

            for row in cur.fetchall():
                similar_items.append({
                    "id": row['id'],
                    "source_table": "vendor_sop_items",
                    "item_name": row['item_name'],
                    "similarity_score": float(row['similarity_score'])
                })

            # 檢測 2: 搜尋 loop_generated_knowledge 表（待審核 SOP）
            cur.execute("""
                SELECT
                    id,
                    question AS item_name,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM loop_generated_knowledge
                WHERE knowledge_type = 'sop'
                  AND status IN ('pending', 'approved')
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) > 0.85
                ORDER BY embedding <=> %s::vector ASC
                LIMIT 3
            """, (query_embedding, query_embedding, query_embedding))

            for row in cur.fetchall():
                similar_items.append({
                    "id": row['id'],
                    "source_table": "loop_generated_knowledge",
                    "item_name": row['item_name'],
                    "similarity_score": float(row['similarity_score'])
                })

            # 按相似度排序，取前 3 個
            similar_items.sort(key=lambda x: x['similarity_score'], reverse=True)
            similar_items = similar_items[:3]

            if similar_items:
                print(f"   🔍 檢測到 {len(similar_items)} 個相似 SOP:")
                for item in similar_items:
                    print(f"      - [{item['source_table']}] {item['item_name']} (相似度: {item['similarity_score']:.1%})")

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
            if (item.get('similar_knowledge') or {}).get('detected', False)
        )

        # 收集相似度分布
        similarity_scores = []
        for item in generated_items:
            similar_knowledge = item.get('similar_knowledge')
            if similar_knowledge and isinstance(similar_knowledge, dict) and similar_knowledge.get('detected'):
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

    async def _find_similar_sop(
        self,
        vendor_id: int,
        question: str,
        represents_questions: List[str]
    ) -> Optional[Dict]:
        """查找相似的現有 SOP

        使用關鍵字重疊度來判斷相似性

        Args:
            vendor_id: 業者 ID
            question: 代表性問題
            represents_questions: 聚類的相關問題列表

        Returns:
            相似的 SOP 資料（包含 id, item_name, trigger_keywords）或 None
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 構建所有問題文字
                all_questions = [question]
                if represents_questions and len(represents_questions) > 1:
                    all_questions.extend(represents_questions)

                # 提取問題中的關鍵詞（簡單分詞）
                import re
                question_keywords = set()
                for q in all_questions:
                    # 移除標點和停用詞
                    clean_q = re.sub(r'[？?！!。、，,；;：:（）\(\)]', ' ', q)
                    words = clean_q.split()
                    stopwords = {'是否', '可以', '如何', '什麼', '哪裡', '為什麼', '怎麼',
                                '請問', '想要', '需要', '可不可以', '能不能', '有沒有'}
                    for word in words:
                        word = word.strip()
                        if 2 <= len(word) <= 8 and word not in stopwords:
                            question_keywords.add(word)

                if not question_keywords:
                    return None

                # 查詢所有已批准的 SOP（只限於該業者）
                cur.execute("""
                    SELECT id, item_name, trigger_keywords
                    FROM vendor_sop_items
                    WHERE vendor_id = %s
                      AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (vendor_id,))

                existing_sops = cur.fetchall()

                # 計算相似度
                best_match = None
                best_score = 0.0

                for sop in existing_sops:
                    # trigger_keywords 是 ARRAY 類型，直接使用
                    trigger_keywords = set(sop['trigger_keywords'] or [])

                    if not trigger_keywords:
                        continue

                    # 計算關鍵字重疊度（Jaccard 相似度）
                    intersection = question_keywords & trigger_keywords
                    union = question_keywords | trigger_keywords

                    if len(union) > 0:
                        jaccard_score = len(intersection) / len(union)

                        # 如果重疊度 >= 30%，視為相似
                        if jaccard_score >= 0.3 and jaccard_score > best_score:
                            best_score = jaccard_score
                            best_match = {
                                'id': sop['id'],
                                'item_name': sop['item_name'],
                                'trigger_keywords': list(trigger_keywords),
                                'similarity_score': jaccard_score
                            }

                if best_match:
                    print(f"   🔍 找到相似 SOP: {best_match['item_name']} (相似度: {best_score:.1%})")

                return best_match

        finally:
            self.db_pool.putconn(conn)

    async def _update_sop_keywords(
        self,
        sop_id: int,
        vendor_id: int,
        existing_keywords: List[str],
        new_keywords: List[str]
    ) -> bool:
        """更新現有 SOP 的關鍵字

        Args:
            sop_id: SOP ID
            vendor_id: 業者 ID
            existing_keywords: 現有關鍵字
            new_keywords: 新增關鍵字

        Returns:
            更新是否成功
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 合併關鍵字，去重
                merged_keywords = list(set(existing_keywords) | set(new_keywords))

                # 直接更新 trigger_keywords 欄位（ARRAY 類型）
                cur.execute("""
                    UPDATE vendor_sop_items
                    SET trigger_keywords = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND vendor_id = %s
                """, (merged_keywords, sop_id, vendor_id))

                if cur.rowcount == 0:
                    print(f"   ⚠️  找不到 SOP {sop_id}（業者 {vendor_id}）")
                    return False

                conn.commit()

                new_added = set(new_keywords) - set(existing_keywords)
                print(f"   ✅ 已更新 SOP {sop_id} 的關鍵字: 原有 {len(existing_keywords)} 個 → 現有 {len(merged_keywords)} 個")
                if new_added:
                    print(f"      新增關鍵字: {', '.join(list(new_added)[:5])}{'...' if len(new_added) > 5 else ''}")

                return True

        except Exception as e:
            conn.rollback()
            print(f"   ❌ 更新 SOP 關鍵字失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.db_pool.putconn(conn)

    async def _generate_single_sop(
        self,
        loop_id: int,
        vendor_id: int,
        gap: Dict,
        iteration: int
    ) -> Optional[Dict]:
        """生成單個 SOP 項目

        Args:
            loop_id: 迴圈 ID
            vendor_id: 業者 ID
            gap: 單個知識缺口
            iteration: 迭代次數

        Returns:
            生成的 SOP 項目（Dict）或 None
        """
        question = gap.get('question', '')
        gap_type = gap.get('gap_type', 'sop_knowledge')
        failure_reason = gap.get('failure_reason', 'no_match')
        priority = gap.get('priority', 'p1')

        # 處理聚類資訊
        represents_questions = gap.get('represents_questions', [])

        # 🔍 Step 1: 檢查是否有相似的現有 SOP
        similar_sop = await self._find_similar_sop(
            vendor_id=vendor_id,
            question=question,
            represents_questions=represents_questions
        )

        if similar_sop:
            # 找到相似 SOP，生成新關鍵字並更新
            print(f"   📝 為相似 SOP 生成新關鍵字...")

            # 生成新關鍵字（基於當前問題）
            new_keywords = await self._enrich_trigger_keywords(
                llm_keywords=[],
                question=question,
                represents_questions=represents_questions
            )

            # 更新現有 SOP 的關鍵字
            success = await self._update_sop_keywords(
                sop_id=similar_sop['id'],
                vendor_id=vendor_id,
                existing_keywords=similar_sop['trigger_keywords'],
                new_keywords=new_keywords
            )

            if success:
                # 返回更新後的 SOP 資訊（標記為更新而非新建）
                return {
                    'id': similar_sop['id'],
                    'item_name': similar_sop['item_name'],
                    'trigger_keywords': new_keywords,
                    'updated': True,  # 標記為更新
                    'question': question
                }
            else:
                print(f"   ⚠️  更新失敗，將照常生成新 SOP")
                # 更新失敗，繼續生成新 SOP
        if represents_questions and len(represents_questions) > 1:
            # 有聚類：列出所有相關問題
            related_questions_text = "**相關問題（需在同一 SOP 中涵蓋）**：\n"
            for idx, q in enumerate(represents_questions, 1):
                related_questions_text += f"{idx}. {q}\n"
            related_questions_text += "\n**重要**：請生成一個統整性的 SOP，涵蓋上述所有問題的答案。"
        else:
            # 無聚類：單一問題
            related_questions_text = ""

        # 構建 Prompt
        prompt = self.SOP_GENERATION_PROMPT.format(
            question=question,
            related_questions=related_questions_text,
            gap_type=gap_type,
            failure_reason=failure_reason,
            priority=priority
        )

        # 調用 OpenAI API
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個專業的 SOP 撰寫專家，專門為包租代管公司撰寫標準作業流程。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )

            # 追蹤成本
            if self.cost_tracker and hasattr(response, 'usage'):
                await self.cost_tracker.track_api_call(
                    model=self.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    operation='sop_generation'
                )

            # 解析結果
            content = response.choices[0].message.content
            sop_data = json.loads(content)

            # 驗證必要欄位
            required_fields = ['item_name', 'content']
            for field in required_fields:
                if field not in sop_data:
                    print(f"   ⚠️  缺少必要欄位: {field}")
                    return None

            # 設定預設值
            # 知識完善迴圈生成的 SOP 預設應為 'auto'，以便自動觸發
            sop_data.setdefault('trigger_mode', 'auto')
            sop_data.setdefault('trigger_keywords', [])
            sop_data.setdefault('next_action', 'none')
            sop_data.setdefault('next_form_id', None)
            sop_data.setdefault('immediate_prompt', '')
            sop_data.setdefault('keywords', [])

            # 強制設定 next_form_id 為 None（避免外鍵約束錯誤）
            # TODO: 後續可以根據實際需求mapping表單ID
            sop_data['next_form_id'] = None

            # 🔑 使用 OpenAI 智能生成檢索關鍵字
            sop_data['trigger_keywords'] = await self._enrich_trigger_keywords(
                sop_data.get('trigger_keywords', []),
                question,
                represents_questions
            )
            print(f"   🔑 檢索關鍵字 ({len(sop_data['trigger_keywords'])} 個): {', '.join(sop_data['trigger_keywords'][:5])}{'...' if len(sop_data['trigger_keywords']) > 5 else ''}")

            # 生成 embedding
            combined_text = f"{sop_data['item_name']}\n\n{sop_data['content']}"
            primary_embedding = await self._generate_embedding(combined_text)

            # 🏷️  使用 LLM 自動選擇 SOP 類別
            category_id = await self._select_category_with_llm(
                vendor_id=vendor_id,
                question=question,
                sop_name=sop_data['item_name'],
                sop_content=sop_data['content']
            )
            sop_data['category_id'] = category_id  # 保存到 sop_data 中

            # 📁 使用 LLM 自動選擇 SOP 群組（在類別選擇後）
            if category_id:
                group_id = await self._select_group_with_llm(
                    vendor_id=vendor_id,
                    category_id=category_id,
                    question=question,
                    sop_name=sop_data['item_name'],
                    sop_content=sop_data['content']
                )
                sop_data['group_id'] = group_id  # 保存到 sop_data 中
            else:
                print("   ⚠️  未選擇類別，跳過群組選擇")
                sop_data['group_id'] = None

            # 持久化到資料庫
            persist_result = await self._persist_sop(
                vendor_id=vendor_id,
                loop_id=loop_id,
                gap_id=gap.get('gap_id'),
                iteration=iteration,
                sop_data=sop_data,
                primary_embedding=primary_embedding
            )

            if persist_result:
                sop_data['id'] = persist_result['id']
                sop_data['vendor_id'] = vendor_id
                sop_data['similar_knowledge'] = persist_result.get('similar_knowledge')
                sop_data['question'] = question
                return sop_data

            return None

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON 解析失敗: {e}")
            return None
        except Exception as e:
            import traceback
            print(f"   ❌ 生成失敗: {e}")
            traceback.print_exc()
            return None

    async def _persist_sop(
        self,
        vendor_id: int,
        loop_id: int,
        gap_id: Optional[int],
        iteration: int,
        sop_data: Dict,
        primary_embedding: Optional[List[float]] = None
    ) -> Optional[int]:
        """持久化 SOP 到審核表（loop_generated_knowledge）

        SOP 將先保存到審核表，狀態為 'pending'，
        需要人工審核通過後才會同步到 vendor_sop_items 並激活

        Args:
            vendor_id: 業者 ID
            loop_id: 迴圈 ID
            gap_id: 知識缺口 ID
            iteration: 迭代次數
            sop_data: SOP 資料
            primary_embedding: 主要向量

        Returns:
            插入的知識 ID（loop_generated_knowledge.id）或 None
        """
        conn = self.db_pool.getconn()
        sop_id = None
        try:
            cur = conn.cursor()

            # 準備 SOP 配置資料（保存到 JSON）
            import json
            sop_config = {
                "item_name": sop_data['item_name'],
                "trigger_mode": sop_data['trigger_mode'],
                "keywords": sop_data.get('trigger_keywords', []),  # 統一使用 keywords 欄位
                "next_action": sop_data['next_action'],
                "next_form_id": sop_data.get('next_form_id'),
                "immediate_prompt": sop_data.get('immediate_prompt', ''),
                "vendor_id": vendor_id,
                "category_id": sop_data.get('category_id'),  # 保存類別 ID
                "group_id": sop_data.get('group_id')  # 保存群組 ID
            }

            sop_name = sop_data['item_name']

            # 【去重檢查 1】檢查是否已存在於 loop_generated_knowledge
            cur.execute("""
                SELECT 1 FROM loop_generated_knowledge
                WHERE question = %s LIMIT 1
            """, (sop_name,))
            if cur.fetchone():
                print(f"⚠️  跳過重複 SOP（已在待審核列表）: {sop_name}")
                return None

            # 【去重檢查 2】檢查是否已存在於 knowledge_base
            cur.execute("""
                SELECT 1 FROM knowledge_base
                WHERE question_summary = %s LIMIT 1
            """, (sop_name,))
            if cur.fetchone():
                print(f"⚠️  跳過重複 SOP（已在知識庫）: {sop_name}")
                return None

            # 【去重檢查 3】檢查是否已存在於 vendor_sop_items
            cur.execute("""
                SELECT 1 FROM vendor_sop_items
                WHERE item_name = %s LIMIT 1
            """, (sop_name,))
            if cur.fetchone():
                print(f"⚠️  跳過重複 SOP（已在 SOP 表）: {sop_name}")
                return None

            # 🔍 執行向量相似度重複檢測（使用 pgvector）
            similar_knowledge = None
            if primary_embedding:
                duplicate_check = await self._detect_duplicate_sops(
                    vendor_id=vendor_id,
                    sop_title=sop_data['item_name'],
                    sop_content=sop_data['content']
                )
                if duplicate_check and duplicate_check['detected']:
                    similar_knowledge = duplicate_check  # 儲存完整的檢測結果

            # 插入到 loop_generated_knowledge（待審核）
            cur.execute("""
                INSERT INTO loop_generated_knowledge (
                    loop_id,
                    iteration,
                    gap_analysis_id,
                    question,
                    answer,
                    knowledge_type,
                    sop_config,
                    keywords,
                    embedding,
                    similar_knowledge,
                    status,
                    synced_to_kb,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING id
            """, (
                loop_id,
                iteration,
                gap_id,
                sop_data['item_name'],      # 使用 SOP 名稱作為問題
                sop_data['content'],         # SOP 內容作為答案
                'sop',                       # 標記為 SOP 類型
                json.dumps(sop_config),      # SOP 配置
                sop_data.get('keywords', []),
                primary_embedding,
                json.dumps(similar_knowledge) if similar_knowledge else None,  # 重複檢測結果
                'pending',                   # 待審核
                False                        # 未同步
            ))

            sop_id = cur.fetchone()[0]

            print(f"   📝 SOP 已保存到審核表（ID: {sop_id}），等待審核")

            # 先提交 SOP 插入
            conn.commit()

            # 記錄到 loop_execution_logs（可選，測試時跳過）
            # 在獨立事務中處理，失敗不影響 SOP 插入
            try:
                cur.execute("""
                    INSERT INTO loop_execution_logs (
                        loop_id,
                        event_type,
                        event_data,
                        created_at
                    ) VALUES (
                        %s, 'sop_generated', %s, NOW()
                    )
                """, (
                    loop_id,
                    json.dumps({
                        'iteration': iteration,
                        'sop_id': sop_id,
                        'gap_id': gap_id,
                        'item_name': sop_data['item_name'],
                        'trigger_mode': sop_data['trigger_mode'],
                        'next_action': sop_data['next_action']
                    })
                ))
                conn.commit()
            except Exception as log_error:
                # 如果 loop_id 不存在，跳過日誌記錄（測試模式）
                conn.rollback()  # 回滾日誌插入，但不影響已提交的 SOP
                print(f"   ⚠️  跳過日誌記錄: {log_error}")

            # 返回 SOP ID 和重複檢測結果
            return {
                'id': sop_id,
                'similar_knowledge': similar_knowledge
            }

        except Exception as e:
            conn.rollback()
            print(f"   ❌ 持久化 SOP 失敗: {e}")
            return None
        finally:
            cur.close()
            self.db_pool.putconn(conn)
