# 步 0b 覆蓋報告：頁面樹基準 193 格 × 兩身分（jgb2 master @ b2ee2ac382ce）

⚠️ covered＝有細目提到這頁，⛔ 不代表細目內容符合 JGB 現況；既有細目來自舊 kb 改寫，逐句對源另出。

## 總表

| 架 | 格 | 售前 prospect covered／partial／missing | 業者 property_manager covered／partial／missing |
|---|---|---|---|
| A | 30 | 16／8／6 | 22／6／2 |
| B | 5 | 4／1／0 | 5／0／0 |
| C | 50 | 12／12／26 | 28／3／19 |
| D | 57 | 12／28／17 | 39／7／11 |
| E | 19 | 0／18／1 | 18／0／1 |
| F | 9 | 8／0／1 | 8／1／0 |
| G | 3 | 3／0／0 | 3／0／0 |
| H | 5 | 0／0／5 | 0／0／5 |
| I | 15 | 4／2／9 | 4／2／9 |
| **合計** | 193 | **59／69／65** | **127／19／47** |

## A（30 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `users.advance` | `advance` | **missing** ｜進階折扣/帳單設定頁無對應細目 | **missing** ｜進階折扣/帳單設定頁無對應細目 |
| `users.approval` | `approval` | **missing** ｜內部簽核流程管理無對應細目 | **missing** ｜內部簽核流程管理無對應細目 |
| `users.create` | `/users/create` | **covered** `A/account-registration` | **covered** `A/account-registration` |
| `users.dashboard` | `` | **covered** `I/dashboard-overview` | **covered** `I/dashboard-overview` |
| `users.forget` | `/users/forget/:which?` | **covered** `A/forgot-password`、`A/forgot-account-email` | **covered** `A/forgot-password`、`A/forgot-account-email` |
| `users.forget.account` | `account` | **covered** `A/forgot-account-email` | **covered** `A/forgot-account-email` |
| `users.forget.password` | `password/:type?` | **covered** `A/forgot-password` | **covered** `A/forgot-password` |
| `users.index` | `/users` | **covered** `I/dashboard-overview` | **covered** `I/dashboard-overview` |
| `users.lesseeList` | `/users/lesseeList` | **missing** ｜售前不會問內部租客名單頁，且無相關細目 | **partial** `D/contract-lookup`｜只涵蓋合約查詢，未涵蓋租客名單列表/篩選頁本身 |
| `users.login` | `/users/login` | **covered** `A/login-methods` | **covered** `A/login-methods` |
| `users.notification` | `notification` | **partial** `A/account-profile-settings`｜只提到通知語言設定，未涵蓋通知中心列表本身 | **partial** `A/account-profile-settings`｜只提到通知語言設定，未涵蓋通知中心列表本身 |
| `users.orders` | `orders` | **missing** ｜扣款/訂單紀錄頁對售前不適用，且無對應細目 | **covered** `I/subscription-change-renewal` |
| `users.payment.add` | `add/:vendorKey?` | **partial** `E/payment-gateway-options`｜只講金流廠商差異與申請條件，未涵蓋新增綁定的操作頁 | **covered** `E/payment-gateway-setup` |
| `users.payment.detail` | `detail/:vendorKey/:vendorId` | **partial** `E/payment-gateway-options`｜只講金流廠商差異與申請條件，未涵蓋綁定明細頁本身 | **covered** `E/payment-gateway-setup` |
| `users.payment.index` | `payment` | **covered** `E/payment-gateway-options` | **covered** `E/payment-gateway-options` |
| `users.public` | `/p/:encryptId?/:mode?/:premisesUseFor?` | **covered** `C/rental-storefront-vr` | **covered** `C/storefront-entry-share` |
| `users.rechargeAccountList` | `/users/rechargeAccountList` | **covered** `E/virtual-account-prepaid` | **covered** `E/fixed-virtual-account-management` |
| `users.signer_info` | `signer_info` | **partial** `D/contract-esign-flow`｜只在簽約流程中提到身分，未涵蓋簽署方資訊設定頁細節 | **covered** `D/signer-identity-and-seal` |
| `users.subscription` | `/users/subscription` | **covered** `I/pricing-plans` | **covered** `I/pricing-plans` |
| `users.subscription.chose` | `/users/subscription/chose` | **covered** `I/pricing-plans` | **covered** `I/pricing-plans` |
| `users.subscription.unsubscribe` | `/users/subscription/unsubscribe` | **partial** `I/subscription-change-renewal`｜有講取消訂閱規則，但target_user不含售前 | **covered** `I/subscription-change-renewal` |
| `users.team.member.owned` | `team/member/owned/:category/:uid` | **missing** ｜售前不會問內部成員資料歸屬轉移頁，且無對應細目 | **partial** `B/remove-team-member-data-retention`｜只答成員移除後資料歸屬，未涵蓋此列表頁操作介面 |
| `users.verify` | `/users/verify/:which?` | **covered** `A/verification-code-invalid`、`A/verification-code-not-received` | **covered** `A/verification-code-invalid`、`A/verification-code-not-received` |
| `users.verify.phone` | `phone` | **covered** `A/verification-code-invalid`、`A/verification-code-not-received` | **covered** `A/verification-code-invalid`、`A/verification-code-not-received` |
| `notifications.index` | `/{type?}` | **partial** `A/account-profile-settings`｜只提到通知語言設定，未涵蓋通知中心列表本身 | **partial** `A/account-profile-settings`｜只提到通知語言設定，未涵蓋通知中心列表本身 |
| `users.account` | `/account` | **covered** `A/account-profile-settings` | **covered** `A/account-profile-settings` |
| `users.add_merchant` | `/add_merchant/{manufacturer?}` | **partial** `E/payment-gateway-options`｜只講金流廠商差異與申請條件，未涵蓋開通綁定操作頁 | **covered** `E/payment-gateway-setup` |
| `users.role` | `/role` | **missing** ｜售前不會問此內部團隊資訊頁，且無對應細目 | **partial** `D/signer-identity-and-seal`｜只涵蓋簽署身分與大小章，未涵蓋此團隊/公司資訊頁其餘欄位 |
| `users.roleTenant` | `/roleTenant` | **partial** `A/account-profile-settings`｜細目只說簽約資訊在哪填，缺公司統編／大小章／經紀人章 | **partial** `D/signer-identity-and-seal`｜只涵蓋簽署身分與大小章，未涵蓋此簽約資訊頁其餘欄位 |
| `users.team` | `/team/{type?}/{action?}/{actionType?}` | **covered** `B/team-management-overview` | **covered** `B/add-team-member`、`B/who-has-permission-lookup`、`B/role-permission-granularity` |

