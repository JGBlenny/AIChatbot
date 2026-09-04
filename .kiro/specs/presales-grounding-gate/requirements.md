# 需求規格：presales-grounding-gate（售前對話「無知識佐證不得生成」閘門）

> 建立時間：2026-09-04　階段：requirements-generated（v2：依 validation_gap §五 回修六條；v1 初版）　語言：zh-TW
> 定位：只修售前小幫手（prospect 身分）在**對話 brain 路徑**上的知識 grounding 與無佐證出口；⛔ 不動一般 b2b／b2c 檢索路徑，⛔ 不補知識條目，⛔ 不改 jgb2 前端（只定契約）。
> 根因正本：`docs/presales-assistant-rootcause-20260904.md`（2026-09-04 canon-audit 22 份＋本機 :8100 重現）。盤查來源：`docs/presales-assistant-quality-audit-20260902.md`（jgb2 側實機測試）。
> ⚠️ 模板缺席：`.kiro/settings/rules/ears-format.md` 與 `templates/specs/requirements.md` 不存在，本檔沿用 `documind-ocr-mapping/requirements.md` 的既有格式。

## 目標形態（拍板基準）

```
prospect 問「有沒有 600 戶以上的客戶」（知識庫沒有任何客戶資料）
  現況：brain 判 answer → grounding 門檻 0.0 撈到最近的三筆泛談 → LLM 依系統脈絡生成
        「並未特別針對 600 戶以上…」／「系統設計上可以支援」（兩裝置相反）
  目標：brain 判 answer、fact_class=customer_reference → grounding 過門檻後為空
        → ⛔ 不呼叫 LLM，回固定句「這題我這邊沒有可靠資料，幫您轉專人——點下方的『找真人』」
        → 回應體帶 handoff:{reason:"no_grounding", fact_class:"customer_reference", channel:"line_official"}
        → 同題連問 5 次逐字相同

prospect 問「舊系統的資料能匯進來嗎？」→ 追問「那物件跟合約呢？」
  現況：R2 合成 prompt 沒有 R1，檢索只用「那物件跟合約呢」→ 答成「物件和合約也可以批次匯入」（合約條目不存在）
  目標：R2 的檢索 query 與合成 prompt 都帶 R1 問句 → grounding 只有物件批次匯入條目 → 回答只講物件、合約明說「這部分我沒有資料」
```

## 已查實的現況（2026-09-04，對碼前提）

- prospect 帶 `session_id` 時由 `routers/chat.py::handle_conversational_entry`（`CONVERSATIONAL_ENABLED_ROLES={'prospect'}`）在分類、檢索、`_top1_relevance_gate` **之前**交給 brain；無 `session_id` 才落一般檢索，且 `_handle_no_knowledge_found` 對 prospect 仍以占位字串呼叫 LLM。
- brain 收斂作答的 grounding：`conversational_engine._converge_grounding` → `_vector_search(similarity_threshold=0.0, top_k=5)` 取前 3 筆 answer；查無以占位字串「（依系統脈絡的功能索引與已知情境給適合建議；…不杜撰、不報價）」照樣送 `synthesize_presales_answer`。
- brain 輸出 JSON 現有鍵：`extracted_fields／action／converge_kind／next_question／converge_topic`；規則文字活在 DB `knowledge_base 3645`（category 對話規則），code fallback 在 `conversational_rules.CONVERSATIONAL_RULES_BY_ROLE`。
- 合成 prompt（`llm_answer_optimizer._build_presales_synth`）不帶對話歷史；brain 只餵 `dialog[-4:]`；無任何上一輪問句意圖的結構化欄位。
- 回應契約（`VendorChatResponse`）只有 `confidence`（售前恆 1.0），無「無佐證／需轉人」訊號；「專人」字樣出現時無入口連結（事實型 `cta_mode=suppress` 不附 CTA 塊）。
- prospect 可見知識 20 筆；`target_user IS NULL` 的知識一律放行給 prospect。

## 已拍板決策（2026-09-04，業主）

