# 審核單：Plan 9.20 S2 F～I 修正後重新先審（60 條）

> 審閱的正本版本：commit `46234eb0`。本單由 `scratchpad/p920-w1/review_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 52／doubt 8／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） `F-repair-list`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/F/repair-status-tabs` 修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存）
- [pass] `jgb/F/repair-view-only-roles` 哪些身分會看到「查看」而不是「編輯＆查看」的齒輪按鈕文字？（大房東角色，以及對這張單只有「顯示所屬」、沒有「顯示所有」修繕資料權限的團隊成員；但這張單的經理人本人看到的仍是「編輯＆查看」）

回覆：

## 報修申請流程 `F-repair-apply`（待審 8 條：pass 7／doubt 1／未先審 0）

- [pass] `jgb/F/repair-apply-without-contract` 沒有租約在跑的物件也能申請修繕嗎？（可以，房東方只要建好物件就能申請，不用先有合約）
- [pass] `jgb/F/repair-apply-category-item-other` 報修分類項目怎麼選？（分類與項目都是系統設定的清單，選好之後在報修細節可以按「編輯」回上一步重選；有一個特定分類會多出讓使用者自己輸入名稱的欄位）
- [pass] `jgb/F/repair-apply-detail-fields` 報修細節要填什麼？（項目分類、問題必填；預約時段依身分決定是否必填；緊急修繕、佐證照片、備註選填；「通知及同步租客」是房東代租客申請時會看到的一個開關，但目前沒有實際作用）
- [pass] `jgb/F/repair-apply-reservation-slots` 預約時段規則是什麼？（畫面上標示為必填，但實際上只有租客身分申請時系統才會擋下沒填的情況；房東申請時就算不填也能送出）
- [pass] `jgb/F/repair-apply-photo-limit` 報修可以附照片或影片嗎？（照片最多 10 張；影片最長 30 秒或 100MB；支援 jpeg／jpg／png 圖片與 mov／mp4／webm 影片）
- [pass] `jgb/F/repair-apply-notifications` 新增修繕單後誰會收到通知？（租客送出時通知房東方；房東方在網頁上建立時只寄 Email 給房東方，租客不會收到通知）
- [pass] `jgb/F/repair-notifications-by-stage` 安排廠商、完成修繕、結單時還會發哪些通知？（租客只有在這張修繕單會通知租客時才收得到；結單只寄 Email）
- [doubt] `jgb/F/repair-apply-flow-and-entry` 怎麼申請修繕單？（【修繕管理】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換） —— 句序 1：第 1 句與標題把入口寫死成【修繕管理】>【修繕單總表】，但第 3、4 句明講租客也走這個流程；程式裡租客側欄的選單名稱是【我的報修】，所以這句漏了租客身分的例外

回覆：

## 修繕單編輯 `F-repair-edit`（待審 10 條：pass 9／doubt 1／未先審 0）

- [pass] `jgb/F/repair-edit-progress-timeline` 修繕單細節頁的進度時間軸顯示什麼？（申請修繕、安排修繕、完成修繕、結單、封存五個階段，以及各階段對應的日期）
- [pass] `jgb/F/repair-edit-print` 修繕單細節頁怎麼列印？（右上角有「列印」按鈕，會叫出瀏覽器內建的列印視窗，可以印出來或存成 PDF）
- [pass] `jgb/F/repair-edit-switch-status` 修繕單細節頁怎麼切換狀態？（下拉選單直接選要換到哪個階段，按「變更」儲存）
- [pass] `jgb/F/repair-edit-cannot-edit-roles` 誰不能編輯修繕單細節頁？（租客帳號、大房東角色不能切換狀態、不能改廠商資訊、不能寫房東備註；租客只能編輯自己的房客備註）
- [pass] `jgb/F/repair-edit-application-detail-readonly` 修繕單細節頁顯示哪些報修時填的資料？（「細節補充」區塊底下：申請日期、是否緊急、照片、聯絡電話或 Email、物件區域與時區、分類項目、問題、備註、預約時段；房東方才看得到「細節補充」這個標題與說明文字）
- [pass] `jgb/F/repair-edit-vendor-assign` 怎麼安排修繕廠商？（填寫修繕時間、廠商名稱、維修人員、聯絡電話，儲存後會留下歷史紀錄可以展開查看）
- [pass] `jgb/F/repair-edit-landlord-complete-memo` 「房東備註」要填什麼？（完成時間、備註文字最多 300 字、可以附照片，最多 10 張、單檔最大 10MB、支援 JPG／PNG／PDF；只有有編輯權限的房東方帳號能編輯）
- [pass] `jgb/F/repair-edit-tenant-memo` 「房客備註」是什麼？（右邊那一欄，放租客的備註文字與照片，只有租客自己能編輯；從網頁建立的修繕單都會顯示這一欄）
- [pass] `jgb/F/repair-edit-share-to-vendor` 怎麼把修繕單分享出去給廠商？（在修繕單細節頁點「分享」，電腦上可以複製連結或用 LINE 分享，手機上會直接叫出手機的分享選單；廠商點開連結不需要登入 JGB 帳號）
- [doubt] `jgb/F/repair-edit-amount-visibility` 修繕結算金額誰看得到？（「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；填了金額不會自動產生帳單） —— 句序 1：講法「修繕結算金額怎麼填」「完成修繕怎麼登記費用」用內文答不出來：兩句只講誰看得到、會不會變成帳單，沒講是在「完成修繕」>「房東備註」的編輯模式裡填金額

