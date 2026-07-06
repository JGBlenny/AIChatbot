# 研究紀錄：contract-conversational-facets（jgb2 ground truth 盤查）

> 建立時間：2026-07-02　來源：`/Users/lenny/jgb/project/jgb_interrogation/jgb2`（Laravel）四路並行盤查，皆附 file:line 證據。
> 前提：外部 API **可以擴充**（使用者已確認），故缺口分「現有可用」與「建議擴充」兩類。

## 一、簽署進度（簽署排障面向的 grounding 基礎）

- **無 per-signer 簽名表**。簽署狀態全在 `contracts.status`/`bit_status`（同一組位元常數，`app/Contract.php:38-49`）：
  - `status=2`（CONTRACT_INVITING）＝待租客簽回；`status=4`（CONTRACT_INVITING_NEXT）＝租客已簽、待管理者回簽；`status=8`＝雙方完成。
  - 「誰還沒簽」＝ `bit_status & 4`（租客）、`bit_status & 8`（管理者）決定性可判。
- 簽署時間戳在 contracts 上：`contract_inviting_at`／`contract_inviting_expire_at`／`contract_inviting_sign_at`（租客簽時）／`contract_finish_sign_at`（雙方完成）。
- **邀請收件通道存在合約上**：`to_user_email`／`to_user_phone`（發送後未選通道會被清空，留下的就是邀請通道，`ContractController.php:14796-14802`）。`to_user_connect`（0/1）＝是否綁定會員帳號。**「發給 gmail X 但租客用 SSO email Y 登入」的錯配診斷 = 比對 `contracts.to_user_email` vs `users.email`（`to_user_id`）**；寄送紀錄在 `role_email_logs.to_email`。
- 邀請效期：預設 **72 小時**（+72h，`ContractController.php:14805`），另有硬編角色白名單 168h（7 天）與 720h（30 天）（`:14815-14819`）。客服案例「3 天改 7 天異動單」＝把該角色加進 168h 名單。過期時排程 `contract:update invite`（每小時）呼叫 `reset()` 退回待發送**並清空租客資料**（`ContractStatusUpdater.php:146`）。
- 逐簽名格進度（哪一格沒簽）**不落地**，即時打雲想 `thinkcloud_api('check')` 查 `JobSignHist[].SIGN_STATUS`（`ContractController.php:17500+`）。診斷流程能答到「租客未簽／待回簽」層級；「第幾格沒簽」需即時代查雲想，不建議納入第一版。

## 二、狀態轉移與可編輯性（異動決策樹的 ground truth）

| 狀態 | 可做什麼 | 證據 |
|---|---|---|
| 1 待發送 | 直接編輯、可刪除 | 編輯僅 READY（`ContractController.php:12636`）；刪除僅 READY（`:18160-18166`） |
| 2/4 待簽 | 不可編輯；取消退回待發送再改 | `saveFormData` 擋 status≥2（`:9873`）；主取消路徑 `reset(true)` **保留租客資料**（`:18489-18492`，已修正舊清空缺陷），但租客按不同意/邀請過期路徑仍清空（`:15246`,`:15413`,`:18587`） |
| 8–512 執行中 | 使用者端不可取消不可編輯；只能提前終止流程、複製重建、或後台異動 | 取消擋 8/16/32/64/128（`:18470-18480`） |
| 1024/2048 歷史 | 每日 01:04 排程自動轉 | `contract:update history`（`Kernel.php:112`）：過 `date_end` → 1024；+30 天 → 2048（`Contract.php:26110-26190`） |

