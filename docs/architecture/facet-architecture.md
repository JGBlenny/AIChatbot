# 面向化系統脈絡架構（domain-conversational-facets · 後續演進定案）

> 建立：2026-07-01。本檔記錄「per-領域系統脈絡」在實作審視後演進到「**面向化（facet）三層疊加**」的完整邏輯與資料佈局，取代 design.md 元件1/D2 的兩層版本（design.md 變更歷史已標注）。

> ⚠️ **2026-09-11 更新**：本檔描述的**資料模型／設定概念**（`category_config`、
> `conversational_config`、`grounding_scope`、`persona_role`、`topic_scope`）
> 仍在用——agentic-MCP 新線（`services/agent/runtime.py`／`turn_context.py`／
> `verifier.py`／`tools/handoff.py`）繼續讀這幾張表與這幾個鍵。但下文引用的
> **舊鏈執行程式**（`services/conversational_engine.py`、`services/system_context.py`、
> `routers/chat.py`、`services/jgb/repair_prefill.py`）已隨舊 REST 對話鏈於
> 2026-09-11 整批砍除（commit `7c905408`／`10116570`，見 `.claude/DECISIONS.md`
> DSP-046）。逐段標記見下；`get_system_context` 一類的系統脈絡組裝邏輯，新線
> 對應位置在 `services/agent/outline.py`／`services/agent/prompt_assembler.py`
> （具體對應關係未逐行核對，僅供下一步查找起點）；`repair_prefill.py` 的
> API 預填機制**沒有**新線對應物——agent 路徑改由模型呼叫工具即時取值，
> 不再有程式先行預填槽位這一步，這是能力形態的改變而非搬家。

## 〇、三層責任分層（與母圖 §0 對齊，2026-08-25）

本檔其餘章節談的是**面向怎麼組裝與執行**；先把它與另外兩層分開，否則「進場」很容易
被讀成「這個面向已經對這句話負責」。

```text
① Entry / Routing Hint    誰**被提出**——檢索知識的 categories ＋ 門檻，或 trigger_facet_key 直達
② Face Responsibility     這個面向**該不該承擔本輪 query**——persona 的【本輪範疇 scope】契約
③ Execution               進場後**怎麼做**——本檔第二～七章的內容
```

```text
**Face entry ≠ responsibility ownership。**
`scope=stay/switch` 屬**第②層的責任判定**，不是 entry evidence，也不能反推 entry 是否正確。
進場成立只代表「有人／有檢索證據提出了這個面向」。
```

⚠️ 已證實：**第①層不消費第②層的契約**——entry nomination 不讀 responsibility contract，
兩者唯一的間接耦合是 knowledge-row 上人工維護的 `categories`
（見母圖 §0.3 與 `.kiro/specs/face-exit-before-grounding/`）。
**本檔刻意不畫「應有的 bridge」**——那屬 governance 尚未做的 normative decision。

⚠️ `PREENTRY_ROUTABILITY_GATE`（現行 `false`）把第②層的判定提前到進場之前，但**不是**
「同一判定提前」：它以 `cfg.key` 取 system context，而 in-session 用的是
`_domain_key(config)`（`topic_scope.category`）——**evaluation context 不同源**（實測 digest 不同）。

---

## 一、問題與演進

初版設計把系統脈絡做成「base（target_user NULL）＋ 領域 append（target_user）」兩層，領域鍵＝`persona_role`（=target_user）。實作審視發現三個問題，逐一修正：

1. **base 其實是「售前系統脈絡」**：現有 `target_user IS NULL` 那列（id 3622，`question_summary='售前系統脈絡'`）內容為售前導向（§5b 競品協定、§6 CTA 出口、§7 功能推薦索引）。疊加後合約診斷仍吃到售前銷售脈絡——正是本 spec 要解的缺口 2。
   → **拆分**：把該列切成「真通用 base（§1–5 產品定位/客群/模組/語氣/合規）」＋「售前 append（§5b/6/7，target_user=['prospect']）」。售前疊加＝原文（不回歸）；其他領域不再吃售前。migration：`split_base_system_context_extract_presales.sql`（切在「## 5b」邊界，內容保全自檢）。

