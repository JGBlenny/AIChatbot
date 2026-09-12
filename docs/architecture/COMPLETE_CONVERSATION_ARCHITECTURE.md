# 對話架構：責任分層、檢索過濾、參數

**最後對碼：2026-09-12**

> 本檔只剩四節，都是**現在仍然成立**的東西：
> §0 三層責任分層（概念，程式無對應符號）、§3 檢索的過濾機制與加成、
> §11 系統角色、§12 關鍵參數。
>
> 2026-09-12 刪掉 976 行——意圖識別、信心度評估、答案優化、SOP 編排、表單管理、
> API 調用、Context 管理、SSE、交易面向、並行檢索與六 case 仲裁：這些機制的程式
> 已於 2026-09-11 隨舊 REST 對話鏈刪除（DSP-046），描述它們的章節一併移除。
> ⛔ 不留「已退役」標記——實測證明那種標記沒人看（2026-09-12 對照實驗：五題裡三題
> 答錯，全部是檔頭有警語、本文沒改的節）。要看舊設計請 `git log`。
>
> 現況架構見 [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md)（全景）與
> [`AGENTIC_MCP_ARCHITECTURE.md`](AGENTIC_MCP_ARCHITECTURE.md) §2b（一回合的完整流程）。

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

## 3. 檢索引擎

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

## 11. 系統角色與職責

| 組件 | 職責 | 關鍵決策點 |
|------|------|-----------|
| **Knowledge Retriever** (`services/vendor_knowledge_retriever_v2.py`) | 知識庫檢索與過濾 | 向量相似度、意圖匹配 |
| **Cache Service** (`services/cache_service.py`) | 三層緩存管理 | 緩存命中、過期策略 |
| **Base Retriever** (`services/base_retriever.py`) | 統一檢索策略 | Pipeline stages、分數組合 |

⚠️ **本表的退役標記已於 2026-09-12 補齊**：在此之前只標了 5 支，`Intent Classifier` 與
`Confidence Evaluator` 漏標，讀者會合理推論「未標＝還在」，進而把 §2（意圖識別）與
§4（信心度評估）整兩節當現況引用。**未標退役的三支（Knowledge Retriever／Cache Service／Base Retriever）是真的還在**。
⚠️ 但「還在」≠「在新線的回合路徑上」：`vendor_knowledge_retriever_v2` 與 `base_retriever`
確實被 `services/agent/**` 用到（`kb.search`）；`cache_service` 的消費者只有 `app.py`／
`routers/vendors.py`／`routers/cache.py`，**不在對話回合路徑上**。

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
# 🔴 2026-09-12 逐鍵對碼（⚠️ 第一版只稽核了「鍵存不存在」、未驗值；值於同日獨立驗證後補正）
OPENAI_MODEL: gpt-4o-mini              # ✅ 仍在（agent/runtime.py、query_rewriter.py）
                                       #    ⛔ 不是 llm_provider.py——它只讀 EMBEDDING_MODEL
KNOWLEDGE_GEN_MODEL: gpt-3.5-turbo     # ✅ 仍在。🔴 值更正：prod compose 預設是 gpt-3.5-turbo，
                                       #    程式 fallback 是 gpt-4o（knowledge_import_service.py）——前稿寫 gpt-4o-mini 兩邊都不對
DOCUMENT_CONVERTER_MODEL: gpt-4o-mini  # ✅ 仍在。🔴 值更正：prod compose 預設 gpt-4o-mini，前稿寫 gpt-4o
QUERY_REWRITE_MODEL: gpt-4o-mini       # ✅ 仍在（query_rewriter.py）
EMBEDDING_MODEL: text-embedding-3-small # ✅ 仍在（llm_provider.py）