- **簽後凍結點**：雙簽完成後雲想產 PDF 存 S3（`contracts.thinkcloud_pdf`），使用者端全面擋存。**「藍字不可改」的機械依據＝status≥8 且 PDF 已產**。
- **「異動單」的系統真相**：**沒有**使用者端異動模組。後台兩條路：Admin `single()` 可改任意存在欄位＋可選連動帳單（`Admin/ContractController.php:838-905`），及手動執行的 `CustomerServiceCommands`（註解明寫「專來用來執行異動單的command」）。→ 對話流程的「填異動單」出口是引導產生申請文件給客服，不是打 API。
- 複製合約＝**分區塊複製**（basic/rent/facilities/situation/謄本/補充條款/附件，白名單 `Contract::COPYABLE_FIELDS`），非整份克隆；同型別群組才可複製（`ContractController.php:24245-24251`）。
- 提前終止：專用欄位群（`early_termination_*`、`old_date_end`）＋位元 256/512；`applyEarlyTermination()` 把 `date_end` 改成希望終止日，之後由每日轉歷史排程收尾。回簽效期預設 +30 天（`ContractService.php:744`）。

## 三、續約機制（續約面向的 ground truth）

- 父子鏈＝`contracts.father_id`（首約 `father_id=自己 id`；續約共用同一 father_id）＋ `is_newest` 旗標。判斷式 `isRenewContract()`＝`father_id 非空且 id≠father_id`。
- 系統續約＝`replicate()` 整列複製 → 新租期（`date_start=原 date_end+1`）、清簽署欄位、`is_newest` 換手（舊 0 新 1）。列表只顯示 `is_newest=1`；開舊約自動跳轉最新續約；**「原合約其他分頁」＝續約增補 PDF 以分頁掛在鏈上**（`ContractController.php:13149-13230`）。
- 續約文件是「續約增補」PDF（`resources/template/contract/renew.pdf`），非重產全文合約。
- 重簽規則：租客已註冊 → 走雲想重簽（`renew_thinkcloud_*` 欄位，72h 效期）；**免註冊租客 → 管理者單方確認即生效**（`contract_confirm_at`，不重簽）。
- 前提：原約需雙簽完成且 `date_end >= 今天` 才可續（`canRenewContract()`，`Contract.php:25321`）。
- ⚠️ **「已達數量上限」真相修正**：客服摘要說是「原約到期致物件下架」，程式證據是**訂閱方案合約配額**——`plan_contract_limit + plan_extra_contract_plus − roles.contracts_count`，且 `contracts_count` 計**所有 active 合約（含歷史、含每筆續約）**（`Role.php:2851-2987`、`PremisesLimitCheck.php:50-64`）。原約過期的失敗訊息是另一種（「無法進行續約」）。知識內容要照程式版本寫。
- 到期提醒既有：30 天前通知排程（`contract:notify-expiring`，每日 07:20）＋ 30/60/90 天到期統計（`expiringContractCount()`）。

## 四、外部 API 露出面（grounding 可用性）

Auth：`X-API-Key` per vendor（`ExternalApiAuth`，sha256、rate limit、資源權限、審計）。現有端點（`routes/api.php:31-125`）：estates、contracts/status-overview、estates/{id}、recharge-accounts、repairs×4、bills、payments、invoices、tenants/{user_id}/summary、contracts/{id}/checkin-eligibility、meters、payment-logs、invoice-logs。

**status-overview 已露出**（`External/ContractApiController.php:91-143`）：`status`、`bit_status`（含 12 里程碑 decode mapping）、`to_user_email/phone`、`to_user_connect`、`is_tenant_registered`、`father_id`、`date_start/date_end`、`early_termination_wish_date_end`、`deposit_amount`、租金地址等。→ 異動樹（只需 status）、退租收尾旗標（bit 16/32/64/128/256/512）、續約鏈（father_id 回溯）**現況即可 ground**。

**缺口與建議擴充**（使用者已同意可擴 API）：

