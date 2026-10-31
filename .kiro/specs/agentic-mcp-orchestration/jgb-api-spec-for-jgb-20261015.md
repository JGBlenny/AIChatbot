# 站內幫手：請 JGB 開／改的 API（2026-10-15，已對碼 jgb2 master）

> 給 JGB 工程團隊。依據：jgb2 `master`（`a0e0020ac7`，本機 `dev1`）的 `routes/api.php` `external/v1` 群組與 `app/Http/Controllers/External/*`、`Internal/EstateWriteController`、`Internal/ContractWriteController`、`app/Support/VisibleScope.php`、`app/Http/Middleware/ExternalApiAuth.php`／`ExternalViewerScope.php`、`app/Repair.php`、`app/Services/RepairService.php`。
> 原則：**能擴充既有端點就不另開新路徑**；格式一律照抄既有 `external/v1`。
> 現況：AIChatbot 已上線並接 www。JGB staging（`8ff2f7b8e7`，2026-10-30 查）已開 #19～#23，以 staging 為準算開放（DSP-132）；master 還沒有這些端點。我方的呼叫端已寫好並在 staging 實測（2026-10-31，團隊 20151，五項寫入各成功一次）：開關 `JGB_WRITE_WIRING` 為 `on` 且 `JGB_API_BASE_URL` 主機是 `staging.jgbsmart.com` 時才送；連 www 時開關不生效，這些功能**不發請求**、回使用者「目前還不支援」（master 沒有這些端點）。

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
| `GET /bills` | 已吃 `viewer_user_id` | 不用改 |
| `GET /contracts/status-overview` | 已吃 `viewer_user_id`，但團隊擁有者身分不限團隊 | 見 §5「團隊擁有者帶 `viewer_user_id` 查合約不限團隊」 |
| `GET /repairs`、`GET /estates`、`GET /meters`、`GET /recharge-accounts` | 不吃 `viewer_user_id`（只看 `role_id` 或 key 白名單） | 帶 `viewer_user_id` 時依成員可見範圍圈定（可重用 `VisibleScope`） |
| `GET /estates/{id}`（已存在） | 只回刊登中（`active=1`、`is_open=1`）；不吃 `viewer_user_id`、不驗 `role_id`；越權 403／不存在 404；結果快取 300 秒 | (a) 帶 `role_id`＋`viewer_user_id` 時回該成員看得到的物件，**含已出租、下架**；(b) 越權與不存在同一句 404；(c) 這條路徑不快取（建合約前要即時狀態） |

## 3. 新增寫入端點（建物件／合約／手動帳單）

⚠️ jgb2 既有的 `internal/v1`、`agent/v1` 的 `POST /estates`、`POST /contracts`、`POST /bills` **不能沿用**：註解與程式都是產測試資料用（物件欄位 `buildMockAttributes` 隨機、承租人隨機姓名與 `mock.tenant.*@example.com`、`POST /bills` 是 `GenerateMockBills` 排程週期租金帳單、無合約歸屬檢查）。請在 `external/v1` 新做，內部呼叫既有的正式方法。

### #19 建立物件（站內幫手 (9)）→ 新增 `POST /api/external/v1/estates`
- 內部可沿用 `Estate::createEstate`；**不要**用 `buildMockAttributes`。
- 我方送：`role_id`、成員身分（見 §0-3）、`idempotency_key`；必填 `title`、`city`、`district`（**名稱**，請以既有 `Address::getCityId`／`getDistrictId` 解析，對不到回 400）、`address`、`use_for`（`residential`｜`business`｜`parking_space`）；選填 `space_type`、`building`、`room_count`、`size`、`rent`、`floor`。沒給的欄位不要補值。
- staging 程式的答案（`8ff2f7b8e7`，`External\EstateController@store`；DSP-132）：`title` 1～60 字；`use_for` 只收三值，另依團隊設定擋「此團隊不支援這個用途」；`space_type`、`building` 的值域取 JGB 設定檔 `config/estate.php`；新物件 `status=1`（未刊登）、`is_open=0`。另有關卡：訂閱無效 403、物件數達方案上限 422。仍待 JGB 回答：「台」「臺」是否視同（由 `Address::getCityId` 解析，未讀到）。
- 回應：201 `{success:true, data:{id, …}}`。

### #20 建立合約（站內幫手 (10)）→ 新增 `POST /api/external/v1/contracts`
- 內部可沿用 `Contract::createContract`；承租人用使用者給的真實資料，**不要**隨機快照、**不要** `GenerateMockBills`。
- 我方送：`role_id`、成員身分、`idempotency_key`；必填 `estate_id`、`date_start`、`date_end`（`YYYY-MM-DD`）、`rent`，`to_user_email`／`to_user_phone` 至少一個；選填 `deposit_amount`、`title`。
- staging 程式的答案（`External\ContractController@store`）：`deposit_amount` 是金額（寫入 `deposit_type=1` 固定金額）；物件不存在、屬他團隊或看不到一律 404；建立時不設承租方（`to_user_id`、`to_role_id`）、不寄邀請、不產帳單。另有關卡（皆 422，訂閱無效 403）：合約數達方案上限、企業房東未填公司電話、操作成員未綁手機、車位物件、物件必填欄位不完整、物件擁有者不存在、物件有效合約達 10 份。仍待 JGB 回答：新合約初始 `status`／`bit_status`（程式內看不到明文賦值）。
- 回應：201 `{success:true, data:{id, …}}`。

