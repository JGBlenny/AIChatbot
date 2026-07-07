# 落差分析：conversational-diagnosis（對話式診斷框架，合約為首案）

> 建立時間：2026-06-30
> 需求：requirements.md（R1–R8）
> 性質：brownfield 擴充——以既有對話引擎 + API 呼叫 + 檢索路由為底座，補「API grounding」與「分類路由進對話」兩項貫通能力。

## 分析摘要

- **底座幾乎齊備**：對話引擎的「多輪追問→收斂→合成」循環、`api_call_handler`/`JGBSystemAPI`（真實合約 API 已驗證可打通）、參數模板解析、續對話接手——皆現成可重用。
- **核心落差只有兩處新能力**：① 引擎收斂時能以 **API 回傳**為 grounding（現只支援 ids/category/vector 三種知識 grounding）；② 在「檢索找到知識」處依**分類**將請求導入對話面向（售前是「按角色從前門進」，合約需「按分類從檢索進」）。
- **其餘為接線/設定/前端**：收斂門檻改讀設定槽位、`topic_scope` 接線（定義已存、無人讀取）、前端設定頁加 api 欄位、1 筆合約對話規則 + 分類補標。
- **兩個需設計定案的阻點**：(a) 從「檢索表單觸發點」啟動 conversational session 並回第一句追問、且確保第 2 輪由既有續對話接手；(b) API 回**多筆/0 筆**時的對話回饋機制（state 存候選反問 vs grounding 帶候選讓 LLM 列出）。
- **建議取向 A（在既有各點原地擴充，加性集中）**；取向 B（把合約也做成前門進）違反 topic-gated 否決；取向 C（多欄位表單模擬）做不到意圖判斷否決。

## 現有元件與重用對照

| 需求 | 既有元件 | 位置 | 重用/落差 |
|---|---|---|---|
| 對話循環/收斂/合成 | `ConversationalEngine.prepare/handle/stream_answer/_finalize_converge` | `conversational_engine.py:~99-200` | ✅ 全重用 |
| 續對話（第2輪+） | `handle_conversational_session`（檢查 `form_id=='conversational'`） | `chat.py:405` | ✅ 全重用（不改） |
| 會話建立 | `engine._start`（建 `form_id='conversational'` + 存 `config_key`） | `conversational_engine.py:59` | ✅ 重用 |
| 設定載入 | `conversational_config`（by_key/by_role 索引、快取） | `conversational_config.py` | ⚠️ 缺 by_category（③附） |
| API 呼叫 | `APICallHandler.execute_api_call` + `get_api_call_handler(db_pool)` | `api_call_handler.py:784` | ✅ 重用 |
| 真實合約 API | `JGBSystemAPI.get_contracts`→`/api/external/v1/contracts/status-overview` | `jgb_system_api.py:151` | ✅ 已驗證可打通 |
| 參數模板解析 | `_resolve_param_value`（`{session.x}`/`{x|if_numeric/if_text}`） | `api_call_handler.py:267` | ⚠️ 需確認 slot 來源綁定（待研究） |
| 收斂門檻 | `_has_basic_info`（寫死 identity/scale/pain） | `conversational_engine.py:29` | ❌ 改讀 config（①） |
| 收斂 grounding | `_converge_grounding`（ids/category/vector 三分支） | `conversational_engine.py:202` | ❌ 加 `select:"api"`（②） |
| 表單觸發點 | `_build_knowledge_response` 依 action_type 觸發表單 | `chat.py:~2765` | ❌ 加分類路由分支（③） |
| 後台設定 | `ConversationalConfigView.vue`（vector/category/ids） | `knowledge-admin/frontend` | ❌ 加 api 欄位（④） |
| 後端設定 payload | `conversational_configs.py`（通用 config dict） | rag-orchestrator | ✅ 不改（已收任意 config） |

## 核心機制落差與整合阻點

### 落差 1（核心）：引擎無 API grounding（R3 / 改②）
`_converge_grounding`（:202）僅 `select` in {ids, category, vector}，全部以**知識**為底稿。需加 `elif select=="api"` 分支：解析參數 → 呼叫 `api_handler` → 回傳當 grounding。
- **整合**：`engine.__init__`（:現簽章 `db_pool, optimizer, retriever, get_system_context, rules_loader`）加 `api_handler` 參數；`app.py:108` 實例化時注入 `get_api_call_handler(db_pool)`。
- **阻點/待研究**：`_resolve_param_value` 目前服務表單（來源 form_data/session_data）。對話要把 `collected_fields`（槽位）當 `{slot.x}` 來源餵入——需確認其介面能否接收對話的槽位 dict，或加一層轉接（設計階段定）。

