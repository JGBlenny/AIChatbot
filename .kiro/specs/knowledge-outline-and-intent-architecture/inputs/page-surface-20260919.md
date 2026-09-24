# 大綱覆蓋基準：JGB 頁面樹（步 0a，DSP-065）— master @ b2ee2ac382ce

SPA 路由檔 15、具名路由 200；blade 頁 28（web.php GET/match 536：vueIndex 55、內部 172、api 路徑 56、無 view 217、controller 缺 8）。
格 228＝基準 183＋租客側 0（未開）＋住都專屬 10（不入基準）＋不計 35（無頁面元件 6＋非功能 29）。正本 210 條。

## A（14 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `notifications.index` | `/{type?}` | NotificationController@index | routes/web.php |
| `users.account` | `/account` | UserController@account | routes/web.php |
| `users.roleTenant` | `/roleTenant` | UserController@roleTenant | routes/web.php |
| `users.create` | `/users/create` | users/auth/Create.vue | users.js |
| `users.dashboard` | `` | users/dashboard/Index.vue | users.js |
| `users.forget` | `/users/forget/:which?` | users/auth/Forget.vue | users.js |
| `users.forget.account` | `account` | users/auth/parts/forget/Account.vue | users.js |
| `users.forget.password` | `password/:type?` | users/auth/parts/forget/Password.vue | users.js |
| `users.index` | `/users` | users/Index.vue | users.js |
| `users.login` | `/users/login` | users/auth/Login.vue | users.js |
| `users.notification` | `notification` | users/notification/Index.vue | users.js |
| `users.signer_info` | `signer_info` | users/signerInfo/Index.vue | users.js |
| `users.verify` | `/users/verify/:which?` | users/auth/Verify.vue | users.js |
| `users.verify.phone` | `phone` | users/auth/parts/PhoneVerify.vue | users.js |

## B（10 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `users.role` | `/role` | UserController@role | routes/web.php |
| `users.team` | `/team/{type?}/{action?}/{actionType?}` | UserController@team | routes/web.php |
| `bigLandlords.index` | `/bigLandlords` | bigLandlords/Index.jsx | bigLandlords.js |
| `bigLandlords.list` | `/bigLandlords/list` | bigLandlords/list/Index.jsx | bigLandlords.js |
| `bigLandlords.report` | `/bigLandlords/report` | bigLandlords/report/Index.vue | bigLandlords.js |
| `bigLandlords.sheet` | `/bigLandlords/sheet/:bigLandlord_id/:role_id?` | bigLandlords/sheet/index.vue | bigLandlords.js |
| `users.team.owned` | `/bigLandlords/owned/:id` | bigLandlords/list/_parts/owned.jsx | bigLandlords.js |
| `users.advance` | `advance` | users/advance/Index.jsx | users.js |
| `users.lesseeList` | `/users/lesseeList` | users/lesseeList/Index.vue | users.js |
| `users.team.member.owned` | `team/member/owned/:category/:uid` | users/team/memberOwned/Index.jsx | users.js |

