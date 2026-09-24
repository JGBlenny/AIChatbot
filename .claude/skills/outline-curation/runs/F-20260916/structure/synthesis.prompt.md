你是知識大綱結構的合成者。輸入＝同一批項目在三個角度下各自的結構提議。任務：合成一份最終提議。
合成規則：三份提議一致處直接採用；分歧處擇一並把未採用的寫進 rejected_alternatives（alternative 一句描述、reason 一句理由）。
⛔ 不得引入三份提議都沒有的細目 id；⛔ 不得改粗目；⛔ 不讀取任何檔案或工具。

## 粗目（受眾 jgb，固定，⛔ 不得增刪改）
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
fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `jgb/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。
id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old＝該新材料的項目 id（tmp:kb:*／tmp:draft:*），⛔ 不是 null。
target_user：每一細目必填，值域 prospect／property_manager；兩者共用的細目明列兩者，不得空陣列。
coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。
同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。
歸位判準（跨粗目命題只能歸一處，依下列定義判）：錢怎麼算歸帳務、錢怎麼進來歸帳務底下的收款金流子題；由合約條款決定的歸租約、出現在帳單列上的歸帳務；物件本身的屬性歸社區與物件、由合約驅動的物件狀態歸租約；通知是投遞管道，歸它所通知的那個領域，⛔ 不自成細目。
講法唯一：同一句講法只掛一個細目；同一命題若答案因受眾而異，各受眾各一細目（不同 id），⛔ 不得同時存在中立細目與受眾版細目。
⚠️ 本次為擴充模式，**只補一架（F）**：候選項目分兩種——`tmp:canon:*`（F 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `F`，`id` 必須為 `jgb/F/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/F/repair-progress-followup-scope", "tmp:canon:jgb/F/repair-system", "tmp:canon:jgb/F/repair-ticket-after-submit", "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel", "tmp:canon:jgb/F/repair-ticket-no-lease", "tmp:canon:jgb/F/repair-ticket-open-and-confirm", "tmp:canon:jgb/F/repair-ticket-photo-count-limit", "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain", "tmp:canon:jgb/F/repair-ticket-reclassify", "tmp:canon:jgb/F/repair-ticket-submit-failure", "tmp:canon:jgb/F/repair-ticket-urgency-judgment", "tmp:kb:1558", "tmp:kb:2963", "tmp:kb:2964", "tmp:kb:2965", "tmp:kb:2966", "tmp:kb:2967", "tmp:kb:2968", "tmp:kb:2969", "tmp:kb:2970", "tmp:kb:2971", "tmp:kb:2972", "tmp:kb:2973", "tmp:kb:2974", "tmp:kb:2975", "tmp:kb:3029", "tmp:kb:3030", "tmp:kb:3145", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3203", "tmp:kb:3219", "tmp:kb:3220", "tmp:kb:3221", "tmp:kb:3222", "tmp:kb:3272", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3286", "tmp:kb:3287", "tmp:kb:3288", "tmp:kb:3289", "tmp:kb:3320", "tmp:kb:3365", "tmp:kb:3424", "tmp:kb:3425", "tmp:kb:3426", "tmp:kb:3427", "tmp:kb:3446", "tmp:kb:3488", "tmp:kb:4249", "tmp:kb:4416", "tmp:kb:4418", "tmp:kb:4420", "tmp:kb:4421", "tmp:kb:4422", "tmp:kb:4654"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/F/repair-progress-followup-scope", "tmp:canon:jgb/F/repair-system", "tmp:canon:jgb/F/repair-ticket-after-submit", "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel", "tmp:canon:jgb/F/repair-ticket-no-lease", "tmp:canon:jgb/F/repair-ticket-open-and-confirm", "tmp:canon:jgb/F/repair-ticket-photo-count-limit", "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain", "tmp:canon:jgb/F/repair-ticket-reclassify", "tmp:canon:jgb/F/repair-ticket-submit-failure", "tmp:canon:jgb/F/repair-ticket-urgency-judgment", "tmp:kb:1558", "tmp:kb:2963", "tmp:kb:2964", "tmp:kb:2965", "tmp:kb:2966", "tmp:kb:2967", "tmp:kb:2968", "tmp:kb:2969", "tmp:kb:2970", "tmp:kb:2971", "tmp:kb:2972", "tmp:kb:2973", "tmp:kb:2974", "tmp:kb:2975", "tmp:kb:3029", "tmp:kb:3030", "tmp:kb:3145", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3203", "tmp:kb:3219", "tmp:kb:3220", "tmp:kb:3221", "tmp:kb:3222", "tmp:kb:3272", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3286", "tmp:kb:3287", "tmp:kb:3288", "tmp:kb:3289", "tmp:kb:3320", "tmp:kb:3365", "tmp:kb:3424", "tmp:kb:3425", "tmp:kb:3426", "tmp:kb:3427", "tmp:kb:3446", "tmp:kb:3488", "tmp:kb:4249", "tmp:kb:4416", "tmp:kb:4418", "tmp:kb:4420", "tmp:kb:4421", "tmp:kb:4422", "tmp:kb:4654"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/F/repair-progress-followup-scope", "tmp:canon:jgb/F/repair-system", "tmp:canon:jgb/F/repair-ticket-after-submit", "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel", "tmp:canon:jgb/F/repair-ticket-no-lease", "tmp:canon:jgb/F/repair-ticket-open-and-confirm", "tmp:canon:jgb/F/repair-ticket-photo-count-limit", "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain", "tmp:canon:jgb/F/repair-ticket-reclassify", "tmp:canon:jgb/F/repair-ticket-submit-failure", "tmp:canon:jgb/F/repair-ticket-urgency-judgment", "tmp:kb:1558", "tmp:kb:2963", "tmp:kb:2964", "tmp:kb:2965", "tmp:kb:2966", "tmp:kb:2967", "tmp:kb:2968", "tmp:kb:2969", "tmp:kb:2970", "tmp:kb:2971", "tmp:kb:2972", "tmp:kb:2973", "tmp:kb:2974", "tmp:kb:2975", "tmp:kb:3029", "tmp:kb:3030", "tmp:kb:3145", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3203", "tmp:kb:3219", "tmp:kb:3220", "tmp:kb:3221", "tmp:kb:3222", "tmp:kb:3272", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3286", "tmp:kb:3287", "tmp:kb:3288", "tmp:kb:3289", "tmp:kb:3320", "tmp:kb:3365", "tmp:kb:3424", "tmp:kb:3425", "tmp:kb:3426", "tmp:kb:3427", "tmp:kb:3446", "tmp:kb:3488", "tmp:kb:4249", "tmp:kb:4416", "tmp:kb:4418", "tmp:kb:4420", "tmp:kb:4421", "tmp:kb:4422", "tmp:kb:4654"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/F/repair-progress-followup-scope", "tmp:canon:jgb/F/repair-system", "tmp:canon:jgb/F/repair-ticket-after-submit", "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel", "tmp:canon:jgb/F/repair-ticket-no-lease", "tmp:canon:jgb/F/repair-ticket-open-and-confirm", "tmp:canon:jgb/F/repair-ticket-photo-count-limit", "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain", "tmp:canon:jgb/F/repair-ticket-reclassify", "tmp:canon:jgb/F/repair-ticket-submit-failure", "tmp:canon:jgb/F/repair-ticket-urgency-judgment", "tmp:kb:1558", "tmp:kb:2963", "tmp:kb:2964", "tmp:kb:2965", "tmp:kb:2966", "tmp:kb:2967", "tmp:kb:2968", "tmp:kb:2969", "tmp:kb:2970", "tmp:kb:2971", "tmp:kb:2972", "tmp:kb:2973", "tmp:kb:2974", "tmp:kb:2975", "tmp:kb:3029", "tmp:kb:3030", "tmp:kb:3145", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3203", "tmp:kb:3219", "tmp:kb:3220", "tmp:kb:3221", "tmp:kb:3222", "tmp:kb:3272", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3286", "tmp:kb:3287", "tmp:kb:3288", "tmp:kb:3289", "tmp:kb:3320", "tmp:kb:3365", "tmp:kb:3424", "tmp:kb:3425", "tmp:kb:3426", "tmp:kb:3427", "tmp:kb:3446", "tmp:kb:3488", "tmp:kb:4249", "tmp:kb:4416", "tmp:kb:4418", "tmp:kb:4420", "tmp:kb:4421", "tmp:kb:4422", "tmp:kb:4654"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（70 筆，原序列舉）
### tmp:canon:jgb/F/repair-progress-followup-scope
標題：修繕進度追問可答範圍
內容：修繕進度可查：單號、物件、分類、狀態、急迫程度、建單時間、指派；開單仍走拍照確認流程。