## B（5 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `bigLandlords.index` | `/bigLandlords` | **covered** `B/what-is-owner-landlord`、`B/owner-report-collection-remit` | **covered** `B/what-is-owner-landlord`、`B/owner-report-collection-remit` |
| `bigLandlords.list` | `/bigLandlords/list` | **covered** `B/what-is-owner-landlord` | **covered** `B/what-is-owner-landlord`、`B/add-owner-landlord-and-access` |
| `bigLandlords.report` | `/bigLandlords/report` | **covered** `B/owner-report-collection-remit` | **covered** `B/owner-report-collection-remit` |
| `bigLandlords.sheet` | `/bigLandlords/sheet/:bigLandlord_id/:role_id?` | **covered** `B/owner-report-collection-remit` | **covered** `B/owner-report-collection-remit` |
| `users.team.owned` | `/bigLandlords/owned/:id` | **partial** `B/what-is-owner-landlord`｜只解釋大房東概念，未涵蓋代管關係指派設定頁 | **covered** `B/add-owner-landlord-and-access` |

## C（50 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `communities.edit` | `/communities/edit/:communityId` | **partial** `C/property-management-overview`｜只有模組總覽，未涵蓋編輯欄位細節 | **covered** `C/community-setup-and-property-binding` |
| `communities.edit.balanceInvoice` | `balanceInvoice` | **missing** ｜缺差額發票機制的售前說明 | **covered** `E/differential-invoice` |
| `communities.edit.basic` | `basic` | **partial** `C/property-management-overview`｜只有總覽，未涵蓋基本資料欄位 | **covered** `C/community-setup-and-property-binding` |
| `communities.edit.gallery` | `gallery` | **partial** `C/property-management-overview`｜只有總覽，未涵蓋照片上傳操作 | **covered** `C/community-setup-and-property-binding` |
| `communities.edit.intros` | `intros` | **partial** `C/property-management-overview`｜只有總覽，未涵蓋介紹文字欄位 | **covered** `C/community-setup-and-property-binding` |
| `communities.estates` | `estates/:communityId/:category?` | **covered** `C/property-management-overview` | **covered** `C/community-setup-and-property-binding` |
| `communities.forceBinding` | `/communities/forceBinding` | **missing** ｜缺社宅強制綁定流程的售前說明 | **covered** `C/community-setup-and-property-binding` |
| `communities.forceBinding.edit` | `edit` | **missing** ｜缺社宅強制綁定流程的售前說明 | **covered** `C/community-setup-and-property-binding` |
| `communities.forceBinding.edit.binding` | `binding` | **missing** ｜缺社宅強制綁定流程的售前說明 | **covered** `C/community-setup-and-property-binding` |
| `communities.forceBinding.welcome` | `` | **missing** ｜缺社宅強制綁定流程的售前說明 | **covered** `C/community-setup-and-property-binding` |
| `communities.index` | `/communities` | **covered** `C/property-management-overview` | **covered** `C/community-setup-and-property-binding` |
| `communities.list` | `` | **covered** `C/property-management-overview` | **covered** `C/community-setup-and-property-binding` |
| `communities.pick` | `pick/:action` | **missing** ｜缺社區挑選器 UI 的售前說明 | **partial** `C/community-setup-and-property-binding`｜涵蓋歸戶邏輯，未描述挑選器介面操作 |
| `communities.show` | `/communities/show/:communityId` | **partial** `C/rental-storefront-vr`｜只涵蓋招租店舖/VR概念，未提社區公開頁 | **covered** `C/community-public-page` |
| `estates.dashboard` | `/estates/dashboard/:id` | **missing** ｜沒有描述物件儀表板總覽入口本身，內容都在各分頁 | **missing** ｜沒有描述物件儀表板總覽入口本身，內容都在各分頁 |
| `estates.dashboard.attachments` | `attachments` | **missing** ｜缺物件附件上傳管理的說明 | **missing** ｜缺物件附件（非合約附件）上傳管理的說明 |
| `estates.dashboard.bills` | `bills/:tab?` | **covered** `E/billing-overview` | **covered** `E/periodic-bill-generation`、`E/bill-status-reconciliation`、`E/bill-reports-export` |
| `estates.dashboard.contractAttachments` | `contractAttachments` | **missing** ｜缺合約附件管理的售前說明 | **covered** `D/contract-attachments-notes-limits` |
| `estates.dashboard.contracts` | `contracts` | **partial** `D/contract-esign-flow`｜只涵蓋簽約流程，缺合約查詢/狀態列表的售前總覽 | **covered** `D/contract-lookup`、`D/contract-status-overview`、`D/contract-filter-by-state` |
| `estates.dashboard.memos` | `memos` | **missing** ｜缺物件記事本功能的售前說明 | **missing** ｜缺物件記事本（備註＋附件）功能的說明 |
| `estates.dashboard.monthlyReport` | `monthlyReport` | **partial** `B/owner-report-collection-remit`｜只涵蓋大房東層級月報，未提個別物件每月報表 | **covered** `E/bill-reports-export` |
| `estates.dashboard.monthlyStatement` | `monthlyStatement` | **partial** `B/owner-report-collection-remit`｜只涵蓋大房東層級對帳單，未提個別物件對帳單 | **covered** `E/bill-reports-export` |
| `estates.dashboard.rent` | `rent` | **missing** ｜缺刊登成效統計的售前說明 | **missing** ｜缺物件刊登瀏覽數據/成效統計的說明 |
| `estates.dashboard.repair` | `repair` | **covered** `F/repair-system` | **covered** `F/repair-request-how-to-submit`、`F/repair-dispatch-and-close` |
| `estates.dashboard.runnings` | `runnings` | **missing** ｜缺流水帳功能的售前說明 | **missing** ｜缺物件流水帳（自訂收支記錄）功能的說明 |
| `estates.dashboard.sell` | `sell` | **missing** ｜頁面顯示「即將推出」，功能尚未上線，無對應說明 | **missing** ｜頁面顯示「即將推出」，功能尚未上線，無對應說明 |
| `estates.edit` | `/estates/edit/:id` | **partial** `C/property-management-overview`｜只有模組總覽，未涵蓋編輯物件的操作流程 | **covered** `C/property-edit-vs-publish`、`C/property-listing-conditions` |
| `estates.edit.basic` | `basic` | **partial** `C/property-management-overview`｜只有總覽，未涵蓋基本欄位填寫細節 | **covered** `C/property-listing-conditions` |
| `estates.edit.building_transcript` | `buildingTranscript` | **missing** ｜缺建物謄本欄位的售前說明 | **missing** ｜缺建物謄本（違建登記）欄位填寫的說明 |
| `estates.edit.building_transcript_general` | `buildingTranscriptGeneral` | **missing** ｜缺建物謄本欄位的售前說明 | **missing** ｜缺一般物件建物謄本欄位填寫的說明 |
| `estates.edit.facilities` | `facilities` | **missing** ｜缺物件設備清單的售前說明 | **missing** ｜缺物件設備清單填寫的說明 |
| `estates.edit.gallery` | `gallery` | **missing** ｜缺物件照片上傳的售前說明 | **missing** ｜缺物件照片上傳操作的說明 |
| `estates.edit.intro` | `intro` | **missing** ｜缺物件介紹欄位的售前說明 | **missing** ｜缺物件介紹文字欄位填寫的說明 |
| `estates.edit.rent_contact` | `rent_contact` | **missing** ｜缺聯絡資訊欄位的售前說明 | **missing** ｜缺租賃廣告聯絡資訊欄位填寫的說明 |
| `estates.edit.rent_detail` | `rent_detail` | **missing** ｜缺租金/生活費用細節的售前說明 | **partial** `C/property-listing-conditions`｜只提租金為必填欄位，未涵蓋生活費用等細節設定 |
| `estates.edit.rent_verify` | `rent_verify` | **missing** ｜缺違建申報欄位的售前說明 | **missing** ｜缺違章建築/租賃住宅條例申報欄位的說明 |
| `estates.edit.sell_contact` | `sell_contact` | **missing** ｜缺出售聯絡資訊的售前說明 | **missing** ｜缺出售廣告聯絡資訊欄位填寫的說明 |
| `estates.edit.sell_detail` | `sell_detail` | **missing** ｜缺出售明細的售前說明 | **missing** ｜缺出售物件明細欄位填寫的說明 |
| `estates.edit.vr` | `vr` | **covered** `C/rental-storefront-vr` | **covered** `C/property-vr-tour` |
| `estates.index` | `/estates/:category?` | **covered** `C/property-management-overview` | **covered** `C/property-status-meaning`、`C/property-advanced-search` |
| `estates.list` | `` | **covered** `C/property-management-overview` | **covered** `C/property-status-meaning`、`C/property-advanced-search` |
| `estates.monthlyUpload` | `/estates/monthlyUpload/:action` | **covered** `B/owner-report-collection-remit` | **covered** `B/owner-report-collection-remit` |
| `estates.pick` | `/estates/pick/:action` | **missing** ｜缺物件挑選器 UI 的售前說明 | **partial** `C/property-advanced-search`｜涵蓋物件列表搜尋，未描述作為批次動作挑選器的用法 |
| `listings.IOTDevice` | `/iot-device` | **covered** `G/smart-meter-lock-iot` | **covered** `G/meter-device-management`、`G/smart-lock-functions` |
| `listings.map` | `/map` | **partial** `C/property-management-overview`｜只有模組總覽，未提地圖搜尋這個入口 | **missing** ｜缺地圖找房（租客端搜尋）頁面對應的內容 |
| `listings.search` | `/search` | **partial** `C/property-management-overview`｜只有模組總覽，未提找房搜尋這個入口 | **missing** ｜缺找房搜尋（租客端搜尋）頁面對應的內容 |
| `estates.house` | `/house/{no}/{action?}` | **covered** `C/rental-storefront-vr` | **covered** `C/storefront-entry-share`、`C/public-display-address` |
| `estates.sell-house` | `/sell-house/{no}/{action?}` | **missing** ｜缺出售物件公開廣告頁的售前說明 | **missing** ｜缺出售物件公開廣告頁的說明（出售功能未見對應細目） |
| `estates.sell-show` | `/sell-show/{id}/{action?}` | **missing** ｜缺出售物件公開廣告頁的售前說明 | **missing** ｜缺出售物件公開廣告頁的說明（出售功能未見對應細目） |
| `estates.show` | `/show/{id}/{action?}` | **covered** `C/rental-storefront-vr` | **covered** `C/storefront-entry-share`、`C/public-display-address` |