## C（43 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `estates.house` | `/house/{no}/{action?}` | EstateController@house | routes/web.php |
| `estates.show` | `/show/{id}/{action?}` | EstateController@show | routes/web.php |
| `share` | `/share/{action}/{id?}` | IndexController@share | routes/web.php |
| `communities.edit` | `/communities/edit/:communityId` | communities/edit/Index.vue | communities.js |
| `communities.edit.basic` | `basic` | communities/edit/Basic.vue | communities.js |
| `communities.edit.gallery` | `gallery` | communities/edit/Gallery.vue | communities.js |
| `communities.edit.intros` | `intros` | communities/edit/Intros.vue | communities.js |
| `communities.estates` | `estates/:communityId/:category?` | communities/estates/Index.vue | communities.js |
| `communities.forceBinding` | `/communities/forceBinding` | communities/forceBinding/Index.vue | communities.js |
| `communities.forceBinding.edit` | `edit` | communities/forceBinding/edit/Index.vue | communities.js |
| `communities.forceBinding.edit.binding` | `binding` | communities/forceBinding/edit/Binding.vue | communities.js |
| `communities.forceBinding.welcome` | `` | communities/forceBinding/Welcome.vue | communities.js |
| `communities.index` | `/communities` | communities/Index.vue | communities.js |
| `communities.list` | `` | communities/list/Index.vue | communities.js |
| `communities.pick` | `pick/:action` | communities/pick/Index.vue | communities.js |
| `communities.show` | `/communities/show/:communityId` | communities/show/Index.vue | communities.js |
| `estates.dashboard` | `/estates/dashboard/:id` | estates/dashboard/Index.vue | estates.js |
| `estates.dashboard.attachments` | `attachments` | estates/dashboard/attachments/Index.vue | estates.js |
| `estates.dashboard.bills` | `bills/:tab?` | estates/dashboard/bills/Index.vue | estates.js |
| `estates.dashboard.contractAttachments` | `contractAttachments` | estates/dashboard/contractAttachments/index.vue | estates.js |
| `estates.dashboard.contracts` | `contracts` | estates/dashboard/contracts/Index.vue | estates.js |
| `estates.dashboard.memos` | `memos` | estates/dashboard/memos/Index.vue | estates.js |
| `estates.dashboard.monthlyReport` | `monthlyReport` | bills/stat/_parts/MonthlyReport.vue | estates.js |
| `estates.dashboard.monthlyStatement` | `monthlyStatement` | bills/stat/_parts/MonthlyReport.vue | estates.js |
| `estates.dashboard.rent` | `rent` | estates/dashboard/rent/Index.vue | estates.js |
| `estates.dashboard.repair` | `repair` | estates/dashboard/repair/Index.vue | estates.js |
| `estates.dashboard.runnings` | `runnings` | estates/dashboard/runnings/Index.vue | estates.js |
| `estates.edit` | `/estates/edit/:id` | estates/edit/Index.vue | estates.js |
| `estates.edit.basic` | `basic` | estates/edit/basic/Index.vue | estates.js |
| `estates.edit.building_transcript` | `buildingTranscript` | estates/edit/building_transcript/Index.vue | estates.js |
| `estates.edit.building_transcript_general` | `buildingTranscriptGeneral` | estates/edit/buildingTranscriptGeneral/Index.vue | estates.js |
| `estates.edit.facilities` | `facilities` | estates/edit/facilities/Index.vue | estates.js |
| `estates.edit.gallery` | `gallery` | estates/edit/gallery/Index.vue | estates.js |
| `estates.edit.intro` | `intro` | estates/edit/intro/Index.vue | estates.js |
| `estates.edit.rent_contact` | `rent_contact` | estates/edit/rent_contact/Index.vue | estates.js |
| `estates.edit.rent_detail` | `rent_detail` | estates/edit/rent_detail/Index.jsx | estates.js |
| `estates.edit.rent_verify` | `rent_verify` | estates/edit/rent_verify/Index.vue | estates.js |
| `estates.edit.vr` | `vr` | estates/edit/vr/Index.vue | estates.js |
| `estates.index` | `/estates/:category?` | estates/Index.vue | estates.js |
| `estates.list` | `` | estates/list/Index.vue | estates.js |
| `estates.monthlyUpload` | `/estates/monthlyUpload/:action` | estates/dashboard/_parts/MonthlyUpload.jsx | estates.js |
| `estates.pick` | `/estates/pick/:action` | estates/pick/Index.jsx | estates.js |
| `users.public` | `/p/:encryptId?/:mode?/:premisesUseFor?` | users/public/Index.vue | users.js |

