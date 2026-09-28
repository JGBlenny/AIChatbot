# Plan 9.18 S4 頁面缺口清單（2026-09-28）

> 範圍：page-surface（`runs/outline-20260920/page-surface.json`）`in_baseline` 的 183 頁，**不分已審**，找出沒有任何細目 `code:` 來源對到的頁。
> 判定用 `endpoint_progress.py` 的 `page_hit` 原樣（SPA＝`src/pages/<component>` 逐字相等；blade＝controller 檔層級）。
> 工具 `scratchpad/p918_page_gap.py`（容器內跑），正本 commit `c646395e`。本清單只陳列，⛔ 裁決、⛔ 補寫細目。

## 1. 結論

- **pm 缺口 48 頁**（＝183−135；和 `endpoint_progress.py --ignore-review` 的 `pm 135` 交叉核相符）。
  - pm：覆蓋 135／183，缺口 48：外殼頁、子元件有引用 36、完全無細目 9、只有同目錄兄弟頁有引用 2、引用帶 #方法 1
  - prospect：覆蓋 48／183，缺口 135：完全無細目 107、外殼頁、子元件有引用 18、只有同目錄兄弟頁有引用 10
- pm 的「外殼頁、子元件有引用」共 36 頁，其中 15 頁是純路由外殼（檔內有 router-view），21 頁沒有 router-view、需人判是否只是分流元件。這兩類多半是**量尺只比對入口檔，而細目引用了實際畫面子元件**，不代表內容沒寫。
- **真正完全沒有細目的 pm 頁只有 9 頁**（見 §2 標「完全無細目」者），加上 2 頁只有同目錄兄弟頁有引用、1 頁因引用寫成 `Controller.php#方法` 而比對不到。
- prospect 的缺口大（135 頁、其中 107 頁完全無細目），但分母 183 包含大量只有登入業者才看得到的後台頁；哪些頁對 prospect 開放**未定義**，本表不推斷。
- ⚠️ 量尺本身的兩個限制（供之後決定要改量尺還是改引用）：(1) 外殼頁只認入口檔；(2) `#方法` 後綴使 blade 比對失敗。

## 2. pm 缺口 48 頁