## D（57 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `contracts.edit` | `/contracts/edit/:id` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約編輯頁總覽與狀態判讀 | **covered** `D/contract-status-overview`、`D/contract-modify-after-sign` |
| `contracts.edit.additionalConvention` | `additionalConvention` | **missing** ｜需要一條細目說明補充條款分頁怎麼填、範本套用方式 | **covered** `D/contract-attachments-notes-limits` |
| `contracts.edit.billSetting` | `billSetting` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋合約內帳單設定分頁 | **covered** `E/periodic-bill-generation`、`E/bill-archive-after-termination` |
| `contracts.edit.buildingTranscript` | `buildingTranscript` | **missing** ｜需要一條細目說明建物謄本資訊分頁的用途與填寫方式 | **missing** ｜需要一條細目說明建物謄本資訊分頁（地號建號、主建物面積等）的填寫方式 |
| `contracts.edit.dealerBasic` | `dealerBasic` | **partial** `D/signer-identity-and-seal`｜細目 target_user 不含 prospect | **covered** `D/signer-identity-and-seal` |
| `contracts.edit.facilities` | `facilities` | **missing** ｜需要一條細目說明合約設備清單分頁怎麼新增/複製設備 | **partial** `D/equipment-usage-under-lease`｜只講設備使用法規，未涵蓋合約編輯頁設備清單填寫操作 |
| `contracts.edit.landlordAttachment` | `landlordAttachment` | **partial** `D/contract-attachments-notes-limits`｜細目 target_user 不含 prospect | **covered** `D/contract-attachments-notes-limits` |
| `contracts.edit.payment` | `payment` | **partial** `E/tenant-payment-methods`｜細目 target_user 不含 prospect | **covered** `E/tenant-payment-methods` |
| `contracts.edit.publicNotary` | `publicNotary` | **covered** `D/lease-notarization` | **covered** `D/lease-notarization` |
| `contracts.edit.rent` | `rent` | **partial** `E/bill-contents-extra-fees`｜只答帳單費用品項，未涵蓋合約租金/押金/延遲金設定操作 | **covered** `D/deposit-setting-and-refund-system`、`E/late-fee-calculation`、`E/bill-contents-extra-fees` |
| `contracts.edit.rentAdjustment` | `rentAdjustment` | **missing** ｜需要一條細目說明合約租金調幅（固定/百分比、調幅週期）怎麼設定 | **missing** ｜需要一條細目說明合約租金調幅（固定/百分比、調幅週期）怎麼批次設定 |
| `contracts.edit.rentBasic` | `basic` | **partial** `D/early-termination-penalty`｜細目 target_user 不含 prospect | **covered** `D/early-termination-penalty`、`D/breach-penalty-rules`、`E/rent-amount-calculation`、`E/periodic-bill-generation`、`E/late-fee-calculation` |
| `contracts.edit.situation` | `situation` | **missing** ｜需要一條細目說明合約屋況/使用限制（消防設備、公共處所計價）分頁填寫方式 | **partial** `D/lease-clauses-interpretation`｜只講租約條款一般解釋，未涵蓋屋況/使用限制分頁的填寫操作 |
| `contracts.edit.socialHousing.attachments` | `attachments` | **partial** `D/contract-attachments-notes-limits`｜細目 target_user 不含 prospect，且未涵蓋社宅版附件項目 | **partial** `D/contract-attachments-notes-limits`｜只講一般合約附件上傳限制，未涵蓋社宅版指定附件項目清單 |
| `contracts.edit.socialHousing.buildingTranscript` | `buildingTranscript` | **missing** ｜需要一條細目說明社宅建物謄本資訊分頁的填寫方式 | **missing** ｜需要一條細目說明社宅建物謄本資訊分頁（建號地號、建物資訊）的填寫方式 |
| `contracts.edit.socialHousing.dealerBasic` | `dealerBasic` | **partial** `D/signer-identity-and-seal`｜細目 target_user 不含 prospect | **covered** `D/signer-identity-and-seal` |
| `contracts.edit.socialHousing.facilities` | `facilities` | **missing** ｜需要一條細目說明合約設備清單分頁怎麼新增/複製設備 | **partial** `D/equipment-usage-under-lease`｜只講設備使用法規，未涵蓋合約編輯頁設備清單填寫操作 |
| `contracts.edit.socialHousing.landlordAttachment` | `landlordAttachment` | **partial** `D/contract-attachments-notes-limits`｜細目 target_user 不含 prospect | **covered** `D/contract-attachments-notes-limits` |
| `contracts.edit.socialHousing.landlordBasic` | `landlordBasic` | **missing** ｜需要一條細目說明社宅合約房東基本資料分頁的填寫方式 | **missing** ｜需要一條細目說明社宅合約房東基本資料分頁（代理人、交付方式等）的填寫方式 |
| `contracts.edit.socialHousing.landlordLicense` | `landlordLicense` | **missing** ｜需要一條細目說明社宅房東資格授權書分頁的用途與填寫規則 | **missing** ｜需要一條細目說明社宅房東資格授權書分頁（公益出租人、代理人授權期間）的填寫規則 |
| `contracts.edit.socialHousing.moveIn` | `moveIn` | **missing** ｜需要一條細目說明社宅合約內建點交表單與一般點交流程的差異 | **partial** `D/handover-checkin`｜只講一般點交流程，未涵蓋社宅合約編輯頁內建點交表單 |
| `contracts.edit.socialHousing.payment` | `payment` | **partial** `E/tenant-payment-methods`｜細目 target_user 不含 prospect | **covered** `E/tenant-payment-methods` |
| `contracts.edit.socialHousing.photos` | `photos` | **missing** ｜需要一條細目說明社宅合約照片檢核（滅火器、火警警報器等）分頁的用途 | **missing** ｜需要一條細目說明社宅合約照片檢核（滅火器、火警警報器等）分頁的填寫方式 |
| `contracts.edit.socialHousing.publicNotary` | `publicNotary` | **covered** `D/lease-notarization` | **covered** `D/lease-notarization` |
| `contracts.edit.socialHousing.rent` | `rent` | **partial** `E/bill-contents-extra-fees`｜只答帳單費用品項，未涵蓋合約租金/押金/延遲金設定操作 | **covered** `D/deposit-setting-and-refund-system`、`E/late-fee-calculation`、`E/bill-contents-extra-fees` |
| `contracts.edit.socialHousing.rentBasic` | `basic` | **partial** `D/early-termination-penalty`｜細目 target_user 不含 prospect | **covered** `D/early-termination-penalty`、`D/breach-penalty-rules` |
| `contracts.edit.socialHousing.situation` | `situation` | **missing** ｜需要一條細目說明合約屋況/使用限制（消防設備、公共處所計價）分頁填寫方式 | **partial** `D/lease-clauses-interpretation`｜只講租約條款一般解釋，未涵蓋屋況/使用限制分頁的填寫操作 |
| `contracts.edit.socialHousing.subsidyTerms` | `subsidyTerms` | **missing** ｜需要一條細目說明社宅租屋補貼修繕費項目分頁的用途 | **missing** ｜需要一條細目說明社宅租屋補貼修繕費項目分頁的填寫規則 |
| `contracts.edit.socialHousing.tenantAttachment` | `tenantAttachment` | **missing** ｜需要一條細目說明社宅租客資格證明文件分頁要求哪些附件 | **missing** ｜需要一條細目說明社宅租客資格證明文件分頁（戶籍謄本、所得清單等）要求哪些附件 |
| `contracts.edit.socialHousing.tenantBasic` | `tenantBasic` | **missing** ｜需要一條細目說明社宅租客資格分類（低收入戶等）分頁的填寫方式 | **missing** ｜需要一條細目說明社宅租客資格分類（低收入戶等）分頁的填寫方式 |
| `contracts.edit.socialHousing.tenantHousehold` | `tenantHousehold` | **missing** ｜需要一條細目說明社宅租客家庭與財產所得檢核分頁的用途 | **missing** ｜需要一條細目說明社宅租客家庭與財產所得檢核分頁的填寫規則 |
| `contracts.edit.socialHousing.tenantLicense` | `tenantLicense` | **missing** ｜需要一條細目說明社宅租客資格授權書分頁的用途 | **missing** ｜需要一條細目說明社宅租客資格授權書分頁的填寫與授權規則 |
| `contracts.edit.taxAndInvoice` | `taxAndInvoice` | **covered** `E/einvoice-issuing` | **partial** `E/einvoice-issuing`｜只講電子發票開立時機與載具，未涵蓋合約內統編/免稅/開票商設定 |
| `contracts.edit.tenantInfo` | `tenantInfo` | **partial** `D/signer-identity-and-seal`｜細目 target_user 不含 prospect | **covered** `D/signer-identity-and-seal` |
| `contracts.index` | `/contracts/:status?` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約列表/狀態總覽頁 | **covered** `D/contract-status-overview`、`D/contract-filter-by-state` |
| `contracts.list` | `` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約列表查詢頁 | **covered** `D/contract-lookup`、`D/contract-filter-by-state` |
| `contracts.moveIn` | `/contracts/sh-move-in/:id` | **partial** `D/handover-checkin`｜細目 target_user 不含 prospect | **covered** `D/handover-checkin` |
| `contracts.moveOut` | `/contracts/move-out/:id` | **partial** `D/return-checkout`｜細目 target_user 不含 prospect | **covered** `D/return-checkout` |
| `contracts.pick` | `pick/:action/:id?` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約挑選頁 | **covered** `D/contract-lookup` |
| `contracts.renew` | `renew` | **partial** `D/renewal-flow`｜細目 target_user 不含 prospect | **covered** `D/renewal-flow` |
| `contracts.renew.preview` | `renew/preview` | **partial** `D/renewal-flow`｜細目 target_user 不含 prospect | **covered** `D/renewal-flow` |
| `contracts.search` | `search` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約搜尋頁 | **covered** `D/contract-lookup` |
| `contracts.show` | `/contracts/sh-show/:id` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約詳情頁狀態判讀 | **covered** `D/contract-status-overview`、`D/contract-lookup` |
| `entrustContracts.index` | `/entrustedContracts/:status?` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.edit` | `/entrustedContracts/:id/edit` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.edit.basic` | `basic` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.edit.fee` | `fee` | **partial** `D/sublease-vs-management-contract`｜只答包租代管差異，未涵蓋委託合約服務費計算設定 | **covered** `D/delegation-contract-terms-general` |
| `entrustedContracts.edit.landlord_info` | `landlord_info` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.edit.manager_info` | `manager_info` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.edit.payment` | `payment` | **partial** `D/sublease-vs-management-contract`｜只答包租代管差異，未涵蓋委託合約收付款帳戶設定 | **covered** `D/delegation-contract-terms-general` |
| `entrustedContracts.list` | `` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `entrustedContracts.show` | `/entrustedContracts/show/:id?` | **covered** `D/delegation-vs-lease-contract`、`D/sublease-vs-management-contract` | **covered** `D/delegation-contract-flow` |
| `contracts.early_termination` | `/early_termination/{id?}/{action?}` | **partial** `D/early-termination-flow`｜細目 target_user 不含 prospect | **covered** `D/early-termination-flow`、`D/early-termination-penalty` |
| `contracts.move_in` | `/move_in/{id?}/{action?}` | **partial** `D/handover-checkin`｜細目 target_user 不含 prospect | **covered** `D/handover-checkin` |
| `contracts.show` | `/show/{id?}/{action?}` | **partial** `D/contract-esign-flow`｜只答簽約流程，未涵蓋合約詳情頁（舊版）狀態判讀 | **covered** `D/contract-status-overview`、`D/contract-lookup` |
| `contracts.sign` | `/sign/{id?}/{action?}` | **covered** `D/contract-esign-flow` | **covered** `D/contract-esign-flow`、`D/tenant-sign-steps` |
| `contracts.thinkcloud` | `/thinkcloud/{id?}/{type?}/{action?}` | **covered** `D/contract-esign-flow` | **covered** `D/contract-esign-flow`、`D/esign-troubleshooting` |

## E（19 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `balanceInvoices.edit` | `/balanceinvoices/edit/:groupId` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.edit.basicInfo` | `basicInfo/:isCreateNew` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.edit.belongingEstates` | `belongingEstates/:isCreateNew` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.edit.pickEstates` | `pickEstates/:isCreateNew` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.groups` | `groups/:groupId?` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.index` | `/balanceinvoices` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `balanceInvoices.list` | `list/:status?` | **partial** `E/differential-invoice`｜細目 target_user 不含 prospect，僅答房東操作面 | **covered** `E/differential-invoice` |
| `bills.create` | `create` | **partial** `E/billing-overview`｜只是帳務模組行銷總覽，未涵蓋建帳單操作細節 | **covered** `E/manual-bill-creation` |
| `bills.create.batch` | `create/batch` | **partial** `E/billing-overview`｜只是帳務模組行銷總覽，未涵蓋建帳單操作細節 | **covered** `E/manual-bill-creation` |
| `bills.create.cycleBatch` | `create/cycleBatch` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋週期帳單建立操作 | **covered** `E/periodic-bill-generation` |
| `bills.edit` | `edit/:billId?` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋編輯帳單操作 | **covered** `E/manual-bill-creation`、`E/bill-contents-extra-fees` |
| `bills.index` | `/bills` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋帳單列表頁操作 | **covered** `E/bill-status-reconciliation` |
| `bills.list` | `:type?/:status?` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋帳單列表篩選操作 | **covered** `E/bill-status-reconciliation` |
| `bills.pick` | `pick/:action?` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋批次排定發送操作 | **covered** `E/bill-scheduled-auto-send` |
| `bills.sheet` | `/bills/sheet` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋財務報表匯出頁 | **covered** `E/bill-reports-export` |
| `bills.socialHousingSheets` | `/bills/socialHousingSheets/:version?` | **missing** ｜需要一條細目說明社宅清冊/表單4、7、9、11 的用途與歸檔流程 | **missing** ｜需要一條細目說明社宅清冊/表單4、7、9、11 的用途、媒合編號與歸檔流程 |
| `bills.stat` | `stat/:target?` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋統計報表頁操作 | **covered** `E/bill-reports-export` |
| `/pick/{action?}` | `/pick/{action?}` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋批次排定發送操作 | **covered** `E/bill-scheduled-auto-send` |
| `bills.one` | `/one/{type}/{status}/{id}` | **partial** `E/billing-overview`｜只是行銷總覽，未涵蓋單筆帳單詳情頁 | **covered** `E/bill-status-reconciliation`、`E/bill-contents-extra-fees` |

