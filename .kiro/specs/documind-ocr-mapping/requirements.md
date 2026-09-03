# 需求規格：documind-ocr-mapping（DocuMind OCR 結果 → JGB 欄位映射）

> 建立時間：2026-09-03　階段：implementation（v4：D1 定案 A，新增 R4.6 `rental_terms` 來源優先序、R8 作廢；v3：R9.1／9.2 依實作形狀修正）　語言：zh-TW
> 定位：LINE 房東管家「歸納謄本」（線①）與「上傳既存合約」（線②）在 chatai 側的**唯一**工作——把 DocuMind 吐出的 OCR JSON 翻譯成 JGB 欄位草稿。⛔ chatai 不碰檔案、不呼叫 DocuMind、不寫 JGB。
> 對碼前提（2026-09-03 已查實）：chatai 現有圖片路徑只把 URL 交給 OpenAI vision、從不下載檔案；`image_recognition_service` 是修繕損壞分類器（回 `damage_type／suggested_category`），⛔ 不是 OCR；`VendorChatRequest.image_urls` 超過 3 張直接 422；PDF 進 vision 會被 OpenAI 400 後靜默降級。⇒ 本案 ⛔ 不沿用 `/api/v1/message` 的圖片通道。
> 外部契約：DocuMind `POST /api/v1/analyze` 回應（`pages[].structured_data`／`field_confidences`／`needs_confirmation`／`needs_review`／`ocr_raw.text`）；line-bot `docs/chatai-integration-scenario.md` v5 §7.2–§7.5 與 Q8–Q11。
> ⚠️ 模板缺席：`.kiro/settings/rules/ears-format.md` 與 `templates/specs/requirements.md` 皆不存在，本檔沿用 `conversational-repair/requirements.md` 的既有格式。

## 目標形態（拍板基準）

```
line-bot 上傳 PDF 給 DocuMind ──► DocuMind 回 JSON（慢、單線、needs_review 幾乎恆 true）
                                        │
                                        ▼
line-bot  POST chatai /api/v1/ocr-mapping/contract   body = DocuMind 原始回應 ＋ 身分
                                        │
                                        ▼  秒回（無 LLM 時 < 2s）
chatai    { status: "draft",
            fields: { date_start: {value:"2025-01-21", confidence:0.9, source:"ocr", raw:"中華民國114年1月21日"},
                      rent:       {value:13800, confidence:0.9, source:"ocr", raw:"每月租金新台幣壹萬參仟捌佰元整"},
                      deposit_type: {value:1, confidence:0.8, source:"ocr", raw:"押金新台幣貳萬柒仟陸佰元整"},
                      deposit_amount: {value:27600, …},
                      deposit:    {value:null, source:"absent"},          ← ⛔ 不推算
                      cycle_date: {value:null, source:"absent"} … },
            needs_confirmation: ["cycle_date","to_user_first_name",…],
            unmapped_clauses: ["半年繳整年優惠6000","電費預繳1000/月共6個月"],
            provenance: { document_type:"contract", total_pages:12, review_item_id:"…", needs_review:true } }
                                        │
                                        ▼
line-bot LIFF 把 needs_confirmation 那幾格反白，房東確認後才進 JGB
```

設計判斷：**AI 碰翻譯與規則，⛔ 不碰數字**（金額、日期、月數只能來自 OCR 文字或決定性換算）；**每個值都帶出處**（`ocr`／`derived`／`absent`）；**寧可空白也不猜**。

## 已拍板決策（2026-09-03，業主）

1. 分工採 B：DocuMind 負責 OCR＋抽欄位，line-bot 負責檔案與呼叫 DocuMind，chatai 只做映射與規則校驗。
2. chatai 端點為**同步**、無狀態、不碰檔案；⛔ 不新建 job／回呼／佇列。
3. 押金 `deposit_type／deposit／deposit_amount` 二選一，⛔ 不得由另一邊推算（line-bot §7.3；業主曾寫過又拿掉）。
4. 對不到 JGB 欄位的條款一律原樣回傳，⛔ 不得丟棄（§7.5）。
5. `needs_review=true` 的結果一律標 `draft`，⛔ 不得被下游當可信輸出。