| # | 缺口 | 影響面向 | 建議擴充 | 成本 |
|---|---|---|---|---|
| G1 | 簽署時間戳與邀請效期不露出（`contract_inviting_at/expire_at/sign_at`、`contract_finish_sign_at`） | 簽署排障 | status-overview 加 4 欄（皆 contracts 現有欄位） | 低 |
| G2 | 租客**登入帳號 email**（`users.email` via `to_user_id`）不露出，無法機械判 email 錯配 | 簽署排障 | status-overview 加 `to_user_login_email`（join users） | 低 |
| G3 | bills 外部端點**無封存欄位**（`archive_at/archive_ymd` 在 model 有、response 沒選） | 退租收尾（帳單封存了沒） | `BillApiController` select＋formatBill 加 `is_archived`/`archive_ymd` | 低 |
| G4 | 續約鏈只能回溯（father_id），無「此約是否已被續約」正向指標 | 續約 | status-overview 加 `is_newest`（現有欄位；`is_newest=0` ⇒ 已有較新續約） | 低 |
| G5 | 異動單無任何端點 | 異動樹 | 不擴——系統本無此模組，出口＝對話收斂異動資訊後產出申請書填寫內容（見 §六） | — |
| G6 | 逐簽名格進度需即時代查雲想 | 簽署排障 | 第一版不做；bit_status 層級已足 | — |

補充可用：`contracts/{id}/checkin-eligibility` 已回 `deposit_status`（應繳/已繳/是否足額）＋ `checkin_blockers`，退租收尾與押金相關追問可直接用。

## 五、對既有規劃的修正結論

1. 簽署排障的三步排查**全部可機械化**：誰沒簽（bit 4/8）→ 邀請發到哪（to_user_email/phone）→ 帳號錯配（G2 擴充後可比對）→ 效期是否已過（G1 擴充後可判，且過期會自動退回待發送並清租客資料——這本身就是高頻疑問的答案）。
2. 異動樹三出口與狀態的對映已定案（見 §二表），status-overview 現況即可 ground，**零 API 擴充**。
3. 退租收尾只差 G3（帳單封存）一個低成本擴充；其餘旗標現成。
4. 續約知識內容兩處要照程式修正：「已達數量上限」的真因（方案配額）；免註冊租客續約不重簽。
5. formatter 原則不變：decode 與可否操作全由 mapping/位元決定性算，LLM 只轉述 facts。

## 六、異動申請書出口契約（使用者定案 2026-07-02）

異動樹的「後台異動」出口形態：**對話收斂異動資訊 → 提供申請書範本＋可抄錄的填寫內容 → 客戶填寫、用印/簽名 → 提交給 JGB 人員**。非線上表單、非 API。

範本：`20250101_資料異動申請書_(公司名).docx`（金箍棒官方版），結構三段：

1. **申請人會員資訊**：會員類別擇一（個人/房東｜團隊管理者｜租客；團隊管理者的會員帳號應為**團隊擁有者**）、申請人會員帳號（手機/Email）、會員姓名、會員編號、團隊經辦人姓名/電話/信箱（＝提出申請的人）。註：帳號欄位「客戶調整帳號相關再填」。
2. **申請異動內容**：異動項目可複選（會員資料/物件資料/合約資料/帳務資料/其他）＋「異動前項目/狀態 → 異動後項目/狀態」自由欄——**合約 ID 與修改內容填這**。
3. **申請人簽署**：申請人姓名、(公司)負責人、地址、申請日期、**公司用印**。

提交通道：由**申請人會員帳戶之電子信箱**寄 `service@jgbsmart.com`，或紙本郵寄（114 台北市內湖區瑞光路335號6樓之16，客戶服務部門收）。

對話收斂要產出的欄位（converge payload）：
- 異動項目類別（勾選項，對話已知：合約資料為主）
- 合約 ID（grounding 已鎖定的那份；多份則列清單）
- 異動前 → 異動後（把使用者口語訴求轉成申請書可抄錄的兩欄文字，例：「合約 83315 租期 2026/9/1–2027/8/31 → 2026/9/1–2029/8/31」）
- 會員類別與經辦人提示（團隊管理者需用團隊擁有者帳號）

回覆並附固定指引：範本下載、用印後從會員信箱寄 service@jgbsmart.com、金箍棒保留異動與否及費用收取權利、完成後以 email 回覆。