| # | 決策 | 依據 |
|---|---|---|
| 1 | 開此 spec，機制層先做；知識條目補充另案 | 業主「開 kiro spec」 |
| 2 | 五類敏感事實（客戶名單／報價／合約 SLA／法遵／資安）⛔ 不用關鍵字規則判，由 brain 回封閉 enum `fact_class` 再由程式決定出口 | 「規則只能治封閉集合」（feedback_rule_vs_layer） |
| 3 | 客戶規模／案例類**刻意不補知識**，一律走「不確定＋轉人」 | 盤查 P0-1「要求的行為」；業主未反對 |

## 待業主裁決（design 階段前）

| # | 問題 | 建議（預設） | 另一選項 |
|---|---|---|---|
| D1 | 無佐證固定句的措辭與 `handoff.channel` 值 | 「這題我這邊沒有可靠資料，幫您轉專人——點下方的『找真人』。」／`channel="line_official"`（對齊 jgb2 切片 2） | 措辭由 DB 對話規則供給（後台可編），程式只保底 |
| D2 ✅ **2026-09-04 定案** | 售前 grounding 門檻 | **`docker-compose.prod.yml` 加 `PRESALES_GROUNDING_THRESHOLD: 0.5`**（程式預設與全系統 `KB_SIMILARITY_THRESHOLD=0.65` 不動）；依 20 題掃描：無知識題最高 0.337、有知識題最低 0.534，0.65 誤擋「電子發票」等 | 0.65（`retrieval-parameters.md` 的知識候選門檻）。⚠️ 三個數字是三個命題：0.55 決策層讀值點／0.6 steering 舊表／0.65 檢索候選；以 prospect 池實測定（research 主題 1） |
| D3 | 推薦題（`converge_kind=recommend`）grounding 為空時是否維持以系統脈絡推薦 | 維持（那是系統脈絡功能索引的本職），但 prompt 加「⛔ 不得含任何客戶／價格／合規事實斷言」 | 也改為 handoff |
| D4 | 敏感五類 grounding **非空**時的處理 | 照答，temperature 固定 0.2、回應只引 grounding 原文，`handoff` 不出現 | 一律 handoff（過度保守，會把有知識的題也擋掉） |

## 名詞定義

- **prospect 路徑**：`mode=b2b`＋`target_user=prospect`，無 `role_id／user_id／vendor_id`；含「有 `session_id`（brain 路徑）」與「無 `session_id`（一般檢索路徑）」兩條。
- **grounding**：售前收斂作答時實際餵給 LLM 的知識 answer 集合；**空 grounding**＝過門檻後零筆（⛔ 占位字串不算 grounding）。
- **事實題／推薦題**：brain 輸出 `converge_kind ∈ {answer, recommend}`。
- **fact_class**：brain 對本輪問題的封閉分類 `{customer_reference, pricing, contract_sla, compliance, security, feature, other}`；缺值或非法值一律視為 `other`（⛔ 不猜變體）。
- **敏感五類**：`customer_reference／pricing／contract_sla／compliance／security`（盤查 P0-1「要求的行為」五類的一對一映射）。
- **handoff**：回應體中的結構化轉人訊號物件；出現＝本題未由知識回答、應導向真人入口。
- **一般 b2b 檢索路徑**：`_smart_retrieval_with_comparison` → `_top1_relevance_gate` → `_build_knowledge_response` 這條；本 spec ⛔ 不得改變其對非 prospect 的任何行為。

## 範圍

### 範圍內
- prospect 兩條路徑的 grounding 門檻、無佐證分流、`fact_class`、`handoff` 契約、多輪問句保留。
- 售前規則文字（DB 3645／code fallback／`PRESALES_ANSWER_RULES`）中「導專人」話術對齊 `handoff` 入口。
- 可觀測：`usage_events` 記錄 handoff 與 fact_class。
- 單元測試、b2b 回歸、本機 :8100 prospect 實打收案。

### 範圍外
- 知識條目補充（權限模型、匯入——匯入待 DSP-008 裁決）。
- P2-1 起手式體驗（`_has_basic_info` 語義與 DB 3645 追問策略）。
- jgb2 前端「找真人」按鈕實作與 LINE 官方帳號接入（切片 2）；本 spec 只定契約。
- P1-1「給可操作下一步」的話術設計。
- 一般 b2b／b2c 檢索路徑、SOP、交易面向。
- DB `knowledge_base 3645`（對話規則）與 `3798`（系統脈絡）的文字更新**由業主執行 SQL**；本 spec 提供文字與 SQL（已核：兩列不在不變量 10／17 母體，寫入不觸發稽核紅燈，但仍是 DB 寫入）。