## 待業主裁決（design 階段前）

| # | 分岔 | 選項 A | 選項 B |
| --- | --- | --- | --- |
| D1 ✅ **2026-09-04 定案 A** | 租約特有欄位（`deposit_type`／`cycle_date`／`cycle`／`early_termination_*`）DocuMind `contract` 型抽不到 | **採此**：DocuMind 已回 `rental_terms`（僅制式標籤命中），chatai 消費之（R4.6）；缺的欄位由 DocuMind 補樣式（BACKLOG「DocuMind 側待辦」） | chatai 對 `pages[].ocr_raw.text` 做**第二段 LLM 抽取**（gpt-4o-mini、temperature ≤ 0.3、JSON 輸出），值標 `source:"llm_extracted"` |
| D2 | 端點形狀 | 新資源 `POST /api/v1/ocr-mapping/{document_type}`（建議，**已依此實作**；DSP-005） | 掛在 `/api/v1/message` 加 `action` 欄位 |
| D3 | 承租方姓名切分（DocuMind 只回 `party_b` 全名） | chatai 以常見複姓表切姓／名，低信心時整串放 `to_user_last_name` 並列 `needs_confirmation` | ⛔ 不切，整串回 `party_b_full_name`，由 LIFF 讓房東拆 |

✅ D1 已定案 A（2026-09-04）：Requirement 8 整段**作廢**；租約欄位改由 Requirement 4.6 的 `rental_terms` 映射供給。

## 名詞定義

- **DocuMind 回應**：`POST /api/v1/analyze` 的 200 JSON 全文，含 `document_type`、`pages[]`、`needs_review`、`review_item_id`、`stats`。
- **頁級結構化資料**：`pages[i].structured_data`，鍵依 `document_type` 而異；同一欄位可能出現在多頁。
- **欄位值物件**：chatai 回傳的每個 JGB 欄位皆為 `{value, jgb_value, confidence, source, raw, page}`；`value` 給人看（日期 ISO、金額整數），`jgb_value` 給 JGB 送（日期 `Ymd` 整數，與 `jgb_system_api.py` 既有先例同形；非日期欄位兩者相同）；`source ∈ {ocr, derived, llm_extracted, absent}`。
- **決定性換算（derived）**：⛔ 不經 LLM、⛔ 不含猜測的規則轉換——民國年→西元、中文數字→阿拉伯數字、千分位去除、「壹年」→12 個月。
- **草稿（draft）**：回傳整體狀態；只要 DocuMind `needs_review=true` 或任一必填欄位 `absent`，即為 `draft`。

## 範圍

### 範圍內
- 兩種 `document_type` 的映射：`transcript`（謄本 5 欄 → 物件草稿）與 `contract`（通用合約欄位 → JGB 租約欄位，對照 line-bot §7.2 表）。
- 多頁合併：同一欄位跨頁出現時的決定性取值規則與衝突標記。
- 領域規則：押金二選一、兩種曆法、租期月數、未映射條款陣列、逐欄信心度與 `needs_confirmation` 透傳／合併。
- 同步端點、Pydantic 契約、`X-API-Key` 沿用既有機制、`usage_events` 計量。
- 單元測試（以 DocuMind 樣本回應為 fixture）＋ 一組真實謄本／合約回應的 e2e。

### 範圍外
- 呼叫 DocuMind、下載簽章 URL、檔案暫存——line-bot 負責。
- 寫入 JGB（`POST /contracts` 尚不存在；謄本在 JGB 的落點待產品決定）。
- LIFF 顯示與確認流程。
- DocuMind 本身的認證與併發保護（⚠️ **上線前置條件**：目前無認證、公網 IP、單 worker；由 line-bot 側在呼叫端補 auth 與串列化，⛔ 不是本 spec 的工作，但本 spec 不得在該前置未滿足時宣告上線）。
- `document_type = repair_photo`（既有修繕面向的 Step 0.5 vision 路徑已涵蓋）與 `bill`（尚無消費端）。
- 對 OCR 品質本身的改善。

