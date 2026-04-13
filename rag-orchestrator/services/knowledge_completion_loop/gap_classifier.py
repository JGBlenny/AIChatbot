"""
知識缺口分類器

使用 OpenAI API 對知識缺口進行智能分類和聚類
"""

import asyncio
import json
from typing import List, Dict, Optional
from openai import AsyncOpenAI


class GapClassifier:
    """知識缺口分類器

    功能：
    1. 分類問題類型（SOP、API、表單等）
    2. 識別重複/相似問題
    3. 建議處理策略
    """

    # 分類 Prompt
    CLASSIFICATION_PROMPT = """你是一個專業的知識庫管理專家。請分析以下問題，並進行分類。

**問題列表**：
{questions}

---

**分類方法 — 依序判斷（決策樹）**：

對每個問題，按以下順序判斷，**命中第一個就停止**：

**第 ① 步：答案是否因人/物件/業者/租約而異？**
→ 如果回答這個問題需要知道「哪個物件」「哪個租客」「哪個業者」「哪份租約」才能給出正確答案
→ 分類為 **api_query**，should_generate_knowledge = **false**
→ 判斷方式：把問題套入「A 物件的答案和 B 物件的答案會不同嗎？」如果會 → api_query
→ 涵蓋範圍（不限於以下例子）：
  - 費用金額類：租金、電費、水費、瓦斯費、管理費、停車費、網路費、押金金額
  - 帳單/帳務類：帳單查詢、匯款帳號、轉帳資訊、收款帳戶
  - 繳費條件類：繳費頻率、能否分期、能否半月繳、付款期限
  - 計量/抄表類：電表、水表、抄表日期、度數
  - 合約資訊類：合約到期日、租期多長、租約內容
  - 物件資訊類：房東自租或代管、客服電話、聯絡方式
→ **核心判斷**：如果答案會因為「不同租約」或「不同物件」而不同，就是 api_query

**第 ② 步：是否涉及 JGB 平台的畫面操作或系統功能？**
→ 如果需要看平台 UI 畫面才能回答，或是在問「系統有什麼功能」
→ 分類為 **jgb_system**，should_generate_knowledge = **false**
→ 判斷方式：回答時是否需要說「點擊某按鈕」「進入某頁面」「在某選單中」，或在描述系統功能
→ 涵蓋範圍（不限於以下例子）：
  - UI 操作：上傳匯款證明、查繳費紀錄、產出帳單報表、匯出發票
  - 帳號操作：登入、密碼、切換團隊
  - 資料管理：資料刪除、資料保留、搬出後資料保留
  - 系統功能：系統通知、自動對帳、自動化功能、APP 功能
  - 發票操作：開發票、發票作廢、差額發票
→ **核心判斷**：如果回答需要描述「在系統裡怎麼操作」或「系統提供什麼功能」，就是 jgb_system

**第 ③ 步：是否需要用戶填寫表單提供資料？**
→ 如果問題的解決方式是「引導用戶填表」（報修、找房、投訴、申請）
→ 分類為 **form_fill**，should_generate_knowledge = **true**
→ 例如：我想找房、我要報修、我要投訴、申請機車位

**第 ④ 步：是否涉及租客/房東需要主動執行的業務流程？**
→ 如果問題的答案包含「步驟」或「需要租客/房東做什麼事」
→ 分類為 **sop_knowledge**，should_generate_knowledge = **true**
→ 判斷方式：回答時是否會出現「第一步...第二步...」或「你需要先...然後...」
→ 例如：續約申請、退租通知、入住手續、訪客過夜規範、寵物飼養規定

**第 ⑤ 步：以上都不是**
→ 分類為 **system_config**，should_generate_knowledge = **true**
→ 這是可以用固定文字直接回答的概念性知識
→ 例如：包租和代管的差別、為什麼要收管理費、單合約和雙合約的區別

---

**任務**：
1. 對每個問題，**按照上述 ①→②→③→④→⑤ 順序判斷**，命中即停止
2. 為每個分類給出 **confidence**（0-1 之間的浮點數），表示你對這個分類結果的確定程度
   - 1.0 = 非常確定，問題明確屬於該類別
   - 0.8+ = 有信心，大部分情況下正確
   - 0.5-0.8 = 不確定，可能需要人工判斷
   - < 0.5 = 很不確定
3. 適度識別並聚類相似問題
4. 給出處理建議

**聚類原則**：
- 只有問的是「同一個具體面向」才聚類，每個聚類最多 2-3 個問題
- 大主題的不同面向必須拆成獨立聚類（退租通知 vs 押金退還 vs 退租點交 = 三個獨立聚類）
- 同一分類內才能聚類（不要跨 sop_knowledge 和 system_config 聚類）

**輸出格式**（JSON）：
{{
  "classifications": [
    {{
      "question_index": 1,
      "question": "問題內容",
      "category": "sop_knowledge|api_query|form_fill|system_config|jgb_system",
      "confidence": 0.95,
      "reasoning": "分類理由（說明為什麼在決策樹的這一步命中）",
      "should_generate_knowledge": true|false,
      "similar_to": [2, 3]  // 與哪些問題相似（問題編號）
    }}
  ],
  "clusters": [
    {{
      "cluster_id": 1,
      "category": "sop_knowledge",
      "question_indices": [1, 5, 8],
      "representative_question": "代表性問題",
      "combined_answer_needed": "是否需要合併成一個答案",
      "reasoning": "聚類理由"
    }}
  ],
  "summary": {{
    "total_questions": 46,
    "sop_knowledge_count": 15,
    "api_query_count": 10,
    "form_fill_count": 8,
    "system_config_count": 5,
    "jgb_system_count": 7,
    "should_generate_count": 20,
    "recommended_clusters": 8
  }}
}}

只輸出 JSON，不要其他說明。"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """初始化分類器

        Args:
            openai_api_key: OpenAI API Key
            model: 使用的模型（建議 gpt-4o-mini 或 gpt-4o）
        """
        self.openai_api_key = openai_api_key
        self.model = model

        if openai_api_key:
            self.client = AsyncOpenAI(api_key=openai_api_key)
        else:
            self.client = None

    async def pre_filter_dynamic_questions(self, gaps: List[Dict]) -> List[Dict]:
        """預過濾：用輕量 AI call 判斷問題是否能用固定文字回答所有租客

        無法用固定文字回答的（因人/物件而異）直接跳過不送分類器。

        Args:
            gaps: 知識缺口列表

        Returns:
            List[Dict]: 過濾後的 gaps（只保留可生成靜態知識的）
        """
        if not self.client or not gaps:
            return gaps

        # 批次判斷（一次最多 30 題）
        questions_text = "\n".join([
            f"{i+1}. {gap.get('question', '')}"
            for i, gap in enumerate(gaps[:30])
        ])

        prompt = f"""判斷以下每個問題是否屬於「需要查詢特定租客/物件資料才能回答」的個人化查詢。

