# 研究：合約基底架構（jgb2 程式盤查 ground-truth）

> 來源：真實盤查 `/Users/lenny/jgb/project/jgb_interrogation/jgb2`（Laravel）。
> 用途：作為「合約」領域的**系統脈絡（基底架構知識）**的事實依據；供 R4.1 混合 grounding 注入。
> 原則：知識由真實碼推導，非臆測；下列標「⚠️修正」處為先前 mock 假設與真碼不符、需以真碼為準。

## 1. 合約狀態：`status`（單一現值）vs `bit_status`（累積位元遮罩）

**⚠️修正（重要）**：兩者不同概念，共用同一組 12 常數值。
- `status` = 合約**當前所在的單一階段**（值為下表其一）。
- `bit_status` = **累積位元遮罩**，記錄合約走過的每個里程碑（加位元；取消時偶爾減位元）。

### 12 狀態常數（`app/Contract.php:38-49`，唯一事實來源）
| 常數 | 值 | 意義（程式註解） |
|---|---|---|
| CONTRACT_READY | 1 | 合約剛建立（待發送合約）|
| CONTRACT_INVITING | 2 | 送出邀請給租客（待租客簽回）|
| CONTRACT_INVITING_NEXT | 4 | 租客已簽（待房東簽名）|
| CONTRACT_SIGNED | 8 | 雙方簽名完成（執行中）|
| CONTRACT_MOVE_IN | 16 | 點交送出，等租客同意（點交＝move-in／交屋）|
| CONTRACT_MOVE_IN_DONE | 32 | 點交完成，租客已同意 |
| CONTRACT_MOVE_OUT | 64 | 點退送出，等租客同意（點退＝move-out／退租）|
| CONTRACT_MOVE_OUT_DONE | 128 | 點退完成，租客已同意 |
| CONTRACT_EARLY_TERMINATION | 256 | 提前解約中 |
| CONTRACT_EARLY_TERMINATION_DONE | 512 | 提前解約已確認 |
| CONTRACT_HISTORY | 1024 | 合約結束（歷史合約）|
| CONTRACT_HISTORY_DONE | 2048 | 合約結束（生命週期結束）|

**⚠️修正**：16/32 是**點交＝交屋（move-in）**、64/128 是**點退＝退租（move-out）**；先前 mock 用詞方向對，但需釐清點交/點退中英對應。

### 階段分組（真碼有兩種）
- **5 桶顯示分組** `getContractToList()` `app/Contract.php:23055-23095`：待發送 / 待租客簽回 / 待房東簽回 / 執行中 / 歷史。
- **4 桶篩選分組** `ContractController::list()` `:2224-2233`：待租客簽回 / 待房東簽回 / 執行中 / 歷史。
- 自然 4 大階段模型：**簽約前（READY→INVITING→INVITING_NEXT）→ 執行中（SIGNED＋點交/點退/提前解約）→ 歷史（HISTORY/HISTORY_DONE）**。
- **⚠️修正**：先前「12 種狀態 4 大階段」概略對，但真碼是 12 常數 + 5桶(顯示)/4桶(篩選) 兩種分組。

## 2. 生命週期流轉與「此刻能做什麼」（gate 條件）

- **點交 `canMoveIn()` `:25018-25047`**：需 `to_user_connect` 且 `bit_status & SIGNED`；已有 MOVE_IN/MOVE_IN_DONE/MOVE_OUT/MOVE_OUT_DONE/HISTORY 則擋；`status==EARLY_TERMINATION` 擋。
- **點退 `canMoveOut()` `:25054-25098`**：`status ∈ {SIGNED, MOVE_IN_DONE, HISTORY, HISTORY_DONE}` 才可；已 MOVE_OUT_DONE 擋；須在 date_start 之後；免註冊租客（is_tenant_registered==0）可在未綁定時點退。
- **提前解約 `canEarlyTermination()` `:25105-25139`**：`status ∈ {SIGNED, MOVE_IN_DONE}` 才可；已 EARLY_TERMINATION(_DONE) 擋；租客需 `allow_early_termination=1`（房東免此限）；續約中(isRenewing)擋。發起方 `early_termination_role_key`：**1=租客、2/3=房東**。`applyEarlyTermination()` 會改 `date_end=early_termination_wish_date_end`（原值存 old_date_end）、加 EARLY_TERMINATION_DONE 位元，並把 status 還原到最高執行階段。
- **續約（父子鏈，father_id）**：`isRenewContract()` `:25333-25338` = father_id 有值且 id≠father_id；`canRenewContract()` `:25306-25326` 需 to_user_connect、bit_status&SIGNED，且非點退/點交中/提前解約中/已過期。付款資訊綁在父約。
- **轉歷史 `:26135-26173`**：依 is_history/is_history_done 加 HISTORY/HISTORY_DONE 位元並設 status。

## 3. status-overview API（合約診斷實際打的端點）

