# 大綱骨架：九架 → 粗目（產品功能）— 2026-09-20 定案（DSP-067，業主「同意」）

定義：粗目＝JGB 的一個功能（使用者在產品裡看得到的一個頁面或功能區），名稱用產品介面自己的標籤（`src/routes/*.js` 的 `meta.label`、blade 的頁標題）。細目（該功能上使用者會問的一件事）在骨架核可後才寫。來源＝jgb2 `master` 頁面樹 193 頁（`inputs/page-surface-20260919.md`）。歸架依內容，不依路由檔；⇄＝與路由檔歸架不同、已裁換架。

規則：每頁恰歸一個粗目。唯一例外 `users.team`（blade）：同一路由依 `type` 是兩個頁（1＝成員列表、2＝大房東列表），分別歸兩個粗目，下方標「（type=1）」「（type=2）」。挑選器與 SPA 殼層路由不獨立成粗目，掛在使用它的功能底下。

## A 帳號與身分（8 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 註冊帳號（Email／SSO、驗證碼、手機綁定） | `users.create`、`users.verify`、`users.verify.phone` |
| 登入 | `users.login` |
| 忘記帳號、忘記密碼 | `users.forget`、`users.forget.account`、`users.forget.password` |
| 會員中心首頁 | `users.index`、`users.dashboard` |
| 帳號資訊 | `users.account`（blade） |
| 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） | `users.signer_info`、`users.roleTenant`（blade，頁標題「簽約資訊」） |
| 通知中心 | `notifications.index`（blade） |
| 通知收件設定與發送報表（通知收件信箱最多再加 3 組） | `users.notification` |

## B 團隊、人員與大房東（7 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊）⇄ 由 A 移入 | `users.role`（blade，`role.blade.php`） |
| 成員列表（邀請、角色、成員名下資料） | `users.team`（blade，type=1）、`users.team.member.owned` |
| 大房東列表與授權物件 | `users.team`（blade，type=2）、`bigLandlords.index`、`bigLandlords.list`、`users.team.owned` |
| 大房東報表 | `bigLandlords.report` |
| 大房東對帳表 | `bigLandlords.sheet` |
| 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」）⇄ 由 A 移入 | `users.advance` |
| 租客列表（當前租客／封存、準時繳租率、信用評價）⇄ 由 A 移入 | `users.lesseeList` |

## C 社區與物件（11 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 社區列表與建立 | `communities.index`、`communities.list` |
| 社區資料編輯（基本資料、照片與描述、介紹與交通） | `communities.edit`、`.basic`、`.gallery`、`.intros` |
| 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） | `communities.estates` |
| 社區廣告（社區公開頁；程式裡「社區詳情」指的是管理端的社區底下物件頁） | `communities.show` |
| 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） | `communities.forceBinding`、`.edit`、`.edit.binding`、`.welcome` |
| 物件列表與篩選 | `estates.index`、`estates.list` |
| 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） | `estates.edit`、`.basic`、`.building_transcript`、`.building_transcript_general`、`.facilities`、`.gallery`、`.intro`、`.vr` |
| 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） | `estates.edit.rent_detail`、`.rent_contact`、`.rent_verify` |
| 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） | `estates.dashboard`、`.rent`、`.contracts`、`.bills`、`.repair`、`.attachments`、`.runnings`、`.contractAttachments`、`.memos`、`.monthlyReport`、`.monthlyStatement`、`estates.monthlyUpload` |
| 單一物件廣告頁（招租） | `estates.house`（blade）、`estates.show`（blade） |
| 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選）⇄ 由 A 移入 | `users.public`；分享燈箱 `share`（blade）⇄ 由 I 移入 |

工具頁：`estates.pick`、`communities.pick`（挑選器，掛在使用它的功能底下）。