**回答 "no"（過濾掉）的條件非常嚴格**：
只有明確需要查詢「某個特定租客」或「某個特定物件」的即時資料才回答 "no"。
例如：「我的租金多少？」「我的電費帳單？」「我的合約到期日？」「客服電話幾號？」

**回答 "yes"（保留）**：
- 業務流程問題（如何續約、退租流程、報修怎麼做）→ yes
- 政策規範問題（可以養寵物嗎、朋友能過夜嗎、雙人入住規定）→ yes
- 概念說明（單合約雙合約差別、包租代管是什麼）→ yes
- 系統操作說明（怎麼上傳匯款證明、怎麼看帳單）→ yes
- 通用繳費方式（有哪些付款方式、何時繳租金）→ yes
- 發票相關（發票怎麼開、發票作廢）→ yes

寧可多保留，不要誤殺。不確定就回答 "yes"。

**問題列表**：
{questions_text}

**輸出 JSON**：
{{
  "results": [
    {{"index": 1, "answer": "yes|no", "reason": "簡短理由"}}
  ]
}}

只輸出 JSON。"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            results_map = {}
            for r in result.get("results", []):
                results_map[r.get("index", 0)] = r.get("answer", "yes")

            filtered = []
            skipped = 0
            for i, gap in enumerate(gaps):
                answer = results_map.get(i + 1, "yes")
                if answer == "no":
                    skipped += 1
                    print(f"   🚫 預過濾跳過（因人而異）: {gap.get('question', '')[:50]}")
                else:
                    filtered.append(gap)

            if skipped > 0:
                print(f"🔒 預過濾：{skipped}/{len(gaps)} 題無法用固定文字回答，已跳過")

            return filtered

        except Exception as e:
            print(f"⚠️  預過濾失敗，跳過此步驟: {e}")
            return gaps

    # 聚類規則（精準版 - 最小化聚類，避免名稱與內容錯配）
    cluster_rules = [
            # 【拆分】雙人入住政策（獨立）
            {
                "keywords": ["雙人", "雙人入住", "兩人", "2人", "單人", "入住人數"],
                "name": "雙人入住政策",
                "category": "sop_knowledge"
            },
            # 【拆分】訪客過夜規範（獨立）
            {
                "keywords": ["過夜", "朋友", "訪客", "帶朋友", "留宿", "同住"],
                "name": "訪客過夜規範",
                "category": "sop_knowledge"
            },
            # 【拆分】租金支付方式（獨立）
            {
                "keywords": ["租金", "支付", "繳費", "匯款", "付款", "繳納", "怎麼付"],
                "name": "租金支付方式",
                "category": "sop_knowledge"
            },
            # 【拆分】租金對帳流程（獨立）
            {
                "keywords": ["對帳", "帳單", "確認", "收據", "繳費證明"],
                "name": "租金對帳流程",
                "category": "sop_knowledge"
            },
            # 【拆分】發票開立（獨立）
            {
                "keywords": ["發票", "開立", "報帳", "憑證", "開發票"],
                "name": "發票開立流程",
                "category": "sop_knowledge"
            },
            # 【拆分】發票作廢（獨立）
            {
                "keywords": ["作廢", "發票作廢", "取消發票"],
                "name": "發票作廢流程",
                "category": "sop_knowledge"
            },
            # 合約建立流程（保持）
            {
                "keywords": ["合約", "單合約", "雙合約", "簽約", "建立", "契約", "協議"],
                "name": "合約建立流程",
                "category": "sop_knowledge"
            },
            # 【拆分】租約續約（獨立）
            {
                "keywords": ["續約", "續租", "延長", "繼續租"],
                "name": "租約續約流程",
                "category": "sop_knowledge"
            },
            # 【拆分】退租解約（獨立）
            {
                "keywords": ["退租", "解約", "終止", "搬遷", "搬走", "不租"],
                "name": "退租解約流程",
                "category": "sop_knowledge"
            },
            # 維修報修流程（保持）
            {
                "keywords": ["維修", "報修", "修繕", "損壞", "故障", "修理", "維護"],
                "name": "維修報修流程",
                "category": "sop_knowledge"
            },
            # 停車位管理（保持）
            {
                "keywords": ["停車", "車位", "停車位", "車輛", "汽車", "機車"],
                "name": "停車位申請與管理",
                "category": "sop_knowledge"
            },
            # 寵物飼養規範（保持）
            {
                "keywords": ["寵物", "養寵物", "狗", "貓", "動物"],
                "name": "寵物飼養規範",
                "category": "sop_knowledge"
            },
            # 公共設施使用規範（保持）
            {
                "keywords": ["公共設施", "健身房", "交誼廳", "洗衣", "頂樓", "設施"],
                "name": "公共設施使用規範",
                "category": "sop_knowledge"
            },
            # 噪音管理（保持）
            {
                "keywords": ["噪音", "吵鬧", "安寧", "鄰居", "音量", "打擾"],
                "name": "噪音管理規範",
                "category": "sop_knowledge"
            },
            # 鑰匙與門禁管理（保持）
            {
                "keywords": ["鑰匙", "門禁", "卡片", "遺失", "複製", "門鎖"],
                "name": "鑰匙與門禁管理",
                "category": "sop_knowledge"
            },
            # 水電瓦斯費用（保持）
            {
                "keywords": ["水費", "電費", "瓦斯", "水電", "度數", "抄表"],
                "name": "水電瓦斯費用",
                "category": "sop_knowledge"
            },
            # 垃圾清運（保持）
            {
                "keywords": ["垃圾", "資源回收", "清潔", "打掃", "環境"],
                "name": "垃圾清運與清潔",
                "category": "sop_knowledge"
            },
            # 裝潢改建（保持）
            {
                "keywords": ["裝潢", "裝修", "改建", "施工", "釘釘子", "油漆"],
                "name": "裝潢改建申請",
                "category": "sop_knowledge"
            },
            # 房東收回房屋（保持）
            {
                "keywords": ["房東", "收回", "收房", "提前", "通知"],
                "name": "房東收回房屋流程",
                "category": "sop_knowledge"
            },
            # 【拆分】押金收取（獨立）
            {
                "keywords": ["押金", "保證金", "繳交", "給押金"],
                "name": "押金收取規範",
                "category": "sop_knowledge"
            },
            # 【拆分】押金退還（獨立）
            {
                "keywords": ["退還", "退押金", "押金退還", "扣款", "返還"],
                "name": "押金退還流程",
                "category": "sop_knowledge"
            },
            # 表單填寫類（保持）
            {
                "keywords": ["申請", "表單", "填寫", "辦理", "登記"],
                "name": "申請與表單填寫",
                "category": "form_fill"
            },
            # 系統操作類（保持）
            {
                "keywords": ["系統", "功能", "操作", "如何使用", "登入", "匯出"],
                "name": "系統操作說明",
                "category": "system_config"
            }
        ]

    # 硬編碼前置規則：明確的 api_query / jgb_system 不交給 AI 判斷
    # 其他模糊情況交由 AI 決策樹 + confidence 機制處理
    # 單關鍵字：只要出現就攔
    # 硬編碼黑名單只保留最高頻、最明確的關鍵字作為安全網
    # 其他邊界案例靠上方加強過的 AI 決策樹 prompt 判斷
    _FORCE_API_QUERY_KEYWORDS = [
        '電費', '水費', '瓦斯費', '管理費', '停車費', '網路費',
        '帳單', '客服電話',
    ]

    _FORCE_JGB_SYSTEM_KEYWORDS = [
        '系統', '登入', '密碼', 'APP', 'app',
        '發票',
    ]

    # 組合關鍵字：問題中同時包含這些詞就攔（解決「系統有哪些通知」這類中間隔了其他字的情況）
    _FORCE_API_QUERY_COMBOS = [
        # (所有詞都出現 → 分類)
        (['自租', '代管'], 'api_query'),
        (['房東', '自租'], 'api_query'),
    ]

    _FORCE_JGB_SYSTEM_COMBOS = [
    ]

    def _pre_classify(self, question: str) -> Optional[str]:
        """硬編碼前置分類：明確的 api_query / jgb_system 不交給 AI"""
        q = question.lower()
        # 單關鍵字比對
        for kw in self._FORCE_API_QUERY_KEYWORDS:
            if kw in q:
                return 'api_query'
        for kw in self._FORCE_JGB_SYSTEM_KEYWORDS:
            if kw in q:
                return 'jgb_system'
        # 組合關鍵字比對
        for combo, category in self._FORCE_API_QUERY_COMBOS:
            if all(word in q for word in combo):
                return category
        for combo, category in self._FORCE_JGB_SYSTEM_COMBOS:
            if all(word in q for word in combo):
                return category
        return None

    async def classify_gaps(
        self,
        gaps: List[Dict],
        batch_size: int = 50
    ) -> Dict:
        """分類知識缺口

        Args:
            gaps: 知識缺口列表，每個包含 question 等欄位
            batch_size: 每批處理的問題數量

        Returns:
            Dict: 分類結果
            {
                "classifications": [...],
                "clusters": [...],
                "summary": {...}
            }
        """
        # 前置過濾：硬編碼規則強制分類
        pre_classified = {}
        ai_gaps = []
        for i, gap in enumerate(gaps):
            forced = self._pre_classify(gap.get("question", ""))
            if forced:
                pre_classified[i] = forced
            else:
                ai_gaps.append((i, gap))

        if pre_classified:
            forced_api = sum(1 for v in pre_classified.values() if v == 'api_query')
            forced_jgb = sum(1 for v in pre_classified.values() if v == 'jgb_system')
            print(f"🔒 前置分類：api_query={forced_api}, jgb_system={forced_jgb}（不送 AI）")

        # 只把未被前置分類的 gap 送 AI
        if not ai_gaps:
            # 全部被前置分類了
            classifications = []
            for i, gap in enumerate(gaps):
                cat = pre_classified.get(i, 'system_config')
                classifications.append({
                    "question_index": i + 1,
                    "question": gap.get("question", ""),
                    "category": cat,
                    "reasoning": "硬編碼前置規則",
                    "should_generate_knowledge": cat in ['sop_knowledge', 'form_fill', 'system_config'],
                    "similar_to": []
                })
            return {
                "classifications": classifications,
                "clusters": [],
                "summary": self._calculate_summary(classifications)
            }

        # AI 分類（只處理未被前置分類的 gap）
        ai_only_gaps = [gap for _, gap in ai_gaps]
        if not self.client:
            ai_result = await self._stub_classify(ai_only_gaps)
        elif len(ai_only_gaps) <= batch_size:
            ai_result = await self._classify_batch(ai_only_gaps)
        else:
            ai_classifications = []
            ai_clusters = []
            for i in range(0, len(ai_only_gaps), batch_size):
                batch = ai_only_gaps[i:i+batch_size]
                result = await self._classify_batch(batch, offset=i)
                ai_classifications.extend(result["classifications"])
                ai_clusters.extend(result["clusters"])
            ai_result = {"classifications": ai_classifications, "clusters": ai_clusters}

        # 合併前置分類和 AI 分類結果
        ai_class_map = {}
        for c in ai_result.get("classifications", []):
            ai_class_map[c.get("question", "")] = c

        merged_classifications = []
        for i, gap in enumerate(gaps):
            question = gap.get("question", "")
            if i in pre_classified:
                cat = pre_classified[i]
                merged_classifications.append({
                    "question_index": i + 1,
                    "question": question,
                    "category": cat,
                    "reasoning": f"硬編碼前置規則 → {cat}",
                    "should_generate_knowledge": False,
                    "similar_to": []
                })
            elif question in ai_class_map:
                c = ai_class_map[question]
                c["question_index"] = i + 1  # 修正索引為全局索引
                merged_classifications.append(c)
            else:
                merged_classifications.append({
                    "question_index": i + 1,
                    "question": question,
                    "category": "system_config",
                    "reasoning": "fallback",
                    "should_generate_knowledge": True,
                    "similar_to": []
                })

        # clusters 保留 AI 回傳的（索引需要重映射到全局）
        ai_clusters = ai_result.get("clusters", [])
        ai_index_to_global = {}
        for ai_idx, (global_idx, _) in enumerate(ai_gaps):
            ai_index_to_global[ai_idx + 1] = global_idx + 1  # 1-based

        for cluster in ai_clusters:
            cluster["question_indices"] = [
                ai_index_to_global.get(idx, idx)
                for idx in cluster.get("question_indices", [])
            ]

        return {
            "classifications": merged_classifications,
            "clusters": ai_clusters,
            "summary": self._calculate_summary(merged_classifications)
        }

    async def _classify_batch(
        self,
        gaps: List[Dict],
        offset: int = 0
    ) -> Dict:
        """分類單批問題"""

        # 構建問題列表
        questions_text = "\n".join([
            f"{i+1+offset}. {gap['question']}"
            for i, gap in enumerate(gaps)
        ])

        # 構建 Prompt
        prompt = self.CLASSIFICATION_PROMPT.format(
            questions=questions_text
        )

        try:
            # 調用 OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個專業的知識庫管理專家，擅長分類和組織問題。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 較低溫度保證穩定性
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            # 解析回應
            content = response.choices[0].message.content
            result = json.loads(content)

            clusters = result.get("clusters", [])
            print(f"✅ OpenAI 分類完成：{len(gaps)} 個問題")
            print(f"   OpenAI 返回聚類數：{len(clusters)}")

            # 總是使用本地聚類邏輯來拆分過大的聚類
            if clusters:
                print(f"🔍 檢查 OpenAI 聚類是否需要進一步拆分...")
                refined_clusters = self._refine_openai_clusters(clusters, result.get("classifications", []), gaps)
                if len(refined_clusters) > len(clusters):
                    print(f"   ✅ 本地規則拆分：{len(clusters)} 個 → {len(refined_clusters)} 個聚類")
                    result["clusters"] = refined_clusters
                else:
                    print(f"   ℹ️  OpenAI 聚類已經足夠精準，無需拆分")
            else:
                print(f"⚠️  OpenAI 未返回聚類，啟用本地聚類邏輯...")
                result["clusters"] = self._local_clustering(result.get("classifications", []), gaps)
                print(f"   本地聚類產生：{len(result['clusters'])} 個聚類")

            return result

        except Exception as e:
            print(f"❌ OpenAI 分類失敗: {e}")
            return await self._stub_classify(gaps, offset)

    async def _stub_classify(
        self,
        gaps: List[Dict],
        offset: int = 0
    ) -> Dict:
        """Stub 模式：簡單的分類邏輯"""

        classifications = []

        for i, gap in enumerate(gaps):
            question = gap["question"].lower()

            # 簡單的關鍵字匹配
            if any(keyword in question for keyword in ["租金", "房租", "費用", "價格"]):
                category = "api_query"
                should_generate = False
            elif any(keyword in question for keyword in ["如何", "怎麼", "流程", "步驟"]):
                category = "sop_knowledge"
                should_generate = True
            elif any(keyword in question for keyword in ["我想", "申請", "辦理"]):
                category = "form_fill"
                should_generate = True
            else:
                category = "sop_knowledge"
                should_generate = True

            classifications.append({
                "question_index": i + 1 + offset,
                "question": gap["question"],
                "category": category,
                "reasoning": "Stub 模式分類",
                "should_generate_knowledge": should_generate,
                "similar_to": []
            })

        summary = {
            "total_questions": len(gaps),
            "sop_knowledge_count": sum(1 for c in classifications if c["category"] == "sop_knowledge"),
            "api_query_count": sum(1 for c in classifications if c["category"] == "api_query"),
            "form_fill_count": sum(1 for c in classifications if c["category"] == "form_fill"),
            "system_config_count": sum(1 for c in classifications if c["category"] == "system_config"),
            "jgb_system_count": sum(1 for c in classifications if c["category"] == "jgb_system"),
            "should_generate_count": sum(1 for c in classifications if c["should_generate_knowledge"]),
            "recommended_clusters": 0
        }

        return {
            "classifications": classifications,
            "clusters": [],
            "summary": summary
        }

    def _calculate_summary(self, classifications: List[Dict]) -> Dict:
        """計算摘要統計"""

        from collections import Counter

        categories = Counter([c["category"] for c in classifications])
        should_generate_count = sum(1 for c in classifications if c["should_generate_knowledge"])

        return {
            "total_questions": len(classifications),
            "sop_knowledge_count": categories.get("sop_knowledge", 0),
            "api_query_count": categories.get("api_query", 0),
            "form_fill_count": categories.get("form_fill", 0),
            "system_config_count": categories.get("system_config", 0),
            "jgb_system_count": categories.get("jgb_system", 0),
            "should_generate_count": should_generate_count,
            "recommended_clusters": 0  # TODO: 從 clusters 計算
        }

    def filter_gaps_for_generation(
        self,
        gaps: List[Dict],
        classification_result: Dict
    ) -> List[Dict]:
        """根據分類結果過濾出需要生成知識的缺口

        Args:
            gaps: 原始知識缺口列表
            classification_result: 分類結果

        Returns:
            List[Dict]: 過濾後的知識缺口列表（包含 gap_type 欄位）
        """
        # 創建分類索引對應字典
        classification_map = {}
        for classification in classification_result["classifications"]:
            # question_index 是從 1 開始的
            idx = classification["question_index"] - 1
            classification_map[idx] = classification

        # 過濾缺口並加入 gap_type
        filtered_gaps = []
        for i, gap in enumerate(gaps):
            classification = classification_map.get(i)
            if classification and classification["should_generate_knowledge"]:
                # 複製 gap 並加入 gap_type
                gap_with_type = gap.copy()
                gap_with_type['gap_type'] = classification["category"]
                filtered_gaps.append(gap_with_type)

        print(f"✅ 過濾結果：{len(gaps)} 題 → {len(filtered_gaps)} 題需要生成知識")

        return filtered_gaps

    def get_clusters_for_generation(
        self,
        gaps: List[Dict],
        classification_result: Dict
    ) -> List[Dict]:
        """獲取聚類後的代表性缺口

        優先使用 OpenAI 回傳的 clusters，fallback 到本地聚類。

        Args:
            gaps: 原始知識缺口列表
            classification_result: 分類結果（含 classifications + clusters）

        Returns:
            List[Dict]: 聚類後的知識缺口列表（SOP + Knowledge）
        """
        classifications = classification_result.get("classifications", [])
        ai_clusters = classification_result.get("clusters", [])

        # 建立索引到分類的映射
        classification_map = {}
        for classification in classifications:
            idx = classification["question_index"] - 1
            classification_map[idx] = classification

        # 篩選需要生成知識的 gap 索引（信心分數 < 0.8 不生成）
        generatable = {}  # index → (gap, category)
        low_confidence_count = 0
        for i, gap in enumerate(gaps):
            c = classification_map.get(i)
            if c and c.get("should_generate_knowledge"):
                confidence = c.get("confidence", 1.0)
                if confidence < 0.8:
                    low_confidence_count += 1
                    print(f"   ⚠️  跳過低信心分類（{confidence:.2f}）: {gap.get('question', '')[:50]}")
                    continue
                generatable[i] = (gap, c.get("category", "system_config"))
        if low_confidence_count > 0:
            print(f"🔒 信心分數過濾：跳過 {low_confidence_count} 題（confidence < 0.8）")

        # 優先使用 OpenAI clusters
        representative_gaps = []
        clustered_indices = set()

        if ai_clusters:
            print(f"📊 使用 OpenAI 聚類（{len(ai_clusters)} 個）...")
            for cluster in ai_clusters:
                indices = [idx - 1 for idx in cluster.get("question_indices", [])]
                # 只保留需要生成知識的索引
                valid_indices = [idx for idx in indices if idx in generatable]
                if not valid_indices:
                    continue

                # 取第一個作為代表
                rep_idx = valid_indices[0]
                rep_gap, rep_category = generatable[rep_idx]
                result_gap = rep_gap.copy()
                result_gap["cluster_id"] = f"AI_{cluster.get('cluster_id', 0)}"
                result_gap["cluster_size"] = len(valid_indices)
                result_gap["represents_questions"] = [
                    generatable[idx][0]["question"] for idx in valid_indices
                ]
                result_gap["gap_type"] = rep_category
                representative_gaps.append(result_gap)
                clustered_indices.update(valid_indices)

            print(f"   → OpenAI 聚類覆蓋 {len(clustered_indices)} 題")

        # 未被 OpenAI 聚類覆蓋的，每個單獨成為一個 gap
        unclustered_count = 0
        for idx, (gap, category) in generatable.items():
            if idx in clustered_indices:
                continue
            result_gap = gap.copy()
            result_gap["cluster_id"] = f"single_{idx}"
            result_gap["cluster_size"] = 1
            result_gap["represents_questions"] = [gap["question"]]
            result_gap["gap_type"] = category
            representative_gaps.append(result_gap)
            unclustered_count += 1

        if unclustered_count > 0:
            print(f"   → 未聚類（獨立）：{unclustered_count} 題")

        # 統計
        sop_count = sum(1 for g in representative_gaps if g.get("gap_type") in ["sop_knowledge", "form_fill"])
        knowledge_count = sum(1 for g in representative_gaps if g.get("gap_type") == "system_config")
        print(f"✅ 總聚類結果：{len(generatable)} 題 → {len(representative_gaps)} 個聚類（SOP: {sop_count}, Knowledge: {knowledge_count}）")

        return representative_gaps

    def _cluster_by_category(
        self,
        questions: List[Dict],
        category_type: str
    ) -> List[Dict]:
        """對同一類別的問題進行聚類

        Args:
            questions: 問題列表（已包含 gap, index, category 等元數據）
            category_type: 類別類型名稱（用於日誌）

        Returns:
            List[Dict]: 聚類後的代表性問題列表
        """
        if not questions:
            return []

        # 使用本地聚類邏輯（基於關鍵詞）
        from collections import defaultdict

        # 按 category 分組
        category_groups = defaultdict(list)
        for q in questions:
            category = q["category"]
            category_groups[category].append(q)

        clusters = []
        cluster_id = 1

        # 對每個 category 進行聚類
        for category, items in category_groups.items():
            # 使用關鍵詞規則進行聚類
            clustered_indices = set()

            for rule in self.cluster_rules:
                if rule["category"] != category:
                    continue

                matching_items = []
                for item in items:
                    if item["index"] in clustered_indices:
                        continue

                    question = item["gap"].get("question", "")
                    if any(keyword in question for keyword in rule["keywords"]):
                        matching_items.append(item)
                        clustered_indices.add(item["index"])

                if matching_items:
                    # 創建聚類
                    representative_gap = matching_items[0]["gap"].copy()
                    representative_gap["cluster_id"] = f"{category_type}_{cluster_id}"
                    representative_gap["cluster_size"] = len(matching_items)
                    representative_gap["represents_questions"] = [
                        item["gap"]["question"] for item in matching_items
                    ]
                    representative_gap["gap_type"] = category
                    clusters.append(representative_gap)
                    cluster_id += 1

            # 處理未聚類的項目（每個單獨成為一個聚類）
            for item in items:
                if item["index"] not in clustered_indices:
                    representative_gap = item["gap"].copy()
                    representative_gap["cluster_id"] = f"{category_type}_{cluster_id}"
                    representative_gap["cluster_size"] = 1
                    representative_gap["represents_questions"] = [item["gap"]["question"]]
                    representative_gap["gap_type"] = category
                    clusters.append(representative_gap)
                    cluster_id += 1

        return clusters

    def _local_clustering(
        self,
        classifications: List[Dict],
        gaps: List[Dict]
    ) -> List[Dict]:
        """本地聚類邏輯（當 OpenAI 未返回聚類時使用）
        
        基於關鍵詞相似度和分類相同性進行聚類
        """
        from collections import defaultdict
        
        # 按分類分組
        category_groups = defaultdict(list)
        for idx, classification in enumerate(classifications):
            category = classification.get("category", "sop_knowledge")
            if category in ["sop_knowledge", "form_fill", "system_config"]:
                category_groups[category].append({
                    "index": idx + 1,
                    "question": gaps[idx].get("question", ""),
                    "classification": classification
                })
        
        clusters = []
        cluster_id = 1

        # 使用類屬性定義的聚類規則
        cluster_rules = self.cluster_rules
        
        # 對每個分類進行聚類
        for category, items in category_groups.items():
            if not items:
                continue
            
            # 使用規則進行聚類
            clustered_indices = set()
            
            for rule in cluster_rules:
                if rule["category"] != category:
                    continue
                
                matching_items = []
                for item in items:
                    if item["index"] in clustered_indices:
                        continue
                    
                    question = item["question"]
                    if any(keyword in question for keyword in rule["keywords"]):
                        matching_items.append(item)
                        clustered_indices.add(item["index"])
                
                if len(matching_items) >= 2:  # 至少 2 個問題才聚類
                    clusters.append({
                        "cluster_id": cluster_id,
                        "category": category,
                        "question_indices": [item["index"] for item in matching_items],
                        "representative_question": matching_items[0]["question"],
                        "combined_answer_needed": True,
                        "reasoning": f"基於關鍵詞聚類：{rule['name']}"
                    })
                    cluster_id += 1

        return clusters

    def _refine_openai_clusters(
        self,
        openai_clusters: List[Dict],
        classifications: List[Dict],
        gaps: List[Dict]
    ) -> List[Dict]:
        """拆分 OpenAI 返回的過大聚類

        Args:
            openai_clusters: OpenAI 返回的聚類列表
            classifications: 問題分類列表
            gaps: 原始知識缺口列表

        Returns:
            List[Dict]: 拆分後的聚類列表
        """
        from collections import defaultdict

        # 建立問題索引到分類的對應表
        classification_map = {}
        for c in classifications:
            classification_map[c.get("question_index")] = c.get("category")

        # 使用類屬性定義的聚類規則（只提取 SOP 相關規則用於拆分）
        cluster_rules = [rule for rule in self.cluster_rules if rule.get("category") == "sop_knowledge"]

        refined_clusters = []
        next_cluster_id = max([c.get("cluster_id", 0) for c in openai_clusters], default=0) + 1

        for cluster in openai_clusters:
            question_indices = cluster.get("question_indices", [])

            # **關鍵修改：先按 category 拆分聚類**
            # 確保不同 category 的問題不會在同一個聚類中
            category_groups = defaultdict(list)
            for idx in question_indices:
                category = classification_map.get(idx, cluster.get("category", "sop_knowledge"))
                if idx - 1 < len(gaps):
                    category_groups[category].append({
                        "index": idx,
                        "question": gaps[idx - 1].get("question", ""),
                        "category": category
                    })

            # 對每個 category 分組分別處理
            for category, cluster_questions in category_groups.items():
                # 嘗試使用本地規則進一步拆分（僅對 SOP 類型）
                if category in ["sop_knowledge", "form_fill"]:
                    sub_clusters = defaultdict(list)
                    unmatched = []

                    for q in cluster_questions:
                        matched = False
                        for rule in cluster_rules:
                            if any(keyword in q["question"] for keyword in rule["keywords"]):
                                sub_clusters[rule["name"]].append(q)
                                matched = True
                                break

                        if not matched:
                            unmatched.append(q)

                    # 如果成功拆分成多個子聚類，使用拆分結果
                    if len(sub_clusters) > 1 or (len(sub_clusters) == 1 and unmatched):
                        for rule_name, questions in sub_clusters.items():
                            if len(questions) >= 1:  # 至少 1 個問題
                                refined_clusters.append({
                                    "cluster_id": next_cluster_id,
                                    "category": category,
                                    "question_indices": [q["index"] for q in questions],
                                    "representative_question": questions[0]["question"],
                                    "combined_answer_needed": True,
                                    "reasoning": f"按 category 拆分後再用規則拆分：{rule_name}"
                                })
                                next_cluster_id += 1

                        # 如果有未匹配的問題，保留為單獨的聚類
                        if unmatched:
                            refined_clusters.append({
                                "cluster_id": next_cluster_id,
                                "category": category,
                                "question_indices": [q["index"] for q in unmatched],
                                "representative_question": unmatched[0]["question"],
                                "combined_answer_needed": True,
                                "reasoning": f"按 category 拆分後再用規則拆分：其他主題"
                            })
                            next_cluster_id += 1
                    else:
                        # 沒有進一步拆分，但仍按 category 分組
                        refined_clusters.append({
                            "cluster_id": next_cluster_id,
                            "category": category,
                            "question_indices": [q["index"] for q in cluster_questions],
                            "representative_question": cluster_questions[0]["question"],
                            "combined_answer_needed": True,
                            "reasoning": f"按 category 拆分：{category}"
                        })
                        next_cluster_id += 1
                else:
                    # 非 SOP 類型（system_config 等），直接按 category 分組
                    refined_clusters.append({
                        "cluster_id": next_cluster_id,
                        "category": category,
                        "question_indices": [q["index"] for q in cluster_questions],
                        "representative_question": cluster_questions[0]["question"],
                        "combined_answer_needed": True,
                        "reasoning": f"按 category 拆分：{category}"
                    })
                    next_cluster_id += 1

        return refined_clusters