## 需求

### Requirement 1：輸入契約與型別守門

**使用者故事**：作為 line-bot 開發者，我把 DocuMind 的回應原樣丟給 chatai，不必先整理；型別對不上時我要立刻拿到明確錯誤，而不是一份空草稿。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 接受一個包含 DocuMind 回應全文（`document_type`、`pages[]`、`needs_review`、`review_item_id`、`stats`）與呼叫者身分（`vendor_id`、`role_id`、`user_id`）的 JSON 請求。
2. WHEN 路徑上的 `document_type` 與請求體 `document_type` 不一致，THE SYSTEM SHALL 回 400 並帶 `error_code = DOCUMENT_TYPE_MISMATCH`，⛔ 不得以任一方為準靜默處理。
3. WHEN `document_type` 不在 `{transcript, contract}`，THE SYSTEM SHALL 回 400 並帶 `error_code = UNSUPPORTED_DOCUMENT_TYPE`。
4. WHEN `pages[]` 為空或每一頁的 `structured_data` 皆為空物件，THE SYSTEM SHALL 回 200、`status = draft`、所有欄位 `source = absent`，並在 `needs_confirmation` 列出全部必填欄位——⛔ 不得回 500。
5. WHEN 請求體超過 2 MB，THE SYSTEM SHALL 回 413（DocuMind 20 頁回應含 `ocr_raw.text` 通常 < 1 MB；上限由 `OCR_MAPPING_MAX_BODY_MB` 調整）。WHEN 該環境變數為非數字、空字串或 ≤ 0，THE SYSTEM SHALL 回退預設 2 MB，⛔ 不得因此 500 或恆 413（v3，對抗驗證 ②-5）。
6. THE SYSTEM SHALL 沿用 `services/api_key_auth.py` 的 `X-API-Key` 機制與 `RAG_API_AUTH_ENFORCE` 開關，⛔ 不另立一套認證。

### Requirement 2：多頁合併

**使用者故事**：作為房東，我的謄本有四頁、合約有十二頁，同一個欄位可能散在不同頁；我要的是一份合併後的草稿，而不是每頁一份。

#### 驗收標準（EARS）
1. WHEN 同一欄位僅在一頁有非空值，THE SYSTEM SHALL 採用該值並記錄 `page`。
2. WHEN 同一欄位在多頁有**相同**非空值，THE SYSTEM SHALL 採用該值、`confidence` 取各頁最大值、`page` 記錄首見頁。
3. WHEN 同一欄位在多頁有**不同**非空值，THE SYSTEM SHALL 採用 `field_confidences` 最高者為 `value`，將其餘值列入該欄位的 `conflicts[]`，並將該欄位加入 `needs_confirmation`——⛔ 不得靜默取第一頁。
4. WHEN DocuMind 某頁 `llm_postprocessed` 為 `null`（LLM 未觸發），THE SYSTEM SHALL 仍以該頁 `structured_data` 參與合併，⛔ 不得因此跳過該頁。
5. THE SYSTEM SHALL 將 DocuMind 各頁 `structured_data.needs_confirmation` 取聯集後併入回傳的 `needs_confirmation`。
6. WHEN DocuMind 頂層 `field_confidences` 或 `consensus` 非空（DocuMind 自己已做跨頁共識），THE SYSTEM SHALL 優先採用頂層值，頁級合併（2.1–2.3）僅作 fallback，⛔ 不得對同一欄位做兩次合併。

### Requirement 3：謄本映射（transcript）