## D 租約（10 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 合約列表與搜尋 | `contracts.index`、`contracts.list`、`contracts.search` |
| 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） | `contracts.edit`、`.tenantInfo`、`.rentBasic`、`.rent`、`.rentAdjustment`、`.taxAndInvoice`、`.billSetting`、`.payment`、`.facilities`、`.situation`、`.dealerBasic`、`.buildingTranscript`、`.landlordAttachment`、`.additionalConvention` |
| 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） | `contracts.edit.socialHousing.*` 19 個分頁 |
| 簽約與合約檢視 | `contracts.sign`（blade）、`contracts.show`（SPA）、`contracts.show`（blade） |
| 點交 | `contracts.moveIn`、`contracts.move_in`（blade） |
| 點退 | `contracts.moveOut` |
| 續約 | `contracts.renew`、`contracts.renew.preview` |
| 提前解約 | `contracts.early_termination`（blade） |
| 租約公證（公證分頁與公證服務） | `contracts.edit.publicNotary`、`contracts.thinkcloud`（blade） |
| 委託合約（列表、建立編輯、檢視） | `entrustContracts.index`、`entrustedContracts.*` 8 頁 |

工具頁：`contracts.pick`（掛在建約／續約底下）。

## E 帳務（7 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 帳單列表與帳單狀態 | `bills.index`、`bills.list`、`bills.one`（blade） |
| 建立與編輯帳單（單筆、批次、週期批次） | `bills.create`、`.batch`、`.cycleBatch`、`bills.edit` |
| 帳單統計與報表 | `bills.stat`、`bills.sheet` |
| 社宅報表 | `bills.socialHousingSheets` |
| 差額發票（群組、底租、社區層開關） | `balanceInvoices.*` 7 頁、`communities.edit.balanceInvoice` ⇄ 由 C 移入 |
| 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程）⇄ 由 A 移入 | `users.rechargeAccountList` |
| 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」）⇄ 由 A 移入 | `users.add_merchant`（blade） |

工具頁：`bills.pick`、`/pick`（blade）。

## F 修繕（4 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） | `repair`、`repair.apply`、`.assign`、`.complete`、`.finish`、`.archive`；SPA 殼層 `/repair/{any?}`（blade，需登入）⇄ 由 I 移入 |
| 報修申請流程 | `repair.applyProcess` |
| 修繕單編輯 | `repair.edit` |
| 修繕單分享頁 | `repair.share` |

## G 裝置（3 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 電表列表與單一電表 | `powerMeter.list`、`powerMeter.single` |
| 裝置頁（門鎖、攝影機、小白盒） | `/{deviceType}`（blade，`where` 限 lock／camera／gateway） |
| 遠端解鎖（輸入解鎖密碼開門）⇄ 由 I 移入 | `tools.unlock` |

裝置廠商帳號綁定不是獨立頁：在 B「進階設定」裡（`iots/list` 的提示文字「請至 團隊管理 > 進階設定 內設定」）。

## H 幫助中心（1 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 幫助中心（分類、文章、搜尋） | `listings.helpCenter`、`.group`、`.post`、`.search`、`/help`（blade） |

## I 方案與導入（6 個粗目）

| 粗目 | 對應頁 |
|---|---|
| 方案、價格與免費試用 | `listings.pricing`、`listings.pricing.TrialPlan` |
| 訂閱、付款與訂單 ⇄ 由 A 移入 | `users.subscription`、`.chose`、`.unsubscribe`、`users.orders`、`users.payment.index`、`.add`、`.detail` |
| 預約 demo | `listings.demoForm` |
| 控制台（設定、通知信範本、自動化任務） | `controlPanel.index`、`controlPanel.setting`、`notificationMail`、`taskManagement`、`.create`、`.edit` |
| 官網首頁 | `indexs`（blade） |
| 中華電信雲市集訂單頁 | `customers.tcloud`（blade） |

## 數字

粗目 57（A8／B7／C11／D10／E7／F4／G3／H1／I6）。基準 183 頁＝174 頁各歸一個粗目＋`users.team` 依 type 歸兩個（1 頁）＋工具頁與殼層 5 頁掛在功能底下（`estates.pick`、`communities.pick`、`contracts.pick`、`bills.pick`、`/pick`）＋`customers.tcloud` 1 頁＋`contracts.show` SPA／blade 兩頁計 2。已裁不入基準 10 頁：`users.approval`（統上客製）、出售 5 頁、`listings.search`／`listings.map`、`listings.IOTDevice`、`customers.demand`。⇄ 換架 11 處：`users.role`／`users.advance`／`users.lesseeList`（A→B）、`users.public`／`share`（A／I→C）、`communities.edit.balanceInvoice`／`users.rechargeAccountList`／`users.add_merchant`（C／A／A→E）、`/repair/{any?}`（I→F）、`tools.unlock`（I→G）、訂閱付款整組（A→I）。