# LLM 溫度與 token 配置（環境變數）
# 🔴 2026-09-12 逐鍵對碼：答案優化與意圖分類的六顆溫度鍵全數 0 命中
KNOWLEDGE_GEN_TEMPERATURE: 0.7         # ✅ 仍在（knowledge_generator.py）
KNOWLEDGE_GEN_MAX_TOKENS: 800          # ✅ 仍在（knowledge_generator.py）
QUERY_REWRITE_TEMPERATURE: 0           # ✅ 仍在。🔴 值更正：程式預設與 prod compose 皆為 0，前稿寫 0.3
QUERY_REWRITE_MAX_TOKENS: 100          # ✅ 仍在（query_rewriter.py）
# 新線的模型組態改由 AGENT_MODEL／AGENT_REASONING_EFFORT／IMAGE_RECOGNITION_MODEL／
# DOCUMENT_EXTRACTION_MODEL 管，見 docs/architecture/AGENTIC_MCP_ARCHITECTURE.md §6

# 進場／閘門旗標（🔴 2026-09-12 逐鍵對碼更正，前一版寫「皆為現行值」是錯的）
ENABLE_QUERY_REWRITE_B2B: false        # compose 兩份皆 false；⚠️ 程式 fallback 是 true
                                       #   （services/base_retriever.py）——env 未設的環境會開著
PREENTRY_ROUTABILITY_GATE: false       # ⛔ 已無程式讀者：compose 兩份仍宣告，但 rag-orchestrator
                                       #   的 .py 只有 tests/unit/_meta/test_env_parity_req.py 列名。
                                       #   受測物 `_preentry_routable` 隨 routers/chat.py 一併刪除
                                       #   單發答題的適用性把關」——**線上從來沒有這道閘**

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

🔴 **2026-09-12 對碼更正（數字經獨立驗證後修正）：下表 14 個鍵有 12 個在
`rag-orchestrator/**/*.py` 完全 0 命中。** 兩個例外：`required_slots` 只剩 3 支**測試**引用
（非測試 0 支）；`facet_key` 非測試 3 支（`usage_metering.py`／`conversational_config.py`／
`tools/audit_config.py`）——⚠️ **但 `set_facet` 零生產呼叫端**（正對照：同檔 `set_path`／
`set_decision` 在 `services/agent/shadow.py`／`mcp_facade.py` 有生產呼叫）⇒ 正確說法是
**函式與 DB 欄位仍在、埋點無人呼叫**。 前一版寫「全配置驅動、引擎零硬編」——那是舊鏈 `conversational_engine`
時代的事實，該引擎已刪。**⛔ 不得照本表寫面向配置**：寫出來沒有任何程式會讀。

現行等價能力改由**硬編的工具鏈**承擔，⛔ 不是配置鍵：

| 舊配置鍵 | 現行對應（新線） |
|---|---|
| `execute_endpoint`（修繕＝create_repair） | `services/agent/tools/action.py::REPAIR_CREATE_ACTION`（字串常數 `"repair_create"`） |
| `required_slots`／`confirm_template`／`confirm_qr_labels` | `services/agent/confirm_card.py::render`（程式決定性產卡文字） |
| `execute_params`／`execute_result_path` | `services/agent/tools/action.py` 內的 payload 組裝與 `receipt` |
| `enabled_gate`／`degraded_messages`／`contact_config_key` | 可見性改為 `AGENT_WRITE_TOOLS_ENABLED` AND `ToolSpec.stage`（DSP-038-1） |
| `facet_key`（埋點） | ⚠️ **函式與欄位在、無人呼叫**：`services/usage_metering.py::set_facet` 與 `_FACET_COLS=("facet_key","turn_number")` 都在，但 `set_facet` **零生產呼叫端** |
| `prefill_api`／`candidate_max`／`inference_confidence` | 無對應；照片辨識分類改走 `runtime.IMAGE_SUGGESTION_KEY` 程式補值 |

以下為**歷史記錄**（舊鏈 `grounding_scope` 內的鍵，⛔ 不是現況）：

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

面向配置列鐵則（歷史）：`target_user` 必須＝`persona_role`（修繕＝`tenant_repair`，`load_rules` 按
`persona_role` 查）。🔴 `services/conversational_rules.py::load_rules` 已於 2026-09-11 刪除；
新線的規則正本是 `services/agent/agent_rules.py`，按受眾（非 persona_role）分支。

---

