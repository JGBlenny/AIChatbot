# 完整對話架構

**最後更新**: 2026-08-25
**版本**: 2.2（＋§0 三層責任分層；§12 參數回寫至實況）

> **相關文件**：
> - Retriever Pipeline 分數欄位：[retriever-pipeline.md](./retriever-pipeline.md)
> - 知識資料結構：[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)
> - **端到端合併大圖**（§1–§14＋全景圖合成單一流程圖，技術版）：[conversation-flow-complete.mmd](./conversation-flow-complete.mmd)／[.svg](./conversation-flow-complete.svg)
> - **業務版流程圖**（給非技術受眾，白話無術語）：[conversation-flow-business.mmd](./conversation-flow-business.mmd)／[.svg](./conversation-flow-business.svg)／[.png](./conversation-flow-business.png)

---

## 0. 三層責任分層（**讀本文件其餘部分之前先讀這節**）

「routing」一詞在本系統裡曾被用來含混指涉三件**責任不同**的事。本節把它們拆開；
之後各節出現的「routing」，一律指第一層。

### 0.1 三層

```text
① Entry / Routing Hint（進場提名）
   決定    **哪個 Face 被提出／進場**
   證據    檢索 top-1 知識的 categories ＋ 相似度門檻（FORM_TRIGGER_THRESHOLD）
           或 trigger_facet_key 直達（呼叫端指定，不看 query）
   ⚠️ 提名成立**不代表** responsibility ownership 成立

② Face Responsibility / Conversational Action（責任判定）
   決定    **這個 Face 是否應承擔本輪 query**
   證據    persona responsibility／scope contract（「對話規則」列的【本輪範疇 scope】）
   輸出    stay ／ switch（switch → 關會話、重路由當前訊息）
   ⚠️ 與第①層**目前沒有直接的 contract bridge**（見 0.3）

③ Execution（執行）
   決定    **進場後實際怎麼做**
   內容    Form ／ API grounding ／ Direct Answer ／ secondary_call ／ formatter facts
   ⚠️ Face 具備某種 execution capability，**不能反推** entry 應該提名它；
      測試用的 `execution_face` 標籤更不是 routing ownership 證據
```

### 0.2 三條**禁止推論**（寫死）

```text
成功 entry                    ≠ responsibility 已成立
Face 有 execution capability   ≠ entry 應提名該 Face
responsibility owner 存在      ≠ current entry path 一定會提出它
```

### 0.3 已證實的 architecture fact（2026-08-25）

```text
Responsibility Contract
        ╳
        │  no direct consumption
        ╳
Entry Nomination

唯一的間接耦合：knowledge-row 的 `categories`（人工維護的標註）
```

實證：某 query 的 responsibility owner（`contract_closeout`）在其 in-session context 下
**穩定接受**（3/3 stay），但現行 entry nomination 從未提出它（9/9 只提出會拒絕的 Face）。
分類為 **`OWNER_EXISTS_BUT_NOT_PROPOSED`**。

⚠️ **這不是**「categories 標錯了」，**也不是**「某個 Face 應該有更高 priority」——
兩者都是 responsibility allocation 的 normative decision，屬
`routing-authority-model / Responsibility Governance Decision Record`，
**不得**在文件或程式裡當成 metadata／routing fix 順手做掉。
本節**刻意不畫**「應有的 bridge」，那會提前替 governance 設計答案。
（來源：`.kiro/specs/face-exit-before-grounding/`）

### 0.4 實際流程（含中間的責任判定，不可省略）

```text
Retrieval ／ Direct Entry
        │
        ▼
Entry Nomination            ← ①（categories ＋ 門檻／trigger_facet_key）
        │
        ▼
Face Session（開啟）
        │
        ▼
Responsibility / Scope Evaluation   ← ②（persona scope contract）
      ├─ stay ───▶ Execution / Grounding    ← ③
      └─ switch ─▶ Close / Reroute（grounding 從未取得）
```

⚠️ 舊圖把「Face entry → execution」畫成直線，會讓人以為進場即執行。
**進場與執行之間永遠隔著第②層**，且它可以在 grounding 前把會話關掉。

### 0.5 KB 一列同時攜帶三層資訊（**分開讀**）

| 層 | 欄位 | 語義 | 常見誤讀 |
|---|---|---|---|
| ① Routing Hint | `categories`／`category` | 這列知識**可以提名**哪些 Face | ⚠️ **`categories` 命中 ≠ 決定**——仍須 `similarity ≥ FORM_TRIGGER_THRESHOLD`，且面向可在進場後判 switch |
| ② Action Declaration | `form_id`／`action_type`／`trigger_mode` | 這列宣告了什麼動作 | ⚠️ **帶 `form_id` ≠ 直接開表單**——`trigger_mode` 另有分支（`manual`／`immediate` 需等確認，`auto` 才直開） |
| ③ Execution Configuration | 面向配置的 `grounding_scope` | 選定後怎麼取事實／怎麼寫入 | ⚠️ **`grounding_scope` 僅在 Face 被選定後生效**，**不是** routing 階段的候選條件 |

### 0.6 對話政策旗標放這裡，不要放進 routing

```text
result_mapping.skip_refine（預設關）
  作用   N > candidate_cap 時**跳過「請補更明確識別」那一輪**，直接列前 cap 筆候選
  不是   ✗ routing responsibility  ✗ 「跳過選定後的重查」
  實證   選定候選後仍會填回 required_slots[0] 並**重查 API**，收斂單筆
         （任務 7 定案；tests/unit/conversational/test_skip_refine_semantics_req.py）
  ⚠️ 誤讀成「跳過重查」→ 有人會拿候選列的欄位當 grounding，底稿即失去 API 權威來源
```

---

## 1. 總體對話流程

### 流程圖

