# 需求規格：option-routing（選項層決策樹路由）

> 建立時間：2026-06-20T08:15:27Z
> 階段：requirements-generated
> 語言：zh-TW
> 修訂：2026-06-20 依 presales-kb 三份文件盤查補入 G1–G5（不報價合規、競品分支、URL 葉出口、方案分級邏輯、起手式兩題）

## 簡介

本功能為表單系統（`form_schemas` / `form_manager`）新增「**選項層路由（per-option routing）**」能力：讓 select 選單表單的**每個選項各自決定後續走向**，實現真正的「依答案分歧」決策樹，而非既有 form-chaining 的「整張表單接同一張後續表單」的主幹式串接。

本功能**建立於既有 form-chaining 機制之上**（串接引擎 `_maybe_chain_next_form`、`branch_answer` 葉答案、合併呈現、會話切換、取消守衛、最新列更新修正），僅將「後續路由」的來源從**表單層**下放到**被選中的選項層**。

**主場景**：售前顧問 bot（presales）決策樹——使用者諮詢時，依「個人 vs 團隊」「痛點類型」等選擇，分歧到不同的後續問題、模組說明與行動呼籲（CTA），最終收束到試用 / demo / 專人 / 公開頁等出口，全程遵守售前合規約束（不主動報價、IoT 不主動提、競品中立）。

## 名詞定義

- **選項層路由（option route）**：掛在 select 選項上的後續走向設定，可為「葉出口」與/或「後續子樹」。
- **葉出口（leaf outlet）**：分支底端的去向，共三型：(a) **知識答案**（沿用 `branch_answer` 回一筆知識）；(b) **動作表單**（串接 `trial_form` / `demo_form` 收集留資並 `call_api`）；(c) **導向連結 / 公開頁**（如 `/pricing`、`/features`、`/advantages`）。
- **後續子樹（branch / 內部節點）**：選項對應一張後續表單，選擇後自動接續呈現（沿用串接引擎）。
- **主幹式串接（form-level chaining）**：既有 form-chaining 行為，整張表單完成後接同一張 `next_form_id` 後續表單，與被選中的選項無關。
- **CTA 表單**：行動呼籲表單（如 `trial_form` 試用、`demo_form` 預約 demo），`on_complete_action=call_api`。
- **不報價約束**：bot **不**在對話中報方案級距 / 價格數字，一律導向 `/pricing` 或留資；IoT 硬體不主動提、被問才轉專人且不報價。
- **決策樹深度**：一次對話中連續自動串接的表單層數（沿用 form-chaining 的深度上限與循環防護）。
- **葉答案合成（grounded LLM synthesis）**：葉節點回知識答案時，以「選定的審核知識」為唯一事實底稿、加跨步情境，由 LLM 合成個人化措辭（不改事實、受合規 prompt 約束）。
- **跨步情境累積**：決策樹各步被選中選項所代表的情境（如個人房東 / 約 20 戶 / 痛點）沿串接累積，供葉答案合成個人化使用。
- **系統脈絡 md**：一份精簡審核過的售前底座文件（產品概觀 / 客群 / 模組概覽 / 品牌語氣 / 合規鐵則 / 競品協定 / CTA 慣例 / 功能索引），注入所有 prospect 情境的 LLM 合成；只放穩定·一般·索引，不放價格 / 競品事實 / 功能細節。
- **AI 引導式顧問對話**：以 LLM 驅動的自適應售前對話——依使用者回答決定下一步（提問或收斂），提問優先標準欄位、缺口才動態補問，AI 自判或使用者要求時收斂給 grounded 推薦結論。受系統脈絡 md 合規護欄約束。
- **顧問對話狀態**：跨輪保存的已收集欄位值 / 已知缺口 / 累積情境，限本會話。
- **收斂**：AI 判斷已知欄位足以推薦（或使用者要求）→ 停止提問、給出個人化推薦結論（方案級距說明 + 模組 + CTA），grounding 只用已收集情境 + 知識 + md。

