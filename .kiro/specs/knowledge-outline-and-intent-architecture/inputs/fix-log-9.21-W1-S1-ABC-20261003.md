# Plan 9.21 W1-S1 修正紀錄（A／B／C 疑點 25 條，新 D1「修整條」）

> 允許集合 `scratchpad/p921-w1/allowed.json`（25 條，A 8／B 5／C 12；兩來源＝repo 審核單 9.19 S2 與從 transcript 重取的 raw）。基準＝`scratchpad/p921-w1/backup/drafts/`。句序一律為**備份側**句序（drafts_diff 的 item 句序，0 起算）；9.19 doubt 的「句序」為 1 起算（0＝標題），依據節照原文保留。**範圍**寫在「依據」欄：`依據 #n`＝doubt 所指、`整條 #m`＝同條整條檢查新增、`依據 #n＋整條 #m`＝兩者（計畫 §1「新 D1」）。起草＝executor（`scratchpad/p921-w1/brief-executor-fix.md`，逐句筆記 `fix-notes.md`），主 session 審閱並機械驗證後套用；ops 原檔 `scratchpad/p921-w1/ops.json`。verifier 判定：過／不過／待核。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/A/account-basic-info` | sentences | 2 | 改 | 依據 #1 | 過 |
| `jgb/A/account-basic-info` | sources |  | 改 | 依據 #1 | 過 |
| `jgb/A/account-change-password` | sentences | 0 | 新增句 | 整條 #1 | 過 |
| `jgb/A/account-change-password` | sentences | 2 | 改 | 整條 #1 | 過 |
| `jgb/A/account-change-password` | sentences | 3 | 刪句 | 依據 #2 | — |
| `jgb/A/account-change-password` | sources |  | 改 | 整條 #1 | 過 |
| `jgb/A/forget-account-flow` | sentences | 1 | 改 | 整條 #2 | 過 |
| `jgb/A/forget-account-flow` | sentences | 2 | 改 | 整條 #2 | 過 |
| `jgb/A/forget-account-flow` | sentences | 3 | 改 | 整條 #2 | 過 |
| `jgb/A/forget-account-flow` | sentences | 4 | 新增句 | 依據 #3 | 過 |
| `jgb/A/forget-account-flow` | sources |  | 改 | 依據 #3 | 過 |
| `jgb/A/notification-mark-read-navigate` | sentences | 0 | 改 | 整條 #3 | 過 |
| `jgb/A/notification-mark-read-navigate` | sentences | 1 | 改 | 依據 #4 | 過 |
| `jgb/A/notification-mark-read-navigate` | sentences | 2 | 新增句 | 整條 #3 | 過 |
| `jgb/A/notification-mark-read-navigate` | sources |  | 改 | 整條 #3 | 過 |
| `jgb/A/notification-mark-read-navigate` | title |  | 改 | 整條 #3 | 過 |
| `jgb/A/notification-settings-report-buttons` | sentences | 0 | 改 | 整條 #4 | 過 |
| `jgb/A/notification-settings-report-buttons` | sentences | 1 | 新增句 | 依據 #5 | 過 |
| `jgb/A/notification-settings-report-buttons` | sentences | 2 | 新增句 | 依據 #5 | 過 |
| `jgb/A/notification-settings-report-buttons` | sources |  | 改 | 依據 #5 | 過 |
| `jgb/A/notification-settings-report-buttons` | title |  | 改 | 依據 #5 | 過 |
| `jgb/A/register-captcha-expired` | phrasings |  | 改 | 依據 #6 | 過 |
| `jgb/A/register-captcha-expired` | sentences | 0 | 改 | 依據 #6 | 過 |
| `jgb/A/register-captcha-expired` | sentences | 1 | 改 | 依據 #6 | 過 |
| `jgb/A/register-captcha-expired` | sentences | 2 | 新增句 | 整條 #5 | 過 |
| `jgb/A/register-captcha-expired` | sources |  | 改 | 整條 #5 | 過 |
| `jgb/A/register-captcha-expired` | title |  | 改 | 依據 #6 | 過 |
| `jgb/A/register-email-link-resume` | phrasings |  | 改 | 依據 #7 | 過 |
| `jgb/A/register-email-link-resume` | sentences | 0 | 改 | 依據 #7 | 過 |
| `jgb/A/register-email-link-resume` | sentences | 1 | 改 | 依據 #7＋整條 #6 | 過 |
| `jgb/A/register-email-link-resume` | sentences | 2 | 新增句 | 整條 #6 | 過 |
| `jgb/A/register-email-link-resume` | sources |  | 改 | 整條 #6 | 過 |
| `jgb/A/register-email-link-resume` | title |  | 改 | 依據 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sentences | 0 | 改 | 整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sentences | 1 | 改 | 整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sentences | 2 | 改 | 依據 #8＋整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sentences | 3 | 改 | 整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sentences | 4 | 新增句 | 整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | sources |  | 改 | 整條 #7 | 過 |
| `jgb/A/register-tenant-contract-invitation` | title |  | 改 | 依據 #8 | 過 |
| `jgb/B/advance-custom-label` | sentences | 2 | 改 | 依據 #9 | 過 |
| `jgb/B/advance-custom-label` | sentences | 3 | 新增句 | 依據 #9 | 過 |
| `jgb/B/advance-custom-label` | sources |  | 改 | 依據 #9 | 過 |
| `jgb/B/advance-custom-label` | title |  | 改 | 依據 #9 | 過 |
| `jgb/B/advance-fee-items` | phrasings |  | 改 | 依據 #10 | 過 |
| `jgb/B/advance-fee-items` | sentences | 1 | 改 | 整條 #8 | 過 |
| `jgb/B/advance-fee-items` | sentences | 3 | 新增句 | 整條 #8 | 過 |
| `jgb/B/advance-fee-items` | sources |  | 改 | 整條 #8 | 過 |
| `jgb/B/advance-fee-items` | title |  | 改 | 整條 #8 | 過 |
| `jgb/B/biglandlord-report-permission` | sentences | 0 | 改 | 依據 #11 | 過 |
| `jgb/B/biglandlord-report-permission` | sentences | 1 | 新增句 | 整條 #9 | 過 |
| `jgb/B/biglandlord-report-permission` | sources |  | 改 | 依據 #11 | 過 |
| `jgb/B/biglandlord-report-permission` | title |  | 改 | 依據 #11 | 過 |
| `jgb/B/lessee-bulk-notify` | sentences | 0 | 改 | 依據 #12 | 過 |
| `jgb/B/lessee-bulk-notify` | sentences | 1 | 新增句 | 依據 #12 | 過 |
| `jgb/B/lessee-bulk-notify` | sources |  | 改 | 整條 #10 | 過 |
| `jgb/B/team-signer-personal-info` | sentences | 0 | 改 | 整條 #11 | 過 |
| `jgb/B/team-signer-personal-info` | sources |  | 改 | 整條 #11 | 過 |
| `jgb/B/team-signer-personal-info` | title |  | 改 | 整條 #11 | 過 |
| `jgb/C/community-estates-extra-tabs` | sentences | 1 | 改 | 整條 #12 | 過 |
| `jgb/C/community-estates-extra-tabs` | sources |  | 改 | 整條 #12 | 過 |
| `jgb/C/community-estates-extra-tabs` | title |  | 改 | 依據 #14 | 過 |
| `jgb/C/community-estates-overview-card` | sentences | 2 | 改 | 依據 #15＋整條 #13 | 過 |
| `jgb/C/community-estates-overview-card` | sentences | 3 | 新增句 | 依據 #15 | 過 |
| `jgb/C/community-estates-overview-card` | sources |  | 改 | 依據 #15＋整條 #13 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 0 | 改 | 依據 #16＋整條 #14 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 1 | 改 | 依據 #16＋整條 #14 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 2 | 新增句 | 依據 #16 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 3 | 新增句 | 整條 #14 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sources |  | 改 | 整條 #14 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | title |  | 改 | 依據 #16＋整條 #14 | 過 |
| `jgb/C/estate-dashboard-runnings-vs-memos` | sentences | 0 | 改 | 整條 #15 | 過 |
| `jgb/C/estate-dashboard-runnings-vs-memos` | sentences | 1 | 改 | 整條 #15 | 過 |
| `jgb/C/estate-dashboard-runnings-vs-memos` | sentences | 2 | 新增句 | 整條 #15 | 過 |
| `jgb/C/estate-dashboard-runnings-vs-memos` | sources |  | 改 | 整條 #15 | 過 |
| `jgb/C/estate-dashboard-runnings-vs-memos` | title |  | 改 | 依據 #17 | 過 |
| `jgb/C/estate-edit-facilities` | sentences | 0 | 改 | 依據 #18 | 過 |
| `jgb/C/estate-edit-facilities` | sentences | 1 | 改 | 整條 #16 | 過 |
| `jgb/C/estate-edit-facilities` | sentences | 2 | 新增句 | 整條 #16 | 過 |
| `jgb/C/estate-list-batch-actions` | sentences | 0 | 改 | 依據 #19 | 過 |
| `jgb/C/estate-list-batch-actions` | sentences | 1 | 改 | 整條 #17 | 過 |
| `jgb/C/estate-list-batch-actions` | sentences | 2 | 新增句 | 整條 #17 | 過 |
| `jgb/C/estate-list-batch-actions` | sources |  | 改 | 整條 #17 | 過 |
| `jgb/C/estate-list-batch-actions` | title |  | 改 | 依據 #19 | 過 |
| `jgb/C/estate-list-filters` | sentences | 2 | 改 | 依據 #20 | 過 |
| `jgb/C/estate-list-filters` | sentences | 3 | 新增句 | 整條 #18 | 過 |
| `jgb/C/estate-list-filters` | sources |  | 改 | 整條 #18 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | sentences | 1 | 改 | 依據 #21 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | sentences | 2 | 新增句 | 依據 #21 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | sources |  | 改 | 依據 #21 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | title |  | 改 | 依據 #21 | 過 |
| `jgb/C/estate-status-affects-actions` | phrasings |  | 改 | 依據 #22 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 0 | 改 | 依據 #22 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 1 | 改 | 依據 #22 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 2 | 改 | 依據 #22 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 3 | 新增句 | 整條 #19 | 過 |
| `jgb/C/estate-status-affects-actions` | sources |  | 改 | 依據 #22 | 過 |
| `jgb/C/estate-status-affects-actions` | title |  | 改 | 依據 #22 | 過 |
| `jgb/C/team-public-page-edit-and-banner` | sentences | 0 | 改 | 依據 #23 | 過 |
| `jgb/C/team-public-page-edit-and-banner` | sentences | 1 | 改 | 依據 #23 | 過 |
| `jgb/C/team-public-page-edit-and-banner` | sentences | 2 | 新增句 | 整條 #20 | 過 |
| `jgb/C/team-public-page-edit-and-banner` | sources |  | 改 | 依據 #23 | 過 |
| `jgb/C/team-public-page-edit-and-banner` | title |  | 改 | 依據 #23 | 過 |
| `jgb/C/team-public-page-filter-and-view` | sentences | 0 | 改 | 依據 #24 | 過 |
| `jgb/C/team-public-page-filter-and-view` | sentences | 1 | 改 | 整條 #21 | 過 |
| `jgb/C/team-public-page-filter-and-view` | sentences | 2 | 新增句 | 整條 #21 | 過 |
| `jgb/C/team-public-page-filter-and-view` | sources |  | 改 | 依據 #24 | 過 |
| `jgb/C/team-public-page-filter-and-view` | title |  | 改 | 依據 #24 | 過 |
| `jgb/C/team-public-page-share` | sentences | 0 | 改 | 依據 #25 | 過 |
| `jgb/C/team-public-page-share` | sentences | 1 | 改 | 整條 #22 | 過 |
| `jgb/C/team-public-page-share` | sentences | 2 | 新增句 | 依據 #25 | 過 |
| `jgb/C/team-public-page-share` | sources |  | 改 | 依據 #25 | 過 |
| `jgb/C/team-public-page-share` | title |  | 改 | 依據 #25 | 過 |

## 刪除

（無）

## 已由前案處理

（無）

## 停下交業主

（無）

## 依據

1. `jgb/A/account-basic-info`（9.19 S2 doubt）：句序 3：「姓氏、名稱、身分證字號都已填寫才鎖定」只是其中一條路徑；房東在租客簽完後簽署的那條路徑，只要合約上有租客身分證字號，而且團隊在名單內，就會直接上鎖，不看姓名有沒有填
2. `jgb/A/account-change-password`（9.19 S2 doubt）：句序 4：程式是把新密碼寫進 father_id 底下所有子帳號，其中也包含 Email 登入帳號，跟「有沒有綁 Facebook/Google/LINE」無關。這是內部資料結構的細節，寫成「同步到綁定的登入帳號」會讓人誤以為第三方帳號的密碼也改了
3. `jgb/A/forget-account-flow`（9.19 S2 doubt）：句序 4：「聯繫所屬的租賃管理業者」出自幫助中心寫給租客的文章，但本細目的對象是房東/管理者，這句沒有限定身分；現行畫面寫的則是「如有其他問題，請聯繫 JGB 客服」
4. `jgb/A/notification-mark-read-navigate`（9.19 S2 doubt）：句序 2：「每則通知會顯示所屬物件名稱、通知來源使用者姓名」這個絕對句漏了例外：物件名稱和來源姓名都包在 estate_title 非空的條件裡，沒有物件的通知兩者都不顯示。另外這句是在講列表長什麼樣，沒有回答「點擊會發生什麼」
5. `jgb/A/notification-settings-report-buttons`（9.19 S2 doubt）：句序 1：標題問按鈕「是做什麼的」，講法也有「分潤報表怎麼看」，但內文只說按了會開啟燈箱；沒寫出這個視窗實際的用途：選起始日和終止日，再把該區間的報表寄到信箱。所以標題和講法都答不到
6. `jgb/A/register-captcha-expired`（9.19 S2 doubt）：句序 1：提示加退回第一步，只發生在寄驗證信時後端回 recaptcha_required；如果停在第一步時勾選過期，只會把「繼續」按鈕收起來，不會提示也沒有退回。另外講法「驗證框顯示不出來」內文完全沒有回答
7. `jgb/A/register-email-link-resume`（9.19 S2 doubt）：句序 1：標題和講法寫的是「驗證信連結」，但驗證信裡只有驗證碼，沒有註冊連結；程式處理的其實是從信箱 App 重新點開「註冊邀請連結」的情境。句 1 也是照程式註解改寫的開發背景說明
8. `jgb/A/register-tenant-contract-invitation`（9.19 S2 doubt）：句序 3：「點選「註冊」按鈕」這個引號標籤是照幫助中心文件寫的，現行登入頁上沒有叫「註冊」的按鈕，只有「立即註冊」；標題也有同樣問題
9. `jgb/B/advance-custom-label`（9.19 S2 doubt）：句序 3：說明文字寫 18 字元（9 個字），但程式實際不分中英文，一律只收 9 個字元，打英文也收不到 18 個；標題和第 3 句寫的「18 字元」跟程式行為不符
10. `jgb/B/advance-fee-items`（9.19 S2 doubt）：句序 1：講法「費用項目可以合併嗎」在本條三句裡都答不到（合併寫在另一條 advance-fee-items-merge）
11. `jgb/B/biglandlord-report-permission`（9.19 S2 doubt）：句序 1：「才不會在選單整理時被拿掉」是在描述程式的 unset 動作，屬於實作用語；而且列出的來源 UserController.php 只有權限名稱，選單的顯示規則其實在 app/Role.php，另外選單項目只給法人和社宅團隊（allow_role_key）這個身分條件也沒寫
12. `jgb/B/lessee-bulk-notify`（9.19 S2 doubt）：句序 1：批次操作列固定黏在列表上方，不在「畫面下方」。另外，非特定合作團隊的列表根本沒有勾選框，並不是「勾選後沒有批次列」
13. `jgb/B/team-signer-personal-info`（9.19 S2 doubt）：句序 4：標題講的是只有個人團隊看得到的「個人資訊」區塊，但第 4、5 句寫的是公司資訊的地址欄位和社宅團隊的經紀人／管理人員地址。這兩塊只有法人或社宅團隊看得到，和標題不符，等於把另一條細目 team-signer-address-groups 的內容混了進來
14. `jgb/C/community-estates-extra-tabs`（9.19 S2 doubt）：句序 標題：標題寫兩種頁籤都「依團隊是否開通」，但差額發票頁籤看的是單一社區自己的開關，內文也寫「該社區開通」，標題和內文互相矛盾
15. `jgb/C/community-estates-overview-card`（9.19 S2 doubt）：句序 3：卡片右上角的選單只在電腦版出現。手機版沒有這個選單，改成在卡片下方顯示「編輯社區」「預覽廣告頁」「刪除社區」，標籤也不同。絕對句漏了手機版例外
16. `jgb/C/estate-dashboard-attachments-vs-contract-attachments`（9.19 S2 doubt）：句序 1：「加價購」按鈕在現行程式裡已被註解掉，畫面上不存在；講法「附件清單空間不夠怎麼辦」會因此被答成一條走不到的路（另外，「租賃法定文件」在畫面上沒有來源，畫面原文是「如有以下附件，可上傳圖片做補充，以避免日後爭議」）
17. `jgb/C/estate-dashboard-runnings-vs-memos`（9.19 S2 doubt）：句序 0（標題）：標題說記事本「只是純文字備註」，但第 2 句與程式都顯示記事本可以附加附件，標題跟內文互相矛盾
18. `jgb/C/estate-edit-facilities`（9.19 S2 doubt）：句序 1：「商用」和「有建物」這兩個標題底下只有必填的「座位數」，不是設定家電、傢俱的地方。商用物件的傢俱在「辦公空間」區塊，店面在「店面空間」區塊。「每個區塊都能設定家電、傢俱」不成立
19. `jgb/C/estate-list-batch-actions`（9.19 S2 doubt）：句序 1：個人房東、大房東、租客在物件總表沒有勾選框，完全不能批次操作。句子只寫「依權限」，漏了身分例外
20. `jgb/C/estate-list-filters`（9.19 S2 doubt）：句序 3：「篩選結果：目前範圍／總筆數」只在寬螢幕（lg）顯示；窄螢幕看不到，手機版篩選區塊也沒有這一行。絕對句漏了手機版例外
21. `jgb/C/estate-list-sort-remembers-last`（9.19 S2 doubt）：句序 3：「窄螢幕不會自動帶入上次的排序」與程式不符。進入頁面時一律用 estatesList 這個鍵讀回排序，不看螢幕寬度，所以窄螢幕也會帶入在寬螢幕選過的排序；窄螢幕只是不會把自己的選擇存成 estatesList。分界是 576px，也不是「電腦版」
22. `jgb/C/estate-status-affects-actions`（9.19 S2 doubt）：句序 1：這條把幫助中心的舊四態分類（文件寫「合約中」）和程式標籤「租約中」拼在一起。現行程式的合約狀態貼紙只有 無合約／洽談中／租約中，刊登狀態（未刊登／刊登中）是另一個獨立維度；四態互斥的狀態表在後端是被註解掉的舊碼。各狀態可做的操作也只有文件來源，找不到現行程式對應
23. `jgb/C/team-public-page-edit-and-banner`（9.19 S2 doubt）：句序 1：程式裡能編輯的欄位跟句子不符。個人房東的「姓名」沒有 editable，只有自我介紹可以改；團隊身分能編輯的是「團隊名稱」「經理人證號」「租賃管理員證號」「公司電話」「公司Email」「團隊介紹」，沒有「姓名／自我介紹」這兩個標籤。句子也漏了權限條件：必須同時符合 is_admin 和 edit_role 權限才能編輯。這句只照幫助中心寫，跟現行程式衝突
24. `jgb/C/team-public-page-filter-and-view`（9.19 S2 doubt）：句序 1：「鄉鎮/區或捷運」「類型與格局」這兩個群組標題只出現在 id="asideFilter" 的 Lightbox2 裡，而整個 src 都沒有任何地方打開這個燈箱，是走不到的畫面。現行實際的篩選列是 PublicSearchBlock／PublicSearchBlockM，內容有縣市、區域、社區、捷運、類型、房數、建築類型、租金、面積、其他，並不是「兩組」
25. `jgb/C/team-public-page-share`（9.19 S2 doubt）：句序 1：絕對句漏了手機裝置的例外：在 Android／iOS 裝置上，如果瀏覽器支援 navigator.share，會直接叫出系統原生的分享選單，不會出現 FB／Line／LinkedIn／複製連結的燈箱

## 整條依據

1. `jgb/A/account-change-password`：密碼表單另要求新密碼須同時含英文與數字、且帳號無密碼時不顯示「密碼」區塊：code:src/components/PasswordForm.vue `return /[0-9]/.test(this.password) && /[a-zA-Z]/.test(this.password)`；code:app/Http/Controllers/UserController.php `$showPassword = !empty($user->password);`
2. `jgb/A/forget-account-flow`：「沒綁手機」說明是靜態文字而非條件式提示，並補帳號提示遮蔽規則與找不到號碼的錯誤：code:app/Http/Controllers/AuthController.php `$account = asterisks($account, $showCount);`
3. `jgb/A/notification-mark-read-navigate`：點擊後的標已讀行為由目標頁載入時處理，原句含糊且一句兩事：code:app/Http/Controllers/Controller.php `Notification::markAsRead($this->user->id, $this->role->id, $notificationId);`
4. `jgb/A/notification-settings-report-buttons`：「發送報表」分類限定開放，且需補寄送對象與失敗情況：code:app/Services/FranchiseProfitShareService.php `if (isset($emailGroups['franchiseProfitShare']['custom_emails'])) {`
5. `jgb/A/register-captcha-expired`：「通行證」實作詞改寫並補機器人驗證 30 分鐘時效：code:app/Services/AuthService.php `const REGISTER_CAPTCHA_TTL = 1800;`
6. `jgb/A/register-email-link-resume`：原句「在另一個瀏覽器開啟連結會清空 Email」與程式不符，並補回到驗證碼步驟會再寄驗證信：code:src/pages/users/auth/parts/EmailVerify.vue `emailVerificator.send()`
7. `jgb/A/register-tenant-contract-invitation`：「待租客簽回顯示 Email」「右下角」無源，租客免註冊其實由房東建約時選擇，並補簡訊邀請：code:src/pages/contracts/edit/tenantInfo/Index.jsx `label: t('租客免註冊'),`；code:app/Notification.php `sms($configCountry[$toUserPhoneCountryKey]['code'], $contract->to_user_phone, $message, 'l1');`
8. `jgb/B/advance-fee-items`：「必填」只是畫面標示、標題標籤字樣需對齊介面，並補自訂／預設項目的操作：code:src/pages/users/advance/_part/FeePanel.vue `<div class="after-required mb-1 text-[13px]">{{ t('性質') }}</div>`
9. `jgb/B/biglandlord-report-permission`：補權限的開啟條件（需先有「查看大房東列表」）：code:app/Http/Controllers/UserController.php `'requires'=> ['g_show_biglandlord']`
10. `jgb/B/lessee-bulk-notify`：補「發送通知」實際操作與收件對象（來源檔補齊）：code:src/pages/users/lesseeList/parts/ListTable.vue `targets: state.pickedItems.map((node)=>{`
11. `jgb/B/team-signer-personal-info`：「個人資訊」區塊對租客與個人房東都顯示，原寫「只有個人團隊」漏租客身分：code:src/pages/users/team/_parts/SignerDetails.vue `isIndividual: computed(()=>[1, 2].includes(store.state?.userData?.role?.config_rule_key)),`
12. `jgb/C/community-estates-extra-tabs`：投入成本／投報率頁籤漏租客身分例外，且「帳單查看權限」應為介面標籤「查看所有帳單」：code:app/Http/Controllers/CommunityController.php `if ((int) $role->config_rule_key === \App\Role::RULE_KEY_TENANT) {`
13. `jgb/C/community-estates-overview-card`：卡片數量與金額只計入登入者有權限看到的物件，原句漏身分限定：code:app/Services/CommunityService.php `if ($role->hasPermissionByUser($user->id, 'show_estate')) {`
14. `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：附件清單的上限是檔案個數（5 個）而非總儲存空間，並補合約附件的上傳權限：code:app/Http/Controllers/EstateController.php `$attachmentDatas['max'] = 5; // 最大數量限制`；code:src/pages/estates/dashboard/contractAttachments/index.vue `return !store.state.userData.is_big_landlord &&`
15. `jgb/C/estate-dashboard-runnings-vs-memos`：兩條都把可留空的欄位寫成「要填」，並補附件上限與流水帳權限擋下：code:app/Http/Controllers/EstateController.php `'price' => 'required|gte:0'`；code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue `maxNumberOfFiles: 3 - (props.form?.attachments?.length || 0),`
16. `jgb/C/estate-edit-facilities`：「任何項目數量 0 不顯示」漏「大樓/社區空間」是勾選的例外，並補車位／空地不需設定格局：code:src/pages/estates/edit/facilities/_parts/General.vue `{{ t('空地用途物件，不需要設定「格局」內容') }}`
17. `jgb/C/estate-list-batch-actions`：「結果燈箱列出物件」與程式不符（只顯示件數），「刪除」是條件不符即不出現：code:src/components/Lightbox/EstatePublishResult.jsx `t('清單中的 [s1] 個物件資訊不齊全，並未刊登廣告。', [props.failCount])`
18. `jgb/C/estate-list-filters`：手機版篩選排列不同，且租金範圍只在幣別為 TWD 時出現：code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlockM.jsx `store.state.siteOptions.dollarSign === 'TWD'`
19. `jgb/C/estate-status-affects-actions`：補單一物件刪除的條件（未刊登、無合約、無 IoT 綁定）：code:app/Http/Controllers/EstateController.php `if ($estate->has_iot) {`
20. `jgb/C/team-public-page-edit-and-banner`：「連動帳號資訊」只對頭像成立，橫幅與自我介紹不在帳號資訊頁：code:app/Http/Controllers/UserController.php `$user->avatar = $avatarData ? $avatarData['filename'] : $user->avatar;`
21. `jgb/C/team-public-page-filter-and-view`：多團隊招募頁沒有經理人與社區篩選，並把顯示模式與每頁筆數拆成兩句：code:src/pages/users/public/_parts/TopFilter.vue `...(route.params.encryptId !== 'recruitment' ? {`
22. `jgb/C/team-public-page-share`：分享網址含已套用的篩選條件（route.fullPath）：code:src/pages/users/public/_parts/AsideInfo.vue `url: `${window.location.protocol}//${window.location.host}${route.fullPath}`,`

## 整條待裁

- `jgb/A/account-change-password`：已有待裁 #4（`open-questions-20261003-s4-920.md`）：後端驗證 `'password' => 'min:6|…'` 允許剛好 6 碼，但後端訊息文案寫「密碼必須超過6個字元」，兩者不一致、何者為準待業主裁決。本條新句 3 只依畫面提示（`PasswordForm.vue` `tip_pwd_length: '至少6位(含)字元以上'`）與 `min:6` 規則寫「至少 6 個字元」（與原句相同），沒有引用後端錯誤文案，也沒有替待裁選邊；待裁仍在。
- `jgb/C/estate-status-affects-actions`：對應 `open-questions-20261003-s4-920.md` 待裁 #14（文件四態與程式三態是否為同一機制，無法判斷）。我依規則 5「文件與程式衝突以程式為準」只留程式可證的內容，未替待裁選邊。幫助中心 slug39 的「各狀態可做的操作」表是否為現行產品政策（例如「租約中 30 天內到期才可刊登」），程式端找不到對應。我依「以程式為準」刪除，未選邊；若業主要保留文件說法，需先在程式端找到對應或另案確認。

## 另見

（同粗目其他細目或程式本身的問題，本片不改，留下一份計畫或另案）

- `jgb/A/register-captcha-expired`：register-email-link-resume 原句 1 的「在另一個瀏覽器開啟連結 → 清空 Email 退回第一步」與程式不符（另一個瀏覽器根本沒有 localStorage，直接是第一步），已在該條處理（屬 7 號細目本身，不是他條）。
- `jgb/B/advance-fee-items`：另一條 `jgb/B/advance-custom-label` 以外，`FeePanel.vue` 的選項沒有角色限制，但進階設定頁其他區塊（全域設定、社區管理）限法人／社宅；本條不涉及。
- `jgb/C/community-estates-overview-card`：窄螢幕的「刪除社區」在 `Index.vue` 用 `LightBoxAction.delete(…)`，電腦版（`CommunityOverview.vue`）用 `LightBoxAction.community.delete(…)`，兩者是否同一個燈箱本輪沒有查；若手機版刪除無反應屬程式問題，另案。
- `jgb/C/estate-list-filters`：`EstatesAdvanceSearchBlock.jsx` 桌面版還渲染了 `isContractQtyReached` 單選（`EstateSearchKey.isContractQtyReached`），但 `src/use/search/modules/` 底下沒有同名模組，是否真的有畫面不確定，本條未列也未改；若 sibling「物件總表篩選還有哪些條件」要寫此項需另查。
- `jgb/C/estate-status-affects-actions`：同粗目 `jgb/C/estate-list-filters` 的合約狀態篩選項寫「即時合約狀態」，列表貼紙是「無合約」，篩選選項是「無租約」（`contractStatus.js`）；兩個標籤字面不同，兩條都沒有寫出，屬畫面用詞不一致，只提醒。
- `jgb/C/estate-list-sort-remembers-last`：窄螢幕的 `sortingKey` 是 `bills_${route?.params?.action}`（帳單頁的命名，在物件總表套用），應是複製貼上遺留；結果是窄螢幕的排序選擇存進一個與物件總表無關的鍵，屬程式問題，僅提醒。
- `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：①合約附件頁說明寫「圖片僅支援JPG、PNG」，但上傳 input `accept` 含 `application/pdf` 且縮圖元件處理 `.pdf`，說明文字與實際不一致；②`EstateController::dashboard` 的 `add_attachment` 在判斷上限時用 `$attachments['total']`／`$attachments['max']`（頂層），但實際值在 `$attachments['data']` 底下，所以後端上限檢查可能永遠不成立，僅前端 `limitLength` 擋，屬程式問題，不在本輪範圍。
- `jgb/C/estate-dashboard-runnings-vs-memos`：記事本新增（`add_memo`）後端沒有看到類似 `$hasEditPermission` 的檢查，與流水帳（`add_bill_running` 有檢查）不一致，是否為刻意設計不確定，僅提醒、不寫入內文。
- `jgb/C/team-public-page-edit-and-banner`：`AsideInfo.vue` textarea 列用 `row.label`（不存在）而非 `row.labelKey`，且個人房東列的鍵 `lablabelKeyel` 拼錯，造成「自我介紹」「團隊介紹」標籤在畫面上空白，屬程式問題，僅提醒。
- `jgb/C/team-public-page-filter-and-view`：`Index.vue` 的 `asideFilter` 燈箱（含其中的 `FilterDistAndMrt`、`FilterSpaceTypeAndPattern`、`AsideFilter` 等元件）是死碼，可另案清理（⛔ 本輪不改程式）。

## 核對過程

- **A＋B 包**（fresh verifier，`scratchpad/p921-w1/brief-fix-AB.txt`，結論機械取出存 `verdict-AB.txt`）：59 項 **REFUTED 58／59**。不過 1 項：`account-basic-info` 句 2——改後把上鎖條件全拿掉成絕對句；程式兩條上鎖路徑都要求有身分證字號（P2）。
- **C 包**（`brief-fix-C.txt`，`verdict-C.txt`）：54 項 **REFUTED 53／54**。不過 1 項：`team-public-page-filter-and-view` 句 0（與標題）——漏手機版例外（寬度 <576 改用另一個篩選元件，多數條件收在「更多」，租金／售價只在新台幣時出現，關鍵字提示不同）（P2）。
- 兩包 verifier 對「整條」列 56 列全數判過；無範圍標錯判定（只有「範圍可標得更精確」的建議，皆註明不算標錯）。
- **依 D1 修一次**（ops `scratchpad/p921-w1/ops-recheck.json`，新 evidence 6 筆逐字命中）：account-basic-info 句 2 補「兩條路徑都要求已有身分證字號，沒有就不會鎖定」；filter-and-view 句 0／1 加寬度條件、新增手機版句、標題同步、sources 補手機版元件。
- **複核**（`brief-recheck.txt`，`verdict-recheck.txt`）：7 項 **CONFIRMED 7／7**。
- **生成時的 DSP-068 調整**（複核後、重生成時）：`forget-account-flow` 句 3 的引號標籤「身份驗證成功！以下為您的帳號提示：」中間含終止符，生成器以引號不成對大聲失敗；依 DSP-068 改寫成兩段引號「身份驗證成功！」「以下為您的帳號提示：」（兩段各自逐字，`Account.vue` `t('身份驗證成功！以下為您的帳號提示：')`），語意不變，ops 存 `ops-dsp068.json`；由 outcome verifier 一併核。
- 附建議（不阻擋，延後）：兩包與複核共附約 15 則建議（例：askable 欄未同步、`not_supported_greps` 的過期句序、「依簽署方式」用詞可更精確、特定合作團隊的 Email 邀請停用例外），明細見各 verdict 檔，留下一份計畫。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p921-w1/drafts_diff.py --base scratchpad/p921-w1/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p921-w1/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 25; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 539; doubt set: 25 (not found in base: 0)
[diff] changed/deleted items: 113 in 25 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 113; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-D～I 與備份 `cmp` 相同；`scope_check` PASS；`coverage_check` PASS。