**使用者故事**：作為房東，我拍了建物謄本，系統把地號、建號、面積、權利範圍、所有權人整理好給我看，我只要核對。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 將 DocuMind `transcript` 的 `land_number`／`building_number`／`area`／`rights_scope`／`owner` 五欄映射為物件草稿欄位，鍵名沿用 DocuMind 原名，⛔ 不得在本 spec 內自行對應到 JGB `estates` 欄位（JGB 落點待產品決定，見範圍外）。
2. WHEN `area` 含千分位或單位文字（如 `"3,406.98"`、`"3406.98平方公尺"`），THE SYSTEM SHALL 回傳 `value = 3406.98`（數值）、`raw` 保留原文、`source = derived`。
3. WHEN `building_number` 為 `null` 且 `land_number` 非空，THE SYSTEM SHALL 在 `provenance.notes` 標記「可能為土地謄本」，⛔ 不得把地號填進建號。
4. WHEN `owner` 為多人（含「、」「及」或多列），THE SYSTEM SHALL 回傳 `owners[]` 陣列並保留原字串於 `raw`，⛔ 不得只取第一人。
5. THE SYSTEM SHALL 為五欄各自帶出 DocuMind 的 `field_confidences[欄位]`；缺者以 `structured_data.extraction_confidence` 補位並標 `confidence_source = page_level`。

### Requirement 4：合約映射（contract → JGB 租約欄位）

**使用者故事**：作為房東，我上傳既有的紙本租約掃描檔，系統把租金、起訖日、承租人整理成 JGB 建約要的格子；對不到的條款也要讓我看到，不能不見。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 依下表把 DocuMind `contract` 的通用欄位映射到 line-bot §7.2 的 JGB 欄位；表中未列的 JGB 欄位一律 `source = absent`：

   | DocuMind | JGB | 換算 |
   | --- | --- | --- |
   | `contract_metadata.effective_date` | `date_start` | Requirement 5 曆法 |
   | `contract_metadata.signing_date` | `lease_signing_date` | Requirement 5；⚠️ 僅 `contract_is_existing ∈ {1,2}` 時 JGB 讀它，本 spec 仍回傳、由 LIFF 決定送不送 |
   | `financial_terms.contract_amount` | `rent` | 中文數字→阿拉伯數字（Requirement 5） |
   | `financial_terms.currency` | `currency` | 原值；缺則 `absent`（⛔ 不預設 TWD） |
   | `financial_terms.payment_deadline` | `cycle_date` | **僅當**原文可決定性解析為 1–31 的整數日（如「每月五日前」）；否則 `absent` 並列 `needs_confirmation` |
   | `parties.party_b` | `to_user_*`（依 D3） | — |
   | `parties.party_b_address` | 不映射 | JGB 承租方地址非建約必填 |
   | `parties.party_a` / `party_a_address` | 不映射 | 出租方由 JGB 帳號帶入 |
   | （`ocr_raw.text` 提前終止視窗）「N 日／天前…通知」 | `early_termination_days` | 決定性解析為 1–365 的整數日，`source=derived`、列 `needs_confirmation`；「一個月前」非日數 ⇒ absent（v3，⑧(b)） |
   | `rental_terms.date_start` | `date_start` | v4：租約專用來源，**優先於** `effective_date`（規則見 4.6）；DocuMind 空白串接民國「114 1 21」依 5.1 換算 |
   | `rental_terms.date_end` | `date_end` | v4：優先於明文「至…止」與月數推算（4.2／4.6） |
   | `rental_terms.monthly_rent` | `rent` | v4：擷取群無「元」（「13,800」「壹萬參仟捌佰」）也決定性收下；優先於 `contract_amount` |
   | `rental_terms.payment_day` | `cycle_date` | v4：「5」→5、「每月5日」→5；「月初／月底」⛔ 不猜 ⇒ 退回 `payment_deadline` |
   | `rental_terms.tenant_name` | `to_user_*`（依 D3） | v4：優先於 `parties.party_b`；不同 ⇒ `party_b_full_name.conflicts` 反白 |
   | `rental_terms.deposit` | **不映射** | v4：DocuMind 把金額（「27,600」）與月數（「2」）混收同一鍵，收到「2」無法區分 ⇒ 二選一鐵則下寧可 absent；押金仍只由 Requirement 6 的原文視窗決定 |

