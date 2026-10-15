# 站內幫手：請 JGB 開／改的 API（2026-10-15，已對碼 jgb2 master）

> 給 JGB 工程團隊。依據：jgb2 `master`（`a0e0020ac7`，本機 `dev1`）的 `routes/api.php` `external/v1` 群組與 `app/Http/Controllers/External/*`、`Internal/EstateWriteController`、`Internal/ContractWriteController`、`app/Support/VisibleScope.php`、`app/Http/Middleware/ExternalApiAuth.php`／`ExternalViewerScope.php`、`app/Repair.php`、`app/Services/RepairService.php`。
> 原則：**能擴充既有端點就不另開新路徑**；格式一律照抄既有 `external/v1`。
> 現況：AIChatbot 已上線並接 www。下列功能在 JGB 開放前，我方**不發請求**、回使用者「目前還不支援」。

## 0. 沿用既有 `external/v1` 的格式（新增或擴充都照這個）

| 項目 | 既有慣例（照抄） | 出處 |
|---|---|---|
| 認證 | header `X-API-Key`；每把 key 有 resource／action 權限、限流 429、稽核 log | `ExternalApiAuth` |
| 團隊 | `role_id` 必填（缺 ⇒ 400「role_id 為必填參數」） | 各 External controller |
| 成員可見範圍 | `viewer_user_id`：由 `external_viewer` 解析，controller 以 `queryThisUser`／`VisibleScope` 圈定 | `ExternalViewerScope`、`VisibleScope` |
| 成功（單筆） | `{success:true, data:{…}}`；建立成功 HTTP 201，`data` 含 `id` | `RepairApiController@store` |
| 成功（列表） | 頂層同層：`{success:true, mapping:{…}, data:[…], pagination:{current_page, per_page, total, total_pages, has_more}}` | `BillApiController@index` |
| 分頁 | `page`、`per_page`（預設 50、上限 200） | `DEFAULT_PER_PAGE`／`MAX_PER_PAGE` |
| 錯誤 | `{success:false, error:{code, message}}`，HTTP 狀態＝`error.code`；驗證失敗 400 | `errorResponse`、`RepairApiController@store` |
| 日期 | 參數 `YYYY-MM-DD`；帳單、合約的日期欄回整數 `YYYYMMDD` | `formatBill` |
| 排序 | `sort_by`、`sort_direction`（白名單） | 各 index |

**站內幫手額外需要、既有沒有的規則（請 JGB 新增）**：
1. **越權與不存在同一回應**：目前 `repairs/{id}`、`estates/{id}` 越權回 403、不存在回 404（可區分）；`bills/{id}`、`meters/{id}` 已合併成 404。請統一成 404「不存在或無權存取」，且回應時間不可區分。
2. **冪等**：寫入 body 帶 `idempotency_key`（JSON body 欄位），同鍵重送回同一筆、不重複建立。jgb2 目前沒有任何冪等機制（`app/` grep `idempotency` 0 筆）。
3. **寫入的成員身分**：寫入時帶登入成員，JGB 驗 (a) 成員屬 `role_id`、(b) 成員有對應能力、(c) 引用的物件／合約該成員看得到。既有寫入（`POST /repairs`）三項都沒驗，開單人由物件決定。參數名請 JGB 定：讀取慣例是 `viewer_user_id`，我方目前寫入 body 送 `user_id`，**JGB 選一個，我方配合改**。
4. **歸屬欄位不得由呼叫端指定**：body 帶 `team_id`、`owner_*`、`vendor_id`、`to_user_id`、`agent_user_id`、`created_by` ⇒ 拒絕。既有端點對未知欄位一律**靜默忽略**，請至少對歸屬欄位明確拒絕。

## 1. 擴充既有讀取端點（統計三項：不必開新路徑）

### #16 未收帳單（站內幫手 (4)）→ 擴充 `GET /bills`
- 既有已有：`role_id`、`status`（單值）、`month=YYYY-MM`、`viewer_user_id` 圈定、分頁、排序。
- **請加**：
  1. `status` 多值（例 `status=2,8`），一次取「未收」。**「未收」是否含 8 待對帳請 JGB 答。**
  2. 到期日區間 `date_expire_from`／`date_expire_to`（`YYYY-MM-DD`）——「逾期未收」需要 `date_expire < 今天`，既有做不到。
  3. 頂層 `summary:{count, total_amount}`（全部符合者的合計；`data` 維持陣列分頁）。
- 若不加 `summary`，我方會翻頁自行加總；但「逾期」一定要有區間篩選。