### tmp:canon:jgb/F/repair-system
標題：線上報修與進度追蹤
內容：報修處理慢、追蹤不易？ 金箍棒的修繕系統讓租客線上報修、房東與管理方追蹤處理進度，把報修流程數位化。 想看實際流程可預約 demo。

### tmp:canon:jgb/F/repair-ticket-after-submit
標題：確認送出後的單如何處理
內容：確認送出後，這張單不在對話裡修改：業務要改內容時，說明這張單已送出，並指到 JGB 的修繕單頁面處理。 送出後再描述同一戶的另一個問題，視為另一張新單：物件不重問，依口述描述出新的確認摘要，仍只有按「確認送出」才建單。

### tmp:canon:jgb/F/repair-ticket-mid-flow-cancel
標題：報修流程中途取消的規則
內容：任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。

### tmp:canon:jgb/F/repair-ticket-no-lease
標題：代開單時的租約查詢身分與空屋／無租約物件開單規則
內容：業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。 可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。

### tmp:canon:jgb/F/repair-ticket-open-and-confirm
標題：開修繕單基本流程與確認機制（拍照進場／文字口述）
內容：由拍照進場時，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；聊天以文字口述時，以口述的物件、問題描述與分類直接出確認摘要與三顆按鈕，不要求照片；兩者都只有按下「確認送出」才建單，任何未經確認的自動建單視為重大錯誤。

### tmp:canon:jgb/F/repair-ticket-photo-count-limit
標題：修繕辨識與附件的照片張數限制
內容：辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。

### tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain
標題：照片辨識信心不足或看不出損壞時的處理
內容：辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。 看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣寫進修繕單給師傅。

### tmp:canon:jgb/F/repair-ticket-reclassify
標題：確認卡上修改辨識結果的規則
內容：**確認卡尚在時**按「我要修改」只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。

### tmp:canon:jgb/F/repair-ticket-submit-failure
標題：建單失敗時的處理與重試規則
內容：建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。

### tmp:canon:jgb/F/repair-ticket-urgency-judgment
標題：修繕單急迫程度的判斷來源與值域
內容：急迫與非急迫由辨識建議或業務口述；未表明時以非緊急建單，不得預設為急迫、也不為此反問；值域以 JGB 資料庫為準：2＝緊急、1＝非緊急。

### tmp:kb:1558
標題：維修進度查詢
內容：維修進度可以透過系統查詢，請提供您的物件地址，我幫您查詢。

### tmp:kb:2963
標題：房屋修繕責任
內容：房東在租約期間負責維護房屋的結構及主要設施的修繕，例如水電管路、固定設備等。若因房客使用不當造成的損壞，則由房客負責修繕費用。若您遇到任何修繕問題，請隨時聯繫您的管理師協助處理。

### tmp:kb:2964
標題：修繕責任
內容：租客在租約期間對於房屋的修繕責任包括日常維護和小型修繕，例如更換燈泡或清理排水管等。若遇到結構性問題或重大故障，則由房東或管理師負責修繕。建議您如有問題，立即聯繫您的管理師以獲取具體指導。

### tmp:kb:2965
標題：緊急修繕
內容：租客可以在出現影響居住安全或健康的情況下進行緊急修繕，例如漏水、電力故障或設備故障等。若發生此類情況，請立即聯繫您的管理師以報修，並記得保留相關證據，以保障您的權益。

### tmp:kb:2966
標題：修繕通知
內容：租客在發現房屋需要修繕時，有通知房東的義務。這樣可以確保問題得到及時處理，避免進一步損壞或影響居住品質。您可以透過管理師提交修繕申請，我們會協助您處理相關事宜。

### tmp:kb:2967
標題：漏水修繕責任
內容：如果鄰居漏水，通常由漏水方負責修繕，您可以先聯繫您的管理師，協助您進行後續處理。如果漏水影響到您的居住環境，請儘快報修，我們會協助您解決問題。

### tmp:kb:2968
標題：修繕費用負擔
內容：一般來說，房東負責房屋的結構性修繕及設施的維護，例如水管漏水或電力故障等。而租客則需負責因日常使用導致的輕微損壞，例如燈泡更換。具體的負擔劃分可能依合約有所不同，建議您確認租約內容以了解自己的權益。

### tmp:kb:2969
標題：修繕條款
內容：常見的修繕條款包括：房東負責結構性修繕，例如水管、電路和屋頂的維修；房客則需負責日常小修小補，如燈泡更換和小型設備的維護。如果發現重大損壞，房客應立即通知管理師以便及時處理。根據租約，房客有權要求房東在合理時間內完成必要的修繕工作，確保居住環境的安全與舒適。

### tmp:kb:2970
標題：公共設施維護
內容：房東對於公共設施的維護責任是確保這些設施的安全性和良好運作，包括定期檢查和必要的修繕。如果您發現公共設施有問題，建議立即通知您的管理師，以便及時處理。

### tmp:kb:2971
標題：維護責任
內容：租客對於租屋內部設施的維護責任通常限於日常使用中的小修小補，例如更換燈泡或清潔空調濾網等。主要的設備故障或損壞維修責任則由出租方或包租代管公司負責。您可以隨時向管理師報告任何需要維修的問題，讓我們幫您處理。

### tmp:kb:2972
標題：修繕請求
內容：您可以通過填寫報修申請表來提出修繕請求。請提供報修地點、問題描述、緊急程度以及方便聯繫的時間。這樣我們的管理師可以迅速處理您的請求。

### tmp:kb:2973
標題：修繕義務
內容：房東在租約中通常負責大部分的修繕義務，包括維持租屋的結構、安全與基本設施的正常運作，如水電、暖氣等。如果修繕問題是因租客使用不當而產生的，則可能由租客負責。建議您詳細閱讀租約內容，確保了解自身及房東的責任。

### tmp:kb:2974
標題：修繕責任爭議
內容：若您與房東對修繕責任有爭議，建議先查看租約中對於修繕責任的相關條款。您也可以向管理師反映此問題，管理師會協助調解並提供必要的支持。您的權益受到重視，請確保所有溝通和協調都有紀錄，以便維護您的權益。

### tmp:kb:2975
標題：修繕保固期
內容：修繕後的保固期通常為一年，但具體內容可能會依合約條款而異。建議您查看租約內關於修繕的相關條款，或聯繫您的管理師以確認詳細信息。

### tmp:kb:3029
標題：維修責任
內容：在租屋期間，房客對於小型維修和日常保養負有一定責任，例如更換燈泡、清潔空調濾網等。不過，主要的結構性維修如水管漏水或電路故障等，則應由房東或管理師負責處理。您可以隨時聯繫管理師報告需要維修的問題，確保您的居住環境安全舒適。

### tmp:kb:3030
標題：房屋維修責任
內容：房東在租屋期間負責維修房屋的主要結構及設施，例如水電系統、供暖和冷氣設備等，確保租客可以安全居住。如果發現任何需要維修的問題，請及時通知管理師，我們會協助處理維修事宜。

### tmp:kb:3145
標題：緊急維修服務
內容：我們的業者確實提供緊急維修服務，以確保您的居住安全與舒適。若您遇到任何緊急問題，請及時聯繫您的管理師報修，他們將協助您處理相關事宜。

### tmp:kb:3186
標題：公共設備維護
內容：公共設備的維護責任通常由物業管理方負責，您作為房客在使用公共設施時，若遇到問題可以隨時通知管理師進行處理。

### tmp:kb:3187
標題：租客設備維護
內容：租客在租期內應負責日常的設備保養與清潔，並及時報告任何故障或損壞。若設備因正常使用而出現的磨損，通常由房東負責維修或更換，但如因租客不當使用造成的損壞，租客需承擔維修責任。

### tmp:kb:3188
標題：公共設備損壞責任
內容：公共設備的損壞通常由房東或管理公司負責維修與維護。作為房客，您有權要求迅速處理這些問題，確保居住環境的安全與舒適。如果發現設備損壞，建議您立即聯繫管理師報修。

### tmp:kb:3189
標題：設備損壞責任
內容：如果租客設備損壞，通常需要負擔修繕費用，但這取決於損壞的原因。若是因正常使用造成的磨損，房東通常會負責修繕。建議您查看租約中的相關條款，必要時可聯繫管理師確認具體責任。

### tmp:kb:3190
標題：公共設備檢查
內容：公共設備的檢查頻率通常為每月或每季一次，具體頻率會依據物件的管理規定而有所不同。如有特殊需求或問題，您可以隨時聯繫您的管理師確認詳細資訊。