### #21 建立手動帳單（站內幫手 (11)）→ 新增 `POST /api/external/v1/bills/manual`
- 照網頁 `BillController` 的「新增帳單」流程（`Bill::BILL_TYPE_CREATE`＝3），同步建立、回帳單 `id`。
- 我方送：`role_id`、成員身分、`idempotency_key`；必填 `contract_id`、`title`、`total`、`date_expire`（`YYYY-MM-DD`）；選填 `sub_title`。
- staging 程式的答案（`External\BillController@storeManual`）：不看簽署狀態，但合約要已有承租方（`to_role_id`），沒有回 422「此合約尚未綁定承租方，無法建立帳單」。承租方通常在承租人接受邀請或簽約後才有，所以 #20 剛建、未邀請的合約開不了手動帳單。新帳單 `status=1`（待發送），不發送、不通知，要發送得在 JGB 網頁操作。`title` 不得是保留品項名。
- 回應：201 `{success:true, data:{id, …}}`。

## 4. 修改既有寫入端點

### #22 修繕單附照片 → 改 `POST /api/external/v1/repairs`
- master 現況：`broken_photos` 是**網址字串陣列**（每筆 `url` 規則、最多 10），程式只存 `basename`、不抓檔不上傳；`user_id`、`idempotency_key` 未宣告 ⇒ 被忽略；驗證失敗回 400。
- 照片由使用者的瀏覽器直接傳到 AIChatbot（接口文件 §7），位元組在我們這邊，所以採 **(a) `multipart/form-data`**：請 `POST /api/external/v1/repairs` 也接受 `multipart/form-data`。
  - 原有的文字欄位照舊，放在同名的表單欄位。
  - 照片放在 `broken_photos[]`，multipart 時每筆是一個檔案。JSON 送網址字串的舊用法可以保留。
  - 我們送出前，照片一律重新編碼成 `image/jpeg`，並去掉 EXIF 和 GPS。每張修繕單最多 10 張，每張 ≤ 5,000,000 bytes。檔名由我們產生，格式是 `photo-N.jpg`。staging 的上限相同：≤10 張、每張 ≤5,000,000 bytes、內容須為 JPEG／PNG。
  - 請 jgb2 收下照片、掛到這張修繕單，回應格式照舊。jgb2 也請自己驗一次型別；提供照片時加上 `X-Content-Type-Options: nosniff`。
- 本系統現況：呼叫端已改接（開關生效時以 multipart 送 `broken_photos[]`，照片位元組取自確認卡綁定的暫存檔、送出前重算 `sha256` 對卡上值），2026-10-31 在 staging 實測一次成功；開關不生效時不送照片，文字修繕單照常送。
- 請加：成員身分驗證（§0-3）、冪等（§0-2）。同一個冪等鍵重送時，照片不能重複掛。
- JGB 不用提供專用上傳網域、簽章網址，也不用回頭抓我們的任何網址。

### #23 改帳單到期日 → `PATCH /api/external/v1/bills/{id}`
- staging 已開（`External\BillController@updateDueDate`），只改 `date_expire`。本系統現況：呼叫端已改接這條路徑（開關生效時），body 只送 `date_expire`、`role_id`、`viewer_user_id`、`idempotency_key`，`bill_id` 須純數字；2026-10-31 在 staging 實測：待發送帳單改到期日成功一次，非待發送帳單回 422「只有待發送的帳單可以修改到期日」，我方換成固定句回客人、沒有寫入。

### 本系統收到拒絕與逾時時怎麼處理（#19～#23 共用）
- 拒絕：只有 `(端點樣板, HTTP 狀態碼, 訊息全文)` 逐字等於我方白名單時，才換成固定句回客人（全文取自 staging `544e8592eb` 各 controller 的 `MSG_*` 常數與 `RepairController::store` 的兩句 400）；請 JGB 改這些訊息文字前先通知我方，否則會落到「這筆操作目前無法執行」。白名單外 4xx、金鑰層錯誤、404 一律同一句，JGB 原文不轉給客人。
- 結果未確認：逾時、5xx、送出後連線錯誤、2xx 非 JSON 或缺 `data.id`，我方回「結果未確認，請到 JGB 畫面確認是否已建立，再決定要不要重送」，不自動重送。寫入逾時 JSON 30 秒、multipart 60 秒。
- 冪等：我方送的 `idempotency_key` 是確認碼；同一張卡重按由我方回同一份結果、不再發請求（staging 實測五項重按皆 0 次新請求）。JGB 端同鍵重送是否不重複建立**未實測**（我方不會重送同鍵），見 §6 §0 列。

## 5. 請 JGB 修正的既有問題