## 需求

### Requirement 1：售前 grounding 相關性門檻

**使用者故事**：作為業主，我要售前顧問「引用知識」時引用的真的是相關知識，而不是最近的三筆泛談。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 對售前收斂作答的知識撈取套用相關性門檻；門檻比對的 SHALL 是檢索管線的 **final `similarity`**（經 `BaseRetriever.retrieve()` 的 application 端過濾），⛔ 不是純向量分（`_vector_search` 的 `similarity_threshold` 參數不過濾，見 validation_gap 缺口 1）；低於門檻的知識 SHALL NOT 進入 grounding。
2. THE SYSTEM SHALL 以單一環境變數供給售前門檻（名稱由 design 定），未設定時預設值 SHALL 等於既有知識庫門檻（D2）；值不可解析或不在 [0,1] 時 SHALL 回預設並記錄警告，⛔ 不得 500、⛔ 不得靜默放寬為 0。
3. THE SYSTEM SHALL 只在一個讀值點解析該門檻（比照 `retrieval-decision-layer` R7.4「門檻唯一讀值點」），其他模組 SHALL 透過該讀值點取得。
4. WHEN 過門檻後零筆，THE SYSTEM SHALL 視為**空 grounding**；⛔ 不得以占位字串、系統脈絡摘要或任何非知識文字充當 grounding。
5. THE SYSTEM SHALL 對兩條 prospect 路徑（有／無 `session_id`）套用同一門檻語義。

### Requirement 2：無佐證分流（事實題不生成）

**使用者故事**：作為企業評估者，我寧願聽到「這題我沒資料，幫你轉人」，也不要一個敢對客戶名單、報價、合規現場編答案的 AI。

