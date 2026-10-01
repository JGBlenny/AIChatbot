# Plan 9.20 S1 修正紀錄（F～I 疑點 38 條）

> 允許集合 `scratchpad/p920-w1/allowed.json`（38 條，F 12／G 5／H 1／I 20）。基準＝`scratchpad/p920-w1/backup/drafts/`。句序一律為**備份側**句序（drafts_diff 的 item 句序，0 起算；SequenceMatcher 對齊，刪＋插於同位置記為「改」）。evidence 句序位移由 `edit_fine.py` 機械處理，不列入本表（差異比對 (g) 另查）。改寫工具 `scratchpad/p920-w1/edit_fine.py`，ops 原檔 `scratchpad/p920-w1/ops.json`。verifier 判定：過／不過／待核。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/F/repair-apply-flow-and-entry` | sentences | 2 | 改 | 依據 #1 | 過 |
| `jgb/F/repair-apply-flow-and-entry` | sources |  | 改 | 依據 #1 | 過 |
| `jgb/F/repair-apply-notifications` | sentences | 0 | 改 | 依據 #2 | 過 |
| `jgb/F/repair-apply-notifications` | sentences | 1 | 新增句 | 依據 #2 | 過 |
| `jgb/F/repair-apply-notifications` | sources |  | 改 | 依據 #2 | 過 |
| `jgb/F/repair-apply-notifications` | title |  | 改 | 依據 #2 | 過 |
| `jgb/F/repair-apply-without-contract` | sentences | 0 | 改 | 依據 #3 | 過 |
| `jgb/F/repair-apply-without-contract` | sentences | 2 | 刪句 | 依據 #3 | — |
| `jgb/F/repair-edit-amount-visibility` | title |  | 改 | 依據 #4 | 過 |
| `jgb/F/repair-edit-cannot-edit-roles` | sentences | 0 | 改 | 依據 #5 | 過 |
| `jgb/F/repair-edit-cannot-edit-roles` | title |  | 改 | 依據 #5 | 過 |
| `jgb/F/repair-edit-progress-timeline` | sentences | 0 | 改 | 依據 #6 | 過 |
| `jgb/F/repair-edit-progress-timeline` | sentences | 1 | 新增句 | 依據 #6 | 過 |
| `jgb/F/repair-edit-progress-timeline` | sources |  | 改 | 依據 #6 | 過 |
| `jgb/F/repair-edit-progress-timeline` | title |  | 改 | 依據 #6 | 過 |
| `jgb/F/repair-edit-share-to-vendor` | sentences | 0 | 改 | 依據 #7 | 過 |
| `jgb/F/repair-edit-share-to-vendor` | sentences | 1 | 改 | 依據 #7 | 過 |
| `jgb/F/repair-edit-share-to-vendor` | title |  | 改 | 依據 #7 | 過 |
| `jgb/F/repair-edit-tenant-memo` | sentences | 1 | 改 | 依據 #8 | 過 |
| `jgb/F/repair-edit-tenant-memo` | sources |  | 改 | 依據 #8 | 過 |
| `jgb/F/repair-edit-tenant-memo` | title |  | 改 | 依據 #8 | 過 |
| `jgb/F/repair-notifications-by-stage` | sentences | 0 | 改 | 依據 #9 | 過 |
| `jgb/F/repair-notifications-by-stage` | sentences | 1 | 改 | 依據 #9 | 過 |
| `jgb/F/repair-notifications-by-stage` | sentences | 2 | 改 | 依據 #9 | 過 |
| `jgb/F/repair-notifications-by-stage` | sentences | 3 | 新增句 | 依據 #9 | 過 |
| `jgb/F/repair-notifications-by-stage` | sources |  | 改 | 依據 #9 | 過 |
| `jgb/F/repair-notifications-by-stage` | title |  | 改 | 依據 #9 | 過 |
| `jgb/F/repair-share-no-expiry` | sentences | 1 | 刪句 | 依據 #10 | — |
| `jgb/F/repair-share-no-expiry` | title |  | 改 | 依據 #10 | 過 |
| `jgb/F/repair-status-tabs` | sentences | 1 | 改 | 依據 #11 | 過 |
| `jgb/F/repair-status-tabs` | sources |  | 改 | 依據 #11 | 過 |
| `jgb/F/repair-status-tabs` | title |  | 改 | 依據 #11 | 過 |
| `jgb/F/repair-view-only-roles` | sentences | 1 | 改 | 依據 #12 | 過 |
| `jgb/F/repair-view-only-roles` | sentences | 3 | 改 | 依據 #12 | 過 |
| `jgb/F/repair-view-only-roles` | sources |  | 改 | 依據 #12 | 過 |
| `jgb/F/repair-view-only-roles` | title |  | 改 | 依據 #12 | 過 |
| `jgb/G/device-edit-tabs-by-type` | sentences | 3 | 刪句 | 依據 #13 | — |
| `jgb/G/device-lock-passwords-three-types` | sentences | 2 | 改 | 依據 #14 | 過 |
| `jgb/G/iot-entry-requirements` | phrasings |  | 改 | 依據 #15 | 過 |
| `jgb/G/iot-entry-requirements` | sentences | 0 | 改 | 依據 #15 | 過 |
| `jgb/G/iot-entry-requirements` | sentences | 1 | 新增句 | 依據 #15 | 過 |
| `jgb/G/iot-entry-requirements` | sources |  | 改 | 依據 #15 | 過 |
| `jgb/G/iot-entry-requirements` | title |  | 改 | 依據 #15 | 過 |
| `jgb/G/power-meter-vendor-unreachable` | sentences | 0 | 改 | 依據 #16 | 過 |
| `jgb/G/power-meter-vendor-unreachable` | sentences | 1 | 改 | 依據 #16 | 過 |
| `jgb/G/power-meter-vendor-unreachable` | sentences | 2 | 改 | 依據 #16 | 過 |
| `jgb/G/power-meter-vendor-unreachable` | title |  | 改 | 依據 #16 | 過 |
| `jgb/G/remote-unlock-page` | sentences | 4 | 改 | 依據 #17 | 過 |
| `jgb/G/remote-unlock-page` | title |  | 改 | 依據 #17 | 過 |
| `jgb/H/help-center-search` | sentences | 2 | 改 | 依據 #18 | 過 |
| `jgb/I/control-panel-entry-scope` | sentences | 1 | 改 | 依據 #19 | 過 |
| `jgb/I/control-panel-entry-scope` | sources |  | 改 | 依據 #19 | 過 |
| `jgb/I/control-panel-entry-scope` | title |  | 改 | 依據 #19 | 過 |
| `jgb/I/control-panel-setting-shell` | sentences | 0 | 改 | 依據 #20 | 過 |
| `jgb/I/control-panel-setting-shell` | sources |  | 改 | 依據 #20 | 過 |
| `jgb/I/control-panel-setting-shell` | title |  | 改 | 依據 #20 | 過 |
| `jgb/I/demo-form-actual-validation-scope` | sentences | 0 | 改 | 依據 #21 | 過 |
| `jgb/I/demo-form-actual-validation-scope` | sources |  | 改 | 依據 #21 | 過 |
| `jgb/I/demo-form-actual-validation-scope` | title |  | 改 | 依據 #21 | 過 |
| `jgb/I/homepage-latest-news-section` | sentences | 0 | 改 | 依據 #22 | 過 |
| `jgb/I/homepage-latest-news-section` | title |  | 改 | 依據 #22 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 0 | 改 | 依據 #23 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 1 | 改 | 依據 #23 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 2 | 改 | 依據 #23 | 過 |
| `jgb/I/notification-mail-settings` | sentences | 1 | 新增句 | 依據 #24 | 過 |
| `jgb/I/notification-mail-settings` | sources |  | 改 | 依據 #24 | 過 |
| `jgb/I/notification-mail-settings` | title |  | 改 | 依據 #24 | 過 |
| `jgb/I/orders-payment-history` | sentences | 0 | 改 | 依據 #25 | 過 |
| `jgb/I/payment-bill-e-invoice-setup` | sentences | 2 | 改 | 依據 #26 | 過 |
| `jgb/I/payment-icash-ctbc-setup` | phrasings |  | 改 | 依據 #27 | 過 |
| `jgb/I/payment-icash-ctbc-setup` | sentences | 0 | 改 | 依據 #27 | 過 |
| `jgb/I/payment-icash-ctbc-setup` | title |  | 改 | 依據 #27 | 過 |
| `jgb/I/payment-permission-menu-visibility` | phrasings |  | 改 | 依據 #28 | 過 |
| `jgb/I/payment-permission-menu-visibility` | sentences | 0 | 改 | 依據 #28 | 過 |
| `jgb/I/payment-permission-menu-visibility` | sources |  | 改 | 依據 #28 | 過 |
| `jgb/I/payment-vendor-edit-after-binding` | sentences | 0 | 改 | 依據 #29 | 過 |
| `jgb/I/payment-vendor-edit-after-binding` | sources |  | 改 | 依據 #29 | 過 |
| `jgb/I/payment-vendor-edit-after-binding` | title |  | 改 | 依據 #29 | 過 |
| `jgb/I/pricing-free-trial-eligibility` | sentences | 0 | 改 | 依據 #30 | 過 |
| `jgb/I/pricing-free-trial-feature-scope` | sentences | 2 | 改 | 依據 #31 | 過 |
| `jgb/I/pricing-individual-vs-corporate-team` | sentences | 1 | 改 | 依據 #32 | 過 |
| `jgb/I/pricing-individual-vs-corporate-team` | title |  | 改 | 依據 #32 | 過 |
| `jgb/I/pricing-plan-price-basis` | phrasings |  | 改 | 依據 #33 | 過 |
| `jgb/I/pricing-plan-price-basis` | sentences | 0 | 改 | 依據 #33 | 過 |
| `jgb/I/pricing-plan-price-basis` | sentences | 1 | 刪句 | 依據 #33 | — |
| `jgb/I/pricing-plan-price-basis` | title |  | 改 | 依據 #33 | 過 |
| `jgb/I/pricing-quota-near-full-notice` | sentences | 0 | 改 | 依據 #34 | 過 |
| `jgb/I/pricing-quota-near-full-notice` | sentences | 1 | 改 | 依據 #34 | 過 |
| `jgb/I/pricing-quota-near-full-notice` | sources |  | 改 | 依據 #34 | 過 |
| `jgb/I/pricing-trial-plan-landing-page` | phrasings |  | 改 | 依據 #35 | 過 |
| `jgb/I/subscription-cancel-effect` | sentences | 2 | 改 | 依據 #36 | 過 |
| `jgb/I/task-manager-purpose` | title |  | 改 | 依據 #37 | 過 |
| `jgb/I/tcloud-payment-instructions` | title |  | 改 | 依據 #38 | 過 |

## 刪除

（無整條刪除）

## 依據

1. `jgb/F/repair-apply-flow-and-entry`（9.18 S2 doubt）：句序 3：租客的修繕單總表只列 is_notice_tenant=1 的單；網頁上「通知及同步租客」開關沒有接上，房東建的單一律存成 is_notice_tenant=false，租客看不到，所以「不管誰發起，雙方登入系統都看得到」與程式衝突（文件與程式衝突，以程式為準）
2. `jgb/F/repair-apply-notifications`（9.18 S2 doubt）：句序 1：程式裡 repair_create 的實際行為：租客發起只通知房東（LINE、通知中心、Email），不通知租客；房東發起時，租客通知受 is_notice_tenant 控制，而網頁建單一律是 false，所以只寄 Email 給房東。沒有「租客收到 Email／LINE」的路徑；句子只依幫助中心，與程式衝突
3. `jgb/F/repair-apply-without-contract`（9.18 S2 doubt）：句序 1：含實作與過程筆記：「系統裡原本用合約找修繕對象的那段邏輯已經標註不再使用」，句 3「流程裡原本預留的合約欄位目前維持空白」也是；事實本身（房東方有物件就能申請）成立
4. `jgb/F/repair-edit-amount-visibility`（9.18 S2 doubt）：句序 標題：標題含過程筆記與實作詞：「沒有找到跟帳單模組串接的路徑」。內文「不會自動產生帳單」本身成立
5. `jgb/F/repair-edit-cannot-edit-roles`（9.18 S2 doubt）：句序 1：「租客帳號…都只能看內容」與同組的 repair-edit-tenant-memo 句 3 矛盾：租客在細節頁可以編輯「房客備註」。標題「都只能看」也一樣
6. `jgb/F/repair-edit-progress-timeline`（9.18 S2 doubt）：句序 1：時間軸上的日期不是「到了這個階段的日期」：安排修繕取第一筆廠商紀錄的修繕時間，完成修繕取房東備註的完成時間；結單、封存時間在列表「移至」往回移時不會清掉。所以「還沒到的階段不顯示日期」這個絕對說法有程式反例（例如還在安排修繕，房東先填了完成時間）
7. `jgb/F/repair-edit-share-to-vendor`（9.18 S2 doubt）：句序 1：絕對句漏了裝置例外：行動裝置上瀏覽器支援 navigator.share 時，點「分享」直接叫出系統分享選單，不會開「分享修繕申請單」視窗，句 2 的「兩種方式」也就不成立
8. `jgb/F/repair-edit-tenant-memo`（9.18 S2 doubt）：句序 2：房東在網頁申請時一定會送出至少一列預約時段，因為第一列刪不掉，沒填的話就是空值；後端仍把它存進 pre_assign_data，細節頁的 tenant_order_times 變成 ["  - "]，不是空的。結果房東發起、沒填時段的單也會顯示房客備註區，不會出現「此修繕單為房東發起，無房客備註」
9. `jgb/F/repair-notifications-by-stage`（9.18 S2 doubt）：句序 3：結單通知 repair_finish 只寄 Email（房東一律寄，租客要 is_notice_tenant 為 true 才寄），沒有 LINE 也沒有通知中心；句 1、句 2 的租客通知同樣受 is_notice_tenant 控制，網頁上房東建的單不會通知租客。只依幫助中心，與程式衝突
10. `jgb/F/repair-share-no-expiry`（9.18 S2 doubt）：句序 2：含實作歷史筆記：「系統背後曾經寫過『如果超過 30 天就不給查看』的檢查，但這段檢查已經被停用」，標題「系統一度寫過 30 天過期的檢查」也是；對使用者來說只要「目前不會過期」即可
11. `jgb/F/repair-status-tabs`（9.18 S2 doubt）：句序 2：這句說明各狀態代表什麼（「安排修繕代表房東方正在確認或已經指派廠商」「完成修繕代表…房東方在做結算與備註」等），但列出的來源全是程式，程式裡只有狀態名稱和註解，查不到這些說法，屬於無源句
12. `jgb/F/repair-view-only-roles`（9.18 S2 doubt）：句序 2：團隊成員若是這張修繕單的經理人（agent_user_id 等於本人），逐物件權限判斷對所有修繕權限都回 true，所以只有「顯示所屬」權限的經理人看自己負責的修繕單時，齒輪文字是「編輯＆查看」而且有移動選項；把「查看」寫成經理人的常態（句 2、句 5 與標題）與程式相反
13. `jgb/G/device-edit-tabs-by-type`（9.18 S2 doubt）：句序 4：「編輯按鈕在分類群組被標記成不可編輯時會鎖住…目前程式把這個群組一律標記為可編輯」是程式實作筆記，講的是使用者看不到的失效機制，不是畫面行為
14. `jgb/G/device-lock-passwords-three-types`（9.18 S2 doubt）：句序 3：加引號的「編輯密碼」在現行畫面上不會出現（被設成隱藏），不能當介面標籤引用；「畫面上雖然定義了…被設定成永遠不會顯示」是實作詞。使用者看得到的事實（沒有編輯入口，只能刪掉重新新增）應直接寫
15. `jgb/G/iot-entry-requirements`（9.18 S2 doubt）：句序 1：第二道檢查不是物件數量上限，而是方案有沒有開 IoT 功能；兩道檢查也都不擋租客。另外「路由」「掛了檢查」是實作詞
16. `jgb/G/power-meter-vendor-unreachable`（9.18 S2 doubt）：句序 1：「如果目前連不上某個廠商，清單頁與單一電錶頁…都會出現」是絕對句，但只適用全站共用連線的那家廠商；另一家以帳號巡檢回報連不上時，提示只給業者看、只出現在清單頁，而且會寫帳號並叫人查帳號密碼，和句序 2、3 的敘述相反
17. `jgb/G/remote-unlock-page`（9.18 S2 doubt）：句序 5：「找不到任何按鈕或畫面會產生…」是盤查過程筆記，「連結碼是用這台門鎖的建立時間算出來的固定值」是實作細節（實際是門鎖 id 加建立時間算出的雜湊）。標題「找不到產生這個連結的入口」也帶著同樣的過程筆記語氣
18. `jgb/H/help-center-search`（9.18 S2 doubt）：句序 3：「沒有輸入任何關鍵字就送出搜尋，會直接被導回幫助中心首頁」與畫面行為不符：關鍵字空白時，搜尋框的送出根本不會跳頁，人會停在原頁。導回首頁只發生在直接打開沒帶關鍵字的搜尋網址時
19. `jgb/I/control-panel-entry-scope`（9.18 S2 doubt）：句序 2：「點擊後會進入任務管理器頁面」是絕對句，漏了權限例外：角色不在 controlPanel 或 tongSang 分組的人，點了會被導回 /users
20. `jgb/I/control-panel-setting-shell`（9.18 S2 doubt）：句序 1：「本身不含其他獨立內容」和程式不符：外殼在非新增／編輯頁會顯示 OrderAside 側欄（標題寫了側欄，內文沒寫）。子路由也不只有任務管理器與新增／編輯，還有 notificationMail
21. `jgb/I/demo-form-actual-validation-scope`（9.18 S2 doubt）：句序 1：送出按鈕不是填完才「變可點擊」，它一直都能點；前端 10 個欄位都有瀏覽器原生 required，會先擋下送出，所以「只要四項合格就能送出成功」只有直接打 API 才成立。這和同組 demo-form-fields 說的「按鈕本身一律可以點擊，擋送出的是瀏覽器驗證」互相矛盾
22. `jgb/I/homepage-latest-news-section`（9.18 S2 doubt）：句序 1：`v-if="news"` 檢查的是陣列：後端回傳的是 array_slice 產生的陣列，前端預設值也是 []，[] 是 truthy，所以沒有消息時「最新消息」標題與空輪播照樣會出現，「整區塊不會出現」（標題也這樣寫）不成立
23. `jgb/I/homepage-sections-overview`（9.18 S2 doubt）：句序 2：`v-if="hotListings"` 和 `v-if="landlordFeedback"` 檢查的是陣列：前端預設值與後端回傳都是 []，而 [] 在 JS 裡是 truthy，所以沒資料時區塊標題照樣會顯示，「只有在有回傳資料時才會顯示」不成立（句序 3 同理）。另外句序 1 說「最後是企業夥伴」，但企業夥伴後面還有一張 IWBI 圖片
24. `jgb/I/notification-mail-settings`（9.18 S2 doubt）：句序 1：標題問「怎麼設定」，但這一頁只有說明文字，沒有任何可以新增副本信箱的表單或控制項；首頁卡片和側欄的入口也都被註解掉了，所以回答不了標題，還會把人引到一個不能用的頁面
25. `jgb/I/orders-payment-history`（9.18 S2 doubt）：句序 1：括號裡舉的例子「熱門方案的加購次數、續訂折扣說明」沒有來源。付款內容實際是「訂閱方案：[方案名] - 共 [n] 個物件 * 1」這類品項，再加上訂單的 contents
26. `jgb/I/payment-bill-e-invoice-setup`（9.18 S2 doubt）：句序 3：「預先開立發票」模式只有特定合作團隊（preBillingInvoice 群組）才有，一般帳號只能選「帳單已到帳後開立」；而且開立時機還有「繳費期限後」，不只是「提前」
27. `jgb/I/payment-icash-ctbc-setup`（9.18 S2 doubt）：句序 1：「智付通…需至少 2 - 5 個工作天」這段提醒是在選藍新（newebpay）時才顯示，不是 icash Pay；標題跟著錯
28. `jgb/I/payment-permission-menu-visibility`（9.18 S2 doubt）：句序 1：唯一的文件來源 qa23 說是少了「編輯團隊」權限；程式則是兩個選單各自看 show_role_payment／show_role_subscription（查看收款設置／查看訂閱方案）。文件和程式本身就衝突，正本又把兩邊混在一起，還把文件裡綁「編輯團隊」的「帳號資訊以個人房東形式呈現」接到查看權限上
29. `jgb/I/payment-vendor-edit-after-binding`（9.18 S2 doubt）：句序 1：國泰世華明細頁的主要綁定欄位（加密因子、ATM 前綴）一樣是唯讀；只有超商條碼欄位還沒填齊時，才能補填那一段再送出，不是整張表都能重填
30. `jgb/I/pricing-free-trial-eligibility`（9.18 S2 doubt）：句序 1：引號裡的介面文案跟現行畫面不一致：畫面上是「不綁信用卡的30天的試用方案，歡迎體驗！」，正本寫成「不綁信用卡的 30 天試用方案」
31. `jgb/I/pricing-free-trial-feature-scope`（9.18 S2 doubt）：句序 3：兩個問題：(1) 引號文字多了一個逗號，現行是「無法申請國泰、永豐可申請藍新、中信」；(2)「這個限制其實只擋國泰與永豐」是絕對句，漏了個人房東的例外。個人房東連藍新也不能開，跟同組 payment-vendor-eligibility-by-role-and-plan 矛盾
32. `jgb/I/pricing-individual-vs-corporate-team`（9.18 S2 doubt）：句序 2：標題和句 2 都說這四項屬於「人員管理」，但比較表裡「團隊資訊」「進階設定」其實在「團隊管理 / 其他設定」群組
33. `jgb/I/pricing-plan-price-basis`（9.18 S2 doubt）：句序 1：100 元只是說明文字裡寫死的數字。實際扣款和方案頁顯示的價格，都是 get_plan_price(10,…) 從 plan_estate_prices 表讀出來的，所以「體驗方案固定 100 元」跟句 2「其他方案不是寫死」的對比不成立
34. `jgb/I/pricing-quota-near-full-notice`（9.18 S2 doubt）：句序 1：剩 5 個以下時系統只寫通知中心、不寄 Email；只有剛好剩 5 個那次才寄一封 Email，所以句 1 的「與 Email」沒有來源，句 2「再另外寄送一封」也跟著錯
35. `jgb/I/pricing-trial-plan-landing-page`（9.19 S2 doubt）：講法：講法「深入了解企業方案後看到什麼」對應不到這條細目：「深入了解企業方案」連到的是預約 demo 表單，不是體驗方案介紹頁，進到介紹頁的入口是「查看體驗方案」。這句講法也跟同粗目的 pricing-enterprise-plan-offer 矛盾
36. `jgb/I/subscription-cancel-effect`（9.18 S2 doubt）：句序 3：「寄送 Email 通知使用者」實際不會發生。controller 呼叫的是 'subscription_cancel'，但 Notification::notice 裡只有拼錯的 case 'subscription_cance'，比對不到就不寄；就算拼對了，那個 case 也只在訂閱仍有效時才寄。對照組：同一個 switch 裡的 case 'will_full_remind_to_subscription' 有抓到
37. `jgb/I/task-manager-purpose`（9.18 S2 doubt）：句序 標題：標題把「系統會提前自動開單並寄信」寫成系統事實，但目前任務類型只有「通知」，修繕開單已經被註解掉，和同組 task-manager-type-behavior-scope 矛盾。內文只是轉述頁面說明，而頁面說明本身兩處也對不上：列表頁寫前三十天，新增頁寫前 45 天
38. `jgb/I/tcloud-payment-instructions`（9.18 S2 doubt）：句序 標題：標題「付款後 2 天開發票、7 天內開通」把來源的「工作天」拿掉了，數字單位對不上；「限 WebATM」也比來源的「請透過WebATM進行轉帳，避免付款失敗」說得更死（內文三句本身正確）

## 核對過程

- **第一輪**（fresh verifier 兩包，brief 由 `templates/brief-fix-verify.txt` 衍生，存 `scratchpad/p920-w1/brief-fix-{FH,GI}.txt`）：
  - F＋H：35 項，**CONFIRMED 35／35**；
  - G＋I：55 項，**REFUTED 53／55**。不過的 2 項：
    - `control-panel-setting-shell` 句 1：側欄寫成一律成立，漏了手機版與電腦版預設收合；
    - `payment-icash-ctbc-setup` 句 0：漏了個人房東選藍新時看不到提醒的例外。
- **依 D1 修一次後複核**（fresh verifier，`brief-recheck.txt`）：
  - `payment-icash-ctbc-setup` 句 0 **過**；
  - `control-panel-setting-shell` 句 1 **仍不過**：新寫的「可左右切換的選單列」不對，手機版左右箭頭是固定導頁，不是切換。
  - ⇒ 依 D1 **整句刪**（這一句是新增句，刪掉即回到只有句 0）。標題同步拿掉「與側欄」（標題只是縮窄，不新增主張，由主 session 對照 drafts 機械確認），並移除只為那句加的 source `OrderAside.vue`。原 doubt 指出的「內文沒寫側欄」因此改為不寫側欄，屬於「沒寫到但不矛盾」。
- **刪句 4 項**（D1 不需判定）：verifier 已確認刪除後剩下的句子仍然成立。
- **附建議**（P3／P4 共 8 項，不阻擋，延後到 S2 重審一併看）：
  - repair-apply-notifications、repair-notifications-by-stage 的 sources 可補 Detail.vue／SwitchButton.vue；
  - repair-edit-progress-timeline 句 0 可補 evidence；
  - repair-edit-share-to-vendor：isMobile 也比對平板，標題可補「瀏覽器支援時」；
  - repair-notifications-by-stage 句 3 可寫明範圍；
  - repair-view-only-roles 句 3 可加「不是這張單的經理人」；
  - pricing-free-trial-eligibility 引號內數字前後空白（P4）；
  - pricing-free-trial-feature-scope 的「另見」引用標題（P4）；
  - payment-icash-ctbc-setup 的 askable 仍寫 icash Pay（P3；askable 不進正本）。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p920-w1/drafts_diff.py --base scratchpad/p920-w1/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p920-w1/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 27; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 539; doubt set: 38 (not found in base: 0)
[diff] changed/deleted items: 93 in 38 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 93; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-A～E 與備份 `cmp` 相同。