2. THE SYSTEM SHALL 先在 `ocr_raw.text` 讀**明文到期日**（「…起至 <日期> 止」）作為 `date_end`（曆法依 Requirement 5，`raw` 記該段原文）；WHEN 無明文而有租期敘述（Requirement 5.4），THE SYSTEM SHALL 以 `date_start + 月數 − 1 日` 推算並列入 `needs_confirmation`；WHEN 明文與推算**皆有且不同**，THE SYSTEM SHALL 以明文為值、推算值進 `conflicts` 並列入 `needs_confirmation`；兩者一致則不反白（v3，⑧(a)）。
3. THE SYSTEM SHALL 對 line-bot §7.2 表列的每一個 JGB 欄位都回傳一個欄位值物件（即使 `absent`），使 LIFF 不需另行補齊鍵。
4. THE SYSTEM SHALL 將 `cycle_date`、`rent`、`date_start`、`date_end` 四欄（JGB `isWriteDone()` 無條件必填，line-bot 合約規格 §2.5）中任何 `absent` 者加入 `needs_confirmation`，並將整體 `status` 設為 `draft`。
5. WHEN DocuMind `financial_terms.payment_method` 非空，THE SYSTEM SHALL 原樣放入 `unmapped_clauses[]`（JGB 的收款方式為結構化旗標，⛔ 不得由自由文字推導）。
6. （v4，D1 定案 A）WHEN 同一 JGB 欄位同時有 `rental_terms` 來源與通用來源，THE SYSTEM SHALL 以 `rental_terms` 值為準；WHEN 兩者皆可決定性解析且換算後**不同**，THE SYSTEM SHALL 把通用值放入該欄 `conflicts[]` 並列 `needs_confirmation`；WHEN `rental_terms` 值無法決定性解析，THE SYSTEM SHALL 退回通用來源且**不**視為衝突。落選來源的原文一併視為「已被欄位吸收」（7.1）。`date_end` 的三來源順序為 `rental_terms.date_end` → 明文「至…止」→ 月數推算；推算值為最終值時一律反白。⛔ `rental_terms.deposit` 不得消費（見 4.1 表）。

### Requirement 5：曆法、數字與租期的決定性換算

**使用者故事**：作為房東，合約上寫「中華民國114年1月21日」「租期壹年」「新台幣壹萬參仟捌佰元整」，我要拿到系統看得懂的格式，但原文要留著讓我對。

#### 驗收標準（EARS）
1. WHEN 日期原文為民國年（`中華民國NNN年M月D日`、`NNN/M/D`、七碼 `NNNMMDD`、v4：DocuMind 多捕獲組空白串接的 `NNN M D`），THE SYSTEM SHALL 回傳 `value = YYYY-MM-DD`、`jgb_value = YYYYMMDD`（整數）、`source = derived`、`raw` 保留原文。
2. WHEN 日期原文已為西元（`YYYY/M/D`、`YYYY-MM-DD`、`YYYY年M月D日`），THE SYSTEM SHALL 正規化為 `value = YYYY-MM-DD`、`jgb_value = YYYYMMDD`（整數）、`source = ocr`。
3. WHEN 同一份文件同時出現民國與西元且換算後**不一致**，THE SYSTEM SHALL 採 `field_confidences` 較高者，其餘列 `conflicts[]`，並加入 `needs_confirmation`。
4. WHEN `ocr_raw.text` 含租期敘述（`租期壹年`、`租賃期間貳年`、`為期十二個月`、`一年半`），THE SYSTEM SHALL 回傳 `lease_months` 整數（壹年→12、貳年→24、N個月→N、N年半→N×12+6），`source = derived`；⛔ 無法決定性解析者一律 `absent`，⛔ 不得以 LLM 猜。⚠️ v3 邊界（對抗驗證 ②-1 與實打）：租期視窗遇標點即停（「為期二年，押金三個月」＝24）；「押金N個月」不計入租期；無「個」的裸「N月」緊接在「年」之後一律視為日期（「115年1月2」⛔ 不是 +1 個月）。⚠️ 沒有前導年數的獨立「半年」（「租期半年」）目前**不解析**⇒ `absent`（見 BACKLOG「租期獨立半年」，預設不做）。
5. WHEN 金額原文為中文大寫（`壹萬參仟捌佰元整`）或含千分位／單位（`13,800元`），THE SYSTEM SHALL 回傳整數 `value`、`source = derived`；含「元整」以外的模糊量詞（如「約」「以上」）者 `absent` 並列 `needs_confirmation`。
6. THE SYSTEM SHALL 對所有 `derived` 值保證**可逆對照**：`raw` 必含原文全段，使房東能一眼核對。