### #17 執行中修繕（站內幫手 (5)）→ 擴充 `GET /repairs`
- 既有已有：`role_id`、`status`（單值）、`estate_id`、`apply_after`／`apply_before`、分頁、排序。
- **請加**：
  1. `status` 多值（執行中＝1 申請中、2 安排修繕、16 完成修繕；**請確認此定義**）。
  2. `viewer_user_id` 圈定（既有 `GET /repairs` 不吃；`VisibleScope::estateIdsQuery` 已寫好、註解寫「供 repairs 圈定」，接上即可）。
  3. （建議）站內幫手呼叫時不回 `user_phone`、`user_email`、`to_user_phone`、`to_user_email`；若不改，我方端丟棄。

### #18 N 個月內到期合約（站內幫手 (8)）→ 擴充 `GET /contracts/status-overview`
- 既有已有：`role_id`、`viewer_user_id` 圈定、固定 `active=1`、`is_newest=1`、分頁。
- **請加**：`date_end_from`／`date_end_to`（`YYYY-MM-DD`）、排除 `is_history=1`。`days_left` 可不加（我方自算）。**請確認篩選條件與畫面「即將到期」一致。**

## 2. 既有讀取端點補成員過濾（#24）

| 端點 | 現況 | 請改 |
|---|---|---|
| `GET /bills`、`GET /contracts/status-overview` | 已吃 `viewer_user_id` | 不用改 |
| `GET /repairs`、`GET /estates`、`GET /meters`、`GET /recharge-accounts` | 不吃 `viewer_user_id`（只看 `role_id` 或 key 白名單） | 帶 `viewer_user_id` 時依成員可見範圍圈定（可重用 `VisibleScope`） |
| `GET /estates/{id}`（已存在） | 只回刊登中（`active=1`、`is_open=1`）；不吃 `viewer_user_id`、不驗 `role_id`；越權 403／不存在 404；結果快取 300 秒 | (a) 帶 `role_id`＋`viewer_user_id` 時回該成員看得到的物件，**含已出租、下架**；(b) 越權與不存在同一句 404；(c) 這條路徑不快取（建合約前要即時狀態） |

## 3. 新增寫入端點（建物件／合約／手動帳單）

⚠️ jgb2 既有的 `internal/v1`、`agent/v1` 的 `POST /estates`、`POST /contracts`、`POST /bills` **不能沿用**：註解與程式都是產測試資料用（物件欄位 `buildMockAttributes` 隨機、承租人隨機姓名與 `mock.tenant.*@example.com`、`POST /bills` 是 `GenerateMockBills` 排程週期租金帳單、無合約歸屬檢查）。請在 `external/v1` 新做，內部呼叫既有的正式方法。

### #19 建立物件（站內幫手 (9)）→ 新增 `POST /api/external/v1/estates`
- 內部可沿用 `Estate::createEstate`；**不要**用 `buildMockAttributes`。
- 我方送：`role_id`、成員身分（見 §0-3）、`idempotency_key`；必填 `title`、`city`、`district`（**名稱**，請以既有 `Address::getCityId`／`getDistrictId` 解析，對不到回 400）、`address`、`use_for`（`residential`｜`business`｜`parking_space`）；選填 `space_type`、`building`、`room_count`、`size`、`rent`、`floor`。沒給的欄位不要補值。
- 請回答：`title` 上限（內部端點 100，我方目前限 60，可放寬照 JGB）；`use_for`、`space_type`、`building` 的值域（`building` 內部用英文代碼 condo／apartment／townhouse）；「台」「臺」是否視同；新物件初始 `status`（內部為 `ESTATE_READY`、`is_open=0`）。
- 回應：201 `{success:true, data:{id, …}}`。

### #20 建立合約（站內幫手 (10)）→ 新增 `POST /api/external/v1/contracts`
- 內部可沿用 `Contract::createContract`；承租人用使用者給的真實資料，**不要**隨機快照、**不要** `GenerateMockBills`。
- 我方送：`role_id`、成員身分、`idempotency_key`；必填 `estate_id`、`date_start`、`date_end`（`YYYY-MM-DD`）、`rent`，`to_user_email`／`to_user_phone` 至少一個；選填 `deposit_amount`、`title`。
- 請回答：押金欄位——我方的 `deposit_amount` 是**金額**，內部端點的 `deposit` 是**月數**（預設 2），正式欄位用哪個；新合約初始 `status`／`bit_status`；物件屬他團隊時請回 404（內部端點回 422「此物件不屬於該團隊」，可被用來區分）。
- 回應：201 `{success:true, data:{id, …}}`。