### 團隊擁有者帶 `viewer_user_id` 查合約不限團隊（資安，擋上線）
- `GET /contracts/status-overview`（`External\ContractController@index`）：有 `user_data`（帶 `viewer_user_id`）時走 `Contract::queryThisUser($query, $userData)`，**不再加** `where('role_id', $roleId)`；沒帶時才 `where('role_id', $roleId)`。
- `app/Models/Contract.php` `queryThisUser` 的 `roleType === 'owner'` 分支沒有任何範圍條件（`where('user_id'…)` 是註解）；`tenant` 分支只限 `to_user_id`（與狀態下限），也沒有 role 條件；`biglandlord`、`agent` 分支都有。`UserData::getRoleTypeByRoleUser` 在 `$role->user_id == $user->id` 時判為 `owner`。
- 網頁端不受影響：各呼叫點先自加 role 條件再呼叫（`ContractController` 中 `->where($searchRoleIndex,$roleId)` 後接 `Contract::queryThisUser`）。
- 結果：團隊擁有者透過對外 API 查合約，會拿到其他團隊的合約（含承租人個資）；租客身分會拿到這位租客與其他房東的合約。
- `app/Support/VisibleScope.php` `contractIdsQuery` 同樣只呼叫 `Contract::queryThisUser`、不加 role 條件；目前 `External/*` 沒有呼叫點，建議一併修。
- `External\BillController`（及經 `VisibleScope::billIdsQuery` 圈定的 `PaymentController`、`InvoiceController`）：`Bill::queryThisUser` 的 `owner`、`agent`、`biglandlord` 分支都加 `owner_role_id`，不受影響；`tenant` 分支改以 `issue_target_role_id` 圈定，是否跨團隊未查。
- 依據：讀碼，jgb2 `origin/master` `bb217ebc6a`（2026-10-28）；正式機 www 部署版即 `bb217ebc6a`（2026-10-28 唯讀查詢），這段程式在線上。未實跑重現。JGB 已開單 #13404266981。
- **請 JGB 修正**：`index` 不論有無 `user_data`，一律先 `where('role_id', $roleId)`，再交 `queryThisUser` 圈成員範圍。

### 經 `POST /estates` 新建的物件，列表查不到
- `GET /api/external/v1/estates`（`External\EstateController@index`）只列 `active=1 AND is_open=1` 的物件（staging `544e8592eb`）。`POST /estates` 新建的物件 `is_open=0`（§3 #19），所以不在列表裡。站內幫手依名稱或編號找物件時走列表，客人「剛建物件，接著建合約或報修」會被回找不到。
- 依編號的單筆明細，帶 `role_id`＋`viewer_user_id` 時（JGB 端 showForViewer 方法）已不限 `is_open`；不帶身分的單筆與列表仍限刊登中。
- **請 JGB 決定**：列表納入未開放物件（至少對建立者團隊），或確認「依編號查明細」可作為寫入前解析物件的正式路徑。
- 查證：`git -C ~/dev/work/jgb2/dev1 show 544e8592eb:app/Http/Controllers/External/EstateController.php | grep -n "is_open"`（第 77～79 行列表條件，第 191 行起 showForViewer 的註解）。

## 6. 請 JGB 回答（彙整）

| # | 問題 | 會不會擋上線 |
|---|---|---|
| #16 | 「未收」是否含 8 待對帳 | 否（影響數字） |
| #16～#18 | 同意以「擴充既有端點」方式做嗎？參數命名可照 JGB 慣例調整 | 是 |
| #17 | 執行中＝1／2／16 是否正確 | 否 |
| #18 | 到期篩選是否與畫面「即將到期」一致 | 否 |
| #19 | 「台」「臺」是否視同 | 否 |
| #20 | 新合約初始 `status`／`bit_status` | 否 |
| §0 | 冪等：同一個 `idempotency_key` 重送時回什麼、內容不同時回什麼（HTTP 碼與訊息） | 是 |
| §5 | 經 `POST /estates` 新建的物件，列表（只列 `active=1 AND is_open=1`）查不到；列表要不要納入未開放物件，或改走依編號查明細 | 否（影響剛建物件的後續建合約、報修） |

staging 程式已答、不再問（`8ff2f7b8e7`，DSP-132；答案寫在 §3 各節）：#19 `title` 上限與初始狀態、#20 押金是金額、#21 簽署與發送、§0 寫入成員身分參數名是 `viewer_user_id`、寫入越權統一回 404。讀取端點的越權是否也統一 404，未查。

## 7. 我方要配合改的（AIChatbot 內部，JGB 不必做）

- #16～#18 改呼叫擴充後的既有端點（目前程式呼叫的是 `bills/summary/unpaid`、`repairs/in-progress`、`contracts/expiring` 三條新路徑與 `data` 物件形狀），JGB 定案後改呼叫端與解析。
- 寫入成員身分參數名照 JGB 定案調整。
- 寫入呼叫端（#19～#23）與照片 multipart（接口文件 §7.1）已寫好，開關 `JGB_WRITE_WIRING` 生效（連 staging）時送出；開關不生效時，接真 JGB 不發寫入請求、不送 `broken_photos`。