### Requirement 6：押金二選一（⛔ 不推算）

**使用者故事**：作為房東，押金是我談定的那個數字或那個月數，系統不要自作聰明幫我換算另一邊——租金之後改了，押金不該跟著變。

#### 驗收標準（EARS）
1. WHEN 押金原文為金額（`押金新台幣貳萬柒仟陸佰元整`），THE SYSTEM SHALL 回傳 `deposit_type = 1`、`deposit_amount = 27600`、`deposit = null（absent）`。
2. WHEN 押金原文為月數（`押金貳個月`、`押金二個月租金`），THE SYSTEM SHALL 回傳 `deposit_type = 0`、`deposit = 2`、`deposit_amount = null（absent）`。
3. WHEN 押金原文同時可讀為金額與月數（`貳個月，計貳萬柒仟陸佰元`、`貳萬柒仟陸佰元整（貳個月）`——**不限先後順序**，v3 ②-4），THE SYSTEM SHALL 以**金額**為準（`deposit_type = 1`），月數放 `raw`，並加入 `needs_confirmation` 讓房東選。
4. WHEN 押金原文無法判定型別，THE SYSTEM SHALL 三欄皆 `absent`、`deposit_type` 加入 `needs_confirmation`。
5. THE SYSTEM SHALL NOT 在任何情況下以 `deposit_amount ÷ rent` 推算 `deposit`，亦 SHALL NOT 以 `deposit × rent` 推算 `deposit_amount`；單元測試 SHALL 含此二反例。
6. THE SYSTEM SHALL 對 `deposit_type`／`deposit`／`deposit_amount` 三欄各自標 `source`，使下游能區分「讀到的」與「沒讀到的」。

### Requirement 7：未映射條款與逐欄信心度

**使用者故事**：作為房東，合約裡「半年繳整年優惠 6000」這種條件系統沒欄位裝，但它是我談的條件，我要看到它被收下來；哪幾格系統沒把握，也要明白告訴我。

#### 驗收標準（EARS）
1. WHEN `ocr_raw.text` 中存在可辨識為條款的句段（以「第N條」「一、」「（一）」與換行**粗切**，含金額、期間、或「不得／應／須／付清／逾期／滯納」等義務語），THE SYSTEM SHALL 原樣放入 `unmapped_clauses[]`，**除非**該段整段落在某個已映射欄位的 `raw` 內，或拿掉所有已映射片段後剩餘文字已無任何條款訊號（v3 ②-2：部分重疊 ⛔ 不得整條刪——「應於每月五日前繳納租金，逾期按日加收滯納金」不因 `cycle_date` 吸收了「每月五日前」而消失）；⛔ 不求切分精準，LIFF 端 SHALL 可編輯該清單。
2. THE SYSTEM SHALL NOT 對 `unmapped_clauses[]` 的內容做摘要、改寫或翻譯。
3. WHEN 條款涉及寵物、吸菸、訪客等 JGB 無欄位的主題，THE SYSTEM SHALL 一律走 `unmapped_clauses[]`，⛔ 不得映射到 `smoke_detector` 等語義不同的欄位。
4. THE SYSTEM SHALL 為每個欄位值物件帶 `confidence`：`source = ocr` 者取 DocuMind `field_confidences`；`source = derived` 者繼承來源欄位的信心度；`source = absent` 者為 `null`。
5. THE SYSTEM SHALL 回傳 `needs_confirmation[]` ＝ DocuMind 各頁聯集 ∪ Requirement 2.3 衝突欄位 ∪ Requirement 4.4 必填缺漏 ∪ Requirement 6 押金待選，去重且順序穩定。
6. WHEN DocuMind `needs_review = true`，THE SYSTEM SHALL 回傳 `status = draft` 並在 `provenance` 透傳 `review_item_id`，⛔ 不得因欄位齊全而升為 `ready`。

