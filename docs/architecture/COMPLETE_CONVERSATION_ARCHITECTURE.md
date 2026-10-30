# 對話架構：責任分層、檢索過濾、參數

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

**最後對碼：2026-09-12**

> 本檔只剩四節，都是**現在仍然成立**的東西：
> §0 三層責任分層（概念，程式無對應符號）、§3 檢索的過濾機制與加成、
> §11 系統角色、§12 關鍵參數。
>
> 2026-09-12 分兩批刪掉 1,400＋行——意圖識別、信心度評估、答案優化、SOP 編排、表單管理、
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
         （任務 7 定案；`tests/unit/agent/test_select_scope_req.py`／`test_jgb2_tools_req.py`）
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
- **文件類排除**（2026-09-12 補：前一版漏列這兩條）：
  `category IS DISTINCT FROM '系統脈絡'` AND `category IS DISTINCT FROM '對話規則'`
  ——`SYSTEM_DOC_CATEGORY`／`RULES_DOC_CATEGORY` 兩個常數；這兩類列只給後台維護看，
  ⛔ 不進檢索結果。查證：`grep -n "IS DISTINCT FROM" rag-orchestrator/services/vendor_knowledge_retriever_v2.py`

### 優先級與加成（知識庫專屬）

> ⚠️ 2026-07-16 對碼修正：原記載「priority>0 且 similarity≥0.70 → +0.15」**無實裝**。實碼行為：`priority` 用於檢索排序（vendor_knowledge_retriever_v2.py:121 `ORDER BY kb.priority DESC`）；分數加成為關鍵字加成 1.0–1.3x（`services/base_retriever.py::_apply_keyword_boost`，每詞 +0.1、上限 +0.3）。

> Retriever Pipeline 各階段分數欄位的詳細說明，請參考 [retriever-pipeline.md](./retriever-pipeline.md)。

---

## 11. 系統角色與職責

| 組件 | 職責 | 關鍵決策點 |
|------|------|-----------|
| **Knowledge Retriever** (`services/vendor_knowledge_retriever_v2.py`) | 知識庫檢索與過濾 | 向量相似度、意圖匹配 |
| **Cache Service** (`services/cache_service.py`) | 三層緩存管理 | 緩存命中、過期策略 |
| **Base Retriever** (`services/base_retriever.py`) | 統一檢索策略 | Pipeline stages、分數組合 |

⚠️ **上表三支都真的還在，但「還在」≠「在新線的回合路徑上」**：`vendor_knowledge_retriever_v2` 與 `base_retriever`
確實被 `services/agent/**` 用到（`kb.search`）；`cache_service` 的消費者只有 `app.py`／
`routers/vendors.py`／`routers/cache.py`，**不在對話回合路徑上**。

---

## 12. 關鍵參數配置

> ⚠️ **母圖只引用、不複製**：參數的唯一真實來源是
> [docs/retrieval-parameters.md](../retrieval-parameters.md) 與兩份 compose 的宣告。
> 本節僅為速查；**發現不一致時以該檔與 compose 為準，並回寫本節**。
>
> 🔴 **2026-09-12 全表逐鍵對碼：以下每一個鍵都有 `rag-orchestrator` 非測試 `.py` 讀者。**
> 同日刪掉 13 個 0 命中的鍵（主體隨舊鏈於 2026-09-11 刪除）。
> ⛔ 要看舊旋鈕請 `git show c93c60fe:docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md`。

```yaml
# 分數閾值
KB_SIMILARITY_THRESHOLD: 0.65    # 檢索過濾門檻。⛔ 不取代 knowledge_min=0.6，那是另一顆
FORM_TRIGGER_THRESHOLD: 0.75     # 表單觸發／**面向進場提名**共用門檻（§0.5 ①）
                                 # ⚠️ 讀者只有 services/decision_layer.py::DecisionConfig，
                                 #    而該檔 docstring 自述零生產呼叫端——鍵活著、路可能是死的

# LLM 模型配置（環境變數）
OPENAI_MODEL: gpt-4o-mini              # agent/runtime.py、query_rewriter.py
                                       #   ⛔ 不是 llm_provider.py——它只讀 EMBEDDING_MODEL
KNOWLEDGE_GEN_MODEL: gpt-3.5-turbo     # prod compose 預設 gpt-3.5-turbo；
                                       #   程式 fallback 是 gpt-4o（knowledge_import_service.py）
DOCUMENT_CONVERTER_MODEL: gpt-4o-mini  # prod compose 預設 gpt-4o-mini
QUERY_REWRITE_MODEL: gpt-4o-mini       # query_rewriter.py
EMBEDDING_MODEL: text-embedding-3-small # llm_provider.py

# LLM 溫度與 token 配置（環境變數）
KNOWLEDGE_GEN_TEMPERATURE: 0.7         # knowledge_generator.py
KNOWLEDGE_GEN_MAX_TOKENS: 800          # knowledge_generator.py
QUERY_REWRITE_TEMPERATURE: 0           # 程式預設與 prod compose 皆為 0
QUERY_REWRITE_MAX_TOKENS: 100          # query_rewriter.py
# 新線的模型組態改由 AGENT_MODEL／AGENT_REASONING_EFFORT／IMAGE_RECOGNITION_MODEL／
# DOCUMENT_EXTRACTION_MODEL 管，見 docs/architecture/AGENTIC_MCP_ARCHITECTURE.md §6

# 進場旗標
ENABLE_QUERY_REWRITE_B2B: false        # compose 兩份皆 false；⚠️ 程式 fallback 是 true
                                       #   （services/base_retriever.py）——env 未設的環境會開著
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

---

