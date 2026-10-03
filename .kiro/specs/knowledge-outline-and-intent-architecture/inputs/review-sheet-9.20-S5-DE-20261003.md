# 審核單：Plan 9.20 S5 D／E 修正後重新先審（63 條）

> 審閱的正本版本：commit `589e0a14`。本單由 `scratchpad/p920-w1/review_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 50／doubt 13／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） `D-contract-edit-general`（待審 6 條：pass 4／doubt 2／未先審 0） ⚠️

- [pass] `jgb/D/contract-edit-tabs-overview` 建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）
- [pass] `jgb/D/contract-rentbasic-template-and-dates` 「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）
- [pass] `jgb/D/contract-rentbasic-latefee` 「基本條件」分頁的遲繳滯納金怎麼計算？（僅特定合作團隊可見，兩段比例＋拖欠天數門檻，欄位唯讀）
- [pass] `jgb/D/contract-landlord-dealer-basic` 出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、法人房東可用電子簽名圖章）
- [doubt] `jgb/D/contract-tax-invoice` 稅與發票分頁怎麼設定？（是否開立發票、出租方統一編號、各品項是否應稅） —— 句序 3：講法「租金以外可以開發票嗎」只能用「僅提供租金品項開立發票」這句提示回答，但程式會對所有應稅品項開票，押金設算息也有獨立發票，畫面上還有生活費用計稅品項，所以這句提示已過時，照它回答會誤導
- [doubt] `jgb/D/contract-payment-method` 合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種） —— 句序 5：「加入常用帳號」實際看的是 edit_role 權限，也就是「編輯團隊」，跟收款設定無關；收款設定是另一個權限 edit_role_payment「編輯收款設置」

回覆：

## 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） `D-contract-edit-social-housing`（待審 19 條：pass 18／doubt 1／未先審 0）

- [pass] `jgb/D/social-housing-building-detail` 社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）
- [pass] `jgb/D/social-housing-photos-tab` 社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）
- [pass] `jgb/D/social-housing-facilities-tab` 社宅合約「附設傢俱」分頁要填什麼？（設備、隔間、家電與傢俱的數量與型號）
- [pass] `jgb/D/social-housing-rent-basic-conditions` 社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理）
- [pass] `jgb/D/social-housing-early-termination-difference` 社宅合約的提前解約怎麼設定？跟一般合約一樣嗎？（只設定雙方是否可以提前解約，沒有違約金計算方式）
- [pass] `jgb/D/social-housing-rent-fees-tab` 社宅合約「租金費用」分頁要填什麼？（代租金額或包租金額、租金與押金、生活費用）
- [pass] `jgb/D/social-housing-payment-method-tab` 社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種；代租代管範本還要選收款人是原房東或業者）
- [pass] `jgb/D/social-housing-notary` 社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔）
- [pass] `jgb/D/social-housing-attachments-tab` 社宅合約「合約附件」要準備什麼？（合約附件只收其他文件如附註條款、稅籍證明；測量成果圖等在出租方附件分頁，轉租範本除外）
- [pass] `jgb/D/social-housing-subsidy-terms-tab` 社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）
- [pass] `jgb/D/social-housing-landlord-tabs-overview` 社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁）
- [pass] `jgb/D/social-housing-landlord-license-conditions` 社宅合約「授權」分頁要確認什麼？（合法建物條件、住宅使用、同意提供住宅的方式等授權事項）
- [pass] `jgb/D/social-housing-tenant-tabs-overview` 社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件）
- [pass] `jgb/D/social-housing-tenant-basic-status` 社宅合約「基本資料」怎麼審核租客資格？（承租人資格、住宅政策補貼戶、代理人；包租包管改填公司資料）
- [pass] `jgb/D/social-housing-tenant-household` 社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）
- [pass] `jgb/D/social-housing-dealer-basic` 社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）
- [pass] `jgb/D/social-housing-move-in-terms` 社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）
- [pass] `jgb/D/social-housing-charter-sublet-tab-hiding` 社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管不顯示承租方的家庭＆財產、授權、附件，轉租不顯示出租方的授權、附件）
- [doubt] `jgb/D/social-housing-tenant-license` 社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件） —— 句序 1：「家庭年所得是否低於當地一定百分位所得」這個選項在程式裡已被註解掉，畫面上現在是無自有住宅、所得低於最低生活費 3.5 倍、財稅所得總檢核三項，標題的「家庭年所得百分位」也一樣不成立

回覆：

## 簽約與合約檢視 `D-contract-sign-view`（待審 9 條：pass 7／doubt 2／未先審 0）

- [pass] `jgb/D/contract-invite-and-review-period` 合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）
- [pass] `jgb/D/contract-sign-flow-steps` 租客簽約要經過哪些步驟？（填承租方簽約資料與上傳文件、預覽合約、自動扣款先授權信用卡、部分範本另有條款勾選、雲想科技畫面簽名）
- [pass] `jgb/D/contract-esign-no-extra-fee` 電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）
- [pass] `jgb/D/contract-locked-after-signing` 合約簽約後可以修改嗎？（送出前可編輯、雙方簽名完成前可取消邀請重編，簽署完成即無法更改，需重新簽一份新合約）
- [pass] `jgb/D/contract-show-paper-upload-archive` 合約檢視頁的「歸檔資料」是什麼？有什麼檔案限制？（租客免註冊的合約簽署後上傳合約、續約、終止合約的歸檔 PDF，最大 10MB）
- [pass] `jgb/D/contract-show-creditcard-auth-prompt` 簽約時會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時，租客在簽約頁點「下一步」會提示前往授權；特定合作團隊專屬範本除外）
- [pass] `jgb/D/contract-guarantor-add-after-signing` 簽約後可以補加保證人嗎？（租客簽約流程本身就能加連帶保證人；簽約完成後要補加，業者端沒有自助功能，需洽 JGB 客服協助）
- [doubt] `jgb/D/contract-show-panels` 社宅合約的檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示） —— 句序 2：兩種提示是看檢視者身分決定的（租客看到「請確認點交結果」，房東端看到「等待承租方確認」），不是看「目前哪一方在等待」；第 3 句的點退提示也是同一個判斷
- [doubt] `jgb/D/contract-upload-existing-vs-electronic` 上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤） —— 句序 3：10MB 上限出自幫助中心，跟程式不一致：建立紙本合約時，在「基本條件」分頁上傳合約檔案的上限是 15MB；10MB 是合約檢視頁上傳用的元件預設值

回覆：

## 點退 `D-move-out`（待審 7 條：pass 5／doubt 2／未先審 0）

- [pass] `jgb/D/move-out-checklist-and-damage` 點退時怎麼處理設備損壞？（系統點退可逐項填入賠償金額與理由、可儲存草稿；上傳點退文件則只顯示文件）
- [pass] `jgb/D/move-out-timing-window` 點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）
- [pass] `jgb/D/move-out-remains-in-active-list` 點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）
- [pass] `jgb/D/move-out-fee-adjustment-step` 點退第二步「點退找補費用」頁面要填什麼？（系統帶入的點退費用項目，含提前解約時自動帶入的違約金、傢俱賠償，另可填備註、期限、附件）
- [pass] `jgb/D/move-out-tenant-no-response-cancel` 租客不確認點退時要怎麼辦？（系統不會逾期自動放行，只能由房東取消點退邀請後重新發送）
- [doubt] `jgb/D/move-out-bill-generation` 點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成；免註冊租客送出即完成） —— 句序 3：程式裡「點退完成」不看有沒有繳款：註冊租客按下同意，點退帳單就成立，合約當下轉為點退完成，跟句子與標題寫的「租客確認並繳款才算完成」不符（幫助中心這樣寫，但與程式衝突）
- [doubt] `jgb/D/move-out-eligibility-conditions` 什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外） —— 句序 標題：標題寫「合約狀態須為執行中」，內文與程式只允許合約成立（SIGNED）、點交完成、歷史合約；點交中、點退中、提前解約中的合約也在執行中列表，卻不能點退，標題比內容寬

回覆：

## 提前解約 `D-early-termination`（待審 6 條：pass 4／doubt 2／未先審 0） ⚠️

- [pass] `jgb/D/early-termination-tenant-cancel` 誰可以取消已送出的提前解約申請？（房東透過小齒輪取消；租客只能取消自己發起、還在申請中的提前解約）
- [pass] `jgb/D/early-termination-eligibility` 什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）
- [pass] `jgb/D/early-termination-effect-move-out` 提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）
- [pass] `jgb/D/early-termination-billing-after` 提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存）
- [doubt] `jgb/D/early-termination-reasons` 房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」） —— 句序 2：引號內的例句「承租方擅自將租賃住宅轉租或轉讓租賃權於他人」在現行選項裡找不到逐字原文；實際字串中間還有「違反第七條第三項規定，」
- [doubt] `jgb/D/early-termination-form-fields` 申請提前解約要填什麼？（預計提前解約日須早於原合約到期日、違約金支付方與金額、佐證資料） —— 句序 講法：講法「取消提前終止合約」沒辦法用本條內文回答：兩句都只講申請欄位，完全沒提取消（取消寫在 early-termination-tenant-cancel）

回覆：

## 租約公證（公證分頁與公證服務） `D-notary`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/D/general-contract-notary-tab` 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；英文與英越文版合約不支援）
- [pass] `jgb/D/contract-thinkcloud-esign-service` 簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）
- [doubt] `jgb/D/contract-thinkcloud-signing-variants` 簽署畫面與客製化契約書 PDF 要注意什麼？（公會版本合約加補充條款多一個協商條款簽名框；上傳的 PDF 底稿無法解析時合約建立不了，要重新輸出再上傳） —— 句序 1：「協商條款」簽名框這個標籤只出現在程式註解；介面、合約 PDF 範本與設定檔都沒有這個字串，等於把註解當成介面標籤