回覆：

## 修繕單分享頁 `F-repair-share`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/F/repair-share-no-expiry` 分享連結會過期嗎？（目前不會，沒有天數限制）

回覆：

## 電表列表與單一電表 `G-power-meter`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/G/power-meter-vendor-unreachable` 電錶顯示目前連不上廠商怎麼辦？（度數不會更新、儲值送不出去；全站共用連線的廠商業者跟租客都看得到，以團隊帳號連線的廠商只有業者在清單頁看得到）
- [pass] `jgb/G/iot-entry-requirements` 電錶／門鎖／攝影機／小白盒頁面需要什麼條件才能進入？（房東方要有生效中的訂閱，而且方案有開放智能裝置功能；租客不受限制）

回覆：

## 裝置頁（門鎖、攝影機、小白盒） `G-device-page`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/G/device-edit-tabs-by-type` 裝置編輯頁的頁籤，門鎖跟攝影機／小白盒不一樣？（門鎖多出密碼設定、開門記錄兩個頁籤）
- [pass] `jgb/G/device-lock-passwords-three-types` 門鎖密碼有哪三種？（房東個人密碼、租客個人密碼、租客共用密碼，權限各不同）

回覆：

## 遠端解鎖（輸入解鎖密碼開門） `G-remote-unlock`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/G/remote-unlock-page` 遠端解鎖連結怎麼用？（輸入共用密碼按開門，密碼錯誤或連結失效會提示原因）
- [pass] `jgb/G/remote-unlock-no-login` 遠端解鎖連結需要登入嗎？（不用登入，只要有連結跟密碼就能開）

回覆：

## 幫助中心（分類、文章、搜尋） `H-help-center`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/H/help-center-search` 幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類）

回覆：

## 方案、價格與免費試用 `I-pricing`（待審 11 條：pass 8／doubt 3／未先審 0）

- [pass] `jgb/I/pricing-plan-tiers-overview` JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）
- [pass] `jgb/I/pricing-free-trial-feature-scope` 免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能）
- [pass] `jgb/I/pricing-individual-vs-corporate-team` 個人房東與企業團隊方案差在哪？（團隊成員管理等四項功能、自動對帳與分店管理起始級距不同）
- [pass] `jgb/I/pricing-calc-by-estate-count` 怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案）
- [pass] `jgb/I/pricing-quota-near-full-notice` 物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email）
- [pass] `jgb/I/pricing-enterprise-plan-offer` 企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談）
- [pass] `jgb/I/pricing-trial-plan-landing-page` 體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕）
- [pass] `jgb/I/pricing-plan-price-basis` 方案價格怎麼算、年繳有折扣嗎？（各方案單價從系統價格表讀取；一般方案年繳等於 10 個月的月費）
- [doubt] `jgb/I/pricing-free-trial-eligibility` 免費試用怎麼開始、能用多久？（新建立房東身分自動取得，一個週期後不自動續訂） —— 句序 4：「取消訂閱也不會退款」描述的是現行程式走不到的情境：免費方案建立時不設自動續約資料，取消訂閱入口一開始就因 plan_extend_ymd 為空而擋下（同組外的 subscription-cancel-effect 第 4 句也這樣寫），這句其實是程式註解，被寫成了使用者會遇到的事實
- [doubt] `jgb/I/pricing-free-vs-experience-plan` 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件） —— 句序 1：沒有標明出處就直接說免費方案「擁有智能合約及自動對帳功能」，等於替待裁 #42/#43 選了 FAQ 那一邊；同粗目的 pricing-free-trial-feature-scope 依免費試用彈窗把自動對帳列為不支援，兩條互相矛盾
- [doubt] `jgb/I/pricing-quota-full-block` 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案） —— 句序 3：未訂閱版內文的物件數條件寫反了：上限有值時顯示「無上限」，沒有值時顯示空白，畫面上永遠不會出現句中說的「[物件上限]」數字

