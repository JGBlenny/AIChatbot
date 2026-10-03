# 審核單：Plan 9.22 S2 A／C／D／I 修正後重新先審（14 條）

> 審閱的正本版本：commit `fd89adaa`。本單由 `scratchpad/p920-w1/review_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 13／doubt 1／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 帳號資訊 `A-account-profile`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/A/account-basic-info` 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂）
- [pass] `jgb/A/account-contact-info` 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話）
- [doubt] `jgb/A/account-change-password` 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼、新密碼與確認新密碼） —— 句序 4：句子說新密碼「需同時包含英文與數字」，但現行程式沒有擋這條規則：帳號資訊頁的「儲存」按鈕沒有綁 PasswordForm 的 is_allow_submit／password_allow_submit；後端驗證只檢查 min:6 與 same:password_confirmation，所以純數字密碼（例如 123456）照樣會存進去；英數混合在畫面上只是一行提示「密碼應有至少一位英文和數字」

回覆：

## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） `C-estate-dashboard`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/C/estate-dashboard-attachments-vs-contract-attachments` 「附件清單」跟「合約附件」差在哪？（附件清單可上傳 JPG／PNG／PDF、每個物件最多 5 個檔案、單檔 10MB，上傳與下載需要物件編輯權限，刪除操作只有代理人且有新增物件權限才看得到；合約附件是固定的附件項目清單，可上傳附件補充以避免日後爭議）
- [pass] `jgb/C/estate-dashboard-runnings-vs-memos` 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入或支出與金額，記事本沒有金額欄位；兩者都能附檔）

回覆：

## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） `C-team-storefront`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/C/team-public-page-recruitment` 多團隊招募頁和一般招租店舖有什麼不同？（網址格式不同、物件列表只有招租、沒有社區篩選、每頁預設 10 筆）

回覆：

## 簽約與合約檢視 `D-contract-sign-view`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/D/contract-show-panels` 社宅合約的檢視頁面看得到什麼？（承租方、業者、經理人資訊，以及點交點退進行中的提示）
- [pass] `jgb/D/contract-upload-existing-vs-electronic` 上傳既有合約跟建立電子合約差在哪？（上傳＝「紙本簽約」，用於已簽訂或已公證完成的合約；自製合約模板是電子合約的「客製化契約書」）

回覆：

## 租約公證（公證分頁與公證服務） `D-notary`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/D/general-contract-notary-tab` 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；只有部分合約範本有此選項）
- [pass] `jgb/D/contract-thinkcloud-esign-service` 簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）
- [pass] `jgb/D/contract-thinkcloud-signing-variants` 簽署畫面與客製化契約書 PDF 要注意什麼？（公會中文版合約加補充條款會多一組簽名位置；上傳的 PDF 底稿無法解析時合約建立不了，要重新輸出再上傳）

回覆：

## 方案、價格與免費試用 `I-pricing`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/I/pricing-free-trial-eligibility` 免費試用怎麼開始、能用多久？（企業團隊與社宅房東建立身分時自動取得，個人房東未帶優惠代碼時自動取得；一個週期後不自動續訂）
- [pass] `jgb/I/pricing-free-vs-experience-plan` 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者付費訂閱、可選月繳或年繳，可建 10 個物件並自行續訂）
- [pass] `jgb/I/pricing-quota-full-block` 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）

回覆：