2. **領域鍵用 target_user 會撞鍵**：同一角色（property_manager）未來會有多個診斷領域（合約、帳單…），全掛 property_manager → 系統脈絡/persona 互蓋。能唯一區分領域的是**分類（category）**，不是角色。
   → **領域鍵改＝診斷 config 的 `topic_scope.category`（分類值）**。角色級面向（售前 `mode:'all'`）仍用 persona_role/target_user。

3. **合約整份每輪常駐會越長越貴**：合約知識會長（狀態、違約金、續約…），全塞每輪注入浪費 token。
   → **面向化**：把領域知識拆成「母分類共用 ＋ 子分類面向」，**只載入當下問到的面向**。

（另修：半形/全形冒號不一致——config/backfill 用半形 `條件診斷:合約`，category_config 與真知識用全形 `條件診斷：合約`，路由對不上。改採真實資料驅動的分類名。）

## 二、面向模型（三層疊加）

```
通用 base（category='系統脈絡'，無 target_user、無 categories）        —— 每輪必注入
  └ 母分類『系統合約』(categories=['系統合約'])：合約領域共用框架        —— 命中合約任一面向都載
        └ 子面向『狀態判斷』(categories=['狀態判斷'])：各階段下一步/可否操作 —— 只有問狀態才載
              （未來）違約金試算面向、續約面向… 各一列，同理

system_md = base ＋（沿領域鍵在 category_config 的父鏈，母共用在前、子面向在後）
```

- **領域鍵**＝`topic_scope.category`＝子面向值（如 `狀態判斷`）。
- `get_system_context('狀態判斷')` 沿 `category_config` 父鏈（`狀態判斷`→parent `系統合約`）逐層取 `categories` 命中的系統脈絡列，**母共用在前、子面向在後**，疊加於 base 之後。
- **售前**領域鍵＝`prospect`（角色級）→ 走 `target_user`，維持單層（base＋售前 append），內容＝原 3622（不回歸）。

**省 token**：面向一多時每輪只載「base＋母共用＋命中的那個子面向」，不是整個領域。實測合約問狀態＝base560＋母994＋子372≈1930 字，遠低於 4500 上限。

## 三、資料佈局（誰標什麼）

| 資料列 | category | 標記 | 內容 |
|---|---|---|---|
| 通用 base | 系統脈絡 | target_user NULL、categories 空 | 產品定位/客群/模組/語氣/合規（真通用） |
| 售前 append | 系統脈絡 | target_user=['prospect'] | 競品協定/CTA/功能推薦索引（售前專屬） |
| 母『系統合約』 | 系統脈絡 | categories=['系統合約'] | 狀態模型/12 里程碑/續約父子鏈/欄位語義 |
| 子『狀態判斷』 | 系統脈絡 | categories=['狀態判斷'] | 各階段下一步/可否動作前提 |
| 合約診斷 config | 對話規則 | target_user=['property_manager']、metadata.topic_scope.category=`狀態判斷` | persona＋grounding_scope(api) |
| 合約查詢知識 | （原分類） | categories 含 `狀態判斷` | 觸發診斷路由（config_for_category 命中） |
| category_config | — | `系統合約`(母,parent NULL)、`狀態判斷`(子,parent=系統合約) | 面向父子骨架 |

## 四、程式（皆讀設定，與名稱無關）

- `services/system_context.py`（⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）：
  - `_fetch_base`：`target_user IS NULL AND categories 空`（真通用，避免誤取面向列）。
  - `_fetch_category_chain`：`category_config` 遞迴父鏈（母在前、子在後）。
  - `_fetch_appends`：角色級鍵走 target_user 單層；面向鍵沿父鏈逐層取 categories 列，多層。
  - `get_system_context`：`base ＋ "\n\n".join(appends)`，per-key 快取。
- `services/conversational_engine.py::_domain_key(config)`（⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）：`topic_scope.mode=='category'` → `topic_scope.category`；否則 `persona_role`。prepare 兩處呼叫傳它。
- `config_for_category`（chat.py 路由，⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）：**無需改**——config 宣告子面向 `狀態判斷`、知識也掛 `狀態判斷`，精確命中。（若未來知識只掛更細子分類，再補子→母展開。）

## 五、部署順序（migrations）