## 範圍

### 範圍內
- select 選項層的「後續路由」設定機制：葉出口（知識答案 / 動作表單 / 導向連結）、後續子樹、兩者合併。
- 表單完成時，依**被選中的選項**決定回覆與後續串接。
- 與既有表單層 `next_form_id` 主幹串接的優先順序與共存。
- 多個選項路由到同一後續表單 / 同一出口（多對一匯流）。
- 沿用 form-chaining 的深度上限、循環防護、容錯、合併呈現、會話切換、取消。
- presales 合規行為：不主動報價 / 級距、IoT 不主動提、競品被問才中立比較。
- 交付一個可運作的 presales 決策樹範例（個人 vs 團隊分流 + 痛點分流 + 競品比較，導向 CTA / 公開頁）。
- **葉答案 LLM 個人化 + 跨串接情境累積**：葉節點知識答案以「選定知識 + 系統脈絡 md」grounding、整合跨步情境，由 LLM 合成自然回覆（決定性路由不變）。
- **系統脈絡 md**：精簡審核底座，注入所有 prospect 情境的 LLM 合成（葉答案 + 自由問答），含功能索引以支援情境式功能推薦。
- **AI 引導式顧問對話**：LLM 驅動的自適應售前對話（自適應提問 + 收斂判準 + 對話狀態 + 合規護欄）；CTA 留資仍用結構化表單、選單入口保留為 fast-path（決策樹降為 CTA + 快速選，顧問對話交 AI）。

### 範圍外
- **樹根入口觸發穩健性**（自然語言 → 進入決策樹第一張表單）：沿用既有檢索觸發（向量相似度 ≥ `FORM_TRIGGER_THRESHOLD` + 業態過濾 + reranker）。已確認 b2b mode 下運作正常，本功能不修改檢索 / reranker / 觸發門檻，僅標註關聯。
- 不新增 `presales` mode（系統 `BUSINESS_MODES=['b2c','b2b']`）；售前訪客掛既有 **b2b** mode，售前知識以 b2b/`system_provider` scope 新增資料。
- 不重做 CTA 留資表單（`trial_form` / `demo_form` 對齊既有 `demoForm` 欄位）；本功能只負責「導向對的 CTA 表單 / 出口」。
- 不實作公開頁本身（`/pricing` 等頁面）；本功能僅負責在對話中**導向**該連結。
- 不交付完整售前知識「內容」的全部撰寫；交付**機制** + 一個可運作的分歧範例。

## 需求

### Requirement 1：選項層路由設定

**使用者故事**：作為表單設定者，我希望能在 select 選項上標示「選了它之後要走哪裡」，這樣不同選項就能分歧到不同的後續。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 支援在 select 欄位的每個選項上設定可選的「後續路由」，可指定下列任一或組合：後續表單識別碼（`next_form_id`）、葉答案（知識識別碼）、導向連結（公開頁 URL）。
2. WHERE 一個選項未設定任何後續路由，THE SYSTEM SHALL 維持該選項的既有行為（沿用表單層設定或既有 `branch_answer`），不產生分歧。
3. THE SYSTEM SHALL 允許後續子樹表單本身亦設定選項層路由，以支援多層決策樹（受 Requirement 6 深度上限約束）。
4. IF 選項層路由指向的後續表單不存在或未啟用，THEN THE SYSTEM SHALL 不中斷來源表單完成，並照常回覆來源完成結果（不分歧）。

### Requirement 2：依被選中選項分歧

**使用者故事**：作為使用者，我在選單選擇一個選項後，希望系統依「我選的那個」決定接下來要回什麼、要不要再問。