### #21 建立手動帳單（站內幫手 (11)）→ 新增 `POST /api/external/v1/bills/manual`
- 照網頁 `BillController` 的「新增帳單」流程（`Bill::BILL_TYPE_CREATE`＝3），同步建立、回帳單 `id`。
- 我方送：`role_id`、成員身分、`idempotency_key`；必填 `contract_id`、`title`、`total`、`date_expire`（`YYYY-MM-DD`）；選填 `sub_title`。
- 請回答：網頁路徑要求合約已簽署（`bit_status & CONTRACT_SIGNED`）——外部端點是否同樣要求？（若是，#20 剛建好的草稿合約不能立刻開帳單，使用者會被擋，我方要先知道）；初始 `status`；是否需另外「發送」。
- 回應：201 `{success:true, data:{id, …}}`。

## 4. 修改既有寫入端點

### #22 修繕單附照片 → 改 `POST /api/external/v1/repairs`
- 現況：`broken_photos` 是**網址字串陣列**（每筆 `url` 規則、最多 10），程式只存 `basename`、不抓檔不上傳；`user_id`、`idempotency_key` 未宣告 ⇒ 被忽略；驗證失敗回 400。
- ⚠️ **我方目前有照片時送的是物件陣列** `[{filename, content_type, size, sha256}]` ⇒ 對現行端點會 400。**我方待改**：JGB 定案前，接真 JGB 時不送 `broken_photos`（目前程式仍會送；JGB 尚未接上照片網域，所以目前不會有照片進來，文字報修不受影響）。
- 請 JGB 定照片怎麼交：(a) `multipart/form-data`；(b) **預簽上傳＋JGB 自己的識別碼（我方建議）**——照片本來就在 JGB 的專用上傳網域，我方只回傳識別碼。另請提供**專用上傳網域名稱**（我方抓圖白名單用，不可是 www 或 API 主機）。
- 請加：成員身分驗證（§0-3）、冪等（§0-2）。

### #23 改帳單到期日 → 請給正式路徑
- 我方目前的 `PATCH /agent/v1/bills/{id}` **在 jgb2 master 與 preview 的 `routes/api.php` 都查不到**。請確認它在哪個環境／分支，或改給正式路徑（建議 `PATCH /api/external/v1/bills/{id}`，只准改 `date_expire`，套用 §0 的成員身分與冪等）。

## 5. 請 JGB 修正的既有問題

### 修繕 `emergency_status` 的對外 mapping 標反了
- 網頁與服務層：**2＝緊急、1＝非緊急**（`RepairService` 的對照表；`RepairController` 的 `is_urgent` 判斷 `=== Repair::EMERGENCY_STATUS`，也就是 2；表單 `is_urgent=true` 寫入 2）。
- 對外 API：`RepairApiController::getMapping` 寫成 1→緊急、2→非緊急，與網頁相反；`app/Repair.php` 常數註解也寫反（`EMERGENCY_NON_STATUS = 1; // 緊急`）。
- 我方以網頁行為為準（2＝緊急）。**請 JGB 修正 `getMapping` 與常數註解**，或回覆以哪個為準。

## 6. 請 JGB 回答（彙整）

| # | 問題 | 會不會擋上線 |
|---|---|---|
| #16 | 「未收」是否含 8 待對帳 | 否（影響數字） |
| #16～#18 | 同意以「擴充既有端點」方式做嗎？參數命名可照 JGB 慣例調整 | 是 |
| #17 | 執行中＝1／2／16 是否正確 | 否 |
| #18 | 到期篩選是否與畫面「即將到期」一致 | 否 |
| #19 | `title` 上限、`use_for`／`space_type`／`building` 值域、「台」「臺」、初始狀態 | 否 |
| #20 | 押金欄位（金額或月數）、初始狀態 | 是 |
| #21 | 開手動帳單是否要求合約已簽署；初始狀態；是否需另外發送 | 是 |
| #22 | 照片上傳方式 (a)／(b)；專用上傳網域 | 是（照片） |
| #23 | 改到期日的正式路徑 | 是（延長到期日功能） |
| §0 | 寫入成員身分參數名（`viewer_user_id` 或 `user_id`）；越權統一 404；冪等 | 是 |
| §5 | `emergency_status` 以網頁（2＝緊急）為準並修 API mapping | 是 |

## 7. 我方要配合改的（AIChatbot 內部，JGB 不必做）

- #16～#18 改呼叫擴充後的既有端點（目前程式呼叫的是 `bills/summary/unpaid`、`repairs/in-progress`、`contracts/expiring` 三條新路徑與 `data` 物件形狀），JGB 定案後改呼叫端與解析。
- 寫入成員身分參數名照 JGB 定案調整。
- 接真 JGB 時暫不送 `broken_photos`（**尚未實作**；目前 JGB 尚未接上照片網域，實際不會觸發），待 #22 定案。