### tmp:kb:3192
標題：公共設備維護費
內容：公共設備的維護費用通常由房東負擔，這是根據租約的約定來決定的。您作為房客，應該不需要承擔這部分費用。如果有任何疑問，建議您聯繫您的管理師確認具體的責任分配。

### tmp:kb:3193
標題：設備維護費用
內容：在租期內，租客對租屋內設備的維護費用通常由房東負擔，除非租約中有特別約定。建議您查看租約內容，或洽詢您的管理師以獲取具體資訊。

### tmp:kb:3194
標題：公共設備更新責任
內容：公共設備的更新責任通常由房東負責，但具體情況可能會根據租賃合約的不同而有所變動。如果您對設備的狀況有疑問或需要協助，請聯繫您的管理師確認相關責任。

### tmp:kb:3195
標題：設備更新責任
內容：租客通常不需要負擔租客設備的更新責任，這一般由房東或管理公司負責。若設備出現問題，我們會協助處理相關的維修或更換事宜，確保您能居住在安全舒適的環境中。

### tmp:kb:3197
標題：設備維護記錄
內容：房東需要保留公共設備的維護記錄，這是確保設備正常運作及保障租客權益的重要措施。這些記錄不僅有助於房東管理物業，也能在設備出現問題時提供必要的依據，讓租客享有更好的居住環境。

### tmp:kb:3198
標題：設備使用責任
內容：租客在使用租客設備時，需確保設備的正常使用及維護，並對因不當使用造成的損壞或故障負責。如果設備出現問題，請及時通知管理師進行檢修，以免影響後續使用權益。

### tmp:kb:3199
標題：設備維護法律
內容：設備維護的法律依據主要源自《民法》及相關租賃法規，根據這些法律，房東有責任保持租賃物的良好狀態，確保其適合居住。您作為房客，有權要求房東進行必要的維修和維護，以保障您的居住安全和舒適。若遇到設備故障，您可以隨時向管理師提出報修申請，我們將協助您處理相關問題。

### tmp:kb:3200
標題：設備損壞賠償
內容：如果租客造成設備損壞，賠償標準通常依據合約內容及損壞程度來決定。一般來說，租客需負擔修復或更換的費用，但具體金額需由管理師評估後告知。如有疑問，建議您與您的管理師進一步確認。

### tmp:kb:3203
標題：維護責任範圍
內容：房東的維護責任通常包括房屋結構、暖氣系統、冷氣系統、水管、電力系統、以及其他固定設備的正常運作。如果您遇到任何設備故障，請及時聯繫您的管理師進行維修申請。

### tmp:kb:3219
標題：修繕通知義務
內容：租客在發現房屋需要修繕時，確實有通知房東的義務。這樣可以確保問題及時獲得處理，避免情況惡化。此外，租客有權要求房東在合理的時間內進行修繕，以維持居住環境的安全與舒適。

### tmp:kb:3220
標題：自行修繕
內容：租客在緊急情況下，例如水管破裂或電力故障，若不及時修繕會造成更大損失，可以自行進行修繕。但請務必在修繕後的第一時間通知房東，以便後續處理。建議保留收據，房東應負擔合理的修繕費用。

### tmp:kb:3221
標題：修繕維護責任
內容：修繕完成後，維持修繕狀態的責任通常屬於房東，但您應該確保不會因使用不當而造成損壞。如果發現任何問題，請及時通知管理師以便處理。

### tmp:kb:3222
標題：租屋設施維護責任
內容：租客對於租屋內部設施的維護責任主要是保持設施的清潔和正常使用。如果設施出現故障或損壞，通常由房東或管理公司負責修繕。建議您在發現問題時及時通知管理師，以便快速處理。

### tmp:kb:3272
標題：設備維護責任
內容：租客在租期內對租客設備的維護責任主要包括日常的保養和清潔。如設備出現故障或需修理，應及時通知管理師協助處理。租客不需負責因正常使用造成的磨損，但如因不當使用導致損壞，則需負擔修理費用。

### tmp:kb:3274
標題：公共設備維護費用
內容：公共設備的維護費用通常由房東或物業管理公司負擔，這是房客的權益之一。若有任何維護需求或問題，請隨時聯繫您的管理師進行報修。

### tmp:kb:3275
標題：租客設備責任
內容：租客在使用租客設備時，需妥善保管並合理使用設備，避免因使用不當導致的損壞。如果設備因正常使用而發生故障，管理公司會負責維修，但若是因租客不當操作造成損壞，租客可能需要承擔修復費用。建議在發現設備問題時，及時聯繫管理師以獲得協助。

### tmp:kb:3276
標題：設備維護法律依據
內容：設備維護的法律依據主要來自《民法》第 655 條，規定房東需維護租賃物的使用安全和適用性。此外，根據《租屋條例》，房客有權要求房東負責必要的維修和保養，以確保居住環境的良好狀態，保障房客的基本居住權益。

### tmp:kb:3277
標題：房東維護責任
內容：房東的維護責任範圍通常包括房屋的結構、供水、供電、供氣系統，以及其他基本設施的運作和維修。例如，水管漏水、電器故障等問題一般應由房東負責處理。如果您遇到具體的維修問題，請聯繫您的管理師進行報修。

### tmp:kb:3286
標題：修繕通知責任
內容：租客在發現房屋需要修繕時，應主動通知房東。這是租客的責任之一，以確保房屋的安全與舒適，同時也保護您的租住權益。如果您發現任何問題，請儘快聯繫管理師進行報修。

### tmp:kb:3287
標題：修繕費用分擔
內容：根據一般的租賃合約，房東負責房屋的主要結構及設施的修繕，例如水管、電路等問題；而租客則負責日常使用造成的損壞修繕。但具體情況可能因合約而異，建議您確認合約內容或聯繫您的管理師以獲取詳細資訊。

### tmp:kb:3288
標題：修繕權限
內容：如果修繕涉及到緊急情況，例如漏水或電力故障，租客可以自行進行必要的修繕而無需事先取得房東的同意。這些情況下，為了避免進一步損害，租客有權立即處理，但建議在修繕後儘快通知房東以便報銷相關費用。

### tmp:kb:3289
標題：修繕責任約定
內容：在租約中，修繕責任通常會明確規定由房東或租客負責。一般來說，房東負責結構性修繕和設備維護，而租客則負責日常的輕微維護。如果您對租約條款有疑問，建議請聯繫您的管理師確認具體內容。

### tmp:kb:3320
標題：社會住宅維修責任
內容：社會住宅的維修責任一般由管理單位負擔，主要維修和維護工作會由管理師負責處理。如果您在居住過程中遇到維修問題，可以隨時聯繫您的管理師進行報修。

### tmp:kb:3365
標題：修繕進度 修繕查詢
內容：

### tmp:kb:3424
標題：修繕流程 狀態說明
內容：修繕流程共有 6 個階段：（1）申請中：租客或房東提出修繕申請，填寫損壞原因、照片和說明；（2）安排修繕：管理者指派維修廠商，填寫廠商資訊和預估費用；（3）進行中：廠商正在進行維修工作；（4）完成修繕：維修工作完成，記錄實際費用和完修照片；（5）結單：管理者確認修繕結案，若有費用會自動產生修繕費帳單；（6）封存：修繕紀錄歸檔。每個階段變更時系統會自動通知相關人員。

### tmp:kb:3425
標題：修繕費用 結算方式
內容：修繕費用由管理者在修繕流程中記錄：安排修繕時填寫預估費用，完成修繕時更新為實際費用。結單時若修繕費用大於零，系統會自動產生一張修繕費帳單，向相關方收取費用。費用的分擔方式由房東自行決定並記錄在系統中，系統不強制特定的分擔規則。常見做法是依損壞原因判斷：自然耗損由房東負擔，人為損壞由租客負擔。

### tmp:kb:3426
標題：緊急修繕 判定處理
內容：修繕申請時可標記為「緊急」狀態，用於區分需要優先處理的維修項目（如漏水、門鎖故障、電力問題等）。緊急修繕在系統中以特殊標記顯示，方便管理者快速識別並優先安排。實際的處理優先順序和回應時間由管理公司自行規範，系統提供標記功能供管理者判斷排序。建議緊急修繕問題應在 24 小時內安排處理。

### tmp:kb:3427
標題：修繕申請 報修方式
內容：租客或房東都可以在系統中提出修繕申請。申請時需填寫：修繕類別（如水電、門窗、設備等）、損壞原因描述、現場照片。提交後系統自動通知管理者（房東或物管），管理者會安排維修廠商並回覆預估處理時間。申請人可在系統中查看修繕進度，每個階段更新時也會收到通知。

