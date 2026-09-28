# jgb2 疑似程式缺陷清單（Plan 9.19 S0，2026-09-28）

> **來源**：
> - 9.17 S1 審核單（`review-sheet-9.17-S1-ABC-20260928.md`）、9.18 S2 審核單（`review-sheet-9.18-S2-FGHI-20260928.md`）的 doubt 理由；
> - 9.15 G1 清單（`doc-fix-list-9.15-G1-20260927.md`）；
> - 9.16 §6。
>
> **只收錄「程式行為疑似缺陷」**：畫面或文案給出的承諾，和程式實際行為不一致；或是有使用者可見的錯誤。正本寫錯的項目不在此表，由正本修正處理。
>
> **程式證據**：依據 jgb2 釘住匯出 `scratchpad/jgb2-b2ee2ac/`（commit `b2ee2ac`）。每一項都用「檔案＋可 grep 字串」實跑 grep 確認命中。
> - 正對照 `app/Bill.php` `private function checkIotBill(` 命中 1。
> - 負對照：不存在的符號命中 0。
>
> ⛔ 本清單不裁決是否為缺陷，也不開 Monday 單；交業主決定。

## 使用者可見後果較明顯

| # | 疑似缺陷 | 使用者可見後果 | 證據（檔案＋grep 字串，命中數） | 相關細目 |
|---|---|---|---|---|
| D1 | 取消訂閱的通知名稱拼錯 | 取消訂閱後不會寄出 Email 通知 | `app/Http/Controllers/UserController.php` `Notification::notice('subscription_cancel'`（1）；`app/Notification.php` `case 'subscription_cance':`（1） | `jgb/I/subscription-cancel-effect` |
| D2 | 修繕「通知及同步租客」開關沒有綁到資料，房東建單一律 `is_notice_tenant=false` | 房東建的修繕單，租客在修繕列表看不到，也收不到通知 | `src/pages/repair/applyProcess/_parts/Detail.vue` `<SwitchButton :model="repairForm.is_notice_tenant" />`（1）；`app/Role.php` `->where('is_notice_tenant', 1)`（1） | `jgb/F/repair-apply-flow-and-entry`、`repair-apply-notifications`、`repair-notifications-by-stage` |
| D3 | 房東建修繕單時，預約時段第一列刪不掉，空值仍被存入 | 房東發起、沒填時段的單，也會出現空白的房客備註區 | `app/Http/Controllers/RepairController.php` `if (!empty($requestData['tenant_order_times'])) {`（1）；`src/pages/repair/edit/Index.vue` `<MemoArea v-if="!isEmpty(state?.tenant_order_times)"`（1） | `jgb/F/repair-edit-tenant-memo` |
| D4 | 官網首頁區塊用 `v-if` 判斷陣列，空陣列在 JS 裡也算成立 | 沒有資料時，「最新消息」「熱門物件」等區塊的標題與空輪播照樣出現 | `src/pages/listings/Home.vue` `<div v-if="news" class="w-full pt-12">`（1）、`<div v-if="hotListings"`（1） | `jgb/I/homepage-latest-news-section`、`homepage-sections-overview` |
| D5 | 社區公開頁的售價單價區間，後端寫死為空陣列 | 「售價單價區間」永遠不會顯示 | `app/Services/CommunityService.php` `'sell_price_range_per_unit' => [],`（1） | `jgb/C/community-show-price-range` |
| D6 | 物件公開頁傳給元件的 spaceType 是翻譯後的中文，元件卻拿英文 key 比對 | 所有商用物件都會顯示「座位數」，包含店面與整層空間 | `src/pages/estates/show/_parts/EstateBasicInfo.vue` `props.spaceType !== 'retail_shop' && props.spaceType !== 'office_flat'`（1）；`resources/views/estate/show.blade.php` `:space-type="{{ json_encode($labelsSpaceType[$premisesInfoBasic['space_type']]`（2） | `jgb/C/estate-house-info-card` |
| D7 | 通知中心的訊息類通知（type 32）引用了未定義變數 `userMessageData` | 點訊息類通知時，燈箱可能打不開或出錯 | `resources/views/notifications/index.blade.php` `if(data.type == 32)`（1） | `jgb/A/notification-mark-read-navigate` |
| D8 | 修改密碼頁寫「至少一位英文和數字」，但後端只驗 `min:6`；重設密碼的 regex 又和註冊規則不同 | 三處密碼規則不一致：可以設出不符畫面規則的密碼 | `app/Http/Controllers/UserController.php` `'password' => 'min:6|required_with`（2）；`app/Http/Controllers/AuthController.php` `regex:/(^[A-Za-z0-9*&-_]+$)+/`（1） | `jgb/A/account-change-password`、`forget-password-flow` |
| D9 | 社區名稱輸入框提示「限制 30 個字」，後端只驗 required | 超過 30 字也存得進去 | `app/Services/CommunityService.php` `"name" => "required"`（1） | `jgb/C/community-edit-basic-fields` |
| D10 | 物件總表在手機版把排序存到另一個鍵，進頁時只讀 `estatesList` | 手機上不會記住上次的排序 | `src/pages/estates/list/Index.vue` `genLocalSort({ to, from, next }, 'estatesList')`（1） | `jgb/C/estate-list-sort-remembers-last` |
| D11 | 租客列表 `currentRole` 只會回傳社宅或 default，特定合作團隊的欄位組永遠選不到 | 特定合作團隊看不到專屬欄位（國籍、生日、主要聯絡方式） | `src/pages/users/lesseeList/parts/ListTable.vue` `return 'default'`（1） | `jgb/B/lessee-list-columns-by-role` |
| D12 | 成員人數以 `member_list.length+1` 計，但 `member_list` 同時排除了擁有者和自己 | 非擁有者看成員頁時，「N 個成員」的數字少算 | `resources/views/users/team/index.blade.php` `t('[s1] 個成員', [$store.state.team.member_list.length+1])`（1） | `jgb/B/member-list-overview` |
| D13 | 任務管理器列表頁寫「前三十天」開單，新增頁寫「前 45 天」 | 兩頁說法矛盾 | `src/pages/control-panel/taskManagement/Index.vue` `指定週期的前三十天完成單據的開立`（1）；`src/pages/control-panel/taskManagement/edit/Index.jsx` `觸發時間前 45 天完成單據的開立`（1） | `jgb/I/task-manager-purpose` |
| D14 | 控制台「通知信設定」頁只有說明文字，沒有任何控制項，首頁卡片與側欄入口也已註解掉 | 直接開網址會進到一個不能用的頁面 | `src/pages/control-panel/notificationMail/Index.jsx` `<div class="row lg:flex-nowrap lg:justify-between">`（1） | `jgb/I/notification-mail-settings` |
| D15 | 電錶儲值燈箱留有 QA 用的自訂金額後門，程式標了 TODO 要移除 | 網址加 `customAmount=1` 就能輸入任意儲值金額 | `src/components/Lightbox/PowerMeterTopUp.vue` `route.query?.customAmount === '1'`（1） | `jgb/G/power-meter-topup-flow` |
| D20 | 租客列表頁的注意事項寫「關閉通知開關就收不到所有通知」，實際上 Email 與手機是兩個分開的開關，各自只停該管道 | 頁面說明與實際行為相反，房東可能誤以為關一個就全停 | `src/pages/users/lesseeList/parts/PageTop.vue` `當通知開關關閉時，租客將無法收到所有的通知`（1）；`src/pages/users/lesseeList/parts/ContactInfoBlock.jsx` `props?.is_tenant_registered === 1 && 'disabled'`（1） | `jgb/B/lessee-notification-toggle-effect` |