#### 驗收標準（EARS）
1. WHEN brain 判定 `converge_kind=answer` 且 grounding 為空，THE SYSTEM SHALL 回覆固定的無佐證句（D1）並附 `handoff`，且 SHALL NOT 呼叫任何 LLM 生成回答。
2. WHEN brain 判定 `converge_kind=answer` 且 `fact_class` 屬敏感五類且 grounding 為空，THE SYSTEM SHALL 在 `handoff.fact_class` 標明類別；固定句 SHALL 一致，⛔ 不因類別改寫成推測性肯定句。
3. WHEN brain 判定 `converge_kind=answer` 且 grounding 非空，THE SYSTEM SHALL 以 grounding 為唯一事實來源生成回答，temperature SHALL ≤ 0.2；`fact_class` 屬敏感五類時 SHALL 只引 grounding 原文陳述（D4）。
4. WHEN brain 判定 `converge_kind=recommend` 且 grounding 為空，THE SYSTEM SHALL 依 D3 處理；預設維持以系統脈絡功能索引推薦，但 prompt SHALL 明示「⛔ 不得含客戶名單、價格數字、合約條款、法遵、資安的事實斷言」。
5. WHEN prospect 無 `session_id` 而落一般檢索路徑且零命中，THE SYSTEM SHALL 回同一固定句並附 `handoff`，⛔ 不得再以占位字串呼叫 LLM（取代現行 `_handle_no_knowledge_found` 的 prospect 分支）。
6. THE SYSTEM SHALL 對同一問題、任意 session、任意裝置的無佐證回覆做到**逐字相同**（決定性路徑，無 LLM）。
7. （v3，verifier F-1 二次實打；v4 依 e2e 回測修正）WHEN brain 走 `ask` 且帶「岔題即答」`inline_answer`，THE SYSTEM SHALL 對 `inline_answer` 套用同一 grounding 門檻；空 grounding ⇒ 該輪 SHALL 直接以 handoff 決策回覆——**只有固定句**（逐字，R2.6）、附 `handoff`、⛔ 不接 `next_question`（e2e 實測假事實會從問句溜出）；有 grounding ⇒ 原樣保留。⛔ 只對 prospect（交易面向的 inline 由 `kb_search` 工具背書）。
8. （v4，e2e 第二輪 F2）WHEN prospect 在同一 session **逐字重問**一句已走 handoff 的問題，THE SYSTEM SHALL 以同一 `fact_class` 決定性重播固定句＋`handoff`，⛔ 不再呼叫 brain（brain 看到「已轉真人」標記會改問痛點或改判 `other`，固定句便不逐字）。
9. （v4，e2e 第二輪 B4）R4.2 的封閉詞集加入「沒有資料」——那是本 spec 自己要求 LLM 說的句式（「這部分我沒有資料」），承認沒資料就必須給出口。
10. （v5，D6 業主 2026-09-04 定案；**同日二次裁決：D6 以 env `PRESALES_EXTRACTIVE` 開關、預設關**——業主可接受功能邊界的小機率漏，先補知識（DSP-008、3600／3610／3584 講法）再考慮開。關時本條的「抽取」一律改為「交 LLM 依知識合成」，其餘條文不變）WHEN brain 判事實題（`fact_class ≠ other`）且 grounding 非空，THE SYSTEM SHALL 直接回傳 top-1 知識 `answer` **原文**，⛔ 不經 LLM 合成；WHEN 使用者問句以封閉分隔詞（、和跟與及含包含）列了多個項目，THE SYSTEM SHALL 在原文後接固定尾句「以上是我有資料的部分；沒提到的項目我這邊沒有資料，可點下方『找真人』。」並附 `handoff(reason=partial_grounding)`；單項目問句 SHALL 直接貼原文、無 handoff。WHEN brain 走 `ask` 且帶 `inline_answer` 而 grounding 非空，THE SYSTEM SHALL **不論 `fact_class`** 一律抽取（inline 本身就是事實答；D6 上線首輪探針抓到 brain 回 `other`＋「物件和合約也可以匯入」漏出）。推薦題、收斂型 `fact_class=other`、無知識固定句路徑 SHALL 不受影響。理由：e2e 兩輪皆抓到 LLM 對部分相關 grounding 加料（B1），prompt 指令降低不消滅。
11. （v5，e2e 第三輪 A1）WHEN prospect 的使用者訊息含封閉問句標記（`presales_gate.QUESTION_MARKERS`）且 brain 回 `ask`、未填 `inline_answer`、而 `next_question` 以句末標點拆句後的**陳述部分 ≥ 8 字**，THE SYSTEM SHALL 視該陳述為未經 grounding 的答案，整輪改走同一把閘門：grounding 非空 ⇒ 抽取 top-1 原文（⛔ 不接反問句）；空 ⇒ 固定句＋`handoff`。WHEN 陳述不是獨立句、而是問句內以逗號分開、不含問句標記、≥ 8 字的前綴子句（「物件和合約的資料也可以匯入，您還有其他想了解的功能嗎？」），THE SYSTEM SHALL 同樣走 grounding：非空 ⇒ 抽取；空 ⇒ **剝掉該子句只留問句**（⛔ 不升格固定句，因「如果您有 20 間物件，最在意哪一點？」這類合法前綴也會被判成子句，誤判方向刻意往「少講一句」錯）；但剝掉的子句含 R4.2 轉人詞時 SHALL 視同獨立陳述句走固定句＋`handoff`。純反問句、使用者非問句的回合 SHALL 不受影響。理由：brain 把「合約和歷史帳單可匯入」塞進反問句前綴，inline 閘門看不到（3/5 次重現）；D6 上線探針又見同句合併寫法。
13. （v6，主題 pilot 2026-09-04，業主「依序處理」①）WHEN prospect 訊息為**陳述句形的事實題**（brain 回 `ask`、未填 `inline_answer`、但 `fact_class ≠ other`）且 grounding 非空，THE SYSTEM SHALL 走有據作答（同 R2.10 開關：抽取或依知識合成），⛔ 不反問身分；grounding 為空時 SHALL 維持 brain 的反問（⛔ 不升格固定句——陳述句可能真是在描述情境）。理由：46 句問法量測有 15 句被反問，其中 8 句知識已在 top-1，R2.11 只看問句標記看不到陳述句。
12. （v5，e2e 第三輪 E1）WHEN 抽取式回覆的知識原文本身含 R4.2 封閉詞（如 3611「由專人帶您看」），THE SYSTEM SHALL 仍附 `handoff(reason=llm_mentioned_handoff, message=入口提示句)`，文字不改。

