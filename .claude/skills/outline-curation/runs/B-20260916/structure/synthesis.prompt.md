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
⚠️ 本次為擴充模式，**只補一架（B）**：候選項目分兩種——`tmp:canon:*`（B 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `B`，`id` 必須為 `jgb/B/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/B/owner-report-collection-remit", "tmp:canon:jgb/B/role-permission-granularity", "tmp:canon:jgb/B/team-management-overview", "tmp:canon:jgb/B/what-is-owner-landlord", "tmp:kb:2980", "tmp:kb:3084", "tmp:kb:3085", "tmp:kb:3086", "tmp:kb:3087", "tmp:kb:3088", "tmp:kb:3091", "tmp:kb:3092", "tmp:kb:3094", "tmp:kb:3095", "tmp:kb:3096", "tmp:kb:3254", "tmp:kb:3255", "tmp:kb:3303", "tmp:kb:3304", "tmp:kb:3305", "tmp:kb:3306", "tmp:kb:3307", "tmp:kb:3308", "tmp:kb:3309", "tmp:kb:3310", "tmp:kb:3312", "tmp:kb:3326", "tmp:kb:3359", "tmp:kb:3360", "tmp:kb:3438", "tmp:kb:3439", "tmp:kb:3463", "tmp:kb:3464", "tmp:kb:3465", "tmp:kb:3467", "tmp:kb:3480", "tmp:kb:3482", "tmp:kb:3543", "tmp:kb:3544", "tmp:kb:3545", "tmp:kb:3546", "tmp:kb:3547", "tmp:kb:3974", "tmp:kb:3981", "tmp:kb:3982", "tmp:kb:4224", "tmp:kb:4250", "tmp:kb:4251", "tmp:kb:4272", "tmp:draft:1"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/B/owner-report-collection-remit", "tmp:canon:jgb/B/role-permission-granularity", "tmp:canon:jgb/B/team-management-overview", "tmp:canon:jgb/B/what-is-owner-landlord", "tmp:kb:2980", "tmp:kb:3084", "tmp:kb:3085", "tmp:kb:3086", "tmp:kb:3087", "tmp:kb:3088", "tmp:kb:3091", "tmp:kb:3092", "tmp:kb:3094", "tmp:kb:3095", "tmp:kb:3096", "tmp:kb:3254", "tmp:kb:3255", "tmp:kb:3303", "tmp:kb:3304", "tmp:kb:3305", "tmp:kb:3306", "tmp:kb:3307", "tmp:kb:3308", "tmp:kb:3309", "tmp:kb:3310", "tmp:kb:3312", "tmp:kb:3326", "tmp:kb:3359", "tmp:kb:3360", "tmp:kb:3438", "tmp:kb:3439", "tmp:kb:3463", "tmp:kb:3464", "tmp:kb:3465", "tmp:kb:3467", "tmp:kb:3480", "tmp:kb:3482", "tmp:kb:3543", "tmp:kb:3544", "tmp:kb:3545", "tmp:kb:3546", "tmp:kb:3547", "tmp:kb:3974", "tmp:kb:3981", "tmp:kb:3982", "tmp:kb:4224", "tmp:kb:4250", "tmp:kb:4251", "tmp:kb:4272", "tmp:draft:1"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/B/owner-report-collection-remit", "tmp:canon:jgb/B/role-permission-granularity", "tmp:canon:jgb/B/team-management-overview", "tmp:canon:jgb/B/what-is-owner-landlord", "tmp:kb:2980", "tmp:kb:3084", "tmp:kb:3085", "tmp:kb:3086", "tmp:kb:3087", "tmp:kb:3088", "tmp:kb:3091", "tmp:kb:3092", "tmp:kb:3094", "tmp:kb:3095", "tmp:kb:3096", "tmp:kb:3254", "tmp:kb:3255", "tmp:kb:3303", "tmp:kb:3304", "tmp:kb:3305", "tmp:kb:3306", "tmp:kb:3307", "tmp:kb:3308", "tmp:kb:3309", "tmp:kb:3310", "tmp:kb:3312", "tmp:kb:3326", "tmp:kb:3359", "tmp:kb:3360", "tmp:kb:3438", "tmp:kb:3439", "tmp:kb:3463", "tmp:kb:3464", "tmp:kb:3465", "tmp:kb:3467", "tmp:kb:3480", "tmp:kb:3482", "tmp:kb:3543", "tmp:kb:3544", "tmp:kb:3545", "tmp:kb:3546", "tmp:kb:3547", "tmp:kb:3974", "tmp:kb:3981", "tmp:kb:3982", "tmp:kb:4224", "tmp:kb:4250", "tmp:kb:4251", "tmp:kb:4272", "tmp:draft:1"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/B/owner-report-collection-remit", "tmp:canon:jgb/B/role-permission-granularity", "tmp:canon:jgb/B/team-management-overview", "tmp:canon:jgb/B/what-is-owner-landlord", "tmp:kb:2980", "tmp:kb:3084", "tmp:kb:3085", "tmp:kb:3086", "tmp:kb:3087", "tmp:kb:3088", "tmp:kb:3091", "tmp:kb:3092", "tmp:kb:3094", "tmp:kb:3095", "tmp:kb:3096", "tmp:kb:3254", "tmp:kb:3255", "tmp:kb:3303", "tmp:kb:3304", "tmp:kb:3305", "tmp:kb:3306", "tmp:kb:3307", "tmp:kb:3308", "tmp:kb:3309", "tmp:kb:3310", "tmp:kb:3312", "tmp:kb:3326", "tmp:kb:3359", "tmp:kb:3360", "tmp:kb:3438", "tmp:kb:3439", "tmp:kb:3463", "tmp:kb:3464", "tmp:kb:3465", "tmp:kb:3467", "tmp:kb:3480", "tmp:kb:3482", "tmp:kb:3543", "tmp:kb:3544", "tmp:kb:3545", "tmp:kb:3546", "tmp:kb:3547", "tmp:kb:3974", "tmp:kb:3981", "tmp:kb:3982", "tmp:kb:4224", "tmp:kb:4250", "tmp:kb:4251", "tmp:kb:4272", "tmp:draft:1"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（50 筆，原序列舉）
### tmp:canon:jgb/B/owner-report-collection-remit
標題：大房東報表與代收代付怎麼交代
內容：要定期跟業主交報表很花時間？ 金箍棒的大房東報表能把代收代付、月結與營運狀況整理成報表，並可排程自動寄送給業主，省去人工彙整。 想看報表內容可預約 demo。 代管業者對房東的月結差額，系統每月自動整理成差額發票群組並開立，次月重新計算。

### tmp:canon:jgb/B/role-permission-granularity
標題：成員權限能不能細分（只看不改、看不到財務）
內容：可以。 金箍棒的權限依八大功能分類（物件、合約、帳務、修繕、通知、團隊、人員、大房東管理），每類再細分查看、編輯、新增等項目；不給某位成員「查看帳務」，他就看不到帳務圖表、收付款與屋主帳單。 系統內建擁有者、最高管理者、店長、會計、一般業務等十種範本角色，也可以自訂角色；還能把物件指派給經理人，只給他該物件與對應合約的查看／編輯權限。

### tmp:canon:jgb/B/team-management-overview
標題：團隊管理模組做什麼
內容：人多、管不動？ 金箍棒的團隊管理支援多人帳號與角色權限，讓代管團隊分工協作，並提供大房東報表對業主交代。 系統沒有叫「系統管理」的模組；成員、角色權限、訂閱方案這類設定都在團隊管理裡。 想了解團隊方案可預約 demo 由專人說明。

### tmp:canon:jgb/B/what-is-owner-landlord
標題：大房東是什麼
內容：在金箍棒裡，「大房東」指的是把物件交給您代管的業主。 物管團隊可以在大房東列表用 email 邀請業主，並把特定物件授權給他，業主登入後就能瀏覽自己物件的合約、帳務與修繕狀態，不必逐一問您。 搭配大房東報表，代收代付與月結會自動整理並可排程寄給業主。 想看業主端的畫面可預約 demo。

### tmp:kb:2980
標題：公共區域使用權限
內容：租客在公共區域的使用權限通常包括進入、使用和享受公共設施，但不得妨礙其他租客的使用權。具體限制可能包括禁止在公共區域吸煙、存放個人物品或進行商業活動。請參考租約或聯繫您的管理師以獲取詳細資訊。

### tmp:kb:3084
標題：包租業定義
內容：包租業是指業主將房產租給專業公司，該公司負責整個租賃過程的管理，包括出租、維護和租金收取等。而包租代管則是這種業務的一部分，專注於代為管理房屋，讓業主能夠省去管理的麻煩。作為房客，您可以享有更專業的服務及更好的居住體驗。

### tmp:kb:3085
標題：代管業介紹
內容：代管業是專門負責管理租屋物件的服務，透過專業管理師協助房東與房客之間的溝通、租金收取、維修管理等事務，讓房客能夠享有更便利的居住體驗，並保障他們的權益。

### tmp:kb:3086
標題：包租代管差異
內容：包租業主要是將物業整體出租，業主將物件租給租客，並負責所有相關事務；而代管業則是為業主提供物業管理服務，包括協助物業出租、維護等，業主仍然擁有物件的所有權。房客在代管業中可享有更完善的服務，如維修保障和租金透明度等權益。

### tmp:kb:3087
標題：包租與代管差異
內容：包租業主要是將房東的房產整體租出，房東負責管理，而租客與房東直接簽約。代管業則是由代管公司負責管理房產，包括租金收取、維修等服務，租客則與代管公司簽約，享有更完善的服務及保障。

### tmp:kb:3088
標題：收費結構差異
內容：包租業通常收取固定的租金，租客需按月支付；而代管業則會收取管理費用，可能依照租金的比例計算。這意味著在選擇時，您需要了解自己所需的服務類型以及相關費用結構，以確保符合您的預算和需求。

### tmp:kb:3091
標題：包租業與代管業差異
內容：包租業主要是將整個房產租給包租公司，房東可獲得穩定租金，風險較低。而代管業則是房東自行出租，代管公司負責管理，房東需承擔租金風險，但可獲得更高的租金收益。房客在代管業中可享有更多的維修及服務保障。

### tmp:kb:3092
標題：管理費用差異
內容：包租業的管理費用通常包含房屋的租金收取、客戶服務及物業管理等，較為全面。而代管業的管理費用則主要集中在物業的日常維護與管理服務，可能不包括租金收取。這意味著作為房客，您應該了解這些費用的範疇，以確保您獲得的服務符合您的需求。

### tmp:kb:3094
標題：租金調整政策
內容：租金調整通常依據租約中的條款進行，主要規定包括：
1. 調整頻率：包租業通常在合約期結束時調整，代管業可能每年依市場行情調整
2. 調整方式：可能按市場行情、通貨膨脹率或約定百分比進行
3. 通知義務：調整前應提前通知租客

您有權了解調整的具體理由及幅度。如需確認具體條款，請查看租約或聯繫管理師。

### tmp:kb:3095
標題：包租業與代管業
內容：包租業主要是房東將房產出租給租客，房東負責所有管理和維護的法律責任。而代管業則是房東委託專業公司管理其房產，法律責任由代管公司承擔，這樣租客的權益可以更有保障，例如在維修和服務上的回應速度更快。

### tmp:kb:3096
標題：風險管理策略
內容：包租業通常承擔較多的風險，包括租金未支付及房屋損壞等，因此需要建立嚴謹的租約和風險評估機制。而代管業則重視物業的日常維護和租客的滿意度，風險管理主要集中在服務質量和客戶關係上。無論是哪一種業務模式，房客都應確保了解自己的權益，包括在租約中明確的維修責任和租金保障等。這樣可以在遇到問題時，依據合約要求相應的維護和補償。

### tmp:kb:3254
標題：法律責任差異
內容：包租業主要負責整個租賃過程，包括租金的收取和房屋管理，對租客的權益負有直接責任。而代管業則是為房東提供管理服務，承擔的責任相對較少，主要是在代為管理房屋的範疇內負責。租客應了解自己的權益，如租金透明、維修責任等，確保在合約中有明確的條款保障自身利益。

### tmp:kb:3255
標題：風險管理差異
內容：包租業的風險管理主要集中在租金收入的穩定性和租客信用評估上，例如選擇可靠的租客並進行租約保障。而代管業則更著重於物業的日常維護和管理風險，確保物業狀況良好，並快速處理租客的維修需求。作為房客，您有權要求及時的維修服務和物業安全保障。

### tmp:kb:3303
標題：包租業介紹
內容：包租業是指房東將房產出租給包租代管公司，後者負責整體管理、維護和出租事宜。這樣一來，房東可以獲得穩定收入，而租客則能享受到更專業的服務和維護。作為房客，您可以享有更完善的租住環境、專業的服務支持以及相關的租住保障。

### tmp:kb:3304
標題：代管業定義
內容：代管業是專門負責管理房屋租賃事務的服務，包含租金收取、房屋維護、租客管理等，讓房東和租客之間的溝通和交易更為順利。租客可以享有更便捷的服務與房屋管理，保障自己的居住權益。

### tmp:kb:3305
標題：包租代管服務差異
內容：包租業通常是房東將房屋出租給租客，由租客直接與房東簽約，而代管業則是房東將物業委託給專業公司管理，租客則與該公司簽約。這意味著租客在代管業中享有更專業的服務和管理，也能更方便地處理維修請求和其他問題。

### tmp:kb:3306
標題：包租業與代管業比較
內容：包租業通常是房東將房產全權出租給包租公司，管理和維護由公司負責，租客與包租公司直接打交道。而代管業則是房東將房產委託給代管公司，租客仍然與房東簽約，代管公司負責協助管理。租客的權益保障上，包租業可能提供更全方位的服務，如維修及客服支持，而代管業則強調與房東的直接聯繫，租客的問題可能需通過房東處理。

### tmp:kb:3307
標題：包租代管法律責任
內容：包租業通常負責整體租約的法律責任，包括租金收取和維護房屋的義務；而代管業主要是代理業主進行日常管理，因此法律責任相對較小，主要集中在維護租客權益和提供服務的範疇。房客享有的權益如房屋維修、租金透明等，應由代管方保障。

### tmp:kb:3308
標題：包租代管業務差異
內容：包租業主要是指業主將整個房產出租給包租公司，由公司負責整體管理和租金收入。而代管業則是業主將房產委託給代管公司，後者負責日常管理、維修及租客管理，業主仍擁有租金收入的權利。這兩者的主要差異在於業主對房產的控制程度及管理方式。

### tmp:kb:3309
標題：包租代管關係
內容：包租業主要是將物件出租給租客，而代管業則是負責物件的管理和維護。在客戶關係上，包租業通常較為單向，重點在於租約和租金的收取；而代管業則會提供更全面的服務，包括日常維護、租客溝通及問題處理，強調雙向的互動和支持。

### tmp:kb:3310
標題：包租與代管風險管理
內容：包租業主要風險在於租客的信用和租金的收回，通常會要求租客提供信用證明或擔保。而代管業則更注重物業的維護和管理，風險主要來自於物業損壞和維修問題。代管公司會制定維修計劃和保險措施以降低風險，並確保租客的居住品質。

### tmp:kb:3312
標題：代管服務費
內容：代管業的服務費比例通常會依據租金的百分比來計算，具體的比例可能會因公司政策或物件類型而有所不同。若您想了解您租屋的具體服務費比例，請提供您的物件地址，我幫您查詢。

### tmp:kb:3326
標題：包租代管租金代收與房東直收差異
內容：租金代收制度是由包租代管公司負責收取租金，房客只需按時繳納租金給公司，確保資金安全與透明。而房東直收制度則是房東直接向租客收取租金，可能會造成租金收取上的不便。如果選擇租金代收，房客的權益也能得到更好的保障，如及時的收據與透明的費用明細。

### tmp:kb:3359
標題：團隊 權限 成員 管理
內容：團隊成員可設定不同的操作權限，包括物件授權、帳務檢視等。團隊擁有者擁有最高權限。

物件可授權給特定團隊成員管理，授權後該成員可查看與操作指定物件的相關功能。

若需變更團隊主要負責人或綁定手機號碼，請透過異動單申請。

### tmp:kb:3360
標題：匯出 報表 收支明細
內容：系統支援匯出多種報表，包括收支明細表、差額發票收支表等。

操作時可依金流類型、日期範圍等條件篩選。

注意：報表只會抓取特定收款品項的帳單，若收款品項設定不同，可能導致部分帳單未帶入報表。如發現匯出資料不完整，請確認帳單的收款品項設定是否正確。

### tmp:kb:3438
標題：角色切換 房東租客
內容：同一帳號可以同時擁有多個身分（例如既是房東也是租客，或加入多個團隊）。切換方式：點畫面左上角的身分選單，選擇要切換的身分即可。系統會記住你上次使用的身分，下次登入直接落在該身分。提醒：每個身分看到的資料範圍不同——租客的合約、帳單、電表要在租客身分下才看得到，登入後覺得「資料不見了」多半是身分沒切對。

### tmp:kb:3439
標題：團隊成員 新增管理
內容：團隊成員管理讓法人房東團隊多人共同管理物件和合約。新增成員：進入團隊管理頁，輸入對方的 Email 或手機號碼加入（對方必須已註冊 JGB 會員），加入即時生效。重要：加入後請到成員列表為該成員「變更角色」指派角色——尚未指派角色的成員沒有任何權限，會看不到社區與物件、也無法新增資料。系統內建十種範本角色（最高管理者、店長、會計、一般業務等），也可自訂角色的功能權限。

### tmp:kb:3463
標題：大房東 概念說明
內容：大房東是 JGB 系統中的角色概念，指的是擁有多間物件、委託物管業者代為管理的房東。與一般房東直接管理物件不同，大房東的物件由物管團隊統一代管，大房東可透過系統查看自己名下物件的合約、帳單和報表資訊。物管業者可在系統中設定大房東帳號，並指定其可查看的物件範圍和權限。每個訂閱方案有大房東數量上限。

### tmp:kb:3464
標題：大房東新增 權限設定
內容：新增大房東操作：1. 進入大房東管理頁面，點選新增；2. 填寫大房東資訊（姓名、聯絡方式）；3. 設定物件存取權限（指定該大房東可查看哪些物件的合約和帳單）；4. 發送邀請通知。大房東權限可細分為：查看物件、查看合約、查看帳單等。權限設定後，大房東登入系統只能看到被授權範圍內的資料。若大房東尚未註冊 JGB 帳號，可發送邀請通知引導其完成註冊。

### tmp:kb:3465
標題：大房東月報表 報表功能
內容：大房東月報表功能：系統可自動產生大房東名下物件的月度財務報表，包含租金收入、費用支出、帳單狀態等彙總資訊。（1）手動檢視：大房東登入後在報表頁面查看；（2）排程發送：物管可設定定期自動將月報表以 Email 發送給大房東，支援指定發送日期；（3）手動上傳：物管可上傳自訂報表檔案供大房東下載。報表會在發送前發出預告通知。

### tmp:kb:3467
標題：大房東聯絡簿 批次匯入匯出
內容：大房東聯絡簿功能讓物管可以集中管理所有大房東的聯絡資訊。支援 Excel 批次匯入和匯出功能：（1）匯出：將所有大房東的聯絡資訊和綁定物件清冊匯出為 Excel 檔案；（2）匯入：透過 Excel 範本批次新增或更新大房東聯絡記錄。此功能方便物管進行大量資料維護，無需逐一手動修改。

### tmp:kb:3480
標題：房東租客大房東 各角色功能範圍
內容：JGB 系統各角色可使用的功能範圍：（1）房東/物管：所有功能皆可使用，包含物件管理、合約建立、帳單管理、修繕處理、訂閱方案、團隊管理、大房東管理、社區管理等；（2）租客：查看合約和帳單、線上繳費、確認點交/點退、提出修繕申請、查看 IoT 設備狀態、管理個人資料和簽約身份；（3）大房東：查看被授權的物件、合約、帳單資訊和月報表；（4）團隊成員：依被授權的權限範圍操作，可執行房東大部分功能。

### tmp:kb:3482
標題：看不到功能 權限不足
內容：在系統中找不到某功能或無法操作的可能原因：1. 角色限制：目前登入的角色不支援該功能（如租客無法看到物件管理），請確認是否需要切換角色；2. 訂閱方案限制：部分進階功能需要特定方案才能使用，請確認訂閱方案是否包含該功能；3. 團隊權限限制：團隊成員的權限可能未包含該功能，請聯繫團隊管理者調整權限；4. 功能開關：部分功能需由管理者在後台開啟（如差額發票），請聯繫客服確認。若以上都不是原因，請嘗試重新登入或清除瀏覽器快取。

### tmp:kb:3543
標題：大房東報表排程 自動寄送設定
內容：大房東報表可以設定排程自動寄送，不用每次手動匯出：週期可選每月、每季、每半年或每年，設定後系統會依週期自動產生報表寄給大房東，建立排程時會先寄確認信，每次寄送前也有預告通知。聯絡簿資料另外支援手動匯出 Excel。設定入口在大房東管理的報表排程功能。

### tmp:kb:3544
標題：新增團隊成員 需先註冊帳號
內容：新增團隊成員是在團隊管理頁的新增成員視窗，輸入對方的 Email 或手機號碼加入。對方必須已經是 JGB 會員——如果還沒註冊，會無法新增（視窗上也有提示「受邀請的對象如果不是 JGB 會員，將無法新增為團隊成員」），請先請對方完成 JGB 帳號註冊再加入。加入後立即生效，沒有邀請連結或有效期的問題。

### tmp:kb:3545
標題：團隊成員權限 只能查看不能編輯
內容：團隊成員的權限按功能模組劃分：物件、合約、帳單、修繕、通知、團隊管理等，每個模組內再分層級——查看所屬資料、查看全部資料、新增、編輯、匯出，層級間有相依關係（例如要先有查看權限才能給編輯權限），所以可以做到「只能看帳單不能改」這類設定。帳單模組裡也包含固定虛擬帳號的查看與編輯權限。系統提供權限範本可以快速套用，不必逐項勾選。

### tmp:kb:3546
標題：移除團隊成員 資料保留處理
內容：從團隊移除成員後，他在團隊裡建立的物件、合約、帳單等資料都會保留在團隊內，不會跟著被刪除，所以員工離職移除帳號不用擔心資料遺失。如果該成員把這個團隊設為預設身分，移除時系統會自動清除他的預設身分設定。移除操作在團隊管理的成員列表進行。

### tmp:kb:3547
標題：一個帳號加入多個團隊 身分切換
內容：一個 JGB 帳號可以同時加入多個團隊：在各團隊分別被加為成員後，登入時用切換身分功能在團隊之間切換，每個團隊的權限獨立計算、互不影響。常用的身分可以在帳號的偏好設定裡設為預設身分，之後登入就直接進入該團隊，不用每次切換。

### tmp:kb:3974
標題：誰有權限 操作權限 盤查
內容：要確認團隊裡誰擁有某個操作權限（例如取消帳單、封存合約）：到團隊管理的成員列表可以看到每位成員的角色，點該成員「變更角色」可檢視這個角色開了哪些功能權限。權限是跟著角色走的——同角色的成員權限相同。若需要進一步查特定操作是誰執行的（操作紀錄），這部分請聯繫客服協助調閱。

### tmp:kb:3981
標題：加了團隊成員 他什麼都看不到
內容：

### tmp:kb:3982
標題：成員權限怎麼開 只能看不能改
內容：

### tmp:kb:4224
標題：包租 代管 差別 系統功能
內容：包租：業者先向房東承租房屋、再以二房東身分轉租給租客——租客的合約是跟業者簽的，收據/發票由業者開立，系統另提供差額發票群組功能（按底租與實收差額開立）。代管：業者受房東委託管理，租約仍在房東與租客之間，業者負責代收代付與收取管理服務費。系統面的差異主要在合約模板、收據/發票的開立主體，以及包租特有的差額發票設定。團隊的業態在方案/團隊設定中設定。

### tmp:kb:4250
標題：團隊成員 角色權限 有哪些選擇
內容：團隊成員的權限由「角色」決定：系統提供預設角色（如管理者、一般成員等），也支援自訂角色——可逐項勾選該角色能使用的功能（合約、帳務、物件、修繕等模組的查看/編輯權限，共數十個細項開關）。設定入口：成員列表對成員「變更角色」指派；角色的權限內容在團隊設定的角色管理中調整。成員未指派角色時沒有任何權限。

### tmp:kb:4251
標題：新增團隊成員 邀請流程
內容：新增團隊成員的流程：1. 到團隊設定的成員管理，以 Email（或手機號碼）發送邀請；2. 對方接受邀請加入團隊後，記得立刻「變更角色」指派角色——沒有角色的成員登入後什麼都看不到、也無法操作；3. 若角色的可見範圍是「自己負責的物件」，還需在物件上把該成員設為經理人。邀請未送達時請確認 Email 大小寫完全正確。

### tmp:kb:4272
標題：管理員會代收包裹嗎
內容：

### tmp:draft:1
標題：租賃專法下的包租代管業
內容：租賃專法下的包租代管業 租賃專法的架構下，除了去提升健全租賃市場、保障租賃雙方權益以及提升居住正義之外，其中的有一項立法目的為「 發展租賃住宅服務業 」，而此服務業即是近年來大家耳熟能詳 「包租」以及「代管」業者，但雖然大家或多或少都聽過包租代管，但真的了解包租和代管業者有什麼區別、業務內容...等相關資訊的人可能不多，接下來就透過以下文章內容帶您快速了解一下有關包租代管業的服務內容和在租賃專法下所帶來的影響和改變。 一、什麼是包租業？又什麼是代管業？ 「包租」： 指的是由業者和房東簽訂租賃契約後，將房屋承包租賃，再當起二房東轉租給房客，並管理該房屋，所有住宅問題由業者承擔。 「代管」： 則是房東委託業者代為管理房屋，可視為「房東代理人」的角色，業者協助房東出租房屋給房客，由房客向房東簽訂契約，因此業者僅負責管理住宅、不負責承租。 二、包租跟代管的優勢分別是什麼？如果我是房東又該選擇哪個？ 包租 優點 對房東而言可以透過與業者簽訂較長的租約來保持長期穩定收益，並且無需負擔房屋空置期的壓力以及任何有關該房屋的管理。 缺點 由於業者須負擔契約期間房屋空置找不到租戶的風險，一般會以較低價格向房東承租房子（一般為市價5~8成左右） 適合對象 如果您手上有房子「管不到、不想管、沒時間管」，加上又追求長期穩定的租金收益，那委託包租業者絕對是您最佳的選擇 代管 優點 收費相較包租低一些（一般抽取租金1~2成作為費用） 缺點 業者無法保證一定租得出去，房東必須自行承擔房屋空置期的損失。 適合對象 如果您不想花時間去媒合房客跟處理像是修繕、催租等雜事，就可以考慮將房子交給代管業者，由他們幫您妥善處理。 三、包租代管業者怎麼賺錢？ （一）主要收入來源 包租： 以低於 市場行情價的租金（市價5到8折） 和房東簽約，賺取房東和房客（次承租人）之間租金的差額。 代管：租金抽成（租金之1~2成）。 （二）租賃專法補貼 包租業者可以得到政府補助之 開發費、包管費 代管業者可得到政府補助之 媒合費、代管費 另外，政府也提供業者專案貸款或融資的管道，上述政府補助費用，可先向銀行申請一定成數的貸款或融資，再由地方政府撥款到還款帳戶內。 四、如果想成政府許可的包管業者，該如何申請？ 申請管道： 向各直轄市、縣（市）政府地政局（處）申請 申請流程 向所在地直轄市、縣（市）政府地政局處取得許可 三個月內完成公司登記 向中華民國租賃住宅服務商業同業公會全國聯合會繳交保證金 加入所在地之「租賃住宅服務商業同業公會」 向所在地直轄市、縣（市）政府檢附文件申請登記 領取登記證執業 五、要如何成為一名專業包管人員？ 如果要成為一名合格的包管人員，須先經過課程訓練，並且完成測驗，以下為訓練和測驗的方式和流程： 報名方式： 中華民國租賃住宅服務商業同業公會全國聯合會網站 上會公告每個月各縣市的開班資訊及課程表，可至全聯會官網下載報名表，依各縣市公會公告之方式辦理報名（含親送、傳真或電子郵件）。 報名資格 ①年滿20歲具行為能力之中華民國國民 ②高中職畢業或持有同等學歷證明，或是持有高普考及格證書 訓練期程 ①資格訓練課程：資格訓練課程合計共30小時，若具有相關職業資格，如不動產經紀人、地政士、不動產估價師、公寓大廈管理人員可折抵課程時數，詳細時數折抵資料參考可至 全聯會官網開班資訊頁面 查詢每月各縣市最新開班資訊及課程表，並可下載當年度管理人員實施計畫書。。 ②資格測驗：完成課程並通過資格測驗會發給 「租賃住宅管理人員訓練測驗合格證明」


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
    "id": "jgb/B/owner-report-collection-remit",
    "coarse_id": "B",
    "title": "大房東報表與代收代付怎麼交代",
    "slug": "owner-report-collection-remit",
    "merge_of": [
     "tmp:canon:jgb/B/owner-report-collection-remit",
     "tmp:kb:3465",
     "tmp:kb:3543"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者問「大房東報表怎麼產／怎麼自動寄／內容有什麼」都落在同一題；3465 月報表三種取得方式與 3543 排程週期是同一問題的操作答案，併入既有細目、id 不變。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/role-permission-granularity",
    "coarse_id": "B",
    "title": "成員權限能不能細分（只看不改、看不到財務）",
    "slug": "role-permission-granularity",
    "merge_of": [
     "tmp:canon:jgb/B/role-permission-granularity",
     "tmp:kb:3359",
     "tmp:kb:3545",
     "tmp:kb:3982",
     "tmp:kb:4250"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "「權限能不能只給看不給改／有哪些角色可選／怎麼開權限」是同一個提問路徑；3545 層級相依、4250 自訂角色與設定入口、3982 空內文只當入口、3359 的權限與物件授權段併入，id 不變。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/team-management-overview",
    "coarse_id": "B",
    "title": "團隊管理模組做什麼",
    "slug": "team-management-overview",
    "merge_of": [
     "tmp:canon:jgb/B/team-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「團隊管理是做什麼的」是模組總覽提問，與各操作題層級不同，維持獨立。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/B/what-is-owner-landlord",
    "coarse_id": "B",
    "title": "大房東是什麼",
    "slug": "what-is-owner-landlord",
    "merge_of": [
     "tmp:canon:jgb/B/what-is-owner-landlord",
     "tmp:kb:3463"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「大房東是什麼／跟一般房東差在哪／能看什麼」同一提問路徑；3463 概念說明與方案數量上限併入既有細目、id 不變。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/rent-vs-manage-difference",
    "coarse_id": "B",
    "title": "包租與代管有什麼不一樣（定義、簽約對象、誰管理）",
    "slug": "rent-vs-manage-difference",
    "merge_of": [
     "tmp:kb:3084",
     "tmp:kb:3085",
     "tmp:kb:3086",
     "tmp:kb:3087",
     "tmp:kb:3091",
     "tmp:kb:3095",
     "tmp:kb:3303",
     "tmp:kb:3304",
     "tmp:kb:3305",
     "tmp:kb:3306",
     "tmp:kb:3308",
     "tmp:kb:3309",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "使用者問「包租跟代管差在哪／什麼是包租／什麼是代管」是一個可獨立回答的問題；13 筆重複改寫的定義與差異文全部收成一題，草稿第一、二節（定義與適合對象）拆入此處。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rent-vs-manage-fees-and-revenue",
    "coarse_id": "B",
    "title": "包租與代管怎麼收費、業者怎麼賺錢",
    "slug": "rent-vs-manage-fees-and-revenue",
    "merge_of": [
     "tmp:kb:3088",
     "tmp:kb:3092",
     "tmp:kb:3312",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "「代管服務費抽幾成／包租怎麼算／業者收入從哪來（含政府補貼）」是與定義題不同的提問，屬業態商業模式而非系統帳單計算，故不歸帳務；草稿第三節拆入此處。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rent-vs-manage-liability-and-risk",
    "coarse_id": "B",
    "title": "包租與代管的法律責任與風險由誰承擔",
    "slug": "rent-vs-manage-liability-and-risk",
    "merge_of": [
     "tmp:kb:3096",
     "tmp:kb:3254",
     "tmp:kb:3255",
     "tmp:kb:3307",
     "tmp:kb:3310"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「出問題誰負責／風險誰扛」是與定義、收費不同的提問路徑；法律責任與風險管理五筆互為改寫，合為一題。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rent-vs-manage-system-difference",
    "coarse_id": "B",
    "title": "系統裡包租與代管的差別（合約模板、發票主體、差額發票、業態設定）",
    "slug": "rent-vs-manage-system-difference",
    "merge_of": [
     "tmp:kb:4224"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「系統支援包租嗎／業態在哪設／包租跟代管在系統上差在哪」問的是產品功能而非產業定義，另立一題並另見定義題。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rental-service-business-license",
    "coarse_id": "B",
    "title": "怎麼申請成為政府許可的包租代管業者",
    "slug": "rental-service-business-license",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "「想開包租代管公司要怎麼申請許可」是獨立提問；草稿第四節（申請管道與流程）拆出成題。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rental-manager-certification",
    "coarse_id": "B",
    "title": "怎麼成為合格的租賃住宅管理人員（包管人員）",
    "slug": "rental-manager-certification",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "「包管人員證照怎麼考／報名資格與時數」是獨立提問；草稿第五節拆出成題。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/add-team-member",
    "coarse_id": "B",
    "title": "怎麼新增團隊成員（需先註冊、加入後要指派角色）",
    "slug": "add-team-member",
    "merge_of": [
     "tmp:kb:3439",
     "tmp:kb:3544",
     "tmp:kb:4251",
     "tmp:kb:3981"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「怎麼加成員／為什麼加不進去／加了他什麼都看不到」是同一條操作提問路徑，答案都是先註冊、加入後指派角色；3981 空內文只作入口掛此。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/who-has-permission-lookup",
    "coarse_id": "B",
    "title": "怎麼查團隊裡誰有某個操作權限",
    "slug": "who-has-permission-lookup",
    "merge_of": [
     "tmp:kb:3974"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「誰能取消帳單／誰動了這筆」是盤查型提問，與「權限能不能細分」的設定型提問不同，獨立一題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/remove-team-member-data-retention",
    "coarse_id": "B",
    "title": "移除團隊成員後他建的資料會怎樣",
    "slug": "remove-team-member-data-retention",
    "merge_of": [
     "tmp:kb:3546"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「員工離職移除帳號資料會不會不見」是獨立提問，答案為資料保留在團隊內。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/account-in-multiple-teams",
    "coarse_id": "B",
    "title": "一個帳號可以加入多個團隊嗎、怎麼切換",
    "slug": "account-in-multiple-teams",
    "merge_of": [
     "tmp:kb:3547"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「同一帳號能加幾個團隊／權限會不會互相影響」問的是團隊成員身分，切換動作附帶說明；與 A 架的房東租客身分切換是不同題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/change-team-owner-request",
    "coarse_id": "B",
    "title": "怎麼變更團隊主要負責人或綁定手機",
    "slug": "change-team-owner-request",
    "merge_of": [
     "tmp:kb:3359"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "「團隊擁有者要換人怎麼辦」是獨立提問，答案為透過異動單申請；從 3359 拆出。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/feature-not-visible-troubleshooting",
    "coarse_id": "B",
    "title": "找不到某功能或無法操作的可能原因",
    "slug": "feature-not-visible-troubleshooting",
    "merge_of": [
     "tmp:kb:3482"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「為什麼我看不到這功能」是排查型提問，四個原因中以角色與團隊權限為主，獨立一題並另見權限細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/role-function-scope",
    "coarse_id": "B",
    "title": "房東、租客、大房東、團隊成員各自能用哪些功能",
    "slug": "role-function-scope",
    "merge_of": [
     "tmp:kb:3480"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「某個角色能做什麼／大房東能看哪些」是角色功能範圍總覽提問，與單一角色定義題層級不同，獨立一題。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/add-owner-landlord-and-access",
    "coarse_id": "B",
    "title": "怎麼新增大房東並設定他能看的物件範圍",
    "slug": "add-owner-landlord-and-access",
    "merge_of": [
     "tmp:kb:3464"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「大房東怎麼新增／怎麼指定他能看什麼」是操作型提問，與「大房東是什麼」概念題分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/owner-landlord-contact-book-import-export",
    "coarse_id": "B",
    "title": "大房東聯絡簿怎麼批次匯入匯出",
    "slug": "owner-landlord-contact-book-import-export",
    "merge_of": [
     "tmp:kb:3467"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「大房東資料能不能整批 Excel 匯入匯出」是獨立操作提問。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/B/owner-report-collection-remit",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3465",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3543",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/B/role-permission-granularity",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/role-permission-granularity",
    "op": "split"
   },
   {
    "old": "tmp:kb:3545",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3982",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4250",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/B/team-management-overview",
    "new": "jgb/B/team-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/B/what-is-owner-landlord",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3463",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3084",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3085",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3086",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3087",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3091",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3095",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3303",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3304",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3305",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3306",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3308",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:kb:3309",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/rent-vs-manage-difference",
    "op": "split"
   },
   {
    "old": "tmp:kb:3088",
    "new": "jgb/B/rent-vs-manage-fees-and-revenue",
    "op": "new"
   },
   {
    "old": "tmp:kb:3092",
    "new": "jgb/B/rent-vs-manage-fees-and-revenue",
    "op": "new"
   },
   {
    "old": "tmp:kb:3312",
    "new": "jgb/B/rent-vs-manage-fees-and-revenue",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/rent-vs-manage-fees-and-revenue",
    "op": "split"
   },
   {
    "old": "tmp:kb:3096",
    "new": "jgb/B/rent-vs-manage-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3254",
    "new": "jgb/B/rent-vs-manage-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3255",
    "new": "jgb/B/rent-vs-manage-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3307",
    "new": "jgb/B/rent-vs-manage-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3310",
    "new": "jgb/B/rent-vs-manage-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:4224",
    "new": "jgb/B/rent-vs-manage-system-difference",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/rental-service-business-license",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/rental-manager-certification",
    "op": "split"
   },
   {
    "old": "tmp:kb:3439",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3544",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:4251",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3981",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3974",
    "new": "jgb/B/who-has-permission-lookup",
    "op": "new"
   },
   {
    "old": "tmp:kb:3546",
    "new": "jgb/B/remove-team-member-data-retention",
    "op": "new"
   },
   {
    "old": "tmp:kb:3547",
    "new": "jgb/B/account-in-multiple-teams",
    "op": "new"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/change-team-owner-request",
    "op": "split"
   },
   {
    "old": "tmp:kb:3482",
    "new": "jgb/B/feature-not-visible-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3480",
    "new": "jgb/B/role-function-scope",
    "op": "new"
   },
   {
    "old": "tmp:kb:3464",
    "new": "jgb/B/add-owner-landlord-and-access",
    "op": "new"
   },
   {
    "old": "tmp:kb:3467",
    "new": "jgb/B/owner-landlord-contact-book-import-export",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2980",
    "suggested_shelf": "C",
    "why": "租客在公共區域的使用權限屬社區與物件的規範，與團隊、人員、大房東無關。"
   },
   {
    "id": "tmp:kb:3094",
    "suggested_shelf": "D",
    "why": "租金調整依租約條款進行，歸位判準「由合約條款決定的歸租約」。"
   },
   {
    "id": "tmp:kb:3326",
    "suggested_shelf": "E",
    "why": "租金代收與房東直收是錢怎麼進來的問題，歸位判準「錢怎麼進來歸帳務底下的收款金流」。"
   },
   {
    "id": "tmp:kb:3360",
    "suggested_shelf": "E",
    "why": "收支明細表、差額發票收支表是帳務報表匯出，非大房東報表，歸帳務。"
   },
   {
    "id": "tmp:kb:3438",
    "suggested_shelf": "A",
    "why": "房東／租客身分切換與登入後資料範圍屬帳號與身分。"
   },
   {
    "id": "tmp:kb:4272",
    "suggested_shelf": "C",
    "why": "管理員代收包裹是社區服務問題，且內文為空，不屬本架。"
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
    "id": "jgb/B/team-management-overview",
    "coarse_id": "B",
    "title": "團隊管理模組做什麼",
    "slug": "team-management-overview",
    "merge_of": [
     "tmp:canon:jgb/B/team-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "既有細目自成一題（模組總覽與導覽），本次新材料無同主題可吸收；成員新增、權限、大房東各為獨立可答主題，以另見處理。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/B/role-permission-granularity",
    "coarse_id": "B",
    "title": "成員權限能不能細分（角色、範本、模組層級）",
    "slug": "role-permission-granularity",
    "merge_of": [
     "tmp:canon:jgb/B/role-permission-granularity",
     "tmp:kb:3545",
     "tmp:kb:4250",
     "tmp:kb:3982",
     "tmp:kb:3359"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "3545／4250 講權限依模組分層級、角色範本與自訂，與既有細目互相依賴才完整（能否細分＝靠角色與層級機制）；3982 空內文只當入口；3359 的權限與物件授權段併入，其異動單段拆出。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/add-team-member",
    "coarse_id": "B",
    "title": "新增團隊成員（須已註冊、加入後須指派角色）",
    "slug": "add-team-member",
    "merge_of": [
     "tmp:kb:3439",
     "tmp:kb:3544",
     "tmp:kb:4251",
     "tmp:kb:3981"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "新增成員與「加了看不到」互相依賴才完整（未指派角色＝無權限），3439／3544／4251 三者同一流程各補一段，3981 空內文只當入口。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/who-has-permission-lookup",
    "coarse_id": "B",
    "title": "怎麼查誰有某個操作權限",
    "slug": "who-has-permission-lookup",
    "merge_of": [
     "tmp:kb:3974"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "盤查誰擁有某權限是獨立可答的查詢程序（成員列表→變更角色檢視），主題與「權限能不能細分」不同，只依賴其結論；操作紀錄調閱附帶於此。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/remove-team-member-data-retention",
    "coarse_id": "B",
    "title": "移除團隊成員後資料會不會留",
    "slug": "remove-team-member-data-retention",
    "merge_of": [
     "tmp:kb:3546"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "移除成員與其資料保留規則自成一題，不依賴新增／權限段落即可完整回答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/one-account-multiple-teams",
    "coarse_id": "B",
    "title": "一個帳號加入多個團隊怎麼切換",
    "slug": "one-account-multiple-teams",
    "merge_of": [
     "tmp:kb:3547"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "多團隊成員身分、各團隊權限獨立計算、預設身分設定為一段完整內容；主軸是團隊成員關係而非房東／租客身分（後者歸 A）。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/change-team-owner",
    "coarse_id": "B",
    "title": "變更團隊擁有者／主要負責人要走異動單",
    "slug": "change-team-owner",
    "merge_of": [
     "tmp:kb:3359"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "3359 末段「變更團隊主要負責人須透過異動單」與該列的權限段各自完整、主題不同，故拆出獨立細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/what-is-owner-landlord",
    "coarse_id": "B",
    "title": "大房東是什麼",
    "slug": "what-is-owner-landlord",
    "merge_of": [
     "tmp:canon:jgb/B/what-is-owner-landlord",
     "tmp:kb:3463"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "3463 與既有細目同為大房東的概念定義（委託代管的業主、可看授權物件的合約帳單報表），內容重疊故吸收；方案的大房東數量上限僅附帶一句，不另立。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/add-owner-landlord-and-scope",
    "coarse_id": "B",
    "title": "新增大房東並設定可看的物件範圍",
    "slug": "add-owner-landlord-and-scope",
    "merge_of": [
     "tmp:kb:3464"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "新增大房東的操作步驟與物件／合約／帳單授權範圍是完整的程序內容，與「大房東是什麼」的概念題主題不同；概念細目中的邀請句以另見處理。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/owner-report-collection-remit",
    "coarse_id": "B",
    "title": "大房東報表與代收代付怎麼交代（月報內容、提供方式、排程）",
    "slug": "owner-report-collection-remit",
    "merge_of": [
     "tmp:canon:jgb/B/owner-report-collection-remit",
     "tmp:kb:3465",
     "tmp:kb:3543"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "3465（月報表內容與三種提供方式）與 3543（排程週期、確認信、預告通知）互相依賴才構成完整的大房東報表說明，與既有細目同一主題故吸收；3543 提到聯絡簿匯出僅一句，以另見指向聯絡簿細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/owner-landlord-contact-book-import-export",
    "coarse_id": "B",
    "title": "大房東聯絡簿的 Excel 批次匯入匯出",
    "slug": "owner-landlord-contact-book-import-export",
    "merge_of": [
     "tmp:kb:3467"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "聯絡簿的批次匯入／匯出自成一題，不依賴報表或新增大房東段落即可完整回答。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/business-type-lease-vs-manage",
    "coarse_id": "B",
    "title": "包租與代管是什麼、差在哪（契約主體、責任、風險）",
    "slug": "business-type-lease-vs-manage",
    "merge_of": [
     "tmp:kb:3084",
     "tmp:kb:3085",
     "tmp:kb:3086",
     "tmp:kb:3087",
     "tmp:kb:3091",
     "tmp:kb:3095",
     "tmp:kb:3096",
     "tmp:kb:3254",
     "tmp:kb:3255",
     "tmp:kb:3303",
     "tmp:kb:3304",
     "tmp:kb:3305",
     "tmp:kb:3306",
     "tmp:kb:3307",
     "tmp:kb:3308",
     "tmp:kb:3309",
     "tmp:kb:3310",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "定義、誰跟誰簽約、法律責任、風險承擔互相依賴才完整（責任與風險皆由契約主體推導），17 列 kb 各只講其中一面且彼此重疊，draft:1 第一、二節同題故拆入；業態是團隊層級屬性（見 4224）故歸本架。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/business-type-fee-model",
    "coarse_id": "B",
    "title": "包租與代管的收費與收入模式",
    "slug": "business-type-fee-model",
    "merge_of": [
     "tmp:kb:3088",
     "tmp:kb:3092",
     "tmp:kb:3312",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "業者怎麼向房東收費／賺錢（包租賺租差、代管抽成、管理費範疇）是獨立於定義的完整主題，3088／3092／3312 與 draft:1 第三節同題；此為業者商業模式而非系統帳單計算，故不歸 E。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/business-type-system-differences",
    "coarse_id": "B",
    "title": "包租與代管在系統上的差異與業態設定",
    "slug": "business-type-system-differences",
    "merge_of": [
     "tmp:kb:4224"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "合約模板、開立主體、差額發票群組、業態在團隊設定中設定，是系統面的獨立內容，與業態定義的法律面各自完整故分開。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/rental-service-act-licensing",
    "coarse_id": "B",
    "title": "租賃專法下的業者許可、補貼與包管人員資格",
    "slug": "rental-service-act-licensing",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "draft:1 第三（二）至五節講政府補貼、許可登記流程、包管人員訓練測驗，屬法規與人員資格，自成一題且與定義／收費段各自完整，故拆出。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/B/team-management-overview",
    "new": "jgb/B/team-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/B/role-permission-granularity",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3545",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4250",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3982",
    "new": "jgb/B/role-permission-granularity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/role-permission-granularity",
    "op": "split"
   },
   {
    "old": "tmp:kb:3439",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3544",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:4251",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3981",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3974",
    "new": "jgb/B/who-has-permission-lookup",
    "op": "new"
   },
   {
    "old": "tmp:kb:3546",
    "new": "jgb/B/remove-team-member-data-retention",
    "op": "new"
   },
   {
    "old": "tmp:kb:3547",
    "new": "jgb/B/one-account-multiple-teams",
    "op": "new"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/change-team-owner",
    "op": "split"
   },
   {
    "old": "tmp:canon:jgb/B/what-is-owner-landlord",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3463",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3464",
    "new": "jgb/B/add-owner-landlord-and-scope",
    "op": "new"
   },
   {
    "old": "tmp:canon:jgb/B/owner-report-collection-remit",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3465",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3543",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3467",
    "new": "jgb/B/owner-landlord-contact-book-import-export",
    "op": "new"
   },
   {
    "old": "tmp:kb:3084",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3085",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3086",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3087",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3091",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3095",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3096",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3254",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3255",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3303",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3304",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3305",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3306",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3307",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3308",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3309",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:kb:3310",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/business-type-lease-vs-manage",
    "op": "split"
   },
   {
    "old": "tmp:kb:3088",
    "new": "jgb/B/business-type-fee-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3092",
    "new": "jgb/B/business-type-fee-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3312",
    "new": "jgb/B/business-type-fee-model",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/business-type-fee-model",
    "op": "split"
   },
   {
    "old": "tmp:kb:4224",
    "new": "jgb/B/business-type-system-differences",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/rental-service-act-licensing",
    "op": "split"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2980",
    "suggested_shelf": "C",
    "why": "租客在公共區域的使用限制屬社區與物件本身的規範，非團隊／人員／大房東主題。"
   },
   {
    "id": "tmp:kb:3094",
    "suggested_shelf": "D",
    "why": "租金調整依租約條款、頻率與通知義務，歸位判準：由合約條款決定的歸租約。"
   },
   {
    "id": "tmp:kb:3326",
    "suggested_shelf": "E",
    "why": "租金代收與房東直收是錢怎麼進來的問題，歸位判準：歸帳務底下的收款金流子題。"
   },
   {
    "id": "tmp:kb:3360",
    "suggested_shelf": "E",
    "why": "收支明細表、差額發票收支表的匯出與收款品項設定屬帳務報表，非大房東報表。"
   },
   {
    "id": "tmp:kb:3438",
    "suggested_shelf": "A",
    "why": "房東／租客身分切換與資料範圍隨身分而異，主軸是帳號身分，非團隊成員關係。"
   },
   {
    "id": "tmp:kb:3480",
    "suggested_shelf": "A",
    "why": "橫跨房東／租客／大房東／團隊成員四種身分的功能範圍總表，主軸是身分而非團隊；大房東可看範圍已在 what-is-owner-landlord 涵蓋。"
   },
   {
    "id": "tmp:kb:3482",
    "suggested_shelf": "H",
    "why": "看不到功能的排查橫跨角色、方案、團隊權限、功能開關與快取，是通用疑難排解，非單一團隊主題。"
   },
   {
    "id": "tmp:kb:4272",
    "suggested_shelf": "C",
    "why": "管理員代收包裹指社區管理員的社區服務，且內文為空；不屬團隊人員。"
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
    "id": "jgb/B/team-management-overview",
    "coarse_id": "B",
    "title": "團隊管理模組做什麼",
    "slug": "team-management-overview",
    "merge_of": [
     "tmp:canon:jgb/B/team-management-overview"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層：售前只需知道團隊管理能做什麼；成員新增、角色設定等操作層另見 add-team-member／member-role-permission-setup。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/B/role-permission-granularity",
    "coarse_id": "B",
    "title": "成員權限能不能細分（只看不改、看不到財務）",
    "slug": "role-permission-granularity",
    "merge_of": [
     "tmp:canon:jgb/B/role-permission-granularity"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層：售前問「能不能」；同主題的操作層（怎麼開、怎麼查誰有權限）另見 member-role-permission-setup，不併入以免同一細目混兩層級。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/B/what-is-owner-landlord",
    "coarse_id": "B",
    "title": "大房東是什麼",
    "slug": "what-is-owner-landlord",
    "merge_of": [
     "tmp:canon:jgb/B/what-is-owner-landlord",
     "tmp:kb:3463"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "概念層：3463 與既有細目同為「大房東是什麼、能看什麼、方案有上限」的概念說明，同受眾同層級併入；新增與授權的操作層另見 add-owner-landlord-and-access。",
    "target_user": [
     "prospect"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/B/owner-report-collection-remit",
    "coarse_id": "B",
    "title": "大房東報表與代收代付怎麼交代",
    "slug": "owner-report-collection-remit",
    "merge_of": [
     "tmp:canon:jgb/B/owner-report-collection-remit"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層：售前只需知道報表能自動整理並排程寄送；週期選項、預告信、手動上傳等操作層另見 owner-landlord-report-schedule。",
    "target_user": [
     "prospect"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/B/leasing-vs-management-business-model",
    "coarse_id": "B",
    "title": "包租業與代管業是什麼、差在哪",
    "slug": "leasing-vs-management-business-model",
    "merge_of": [
     "tmp:kb:3084",
     "tmp:kb:3085",
     "tmp:kb:3086",
     "tmp:kb:3087",
     "tmp:kb:3091",
     "tmp:kb:3303",
     "tmp:kb:3304",
     "tmp:kb:3305",
     "tmp:kb:3306",
     "tmp:kb:3308",
     "tmp:kb:3309",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "概念層：多筆 kb 與 draft 第一、二節皆在回答「包租／代管各是什麼、簽約對象與控制權差異、房東該選哪個」，同受眾同層級合為一個主題；系統面差異的操作層另見 business-type-setting-and-system-differences。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/leasing-vs-management-liability-and-risk",
    "coarse_id": "B",
    "title": "包租與代管的法律責任與風險承擔差異",
    "slug": "leasing-vs-management-liability-and-risk",
    "merge_of": [
     "tmp:kb:3095",
     "tmp:kb:3096",
     "tmp:kb:3254",
     "tmp:kb:3255",
     "tmp:kb:3307",
     "tmp:kb:3310"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益層：誰對租客負責、誰承擔空置與損壞風險，是與「是什麼」不同的可獨立回答主題；同受眾只留此一層級，定義另見 leasing-vs-management-business-model。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "coarse_id": "B",
    "title": "包租與代管的收費結構與租金收取方式",
    "slug": "leasing-vs-management-fee-and-rent-collection",
    "merge_of": [
     "tmp:kb:3088",
     "tmp:kb:3092",
     "tmp:kb:3312",
     "tmp:kb:3326",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "權益層：業者怎麼收費／怎麼賺（抽成 vs 租金差額、政府補貼）與租金由業者代收或房東直收，屬業態的商業模式而非 JGB 帳單計算，故留在本架；draft 第三節拆入此處。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/leasing-management-license-and-staff-qualification",
    "coarse_id": "B",
    "title": "如何成為合法包租代管業者與合格包管人員",
    "slug": "leasing-management-license-and-staff-qualification",
    "merge_of": [
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "概念層：draft 第四、五節談業者許可申請流程與租賃住宅管理人員的訓練測驗資格，屬「人員」子題且可獨立回答，與商業模式分開。",
    "target_user": [
     "prospect"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/business-type-setting-and-system-differences",
    "coarse_id": "B",
    "title": "團隊業態（包租／代管）在系統裡怎麼設、差在哪",
    "slug": "business-type-setting-and-system-differences",
    "merge_of": [
     "tmp:kb:4224"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：物管需要知道業態設定入口與系統面差異（合約模板、發票開立主體、差額發票）；差額發票的細節另見帳務架，概念層另見 leasing-vs-management-business-model。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/add-team-member",
    "coarse_id": "B",
    "title": "新增團隊成員（需先註冊、加入後指派角色）",
    "slug": "add-team-member",
    "merge_of": [
     "tmp:kb:3439",
     "tmp:kb:3544",
     "tmp:kb:4251"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：三筆皆為「怎麼把人加進團隊」的步驟、前置條件（須為會員）與加入後必做的角色指派，同受眾同層級合一；成員加了卻看不到東西的排查另見 member-cannot-see-function-troubleshooting。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/member-role-permission-setup",
    "coarse_id": "B",
    "title": "成員角色與功能權限怎麼設定、怎麼查誰有權限",
    "slug": "member-role-permission-setup",
    "merge_of": [
     "tmp:kb:3545",
     "tmp:kb:4250",
     "tmp:kb:3974",
     "tmp:kb:3982",
     "tmp:kb:3359"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "操作層：權限層級（查看／編輯／匯出）、範本與自訂角色、物件授權給成員、盤查誰有某操作權限，皆為物管的設定操作；3982 空內文只當入口；3359 的權限與物件授權段拆入此處；能力層另見 role-permission-granularity。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/member-cannot-see-function-troubleshooting",
    "coarse_id": "B",
    "title": "成員看不到功能或無法操作怎麼排查",
    "slug": "member-cannot-see-function-troubleshooting",
    "merge_of": [
     "tmp:kb:3482",
     "tmp:kb:3981"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：以「症狀」為入口的排查（未指派角色、角色限制、方案限制、功能開關），3981 空內文只當入口掛在此處；角色怎麼指派的操作另見 add-team-member／member-role-permission-setup。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/remove-team-member-data-retention",
    "coarse_id": "B",
    "title": "移除團隊成員後資料會不會留",
    "slug": "remove-team-member-data-retention",
    "merge_of": [
     "tmp:kb:3546"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：移除操作與資料保留、預設身分清除，是離職處理時獨立可答的主題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/account-in-multiple-teams",
    "coarse_id": "B",
    "title": "一個帳號加入多個團隊",
    "slug": "account-in-multiple-teams",
    "merge_of": [
     "tmp:kb:3547"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：帳號可同時屬多團隊、各團隊權限獨立計算，屬團隊成員關係；身分切換與預設身分的機制本身歸帳號與身分架，此處只交叉引用。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/change-team-principal-or-phone",
    "coarse_id": "B",
    "title": "變更團隊主要負責人或綁定手機（異動單）",
    "slug": "change-team-principal-or-phone",
    "merge_of": [
     "tmp:kb:3359"
    ],
    "split_from": [
     "tmp:kb:3359"
    ],
    "moved_from": [],
    "reason": "操作層：3359 末段的異動單申請是與權限設定無關、可獨立回答的團隊主體變更流程，故自 3359 拆出。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/add-owner-landlord-and-access",
    "coarse_id": "B",
    "title": "新增大房東與設定其可看的物件範圍",
    "slug": "add-owner-landlord-and-access",
    "merge_of": [
     "tmp:kb:3464"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：新增步驟、授權範圍、邀請未註冊者，是物管的設定操作；概念層另見 what-is-owner-landlord。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/owner-landlord-report-schedule",
    "coarse_id": "B",
    "title": "大房東月報表怎麼看、怎麼排程寄送與手動上傳",
    "slug": "owner-landlord-report-schedule",
    "merge_of": [
     "tmp:kb:3465",
     "tmp:kb:3543"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：報表內容、排程週期、確認信與預告通知、手動上傳，兩筆同主題同層級合一；能力層另見 owner-report-collection-remit。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/B/owner-landlord-contact-book-import-export",
    "coarse_id": "B",
    "title": "大房東聯絡簿批次匯入匯出",
    "slug": "owner-landlord-contact-book-import-export",
    "merge_of": [
     "tmp:kb:3467"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層：Excel 匯入匯出是獨立的資料維護操作，與報表排程分開。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/B/team-management-overview",
    "new": "jgb/B/team-management-overview",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/B/role-permission-granularity",
    "new": "jgb/B/role-permission-granularity",
    "op": "keep"
   },
   {
    "old": "tmp:canon:jgb/B/what-is-owner-landlord",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3463",
    "new": "jgb/B/what-is-owner-landlord",
    "op": "merge"
   },
   {
    "old": "tmp:canon:jgb/B/owner-report-collection-remit",
    "new": "jgb/B/owner-report-collection-remit",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3084",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3085",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3086",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3087",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3091",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3303",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3304",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3305",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3306",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3308",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:kb:3309",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/leasing-vs-management-business-model",
    "op": "split"
   },
   {
    "old": "tmp:kb:3095",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3096",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3254",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3255",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3307",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3310",
    "new": "jgb/B/leasing-vs-management-liability-and-risk",
    "op": "new"
   },
   {
    "old": "tmp:kb:3088",
    "new": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "op": "new"
   },
   {
    "old": "tmp:kb:3092",
    "new": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "op": "new"
   },
   {
    "old": "tmp:kb:3312",
    "new": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "op": "new"
   },
   {
    "old": "tmp:kb:3326",
    "new": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "op": "new"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/leasing-vs-management-fee-and-rent-collection",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/B/leasing-management-license-and-staff-qualification",
    "op": "split"
   },
   {
    "old": "tmp:kb:4224",
    "new": "jgb/B/business-type-setting-and-system-differences",
    "op": "new"
   },
   {
    "old": "tmp:kb:3439",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3544",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:4251",
    "new": "jgb/B/add-team-member",
    "op": "new"
   },
   {
    "old": "tmp:kb:3545",
    "new": "jgb/B/member-role-permission-setup",
    "op": "new"
   },
   {
    "old": "tmp:kb:4250",
    "new": "jgb/B/member-role-permission-setup",
    "op": "new"
   },
   {
    "old": "tmp:kb:3974",
    "new": "jgb/B/member-role-permission-setup",
    "op": "new"
   },
   {
    "old": "tmp:kb:3982",
    "new": "jgb/B/member-role-permission-setup",
    "op": "new"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/member-role-permission-setup",
    "op": "split"
   },
   {
    "old": "tmp:kb:3482",
    "new": "jgb/B/member-cannot-see-function-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3981",
    "new": "jgb/B/member-cannot-see-function-troubleshooting",
    "op": "new"
   },
   {
    "old": "tmp:kb:3546",
    "new": "jgb/B/remove-team-member-data-retention",
    "op": "new"
   },
   {
    "old": "tmp:kb:3547",
    "new": "jgb/B/account-in-multiple-teams",
    "op": "new"
   },
   {
    "old": "tmp:kb:3359",
    "new": "jgb/B/change-team-principal-or-phone",
    "op": "split"
   },
   {
    "old": "tmp:kb:3464",
    "new": "jgb/B/add-owner-landlord-and-access",
    "op": "new"
   },
   {
    "old": "tmp:kb:3465",
    "new": "jgb/B/owner-landlord-report-schedule",
    "op": "new"
   },
   {
    "old": "tmp:kb:3543",
    "new": "jgb/B/owner-landlord-report-schedule",
    "op": "new"
   },
   {
    "old": "tmp:kb:3467",
    "new": "jgb/B/owner-landlord-contact-book-import-export",
    "op": "new"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:2980",
    "suggested_shelf": "C",
    "why": "租客在公共區域的使用權限屬物件／社區本身的規範，與團隊、人員、大房東無關。"
   },
   {
    "id": "tmp:kb:3094",
    "suggested_shelf": "D",
    "why": "租金調整依租約條款決定，依歸位判準由合約條款決定的歸租約。"
   },
   {
    "id": "tmp:kb:3360",
    "suggested_shelf": "E",
    "why": "收支明細表、差額發票收支表的匯出與收款品項設定屬帳務報表，不是大房東報表。"
   },
   {
    "id": "tmp:kb:3438",
    "suggested_shelf": "A",
    "why": "房東／租客身分切換與預設身分是帳號與身分機制。"
   },
   {
    "id": "tmp:kb:3480",
    "suggested_shelf": "A",
    "why": "房東／租客／大房東／團隊成員四種身分的功能範圍總表，主體是身分而非團隊；跨架命題只能歸一處。"
   },
   {
    "id": "tmp:kb:4272",
    "suggested_shelf": "C",
    "why": "空內文入口，主題是社區管理員代收包裹，屬社區與物件；本架無可掛的細目。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。