回覆：

## 訂閱、付款與訂單 `I-subscription-payment`（待審 6 條：pass 6／doubt 0／未先審 0）

- [pass] `jgb/I/subscription-cancel-effect` 取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效）
- [pass] `jgb/I/orders-payment-history` 付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據）
- [pass] `jgb/I/payment-vendor-edit-after-binding` 金流綁定後還能改嗎？（綁定資料都是唯讀；國泰世華只能補填還沒填齊的超商條碼欄位）
- [pass] `jgb/I/payment-icash-ctbc-setup` 藍新／中信收款帳戶申請要多久？（藍新：智付通至少 2-5 個工作天；中信 ACH 驗證約 5 個工作天）
- [pass] `jgb/I/payment-bill-e-invoice-setup` 帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁）
- [pass] `jgb/I/payment-permission-menu-visibility` 沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現）

回覆：

## 預約 demo `I-demo-booking`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/I/demo-form-actual-validation-scope` demo 表單哪些欄位真的會被系統擋下？（畫面上全部欄位都要填才能送出；系統端只再檢查公司、姓名、電話、Email 四項）

回覆：

## 控制台（設定、通知信範本、自動化任務） `I-control-panel`（待審 9 條：pass 7／doubt 2／未先審 0）

- [pass] `jgb/I/control-panel-entry-scope` 控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入，而且只開放給特定合作團隊）
- [pass] `jgb/I/task-manager-purpose` 任務管理器是做什麼用的？（設定週期性任務或預定通知的排程功能）
- [pass] `jgb/I/task-manager-type-behavior-scope` 新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知）
- [pass] `jgb/I/task-manager-cycle-options` 任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數）
- [pass] `jgb/I/task-manager-form-fields` 新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容）
- [pass] `jgb/I/task-manager-edit-delete-copy` 已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改）
- [pass] `jgb/I/control-panel-access-restriction` 誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）
- [doubt] `jgb/I/control-panel-setting-shell` 進入控制台設定後看到什麼？（麵包屑外殼，內容是任務管理器、新增／編輯任務或通知信設定頁） —— 句序 1：講法「控制台側邊欄」在內文找不到答案：設定頁在非新增／編輯時會顯示側欄，裡面只有「任務管理設定」一項，內文完全沒提
- [doubt] `jgb/I/notification-mail-settings` 通知信副本信箱可以設定嗎？（設定頁只有說明：預設收件為團隊擁有者信箱、每個通知信最多可再加 3 組副本；頁面上目前沒有新增副本的欄位，控制台也沒有入口） —— 句序 2：標題與講法（「通知信副本信箱怎麼加」「通知信設定在哪裡」）都在問能不能加副本信箱，內文卻只看控制台這一頁，等於回答「沒有地方可加」；但現行會員側欄的「通知收件信箱」頁就能新增信箱，每個通知信最多 3 組，內文漏了這個例外

回覆：

## 官網首頁 `I-marketing-home`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/I/homepage-latest-news-section` 首頁「最新消息」顯示什麼？（用輪播呈現消息，點擊會開啟幫助中心文章）
- [doubt] `jgb/I/homepage-sections-overview` 官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息） —— 句序 2：「從特定搜尋入口進入首頁時才會顯示」沒有來源：顯示條件只是網址帶 allowSearch 參數，全庫沒有任何入口會帶這個參數

回覆：

## 中華電信雲市集訂單頁 `I-hicloud-order`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/I/tcloud-order-info-fields` 雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態）
- [pass] `jgb/I/tcloud-payment-instructions` 雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號，注意事項請用 WebATM 轉帳；收到匯款資訊後 2 個工作天內付款，款項確認後 2 個工作天內開發票、7 個工作天內開通）
- [pass] `jgb/I/tcloud-link-invalid-cases` 雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁）

回覆：
