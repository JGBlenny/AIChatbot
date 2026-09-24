⛔ 不是現況：2026-09-15 DSP-058 改為 `canon/jgb/` 圖書館形態；本檔已掉出 hook `CANON_RE` 掃描
---
audience: property_manager
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
budget_tokens: 8000
target_user: [property_manager]
business_types: [system_provider]
---
## A 帳號與身分 {#A}
## B 團隊、人員與大房東 {#B}
## C 社區與物件 {#C}
## D 租約（含委託約子題） {#D}
### 合約到期追問可答範圍（導向續約面向） {#property_manager/D/lease-expiry-followup-scope}
- phrasings:
  - {text: "合約預告期是否已到", source: "line-doc:⑤#E", status: approved}
  - {text: "租客續約意願查詢", source: "line-doc:⑤#E", status: approved}
- sources: [draft:batch#17, kb:3799, kb:3824]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
進續約面向（不是退租收尾）：可依合約條款回答預告期是否到了、距到期幾天；租客有無續約意願 JGB 沒有欄位，要業務自己問。
本細目涵蓋的系統機制目錄：合約領域-系統合約(母共用)；合約領域-續約(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

## E 帳務（含發票、收款金流、抄表） {#E}
### 催繳草稿的生成規則（模板、語氣分級與滯納金提及） {#property_manager/E/dunning-draft-template-tone-late-fee}
- phrasings:
  - {text: "產生催繳草稿", source: "line-doc:④#-", status: approved}
- sources: [draft:batch#11, draft:batch#13]
- instance_applicability: general
催繳草稿是模板加語氣等級：系統依近一年逾期次數分三級語氣（第 1 次客氣、2–3 次提醒、4 次以上明確），回傳含佔位符的模板；金額、天數、次數等數字一律由呼叫端從 JGB 帶入填進佔位符，模板本身不得出現任何阿拉伯數字。
合約有滯納金條款時模板可提及依合約計算滯納金；合約沒寫則不提；語氣第 1 級不提滯納金。

### 催繳草稿不可一鍵發送給租客 {#property_manager/E/dunning-draft-not-auto-send}
- sources: [draft:batch#12]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
不可以；草稿一律推給業務自己複製去傳，不設計一鍵發送，所有提醒都是給業務而不是給租客。

### 逾期帳單追問可答範圍 {#property_manager/E/overdue-bill-followup-scope}
- phrasings:
  - {text: "本期滯納金金額", source: "line-doc:⑤#A", status: approved}
  - {text: "租客過去繳款紀錄", source: "line-doc:⑤#-", status: approved}
- sources: [draft:batch#14, kb:3909, kb:3913]
- reviewed: {by: owner, at: 2026-09-08}
- instance_applicability: general
可回業務權限內任一筆帳單（以帳單編號指定，或先列出可見帳單再指定）的狀態、金額、到期日與近一年逾期明細（哪幾期、逾期幾天、是否補繳），數字全部來自 JGB 帳單資料；滯納金若依合約條款推算必須標明是推算、實際以 JGB 為準。
本細目涵蓋的系統機制目錄：帳務領域-系統帳務(母共用)；帳務領域-滯納金(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

## F 修繕 {#F}
### 開修繕單基本流程與確認機制（拍照進場／文字口述） {#property_manager/F/repair-ticket-open-and-confirm}
- phrasings:
  - {text: "浴室天花板漏水報修", source: "line-doc:③#A", status: approved}
  - {text: "確認送出", source: "line-doc:③#A", status: approved}
  - {text: "廚房水槽下方漏水報修", source: "line-doc:③#F", status: approved}
- sources: [draft:batch#1]
- reviewed: {by: owner, at: 2026-09-08}
- instance_applicability: general
由拍照進場時，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；聊天以文字口述時，以口述的物件、問題描述與分類直接出確認摘要與三顆按鈕，不要求照片；兩者都只有按下「確認送出」才建單，任何未經確認的自動建單視為重大錯誤。

### 照片辨識信心不足或看不出損壞時的處理 {#property_manager/F/repair-ticket-photo-recognition-uncertain}
- phrasings:
  - {text: "牆角疑似損壞報修", source: "line-doc:③#C", status: approved}
  - {text: "牆面滲水", source: "line-doc:③#C", status: approved}
  - {text: "熱水器不出熱水", source: "line-doc:③#D", status: approved}
- sources: [draft:batch#3, draft:batch#4]
- instance_applicability: general
辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。
看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣寫進修繕單給師傅。

### 確認卡上修改辨識結果的規則 {#property_manager/F/repair-ticket-reclassify}
- phrasings:
  - {text: "報修分類改為水管", source: "line-doc:③#B", status: approved}
  - {text: "我要修改", source: "line-doc:③#B", status: approved}
- sources: [draft:batch#2]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
**確認卡尚在時**按「我要修改」只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。

### 修繕辨識與附件的照片張數限制 {#property_manager/F/repair-ticket-photo-count-limit}
- sources: [draft:batch#5]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。

### 修繕單急迫程度的判斷來源與值域 {#property_manager/F/repair-ticket-urgency-judgment}
- sources: [draft:batch#7]
- reviewed: {by: owner, at: 2026-09-08}
- instance_applicability: general
急迫與非急迫由辨識建議或業務口述；未表明時以非緊急建單，不得預設為急迫、也不為此反問；值域以 JGB 資料庫為準：2＝緊急、1＝非緊急。

### 代開單時的租約查詢身分與空屋／無租約物件開單規則 {#property_manager/F/repair-ticket-no-lease}
- phrasings:
  - {text: "客廳日光燈故障報修", source: "line-doc:③#K", status: approved}
- sources: [draft:batch#6, draft:batch#9]
- instance_applicability: general
業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。
可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。

### 報修流程中途取消的規則 {#property_manager/F/repair-ticket-mid-flow-cancel}
- phrasings:
  - {text: "取消", source: "line-doc:③#G", status: approved}
- sources: [draft:batch#10]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。

### 建單失敗時的處理與重試規則 {#property_manager/F/repair-ticket-submit-failure}
- phrasings:
  - {text: "確認送出重試", source: "line-doc:③#I", status: approved}
- sources: [draft:batch#8]
- reviewed: {by: owner, at: 2026-09-07}
- instance_applicability: general
建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。

### 確認送出後的單如何處理 {#property_manager/F/repair-ticket-after-submit}
- phrasings:
  - {text: "我要改一下描述", source: "line-doc:③#H4", status: approved}
  - {text: "廚房抽風機不會轉 同一戶", source: "line-doc:③#H4", status: approved}
- sources: [draft:batch#31]
- reviewed: {by: owner, at: 2026-09-09}
- instance_applicability: general
確認送出後，這張單不在對話裡修改：業務要改內容時，說明這張單已送出，並指到 JGB 的修繕單頁面處理。
送出後再描述同一戶的另一個問題，視為另一張新單：物件不重問，依口述描述出新的確認摘要，仍只有按「確認送出」才建單。

### 修繕進度追問可答範圍 {#property_manager/F/repair-progress-followup-scope}
- phrasings:
  - {text: "熱水器維修歷史查詢", source: "line-doc:⑤#F", status: approved}
- sources: [draft:batch#18]
- reviewed: {by: owner, at: 2026-09-08}
- instance_applicability: general
修繕進度可查：單號、物件、分類、狀態、急迫程度、建單時間、指派；開單仍走拍照確認流程。

## G 裝置（IoT） {#G}
### 電錶項目追問可答範圍（導向電表排障面向） {#property_manager/G/meter-item-followup-scope}
- phrasings:
  - {text: "電表餘額與斷電時間查詢", source: "line-doc:⑤#-", status: approved}
- sources: [draft:batch#19, kb:4021, kb:4091]
- reviewed: {by: owner, at: 2026-09-08}
- instance_applicability: general
電錶餘額不足走電表排障面向；電錶可依名稱或 id 指定，餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算，必須標明是推算。
本細目涵蓋的系統機制目錄：IoT領域-智慧設備(母共用)；IoT領域-電表排障(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

## H 幫助中心 {#H}
## I 方案與導入 {#I}