#### 驗收標準（EARS）
1. WHEN 一張 select 表單完成且**被選中的選項**設有後續路由，THE SYSTEM SHALL 依該選項（而非表單層）的設定決定後續走向。
2. WHERE 被選中選項設有葉出口（知識答案 / 導向連結），THE SYSTEM SHALL 呈現該葉出口內容，且該分支結束（不再串接）。
3. WHERE 被選中選項設有後續子樹，THE SYSTEM SHALL 自動為該後續表單建立收集中（COLLECTING）會話並在同一回應中呈現其第一個欄位提示。
4. WHERE 被選中選項同時設有葉出口與後續子樹，THE SYSTEM SHALL 在單一回應中先呈現葉出口、再接續後續子樹的第一欄提示（沿用合併呈現分隔）。
5. THE SYSTEM SHALL 依被選中選項的路由結果套用回應旗標契約（後續子樹時 `form_triggered=True`、`form_completed=False`、`form_id`/`current_field`/`quick_replies` 指向後續表單；純葉出口時為完成）。

### Requirement 3：與表單層串接的優先順序與共存

**使用者故事**：作為系統維運者，我希望新的選項層路由與既有表單層串接能並存且規則清楚，不互相打架。

#### 驗收標準（EARS）
1. WHEN 一張 select 表單完成且被選中選項設有後續路由，THE SYSTEM SHALL **優先**採用選項層路由，忽略表單層 `next_form_id`。
2. IF 被選中選項未設後續路由，THEN THE SYSTEM SHALL **回退（fallback）**到表單層 `next_form_id` 的既有主幹串接行為。
3. WHERE 表單的最後一欄非 select（無選項可承載路由），THE SYSTEM SHALL 沿用表單層 `next_form_id` 主幹串接，行為與現況一致。

### Requirement 4：葉出口（知識答案 / 動作表單 / 導向連結）

**使用者故事**：作為使用者，我希望走到決策樹底端時，能直接得到答案、被自然帶到「試用 / 預約 demo」，或被導到對的公開頁。

#### 驗收標準（EARS）
1. WHEN 被選中選項的葉答案指向一筆知識，THE SYSTEM SHALL 透過 `branch_answer` 回覆該知識內容，全程不經向量檢索。
2. WHERE 被選中選項的後續子樹是 CTA 動作表單（如 `trial_form` / `demo_form`），THE SYSTEM SHALL 串接該表單以收集留資並於完成時執行其 `call_api` 動作。
3. WHERE 被選中選項的葉出口是導向連結（公開頁 URL，如 `/pricing`、`/features`、`/advantages`），THE SYSTEM SHALL 在回應中提供該連結作為出口。
4. THE SYSTEM SHALL 允許多個選項路由到同一後續表單 / 同一出口（多對一匯流），例如多個痛點皆導向 `demo_form`。
5. IF 被選中選項輸入無法對應任何選項，THEN THE SYSTEM SHALL 回覆該選單設定的 fallback 訊息，不送入向量檢索。

### Requirement 5：取消與離題

**使用者故事**：作為使用者，我在決策樹任一層若不想繼續，希望能取消；若改問別的，系統也應合理處置。

#### 驗收標準（EARS）
1. WHEN 使用者於決策樹任一 select 層輸入取消關鍵字，THE SYSTEM SHALL 結束目前會話、不再自動串接後續，並沿用既有取消回應（`form_cancelled`）。
2. WHILE 決策樹會話進行中，IF 使用者輸入明顯離題內容，THEN THE SYSTEM SHALL 依既有離題（DIGRESSION）機制處置，不因選項層路由而失效。
3. WHEN 會話被取消，THE SYSTEM SHALL 清除觸發情境，避免後續被錯誤地再次自動觸發。

### Requirement 6：防護與容錯

**使用者故事**：作為系統維運者，我希望選項層路由不會造成無限串接或在出錯時拖垮對話。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 沿用 form-chaining 的串接深度上限，達上限後不再自動串接後續子樹。
2. IF 選項層路由形成循環（已訪表單再次被指向），THEN THE SYSTEM SHALL 中止串接並照常回覆當前結果。
3. IF 後續子樹會話建立過程發生錯誤，THEN THE SYSTEM SHALL 不中斷來源表單完成、記錄日誌，並回覆來源完成結果。
4. THE SYSTEM SHALL 確保選項層路由的任何失敗都不影響來源表單既有的核心完成行為（純加值）。