| unit_id | 架 | 類型 | component | 分類 | 外殼判讀 | 附近引用（前 2） |
|---|---|---|---|---|---|---|
| `page:balanceInvoices.edit.belongingEstates` | E | spa | `balanceInvoices/edit/belongingEstates/Index.vue` | 完全無細目 |  |  |
| `page:bills.sheet` | E | spa | `bills/sheet/Index.vue` | 完全無細目 |  |  |
| `page:communities.pick` | C | spa | `communities/pick/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.landlordBasic` | D | spa | `contracts/edit/landlordBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.photos` | D | spa | `contracts/edit/photos/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.subsidyTerms` | D | spa | `contracts/edit/subsidyTerms/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.bills` | C | spa | `estates/dashboard/bills/Index.vue` | 完全無細目 |  |  |
| `page:web:/help/{any?}/{slug?}` | H | blade | `ListingController@index` | 完全無細目 |  |  |
| `page:web:indexs` | I | blade | `ListingController@index` | 完全無細目 |  |  |
| `page:users.forget` | A | spa | `users/auth/Forget.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/users/auth/Create.vue`、`src/pages/users/auth/Login.vue` |
| `page:users.verify` | A | spa | `users/auth/Verify.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/users/auth/Create.vue`、`src/pages/users/auth/Login.vue` |
| `page:web:notifications.index` | A | blade | `NotificationController@index` | 引用帶 #方法 |  | `app/Http/Controllers/NotificationController.php#index`、`app/Http/Controllers/NotificationController.php#navbar` |
| `page:balanceInvoices.list` | E | spa | `balanceInvoices/list/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（48 行，需人判） | `src/pages/balanceInvoices/list/_parts/ListTable.vue` |
| `page:bigLandlords.list` | B | spa | `bigLandlords/list/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（95 行，需人判） | `src/pages/bigLandlords/list/_parts/ListTable.vue`、`src/pages/bigLandlords/list/_parts/PageTop.vue` |
| `page:bigLandlords.report` | B | spa | `bigLandlords/report/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（204 行，需人判） | `src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx`、`src/pages/bigLandlords/report/_parts/ListTable.vue` |
| `page:contracts.edit.facilities` | D | spa | `contracts/edit/facilities/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（42 行，需人判） | `src/pages/contracts/edit/facilities/General.vue` |
| `page:contracts.edit.payment` | D | spa | `contracts/edit/payment/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（99 行，需人判） | `src/pages/contracts/edit/payment/General.vue`、`src/pages/contracts/edit/payment/SocialHousing.vue` |
| `page:contracts.edit.publicNotary` | D | spa | `contracts/edit/publicNotary/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（40 行，需人判） | `src/pages/contracts/edit/publicNotary/General.vue`、`src/pages/contracts/edit/publicNotary/SocialHousing.vue` |
| `page:contracts.edit.rentBasic` | D | spa | `contracts/edit/rentBasic/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（92 行，需人判） | `src/pages/contracts/edit/rentBasic/General.vue`、`src/pages/contracts/edit/rentBasic/SocialHousing.vue` |
| `page:contracts.edit.situation` | D | spa | `contracts/edit/situation/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（44 行，需人判） | `src/pages/contracts/edit/situation/General.vue`、`src/pages/contracts/edit/situation/SocialHousing.vue` |
| `page:contracts.edit.socialHousing.facilities` | D | spa | `contracts/edit/facilities/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（42 行，需人判） | `src/pages/contracts/edit/facilities/General.vue` |
| `page:contracts.edit.socialHousing.payment` | D | spa | `contracts/edit/payment/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（99 行，需人判） | `src/pages/contracts/edit/payment/General.vue`、`src/pages/contracts/edit/payment/SocialHousing.vue` |
| `page:contracts.edit.socialHousing.publicNotary` | D | spa | `contracts/edit/publicNotary/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（40 行，需人判） | `src/pages/contracts/edit/publicNotary/General.vue`、`src/pages/contracts/edit/publicNotary/SocialHousing.vue` |
| `page:contracts.edit.socialHousing.rentBasic` | D | spa | `contracts/edit/rentBasic/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（92 行，需人判） | `src/pages/contracts/edit/rentBasic/General.vue`、`src/pages/contracts/edit/rentBasic/SocialHousing.vue` |
| `page:contracts.edit.socialHousing.situation` | D | spa | `contracts/edit/situation/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（44 行，需人判） | `src/pages/contracts/edit/situation/General.vue`、`src/pages/contracts/edit/situation/SocialHousing.vue` |
| `page:entrustedContracts.list` | D | spa | `entrustedContracts/list/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（224 行，需人判） | `src/pages/entrustedContracts/list/_parts/PageTop.jsx` |
| `page:estates.edit.facilities` | C | spa | `estates/edit/facilities/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（52 行，需人判） | `src/pages/estates/edit/facilities/_parts/General.vue` |
| `page:estates.pick` | C | spa | `estates/pick/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（36 行，需人判） | `src/pages/estates/pick/_parts/pick.jsx` |
| `page:users.dashboard` | A | spa | `users/dashboard/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（36 行，需人判） | `src/pages/users/dashboard/Landlord.vue`、`src/pages/users/dashboard/parts/BalanceChart.vue` |
| `page:users.lesseeList` | B | spa | `users/lesseeList/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（183 行，需人判） | `src/pages/users/lesseeList/parts/ListTable.vue`、`src/pages/users/lesseeList/parts/PageNav.vue` |
| `page:users.subscription` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue`、`src/pages/users/subscription/MyPlan.vue` |
| `page:users.subscription.chose` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue`、`src/pages/users/subscription/MyPlan.vue` |
| `page:users.subscription.unsubscribe` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue`、`src/pages/users/subscription/MyPlan.vue` |
| `page:balanceInvoices.edit` | E | spa | `balanceInvoices/edit/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/balanceInvoices/edit/basicInfo/Index.vue`、`src/pages/balanceInvoices/edit/pickEstates/Index.vue` |
| `page:balanceInvoices.index` | E | spa | `balanceInvoices/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/balanceInvoices/_parts/IndividualBaseRentSetting.vue`、`src/pages/balanceInvoices/edit/basicInfo/Index.vue` |
| `page:bigLandlords.index` | B | spa | `bigLandlords/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/bigLandlords/list/_parts/ListTable.vue`、`src/pages/bigLandlords/list/_parts/PageTop.vue` |
| `page:bills.index` | E | spa | `bills/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/bills/_parts/ListTable.jsx`、`src/pages/bills/edit/Index.jsx` |
| `page:communities.forceBinding` | C | spa | `communities/forceBinding/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/communities/forceBinding/Welcome.vue`、`src/pages/communities/forceBinding/edit/Binding.vue` |
| `page:communities.index` | C | spa | `communities/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/communities/_parts/CommunityItem.vue`、`src/pages/communities/edit/BalanceInvoice.jsx` |
| `page:contracts.edit` | D | spa | `contracts/edit/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/contracts/edit/_methods/getFormDataForStepDone.js`、`src/pages/contracts/edit/additionalConvention/Index.vue` |
| `page:contracts.index` | D | spa | `contracts/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/contracts/_parts/show/signerInfo/ButtonArea.jsx`、`src/pages/contracts/edit/_methods/getFormDataForStepDone.js` |
| `page:entrustContracts.index` | D | spa | `entrustedContracts/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/entrustedContracts/edit/Index.jsx`、`src/pages/entrustedContracts/edit/landlordInfo/LandlordInfo.jsx` |
| `page:estates.dashboard` | C | spa | `estates/dashboard/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/estates/dashboard/_parts/MonthlyUpload.jsx`、`src/pages/estates/dashboard/_parts/TabNav.vue` |
| `page:estates.edit` | C | spa | `estates/edit/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/estates/edit/basic/Index.vue`、`src/pages/estates/edit/buildingTranscriptGeneral/Index.vue` |
| `page:estates.index` | C | spa | `estates/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/estates/dashboard/_parts/MonthlyUpload.jsx`、`src/pages/estates/dashboard/_parts/TabNav.vue` |
| `page:listings.pricing` | I | spa | `listings/pricing/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/listings/pricing/Home.vue`、`src/pages/listings/pricing/TrialPlan.vue` |
| `page:users.index` | A | spa | `users/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/users/advance/Index.jsx`、`src/pages/users/advance/_part/BillsManagement.vue` |
| `page:users.payment.index` | I | spa | `users/payment/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/users/payment/_parts/CashBanks.vue`、`src/pages/users/payment/_parts/Ctbc.vue` |

## 3. prospect 缺口 135 頁（依分類）

| unit_id | 架 | 類型 | component | 分類 | 外殼判讀 | 附近引用（前 2） |
|---|---|---|---|---|---|---|
| `page:users.dashboard` | A | spa | `users/dashboard/Index.vue` | 完全無細目 |  |  |
| `page:users.forget.account` | A | spa | `users/auth/parts/forget/Account.vue` | 完全無細目 |  |  |
| `page:users.forget.password` | A | spa | `users/auth/parts/forget/Password.vue` | 完全無細目 |  |  |
| `page:users.notification` | A | spa | `users/notification/Index.vue` | 完全無細目 |  |  |
| `page:users.signer_info` | A | spa | `users/signerInfo/Index.vue` | 完全無細目 |  |  |
| `page:web:notifications.index` | A | blade | `NotificationController@index` | 完全無細目 |  |  |
| `page:bigLandlords.report` | B | spa | `bigLandlords/report/Index.vue` | 完全無細目 |  |  |
| `page:bigLandlords.sheet` | B | spa | `bigLandlords/sheet/index.vue` | 完全無細目 |  |  |
| `page:users.team.member.owned` | B | spa | `users/team/memberOwned/Index.jsx` | 完全無細目 |  |  |
| `page:communities.estates` | C | spa | `communities/estates/Index.vue` | 完全無細目 |  |  |
| `page:communities.forceBinding` | C | spa | `communities/forceBinding/Index.vue` | 完全無細目 |  |  |
| `page:communities.forceBinding.edit` | C | spa | `communities/forceBinding/edit/Index.vue` | 完全無細目 |  |  |
| `page:communities.forceBinding.edit.binding` | C | spa | `communities/forceBinding/edit/Binding.vue` | 完全無細目 |  |  |
| `page:communities.forceBinding.welcome` | C | spa | `communities/forceBinding/Welcome.vue` | 完全無細目 |  |  |
| `page:communities.list` | C | spa | `communities/list/Index.vue` | 完全無細目 |  |  |
| `page:communities.pick` | C | spa | `communities/pick/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard` | C | spa | `estates/dashboard/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.attachments` | C | spa | `estates/dashboard/attachments/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.bills` | C | spa | `estates/dashboard/bills/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.contractAttachments` | C | spa | `estates/dashboard/contractAttachments/index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.contracts` | C | spa | `estates/dashboard/contracts/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.memos` | C | spa | `estates/dashboard/memos/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.rent` | C | spa | `estates/dashboard/rent/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.repair` | C | spa | `estates/dashboard/repair/Index.vue` | 完全無細目 |  |  |
| `page:estates.dashboard.runnings` | C | spa | `estates/dashboard/runnings/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.basic` | C | spa | `estates/edit/basic/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.building_transcript` | C | spa | `estates/edit/building_transcript/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.building_transcript_general` | C | spa | `estates/edit/buildingTranscriptGeneral/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.facilities` | C | spa | `estates/edit/facilities/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.gallery` | C | spa | `estates/edit/gallery/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.intro` | C | spa | `estates/edit/intro/Index.vue` | 完全無細目 |  |  |
| `page:estates.edit.vr` | C | spa | `estates/edit/vr/Index.vue` | 完全無細目 |  |  |
| `page:estates.list` | C | spa | `estates/list/Index.vue` | 完全無細目 |  |  |
| `page:estates.monthlyUpload` | C | spa | `estates/dashboard/_parts/MonthlyUpload.jsx` | 完全無細目 |  |  |
| `page:estates.pick` | C | spa | `estates/pick/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.edit` | D | spa | `contracts/edit/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.additionalConvention` | D | spa | `contracts/edit/additionalConvention/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.billSetting` | D | spa | `contracts/edit/billSetting/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.edit.buildingTranscript` | D | spa | `contracts/edit/buildingTranscript/General.vue` | 完全無細目 |  |  |
| `page:contracts.edit.dealerBasic` | D | spa | `contracts/edit/dealerBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.facilities` | D | spa | `contracts/edit/facilities/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.landlordAttachment` | D | spa | `contracts/edit/landlordAttachment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.payment` | D | spa | `contracts/edit/payment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.publicNotary` | D | spa | `contracts/edit/publicNotary/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.rent` | D | spa | `contracts/edit/rent/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.edit.rentAdjustment` | D | spa | `contracts/edit/rentAdjustment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.rentBasic` | D | spa | `contracts/edit/rentBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.situation` | D | spa | `contracts/edit/situation/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.attachments` | D | spa | `contracts/edit/attachments/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.buildingTranscript` | D | spa | `contracts/edit/buildingTranscript/SocialHousing.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.dealerBasic` | D | spa | `contracts/edit/dealerBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.facilities` | D | spa | `contracts/edit/facilities/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.landlordAttachment` | D | spa | `contracts/edit/landlordAttachment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.landlordBasic` | D | spa | `contracts/edit/landlordBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.landlordLicense` | D | spa | `contracts/edit/landlordLicense/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.moveIn` | D | spa | `contracts/edit/moveIn/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.payment` | D | spa | `contracts/edit/payment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.photos` | D | spa | `contracts/edit/photos/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.publicNotary` | D | spa | `contracts/edit/publicNotary/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.rent` | D | spa | `contracts/edit/rent/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.rentBasic` | D | spa | `contracts/edit/rentBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.situation` | D | spa | `contracts/edit/situation/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.subsidyTerms` | D | spa | `contracts/edit/subsidyTerms/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.tenantAttachment` | D | spa | `contracts/edit/tenantAttachment/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.tenantBasic` | D | spa | `contracts/edit/tenantBasic/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.tenantHousehold` | D | spa | `contracts/edit/tenantHousehold/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.socialHousing.tenantLicense` | D | spa | `contracts/edit/tenantLicense/Index.vue` | 完全無細目 |  |  |
| `page:contracts.edit.taxAndInvoice` | D | spa | `contracts/edit/taxAndInvoice/index.jsx` | 完全無細目 |  |  |
| `page:contracts.edit.tenantInfo` | D | spa | `contracts/edit/tenantInfo/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.list` | D | spa | `contracts/list/Index.vue` | 完全無細目 |  |  |
| `page:contracts.moveIn` | D | spa | `contracts/move-in/Index.vue` | 完全無細目 |  |  |
| `page:contracts.moveOut` | D | spa | `contracts/move-out/Index.jsx` | 完全無細目 |  |  |
| `page:contracts.renew` | D | spa | `contracts/renew/Index.vue` | 完全無細目 |  |  |
| `page:contracts.renew.preview` | D | spa | `contracts/renew/Preview.vue` | 完全無細目 |  |  |
| `page:contracts.search` | D | spa | `contracts/list/Index.vue` | 完全無細目 |  |  |
| `page:contracts.show` | D | spa | `contracts/show/Index.vue` | 完全無細目 |  |  |
| `page:entrustedContracts.edit.landlord_info` | D | spa | `entrustedContracts/edit/landlordInfo/LandlordInfo.jsx` | 完全無細目 |  |  |
| `page:entrustedContracts.edit.manager_info` | D | spa | `entrustedContracts/edit/managerInfo/ManagerInfo.jsx` | 完全無細目 |  |  |
| `page:entrustedContracts.show` | D | spa | `entrustedContracts/show/Index.jsx` | 完全無細目 |  |  |
| `page:balanceInvoices.edit` | E | spa | `balanceInvoices/edit/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.edit.basicInfo` | E | spa | `balanceInvoices/edit/basicInfo/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.edit.belongingEstates` | E | spa | `balanceInvoices/edit/belongingEstates/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.edit.pickEstates` | E | spa | `balanceInvoices/edit/pickEstates/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.groups` | E | spa | `balanceInvoices/groups/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.index` | E | spa | `balanceInvoices/Index.vue` | 完全無細目 |  |  |
| `page:balanceInvoices.list` | E | spa | `balanceInvoices/list/Index.vue` | 完全無細目 |  |  |
| `page:bills.pick` | E | spa | `bills/pick/Index.jsx` | 完全無細目 |  |  |
| `page:bills.sheet` | E | spa | `bills/sheet/Index.vue` | 完全無細目 |  |  |
| `page:bills.socialHousingSheets` | E | spa | `bills/socialHousingSheets/Index.vue` | 完全無細目 |  |  |
| `page:users.rechargeAccountList` | E | spa | `users/rechargeAccountList/Index.vue` | 完全無細目 |  |  |
| `page:web:/pick/{action?}` | E | blade | `BillController@pick` | 完全無細目 |  |  |
| `page:web:bills.one` | E | blade | `BillController@one` | 完全無細目 |  |  |
| `page:repair.edit` | F | spa | `repair/edit/Index.vue` | 完全無細目 |  |  |
| `page:powerMeter.list` | G | spa | `iots/list/Index.jsx` | 完全無細目 |  |  |
| `page:powerMeter.single` | G | spa | `iots/_parts/Single.vue` | 完全無細目 |  |  |
| `page:web:/{deviceType}/{params?}` | G | blade | `IotController@index` | 完全無細目 |  |  |
| `page:web:/help/{any?}/{slug?}` | H | blade | `ListingController@index` | 完全無細目 |  |  |
| `page:controlPanel.index` | I | spa | `control-panel/Index.vue` | 完全無細目 |  |  |
| `page:controlPanel.setting` | I | spa | `control-panel/setting/Index.jsx` | 完全無細目 |  |  |
| `page:notificationMail` | I | spa | `control-panel/notificationMail/Index.jsx` | 完全無細目 |  |  |
| `page:taskManagement` | I | spa | `control-panel/taskManagement/Index.vue` | 完全無細目 |  |  |
| `page:taskManagement.create` | I | spa | `control-panel/taskManagement/edit/Index.jsx` | 完全無細目 |  |  |
| `page:taskManagement.edit` | I | spa | `control-panel/taskManagement/edit/Index.jsx` | 完全無細目 |  |  |
| `page:users.orders` | I | spa | `users/orders/Index.vue` | 完全無細目 |  |  |
| `page:users.payment.add` | I | spa | `users/payment/routerView/Add.vue` | 完全無細目 |  |  |
| `page:users.payment.detail` | I | spa | `users/payment/routerView/Detail.vue` | 完全無細目 |  |  |
| `page:web:indexs` | I | blade | `ListingController@index` | 完全無細目 |  |  |
| `page:users.forget` | A | spa | `users/auth/Forget.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/users/auth/Create.vue`、`src/pages/users/auth/parts/AccountSetting.vue` |
| `page:users.login` | A | spa | `users/auth/Login.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/users/auth/Create.vue`、`src/pages/users/auth/parts/AccountSetting.vue` |
| `page:users.verify` | A | spa | `users/auth/Verify.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/users/auth/Create.vue`、`src/pages/users/auth/parts/AccountSetting.vue` |
| `page:users.team.owned` | B | spa | `bigLandlords/list/_parts/owned.jsx` | 只有同目錄兄弟頁有引用 |  | `src/pages/bigLandlords/list/_parts/PageTop.vue` |
| `page:communities.edit.basic` | C | spa | `communities/edit/Basic.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/communities/edit/BalanceInvoice.jsx`、`src/pages/communities/edit/Index.vue` |
| `page:communities.edit.gallery` | C | spa | `communities/edit/Gallery.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/communities/edit/BalanceInvoice.jsx`、`src/pages/communities/edit/Index.vue` |
| `page:communities.edit.intros` | C | spa | `communities/edit/Intros.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/communities/edit/BalanceInvoice.jsx`、`src/pages/communities/edit/Index.vue` |
| `page:estates.dashboard.monthlyReport` | C | spa | `bills/stat/_parts/MonthlyReport.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/bills/stat/_parts/Stat.jsx` |
| `page:estates.dashboard.monthlyStatement` | C | spa | `bills/stat/_parts/MonthlyReport.vue` | 只有同目錄兄弟頁有引用 |  | `src/pages/bills/stat/_parts/Stat.jsx` |
| `page:entrustedContracts.edit.payment` | D | spa | `entrustedContracts/edit/requirement/Payment.jsx` | 只有同目錄兄弟頁有引用 |  | `src/pages/entrustedContracts/edit/requirement/Basic.jsx`、`src/pages/entrustedContracts/edit/requirement/Fees.jsx` |
| `page:users.index` | A | spa | `users/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/users/advance/Index.jsx`、`src/pages/users/auth/Create.vue` |
| `page:bigLandlords.index` | B | spa | `bigLandlords/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/bigLandlords/list/_parts/PageTop.vue` |
| `page:bigLandlords.list` | B | spa | `bigLandlords/list/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（95 行，需人判） | `src/pages/bigLandlords/list/_parts/PageTop.vue` |
| `page:users.lesseeList` | B | spa | `users/lesseeList/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（183 行，需人判） | `src/pages/users/lesseeList/parts/ListTable.vue`、`src/pages/users/lesseeList/parts/PageTop.vue` |
| `page:communities.index` | C | spa | `communities/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/communities/edit/BalanceInvoice.jsx`、`src/pages/communities/edit/Index.vue` |
| `page:estates.edit` | C | spa | `estates/edit/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/estates/edit/rent_contact/Index.vue`、`src/pages/estates/edit/rent_detail/Index.jsx` |
| `page:estates.index` | C | spa | `estates/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/estates/edit/rent_contact/Index.vue`、`src/pages/estates/edit/rent_detail/Index.jsx` |
| `page:contracts.index` | D | spa | `contracts/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/contracts/pick/_parts/PageTop.vue` |
| `page:contracts.pick` | D | spa | `contracts/pick/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（704 行，需人判） | `src/pages/contracts/pick/_parts/PageTop.vue` |
| `page:entrustContracts.index` | D | spa | `entrustedContracts/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/entrustedContracts/edit/requirement/Basic.jsx`、`src/pages/entrustedContracts/edit/requirement/Fees.jsx` |
| `page:entrustedContracts.edit` | D | spa | `entrustedContracts/edit/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/entrustedContracts/edit/requirement/Basic.jsx`、`src/pages/entrustedContracts/edit/requirement/Fees.jsx` |
| `page:entrustedContracts.list` | D | spa | `entrustedContracts/list/Index.jsx` | 外殼頁、子元件有引用 | 無 router-view（224 行，需人判） | `src/pages/entrustedContracts/list/_parts/PageTop.jsx` |
| `page:bills.index` | E | spa | `bills/Index.jsx` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/bills/edit/Index.jsx`、`src/pages/bills/edit/_parts/BillBasicInfoSection.vue` |
| `page:listings.pricing` | I | spa | `listings/pricing/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/listings/pricing/Home.vue`、`src/pages/listings/pricing/TrialPlan.vue` |
| `page:users.payment.index` | I | spa | `users/payment/Index.vue` | 外殼頁、子元件有引用 | 含 router-view（純路由外殼） | `src/pages/users/payment/_parts/Invoice.vue`、`src/pages/users/payment/_parts/Newebpay.vue` |
| `page:users.subscription` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue` |
| `page:users.subscription.chose` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue` |
| `page:users.subscription.unsubscribe` | I | spa | `users/subscription/Index.vue` | 外殼頁、子元件有引用 | 無 router-view（57 行，需人判） | `src/pages/users/subscription/Chose.vue` |

## 4. 驗收紀錄

- 缺口頁數：pm 48＝183−135、prospect 135＝183−48；與 `endpoint_progress.py --ignore-review` 輸出 `正對照（不過濾已審）：頁面 不分身分 135／183；pm 135、prospect 48` 相符。
- 正對照：scratch 正本副本移除 `code:src/pages/bills/pick/Index.jsx` 的唯一引用（E.md 1 處）⇒ pm 覆蓋 135→134，新缺口只有 `page:bills.pick`。
- 外殼判讀以釘住匯出 `scratchpad/jgb2-b2ee2ac/src/pages/<component>` 是否含 `router-view`／`RouterView`／`Outlet` 判定（機械判讀，未逐頁人看）。