- **路由** `routes/api.php:40` → `External\ContractApiController@index`，`GET /contracts/status-overview`（external-api-key middleware）。
- **參數**：`role_id`**必填**（缺→400）；`user_id`（→to_user_id）；`contract_ids`（逗號→whereIn id）；`keyword`（→`title LIKE %kw%`，跳脫 %/_）；`page`(1)/`per_page`(50，上限200)。
- **基礎過濾**：一律 `active=1 AND is_newest=1`；`id desc`。
- **bit_status**：控制器**不解碼**，原樣回整數 `bit_status`/`status`，另附靜態 `mapping.bit_status` 解碼表（`getMapping()` `:126-144`）。**⚠️注意**：mapping 標籤用詞與 Contract.php 常數註解略有出入（如 mapping「已發送點交」vs 常數「點交送出(等租客同意)」）。
- **回傳欄位**：id, status, bit_status, active, is_history, is_history_done, estate_id, title, city, district, address, currency, rent, deposit_amount, date_start, date_end, allow_early_termination, early_termination_days, is_auto_generate_invoice, to_user_connect, is_tenant_registered, to_user_phone, to_user_email, property_purpose_key, father_id, early_termination_wish_date_end, created_at, updated_at。
- **信封**：`{success, mapping, data[], pagination{current_page, per_page, total, total_pages, has_more}}`。

## 4. 業務規則：違約金 / 滯納金

### 提前解約違約金（PDF 渲染邏輯 `app/Contract.php:7613-7666`, `:6011-6025`）
- 閘門：`allow_early_termination==1`；通知天數 `early_termination_days`＝「一方應於 N 日前通知他方」。
- **`early_termination_penalty_type`**（**⚠️修正：非布林，3 值**）：
  - **0 = 按月數**：金額 = `rent × early_termination_penalty`（≤通知日）或 `rent × early_termination_penalty2`（>通知日）；penalty 欄位存**月數**。
  - **1 = 固定金額**：金額 = `early_termination_penalty_amount` / `_penalty2_amount`（現金）。
  - **2 = 其他/自由文字**：渲染「詳參後文補充條款」，文字存 `early_termination_penalty_other`（2026_05_25 migration）。
- **⚠️修正**：有**兩階**（≤通知日 vs >通知日）：`_penalty(_amount)` 與 `_penalty2(_amount)`。37 個 early_termination_* 欄位已拆到 1:1 衛星表 `ContractLifecycle`（`contract_lifecycle`，2026_06_17 migration，雙寫）。

### 滯納金（`app/Contract.php:16129-16140`, `:1026-1029`）
- 閘門：`enable_late_fee==1`。欄位承自房東 Role：`enable_late_fee`, `calc_late_fee_buffer_days`, `late_fee_percent`。
- 規則字串：「緩衝 [calc_late_fee_buffer_days] 天，延遲金計算 [late_fee_percent] %」＝逾期超過緩衝天數後，按 X% 收滯納金。

## 5. 關鍵欄位語義

- **title**：顯示標題，也是 status-overview 的 keyword 搜尋鍵（LIKE）。**⚠️同物件多份合約 title 相同 → 候選需帶期間/狀態辨識。**
- **estate_id**：物件 FK（App\Estate）；`hasOneProcessing()` 用以偵測同物件重疊的有效合約。
- **date_start/date_end**：租期（Ymd）；date_end 會被 applyEarlyTermination 改（原值存 old_date_end）。
- **rent**：月租；月數型違約金基數。**deposit_amount**：押金。
- **property_purpose_key**（`Contract.php:34-35`）：**1=一般住宅、2=社會住宅**；承自房東 role，驅動社宅專屬分支。
- **father_id**：續約父子鏈；isRenewContract＝father_id 有值且 id≠father_id；付款綁父約。
- **is_history/is_history_done**：生命週期旗標，對應 HISTORY(1024)/HISTORY_DONE(2048)。
- **active / is_newest**：active＝軟可見；外部 API 以 `active=1 AND is_newest=1` 取續約鏈當前列。

## 設計探索與決策（design discovery log）

> 探索類型：Light（Extension）。整合點盤查見 gap-analysis.md。

### 關鍵發現（形塑設計）
- `synthesize_presales_answer(grounding, ctx, system_md, …)` **本就同時吃 grounding 與 system_md** → 「混合 grounding」可由 per-領域 system_md 達成，`_ground_by_api` 零改（設計 D3 選項 A）。
- `load_rules(db_pool, role)` 已是「per-角色查 target_user + per-role 快取」的成熟範本 → `get_system_context` 照抄即可 per-領域化（D2）。
- `get_system_context` 現為全域單例（查 `category='系統脈絡'` LIMIT 1、單槽快取）→ 主改造點；`category_config.parent_value` 已存在 → 母分類組織零 schema。
- 真 jgb2 API（role_id=20151 回 50 筆）證實：通用詞「套房」回 50、完整名回 3 同名 → 候選須帶區別欄位 + 大 N 上限（D4）。`jgb_response_formatter` 已能逐位元解 bit_status。

### 決策摘要
- D1 領域＝母分類 + 慣例（不建表）｜D2 領域鍵＝target_user｜**D3 混合走 system_md 常駐（選項 A）**｜D4 label_fields + candidate_cap｜D5 全向後相容預設。
- 待設計驗證確認：system_md 每輪注入的字元預算（合約架構需精簡）；如超標則 fallback 至 knowledge_ref（選項 B）。

## 主要檔案索引
`app/Contract.php`（常數 :38-83、生命週期 :25018-25360、轉歷史 :26135-26173、違約金 PDF :7613-7666）、`app/Http/Controllers/External/ContractApiController.php`、`routes/api.php:40`、`app/ContractLifecycle.php`、`app/Http/Controllers/Internal/ContractWriteController.php:194-232`、`app/Http/Controllers/ContractController.php:2224-2233`、`app/Estate.php:50-51`。
