"""
SOP 生成服務

使用 OpenAI API 生成 SOP（標準作業流程）內容到 vendor_sop_items 表
"""

import asyncio
import json
import os
import re
from typing import Dict, List, Optional
import psycopg2.pool
import psycopg2.extras
from openai import AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIConnectionError
import httpx

# 編造內容檢測正則：電話號碼、Email、網址
_FABRICATED_PHONE_RE = re.compile(r'0[0-9]{1,3}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}')
_FABRICATED_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
_FABRICATED_URL_RE = re.compile(r'https?://[^\s]+')
_BANNED_TERMS = ['專屬管家', '客服專線', '客服電話']


class SOPGenerator:
    """SOP 生成器

    功能：
    1. 根據知識缺口生成 SOP 內容
    2. 調用 OpenAI API 生成流程說明
    3. 自動判斷 trigger_mode 和 next_action
    4. 持久化到 vendor_sop_items 表
    5. 支援表單填寫類型的 SOP（form_fill）
    6. SOP 主題白名單機制
    """

    # SOP 主題白名單：只有「業務流程」或「政策規範」才適合生成 SOP
    # 注意：不要放 api_query（電費、水費等費用查詢）或 jgb_system（系統操作）的關鍵字
    SOP_TOPIC_WHITELIST = [
        # 合約相關流程
        '續約', '續租', '退租', '解約', '簽約', '合約', '轉租', '租約',
        # 入住/搬出流程
        '入住', '搬出', '搬遷', '點交', '交屋', '搬家',
        # 生活規範（政策類）
        '寵物', '養寵物', '訪客', '過夜', '留宿', '噪音', '安寧',
        '雙人', '入住人數', '帶朋友', '同住',
        # 繳費「流程」（注意：不是費用金額查詢）
        '繳費方式', '付款方式', '繳租金',
        '遲繳', '逾期', '違約金', '晚繳',
        # 押金流程
        '押金退還', '退押金', '押金收取',
        # 報修/投訴流程
        '報修', '維修', '修繕', '投訴', '客訴',
        # 停車位申請
        '停車位', '車位申請', '機車位',
        # 公共設施使用規範
        '公共設施', '健身房', '洗衣', '交誼廳',
        # 鑰匙門禁管理
        '鑰匙', '門禁', '門卡', '門鎖',
        # 裝潢申請
        '裝潢', '裝修', '改建',
        # 申請類（表單填寫）
        '找房', '租屋申請',
        # 發票流程
        '發票開立', '發票作廢',
        # 垃圾清運規範
        '垃圾', '資源回收',
    ]

    # SOP 生成 Prompt 模板
    SOP_GENERATION_PROMPT = """你是包租代管公司的營運主管，負責建立業務流程知識庫。

**你的任務**：針對客人常問的問題，建立對應的「業務流程」或「政策規範」。
**內容定位**：結構化的流程步驟或政策說明，但語氣要親切易懂，不是寫公文。

---

**客人的問題**：{question}

{related_questions}

**問題類型**：{gap_type}
**失敗原因**：{failure_reason}
**優先級**：{priority}

---

{available_forms_section}

---

**輸出 JSON 格式**：

```json
{{
  "item_name": "簡短標題（15字以內，例如：退租流程、續約申請方式）",
  "content": "客服回答內容（200-500字）",
  "trigger_mode": "auto",
  "trigger_keywords": ["關鍵字1", "關鍵字2", "關鍵字3"],
  "next_action": "none 或 form_fill 或 api_call",
  "next_form_id": "對應的 form_id（從上方表單清單選擇，沒有合適的填 null）",
  "immediate_prompt": "簡短回應（50字以內）",
  "keywords": ["搜尋關鍵字1", "關鍵字2"]
}}
```

---

**next_action 判斷規則**：
- **form_fill**：客人需要填表才能完成的事（如報修申請、租屋申請、投訴），`next_form_id` 必須從上方表單清單中選擇
- **api_call**：需要查詢即時資料的（如查租金、查電費、查停車費），`next_form_id` 必須從上方表單清單中選擇
- **none**：純知識說明，不需要表單或 API（如退租流程說明、續約規定）

**content 撰寫規則（非常重要）**：

1. **你是客服在跟客人說話**，語氣自然親切，像 LINE 對話
2. **第一句直接回答問題**，不要任何鋪陳
3. **只寫你確定知道的事實**，不確定的寫「請聯繫您的管理師確認」
4. **一個 SOP 只處理一個具體面向**，例如「退租通知期限」「退租點交」「押金退還」是三個獨立 SOP，不要合成一個「退租流程」

**絕對禁止（違反任何一條就是不合格）**：
- ❌ 編造電話號碼（如 0800-123-456、02-XXXX-XXXX）、Email、網址 — 任何數字格式的電話都不行
- ❌ 使用「專屬管家」「客服專線」「客服人員」等稱呼，統一用「管理師」
- ❌ 使用「SOP」「標準作業流程」「本流程旨在」等術語
- ❌ 使用「在包租代管的過程中」「至關重要」「以下是關於...的說明」等廢話
- ❌ 編造不確定的政策細節（如具體天數、百分比、金額），不確定就不要寫
- ❌ item_name 包含「SOP」「流程說明」「政策說明」「查詢流程」等冗詞

**好的回答範例**：
```
續約請在合約到期前 30 天提出，流程如下：

1. 跟您的專屬管家說想續約
2. 準備身分證件及原合約
3. 審核通過後簽新約、繳費就完成了

有任何問題都可以直接問我哦！
```

**不好的回答範例**：
```
在包租代管的過程中，續約是一個重要的環節。以下是關於續約的具體步驟說明：
1. 續約時機：請在合約到期前 30 天提出續約申請
2. 聯繫客服：可透過以下方式聯繫：
   - 客服電話：0800-XXX-XXX
   - 電子郵件：service@example.com
```

**item_name 範例**：
- ✅ 退租流程、續約申請、押金退還、租金繳費方式、訪客過夜規範
- ❌ 退租流程SOP、退租解約流程說明、管理費固定金額查詢流程、自助查閱電表讀數流程

所有文字使用繁體中文。只輸出 JSON。
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
        self._form_schemas_cache = None  # 表單清單快取

    # 大主題拆解 Prompt
    TOPIC_DECOMPOSE_PROMPT = """你是包租代管公司的營運主管。判斷以下問題是否涉及多個不同面向，需要拆成多筆獨立的 SOP。