### Requirement 7：向後相容

**使用者故事**：作為系統維運者，我希望新增選項層路由後，所有既有表單與 form-chaining 行為維持不變。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 確保所有未設定選項層路由的既有 select 選項，其完成與回覆行為與本功能上線前完全一致。
2. THE SYSTEM SHALL 確保既有表單層 `next_form_id` 主幹串接（含 form-chaining 已上線之金流範例）行為不受影響。
3. WHEN 本功能所需的選項層路由設定尚未填寫於任何選項，THE SYSTEM SHALL 正常運作且不產生錯誤。

### Requirement 8：presales 決策樹範例

**使用者故事**：作為產品方，我希望有一個可運作的售前決策樹，讓潛在客戶用點選方式被引導到適合的方案與行動。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 交付一個可運作的 presales 決策樹範例，以既有資料表（`knowledge_base` / `form_schemas`）擴充資料實作，不新增資料表。
2. WHEN 使用者於起手式進行身分定位（個人房東 vs 公司/團隊；以及大約管幾戶），THE SYSTEM SHALL 依「**有無團隊**」為主要分界進行分流（50 戶為個人↔法人象徵分界、31–49 戶依有無團隊判斷而非純戶數）。
3. WHERE 歸類為個人房東，THE SYSTEM SHALL 對應個人方案級距（約 10 / 20 / 30 戶）並依不報價規則（Requirement 9）導向 `/pricing` 或留資，並推免費試用（`trial_form`）。
4. WHERE 歸類為公司/團隊，THE SYSTEM SHALL 導向全模組 + 大房東報表說明並串接 `demo_form` / 專人。
5. WHEN 使用者於痛點選單選擇一個痛點（收租對帳 / 合約 / 人多協作 / 抄表換鎖 / 交報表 / 報修），THE SYSTEM SHALL 依選擇導向對應模組說明（C1–C6 / 大房東報表 / 修繕）並收束到對應出口（一般走 demo；IoT 類依 Requirement 9 走專人、不報價）。
6. WHERE presales 知識與表單，THE SYSTEM SHALL 以既有 b2b mode（`system_provider` scope）建立，使售前訪客在 b2b 情境下可被檢索觸發。

### Requirement 9：售前合規與引導約束

**使用者故事**：作為產品方，我希望 bot 在售前對話中遵守不報價、IoT 不主動、必收束出口的規則，避免講出不該講的內容。

#### 驗收標準（EARS）
1. WHEN 使用者詢問方案 / 價格 / 級距，THE SYSTEM SHALL 導向 `/pricing` 或留資，且 SHALL NOT 在對話中報出方案級距或價格數字。
2. THE SYSTEM SHALL NOT 主動提及 IoT 硬體（智慧門鎖 / 電錶）；WHEN 使用者主動詢問 IoT，THE SYSTEM SHALL 回「有支援，細節與費用由專人說明」並導向留資 / 專人，且不報價。
3. THE SYSTEM SHALL 在每段售前對話的分支底端收束到一個明確出口（試用 / demo / 公開頁 / 專人），不留空懸。

### Requirement 10：競品比較分支

**使用者故事**：作為產品方，我希望使用者問到競品時，bot 能中立、只憑事實回應，並收束回我們的優勢與行動。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL NOT 主動點名競品；WHEN 使用者主動提及競品，THE SYSTEM SHALL 才進入競品比較分支。
2. WHEN 進入競品比較，THE SYSTEM SHALL 僅依既有競品事實知識（KB-E1）中立陳述；WHERE 對手某功能未列明，THE SYSTEM SHALL 回「不確定對方是否提供，建議您直接向對方確認」，且 SHALL NOT 斷言對方「無 / 不支援」。
3. WHEN 完成競品比較，THE SYSTEM SHALL 收束回 JGB 差異化優勢（KB-E2）並導向試用 / demo。
4. THE SYSTEM SHALL NOT 討論競品價格或傳播未經證實的負面訊息。

