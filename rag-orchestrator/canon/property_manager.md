---
audience: property_manager
version: 2026-09-09.1
reviewers: [owner]
language: zh-TW
budget_tokens: 8000
target_user: [property_manager]
business_types: [system_provider]
---
## A 開修繕單（線③；拍照或文字） {#A}
### 開修繕單基本流程與確認機制（拍照進場／文字口述） {#property_manager/A/repair-ticket-photo-flow}
- phrasings:
  - {text: "浴室天花板漏水報修", source: "line-doc:③#A", status: proposed}
  - {text: "確認送出", source: "line-doc:③#A", status: proposed}
  - {text: "廚房水槽下方漏水報修", source: "line-doc:③#F", status: proposed}
  - {text: "敦南", source: "line-doc:③#A", status: proposed}
- sources: [draft:batch#1]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
由拍照進場時，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；聊天以文字口述時，以口述的物件、問題描述與分類直接出確認摘要與三顆按鈕，不要求照片；兩者都只有按下「確認送出」才建單，任何未經確認的自動建單視為重大錯誤。

### 分類辨識結果錯誤時如何修改 {#property_manager/A/repair-ticket-reclassify}
- phrasings:
  - {text: "報修分類改為水管", source: "line-doc:③#B", status: proposed}
  - {text: "我要修改", source: "line-doc:③#B", status: proposed}
- sources: [draft:batch#2]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
**確認卡尚在時**按「我要修改」只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。

### 確認送出後的單如何處理 {#property_manager/A/repair-ticket-after-submit}
- phrasings:
  - {text: "我要改一下描述", source: "line-doc:③#H4", status: proposed}
  - {text: "廚房抽風機不會轉 同一戶", source: "line-doc:③#H4", status: proposed}
- sources: [draft:batch#31]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-09}
確認送出後，這張單不在對話裡修改：業務要改內容時，說明這張單已送出，並指到 JGB 的修繕單頁面處理。
送出後再描述同一戶的另一個問題，視為另一張新單：物件不重問，依口述描述出新的確認摘要，仍只有按「確認送出」才建單。

### 照片辨識信心不足時的候選類別流程 {#property_manager/A/repair-ticket-low-confidence-candidates}
- phrasings:
  - {text: "牆角疑似損壞報修", source: "line-doc:③#C", status: proposed}
  - {text: "牆面滲水", source: "line-doc:③#C", status: proposed}
- sources: [draft:batch#3]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。

### 照片看不出損壞時的留白規則 {#property_manager/A/repair-ticket-unrecognizable-photo}
- phrasings:
  - {text: "熱水器不出熱水", source: "line-doc:③#D", status: proposed}
  - {text: "物件：D02 敦南 66 號 2 樓", source: "line-doc:③#D", status: proposed}
- sources: [draft:batch#4]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣寫進修繕單給師傅。

### 修繕辨識與附件的照片張數限制 {#property_manager/A/repair-ticket-photo-count-limit}
- sources: [draft:batch#5]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。

### 業務代開修繕單時的租約查詢身分規則 {#property_manager/A/repair-ticket-agent-identity-lease-lookup}
- sources: [draft:batch#6]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。

### 修繕單急迫程度的判斷來源 {#property_manager/A/repair-ticket-urgency-judgment}
- sources: [draft:batch#7]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
急迫與非急迫由辨識建議或業務口述；未表明時以非緊急建單，不得預設為急迫、也不為此反問；值域以 JGB 資料庫為準：2＝緊急、1＝非緊急。

### 建單失敗時的處理與重試規則 {#property_manager/A/repair-ticket-submit-failure}
- phrasings:
  - {text: "確認送出重試", source: "line-doc:③#I", status: proposed}
- sources: [draft:batch#8]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。

### 空屋或無租約物件的開單規則 {#property_manager/A/repair-ticket-vacant-no-lease}
- phrasings:
  - {text: "客廳日光燈故障報修", source: "line-doc:③#K", status: proposed}
- sources: [draft:batch#9]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。

### 報修流程中途取消的規則 {#property_manager/A/repair-ticket-mid-flow-cancel}
- phrasings:
  - {text: "取消", source: "line-doc:③#G", status: proposed}
- sources: [draft:batch#10]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。

## B 催繳草稿（線④） {#B}
### 催繳草稿的生成規則（模板＋語氣分級） {#property_manager/B/dunning-draft-generation}
- phrasings:
  - {text: "產生催繳草稿", source: "line-doc:④#-", status: proposed}
- sources: [draft:batch#11]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
催繳草稿是模板加語氣等級：系統依近一年逾期次數分三級語氣（第 1 次客氣、2–3 次提醒、4 次以上明確），回傳含佔位符的模板；金額、天數、次數等數字一律由呼叫端從 JGB 帶入填進佔位符，模板本身不得出現任何阿拉伯數字。

### 催繳草稿不可一鍵發送給租客 {#property_manager/B/dunning-draft-not-auto-send}
- sources: [draft:batch#12]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
不可以；草稿一律推給業務自己複製去傳，不設計一鍵發送，所有提醒都是給業務而不是給租客。

### 催繳草稿是否提及滯納金的規則 {#property_manager/B/dunning-draft-late-fee-mention}
- sources: [draft:batch#13]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
合約有滯納金條款時模板可提及依合約計算滯納金；合約沒寫則不提；語氣第 1 級不提滯納金。

## C 今天要顧的追問（線⑤：逾期帳單／合約到期／緊急修繕／電錶） {#C}
### 逾期帳單追問可答範圍 {#property_manager/C/overdue-bill-followup-scope}
- phrasings:
  - {text: "系統脈絡:帳務領域-滯納金(子面向)", source: "question_summary:3913", status: proposed}
  - {text: "系統脈絡:帳務領域-系統帳務(母共用)", source: "question_summary:3909", status: proposed}
  - {text: "本期滯納金金額", source: "line-doc:⑤#A", status: proposed}
  - {text: "租客過去繳款紀錄", source: "line-doc:⑤#-", status: proposed}
- sources: [draft:batch#14, kb:3909, kb:3913]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
可回業務權限內任一筆帳單（以帳單編號指定，或先列出可見帳單再指定）的狀態、金額、到期日與近一年逾期明細（哪幾期、逾期幾天、是否補繳），數字全部來自 JGB 帳單資料；滯納金若依合約條款推算必須標明是推算、實際以 JGB 為準。
本細目涵蓋的系統機制目錄：帳務領域-系統帳務(母共用)；帳務領域-滯納金(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 追問的單筆會話邊界（不跨戶回答） {#property_manager/C/followup-session-single-item-boundary}
- phrasings:
  - {text: "追問其他物件的帳單", source: "line-doc:⑤#-", status: proposed}
  - {text: "追問其他租客的帳單", source: "line-doc:⑤#C", status: proposed}
- sources: [draft:batch#15]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
由清單進場（帶進場脈絡）時，每筆清單項目是獨立會話、只看被點選的那一戶（戶＝該筆所屬的物件；同一物件的帳單、合約、修繕都可追問），問到別戶時退出並提示回清單點該戶，這段對話裡之後用文字問別戶也一樣退出；聊天直接進場時沒有點選項目，同一業務權限內的帳單、合約、物件、修繕可依編號或名稱切換，不視為離題。

### 追問遇到 JGB 沒有的資料時怎麼回 {#property_manager/C/followup-missing-data-in-jgb}
- phrasings:
  - {text: "帳單入帳日期查詢", source: "line-doc:⑤#D", status: proposed}
- sources: [draft:batch#16]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
JGB 帳單只有已繳／未繳，沒有入帳日期；問到沒有的欄位就明講答不出來，不用更新時間冒充入帳日、不推算。

### 合約到期追問可答範圍（導向續約面向） {#property_manager/C/lease-expiry-followup-scope}
- phrasings:
  - {text: "對話規則:續約", source: "question_summary:3829", status: proposed}
  - {text: "系統脈絡:合約領域-系統合約(母共用)", source: "question_summary:3799", status: proposed}
  - {text: "系統脈絡:合約領域-續約(子面向)", source: "question_summary:3824", status: proposed}
  - {text: "合約預告期是否已到", source: "line-doc:⑤#E", status: proposed}
  - {text: "租客續約意願查詢", source: "line-doc:⑤#E", status: proposed}
- sources: [draft:batch#17, kb:3799, kb:3824]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
進續約面向（不是退租收尾）：可依合約條款回答預告期是否到了、距到期幾天；租客有無續約意願 JGB 沒有欄位，要業務自己問。
本細目涵蓋的系統機制目錄：合約領域-系統合約(母共用)；合約領域-續約(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 緊急修繕追問範圍（目前無獨立面向） {#property_manager/C/urgent-repair-followup-scope}
- phrasings:
  - {text: "熱水器維修歷史查詢", source: "line-doc:⑤#F", status: proposed}
- sources: [draft:batch#18]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
修繕進度可查：單號、物件、分類、狀態、急迫程度、建單時間、指派；開單仍走拍照確認流程。

### 電錶項目追問（導向電表排障面向） {#property_manager/C/meter-item-followup-scope}
- phrasings:
  - {text: "對話規則:電表排障", source: "question_summary:4089", status: proposed}
  - {text: "系統脈絡:IoT領域-智慧設備(母共用)", source: "question_summary:4021", status: proposed}
  - {text: "系統脈絡:IoT領域-電表排障(子面向)", source: "question_summary:4091", status: proposed}
  - {text: "電表餘額與斷電時間查詢", source: "line-doc:⑤#-", status: proposed}
- sources: [draft:batch#19, kb:4021, kb:4091]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
電錶餘額不足走電表排障面向；電錶可依名稱或 id 指定，餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算，必須標明是推算。
本細目涵蓋的系統機制目錄：IoT領域-智慧設備(母共用)；IoT領域-電表排障(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 追問結束與流程收尾 {#property_manager/C/followup-session-end}
- phrasings:
  - {text: "好了", source: "line-doc:⑤#G", status: proposed}
  - {text: "結束", source: "line-doc:⑤#G", status: proposed}
- sources: [draft:batch#20]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
由清單進場時，業務說結束（結束鈕送「結束」）即關閉這筆項目的會話並回清單；聊天直接進場時，業務說結束、好了、謝謝等收尾語即簡短收尾，不提結束鈕、不回清單；30 分鐘沒動作會話過期的規則兩者相同，過期後同一會話再進來要回可辨識的過期訊號並重新進場。

## D 語氣模板與禁止項 {#D}
### 回覆語氣與介面原則 {#property_manager/D/reply-tone-principles}
- sources: [draft:batch#21]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
對象是站在現場、單手用手機的代管業務或房東：回答短、先給結論、按鈕優先於自由輸入；AI 只碰分類、措辭與挑選，數字與金額一律由 JGB 帶入。

### 禁止項清單（不編造／不推算／不代決定） {#property_manager/D/prohibited-statements}
- sources: [draft:batch#22]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
不編損壞描述、不推算 JGB 沒有的數字、不用系統時間冒充業務事實、不替租客做決定、不回答別戶資料、不自動送出任何會寫入 JGB 的動作。

## E 資料邊界與什麼時候說不 {#E}
### 數字的來源規則（一律引用JGB，需推算須標明） {#property_manager/E/number-data-provenance-rule}
- sources: [draft:batch#23]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
帳單金額、逾期天數、次數、合約日期一律來自 JGB 資料；需要推算的（如依條款算滯納金）必須標明是推算並註明實際以 JGB 為準；沒有的欄位就說沒有。

### 什麼情況要拒答或退出 {#property_manager/E/when-to-decline}
- sources: [draft:batch#24]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
三種情況一律拒答或退出：問到 JGB 沒有的資料、問到目前會話範圍以外的物件或人、以及需要寫入 JGB 但使用者尚未確認的動作。

### 誰在跟系統對話與權限邊界 {#property_manager/E/identity-and-scope-boundary}
- sources: [draft:batch#25]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
呼叫方是代管業務（管數十到數百戶）或自管房東，不是租客；身分由 LINE 綁定推出，權限以角色為邊界、只能看到自己權限內的物件。

### 會話多久過期（一般規則） {#property_manager/E/session-expiry-general-rule}
- sources: [draft:batch#26]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
系統端會話 30 分鐘沒動作即清除；過期後不得把新訊息當成全新對話靜默處理，要回可辨識的過期訊號。

## F 待裁與待驗 {#F}
### 急迫程度值域與預設值衝突（待裁） {#property_manager/F/urgency-value-domain-pending}
- sources: [draft:batch#27]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
急迫程度的數值定義程式註解與舊表單相反，且缺值時預設為急迫；需以 JGB 資料庫為準裁定並改預設為非急迫或留空。

### 修繕歷史／進度面向（已建） {#property_manager/F/repair-history-facet-pending}
- sources: [draft:batch#28]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-08}
修繕進度面向已建（2026-09-08），查詢範圍見 C 的修繕進度細目；修繕歷史（已結案單的完整紀錄）仍不在範圍。

### 催繳草稿端點形式（待裁） {#property_manager/F/dunning-endpoint-form}
- sources: [draft:batch#29]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
催繳草稿要做成面向內動作或獨立同步端點，二選一待裁；不論哪種都回模板加語氣等級、不回自由文字。

### 追問回覆延遲上限（待驗） {#property_manager/F/followup-latency-budget}
- sources: [draft:batch#30]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
呼叫端逾時 30 秒、點開才看等不了；追問回覆的 p95 尚無實測數據，待量。

### 合約其他子面向與對話規則是否納入本受眾範圍，待裁 {#property_manager/F/contract-other-facets-scope-pending}
- phrasings:
  - {text: "對話規則:合約異動", source: "question_summary:4005", status: proposed}
  - {text: "對話規則:合約診斷", source: "question_summary:3801", status: proposed}
  - {text: "對話規則:建約引導", source: "question_summary:4215", status: proposed}
  - {text: "對話規則:簽署排障", source: "question_summary:3831", status: proposed}
  - {text: "對話規則:退租收尾", source: "question_summary:4202", status: proposed}
  - {text: "系統脈絡:合約領域-合約異動(子面向)", source: "question_summary:3822", status: proposed}
  - {text: "系統脈絡:合約領域-建約引導(子面向)", source: "question_summary:3825", status: proposed}
  - {text: "系統脈絡:合約領域-狀態判斷(子面向)", source: "question_summary:3800", status: proposed}
  - {text: "系統脈絡:合約領域-簽署排障(子面向)", source: "question_summary:3826", status: proposed}
  - {text: "系統脈絡:合約領域-退租收尾(子面向)", source: "question_summary:3823", status: proposed}
- sources: [kb:3800, kb:3822, kb:3823, kb:3825, kb:3826]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：合約領域-狀態判斷(子面向)；合約領域-合約異動(子面向)；合約領域-退租收尾(子面向)；合約領域-建約引導(子面向)；合約領域-簽署排障(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 帳務其他子面向與對話規則是否納入本受眾範圍，待裁 {#property_manager/F/billing-other-facets-scope-pending}
- phrasings:
  - {text: "對話規則:帳單異常", source: "question_summary:3916", status: proposed}
  - {text: "對話規則:帳單設定引導", source: "question_summary:4214", status: proposed}
  - {text: "對話規則:帳單診斷", source: "question_summary:4252", status: proposed}
  - {text: "對話規則:滯納金", source: "question_summary:3918", status: proposed}
  - {text: "對話規則:發票", source: "question_summary:3917", status: proposed}
  - {text: "對話規則:繳費金流排障", source: "question_summary:3915", status: proposed}
  - {text: "系統脈絡:帳務領域-帳單異常(子面向)", source: "question_summary:3911", status: proposed}
  - {text: "系統脈絡:帳務領域-發票(子面向)", source: "question_summary:3912", status: proposed}
- sources: [kb:3910, kb:3911, kb:3912, kb:3914]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：帳務領域-繳費金流排障(子面向)；帳務領域-帳單異常(子面向)；帳務領域-發票(子面向)；帳務領域-帳單設定引導(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 帳號領域（註冊／登入／綁定異動／團隊權限）系統知識是否納入本受眾範圍，待裁 {#property_manager/F/account-domain-scope-pending}
- phrasings:
  - {text: "對話規則:團隊成員權限", source: "question_summary:4001", status: proposed}
  - {text: "對話規則:帳號綁定異動", source: "question_summary:3984", status: proposed}
  - {text: "對話規則:登入排障", source: "question_summary:3990", status: proposed}
  - {text: "對話規則:註冊驗證排障", source: "question_summary:3983", status: proposed}
  - {text: "系統脈絡:帳號領域-帳號中心(母共用)", source: "question_summary:3952", status: proposed}
  - {text: "系統脈絡:帳號領域-登入排障(子面向)", source: "question_summary:3954", status: proposed}
- sources: [kb:3952, kb:3953, kb:3954, kb:3955, kb:3956]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：帳號領域-帳號中心(母共用)；帳號領域-註冊驗證排障(子面向)；帳號領域-登入排障(子面向)；帳號領域-帳號綁定異動(子面向)；帳號領域-團隊成員權限(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### IoT 設定引導系統知識是否納入本受眾範圍，待裁 {#property_manager/F/iot-setup-scope-pending}
- phrasings:
  - {text: "對話規則:IoT設定引導", source: "question_summary:4090", status: proposed}
- sources: [kb:4088]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：IoT領域-IoT設定引導(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 物件領域（物件管理／操作引導／現況診斷）系統知識是否納入本受眾範圍，待裁 {#property_manager/F/estate-domain-scope-pending}
- phrasings:
  - {text: "對話規則:物件操作引導", source: "question_summary:4203", status: proposed}
  - {text: "對話規則:物件現況診斷", source: "question_summary:4176", status: proposed}
  - {text: "系統脈絡:物件領域-物件管理(母共用)", source: "question_summary:4132", status: proposed}
- sources: [kb:4132, kb:4133, kb:4134]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：物件領域-物件管理(母共用)；物件領域-物件操作引導(子面向)；物件領域-物件現況診斷(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### 訂閱領域系統知識是否納入本受眾範圍，待裁 {#property_manager/F/subscription-domain-scope-pending}
- phrasings:
  - {text: "對話規則:訂閱診斷", source: "question_summary:5374", status: proposed}
- sources: [kb:5373]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-07}
本細目涵蓋的系統機制目錄：訂閱領域-條件診斷：訂閱(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

