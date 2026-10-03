# 審核單：Plan 9.21 W1-S2 A／B／C 修正後重新先審（43 條）

> 審閱的正本版本：commit `ca8b3a08`。本單由 `scratchpad/p920-w1/review_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 40／doubt 3／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 註冊帳號（Email／SSO、驗證碼、手機綁定） `A-registration`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/A/register-tenant-contract-invitation` 租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「立即註冊」接續完成）
- [pass] `jgb/A/register-captcha-expired` 註冊卡在機器人驗證過期怎麼辦？（重新勾選「我不是機器人」；寄驗證信時沒通過會退回第一步）
- [pass] `jgb/A/register-email-link-resume` 從信箱 App 點註冊連結、去收驗證碼再回來，會從頭開始註冊嗎？（同一瀏覽器會記住 Email 回到驗證碼步驟；機器人驗證失效時退回第一步）

回覆：

## 忘記帳號、忘記密碼 `A-account-recovery`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/A/forget-account-flow` 忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）

回覆：

## 帳號資訊 `A-account-profile`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/A/account-basic-info` 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂）
- [pass] `jgb/A/account-change-password` 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼、新密碼與確認新密碼）
- [doubt] `jgb/A/account-contact-info` 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話） —— 句序 5：「第二組聯絡號碼欄位限填純數字」在程式裡沒有被強制：「限純數字」提示判斷的是另一個 store 值 premises_edit.contact.phone2（預設 ''，這頁的輸入框沒綁到它），提示永遠不會出現；後端存檔時也是原值照存，沒有任何數字驗證

回覆：

## 通知中心 `A-notification-center`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/A/notification-mark-read-navigate` 點擊通知列表項目會發生什麼？（前往原連結並把該則通知標為已讀；訊息類通知不換頁）
- [pass] `jgb/A/notification-mark-read-out-of-range` 篩選後頁碼超出範圍會自動跳回第一頁嗎？（不會，只會顯示空的通知清單）

回覆：

## 通知收件設定與發送報表（通知收件信箱最多再加 3 組） `A-notification-settings`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/A/notification-settings-report-buttons` 「發送報表」「多團隊合併報表」按鈕是做什麼的？（選起始日與終止日，把加盟分潤報表寄到自訂通知信箱；僅限加盟分潤報表分類，多團隊合併僅限特定團隊）

回覆：

## 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） `B-team-profile`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/B/team-signer-personal-info` 簽約資訊卡「個人資訊」區塊要填什麼？（只有租客與個人房東身分才有；姓氏、名稱、身分證字號、Email、手機、戶籍地址、通訊地址必填；身分證正反面與其他附件選填）
- [pass] `jgb/B/team-signer-profile-switch` 怎麼在多組簽約資訊之間切換？（頁面上方有可切換的分頁列，超過 5 組時另外多出「所有團隊」下拉選單）

回覆：

## 大房東報表 `B-biglandlord-report`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/B/biglandlord-report-overview` 大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）
- [pass] `jgb/B/biglandlord-report-permission` 誰看得到大房東報表？（法人房東與社宅團隊身分，且角色要有「查看大房東報表」權限）
- [pass] `jgb/B/biglandlord-report-community-rate` 大房東報表可以依社區細看嗎？（報表清單有「社區」欄，幣別不同時細節頁會顯示匯率）

回覆：

## 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） `B-advanced-settings`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/B/advance-fee-items` 「帳單自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填）
- [pass] `jgb/B/advance-custom-label` 「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤輸入框最多收 9 個字元）

回覆：

## 租客列表（當前租客／封存、準時繳租率、信用評價） `B-tenant-list`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/B/lessee-bulk-notify` 租客列表勾選多筆租客後可以做什麼？（特定合作團隊可以批次發送通知，其他團隊沒有這個批次操作）

回覆：

## 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） `C-community-estates`（待審 5 條：pass 5／doubt 0／未先審 0）

- [pass] `jgb/C/community-estates-overview-card` 社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額）
- [pass] `jgb/C/community-estates-category-switch` 社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變）
- [pass] `jgb/C/community-estates-add-batch-copy` 怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）
- [pass] `jgb/C/community-estates-extra-tabs` 社區底下有差額發票、投報率頁籤嗎？（差額發票看該社區是否開通；投入成本與投報率由團隊的投報率功能開關一起控制，租客、大房東與沒有「查看所有帳單」權限的成員看不到）
- [pass] `jgb/C/community-estates-pagination` 社區物件清單每頁筆數可以調整嗎？（30／60／90項）