### Requirement 3：`fact_class` 封閉分類

**使用者故事**：作為維護者，我要知道每一題被當成哪一類事實處理，而且這個判斷不是靠關鍵字硬猜。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 要求 brain 的 JSON 輸出新增 `fact_class`，值域為封閉 enum `{customer_reference, pricing, contract_sla, compliance, security, feature, other}`。
2. WHEN `fact_class` 缺值、非字串或不在 enum 內，THE SYSTEM SHALL 視為 `other`，⛔ 不得容忍變體（如 `Pricing`、`price`）。
3. THE SYSTEM SHALL 把 `fact_class` 的定義與範例寫入售前對話規則文字（DB 3645 與 code fallback 同步），⛔ 不得在程式內以關鍵字表判類別。
4. THE SYSTEM SHALL 對 brain 呼叫失敗或逾時的情形維持既有降級路徑，`fact_class` 視為 `other`，⛔ 不得因新增欄位讓既有 ask／converge 流程 500。

### Requirement 4：`handoff` 回應契約與話術對齊

**使用者故事**：作為 jgb2 前端，我要一個結構化訊號決定何時畫「找真人」按鈕，而不是去讀回答裡有沒有「專人」兩個字。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 在 `VendorChatResponse` 新增可選欄位 `handoff`，形狀為 `{reason, fact_class, channel, message}`；`reason ∈ {no_grounding, sensitive_no_grounding, llm_mentioned_handoff}`、`channel` 依 D1；欄位不出現時 SHALL 為 `null`，既有呼叫端不升級 SHALL 不受影響。
2. WHEN 回覆文字含「專人」「真人」「客服」任一字樣，THE SYSTEM SHALL 同時帶 `handoff`（測試以程式斷言，⛔ 不靠人讀文字）。決定性路徑由程式直接附上；LLM 生成路徑以**封閉三詞**的後置掃描補 `handoff{reason:"llm_mentioned_handoff"}`，⛔ 只加訊號、不改文字（v2：validation_gap 缺口 6）。
3. THE SYSTEM SHALL 把售前規則文字中「導專人」相關句改為指向入口的話術（D1），DB 3645、`conversational_rules` code fallback、`PRESALES_ANSWER_RULES`／`PRESALES_CTA_RULES` 三處 SHALL 同步。
4. WHEN `handoff` 出現，THE SYSTEM SHALL 在 SSE 串流路徑以與非串流相同的欄位語義送出（既有 `stream_synthesis_response` 亦適用）。
5. THE SYSTEM SHALL 在 `docs/api/conversational-api.md` 與 `docs/jgb2-chat-integration.md` 記錄 `handoff` 欄位、出現條件與前端預期行為（jgb2 切片 2 對齊）。

### Requirement 5：多輪問句意圖保留

**使用者故事**：作為評估中的業者，我追問「那物件跟合約呢？」時，要的是「能不能匯入」的答案，不是「物件與合約有什麼功能」。

#### 驗收標準（EARS）
1. WHEN brain 判定 `converge_kind=answer` 且本輪為追問（同 session 且存在上一輪 Q/A），THE SYSTEM SHALL 把上一輪使用者問句併入 grounding 檢索 query；（v4，e2e 回測 N-1）併入只為召回同題脈絡——**本輪問句自身** SHALL 也過門檻，自身零命中 ⇒ 視為空 grounding，⛔ 不得以併入後撈到的相鄰知識放行生成。
2. WHEN 合成回答時存在上一輪 Q/A，THE SYSTEM SHALL 把上一輪問句與回答（各截既有上限）帶入合成 prompt，並明示「本輪追問延續上一輪的動作意圖」。
3. WHEN 追問的主題在 grounding 中無對應（如「合約」無匯入條目），THE SYSTEM SHALL 對該主題明說「這部分沒有資料」，⛔ 不得換一組功能回答，⛔ 不得把其他主題的能力套到該主題。
4. WHEN 本輪被 brain 判為全新主題（規則 (c)），THE SYSTEM SHALL NOT 讓上一輪問句影響 grounding 檢索（岔題不被拖走）。決定性守門：以本輪 `converge_topic` 與上一輪是否相同判斷是否併入上一輪問句，⛔ 不另做語義判斷（v2）。