### 落差 2（核心阻點）：分類路由進對話（R1 / 改③ + ③附）
售前是「Step1.5 前門、按 `target_user` 進」（`handle_conversational_entry` 寫死 `{'prospect'}`）。合約需「檢索找到知識、按**分類**進」——位置在 `_build_knowledge_response` 的表單觸發點（:~2765）。
- **整合**：在觸發表單前，以 best_knowledge 的分類查「依分類找設定」（③附）；命中診斷面向 → 呼叫 `engine.handle(start_if_absent=True)` 取第一句追問、轉 `VendorChatResponse` 回傳；否則維持表單。
- **接手**：`_start` 會建 `form_id='conversational'` 並存 `config_key`，故第 2 輪 `handle_conversational_session`（:405）會自動接手、`prepare` 以 `config_key` 還原設定——**續對話零改**。
- **阻點/待研究**：啟動時機與回應形狀（ask 的 `{answer}` 如何包成既有回應/串流）需與既有「表單觸發回應」對齊，避免破壞 SSE/JSON 契約。

### 落差 3：`topic_scope` 定義已存、無人讀取（R1.3 / ③附）
`conversational_config.py` 的 cache 只有 `by_key`/`by_role`，`topic_scope` 僅被存進物件（:74）未被消費。需建 `by_category` 索引 + `config_for_category()` 查詢，wire `topic_scope{mode:category}`。小而獨立。

### 落差 4：收斂門檻寫死（R2 / 改①）
`_has_basic_info(fields)`（:29）寫死 identity/scale/pain。改為 `_has_basic_info(fields, config)` 讀 `config.required_slots`；呼叫點（:134，`prepare` 內，`config` 在 scope）一併傳入。售前無 required_slots → 維持舊行為。極小。

### 落差 5：前端設定頁無 api grounding（R5 / 改④）
`ConversationalConfigView.vue`（214 行）grounding 下拉僅 vector/category/ids（:78-82），無 endpoint/params/required_slots 欄位。加 `api` 選項 + 對應輸入。後端 payload 已收通用 config（不改）。純前端表單。

### 落差 6：API 多筆/0 筆的對話回饋（R3.4/R3.5 阻點）
引擎現以 LLM `step` 決定 ask/converge，無「API 回多筆→再一輪反問選哪筆」的機制。需設計：
- **選項甲**：把 API 候選存進對話 state，下一輪以「請選擇」追問，使用者選定後再以單筆收斂。
- **選項乙**：grounding 直接帶候選清單文字，由 LLM 在合成時列出反問（較簡單、但較不結構化）。
- 0 筆：grounding 帶「查無」訊息 → 回追問確認識別。設計階段定案。

### 落差 7：合約首案資料（R8 / 純資料，無程式落差）
- 新增 1 筆「合約診斷對話規則」（category=對話規則）：persona_role + rules_text + topic_scope(category:條件診斷:合約) + grounding_scope(select:api + endpoint:jgb_contracts + params + required_slots:[contract_ref])。
- 合約 form_fill 知識中 category 空白者（前查約 4 筆）補標 `條件診斷:合約`。

## 實作取向評估

### 取向 A：在既有各點原地擴充（推薦）
①②於 `conversational_engine.py`、③於 `chat.py` 表單觸發點、③附於 `conversational_config.py`、④於前端。全加性、集中於對話引擎一檔為主。
- **優點**：重用最大、影響半徑小、續對話/API/解析全現成；符合「通用底座」（讀設定）。
- **缺點**：落差 1 的參數來源轉接、落差 6 的多筆機制需設計定案。

### 取向 B：把合約也做成「前門進」（按角色加進 `CONVERSATIONAL_ENABLED_ROLES`）
- **否決**：會把該角色**所有**流量吸進對話（帳單/修繕/繳費都被誤吸），違反 topic-gated 與需求 R7.2。

### 取向 C：多欄位表單 + form_then_api 模擬「追問」
- **否決**：表單是腳本式收集，做不到 R2 的自適應「條件不足」與 R4 的意圖判斷/轉知識，不符「對話式」需求。

## 風險與待研究（交設計階段）

1. **參數來源綁定**（落差1）：`_resolve_param_value` 介面能否直接吃對話 `collected_fields` 當 `{slot.x}`；或加薄轉接層。→ 設計需定介面。
2. **多筆/0 筆對話回饋**（落差6）：選甲（state 存候選反問）vs 選乙（grounding 帶候選）。→ 影響使用者體驗與狀態複雜度。
3. **從檢索啟動對話的回應契約**（落差2）：ask 結果包成 JSON/SSE 與既有表單觸發回應一致；確保不破壞串流。
4. **API 回傳→grounding 文字**：通用格式化器 vs 每面向自訂；首案合約先做可運作版，通用化於設計權衡。
5. **通用性驗證**：①②③④ 不得殘留合約硬編；設計需明列「未來面向只加設定」的零改程式路徑。
6. **session 衝突**：合約對話沿用 `form_id='conversational'`，與售前共用同一 session 命名；需確認 `config_key` 還原能正確區分面向（_start 已存 config.key，應足夠，設計覆核）。

## 結論與下一步

- **可行性高**：核心只新增「API grounding」與「分類路由」兩能力，其餘為接線/設定/前端；底座（引擎、API、解析、續對話）全現成且合約 API 已實測可打通。
- **建議取向 A**，並於設計階段先定案落差 1/6 兩個阻點（參數來源、多筆回饋）。
- 進入設計：

```bash
/kiro:spec-design conversational-diagnosis -y
```