## D（57 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `contracts.early_termination` | `/early_termination/{id?}/{action?}` | ContractController@earlyTermination | routes/web.php |
| `contracts.move_in` | `/move_in/{id?}/{action?}` | ContractController@moveIn | routes/web.php |
| `contracts.show` | `/show/{id?}/{action?}` | ContractController@show | routes/web.php |
| `contracts.sign` | `/sign/{id?}/{action?}` | ContractController@sign | routes/web.php |
| `contracts.thinkcloud` | `/thinkcloud/{id?}/{type?}/{action?}` | ContractController@thinkcloud | routes/web.php |
| `contracts.edit` | `/contracts/edit/:id` | contracts/edit/Index.vue | contracts.js |
| `contracts.edit.additionalConvention` | `additionalConvention` | contracts/edit/additionalConvention/Index.vue | contracts.js |
| `contracts.edit.billSetting` | `billSetting` | contracts/edit/billSetting/Index.jsx | contracts.js |
| `contracts.edit.buildingTranscript` | `buildingTranscript` | contracts/edit/buildingTranscript/General.vue | contracts.js |
| `contracts.edit.dealerBasic` | `dealerBasic` | contracts/edit/dealerBasic/Index.vue | contracts.js |
| `contracts.edit.facilities` | `facilities` | contracts/edit/facilities/Index.vue | contracts.js |
| `contracts.edit.landlordAttachment` | `landlordAttachment` | contracts/edit/landlordAttachment/Index.vue | contracts.js |
| `contracts.edit.payment` | `payment` | contracts/edit/payment/Index.vue | contracts.js |
| `contracts.edit.publicNotary` | `publicNotary` | contracts/edit/publicNotary/Index.vue | contracts.js |
| `contracts.edit.rent` | `rent` | contracts/edit/rent/Index.jsx | contracts.js |
| `contracts.edit.rentAdjustment` | `rentAdjustment` | contracts/edit/rentAdjustment/Index.vue | contracts.js |
| `contracts.edit.rentBasic` | `basic` | contracts/edit/rentBasic/Index.vue | contracts.js |
| `contracts.edit.situation` | `situation` | contracts/edit/situation/Index.vue | contracts.js |
| `contracts.edit.socialHousing.attachments` | `attachments` | contracts/edit/attachments/Index.vue | contracts.js |
| `contracts.edit.socialHousing.buildingTranscript` | `buildingTranscript` | contracts/edit/buildingTranscript/SocialHousing.vue | contracts.js |
| `contracts.edit.socialHousing.dealerBasic` | `dealerBasic` | contracts/edit/dealerBasic/Index.vue | contracts.js |
| `contracts.edit.socialHousing.facilities` | `facilities` | contracts/edit/facilities/Index.vue | contracts.js |
| `contracts.edit.socialHousing.landlordAttachment` | `landlordAttachment` | contracts/edit/landlordAttachment/Index.vue | contracts.js |
| `contracts.edit.socialHousing.landlordBasic` | `landlordBasic` | contracts/edit/landlordBasic/Index.vue | contracts.js |
| `contracts.edit.socialHousing.landlordLicense` | `landlordLicense` | contracts/edit/landlordLicense/Index.vue | contracts.js |
| `contracts.edit.socialHousing.moveIn` | `moveIn` | contracts/edit/moveIn/Index.vue | contracts.js |
| `contracts.edit.socialHousing.payment` | `payment` | contracts/edit/payment/Index.vue | contracts.js |
| `contracts.edit.socialHousing.photos` | `photos` | contracts/edit/photos/Index.vue | contracts.js |
| `contracts.edit.socialHousing.publicNotary` | `publicNotary` | contracts/edit/publicNotary/Index.vue | contracts.js |
| `contracts.edit.socialHousing.rent` | `rent` | contracts/edit/rent/Index.jsx | contracts.js |
| `contracts.edit.socialHousing.rentBasic` | `basic` | contracts/edit/rentBasic/Index.vue | contracts.js |
| `contracts.edit.socialHousing.situation` | `situation` | contracts/edit/situation/Index.vue | contracts.js |
| `contracts.edit.socialHousing.subsidyTerms` | `subsidyTerms` | contracts/edit/subsidyTerms/Index.vue | contracts.js |
| `contracts.edit.socialHousing.tenantAttachment` | `tenantAttachment` | contracts/edit/tenantAttachment/Index.vue | contracts.js |
| `contracts.edit.socialHousing.tenantBasic` | `tenantBasic` | contracts/edit/tenantBasic/Index.vue | contracts.js |
| `contracts.edit.socialHousing.tenantHousehold` | `tenantHousehold` | contracts/edit/tenantHousehold/Index.vue | contracts.js |
| `contracts.edit.socialHousing.tenantLicense` | `tenantLicense` | contracts/edit/tenantLicense/Index.vue | contracts.js |
| `contracts.edit.taxAndInvoice` | `taxAndInvoice` | contracts/edit/taxAndInvoice/index.jsx | contracts.js |
| `contracts.edit.tenantInfo` | `tenantInfo` | contracts/edit/tenantInfo/Index.jsx | contracts.js |
| `contracts.index` | `/contracts/:status?` | contracts/Index.vue | contracts.js |
| `contracts.list` | `` | contracts/list/Index.vue | contracts.js |
| `contracts.moveIn` | `/contracts/sh-move-in/:id` | contracts/move-in/Index.vue | contracts.js |
| `contracts.moveOut` | `/contracts/move-out/:id` | contracts/move-out/Index.jsx | contracts.js |
| `contracts.pick` | `pick/:action/:id?` | contracts/pick/Index.jsx | contracts.js |
| `contracts.renew` | `renew` | contracts/renew/Index.vue | contracts.js |
| `contracts.renew.preview` | `renew/preview` | contracts/renew/Preview.vue | contracts.js |
| `contracts.search` | `search` | contracts/list/Index.vue | contracts.js |
| `contracts.show` | `/contracts/sh-show/:id` | contracts/show/Index.vue | contracts.js |
| `entrustContracts.index` | `/entrustedContracts/:status?` | entrustedContracts/Index.jsx | entrustedContracts.js |
| `entrustedContracts.edit` | `/entrustedContracts/:id/edit` | entrustedContracts/edit/Index.jsx | entrustedContracts.js |
| `entrustedContracts.edit.basic` | `basic` | entrustedContracts/edit/requirement/Basic.jsx | entrustedContracts.js |
| `entrustedContracts.edit.fee` | `fee` | entrustedContracts/edit/requirement/Fees.jsx | entrustedContracts.js |
| `entrustedContracts.edit.landlord_info` | `landlord_info` | entrustedContracts/edit/landlordInfo/LandlordInfo.jsx | entrustedContracts.js |
| `entrustedContracts.edit.manager_info` | `manager_info` | entrustedContracts/edit/managerInfo/ManagerInfo.jsx | entrustedContracts.js |
| `entrustedContracts.edit.payment` | `payment` | entrustedContracts/edit/requirement/Payment.jsx | entrustedContracts.js |
| `entrustedContracts.list` | `` | entrustedContracts/list/Index.jsx | entrustedContracts.js |
| `entrustedContracts.show` | `/entrustedContracts/show/:id?` | entrustedContracts/show/Index.jsx | entrustedContracts.js |

