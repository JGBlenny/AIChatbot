# Plan 9.20 S4 修正紀錄（D／E 疑點 40 條：修正 38、已由前案處理 2）

> 允許集合 `scratchpad/p920-w2/allowed.json`（40 條，D 30／E 10；兩來源＝repo 審核單 9.16 S3 與從 transcript 重取的 raw，見計畫 §1 S4「已預跑」）。基準＝`scratchpad/p920-w2/backup/drafts/`。句序一律為**備份側**句序（drafts_diff 的 item 句序，0 起算；SequenceMatcher 對齊，刪＋插於同位置記為「改」）。9.16 doubt 的「句序」為 1 起算（0＝標題），依據節照原文保留。evidence 句序位移由 `edit_fine.py` 機械處理，不列入本表（差異比對 (g) 另查）。改寫工具 `scratchpad/p920-w2/edit_fine.py`，ops 原檔 `scratchpad/p920-w2/ops.json`。verifier 判定：過／不過／待核。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/D/contract-edit-tabs-overview` | sentences | 6 | 改 | 依據 #1 | 過 |
| `jgb/D/contract-landlord-dealer-basic` | sentences | 3 | 改 | 依據 #2 | 過 |
| `jgb/D/contract-landlord-dealer-basic` | sources |  | 改 | 依據 #2 | 過 |
| `jgb/D/contract-landlord-dealer-basic` | title |  | 改 | 依據 #2 | 過 |
| `jgb/D/contract-locked-after-signing` | phrasings |  | 改 | 依據 #3 | 過 |
| `jgb/D/contract-locked-after-signing` | sentences | 1 | 改 | 依據 #3 | 過 |
| `jgb/D/contract-locked-after-signing` | sources |  | 改 | 依據 #3 | 過 |
| `jgb/D/contract-locked-after-signing` | title |  | 改 | 依據 #3 | 過 |
| `jgb/D/contract-rentbasic-template-and-dates` | sentences | 5 | 改 | 依據 #4 | 過 |
| `jgb/D/contract-show-panels` | phrasings |  | 改 | 依據 #5 | 過 |
| `jgb/D/contract-show-panels` | sentences | 0 | 改 | 依據 #5 | 過 |
| `jgb/D/contract-show-panels` | sources |  | 改 | 依據 #5 | 過 |
| `jgb/D/contract-show-panels` | title |  | 改 | 依據 #5 | 過 |
| `jgb/D/contract-sign-flow-steps` | sentences | 2 | 改 | 依據 #6 | 過 |
| `jgb/D/contract-sign-flow-steps` | sources |  | 改 | 依據 #6 | 過 |
| `jgb/D/contract-tax-invoice` | title |  | 改 | 依據 #7 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | phrasings |  | 改 | 依據 #8 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | sentences | 1 | 改 | 依據 #8 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | title |  | 改 | 依據 #8 | 過 |
| `jgb/D/early-termination-billing-after` | sentences | 2 | 改 | 依據 #9 | 過 |
| `jgb/D/early-termination-billing-after` | sources |  | 改 | 依據 #9 | 過 |
| `jgb/D/early-termination-tenant-cancel` | sentences | 1 | 改 | 依據 #10 | 過 |
| `jgb/D/early-termination-tenant-cancel` | title |  | 改 | 依據 #10 | 過 |
| `jgb/D/entrusted-contract-fees` | sentences | 1 | 改 | 依據 #11 | 過 |
| `jgb/D/entrusted-contract-fees` | sentences | 3 | 新增句 | 依據 #11 | 過 |
| `jgb/D/entrusted-contract-lease-type` | sentences | 3 | 新增句 | 依據 #12 | 過 |
| `jgb/D/entrusted-contract-lease-type` | sources |  | 改 | 依據 #12 | 過 |
| `jgb/D/entrusted-contract-tabs-overview` | sentences | 1 | 新增句 | 依據 #13 | 過 |
| `jgb/D/entrusted-contract-tabs-overview` | sources |  | 改 | 依據 #13 | 過 |
| `jgb/D/move-out-bill-generation` | sentences | 2 | 改 | 依據 #14 | 過 |
| `jgb/D/move-out-bill-generation` | sources |  | 改 | 依據 #14 | 過 |
| `jgb/D/move-out-bill-generation` | title |  | 改 | 依據 #14 | 過 |
| `jgb/D/move-out-checklist-and-damage` | sentences | 0 | 改 | 依據 #15 | 過 |
| `jgb/D/move-out-checklist-and-damage` | sentences | 1 | 新增句 | 依據 #15 | 過 |
| `jgb/D/move-out-checklist-and-damage` | sources |  | 改 | 依據 #15 | 過 |
| `jgb/D/move-out-checklist-and-damage` | title |  | 改 | 依據 #15 | 過 |
| `jgb/D/move-out-eligibility-conditions` | sentences | 2 | 改 | 依據 #16 | 過 |
| `jgb/D/social-housing-attachments-tab` | sentences | 0 | 改 | 依據 #17 | 過 |
| `jgb/D/social-housing-attachments-tab` | sources |  | 改 | 依據 #17 | 過 |
| `jgb/D/social-housing-attachments-tab` | title |  | 改 | 依據 #17 | 過 |
| `jgb/D/social-housing-charter-sublet-tab-hiding` | title |  | 改 | 依據 #18 | 過 |
| `jgb/D/social-housing-early-termination-difference` | sentences | 1 | 改 | 依據 #19 | 過 |
| `jgb/D/social-housing-facilities-tab` | phrasings |  | 改 | 依據 #20 | 過 |
| `jgb/D/social-housing-facilities-tab` | sentences | 0 | 改 | 依據 #20 | 過 |
| `jgb/D/social-housing-facilities-tab` | sources |  | 改 | 依據 #20 | 過 |
| `jgb/D/social-housing-facilities-tab` | title |  | 改 | 依據 #20 | 過 |
| `jgb/D/social-housing-landlord-license-conditions` | sentences | 0 | 改 | 依據 #21 | 過 |
| `jgb/D/social-housing-landlord-license-conditions` | sentences | 1 | 改 | 依據 #21 | 過 |
| `jgb/D/social-housing-landlord-license-conditions` | title |  | 改 | 依據 #21 | 過 |
| `jgb/D/social-housing-landlord-tabs-overview` | sentences | 0 | 改 | 依據 #22 | 過 |
| `jgb/D/social-housing-landlord-tabs-overview` | sources |  | 改 | 依據 #22 | 過 |
| `jgb/D/social-housing-notary` | sentences | 1 | 改 | 依據 #23 | 過 |
| `jgb/D/social-housing-notary` | sources |  | 改 | 依據 #23 | 過 |
| `jgb/D/social-housing-payment-method-tab` | sentences | 1 | 改 | 依據 #24 | 過 |
| `jgb/D/social-housing-payment-method-tab` | sources |  | 改 | 依據 #24 | 過 |
| `jgb/D/social-housing-rent-basic-conditions` | sentences | 0 | 改 | 依據 #25 | 過 |
| `jgb/D/social-housing-rent-basic-conditions` | sentences | 1 | 改 | 依據 #25 | 過 |
| `jgb/D/social-housing-rent-basic-conditions` | sentences | 4 | 改 | 依據 #25 | 過 |
| `jgb/D/social-housing-rent-basic-conditions` | sources |  | 改 | 依據 #25 | 過 |
| `jgb/D/social-housing-rent-fees-tab` | sentences | 0 | 改 | 依據 #26 | 過 |
| `jgb/D/social-housing-rent-fees-tab` | sources |  | 改 | 依據 #26 | 過 |
| `jgb/D/social-housing-tenant-basic-status` | sentences | 0 | 改 | 依據 #27 | 過 |
| `jgb/D/social-housing-tenant-basic-status` | sentences | 1 | 改 | 依據 #27 | 過 |
| `jgb/D/social-housing-tenant-basic-status` | sources |  | 改 | 依據 #27 | 過 |
| `jgb/D/social-housing-tenant-basic-status` | title |  | 改 | 依據 #27 | 過 |
| `jgb/D/social-housing-tenant-tabs-overview` | sentences | 0 | 改 | 依據 #28 | 過 |
| `jgb/D/social-housing-tenant-tabs-overview` | sources |  | 改 | 依據 #28 | 過 |
| `jgb/E/balance-invoice-monthly-invoice-table` | sentences | 3 | 改 | 依據 #29 | 過 |
| `jgb/E/balance-invoice-monthly-invoice-table` | sources |  | 改 | 依據 #29 | 過 |
| `jgb/E/bill-actions-received` | sentences | 7 | 改 | 依據 #30 | 過 |
| `jgb/E/bill-actions-received` | sources |  | 改 | 依據 #30 | 過 |
| `jgb/E/bill-internal-note-visibility` | sentences | 0 | 改 | 依據 #31 | 過 |
| `jgb/E/bill-internal-note-visibility` | sources |  | 改 | 依據 #31 | 過 |
| `jgb/E/bill-internal-note-visibility` | title |  | 改 | 依據 #31 | 過 |
| `jgb/E/bill-partial-month-proration` | sentences | 0 | 改 | 依據 #32 | 過 |
| `jgb/E/bill-partial-month-proration` | sources |  | 改 | 依據 #32 | 過 |
| `jgb/E/bill-partial-month-proration` | title |  | 改 | 依據 #32 | 過 |
| `jgb/E/bill-receipt-feature-roadmap` | sentences | 0 | 改 | 依據 #33 | 過 |
| `jgb/E/bill-receipt-feature-roadmap` | sources |  | 改 | 依據 #33 | 過 |
| `jgb/E/bill-receipt-feature-roadmap` | title |  | 改 | 依據 #33 | 過 |
| `jgb/E/bill-tenant-unverified-draft-lock` | sentences | 0 | 改 | 依據 #34 | 過 |
| `jgb/E/bill-tenant-unverified-draft-lock` | sentences | 2 | 刪句 | 依據 #34 | — |
| `jgb/E/bill-tenant-unverified-draft-lock` | sources |  | 改 | 依據 #34 | 過 |
| `jgb/E/bill-tenant-unverified-draft-lock` | title |  | 改 | 依據 #34 | 過 |
| `jgb/E/newebpay-payment-methods` | sentences | 0 | 改 | 依據 #35 | 過 |
| `jgb/E/newebpay-payment-methods` | title |  | 改 | 依據 #35 | 過 |
| `jgb/E/newebpay-required-fields` | phrasings |  | 改 | 依據 #36 | 過 |
| `jgb/E/newebpay-required-fields` | sentences | 0 | 改 | 依據 #36 | 過 |
| `jgb/E/newebpay-required-fields` | sentences | 2 | 刪句 | 依據 #36 | — |
| `jgb/E/newebpay-required-fields` | sources |  | 改 | 依據 #36 | 過 |
| `jgb/E/newebpay-required-fields` | title |  | 改 | 依據 #36 | 過 |
| `jgb/E/payment-onboarding-tax-risk` | sentences | 0 | 改 | 依據 #37 | 過 |
| `jgb/E/payment-onboarding-tax-risk` | title |  | 改 | 依據 #37 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | sentences | 1 | 改 | 依據 #38 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | sources |  | 改 | 依據 #38 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | title |  | 改 | 依據 #38 | 過 |

## 刪除

（無；本片沒有整條刪除的細目）

## 已由前案處理

- `jgb/D/contract-payment-method`：9.16 doubt 指的是句中客戶名「Meta Capital 系列」；9.20 S0（`1286d00a`）已改寫為「特定合作團隊的專用範本」，現行文字 `name_scan` 0 命中。
- `jgb/D/contract-rentbasic-latefee`：9.16 doubt 指的是標題與句 1 的客戶名「新北住都」；現行標題與句 0 已寫「特定合作團隊」（9.18 S1 客戶名改寫），`name_scan` 0 命中；doubt 理由並註明內容本身與程式相符。

## 停下交業主

（無）

## 依據

1. `jgb/D/contract-edit-tabs-overview`（9.16 S3 doubt）：句序 7：句中說「稅與發票」只有在團隊沒開通自動產生發票時「才會」被拿掉，但車位合約不論有沒有開通，只要沒有特定角色也會拿掉這個分頁，程式有反例
2. `jgb/D/contract-landlord-dealer-basic`（9.16 S3 doubt）：句序 4：句中寫成出租方都能選電子簽名圖章，但這個功能只開放給法人房東；個人房東的分頁上不會出現這個區塊
3. `jgb/D/contract-locked-after-signing`（9.16 S3 doubt）：句序 2：現行合約列表齒輪選單的字樣是「取消邀請」，不是「取消簽名」。「取消簽名」只出現在沒有路由的舊 ContractController@index。另外，「取消邀請」在「待房東簽名」（租客已簽）狀態下也能用，不只是「雙方都還沒簽名前」
4. `jgb/D/contract-rentbasic-template-and-dates`（9.16 S3 doubt）：句序 6：句中把「轉租合約」寫成一般合約範本可選的一種，但這個標籤只出現在社宅範本（sublet）；一般住宅的 12 種範本裡沒有「轉租合約」，只有「113年內政部轉租契約(包租轉租)」
5. `jgb/D/contract-show-panels`（9.16 S3 doubt）：句序 1：這個檢視頁（src/pages/contracts/show/Index.vue）只給社宅合約用，路由是 sh-show。一般合約的檢視頁是 show.blade.php，上面沒有「合約點交中／點退中」提示。內文把它寫成所有合約的檢視頁，範圍錯了
6. `jgb/D/contract-sign-flow-steps`（9.16 S3 doubt）：句序 3：「租客身份要上傳『小章』；法人身份則要上傳『大章』與『小章』」把選填寫成必填。印章欄位在「合約附件(選填)」區塊內，沒有必填標記，送出前的完成度檢查（allDone）也不檢查印章
7. `jgb/D/contract-tax-invoice`（9.16 S3 doubt）：句序 0（標題）：標題把「目前只支援租金品項開發票」當成事實，但現行畫面上「押金設算息」（功能開關開啟時）和「生活費用計稅品項」都能設為應稅並開發票；內文句 3 只是轉述畫面提示，沒有問題
8. `jgb/D/contract-thinkcloud-signing-variants`（9.16 S3 doubt）：句序 2：「DIY」是程式用語（isDiyContract），畫面上沒有這個字；解析失敗時 thinkcloud 回傳的是 JSON 陣列，而這條流程是整頁跳轉進來的（contracts/sign 轉到 thinkcloud），所以不是畫面上的提示；標題把送簽前的失敗說成簽署畫面的差異
9. `jgb/D/early-termination-billing-after`（9.16 S3 doubt）：句序 3：「合約預覽帳單」是設定檔註解（IS_OPEN_CONTRACT_BILL_SETTING），畫面上沒有這個設定；關閉的只有寫死在程式裡的特定合作團隊，句子卻寫成像團隊自己開關的設定，也沒寫出「特定合作團隊」
10. `jgb/D/early-termination-tenant-cancel`（9.16 S3 doubt）：句序 2：加了引號的狀態名「提前解約確認中」只出現在程式註解，現行畫面和幫助中心用的是「提前解約申請中」或「提前終止合約申請中」；而且租客取消只走「由租客發起」的分支
11. `jgb/D/entrusted-contract-fees`（9.16 S3 doubt）：句序 1：漏了特定合作團隊的例外：beyond360 團隊看不到計算模式、參考金額、計算制度，押金提示也不顯示（押金提示另外只在 zh-TW 顯示），頁面標題是「零用金與服務費」
12. `jgb/D/entrusted-contract-lease-type`（9.16 S3 doubt）：句序 2：漏了特定合作團隊（beyond360）的例外：這個團隊看不到計算模式和計算制度，約定日期也不列入完成檢查，租金標籤顯示「零用金」而不是「包租租金」
13. `jgb/D/entrusted-contract-tabs-overview`（9.16 S3 doubt）：句序 1：漏了特定合作團隊的例外：beyond360 團隊的第二個分頁標籤顯示「零用金與服務費」，不是「租金費用」
14. `jgb/D/move-out-bill-generation`（9.16 S3 doubt）：句序 3：句子說一定要等租客確認並繳款才算完成，漏了免註冊租客的例外：免註冊租客的點退一送出就直接變成點退完成，系統也同時建立點退帳單，不需要租客確認
15. `jgb/D/move-out-checklist-and-damage`（9.16 S3 doubt）：句序 1：免註冊租客可以選「上傳點退文件」，這時第一步只顯示上傳的 PDF（標題「點退清單」），不會列出傢俱項目，也沒有「編輯」，句子寫成所有點退都一樣；另外系統點退時畫面上的標題是「設備損壞確認」，不是「點退清單」
16. `jgb/D/move-out-eligibility-conditions`（9.16 S3 doubt）：句序 3：加了引號的狀態名「完成歷史合約」只出現在程式註解（CONTRACT_HISTORY_DONE），現行畫面上沒有這個標籤；1024 和 2048 兩個狀態在畫面上都歸在「歷史合約」，這是實作詞
17. `jgb/D/social-housing-attachments-tab`（9.16 S3 doubt）：句序 1：例外寫成「轉租合約」「包租合約」（標題也寫「轉租合約除外」），但畫面上的範本名稱是「轉租」「包租包管」。哪些分頁被隱藏（sublet 拿掉出租方附件、charter 拿掉承租方附件）則正確
18. `jgb/D/social-housing-charter-sublet-tab-hiding`（9.16 S3 doubt）：句序 標題：標題寫包租包管隱藏「戶籍/證照/附件」、轉租隱藏「證照/附件」，但這些不是畫面上的分頁名稱，是程式代號（Household/License）的中譯。實際名稱是「家庭＆財產」「授權」「附件」，而內文寫的就是實際名稱，標題和內文對不上
19. `jgb/D/social-housing-early-termination-difference`（9.16 S3 doubt）：句序 2：這句把一般合約寫成一律要選違約金計算方式並分段設定，漏掉特定合作團隊的專屬範本：meta_capital_condos 範本只填「提前解約預告日」，meta_capital_office 範本整段都沒有，nthurc_social_housing 範本只有單一門檻、不分段
20. `jgb/D/social-housing-facilities-tab`（9.16 S3 doubt）：句序 1：社宅附設傢俱分頁不是按格局分別填家具。實際內容是：勾選「設備」、勾選是否有「隔間」，再填「家電」和「傢俱」各品項的整體數量，家電另外填廠牌/型號。格局只是一行提示文字
21. `jgb/D/social-housing-landlord-license-conditions`（9.16 S3 doubt）：句序 1：「主要用途登記含『住』…字樣／提出合法房屋證明」在畫面上屬於「住宅使用」這一項，不在「合法建物條件」下；合法建物條件的選項其實是「出租人為出租住宅之所有權人」「租賃標的需坐落於當地直轄市」。第 2 句也有問題：「同意提供住宅」是在包租包管和代租代管兩種方式中二選一，不是兩個「是否同意」的問題
22. `jgb/D/social-housing-landlord-tabs-overview`（9.16 S3 doubt）：句序 1：說出租方分組「一律」有三個分頁，但選轉租範本時「授權」「附件」兩個分頁會被拿掉，只剩基本資料
23. `jgb/D/social-housing-notary`（9.16 S3 doubt）：句序 2：「只有『包租合約』範本可以逐款選擇」引用的範本名稱畫面上沒有，選單字樣是「包租包管」。可逐款選擇的條件本身（charter）正確
24. `jgb/D/social-housing-payment-method-tab`（9.16 S3 doubt）：句序 2：範本名稱「包租合約」「轉租合約」畫面上沒有，應寫成畫面上的「包租包管」「轉租」。收款人欄位只在代租代管出現，這部分正確
25. `jgb/D/social-housing-rent-basic-conditions`（9.16 S3 doubt）：句序 1：範本下拉選單的選項字樣是「代租代管」「包租包管」，句中寫的「包租合約」「轉租合約」畫面上沒有。「轉租」也不能在基本條件分頁直接選：只有從包租包管合約點「新增轉租契約書」建立的合約才會出現這個選項，而且選單會鎖住（第 2、5 句的範本名稱也有同樣問題）
26. `jgb/D/social-housing-rent-fees-tab`（9.16 S3 doubt）：句序 1：句中寫的範本名稱「包租合約」「轉租合約」畫面上沒有，範本選單的字樣是「包租包管」「轉租」。欄位邏輯（代租金額／包租金額／轉租兩項都沒有）則正確
27. `jgb/D/social-housing-tenant-basic-status`（9.16 S3 doubt）：句序 1：範本名稱「轉租合約」「包租合約」（第 2 句與標題同樣）畫面上沒有，選單字樣是「轉租」「包租包管」。欄位內容（承租人資格、住宅政策補貼戶、代理人最多 3 位、charter 改填公司資料）對碼正確
28. `jgb/D/social-housing-tenant-tabs-overview`（9.16 S3 doubt）：句序 1：說承租方分組「一律」有四個分頁，而且都用來確認租客的社宅資格，但選包租包管範本時會拿掉家庭＆財產、授權、附件，承租方也改填公司資料
29. `jgb/E/balance-invoice-monthly-invoice-table`（9.16 S3 doubt）：句序 4：「要開立差額發票，是在群組列表動作選單點『開立發票』」把手動開立寫成唯一方式，漏了系統每月自動開立這條主路徑，手動和自動兩條流程混成一條
30. `jgb/E/bill-actions-received`（9.16 S3 doubt）：句序 8：寫成到帳時「一律」寄附收據 PDF 的信，但特定合作團隊的款項確認信完全不附收據，漏了這個團隊例外（帳本本身也寫了「或不附」）
31. `jgb/E/bill-internal-note-visibility`（9.16 S3 doubt）：句序 1：標題和句 1 把「可填」限在新增帳單（單筆）與編輯帳單，帳單列表欄位只算「可看」；但帳單列表的「內部備註」欄其實可以直接行內編輯後存檔，有程式反例
32. `jgb/E/bill-partial-month-proration`（9.16 S3 doubt）：句序 1：把設定檔註解裡的標籤「合約預覽帳單」加引號寫成團隊可以開關的功能名，但前台沒有這個字；實際上是寫死只有兩個特定合作團隊關閉，應改寫成「特定合作團隊」
33. `jgb/E/bill-receipt-feature-roadmap`（9.16 S3 doubt）：句序 1：「系統也會自動寄送附收據 PDF 的通知信給租客」是絕對句，漏了特定合作團隊的信完全不附收據；標題「一律可以看到系統寄送的收據」也跟著過頭
34. `jgb/E/bill-tenant-unverified-draft-lock`（9.16 S3 doubt）：句序 1：「帳單停留在草稿、驗證完成前發不出去」只能在畫面提示文字裡找到；現行單張送出、新增後送出、批次新增送出這幾條路徑都沒有檢查租客驗證狀態，發送用的 ready() 也沒有，程式並沒有做這個攔截
35. `jgb/E/newebpay-payment-methods`（9.16 S3 doubt）：句序 1：「可以勾選……預設都是開啟的」跟現行畫面不符：Newebpay.vue 的付款方式 checkbox 是未綁定的 input，沒有 checked 也沒有 onChange，畫面上五個框預設是未勾選的，勾不勾都不會改動送出的 paymentMethods；實際送出時一律用後端預設的 enabled true
36. `jgb/E/newebpay-required-fields`（9.16 S3 doubt）：句序 1：標題和第 1、3 句都寫成個人房東可以走藍新開通、只要先補資料；但在現行收款設定頁，個人房東的藍新選項是停用的，會顯示「您無法開通此收款方式」，進不了這條流程，也和同組 payment-gateway-options 的「個人房東不能開通藍新」矛盾。draft 的證據來自舊的 addMerchant 路徑（`page:web:users.add_merchant`、`return redirect()->route('users.role')`）
37. `jgb/E/payment-onboarding-tax-risk`（9.16 S3 doubt）：句序 1：「系統負責代為收款」沒有來源：draft 證據只有 `'您已開通過商店'`，撐不起這個說法。它也跟程式的實際資金流向不一致：藍新的款項留在業者自己的藍新帳戶，國泰、永豐直接入業者的本行帳戶。在稅務語境下寫「系統代收」會誤導；裁決 #102 只允許寫已查證的系統側事實
38. `jgb/E/recharge-account-mismatch-and-duplicate`（9.16 S3 doubt）：句序 2：「一律……系統自動銷帳、多匯留作餘額抵扣後續帳單」寫成絕對，漏了例外：自動銷帳（入金當下與每日排程都一樣）只對後台自動對帳白名單的特定合作團隊生效，其他團隊的餘額不會自動抵帳單，也和同組 daily-settlement 的「限特定合作團隊」互相矛盾

## 核對過程

- **D 包第一輪**（fresh verifier，brief `scratchpad/p920-w2/brief-fix-D.txt`，結論機械取出存 `verdict-D.txt`）：69 項（改動 67＋已由前案處理 2），**REFUTED 66／69**。已由前案處理 2 條皆「過」。不過的 3 項：
  - `contract-thinkcloud-signing-variants` 句 1（P3）：把「列印 → 另存為 PDF」的訊息寫成所有解析失敗都會出現；實際只有較新壓縮格式（`CODE_COMPRESSED_XREF`）才回這句，其他失敗回「此 PDF 檔案無法解析，請確認檔案內容正確或嘗試重新輸出後再上傳。」。
  - `early-termination-tenant-cancel` 句 1（P2）：沒處理 doubt 後半——租客只能取消**自己發起**的提前解約；房東發起的，租客進入後走房東分支、非擁有者被導回。
  - `move-out-checklist-and-damage` 句 0（P2）：改寫成第一步叫「設備損壞確認」，與同粗目未改細目（`move-out-bill-generation` 句 0、`move-out-fee-adjustment-step` 句 0）把第一步稱為「點退清單」矛盾。
- **依 D1 修一次**（ops `scratchpad/p920-w2/ops-recheck-D.json`，新 evidence 4 筆逐字 grep 命中）：
  - thinkcloud 句 1：分寫兩種訊息（一般失敗請確認或重新輸出；較新壓縮格式才建議「列印 → 另存為 PDF」）。
  - tenant-cancel 句 1＋標題：寫明租客只能取消自己發起、還在申請中的提前解約，房東發起的租客無法取消。
  - move-out-checklist 句 0：改為「第一步的點退清單（畫面標題是「設備損壞確認」）」，與同組用語一致。
  - **複核**（fresh verifier，`brief-recheck-D.txt`，結論存 `verdict-recheck-D.txt`）：4 項 **CONFIRMED 4／4**；並確認這一輪 drafts-D 相對上一輪只有這 3 條細目變動。附建議（不阻擋，延後）：thinkcloud 句 1 的「兩種都失敗」略過下載失敗或時間不足時不跑第二種的情況；tenant-cancel 句 2「如果合約不是這個狀態」承接不清，房東發起被擋時的實際提示是「很抱歉！目前系統繁忙中。」。
- **附建議**（不阻擋）：`move-out-checklist-and-damage` 新增句可註明「上傳點退文件」只出現在免註冊租客的合約（未查證，延後）。
- **E 包**（fresh verifier，brief `brief-fix-E.txt`，結論存 `verdict-E.txt`）：29 項 **CONFIRMED 29／29**；刪句 2 項（`bill-tenant-unverified-draft-lock` 句 2、`newebpay-required-fields` 句 2）確認剩下的句子仍成立。附建議（不阻擋，延後）：
  - `bill-tenant-unverified-draft-lock`：同一段提示也出現在帳單編輯頁（`BillTargetBlock.jsx`）、委託合約頁（`entrustedContracts/show/_parts/SignerInfoCard.jsx`）與租客名單頁（`users/lesseeList/parts/PageTop.vue`），標題與句 0 只寫了「合約頁」（outcome verifier 附記 P3）；
  - `newebpay-required-fields`：剩下的句 1／句 2 內容重複、「則／一樣」承接已刪句，可併句；句 2 的 evidence 仍指向舊 addMerchant 路徑（現行對應字串 `'redirect' => route('users.role')`）。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p920-w2/drafts_diff.py --base scratchpad/p920-w2/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p920-w2/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 33; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 539; doubt set: 40 (not found in base: 0)
[diff] changed/deleted items: 96 in 38 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 96; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-A～C、F～I 與備份 `cmp` 相同。`coverage_check` ⇒ `union 40`、PASS。