**問題**：{question}

**判斷規則**：
- 如果問題只涉及一個具體面向（如「續約申請」「養寵物規定」），不需拆分
- 如果問題涉及多個面向（如「退租流程」包含通知、點交、押金、結算），需要拆分
- 每個面向必須是可以獨立回答的具體問題

**輸出 JSON**：
{{
  "needs_split": true 或 false,
  "aspects": ["面向1的具體問題", "面向2的具體問題"]
}}

如果 needs_split = false，aspects 留空陣列。
只輸出 JSON。
"""

    async def _verify_content_quality(self, question: str, content: str, content_type: str = "SOP") -> Dict:
        """用第二次 AI call 驗證生成內容的品質

        檢查三項：
        1. 是否編造資訊（電話、Email、具體數字）
        2. 是否空泛（只有廢話沒有實質內容）
        3. 是否對所有租客適用（不是因人而異的答案）

        Args:
            question: 原始問題
            content: 生成的內容
            content_type: 內容類型（SOP / Knowledge）

        Returns:
            {"passed": bool, "reasons": List[str]}
        """
        if not self.client:
            return {"passed": True, "reasons": []}

        prompt = f"""你是品質審查員，檢查以下 AI 生成的{content_type}內容是否合格。

**原始問題**：{question}

**生成內容**：
{content}

**檢查項目**（全部通過才合格）：

1. **是否編造資訊？**
   - 是否包含看起來像真實但可能是編造的電話號碼、Email、網址？
   - 是否編造了具體的天數、金額、百分比等數字？（如「30天內退還」「扣除10%」）
   - 注意：「請聯繫管理師確認」不算編造

2. **是否空泛？**
   - 內容是否只是在重複問題或說廢話？
   - 去掉「請聯繫管理師」等話，剩下的內容是否有實質資訊？
   - 實質內容是否少於 50 字？

