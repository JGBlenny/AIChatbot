# 審核單：Plan 9.21 W2-S2 D／E／F／I 修正後重新先審（35 條）

> 審閱的正本版本：commit `59a43bce`。本單由 `scratchpad/p920-w1/review_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 32／doubt 3／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） `D-contract-edit-general`（待審 6 條：pass 6／doubt 0／未先審 0）

- [pass] `jgb/D/contract-edit-tabs-overview` 建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）
- [pass] `jgb/D/contract-rentbasic-template-and-dates` 「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）
- [pass] `jgb/D/contract-rentbasic-latefee` 「基本條件」分頁的遲繳滯納金怎麼計算？（僅特定合作團隊可見，兩段比例＋拖欠天數門檻，欄位唯讀）
- [pass] `jgb/D/contract-tax-invoice` 稅與發票分頁怎麼設定？（是否開立發票、出租方統一編號、各品項是否應稅）
- [pass] `jgb/D/contract-payment-method` 合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種）
- [pass] `jgb/D/contract-landlord-dealer-basic` 出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、法人房東可用電子簽名圖章）

回覆：

## 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） `D-contract-edit-social-housing`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/D/social-housing-tenant-license` 社宅合約承租方的「授權」分頁要同意什麼？（承租資格變動通知、無自有住宅、所得低於最低生活費標準 3.5 倍、財稅所得總檢核）

回覆：

## 簽約與合約檢視 `D-contract-sign-view`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/D/contract-show-panels` 社宅合約的檢視頁面看得到什麼？（承租方、業者、經理人資訊，以及點交點退進行中的提示）
- [doubt] `jgb/D/contract-upload-existing-vs-electronic` 上傳既有合約跟建立電子合約差在哪？（上傳＝「紙本簽約」，用於已簽訂或已公證完成的合約；自製合約模板是電子合約的「客製化契約書」） —— 句序 2：把畫面上已過時的說明「使用最新 109 年內政部公版合約」當成事實照寫，但現行可選範本是 114 年住宅租賃契約、113 年轉租契約等，「最新 109 年」與程式不符

回覆：

## 點退 `D-move-out`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/D/move-out-bill-generation` 點退會產生什麼帳單？（房東在「點退找補費用」確認費用後送出點退；註冊租客按同意後帳單成立、合約轉為點退完成，不看有沒有繳款；免註冊租客送出即成立）
- [pass] `jgb/D/move-out-eligibility-conditions` 什麼合約可以點退？（合約狀態須為合約成立／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外）

回覆：

## 提前解約 `D-early-termination`（待審 6 條：pass 6／doubt 0／未先審 0）

- [pass] `jgb/D/early-termination-reasons` 房東申請提前解約要選什麼理由？（新版中文合約有 10 項理由可選，其餘合約只能選「其他」）
- [pass] `jgb/D/early-termination-form-fields` 申請提前解約要填什麼？（預計提前解約日須早於原合約到期日、違約金支付方與金額、佐證資料）
- [pass] `jgb/D/early-termination-tenant-cancel` 誰可以取消已送出的提前解約申請？（房東透過小齒輪取消；租客只能取消自己發起、還在申請中的提前解約）
- [pass] `jgb/D/early-termination-eligibility` 什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）
- [pass] `jgb/D/early-termination-effect-move-out` 提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）
- [pass] `jgb/D/early-termination-billing-after` 提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存）

回覆：

## 租約公證（公證分頁與公證服務） `D-notary`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/D/contract-thinkcloud-esign-service` 簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）
- [pass] `jgb/D/contract-thinkcloud-signing-variants` 簽署畫面與客製化契約書 PDF 要注意什麼？（公會中文版合約加補充條款會多一組簽名位置；上傳的 PDF 底稿無法解析時合約建立不了，要重新輸出再上傳）
- [doubt] `jgb/D/general-contract-notary-tab` 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；英文與英越文版合約不支援） —— 句序 4：第 4 句與標題寫成「英文與英越文版合約不支援公證」，漏了例外：程式裡「內政部英文版 包租業」範本（en_us_corporation）其實有公證選項；反過來，英文版代租代管範本（en_us_management）與紙本／客製化（DIY）合約也沒有公證選項，卻同樣只顯示那句提示，所以「英文合約可以公證嗎」這個講法會被答錯

回覆：

## 帳單列表與帳單狀態 `E-bill-list`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/E/bill-actions-received` 「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單）
- [pass] `jgb/E/bill-receipt-feature-roadmap` 收據功能還會不會有新的開發？（現行已到帳帳單的齒輪選單一律看得到收據，目前沒有公開的後續開發時程）

回覆：

## 建立與編輯帳單（單筆、批次、週期批次） `E-bill-create-edit`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/E/bill-internal-note-visibility` 「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆、編輯帳單與帳單列表欄位可填，帳單明細可看；批次／週期帳單頁面不顯示）
- [pass] `jgb/E/bill-tenant-unverified-draft-lock` 租客還沒完成驗證時，帳單會被擋在草稿嗎？（合約頁的提示這樣寫，但目前送出帳單時系統不會因為驗證狀態擋下）
- [pass] `jgb/E/bill-partial-month-proration` 不足一個月的租金怎麼算？（依天數比例；一般團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30）

回覆：

## 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） `E-virtual-account`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/E/recharge-account-mismatch-and-duplicate` 租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留在儲值餘額）

回覆：

## 報修申請流程 `F-repair-apply`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/F/repair-apply-flow-and-entry` 怎麼申請修繕單？（房東方從【修繕管理】>【修繕單總表】、租客從【我的報修】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換）

回覆：

## 修繕單編輯 `F-repair-edit`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/F/repair-edit-amount-visibility` 修繕結算金額在哪裡填、誰看得到？（在「完成修繕」的「房東備註」編輯模式填；「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；填了金額不會自動產生帳單）

回覆：

## 方案、價格與免費試用 `I-pricing`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/I/pricing-free-trial-eligibility` 免費試用怎麼開始、能用多久？（企業團隊與社宅房東建立身分時自動取得，個人房東未帶優惠代碼時自動取得；一個週期後不自動續訂）
- [pass] `jgb/I/pricing-quota-full-block` 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）
- [doubt] `jgb/I/pricing-free-vs-experience-plan` 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件） —— 標題：標題寫體驗方案「每月付費」，但內文第 3 句寫體驗方案可切換「月費／年費」，同粗目 pricing-plan-price-basis 也寫體驗方案年繳＝月費×12，程式確實可以年繳訂體驗方案，標題斷言只能按月付與內容不符

回覆：

## 控制台（設定、通知信範本、自動化任務） `I-control-panel`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/I/control-panel-setting-shell` 進入控制台設定後看到什麼？（上方三層麵包屑與左側「控制台」側邊欄，內容是任務管理器、新增／編輯任務或通知信設定頁）
- [pass] `jgb/I/notification-mail-settings` 通知信副本信箱可以設定嗎？（可以：會員側欄「通知收件信箱」頁每個通知類別最多再加 3 組；控制台裡的「通知信設定」頁只有說明、沒有新增欄位，也沒有入口）

回覆：

## 官網首頁 `I-marketing-home`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/I/homepage-sections-overview` 官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息）
- [pass] `jgb/I/homepage-latest-news-section` 首頁「最新消息」顯示什麼？（用輪播呈現消息，點擊會開啟幫助中心文章）

回覆：