## E（22 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `/pick/{action?}` | `/pick/{action?}` | BillController@pick | routes/web.php |
| `bills.one` | `/one/{type}/{status}/{id}` | BillController@one | routes/web.php |
| `users.add_merchant` | `/add_merchant/{manufacturer?}` | UserController@addMerchant | routes/web.php |
| `balanceInvoices.edit` | `/balanceinvoices/edit/:groupId` | balanceInvoices/edit/Index.vue | balanceInvoices.js |
| `balanceInvoices.edit.basicInfo` | `basicInfo/:isCreateNew` | balanceInvoices/edit/basicInfo/Index.vue | balanceInvoices.js |
| `balanceInvoices.edit.belongingEstates` | `belongingEstates/:isCreateNew` | balanceInvoices/edit/belongingEstates/Index.vue | balanceInvoices.js |
| `balanceInvoices.edit.pickEstates` | `pickEstates/:isCreateNew` | balanceInvoices/edit/pickEstates/Index.vue | balanceInvoices.js |
| `balanceInvoices.groups` | `groups/:groupId?` | balanceInvoices/groups/Index.vue | balanceInvoices.js |
| `balanceInvoices.index` | `/balanceinvoices` | balanceInvoices/Index.vue | balanceInvoices.js |
| `balanceInvoices.list` | `list/:status?` | balanceInvoices/list/Index.vue | balanceInvoices.js |
| `bills.create` | `create` | bills/edit/Index.jsx | bills.js |
| `bills.create.batch` | `create/batch` | bills/edit/Index.jsx | bills.js |
| `bills.create.cycleBatch` | `create/cycleBatch` | bills/edit/Index.jsx | bills.js |
| `bills.edit` | `edit/:billId?` | bills/edit/Index.jsx | bills.js |
| `bills.index` | `/bills` | bills/Index.jsx | bills.js |
| `bills.list` | `:type?/:status?` | bills/list/Index.jsx | bills.js |
| `bills.pick` | `pick/:action?` | bills/pick/Index.jsx | bills.js |
| `bills.sheet` | `/bills/sheet` | bills/sheet/Index.vue | bills.js |
| `bills.socialHousingSheets` | `/bills/socialHousingSheets/:version?` | bills/socialHousingSheets/Index.vue | bills.js |
| `bills.stat` | `stat/:target?` | bills/stat/Index.jsx | bills.js |
| `communities.edit.balanceInvoice` | `balanceInvoice` | communities/edit/BalanceInvoice.jsx | communities.js |
| `users.rechargeAccountList` | `/users/rechargeAccountList` | users/rechargeAccountList/Index.vue | users.js |

