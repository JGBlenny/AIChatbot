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
⚠️ 本次為擴充模式，**只補一架（G）**：候選項目分兩種——`tmp:canon:*`（G 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `G`，`id` 必須為 `jgb/G/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/G/meter-item-followup-scope", "tmp:canon:jgb/G/smart-meter-lock-iot", "tmp:kb:2989", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3191", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3196", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3201", "tmp:kb:3202", "tmp:kb:3203", "tmp:kb:3272", "tmp:kb:3273", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3290", "tmp:kb:3458", "tmp:kb:3460", "tmp:kb:3461", "tmp:kb:3462", "tmp:kb:3508", "tmp:kb:4044", "tmp:kb:4049", "tmp:kb:4051", "tmp:kb:4052", "tmp:kb:4054", "tmp:kb:4055", "tmp:kb:4058", "tmp:draft:1"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/G/meter-item-followup-scope", "tmp:canon:jgb/G/smart-meter-lock-iot", "tmp:kb:2989", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3191", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3196", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3201", "tmp:kb:3202", "tmp:kb:3203", "tmp:kb:3272", "tmp:kb:3273", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3290", "tmp:kb:3458", "tmp:kb:3460", "tmp:kb:3461", "tmp:kb:3462", "tmp:kb:3508", "tmp:kb:4044", "tmp:kb:4049", "tmp:kb:4051", "tmp:kb:4052", "tmp:kb:4054", "tmp:kb:4055", "tmp:kb:4058", "tmp:draft:1"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/G/meter-item-followup-scope", "tmp:canon:jgb/G/smart-meter-lock-iot", "tmp:kb:2989", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3191", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3196", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3201", "tmp:kb:3202", "tmp:kb:3203", "tmp:kb:3272", "tmp:kb:3273", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3290", "tmp:kb:3458", "tmp:kb:3460", "tmp:kb:3461", "tmp:kb:3462", "tmp:kb:3508", "tmp:kb:4044", "tmp:kb:4049", "tmp:kb:4051", "tmp:kb:4052", "tmp:kb:4054", "tmp:kb:4055", "tmp:kb:4058", "tmp:draft:1"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/G/meter-item-followup-scope", "tmp:canon:jgb/G/smart-meter-lock-iot", "tmp:kb:2989", "tmp:kb:3186", "tmp:kb:3187", "tmp:kb:3188", "tmp:kb:3189", "tmp:kb:3190", "tmp:kb:3191", "tmp:kb:3192", "tmp:kb:3193", "tmp:kb:3194", "tmp:kb:3195", "tmp:kb:3196", "tmp:kb:3197", "tmp:kb:3198", "tmp:kb:3199", "tmp:kb:3200", "tmp:kb:3201", "tmp:kb:3202", "tmp:kb:3203", "tmp:kb:3272", "tmp:kb:3273", "tmp:kb:3274", "tmp:kb:3275", "tmp:kb:3276", "tmp:kb:3277", "tmp:kb:3290", "tmp:kb:3458", "tmp:kb:3460", "tmp:kb:3461", "tmp:kb:3462", "tmp:kb:3508", "tmp:kb:4044", "tmp:kb:4049", "tmp:kb:4051", "tmp:kb:4052", "tmp:kb:4054", "tmp:kb:4055", "tmp:kb:4058", "tmp:draft:1"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（41 筆，原序列舉）
### tmp:canon:jgb/G/meter-item-followup-scope
標題：電錶項目追問可答範圍（導向電表排障面向）
內容：電錶餘額不足走電表排障面向；電錶可依名稱或 id 指定，餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算，必須標明是推算。 本細目涵蓋的系統機制目錄：IoT領域-智慧設備(母共用)；IoT領域-電表排障(子面向) 機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準

### tmp:canon:jgb/G/smart-meter-lock-iot
標題：智慧電錶與門鎖整合
內容：現場抄電表、換門鎖很煩？ 金箍棒有整合智慧電錶（抄表可自動帶入帳單）與智慧門鎖，屬硬體設備，實際支援範圍、安裝與費用由專人為您說明。 門鎖分兩型：「私人門鎖」是單一房間的門鎖，只綁一個物件，房東與租客各自設一組密碼；「共用門鎖」是大樓或住家大門，可綁多個物件，由房東設一組共用密碼給租客使用。 可留資由專人與您聯絡。

### tmp:kb:2989
標題：設備使用規範
內容：租客在使用租屋內的設備時，應遵循合約中列明的使用規範，例如不得隨意改裝設備、妥善維護並報告任何故障。若設備出現問題，請及時聯繫管理師進行維修，這是您的權利與責任。

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

### tmp:kb:3191
標題：設備處理
內容：租期結束時，您需要檢查並確保所有設備的狀況良好。若有損壞或故障，請及時通知管理師進行維修或更換，以免影響押金的退還。建議您在退租前拍攝設備的照片作為證據，保留良好記錄。

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

### tmp:kb:3196
標題：公共設備使用限制
內容：租客對公共設備的使用通常會有一些基本的限制，例如使用時間、使用人數或遵守社區規範等。具體的使用規則會在租約中列明，您可以參考租約內容或直接詢問您的管理師以獲取詳細信息。

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

### tmp:kb:3201
標題：公共設備使用規範
內容：公共設備的使用規範通常包括不打擾他人、保持設備清潔，以及遵守使用時間等要求。具體規範可能因物件而異，建議您查看租約或與管理師確認詳細規定。

### tmp:kb:3202
標題：租客設備投保
內容：租客設備是否需要投保，通常取決於租約的約定。一般來說，租客有權選擇為其個人物品投保，以避免意外損失。建議您檢視租約內容，若有疑問可聯繫您的管理師確認具體要求。

### tmp:kb:3203
標題：維護責任範圍
內容：房東的維護責任通常包括房屋結構、暖氣系統、冷氣系統、水管、電力系統、以及其他固定設備的正常運作。如果您遇到任何設備故障，請及時聯繫您的管理師進行維修申請。

### tmp:kb:3272
標題：設備維護責任
內容：租客在租期內對租客設備的維護責任主要包括日常的保養和清潔。如設備出現故障或需修理，應及時通知管理師協助處理。租客不需負責因正常使用造成的磨損，但如因不當使用導致損壞，則需負擔修理費用。

### tmp:kb:3273
標題：設備狀況處理
內容：租期結束時，您需檢查並整理設備狀況，確保所有設備運作正常。如有損壞或異常，請及時通知管理師，以便進行維修或處理。這樣有助於順利退還押金，並避免不必要的費用扣除。

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

### tmp:kb:3290
標題：租屋設備使用規範
內容：租客在使用租屋內設備時，應遵循合約中約定的規範，通常包括妥善使用設備、定期維護以及不得私自改動設備設置等。此外，若設備出現故障，請及時聯繫管理師報修，確保問題能夠迅速處理，保障您的居住權益。

### tmp:kb:3458
標題：智慧門鎖 使用說明
內容：JGB 智慧門鎖功能：（1）密碼開門：系統為每位租客產生專屬門鎖密碼，在合約有效期間內可使用；（2）QR Code 開門：系統產生 QR Code，掃碼即可開門，適合訪客臨時使用；（3）開門紀錄：可在系統中查看門鎖的開門歷史記錄。房東可管理門鎖密碼（新增/刪除），也可產生分享密碼供訪客或維修人員臨時使用。若門鎖無法開啟，請確認密碼是否正確、門鎖電量是否充足、網路連線是否正常。

### tmp:kb:3460
標題：電表低電量警報 通知
內容：當儲值電表的餘額低於設定的警戒值時，系統會自動發送低電量警報通知給租客和房東，提醒儘速儲值以避免斷電。系統每日自動檢查所有電表餘額狀態。房東可在管理後台查看低電量警報的歷史紀錄。收到警報後建議立即進行儲值操作，儲值成功後警報會自動解除。

### tmp:kb:3461
標題：IoT 設備無法連線 排查
內容：IoT 設備（門鎖/電表）無法連線的排查順序：1. 確認設備電源正常（門鎖電池、電表通電）；2. 確認現場網路正常（Wi-Fi/閘道器可嘗試重啟）；3. 台科電電表特別注意：若同一帳號下多顆電表同時顯示離線或數據長期不更新，高機率是台科電雲端帳號的密碼變更或未開通 API 服務——請到「團隊管理→進階設定→綁定設備廠商」重新驗證廠商帳號密碼即可恢復。系統與廠商的資料同步為每小時一次，剛恢復後請等下一次同步再確認。以上都排除仍離線，請聯繫對應廠商（台科電/SkyWatch），並提供設備名稱與所在物件。

### tmp:kb:3462
標題：分享門鎖密碼 臨時存取
內容：房東可產生臨時分享密碼提供給訪客、維修人員或清潔人員使用。操作方式：在門鎖管理頁面選擇「分享密碼」，系統會產生一組一次性或限時密碼，可透過連結或訊息分享給對方。分享密碼有使用次數或時間限制，過期後自動失效。此功能僅限房東或有門鎖管理權限的團隊成員操作，租客無法產生分享密碼。

### tmp:kb:3508
標題：IoT 廠商帳號綁定失敗
內容：帳號已被綁定時，需查 DB 確認被哪個 role 綁走。

### tmp:kb:4044
標題：電錶數據與 JGB 不同 度數落差
內容：電表實體顯示的度數與 JGB 上的數字不同，先看落差多大：系統與廠商的資料同步為每小時一次，一小時內的落差屬正常現象，等下次同步就會追上。若數字長期不動或落差持續擴大，高機率是台科電雲端帳號的密碼變更或未開通 API 服務，導致該帳號下所有電表停止同步——到「團隊管理→進階設定→綁定設備廠商」重新驗證廠商帳號密碼即可恢復。JGB 顯示的度數一律以最後同步值為準，不會自行推算。

### tmp:kb:4049
標題：電表串接 綁定 啟用
內容：電表安裝好之後要串接進 JGB：到「團隊管理→進階設定→綁定設備廠商」綁定廠商帳號（台科電選「台科電儲值系統」，輸入雲端帳號密碼），驗證通過後系統會自動同步該帳號下的裝置清單，不需逐顆手動新增；之後每日也會自動同步新裝置。注意：同一個廠商帳號只能綁定一個團隊，若顯示已被綁定，需聯繫客服處理換綁。剛同步的電表不會自動關聯物件，請到「裝置管理→智慧電錶」逐顆編輯綁定物件，租客端就能看到自己房間的電表。要讓租客走儲值電費，建立/編輯合約時電費欄選「依儲值電錶設定」，租客儲值的付款管道會沿用該合約的收款方式（線下/線上）。

### tmp:kb:4051
標題：租客看即時電表 可見設定
內容：租客註冊並綁定合約後，就能在租客端前台看到自己房間的電表即時資訊（度數、儲值餘額）並自行儲值。前提：電表已關聯到該物件、合約已綁定該租客。若租客反映看不到電表，先確認合約與物件的關聯設定；租客登入身分問題（登錯帳號、身分未切換）屬帳號範疇另行排查。

### tmp:kb:4052
標題：IoT 連結起始日 密碼規則 生效
內容：IoT 設定中的門鎖預設密碼規則（如手機末四碼）與連結起始日，決定租客門鎖權限的產生方式與生效時點。調整規則時注意生效範圍：以設定頁說明為準，通常影響新建立的連結，既有合約的門鎖權限是否同步調整請於設定頁確認或逐一檢視。不確定影響範圍時建議先詢問客服再調整，避免影響在住租客的門鎖使用。

### tmp:kb:4054
標題：門鎖硬體功能 悠遊卡 磁扣 電池
內容：門鎖的硬體功能問題——例如是否支援悠遊卡/磁扣開門、磁扣費用、按鍵音量能否調整、電池與接電供電方式——這些屬於門鎖廠商的硬體規格範疇，支援與否和費用以該型號的廠商文件為準，JGB 系統端無法調整硬體行為。請聯繫對應的門鎖廠商（如 SkyWatch）詢問，並提供門鎖型號。JGB 端可管理的是門鎖密碼規則與分享密碼等軟體功能。

### tmp:kb:4055
標題：門鎖失靈 QRCode 密碼開不了
內容：門鎖 QRCode 或密碼突然失靈開不了門：先做基本排查——確認門鎖電池電量（低電量常導致感應異常）、密碼是否在有效期內（租客密碼與合約效期連動）、QRCode 是否過期重新產生一組試試。基本排查後仍失靈，屬設備故障，請聯繫門鎖廠商處理並提供型號與狀況描述；租客被鎖在門外的緊急情況請依社區的備用開門程序處理。

### tmp:kb:4058
標題：電表要怎麼串接進系統
內容：

### tmp:draft:1
標題：房東教學08：IOT設備篇
內容：房東教學08：IOT設備篇 ⚠️ 版本更新 版本更新後，智慧串接設備在系統上僅可操作智慧電表。 智慧電錶 產品主要功能： 串接JGB系統雲端抄錶，免出門、免對帳 串接JGB系統可與帳單進行聯動帶入用電度數 隨時在JGB系統查看用電狀況 智慧電錶的綁定與串接需由 JGB的業務協助，請點選頁面右下角的對話框，進行諮詢，或是寄送電子郵件至 客服信箱（官網），將會有專人與您聯絡。 系統功能＆介面展示 目前JGBx台科電智慧儲值電錶，有特別的教學與導覽 JGBx台科電 儲值電錶串接3大特點 台科電智慧電錶儲值教學（管理者篇） 台科電智慧電錶儲值教學（租客篇） 非台科電電錶的基本設定及綁定物件 點選【裝置管理】>【智慧電錶】查看現有的智能設備列表以及各設備所綁定之物件和其他資訊。 在頁面中點選【編輯】可以進到電錶命名、供電/斷電、綁定物件的定義。 圖 1 操作畫面 點選【儲存】完成設定。 圖 2 操作畫面 查看用電度數 點選【裝置管理】>【智慧電錶】點選【下箭頭圖示】即可查看每天或每周的用電度數以及折線圖。 圖 3 操作畫面 圖 4 操作畫面 智慧電錶綁帳單 電錶建立完成之後，jgb系統也可以同時計算綁定物件的電費，並且生成帳單 首先先進入【帳務管理】>【待發送帳單】，找到綁有智慧電表物件的帳單，選擇【編輯帳單】。 📌 小提醒 請注意此時帳單右方所顯示的金額尚未加計電費 進入編輯頁面後，可看到支出帳單部分，電費已依照本期度數扣除上期度數，乘以每度金額，自動計算完畢，此時若有需要調整之部分也可以於此編輯。 圖 5 操作畫面 確認完帳單總金額後，即可點選【發送帳單】，通知租客繳費。 圖 6 操作畫面


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
    "id": "jgb/G/meter-item-followup-scope",
    "coarse_id": "G",
    "title": "電錶項目追問可答範圍（導向電表排障面向）",
    "slug": "meter-item-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/G/meter-item-followup-scope"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目原樣保留：已登入使用者追問自己電錶餘額／度數／供電時的可答範圍與資料來源，是獨立問題，無新材料需併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:canon:jgb/G/smart-meter-lock-iot"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目原樣保留：潛在客戶問「有沒有支援智慧電錶／門鎖、怎麼開始」落此；PM 的操作型問題另有各自細目，不混入。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/G/meter-vendor-account-binding",
    "coarse_id": "G",
    "title": "電表串接：綁定廠商帳號（台科電）與已被綁定處理",
    "slug": "meter-vendor-account-binding",
    "merge_of": [
     "tmp:kb:4049",
     "tmp:kb:4058",
     "tmp:kb:3508",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "問法「電表要怎麼串接進 JGB／怎麼綁台科電帳號／顯示帳號已被綁定怎麼辦」為一個問題：取 4049 的廠商帳號綁定與自動同步段、3508 的已被綁定處理、draft:1 的「綁定需業務協助＋台科電有專屬教學」段；4058 內文為空，只當入口併入。draft:1 的「電錶綁帳單」段依歸位判準屬 E（抄表→帳單），本架不提成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-device-property-binding",
    "coarse_id": "G",
    "title": "電表綁定物件、命名與供電／斷電設定",
    "slug": "meter-device-property-binding",
    "merge_of": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "問法「同步進來的電表怎麼綁到房間／怎麼改名／怎麼斷電供電」與帳號綁定是不同步驟的不同問題：取 4049 的「裝置管理→智慧電錶逐顆編輯綁定物件」段與 draft:1 的非台科電基本設定段（命名、供電／斷電、綁定物件）。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/tenant-meter-visibility-prepaid",
    "coarse_id": "G",
    "title": "租客看到自己電表與走儲值電費的前提設定",
    "slug": "tenant-meter-visibility-prepaid",
    "merge_of": [
     "tmp:kb:4051",
     "tmp:kb:4049"
    ],
    "split_from": [
     "tmp:kb:4049"
    ],
    "moved_from": [],
    "reason": "問法「租客說看不到電表／租客怎麼儲值電費」為一個問題：4051 的可見前提（電表關聯物件＋合約綁定租客）加上 4049 的「合約電費欄選依儲值電錶設定、付款管道沿用合約」段；登入身分問題屬 A 架另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-usage-readings-view",
    "coarse_id": "G",
    "title": "查看電表每日／每週用電度數",
    "slug": "meter-usage-readings-view",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "問法「在後台哪裡看用電度數／折線圖」是獨立的查詢型問題：取 draft:1 的「裝置管理→智慧電錶→下箭頭查看每天或每周度數」段。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-reading-mismatch-sync",
    "coarse_id": "G",
    "title": "電表實體度數與 JGB 顯示不同",
    "slug": "meter-reading-mismatch-sync",
    "merge_of": [
     "tmp:kb:4044"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「電表上的數字跟系統不一樣」是獨立排障問題：同步一小時一次、長期不動時重新驗證廠商帳號；與離線排查共用同一補救動作但提問入口不同，另見不合併。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/iot-device-offline-troubleshoot",
    "coarse_id": "G",
    "title": "IoT 設備（門鎖／電表）離線或無法連線排查",
    "slug": "iot-device-offline-troubleshoot",
    "merge_of": [
     "tmp:kb:3461"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「設備顯示離線／連不上」是獨立排障問題：電源→網路→台科電帳號重新驗證→聯繫廠商的排查順序。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-low-balance-alert",
    "coarse_id": "G",
    "title": "儲值電表低電量警報通知",
    "slug": "meter-low-balance-alert",
    "merge_of": [
     "tmp:kb:3460"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「收到低電量警報是什麼／怎麼解除／哪裡看紀錄」是獨立問題；通知是投遞管道，內容歸它所通知的電表儲值餘額主題，落本架。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-features-usage",
    "coarse_id": "G",
    "title": "智慧門鎖功能與使用（密碼、QR Code、開門紀錄、密碼管理）",
    "slug": "smart-lock-features-usage",
    "merge_of": [
     "tmp:kb:3458"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "問法「門鎖有哪些開門方式／怎麼管理租客密碼／哪裡看開門紀錄」為一個功能總覽問題：取 3458 的功能段；其「門鎖無法開啟」尾段拆至門鎖失靈細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-share-password",
    "coarse_id": "G",
    "title": "分享門鎖密碼給訪客／維修／清潔人員",
    "slug": "smart-lock-share-password",
    "merge_of": [
     "tmp:kb:3462"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「怎麼給訪客或維修人員臨時密碼」是獨立操作問題，與功能總覽層級不同，以另見處理不合併。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-password-rule-start-date",
    "coarse_id": "G",
    "title": "IoT 設定：門鎖預設密碼規則與連結起始日",
    "slug": "smart-lock-password-rule-start-date",
    "merge_of": [
     "tmp:kb:4052"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「密碼規則改了會不會影響在住租客／連結起始日是什麼」是獨立的設定生效範圍問題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-hardware-vendor-scope",
    "coarse_id": "G",
    "title": "門鎖硬體功能（悠遊卡、磁扣、音量、電池）歸廠商",
    "slug": "smart-lock-hardware-vendor-scope",
    "merge_of": [
     "tmp:kb:4054"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法「門鎖支援悠遊卡嗎／磁扣多少錢／電池怎麼供電」是硬體規格問題，答案為導向廠商並劃分 JGB 端可管理的軟體範圍，獨立成一細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-unlock-failure",
    "coarse_id": "G",
    "title": "門鎖 QR Code 或密碼失靈開不了門",
    "slug": "smart-lock-unlock-failure",
    "merge_of": [
     "tmp:kb:4055",
     "tmp:kb:3458"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "問法「門鎖突然開不了」是獨立排障問題：取 4055 全文與 3458 的「若門鎖無法開啟請確認密碼／電量／網路」尾段。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/G/meter-item-followup-scope",
    "new": "jgb/G/meter-item-followup-scope",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/G/smart-meter-lock-iot",
    "new": "jgb/G/smart-meter-lock-iot",
    "op": "keep"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/meter-vendor-account-binding",
    "op": "split"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/meter-device-property-binding",
    "op": "split"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/tenant-meter-visibility-prepaid",
    "op": "split"
   },
   {
    "old": "tmp:kb:4058",
    "new": "jgb/G/meter-vendor-account-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:3508",
    "new": "jgb/G/meter-vendor-account-binding",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-vendor-account-binding",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-device-property-binding",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-usage-readings-view",
    "op": "split"
   },
   {
    "old": "tmp:kb:4051",
    "new": "jgb/G/tenant-meter-visibility-prepaid",
    "op": "new"
   },
   {
    "old": "tmp:kb:4044",
    "new": "jgb/G/meter-reading-mismatch-sync",
    "op": "new"
   },
   {
    "old": "tmp:kb:3461",
    "new": "jgb/G/iot-device-offline-troubleshoot",
    "op": "new"
   },
   {
    "old": "tmp:kb:3460",
    "new": "jgb/G/meter-low-balance-alert",
    "op": "new"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-features-usage",
    "op": "split"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-unlock-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:3462",
    "new": "jgb/G/smart-lock-share-password",
    "op": "new"
   },
   {
    "old": "tmp:kb:4052",
    "new": "jgb/G/smart-lock-password-rule-start-date",
    "op": "new"
   },
   {
    "old": "tmp:kb:4054",
    "new": "jgb/G/smart-lock-hardware-vendor-scope",
    "op": "new"
   },
   {
    "old": "tmp:kb:4055",
    "new": "jgb/G/smart-lock-unlock-failure",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2989",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "租客依合約規範使用室內設備，是租約條款題，且受眾為租客，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3186",
    "suggested_shelf": "F：修繕",
    "why": "公共設備維護責任與通知管理師處理，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3187",
    "suggested_shelf": "F：修繕",
    "why": "正常磨損 vs 不當使用的維修責任歸屬，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3188",
    "suggested_shelf": "F：修繕",
    "why": "公共設備損壞誰負責修，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3189",
    "suggested_shelf": "F：修繕",
    "why": "設備損壞修繕費用歸屬依租約與原因判定，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3190",
    "suggested_shelf": "F：修繕",
    "why": "公共設備檢查頻率屬維護作業，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3191",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "退租時設備檢查與押金扣除，是租約退租題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3192",
    "suggested_shelf": "F：修繕",
    "why": "公共設備維護費用由誰負擔，是修繕費用責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3193",
    "suggested_shelf": "F：修繕",
    "why": "室內設備維護費用由誰負擔，是修繕費用責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3194",
    "suggested_shelf": "F：修繕",
    "why": "公共設備更新責任歸屬，是修繕／更換責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3195",
    "suggested_shelf": "F：修繕",
    "why": "租客設備更新責任歸屬，是修繕／更換責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3196",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "公共設備使用時間／人數限制由租約與社區規範列明，是租約條款題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3197",
    "suggested_shelf": "F：修繕",
    "why": "房東保留設備維護記錄，是修繕管理題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3198",
    "suggested_shelf": "F：修繕",
    "why": "租客使用設備的維護與不當使用賠責，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "F：修繕",
    "why": "設備維護的民法依據與報修權利，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3200",
    "suggested_shelf": "F：修繕",
    "why": "租客造成設備損壞的賠償標準，是修繕費用責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3201",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "公共設備使用規範由租約與物件規定列明，是租約條款題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3202",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "租客物品是否投保依租約約定，是租約條款題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3203",
    "suggested_shelf": "F：修繕",
    "why": "房東維護責任範圍（結構、水電、冷暖氣），是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3272",
    "suggested_shelf": "F：修繕",
    "why": "租客設備維護責任與不當使用修理費，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3273",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "退租時設備狀況整理與押金退還，是租約退租題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3274",
    "suggested_shelf": "F：修繕",
    "why": "公共設備維護費用由房東或物管負擔，是修繕費用責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3275",
    "suggested_shelf": "F：修繕",
    "why": "租客設備使用不當的修復費用責任，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "F：修繕",
    "why": "設備維護的民法與租屋條例依據，是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3277",
    "suggested_shelf": "F：修繕",
    "why": "房東維護責任範圍（結構、水電氣），是修繕責任題，非 IoT 裝置"
   },
   {
    "id": "tmp:kb:3290",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "租客依合約規範使用室內設備不得私自改動，是租約條款題，非 IoT 裝置"
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
    "id": "jgb/G/meter-item-followup-scope",
    "coarse_id": "G",
    "title": "電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報）",
    "slug": "meter-item-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/G/meter-item-followup-scope",
     "tmp:kb:3460"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目 id 不變；kb:3460 低電量警報是「電錶餘額不足」這個命題的投遞管道（通知不自成細目、歸它所通知的領域），與餘額／可用度數／供電同屬一個可獨立回答的主題，故吸收為 merge；「還能用幾天」仍標明為推算。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合（售前）",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:canon:jgb/G/smart-meter-lock-iot"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目原樣保留：售前層級的「有沒有整合、門鎖兩型、留資由專人說明」自成完整內容；draft:1 雖有相同產品賣點，但受眾為房東操作教學、答案因受眾而異，依「各受眾各一細目」不併入。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/G/meter-vendor-binding",
    "coarse_id": "G",
    "title": "電表串接：綁定設備廠商帳號與裝置自動同步",
    "slug": "meter-vendor-binding",
    "merge_of": [
     "tmp:kb:4049",
     "tmp:kb:4058",
     "tmp:kb:3508",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "「怎麼把電表串進 JGB」自成一個完整命題：團隊管理→進階設定→綁定設備廠商、驗證後自動同步裝置清單、一個廠商帳號只能綁一個團隊、已被綁定時的換綁處理（kb:3508 的查 DB role 是同一命題的內部處置）。kb:4058 內文為空，只作入口併入；draft:1 的「綁定與串接需由 JGB 業務協助」段拆入此處。kb:4049 尾段「合約電費欄選依儲值電錶設定」屬租約／收款金流（D／E），本架不收、另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-device-management",
    "coarse_id": "G",
    "title": "智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數",
    "slug": "meter-device-management",
    "merge_of": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:kb:4049",
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "裝置管理→智慧電錶頁的操作（命名、供電/斷電、綁定物件、日／週度數折線圖）不依賴廠商綁定步驟即可獨立回答，故自 kb:4049 與 draft:1 拆出成細目；draft:1 的版本警語「僅可操作智慧電表」屬本頁範圍。draft:1「智慧電錶綁帳單」段（帳務管理→待發送帳單自動算電費）出現在帳單列上、屬 E 抄表／帳務，本架不收、另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/tenant-meter-visibility",
    "coarse_id": "G",
    "title": "租客端看到即時電表與自行儲值的前提",
    "slug": "tenant-meter-visibility",
    "merge_of": [
     "tmp:kb:4051"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「租客為什麼看不到電表」是獨立的排查命題，答案自帶前提（電表已關聯物件、合約已綁租客），不需引用裝置管理步驟即完整；登入身分問題明示屬帳號範疇（A）另行排查，不在此細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-data-sync-gap",
    "coarse_id": "G",
    "title": "電錶實體度數與 JGB 不同／長期不更新",
    "slug": "meter-data-sync-gap",
    "merge_of": [
     "tmp:kb:4044"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「度數落差」是與「離線」不同的命題：答案由每小時同步、以最後同步值為準、長期不動時重新驗證廠商帳號三段構成，自身完整；與 iot-offline-troubleshooting 共用同一補救動作但問題不同，各自保留、另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/iot-offline-troubleshooting",
    "coarse_id": "G",
    "title": "IoT 設備（門鎖／電表）無法連線的排查順序",
    "slug": "iot-offline-troubleshooting",
    "merge_of": [
     "tmp:kb:3461"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "連線排查是跨門鎖與電表的獨立命題：電源→現場網路→台科電帳號重新驗證→聯繫廠商，四步互相依賴才構成完整答案，故不再拆；門鎖「開不了門」另屬 smart-lock-failure。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-functions",
    "coarse_id": "G",
    "title": "智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理",
    "slug": "smart-lock-functions",
    "merge_of": [
     "tmp:kb:3458"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "門鎖三項功能與房東的密碼管理是一組彼此依賴的功能說明，自成一題；kb:3458 尾句「無法開啟時確認密碼／電量／網路」屬排障命題，拆到 smart-lock-failure。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-share-password",
    "coarse_id": "G",
    "title": "分享門鎖密碼：訪客／維修人員臨時存取",
    "slug": "smart-lock-share-password",
    "merge_of": [
     "tmp:kb:3462"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "分享密碼的操作步驟、次數／時間限制、僅房東或有權限成員可操作，是可獨立回答的操作命題；smart-lock-functions 僅一句提及，屬不同層級，以另見處理而非重複。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-password-rules",
    "coarse_id": "G",
    "title": "IoT 設定：門鎖預設密碼規則與連結起始日的生效範圍",
    "slug": "smart-lock-password-rules",
    "merge_of": [
     "tmp:kb:4052"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "預設密碼規則與連結起始日的生效時點是設定層級命題，與功能說明、排障皆不重疊，自身完整。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-hardware-vendor",
    "coarse_id": "G",
    "title": "門鎖硬體功能（悠遊卡／磁扣／電池／音量）屬廠商範疇",
    "slug": "smart-lock-hardware-vendor",
    "merge_of": [
     "tmp:kb:4054"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「JGB 端能管什麼、硬體規格找誰」是邊界命題，答案自身完整，與軟體功能細目不重疊。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-failure",
    "coarse_id": "G",
    "title": "門鎖 QRCode／密碼失靈開不了門的排查",
    "slug": "smart-lock-failure",
    "merge_of": [
     "tmp:kb:4055",
     "tmp:kb:3458"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "「開不了門」是獨立排障命題：電池→效期→重新產生 QRCode→聯繫廠商→備用開門程序，需整段才完整；kb:3458 的排障尾句拆入此處；與 iot-offline-troubleshooting（無法連線）是不同故障面，各自保留。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/G/meter-item-followup-scope",
    "new": "jgb/G/meter-item-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3460",
    "new": "jgb/G/meter-item-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/G/smart-meter-lock-iot",
    "new": "jgb/G/smart-meter-lock-iot",
    "op": "keep"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/meter-vendor-binding",
    "op": "split"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/meter-device-management",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-vendor-binding",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-device-management",
    "op": "split"
   },
   {
    "old": "tmp:kb:4058",
    "new": "jgb/G/meter-vendor-binding",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3508",
    "new": "jgb/G/meter-vendor-binding",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4051",
    "new": "jgb/G/tenant-meter-visibility",
    "op": "new"
   },
   {
    "old": "tmp:kb:4044",
    "new": "jgb/G/meter-data-sync-gap",
    "op": "new"
   },
   {
    "old": "tmp:kb:3461",
    "new": "jgb/G/iot-offline-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-functions",
    "op": "split"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:3462",
    "new": "jgb/G/smart-lock-share-password",
    "op": "new"
   },
   {
    "old": "tmp:kb:4052",
    "new": "jgb/G/smart-lock-password-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:4054",
    "new": "jgb/G/smart-lock-hardware-vendor",
    "op": "new"
   },
   {
    "old": "tmp:kb:4055",
    "new": "jgb/G/smart-lock-failure",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2989",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備使用規範由合約條款約定，歸租約。"
   },
   {
    "id": "tmp:kb:3186",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備維護／報修責任歸修繕。"
   },
   {
    "id": "tmp:kb:3187",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租客與房東的維修責任分配歸修繕。"
   },
   {
    "id": "tmp:kb:3188",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備損壞的維修責任歸修繕。"
   },
   {
    "id": "tmp:kb:3189",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備損壞的修繕費用責任歸修繕。"
   },
   {
    "id": "tmp:kb:3190",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備檢查頻率屬維護作業，歸修繕。"
   },
   {
    "id": "tmp:kb:3191",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），退租時設備狀況與押金退還由租約流程決定，歸租約。"
   },
   {
    "id": "tmp:kb:3192",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備維護費用的負擔方屬維修責任分配，歸修繕。"
   },
   {
    "id": "tmp:kb:3193",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租屋內設備維護費用負擔方屬維修責任分配，歸修繕。"
   },
   {
    "id": "tmp:kb:3194",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備更新責任歸修繕。"
   },
   {
    "id": "tmp:kb:3195",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備更新責任歸修繕。"
   },
   {
    "id": "tmp:kb:3196",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備使用限制在租約中列明，歸租約。"
   },
   {
    "id": "tmp:kb:3197",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備維護記錄屬維護作業，歸修繕。"
   },
   {
    "id": "tmp:kb:3198",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），不當使用造成損壞的修繕責任歸修繕。"
   },
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備維護的法律依據與報修權利歸修繕。"
   },
   {
    "id": "tmp:kb:3200",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備損壞賠償屬修繕費用責任，歸修繕。"
   },
   {
    "id": "tmp:kb:3201",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備使用規範由租約約定，歸租約。"
   },
   {
    "id": "tmp:kb:3202",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租客設備投保與否由租約約定，歸租約。"
   },
   {
    "id": "tmp:kb:3203",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），房東維護責任範圍歸修繕。"
   },
   {
    "id": "tmp:kb:3272",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租客設備維護責任歸修繕。"
   },
   {
    "id": "tmp:kb:3273",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），退租時設備狀況處理與押金扣除由租約流程決定，歸租約。"
   },
   {
    "id": "tmp:kb:3274",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），公共設備維護費用負擔方屬維修責任分配，歸修繕。"
   },
   {
    "id": "tmp:kb:3275",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租客設備責任與修復費用歸修繕。"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），設備維護法律依據歸修繕。"
   },
   {
    "id": "tmp:kb:3277",
    "suggested_shelf": "F：修繕",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），房東維護責任範圍歸修繕。"
   },
   {
    "id": "tmp:kb:3290",
    "suggested_shelf": "D：租約（含委託約子題）",
    "why": "受眾為租客的一般設備責任知識（非 IoT 裝置、非 prospect／property_manager），租屋設備使用規範由合約約定，歸租約。"
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
    "id": "jgb/G/smart-meter-lock-iot",
    "coarse_id": "G",
    "title": "智慧電錶與門鎖整合",
    "slug": "smart-meter-lock-iot",
    "merge_of": [
     "tmp:canon:jgb/G/smart-meter-lock-iot",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "能力層／售前受眾：產品能做什麼（雲端抄錶、帳單聯動、門鎖兩型）與「由業務協助串接、可留資」；tmp:draft:1 開頭的產品主要功能與諮詢段落屬能力層併入此細目，其操作教學段落拆至 jgb/G/meter-device-management；業者受眾的操作層另見該細目，不在此重複。",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/G/meter-item-followup-scope",
    "coarse_id": "G",
    "title": "電錶項目追問可答範圍（含餘額與低電量警報）",
    "slug": "meter-item-followup-scope",
    "merge_of": [
     "tmp:canon:jgb/G/meter-item-followup-scope",
     "tmp:kb:3460"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層／業者受眾：電錶餘額、可用度數、供電狀態的可答範圍與資料來源；tmp:kb:3460 的低電量警報是「餘額低於警戒值」這個命題的通知管道（通知歸它所通知的領域，不自成細目），同受眾同層級併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/G/meter-vendor-binding",
    "coarse_id": "G",
    "title": "電表串接與廠商帳號綁定",
    "slug": "meter-vendor-binding",
    "merge_of": [
     "tmp:kb:4049",
     "tmp:kb:4058",
     "tmp:kb:3508"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層／業者受眾：電表裝好後如何綁定廠商帳號、自動同步裝置清單、同一廠商帳號只能綁一個團隊；tmp:kb:4058 為空內文入口併入；tmp:kb:3508「帳號已被綁定需查 DB 看被哪個 role 綁走」是同一命題（已被綁定）的處置備註併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/meter-device-management",
    "coarse_id": "G",
    "title": "智慧電錶裝置管理與租客可見設定",
    "slug": "meter-device-management",
    "merge_of": [
     "tmp:draft:1",
     "tmp:kb:4051"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "操作層／業者受眾：裝置管理→智慧電錶的命名、供電／斷電、綁定物件、查看每日／每週用電度數，以及租客端要看到電表所需的物件關聯與合約綁定前提（租客看不到電表的排查）；自 tmp:draft:1 拆出操作教學段落；draft 的「智慧電錶綁帳單」段落屬 E 抄表命題，此處只另見不承接；租客登入身分問題另見 A。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/iot-offline-sync-troubleshooting",
    "coarse_id": "G",
    "title": "IoT 裝置離線與數據同步落差排查",
    "slug": "iot-offline-sync-troubleshooting",
    "merge_of": [
     "tmp:kb:3461",
     "tmp:kb:4044"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層／業者受眾：門鎖／電表無法連線、電錶度數與 JGB 不同的排查順序，兩者共用同一根因（每小時同步、台科電雲端帳號密碼變更或未開通 API → 重新驗證廠商帳號）與同一升級路徑（聯繫廠商），故同受眾同層級合為一細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-management",
    "coarse_id": "G",
    "title": "智慧門鎖密碼與分享權限管理",
    "slug": "smart-lock-management",
    "merge_of": [
     "tmp:kb:3458",
     "tmp:kb:3462",
     "tmp:kb:4052"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "操作層／業者受眾：JGB 端可管理的門鎖軟體功能——租客專屬密碼、QR Code、開門紀錄、分享密碼（僅房東／有權限成員可產生）、預設密碼規則與連結起始日的生效範圍；tmp:kb:3458 的功能與管理段落歸此，其結尾「門鎖無法開啟」排查句拆至 jgb/G/smart-lock-failure；售前的門鎖能力層另見 jgb/G/smart-meter-lock-iot。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-failure",
    "coarse_id": "G",
    "title": "門鎖失靈排查",
    "slug": "smart-lock-failure",
    "merge_of": [
     "tmp:kb:4055",
     "tmp:kb:3458"
    ],
    "split_from": [
     "tmp:kb:3458"
    ],
    "moved_from": [],
    "reason": "操作層／業者受眾：QR Code 或密碼開不了門的基本排查（電池、密碼效期與合約連動、QR 過期重產）、排除後屬設備故障轉廠商、被鎖門外走社區備用程序；tmp:kb:3458 結尾的排查句拆入此細目；純連線問題另見 jgb/G/iot-offline-sync-troubleshooting。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/G/smart-lock-hardware-boundary",
    "coarse_id": "G",
    "title": "門鎖硬體功能與廠商邊界",
    "slug": "smart-lock-hardware-boundary",
    "merge_of": [
     "tmp:kb:4054"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力邊界層／業者受眾：悠遊卡／磁扣、按鍵音量、電池與供電等屬門鎖廠商硬體規格，JGB 系統端無法調整，需帶型號問廠商；與失靈排查（操作層）是不同命題，故各自一細目而非同一層級重複。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/G/smart-meter-lock-iot",
    "new": "jgb/G/smart-meter-lock-iot",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/smart-meter-lock-iot",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/G/meter-item-followup-scope",
    "new": "jgb/G/meter-item-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3460",
    "new": "jgb/G/meter-item-followup-scope",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4049",
    "new": "jgb/G/meter-vendor-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:4058",
    "new": "jgb/G/meter-vendor-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:3508",
    "new": "jgb/G/meter-vendor-binding",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/G/meter-device-management",
    "op": "split"
   },
   {
    "old": "tmp:kb:4051",
    "new": "jgb/G/meter-device-management",
    "op": "new"
   },
   {
    "old": "tmp:kb:3461",
    "new": "jgb/G/iot-offline-sync-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:4044",
    "new": "jgb/G/iot-offline-sync-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-management",
    "op": "split"
   },
   {
    "old": "tmp:kb:3462",
    "new": "jgb/G/smart-lock-management",
    "op": "new"
   },
   {
    "old": "tmp:kb:4052",
    "new": "jgb/G/smart-lock-management",
    "op": "new"
   },
   {
    "old": "tmp:kb:4055",
    "new": "jgb/G/smart-lock-failure",
    "op": "new"
   },
   {
    "old": "tmp:kb:3458",
    "new": "jgb/G/smart-lock-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:4054",
    "new": "jgb/G/smart-lock-hardware-boundary",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2989",
    "suggested_shelf": "D",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是「合約中列明的設備使用規範」，由合約條款決定者歸租約。"
   },
   {
    "id": "tmp:kb:3186",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備維護責任與報修，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3187",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是正常磨損／不當使用的維修責任歸屬，屬修繕。"
   },
   {
    "id": "tmp:kb:3188",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備損壞的維修責任與報修，屬修繕。"
   },
   {
    "id": "tmp:kb:3189",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是設備損壞的修繕費用責任歸屬，屬修繕。"
   },
   {
    "id": "tmp:kb:3190",
    "suggested_shelf": "C",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備檢查頻率依物件管理規定而定，屬社區與物件的管理規範。"
   },
   {
    "id": "tmp:kb:3191",
    "suggested_shelf": "D",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是退租時的設備檢查與押金退還，由合約驅動的退租流程歸租約。"
   },
   {
    "id": "tmp:kb:3192",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備維護費用由誰負擔，是修繕責任歸屬而非金額計算。"
   },
   {
    "id": "tmp:kb:3193",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租屋內設備維護費用由誰負擔，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3194",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備更新責任歸屬，屬修繕／更換責任。"
   },
   {
    "id": "tmp:kb:3195",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租客設備更新責任歸屬，屬修繕／更換責任。"
   },
   {
    "id": "tmp:kb:3196",
    "suggested_shelf": "C",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備使用限制（時間、人數、社區規範），屬社區規範。"
   },
   {
    "id": "tmp:kb:3197",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是房東應保留設備維護記錄，屬修繕管理。"
   },
   {
    "id": "tmp:kb:3198",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是不當使用導致損壞的責任與報修，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3199",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是設備維護的法律依據與房東維修義務，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3200",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租客造成設備損壞的賠償標準，依合約與損壞程度由管理師評估，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3201",
    "suggested_shelf": "C",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備使用規範（不打擾他人、保持清潔、使用時間），屬社區規範。"
   },
   {
    "id": "tmp:kb:3202",
    "suggested_shelf": "D",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租客設備是否投保取決於租約約定，由合約條款決定者歸租約。"
   },
   {
    "id": "tmp:kb:3203",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是房東維護責任範圍（結構、水電、固定設備），屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3272",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租客設備日常保養與不當使用維修責任，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3273",
    "suggested_shelf": "D",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是退租時設備狀況處理與押金扣除，由合約驅動的退租流程歸租約。"
   },
   {
    "id": "tmp:kb:3274",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是公共設備維護費用由房東／物管負擔與報修，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3275",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是租客設備正常故障與不當操作的修復責任，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3276",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是設備維護的法律依據（民法、租屋條例）與房東維修義務，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3277",
    "suggested_shelf": "F",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是房東維護責任範圍（結構、水電氣）與報修，屬修繕責任歸屬。"
   },
   {
    "id": "tmp:kb:3290",
    "suggested_shelf": "D",
    "why": "受眾為租客（值域外，非 prospect／property_manager），且題材是租屋內一般設備（家具家電、公共設施）而非 IoT 裝置；命題是合約約定的租屋設備使用規範（不得私自改動），由合約條款決定者歸租約。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。