## 七、面向收斂定案（2026-07-02，需求階段的輸入）

母分類 `系統合約` 下，既有子面向 `狀態判斷`，本次新增 5 個子面向。優先序按「價值×依賴」排：

| 序 | 子面向（category_config 值） | 型態 | grounding | API 依賴 | 知識素材 |
|---|---|---|---|---|---|
| 1 | `合約異動` | 診斷樹（多輪） | status-overview 現況即可（status 1/2/4/≥8 三出口） | **無** | Excel 38 筆＋C-1 藍字兩則＋help qa03/slug17/qa13；出口＝異動申請書收斂產出（§六） |
| 2 | `退租收尾` | 步驟推進（多輪） | bit 16/32/64/128/256/512 現成；帳單封存缺 | G3（bills 加 is_archived；未上線前該步給通用指引） | Excel 13 筆＋C-1 提前終止/封存 4 則＋help 9-1/9-2/slug29/slug68/qa15 |
| 3 | `續約` | 輕引導（1–2 輪） | date_end/father_id/is_tenant_registered 現成 | G4 選配（is_newest） | Excel 20 筆＋C-1 合約延長/租補 2 則＋help slug15；知識照程式修正（配額真因、免註冊不重簽） |
| 4 | `建約引導` | 輕引導（1–2 輪分流） | 不需 | 無 | help 基本教學 29 篇為主幹＋Excel 40 筆補邊界；共同承租話術、條款法律 QA（滯納金/審閱期/身分證/商用店面）作為知識掛此面向，不另開面向 |
| 5 | `簽署排障` | 診斷樹（多輪） | 部分現成（bit 4/8 誰沒簽、to_user_email 發到哪、to_user_connect 綁定）；效期與登入信箱比對缺 | G1＋G2（未上線前可先出「誰沒簽＋發送信箱」兩分支） | Excel 37 筆＋C-1 簡訊未收到/驗證碼＋help slug13/slug73/slug48/slug84/qa16 |

**併入決策樹的分支（不獨立成面向）**：
- 轉歷史/封存 → `合約異動` 與 `退租收尾` 共用出口（到期後每日 01:04 排程自動轉；逾期未轉導客服）。
- **權限分支**（新發現）：「編輯不了合約」不一定是狀態問題——可能是角色只有查閱權限（Excel 案例＋help qa13）。`合約異動` 樹入口先分：狀態擋 vs 權限擋。
- 邀請過期 → `簽署排障` 分支：過期自動退回待發送並清租客資料（72h 預設），這是「資料怎麼不見了」的標準答案。

**不做**：特殊建檔個案（包租 ABCD 等）、系統事故類 → 識別導客服；金流工程事件不屬對話流。

**平行知識軌**：help 中心「新手上路 51＋常見問題 85」全文可經公開 API（`/api2/helpCenter/getGroups`、`/api2/helpCenter/post?slug=`）抓取，其中合約相關 45 篇；官方文章給通則、Excel 給真實問法與邊界，依既有知識品質標準（先述情境再帶條件、短主題關鍵字 question）產製後掛對應面向。

## 八、設計階段定案（2026-07-02，gap-analysis §四 五個待決點）