## F（10 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `/repair/{any?}/{any2?}` | `/repair/{any?}/{any2?}` | IndexController@repairIndex | routes/web.php |
| `repair` | `/repair` | repair/Index.vue | repairs.js |
| `repair.apply` | `/repair/apply` | repair/Index.vue | repairs.js |
| `repair.applyProcess` | `/repair/applyProcess/:step?` | repair/applyProcess/Index.vue | repairs.js |
| `repair.archive` | `/repair/archive` | repair/Index.vue | repairs.js |
| `repair.assign` | `/repair/assign` | repair/Index.vue | repairs.js |
| `repair.complete` | `/repair/complete` | repair/Index.vue | repairs.js |
| `repair.edit` | `/repair/edit/:id?` | repair/edit/Index.vue | repairs.js |
| `repair.finish` | `/repair/finish` | repair/Index.vue | repairs.js |
| `repair.share` | `/repair/share/:id?` | repair/share/Index.vue | repairs.js |

## G（4 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `/{deviceType}/{params?}` | `/{deviceType}/{params?}` | IotController@index | routes/web.php |
| `powerMeter.list` | `:type` | iots/list/Index.jsx | iots.js |
| `powerMeter.single` | `single/:iotId` | iots/_parts/Single.vue | iots.js |
| `tools.unlock` | `/unlock/:iotId/:batch` | tools/unlock/Index.vue | tools.js |

## H（5 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `/help/{any?}/{slug?}` | `/help/{any?}/{slug?}` | ListingController@index | routes/web.php |
| `listings.helpCenter` | `/help` | help-center/Index.vue | listings.js |
| `listings.helpCenter.group` | `group/:slug?` | help-center/Group.vue | listings.js |
| `listings.helpCenter.post` | `post/:slug?` | help-center/Post.vue | listings.js |
| `listings.helpCenter.search` | `search` | help-center/Search.vue | listings.js |

## I（18 格）

| 格 | 路徑 | 頁面／controller | 來源 |
|---|---|---|---|
| `customers.tcloud` | `/tcloud/{action?}/{id?}/{sign?}` | CustomerController@tcloud | routes/web.php |
| `indexs` | `/` | ListingController@index | routes/web.php |
| `controlPanel.index` | `/controlPanel` | control-panel/Index.vue | controlPanel.js |
| `controlPanel.setting` | `/controlPanel/setting` | control-panel/setting/Index.jsx | controlPanel.js |
| `notificationMail` | `notificationMail` | control-panel/notificationMail/Index.jsx | controlPanel.js |
| `taskManagement` | `taskManagement` | control-panel/taskManagement/Index.vue | controlPanel.js |
| `taskManagement.create` | `taskManagement/create` | control-panel/taskManagement/edit/Index.jsx | controlPanel.js |
| `taskManagement.edit` | `taskManagement/edit/:id?` | control-panel/taskManagement/edit/Index.jsx | controlPanel.js |
| `listings.demoForm` | `/demo-form` | listings/DemoForm.vue | listings.js |
| `listings.pricing` | `/pricing` | listings/pricing/Index.vue | listings.js |
| `listings.pricing.TrialPlan` | `/pricing/trial-plan` | listings/pricing/TrialPlan.vue | listings.js |
| `users.orders` | `orders` | users/orders/Index.vue | users.js |
| `users.payment.add` | `add/:vendorKey?` | users/payment/routerView/Add.vue | users.js |
| `users.payment.detail` | `detail/:vendorKey/:vendorId` | users/payment/routerView/Detail.vue | users.js |
| `users.payment.index` | `payment` | users/payment/Index.vue | users.js |
| `users.subscription` | `/users/subscription` | users/subscription/Index.vue | users.js |
| `users.subscription.chose` | `/users/subscription/chose` | users/subscription/Index.vue | users.js |
| `users.subscription.unsubscribe` | `/users/subscription/unsubscribe` | users/subscription/Index.vue | users.js |

