---
coarse: C
title: 社區與物件
scope: 社區建檔、物件新增與批次匯入、刊登與銷售、物件狀態與欄位；⛔ 物件上的租約歸 D、抄表歸 E
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 社區與物件 {#C}
### 房源管理模組做什麼（含自訂狀態標籤） {#jgb/C/property-management-overview}
- phrasings:
  - {text: "VR看屋", source: "question_summary:3599", status: approved}
  - {text: "房源管理", source: "question_summary:3599", status: approved}
  - {text: "批次上傳", source: "question_summary:3599", status: approved}
  - {text: "物件集中", source: "question_summary:3599", status: approved}
  - {text: "社區歸戶", source: "question_summary:3599", status: approved}
  - {text: "物件自訂標籤有什麼用", source: "gapmap:C15", status: approved}
- sources: [kb:3599, docs:knowledge/jgb-product-facts.md#estate-labels, helpcenter:slug90]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
物件多、資料分散難管？
金箍棒的房源管理把所有物件集中：物件建檔、社區歸戶、批次上傳，還有招租公開頁與 VR 看屋連結，取代散落的 Excel。
物件可以貼團隊自訂的狀態標籤（預設有可帶看、待清潔、待簽約、維修中、不出租、待完善六種），方便篩選與分工。
想看實際畫面可預約 demo。

### 社區建立與批次新增物件 {#jgb/C/community-batch-create}
- phrasings:
  - {text: "如何新增物件?", source: "helpcenter:slug1", status: approved}
  - {text: "物件批次新增表格如何填寫?", source: "helpcenter:qa01", status: approved}
  - {text: "社區可以批次建立嗎", source: "koyu:property（原#7", status: approved}
- sources: [draft:batch#6, helpcenter:onboarding4]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒用「社區」把同一棟或同一社區的物件歸戶管理。
流程是先建立社區，再在「社區總表」選該社區，按右側的「批次新增」下載 Excel 模板、填入物件資料後上傳，就能一次把整批物件建進系統；單筆新增則在物件總表「新增物件」。
想看實際畫面可預約 demo。

### 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 {#jgb/C/property-status-meaning}
- phrasings:
  - {text: "未刊登是什麼意思", source: "koyu:slug10#15", status: approved}
  - {text: "已失效是什麼意思", source: "koyu:slug20#3", status: approved}
  - {text: "已支出是什麼意思", source: "koyu:slug88#15", status: approved}
  - {text: "帳單狀態顯示「已失效」是什麼意思?", source: "helpcenter:billexpired", status: approved}
  - {text: "找補費用是什麼意思", source: "koyu:slug66#6", status: approved}
  - {text: "未退押金是什麼意思", source: "koyu:slug28#14", status: approved}
  - {text: "物件狀態有什麼差別", source: "koyu:slug39#6", status: approved}
  - {text: "紅色的字是什麼意思", source: "koyu:slug24#9", status: approved}
  - {text: "自動對帳是什麼意思", source: "koyu:slug75#15", status: approved}
  - {text: "洽談中的物件可以做什麼", source: "koyu:property（原#5", status: approved}
  - {text: "解約後30天是什麼意思", source: "koyu:slug29#14", status: approved}
- sources: [draft:batch#5, helpcenter:slug39, kb:3428, kb:4154]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件總表把物件分成四種狀態：「未刊登」是建好還沒對外刊登，可編輯、刊登或刪除；「刊登中」是已對外招租，可編輯、取消刊登、建立合約；「洽談中」代表已經建立合約但雙方還沒都簽署完成；雙方簽完就變成「合約中」（租約中）。
另外要注意刊登與合約是兩條獨立的軸，租約中的物件也可以同時在刊登中。
物件狀態要分兩條獨立軸來看。
合約軸四狀態：（1）未刊登：物件剛建立；（2）刊登中；（3）洽談中：已綁定合約但尚未完成簽署；（4）租約中：合約已簽署生效。
狀態隨合約流程推進——建立合約後進洽談中、簽署完成進租約中。
刊登軸（是否對外刊登公開）獨立於合約軸——租約中的物件也可以同時在刊登中（例如租約快到期先開放招租）。
兩軸不要混為一談：看「能不能建約」是刊登與必填欄位的問題；看「有沒有出租」才是合約軸的問題。

### 招租店舖與 VR 看屋 {#jgb/C/rental-storefront-vr}
- phrasings:
  - {text: "什麼是「房東對外首頁」(招租店舖)?", source: "helpcenter:slug90", status: approved}
  - {text: "招租店舖是什麼", source: "koyu:slug90#2", status: approved}
  - {text: "我改了大頭照對外首頁沒變", source: "koyu:slug90#8", status: approved}
- sources: [draft:batch#7, helpcenter:slug90]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒每個帳號或團隊都有自己的「房東對外首頁」（招租店舖），刊登中的物件會出現在上面供房客瀏覽；團隊可以在團隊管理設定招租頁面的專屬網址與時區，強化品牌辨識。
新增物件時可上傳 VR 物件連結，房客能在線上看屋。
想看招租頁長什麼樣可預約 demo。

### 社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定） {#jgb/C/community-setup-and-property-binding}
- phrasings:
  - {text: "建立編輯", source: "question_summary:3468", status: proposed}
  - {text: "社區管理", source: "question_summary:3468", status: proposed}
  - {text: "社區與物件關係", source: "question_summary:3469", status: proposed}
- sources: [kb:3468, kb:3469]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區管理功能讓物管/房東集中管理同一社區或大樓的物件。
建立社區步驟：1. 進入社區管理頁面，點選新增社區；2. 填寫基本資訊（社區名稱、地址、介紹、交通資訊）；3. 上傳社區照片；4. 儲存即完成建立。
建立後可將物件歸屬至該社區下進行統一管理。
也支援批次匯入方式一次建立多個社區。
編輯社區時可更新基本資料、照片和公開顯示設定。
社區與物件為一對多的關係：一個社區可包含多個物件，每個物件可歸屬於一個社區。
物件歸屬社區後，可在社區頁面統一查看該社區下的所有物件清單。
社區也支援設定「公共區域」物件（如公共設施、會議室等）。
在某些配置下（如社宅方案），系統會要求強制綁定社區，引導使用者在操作前先完成社區設定。

### 物件批次匯入：範本、表格填寫與上傳失敗 {#jgb/C/property-batch-import}
- phrasings:
  - {text: "Excel", source: "question_summary:3431", status: proposed}
  - {text: "物件批次匯入", source: "question_summary:3431", status: proposed}
  - {text: "匯入excel怎麼做", source: "koyu:qa01#15", status: proposed}
  - {text: "excel範本在哪裡下載", source: "koyu:qa01#2", status: proposed}
  - {text: "批次上傳失敗", source: "koyu:qa01#16", status: proposed}
- sources: [kb:3431, kb:3357, helpcenter:qa01_zh-Hant拷貝.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大量建立物件可使用 Excel 批次匯入功能：1. 在物件管理頁面選擇「批次匯入」；2. 下載匯入範本（一般物件範本或社宅物件範本）；3. 依範本格式填寫物件資料（名稱、地址、坪數、樓層、租金等）；4. 上傳完成的 Excel 檔案；5. 系統驗證並批次建立物件。
匯入成功後物件預設為「未刊登」狀態，需確認資料無誤後再手動上架。
社宅物件有專屬範本，包含額外的社宅專用欄位。
系統支援物件批次匯入，由 JGB 協助提供批次匯入表格。
注意事項：
檔案格式須為 .xls（非 .xlsx）
若上傳失敗，建議重新下載範本檔案，將資料複製後用 Ctrl+Shift+V（純文字貼上）方式貼入，避免格式異常
上傳成功後按重新整理，約 3 秒內會顯示
要批次新增物件時，入口在物件管理的社區總表：按右上方「新增物件」旁的三角形，選擇「批次新增」，再下載指定格式的 Excel 表格填寫。
批次新增用的 Excel 表格在程式上已設定好格式，填寫時請依照指定格式完成，不要更動表格既有的格式。
填寫批次新增表格時，用途、建築類型、地址（國家）、朝向方向、最短租期、產權登記這幾個欄位是下拉選單，必須從選單中的選項選擇。
批次新增表格中由使用者自行填寫的欄位包括：物件標題、地址（縣市、區）、樓層房間、平方單位、社區/大樓、屋齡、租金、押金、入住日期、交通、房源簡介、生活公約、廣告法定用途。
批次新增表格的金額欄位，格式請選擇「通用格式」，勿選擇「貨幣格式」。
需要更多批次新增的操作說明時，可透過線上客服聯繫，或參考其他幫助文章。

### 物件要怎麼刊登上架、刊登需要什麼條件 {#jgb/C/property-listing-conditions}
- phrasings:
  - {text: "上架條件", source: "question_summary:3429", status: proposed}
  - {text: "上架流程", source: "question_summary:4151", status: proposed}
  - {text: "物件刊登", source: "question_summary:3429", status: proposed}
  - {text: "物件要怎麼刊登", source: "question_summary:4151", status: proposed}
  - {text: "房源上架流程", source: "koyu:onboarding4#16", status: proposed}
  - {text: "房子要怎麼上架", source: "koyu:slug10#14", status: proposed}
- sources: [kb:3429, kb:4151]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件刊登（上架）需滿足以下條件：1. 帳號已訂閱方案（未訂閱無法刊登）；2. 已刊登物件數未達方案上限；3. 必填欄位已填寫完整，包含：物件名稱、租金、押金、坪數、樓層。
滿足條件後即可上架公開，物件會出現在搜尋結果中。
若刊登後修改資料導致必填欄位不完整，系統會自動下架該物件。

### 物件怎麼下架、為什麼突然全部下架 {#jgb/C/property-unlisting}
- phrasings:
  - {text: "條件流程", source: "question_summary:3430", status: proposed}
  - {text: "物件下架", source: "question_summary:3430", status: proposed}
  - {text: "物件為什麼突然全部下架", source: "question_summary:3506", status: proposed}
- sources: [kb:3430, kb:3506]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件下架有兩種情況：（1）手動下架：管理者主動將物件從公開列表移除，需具備物件管理或刊登權限；（2）自動下架：修改物件資料後，若必填欄位（名稱、租金、押金、坪數、樓層）驗證失敗，系統會自動下架。
下架後物件不會出現在搜尋結果中，但資料保留，可隨時重新上架。
已綁定合約的物件建議先處理完合約再下架。
物件突然全部下架，最常見的原因是訂閱續約扣款失敗——方案失效時系統會將物件自動下架。
請到「訂閱方案」頁確認方案狀態與付款方式，完成續約後再將物件重新上架。
若方案正常但個別物件被下架，多半是修改資料後必填欄位驗證失敗導致自動下架，補齊欄位後重新刊登即可。

### 編輯物件與刊登物件差在哪、為什麼修改沒存到 {#jgb/C/property-edit-vs-publish}
- phrasings:
  - {text: "刊登物件", source: "question_summary:4147", status: proposed}
  - {text: "編輯物件", source: "question_summary:4147", status: proposed}
  - {text: "編輯物件跟刊登物件差在哪", source: "koyu:property（原#4", status: proposed}
- sources: [kb:4147]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「編輯物件」是修改內容但不會上架，「刊登物件」才會把物件上架公開——兩個是不同動作。
編輯後務必按「儲存」再離開頁面：直接切換頁面不會自動儲存，修改的內容會遺失（客服常見案例：取消勾選設備後直接點回列表，結果沒存到）。
另外，任何狀態的物件都可以編輯，修改不會影響既有合約——合約簽訂當下已把物件資料快照保存。

### 為什麼不能新增物件 {#jgb/C/property-add-blocked}
- phrasings:
  - {text: "為什麼不能新增物件", source: "question_summary:3505", status: proposed}
  - {text: "未刊登的物件為什麼不能簽約", source: "koyu:slug71#17", status: proposed}
  - {text: "為什麼現在不能點退", source: "koyu:slug28#4", status: proposed}
  - {text: "為什麼我這間房子不能建合約", source: "koyu:slug71#7", status: proposed}
  - {text: "新進同事什麼都不能做", source: "koyu:qa23#9", status: proposed}
  - {text: "為什麼有些按鈕不見了", source: "koyu:slug39#5", status: proposed}
  - {text: "貝殼為什麼成長那麼快", source: "koyu:TOFILL-beike#2", status: proposed}
- sources: [kb:3505]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
無法新增物件最常見兩個原因：（1）訂閱方案的物件額度已滿——系統會提示方案已滿，可升級方案、加購物件額度，或刪除/下架不再使用的物件釋放額度；目前用量可在「訂閱方案」頁查看。
（2）帳號權限不足——新增物件需要對應的物件管理權限，請團隊管理者確認你的角色權限設定。

### 對外顯示地址改了為什麼後台還是完整地址 {#jgb/C/public-display-address}
- phrasings:
  - {text: "對外顯示地址", source: "question_summary:4145", status: proposed}
  - {text: "怎麼還是顯示完整地址", source: "question_summary:4152", status: proposed}
  - {text: "改了對外顯示地址", source: "question_summary:4152", status: proposed}
  - {text: "沒生效", source: "question_summary:4145", status: proposed}
  - {text: "還是完整地址", source: "question_summary:4145", status: proposed}
  - {text: "我設了對外顯示地址但還是看到完整地址", source: "koyu:property（原#12", status: proposed}
- sources: [kb:4145, kb:4152]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「對外顯示地址」只作用在物件的對外廣告頁與地圖顯示——業者自己的後台介面永遠顯示完整地址，這不是設定沒生效。
要確認效果，請打開物件的對外廣告頁（或招租店舖頁）查看：租客與外部訪客看到的就是對外顯示地址的版本。

### 招租店舖入口在哪、怎麼分享、為什麼物件沒出現 {#jgb/C/storefront-entry-share}
- phrasings:
  - {text: "房東對外首頁", source: "question_summary:4146", status: proposed}
  - {text: "招租店舖", source: "question_summary:4146", status: proposed}
- sources: [kb:4146]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
招租店舖（房東對外首頁）會公開展示團隊所有「刊登中」的物件，網址是 /p/ 開頭的專屬連結，可設定自訂帳號名稱讓網址更好記。
入口：登入後台後由側邊選單即可連到自己的店舖頁；店舖的封面照片、大頭照、自我介紹與「會員中心→帳號資訊」連動，改一處兩邊都會更新。
把店舖連結分享到 FB、LINE 就是現成的招租頁。
注意：非刊登中的物件不會出現在店舖，其廣告頁連結分享給別人也看不到內容。

### 社區公開頁面是什麼、能拿來做什麼 {#jgb/C/community-public-page}
- phrasings:
  - {text: "廣告展示", source: "question_summary:3470", status: proposed}
  - {text: "社區公開頁面", source: "question_summary:3470", status: proposed}
  - {text: "我的公開頁面在哪裡", source: "koyu:slug90#4", status: proposed}
- sources: [kb:3470]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區公開頁面是對外展示社區資訊的頁面，不需登入即可瀏覽。
頁面內容包含社區介紹、照片、地理位置和公開刊登中的物件列表。
此頁面可作為招租的行銷工具，將連結分享給有意租屋的人瀏覽社區和可租物件。
房東也有專屬的招租店鋪頁面，展示其所有公開物件。
頁面顯示的內容會隨物件刊登狀態即時更新。

### 物件 VR 虛擬導覽怎麼綁、費用與拍攝找誰 {#jgb/C/property-vr-tour}
- phrasings:
  - {text: "虛擬導覽", source: "question_summary:3433", status: proposed}
- sources: [kb:3433]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 物件頁支援 VR 虛擬導覽（整合 iStaging 服務）：在物件編輯頁的 VR 導覽區綁定後，物件公開頁會顯示 VR 看屋入口，瀏覽者可在網頁直接觀看 360 度全景。
VR 裝置申請、拍攝方式、marker 操作與費用等屬 iStaging 廠商服務範圍，請直接洽 iStaging，或聯繫客服協助轉介。

### 物件自訂標籤怎麼建、怎麼用來篩選 {#jgb/C/property-custom-tags}
- phrasings:
  - {text: "分類管理", source: "question_summary:3434", status: proposed}
  - {text: "物件自訂標籤", source: "question_summary:3434", status: proposed}
- sources: [kb:3434]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
自訂標籤功能讓房東可以為物件加上自訂分類標記，方便搜尋和管理。
例如可建立「寵物友善」、「近捷運」、「含家具」等標籤。
操作方式：在帳號設定的「自訂標籤」頁面新增標籤，然後在物件編輯時勾選適用的標籤。
物件列表支援依標籤篩選，快速找到符合條件的物件。
標籤也會顯示在物件的公開頁面上，幫助租客篩選。

### 物件列表進階搜尋怎麼用 {#jgb/C/property-advanced-search}
- phrasings:
  - {text: "進階搜尋怎麼操作", source: "koyu:slug93#13", status: proposed}
  - {text: "進階搜尋要怎麼用", source: "koyu:slug93#1", status: proposed}
  - {text: "進階搜尋在哪", source: "koyu:slug93#6", status: proposed}
  - {text: "點交物件怎麼用", source: "koyu:onboarding7#15", status: proposed}
  - {text: "進階搜尋功能如何用?", source: "helpcenter:slug93", status: proposed}
  - {text: "物件怎麼建", source: "koyu:onboarding4#15", status: proposed}
  - {text: "行動版怎麼用", source: "koyu:Landlordonboarding00phone#14", status: proposed}
  - {text: "招租頁面怎麼用", source: "koyu:slug90#14", status: proposed}
  - {text: "角色管理怎麼用", source: "koyu:qa23#6", status: proposed}
  - {text: "藍心ATM怎麼用", source: "koyu:slug100#13", status: proposed}
  - {text: "角色資料卡怎麼用", source: "koyu:slug101#13", status: proposed}
- sources: [helpcenter:slug93]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在物件列表找物件時，除了一般的關鍵字搜尋之外，還可以使用進階搜尋功能做篩選。
進階搜尋可以把「空間類型」、「社區大樓」、「租金範圍」、「坪數」作為篩選工具，縮小物件列表的搜尋結果。
需要更多進階搜尋的操作說明時，可透過線上客服聯繫，或參考其他幫助文章。

### 首頁即時物件出租率怎麼算、已出租數字從哪來 {#jgb/C/occupancy-rate-calculation}
- phrasings:
  - {text: "即時物件出租率", source: "question_summary:4648", status: proposed}
  - {text: "已出租數字來源", source: "question_summary:4648", status: proposed}
  - {text: "百分比怎麼算", source: "question_summary:4648", status: proposed}
- sources: [kb:4648]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
首頁「即時物件出租率」的已出租數字，是以「合約中的物件總數量 ÷ 物件總數」計算出來的百分比，會隨合約綁定的物件數量即時變動。

### 社區有哪些公共設施、開放時間、費用與變更通知 {#jgb/C/community-facilities-and-hours}
- phrasings:
  - {text: "交誼廳", source: "question_summary:4262", status: proposed}
  - {text: "健身房", source: "question_summary:4262", status: proposed}
  - {text: "公共設施", source: "question_summary:4262", status: proposed}
  - {text: "公共設施使用", source: "question_summary:3058", status: proposed}
  - {text: "公共設施使用變更", source: "question_summary:3063", status: proposed}
  - {text: "公共設施使用費用", source: "question_summary:3059", status: proposed}
  - {text: "公共設施費用", source: "question_summary:3299", status: proposed}
  - {text: "公共設施開放時間", source: "question_summary:3056", status: proposed}
  - {text: "社區公共設施有哪些", source: "question_summary:1396", status: proposed}
  - {text: "社區有哪些公共設施可以用", source: "question_summary:4276", status: proposed}
  - {text: "社區設施", source: "question_summary:4262", status: proposed}
  - {text: "社區設施開放", source: "question_summary:3246", status: proposed}
- sources: [kb:1396, kb:4262, kb:4276, kb:3056, kb:3058, kb:3246, kb:3063, kb:3059, kb:3299]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
請提供您的物件地址和想查詢的設施名稱，我將為您查詢詳細資訊。
社區內公共設施的開放時間通常為上午6點至晚上10點，但具體時間可能會因社區規定而有所不同。
請提供您的物件地址，我幫您查詢更詳細的資訊。
社區內的公共設施使用時間通常會有一定的限制，具體使用時間請參考社區的管理規範或聯繫您的管理師以獲取詳細資訊。
春節期間社區設施的開放情況可能會有所調整，具體時間請聯繫您的管理師確認。
通常在假期期間，設施的開放時間會依照社區的規定進行調整，以確保所有住戶的安全與便利。
社區內公共設施的使用變更需要提前通知租客，這樣可以確保租客了解相關變更及可能影響。
如果您有任何疑問或需要更詳細的信息，建議聯繫您的管理師確認具體情況。
社區內的公共設施一般來說是不需要額外支付費用的，這些設施的維護費用通常已包含在管理費中。
不過，某些特定設施如健身房、游泳池等可能會有額外的使用費，建議您確認相關社區規定或聯繫管理師以獲取詳細資訊。
社區內的公共設施一般不需要額外支付費用，這些費用通常已包含在管理費中。
不過，某些特定設施（如健身房、游泳池等）可能會有額外的使用費用，建議您查看社區規範或與管理師確認。

### 公共設施使用規範：權利、義務、安全規範與違規後果 {#jgb/C/community-facility-usage-rules}
- phrasings:
  - {text: "公共區域使用權限", source: "question_summary:2980", status: proposed}
  - {text: "公共設施使用權", source: "question_summary:3049", status: proposed}
  - {text: "公共設施使用義務", source: "question_summary:3245", status: proposed}
  - {text: "公共設施使用規則", source: "question_summary:3247", status: proposed}
  - {text: "公共設施使用規範", source: "question_summary:3061", status: proposed}
  - {text: "公共設施安全規範", source: "question_summary:3248", status: proposed}
  - {text: "公共設施義務", source: "question_summary:3050", status: proposed}
  - {text: "公共設施規範", source: "question_summary:3060", status: proposed}
- sources: [kb:2980, kb:3049, kb:3050, kb:3245, kb:3061, kb:3248, kb:3060, kb:3247]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客在公共區域的使用權限通常包括進入、使用和享受公共設施，但不得妨礙其他租客的使用權。
具體限制可能包括禁止在公共區域吸煙、存放個人物品或進行商業活動。
請參考租約或聯繫您的管理師以獲取詳細資訊。
租客在公共設施中享有使用權利，包括合理使用設施的自由，以及在遵守社區規範下，享受設施提供的便利與服務。
若有任何設施使用上的疑問或需要，請隨時聯繫管理師協助。
租客在公共設施中的使用義務包括遵守社區規範，不得損壞設施，並保持環境整潔。
此外，租客需尊重其他使用者的權利，避免大聲喧嘩或其他影響公共安寧的行為。
若發現設施故障或問題，請及時通知管理師進行維修。
租客在公共設施中有保持清潔、遵守使用時間、愛護設施的義務。
此外，租客應遵循社區規範，避免喧鬧和損壞設施。
如有問題或需進一步了解規範，建議聯繫您的管理師。
社區內公共設施的安全使用規範通常包括遵守使用時間、保持設施清潔、遵守人數限制以及不在設施內進行危險行為等。
建議您查看社區公告或聯繫您的管理師以獲取具體的使用規範和要求。
社區內公共設施的安全使用規範通常包括遵循使用時間、保持設施清潔、避免攜帶危險物品、及遵守相關標示與指示。
如需詳細規範，建議您聯繫您的管理師確認具體條款與規範。
違反公共設施使用規則可能會導致警告、罰款或限制使用該設施的權利。
這些措施旨在維護社區的良好秩序，因此建議您遵守相關規定，以避免不必要的處罰。
違反公共設施使用規則可能會受到管理方的警告或罰款，具體懲處方式會依照社區規範而定。
作為房客，您有權了解規則及相關後果，並可向管理師詢問具體細節以保護您的權益。

### 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 {#jgb/C/community-garbage-disposal}
- phrasings:
  - {text: "垃圾分類規範", source: "question_summary:3053", status: proposed}
  - {text: "垃圾回收時間", source: "question_summary:3054", status: proposed}
  - {text: "大型廢棄物處理", source: "question_summary:3055", status: proposed}
  - {text: "洗衣機使用規範", source: "question_summary:3051", status: proposed}
  - {text: "烘衣機使用規範", source: "question_summary:3052", status: proposed}
- sources: [kb:3053, kb:3054, kb:3055, kb:3051, kb:3052]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區內的垃圾分類規範通常分為可回收物、廚餘及一般垃圾，請依照社區公告的指示進行分類。
可回收物需要清潔並分開放置，而廚餘則需放入專用容器中。
建議您查看社區公告或詢問管理師以獲取具體的分類規範。
社區內的垃圾回收時間通常是每週二和每週五的早上7點。
建議您在這之前將垃圾放置到指定位置，確保能夠順利回收。
如有變更，請聯繫您的管理師確認。
社區內的大型廢棄物處理通常會依照社區規定進行，可能會定期安排專門的清運服務。
建議您向管理師查詢具體的處理時間和方式，也可以了解是否有特定的處理平台或指引。
您的意見和需求也可以反映給管理師，以便改善服務。
社區內的洗衣機使用規範通常包括按時清理洗衣槽、遵守使用時間、避免超載等。
建議您查閱社區公告或聯繫您的管理師以獲取具體細節。
社區內的烘衣機使用規範通常包括：使用前需清理烘衣機內部，並將衣物均勻放置以避免機器損壞；每次使用後請關閉電源，保持設施的整潔。
此外，請遵守使用時間，避免佔用過長時間以便其他住戶使用。
如需更詳細的規範，建議聯繫您的管理師確認。

### 公共設施損壞責任、使用爭議處理與責任保險 {#jgb/C/community-facility-disputes}
- phrasings:
  - {text: "公共設施保險", source: "question_summary:3064", status: proposed}
  - {text: "公共設施投保", source: "question_summary:3300", status: proposed}
  - {text: "公共設施損壞", source: "question_summary:3057", status: proposed}
  - {text: "公共設施爭議", source: "question_summary:3249", status: proposed}
  - {text: "公共設施爭議解決", source: "question_summary:3062", status: proposed}
- sources: [kb:3057, kb:3062, kb:3249, kb:3064, kb:3300]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客不需要對公共設施的損壞負責賠償，這類問題應由物業管理方負責處理。
若發現公共設施損壞，建議您及時通知管理師進行維修。
如果對公共設施的使用產生爭議，您可以首先與其他住戶進行溝通，尋求協商解決。
如果無法達成共識，建議您聯繫您的管理師，讓他們協助調解和解決問題，並確保所有住戶的權益得到保障。
如果對公共設施的使用產生爭議，建議您首先與其他使用者進行溝通協調。
如果問題無法解決，可以向您的管理師反映，並請求協助處理。
管理師會根據社區規範及相關規定進行調查，並協助您尋找解決方案。
社區內的公共設施通常需要投保責任保險，以保障所有住戶的安全和權益。
這項保險能夠涵蓋意外事故造成的損害，為住戶提供必要的保障。
如果您有任何具體的疑問或建議，建議您聯繫您的管理師確認相關的保險政策和條款。
社區內的公共設施通常是由管理單位負責投保責任保險，以保障使用者的安全和權益。
您作為房客，使用這些設施時享有相應的安全保障。
若有具體問題或需要更多資訊，建議您聯繫您的管理師確認細節。

### 社區生活服務與活動（社區活動、包裹代收、社宅社區服務） {#jgb/C/community-services-and-events}
- phrasings:
  - {text: "社區活動", source: "question_summary:3157", status: proposed}
  - {text: "社會〈社區名〉服務", source: "question_summary:3263", status: proposed}
  - {text: "管理員會代收包裹嗎", source: "question_summary:4272", status: proposed}
- sources: [kb:3157, kb:3263, kb:4272]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
我們的業者會不定期舉辦社區活動，這些活動旨在促進房客之間的交流與互動，增進社區的和諧氛圍。
具體活動內容和時間，您可以向您的管理師詢問以獲取最新資訊。
社會住宅通常提供多種社區服務，包括社區活動、心理諮詢、健康檢查、法律諮詢及就業輔導等，旨在提升居住者的生活品質與社會融入。
這些服務可能因不同住宅而異，建議您向管理師確認具體可用服務。