3. **是否完全無法通用？**
   - 注意：業務流程、政策規範、操作說明本質上是通用的，即使細節因業者而異也算通用
   - 只有回答明確針對「某一個特定租客」或「某一個特定物件」的個人資料才算不通用
   - 例如「您的租金是 15,000 元」不通用，但「租金繳費方式有匯款和信用卡」是通用的
   - 寧可判定為通用，不要過度攔截

**輸出 JSON**：
{{
  "fabricated": false,
  "vague": false,
  "not_universal": false,
  "passed": true,
  "reasons": []
}}

如果任何一項為 true，passed 必須為 false，並在 reasons 中說明原因。
只輸出 JSON。"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            if self.cost_tracker and hasattr(response, 'usage'):
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

    async def _is_sop_topic(self, question: str) -> bool:
        """用 AI 判斷問題是否適合生成 SOP（業務流程/政策規範）

        Args:
            question: 問題文字

        Returns:
            True 如果問題適合生成 SOP
        """
        if not self.client:
            return True  # 沒有 AI client 時預設通過

        prompt = f"""判斷以下問題是否適合建立「業務流程 SOP」或「政策規範」。

**問題**：{question}

**適合生成 SOP 的問題**（回答 yes）：
- 涉及租客/房東需要執行的「完整步驟流程」（退租怎麼做、報修流程、續約申請）
- 政策規範說明（寵物飼養規定、訪客過夜規範、雙人入住政策）

**特別注意**：如果問題只是問一個「數值」或「時間點」（例如：提前幾天通知、幾天內退還、通知時間是多久），這不是流程，這是知識點，回答 no

**不適合生成 SOP 的問題**（回答 no）：
- 查詢特定數值（電費多少、租金多少、押金金額）→ 這是 API 查詢
- 系統畫面操作（怎麼上傳匯款證明、哪裡看帳單、怎麼登入、查詢繳費紀錄）→ 這是系統操作指南
- 費用計算方式（電費怎麼算、水費計費標準）→ 這因物件而異
- 費用支付管道（電費支付方式、水費怎麼繳）→ 這因物件/業者而異
- 系統功能說明（有哪些通知、自動對帳功能）→ 這是系統說明
- 任何「查詢」「查看」「在哪看」類問題 → 通常是系統操作

只輸出 JSON：{{"is_sop": true/false, "reason": "一句話理由"}}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("is_sop", True)
        except Exception as e:
            print(f"   ⚠️ SOP 主題判斷失敗，預設通過: {e}")
            return True

    def _load_form_schemas(self) -> List[Dict]:
        """從資料庫載入可用表單清單（快取）"""
        if self._form_schemas_cache is not None:
            return self._form_schemas_cache

        conn = self.db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT form_id, form_name, description, on_complete_action,
                       fields::text, api_config::text
                FROM form_schemas
                WHERE is_active = true
                ORDER BY id
            """)
            rows = cur.fetchall()
            forms = []
            for row in rows:
                field_names = []
                try:
                    fields = json.loads(row[4]) if row[4] else []
                    field_names = [f.get('field_label', f.get('field_name', '')) for f in fields]
                except (json.JSONDecodeError, TypeError):
                    pass
                forms.append({
                    'form_id': row[0],
                    'form_name': row[1],
                    'description': row[2] or '',
                    'action_type': row[3],  # show_knowledge or call_api
                    'field_names': field_names,
                })
            self._form_schemas_cache = forms
            return forms
        finally:
            self.db_pool.putconn(conn)

    def _build_available_forms_section(self) -> str:
        """組裝可用表單清單文字，供 prompt 注入"""
        forms = self._load_form_schemas()
        if not forms:
            return "（系統目前沒有可用表單）"

        lines = ["**可用表單清單（選擇 next_form_id 時必須從此清單中選）**：", ""]

        # 分類：資料收集表單 vs API 查詢表單
        collect_forms = [f for f in forms if f['action_type'] == 'show_knowledge']
        api_forms = [f for f in forms if f['action_type'] == 'call_api']

        if collect_forms:
            lines.append("📋 **資料收集表單**（next_action = form_fill）：")
            for f in collect_forms:
                fields_str = "、".join(f['field_names'][:4]) if f['field_names'] else ''
                lines.append(f"- `{f['form_id']}` → {f['form_name']}（欄位：{fields_str}）")
            lines.append("")

        if api_forms:
            lines.append("🔍 **API 查詢表單**（next_action = api_call）：")
            for f in api_forms:
                fields_str = "、".join(f['field_names'][:4]) if f['field_names'] else ''
                desc = f"（{f['description']}）" if f['description'] else ''
                lines.append(f"- `{f['form_id']}` → {f['form_name']}{desc}（欄位：{fields_str}）")
            lines.append("")

        return "\n".join(lines)

    async def _decompose_topic(self, question: str) -> List[str]:
        """判斷問題是否需要拆分成多個面向，回傳面向清單"""
        try:
            prompt = self.TOPIC_DECOMPOSE_PROMPT.format(question=question)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            if result.get("needs_split") and result.get("aspects"):
                aspects = result["aspects"]
                if len(aspects) > 1:
                    print(f"   🔀 大主題拆解：「{question}」→ {len(aspects)} 個面向")
                    for i, a in enumerate(aspects, 1):
                        print(f"      {i}. {a}")
                    return aspects
        except Exception as e:
            print(f"   ⚠️ 主題拆解失敗，照常生成: {e}")
        return []

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

        # SOP 主題過濾：用 AI 判斷是否適合生成 SOP，不適合的降級為 system_config
        # form_fill 類型直接通過（表單引導本身就需要 SOP 來觸發）
        sop_gaps = []
        self._downgraded_gaps = []  # 暫存降級的 gaps，讓 coordinator 可以取回
        for gap in gaps:
            question = gap.get('question', '')
            gap_type = gap.get('gap_type', '')
            if gap_type == 'form_fill':
                sop_gaps.append(gap)
                print(f"   📋 form_fill 直接進 SOP: {question[:50]}")
                continue
            is_sop = await self._is_sop_topic(question)
            if is_sop:
                sop_gaps.append(gap)
            else:
                gap_copy = gap.copy()
                gap_copy['gap_type'] = 'system_config'
                gap_copy['downgraded_from'] = 'sop_knowledge'
                self._downgraded_gaps.append(gap_copy)
                print(f"   📋 非 SOP 主題，降級 → system_config: {question[:50]}")

        if self._downgraded_gaps:
            print(f"🔒 SOP 白名單過濾：{len(self._downgraded_gaps)} 題降級為一般知識")

        gaps = sop_gaps
        generated_sops = []

        if not gaps:
            print(f"   ℹ️  白名單過濾後無 SOP 題目需生成")
            return generated_sops

        # 主題拆解：大主題拆成多個面向
        # 拆解後的子問題也必須通過 SOP AI 判斷
        expanded_gaps = []
        for gap in gaps:
            aspects = await self._decompose_topic(gap.get('question', ''))
            if aspects:
                for aspect in aspects:
                    # 拆解後的子問題也做 SOP 判斷
                    is_sop = await self._is_sop_topic(aspect)
                    if not is_sop:
                        print(f"   📋 拆解子面向非 SOP，跳過: {aspect[:50]}")
                        continue
                    sub_gap = dict(gap)
                    sub_gap['question'] = aspect
                    sub_gap['original_question'] = gap.get('question', '')
                    expanded_gaps.append(sub_gap)
            else:
                expanded_gaps.append(gap)

        if len(expanded_gaps) != len(gaps):
            print(f"   📊 主題拆解後：{len(gaps)} 題 → {len(expanded_gaps)} 題")

        # 批次處理
        for i in range(0, len(expanded_gaps), batch_size):
            batch = expanded_gaps[i:i + batch_size]
            print(f"\n   處理批次 {i // batch_size + 1}/{(len(expanded_gaps) + batch_size - 1) // batch_size}")

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
            # 閾值：similarity > 0.70 視為相似（距離 < 0.30）
            cur.execute("""
                SELECT
                    id,
                    item_name,
                    1 - (primary_embedding <=> %s::vector) AS similarity_score
                FROM vendor_sop_items
                WHERE vendor_id = %s
                  AND primary_embedding IS NOT NULL
                  AND 1 - (primary_embedding <=> %s::vector) > 0.70
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
                  AND 1 - (embedding <=> %s::vector) > 0.70
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

        # 構建 Prompt（注入可用表單清單）
        available_forms_section = self._build_available_forms_section()
        prompt = self.SOP_GENERATION_PROMPT.format(
            question=question,
            related_questions=related_questions_text,
            gap_type=gap_type,
            failure_reason=failure_reason,
            priority=priority,
            available_forms_section=available_forms_section
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

            # 後處理品質檢查：攔截編造內容
            sop_content = sop_data.get('content', '')
            fabricated = []
            if _FABRICATED_PHONE_RE.search(sop_content):
                fabricated.append('電話號碼')
            if _FABRICATED_EMAIL_RE.search(sop_content):
                fabricated.append('Email')
            if _FABRICATED_URL_RE.search(sop_content):
                fabricated.append('網址')
            if fabricated:
                print(f"   ⛔ 攔截 SOP（內容包含編造的 {', '.join(fabricated)}）: {sop_data.get('item_name', '?')}")
                return None
            # 替換禁用稱呼
            for term in _BANNED_TERMS:
                if term in sop_content:
                    sop_data['content'] = sop_data['content'].replace(term, '管理師')
                    print(f"   🔄 已將「{term}」替換為「管理師」")

            # 品質檢查：標記空泛回答（不攔截，讓人工審核決定）
            content_without_contact = re.sub(r'(請|可以|建議|隨時).*?(聯繫|聯絡|詢問|洽詢).*?管理師.*', '', sop_data['content'])
            content_without_contact = re.sub(r'(如果|若).*?(問題|疑問|需要).*', '', content_without_contact)
            meaningful_chars = len(content_without_contact.strip())
            if meaningful_chars < 50:
                sop_data['_quality_warning'] = f'內容可能空泛（實質內容僅 {meaningful_chars} 字），建議人工補充'
                print(f"   ⚠️  SOP 內容偏短（{meaningful_chars} 字），標記待人工審核: {sop_data.get('item_name', '?')}")

            # 🔍 AI 品質驗證（第二次 AI call）
            quality_result = await self._verify_content_quality(
                question=question,
                content=sop_data['content'],
                content_type="SOP"
            )
            if not quality_result["passed"]:
                reasons = ", ".join(quality_result["reasons"])
                print(f"   ⛔ 品質驗證未通過: {sop_data.get('item_name', '?')} — {reasons}")
                return None

            # 設定預設值
            # 知識完善迴圈生成的 SOP 預設應為 'auto'，以便自動觸發
            sop_data.setdefault('trigger_mode', 'auto')
            sop_data.setdefault('trigger_keywords', [])
            sop_data.setdefault('next_action', 'none')
            sop_data.setdefault('next_form_id', None)
            sop_data.setdefault('immediate_prompt', '')
            sop_data.setdefault('keywords', [])

            # 🔒 [TODO-13.1] 回測驗證通過後啟用 form_id 映射
            # 目前強制設定 next_form_id 為 None，避免外鍵約束錯誤
            # 啟用方式：移除下面這行，改用下方的驗證邏輯
            sop_data['next_form_id'] = None
            # --- 啟用後的驗證邏輯 ---
            # valid_form_ids = {f['form_id'] for f in self._load_form_schemas()}
            # if sop_data.get('next_form_id') not in valid_form_ids:
            #     sop_data['next_form_id'] = None

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
                    # 檢查最高相似度，超過 0.75 直接跳過不生成
                    max_similarity = max(
                        item.get('similarity_score', 0)
                        for item in duplicate_check.get('items', [])
                    ) if duplicate_check.get('items') else 0
                    if max_similarity >= 0.75:
                        most_similar = duplicate_check['items'][0]
                        print(f"   ⛔ 跳過重複 SOP（向量相似度 {max_similarity:.1%}）: {sop_data['item_name']}")
                        print(f"      相似項: [{most_similar['source_table']}] {most_similar['item_name']}")
                        return None
                    similar_knowledge = duplicate_check  # 相似度不高，記錄但繼續生成

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
