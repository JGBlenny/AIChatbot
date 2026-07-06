# 需求規格：conversational-diagnosis（對話式診斷框架，合約為首案）

> 建立時間：2026-06-30T07:42:07Z
> 階段：requirements-generated
> 語言：zh-TW

## 簡介

本功能為既有「對話式回答引擎」（`conversational_engine`，目前售前 presales 在用的多輪自適應問答→收斂機制）擴充**「診斷型對話面向」**能力：讓「查詢/診斷某一筆業務資料」的問題（合約為首案），從現行的**單欄表單收集**（`form_fill` + `call_api`）改為**對話式引導**——模糊入口會追問釐清、條件不足會說明還缺什麼、收齊識別後**呼叫真實 API** 回傳狀態/資訊、判斷不是查某筆資料時轉**靜態知識**回答。

本功能**建立於既有元件之上**並完全重用：對話引擎的提問/收斂/合成循環、`api_call_handler`/`JGBSystemAPI`/`_resolve_param_value`（API 呼叫與參數解析）、`handle_conversational_session`（續對話）、既有靜態合約知識。新增的是「對話收斂時能以 **API 回傳**作為 grounding」與「依**知識分類**將請求路由進對話面向」兩項貫通能力。

**主場景**：使用者（房東/管理者，由 JGB 帶 `role_id`）問「我的合約狀態怪怪的」→ 對話引擎追問是哪一份合約（合約編號或物件名稱）→ 收齊後呼叫 jgb2 合約 API → 回傳真實狀態/資訊；若問的是「違約責任」等一般問題則轉靜態知識。

**通用性為硬約束**：所有程式改動一律**讀設定、不得寫死合約**，使未來帳單/繳費/修繕等十幾個 `jgb_*` 面向僅以「新增一筆對話規則 + 標分類」即可零改程式比照啟用。

## 名詞定義

- **診斷型對話面向（diagnosis facet）**：一組「對話式查詢/診斷」設定，掛在 `category='對話規則'` 的一筆知識上（同售前設定機制）。合約為第一個面向。
- **必填槽位（required slot）**：對話收斂前必須收集到的識別資訊（合約面向＝`contract_ref`，即合約編號或物件名稱）。
- **條件不足（insufficient condition）**：必填槽位尚未收齊的狀態；系統應繼續追問並說明還缺什麼，而非空泛收斂或報錯。
- **API grounding（`select:"api"`）**：對話收斂時，以「呼叫設定指定之 API 的回傳資料」作為 LLM 合成的事實底稿（相對於既有 `vector`/`category`/`ids` 三種以**知識**為底稿的 grounding）。
- **參數映射（param mapping）**：把對話收集到的槽位與會話資訊解析成 API 參數的模板設定（沿用既有 `{session.x}` / `{slot.x|if_numeric}` / `{if_text}` 模板，由 `_resolve_param_value` 解析）。
- **分類路由（category routing）**：依「檢索找到之知識的分類」判定請求應進入哪個診斷型對話面向（沿用 `topic_scope{mode:category}` 設定）。
- **三出口分派**：同一路由層對「搜尋到的知識」分派三種答法：一般 FAQ→直接知識答；查詢/診斷→對話+API；結構化送出（寫入，如報修建立）→保留表單。
- **對話規則（persona/rules_text）**：教 LLM 如何開場/追問識別/判斷條件不足/判斷查 API 或用知識/多筆如何反問/語氣的規則文字（同售前 persona）。

## 範圍

### 範圍內
- 對話引擎新增 **API grounding（`select:"api"`）**：收齊必填槽位 → 解析參數 → 呼叫設定指定之 API → 回傳當 grounding 合成回覆；含 **API 回 0 筆 / 多筆** 的處置。
- 收斂門檻**讀設定的必填槽位**（取代寫死的售前欄位），驅動「條件不足→繼續追問」。
- **分類路由**：在既有「檢索找到知識→表單觸發」處，依知識分類改為「啟動診斷型對話」或「維持表單」。
- **依分類查設定**的查詢（wire 目前已存但無人讀取的 `topic_scope`）。
- knowledge-admin 後台設定頁支援設定 API grounding（`api` 選項 + endpoint + 參數映射 + 必填槽位）。
- 交付**合約**為第一個可運作面向：1 筆合約診斷對話規則 + 必要的知識分類補標 + 端到端可運作（打真實 jgb2 API）。
- **通用底座**：上述能力一律讀設定，不綁死合約，支援未來面向零改程式擴充。