### tmp:kb:3446
標題：提出修繕 報修步驟
內容：租客提出修繕申請步驟：1. 登入系統，進入修繕功能頁面；2. 選擇要報修的物件（合約）；3. 填寫修繕資訊：選擇修繕類別（如水電、門窗、設備等）、描述損壞原因、上傳現場照片；4. 若為緊急問題（如漏水、門鎖故障），可標記為緊急修繕；5. 提交後系統自動通知房東或物管，可在修繕列表中追蹤處理進度。每個階段更新時租客都會收到通知。

### tmp:kb:3488
標題：修繕受理派工 安排廠商
內容：業者處理修繕的操作流程：1. 收到租客報修通知後，在修繕列表中查看新申請（狀態為「申請」）；2. 安排廠商：填入維修日期、時段、廠商名稱與聯繫電話，狀態更新為「安排修繕」，系統通知租客廠商資訊；3. 維修完成後更新備註：填寫完工日期、維修說明、上傳完工照片、填入結算金額；4. 確認修繕完成後將狀態推進至「結單」，系統通知租客修繕已結案；5. 最後可將修繕記錄「封存」歸檔。業者也可自行發起修繕申請（選擇物件、修繕分類、描述問題、上傳照片）。只有業者可以推進修繕狀態，租客僅能查看進度和補充備註。

### tmp:kb:4249
標題：收到租客修繕申請 怎麼受理處理
內容：收到租客的修繕申請後，業者的處理流程：1. 到修繕列表查看新申請（狀態「申請」），確認損壞描述與照片；2. 安排廠商——填入維修日期、時段、廠商名稱與聯繫電話，狀態更新為「安排修繕」，系統會自動通知租客廠商資訊；3. 維修完成後填寫完工日期、維修說明與實際費用完成結案。緊急案件可先電話聯繫租客再補系統紀錄。

### tmp:kb:4416
標題：報修 修繕 東西壞了 想報修
內容：

### tmp:kb:4418
標題：馬桶不通 排水堵塞 水管堵住
內容：

### tmp:kb:4420
標題：修繕進度 報修單 修得怎樣了 處理到哪
內容：為您查詢名下的報修單處理進度；若目前沒有任何報修單，代表尚未提出報修——需要的話跟我說「我要報修」，我可以直接協助您建單。

### tmp:kb:4421
標題：漏水 滲水 天花板漏水 水管漏水
內容：

### tmp:kb:4422
標題：冷氣壞了 電器壞了 家電故障
內容：

### tmp:kb:4654
標題：報修多個品項 都壞了分開報嗎 一張報修單
內容：同一次報修有多個品項（例如浴室三個設備）時，不必分開建立多張報修單：修繕品項選「其他」自行輸入，即可把多個品項整合寫在同一張報修單裡。