```bash
# 1) 拆售前出 base（內容保全、冪等、自檢）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/split_base_system_context_extract_presales.sql
# 2) 建面向分類骨架（系統合約母 / 狀態判斷子）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/add_contract_facet_categories.sql
# 3) 合約系統脈絡兩列（母共用 + 子面向）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/seed_domain_contract_system_context.sql
# 4) 合約診斷 config（topic_scope.category=狀態判斷）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/seed_conversational_diagnosis_contract_rule.sql
# 5) 合約查詢知識補標 狀態判斷
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/backfill_contract_knowledge_diagnosis_category.sql
# 套用後清快取（重啟服務，或後台 /conversational-config 任一儲存）
```

## 六、擴一個新面向 / 新領域（零改程式）

- **合約加面向（違約金試算…）**：category_config 加 `違約金`(parent=系統合約)；系統脈絡加一列 `categories=['違約金']`；相關知識掛 `違約金`。問違約金→載 base＋系統合約母＋違約金子。
- **新領域（帳單…）**：category_config 加 `系統帳單`(母)＋子面向；系統脈絡加母/子列；診斷 config topic_scope.category＝該子面向；知識掛該子面向。與合約完全平行，程式不動。

---

## 七、交易面向（conversational-repair 落地）

<!-- tested-by: conversational-repair:4.1 -->
<!-- tested-by: conversational-repair:4.4 -->

> 建立：2026-07-11（commit 646743a）。§一–六是**診斷面向**（收斂＝查詢唯讀）；本節記錄引擎長出的**交易面向**（收斂＝執行寫入），以修繕（報修建單）為第一個落地。與診斷面向共用同一套面向配置機制，差異全在配置與引擎的 confirm/execute 分支——引擎零硬編面向字樣，下一個交易面向（退租等）＝加配置與 seeds、引擎零改動（目標）。

### 7.1 定義：交易面向 vs 診斷面向

| 維度 | 診斷面向（§一–六） | 交易面向（本節） |
|---|---|---|
| 判定 | `grounding_scope` 無 `execute_endpoint` | `grounding_scope` **宣告 `execute_endpoint`** |
| 收斂動作 | 查現值→formatter facts→LLM 組話（唯讀） | 收齊槽位→確認 gate→**執行寫入**（create_repair） |
| state | 既有結構（不設交易鍵） | `form_sessions.collected_data` 內 TransactionState（slots/executed/execute_result/user_turns/awaiting_confirm） |
| brain action | `ask`／`converge` | ＋`confirm`（新） |

- **面向配置列鐵則**：`target_user` 必須＝`persona_role`（修繕＝`tenant_repair`，`load_rules` 按 `persona_role` 查；寫錯全程降級）。

### 7.2 進場三路（共用 repair_enabled gate）

三路都先過同一個 gate helper（`routers/chat.py`（⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）），命中才 seed 面向：

| 路 | 觸發 | 行為 |
|---|---|---|
| ①分類路由（既有機制） | 意圖錨點知識（`vendor_ids` 空、`question` 主題關鍵字式、掛「修繕報修」分類）命中，觸發門檻 similarity≥0.75 | `by_category` 1:1 → 面向配置。**模糊敘述**（如「房子有點問題」）<0.75 不進面向、先澄清 |
| ②Step 0.5 改道 | 損傷照片 `is_damage` 且信心足 | **不打 SOP 檢索**、直接 seed 修繕面向並攜帶 RecognitionResult；找不到面向配置→降級回原行為（安全網）；非損傷/信心不足維持現行降級。非租約標的（公共區域）損傷仍進面向、由對話處理，不另設分支 |
| ③`trigger_facet_key` 直達（chat API 新選填參數） | 命中 conversational config registry（by_key）且 enabled | 跳過意圖辨識直接 seed（帶本次訊息與圖）；**未命中→照常管線不報錯**（防呆） |

⚠️ 三路都只是**第①層的提名**；進場後仍由第②層（`scope=stay/switch`）決定要不要承擔，
可在 grounding 之前關閉會話並重路由（見 §〇）。

**gate（`enabled_gate`）**：面向配置有 `enabled_gate` 鍵（修繕＝`"repair_enabled"`）才檢查——`vendor_configs` 讀值、**缺值預設 true**；`false`→不進面向、回 `degraded_messages.gate_disabled` 文案並注入客服管道參數（預設鍵 `service_hotline`，可由 `contact_config_key` 覆蓋）。gate 僅對「宣告 `enabled_gate` 的面向」生效（配置驅動，引擎/進場不硬編修繕字樣）。