1. **formatter 面向感知介面**：`_ground_by_api` → `execute_api_call` → `format_jgb_response` 鏈路貫穿一個選配參數 `face: Optional[str]`（併帶 `user_input=user_message`）。`jgb/contracts.py` 內建 `FACE_BUILDERS` 註冊表（face 值 → fact-builder）；face 未命中/未傳 → 完全走現行路由（狀態判斷零回歸）。面向字面只出現在 JGB 專屬 formatter，通用引擎維持零硬編。
2. **退租收尾 bills 二次查詢**：分兩階。本 spec：封存步驟一律輸出通用指引（G3 未上線的降級態＝常態）。G3 上線後：`grounding_scope` 增加通用 `secondary_call` 宣告（endpoint＋params 模板，設定驅動），engine 於單筆收斂後執行、結果併入 formatter 呼叫——契約先定於 design.md，實作列為 G3-gated 任務。
3. **R8 跨 grounding 型態切換**：定案「面向內切換走 face（換脈絡不換 config）；跨 grounding 型態（建約引導→診斷）走既有 scope=switch 關會話重路由」——重路由本來就會換 config，機制現成零改。建約引導 persona 規則明示：涉及特定合約現況時判 scope=switch。
4. **異動申請書格式骨架**：固定三段骨架（①申請書填寫內容：項目類別/合約ID/異動前→異動後 ②範本與提交通道 ③注意事項）寫死在 `合約異動` 子面向系統脈絡，LLM 按骨架填 `collected_fields` 值；e2e 斷言關鍵 token（`service@jgbsmart.com`、「異動前」「異動後」、合約 ID）。
5. **persona 規則分工**：五份獨立 config、各自 persona 規則，只寫面向差異（追問槽位、分流問句、收斂形態）；合約領域共同知識由母『系統合約』脈絡承擔，不在 persona 重複。

## 九、快照 vs 現況盤查（2026-07-02，使用者提供 jgb2 證據）

**總則：簽約當下把「物件」與「承租人」完整快照進 contracts（帳單、通知再各複製一層）。改物件/改個資不回寫任何既有合約。**

1. **物件租約中全欄位可編輯**（EstateController:5240 save 無合約狀態檢查；唯一限制是大房東權限 Estate:5577）。
2. **合約顯示＝簽約快照**：createContract 複製 estate 欄位＋estate_json＋estate_serialized（Contract:975-1041）；詳情頁 estateSnapshot()=unserialize（Contract:1397-1419），不讀 estates 現值；物件 saved 事件只做 RAG/快取不回寫合約。人工「重抓物件資料」僅合約草稿可用（ContractController:24675），非自動連動。
3. **帳單不受物件影響**：金額鏈 estate.rent →簽約複製→ contract.rent → getDiscountedRent（Contract:28542）→ bills.total 實體存值（Bill:3015）；已產生帳單不回改，新帳單只讀 contract.rent。
4. **點交/現況確認＝合約自身快照欄位**（facilities Contract:1001、situation:1035；moveIn 全程只動合約欄位，ContractController:19073）。
5. **租客自助改個資不回寫已簽合約**（UserController:4939 無 Contract 寫入）；夜間排程 ContactInfoUpdater 只處理房東且僅未發送合約（:107）；唯一回寫是客服手動工具且 update_contracts 預設 false（CustomerServiceController:5871）。
6. **通知一律寄快照**：簽約邀請/點交/點退用 contracts.to_user_email/phone（Notification:3404/4459/5163）；帳單用 bills.user_email（建帳單時再複製一層＝雙重快照，Bill:11970）。→「租客改了信箱收不到通知」的根因。
7. **姓名恆為快照**：列表/詳情用 to_user_first/last_name（Contract:23680/23706），與 PDF 一致（不會畫面新名 PDF 舊名）。
8. **無換承租人功能**：資料異動/帳單重產白名單只有週期欄位（cycle*，:1608-1625），不含 to_user_*；續約 replicate 沿用同一 to_user_id；to_user_id 僅簽署前邀請階段綁定（ContractController:14684）。換人＝重簽新約（原約處理屬營運 SOP，程式無法證明）。

## 參考

- 既有 ground truth：`.kiro/specs/conversational-diagnosis/research.md`（引擎整合面）、`reference_jgb2_contract_architecture`（12 狀態/4 階段/違約金 type）
- 本次證據索引：`app/Contract.php`、`app/Http/Controllers/ContractController.php`、`app/Services/ContractService.php`、`app/Console/Commands/ContractStatusUpdater.php`、`app/Http/Controllers/External/*`、`routes/api.php`、`app/Http/Middleware/PremisesLimitCheck.php`、`app/Role.php`