```mermaid
flowchart TB
    Start([用戶訊息輸入]) --> API[POST /api/v1/message]

    API --> Step0{Step 0: 表單會話檢查}

    Step0 -->|有表單會話| FormState{表單狀態?}
    FormState -->|REVIEWING| FormReview[確認/取消/編輯]
    FormState -->|EDITING| FormEdit[收集編輯值]
    FormState -->|COLLECTING/DIGRESSION/PAUSED| FormCollect[收集欄位]

    Step0 -->|無表單會話| Step04{Step 0.4: trigger_facet_key?}
    Step04 -->|命中 registry 且 enabled| FacetGate{交易面向 gate}
    Step04 -->|未命中/照常| Step1[Step 1-3: 基礎處理]

    Step1 --> Validate[驗證業者]
    Validate --> Step05{Step 0.5: 損傷圖 is_damage?}
    Step05 -->|信心足| FacetGate
    Step05 -->|否/信心不足| Cache{緩存檢查}

    FacetGate -->|enabled_gate 開/缺值預設 true| TxFacet[交易面向<br/>prefill→brain→confirm gate→execute]
    FacetGate -->|repair_enabled=false| GateDegraded[降級文案+客服管道]
    TxFacet --> Response
    GateDegraded --> Response

    Cache -->|命中| CachedResponse[返回緩存結果]
    Cache -->|未命中| Intent[意圖分類]

    Intent --> Parallel{並行檢索}

    Parallel --> SOP[SOP 檢索]
    Parallel --> Knowledge[知識庫檢索]

    SOP --> Decision{智能決策}
    Knowledge --> Decision

    Decision -->|SOP 勝出| SOPFlow[SOP 流程]
    Decision -->|知識庫勝出| KnowledgeFlow[知識庫流程]
    Decision -->|都不達標| Fallback[兜底回應]

    SOPFlow --> SOPTrigger{觸發模式?}
    SOPTrigger -->|Manual| Manual[顯示內容 + 等待關鍵詞]
    SOPTrigger -->|Immediate| Immediate[顯示內容 + 詢問確認]
    SOPTrigger -->|None/null| NoneMode[純資訊展示]

    Manual --> WaitKeyword{等待觸發詞}
    Immediate --> WaitConfirm{等待確認}
    NoneMode --> Response

    WaitKeyword -->|匹配| NextAction
    WaitConfirm -->|確認| NextAction

    NextAction -->|form_fill| TriggerForm[觸發表單]
    NextAction -->|api_call| CallAPI[調用 API]
    NextAction -->|form_then_api| FormThenAPI[表單→API]

    KnowledgeFlow --> KnowledgeAction{action_type?}
    KnowledgeAction -->|direct_answer| LLMOptimize[LLM 優化答案]
    KnowledgeAction -->|form_fill| KnowledgeForm[知識庫表單觸發]
    KnowledgeAction -->|api_call| KnowledgeAPI[知識庫 API 調用]

    KnowledgeForm --> KnowledgeTrigger{觸發模式?}
    KnowledgeTrigger -->|Manual| KManual[顯示知識 + 等待關鍵詞]
    KnowledgeTrigger -->|Immediate| KImmediate[顯示知識 + 詢問確認]
    KnowledgeTrigger -->|Auto| KAuto[自動觸發表單]

    TriggerForm --> FormFlow[表單流程]
    FormThenAPI --> FormFlow
    KnowledgeForm --> FormFlow
    KAuto --> FormFlow

    FormFlow --> CollectFields[收集欄位資料]
    CollectFields --> Review[審核確認]
    Review --> Submit[提交表單]
    Submit --> OnComplete{完成後動作}

    OnComplete -->|show_knowledge| ShowKnowledge[顯示知識答案]
    OnComplete -->|call_api| ExecuteAPI[執行 API]
    OnComplete -->|both| BothActions[兩者都執行]

    LLMOptimize --> InjectParams[注入業者參數]
    InjectParams --> CacheResult[緩存結果]

    CallAPI --> APIResponse[API 回應]
    ExecuteAPI --> APIResponse
    KnowledgeAPI --> APIResponse

    CacheResult --> Response([返回回應給用戶])
    CachedResponse --> Response
    Fallback --> Response
    ShowKnowledge --> Response
    APIResponse --> Response
    BothActions --> Response

    FormReview --> Response
    FormEdit --> Response
    FormCollect --> Response

    style Start fill:#e1f5e1
    style Response fill:#e1f5e1
    style Decision fill:#fff3cd
    style SOP fill:#d1ecf1
    style Knowledge fill:#d1ecf1
    style FormFlow fill:#f8d7da
```

### 進場順位補述（conversational-repair）

<!-- tested-by: conversational-repair:1.1 -->