### 範圍外
- 不新增/修改派發器結構、檢索 pipeline、reranker、其他 handler、DB schema、後端 `conversational_configs` payload。
- 不修改既有售前（prospect）對話流程，不修改既有表單機制與 `api_call_handler`/`JGBSystemAPI` 內部邏輯（只重用）。
- 不實作「結構化送出（寫入）類」改為對話（如報修建立 `jgb_repair_create` 維持表單）。
- 不撰寫所有面向的對話規則內容；本功能交付**機制** + 合約一個面向範例。
- 不負責 jgb2 後端 API 本身（已存在 `/api/external/v1/contracts/status-overview`）；不負責 prod 環境的 base_url/API key 切換（上線作業）。
- 不新增「身分證/手機→role_id」之租客身分映射（`role_id` 由 JGB 呼叫端帶入）。

## 需求

### Requirement 1：分類路由進入診斷型對話

**使用者故事**：作為使用者，當我問到「某一筆合約」的問題時，我希望系統用對話引導我，而不是直接丟一段靜態說明或死板表單。

#### 驗收標準（EARS）
1. WHEN 智能檢索找到的最高順位知識其分類屬於某個「診斷型對話面向」（如 `條件診斷:合約`）且達表單觸發門檻，THE SYSTEM SHALL 啟動該面向的對話會話，並回傳該面向對話規則所驅動的第一句追問，而非觸發既有表單。
2. WHERE 該分類**未**對應任何診斷型對話面向設定，THE SYSTEM SHALL 維持既有處理（表單觸發或直接知識回答）不變。
3. THE SYSTEM SHALL 以「依分類查設定」之查詢將知識分類對應到對話面向設定，且該查詢 SHALL 反映設定中 `topic_scope{mode:category}` 的分類值。
4. IF 同一請求同時可命中診斷型對話與既有表單，THEN THE SYSTEM SHALL 以分類路由優先（進對話），不重複觸發表單。

### Requirement 2：必填槽位與條件不足追問

**使用者故事**：作為使用者，當我講得不清楚（沒給合約編號或名稱）時，我希望系統明確告訴我還需要什麼，並繼續問，而不是給我空泛或錯誤的回答。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 依**對話面向設定的必填槽位清單**（而非寫死欄位）判斷是否達到收斂條件。
2. WHILE 必填槽位尚未全部收齊，THE SYSTEM SHALL 持續以追問（ask）回應，並引導使用者補齊缺少的識別資訊，不進行 API 呼叫。
3. WHEN 使用者一則訊息即已提供必填槽位（如直接給合約編號），THE SYSTEM SHALL 抽取該槽位並立即進入收斂，不額外追問。
4. THE SYSTEM SHALL 沿用既有對話的提問次數上限保護（達上限強制收斂），避免無限追問。
5. WHERE 設定未指定必填槽位（如售前面向），THE SYSTEM SHALL 維持既有收斂門檻行為不變。

### Requirement 3：API grounding（收齊→呼叫真實 API→回覆）

**使用者故事**：作為使用者，當我給了合約識別後，我希望拿到的是我這份合約的**真實**狀態/資訊，而不是通用說明。

#### 驗收標準（EARS）
1. WHEN 對話收斂且設定的 grounding 方式為 `api`，THE SYSTEM SHALL 以收集到的槽位與會話資訊（含 `role_id`）解析出 API 參數，呼叫設定指定之 API endpoint，並以其回傳資料作為合成回覆的事實底稿。
2. THE SYSTEM SHALL 重用既有參數解析（`{session.x}` / `{slot.x|if_numeric}` / `{if_text}` 模板）與既有 API 呼叫元件，不另寫 API 邏輯。
3. THE SYSTEM SHALL 由設定讀取 endpoint 與參數映射（合約面向＝合約查詢端點），不得將端點或參數寫死於程式。
4. IF API 回傳 0 筆（查無對應資料），THEN THE SYSTEM SHALL 不杜撰結果，並回到追問以請使用者確認/更正識別資訊。
5. IF API 回傳多筆（識別不唯一），THEN THE SYSTEM SHALL 將候選列出並反問使用者選擇哪一筆，再以選定者收斂。
6. WHEN API 呼叫失敗或逾時，THE SYSTEM SHALL 降級為不阻斷的回覆（如請稍後再試或轉專人），不使整個請求失敗。

### Requirement 4：三出口分派與意圖判斷