## F（9 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `repair` | `/repair` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.apply` | `/repair/apply` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.applyProcess` | `/repair/applyProcess/:step?` | **covered** `F/repair-request-how-to-submit` | **covered** `F/repair-ticket-open-and-confirm` |
| `repair.archive` | `/repair/archive` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.assign` | `/repair/assign` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.complete` | `/repair/complete` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.edit` | `/repair/edit/:id?` | **covered** `F/repair-request-how-to-submit` | **covered** `F/repair-ticket-open-and-confirm`、`F/repair-ticket-reclassify` |
| `repair.finish` | `/repair/finish` | **covered** `F/repair-flow-stages` | **covered** `F/repair-flow-stages` |
| `repair.share` | `/repair/share/:id?` | **missing** ｜缺報修單分享連結機制的售前說明 | **partial** `F/repair-dispatch-and-close`｜涵蓋業者/廠商協作，未提報修單分享連結機制 |

## G（3 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `powerMeter.list` | `:type` | **covered** `G/smart-meter-lock-iot` | **covered** `G/meter-device-management` |
| `powerMeter.single` | `single/:iotId` | **covered** `G/smart-meter-lock-iot` | **covered** `G/meter-device-management` |
| `/{deviceType}/{params?}` | `/{deviceType}/{params?}` | **covered** `G/smart-meter-lock-iot` | **covered** `G/meter-device-management`、`G/smart-lock-functions` |

## H（5 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `listings.helpCenter` | `/help` | **missing** ｜H 幫助中心目前空架，無對應細目 | **missing** ｜H 幫助中心目前空架，無對應細目 |
| `listings.helpCenter.group` | `group/:slug?` | **missing** ｜H 幫助中心目前空架，無對應細目 | **missing** ｜H 幫助中心目前空架，無對應細目 |
| `listings.helpCenter.post` | `post/:slug?` | **missing** ｜H 幫助中心目前空架，無對應細目 | **missing** ｜H 幫助中心目前空架，無對應細目 |
| `listings.helpCenter.search` | `search` | **missing** ｜H 幫助中心目前空架，無對應細目 | **missing** ｜H 幫助中心目前空架，無對應細目 |
| `/help/{any?}/{slug?}` | `/help/{any?}/{slug?}` | **missing** ｜H 幫助中心目前空架，無任何細目 | **missing** ｜H 幫助中心目前空架，無任何細目 |

## I（15 格）

| 格 | 路徑 | 售前 prospect | 業者 property_manager |
|---|---|---|---|
| `controlPanel.index` | `/controlPanel` | **missing** ｜控制台總覽（連結任務管理／通知信）無對應細目 | **missing** ｜控制台總覽（連結任務管理／通知信）無對應細目 |
| `controlPanel.setting` | `/controlPanel/setting` | **missing** ｜控制台設定頁無對應細目 | **missing** ｜控制台設定頁無對應細目 |
| `listings.demoForm` | `/demo-form` | **missing** ｜缺預約 demo 表單流程的說明 | **missing** ｜缺預約 demo 表單流程的說明 |
| `listings.pricing` | `/pricing` | **covered** `I/pricing-plans` | **covered** `I/pricing-plans` |
| `listings.pricing.TrialPlan` | `/pricing/trial-plan` | **covered** `I/free-trial` | **covered** `I/pricing-plans` |
| `notificationMail` | `notificationMail` | **missing** ｜通知信範本/類型設定無對應細目 | **missing** ｜通知信範本/類型設定無對應細目 |
| `taskManagement` | `taskManagement` | **missing** ｜自動化任務管理（排程通知/報修）無對應細目 | **missing** ｜自動化任務管理（排程通知/報修）無對應細目 |
| `taskManagement.create` | `taskManagement/create` | **missing** ｜自動化任務建立流程無對應細目 | **missing** ｜自動化任務建立流程無對應細目 |
| `taskManagement.edit` | `taskManagement/edit/:id?` | **missing** ｜自動化任務編輯流程無對應細目 | **missing** ｜自動化任務編輯流程無對應細目 |
| `tools.unlock` | `/unlock/:iotId/:batch` | **partial** `G/smart-meter-lock-iot`｜只涵蓋門鎖IoT概念，未涵蓋此遠端解鎖工具頁 | **partial** `G/smart-lock-functions`｜只涵蓋一般開門/密碼功能，未涵蓋此技師遠端解鎖工具頁 |
| `/repair/{any?}/{any2?}` | `/repair/{any?}/{any2?}` | **covered** `F/repair-system`、`F/repair-request-how-to-submit` | **covered** `F/repair-request-how-to-submit` |
| `customers.demand` | `/demand/{action?}/{id?}` | **missing** ｜過去活動付款連結頁，屬舊活動，無對應細目 | **missing** ｜過去活動付款連結頁，屬舊活動，無對應細目 |
| `customers.tcloud` | `/tcloud/{action?}/{id?}/{sign?}` | **missing** ｜中華電信雲市集訂單頁，屬外部行銷通路，無對應細目 | **missing** ｜中華電信雲市集訂單頁，屬外部行銷通路，無對應細目 |
| `indexs` | `/` | **covered** `I/product-overview`、`I/pricing-plans` | **covered** `I/pricing-plans` |
| `share` | `/share/{action}/{id?}` | **partial** `C/rental-storefront-vr`｜只解釋招租店舖是什麼，未涵蓋通用分享燈箱功能 | **partial** `C/storefront-entry-share`｜只涵蓋招租店舖分享，未涵蓋物件廣告等其他分享類型 |
