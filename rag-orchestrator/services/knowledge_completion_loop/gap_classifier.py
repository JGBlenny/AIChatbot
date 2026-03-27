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

**分類標準**：

**【SOP 類型】- 包租/代管的流程規則類知識（流程導向）**

1. **sop_knowledge**（SOP 業務流程知識）
   - **定義**：包租代管的**業務流程、政策規則**類知識
   - **特徵**：流程性、規則性、系統化的步驟說明
   - **核心判斷標準**：涉及房東、租客、合約、房源、租賃等**業務實體的流程與規則**
   - **✓ 應歸類為 SOP 的範例**：
     * 「如何續約」（租約續約流程）
     * 「如何退租」（退租流程）
     * 「房東收回房屋怎麼辦」（業務流程）
     * 「可以養寵物嗎」（租賃政策規則）
     * 「雙人入住政策」（租賃政策規則）
     * 「可以帶朋友回來過夜嗎」（租賃規範）
   - **✗ 不應歸類為 SOP 的範例**（這些應歸類為 system_config）：
     * 「如何產出12個月帳單」（系統操作，不是業務流程）
     * 「手機版有什麼功能」（產品功能說明）
     * 「忘記密碼怎麼辦」（系統帳戶操作）
     * 「未收到邀請信」（系統帳戶操作）
     * 「如何匯出發票」（系統操作）
     * 「離職員工資料備份」（系統管理操作）
   - **建議處理**：生成 SOP 到 vendor_sop_items 表
   - **should_generate_knowledge**: **true**（流程規則類知識需要生成 SOP）

2. **form_fill**（表單填寫流程）
   - **定義**：需要用戶提供資訊的**互動式流程**
   - **特徵**：引導用戶完成特定業務操作的流程
   - **範例**：「我想找房」、「我想退租」、「申請維修」
   - **建議處理**：生成表單引導流程到 vendor_sop_items 表
   - **should_generate_knowledge**: **true**（表單流程也是流程類知識）

**【Knowledge 類型】- 單獨情境的問題解答（情境導向）**

3. **system_config**（系統操作與配置）
   - **定義**：單獨情境的問題解答，主要是系統功能使用、帳戶設定、技術操作
   - **特徵**：情境性、問答導向、針對單一問題的解答（非流程性）
   - **與 SOP 的區別**：這類問題是單點解答，不涉及業務流程規則
   - **範例**：
     * 「可以用 Google 登入嗎」（帳戶設定問題）
     * 「如何切換團隊」（系統操作問題）
     * 「如何產出12個月帳單」（系統功能操作問題）
     * 「手機版有什麼功能」（產品功能說明）
     * 「如何匯出發票資料」（系統操作問題）
   - **建議處理**：生成單獨情境的問答知識到 knowledge_base 表
   - **should_generate_knowledge**: **true**（單獨情境也需要生成知識文檔）

**【動態查詢類型】- 不生成靜態知識**

4. **api_query**（API 動態查詢）
   - **定義**：需要查詢即時資料的問題
   - **特徵**：與具體房源/合約/業者相關，答案因物件而異
   - **範例**：「租金多少」、「房租包含哪些費用」、「我的合約何時到期」
   - **建議處理**：使用 API 查詢，不生成靜態知識
   - **should_generate_knowledge**: **false**（動態查詢，不需要生成知識）

---

**任務**：
1. 為每個問題分類
2. **適度識別並聚類相似問題**（重要！平衡完整性與精準度）
3. 給出處理建議

**聚類原則**（非常重要）：
- **適度聚類**：只有當問題高度相關且可用同一個 SOP 完整回答時才聚類
- **聚類大小限制**：每個聚類最多包含 3-5 個問題，超過則拆分為多個聚類
- **範例**：
  * ✅ 適當聚類：「可以雙人入住嗎」+「可以帶朋友過夜嗎」→ 聚類為「入住人數與訪客管理」（2題）
  * ✅ 適當聚類：「租金如何支付」+「匯款後如何確認」+「支付方式有哪些」→ 聚類為「租金支付流程」（3題）
  * ❌ 過度聚類：將「租約簽訂」+「租金支付」+「退租流程」+「續約」+「押金退還」聚類在一起（5+題，過於泛化）