- **Step 0.4：`trigger_facet_key` 直達**（會話續跑之後、快取之前）——選填參數命中 conversational config registry（by_key）且 enabled → 跳過意圖辨識直接 seed 面向；未命中→照常走既有管線（防呆不報錯）。
- **Step 0.5：損傷圖改道**——`is_damage` 且信心足 → **不打 SOP 檢索**、直接 seed 修繕交易面向並攜帶辨識結果；找不到面向配置→降級回原行為；非損傷/信心不足維持現行降級。
- **共用 gate（`enabled_gate`）**：宣告 `enabled_gate` 的面向（修繕＝`repair_enabled`）→ 讀 `vendor_configs`（缺值預設 true）；`false`→回 `gate_disabled` 文案＋客服管道。
- 第三路（分類路由）仍走既有檢索：意圖錨點知識掛「修繕報修」分類、similarity≥0.75 → `by_category` 1:1 進面向。
- 交易面向流程細節見 [§14 交易面向流程](#14-交易面向流程conversational-repair)。

### 請求/回應模型

**請求核心欄位**：
- `vendor_id`: 業者 ID（業者隔離）
- `message`: 用戶訊息
- `session_id`: 會話 ID（表單狀態追蹤）
- `target_user`: 目標角色（tenant/landlord/property_manager）
- `mode`: 業務模式（b2c/b2b）
- `debug`: Debug 模式（跳過緩存）

**回應核心欄位**：
- `answer`: 答案內容
- `intent_name` + `intent_type`: 意圖資訊
- `confidence`: 信心度（0-1）
- `action_type`: 動作類型（direct_answer/form_fill/api_call/sop_knowledge）
- `form_triggered` + `form_completed`: 表單狀態

### 緩存機制

**三層緩存架構**：

| 層級 | 緩存鍵格式 | 用途 |
|------|-----------|------|
| L1 問答緩存 | `rag:question:{vendor_id}:{target_user}:{config_version}:{question_hash}` | 完整回答結果 |
| L2 向量緩存 | `rag:vector:{text_hash}` | embedding 向量 |
| L3 RAG 結果緩存 | `rag:result:{vendor_id}:{intent_id}:{question_hash}` | 檢索結果 |

**失效追蹤鍵**（event-driven 失效）：
- `rag:relation:knowledge:{knowledge_id}`
- `rag:relation:intent:{intent_id}`
- `rag:relation:vendor:{vendor_id}`

**跳過緩存條件**：
- Debug 模式開啟
- 有進行中的表單會話
- 用戶訊息包含表單觸發關鍵字

---

## 2. 意圖識別系統

### 意圖分類邏輯

**LLM Function Calling 架構**：
```python
classify_intent(question, available_intents) → {
    primary_intent: {name, confidence},      # 主要意圖
    secondary_intents: [{name, confidence}]  # 次要意圖（最多2個）
}
```

### 多意圖支援

| 意圖級別 | 數量限制 | 用途 |
|---------|---------|------|
| 主要意圖 | 1 個 | 回應標註／knowledge_intent_mapping 關聯 |
| 次要意圖 | 最多 2 個 | 同上 |

> ⚠️ 2026-07-16 對碼修正：原記載「主 1.3x／次 1.1x 檢索加成」**無實裝**。實碼的分數加成是**關鍵字加成**（base_retriever.py:357-403：每命中一詞 +0.1、上限 +0.3，倍率 1.0–1.3）；意圖經 knowledge_intent_mapping JOIN 帶出（vendor_knowledge_retriever_v2.py:219-221），無意圖倍率。

**意圖配置來源**：
1. **資料庫** (intents 表)：動態配置，支援業者自定義
2. **YAML 配置** (fallback)：系統預設意圖

### 信心度評估

**獨立閾值檢查**：每個意圖有自己的 `confidence_threshold`

```python
for intent in [primary, *secondary]:
    if intent.confidence < intent.threshold:
        filtered_out()  # 不參與檢索加成
```

**信心度標準**：
- **0.9-1.0**：非常確定
- **0.7-0.9**：較為確定（預設閾值）
- **0.5-0.7**：不太確定
- **< 0.5**：不確定

### 降級機制

**主意圖失敗處理**：
```python
if primary_failed AND has_valid_secondary:
    promote_best_secondary_to_primary()
    demote_original_primary_to_secondary()
```

**無有效意圖**：
```python
if all_intents_failed:
    return unclear_intent  # intent_name = "unclear"
```

---

## 3. 檢索引擎

### 並行檢索架構

```mermaid
flowchart LR
    subgraph Input[用戶輸入]
        Message[用戶訊息]
        Intent[意圖分類結果]
    end

    subgraph Parallel[並行檢索]
        SOPT[SOP Task<br/>sop_orchestrator.process_message]
        KnowledgeT[Knowledge Task<br/>_retrieve_knowledge]
    end

    Message --> SOPT
    Intent --> SOPT
    Message --> KnowledgeT
    Intent --> KnowledgeT

    subgraph Scoring[分數比較]
        SOPScore[SOP 分數<br/>閾值: 0.55]
        KnowledgeScore[知識庫分數<br/>閾值: 0.6]
        Gap[差距閾值: 0.15]
    end

    SOPT --> SOPScore
    KnowledgeT --> KnowledgeScore

    subgraph DecisionLogic[決策邏輯]
        C0C[Case 0C: SOP 等待關鍵詞<br/>→ 略過 SOP]
        C1[Case 1: SOP > 知識+0.15<br/>→ 使用 SOP]
        C2[Case 2: 知識 > SOP+0.15<br/>→ 使用知識庫]
        C3[Case 3: 分數接近<br/>→ 看後續動作]
        C4[Case 4: 只有 SOP 達標<br/>→ 使用 SOP]
        C5[Case 5: 只有知識達標<br/>→ 使用知識庫]
        C6[Case 6: 都不達標<br/>→ 兜底回應]
    end

    SOPScore --> DecisionLogic
    KnowledgeScore --> DecisionLogic
    Gap --> DecisionLogic

    style Parallel fill:#e3f2fd
    style Scoring fill:#fff3cd
    style DecisionLogic fill:#d4edda
```

### SOP vs 知識庫決策邏輯

**閾值定義**：
- `SOP_MIN_THRESHOLD = 0.55`
- `KB_SIMILARITY_THRESHOLD`：部署值 **0.65**（程式 fallback `0.55`，見 `decision_layer.DecisionConfig`）
  ⚠️ 它與決策樹用的 `knowledge_min = 0.6` 是**兩顆不同的常數，⛔ 不可互相取代**：
  前者是檢索過濾門檻，後者是六 case 答題仲裁的最低分（**硬編碼、刻意不開 env**）。
  （舊版寫「`KNOWLEDGE_MIN_THRESHOLD = 0.6` 鍵名與值皆已過時」——**兩件事都錯**，2026-09-01 修正）
- `SCORE_GAP_THRESHOLD = 0.15`（顯著差異）

**決策樹**：

```python
# Case 0A: SOP 被用戶取消
if sop_cancelled:
    return sop_result  # 優先處理取消回應

# Case 0B: SOP 已觸發並執行動作
if sop_triggered_with_action:
    return sop_result  # 優先完成 SOP 流程

# Case 0C: SOP 等待關鍵詞（response 為 None）
if sop_has_result AND NOT sop_has_response:
    if kb_score >= 0.6:
        return knowledge_result  # 讓知識庫先回答
    else:
        return none_result  # 都無法回答

# Case 1: SOP 顯著更高
if sop_score >= 0.55 AND sop_score > kb_score + 0.15:
    return sop_result

# Case 2: 知識庫顯著更高
if kb_score >= 0.6 AND kb_score > sop_score + 0.15:
    return knowledge_result

# Case 3: 分數接近（兩者都達標）
if sop_score >= 0.55 AND kb_score >= 0.6:
    if sop_has_next_action:
        return sop_result  # 優先處理後續動作（表單/API）
    else:
        return higher_score_result

# Case 4: 只有 SOP 達標
if sop_score >= 0.55:
    return sop_result

# Case 5: 只有知識庫達標
if kb_score >= 0.6:
    return knowledge_result

# Case 6: 都不達標
return unclear_response
```

### 過濾機制

> ✅ **本節公式已於 2026-09-01 逐行對碼修正**，來源＝`services/vendor_knowledge_retriever_v2.py`
> 的 `_vector_search`／`_keyword_search`。查證用的尺是
> [`b2b-ground-truth.md`](../../.kiro/specs/conversational-routing-execution/b2b-ground-truth.md)；
> 全文件可信度分流見
> [`b2b-doc-status-ledger.md`](../../.kiro/specs/conversational-routing-execution/b2b-doc-status-ledger.md)。
> ⚠️ 修改本節前請重新對碼——**行號會漂,以符號名 grep**。


- **業者隔離**：`array_length(vendor_ids, 1) IS NULL OR vendor_ids && ARRAY[$vendor_id]`
  ——運算子是 `&&`（交集），**不是** `@>`；⚠️ `vendor_ids` 為空＝全業者共用，**必須放行**
- **角色隔離**：`target_user IS NULL OR target_user && ARRAY[$target_user]`
  ——b2c 另放行 `'all_users'`；⚠️ 未知／空的 `target_user` 會被 `_effective_target_user`
  **靜默正規化為 `tenant`**（測試打錯角色名不會報錯，只會安靜地測到別的池）
- **業態過濾**：⚠️ **b2b 與 b2c 是兩條不同的分支，⛔ 不是同一條公式**
  - b2b（`target_user ∈ {property_manager, system_admin}` **或** `mode='b2b'`）：
    `business_types && ARRAY['system_provider']` —— **無 `IS NULL` 放行**
    🔴 補上 `IS NULL` 會打穿刻意設計的跨業者隔離
  - b2c：`business_types IS NULL OR business_types && ARRAY[$vendor_business_types]`
- **啟用狀態**：`is_active = true`

### 優先級與加成（知識庫專屬）

> ⚠️ 2026-07-16 對碼修正：原記載「priority>0 且 similarity≥0.70 → +0.15」**無實裝**。實碼行為：`priority` 用於檢索排序（vendor_knowledge_retriever_v2.py:121 `ORDER BY kb.priority DESC`）；分數加成為關鍵字加成 1.0–1.3x（見 §2 修正註）。

> Retriever Pipeline 各階段分數欄位的詳細說明，請參考 [retriever-pipeline.md](./retriever-pipeline.md)。

---

## 4. 信心度評估

### 評估指標

**加權分數**：
```python
confidence_score = (
    max_similarity * 0.7 +             # 相似度（權重 70%）
    min(result_count / 5, 1.0) * 0.2 + # 結果數量（權重 20%）
    keyword_match_rate * 0.1            # 關鍵字匹配（權重 10%）
)
```

### 信心度等級與處理決策

| 等級 | 分數範圍 | 額外條件 | 處理決策 |
|------|---------|---------|---------|
| **high** | >= 0.85 | 結果數 >= 2 | `direct_answer` — 可能啟用快速路徑 |
| **medium** | 0.70-0.85 | - | `needs_enhancement` — LLM 優化 |
| **low** | < 0.70 | - | `unclear` — 轉人工或提示重新描述 |

---

## 5. 答案優化

### 條件式優化決策樹

```python
# 1. 完美匹配（跳過 LLM）— 使用純向量分數 vector_similarity
if max_vector_similarity >= 0.90:
    return original_answer

# 2. 答案合成（多高品質結果）
high_quality = [r for r in results if r.similarity > 0.80]
if len(high_quality) >= 2 AND is_complex_question:
    synthesize_answers(high_quality)

# 3. 快速路徑（單一高品質）
elif confidence >= 0.75 AND single_result:
    format_with_template()

# 4. 模板格式化（中等信心）
elif 0.55 <= confidence < 0.75:
    apply_template()

# 5. 完整 LLM 優化（低信心）
else:
    full_llm_optimization()
```

### 答案合成觸發條件

**必須同時滿足**：
1. `ENABLE_SYNTHESIS = true`（環境變數）
2. 結果數 >= 2
3. 包含複雜問題模式：
   - 流程問題（「如何」「怎麼」「流程」「步驟」「程序」「過程」）
   - 廣泛查詢（「條款」「規定」「說明」「內容」「包括」「有哪些」「什麼」「包含」）+ 主題多樣性 >= 3
4. 無單一完美匹配（max_vector_similarity < 0.90）

**合成策略**：
```python
LLM Prompt: """
整合以下多個答案片段，生成一個完整、連貫的回答：
1. [答案1]
2. [答案2]
3. [答案3]

要求：
- 保留所有關鍵資訊
- 去除重複內容
- 邏輯連貫
- 結構清晰（使用列表或步驟）
"""
```

### 業者參數注入

**階段 1：確定性替換**（正則表達式）
```python
# 模板變數替換
{company_name} → 實際公司名稱
{service_phone} → 實際服務電話
{business_hours} → 實際營業時間

# 智能替換（語境感知）
"我們的客服" → "{company_name}的客服"
"撥打服務專線" → "撥打 {service_phone}"
```

**階段 2：語氣調整**（已停用）
- 原因：避免 LLM 誤刪替換後的參數

### 優化參數配置

| 參數 | 預設值 | 用途 |
|------|--------|------|
| `PERFECT_MATCH_THRESHOLD` | 0.90 | 完美匹配閾值 |
| `SYNTHESIS_THRESHOLD` | 0.80 | 答案合成閾值 |
| `FAST_PATH_THRESHOLD` | 0.75 | 快速路徑閾值 |
| `LLM_ANSWER_TEMPERATURE` | 0.7 | 答案生成溫度 |
| `LLM_SYNTHESIS_TEMP` | **0.1**（部署值） | 合成專用溫度。⚠️ 程式 fallback 是 `0.5`，env 未設的環境會跑 0.5 |
| `LLM_ANSWER_SYNTH_TEMP` | 0.2 | 事實型收斂（`cta_mode=factual/suppress`）專用低溫 |
| `LLM_ANSWER_MAX_TOKENS` | 800 | 最大 token 數 |

---

## 6. SOP 編排

> **現況註記（2026-07-11，conversational-repair）**：SOP 機制本體保留不動。**修繕子集已停用**——vendor 2/4 各 75 條 `next_form_id='jgb_repair_create'` SOP `is_active=false`（M2，可逆、rollback 備、prod 使用者手動），b2c 修繕改走[§14 交易面向](#14-交易面向流程conversational-repair)。vendor 2 其餘 250 條非修繕 SOP 行為不變。

### 觸發模式

```mermaid
stateDiagram-v2
    [*] --> 用戶提問

    用戶提問 --> SOP檢索成功

    SOP檢索成功 --> 檢查觸發模式

    state 檢查觸發模式 {
        [*] --> Manual: trigger_mode='manual'
        [*] --> Immediate: trigger_mode='immediate'
        [*] --> NullMode: trigger_mode=null

        Manual --> 顯示SOP內容_Manual
        顯示SOP內容_Manual --> 等待關鍵詞
        等待關鍵詞 --> 檢測關鍵詞
        檢測關鍵詞 --> 匹配成功: ["還是不行", "試過了", "需要維修"]
        檢測關鍵詞 --> 無匹配: 其他詞彙
        無匹配 --> 結束對話

        Immediate --> 顯示SOP內容_Immediate
        顯示SOP內容_Immediate --> 顯示確認提示
        顯示確認提示 --> 等待用戶確認
        等待用戶確認 --> 確認: ["是", "要", "好"]
        等待用戶確認 --> 取消: ["否", "不用"]
        取消 --> 結束對話

        NullMode --> 顯示SOP內容_Null
        顯示SOP內容_Null --> 結束對話: next_action='none'
    }

    匹配成功 --> 執行後續動作
    確認 --> 執行後續動作

    state 執行後續動作 {
        [*] --> form_fill: next_action='form_fill'
        [*] --> api_call: next_action='api_call'
        [*] --> form_then_api: next_action='form_then_api'

        form_fill --> 啟動表單流程
        api_call --> 調用外部API
        form_then_api --> 表單後調用API
    }

    啟動表單流程 --> [*]
    調用外部API --> [*]
    表單後調用API --> [*]
    結束對話 --> [*]
```

| 模式 | 行為 | 等待條件 | 使用場景 |
|------|------|---------|---------|
| `none`/null | 純資訊展示 | 無 | 政策說明、規範解釋 |
| `manual` | 等待特定關鍵詞 | `trigger_keywords` | 需用戶主動確認的流程 |
| `immediate` | 立即詢問確認 | 確認詞列表 | 需即時確認的操作 |
| `auto` | 立即執行後續動作 | 無（不等待） | 自動觸發表單/API |

### 觸發關鍵字匹配邏輯

**immediate 模式特殊處理**：
```python
# 1. 純粹否定詞（優先級最高）
if message in ['不用', '不要', '不需要', '算了', '不必', '免了', '不了', '不']:
    cancel_action()

# 2. 問句檢測（不視為確認）
elif any(ind in message for ind in ['？', '?', '嗎', '呢', '什麼', '如何', '怎麼', '怎樣', '為何', '為什麼', '哪裡', '誰', '何時']):
    not_confirmed()

# 3. 訊息過長（可能是新問題）
elif len(message) > 10:
    not_confirmed()

# 4. 確認詞匹配（immediate 預設：確認/好/是的/可以/ok/yes/要/需要/開始）
elif message in trigger_keywords:
    trigger_action()
```

**manual 模式**：
```python
if any(keyword in message for keyword in trigger_keywords):
    trigger_action()
```

### 多輪對話管理

**Context 結構**：
```python
{
    'sop_id': int,
    'sop_name': str,
    'trigger_mode': str,
    'trigger_keywords': List[str],
    'next_action': str,              # none/form_fill/api_call/form_then_api
    'next_form_id': int,
    'next_api_config': dict,
    'state': 'WAITING' | 'TRIGGERED',
    'original_question': str         # 相似問題檢測用
}
```

**相似問題處理**：
```python
if has_pending_context:
    similarity = compare(new_question, original_question)

    if similarity >= 0.7:
        # 視為新問題，重新檢索
        clear_context()
        start_new_retrieval()
    else:
        # 視為回應，檢查關鍵字
        check_keywords()
```

### 後續動作執行

```python
if next_action == 'form_fill':
    trigger_form(next_form_id)

elif next_action == 'api_call':
    execute_api(next_api_config)

elif next_action == 'form_then_api':
    trigger_form(next_form_id, pause_mode=True)
    # 表單完成後自動執行 API
```

---

## 7. 表單管理

> **現況註記（2026-07-11，conversational-repair）**：表單機本體保留不動。`jgb_repair_create` 表單 schema 已升為通用（vendor_id 2→NULL，dev＋prod dump 雙查證已是 NULL），但**修繕不再走逐欄位表單流程**——改由[§14 交易面向](#14-交易面向流程conversational-repair)的推斷＋確認 gate 收斂；表單 schema 僅供交易面向的**欄位契約引用**（`execute_params` 映射對齊）。其餘表單流程不受影響。

### 狀態機

```mermaid
stateDiagram-v2
    [*] --> START: trigger_form()

    START --> COLLECTING: 開始收集

    COLLECTING --> COLLECTING: 收集欄位
    COLLECTING --> DIGRESSION: 用戶離題
    COLLECTING --> REVIEWING: 所有欄位完成

    DIGRESSION --> COLLECTING: 選擇恢復
    DIGRESSION --> PAUSED: 選擇暫停

    PAUSED --> COLLECTING: resume_form()
    PAUSED --> CANCELLED: 超時/取消（預設 30 分鐘）

    REVIEWING --> EDITING: 用戶要求修改
    REVIEWING --> COMPLETED: 確認提交
    REVIEWING --> PAUSED: API 執行前暫停
    REVIEWING --> CANCELLED: 取消

    EDITING --> REVIEWING: 修改完成

    COMPLETED --> [*]: 表單完成
    CANCELLED --> [*]: 表單取消

    note right of COLLECTING
        狀態: 正在收集欄位
        動作: collect_field_data()
    end note

    note right of DIGRESSION
        狀態: 用戶離題
        動作: 處理其他問題
    end note

    note right of REVIEWING
        狀態: 審核確認
        動作: 顯示所有資料
    end note

    note right of EDITING
        狀態: 編輯模式
        動作: 修改特定欄位
    end note
```

> ⚠️ 2026-07-16 對碼修正：`CONFIRMING` 於 FormState 有定義（form_manager.py:41）但全庫**無任何轉換使用**（死狀態）；SOP immediate 的待確認由 SOP context（Redis）管理，不進表單狀態機。上圖已移除 CONFIRMING 轉換，實際使用中狀態為 7 個。

### 離題偵測

**偵測邏輯**：
```python
detect_digression(message, current_field, form_schema, intent) → {
    is_digression: bool,
    digression_type: str,  # explicit_exit/question/irrelevant_response
    confidence: float
}
```

**離題類型與處理**：

| 離題類型 | 範例 | 處理策略 |
|---------|------|---------|
| `explicit_exit` | 「取消」「算了」「不填了」 | 取消表單 |
| `question` | 包含 "?" 或問題關鍵字 | 回答問題後回到當前欄位 |
| `irrelevant_response` | 與當前欄位無關 | 澄清後重試 |

### 欄位驗證

**驗證類型**：
- `text`: 文字長度、格式
- `phone`: 台灣手機格式（09xxxxxxxx）
- `email`: Email 格式
- `date`: 日期格式（YYYY-MM-DD）
- `number`: 數字範圍
- `select`: 選項匹配

**驗證失敗處理**：
```python
if not is_valid:
    return {
        "answer": f"{error_message}\n\n{field_prompt}",
        "validation_failed": True
    }
```

### 審核與編輯

**審核模式觸發**：
```python
if all_fields_collected:
    if form_schema.skip_review:
        complete_form()  # 直接完成
    else:
        show_review_summary()  # 進入審核模式
```

**審核摘要格式**：
```
請確認以下資訊是否正確：

1. 姓名：王小明
2. 電話：0912345678
3. 地址：台北市信義區...

輸入「確認」提交，或輸入欄位編號修改（例如：「修改2」）
```

**編輯模式**：
```python
if message.startswith('修改'):
    field_number = extract_number(message)
    enter_editing_mode(field_number)
```

### 完成後動作

```python
if on_complete_action == 'call_api':
    result = execute_api(form_data)
    show_result(result)

elif on_complete_action == 'show_knowledge':
    show_knowledge_answer(related_kb_id)

elif on_complete_action == 'both':
    result = execute_api(form_data)
    knowledge = get_knowledge(related_kb_id)
    show_combined_response(result, knowledge)
```

### API 重試機制

```python
MAX_RETRIES = 2

if api_error in ['ambiguous_match', 'no_match', 'invalid_input']:
    retry_count += 1

    if retry_count >= MAX_RETRIES:
        cancel_form()  # 自動取消，避免無限重試
        notify_manual_intervention()
    else:
        show_retry_hint(api_error)
```

---

## 8. API 調用流程

```mermaid
sequenceDiagram
    participant User as 用戶
    participant Chat as Chat API
    participant SOP as SOP/知識庫
    participant Form as 表單管理器
    participant External as 外部 API

    User->>Chat: 發送訊息
    Chat->>SOP: 檢索匹配內容

    alt SOP 有 API 調用
        SOP-->>Chat: next_action='api_call'
        Chat->>External: 直接調用 API
        External-->>Chat: API 響應
    else SOP 有表單+API
        SOP-->>Chat: next_action='form_then_api'
        Chat->>Form: 啟動表單

        loop 收集欄位
            User->>Form: 提供資料
            Form-->>User: 下一個問題
        end

        Form->>User: 審核確認
        User->>Form: 確認提交

        Form->>External: 調用 API (帶表單資料)
        External-->>Form: API 響應
        Form-->>Chat: 完成回應
    else 知識庫有 API 調用
        SOP-->>Chat: action_type='api_call'
        Chat->>External: 調用配置的 API
        External-->>Chat: API 響應
    end

    Chat-->>User: 返回結果
```

---

## 9. 知識庫表單觸發流程

```mermaid
flowchart TB
    subgraph KnowledgeRetrieval[知識庫檢索]
        Query[用戶查詢]
        Search[向量搜尋 + 意圖過濾]
        Match{找到匹配?}
    end

    Query --> Search
    Search --> Match

    Match -->|是| CheckAction{檢查 action_type}
    Match -->|否| NoMatch[無結果]

    CheckAction -->|direct_answer| DirectAnswer[直接回答]
    CheckAction -->|form_fill| FormTrigger{檢查 trigger_mode}
    CheckAction -->|api_call| DirectAPI[直接調用 API]
    CheckAction -->|form_then_api| FormThenAPIFlow[表單→API]

    FormTrigger -->|NULL/auto| AutoForm[自動觸發表單]
    FormTrigger -->|manual| ManualFlow[Manual 流程]
    FormTrigger -->|immediate| ImmediateFlow[Immediate 流程]

    subgraph ManualProcess[Manual 處理]
        ManualFlow --> ShowKnowledge1[顯示知識內容]
        ShowKnowledge1 --> AddPrompt1[添加觸發提示]
        AddPrompt1 --> SaveContext1[保存 Context]
        SaveContext1 --> WaitKeyword1[等待關鍵詞]
        WaitKeyword1 -->|"是"/"要"| TriggerForm1[觸發表單]
        WaitKeyword1 -->|其他| Continue1[繼續對話]
    end

    subgraph ImmediateProcess[Immediate 處理]
        ImmediateFlow --> ShowKnowledge2[顯示知識內容]
        ShowKnowledge2 --> AskConfirm[詢問是否需要表單]
        AskConfirm --> SaveContext2[保存 Context]
        SaveContext2 --> WaitConfirm2[等待確認]
        WaitConfirm2 -->|"是"/"要"| TriggerForm2[觸發表單]
        WaitConfirm2 -->|"否"/"不用"| Continue2[結束]
    end

    AutoForm --> FormSession[創建表單會話]
    TriggerForm1 --> FormSession
    TriggerForm2 --> FormSession
    FormThenAPIFlow --> FormSession

    FormSession --> CollectData[收集表單資料]
    CollectData --> FormComplete{表單完成}

    FormComplete --> OnCompleteAction{on_complete_action?}
    OnCompleteAction -->|show_knowledge| ShowResult[顯示知識答案]
    OnCompleteAction -->|call_api| CallConfigAPI[調用配置的 API]
    OnCompleteAction -->|both| BothAction[兩者都執行]

    style ManualProcess fill:#e8f5e9
    style ImmediateProcess fill:#e3f2fd
    style FormSession fill:#fff3e0
```

---

## 10. Context 管理機制

```mermaid
flowchart LR
    subgraph ContextStorage[Context 存儲]
        Redis[(Redis Cache)]
        Memory[(內存備援)]
    end

    subgraph SOPContext[SOP Context 結構]
        SOPData["{<br/>
        sop_id: 123,<br/>
        trigger_mode: 'manual',<br/>
        state: 'MANUAL_WAITING',<br/>
        trigger_keywords: ['還是不行'],<br/>
        next_action: 'form_fill',<br/>
        created_at: '2026-02-04'<br/>
        }"]
    end

    subgraph KnowledgeContext[知識庫 Context 結構]
        KnowledgeData["{<br/>
        knowledge_id: 456,<br/>
        trigger_mode: 'immediate',<br/>
        state: 'IMMEDIATE_WAITING',<br/>
        trigger_keywords: ['是', '要'],<br/>
        form_id: 'inquiry_form',<br/>
        on_complete_action: 'call_api'<br/>
        }"]
    end

    subgraph Operations[操作]
        Save[保存 Context]
        Get[獲取 Context]
        Update[更新狀態]
        Delete[清除 Context]
    end

    Save --> Redis
    Redis -.->|Redis 不可用| Memory

    Get --> Redis
    Redis -.->|未找到| Memory

    Update --> Redis
    Update -.-> Memory

    Delete --> Redis
    Delete --> Memory

    SOPData --> Save
    KnowledgeData --> Save

    style Redis fill:#fce4ec
    style Memory fill:#e0f2f1
```

---

## 11. 系統角色與職責

| 組件 | 職責 | 關鍵決策點 |
|------|------|-----------|
| **Chat Router** (`routers/chat.py`) | 主入口，協調整體流程 | 表單優先、SOP 優先、分數比較 |
| **SOP Orchestrator** (`services/sop_orchestrator.py`) | SOP 檢索與觸發管理 | 觸發模式判斷、關鍵詞匹配 |
| **Knowledge Retriever** (`services/vendor_knowledge_retriever_v2.py`) | 知識庫檢索與過濾 | 向量相似度、意圖匹配 |
| **Form Manager** (`services/form_manager.py`) | 表單生命週期管理 | 狀態轉換、欄位驗證 |
| **Intent Classifier** (`services/intent_classifier.py`) | 意圖識別 | 多意圖支援、信心度評估 |
| **LLM Optimizer** (`services/llm_answer_optimizer.py`) | 答案優化與合成 | 合成策略、參數注入 |
| **Cache Service** (`services/cache_service.py`) | 三層緩存管理 | 緩存命中、過期策略 |
| **Confidence Evaluator** (`services/confidence_evaluator.py`) | 品質評估 | 信心度計算、等級判定 |
| **Base Retriever** (`services/base_retriever.py`) | 統一檢索策略 | Pipeline stages、分數組合 |

---

## 12. 關鍵參數配置

> ⚠️ **母圖只引用、不複製**：參數的唯一真實來源是
> [docs/retrieval-parameters.md](../retrieval-parameters.md) 與兩份 compose 的宣告。
> 本節僅為速查；**發現不一致時以該檔與 compose 為準，並回寫本節**。

```yaml
# 分數閾值
SOP_MIN_THRESHOLD: 0.55          # SOP 最低分數
KB_SIMILARITY_THRESHOLD: 0.65    # 檢索過濾門檻（程式 fallback 0.55）。⛔ 不取代 knowledge_min=0.6，那是另一顆
SCORE_GAP_THRESHOLD: 0.15        # 顯著差距閾值
FORM_TRIGGER_THRESHOLD: 0.75     # 表單觸發／**面向進場提名**共用門檻（§0.5 ①）

# 優化閾值（環境變數，可配置）
PERFECT_MATCH_THRESHOLD: 0.90    # 完美匹配閾值（比對 vector_similarity）
SYNTHESIS_THRESHOLD: 0.80        # 答案合成閾值（比對 similarity）
HIGH_QUALITY_THRESHOLD: 0.80     # 高質量閾值
FAST_PATH_THRESHOLD: 0.75        # 快速路徑閾值

# 信心度閾值（環境變數）
CONFIDENCE_HIGH_THRESHOLD: 0.85  # 高信心度
CONFIDENCE_MEDIUM_THRESHOLD: 0.70 # 中信心度

# LLM 模型配置（環境變數）
OPENAI_MODEL: gpt-4o-mini              # 答案優化模型（預設）
INTENT_CLASSIFIER_MODEL: gpt-3.5-turbo # 意圖分類模型
KNOWLEDGE_GEN_MODEL: gpt-4o-mini       # 知識生成模型
DOCUMENT_CONVERTER_MODEL: gpt-4o       # 文件轉換模型（fallback: KNOWLEDGE_GEN_MODEL）
QUERY_REWRITE_MODEL: gpt-4o-mini       # 查詢改寫模型（舊文寫 gpt-3.5-turbo，已過時）
PRESALES_SYNTH_MODEL: gpt-4o           # 對話 brain（conversational_step）與推薦型合成
RELEVANCE_GATE_MODEL: —                # 未設 → LLM_MODEL → OPENAI_MODEL（gpt-4o-mini）
EMBEDDING_MODEL: text-embedding-3-small # Embedding 模型

# LLM 溫度與 token 配置（環境變數）
LLM_ANSWER_TEMPERATURE: 0.7            # 答案生成溫度
LLM_ANSWER_MAX_TOKENS: 800             # 答案最大 token 數
LLM_SYNTHESIS_TEMP: 0.1                # 合成專用溫度（部署值；程式 fallback 0.5）
LLM_ANSWER_SYNTH_TEMP: 0.2             # 事實型收斂（factual/suppress）低溫
ADVISOR_TEMP: 0.4                      # 對話 brain（conversational_step）溫度
LLM_TONE_ADJUSTMENT_TEMP: 0.3          # 語氣調整溫度（已停用）
INTENT_CLASSIFIER_TEMPERATURE: 0.1     # 意圖分類溫度
INTENT_CLASSIFIER_MAX_TOKENS: 500      # 意圖分類最大 token 數
KNOWLEDGE_GEN_TEMPERATURE: 0.7         # 知識生成溫度
KNOWLEDGE_GEN_MAX_TOKENS: 800          # 知識生成最大 token 數
QUERY_REWRITE_TEMPERATURE: 0.3         # 查詢改寫溫度
QUERY_REWRITE_MAX_TOKENS: 100          # 查詢改寫最大 token 數

# 進場／閘門旗標（**皆為現行值**）
ENABLE_QUERY_REWRITE_B2B: false        # b2b 查詢改寫（現行停用）
PREENTRY_ROUTABILITY_GATE: false       # 進場前 scope 預判閘（現行停用；⚠️ 它與 in-session
                                       #   取到的 system context **不同源**，不等於「同一判定提前」）
RELEVANCE_GATE_ENABLED: true           # 單發答題的適用性把關
RELEVANCE_GATE_SKIP_VEC: —             # 未設＝不跳過

# 觸發配置
DEFAULT_TRIGGER_KEYWORDS:
  - "是"
  - "要"
  - "好"
  - "確認"

CANCEL_KEYWORDS:
  - "否"
  - "不用"
  - "取消"
  - "算了"

# Context 配置
CONTEXT_TTL: 3600                 # Context 存活時間（秒）
CONTEXT_STORAGE: "redis"          # 存儲方式（redis/memory）

# 表單配置
FORM_SESSION_TIMEOUT: 1800        # 表單會話超時（秒）
MAX_FORM_FIELDS: 20               # 最大欄位數
DIGRESSION_THRESHOLD: 0.7         # 離題判定閾值
```

### 交易面向配置鍵（`grounding_scope` 內，conversational-repair）

宣告 `execute_endpoint` 即判定為交易面向；以下鍵全配置驅動、引擎零硬編：

| 鍵 | 預設 | 用途 |
|---|---|---|
| `execute_endpoint` | — | 收斂寫入端點（交易面向判定依據，修繕＝create_repair） |
| `execute_params` | — | slots→params 映射（`params_from_form` 語彙，支援 `{session.role_id}`） |
| `required_slots` | — | 必填槽位清單（引擎保底驗齊才出確認/執行） |
| `confirm_template` | — | 確認摘要範本（嵌槽位、缺槽容錯渲染） |
| `receipt_template` | — | 成功回執範本 |
| `execute_result_path` | — | 回執取單號路徑（修繕＝`data.id`） |
| `inference_confidence` | 0.7 | 分類推斷信心門檻 |
| `prefill_api` | — | 預填武裝鍵（宣告則面向啟動時 prefill 租約/分類） |
| `degraded_messages` | — | `{no_contract, gate_disabled}` 降級文案 |
| `candidate_max` | 3 | 推斷退化候選上限 |
| `facet_key` | — | 埋點面向識別（`set_facet`） |
| `enabled_gate` | — | gate 的 vendor_configs 開關鍵名（修繕＝`repair_enabled`；未宣告→不檢查） |
| `confirm_qr_labels` | — | 確認 quick reply 顯示文字覆寫（機器值不變） |
| `contact_config_key` | `service_hotline` | gate 關閉時客服管道鍵覆寫 |

面向配置列鐵則：`target_user` 必須＝`persona_role`（修繕＝`tenant_repair`，`load_rules` 按 `persona_role` 查）。

---

## 13. 串流回應（SSE）

**事件類型依序**：`start` → `intent` → `search` → `answer_chunk`（逐 token）→ `form_field`（如有表單）→ `metadata` → `done`

```
IF request.stream == True:
  └─ StreamingResponse(generate_answer_stream(...))
ELSE:
  └─ JSON 即時回傳
```

---

## 14. 交易面向流程（conversational-repair）

<!-- tested-by: conversational-repair:4.1 -->
<!-- tested-by: conversational-repair:4.4 -->

> 建立：2026-07-11（commit 646743a）。§1–13 的對話面向皆為**診斷型**（收斂＝查詢唯讀）；本節記錄引擎新長出的**交易型面向**（收斂＝執行寫入），以修繕（報修建單）為首個落地。與 SOP（§6）/表單機（§7）並存——**機制本體都保留**，僅修繕子集由 SOP＋逐欄位表單改走本流程。完整邏輯主落點見 [`facet-architecture.md` §七](./facet-architecture.md)。

### 14.1 判定與 state

- **判定**：`grounding_scope` 宣告 `execute_endpoint` ＝交易面向；診斷面向無此鍵、完全走原路徑。
- **state**：`form_sessions.collected_data` 內 `TransactionState`（`slots`／`executed`／`execute_result`／`user_turns`／`awaiting_confirm`）；非交易面向不設這些鍵、既有結構零改變。
- **槽位形狀**：`SlotValue{value, source∈prefill|inferred|user|candidate_pick, confirmed}`；**扁平標量鐵則**（`api_call_handler` 的 `{form.x}` 不吃 dict/點號）。

### 14.2 情境 A 時序（≤3 輪建單）

```mermaid
sequenceDiagram
    participant U as 租客
    participant C as chat.py（進場三路+gate）
    participant P as Prefill
    participant B as Brain
    participant G as 確認gate/execute（引擎）
    participant J as JGB API

    U->>C: 「冷氣壞了」＋照片
    C->>C: 進場（分類路由/Step0.5改道/trigger_facet_key）＋repair_enabled gate
    C->>P: 啟動面向＋Vision 辨識
    P->>J: get_tenant_contracts（雙證 role_id+user_id）
    J-->>P: 1 筆租約 → estate_*=prefill
    P-->>B: slots{estate,分類三槽=inferred}＋缺{emergency_status}
    B-->>U: 第1輪：確認式陳述＋僅問急迫性（確認型槽位不開口問）
    U->>B: 「昨天開始，蠻急的，要自己出錢嗎」
    B->>B: extracted{emergency_status}＋inline_answer（費用，岔題即答）
    B-->>U: 先答費用→action=confirm→confirm_template 摘要＋quick_replies三顆
    U->>G: 「✅ 確認送出」（confirm_submit）
    G->>G: 引擎層決定性判定同意＋保底驗 required_slots 齊
    G->>J: execute（execute_endpoint，execute_params 映射）
    J-->>G: {success,data:{id}}
    G-->>U: receipt_template 回執（單號取 execute_result_path=data.id）＋追蹤指引（executed=true）
```

### 14.3 confirm gate 狀態流

```mermaid
stateDiagram-v2
    [*] --> 收集中: 面向啟動（prefill）
    收集中 --> 收集中: brain ask（只問推不出的詢問型槽位）
    收集中 --> 岔題答: brain inline_answer（費用/時程）→ 同回覆接回收集
    岔題答 --> 收集中
    收集中 --> 確認中: required_slots 全齊 → brain confirm ＋引擎保底驗齊
    確認中 --> 執行: 引擎層決定性同意（按鈕值/明確同意詞）
    確認中 --> 收集中: 「修改」→ brain 帶否定語境重出 confirm（槽位保留、局部更新）
    確認中 --> 取消: 「取消」→ _close、槽位丟棄不留殘單
    確認中 --> 確認中: 模糊語 → 交 brain（安全方向：不送出）
    執行 --> 已建單: 成功 executed=true＋回執
    執行 --> 執行失敗: 失敗→executed 不設＋誠實告知＋重試 quick reply
    已建單 --> 已建單: 冪等——同意詞回「已為您建單 #X」不重複執行
    已建單 --> [*]: 收斂不關會話（供追問進度）
    取消 --> [*]
```

**關鍵鐵則**：
- **收齊≠送出**：brain 回 confirm 後，引擎仍**保底驗 `required_slots` 真的齊**（防 brain 誤判空槽 confirm），沒齊→續問。
- **同意判定在引擎層非 brain**（決定性）：按鈕機器值 `confirm_submit`/`confirm_edit`/`confirm_cancel` 或明確同意詞（好/確認/送出/OK 小集合）→execute。
- **冪等**：`executed=True` 後任何同意詞不重複建單。
- **失敗誠實**：execute 失敗→`executed` 不設＋告知＋重試，絕不假裝成功；brain 失敗→降級一般流程、**絕不建單**。

### 14.4 與 SOP（§6）/表單機（§7）的關係

| 機制 | 修繕子集 | 其餘 |
|---|---|---|
| SOP（§6） | vendor 2/4 各 75 條停用（is_active=false，M2 可逆） | vendor 2 其餘 250 條不動 |
| 表單機（§7） | `jgb_repair_create` schema 保留（vendor_id→NULL），但不走逐欄位流程；僅供 `execute_params` 欄位契約引用 | 其餘表單流程不受影響 |
| 續跑補圖 | `handle_conversational_session` 見 `image_urls`→Vision→`ingest_recognition`：**只填空槽、不覆蓋使用者已提供槽位**；非交易面向/無辨識＝no-op | — |

### 14.5 埋點與切換

- **埋點**：`user_turns` 每輪+1→`set_facet(facet_key, turn_number)`（fire-and-forget、失敗不影響對話；欄位偵測降級）。`usage_events` 新欄 `facet_key VARCHAR(60)`／`turn_number SMALLINT`（M3 加性冪等）。P50/P90＝per session `MAX(turn_number)` 聚合 `percentile_cont`。輪數＝使用者訊息數、開場算第 1 輪。驗收：A 類 e2e ≤3 輪（無岔題）；上線 P50≤4／P90≤6（含岔題），未達標觸發設計覆核。
- **知識 seeds**：錨點 4 筆＋查進度 1 筆（`action_type=api_call→jgb_repairs`，帶身份雙證 params）；走既有 embedding 生成。reranker（`/rerank`）＝stateless cross-encoder，新知識免重建 semantic-model；需清 redis 檢索快取。
- **E1 真 API** 為上線 gate（現 `USE_MOCK_JGB_API` 驗流程；`get_tenant_contracts` 真端點列 J 清單）。
