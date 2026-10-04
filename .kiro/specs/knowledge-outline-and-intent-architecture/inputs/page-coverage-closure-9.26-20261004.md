# Plan 9.26 附件：量尺改用頁面閉包後新增覆蓋的 pm 頁（2026-10-04 預跑）

> 量測：HEAD `60cc55df` 正本、已審且含 `property_manager` 的細目；舊量尺（只比入口檔）未覆蓋、新量尺（入口檔＋其 `src/pages` 內 import 與子路由閉包；blade 去 `#方法`）覆蓋的頁。每頁列命中細目數與一例「細目 → 命中檔」，供業主抽查是否合理。SPA 頁的命中檔取自閉包（`src/pages/` 底下）；blade 頁（`page:web:notifications.index`）的命中檔是細目 `sources` 去掉 `#方法` 後的 controller 檔，不在閉包內。⚠️ 閉包是代理指標：跨功能共用的子元件（例：差額發票編輯頁引用物件搜尋區塊）也會讓頁面被算入。

| 頁 | 命中細目數 | 例：細目 → 閉包內命中檔 |
|---|---|---|
| `page:web:notifications.index` | 6 | `jgb/A/notification-center-type-filter` → `app/Http/Controllers/NotificationController.php` |
| `page:balanceInvoices.edit` | 6 | `jgb/C/estate-list-filters` → `estates/list/_parts/EstatesAdvanceSearchBlock.jsx` |
| `page:balanceInvoices.edit.belongingEstates` | 1 | `jgb/E/balance-invoice-pick-and-individual-rent` → `balanceInvoices/_parts/IndividualBaseRentSetting.vue` |
| `page:balanceInvoices.index` | 6 | `jgb/E/balance-invoice-group-statuses` → `balanceInvoices/list/_parts/ListTable.vue` |
| `page:balanceInvoices.list` | 2 | `jgb/E/balance-invoice-group-statuses` → `balanceInvoices/list/_parts/ListTable.vue` |
| `page:bigLandlords.index` | 5 | `jgb/B/biglandlord-list-overview` → `bigLandlords/list/_parts/ListTable.vue` |
| `page:bigLandlords.list` | 3 | `jgb/B/biglandlord-list-overview` → `bigLandlords/list/_parts/ListTable.vue` |
| `page:bigLandlords.report` | 2 | `jgb/B/biglandlord-report-overview` → `bigLandlords/report/_parts/BigLandlordItemDetail.jsx` |
| `page:bills.index` | 25 | `jgb/A/dashboard-big-landlord-view` → `users/dashboard/parts/EstateDetails.vue` |
| `page:communities.forceBinding` | 11 | `jgb/C/community-edit-basic-fields` → `communities/edit/Basic.vue` |
| `page:communities.index` | 14 | `jgb/C/community-list-overview-stats` → `communities/_parts/CommunityItem.vue` |
| `page:contracts.edit.facilities` | 3 | `jgb/D/contract-facilities-tab` → `contracts/edit/facilities/General.vue` |
| `page:contracts.edit.publicNotary` | 2 | `jgb/D/social-housing-notary` → `contracts/edit/publicNotary/SocialHousing.vue` |
| `page:contracts.edit.rentBasic` | 8 | `jgb/D/contract-rentbasic-template-and-dates` → `contracts/edit/rentBasic/General.vue` |
| `page:contracts.edit.situation` | 2 | `jgb/D/contract-situation-tab` → `contracts/edit/situation/General.vue` |
| `page:contracts.edit.socialHousing.facilities` | 3 | `jgb/D/contract-facilities-tab` → `contracts/edit/facilities/General.vue` |
| `page:contracts.edit.socialHousing.publicNotary` | 2 | `jgb/D/social-housing-notary` → `contracts/edit/publicNotary/SocialHousing.vue` |
| `page:contracts.edit.socialHousing.rentBasic` | 8 | `jgb/D/contract-rentbasic-template-and-dates` → `contracts/edit/rentBasic/General.vue` |
| `page:contracts.edit.socialHousing.situation` | 2 | `jgb/D/contract-situation-tab` → `contracts/edit/situation/General.vue` |
| `page:contracts.index` | 16 | `jgb/D/contract-list-status-tabs` → `contracts/list/_parts/PageTop.vue` |
| `page:entrustContracts.index` | 2 | `jgb/D/entrusted-contract-what-is-it` → `entrustedContracts/list/_parts/PageTop.jsx` |
| `page:entrustedContracts.list` | 2 | `jgb/D/entrusted-contract-what-is-it` → `entrustedContracts/list/_parts/PageTop.jsx` |
| `page:estates.dashboard.bills` | 1 | `jgb/E/bill-internal-note-visibility` → `bills/_parts/ListTable.jsx` |
| `page:estates.index` | 10 | `jgb/B/advance-custom-label` → `estates/list/Index.vue` |
| `page:estates.pick` | 6 | `jgb/C/estate-list-filters` → `estates/list/_parts/EstatesAdvanceSearchBlock.jsx` |
| `page:listings.pricing` | 7 | `jgb/I/pricing-plan-tiers-overview` → `listings/pricing/Home.vue` |
| `page:users.dashboard` | 7 | `jgb/A/dashboard-overview-blocks` → `users/dashboard/Landlord.vue` |
| `page:users.forget` | 5 | `jgb/A/register-verify-code-shape` → `users/auth/parts/VerifyPanel.vue` |
| `page:users.index` | 63 | `jgb/A/dashboard-overview-blocks` → `users/dashboard/Landlord.vue` |
| `page:users.lesseeList` | 13 | `jgb/B/lessee-tabs` → `users/lesseeList/parts/ListTable.vue` |
| `page:users.payment.index` | 14 | `jgb/E/payment-gateway-fees` → `users/payment/_parts/Newebpay.vue` |
| `page:users.subscription` | 8 | `jgb/I/pricing-free-vs-experience-plan` → `users/subscription/Chose.vue` |
| `page:users.subscription.chose` | 8 | `jgb/I/pricing-free-vs-experience-plan` → `users/subscription/Chose.vue` |
| `page:users.subscription.unsubscribe` | 8 | `jgb/I/pricing-free-vs-experience-plan` → `users/subscription/Chose.vue` |
| `page:users.verify` | 4 | `jgb/A/register-phone-bind` → `users/auth/parts/PhoneVerify.vue` |

共 35 頁。