### Requirement 8：租約特有欄位的第二段抽取（⛔ **作廢**——D1 於 2026-09-04 定案 A）

> 以下條文保留供追溯，⛔ 不再是驗收標準；任何任務不得引用 8.x。取代者：Requirement 4.6。

**使用者故事**：作為房東，DocuMind 抽不到「每月幾號繳」「幾個月繳一次」「提前解約預告期」，我希望系統從全文再讀一次，但要標明那是它讀的、不是它猜的。

#### 驗收標準（EARS）
1. WHEN Requirement 4 映射後 `cycle_date`／`cycle`／`deposit_type`／`early_termination_days` 任一為 `absent`，THE SYSTEM SHALL 以 `pages[].ocr_raw.text` 全文對缺漏欄位做一次 LLM 抽取（gpt-4o-mini，temperature ≤ 0.3，JSON 輸出，⛔ 不得改用更弱的 fallback 模型）。
2. THE SYSTEM SHALL 對 LLM 抽取結果的每個值標 `source = llm_extracted`，`confidence` 取 min(LLM 自評, 該頁 `ocr_raw.confidence`)，⛔ 不得高於 OCR 頁級信心度。
3. THE SYSTEM SHALL 要求 LLM 回傳每個值的 `evidence_span`（原文片段）；缺 `evidence_span` 或 `evidence_span` 不在 `ocr_raw.text` 中者，該值 SHALL 降為 `absent`。
4. THE SYSTEM SHALL NOT 讓 LLM 產出 `rent`、`deposit_amount`、`date_start`、`date_end` 的**數值**（金額與日期只能來自 Requirement 5 的決定性換算）；LLM 只准回**原文片段**，數值由規則層換算。
5. WHEN LLM 呼叫失敗或逾時（≤ 8 s），THE SYSTEM SHALL 回傳不含 `llm_extracted` 的結果並在 `provenance.notes` 記錄，⛔ 不得整體 500。
6. THE SYSTEM SHALL 將此段 LLM 用量計入 `usage_events`（token／成本），與既有計量同源。

### Requirement 9：回應契約、計量與可觀測

**使用者故事**：作為 line-bot 開發者，我要一個形狀固定、鍵集合可預期的回應，好讓 LIFF 直接綁欄位；作為業主，我要看得到這個端點被誰打了幾次、花了多少。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以 Pydantic 定義回應模型：`status`（`draft`｜`ready`）、`document_type`、`fields{}`（每欄為欄位值物件，含 `jgb_value` 與該欄自己的 `conflicts[]`）、`needs_confirmation[]`、`unmapped_clauses[]`、`provenance{}`；`fields` 的鍵集合對同一 `document_type` **恆定**。⚠️ v3 修正（2026-09-03 獨立驗證 N3）：衝突**落在各欄位值物件內**，⛔ 不另設頂層 `conflicts{}`——同一欄位的值與其落選值放一起，LIFF 反白時不必跨結構對照。
2. THE SYSTEM SHALL 在 `provenance` 回傳 `document_type`、`total_pages`、`needs_review`、`review_item_id`、`documind_estimated_cost`（＝DocuMind `stats.estimated_cost` 的扁平投影）、`mapping_version`、`notes[]`。⚠️ v3 修正：鍵名由 `documind_stats.estimated_cost` 改為扁平 `documind_estimated_cost`（N3）。
3. THE SYSTEM SHALL 每次呼叫寫一筆 `usage_events`（`processing_path = ocr_mapping`、`vendor_id`、`role_id`、`duration_ms`、LLM 用量若有），沿用 `usage_metering` 既有欄位，⛔ 不新增表。⚠️ 既有計量 middleware 只認 `/api/v1/message`（`app.py` 符號 `usage_metering_middleware`），本端點的落點方式（擴 middleware 路徑集合 vs 端點內自行 `begin`／出場落事件）由 design 決定，⛔ 兩者不得並存造成雙落點。
3b. WHEN 映射過程拋出未預期例外，THE SYSTEM SHALL 回 500 並帶 `error_code = MAPPING_ERROR`（⛔ 不含個資），且該次呼叫 SHALL 仍以 `status = error` 落 `usage_events`（v3 ②-3）。
3a. THE SYSTEM SHALL 沿用 `/api/v1/message` 的內部流量規則：請求帶 `session_id` 且前綴命中 `usage_metering.INTERNAL_RULES` 者標 `is_internal`；未帶 `session_id` 者視為外部流量。
4. THE SYSTEM SHALL 在 P95 < 2 s 內回應（純規則；v4：Requirement 8 已作廢，無 LLM 路徑）。
5. THE SYSTEM SHALL NOT 將 `ocr_raw.text`、所有權人姓名、身分證字號等個資寫入 `print()` 日誌或 `usage_events`；日誌只准記欄位名與信心度。