回覆：

## 委託合約（列表、建立編輯、檢視） `D-entrust-contract`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/D/entrusted-contract-lease-type` 委託合約「包租」跟「代管」有什麼不同？（代管必填服務費計算模式、幣別與金額或比例；計算制度、週期、約定日期兩者都要填）
- [pass] `jgb/D/entrusted-contract-tabs-overview` 委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁）
- [pass] `jgb/D/entrusted-contract-fees` 委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金）

回覆：

## 帳單列表與帳單狀態 `E-bill-list`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/E/bill-receipt-feature-roadmap` 收據功能還會不會有新的開發？（現行已到帳帳單的齒輪選單一律看得到收據，目前沒有公開的後續開發時程）
- [doubt] `jgb/E/bill-actions-received` 「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單） —— 句序 4：「此操作需由 JGB 客服協助。」沒有指明是哪個操作；講法裡的重開發票、作廢發票，在現行齒輪選單是業者可以自己做的動作（需 add_bill 權限），與這句矛盾；標題列出的「退款對帳單」內文也完全沒寫

回覆：

## 建立與編輯帳單（單筆、批次、週期批次） `E-bill-create-edit`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/E/bill-internal-note-visibility` 「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆、編輯帳單與帳單列表欄位可填，帳單明細可看；批次／週期帳單頁面不顯示）
- [pass] `jgb/E/bill-tenant-unverified-draft-lock` 租客還沒完成驗證時，帳單會被擋在草稿嗎？（合約頁的提示這樣寫，但目前送出帳單時系統不會因為驗證狀態擋下）
- [doubt] `jgb/E/bill-partial-month-proration` 不足一個月的租金怎麼算？（依天數比例；一般團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30） —— 句序 講法：講法「點退帳單租金怎麼算」無法由內文回答：內文只寫週期產帳的不足月比例；點退帳單的費用來自合約的點退費用項目，不走這套比例，照內文回答會誤導

回覆：

## 差額發票（群組、底租、社區層開關） `E-balance-invoice`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/E/balance-invoice-monthly-invoice-table` 「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌）

回覆：

## 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） `E-virtual-account`（待審 1 條：pass 0／doubt 1／未先審 0） ⚠️

- [doubt] `jgb/E/recharge-account-mismatch-and-duplicate` 租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留在儲值餘額） —— 句序 講法：講法「虛擬帳號匯款金額不符」無法由內文回答：內文只寫重複匯款與餘額；引用的 #p914-atm-amount-mismatch（國泰／中信／永豐轉待對帳、藍新不動帳）一句都沒寫進來

回覆：

## 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） `E-payment-onboarding`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/E/newebpay-required-fields` 開通藍新智付通前，團隊要先填完哪些資料？（個人房東不能開通藍新）
- [pass] `jgb/E/newebpay-payment-methods` 藍新開通時有哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼送出時都會開啟；國外卡要另外申請）
- [pass] `jgb/E/payment-onboarding-tax-risk` 線上金流收款會不會有稅務申報風險？（屬稅捐機關與業者自身規劃，系統不判斷）

回覆：