- **目標**：生成精準、專注的 SOP，每個 SOP 應該能完整且準確地回答 2-5 個高度相關的問題

**輸出格式**（JSON）：
{{
  "classifications": [
    {{
      "question_index": 1,
      "question": "問題內容",
      "category": "sop_knowledge|api_query|form_fill|system_config",
      "reasoning": "分類理由",
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

        # 定義聚類規則（精準版 - 最小化聚類，避免名稱與內容錯配）
        self.cluster_rules = [
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
        if not self.client:
            return await self._stub_classify(gaps)

        # 如果問題太多，分批處理
        if len(gaps) <= batch_size:
            return await self._classify_batch(gaps)

        # 分批處理並合併結果
        all_classifications = []
        all_clusters = []

        for i in range(0, len(gaps), batch_size):
            batch = gaps[i:i+batch_size]
            result = await self._classify_batch(batch, offset=i)

            all_classifications.extend(result["classifications"])
            all_clusters.extend(result["clusters"])

        # 重新計算摘要
        summary = self._calculate_summary(all_classifications)

        return {
            "classifications": all_classifications,
            "clusters": all_clusters,
            "summary": summary
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

        新架構：先按類別分離，再分別聚類
        1. 從分類結果中分離 SOP 類型 和 Knowledge 類型
        2. 對每個類型分別進行聚類
        3. 保留正確的 gap_type 信息

        Args:
            gaps: 原始知識缺口列表
            classification_result: 分類結果

        Returns:
            List[Dict]: 聚類後的知識缺口列表（SOP + Knowledge）
        """
        classifications = classification_result.get("classifications", [])

        # 建立索引到分類的映射
        classification_map = {}
        for classification in classifications:
            idx = classification["question_index"] - 1  # question_index 從 1 開始
            classification_map[idx] = classification

        # **第一步：按類別分離問題**
        sop_questions = []  # sop_knowledge + form_fill
        knowledge_questions = []  # system_config

        for i, gap in enumerate(gaps):
            classification = classification_map.get(i)
            if not classification or not classification.get("should_generate_knowledge"):
                continue

            category = classification.get("category")
            question_with_meta = {
                "gap": gap,
                "index": i,
                "question_index": i + 1,  # 1-based
                "category": category,
                "classification": classification
            }

            if category in ["sop_knowledge", "form_fill"]:
                sop_questions.append(question_with_meta)
            elif category == "system_config":
                knowledge_questions.append(question_with_meta)

        print(f"📊 按類別分離：")
        print(f"   - SOP 類型（sop_knowledge + form_fill）: {len(sop_questions)} 題")
        print(f"   - Knowledge 類型（system_config）: {len(knowledge_questions)} 題")

        # **第二步：分別聚類**
        representative_gaps = []

        # 聚類 SOP 類型
        if sop_questions:
            sop_clusters = self._cluster_by_category(sop_questions, "SOP")
            print(f"   → SOP 聚類：{len(sop_questions)} 題 → {len(sop_clusters)} 個聚類")
            representative_gaps.extend(sop_clusters)

        # 聚類 Knowledge 類型
        if knowledge_questions:
            knowledge_clusters = self._cluster_by_category(knowledge_questions, "Knowledge")
            print(f"   → Knowledge 聚類：{len(knowledge_questions)} 題 → {len(knowledge_clusters)} 個聚類")
            representative_gaps.extend(knowledge_clusters)

        print(f"✅ 總聚類結果：{len(gaps)} 題 → {len(representative_gaps)} 個聚類")

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