### Requirement 11：葉答案個人化（grounded LLM 合成）

**使用者故事**：作為潛在客戶，我希望 bot 依我提供的情境（身分、戶數、痛點）量身說明，而非制式吐知識原文。

#### 驗收標準（EARS）
1. WHEN 葉節點需回知識答案（`answer_kb`），THE SYSTEM SHALL 以「跨步收集情境 + 選定的審核知識」為輸入，經 LLM 合成個人化回覆。
2. THE SYSTEM SHALL 以**「選定的審核知識 + 系統脈絡 md（見 Requirement 13）」為事實來源（grounding）**；LLM SHALL NOT 新增、誇大或變更兩者未涵蓋的事實，尤其價格、競品、IoT 規格。
3. THE SYSTEM SHALL 以合規 system prompt 約束輸出：不報價（導 `/pricing` 或留資）、IoT 不主動且細節由專人、競品中立不斷言、每段收束至明確出口（與 Requirement 9、10 一致）。
4. WHERE 葉節點為**動作表單（CTA）或結構輸出**（表單第一欄 / quick_replies），THE SYSTEM SHALL 維持決定性模板、不經 LLM。
5. IF LLM 合成失敗 / 逾時 / 超出成本上限，THEN THE SYSTEM SHALL 降級回選定知識原文（沿用既有降級機制）。

### Requirement 12：跨串接情境累積

**使用者故事**：作為產品方，我希望葉答案能整合使用者在決策樹各步的選擇，而不只看最後一步。

#### 驗收標準（EARS）
1. WHEN 表單串接（A → B → …），THE SYSTEM SHALL 將各步「被選中選項所代表的情境」累積保存於串接情境（沿用 metadata 傳遞）。
2. WHEN 葉答案 LLM 合成（Requirement 11），THE SYSTEM SHALL 將累積情境（如：個人房東 + 約 20 戶 + 痛點：收租對帳）一併作為輸入。
3. THE SYSTEM SHALL NOT 因情境累積而改變決定性路由——累積**僅供措辭個人化**，不影響選哪個知識 / CTA。
4. 累積情境 SHALL 限於本決策樹會話，隨會話結束 / 取消失效（不跨會話保留）。

### Requirement 13：系統脈絡 md（grounding 底座 + 功能索引）

**使用者故事**：作為產品方，我希望除了逐筆知識，還有一份精簡的系統底座，讓 AI 在知識不足時仍能以一致的產品框架、口吻與合規準則作答，並能依使用者情境點名推薦功能。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 維護一份**精簡、審核過**的系統脈絡 md（產品概觀 / 客群適配 / 模組概覽 / 品牌語氣 / 合規鐵則 / 競品協定 / CTA 慣例 / 功能索引），作為 prospect 情境 LLM 合成的常駐底座。
2. THE SYSTEM SHALL 將系統脈絡 md 注入**所有 prospect 情境的 LLM 合成**（決策樹葉答案 + 自由問答，如競品比較 / 功能推薦），不限於決策樹葉節點。
3. WHERE 使用者描述情境（而非點選選項），THE SYSTEM MAY 依 md 的**功能索引點名推薦**對應功能（如退租結算 → 差額發票），並收束至出口；功能**細節** SHALL 以知識為準，WHEN md 與知識皆無該細節，THE SYSTEM SHALL 導 demo / 專人、SHALL NOT 自行展開。
4. 系統脈絡 md SHALL 只含「穩定 · 一般 · 索引」——**不含價格數字、競品事實、功能運作細節**；且 SHALL 維持精簡（每次合成皆注入，見非功能效能）。
5. THE SYSTEM SHALL 以 md 的**競品協定**（不主動點名 / 只用本次 E1 / 未列明說不確定 / 不斷言對方沒有 / 收束回 E2）約束所有競品相關合成；md 本身 SHALL NOT 含競品事實（事實只在 E1 知識，被問才檢索）。

### Requirement 14：AI 引導式自適應提問