### Requirement 10：可測性與收案

**使用者故事**：作為維護者，我要用 DocuMind 的真實回應當測資，證明每一條規則都有正反例，而且被驗過的規則不會被下一次修改悄悄弄壞。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 有單元測試覆蓋 Requirement 3–7 的每一條驗收標準，每條至少一組正例＋一組反例，並以 `@pytest.mark.req("documind-ocr-mapping:N.M")` 標記。
2. THE SYSTEM SHALL 以 DocuMind 提供的樣本回應（謄本 4 頁）與至少一份真實合約回應為 fixture；fixture 中的個資 SHALL 去識別化。⚠️ 真實回應由 line-bot 團隊提供（本案 ⛔ 不呼叫 DocuMind）；取得前，Requirement 10.4 與驗收矩陣第 3、4 項**暫掛**，⛔ 不得以文件樣本充當真實 e2e。
3. THE SYSTEM SHALL 有突變控制測試：把 `deposit_amount ÷ rent` 推算邏輯注入後，Requirement 6.5 的測試必須轉紅。
4. WHEN 收案，THE SYSTEM SHALL 以真實 DocuMind 回應（非 mock）經正式端點跑一次 e2e，逐欄與人工判讀對照，`needs_confirmation` 命中率與漏報數落檔於 `.kiro/specs/documind-ocr-mapping/`。
5. THE SYSTEM SHALL 在容器內（Python 3.11）跑測試，遵循 `testing-code.md` 的分層與 marker 規約。

## 非功能約束

- **無狀態**：同一請求重送得到逐位元相同的回應（v4：無 LLM 路徑，Requirement 8 已作廢）。
- **不出境個資**：chatai 本端點不把任何 OCR 內容送往 LLM 或第三方（v4：Requirement 8 已作廢）。
- **上線前置（範圍外但擋上線）**：DocuMind 加認證與 IP 白名單；line-bot 端串列化呼叫；兩者未滿足前本端點只准在內部前綴（`backtest_session_`）下驗證。

## 驗收矩陣（收案時逐項打勾）

| # | 項目 | 證據形式 |
| --- | --- | --- |
| 1 | ✅ Requirement 1–7、9 單元測試全綠，含每條正反例 | `make test-unit`：2176 過（既有紅 `test_verdict_ruler_req` 非本案）；ocr_mapping 12 檔 130＋ 測試 |
| 2 | ✅ Requirement 6.5 突變控制會紅 | `test_deposit_rule_req.py`：÷rent／×rent 兩向注入皆被 `assert_deposit_exclusive` 擋下＋正對照 |
| 3 | 真實謄本回應 e2e：五欄逐欄對照人工判讀 | 對照表落檔 |
| 4 | 真實合約回應 e2e：§7.2 每欄 `source` 與 `needs_confirmation` 對照人工判讀 | 對照表落檔 |
| 5 | ✅ `usage_events` 有 `processing_path = ocr_mapping` 記錄且無個資 | `tests/integration/ocr_mapping/test_metering_db_req.py`（RUN_INTEGRATION=1 真 DB 通過）；`SELECT processing_path,is_internal FROM usage_events WHERE session_id LIKE 'backtest_session_ocrint_%'` |
| 6 | ✅ D1／D2／D3 登記 `.claude/DECISIONS.md` | DSP-004／005／006（來源＝代理，**待業主裁**） |