**使用者故事**：作為使用者，我在同一段對話裡問「我的合約租金多少」或「違約責任怎麼算」，我希望系統各自給對的答案——前者查我的合約、後者給一般說明。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 支援在同一診斷型對話面向中，依對話規則判斷將回覆 grounding 於「API 回傳」或「靜態知識」二者之一。
2. WHEN 使用者問的是某一筆合約的狀態**或資訊**（如租金、到期日、地址），THE SYSTEM SHALL 以同一支合約 API 的回傳資料回答（因該 API 回傳含豐富欄位），不需另建資料來源。
3. WHEN 使用者問的是一般合約知識（非查某一筆），THE SYSTEM SHALL 以既有靜態合約知識回答，不呼叫 API。
4. WHERE 任務屬「結構化送出/寫入」（如建立報修），THE SYSTEM SHALL 維持既有表單機制，不納入本對話面向。

### Requirement 5：後台設定能力（API grounding 可在管理介面設定）

**使用者故事**：作為設定者，我希望能在既有 `/conversational-config` 後台像設定售前一樣，把合約（及未來面向）的對話流程設定好，包含「打哪支 API、帶什麼參數、必填什麼」。

#### 驗收標準（EARS）
1. THE conversational-config 後台 SHALL 在 grounding 選材提供 `api` 選項（與既有 `vector`/`category`/`ids` 並列）。
2. WHEN 設定者選擇 `api` grounding，THE SYSTEM SHALL 提供設定 API endpoint、參數映射、與必填槽位的輸入欄位。
3. THE SYSTEM SHALL 將上述設定寫入既有對話設定資料結構（沿用後端通用 config 收納，不變更後端 payload 契約）。
4. THE SYSTEM SHALL 在設定者寫入/更新後使對話設定即時生效（沿用既有快取清除機制）。

### Requirement 6：通用性（讀設定、不寫死、可零改程式擴充）

**使用者故事**：作為維護者，我希望這次為合約做的底座，未來帳單/繳費/修繕等面向只要加設定就能用，不必再改程式。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 將必填槽位、API endpoint、參數映射、分類路由全部由**設定**驅動，程式中不得出現綁定特定面向（如合約）的硬編值。
2. WHERE 新增另一個診斷型對話面向（如帳單）僅提供「一筆對話規則 + 對應知識分類」，THE SYSTEM SHALL 無需修改程式即可啟用該面向。
3. THE SYSTEM SHALL 使 API grounding 的端點與參數可由設定指向不同 `jgb_*` 端點（合約／帳單／修繕等）。

### Requirement 7：行為保持與重用（不回歸）

**使用者故事**：作為維護者，我要確保這個新功能不會弄壞既有售前對話、既有表單、與一般查詢。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 維持既有售前（prospect）對話流程的進入方式、追問與收斂行為不變。
2. THE SYSTEM SHALL 維持非診斷型對話面向的查詢路徑（既有檢索→表單／直接知識）行為不變。
3. THE SYSTEM SHALL 重用既有 `api_call_handler`、`JGBSystemAPI`、`_resolve_param_value`、`handle_conversational_session`、對話引擎收斂/合成等元件，不修改其對外行為。
4. THE SYSTEM SHALL 不變更 DB schema、派發器結構、檢索 pipeline 與後端設定 payload 契約。
5. WHEN 第二輪以後的續對話發生，THE SYSTEM SHALL 由既有續對話機制接手，無需新增續對話路徑。

### Requirement 8：合約首案交付與端到端驗證

**使用者故事**：作為驗收者，我要看到合約這個面向真的能用——對真實 API 跑通完整對話。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 交付 1 筆「合約診斷對話規則」設定（含分類路由、API grounding 與參數映射、必填槽位 `contract_ref`）。
2. THE SYSTEM SHALL 對缺少分類的合約查詢知識補標所屬診斷分類，使其能被分類路由命中。
3. WHEN 以真實 `role_id`（測試 20151）對真實 jgb2 合約 API 進行端到端對話，THE SYSTEM SHALL 完成「模糊問句→追問→收齊→回真實狀態/資訊」流程。
4. WHEN 使用者於對話中問一般合約知識，THE SYSTEM SHALL 轉靜態知識回答（驗證三出口分派）。
5. THE SYSTEM SHALL 在 API 回 0 筆與多筆情境下分別正確追問確認與列出反問。
6. THE SYSTEM SHALL 通過全層自動化測試（unit/integration/e2e），且既有售前與一般查詢測試不回歸。

## 下一步

```bash
/kiro:validate-gap conversational-diagnosis   # 對既有 codebase 做落差分析（建議）
/kiro:spec-design conversational-diagnosis -y  # 進入設計階段
```