### 7.3 槽位預填 Prefill（`services/jgb/repair_prefill.py`，⚠️ 已隨舊鏈於 2026-09-11 退役、新線無對應物，見檔頭註記）

面向啟動時執行、配置 `prefill_api` 鍵武裝。

**物件（estate）**：`get_tenant_contracts(role_id, user_id)`（雙證；mock 契約 `{success, data:[{contract_id, estate_id, estate_title, display_address, room}]}`）——
- 1 筆 → 扁平標量槽 `estate_id`／`contract_id`／`estate_display`（source=`'prefill'`）
- N 筆 → `pending_candidates`（重用插點 A 三級比對，物件轉選擇項一輪）
- 0 筆或 API 失敗 → `degraded_messages.no_contract`、**不開面向**

**分類**：Vision `RecognitionResult`（`suggested_category`/`item`/`reason`/`emergency`＋`confidence`）→ `resolve_repair_classification` 以 `get_repair_categories` 分類樹做名稱→ID 解析——
- `confidence≥inference_confidence`（配置，預設 0.7）→ `category_id`／`item_id`（int）＋`broken_reason`（str）＋display 槽（`category`/`item`）（source=`'inferred'`，**確認型槽位**：陳述＋允許否定、不開口問）；急迫性推斷為 `emergency_status` 槽
- 信心不足 → 2–3 候選選一輪（`candidate_max` 預設 3，**不退三層下拉**）
- 名稱樹上對不到 → 該槽留空變詢問型；樹查詢失敗 → 降級候選不拋錯；無圖 → 分類槽留空由 brain 開口問

**槽位統一形狀（SlotValue）**：`{value, source∈prefill|inferred|user|candidate_pick, confirmed}`。**扁平標量鐵則**——`api_call_handler` 的 `{form.x}` 解析不吃 dict／點號，故所有可映射槽位皆為扁平標量。

### 7.4 Brain 交易語義（`llm_answer_optimizer.conversational_step`）

- `action='ask'|'converge'|'confirm'`（新）＋`inline_answer`（岔題即答：有則先答再接 next_question/摘要）；未知 action→None（**拒絕不寬鬆回退**）；`confirm` 免 next_question。
- 規則範本 `conversational_rules.TRANSACTION_FACET_RULES` 三條：
  - (a) `required_slots` 全齊（含推斷槽）→`confirm`
  - (b) 任何槽位被否定→更新後重出 `confirm`
  - (c) 岔題→`inline_answer` 先答、同回覆接回收集
- brain 失敗回 None→降級一般流程、**絕不建單**。

### 7.5 確認 gate 與執行（`conversational_engine`）

**確認（收齊≠送出）**：brain 回 `confirm` 且引擎**保底驗 `required_slots` 真的齊**（沒齊→續問，防 brain 誤判空槽 confirm）→ `confirm_template` 組摘要（缺槽容錯渲染）＋`quick_replies` 三顆（機器值 `confirm_submit`/`confirm_edit`/`confirm_cancel`，顯示文字可由 `confirm_qr_labels` 覆蓋）→ `awaiting_confirm` 存 state 等下一輪。

**同意判定在引擎層非 brain（決定性）**——下一輪先於 brain：
- 按鈕 value 或明確同意詞（好/確認/送出/OK 小集合）→ execute
- 「修改」→ 回 brain 帶否定語境重出 confirm（槽位保留、局部更新，不重跑流程）
- 「取消」→ 既有 `_close`、槽位丟棄不留殘單
- 模糊語 → 交 brain（安全方向：不送出）

**execute**：重用 `execute_api_call`（`endpoint=execute_endpoint`、params 由 `execute_params` 以 `params_from_form` 語彙自槽位映射、支援 `{session.role_id}`）——
- 成功 → `executed=True`＋`receipt_template` 回執（單號取 `execute_result_path`，修繕＝`data.id`；`execute_api_call` 回傳雙包 `result.data`＝原始 API `{success,data:{id}}`；＋追蹤指引）
- 失敗/例外 → **`executed` 不設**＋誠實告知＋「再試一次」quick reply（**絕不假裝成功**）