**使用者故事**：作為潛在客戶，我希望 bot 像顧問一樣依我說的問對問題，而非套固定選單。

#### 驗收標準（EARS）
1. WHEN prospect 在顧問對話中，THE SYSTEM SHALL 依「已收集情境 + 缺口」決定下一步：提問或收斂。
2. THE SYSTEM SHALL **優先問標準欄位**（身分 / 管理規模(戶數) / 有無團隊 / 痛點 / 有興趣功能）中尚未知者。
3. WHERE 某情境需釐清但無對應標準欄位，THE SYSTEM MAY **動態生成一題補問**，惟 SHALL 限於售前 scope（產品適配相關），SHALL NOT 問敏感 / 無關問題。
4. THE SYSTEM SHALL 設**提問上限（預設 ≤ 4 題）**；達上限 SHALL 收斂或導出口。
5. THE SYSTEM SHALL **一次只問一個重點**（不一次轟炸多題）。

### Requirement 15：收斂判準與推薦結論

**使用者故事**：作為潛在客戶，我希望聊到一個程度 bot 就給我具體建議，不要一直問。

#### 驗收標準（EARS）
1. WHEN 已收集欄位足以推薦（**至少身分 +「規模或痛點」之一**），THE SYSTEM SHALL 收斂並給出推薦結論。
2. WHEN 使用者明確要求結論（如「直接給我建議」「不用問了」），THE SYSTEM SHALL **立即收斂**。
3. 收斂結論 SHALL 為 grounded 個人化推薦：依已收集情境給適合方案級距說明（**不報價**）+ 對應模組 + 明確 CTA（試用 / demo / pricing）。
4. 收斂結論 SHALL **只用「已收集情境 + 選定知識 + 系統脈絡 md」**為事實來源（不杜撰）。

### Requirement 16：顧問對話狀態管理

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 維護顧問對話狀態（已收集欄位值 / 已知缺口 / 累積情境）跨輪保存。
2. 對話狀態 SHALL 限本會話，隨結束 / 取消 / 收斂清除（不跨會話）。
3. THE SYSTEM SHALL NOT 重複問已收集的欄位（沿用已知，不重問）。

### Requirement 17：AI 提問 / 收斂的合規護欄

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以系統脈絡 md 鐵則約束所有提問與收斂結論。
2. 提問與結論 SHALL 遵守不報價 / IoT 不主動 / 競品中立 / 不杜撰 / 每段收束出口（與 Requirement 9、10、11 一致）。
3. WHEN AI 提問 / 收斂呼叫失敗 / 逾時，THE SYSTEM SHALL **降級至既有路徑**（選單入口或自由問答合成），不阻斷對話。
4. THE SYSTEM SHALL NOT 因 AI 自由度而新增 / 變更已選定知識的事實。

### Requirement 18：與既有機制的分工與 fast-path

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以 AI 引導對話負責「了解 + 推薦」；以**結構化 CTA 表單**（`trial_form` / `demo_form`）負責「留資 / 提交」（精準收集 → POST `/api2`）。
2. THE SYSTEM SHALL 保留 `presales_entry` 收斂選單為 **fast-path**（想點選者快速進主題），與 AI 自由對話並存。
3. THE SYSTEM SHALL 沿用既有 b2b mode + `target_user='prospect'` 檢索路由，不新增 mode。

### Requirement 19：對話式回答模式（generic + 資料驅動 + 可擴充）

**使用者故事**：作為產品方，我希望「多輪自適應問答→收斂」是一個**通用的回答模式**（不綁售前），可依設定 opt-in 套用到不同面向的問題，且能擴充。

