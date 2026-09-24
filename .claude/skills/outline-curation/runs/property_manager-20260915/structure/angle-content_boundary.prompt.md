你是知識大綱的結構提議者。任務：把輸入項目切成細目並歸入固定粗目。
本次切分依據（角度 content_boundary）：內容邊界：以內容能否獨立成立、彼此不重疊為切分依據；兩段內容若互相依賴才完整，屬同一細目；若各自完整且主題不同，屬不同細目。
只依此角度切分；不評分、不排序、不判斷內容真偽；⛔ 不讀取任何檔案或工具，只依本訊息內容作答。

## 粗目（受眾 property_manager，固定，⛔ 不得增刪改）
- A：帳號與身分
- B：團隊、人員與大房東
- C：社區與物件
- D：租約（含委託約子題）
- E：帳務（含發票、收款金流、抄表）
- F：修繕
- G：裝置（IoT）
- H：幫助中心
- I：方案與導入

## 輸出定義
fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `property_manager/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。
id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old 為 null，表示無來源的新細目（首跑不應出現）。
coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。
同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。
歸位判準（跨粗目命題只能歸一處，依下列定義判）：錢怎麼算歸帳務、錢怎麼進來歸帳務底下的收款金流子題；由合約條款決定的歸租約、出現在帳單列上的歸帳務；物件本身的屬性歸社區與物件、由合約驅動的物件狀態歸租約；通知是投遞管道，歸它所通知的那個領域，⛔ 不自成細目。
講法唯一：同一句講法只掛一個細目；同一命題若答案因受眾而異，各受眾各一細目（不同 id），⛔ 不得同時存在中立細目與受眾版細目。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:kb:property_manager/A/repair-ticket-after-submit", "tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup", "tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates", "tmp:kb:property_manager/A/repair-ticket-mid-flow-cancel", "tmp:kb:property_manager/A/repair-ticket-photo-count-limit", "tmp:kb:property_manager/A/repair-ticket-photo-flow", "tmp:kb:property_manager/A/repair-ticket-reclassify", "tmp:kb:property_manager/A/repair-ticket-submit-failure", "tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo", "tmp:kb:property_manager/A/repair-ticket-urgency-judgment", "tmp:kb:property_manager/A/repair-ticket-vacant-no-lease", "tmp:kb:property_manager/B/dunning-draft-generation", "tmp:kb:property_manager/B/dunning-draft-late-fee-mention", "tmp:kb:property_manager/B/dunning-draft-not-auto-send", "tmp:kb:property_manager/C/lease-expiry-followup-scope", "tmp:kb:property_manager/C/meter-item-followup-scope", "tmp:kb:property_manager/C/overdue-bill-followup-scope", "tmp:kb:property_manager/C/urgent-repair-followup-scope"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:kb:property_manager/A/repair-ticket-after-submit", "tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup", "tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates", "tmp:kb:property_manager/A/repair-ticket-mid-flow-cancel", "tmp:kb:property_manager/A/repair-ticket-photo-count-limit", "tmp:kb:property_manager/A/repair-ticket-photo-flow", "tmp:kb:property_manager/A/repair-ticket-reclassify", "tmp:kb:property_manager/A/repair-ticket-submit-failure", "tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo", "tmp:kb:property_manager/A/repair-ticket-urgency-judgment", "tmp:kb:property_manager/A/repair-ticket-vacant-no-lease", "tmp:kb:property_manager/B/dunning-draft-generation", "tmp:kb:property_manager/B/dunning-draft-late-fee-mention", "tmp:kb:property_manager/B/dunning-draft-not-auto-send", "tmp:kb:property_manager/C/lease-expiry-followup-scope", "tmp:kb:property_manager/C/meter-item-followup-scope", "tmp:kb:property_manager/C/overdue-bill-followup-scope", "tmp:kb:property_manager/C/urgent-repair-followup-scope"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:kb:property_manager/A/repair-ticket-after-submit", "tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup", "tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates", "tmp:kb:property_manager/A/repair-ticket-mid-flow-cancel", "tmp:kb:property_manager/A/repair-ticket-photo-count-limit", "tmp:kb:property_manager/A/repair-ticket-photo-flow", "tmp:kb:property_manager/A/repair-ticket-reclassify", "tmp:kb:property_manager/A/repair-ticket-submit-failure", "tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo", "tmp:kb:property_manager/A/repair-ticket-urgency-judgment", "tmp:kb:property_manager/A/repair-ticket-vacant-no-lease", "tmp:kb:property_manager/B/dunning-draft-generation", "tmp:kb:property_manager/B/dunning-draft-late-fee-mention", "tmp:kb:property_manager/B/dunning-draft-not-auto-send", "tmp:kb:property_manager/C/lease-expiry-followup-scope", "tmp:kb:property_manager/C/meter-item-followup-scope", "tmp:kb:property_manager/C/overdue-bill-followup-scope", "tmp:kb:property_manager/C/urgent-repair-followup-scope"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map"], "additionalProperties": false}

## 輸入項目（18 筆，原序列舉）
### tmp:kb:property_manager/A/repair-ticket-after-submit
標題：確認送出後的單如何處理
內容：確認送出後，這張單不在對話裡修改：業務要改內容時，說明這張單已送出，並指到 JGB 的修繕單頁面處理。 送出後再描述同一戶的另一個問題，視為另一張新單：物件不重問，依口述描述出新的確認摘要，仍只有按「確認送出」才建單。

### tmp:kb:property_manager/A/repair-ticket-agent-identity-lease-lookup
標題：業務代開修繕單時的租約查詢身分規則
內容：業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。

### tmp:kb:property_manager/A/repair-ticket-low-confidence-candidates
標題：照片辨識信心不足時的候選類別流程
內容：辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。

### tmp:kb:property_manager/A/repair-ticket-mid-flow-cancel
標題：報修流程中途取消的規則
內容：任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。

### tmp:kb:property_manager/A/repair-ticket-photo-count-limit
標題：修繕辨識與附件的照片張數限制
內容：辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。

### tmp:kb:property_manager/A/repair-ticket-photo-flow
標題：開修繕單基本流程與確認機制（拍照進場／文字口述）
內容：由拍照進場時，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；聊天以文字口述時，以口述的物件、問題描述與分類直接出確認摘要與三顆按鈕，不要求照片；兩者都只有按下「確認送出」才建單，任何未經確認的自動建單視為重大錯誤。

### tmp:kb:property_manager/A/repair-ticket-reclassify
標題：分類辨識結果錯誤時如何修改
內容：**確認卡尚在時**按「我要修改」只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。

### tmp:kb:property_manager/A/repair-ticket-submit-failure
標題：建單失敗時的處理與重試規則
內容：建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。

### tmp:kb:property_manager/A/repair-ticket-unrecognizable-photo
標題：照片看不出損壞時的留白規則
內容：看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣寫進修繕單給師傅。

### tmp:kb:property_manager/A/repair-ticket-urgency-judgment
標題：修繕單急迫程度的判斷來源
內容：急迫與非急迫由辨識建議或業務口述；未表明時以非緊急建單，不得預設為急迫、也不為此反問；值域以 JGB 資料庫為準：2＝緊急、1＝非緊急。

### tmp:kb:property_manager/A/repair-ticket-vacant-no-lease
標題：空屋或無租約物件的開單規則
內容：可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。

### tmp:kb:property_manager/B/dunning-draft-generation
標題：催繳草稿的生成規則（模板＋語氣分級）
內容：催繳草稿是模板加語氣等級：系統依近一年逾期次數分三級語氣（第 1 次客氣、2–3 次提醒、4 次以上明確），回傳含佔位符的模板；金額、天數、次數等數字一律由呼叫端從 JGB 帶入填進佔位符，模板本身不得出現任何阿拉伯數字。

### tmp:kb:property_manager/B/dunning-draft-late-fee-mention
標題：催繳草稿是否提及滯納金的規則
內容：合約有滯納金條款時模板可提及依合約計算滯納金；合約沒寫則不提；語氣第 1 級不提滯納金。

### tmp:kb:property_manager/B/dunning-draft-not-auto-send
標題：催繳草稿不可一鍵發送給租客
內容：不可以；草稿一律推給業務自己複製去傳，不設計一鍵發送，所有提醒都是給業務而不是給租客。

### tmp:kb:property_manager/C/lease-expiry-followup-scope
標題：合約到期追問可答範圍（導向續約面向）
內容：進續約面向（不是退租收尾）：可依合約條款回答預告期是否到了、距到期幾天；租客有無續約意願 JGB 沒有欄位，要業務自己問。 本細目涵蓋的系統機制目錄：合約領域-系統合約(母共用)；合約領域-續約(子面向) 機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### tmp:kb:property_manager/C/meter-item-followup-scope
標題：電錶項目追問（導向電表排障面向）
內容：電錶餘額不足走電表排障面向；電錶可依名稱或 id 指定，餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算，必須標明是推算。 本細目涵蓋的系統機制目錄：IoT領域-智慧設備(母共用)；IoT領域-電表排障(子面向) 機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### tmp:kb:property_manager/C/overdue-bill-followup-scope
標題：逾期帳單追問可答範圍
內容：可回業務權限內任一筆帳單（以帳單編號指定，或先列出可見帳單再指定）的狀態、金額、到期日與近一年逾期明細（哪幾期、逾期幾天、是否補繳），數字全部來自 JGB 帳單資料；滯納金若依合約條款推算必須標明是推算、實際以 JGB 為準。 本細目涵蓋的系統機制目錄：帳務領域-系統帳務(母共用)；帳務領域-滯納金(子面向) 機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### tmp:kb:property_manager/C/urgent-repair-followup-scope
標題：緊急修繕追問範圍（目前無獨立面向）
內容：修繕進度可查：單號、物件、分類、狀態、急迫程度、建單時間、指派；開單仍走拍照確認流程。


請輸出角度 content_boundary 的結構提議（angle 欄填 content_boundary）。