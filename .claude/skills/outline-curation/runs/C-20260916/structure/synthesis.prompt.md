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
⚠️ 本次為擴充模式，**只補一架（C）**：候選項目分兩種——`tmp:canon:*`（C 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `C`，`id` 必須為 `jgb/C/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/C/community-batch-create", "tmp:canon:jgb/C/property-management-overview", "tmp:canon:jgb/C/property-status-meaning", "tmp:canon:jgb/C/rental-storefront-vr", "tmp:kb:1396", "tmp:kb:2980", "tmp:kb:3011", "tmp:kb:3049", "tmp:kb:3050", "tmp:kb:3051", "tmp:kb:3052", "tmp:kb:3053", "tmp:kb:3054", "tmp:kb:3055", "tmp:kb:3056", "tmp:kb:3057", "tmp:kb:3058", "tmp:kb:3059", "tmp:kb:3060", "tmp:kb:3061", "tmp:kb:3062", "tmp:kb:3063", "tmp:kb:3064", "tmp:kb:3157", "tmp:kb:3245", "tmp:kb:3246", "tmp:kb:3247", "tmp:kb:3248", "tmp:kb:3249", "tmp:kb:3263", "tmp:kb:3299", "tmp:kb:3300", "tmp:kb:3357", "tmp:kb:3358", "tmp:kb:3428", "tmp:kb:3429", "tmp:kb:3430", "tmp:kb:3431", "tmp:kb:3433", "tmp:kb:3434", "tmp:kb:3456", "tmp:kb:3468", "tmp:kb:3469", "tmp:kb:3470", "tmp:kb:3505", "tmp:kb:3506", "tmp:kb:3973", "tmp:kb:4145", "tmp:kb:4146", "tmp:kb:4147", "tmp:kb:4151", "tmp:kb:4152", "tmp:kb:4154", "tmp:kb:4262", "tmp:kb:4272", "tmp:kb:4276", "tmp:kb:4648", "tmp:draft:1", "tmp:draft:2"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/C/community-batch-create", "tmp:canon:jgb/C/property-management-overview", "tmp:canon:jgb/C/property-status-meaning", "tmp:canon:jgb/C/rental-storefront-vr", "tmp:kb:1396", "tmp:kb:2980", "tmp:kb:3011", "tmp:kb:3049", "tmp:kb:3050", "tmp:kb:3051", "tmp:kb:3052", "tmp:kb:3053", "tmp:kb:3054", "tmp:kb:3055", "tmp:kb:3056", "tmp:kb:3057", "tmp:kb:3058", "tmp:kb:3059", "tmp:kb:3060", "tmp:kb:3061", "tmp:kb:3062", "tmp:kb:3063", "tmp:kb:3064", "tmp:kb:3157", "tmp:kb:3245", "tmp:kb:3246", "tmp:kb:3247", "tmp:kb:3248", "tmp:kb:3249", "tmp:kb:3263", "tmp:kb:3299", "tmp:kb:3300", "tmp:kb:3357", "tmp:kb:3358", "tmp:kb:3428", "tmp:kb:3429", "tmp:kb:3430", "tmp:kb:3431", "tmp:kb:3433", "tmp:kb:3434", "tmp:kb:3456", "tmp:kb:3468", "tmp:kb:3469", "tmp:kb:3470", "tmp:kb:3505", "tmp:kb:3506", "tmp:kb:3973", "tmp:kb:4145", "tmp:kb:4146", "tmp:kb:4147", "tmp:kb:4151", "tmp:kb:4152", "tmp:kb:4154", "tmp:kb:4262", "tmp:kb:4272", "tmp:kb:4276", "tmp:kb:4648", "tmp:draft:1", "tmp:draft:2"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/C/community-batch-create", "tmp:canon:jgb/C/property-management-overview", "tmp:canon:jgb/C/property-status-meaning", "tmp:canon:jgb/C/rental-storefront-vr", "tmp:kb:1396", "tmp:kb:2980", "tmp:kb:3011", "tmp:kb:3049", "tmp:kb:3050", "tmp:kb:3051", "tmp:kb:3052", "tmp:kb:3053", "tmp:kb:3054", "tmp:kb:3055", "tmp:kb:3056", "tmp:kb:3057", "tmp:kb:3058", "tmp:kb:3059", "tmp:kb:3060", "tmp:kb:3061", "tmp:kb:3062", "tmp:kb:3063", "tmp:kb:3064", "tmp:kb:3157", "tmp:kb:3245", "tmp:kb:3246", "tmp:kb:3247", "tmp:kb:3248", "tmp:kb:3249", "tmp:kb:3263", "tmp:kb:3299", "tmp:kb:3300", "tmp:kb:3357", "tmp:kb:3358", "tmp:kb:3428", "tmp:kb:3429", "tmp:kb:3430", "tmp:kb:3431", "tmp:kb:3433", "tmp:kb:3434", "tmp:kb:3456", "tmp:kb:3468", "tmp:kb:3469", "tmp:kb:3470", "tmp:kb:3505", "tmp:kb:3506", "tmp:kb:3973", "tmp:kb:4145", "tmp:kb:4146", "tmp:kb:4147", "tmp:kb:4151", "tmp:kb:4152", "tmp:kb:4154", "tmp:kb:4262", "tmp:kb:4272", "tmp:kb:4276", "tmp:kb:4648", "tmp:draft:1", "tmp:draft:2"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/C/community-batch-create", "tmp:canon:jgb/C/property-management-overview", "tmp:canon:jgb/C/property-status-meaning", "tmp:canon:jgb/C/rental-storefront-vr", "tmp:kb:1396", "tmp:kb:2980", "tmp:kb:3011", "tmp:kb:3049", "tmp:kb:3050", "tmp:kb:3051", "tmp:kb:3052", "tmp:kb:3053", "tmp:kb:3054", "tmp:kb:3055", "tmp:kb:3056", "tmp:kb:3057", "tmp:kb:3058", "tmp:kb:3059", "tmp:kb:3060", "tmp:kb:3061", "tmp:kb:3062", "tmp:kb:3063", "tmp:kb:3064", "tmp:kb:3157", "tmp:kb:3245", "tmp:kb:3246", "tmp:kb:3247", "tmp:kb:3248", "tmp:kb:3249", "tmp:kb:3263", "tmp:kb:3299", "tmp:kb:3300", "tmp:kb:3357", "tmp:kb:3358", "tmp:kb:3428", "tmp:kb:3429", "tmp:kb:3430", "tmp:kb:3431", "tmp:kb:3433", "tmp:kb:3434", "tmp:kb:3456", "tmp:kb:3468", "tmp:kb:3469", "tmp:kb:3470", "tmp:kb:3505", "tmp:kb:3506", "tmp:kb:3973", "tmp:kb:4145", "tmp:kb:4146", "tmp:kb:4147", "tmp:kb:4151", "tmp:kb:4152", "tmp:kb:4154", "tmp:kb:4262", "tmp:kb:4272", "tmp:kb:4276", "tmp:kb:4648", "tmp:draft:1", "tmp:draft:2"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（59 筆，原序列舉）
### tmp:canon:jgb/C/community-batch-create
標題：社區建立與批次新增物件
內容：金箍棒用「社區」把同一棟或同一社區的物件歸戶管理。 流程是先建立社區，再在「社區總表」選該社區，按右側的「批次新增」下載 Excel 模板、填入物件資料後上傳，就能一次把整批物件建進系統；單筆新增則在物件總表「新增物件」。 想看實際畫面可預約 demo。

### tmp:canon:jgb/C/property-management-overview
標題：房源管理模組做什麼（含自訂狀態標籤）
內容：物件多、資料分散難管？ 金箍棒的房源管理把所有物件集中：物件建檔、社區歸戶、批次上傳，還有招租公開頁與 VR 看屋連結，取代散落的 Excel。 物件可以貼團隊自訂的狀態標籤（預設有可帶看、待清潔、待簽約、維修中、不出租、待完善六種），方便篩選與分工。 想看實際畫面可預約 demo。

### tmp:canon:jgb/C/property-status-meaning
標題：物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思
內容：物件總表把物件分成四種狀態：「未刊登」是建好還沒對外刊登，可編輯、刊登或刪除；「刊登中」是已對外招租，可編輯、取消刊登、建立合約；「洽談中」代表已經建立合約但雙方還沒都簽署完成；雙方簽完就變成「合約中」（租約中）。 另外要注意刊登與合約是兩條獨立的軸，租約中的物件也可以同時在刊登中。

### tmp:canon:jgb/C/rental-storefront-vr
標題：招租店舖與 VR 看屋
內容：金箍棒每個帳號或團隊都有自己的「房東對外首頁」（招租店舖），刊登中的物件會出現在上面供房客瀏覽；團隊可以在團隊管理設定招租頁面的專屬網址與時區，強化品牌辨識。 新增物件時可上傳 VR 物件連結，房客能在線上看屋。 想看招租頁長什麼樣可預約 demo。

### tmp:kb:1396
標題：社區公共設施有哪些
內容：請提供您的物件地址和想查詢的設施名稱，我將為您查詢詳細資訊。

### tmp:kb:2980
標題：公共區域使用權限
內容：租客在公共區域的使用權限通常包括進入、使用和享受公共設施，但不得妨礙其他租客的使用權。具體限制可能包括禁止在公共區域吸煙、存放個人物品或進行商業活動。請參考租約或聯繫您的管理師以獲取詳細資訊。

### tmp:kb:3011
標題：公益出租人減稅
內容：公益出租人減稅是針對將房屋出租給低收入戶或社會弱勢群體的房東，政府提供的稅收優惠。這意味著如果房東選擇這種出租方式，可能會享有減免稅款的權利，這樣可以降低租金，讓您作為租客享受到更優惠的租金條件。您可以詢問管理師，了解具體的減稅政策及如何影響您的租金。

### tmp:kb:3049
標題：公共設施使用權
內容：租客在公共設施中享有使用權利，包括合理使用設施的自由，以及在遵守社區規範下，享受設施提供的便利與服務。若有任何設施使用上的疑問或需要，請隨時聯繫管理師協助。

### tmp:kb:3050
標題：公共設施義務
內容：租客在公共設施中的使用義務包括遵守社區規範，不得損壞設施，並保持環境整潔。此外，租客需尊重其他使用者的權利，避免大聲喧嘩或其他影響公共安寧的行為。若發現設施故障或問題，請及時通知管理師進行維修。

### tmp:kb:3051
標題：洗衣機使用規範
內容：社區內的洗衣機使用規範通常包括按時清理洗衣槽、遵守使用時間、避免超載等。建議您查閱社區公告或聯繫您的管理師以獲取具體細節。

### tmp:kb:3052
標題：烘衣機使用規範
內容：社區內的烘衣機使用規範通常包括：使用前需清理烘衣機內部，並將衣物均勻放置以避免機器損壞；每次使用後請關閉電源，保持設施的整潔。此外，請遵守使用時間，避免佔用過長時間以便其他住戶使用。如需更詳細的規範，建議聯繫您的管理師確認。

### tmp:kb:3053
標題：垃圾分類規範
內容：社區內的垃圾分類規範通常分為可回收物、廚餘及一般垃圾，請依照社區公告的指示進行分類。可回收物需要清潔並分開放置，而廚餘則需放入專用容器中。建議您查看社區公告或詢問管理師以獲取具體的分類規範。

### tmp:kb:3054
標題：垃圾回收時間
內容：社區內的垃圾回收時間通常是每週二和每週五的早上7點。建議您在這之前將垃圾放置到指定位置，確保能夠順利回收。如有變更，請聯繫您的管理師確認。

### tmp:kb:3055
標題：大型廢棄物處理
內容：社區內的大型廢棄物處理通常會依照社區規定進行，可能會定期安排專門的清運服務。建議您向管理師查詢具體的處理時間和方式，也可以了解是否有特定的處理平台或指引。您的意見和需求也可以反映給管理師，以便改善服務。

### tmp:kb:3056
標題：公共設施開放時間
內容：社區內公共設施的開放時間通常為上午6點至晚上10點，但具體時間可能會因社區規定而有所不同。請提供您的物件地址，我幫您查詢更詳細的資訊。

### tmp:kb:3057
標題：公共設施損壞
內容：租客不需要對公共設施的損壞負責賠償，這類問題應由物業管理方負責處理。若發現公共設施損壞，建議您及時通知管理師進行維修。

### tmp:kb:3058
標題：公共設施使用
內容：社區內的公共設施使用時間通常會有一定的限制，具體使用時間請參考社區的管理規範或聯繫您的管理師以獲取詳細資訊。

### tmp:kb:3059
標題：公共設施使用費用
內容：社區內的公共設施一般來說是不需要額外支付費用的，這些設施的維護費用通常已包含在管理費中。不過，某些特定設施如健身房、游泳池等可能會有額外的使用費，建議您確認相關社區規定或聯繫管理師以獲取詳細資訊。

### tmp:kb:3060
標題：公共設施規範
內容：違反公共設施使用規則可能會導致警告、罰款或限制使用該設施的權利。這些措施旨在維護社區的良好秩序，因此建議您遵守相關規定，以避免不必要的處罰。

### tmp:kb:3061
標題：公共設施使用規範
內容：社區內公共設施的安全使用規範通常包括遵守使用時間、保持設施清潔、遵守人數限制以及不在設施內進行危險行為等。建議您查看社區公告或聯繫您的管理師以獲取具體的使用規範和要求。

### tmp:kb:3062
標題：公共設施爭議解決
內容：如果對公共設施的使用產生爭議，您可以首先與其他住戶進行溝通，尋求協商解決。如果無法達成共識，建議您聯繫您的管理師，讓他們協助調解和解決問題，並確保所有住戶的權益得到保障。

### tmp:kb:3063
標題：公共設施使用變更
內容：社區內公共設施的使用變更需要提前通知租客，這樣可以確保租客了解相關變更及可能影響。如果您有任何疑問或需要更詳細的信息，建議聯繫您的管理師確認具體情況。

### tmp:kb:3064
標題：公共設施保險
內容：社區內的公共設施通常需要投保責任保險，以保障所有住戶的安全和權益。這項保險能夠涵蓋意外事故造成的損害，為住戶提供必要的保障。如果您有任何具體的疑問或建議，建議您聯繫您的管理師確認相關的保險政策和條款。

### tmp:kb:3157
標題：社區活動
內容：我們的業者會不定期舉辦社區活動，這些活動旨在促進房客之間的交流與互動，增進社區的和諧氛圍。具體活動內容和時間，您可以向您的管理師詢問以獲取最新資訊。

### tmp:kb:3245
標題：公共設施使用義務
內容：租客在公共設施中有保持清潔、遵守使用時間、愛護設施的義務。此外，租客應遵循社區規範，避免喧鬧和損壞設施。如有問題或需進一步了解規範，建議聯繫您的管理師。

### tmp:kb:3246
標題：社區設施開放
內容：春節期間社區設施的開放情況可能會有所調整，具體時間請聯繫您的管理師確認。通常在假期期間，設施的開放時間會依照社區的規定進行調整，以確保所有住戶的安全與便利。

### tmp:kb:3247
標題：公共設施使用規則
內容：違反公共設施使用規則可能會受到管理方的警告或罰款，具體懲處方式會依照社區規範而定。作為房客，您有權了解規則及相關後果，並可向管理師詢問具體細節以保護您的權益。

### tmp:kb:3248
標題：公共設施安全規範
內容：社區內公共設施的安全使用規範通常包括遵循使用時間、保持設施清潔、避免攜帶危險物品、及遵守相關標示與指示。如需詳細規範，建議您聯繫您的管理師確認具體條款與規範。

### tmp:kb:3249
標題：公共設施爭議
內容：如果對公共設施的使用產生爭議，建議您首先與其他使用者進行溝通協調。如果問題無法解決，可以向您的管理師反映，並請求協助處理。管理師會根據社區規範及相關規定進行調查，並協助您尋找解決方案。

### tmp:kb:3263
標題：社會住宅社區服務
內容：社會住宅通常提供多種社區服務，包括社區活動、心理諮詢、健康檢查、法律諮詢及就業輔導等，旨在提升居住者的生活品質與社會融入。這些服務可能因不同住宅而異，建議您向管理師確認具體可用服務。

### tmp:kb:3299
標題：公共設施費用
內容：社區內的公共設施一般不需要額外支付費用，這些費用通常已包含在管理費中。不過，某些特定設施（如健身房、游泳池等）可能會有額外的使用費用，建議您查看社區規範或與管理師確認。 

### tmp:kb:3300
標題：公共設施投保
內容：社區內的公共設施通常是由管理單位負責投保責任保險，以保障使用者的安全和權益。您作為房客，使用這些設施時享有相應的安全保障。若有具體問題或需要更多資訊，建議您聯繫您的管理師確認細節。

### tmp:kb:3357
標題：物件 批次匯入 上傳
內容：系統支援物件批次匯入，由 JGB 協助提供批次匯入表格。

注意事項：
- 檔案格式須為 .xls（非 .xlsx）
- 若上傳失敗，建議重新下載範本檔案，將資料複製後用 Ctrl+Shift+V（純文字貼上）方式貼入，避免格式異常
- 上傳成功後按重新整理，約 3 秒內會顯示

### tmp:kb:3358
標題：大房東 邀請 授權 物件
內容：大房東功能操作說明：
- 邀請大房東：在大房東列表中新增，輸入大房東的 email（注意大小寫需完全正確）
- 授權物件：可將特定物件授權給大房東查看
- 列表管理：在團隊設定中管理大房東列表

常見問題：邀請失敗通常是 email 大小寫不正確造成的。

### tmp:kb:3428
標題：物件狀態 定義條件
內容：物件狀態要分兩條獨立軸來看。合約軸四狀態：（1）未刊登：物件剛建立；（2）刊登中；（3）洽談中：已綁定合約但尚未完成簽署；（4）租約中：合約已簽署生效。狀態隨合約流程推進——建立合約後進洽談中、簽署完成進租約中。刊登軸（是否對外刊登公開）獨立於合約軸——租約中的物件也可以同時在刊登中（例如租約快到期先開放招租）。兩軸不要混為一談：看「能不能建約」是刊登與必填欄位的問題；看「有沒有出租」才是合約軸的問題。

### tmp:kb:3429
標題：物件刊登 上架條件
內容：物件刊登（上架）需滿足以下條件：1. 帳號已訂閱方案（未訂閱無法刊登）；2. 已刊登物件數未達方案上限；3. 必填欄位已填寫完整，包含：物件名稱、租金、押金、坪數、樓層。滿足條件後即可上架公開，物件會出現在搜尋結果中。若刊登後修改資料導致必填欄位不完整，系統會自動下架該物件。

### tmp:kb:3430
標題：物件下架 條件流程
內容：物件下架有兩種情況：（1）手動下架：管理者主動將物件從公開列表移除，需具備物件管理或刊登權限；（2）自動下架：修改物件資料後，若必填欄位（名稱、租金、押金、坪數、樓層）驗證失敗，系統會自動下架。下架後物件不會出現在搜尋結果中，但資料保留，可隨時重新上架。已綁定合約的物件建議先處理完合約再下架。

### tmp:kb:3431
標題：物件批次匯入 Excel 建立
內容：大量建立物件可使用 Excel 批次匯入功能：1. 在物件管理頁面選擇「批次匯入」；2. 下載匯入範本（一般物件範本或社宅物件範本）；3. 依範本格式填寫物件資料（名稱、地址、坪數、樓層、租金等）；4. 上傳完成的 Excel 檔案；5. 系統驗證並批次建立物件。匯入成功後物件預設為「未刊登」狀態，需確認資料無誤後再手動上架。社宅物件有專屬範本，包含額外的社宅專用欄位。

### tmp:kb:3433
標題：物件 VR 虛擬導覽
內容：JGB 物件頁支援 VR 虛擬導覽（整合 iStaging 服務）：在物件編輯頁的 VR 導覽區綁定後，物件公開頁會顯示 VR 看屋入口，瀏覽者可在網頁直接觀看 360 度全景。VR 裝置申請、拍攝方式、marker 操作與費用等屬 iStaging 廠商服務範圍，請直接洽 iStaging，或聯繫客服協助轉介。

### tmp:kb:3434
標題：物件自訂標籤 分類管理
內容：自訂標籤功能讓房東可以為物件加上自訂分類標記，方便搜尋和管理。例如可建立「寵物友善」、「近捷運」、「含家具」等標籤。操作方式：在帳號設定的「自訂標籤」頁面新增標籤，然後在物件編輯時勾選適用的標籤。物件列表支援依標籤篩選，快速找到符合條件的物件。標籤也會顯示在物件的公開頁面上，幫助租客篩選。

### tmp:kb:3456
標題：物件數量上限 額度不足
內容：每個訂閱方案都有物件管理數量上限。當物件數接近上限時，系統會發送提醒通知。若已達上限，將無法新增或刊登更多物件。解決方式：（1）升級至更高等級方案以獲得更多額度；（2）加購額外物件額度；（3）刪除或下架不再使用的物件以釋放額度。可在「訂閱方案」頁面查看目前已使用和剩餘的物件額度。

### tmp:kb:3468
標題：社區管理 建立編輯
內容：社區管理功能讓物管/房東集中管理同一社區或大樓的物件。建立社區步驟：1. 進入社區管理頁面，點選新增社區；2. 填寫基本資訊（社區名稱、地址、介紹、交通資訊）；3. 上傳社區照片；4. 儲存即完成建立。建立後可將物件歸屬至該社區下進行統一管理。也支援批次匯入方式一次建立多個社區。編輯社區時可更新基本資料、照片和公開顯示設定。

### tmp:kb:3469
標題：社區與物件關係 綁定
內容：社區與物件為一對多的關係：一個社區可包含多個物件，每個物件可歸屬於一個社區。物件歸屬社區後，可在社區頁面統一查看該社區下的所有物件清單。社區也支援設定「公共區域」物件（如公共設施、會議室等）。在某些配置下（如社宅方案），系統會要求強制綁定社區，引導使用者在操作前先完成社區設定。

### tmp:kb:3470
標題：社區公開頁面 廣告展示
內容：社區公開頁面是對外展示社區資訊的頁面，不需登入即可瀏覽。頁面內容包含社區介紹、照片、地理位置和公開刊登中的物件列表。此頁面可作為招租的行銷工具，將連結分享給有意租屋的人瀏覽社區和可租物件。房東也有專屬的招租店鋪頁面，展示其所有公開物件。頁面顯示的內容會隨物件刊登狀態即時更新。

### tmp:kb:3505
標題：為什麼不能新增物件
內容：無法新增物件最常見兩個原因：（1）訂閱方案的物件額度已滿——系統會提示方案已滿，可升級方案、加購物件額度，或刪除/下架不再使用的物件釋放額度；目前用量可在「訂閱方案」頁查看。（2）帳號權限不足——新增物件需要對應的物件管理權限，請團隊管理者確認你的角色權限設定。

### tmp:kb:3506
標題：物件為什麼突然全部下架
內容：物件突然全部下架，最常見的原因是訂閱續約扣款失敗——方案失效時系統會將物件自動下架。請到「訂閱方案」頁確認方案狀態與付款方式，完成續約後再將物件重新上架。若方案正常但個別物件被下架，多半是修改資料後必填欄位驗證失敗導致自動下架，補齊欄位後重新刊登即可。

### tmp:kb:3973
標題：成員看不到社區物件 無法新增
內容：把成員加進團隊後，對方卻看不到社區或物件、也無法新增，最常見的原因是：加入後還沒有指派角色——沒有角色的成員沒有任何權限。請到成員列表對該成員「變更角色」，指派後權限立即生效。若已指派角色仍看不到特定物件，確認該角色的可見範圍：部分角色只能看到「自己被指派為經理人」的物件，需要在物件上把該成員設為經理人；新增社區、新增合約則各需要對應的編輯權限，確認角色有開啟。

### tmp:kb:4145
標題：對外顯示地址 沒生效 還是完整地址
內容：「對外顯示地址」只作用在物件的對外廣告頁與地圖顯示——業者自己的後台介面永遠顯示完整地址，這不是設定沒生效。要確認效果，請打開物件的對外廣告頁（或招租店舖頁）查看：租客與外部訪客看到的就是對外顯示地址的版本。

### tmp:kb:4146
標題：招租店舖 房東對外首頁 入口 分享
內容：招租店舖（房東對外首頁）會公開展示團隊所有「刊登中」的物件，網址是 /p/ 開頭的專屬連結，可設定自訂帳號名稱讓網址更好記。入口：登入後台後由側邊選單即可連到自己的店舖頁；店舖的封面照片、大頭照、自我介紹與「會員中心→帳號資訊」連動，改一處兩邊都會更新。把店舖連結分享到 FB、LINE 就是現成的招租頁。注意：非刊登中的物件不會出現在店舖，其廣告頁連結分享給別人也看不到內容。

### tmp:kb:4147
標題：編輯物件 刊登物件 差異 儲存
內容：「編輯物件」是修改內容但不會上架，「刊登物件」才會把物件上架公開——兩個是不同動作。編輯後務必按「儲存」再離開頁面：直接切換頁面不會自動儲存，修改的內容會遺失（客服常見案例：取消勾選設備後直接點回列表，結果沒存到）。另外，任何狀態的物件都可以編輯，修改不會影響既有合約——合約簽訂當下已把物件資料快照保存。

### tmp:kb:4151
標題：物件要怎麼刊登 上架流程
內容：

### tmp:kb:4152
標題：改了對外顯示地址 怎麼還是顯示完整地址
內容：

### tmp:kb:4154
標題：這個物件現在什麼狀態 租客看得到嗎
內容：

### tmp:kb:4262
標題：社區設施 公共設施 健身房 交誼廳
內容：

### tmp:kb:4272
標題：管理員會代收包裹嗎
內容：

### tmp:kb:4276
標題：社區有哪些公共設施可以用
內容：

### tmp:kb:4648
標題：即時物件出租率 百分比怎麼算 已出租數字來源
內容：首頁「即時物件出租率」的已出租數字，是以「合約中的物件總數量 ÷ 物件總數」計算出來的百分比，會隨合約綁定的物件數量即時變動。

### tmp:draft:1
標題：物件批次新增表格如何填寫？
內容：物件批次新增表格如何填寫？ 在物件管理的社區總表中，按下右上方新增物件旁的三角形，選擇「批次新增」，並且下載特定格式 Excel 進行填寫，因程式上已有設定好的格式，請依照指定格式填寫完成。 下拉選單請用選單中選項：用途、建築類型、地址（國家）、朝向方向、最短租期、產權登記。 自行填寫選項：物件標題、地址（縣市、區）、樓層房間、平方單位、社區/大樓、屋齡、租金、押金、入住日期、交通、房源簡介、生活公約、廣告法定用途。 金額欄位請選擇「通用格式」，勿選擇「貨幣格式」。 圖 1 批次新增 圖 2 下載 Excel 表格 圖 3 填寫表格 圖 4 選擇選單中的選項 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:2
標題：進階搜尋功能如何用?
內容：進階搜尋功能如何用? 除了一般的關鍵字搜尋之外，也可以將「空間類型」、「社區大樓」、「租金範圍」、「坪數」做為篩選工具。 圖 1 操作畫面 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。


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
    "id": "jgb/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼（含自訂狀態標籤）",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:canon:jgb/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "潛在客戶問「房源管理能做什麼」的總覽入口；操作型問題（標籤怎麼建、怎麼匯入）各自成細目，不併入總覽。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/community-batch-create",
    "coarse_id": "C",
    "title": "社區建立與批次新增物件",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:canon:jgb/C/community-batch-create"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "潛在客戶問「物件多能不能一次建、能不能按社區歸戶」的總覽入口；業者的逐步操作與填表注意事項另成 community-create-edit 與 property-batch-import，層級不同以另見處理。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:canon:jgb/C/property-status-meaning",
     "tmp:kb:3428",
     "tmp:kb:4154"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「這個物件現在什麼狀態、租客看不看得到」是同一個問題；3428 的兩軸定義是既有細目的同命題補強，4154 為空內文入口只當講法吸收。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖與 VR 看屋",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:canon:jgb/C/rental-storefront-vr"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "潛在客戶問「有沒有對外招租頁、能不能線上看屋」的總覽入口；業者問入口在哪、怎麼分享、VR 怎麼綁各是不同問題，另成細目。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/community-create-edit",
    "coarse_id": "C",
    "title": "社區怎麼建立、編輯，物件怎麼歸屬社區",
    "slug": "community-create-edit",
    "merge_of": [
     "tmp:kb:3468",
     "tmp:kb:3469"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者問「社區怎麼建／改、物件怎麼掛到社區下、公共區域物件、社宅為何強制綁社區」為一組可獨立回答的操作問題，與批次匯入分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-batch-import",
    "coarse_id": "C",
    "title": "物件批次匯入：範本、表格填寫與上傳失敗",
    "slug": "property-batch-import",
    "merge_of": [
     "tmp:kb:3431",
     "tmp:kb:3357",
     "tmp:draft:1"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者問「批次匯入怎麼做、表格怎麼填、為什麼上傳失敗、匯入後為何未刊登」落在同一路徑；三份來源分別是步驟、.xls 與貼上注意事項、欄位填法，合為一題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-listing-conditions",
    "coarse_id": "C",
    "title": "物件要怎麼刊登上架、刊登需要什麼條件",
    "slug": "property-listing-conditions",
    "merge_of": [
     "tmp:kb:3429",
     "tmp:kb:4151"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「怎麼刊登」與「為什麼不能刊登」是同一問題的正反兩面（方案、額度、必填欄位）；4151 為空內文入口只當講法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-unlisting-reasons",
    "coarse_id": "C",
    "title": "物件怎麼下架、為什麼被自動下架",
    "slug": "property-unlisting-reasons",
    "merge_of": [
     "tmp:kb:3430",
     "tmp:kb:3506"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者問「怎麼手動下架」與「物件為什麼突然全部下架」都以下架為起點；3506 根因在方案續約失敗，但提問落在物件狀態，留在本架並另見方案架。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-edit-vs-publish",
    "coarse_id": "C",
    "title": "編輯物件與刊登物件差在哪、為什麼修改沒存到",
    "slug": "property-edit-vs-publish",
    "merge_of": [
     "tmp:kb:4147"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「我改了物件怎麼沒生效／沒存到」是獨立於刊登條件的問題：答案是編輯≠刊登、要按儲存、改物件不影響既有合約。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-add-blocked",
    "coarse_id": "C",
    "title": "為什麼不能新增物件",
    "slug": "property-add-blocked",
    "merge_of": [
     "tmp:kb:3505"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者的提問以「新增物件按不了」為起點，本細目只做排查入口（額度滿→另見方案架、權限不足→另見團隊架），不在本架展開額度與角色機制。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/public-display-address",
    "coarse_id": "C",
    "title": "對外顯示地址改了為什麼後台還是完整地址",
    "slug": "public-display-address",
    "merge_of": [
     "tmp:kb:4145",
     "tmp:kb:4152"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "同一個誤解（以為設定沒生效）對應同一答案（只作用於對外廣告頁與地圖）；4152 為空內文入口只當講法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/storefront-entry-share",
    "coarse_id": "C",
    "title": "招租店舖入口在哪、怎麼分享、為什麼物件沒出現",
    "slug": "storefront-entry-share",
    "merge_of": [
     "tmp:kb:4146"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者的操作問題（入口、/p/ 網址、與帳號資訊連動、非刊登中不顯示）與潛在客戶的「有沒有招租頁」總覽是不同層級，另成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-public-page",
    "coarse_id": "C",
    "title": "社區公開頁面是什麼、能拿來做什麼",
    "slug": "community-public-page",
    "merge_of": [
     "tmp:kb:3470"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「社區公開頁」與「招租店舖」是兩個不同的對外頁面，使用者會分開問；本細目只答社區頁，店舖另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-vr-tour",
    "coarse_id": "C",
    "title": "物件 VR 虛擬導覽怎麼綁、費用與拍攝找誰",
    "slug": "property-vr-tour",
    "merge_of": [
     "tmp:kb:3433"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "業者問「VR 怎麼設定、拍攝／費用找誰」是操作與廠商分工問題，與招租店舖總覽層級不同，獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-custom-tags",
    "coarse_id": "C",
    "title": "物件自訂標籤怎麼建、怎麼用來篩選",
    "slug": "property-custom-tags",
    "merge_of": [
     "tmp:kb:3434"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「標籤在哪建、怎麼掛到物件、能不能篩選、租客看不看得到」是一組操作問題，與房源管理總覽分層。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-advanced-search",
    "coarse_id": "C",
    "title": "物件列表進階搜尋怎麼用",
    "slug": "property-advanced-search",
    "merge_of": [
     "tmp:draft:2"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「物件太多怎麼篩」是獨立的操作問題（空間類型、社區大樓、租金範圍、坪數），與標籤篩選是不同機制，各自一題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/occupancy-rate-calculation",
    "coarse_id": "C",
    "title": "首頁即時物件出租率怎麼算、已出租數字從哪來",
    "slug": "occupancy-rate-calculation",
    "merge_of": [
     "tmp:kb:4648"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「出租率百分比怎麼算」是獨立問題，答案依物件狀態（合約中 ÷ 物件總數）計算，屬物件層統計，另見物件狀態細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/C/property-management-overview",
    "new": "jgb/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/C/community-batch-create",
    "new": "jgb/C/community-batch-create",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/C/property-status-meaning",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3428",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4154",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/rental-storefront-vr",
    "new": "jgb/C/rental-storefront-vr",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3468",
    "new": "jgb/C/community-create-edit",
    "op": "new"
   },
   {
    "old": "tmp:kb:3469",
    "new": "jgb/C/community-create-edit",
    "op": "new"
   },
   {
    "old": "tmp:kb:3431",
    "new": "jgb/C/property-batch-import",
    "op": "new"
   },
   {
    "old": "tmp:kb:3357",
    "new": "jgb/C/property-batch-import",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/C/property-batch-import",
    "op": "new"
   },
   {
    "old": "tmp:kb:3429",
    "new": "jgb/C/property-listing-conditions",
    "op": "new"
   },
   {
    "old": "tmp:kb:4151",
    "new": "jgb/C/property-listing-conditions",
    "op": "new"
   },
   {
    "old": "tmp:kb:3430",
    "new": "jgb/C/property-unlisting-reasons",
    "op": "new"
   },
   {
    "old": "tmp:kb:3506",
    "new": "jgb/C/property-unlisting-reasons",
    "op": "new"
   },
   {
    "old": "tmp:kb:4147",
    "new": "jgb/C/property-edit-vs-publish",
    "op": "new"
   },
   {
    "old": "tmp:kb:3505",
    "new": "jgb/C/property-add-blocked",
    "op": "new"
   },
   {
    "old": "tmp:kb:4145",
    "new": "jgb/C/public-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:4152",
    "new": "jgb/C/public-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:4146",
    "new": "jgb/C/storefront-entry-share",
    "op": "new"
   },
   {
    "old": "tmp:kb:3470",
    "new": "jgb/C/community-public-page",
    "op": "new"
   },
   {
    "old": "tmp:kb:3433",
    "new": "jgb/C/property-vr-tour",
    "op": "new"
   },
   {
    "old": "tmp:kb:3434",
    "new": "jgb/C/property-custom-tags",
    "op": "new"
   },
   {
    "old": "tmp:draft:2",
    "new": "jgb/C/property-advanced-search",
    "op": "new"
   },
   {
    "old": "tmp:kb:4648",
    "new": "jgb/C/occupancy-rate-calculation",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:1396",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:2980",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3011",
    "suggested_shelf": "-",
    "why": "租客受眾內容（「讓您作為租客享受到更優惠的租金」），主題是公益出租人稅賦，既非社區也非物件屬性；A–I 皆為 jgb 受眾且無稅務架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3049",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3050",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3051",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3052",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3053",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3054",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3055",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3056",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3057",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3058",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3059",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3060",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3061",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3062",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3063",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3064",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3157",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3245",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3246",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3247",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3248",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3249",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3263",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3299",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3300",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:4262",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:4272",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:4276",
    "suggested_shelf": "-",
    "why": "租客受眾內容（稱呼「您作為租客」、導向「您的管理師」），jgb 受眾 prospect／property_manager 不會這樣問；主題雖屬社區域，但 A–I 九架皆為 jgb 受眾，無可歸之架，應交租客受眾正本處理。"
   },
   {
    "id": "tmp:kb:3358",
    "suggested_shelf": "B",
    "why": "問的是「大房東怎麼邀請、怎麼授權物件看」，命題落在大房東帳號與授權，B 架標題即含大房東；物件只是被授權的客體。"
   },
   {
    "id": "tmp:kb:3973",
    "suggested_shelf": "B",
    "why": "「成員看不到社區／物件、無法新增」的答案全在角色指派與可見範圍，命題屬團隊成員權限；物件只是症狀所在。"
   },
   {
    "id": "tmp:kb:3456",
    "suggested_shelf": "I",
    "why": "「物件數量上限、額度不足怎麼辦」的答案是訂閱方案額度、升級、加購與用量查詢，命題屬方案；C 架僅以 property-add-blocked 做排查入口另見。"
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
    "id": "jgb/C/community-batch-create",
    "coarse_id": "C",
    "title": "批次新增物件（Excel 範本下載、填寫與上傳）",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:canon:jgb/C/community-batch-create",
     "tmp:kb:3357",
     "tmp:kb:3431",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:canon:jgb/C/community-batch-create"
    ],
    "moved_from": [],
    "reason": "既有細目把「建立社區」與「批次新增物件」寫成一段，但範本下載／欄位填法／xls 格式／上傳失敗處置各自完整且不依賴社區設定即可回答，故拆出批次匯入獨立成立；kb 3357、3431 與 draft:1 皆為同一主題的操作細節，併入此細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/C/community-create-and-binding",
    "coarse_id": "C",
    "title": "社區建立與編輯、社區與物件的歸屬關係",
    "slug": "community-create-and-binding",
    "merge_of": [
     "tmp:canon:jgb/C/community-batch-create",
     "tmp:kb:3468",
     "tmp:kb:3469"
    ],
    "split_from": [
     "tmp:canon:jgb/C/community-batch-create"
    ],
    "moved_from": [],
    "reason": "社區的建立步驟、編輯、一對多歸屬、公共區域物件與社宅強制綁定是彼此依賴才完整的一組內容，與批次匯入的範本操作主題不同，故自既有細目拆出並吸收 kb 3468、3469。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼（含自訂狀態標籤）",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:canon:jgb/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "模組層級的總覽，內容為各功能的摘要與 demo 引導，與各功能操作細目屬不同層級，以另見處理而非合併；自訂標籤的操作細節另立細目。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態（未刊登／刊登中／洽談中／合約中）與刊登軸、合約軸",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:canon:jgb/C/property-status-meaning",
     "tmp:kb:3428",
     "tmp:kb:4154"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "kb 3428 的兩軸定義與既有細目為同一命題的不同寫法，互相補足才完整；kb 4154 為空內文入口（這個物件現在什麼狀態／租客看得到嗎），歸入同一細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖（房東對外首頁）：入口、網址、分享與顯示範圍",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:canon:jgb/C/rental-storefront-vr",
     "tmp:kb:4146"
    ],
    "split_from": [
     "tmp:canon:jgb/C/rental-storefront-vr"
    ],
    "moved_from": [],
    "reason": "既有細目把招租店舖與 VR 看屋寫在一起，但店舖是團隊層級的公開頁（網址、入口、分享、只顯示刊登中物件），VR 是單一物件的導覽綁定，各自完整且主題不同，故拆開；店舖部分保留原 id 並吸收 kb 4146。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/C/property-vr-tour",
    "coarse_id": "C",
    "title": "物件 VR 虛擬導覽（iStaging 綁定與廠商服務範圍）",
    "slug": "property-vr-tour",
    "merge_of": [
     "tmp:canon:jgb/C/rental-storefront-vr",
     "tmp:kb:3433"
    ],
    "split_from": [
     "tmp:canon:jgb/C/rental-storefront-vr"
    ],
    "moved_from": [],
    "reason": "VR 導覽的綁定位置、公開頁顯示與廠商服務邊界不依賴招租店舖即可獨立回答，故自既有細目拆出，以 kb 3433 為主體。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/C/community-public-page",
    "coarse_id": "C",
    "title": "社區公開頁面（對外展示社區與刊登中物件）",
    "slug": "community-public-page",
    "merge_of": [
     "tmp:kb:3470"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區公開頁是社區層級的對外頁面，內容（免登入、社區介紹、該社區刊登中物件）與團隊層級的招租店舖是不同物件的不同頁面，各自完整，故獨立成細目；與招租店舖互為另見。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-display-address",
    "coarse_id": "C",
    "title": "對外顯示地址：作用範圍與為何後台仍顯示完整地址",
    "slug": "property-display-address",
    "merge_of": [
     "tmp:kb:4145",
     "tmp:kb:4152"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對外顯示地址是物件本身的屬性設定，作用範圍（廣告頁／地圖）與後台顯示差異可獨立回答；kb 4152 為同題的空內文入口，一併歸入。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-listing-conditions",
    "coarse_id": "C",
    "title": "物件刊登（上架）條件與流程",
    "slug": "property-listing-conditions",
    "merge_of": [
     "tmp:kb:3429",
     "tmp:kb:4151"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "上架的三項前提（訂閱、額度、必填欄位）與上架後效果構成一個完整命題；kb 4151 為空內文入口，歸入此細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-unlisting",
    "coarse_id": "C",
    "title": "物件下架：手動下架、自動下架與突然全部下架的原因",
    "slug": "property-unlisting",
    "merge_of": [
     "tmp:kb:3430",
     "tmp:kb:3506"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "kb 3430 的下架兩種情況與 kb 3506 的「突然全部下架」排查共用同一機制（必填欄位驗證失敗自動下架），拆開會各自不完整，故合為一個主題；方案失效導致下架僅作為原因列出，方案本身另見 I。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-edit-vs-publish",
    "coarse_id": "C",
    "title": "編輯物件與刊登物件的差異、儲存行為與對既有合約的影響",
    "slug": "property-edit-vs-publish",
    "merge_of": [
     "tmp:kb:4147"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "編輯不等於刊登、離頁不自動儲存、編輯不影響已簽合約三點圍繞「編輯物件」這一個動作，彼此依賴才完整，與刊登條件分屬不同主題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-custom-tags",
    "coarse_id": "C",
    "title": "物件自訂標籤：建立、勾選、篩選與公開頁顯示",
    "slug": "property-custom-tags",
    "merge_of": [
     "tmp:kb:3434"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "自訂標籤的操作流程可獨立回答，與模組總覽中的一句摘要屬不同層級，故獨立成細目並與總覽互為另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-advanced-search",
    "coarse_id": "C",
    "title": "物件列表進階搜尋與篩選",
    "slug": "property-advanced-search",
    "merge_of": [
     "tmp:draft:2"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "進階搜尋的篩選條件（空間類型、社區大樓、租金範圍、坪數）是物件列表的獨立操作，不依賴其他細目即可回答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-cannot-create",
    "coarse_id": "C",
    "title": "為什麼不能新增物件（額度已滿或權限不足）",
    "slug": "property-cannot-create",
    "merge_of": [
     "tmp:kb:3505"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "症狀落在新增物件這個動作，兩個原因並列才是完整答案，故獨立成排查細目；額度細節另見 I、角色權限另見 B。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/occupancy-rate-metric",
    "coarse_id": "C",
    "title": "首頁即時物件出租率的計算方式",
    "slug": "occupancy-rate-metric",
    "merge_of": [
     "tmp:kb:4648"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "出租率是以物件狀態（合約中）計數得到的物件層級指標，計算公式可獨立回答，與狀態定義細目互為另見而非合併。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-facilities-and-hours",
    "coarse_id": "C",
    "title": "社區有哪些公共設施、開放時間與使用變更通知",
    "slug": "community-facilities-and-hours",
    "merge_of": [
     "tmp:kb:1396",
     "tmp:kb:4262",
     "tmp:kb:4276",
     "tmp:kb:3056",
     "tmp:kb:3058",
     "tmp:kb:3246",
     "tmp:kb:3063"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「有哪些設施」與「何時可用」（含假期調整、變更需通知）互相依賴才是完整答案，屬同一主題；kb 1396、4262、4276 為空內文或僅為查詢入口，不獨立成細目。內容為租客視角，本受眾對應訂定社區規範的 property_manager。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-facility-usage-rules",
    "coarse_id": "C",
    "title": "公共設施使用規範：權利、義務、安全規範與違規後果",
    "slug": "community-facility-usage-rules",
    "merge_of": [
     "tmp:kb:2980",
     "tmp:kb:3049",
     "tmp:kb:3050",
     "tmp:kb:3245",
     "tmp:kb:3061",
     "tmp:kb:3248",
     "tmp:kb:3060",
     "tmp:kb:3247"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權利、義務、安全規範與違規後果是同一套使用規範的四個面向，拆開任一面向都不完整；多筆 kb 為同題重複寫法，併為一個細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-laundry-rules",
    "coarse_id": "C",
    "title": "社區洗衣機與烘衣機使用規範",
    "slug": "community-laundry-rules",
    "merge_of": [
     "tmp:kb:3051",
     "tmp:kb:3052"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "洗衣機與烘衣機是同一組共用設備的具體規範，內容自成一題，與通用使用規範屬不同層級，故獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-garbage-disposal",
    "coarse_id": "C",
    "title": "社區垃圾分類、回收時間與大型廢棄物處理",
    "slug": "community-garbage-disposal",
    "merge_of": [
     "tmp:kb:3053",
     "tmp:kb:3054",
     "tmp:kb:3055"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "分類方式、回收時間與大型廢棄物是同一個「垃圾怎麼丟」主題的三個必要部分，合為一細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-facility-disputes",
    "coarse_id": "C",
    "title": "公共設施使用爭議的處理流程",
    "slug": "community-facility-disputes",
    "merge_of": [
     "tmp:kb:3062",
     "tmp:kb:3249"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "爭議處理是規範之外的另一個流程（先協商、再由管理師調解），可獨立回答，故不併入使用規範；兩筆 kb 為同題重複寫法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-facility-insurance",
    "coarse_id": "C",
    "title": "公共設施責任保險",
    "slug": "community-facility-insurance",
    "merge_of": [
     "tmp:kb:3064",
     "tmp:kb:3300"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "設施是否投保及保障範圍是社區設施本身的屬性，內容獨立完整；兩筆 kb 為同題重複寫法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-services-and-events",
    "coarse_id": "C",
    "title": "社區服務與活動（活動、包裹代收、社宅社區服務）",
    "slug": "community-services-and-events",
    "merge_of": [
     "tmp:kb:3157",
     "tmp:kb:3263",
     "tmp:kb:4272"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區提供的非設施類服務（活動、社宅服務、包裹代收）性質相同、彼此不重疊，合為一個主題；kb 4272 為空內文入口，不獨立成細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/C/community-batch-create",
    "new": "jgb/C/community-batch-create",
    "op": "split"
   },
   {
    "old": "tmp:kb:3357",
    "new": "jgb/C/community-batch-create",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3431",
    "new": "jgb/C/community-batch-create",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/C/community-batch-create",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/community-batch-create",
    "new": "jgb/C/community-create-and-binding",
    "op": "split"
   },
   {
    "old": "tmp:kb:3468",
    "new": "jgb/C/community-create-and-binding",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3469",
    "new": "jgb/C/community-create-and-binding",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/property-management-overview",
    "new": "jgb/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/C/property-status-meaning",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3428",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4154",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/rental-storefront-vr",
    "new": "jgb/C/rental-storefront-vr",
    "op": "split"
   },
   {
    "old": "tmp:kb:4146",
    "new": "jgb/C/rental-storefront-vr",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/rental-storefront-vr",
    "new": "jgb/C/property-vr-tour",
    "op": "split"
   },
   {
    "old": "tmp:kb:3433",
    "new": "jgb/C/property-vr-tour",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3470",
    "new": "jgb/C/community-public-page",
    "op": "new"
   },
   {
    "old": "tmp:kb:4145",
    "new": "jgb/C/property-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:4152",
    "new": "jgb/C/property-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:3429",
    "new": "jgb/C/property-listing-conditions",
    "op": "new"
   },
   {
    "old": "tmp:kb:4151",
    "new": "jgb/C/property-listing-conditions",
    "op": "new"
   },
   {
    "old": "tmp:kb:3430",
    "new": "jgb/C/property-unlisting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3506",
    "new": "jgb/C/property-unlisting",
    "op": "new"
   },
   {
    "old": "tmp:kb:4147",
    "new": "jgb/C/property-edit-vs-publish",
    "op": "new"
   },
   {
    "old": "tmp:kb:3434",
    "new": "jgb/C/property-custom-tags",
    "op": "new"
   },
   {
    "old": "tmp:draft:2",
    "new": "jgb/C/property-advanced-search",
    "op": "new"
   },
   {
    "old": "tmp:kb:3505",
    "new": "jgb/C/property-cannot-create",
    "op": "new"
   },
   {
    "old": "tmp:kb:4648",
    "new": "jgb/C/occupancy-rate-metric",
    "op": "new"
   },
   {
    "old": "tmp:kb:1396",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:4262",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:4276",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:3056",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:3058",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:3246",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:3063",
    "new": "jgb/C/community-facilities-and-hours",
    "op": "new"
   },
   {
    "old": "tmp:kb:2980",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3049",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3050",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3245",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3061",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3248",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3060",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3247",
    "new": "jgb/C/community-facility-usage-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3051",
    "new": "jgb/C/community-laundry-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3052",
    "new": "jgb/C/community-laundry-rules",
    "op": "new"
   },
   {
    "old": "tmp:kb:3053",
    "new": "jgb/C/community-garbage-disposal",
    "op": "new"
   },
   {
    "old": "tmp:kb:3054",
    "new": "jgb/C/community-garbage-disposal",
    "op": "new"
   },
   {
    "old": "tmp:kb:3055",
    "new": "jgb/C/community-garbage-disposal",
    "op": "new"
   },
   {
    "old": "tmp:kb:3062",
    "new": "jgb/C/community-facility-disputes",
    "op": "new"
   },
   {
    "old": "tmp:kb:3249",
    "new": "jgb/C/community-facility-disputes",
    "op": "new"
   },
   {
    "old": "tmp:kb:3064",
    "new": "jgb/C/community-facility-insurance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3300",
    "new": "jgb/C/community-facility-insurance",
    "op": "new"
   },
   {
    "old": "tmp:kb:3157",
    "new": "jgb/C/community-services-and-events",
    "op": "new"
   },
   {
    "old": "tmp:kb:3263",
    "new": "jgb/C/community-services-and-events",
    "op": "new"
   },
   {
    "old": "tmp:kb:4272",
    "new": "jgb/C/community-services-and-events",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3011",
    "suggested_shelf": "E",
    "why": "公益出租人減稅是房東稅務與租金計算的命題，錢怎麼算歸帳務，與社區或物件屬性無關。"
   },
   {
    "id": "tmp:kb:3057",
    "suggested_shelf": "F",
    "why": "公共設施損壞的責任歸屬與通知維修屬修繕領域，不是社區設施本身的屬性。"
   },
   {
    "id": "tmp:kb:3059",
    "suggested_shelf": "E",
    "why": "公共設施是否額外收費、是否含在管理費中屬費用計算，依歸位判準歸帳務。"
   },
   {
    "id": "tmp:kb:3299",
    "suggested_shelf": "E",
    "why": "與 kb 3059 同題（設施費用是否含在管理費），同歸帳務。"
   },
   {
    "id": "tmp:kb:3358",
    "suggested_shelf": "B",
    "why": "大房東邀請與物件授權是大房東人員管理的操作，歸團隊、人員與大房東。"
   },
   {
    "id": "tmp:kb:3973",
    "suggested_shelf": "B",
    "why": "成員看不到社區物件的根因是角色權限未指派或可見範圍設定，屬人員與角色管理。"
   },
   {
    "id": "tmp:kb:3456",
    "suggested_shelf": "I",
    "why": "物件數量上限由訂閱方案額度決定，升級／加購／查看額度皆在方案頁，歸方案與導入。"
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
    "id": "jgb/C/community-batch-create",
    "coarse_id": "C",
    "title": "社區建立與批次新增物件",
    "slug": "community-batch-create",
    "merge_of": [
     "tmp:canon:jgb/C/community-batch-create"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目為 prospect 能力層級（社區歸戶＋批次新增能不能做）；同主題的業者操作層級另立 property-batch-import-howto 與 community-setup-and-property-binding，互為另見。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/property-management-overview",
    "coarse_id": "C",
    "title": "房源管理模組做什麼（含自訂狀態標籤）",
    "slug": "property-management-overview",
    "merge_of": [
     "tmp:canon:jgb/C/property-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目為 prospect 能力層級總覽；自訂標籤的操作層級另立 property-custom-tags-howto 作另見，不併入以免混層。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/property-status-meaning",
    "coarse_id": "C",
    "title": "物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思",
    "slug": "property-status-meaning",
    "merge_of": [
     "tmp:canon:jgb/C/property-status-meaning",
     "tmp:kb:3428",
     "tmp:kb:4154"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "3428 與既有細目同命題同層級（四狀態＋刊登／合約兩軸），答案不因受眾而異故兩受眾共用；4154 為空內文入口（租客看不看得到＝刊登軸）併入不獨立。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/C/rental-storefront-vr",
    "coarse_id": "C",
    "title": "招租店舖與 VR 看屋",
    "slug": "rental-storefront-vr",
    "merge_of": [
     "tmp:canon:jgb/C/rental-storefront-vr"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目為 prospect 能力層級（有沒有招租頁與 VR）；業者操作層級拆為 storefront-and-community-page-sharing 與 property-vr-binding 作另見。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/C/property-batch-import-howto",
    "coarse_id": "C",
    "title": "物件批次匯入表格怎麼填、怎麼上傳",
    "slug": "property-batch-import-howto",
    "merge_of": [
     "tmp:kb:3357",
     "tmp:kb:3431",
     "tmp:draft:1"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆皆為業者操作層級的批次匯入步驟與表格填寫規則（.xls、純文字貼上、範本欄位、匯入後為未刊登），與 prospect 能力層級的 community-batch-create 分層另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-setup-and-property-binding",
    "coarse_id": "C",
    "title": "社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定）",
    "slug": "community-setup-and-property-binding",
    "merge_of": [
     "tmp:kb:3468",
     "tmp:kb:3469"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區建檔步驟與社區↔物件一對多歸戶為同一操作層級主題；社區屬物件本身的歸屬屬性，歸 C。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-listing-publish-unpublish",
    "coarse_id": "C",
    "title": "物件刊登（上架）條件、下架條件與突然全部下架的原因",
    "slug": "property-listing-publish-unpublish",
    "merge_of": [
     "tmp:kb:3429",
     "tmp:kb:3430",
     "tmp:kb:3506",
     "tmp:kb:4151"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "上架條件、手動／自動下架、方案失效導致整批下架，皆為業者操作層級的刊登軸主題；4151 為空內文入口併入。刊登軸屬物件本身狀態，歸 C（合約軸另見 property-status-meaning）。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-edit-and-save",
    "coarse_id": "C",
    "title": "編輯物件與刊登物件的差別、儲存與對既有合約的影響",
    "slug": "property-edit-and-save",
    "merge_of": [
     "tmp:kb:4147"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "編輯≠刊登、需按儲存、修改不影響合約快照——屬業者操作層級的物件編輯行為，與刊登條件主題分開以保持一主題一細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/public-display-address",
    "coarse_id": "C",
    "title": "對外顯示地址的作用範圍（後台永遠顯示完整地址）",
    "slug": "public-display-address",
    "merge_of": [
     "tmp:kb:4145",
     "tmp:kb:4152"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "對外顯示地址是物件本身的屬性設定，作用範圍是業者操作層級的常見疑問；4152 為空內文入口併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/storefront-and-community-page-sharing",
    "coarse_id": "C",
    "title": "招租店舖與社區公開頁面的入口、網址與分享",
    "slug": "storefront-and-community-page-sharing",
    "merge_of": [
     "tmp:kb:3470",
     "tmp:kb:4146"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "社區公開頁與招租店舖皆為對外展示頁，入口、專屬網址、分享與連動設定屬業者操作層級；與 prospect 能力層級的 rental-storefront-vr 分層另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-vr-binding",
    "coarse_id": "C",
    "title": "物件 VR 虛擬導覽綁定（iStaging）與服務範圍",
    "slug": "property-vr-binding",
    "merge_of": [
     "tmp:kb:3433"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "VR 綁定操作與廠商服務邊界屬業者操作層級，獨立於招租店舖分享主題；prospect 能力層級見 rental-storefront-vr。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-custom-tags-howto",
    "coarse_id": "C",
    "title": "物件自訂標籤怎麼建立、勾選與篩選",
    "slug": "property-custom-tags-howto",
    "merge_of": [
     "tmp:kb:3434"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "自訂標籤的建立／勾選／篩選／公開頁顯示為業者操作層級；prospect 能力層級已在 property-management-overview 提及，分層另見不重複。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/property-list-advanced-search",
    "coarse_id": "C",
    "title": "物件列表進階搜尋與篩選條件",
    "slug": "property-list-advanced-search",
    "merge_of": [
     "tmp:draft:2"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "進階搜尋（空間類型、社區大樓、租金範圍、坪數）是物件列表的操作層級功能，與標籤篩選為不同主題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/occupancy-rate-calculation",
    "coarse_id": "C",
    "title": "首頁即時物件出租率的百分比怎麼算",
    "slug": "occupancy-rate-calculation",
    "merge_of": [
     "tmp:kb:4648"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "出租率＝合約中物件數÷物件總數，是物件總表層級的統計指標；分母分子皆為物件計數，歸物件屬性而非帳務或租約。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-facility-rules-and-entitlements",
    "coarse_id": "C",
    "title": "社區公共設施的使用權益、義務、規範、費用、開放時間、損壞與爭議處理",
    "slug": "community-facility-rules-and-entitlements",
    "merge_of": [
     "tmp:kb:1396",
     "tmp:kb:2980",
     "tmp:kb:3049",
     "tmp:kb:3050",
     "tmp:kb:3056",
     "tmp:kb:3057",
     "tmp:kb:3058",
     "tmp:kb:3059",
     "tmp:kb:3060",
     "tmp:kb:3061",
     "tmp:kb:3062",
     "tmp:kb:3063",
     "tmp:kb:3064",
     "tmp:kb:3245",
     "tmp:kb:3246",
     "tmp:kb:3247",
     "tmp:kb:3248",
     "tmp:kb:3249",
     "tmp:kb:3299",
     "tmp:kb:3300",
     "tmp:kb:4262",
     "tmp:kb:4276"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "這批來源全為租客權益層級的公共設施問答（使用權／義務／規範／安全／時間／變更／費用／損壞／罰則／爭議／保險），jgb 受眾無租客層級；依受眾層級歸為業者（管理師）需備妥並回覆的社區公共設施資訊一個主題，來源須改寫成業者層級；1396／4262／4276 為空內文或純查詢入口併入不獨立。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/C/community-living-services",
    "coarse_id": "C",
    "title": "社區生活服務與住戶規範（垃圾、洗衣烘衣、社區活動、包裹、社宅服務）",
    "slug": "community-living-services",
    "merge_of": [
     "tmp:kb:3051",
     "tmp:kb:3052",
     "tmp:kb:3053",
     "tmp:kb:3054",
     "tmp:kb:3055",
     "tmp:kb:3157",
     "tmp:kb:3263",
     "tmp:kb:4272"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "與公共設施使用規範同為租客權益層級，但主題是社區生活服務／住戶日常規範而非設施本身，故另立一細目；歸業者操作層級的社區資訊維護；4272 為空內文入口併入。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/C/community-batch-create",
    "new": "jgb/C/community-batch-create",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/C/property-management-overview",
    "new": "jgb/C/property-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/C/property-status-meaning",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3428",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4154",
    "new": "jgb/C/property-status-meaning",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/C/rental-storefront-vr",
    "new": "jgb/C/rental-storefront-vr",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3357",
    "new": "jgb/C/property-batch-import-howto",
    "op": "new"
   },
   {
    "old": "tmp:kb:3431",
    "new": "jgb/C/property-batch-import-howto",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/C/property-batch-import-howto",
    "op": "new"
   },
   {
    "old": "tmp:kb:3468",
    "new": "jgb/C/community-setup-and-property-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:3469",
    "new": "jgb/C/community-setup-and-property-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:3429",
    "new": "jgb/C/property-listing-publish-unpublish",
    "op": "new"
   },
   {
    "old": "tmp:kb:3430",
    "new": "jgb/C/property-listing-publish-unpublish",
    "op": "new"
   },
   {
    "old": "tmp:kb:3506",
    "new": "jgb/C/property-listing-publish-unpublish",
    "op": "new"
   },
   {
    "old": "tmp:kb:4151",
    "new": "jgb/C/property-listing-publish-unpublish",
    "op": "new"
   },
   {
    "old": "tmp:kb:4147",
    "new": "jgb/C/property-edit-and-save",
    "op": "new"
   },
   {
    "old": "tmp:kb:4145",
    "new": "jgb/C/public-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:4152",
    "new": "jgb/C/public-display-address",
    "op": "new"
   },
   {
    "old": "tmp:kb:3470",
    "new": "jgb/C/storefront-and-community-page-sharing",
    "op": "new"
   },
   {
    "old": "tmp:kb:4146",
    "new": "jgb/C/storefront-and-community-page-sharing",
    "op": "new"
   },
   {
    "old": "tmp:kb:3433",
    "new": "jgb/C/property-vr-binding",
    "op": "new"
   },
   {
    "old": "tmp:kb:3434",
    "new": "jgb/C/property-custom-tags-howto",
    "op": "new"
   },
   {
    "old": "tmp:draft:2",
    "new": "jgb/C/property-list-advanced-search",
    "op": "new"
   },
   {
    "old": "tmp:kb:4648",
    "new": "jgb/C/occupancy-rate-calculation",
    "op": "new"
   },
   {
    "old": "tmp:kb:1396",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:2980",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3049",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3050",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3056",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3057",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3058",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3059",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3060",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3061",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3062",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3063",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3064",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3245",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3246",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3247",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3248",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3249",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3299",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3300",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:4262",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:4276",
    "new": "jgb/C/community-facility-rules-and-entitlements",
    "op": "new"
   },
   {
    "old": "tmp:kb:3051",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3052",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3053",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3054",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3055",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3157",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:3263",
    "new": "jgb/C/community-living-services",
    "op": "new"
   },
   {
    "old": "tmp:kb:4272",
    "new": "jgb/C/community-living-services",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3011",
    "suggested_shelf": "E",
    "why": "公益出租人減稅是租金／稅務條件（錢怎麼算），且為租客受眾內容，不是社區或物件屬性。"
   },
   {
    "id": "tmp:kb:3358",
    "suggested_shelf": "B",
    "why": "大房東邀請與物件授權是團隊／人員權限主題（大房東列表在團隊設定），非物件本身屬性。"
   },
   {
    "id": "tmp:kb:3456",
    "suggested_shelf": "I",
    "why": "物件數量上限與加購額度由訂閱方案決定，內容全在方案頁與方案額度，非物件屬性。"
   },
   {
    "id": "tmp:kb:3505",
    "suggested_shelf": "I",
    "why": "無法新增物件的兩個原因皆在他架：方案額度已滿（I）與角色權限不足（B），內容不含物件屬性；主因為方案故建議 I。"
   },
   {
    "id": "tmp:kb:3973",
    "suggested_shelf": "B",
    "why": "成員看不到社區物件／無法新增的根因是角色未指派與可見範圍設定，屬團隊人員權限主題。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。