## 先前計畫已記錄、一併移交

| # | 疑似缺陷 | 使用者可見後果 | 證據 | 出處 |
|---|---|---|---|---|
| D16 | 合約「提前解約中」時，合約總表齒輪選單把「點退押金」誤寫成又一個「點交物件」 | 畫面出現兩個停用的「點交物件」 | `app/Http/Controllers/ContractController.php` `case Contract::CONTRACT_EARLY_TERMINATION`（6，需對 `webList` 內的那一處） | 9.15 G1 清單 |
| D17 | 事後以 Email 註冊時認領合約，用明文比對已加密的 `to_user_email` | 新資料可能無法自動認領合約 | `app/` 下 `receiveContractInvitation`（5 檔） | 9.16 §6 |
| D18 | 委託合約檢視頁上傳區寫 6MB，元件實際上限是 10MB | 文案與實際上限不符 | `src/pages/entrustedContracts/show/_parts/signerInfo/ArchiveFileUploader.jsx` `t('支援 PDF 檔，檔案大小最大 [s1] MB。', [6])`（1）；10MB 上限見 9.16 §6 | 9.16 §6 |
| D19 | `bills.one` 舊路由仍在，但通知連結已改走列表 `?id=` | 舊連結可能指向過時頁面 | `routes/web.php` `'BillController@one')->name('bills.one')`（1） | 9.16 §6 |

## 未收錄（判定為設計或正本寫法問題，不交產品）

- 即將額滿只發站內通知、剩 5 個時才寄一封 Email：屬通知設計，由正本修正處理。
- 幫助中心空白關鍵字不跳頁、LINE ID 非必填、編輯按鈕 editable 恆為 1 等：屬設計或不可見機制。
- 幫助中心 `paymentapply` 寫個人房東可選藍新（9.16 §6）：屬文件錯誤，已在 9.15 G1 文件清單類處理範圍。