## 不入基準（租客側／住都／不計）

| 格 | 原因 | 路徑 |
|---|---|---|
| `/import` | 不計（非功能） | `/import` |
| `/view` | 不計（非功能） | `/view` |
| `/{any?}/{any2?}/{any3?}/{any4?}` | 不計（非功能） | `/{any?}/{any2?}/{any3?}/{any4?}` |
| `customers.demand` | 不計（非功能） | `/demand/{action?}/{id?}` |
| `estates.sell-house` | 不計（非功能） | `/sell-house/{no}/{action?}` |
| `estates.sell-show` | 不計（非功能） | `/sell-show/{id}/{action?}` |
| `lines.liff` | 不計（非功能） | `/liff` |
| `contracts.edit.404` | 不計（無頁面元件：父／轉址／catch-all） | `:pathMatch(.*)*` |
| `entrustedContracts.edit.404` | 不計（無頁面元件：父／轉址／catch-all） | `:pathMatch(.*)*` |
| `estates.dashboard.404` | 不計（無頁面元件：父／轉址／catch-all） | `:pathMatch(.*)*` |
| `estates.dashboard.sell` | 不計（非功能） | `sell` |
| `estates.edit.404` | 不計（無頁面元件：父／轉址／catch-all） | `:pathMatch(.*)*` |
| `estates.edit.sell_contact` | 不計（非功能） | `sell_contact` |
| `estates.edit.sell_detail` | 不計（非功能） | `sell_detail` |
| `404` | 不計（非功能） | `/:pathMatch(.*)*` |
| `marketing.welcome-bonus` | 不計（非功能） | `/welcome-bonus` |
| `vite` | 不計（非功能） | `/vite` |
| `listings.IOTDevice` | 不計（非功能） | `/iot-device` |
| `listings.TA` | 不計（非功能） | `/TA` |
| `listings.about` | 不計（非功能） | `/about` |
| `listings.advantages` | 不計（非功能） | `/advantages` |
| `listings.features` | 不計（非功能） | `/features` |
| `listings.home` | 不計（非功能） | `/` |
| `listings.home.cn` | 不計（非功能） | `/cn` |
| `listings.home.en` | 不計（非功能） | `/en` |
| `listings.home.jp` | 不計（非功能） | `/jp` |
| `listings.home.th` | 不計（非功能） | `/th` |
| `listings.home.vn` | 不計（非功能） | `/vn` |
| `listings.map` | 不計（非功能） | `/map` |
| `listings.search` | 不計（非功能） | `/search` |
| `listings.sitemap` | 不計（非功能） | `/sitemap` |
| `resultScreen` | 不計（非功能） | `/resultScreen/:page` |
| `nthurc.edit` | 住都專屬 | `/nthurc/projects/edit/:projectId` |
| `nthurc.edit.basic` | 住都專屬 | `basic` |
| `nthurc.edit.tenantList` | 住都專屬 | `tenantList/:type?` |
| `nthurc.list` | 住都專屬 | `` |
| `nthurc.parking.edit` | 住都專屬 | `/nthurc-parking/projects/edit/:projectId` |
| `nthurc.parking.edit.basic` | 住都專屬 | `basic` |
| `nthurc.parking.edit.tenantList` | 住都專屬 | `tenantList/:type?` |
| `nthurc.parking.list` | 住都專屬 | `` |
| `nthurc.parking.projects` | 住都專屬 | `/nthurc-parking/projects` |
| `nthurc.projects` | 住都專屬 | `/nthurc/projects` |
| `users.approval` | 不計（非功能） | `approval` |
| `users.forget.index` | 不計（無頁面元件：父／轉址／catch-all） | `` |
| `users.verify.index` | 不計（無頁面元件：父／轉址／catch-all） | `` |