**冪等**：`executed=True` 後任何同意詞→回「已為您建單 #X」不重複執行；收斂**不關會話**（沿用既有慣例）供追問。

**state**：`form_sessions.collected_data` 存 TransactionState（`slots`/`executed`/`execute_result`/`user_turns`/`awaiting_confirm`）；非交易面向不設這些鍵、既有結構零改變。

### 7.6 續跑補圖（image 通道）

`handle_conversational_session` 見 `image_urls`→Vision→`engine.ingest_recognition`——**只填空槽、絕不覆蓋使用者已提供槽位**；非交易面向/無會話/無辨識＝no-op；Vision 失敗/timeout→無推斷降級不阻斷。

### 7.7 埋點（可觀測性）

`user_turns` 每輪+1→`usage_metering.set_facet(facet_key, turn_number)`（fire-and-forget、失敗不影響對話；欄位偵測降級——欄位未建事件本體照寫）。`usage_events` 新欄 `facet_key VARCHAR(60)`／`turn_number SMALLINT`（M3 加性冪等）。

- P50/P90＝per session `MAX(turn_number)` 聚合 `percentile_cont`。
- 驗收：A 類 e2e ≤3 輪（無岔題腳本）；上線 P50≤4／P90≤6 含岔題，未達標觸發設計覆核。
- 輪數定義＝使用者訊息數、開場算第 1 輪。

### 7.8 配置鍵全表（`grounding_scope` 內，全配置驅動）

| 鍵 | 用途 |
|---|---|
| `execute_endpoint` | 收斂寫入的 API 端點（＝交易面向判定依據） |
| `execute_params` | slots→params 映射（`params_from_form` 語彙，支援 `{session.role_id}`） |
| `required_slots` | 必填槽位清單（引擎保底驗齊） |
| `confirm_template` | 確認摘要範本（嵌槽位、缺槽容錯渲染） |
| `receipt_template` | 成功回執範本 |
| `execute_result_path` | 回執取單號路徑（修繕＝`data.id`） |
| `inference_confidence` | 分類推斷信心門檻（預設 0.7） |
| `prefill_api` | 預填武裝鍵（宣告則面向啟動時 prefill） |
| `degraded_messages` | `{no_contract, gate_disabled}` 降級文案 |
| `candidate_max` | 推斷退化候選上限（預設 3） |
| `facet_key` | 埋點面向識別 |
| `enabled_gate` | gate 的 vendor_configs 開關鍵名（修繕＝`repair_enabled`；未宣告→不檢查） |
| `confirm_qr_labels` | 確認 quick reply 顯示文字覆寫（機器值不變） |
| `contact_config_key` | gate 關閉時客服管道鍵覆寫（預設 `service_hotline`） |

### 7.9 邊界與降級矩陣

| 情況 | 行為 |
|---|---|
| 未綁定/雙證缺 | 誠實降級引導、不進面向、不預填 |
| 多租約 | 物件變選擇項一輪 |
| `repair_enabled` 關 | 降級文案＋客服管道 |
| 任一階段取消 | 不留殘單 |
| FAQ 快路徑 | 零影響（回歸鎖） |
| brain 失敗 | 降級一般流程、絕不建單 |
| execute 失敗 | 誠實告知＋重試、不假裝成功 |
| E1 真 API | 上線 gate（現 `USE_MOCK_JGB_API` 驗流程；`get_tenant_contracts` 真端點列 J 清單） |

### 7.10 切換與資料

- **M2**：停 vendor 2/4 `next_form_id='jgb_repair_create'` SOP 各 75 條（`is_active=false` 可逆、rollback 備、prod 使用者手動）；vendor 2 其餘 250 條非修繕 SOP 不動。
- **M1**（表單 vendor_id 2→NULL）免辦——dev＋prod dump 雙查證已是 NULL。表單機本體不動（schema 僅供欄位契約）。
- **知識 seeds**：錨點 4 筆＋查進度 1 筆（`action_type=api_call→jgb_repairs`，帶身份雙證 params）。
- **reranker**（`/rerank`）＝stateless cross-encoder，新知識免重建 semantic-model；需清 redis 檢索快取。