### Requirement 6：範圍保護與回歸

**使用者故事**：作為業主，我今天才驗完 b2b 檢索沒被動到，這次不能又被牽連。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 對 `target_user ≠ prospect` 的所有請求維持逐位元相同的回應（`_top1_relevance_gate`、`vendor_knowledge_retriever_v2`、`_build_knowledge_response` 對非 prospect 的行為不變）。
2. THE SYSTEM SHALL 以既有 unit 全套（`make test-unit`）與一組 b2b 10 題 A/B 回測（`backtest_session_` 前綴，改前改後逐字比對）證明 R6.1。
3. THE SYSTEM SHALL NOT 新增第三方相依、⛔ 不得新增 LLM 呼叫次數（無佐證路徑反而減少一次）。

### Requirement 7：可觀測

#### 驗收標準（EARS）
1. WHEN `handoff` 出現，THE SYSTEM SHALL 在 `usage_events` 記錄可查詢的標記；落點由 design 三選一（`decision_snapshot` 快照／補 `escape_kind` setter／`decision_case` 字串，validation_gap 缺口 8），⛔ 不新增表、⛔ 不新增欄位。
2. THE SYSTEM SHALL 記錄 `fact_class` 於同一事件列，供事後統計「哪類問題最常無佐證」。
3. THE SYSTEM SHALL 在日誌只記 `fact_class`、grounding 筆數、門檻值與 `handoff.reason`，⛔ 不記使用者原句以外的個資推斷。

### Requirement 8：可測性與收案

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 有 unit 測試覆蓋：門檻讀值（好值／壞值／缺值）、空 grounding 分流（answer／recommend）、`fact_class` 非法值歸 `other`、`handoff` 形狀、「專人」字樣必帶 handoff、追問 query 併上一輪、岔題不併，每條貼 `@pytest.mark.req("presales-grounding-gate:N.M")`。
2. THE SYSTEM SHALL 以突變控制證明測試有效：把門檻改回 0.0、把 handoff 拿掉、把上一輪併入拿掉，各自至少一條測試轉紅。
3. THE SYSTEM SHALL 在本機 `:8100`（rebuild 後）以 prospect 身分實打：盤查 P0-1 原句連問 5 次逐字相同且帶 `handoff`；P0-3 原句在知識未補前回固定句；P1-3 兩輪 R2 不出現「合約可匯入」；`backtest_session_` 前綴。
4. THE SYSTEM SHALL 由獨立 verifier 對上述收案項複現後才可宣告完成；⛔ 自驗不作收案證據。

## 非功能約束

- **延遲**：無佐證路徑不呼叫 LLM，P95 SHALL 低於現行事實題路徑；有 grounding 路徑不新增 LLM 呼叫。
- **相容**：`handoff` 為可選欄位；未升級的 jgb2 前端行為不變（只是看不到按鈕）。
- **配置驅動**：門檻、固定句、channel 皆可由 env 或 DB 規則覆寫；程式內只留保底。
- **不出境**：售前路徑不新增任何外部服務。

## 驗收矩陣（收案時逐項打勾）

| # | 項目 | 證據 |
|---|---|---|
| 1 | 同題 5 次逐字相同＋`handoff`（P0-1） | :8100 實打腳本輸出 |
| 2 | 「專人」必帶 `handoff`（P0-2） | unit 斷言＋實打抽樣 |
| 3 | P0-3 原句回固定句（知識未補前） | :8100 實打 |
| 4 | P1-3 兩輪無「合約可匯入」 | :8100 實打 |
| 5 | b2b 10 題 A/B 逐字相同 | 回測 diff |
| 6 | `make test-unit` 全綠（既有紅不變） | 測試輸出 |
| 7 | 突變控制三向轉紅 | verifier 回報 |
| 8 | 文件：conversational-api／jgb2-chat-integration 記 `handoff` | 檔案 diff |