## 三份角度提議
[
 {
  "angle": "user_question_path",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/F/repair-progress-followup-scope",
    "coarse_id": "F",
    "title": "修繕進度追問可答範圍",
    "slug": "repair-progress-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/F/repair-progress-followup-scope",
     "tmp:kb:1558",
     "tmp:kb:3365",
     "tmp:kb:4420"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者問「修得怎樣了／處理到哪／查維修進度」只落這一細目；kb 1558、4420 與空內文入口 3365 都是同一提問路徑，吸收後 id 不變。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:canon:jgb/F/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前問「你們有沒有線上報修／能不能追蹤進度」的入口，維持既有細目。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-after-submit",
    "coarse_id": "F",
    "title": "確認送出後的單如何處理",
    "slug": "repair-ticket-after-submit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-after-submit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「送出後還能改嗎／同一戶再報一個算不算新單」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-mid-flow-cancel",
    "coarse_id": "F",
    "title": "報修流程中途取消的規則",
    "slug": "repair-ticket-mid-flow-cancel",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「不報了／取消」的處理只落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-no-lease",
    "coarse_id": "F",
    "title": "代開單時的租約查詢身分與空屋／無租約物件開單規則",
    "slug": "repair-ticket-no-lease",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-no-lease"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「空屋／查不到租約能不能開單」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-open-and-confirm",
    "coarse_id": "F",
    "title": "開修繕單基本流程與確認機制（拍照進場／文字口述）",
    "slug": "repair-ticket-open-and-confirm",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-open-and-confirm",
     "tmp:kb:4416",
     "tmp:kb:4418",
     "tmp:kb:4421",
     "tmp:kb:4422"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者以「我要報修／馬桶不通／漏水／冷氣壞了」開口即進入對話開單流程；4416、4418、4421、4422 為空內文入口，只當進場講法掛在此細目，不獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/F/repair-ticket-photo-count-limit",
    "coarse_id": "F",
    "title": "修繕辨識與附件的照片張數限制",
    "slug": "repair-ticket-photo-count-limit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-count-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「可以傳幾張照片」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "coarse_id": "F",
    "title": "照片辨識信心不足或看不出損壞時的處理",
    "slug": "repair-ticket-photo-recognition-uncertain",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「照片看不出來怎麼辦」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-reclassify",
    "coarse_id": "F",
    "title": "確認卡上修改辨識結果的規則",
    "slug": "repair-ticket-reclassify",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-reclassify"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「辨識錯了要改分類」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-submit-failure",
    "coarse_id": "F",
    "title": "建單失敗時的處理與重試規則",
    "slug": "repair-ticket-submit-failure",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-submit-failure"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「建單失敗／要不要再按一次」落此，維持既有。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-urgency-judgment",
    "coarse_id": "F",
    "title": "修繕單急迫程度的判斷來源與值域",
    "slug": "repair-ticket-urgency-judgment",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-urgency-judgment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問「開單時急迫程度怎麼判／預設是什麼」落此，維持既有；「緊急修繕怎麼處理」另見 jgb/F/emergency-repair-handling。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "coarse_id": "F",
    "title": "房屋修繕責任劃分（房東與租客各負責什麼、費用誰出）",
    "slug": "repair-responsibility-landlord-vs-tenant",
    "merge_of": [
     "tmp:kb:2963",
     "tmp:kb:2964",
     "tmp:kb:2968",
     "tmp:kb:2969",
     "tmp:kb:2971",
     "tmp:kb:2973",
     "tmp:kb:3029",
     "tmp:kb:3030",
     "tmp:kb:3203",
     "tmp:kb:3221",
     "tmp:kb:3222",
     "tmp:kb:3277",
     "tmp:kb:3287",
     "tmp:kb:3289"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「房東要修什麼／租客要自己處理什麼／修繕費誰出／租約通常怎麼約定」都是同一條劃分規則的不同問法，一個主題一個細目；業者會被租客問到，標 property_manager；3221 修繕後維持責任併入同一規則。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/common-equipment-maintenance-responsibility",
    "coarse_id": "F",
    "title": "公共設備的維護、損壞、更新、費用與檢查紀錄責任",
    "slug": "common-equipment-maintenance-responsibility",
    "merge_of": [
     "tmp:kb:2970",
     "tmp:kb:3186",
     "tmp:kb:3188",
     "tmp:kb:3190",
     "tmp:kb:3192",
     "tmp:kb:3194",
     "tmp:kb:3197",
     "tmp:kb:3274"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "以「公共設備」為主詞的提問（誰維護／壞了誰修／誰出錢／多久檢查／要不要留紀錄）答案同源，合為一細目；與房屋修繕責任的差別在主詞是公共設備而非房屋本體。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-equipment-maintenance-responsibility",
    "coarse_id": "F",
    "title": "租客設備的維護、損壞賠償、更新與費用責任",
    "slug": "tenant-equipment-maintenance-responsibility",
    "merge_of": [
     "tmp:kb:3187",
     "tmp:kb:3189",
     "tmp:kb:3193",
     "tmp:kb:3195",
     "tmp:kb:3198",
     "tmp:kb:3200",
     "tmp:kb:3272",
     "tmp:kb:3275"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "以「租客設備」為主詞的提問（日常保養誰做／弄壞了要不要賠、賠多少／更新誰負責／維護費誰出）合為一細目，與公共設備分開因答案依設備歸屬而異。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-repair-notification-duty",
    "coarse_id": "F",
    "title": "租客發現需修繕時的通知義務",
    "slug": "tenant-repair-notification-duty",
    "merge_of": [
     "tmp:kb:2966",
     "tmp:kb:3219",
     "tmp:kb:3286"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「租客有沒有義務通知房東」三筆同題，一個細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-self-repair-in-emergency",
    "coarse_id": "F",
    "title": "緊急情況下租客自行修繕與費用報銷",
    "slug": "tenant-self-repair-in-emergency",
    "merge_of": [
     "tmp:kb:3220",
     "tmp:kb:3288"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「租客能不能自己先修／修完能不能報銷」是獨立於責任劃分的一問，兩筆合一。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/emergency-repair-handling",
    "coarse_id": "F",
    "title": "緊急修繕的判定、標記與處理時效",
    "slug": "emergency-repair-handling",
    "merge_of": [
     "tmp:kb:2965",
     "tmp:kb:3145",
     "tmp:kb:3426"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「什麼算緊急／有沒有緊急維修服務／緊急件怎麼標記與優先處理」同一提問路徑；售前與業者問法不同但答案同一機制，故兩受眾共用；開單時急迫值域另見 jgb/F/repair-ticket-urgency-judgment。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/neighbor-leak-responsibility",
    "coarse_id": "F",
    "title": "鄰居漏水的修繕責任與處理",
    "slug": "neighbor-leak-responsibility",
    "merge_of": [
     "tmp:kb:2967"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「鄰居漏水誰負責」答案是漏水方負責，與一般房東／租客劃分不同，獨立一問；「漏水我要報修」的入口則掛開單細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-responsibility-dispute",
    "coarse_id": "F",
    "title": "修繕責任有爭議時的處理",
    "slug": "repair-responsibility-dispute",
    "merge_of": [
     "tmp:kb:2974"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「跟房東對修繕責任有爭議怎麼辦」是處理程序題，與劃分規則本身分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-warranty-period",
    "coarse_id": "F",
    "title": "修繕後的保固期",
    "slug": "repair-warranty-period",
    "merge_of": [
     "tmp:kb:2975"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「修好了保固多久」獨立可答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/social-housing-repair-responsibility",
    "coarse_id": "F",
    "title": "社會住宅的維修責任",
    "slug": "social-housing-repair-responsibility",
    "merge_of": [
     "tmp:kb:3320"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「社宅維修誰負責」答案為管理單位，與一般租屋劃分不同，獨立一問。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-flow-stages",
    "coarse_id": "F",
    "title": "修繕流程六階段與各狀態意義",
    "slug": "repair-flow-stages",
    "merge_of": [
     "tmp:kb:3424"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「修繕流程有哪些階段／狀態是什麼意思」售前與業者都會問且答案相同；與售前入口 repair-system 分層（入口 vs 階段說明）。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-fee-recording-and-billing",
    "coarse_id": "F",
    "title": "修繕費用的記錄、分擔與結單自動產生帳單",
    "slug": "repair-fee-recording-and-billing",
    "merge_of": [
     "tmp:kb:3425"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「修繕費用怎麼結算／怎麼分擔」在修繕流程內提問，費用記錄是安排修繕與結單的步驟；帳單本身的收款歸 E，此處只答修繕流程如何記錄與觸發帳單。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-request-how-to-submit",
    "coarse_id": "F",
    "title": "在系統提出修繕申請的步驟與需填資料",
    "slug": "repair-request-how-to-submit",
    "merge_of": [
     "tmp:kb:2972",
     "tmp:kb:3427",
     "tmp:kb:3446"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「報修要填什麼／在系統怎麼報修」三筆同題；與對話開單細目分層（系統頁面步驟 vs 對話確認機制）。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-dispatch-and-close-by-manager",
    "coarse_id": "F",
    "title": "業者受理報修、安排廠商到結單封存的操作",
    "slug": "repair-dispatch-and-close-by-manager",
    "merge_of": [
     "tmp:kb:3488",
     "tmp:kb:4249"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「收到租客報修怎麼受理／怎麼派工／怎麼結單」是業者端操作題，兩筆合一。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-multiple-items-one-ticket",
    "coarse_id": "F",
    "title": "多個品項是否分開報修",
    "slug": "repair-multiple-items-one-ticket",
    "merge_of": [
     "tmp:kb:4654"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「好幾樣壞了要分開報嗎」獨立可答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/F/repair-progress-followup-scope",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:1558",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3365",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4420",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/F/repair-system",
    "new": "jgb/F/repair-system",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-after-submit",
    "new": "jgb/F/repair-ticket-after-submit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel",
    "new": "jgb/F/repair-ticket-mid-flow-cancel",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-no-lease",
    "new": "jgb/F/repair-ticket-no-lease",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-open-and-confirm",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4416",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4418",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4421",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4422",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-count-limit",
    "new": "jgb/F/repair-ticket-photo-count-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain",
    "new": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-reclassify",
    "new": "jgb/F/repair-ticket-reclassify",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-submit-failure",
    "new": "jgb/F/repair-ticket-submit-failure",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-urgency-judgment",
    "new": "jgb/F/repair-ticket-urgency-judgment",
    "op": "keep"
   },
   {
    "old": "tmp:kb:2963",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2964",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2968",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2969",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2971",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2973",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3029",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3030",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3203",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3221",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3222",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3277",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3287",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3289",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2970",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3186",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3188",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3190",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3192",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3194",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3197",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3274",
    "new": "jgb/F/common-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3187",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3189",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3193",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3195",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3198",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3200",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3272",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3275",
    "new": "jgb/F/tenant-equipment-maintenance-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2966",
    "new": "jgb/F/tenant-repair-notification-duty",
    "op": "new"
   },
   {
    "old": "tmp:kb:3219",
    "new": "jgb/F/tenant-repair-notification-duty",
    "op": "new"
   },
   {
    "old": "tmp:kb:3286",
    "new": "jgb/F/tenant-repair-notification-duty",
    "op": "new"
   },
   {
    "old": "tmp:kb:3220",
    "new": "jgb/F/tenant-self-repair-in-emergency",
    "op": "new"
   },
   {
    "old": "tmp:kb:3288",
    "new": "jgb/F/tenant-self-repair-in-emergency",
    "op": "new"
   },
   {
    "old": "tmp:kb:2965",
    "new": "jgb/F/emergency-repair-handling",
    "op": "new"
   },
   {
    "old": "tmp:kb:3145",
    "new": "jgb/F/emergency-repair-handling",
    "op": "new"
   },
   {
    "old": "tmp:kb:3426",
    "new": "jgb/F/emergency-repair-handling",
    "op": "new"
   },
   {
    "old": "tmp:kb:2967",
    "new": "jgb/F/neighbor-leak-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2974",
    "new": "jgb/F/repair-responsibility-dispute",
    "op": "new"
   },
   {
    "old": "tmp:kb:2975",
    "new": "jgb/F/repair-warranty-period",
    "op": "new"
   },
   {
    "old": "tmp:kb:3320",
    "new": "jgb/F/social-housing-repair-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3424",
    "new": "jgb/F/repair-flow-stages",
    "op": "new"
   },
   {
    "old": "tmp:kb:3425",
    "new": "jgb/F/repair-fee-recording-and-billing",
    "op": "new"
   },
   {
    "old": "tmp:kb:2972",
    "new": "jgb/F/repair-request-how-to-submit",
    "op": "new"
   },
   {
    "old": "tmp:kb:3427",
    "new": "jgb/F/repair-request-how-to-submit",
    "op": "new"
   },
   {
    "old": "tmp:kb:3446",
    "new": "jgb/F/repair-request-how-to-submit",
    "op": "new"
   },
   {
    "old": "tmp:kb:3488",
    "new": "jgb/F/repair-dispatch-and-close-by-manager",
    "op": "new"
   },
   {
    "old": "tmp:kb:4249",
    "new": "jgb/F/repair-dispatch-and-close-by-manager",
    "op": "new"
   },
   {
    "old": "tmp:kb:4654",
    "new": "jgb/F/repair-multiple-items-one-ticket",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "D",
    "why": "純法律條文（民法／租賃法規）依據，屬租約層而非修繕操作。"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "D",
    "why": "純法律條文（民法第 655 條、租屋條例）依據，屬租約層而非修繕操作。"
   }
  ]
 },
 {
  "angle": "content_boundary",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/F/repair-progress-followup-scope",
    "coarse_id": "F",
    "title": "修繕進度追問可答範圍",
    "slug": "repair-progress-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/F/repair-progress-followup-scope",
     "tmp:kb:1558",
     "tmp:kb:3365",
     "tmp:kb:4420"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆新材料都是「查修繕進度」的入口與答法（提供物件、查名下報修單、沒有單就轉報修），與既有可答範圍互相依賴才完整，吸收為同一細目；3365 空內文只作入口。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:canon:jgb/F/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前功能介紹，內容自成一體，無新材料需吸收。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-after-submit",
    "coarse_id": "F",
    "title": "確認送出後的單如何處理",
    "slug": "repair-ticket-after-submit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-after-submit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "送出後修改與同戶另一問題的規則自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-mid-flow-cancel",
    "coarse_id": "F",
    "title": "報修流程中途取消的規則",
    "slug": "repair-ticket-mid-flow-cancel",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "取消規則自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-no-lease",
    "coarse_id": "F",
    "title": "代開單時的租約查詢身分與空屋／無租約物件開單規則",
    "slug": "repair-ticket-no-lease",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-no-lease"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "無租約開單規則自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-open-and-confirm",
    "coarse_id": "F",
    "title": "開修繕單基本流程與確認機制（拍照進場／文字口述）",
    "slug": "repair-ticket-open-and-confirm",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-open-and-confirm",
     "tmp:kb:4416",
     "tmp:kb:4418",
     "tmp:kb:4421",
     "tmp:kb:4422"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "四筆空內文 kb 列（想報修／馬桶不通／漏水／冷氣壞）都是「東西壞了要開單」的進場講法，只作本細目入口，不獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/F/repair-ticket-photo-count-limit",
    "coarse_id": "F",
    "title": "修繕辨識與附件的照片張數限制",
    "slug": "repair-ticket-photo-count-limit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-count-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "張數限制自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "coarse_id": "F",
    "title": "照片辨識信心不足或看不出損壞時的處理",
    "slug": "repair-ticket-photo-recognition-uncertain",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "辨識失敗處理自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-reclassify",
    "coarse_id": "F",
    "title": "確認卡上修改辨識結果的規則",
    "slug": "repair-ticket-reclassify",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-reclassify"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "修改辨識結果規則自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-submit-failure",
    "coarse_id": "F",
    "title": "建單失敗時的處理與重試規則",
    "slug": "repair-ticket-submit-failure",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-submit-failure"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "失敗重試規則自成一體。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-urgency-judgment",
    "coarse_id": "F",
    "title": "修繕單急迫程度的判斷來源與值域",
    "slug": "repair-ticket-urgency-judgment",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-urgency-judgment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對話建單時急迫值的來源與值域，是建單規則層；系統緊急標記的意義另立細目（emergency-repair-flag-and-handling）。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "coarse_id": "F",
    "title": "房屋與設施修繕責任劃分（房東／租客）",
    "slug": "repair-responsibility-landlord-vs-tenant",
    "merge_of": [
     "tmp:kb:2963",
     "tmp:kb:2964",
     "tmp:kb:2968",
     "tmp:kb:2969",
     "tmp:kb:2971",
     "tmp:kb:2973",
     "tmp:kb:3029",
     "tmp:kb:3030",
     "tmp:kb:3203",
     "tmp:kb:3221",
     "tmp:kb:3222",
     "tmp:kb:3277",
     "tmp:kb:3287",
     "tmp:kb:3289"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "14 筆講同一命題：結構與固定設施歸房東、日常小修與使用不當歸租客、以租約為準；各筆單獨皆不完整（只講其中一方或一種情形），合起來才是一個可獨立回答的主題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-equipment-responsibility",
    "coarse_id": "F",
    "title": "租客設備的使用、損壞賠償與更新責任",
    "slug": "tenant-equipment-responsibility",
    "merge_of": [
     "tmp:kb:3187",
     "tmp:kb:3189",
     "tmp:kb:3193",
     "tmp:kb:3195",
     "tmp:kb:3198",
     "tmp:kb:3200",
     "tmp:kb:3272",
     "tmp:kb:3275"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "以「租客設備」為主體：使用義務、正常磨損 vs 不當使用的損壞歸屬、賠償標準、維護費用與更新責任互相依賴才完整；與房屋結構層級的責任劃分主題不同，故分立。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/common-facility-maintenance",
    "coarse_id": "F",
    "title": "公共設備的維護、費用、更新、檢查與紀錄責任",
    "slug": "common-facility-maintenance",
    "merge_of": [
     "tmp:kb:2970",
     "tmp:kb:3186",
     "tmp:kb:3188",
     "tmp:kb:3190",
     "tmp:kb:3192",
     "tmp:kb:3194",
     "tmp:kb:3197",
     "tmp:kb:3274"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "以「公共設備」為主體：維護／損壞／費用／更新責任、檢查頻率、維護紀錄皆環繞同一主體，各筆單看不完整，合為一題；主體與租客設備、房屋結構不同，故分立。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-repair-notice-obligation",
    "coarse_id": "F",
    "title": "租客發現需修繕時的通知義務",
    "slug": "tenant-repair-notice-obligation",
    "merge_of": [
     "tmp:kb:2966",
     "tmp:kb:3219",
     "tmp:kb:3286"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆同一命題（租客有通知義務、可要求合理期限內修繕），內容自成一體，與責任劃分是不同主題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/tenant-emergency-self-repair",
    "coarse_id": "F",
    "title": "緊急情況下租客自行修繕的條件與事後處理",
    "slug": "tenant-emergency-self-repair",
    "merge_of": [
     "tmp:kb:2965",
     "tmp:kb:3220",
     "tmp:kb:3288"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆同一命題（緊急可先自行修繕、事後通知、保留收據請款），自成一體；與系統緊急標記是不同層。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/emergency-repair-flag-and-handling",
    "coarse_id": "F",
    "title": "緊急修繕的標記、優先處理與回應時效",
    "slug": "emergency-repair-flag-and-handling",
    "merge_of": [
     "tmp:kb:3145",
     "tmp:kb:3426"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者提供緊急維修服務與系統緊急標記的意義／處理順序互相依賴才完整；此為系統與服務面，與對話建單急迫值來源（urgency-judgment）及租客自行修繕分立。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/neighbor-leak-responsibility",
    "coarse_id": "F",
    "title": "鄰居漏水的修繕責任與處理",
    "slug": "neighbor-leak-responsibility",
    "merge_of": [
     "tmp:kb:2967"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "第三方（鄰居）漏水歸漏水方負責，主體與房東／租客責任劃分不同，自成一題；漏水入口講法（4421）屬開單流程不屬此。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-responsibility-dispute",
    "coarse_id": "F",
    "title": "修繕責任有爭議時的處理",
    "slug": "repair-responsibility-dispute",
    "merge_of": [
     "tmp:kb:2974"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "爭議處理（查租約、管理師調解、留紀錄）自成一體，不依賴責任劃分內容即可回答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-warranty-period",
    "coarse_id": "F",
    "title": "修繕後保固期",
    "slug": "repair-warranty-period",
    "merge_of": [
     "tmp:kb:2975"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "保固期是修繕完成後的獨立命題，自成一題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/social-housing-repair-responsibility",
    "coarse_id": "F",
    "title": "社會住宅的維修責任",
    "slug": "social-housing-repair-responsibility",
    "merge_of": [
     "tmp:kb:3320"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社會住宅由管理單位負責維修，主體與一般房東／租客劃分不同，自成一題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-flow-stages",
    "coarse_id": "F",
    "title": "修繕流程六個狀態階段說明",
    "slug": "repair-flow-stages",
    "merge_of": [
     "tmp:kb:3424"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "狀態模型（申請中→安排→進行中→完成→結單→封存）是獨立可答的定義題；業者的操作步驟另立細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-cost-recording-and-settlement",
    "coarse_id": "F",
    "title": "修繕費用的記錄、結單自動產生帳單與分擔方式",
    "slug": "repair-cost-recording-and-settlement",
    "merge_of": [
     "tmp:kb:3425"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "修繕模組內的預估／實際費用欄位與結單自動開帳單、分擔由房東決定，是修繕流程的一環自成一題；帳單本身的帳務規則另見 E。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-request-submission-in-system",
    "coarse_id": "F",
    "title": "在系統中提出修繕申請的方式與步驟（租客／房東）",
    "slug": "repair-request-submission-in-system",
    "merge_of": [
     "tmp:kb:2972",
     "tmp:kb:3427",
     "tmp:kb:3446"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆都是系統 UI 提出修繕申請要填什麼、步驟與提交後通知，互相補足才完整；與對話式開單（open-and-confirm）是不同介面層，分立。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-intake-and-dispatch",
    "coarse_id": "F",
    "title": "業者受理修繕申請、安排廠商與結案操作",
    "slug": "repair-intake-and-dispatch",
    "merge_of": [
     "tmp:kb:3488",
     "tmp:kb:4249"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "兩筆都是業者端受理→派工→完工→結單→封存的操作步驟，內容重疊互補，合為一題；與狀態定義題分立。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-multiple-items-one-ticket",
    "coarse_id": "F",
    "title": "多個品項合併在一張報修單",
    "slug": "repair-multiple-items-one-ticket",
    "merge_of": [
     "tmp:kb:4654"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "多品項用「其他」合寫一張單是獨立的操作問答，不依賴其他內容即可回答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/F/repair-progress-followup-scope",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:1558",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3365",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4420",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/F/repair-system",
    "new": "jgb/F/repair-system",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-after-submit",
    "new": "jgb/F/repair-ticket-after-submit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel",
    "new": "jgb/F/repair-ticket-mid-flow-cancel",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-no-lease",
    "new": "jgb/F/repair-ticket-no-lease",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-open-and-confirm",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4416",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4418",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4421",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4422",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-count-limit",
    "new": "jgb/F/repair-ticket-photo-count-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain",
    "new": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-reclassify",
    "new": "jgb/F/repair-ticket-reclassify",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-submit-failure",
    "new": "jgb/F/repair-ticket-submit-failure",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-urgency-judgment",
    "new": "jgb/F/repair-ticket-urgency-judgment",
    "op": "keep"
   },
   {
    "old": "tmp:kb:2963",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2964",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2968",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2969",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2971",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2973",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3029",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3030",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3203",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3221",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3222",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3277",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3287",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3289",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3187",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3189",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3193",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3195",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3198",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3200",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3272",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3275",
    "new": "jgb/F/tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2970",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3186",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3188",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3190",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3192",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3194",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3197",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3274",
    "new": "jgb/F/common-facility-maintenance",
    "op": "new"
   },
   {
    "old": "tmp:kb:2966",
    "new": "jgb/F/tenant-repair-notice-obligation",
    "op": "new"
   },
   {
    "old": "tmp:kb:3219",
    "new": "jgb/F/tenant-repair-notice-obligation",
    "op": "new"
   },
   {
    "old": "tmp:kb:3286",
    "new": "jgb/F/tenant-repair-notice-obligation",
    "op": "new"
   },
   {
    "old": "tmp:kb:2965",
    "new": "jgb/F/tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:3220",
    "new": "jgb/F/tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:3288",
    "new": "jgb/F/tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:3145",
    "new": "jgb/F/emergency-repair-flag-and-handling",
    "op": "new"
   },
   {
    "old": "tmp:kb:3426",
    "new": "jgb/F/emergency-repair-flag-and-handling",
    "op": "new"
   },
   {
    "old": "tmp:kb:2967",
    "new": "jgb/F/neighbor-leak-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2974",
    "new": "jgb/F/repair-responsibility-dispute",
    "op": "new"
   },
   {
    "old": "tmp:kb:2975",
    "new": "jgb/F/repair-warranty-period",
    "op": "new"
   },
   {
    "old": "tmp:kb:3320",
    "new": "jgb/F/social-housing-repair-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3424",
    "new": "jgb/F/repair-flow-stages",
    "op": "new"
   },
   {
    "old": "tmp:kb:3425",
    "new": "jgb/F/repair-cost-recording-and-settlement",
    "op": "new"
   },
   {
    "old": "tmp:kb:2972",
    "new": "jgb/F/repair-request-submission-in-system",
    "op": "new"
   },
   {
    "old": "tmp:kb:3427",
    "new": "jgb/F/repair-request-submission-in-system",
    "op": "new"
   },
   {
    "old": "tmp:kb:3446",
    "new": "jgb/F/repair-request-submission-in-system",
    "op": "new"
   },
   {
    "old": "tmp:kb:3488",
    "new": "jgb/F/repair-intake-and-dispatch",
    "op": "new"
   },
   {
    "old": "tmp:kb:4249",
    "new": "jgb/F/repair-intake-and-dispatch",
    "op": "new"
   },
   {
    "old": "tmp:kb:4654",
    "new": "jgb/F/repair-multiple-items-one-ticket",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "D",
    "why": "純法律條文（民法與租賃法規對房東維護義務的規範），屬租約／法規層而非修繕操作或責任劃分講法。"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "D",
    "why": "純法律條文（民法第 655 條、租屋條例），屬租約／法規層而非修繕操作或責任劃分講法。"
   }
  ]
 },
 {
  "angle": "audience_level",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/F/repair-system",
    "coarse_id": "F",
    "title": "線上報修與進度追蹤",
    "slug": "repair-system",
    "merge_of": [
     "tmp:canon:jgb/F/repair-system"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前能力層級：向潛在客戶說明修繕系統能做什麼，屬 prospect 的能力層；操作與權益層另見 property_manager 細目。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-open-and-confirm",
    "coarse_id": "F",
    "title": "開修繕單基本流程與確認機制（拍照進場／文字口述）",
    "slug": "repair-ticket-open-and-confirm",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-open-and-confirm"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-after-submit",
    "coarse_id": "F",
    "title": "確認送出後的單如何處理",
    "slug": "repair-ticket-after-submit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-after-submit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-mid-flow-cancel",
    "coarse_id": "F",
    "title": "報修流程中途取消的規則",
    "slug": "repair-ticket-mid-flow-cancel",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-no-lease",
    "coarse_id": "F",
    "title": "代開單時的租約查詢身分與空屋／無租約物件開單規則",
    "slug": "repair-ticket-no-lease",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-no-lease"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-photo-count-limit",
    "coarse_id": "F",
    "title": "修繕辨識與附件的照片張數限制",
    "slug": "repair-ticket-photo-count-limit",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-count-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "coarse_id": "F",
    "title": "照片辨識信心不足或看不出損壞時的處理",
    "slug": "repair-ticket-photo-recognition-uncertain",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-reclassify",
    "coarse_id": "F",
    "title": "確認卡上修改辨識結果的規則",
    "slug": "repair-ticket-reclassify",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-reclassify"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-submit-failure",
    "coarse_id": "F",
    "title": "建單失敗時的處理與重試規則",
    "slug": "repair-ticket-submit-failure",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-submit-failure"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-ticket-urgency-judgment",
    "coarse_id": "F",
    "title": "修繕單急迫程度的判斷來源與值域",
    "slug": "repair-ticket-urgency-judgment",
    "merge_of": [
     "tmp:canon:jgb/F/repair-ticket-urgency-judgment"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：對話代開修繕單的既有規則，受眾為業者（業務）；本次無新材料涉及此命題，原樣保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/F/repair-progress-followup-scope",
    "coarse_id": "F",
    "title": "修繕進度追問可答範圍與查詢方式",
    "slug": "repair-progress-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/F/repair-progress-followup-scope",
     "tmp:kb:1558",
     "tmp:kb:3365",
     "tmp:kb:4420"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "同一主題（查修繕進度）同一受眾同一層級（操作）：既有細目定可答欄位，新材料補查詢入口與無單時導向報修的講法；3365 為空內文列，只作入口吸收，不獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/F/repair-flow-stages",
    "coarse_id": "F",
    "title": "修繕流程六階段與狀態說明",
    "slug": "repair-flow-stages",
    "merge_of": [
     "tmp:kb:3424"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層級：六階段狀態定義對潛在客戶（了解系統能力）與業者（判讀狀態）答案相同，故共用一細目；各階段的操作步驟另見 repair-dispatch-and-close。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-cost-record-and-bill",
    "coarse_id": "F",
    "title": "修繕費用的記錄與結單自動產生修繕費帳單",
    "slug": "repair-cost-record-and-bill",
    "merge_of": [
     "tmp:kb:3425"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：預估／實際費用在修繕流程中如何記錄、結單時何時自動產生帳單、分擔由房東自行決定；帳單本身的計費與收款另見 E 架，誰負擔的權益層另見 repair-responsibility-landlord-vs-tenant。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-emergency-flag-and-priority",
    "coarse_id": "F",
    "title": "緊急修繕的標記、優先處理與回應時間",
    "slug": "repair-emergency-flag-and-priority",
    "merge_of": [
     "tmp:kb:3426",
     "tmp:kb:3145"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力／操作層級：系統提供緊急標記供業者優先排序、回應時間由業者自訂，對潛在客戶與業者答案相同；租客可否自行緊急修繕屬權益層，另見 repair-tenant-emergency-self-repair。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-request-submit-steps",
    "coarse_id": "F",
    "title": "租客／房東在系統提出修繕申請的方式與步驟",
    "slug": "repair-request-submit-steps",
    "merge_of": [
     "tmp:kb:3427",
     "tmp:kb:3446",
     "tmp:kb:2972",
     "tmp:kb:4416",
     "tmp:kb:4418",
     "tmp:kb:4421",
     "tmp:kb:4422"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層級：報修需填的欄位（類別、原因描述、照片、緊急程度）與提交後的通知與追蹤；4416／4418／4421／4422 為空內文症狀入口列，只作入口吸收；售前的能力層級另見 repair-system。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-request-multiple-items",
    "coarse_id": "F",
    "title": "同一次報修多個品項是否需分開建單",
    "slug": "repair-request-multiple-items",
    "merge_of": [
     "tmp:kb:4654"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層級：多品項可用「其他」自行輸入整合於同一張報修單，屬獨立可答的操作規則，與一般報修步驟分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-dispatch-and-close",
    "coarse_id": "F",
    "title": "業者受理修繕申請、安排廠商、完工登錄與結單封存",
    "slug": "repair-dispatch-and-close",
    "merge_of": [
     "tmp:kb:3488",
     "tmp:kb:4249"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者操作層級：從申請到結單封存的逐步操作、各步系統通知租客、只有業者能推進狀態；階段定義另見 repair-flow-stages。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "coarse_id": "F",
    "title": "房東與租客的修繕責任劃分（結構設施 vs 日常小修與不當使用）",
    "slug": "repair-responsibility-landlord-vs-tenant",
    "merge_of": [
     "tmp:kb:2963",
     "tmp:kb:2964",
     "tmp:kb:2968",
     "tmp:kb:2969",
     "tmp:kb:2971",
     "tmp:kb:2973",
     "tmp:kb:3029",
     "tmp:kb:3030",
     "tmp:kb:3203",
     "tmp:kb:3222",
     "tmp:kb:3277",
     "tmp:kb:3287",
     "tmp:kb:3289",
     "tmp:kb:3221",
     "tmp:kb:3320"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：業者會被租客問到的責任劃分通則（房東負責結構與主要設施、租客負責日常小修與不當使用損壞、依租約為準），十餘列近重複講法合為一細目；3320 為社會住宅由管理單位負擔的變體，3221 為修繕後維持狀態責任，同一命題併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-tenant-equipment-responsibility",
    "coarse_id": "F",
    "title": "租客設備的使用、維護、更新與損壞賠償責任",
    "slug": "repair-tenant-equipment-responsibility",
    "merge_of": [
     "tmp:kb:3187",
     "tmp:kb:3189",
     "tmp:kb:3193",
     "tmp:kb:3195",
     "tmp:kb:3198",
     "tmp:kb:3200",
     "tmp:kb:3272",
     "tmp:kb:3275"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：以「租客設備」為對象的責任問題（日常保養、正常磨損由房東、不當使用由租客賠償、更新與維護費由房東），與總則分開避免混淆對象；賠償金額由管理師評估屬責任歸屬不屬計費。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-common-facility-responsibility",
    "coarse_id": "F",
    "title": "公共設備的維護、檢查、費用、更新與紀錄責任",
    "slug": "repair-common-facility-responsibility",
    "merge_of": [
     "tmp:kb:2970",
     "tmp:kb:3186",
     "tmp:kb:3188",
     "tmp:kb:3190",
     "tmp:kb:3192",
     "tmp:kb:3194",
     "tmp:kb:3197",
     "tmp:kb:3274"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：以公共設備為對象的責任問題（維護／更新／費用由房東或管理方、檢查頻率依管理規定、需保留維護紀錄），與租客設備及總則分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-notify-duty-and-timely-repair-right",
    "coarse_id": "F",
    "title": "租客的修繕通知義務與要求合理期限修繕的權利",
    "slug": "repair-notify-duty-and-timely-repair-right",
    "merge_of": [
     "tmp:kb:2966",
     "tmp:kb:3219",
     "tmp:kb:3286"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：租客發現需修繕時有通知義務、並有權要求房東於合理時間內修繕；此為租客的法定義務與權利命題，非系統通知投遞管道，故獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-tenant-emergency-self-repair",
    "coarse_id": "F",
    "title": "租客緊急情況自行修繕與費用報銷",
    "slug": "repair-tenant-emergency-self-repair",
    "merge_of": [
     "tmp:kb:2965",
     "tmp:kb:3220",
     "tmp:kb:3288"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：緊急情況（漏水、電力故障）租客可先行修繕、事後通知並保留收據由房東負擔合理費用；與系統的緊急標記（操作層）分屬不同層級，以另見處理。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-responsibility-dispute",
    "coarse_id": "F",
    "title": "修繕責任爭議的處理方式",
    "slug": "repair-responsibility-dispute",
    "merge_of": [
     "tmp:kb:2974"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：責任認定有爭議時查租約條款、由管理師調解並保留溝通紀錄，為獨立可答的處理程序。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-warranty-period",
    "coarse_id": "F",
    "title": "修繕後的保固期",
    "slug": "repair-warranty-period",
    "merge_of": [
     "tmp:kb:2975"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：修繕完成後的保固期通常一年、依合約而異，屬修繕結果的保障，非租約條款本身，留本架。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/F/repair-neighbor-leak-responsibility",
    "coarse_id": "F",
    "title": "鄰居漏水的修繕責任與處理",
    "slug": "repair-neighbor-leak-responsibility",
    "merge_of": [
     "tmp:kb:2967"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層級：鄰損（鄰居漏水）由漏水方負責、透過管理師協調並儘快報修，責任對象為第三方，與房東／租客總則分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/F/repair-system",
    "new": "jgb/F/repair-system",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-open-and-confirm",
    "new": "jgb/F/repair-ticket-open-and-confirm",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-after-submit",
    "new": "jgb/F/repair-ticket-after-submit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-mid-flow-cancel",
    "new": "jgb/F/repair-ticket-mid-flow-cancel",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-no-lease",
    "new": "jgb/F/repair-ticket-no-lease",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-count-limit",
    "new": "jgb/F/repair-ticket-photo-count-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain",
    "new": "jgb/F/repair-ticket-photo-recognition-uncertain",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-reclassify",
    "new": "jgb/F/repair-ticket-reclassify",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-submit-failure",
    "new": "jgb/F/repair-ticket-submit-failure",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-ticket-urgency-judgment",
    "new": "jgb/F/repair-ticket-urgency-judgment",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/F/repair-progress-followup-scope",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:1558",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3365",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4420",
    "new": "jgb/F/repair-progress-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3424",
    "new": "jgb/F/repair-flow-stages",
    "op": "new"
   },
   {
    "old": "tmp:kb:3425",
    "new": "jgb/F/repair-cost-record-and-bill",
    "op": "new"
   },
   {
    "old": "tmp:kb:3426",
    "new": "jgb/F/repair-emergency-flag-and-priority",
    "op": "new"
   },
   {
    "old": "tmp:kb:3145",
    "new": "jgb/F/repair-emergency-flag-and-priority",
    "op": "new"
   },
   {
    "old": "tmp:kb:3427",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:3446",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:2972",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:4416",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:4418",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:4421",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:4422",
    "new": "jgb/F/repair-request-submit-steps",
    "op": "new"
   },
   {
    "old": "tmp:kb:4654",
    "new": "jgb/F/repair-request-multiple-items",
    "op": "new"
   },
   {
    "old": "tmp:kb:3488",
    "new": "jgb/F/repair-dispatch-and-close",
    "op": "new"
   },
   {
    "old": "tmp:kb:4249",
    "new": "jgb/F/repair-dispatch-and-close",
    "op": "new"
   },
   {
    "old": "tmp:kb:2963",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2964",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2968",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2969",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2971",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:2973",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3029",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3030",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3203",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3222",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3277",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3287",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3289",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3221",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3320",
    "new": "jgb/F/repair-responsibility-landlord-vs-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3187",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3189",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3193",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3195",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3198",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3200",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3272",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3275",
    "new": "jgb/F/repair-tenant-equipment-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2970",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3186",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3188",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3190",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3192",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3194",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3197",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:3274",
    "new": "jgb/F/repair-common-facility-responsibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:2966",
    "new": "jgb/F/repair-notify-duty-and-timely-repair-right",
    "op": "new"
   },
   {
    "old": "tmp:kb:3219",
    "new": "jgb/F/repair-notify-duty-and-timely-repair-right",
    "op": "new"
   },
   {
    "old": "tmp:kb:3286",
    "new": "jgb/F/repair-notify-duty-and-timely-repair-right",
    "op": "new"
   },
   {
    "old": "tmp:kb:2965",
    "new": "jgb/F/repair-tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:3220",
    "new": "jgb/F/repair-tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:3288",
    "new": "jgb/F/repair-tenant-emergency-self-repair",
    "op": "new"
   },
   {
    "old": "tmp:kb:2974",
    "new": "jgb/F/repair-responsibility-dispute",
    "op": "new"
   },
   {
    "old": "tmp:kb:2975",
    "new": "jgb/F/repair-warranty-period",
    "op": "new"
   },
   {
    "old": "tmp:kb:2967",
    "new": "jgb/F/repair-neighbor-leak-responsibility",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "D",
    "why": "純法律條文（民法及租賃法規對房東維持租賃物狀態的義務），屬租約權益的法源，非修繕操作或責任實務。"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "D",
    "why": "純法律條文引用（民法第 655 條、租屋條例），屬租約法源，非修繕實務。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。