回覆：

## 物件列表與篩選 `C-estate-list`（待審 10 條：pass 10／doubt 0／未先審 0）

- [pass] `jgb/C/estate-list-add-must-pick-community` 物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）
- [pass] `jgb/C/estate-list-counter-and-limit` 物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）
- [pass] `jgb/C/estate-list-filters` 物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤）
- [pass] `jgb/C/estate-list-keyword-search` 物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）
- [pass] `jgb/C/estate-list-batch-actions` 物件總表可以批次操作嗎？（個人房東、大房東、租客身分不能；法人房東與社宅團隊成員可：匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示）
- [pass] `jgb/C/estate-status-affects-actions` 物件狀態會影響哪些功能？（招租廣告狀態未刊登／刊登中，與合約狀態洽談中／租約中，是各自獨立的；刪除物件要求未刊登、沒有合約、沒有 IoT 綁定）
- [pass] `jgb/C/estate-list-pagination` 物件總表每頁筆數可以調整嗎？（30／60／90項）
- [pass] `jgb/C/estate-list-filters-space-type-and-others` 物件總表篩選還有哪些條件？（空間類型多選、「更多」：VR、有電梯、可開伙、可養寵物）
- [pass] `jgb/C/estate-list-category-switch` 物件總表怎麼切換總覽／招租／買賣？（三種分類切換）
- [pass] `jgb/C/estate-list-sort-remembers-last` 物件總表怎麼排序？（排序選項由系統提供，寬度 576px 以上切換的排序會被記住）

回覆：

## 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） `C-estate-edit`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/C/estate-edit-basic-space-type` 物件基本資料的空間類型、用途、格局要怎麼填？
- [pass] `jgb/C/estate-edit-building-transcript-general` 一般物件建物謄本可以填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物，皆非必填）
- [pass] `jgb/C/estate-edit-facilities` 物件附設傢俱怎麼設定？（依用途與格局分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁）

回覆：

## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） `C-estate-dashboard`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/C/estate-dashboard-runnings-vs-memos` 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入或支出與金額，記事本沒有金額欄位；兩者都能附檔）
- [doubt] `jgb/C/estate-dashboard-attachments-vs-contract-attachments` 「附件清單」跟「合約附件」差在哪？（附件清單可上傳 JPG／PNG／PDF、每個物件最多 5 個檔案、單檔 10MB，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是固定的附件項目清單，可上傳圖片補充以避免日後爭議） —— 句序 3：下載附件後端要求物件編輯權限（edit_estate，或代理人且有 add_estate），沒有權限的使用者（包括能看到「附件清單」分頁的大房東）下載時會收到「權限不足！」，所以句子和標題的「下載不限身分」與程式相反

回覆：

## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） `C-team-storefront`（待審 5 條：pass 4／doubt 1／未先審 0）

- [pass] `jgb/C/team-public-page-purpose` 房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）
- [pass] `jgb/C/team-public-page-edit-and-banner` 招租店舖上可以直接編輯哪些內容？（橫幅照片、頭像、自我介紹；團隊身分另可改團隊名稱等欄位，需要「編輯團隊權限」）
- [pass] `jgb/C/team-public-page-filter-and-view` 招租店舖怎麼篩選物件？（篩選條件加關鍵字搜尋，手機版多數條件收在「更多」；可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30）
- [pass] `jgb/C/team-public-page-share` 招租店舖怎麼分享？（電腦上開分享視窗可複製連結或分享到 FB、Line、LinkedIn；手機上會叫出系統分享選單；分享的是目前頁面的網址）
- [doubt] `jgb/C/team-public-page-recruitment` 多團隊招募頁和一般招租店舖有什麼不同？（沒有指定住宅或商用時自動轉址到住宅、只顯示招租、不顯示社區篩選、每頁預設 10 筆） —— 句序 1：標題把「沒有指定用途時自動轉址到住宅」列為與一般店舖的差異，但一般招租店舖缺 mode 或 premisesUseFor 時同樣會轉址補上 rent／residential，所以這一點不是差異；另外講法「招募頁跟一般店舖的網址不一樣嗎」在內文找不到答案（內文沒寫 /p/recruitment/{slug} 和 /p/{encryptId}/{mode}/{premisesUseFor} 的網址差別）

回覆：