**reframe 說明**：R14–R18 描述的「AI 引導顧問」其本質為**通用「對話式回答」模式**；售前適配僅為**第一個套用此模式的面向**。命名由 `advisor` 改為「對話式回答 / conversational」。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 支援答案的「**回答模式**」：`direct`（單次直答，現況）與 `conversational`（多輪自適應問答 → 收斂）。
2. THE SYSTEM SHALL 以**設定（資料驅動）opt-in**決定哪些問題/主題走 `conversational`；**未設定者一律 `direct`**（不把直答題拖進問答迴圈）。
3. 每個 conversational **設定**（一筆 = 一個面向）SHALL 含：①入口（哪個選項/問題進）②persona/規則（依 target_user 或 per-config）③**grounding 範圍**（收斂從哪批知識推薦，多面向不互撈）④seed/目標。
4. THE SYSTEM SHALL 以**資料驅動**載入 persona/規則（如 DB `category='對話規則'`，依 target_user）+ code 內建預設 fallback；**新增面向 / 角色 = 加設定資料，不動程式**。
5. WHEN 多個 conversational 面向並存，THE SYSTEM SHALL 依各設定的 grounding 範圍**各自檢索其知識**，SHALL NOT 跨面向互撈。
6. 售前適配 SHALL 為第一個 conversational 設定（persona=售前顧問、target_user=prospect、grounding=售前知識）；R14–R18 為此模式的機制與此面向的套用。

## 非功能性需求

1. **決定性（路由層）**：決策樹的**路由與知識/CTA 選擇** SHALL 不依賴向量檢索 / reranker——被選中選項 → 對應知識 id / 後續表單為**確定映射**，確保 reranker 異常時樹內仍能正確走訪並選出正確知識。葉答案的「最終措辭」MAY 由 LLM 合成（見 Requirement 11），惟 LLM SHALL NOT 改變已選定的知識事實與 CTA 去向。
2. **可觀測性**：選項層路由的觸發、分歧、深度、循環中止、錯誤 SHALL 留有日誌。
3. **效能**：選項層**路由解析** SHALL 不引入額外外部 API 或 LLM 呼叫。葉答案 LLM 合成 MAY 引入一次 LLM 呼叫（見 Requirement 11）；WHEN 合成失敗 / 逾時，THE SYSTEM SHALL 降級回「選定知識原文」，不阻斷對話、不丟失答案。
4. **最小改動**：SHALL 最大化重用 form-chaining 既有引擎，僅改動「後續路由的來源」（表單層→選項層）。
5. **合規**：售前回應 SHALL 遵守不報價、IoT 不主動、競品中立（Requirement 9、10），此為內容合規硬約束。

## 驗收情境（端到端範例，b2b mode）

1. 業者/潛在客戶問「想了解你們系統適不適合我」→ 觸發售前起手式選單。
2. 選「個人房東」→ 系統依分流接「大約管幾戶？」子樹（與「團隊」完全不同路徑）。
3. 選對應戶數 → 回對應方案**說明（不報價）**，問價格則導向 `/pricing` 或留資 → 推 `trial_form`。
4. （另一路）選「公司/團隊」→ 回團隊模組說明 → 串接 `demo_form`。
5. 痛點選單選「收租對帳很亂」→ 回帳務模組(C3)說明 → 收束 demo；選「抄電表/換鎖煩」→ 回 IoT「有支援，細節由專人說明」→ 走專人（不報價）。
6. 使用者主動問「你們跟 Bananas 差在哪」→ 進競品分支 → 中立陳述事實、未列明處不斷言 → 收束回 JGB 優勢 → 推 demo。
7. 問「多少錢 / 怎麼收費」→ 導向 `/pricing` 或留資，不在對話報數字。
8. 任一層輸入「取消」→ 結束、不再自動串接。
9. 樹內**路由與知識選擇**不經向量檢索（決定性）；葉答案**措辭得經 LLM 合成**，但以選定知識 grounding、不改事實（Requirement 11）。

## 下一步

- 審核本需求文件。
- （建議，既有 codebase）執行 `/kiro:validate-gap option-routing` 進行實作落差分析。
- 核准後執行 `/kiro:spec-design option-routing -y` 進入設計階段（含「擴充共存 vs 取代」最終定案、選項路由 schema 設計含三型葉出口、起手式分流邏輯表達）。
