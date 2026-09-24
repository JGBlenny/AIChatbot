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
⚠️ 本次為擴充模式，**只補一架（I）**：候選項目分兩種——`tmp:canon:*`（I 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `I`，`id` 必須為 `jgb/I/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/I/competitor-comparison", "tmp:canon:jgb/I/competitor-neutrality", "tmp:canon:jgb/I/dashboard-overview", "tmp:canon:jgb/I/data-migration", "tmp:canon:jgb/I/free-trial", "tmp:canon:jgb/I/individual-landlord-scale-fit", "tmp:canon:jgb/I/pricing-plans", "tmp:canon:jgb/I/product-overview", "tmp:canon:jgb/I/property-quota-limit", "tmp:canon:jgb/I/subscription-change-renewal", "tmp:canon:jgb/I/team-company-fit", "tmp:canon:jgb/I/why-choose-jgb", "tmp:kb:2909", "tmp:kb:2910", "tmp:kb:2911", "tmp:kb:2913", "tmp:kb:2918", "tmp:kb:2920", "tmp:kb:2921", "tmp:kb:2924", "tmp:kb:2925", "tmp:kb:2977", "tmp:kb:3006", "tmp:kb:3035", "tmp:kb:3047", "tmp:kb:3105", "tmp:kb:3158", "tmp:kb:3207", "tmp:kb:3208", "tmp:kb:3209", "tmp:kb:3210", "tmp:kb:3356", "tmp:kb:3453", "tmp:kb:3454", "tmp:kb:3455", "tmp:kb:3457", "tmp:kb:3476", "tmp:kb:3478", "tmp:kb:3509", "tmp:kb:3798", "tmp:kb:3850", "tmp:kb:4261", "tmp:kb:4271", "tmp:kb:4275", "tmp:kb:5376", "tmp:draft:1"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/I/competitor-comparison", "tmp:canon:jgb/I/competitor-neutrality", "tmp:canon:jgb/I/dashboard-overview", "tmp:canon:jgb/I/data-migration", "tmp:canon:jgb/I/free-trial", "tmp:canon:jgb/I/individual-landlord-scale-fit", "tmp:canon:jgb/I/pricing-plans", "tmp:canon:jgb/I/product-overview", "tmp:canon:jgb/I/property-quota-limit", "tmp:canon:jgb/I/subscription-change-renewal", "tmp:canon:jgb/I/team-company-fit", "tmp:canon:jgb/I/why-choose-jgb", "tmp:kb:2909", "tmp:kb:2910", "tmp:kb:2911", "tmp:kb:2913", "tmp:kb:2918", "tmp:kb:2920", "tmp:kb:2921", "tmp:kb:2924", "tmp:kb:2925", "tmp:kb:2977", "tmp:kb:3006", "tmp:kb:3035", "tmp:kb:3047", "tmp:kb:3105", "tmp:kb:3158", "tmp:kb:3207", "tmp:kb:3208", "tmp:kb:3209", "tmp:kb:3210", "tmp:kb:3356", "tmp:kb:3453", "tmp:kb:3454", "tmp:kb:3455", "tmp:kb:3457", "tmp:kb:3476", "tmp:kb:3478", "tmp:kb:3509", "tmp:kb:3798", "tmp:kb:3850", "tmp:kb:4261", "tmp:kb:4271", "tmp:kb:4275", "tmp:kb:5376", "tmp:draft:1"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/I/competitor-comparison", "tmp:canon:jgb/I/competitor-neutrality", "tmp:canon:jgb/I/dashboard-overview", "tmp:canon:jgb/I/data-migration", "tmp:canon:jgb/I/free-trial", "tmp:canon:jgb/I/individual-landlord-scale-fit", "tmp:canon:jgb/I/pricing-plans", "tmp:canon:jgb/I/product-overview", "tmp:canon:jgb/I/property-quota-limit", "tmp:canon:jgb/I/subscription-change-renewal", "tmp:canon:jgb/I/team-company-fit", "tmp:canon:jgb/I/why-choose-jgb", "tmp:kb:2909", "tmp:kb:2910", "tmp:kb:2911", "tmp:kb:2913", "tmp:kb:2918", "tmp:kb:2920", "tmp:kb:2921", "tmp:kb:2924", "tmp:kb:2925", "tmp:kb:2977", "tmp:kb:3006", "tmp:kb:3035", "tmp:kb:3047", "tmp:kb:3105", "tmp:kb:3158", "tmp:kb:3207", "tmp:kb:3208", "tmp:kb:3209", "tmp:kb:3210", "tmp:kb:3356", "tmp:kb:3453", "tmp:kb:3454", "tmp:kb:3455", "tmp:kb:3457", "tmp:kb:3476", "tmp:kb:3478", "tmp:kb:3509", "tmp:kb:3798", "tmp:kb:3850", "tmp:kb:4261", "tmp:kb:4271", "tmp:kb:4275", "tmp:kb:5376", "tmp:draft:1"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/I/competitor-comparison", "tmp:canon:jgb/I/competitor-neutrality", "tmp:canon:jgb/I/dashboard-overview", "tmp:canon:jgb/I/data-migration", "tmp:canon:jgb/I/free-trial", "tmp:canon:jgb/I/individual-landlord-scale-fit", "tmp:canon:jgb/I/pricing-plans", "tmp:canon:jgb/I/product-overview", "tmp:canon:jgb/I/property-quota-limit", "tmp:canon:jgb/I/subscription-change-renewal", "tmp:canon:jgb/I/team-company-fit", "tmp:canon:jgb/I/why-choose-jgb", "tmp:kb:2909", "tmp:kb:2910", "tmp:kb:2911", "tmp:kb:2913", "tmp:kb:2918", "tmp:kb:2920", "tmp:kb:2921", "tmp:kb:2924", "tmp:kb:2925", "tmp:kb:2977", "tmp:kb:3006", "tmp:kb:3035", "tmp:kb:3047", "tmp:kb:3105", "tmp:kb:3158", "tmp:kb:3207", "tmp:kb:3208", "tmp:kb:3209", "tmp:kb:3210", "tmp:kb:3356", "tmp:kb:3453", "tmp:kb:3454", "tmp:kb:3455", "tmp:kb:3457", "tmp:kb:3476", "tmp:kb:3478", "tmp:kb:3509", "tmp:kb:3798", "tmp:kb:3850", "tmp:kb:4261", "tmp:kb:4271", "tmp:kb:4275", "tmp:kb:5376", "tmp:draft:1"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（46 筆，原序列舉）
### tmp:canon:jgb/I/competitor-comparison
標題：跟 Bananas、屋我也差在哪
內容：同類的租賃管理系統還有 Bananas、屋我也，三者都做物件、合約、帳務，差異主要在合約類型廣度、金流、IoT 整合與適用場景。 以公開官網可查的事實來說：金箍棒的合約類型較完整（涵蓋一般租賃、社會住宅、委託），金流支援多元（藍新／永豐／中信／國泰／愛金卡），並有智慧門鎖／電錶整合（硬體細節由專人說明）與大房東報表，適合社宅委託、需多元收款、要對業主交報表的代管團隊。 對方官網未明確提及的功能，我們無法替他們確認，建議您直接向對方詢問。 若想實際比較，歡迎預約 demo。

### tmp:canon:jgb/I/competitor-neutrality
標題：會評論競爭對手嗎
內容：我們不會評論同業的好壞或內部狀況，只就公開可查的事實、以及金箍棒實際適合的情境提供中立資訊；對方未明確提供的功能，建議您直接向對方確認，我們不會替他們斷言有或沒有。 若想實際比較，最準的方式是預約 demo 或直接開免費試用體驗。

### tmp:canon:jgb/I/dashboard-overview
標題：首頁儀表板顯示哪些數據
內容：登入後的首頁儀表板有三塊：收支情況（圖表化呈現，可自訂時間區間看營運趨勢）、帳務情況（近期的逾期待收款帳單與待繳費帳單，可點「更多」看明細）、修繕情況（租客目前申請中的修繕單）。 想看實際畫面可預約 demo。

### tmp:canon:jgb/I/data-migration
標題：舊系統資料能否匯入（可匯入範圍與不支援項目）
內容：換系統最怕重建資料。 金箍棒可以用 Excel 範本批次匯入：物件（一般與社會住宅）、租客、社區、大房東聯絡簿；團隊（法人房東）帳號還能用「匯出草稿帳單→填寫→匯回」的方式批次更新帳單；合約與舊系統已繳完的歷史帳單不支援匯入。 搬遷細節可預約 demo，由專人依您的資料量評估。 要特別說明的是：合約目前不支援批次匯入，需要逐筆建立（線上電子簽新約，或上傳既有紙本合約 PDF 存檔）；舊系統已繳完的歷史帳單也沒有搬移功能。

### tmp:canon:jgb/I/free-trial
標題：可以免費試用嗎
內容：可以，新帳號享有免費試用一個月，註冊即可開始，先實際用過再決定。 需要協助開通可以留個聯絡方式，或直接預約 demo 由專人帶您看。

### tmp:canon:jgb/I/individual-landlord-scale-fit
標題：個人房東（約 10～30 戶）適配與建議做法
內容：管 10 間左右的個人房東，最花時間的通常是收租對帳和合約來回。 金箍棒把物件、合約、帳務集中在一個系統：線上電子簽章簽約、自動產帳單與金流代收、收租對帳一條龍，取代 Excel 與 LINE 的零散作業，也能發租客通知、處理報修。 建議先用免費試用一個月實際跑跑看；正式方案級距與費用調整中，可於定價頁(https://www.jgbsmart.com/pricing)查看或由專人為您說明，這裡不報數字。 管到 20 間左右，帳單與對帳的量明顯變大、人工容易出錯。 金箍棒的帳務模組（自動帳單、多元金流代收、電子發票、儲值金）能把收租對帳自動化，搭配物件管理、電子簽章合約、租客通知與修繕，讓一個人也管得動這個規模。 可先免費試用一個月感受效率差異；方案級距與費用請見定價頁(https://www.jgbsmart.com/pricing)或由專人提供，這裡不報過時數字。 管到 30 間左右，已接近個人經營的規模上限，物件與帳務都相當可觀；未來若開始多人協作或要對業主交報表，會很快需要團隊管理與大房東報表。 金箍棒在這階段能用物件、合約、帳務的完整自動化撐住現有規模，並可平順銜接到團隊方案。 建議先免費試用一個月；正式級距與費用調整中，請見定價頁(https://www.jgbsmart.com/pricing)或由專人為您盤點，這裡不直接報價。

### tmp:canon:jgb/I/pricing-plans
標題：怎麼收費
內容：金箍棒採訂閱制，方案依管理規模（物件數）以及是否需要團隊、大房東報表、IoT 等功能分級。 目前方案與價格正在調整，為避免提供過時數字，實際級距與費用請參考線上定價頁(https://www.jgbsmart.com/pricing)，或留下聯絡方式由專人為您報價。 也歡迎先用免費試用一個月實際體驗。

### tmp:canon:jgb/I/product-overview
標題：系統總覽、能解決什麼問題與適不適合我
內容：金箍棒智慧物管能把物件、合約、收租對帳到智慧設備集中在一個系統管理。 想知道適不適合您，先讓我了解一下您的狀況。 管理租賃常見的收租對帳、合約、人多協作、報修等問題，金箍棒都有對應的模組。 想知道我們怎麼解決您的狀況，先選一個您最想改善的：

### tmp:canon:jgb/I/property-quota-limit
標題：方案物件額度上限與用滿怎麼辦
內容：金箍棒的方案是依可管理的物件數分級，物件額度用滿就無法再新增，可以升級方案、加購額度，或把不再使用的物件下架釋放額度；目前用量在「訂閱方案」頁看得到。 各方案的物件數級距請以線上定價頁為準 [查看方案與費用](https://www.jgbsmart.com/pricing)。 免費方案預設可建 5 個物件（免費試用一個月就是免費方案），實際額度以帳號內「訂閱方案」頁顯示為準。 新帳號享有免費試用一個月，可先實際體驗再選方案。

### tmp:canon:jgb/I/subscription-change-renewal
標題：升級、續約與取消訂閱
內容：方案的變更在「團隊管理」的「訂閱方案」頁：點「變更」、選物件數量對應的年／月方案、完成付款即生效，支出可在「付款紀錄」查看。 訂閱到期會自動續約扣款；若扣款失敗，方案會失效、物件會被系統自動下架，補完付款後再重新上架即可。 要取消訂閱，在方案頁下方的服務條款連結點「取消訂閱」。

### tmp:canon:jgb/I/team-company-fit
標題：公司或包租代管團隊適合嗎
內容：公司或團隊（包租代管、物管）通常要多人分工，還得對業主交報表，需求比個人房東複雜。 金箍棒的全模組方案正好對應這種規模——除了物件、合約、帳務，還有團隊權限管理讓成員分工，以及大房東報表，把代收代付與營運狀況整理好、對業主交代清楚；若有現場抄電表或換門鎖的需求，智慧電錶／門鎖也能依需求整合（細節由專人說明）。 實際適合的模組組合與費用會依團隊規模而不同，建議直接預約 demo，由專人陪您盤點需求並提供報價。

### tmp:canon:jgb/I/why-choose-jgb
標題：為什麼選金箍棒
內容：選金箍棒的主要理由在「合約類型廣 + 多元金流 + IoT 整合 + 規模化團隊管理」：合約涵蓋一般／社會住宅／委託（社宅與委託代管尤其完整）、金流支援藍新／永豐／中信／國泰／愛金卡、可串接智慧門鎖／電錶（細節由專人說明）、多人權限搭配大房東報表方便對業主交代，另有押金設算息、VR 看屋、6 國語系等加值，且新帳號享免費試用一個月。 想實際體驗可直接開試用或預約 demo。

### tmp:kb:2909
標題：租金行情參考
內容：租金行情的參考來源包括當地房地產網站、租屋平台、以及與管理師的交流。這些來源可以幫助您了解相似物件的租金水平，確保您支付的租金是公平合理的。

### tmp:kb:2910
標題：管理費
內容：管理費是您在租住期間需要支付的費用，通常用於維護及管理公共設施和服務，如清潔、保安和社區設施的維護等。這筆費用能確保居住環境的整潔和安全，並提高生活品質。

### tmp:kb:2911
標題：公共費用分攤
內容：公共費用的分攤原則通常是按租戶的使用面積或人數來計算，具體分攤方式會在租約中明確說明。您可以根據合約了解自己的分攤比例與金額。

### tmp:kb:2913
標題：租金多繳溢繳退還處理
內容：如果您發現租金多繳，請盡快聯繫您的管理師，提供繳款證明和相關資料。我們將會協助您核對並安排退還多餘的租金。

### tmp:kb:2918
標題：租金支付期限
內容：租金的支付期限通常是每個月的約定日期，具體日期會在租約中明確。如果您有任何疑問，建議聯繫您的管理師以確認具體的支付期限及條件。

### tmp:kb:2920
標題：租金折扣條件
內容：租金折扣的條件通常包括長期租約、提前繳納租金、租客良好的支付紀錄，或特殊促銷活動。具體條件可能因物件和合約而異，建議您聯繫您的管理師以獲取詳情。

### tmp:kb:2921
標題：租金支付證明
內容：租金支付的證明文件包括租金收據、銀行轉帳明細、支付平台的交易紀錄或電子發票。這些文件都可作為您支付租金的證明，若需要進一步的協助或具體文件，請聯繫您的管理師。

### tmp:kb:2924
標題：租金支付法律依據
內容：租金支付的法律依據主要來自於租賃契約，該契約會明確規定租金的金額、支付方式及支付期限等條款。根據法律，房客有權要求房東或管理公司依約收取租金，並應提供相應的收據或證明。您也可以向管理師查詢相關條款，確保自己的權益受到保障。

### tmp:kb:2925
標題：租金市場變化
內容：租金的市場變化通常受到供需關係、經濟狀況、政策法規、地區發展、以及季節性需求等因素影響。例如，若某區域新建設施或交通便利，可能吸引更多租客，進而推高租金。相對地，經濟衰退可能導致租金下降。

### tmp:kb:2977
標題：飼養寵物費用
內容：飼養寵物是否需要額外支付費用，取決於您的租約條款。一般來說，某些租約可能會要求額外的押金或月租費用來涵蓋寵物造成的損害。建議您查看租約內容或聯繫您的管理師以確認具體要求。

### tmp:kb:3006
標題：租屋保險費用
內容：租屋保險的費用通常依據保險公司、保險範圍及保額的不同而有所差異，一般來說，年費用可能在數千元左右。建議您向保險公司詢問具體報價，以獲得最準確的資訊。

### tmp:kb:3035
標題：戶籍遷移
內容：租客在租屋期間是可以遷移戶籍的，這不影響租約的有效性。不過，建議您在遷移戶籍前，先與房東或管理師確認相關規定，確保不會影響您的租住權益。

### tmp:kb:3047
標題：居住證明費用
內容：申請居住證明一般是免費的，您不需要支付任何費用。建議您確認具體的申請流程和要求，以確保一切順利。

### tmp:kb:3105
標題：管理費用途
內容：管理費主要用於物業的日常維護和管理，包括公共設施的維護、清潔、保安服務以及相關的行政管理費用。這些服務保證了居住環境的舒適與安全，並提升了物業的整體價值。

### tmp:kb:3158
標題：服務費用計算
內容：業者的服務費用一般是根據租金的比例來計算的，具體比例可能因合約而異，包含管理、維護等服務費用。建議您查閱合約或聯繫管理師以獲取詳細資訊。

### tmp:kb:3207
標題：租金少繳不足補繳
內容：如果您發現租金少繳，建議您儘快聯繫您的管理師，告知情況，以便確認應繳金額及後續補繳步驟。根據合約，您需在約定的時間內補足租金，以免影響租賃權益。

### tmp:kb:3208
標題：租金遲繳罰款
內容：租金遲繳通常會依合約規定產生罰款，具體金額和罰款條件會在租約中列明。請務必查看您的租約以了解詳細資訊，若有疑問，建議聯繫您的管理師確認。

### tmp:kb:3209
標題：租金包含服務
內容：租金通常包含以下項目：
1. 房屋租金本身
2. 管理費用
3. 公共區域的清潔、維護及保安服務

部分租約也可能包含水電費、網路費及公共設施使用費，具體內容會依租約條款而定。建議您查看租約或聯繫管理師確認詳細項目。

### tmp:kb:3210
標題：租金爭議解決
內容：租金爭議可以透過協商、調解和法律途徑來解決。首先，您可以嘗試與管理師直接溝通，尋求問題的解決方案。如果無法達成共識，可以考慮尋求第三方調解服務，或是向相關政府單位申訴。若情況仍未改善，最終可以通過法律途徑解決，建議您保留所有相關的證據文件以便使用。

### tmp:kb:3356
標題：訂閱 取消 方案
內容：取消訂閱的操作步驟：
1. 點選左側選單「其他設定」>「訂閱方案」
2. 點選「變更」
3. 在價格方案下方找到服務條款連結，點選藍字「取消訂閱」即可完成

### tmp:kb:3453
標題：訂閱方案 種類差異
內容：JGB 提供不同等級的訂閱方案，主要差異在於：（1）可管理的物件數量上限；（2）可設定的大房東數量上限；（3）可使用的進階功能（如 IoT 整合、差額發票等）。免費方案可管理有限數量的物件，付費方案依等級提供更多物件額度和進階功能。各方案詳細內容和價格可在「訂閱方案」頁面查看。若目前方案的物件數量不夠用，可升級方案或加購額外物件額度。

### tmp:kb:3454
標題：訂閱方案 升級更換
內容：升級或更換訂閱方案：進入帳號設定中的「訂閱方案」頁面，查看目前方案資訊後選擇「更換方案」，挑選新方案並完成付款即可。升級後新方案立即生效，物件額度即時更新。方案費用依選擇的付費週期（月繳/年繳等）不同。系統支援信用卡付款，付款成功後會收到訂閱回條通知。

### tmp:kb:3455
標題：取消訂閱 退訂流程
內容：取消訂閱流程：進入帳號設定的「訂閱方案」頁面，選擇「取消訂閱」並確認。取消後方案會在目前付費週期結束時失效，期間仍可正常使用所有功能。取消後物件刊登數若超過免費方案上限，超出的物件會自動下架。已建立的合約和帳單資料不受影響，但部分進階功能將無法使用。若要重新訂閱，可隨時再次選購方案。

### tmp:kb:3457
標題：訂閱付款紀錄 自動續訂
內容：訂閱付款紀錄可在帳號設定的「付款紀錄」頁面查看，包含每次扣款的金額、日期和付款狀態。系統預設自動續訂：在方案到期前 5 天會發送續訂提醒通知，到期時自動以原付款方式扣款續訂。若自動扣款失敗（如信用卡過期、額度不足），系統會通知並給予補繳期限。未在期限內完成付款，方案將降為免費版。

### tmp:kb:3476
標題：租客批次匯入 Excel
內容：大量新增租客可使用 Excel 批次匯入功能：1. 在租客管理頁面下載匯入範本（Excel 格式）；2. 依範本格式填寫租客資料（姓名、聯絡方式等）；3. 上傳填寫完成的 Excel 檔案；4. 系統自動驗證資料格式並匯入。匯入過程中若有格式錯誤或重複資料，系統會提示需要修正的項目。批次匯入適合一次性建檔大量租客，省去逐一手動輸入的時間。

### tmp:kb:3478
標題：邀請租客 訂閱通知
內容：房東可邀請租客訂閱系統通知，讓租客透過 Email 或簡訊接收帳單、合約等相關通知。操作方式：在租客管理頁面選擇要邀請的租客，點選「邀請訂閱通知」，系統會發送邀請給租客的 Email 或手機。租客完成確認後即開始接收通知。此功能適合讓尚未綁定帳號的租客也能收到繳費提醒等重要資訊。

### tmp:kb:3509
標題：訂閱扣款失敗導致功能異常
內容：訂閱扣款失敗時，系統會清除方案並將物件全部自動下架，多數功能會暫時無法使用。處理方式：到「訂閱方案」頁確認方案狀態與付款方式（更換有效的信用卡或付款管道），完成續約付款後方案恢復，再將物件重新上架即可。若付款方式正常仍扣款失敗，請聯繫客服協助。

### tmp:kb:3798
標題：售前系統脈絡 append（競品協定/CTA/功能索引）
內容：## 5b. 競品處理協定（硬護欄）
- 不主動點名競品;使用者主動提到才回應
- 競品事實只能用本次提供的 E1 知識;E1 沒給就不講競品細節
- 對手未列明的功能說「不確定他們是否提供,建議直接向對方確認」
- 絕不斷言對方「沒有/不支援」,不貶低、不評對方內部狀況
- 不討論競品價格、不傳未經證實的負面訊息
- 比較後收束回 JGB 適用情境與優勢（E2）→ 導試用/demo

## 6. CTA 出口慣例
| 情境 | 出口 |
|---|---|
| 想試用 | trial_form |
| 想看 demo / 企業客 | demo_form |
| 問價格 | [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資 |
| 問 IoT 硬體 | 專人（點下方『找真人』） |

## 7. 功能對照索引（情境 → 推薦功能）
| 情境/痛點 | 推薦功能（點名用） |
|---|---|
| 退租結算、押金扣抵複雜 | 差額發票、押金設算息 |
| 收租對帳亂、催繳費 | 自動帳單、金流代收、儲值金 |
| 合約多、社宅/委託 | 電子簽章、社宅/委託合約 |
| 人多協作、對業主交代 | 團隊權限、大房東報表 |
| 現場抄表/換鎖 | 智慧電錶/門鎖（細節由專人）|
| 報修追蹤慢 | 線上報修、進度追蹤 |
| 物件分散難管 | 房源集中、社區歸戶、批次上傳 |
| 找房客、空屋招租 | 物件公開頁、VR 看屋 |
| 逾期未繳、要催繳 | 自動逾期提醒、滯納金 |
| 點交點退、續約解約 | 線上點交點退、續約解約 |
| 發票開錯要作廢 | 電子發票作廢 |
| 大量租客建檔 | 租客批次匯入 |
| 外籍/海外租客 | 多語系介面 |
| 想評估費用 | 導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資／點下方『找真人』 |

### tmp:kb:3850
標題：點退找補費用 操作位置
內容：點退的押金找補（多退少補）在「編輯點退清單」時一併操作，不在帳務管理裡另外設定。房東送出點退結果、租客同意後，系統會立即在合約細節產生點退清單，並依清單金額自動產生帳單、分派到付款方（房東或租客）的繳費帳單中。點退退款目前僅提供線下付款。

### tmp:kb:4261
標題：停車費 車位費用 月租車位
內容：

### tmp:kb:4271
標題：為什麼要收管理費 費用怎麼算
內容：

### tmp:kb:4275
標題：機車汽車停車位費用
內容：

### tmp:kb:5376
標題：費用怎麼算 一年多少錢 收費方式 月費 年費 要花多少
內容：金箍棒採訂閱制，方案依管理規模（物件數）以及是否需要團隊、大房東報表、IoT 等功能分級。目前方案與價格正在調整，為避免提供過時數字，實際級距與費用請參考線上定價頁(https://www.jgbsmart.com/pricing)，或留下聯絡方式由專人為您報價。也歡迎先用免費試用一個月實際體驗。

### tmp:draft:1
標題：房東教學：總論篇
內容：房東教學：總論篇 親愛的管理者您好歡迎您加入JGB的租房管理系統，若您是剛加入系統的新夥伴，或是想了解系統架構和功能的朋友，JGB為您整理了數篇關於房東視角的新手教學，其中有關註冊、簽約、帳務...等功能都可以在文章當中一目瞭然，並且詳細說明有關各個功能的操作流程，有需要的使用者不妨參考以下大綱，找到您想了解的內容並點選上方文章鏈結，讓您快速了解JGB系統如何提升您物件管理的效率 ➡註冊篇（一）－個人房東篇 ➡註冊篇（二）－公司團隊篇 ➡物件篇 ➡合約篇 ➡收款設置篇 ➡帳務篇 ➡社宅篇 ➡修繕篇 ➡設備篇 ➡常見問題篇（移至常見問題分類） 註冊篇（ㄧ）— 個人房東篇 ➡如何註冊JGB系統帳號 ➡如何設定個人房東的帳號資訊（聯絡方式、通訊地址...等） 註冊篇（二）— 公司團隊篇 ➡如何創建團隊 ➡如何設定團隊的帳號資訊（公司名稱、聯絡方式、經紀人資訊...等） ➡團隊成員的加入＆權限管理 ➡大房東的加入＆權限管理 ➡如何查看＆變更現行的訂閱方案 ➡設定對外招租網址、時區 物件篇 ➡如何創建社區 ➡如何查看＆編輯社區 ➡如何批次新增社區 ➡如何建立物件 ➡如何查看＆編輯物件 ➡批次新增物件 合約篇 ➡如何建立合約 ➡如何簽訂合約 ➡如何上傳（既有）合約 ➡如何批次績約 ➡如何提前解約 ➡如何點交/點退 收款設置篇 ➡如何設置線上金流（藍新 / 國泰 / 中信 / 永豐） ➡如何設置現金收款帳戶 ➡單一金流設定多組帳號 ➡如何排定帳單發送時間 ➡如何設定收據形式 帳務篇 ➡如何產生租金帳單 ➡如何新增單一帳單（水費、電費...等） ➡ 如何編輯帳單 ➡ 如何批次發送/編輯帳單 ➡如何確認收款 社宅篇 ➡如何創建社宅團隊 ➡如何創建社宅物件 ➡如何建立社宅合約 ➡如何使用社宅帳務功能（收款、匯出資料...等） 修繕篇 ➡新增修繕單 ➡安排修繕 ➡完成修繕 ➡結單 設備篇 ➡智慧電錶 常見問題篇


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
    "id": "jgb/I/competitor-comparison",
    "coarse_id": "I",
    "title": "跟 Bananas、屋我也差在哪",
    "slug": "competitor-comparison",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-comparison"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者主動點名競品問差異時的唯一落點；只保留既有公開事實陳述，⛔ 不新增競品比較內容，policy 由既有 deliberate_no 規則處理",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/competitor-neutrality",
    "coarse_id": "I",
    "title": "會評論競爭對手嗎",
    "slug": "competitor-neutrality",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-neutrality",
     "tmp:kb:3798"
    ],
    "split_from": [
     "tmp:kb:3798"
    ],
    "moved_from": [],
    "reason": "「你們會不會講同業壞話／能不能幫我比」這一問的落點；吸收 3798 §5b 競品處理協定作為回答邊界（護欄，非新比較內容），其餘段落拆給 product-overview",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/dashboard-overview",
    "coarse_id": "I",
    "title": "首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:canon:jgb/I/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「登入後首頁看得到什麼」單一問題，售前與已導入者問法相同、答案相同",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:canon:jgb/I/data-migration",
     "tmp:kb:3476"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「舊資料能不能搬／租客能不能一次匯入」同一提問路徑；3476 的租客 Excel 批次匯入步驟是此問題在已導入者端的操作答案，併入不另立細目",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:canon:jgb/I/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「能不能先試用」獨立一問；額度細節另見 property-quota-limit",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/individual-landlord-scale-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適配與建議做法",
    "slug": "individual-landlord-scale-fit",
    "merge_of": [
     "tmp:canon:jgb/I/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「我管十幾間適不適合」按受眾規模問的獨立問題，與公司團隊版分立",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費與方案種類差異",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:canon:jgb/I/pricing-plans",
     "tmp:kb:5376",
     "tmp:kb:3453"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「多少錢／怎麼分級／方案差在哪」同一提問路徑；5376 與既有內容逐字相同，3453 的方案差異說明（物件數、大房東數、進階功能）是同一問題在已導入者端的答案；額度用滿另見 property-quota-limit",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題與適不適合我",
    "slug": "product-overview",
    "merge_of": [
     "tmp:canon:jgb/I/product-overview",
     "tmp:kb:3798"
    ],
    "split_from": [
     "tmp:kb:3798"
    ],
    "moved_from": [],
    "reason": "「你們是做什麼的／我有 X 痛點你們能解決嗎」的入口落點；吸收 3798 §7 情境→功能對照索引作為痛點分流依據；§6 CTA 出口慣例是出口規則非可回答問題，不成細目",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限與用滿怎麼辦",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:canon:jgb/I/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「可以建幾個物件／滿了怎麼辦」獨立一問，售前與已導入者皆會問",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級、變更、續約與取消訂閱（操作與付款紀錄）",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3454",
     "tmp:kb:3356",
     "tmp:kb:3455",
     "tmp:kb:3457"
    ],
    "split_from": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3457"
    ],
    "moved_from": [],
    "reason": "「怎麼升級／換方案／取消／會不會自動續約／付款紀錄在哪」都是在訂閱方案頁的正常操作問題，併為一細目；扣款失敗的異常處置從既有細目拆出為另一細目（另見）；3457 的自動續訂與付款紀錄段落歸此",
    "target_user": [
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/I/subscription-payment-failure",
    "coarse_id": "I",
    "title": "訂閱扣款失敗、方案失效與物件被下架怎麼恢復",
    "slug": "subscription-payment-failure",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3509",
     "tmp:kb:3457"
    ],
    "split_from": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3457"
    ],
    "moved_from": [],
    "reason": "「扣款失敗／功能突然不能用／物件全被下架」是排障型提問，與正常變更操作的提問路徑不同，自既有 subscription-change-renewal 拆出；3509 整筆與 3457 的扣款失敗段落歸此",
    "target_user": [
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適合嗎",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:canon:jgb/I/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「我們是公司／代管團隊適不適合」按受眾型態問的獨立問題",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:canon:jgb/I/why-choose-jgb"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「你們優勢是什麼」獨立一問，不點名競品時的落點；點名競品另見 competitor-comparison",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/onboarding-steps-overview",
    "coarse_id": "I",
    "title": "導入起步：新手上路步驟總覽與教學索引",
    "slug": "onboarding-steps-overview",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「剛加入要從哪開始／有沒有教學／導入要做哪些步驟」的入口問題；draft:1 是房東教學總論的章節大綱（註冊→物件→合約→收款設置→帳務→社宅→修繕→設備），作為導入路線圖的索引細目，各篇操作細節另見 H 幫助中心",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/I/competitor-comparison",
    "new": "jgb/I/competitor-comparison",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/competitor-neutrality",
    "new": "jgb/I/competitor-neutrality",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3798",
    "new": "jgb/I/competitor-neutrality",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/dashboard-overview",
    "new": "jgb/I/dashboard-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/data-migration",
    "new": "jgb/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3476",
    "new": "jgb/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/free-trial",
    "new": "jgb/I/free-trial",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/individual-landlord-scale-fit",
    "new": "jgb/I/individual-landlord-scale-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/pricing-plans",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:5376",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3453",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/product-overview",
    "new": "jgb/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3798",
    "new": "jgb/I/product-overview",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/property-quota-limit",
    "new": "jgb/I/property-quota-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-change-renewal",
    "op": "split"
   },
   {
    "old": "tmp:kb:3454",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3356",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3455",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3457",
    "new": "jgb/I/subscription-change-renewal",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-payment-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:3509",
    "new": "jgb/I/subscription-payment-failure",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3457",
    "new": "jgb/I/subscription-payment-failure",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/team-company-fit",
    "new": "jgb/I/team-company-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/why-choose-jgb",
    "new": "jgb/I/why-choose-jgb",
    "op": "keep"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/I/onboarding-steps-overview",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2909",
    "suggested_shelf": "E",
    "why": "租客受眾的租金行情參考，屬租金／帳務主題，非方案與導入"
   },
   {
    "id": "tmp:kb:2910",
    "suggested_shelf": "E",
    "why": "租客受眾的社區管理費說明，費用項目歸帳務"
   },
   {
    "id": "tmp:kb:2911",
    "suggested_shelf": "E",
    "why": "公共費用分攤怎麼算，錢怎麼算歸帳務"
   },
   {
    "id": "tmp:kb:2913",
    "suggested_shelf": "E",
    "why": "租金溢繳退還，帳單金額處理歸帳務"
   },
   {
    "id": "tmp:kb:2918",
    "suggested_shelf": "E",
    "why": "租金繳費期限出現在帳單列上，歸帳務"
   },
   {
    "id": "tmp:kb:2920",
    "suggested_shelf": "E",
    "why": "租金折扣條件屬租金怎麼算，歸帳務"
   },
   {
    "id": "tmp:kb:2921",
    "suggested_shelf": "E",
    "why": "租金支付證明（收據／發票／轉帳明細）歸帳務"
   },
   {
    "id": "tmp:kb:2924",
    "suggested_shelf": "D",
    "why": "租金支付的法律依據來自租賃契約條款，歸租約"
   },
   {
    "id": "tmp:kb:2925",
    "suggested_shelf": "E",
    "why": "租金市場變化為租金主題，與 2909 同類，歸帳務"
   },
   {
    "id": "tmp:kb:2977",
    "suggested_shelf": "D",
    "why": "寵物是否加收費用由租約條款決定，歸租約"
   },
   {
    "id": "tmp:kb:3006",
    "suggested_shelf": "D",
    "why": "租屋保險為租客承租相關事項，非 JGB 方案；最接近租約"
   },
   {
    "id": "tmp:kb:3035",
    "suggested_shelf": "D",
    "why": "戶籍遷移與租約有效性／租住權益相關，歸租約"
   },
   {
    "id": "tmp:kb:3047",
    "suggested_shelf": "D",
    "why": "居住證明申請為租客承租事項，最接近租約"
   },
   {
    "id": "tmp:kb:3105",
    "suggested_shelf": "E",
    "why": "管理費用途與 2910 同題，費用項目歸帳務"
   },
   {
    "id": "tmp:kb:3158",
    "suggested_shelf": "E",
    "why": "業者（包租代管）服務費按租金比例計算，是錢怎麼算，非 JGB 訂閱收費，歸帳務"
   },
   {
    "id": "tmp:kb:3207",
    "suggested_shelf": "E",
    "why": "租金少繳補繳為帳單金額處理，歸帳務"
   },
   {
    "id": "tmp:kb:3208",
    "suggested_shelf": "E",
    "why": "遲繳罰款／滯納金出現在帳單列上，歸帳務"
   },
   {
    "id": "tmp:kb:3209",
    "suggested_shelf": "E",
    "why": "租金包含哪些項目是費用組成，錢怎麼算歸帳務"
   },
   {
    "id": "tmp:kb:3210",
    "suggested_shelf": "D",
    "why": "租金爭議解決以租賃契約為依據，歸租約"
   },
   {
    "id": "tmp:kb:3478",
    "suggested_shelf": "E",
    "why": "邀請租客訂閱通知是投遞管道，通知的是帳單／繳費提醒，歸帳務、不自成細目"
   },
   {
    "id": "tmp:kb:3850",
    "suggested_shelf": "D",
    "why": "點退找補在合約細節的點退清單操作，由合約驅動，歸租約"
   },
   {
    "id": "tmp:kb:4261",
    "suggested_shelf": "E",
    "why": "空內文入口，題為停車費／車位費，費用項目歸帳務"
   },
   {
    "id": "tmp:kb:4271",
    "suggested_shelf": "E",
    "why": "空內文入口，題為社區管理費為何收與怎麼算，與 2910／3105 同題歸帳務"
   },
   {
    "id": "tmp:kb:4275",
    "suggested_shelf": "E",
    "why": "空內文入口，題為機車汽車停車位費用，費用項目歸帳務"
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
    "id": "jgb/I/competitor-comparison",
    "coarse_id": "I",
    "title": "跟 Bananas、屋我也差在哪",
    "slug": "competitor-comparison",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-comparison"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目內容自成一題（同類系統差異），無新材料可吸收；競品內容依既有 deliberate_no 規則處理，不擴充。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/competitor-neutrality",
    "coarse_id": "I",
    "title": "會評論競爭對手嗎",
    "slug": "competitor-neutrality",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-neutrality",
     "tmp:kb:3798"
    ],
    "split_from": [
     "tmp:kb:3798"
    ],
    "moved_from": [],
    "reason": "tmp:kb:3798 的「競品處理協定」段是本細目答法的規則基礎，兩者互相依賴才完整（協定沒有答法無法對外、答法沒有協定無邊界），故拆該段併入；其餘段落屬別題。",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/dashboard-overview",
    "coarse_id": "I",
    "title": "首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:canon:jgb/I/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "儀表板三區塊自成一題，與其他細目無內容依賴。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入範圍、不支援項目與租客批次匯入操作）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:canon:jgb/I/data-migration",
     "tmp:kb:3476"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "tmp:kb:3476 是既有細目所列「租客可批次匯入」這一項的操作步驟，離開匯入範圍脈絡即失去「導入」語義，屬同一題的操作面而非新主題。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:canon:jgb/I/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "試用資格與開通自成一題；額度細節由 property-quota-limit 另見，不重複。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/individual-landlord-scale-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適配與建議做法",
    "slug": "individual-landlord-scale-fit",
    "merge_of": [
     "tmp:canon:jgb/I/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "個人房東規模適配自成一題，無新材料。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費與方案分級差異",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:canon:jgb/I/pricing-plans",
     "tmp:kb:3453",
     "tmp:kb:5376"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "tmp:kb:5376 內文與既有細目逐字相同（純講法入口）；tmp:kb:3453 說明方案等級差異（物件數、大房東數、進階功能），與「依規模與功能分級收費」是同一命題的兩面，缺一即不完整，故合為一題。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題與適不適合我（含情境→功能索引與出口）",
    "slug": "product-overview",
    "merge_of": [
     "tmp:canon:jgb/I/product-overview",
     "tmp:kb:3798"
    ],
    "split_from": [
     "tmp:kb:3798"
    ],
    "moved_from": [],
    "reason": "既有細目以「先選一個您最想改善的」收尾而無下文，tmp:kb:3798 的「功能對照索引」與「CTA 出口慣例」正是該收尾的接續（情境→推薦模組→出口），兩者互相依賴才完整，故拆該兩段併入。",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限與用滿怎麼辦",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:canon:jgb/I/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "額度上限與用滿處置自成一題；方案分級差異由 pricing-plans 另見。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級／變更方案、付款紀錄與自動續約",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3454",
     "tmp:kb:3457"
    ],
    "split_from": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3457"
    ],
    "moved_from": [],
    "reason": "既有細目混裝三個各自完整的主題（變更方案／取消訂閱／扣款失敗），依內容邊界拆開：本細目保留「變更方案＋付款紀錄＋自動續約」，吸收 tmp:kb:3454（升級操作）與 tmp:kb:3457 的付款紀錄／自動續訂段；取消與扣款失敗各自獨立成題。",
    "target_user": [
     "property_manager"
    ],
    "op": "split"
   },
   {
    "id": "jgb/I/subscription-cancel",
    "coarse_id": "I",
    "title": "取消訂閱的操作與影響",
    "slug": "subscription-cancel",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3356",
     "tmp:kb:3455"
    ],
    "split_from": [
     "tmp:canon:jgb/I/subscription-change-renewal"
    ],
    "moved_from": [],
    "reason": "取消訂閱（操作路徑＋生效時點＋超額物件下架＋資料保留）不依賴變更方案即可完整回答，與升級／續約是不同主題；由既有細目拆出取消句，併 tmp:kb:3356 與 tmp:kb:3455。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/I/subscription-payment-failure",
    "coarse_id": "I",
    "title": "訂閱扣款失敗：方案失效、物件下架與恢復",
    "slug": "subscription-payment-failure",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3457",
     "tmp:kb:3509"
    ],
    "split_from": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3457"
    ],
    "moved_from": [],
    "reason": "扣款失敗的後果與恢復步驟是獨立的排障題，不依賴變更或取消即可完整；由既有細目拆出扣款失敗句、tmp:kb:3457 拆出扣款失敗段，併 tmp:kb:3509。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適合嗎",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:canon:jgb/I/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "團隊規模適配自成一題，無新材料。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:canon:jgb/I/why-choose-jgb"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "選擇理由自成一題；與 competitor-comparison 不同層級（自述優勢 vs 對照），另見不重複。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/onboarding-tutorial-index",
    "coarse_id": "I",
    "title": "房東新手教學總覽（從哪開始、各篇教學有哪些）",
    "slug": "onboarding-tutorial-index",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "tmp:draft:1 是新加入管理者的教學導覽地圖（註冊→物件→合約→收款→帳務→社宅→修繕→設備），本身是獨立可答的「導入從哪開始」主題；各篇操作內容屬各自領域架，此處只保留地圖不展開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/I/competitor-comparison",
    "new": "jgb/I/competitor-comparison",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/competitor-neutrality",
    "new": "jgb/I/competitor-neutrality",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3798",
    "new": "jgb/I/competitor-neutrality",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/dashboard-overview",
    "new": "jgb/I/dashboard-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/data-migration",
    "new": "jgb/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3476",
    "new": "jgb/I/data-migration",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/free-trial",
    "new": "jgb/I/free-trial",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/individual-landlord-scale-fit",
    "new": "jgb/I/individual-landlord-scale-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/pricing-plans",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3453",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:5376",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/product-overview",
    "new": "jgb/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3798",
    "new": "jgb/I/product-overview",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/property-quota-limit",
    "new": "jgb/I/property-quota-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-change-renewal",
    "op": "split"
   },
   {
    "old": "tmp:kb:3454",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3457",
    "new": "jgb/I/subscription-change-renewal",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-cancel",
    "op": "split"
   },
   {
    "old": "tmp:kb:3356",
    "new": "jgb/I/subscription-cancel",
    "op": "new"
   },
   {
    "old": "tmp:kb:3455",
    "new": "jgb/I/subscription-cancel",
    "op": "new"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-payment-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:3457",
    "new": "jgb/I/subscription-payment-failure",
    "op": "split"
   },
   {
    "old": "tmp:kb:3509",
    "new": "jgb/I/subscription-payment-failure",
    "op": "new"
   },
   {
    "old": "tmp:canon:jgb/I/team-company-fit",
    "new": "jgb/I/team-company-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/why-choose-jgb",
    "new": "jgb/I/why-choose-jgb",
    "op": "keep"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/I/onboarding-tutorial-index",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2909",
    "suggested_shelf": "D",
    "why": "租客視角的租金行情參考，租金水準由租約決定；非方案與導入。"
   },
   {
    "id": "tmp:kb:2910",
    "suggested_shelf": "E",
    "why": "管理費是帳單列上的費用項目（錢怎麼算歸帳務）；非方案與導入。"
   },
   {
    "id": "tmp:kb:2911",
    "suggested_shelf": "E",
    "why": "公共費用分攤是費用計算（錢怎麼算歸帳務）；非方案與導入。"
   },
   {
    "id": "tmp:kb:2913",
    "suggested_shelf": "E",
    "why": "租金溢繳退還是收款金流處置；非方案與導入。"
   },
   {
    "id": "tmp:kb:2918",
    "suggested_shelf": "E",
    "why": "租金支付期限是帳單繳款期（錢怎麼進來歸帳務）；非方案與導入。"
   },
   {
    "id": "tmp:kb:2920",
    "suggested_shelf": "E",
    "why": "租金折扣條件是租金計算（錢怎麼算歸帳務）；非方案與導入。"
   },
   {
    "id": "tmp:kb:2921",
    "suggested_shelf": "E",
    "why": "租金支付證明（收據／發票／轉帳明細）屬帳務；非方案與導入。"
   },
   {
    "id": "tmp:kb:2924",
    "suggested_shelf": "D",
    "why": "租金支付的法律依據是租賃契約條款；非方案與導入。"
   },
   {
    "id": "tmp:kb:2925",
    "suggested_shelf": "D",
    "why": "租客視角的租金市場變化，租金由租約決定；非方案與導入。"
   },
   {
    "id": "tmp:kb:2977",
    "suggested_shelf": "D",
    "why": "寵物費用是否收取由租約條款決定；非方案與導入。"
   },
   {
    "id": "tmp:kb:3006",
    "suggested_shelf": "D",
    "why": "租屋保險費用是租客租住期間常識，附隨租約；非方案與導入。"
   },
   {
    "id": "tmp:kb:3035",
    "suggested_shelf": "D",
    "why": "戶籍遷移與租約有效性／租住權益相關；非方案與導入。"
   },
   {
    "id": "tmp:kb:3047",
    "suggested_shelf": "D",
    "why": "居住證明申請是租客租住權益事項；非方案與導入。"
   },
   {
    "id": "tmp:kb:3105",
    "suggested_shelf": "E",
    "why": "管理費用途與 tmp:kb:2910 同題，屬帳單費用項目；非方案與導入。"
   },
   {
    "id": "tmp:kb:3158",
    "suggested_shelf": "D",
    "why": "業者向房東收的服務費依租金比例、由合約決定，屬委託約子題；⛔ 非金箍棒訂閱費用。"
   },
   {
    "id": "tmp:kb:3207",
    "suggested_shelf": "E",
    "why": "租金少繳補繳是收款處置；非方案與導入。"
   },
   {
    "id": "tmp:kb:3208",
    "suggested_shelf": "E",
    "why": "租金遲繳罰款出現在帳單列上（滯納金）；非方案與導入。"
   },
   {
    "id": "tmp:kb:3209",
    "suggested_shelf": "D",
    "why": "租金包含哪些項目由租約條款決定；非方案與導入。"
   },
   {
    "id": "tmp:kb:3210",
    "suggested_shelf": "D",
    "why": "租金爭議解決是租約權益事項；非方案與導入。"
   },
   {
    "id": "tmp:kb:3478",
    "suggested_shelf": "B",
    "why": "「邀請租客訂閱通知」的「訂閱」指通知投遞而非訂閱方案，屬租客（人員）管理操作；非方案與導入。"
   },
   {
    "id": "tmp:kb:3850",
    "suggested_shelf": "D",
    "why": "點退找補在合約細節的點退清單操作、由合約驅動；非方案與導入。"
   },
   {
    "id": "tmp:kb:4261",
    "suggested_shelf": "E",
    "why": "空內文入口，標題主題為停車費用（帳單費用項目）；非方案與導入，且空內文不得獨立成細目。"
   },
   {
    "id": "tmp:kb:4271",
    "suggested_shelf": "E",
    "why": "空內文入口，標題主題為管理費計算（與 tmp:kb:2910／3105 同題）；非方案與導入，且空內文不得獨立成細目。"
   },
   {
    "id": "tmp:kb:4275",
    "suggested_shelf": "E",
    "why": "空內文入口，標題主題為停車位費用（帳單費用項目）；非方案與導入，且空內文不得獨立成細目。"
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
    "id": "jgb/I/competitor-comparison",
    "coarse_id": "I",
    "title": "跟 Bananas、屋我也差在哪",
    "slug": "competitor-comparison",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-comparison"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前權益／能力層：潛在客戶問差異；競品內容不擴充，policy 由既有 deliberate_no 規則處理。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/competitor-neutrality",
    "coarse_id": "I",
    "title": "會評論競爭對手嗎",
    "slug": "competitor-neutrality",
    "merge_of": [
     "tmp:canon:jgb/I/competitor-neutrality"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前立場層：只回應是否評論同業，與競品比較分屬不同命題；policy 由既有 deliberate_no 規則處理。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/dashboard-overview",
    "coarse_id": "I",
    "title": "首頁儀表板顯示哪些數據",
    "slug": "dashboard-overview",
    "merge_of": [
     "tmp:canon:jgb/I/dashboard-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層：儀表板呈現什麼，潛在客戶與已使用管理者答案相同，共用一細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/data-migration",
    "coarse_id": "I",
    "title": "舊系統資料能否匯入（可匯入範圍與不支援項目）",
    "slug": "data-migration",
    "merge_of": [
     "tmp:canon:jgb/I/data-migration"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層：導入時哪些資料可搬、哪些不行；實際批次匯入操作步驟另見 jgb/I/bulk-import-operations（操作層）。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/free-trial",
    "coarse_id": "I",
    "title": "可以免費試用嗎",
    "slug": "free-trial",
    "merge_of": [
     "tmp:canon:jgb/I/free-trial"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前權益層：試用資格與期間；額度細節另見 jgb/I/property-quota-limit。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/individual-landlord-scale-fit",
    "coarse_id": "I",
    "title": "個人房東（約 10～30 戶）適配與建議做法",
    "slug": "individual-landlord-scale-fit",
    "merge_of": [
     "tmp:canon:jgb/I/individual-landlord-scale-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前適配層：受眾為個人房東規模的潛在客戶，與團隊適配分屬不同受眾段。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/pricing-plans",
    "coarse_id": "I",
    "title": "怎麼收費與方案分級差異",
    "slug": "pricing-plans",
    "merge_of": [
     "tmp:canon:jgb/I/pricing-plans",
     "tmp:kb:5376",
     "tmp:kb:3453"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層：收費方式與各級方案差在哪（物件數、大房東數、進階功能）是同一命題；kb:5376 與既有內容逐字相同、kb:3453 補方案分級差異；升級操作另見 jgb/I/subscription-change-renewal。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/product-overview",
    "coarse_id": "I",
    "title": "系統總覽、能解決什麼問題與適不適合我",
    "slug": "product-overview",
    "merge_of": [
     "tmp:canon:jgb/I/product-overview",
     "tmp:kb:3798"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前能力層：情境→模組對照；kb:3798 的功能對照索引併入此細目，其競品協定段為既有 deliberate_no policy 已涵蓋、CTA 出口表為路由慣例非知識內容，均不新增內容。",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/property-quota-limit",
    "coarse_id": "I",
    "title": "方案物件額度上限與用滿怎麼辦",
    "slug": "property-quota-limit",
    "merge_of": [
     "tmp:canon:jgb/I/property-quota-limit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層：額度規則與用滿的選項，潛在客戶問免費額度、管理者問用滿怎麼辦，答案同源；方案變更操作另見 jgb/I/subscription-change-renewal。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/subscription-change-renewal",
    "coarse_id": "I",
    "title": "升級、續約、取消訂閱與扣款失敗處理",
    "slug": "subscription-change-renewal",
    "merge_of": [
     "tmp:canon:jgb/I/subscription-change-renewal",
     "tmp:kb:3356",
     "tmp:kb:3454",
     "tmp:kb:3455",
     "tmp:kb:3457",
     "tmp:kb:3509"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：管理者對訂閱的變更、取消、自動續訂／付款紀錄、扣款失敗復原都是同一主題「訂閱管理」的操作，同受眾同層級只留一細目；kb 3356/3454/3455/3457/3509 併入（其中 3455 與 3457 對取消／扣款失敗後果的描述與既有內容不一致，留待內容審核，本步不判真偽）。",
    "target_user": [
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/I/team-company-fit",
    "coarse_id": "I",
    "title": "公司或包租代管團隊適合嗎",
    "slug": "team-company-fit",
    "merge_of": [
     "tmp:canon:jgb/I/team-company-fit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前適配層：受眾為公司／團隊規模的潛在客戶。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/why-choose-jgb",
    "coarse_id": "I",
    "title": "為什麼選金箍棒",
    "slug": "why-choose-jgb",
    "merge_of": [
     "tmp:canon:jgb/I/why-choose-jgb"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "售前價值層：選擇理由，與系統總覽（情境→模組）分屬不同命題。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/I/bulk-import-operations",
    "coarse_id": "I",
    "title": "批次匯入的操作步驟（租客 Excel 範本）",
    "slug": "bulk-import-operations",
    "merge_of": [
     "tmp:kb:3476"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：與 data-migration（能力層：能不能匯入）同主題但不同層級，依角度另立細目並互相另見，不重複能力層內容。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/I/landlord-onboarding-guide",
    "coarse_id": "I",
    "title": "房東新手導入教學總覽（各篇索引）",
    "slug": "landlord-onboarding-guide",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層入口：新加入管理者的導入教學總覽，只保留各篇索引與導入順序；各篇實際操作內容分屬 A/B/C/D/E/F/G 架，此細目以另見引用、不重複。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/I/competitor-comparison",
    "new": "jgb/I/competitor-comparison",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/competitor-neutrality",
    "new": "jgb/I/competitor-neutrality",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/dashboard-overview",
    "new": "jgb/I/dashboard-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/data-migration",
    "new": "jgb/I/data-migration",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/free-trial",
    "new": "jgb/I/free-trial",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/individual-landlord-scale-fit",
    "new": "jgb/I/individual-landlord-scale-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/pricing-plans",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:5376",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3453",
    "new": "jgb/I/pricing-plans",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/product-overview",
    "new": "jgb/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3798",
    "new": "jgb/I/product-overview",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/property-quota-limit",
    "new": "jgb/I/property-quota-limit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/subscription-change-renewal",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3356",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3454",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3455",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3457",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3509",
    "new": "jgb/I/subscription-change-renewal",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/I/team-company-fit",
    "new": "jgb/I/team-company-fit",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/I/why-choose-jgb",
    "new": "jgb/I/why-choose-jgb",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3476",
    "new": "jgb/I/bulk-import-operations",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/I/landlord-onboarding-guide",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2909",
    "suggested_shelf": "E",
    "why": "租客受眾的租金行情參考，屬錢怎麼算（帳務）而非售前方案與導入。"
   },
   {
    "id": "tmp:kb:2910",
    "suggested_shelf": "E",
    "why": "租客受眾的管理費是什麼，出現在帳單列上歸帳務。"
   },
   {
    "id": "tmp:kb:2911",
    "suggested_shelf": "E",
    "why": "公共費用分攤怎麼算歸帳務。"
   },
   {
    "id": "tmp:kb:2913",
    "suggested_shelf": "E",
    "why": "租金溢繳退還屬帳務收款處理。"
   },
   {
    "id": "tmp:kb:2918",
    "suggested_shelf": "D",
    "why": "租金支付期限由合約條款決定，歸租約。"
   },
   {
    "id": "tmp:kb:2920",
    "suggested_shelf": "D",
    "why": "租金折扣條件由合約條款決定，歸租約。"
   },
   {
    "id": "tmp:kb:2921",
    "suggested_shelf": "E",
    "why": "租金支付證明（收據／發票／交易紀錄）歸帳務含發票子題。"
   },
   {
    "id": "tmp:kb:2924",
    "suggested_shelf": "D",
    "why": "租金支付法律依據來自租賃契約，歸租約。"
   },
   {
    "id": "tmp:kb:2925",
    "suggested_shelf": "E",
    "why": "租客受眾的租金市場變化，與 kb:2909 同題，歸帳務錢怎麼算。"
   },
   {
    "id": "tmp:kb:2977",
    "suggested_shelf": "D",
    "why": "寵物費用取決於租約條款，歸租約。"
   },
   {
    "id": "tmp:kb:3006",
    "suggested_shelf": "D",
    "why": "租客租屋保險屬租住須知，非 JGB 方案；若保留歸租約子題。"
   },
   {
    "id": "tmp:kb:3035",
    "suggested_shelf": "D",
    "why": "戶籍遷移屬租住權益、以租約有效性為主體，歸租約。"
   },
   {
    "id": "tmp:kb:3047",
    "suggested_shelf": "D",
    "why": "居住證明申請屬租住權益，歸租約。"
   },
   {
    "id": "tmp:kb:3105",
    "suggested_shelf": "E",
    "why": "管理費用途與 kb:2910 同題，歸帳務。"
   },
   {
    "id": "tmp:kb:3158",
    "suggested_shelf": "D",
    "why": "業者向房東收取的代管服務費由委託約決定，歸租約的委託約子題；非 JGB 訂閱收費。"
   },
   {
    "id": "tmp:kb:3207",
    "suggested_shelf": "E",
    "why": "租金少繳補繳屬帳務收款處理。"
   },
   {
    "id": "tmp:kb:3208",
    "suggested_shelf": "E",
    "why": "遲繳罰款（滯納金）出現在帳單列上，歸帳務。"
   },
   {
    "id": "tmp:kb:3209",
    "suggested_shelf": "D",
    "why": "租金包含哪些項目由合約條款決定，歸租約。"
   },
   {
    "id": "tmp:kb:3210",
    "suggested_shelf": "D",
    "why": "租金爭議解決屬租約權益層，歸租約。"
   },
   {
    "id": "tmp:kb:3478",
    "suggested_shelf": "A",
    "why": "邀請租客訂閱通知屬租客帳號綁定；通知是投遞管道不自成細目，歸它所通知的帳號身分領域。"
   },
   {
    "id": "tmp:kb:3850",
    "suggested_shelf": "D",
    "why": "點退找補在合約細節的點退清單操作，由合約驅動，歸租約；產生的帳單另見帳務。"
   },
   {
    "id": "tmp:kb:4261",
    "suggested_shelf": "E",
    "why": "空內文入口，停車費屬錢怎麼算歸帳務；空列不獨立成細目。"
   },
   {
    "id": "tmp:kb:4271",
    "suggested_shelf": "E",
    "why": "空內文入口，管理費怎麼算與 kb:2910/3105 同題歸帳務；空列不獨立成細目。"
   },
   {
    "id": "tmp:kb:4275",
    "suggested_shelf": "E",
    "why": "空內文入口，車位費用與 kb:4261 同題歸帳務；空列不獨立成細目。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。