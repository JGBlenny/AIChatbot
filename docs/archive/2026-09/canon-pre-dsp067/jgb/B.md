---
coarse: B
title: 團隊、人員與大房東
scope: 團隊建立與成員邀請、角色權限、人員管理、大房東記錄與代管關係；⛔ 帳號本身歸 A
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 團隊、人員與大房東 {#B}
### 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送） {#jgb/B/owner-report-collection-remit}
- phrasings:
  - {text: "代收代付", source: "question_summary:3604", status: approved}
  - {text: "大房東報表", source: "question_summary:3604", status: approved}
  - {text: "對業主交報表", source: "question_summary:3604", status: approved}
  - {text: "自動寄送", source: "question_summary:3604", status: approved}
  - {text: "差額發票什麼時候用", source: "gapmap:C25", status: approved}
- sources: [kb:3604, draft:batch#18, docs:knowledge/jgb-product-facts.md#balance-invoice, helpcenter:Landlordonboarding00, kb:3465, kb:3543]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
要定期跟業主交報表很花時間？
金箍棒的大房東報表能把代收代付、月結與營運狀況整理成報表，並可排程自動寄送給業主，省去人工彙整。
想看報表內容可預約 demo。
代管業者對房東的月結差額，系統每月自動整理成差額發票群組並開立，次月重新計算。
大房東月報表功能：系統可自動產生大房東名下物件的月度財務報表，包含租金收入、費用支出、帳單狀態等彙總資訊。
（1）手動檢視：大房東登入後在報表頁面查看；（2）排程發送：物管可設定定期自動將月報表以 Email 發送給大房東，支援指定發送日期；（3）手動上傳：物管可上傳自訂報表檔案供大房東下載。
報表會在發送前發出預告通知。
大房東報表可以設定排程自動寄送，不用每次手動匯出：週期可選每月、每季、每半年或每年，設定後系統會依週期自動產生報表寄給大房東，建立排程時會先寄確認信，每次寄送前也有預告通知。
聯絡簿資料另外支援手動匯出 Excel。
設定入口在大房東管理的報表排程功能。

### 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） {#jgb/B/role-permission-granularity}
- phrasings:
  - {text: "只能查看不能編輯", source: "question_summary:3545", status: proposed}
  - {text: "只能看不能改", source: "question_summary:3982", status: proposed}
  - {text: "團隊成員權限", source: "question_summary:3545", status: proposed}
  - {text: "成員權限怎麼開", source: "question_summary:3982", status: proposed}
  - {text: "有哪些選擇", source: "question_summary:4250", status: proposed}
- sources: [draft:batch#14, helpcenter:qa23, kb:3359, kb:3545, kb:3982, kb:4250]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
可以。
金箍棒的權限依八大功能分類（物件、合約、帳務、修繕、通知、團隊、人員、大房東管理），每類再細分查看、編輯、新增等項目；不給某位成員「查看帳務」，他就看不到帳務圖表、收付款與屋主帳單。
系統內建擁有者、最高管理者、店長、會計、一般業務等十種範本角色，也可以自訂角色；還能把物件指派給經理人，只給他該物件與對應合約的查看／編輯權限。
團隊成員可設定不同的操作權限，包括物件授權、帳務檢視等。
團隊擁有者擁有最高權限。
物件可授權給特定團隊成員管理，授權後該成員可查看與操作指定物件的相關功能。
若需變更團隊主要負責人或綁定手機號碼，請透過異動單申請。
團隊成員的權限按功能模組劃分：物件、合約、帳單、修繕、通知、團隊管理等，每個模組內再分層級——查看所屬資料、查看全部資料、新增、編輯、匯出，層級間有相依關係（例如要先有查看權限才能給編輯權限），所以可以做到「只能看帳單不能改」這類設定。
帳單模組裡也包含固定虛擬帳號的查看與編輯權限。
系統提供權限範本可以快速套用，不必逐項勾選。
團隊成員的權限由「角色」決定：系統提供預設角色（如管理者、一般成員等），也支援自訂角色——可逐項勾選該角色能使用的功能（合約、帳務、物件、修繕等模組的查看/編輯權限，共數十個細項開關）。
設定入口：成員列表對成員「變更角色」指派；角色的權限內容在團隊設定的角色管理中調整。
成員未指派角色時沒有任何權限。

### 團隊管理模組做什麼 {#jgb/B/team-management-overview}
- phrasings:
  - {text: "團隊管理", source: "question_summary:3602", status: approved}
  - {text: "多人協作", source: "question_summary:3602", status: approved}
  - {text: "角色權限", source: "question_summary:3602", status: approved}
  - {text: "系統管理模組有哪些功能", source: "gapmap:C52", status: approved}
  - {text: "系統管理", source: "gapmap:C52", status: approved}
- sources: [kb:3602, docs:knowledge/jgb-product-facts.md#no-system-management-module, helpcenter:qa23, helpcenter:slug92]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
人多、管不動？
金箍棒的團隊管理支援多人帳號與角色權限，讓代管團隊分工協作，並提供大房東報表對業主交代。
系統沒有叫「系統管理」的模組；成員、角色權限、訂閱方案這類設定都在團隊管理裡。
想了解團隊方案可預約 demo 由專人說明。

### 大房東是什麼 {#jgb/B/what-is-owner-landlord}
- phrasings:
  - {text: "房東對外首頁是什麼", source: "koyu:slug90#1", status: approved}
  - {text: "經理人是什麼", source: "koyu:slug92#15", status: approved}
  - {text: "我的帳號是什麼", source: "koyu:slug01#15", status: approved}
  - {text: "樓盤字典是什麼", source: "koyu:TOFILL-beike#3", status: approved}
  - {text: "物件分類是什麼", source: "koyu:slug39#14", status: approved}
  - {text: "租約公證是什麼", source: "koyu:rent3#1", status: approved}
  - {text: "租賃專法是什麼", source: "koyu:rentallaw.pt1#1", status: approved}
  - {text: "線上金流是什麼", source: "koyu:slug86#15", status: approved}
  - {text: "虛擬帳號是什麼", source: "koyu:landlordonboarding05Paymentsettings#19", status: approved}
- sources: [draft:batch#2, helpcenter:Landlordonboarding00, kb:3463]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
在金箍棒裡，「大房東」指的是把物件交給您代管的業主。
物管團隊可以在大房東列表用 email 邀請業主，並把特定物件授權給他，業主登入後就能瀏覽自己物件的合約、帳務與修繕狀態，不必逐一問您。
搭配大房東報表，代收代付與月結會自動整理並可排程寄給業主。
想看業主端的畫面可預約 demo。
大房東是 JGB 系統中的角色概念，指的是擁有多間物件、委託物管業者代為管理的房東。
與一般房東直接管理物件不同，大房東的物件由物管團隊統一代管，大房東可透過系統查看自己名下物件的合約、帳單和報表資訊。
物管業者可在系統中設定大房東帳號，並指定其可查看的物件範圍和權限。
每個訂閱方案有大房東數量上限。

### 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） {#jgb/B/leasing-vs-management-business-model}
- phrasings:
  - {text: "代管業介紹", source: "question_summary:3085", status: proposed}
  - {text: "代管業定義", source: "question_summary:3304", status: proposed}
  - {text: "包租代管差異", source: "question_summary:3086", status: proposed}
  - {text: "包租代管服務差異", source: "question_summary:3305", status: proposed}
  - {text: "包租代管業務差異", source: "question_summary:3308", status: proposed}
  - {text: "包租代管關係", source: "question_summary:3309", status: proposed}
  - {text: "包租業介紹", source: "question_summary:3303", status: proposed}
  - {text: "包租業定義", source: "question_summary:3084", status: proposed}
  - {text: "包租業與代管業差異", source: "question_summary:3091", status: proposed}
  - {text: "包租業與代管業比較", source: "question_summary:3306", status: proposed}
  - {text: "包租與代管差異", source: "question_summary:3087", status: proposed}
- sources: [kb:3084, kb:3085, kb:3086, kb:3087, kb:3091, kb:3303, kb:3304, kb:3305, kb:3306, kb:3308, kb:3309, helpcenter:rentallaw.pt3]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
包租業是指業主將房產租給專業公司，該公司負責整個租賃過程的管理，包括出租、維護和租金收取等。
而包租代管則是這種業務的一部分，專注於代為管理房屋，讓業主能夠省去管理的麻煩。
作為房客，您可以享有更專業的服務及更好的居住體驗。
代管業是專門負責管理租屋物件的服務，透過專業管理師協助房東與房客之間的溝通、租金收取、維修管理等事務，讓房客能夠享有更便利的居住體驗，並保障他們的權益。
包租業主要是將物業整體出租，業主將物件租給租客，並負責所有相關事務；而代管業則是為業主提供物業管理服務，包括協助物業出租、維護等，業主仍然擁有物件的所有權。
房客在代管業中可享有更完善的服務，如維修保障和租金透明度等權益。
包租業主要是將房東的房產整體租出，房東負責管理，而租客與房東直接簽約。
代管業則是由代管公司負責管理房產，包括租金收取、維修等服務，租客則與代管公司簽約，享有更完善的服務及保障。
包租業主要是將整個房產租給包租公司，房東可獲得穩定租金，風險較低。
而代管業則是房東自行出租，代管公司負責管理，房東需承擔租金風險，但可獲得更高的租金收益。
房客在代管業中可享有更多的維修及服務保障。
包租業是指房東將房產出租給包租代管公司，後者負責整體管理、維護和出租事宜。
這樣一來，房東可以獲得穩定收入，而租客則能享受到更專業的服務和維護。
作為房客，您可以享有更完善的租住環境、專業的服務支持以及相關的租住保障。
代管業是專門負責管理房屋租賃事務的服務，包含租金收取、房屋維護、租客管理等，讓房東和租客之間的溝通和交易更為順利。
租客可以享有更便捷的服務與房屋管理，保障自己的居住權益。
包租業通常是房東將房屋出租給租客，由租客直接與房東簽約，而代管業則是房東將物業委託給專業公司管理，租客則與該公司簽約。
這意味著租客在代管業中享有更專業的服務和管理，也能更方便地處理維修請求和其他問題。
包租業通常是房東將房產全權出租給包租公司，管理和維護由公司負責，租客與包租公司直接打交道。
而代管業則是房東將房產委託給代管公司，租客仍然與房東簽約，代管公司負責協助管理。
租客的權益保障上，包租業可能提供更全方位的服務，如維修及客服支持，而代管業則強調與房東的直接聯繫，租客的問題可能需通過房東處理。
包租業主要是指業主將整個房產出租給包租公司，由公司負責整體管理和租金收入。
而代管業則是業主將房產委託給代管公司，後者負責日常管理、維修及租客管理，業主仍擁有租金收入的權利。
這兩者的主要差異在於業主對房產的控制程度及管理方式。
包租業主要是將物件出租給租客，而代管業則是負責物件的管理和維護。
在客戶關係上，包租業通常較為單向，重點在於租約和租金的收取；而代管業則會提供更全面的服務，包括日常維護、租客溝通及問題處理，強調雙向的互動和支持。
租賃專法的立法目的之一是「發展租賃住宅服務業」，包租業與代管業就是租賃專法架構下所指的租賃住宅服務業。
包租業是由業者先和房東簽訂租賃契約承包整間房屋，再以二房東身分轉租給房客並管理該房屋，房屋的住宅問題都由業者承擔。
代管業是房東委託業者代為管理房屋，業者扮演「房東代理人」的角色，協助房東把房屋出租給房客，租賃契約由房客與房東簽訂，業者只負責管理住宅、不負責承租。
房東選擇包租的好處是可以透過與業者簽訂較長的租約維持長期穩定收益，不必承擔房屋空置期的壓力，也不用處理任何有關該房屋的管理事務。
房東選擇包租的代價是業者必須承擔契約期間找不到租戶的空置風險，因此一般會以低於市價的價格向房東承租房子。
手上的房子「管不到、不想管、沒時間管」，又追求長期穩定租金收益的房東，適合委託包租業者。
房東選擇代管的好處是收費相較包租低一些，代價是業者無法保證一定租得出去，房屋空置期的損失要由房東自行承擔。
不想花時間媒合房客、也不想處理修繕與催租等雜事的房東，可以考慮把房子交給代管業者處理。

### 包租與代管的法律責任與風險由誰承擔 {#jgb/B/leasing-vs-management-liability-and-risk}
- phrasings:
  - {text: "包租代管法律責任", source: "question_summary:3307", status: proposed}
  - {text: "包租業與代管業", source: "question_summary:3095", status: proposed}
  - {text: "包租與代管風險管理", source: "question_summary:3310", status: proposed}
  - {text: "法律責任差異", source: "question_summary:3254", status: proposed}
  - {text: "風險管理差異", source: "question_summary:3255", status: proposed}
  - {text: "風險管理策略", source: "question_summary:3096", status: proposed}
- sources: [kb:3095, kb:3096, kb:3254, kb:3255, kb:3307, kb:3310]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
包租業主要是房東將房產出租給租客，房東負責所有管理和維護的法律責任。
而代管業則是房東委託專業公司管理其房產，法律責任由代管公司承擔，這樣租客的權益可以更有保障，例如在維修和服務上的回應速度更快。
包租業通常承擔較多的風險，包括租金未支付及房屋損壞等，因此需要建立嚴謹的租約和風險評估機制。
而代管業則重視物業的日常維護和租客的滿意度，風險管理主要集中在服務質量和客戶關係上。
無論是哪一種業務模式，房客都應確保了解自己的權益，包括在租約中明確的維修責任和租金保障等。
這樣可以在遇到問題時，依據合約要求相應的維護和補償。
包租業主要負責整個租賃過程，包括租金的收取和房屋管理，對租客的權益負有直接責任。
而代管業則是為房東提供管理服務，承擔的責任相對較少，主要是在代為管理房屋的範疇內負責。
租客應了解自己的權益，如租金透明、維修責任等，確保在合約中有明確的條款保障自身利益。
包租業的風險管理主要集中在租金收入的穩定性和租客信用評估上，例如選擇可靠的租客並進行租約保障。
而代管業則更著重於物業的日常維護和管理風險，確保物業狀況良好，並快速處理租客的維修需求。
作為房客，您有權要求及時的維修服務和物業安全保障。
包租業通常負責整體租約的法律責任，包括租金收取和維護房屋的義務；而代管業主要是代理業主進行日常管理，因此法律責任相對較小，主要集中在維護租客權益和提供服務的範疇。
房客享有的權益如房屋維修、租金透明等，應由代管方保障。
包租業主要風險在於租客的信用和租金的收回，通常會要求租客提供信用證明或擔保。
而代管業則更注重物業的維護和管理，風險主要來自於物業損壞和維修問題。
代管公司會制定維修計劃和保險措施以降低風險，並確保租客的居住品質。

### 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） {#jgb/B/business-type-fee-model}
- phrasings:
  - {text: "代管服務費", source: "question_summary:3312", status: proposed}
  - {text: "收費結構差異", source: "question_summary:3088", status: proposed}
  - {text: "管理費用差異", source: "question_summary:3092", status: proposed}
- sources: [kb:3088, kb:3092, kb:3312, helpcenter:rentallaw.pt3]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
包租業通常收取固定的租金，租客需按月支付；而代管業則會收取管理費用，可能依照租金的比例計算。
這意味著在選擇時，您需要了解自己所需的服務類型以及相關費用結構，以確保符合您的預算和需求。
包租業的管理費用通常包含房屋的租金收取、客戶服務及物業管理等，較為全面。
而代管業的管理費用則主要集中在物業的日常維護與管理服務，可能不包括租金收取。
這意味著作為房客，您應該了解這些費用的範疇，以確保您獲得的服務符合您的需求。
代管業的服務費比例通常會依據租金的百分比來計算，具體的比例可能會因公司政策或物件類型而有所不同。
若您想了解您租屋的具體服務費比例，請提供您的物件地址，我幫您查詢。
包租業者的主要收入來源是租金差額：業者以低於市場行情的租金（一般為市價五到八折）和房東簽約，再轉租給房客，賺取房東與房客（次承租人）之間的租金差額。
代管業者的主要收入來源是租金抽成，一般抽取租金的一到兩成作為費用。
就房東負擔的費用而言，代管的收費相較包租低一些。
租賃專法對包租代管業者提供補貼：包租業者可以得到政府補助的開發費與包管費，代管業者可以得到政府補助的媒合費與代管費。
政府另外提供包租代管業者專案貸款或融資的管道。
上述政府補助費用可以先向銀行申請一定成數的貸款或融資，再由地方政府撥款到還款帳戶內。

### 團隊業態（包租／代管）在系統裡怎麼設、差在哪（合約模板、發票主體、差額發票） {#jgb/B/business-type-setting-and-system-differences}
- phrasings:
  - {text: "系統功能", source: "question_summary:4224", status: proposed}
- sources: [kb:4224]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
包租：業者先向房東承租房屋、再以二房東身分轉租給租客——租客的合約是跟業者簽的，收據/發票由業者開立，系統另提供差額發票群組功能（按底租與實收差額開立）。
代管：業者受房東委託管理，租約仍在房東與租客之間，業者負責代收代付與收取管理服務費。
系統面的差異主要在合約模板、收據/發票的開立主體，以及包租特有的差額發票設定。
團隊的業態在方案/團隊設定中設定。

### 如何成為政府許可的包租代管業者與合格包管人員 {#jgb/B/leasing-management-license-and-staff-qualification}
- phrasings:
  - {text: "要怎麼成為包租代管業者", source: "koyu:rentallaw.pt3#3", status: proposed}
  - {text: "租賃專法下的包租代管業", source: "helpcenter:rentallaw.pt3", status: proposed}
  - {text: "包租代管", source: "koyu:rentallaw.pt3#17", status: proposed}
  - {text: "包租代管稅務優惠", source: "koyu:rentallaw.pt5#15", status: proposed}
  - {text: "包租代管要證照嗎", source: "koyu:rentallaw.pt1#6", status: proposed}
- sources: [helpcenter:rentallaw.pt3]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
想成為政府許可的包租代管業者，申請管道是向各直轄市、縣（市）政府地政局（處）提出申請。
包租代管業者的申請流程依序為：向所在地直轄市、縣（市）政府地政局處取得許可，三個月內完成公司登記，向中華民國租賃住宅服務商業同業公會全國聯合會繳交保證金，加入所在地的租賃住宅服務商業同業公會，向所在地直轄市、縣（市）政府檢附文件申請登記，最後領取登記證執業。
想成為合格的包管人員，必須先經過資格訓練課程，並完成資格測驗。
包管人員訓練課程的報名方式是：中華民國租賃住宅服務商業同業公會全國聯合會網站每月會公告各縣市的開班資訊及課程表，可到全聯會官網下載報名表，再依各縣市公會公告的方式辦理報名（含親送、傳真或電子郵件）。
包管人員訓練的報名資格是年滿 20 歲具行為能力的中華民國國民，且高中職畢業或持有同等學歷證明，或是持有高普考及格證書。
包管人員的資格訓練課程合計 30 小時，具有不動產經紀人、地政士、不動產估價師、公寓大廈管理人員等相關職業資格者可以折抵課程時數，詳細折抵時數可到全聯會官網開班資訊頁面查詢，並可下載當年度管理人員實施計畫書。
完成訓練課程並通過資格測驗後，會發給「租賃住宅管理人員訓練測驗合格證明」。

### 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） {#jgb/B/add-team-member}
- phrasings:
  - {text: "他什麼都看不到", source: "question_summary:3981", status: proposed}
  - {text: "加了團隊成員", source: "question_summary:3981", status: proposed}
  - {text: "團隊成員", source: "question_summary:3439", status: proposed}
  - {text: "新增團隊成員", source: "question_summary:3544", status: proposed}
  - {text: "新增管理", source: "question_summary:3439", status: proposed}
  - {text: "邀請流程", source: "question_summary:4251", status: proposed}
  - {text: "需先註冊帳號", source: "question_summary:3544", status: proposed}
- sources: [kb:3439, kb:3544, kb:4251, kb:3981]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
團隊成員管理讓法人房東團隊多人共同管理物件和合約。
新增成員：進入團隊管理頁，輸入對方的 Email 或手機號碼加入（對方必須已註冊 JGB 會員），加入即時生效。
重要：加入後請到成員列表為該成員「變更角色」指派角色——尚未指派角色的成員沒有任何權限，會看不到社區與物件、也無法新增資料。
系統內建十種範本角色（最高管理者、店長、會計、一般業務等），也可自訂角色的功能權限。
新增團隊成員是在團隊管理頁的新增成員視窗，輸入對方的 Email 或手機號碼加入。
對方必須已經是 JGB 會員——如果還沒註冊，會無法新增（視窗上也有提示「受邀請的對象如果不是 JGB 會員，將無法新增為團隊成員」），請先請對方完成 JGB 帳號註冊再加入。
加入後立即生效，沒有邀請連結或有效期的問題。
新增團隊成員的流程：1. 到團隊設定的成員管理，以 Email（或手機號碼）發送邀請；2. 對方接受邀請加入團隊後，記得立刻「變更角色」指派角色——沒有角色的成員登入後什麼都看不到、也無法操作；3. 若角色的可見範圍是「自己負責的物件」，還需在物件上把該成員設為經理人。
邀請未送達時請確認 Email 大小寫完全正確。

### 怎麼查團隊裡誰有某個操作權限 {#jgb/B/who-has-permission-lookup}
- phrasings:
  - {text: "操作權限", source: "question_summary:3974", status: proposed}
  - {text: "誰有權限", source: "question_summary:3974", status: proposed}
- sources: [kb:3974]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
要確認團隊裡誰擁有某個操作權限（例如取消帳單、封存合約）：到團隊管理的成員列表可以看到每位成員的角色，點該成員「變更角色」可檢視這個角色開了哪些功能權限。
權限是跟著角色走的——同角色的成員權限相同。
若需要進一步查特定操作是誰執行的（操作紀錄），這部分請聯繫客服協助調閱。

### 移除團隊成員後他建的資料會怎樣 {#jgb/B/remove-team-member-data-retention}
- phrasings:
  - {text: "移除團隊成員", source: "question_summary:3546", status: proposed}
  - {text: "資料保留處理", source: "question_summary:3546", status: proposed}
  - {text: "團隊成員設定", source: "koyu:qa23#16", status: proposed}
  - {text: "團隊成員要怎麼邀請", source: "koyu:Landlordonboarding02#2", status: proposed}
- sources: [kb:3546]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
從團隊移除成員後，他在團隊裡建立的物件、合約、帳單等資料都會保留在團隊內，不會跟著被刪除，所以員工離職移除帳號不用擔心資料遺失。
如果該成員把這個團隊設為預設身分，移除時系統會自動清除他的預設身分設定。
移除操作在團隊管理的成員列表進行。

### 一個帳號可以加入多個團隊嗎、權限怎麼算 {#jgb/B/account-in-multiple-teams}
- phrasings:
  - {text: "一個帳號加入多個團隊", source: "question_summary:3547", status: proposed}
  - {text: "身分切換", source: "question_summary:3547", status: proposed}
- sources: [kb:3547]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一個 JGB 帳號可以同時加入多個團隊：在各團隊分別被加為成員後，登入時用切換身分功能在團隊之間切換，每個團隊的權限獨立計算、互不影響。
常用的身分可以在帳號的偏好設定裡設為預設身分，之後登入就直接進入該團隊，不用每次切換。

### 怎麼變更團隊主要負責人或綁定手機（異動單） {#jgb/B/change-team-principal-or-phone}
- phrasings:
  - {text: "物件負責人怎麼指定", source: "koyu:slug92#14", status: proposed}
- sources: [kb:3359]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
團隊成員可設定不同的操作權限，包括物件授權、帳務檢視等。
團隊擁有者擁有最高權限。
物件可授權給特定團隊成員管理，授權後該成員可查看與操作指定物件的相關功能。
若需變更團隊主要負責人或綁定手機號碼，請透過異動單申請。

### 找不到某功能或無法操作的可能原因 {#jgb/B/feature-not-visible-troubleshooting}
- phrasings:
  - {text: "權限不足", source: "question_summary:3482", status: proposed}
  - {text: "看不到功能", source: "question_summary:3482", status: proposed}
- sources: [kb:3482]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在系統中找不到某功能或無法操作的可能原因：1. 角色限制：目前登入的角色不支援該功能（如租客無法看到物件管理），請確認是否需要切換角色；2. 訂閱方案限制：部分進階功能需要特定方案才能使用，請確認訂閱方案是否包含該功能；3. 團隊權限限制：團隊成員的權限可能未包含該功能，請聯繫團隊管理者調整權限；4. 功能開關：部分功能需由管理者在後台開啟（如差額發票），請聯繫客服確認。
若以上都不是原因，請嘗試重新登入或清除瀏覽器快取。

### 怎麼新增大房東並設定他能看的物件範圍 {#jgb/B/add-owner-landlord-and-access}
- phrasings:
  - {text: "大房東新增", source: "question_summary:3464", status: proposed}
  - {text: "權限設定", source: "question_summary:3464", status: proposed}
  - {text: "大房東要怎麼新增", source: "koyu:Landlordonboarding02#3", status: proposed}
  - {text: "大房東要怎麼看自己的物件", source: "koyu:Landlordonboarding00#1", status: proposed}
  - {text: "物件怎麼新增", source: "koyu:slug1#6", status: proposed}
  - {text: "要怎麼新增物件", source: "koyu:onboarding4#1", status: proposed}
  - {text: "要怎麼新增合約", source: "koyu:slug71#1", status: proposed}
- sources: [kb:3464]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增大房東操作：1. 進入大房東管理頁面，點選新增；2. 填寫大房東資訊（姓名、聯絡方式）；3. 設定物件存取權限（指定該大房東可查看哪些物件的合約和帳單）；4. 發送邀請通知。
大房東權限可細分為：查看物件、查看合約、查看帳單等。
權限設定後，大房東登入系統只能看到被授權範圍內的資料。
若大房東尚未註冊 JGB 帳號，可發送邀請通知引導其完成註冊。

### 大房東聯絡簿怎麼批次匯入匯出 {#jgb/B/owner-landlord-contact-book-import-export}
- phrasings:
  - {text: "大房東聯絡簿", source: "question_summary:3467", status: proposed}
  - {text: "批次匯入匯出", source: "question_summary:3467", status: proposed}
  - {text: "批次匯入物件怎麼弄", source: "koyu:qa01#5", status: proposed}
  - {text: "要怎麼批次發送帳單", source: "koyu:onboarding12#1", status: proposed}
- sources: [kb:3467]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東聯絡簿功能讓物管可以集中管理所有大房東的聯絡資訊。
支援 Excel 批次匯入和匯出功能：（1）匯出：將所有大房東的聯絡資訊和綁定物件清冊匯出為 Excel 檔案；（2）匯入：透過 Excel 範本批次新增或更新大房東聯絡記錄。
此功能方便物管進行大量資料維護，無需逐一手動修改。
