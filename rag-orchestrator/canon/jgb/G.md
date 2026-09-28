---
coarse: G
title: 裝置（IoT）
scope: IoT 門鎖、密碼、裝置廠商與狀態；⛔ 抄表歸 E
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 電表列表與單一電表 {#G-power-meter}
### 電錶清單怎麼切換分類？（所有電錶、一般型、儲值型三個分類，切換後會換一批列表） {#jgb/G/power-meter-list-category-tabs}
- phrasings:
  - {text: "電錶清單怎麼切換分類", source: "draft:outline-20260920", status: proposed}
  - {text: "一般型跟儲值型電錶差在哪裡看", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼只看儲值型電錶", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶分類標籤有哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/list/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電錶清單最上方有三個分類：所有電錶、一般型、儲值型，點選其中一個會換成該分類底下的電錶列表。
### 電錶清單的狀態標籤是什麼意思？（全部／供電中／斷電中／未連線，夾在分類跟清單之間；未連線含未啟用） {#jgb/G/power-meter-list-status-tags}
- phrasings:
  - {text: "電錶未連線標籤是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "未啟用跟未連線一樣嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "供電中斷電中是什麼標籤", source: "draft:outline-20260920", status: proposed}
  - {text: "狀態標籤在畫面哪個位置", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/list/Index.jsx, code:app/Http/Controllers/IotController.php, code:src/pages/iots/_parts/PowerTag.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
分類標籤下面、清單本身上面，還有一排全部、供電中、斷電中、未連線四個狀態標籤，可以再篩一層。
未連線標籤旁邊的數字，把未連線跟未啟用兩種狀態都算進去；電錶本身顯示的文字如果是未啟用，篩選時同樣算在未連線這個標籤底下，不是另外分開算。
### 電錶清單怎麼用關鍵字搜尋？（可選描述、序號、設備名稱、所屬物件名稱其中一種） {#jgb/G/power-meter-list-search}
- phrasings:
  - {text: "電錶清單怎麼搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼找特定的電錶", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶搜尋範圍有哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/list/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
可以用關鍵字搜尋，搜尋範圍可選描述、序號、設備名稱或所屬物件名稱其中一種。
### 電錶清單怎麼排序？（可依設備描述、目前電度、預計可用電度排序；門鎖、攝影機、小白盒清單沒有排序選單） {#jgb/G/power-meter-list-sort}
- phrasings:
  - {text: "電錶清單可以排序嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶列表的排序選單", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖清單能排序嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Iot.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
清單另外有排序選單，可以依設備描述、目前電度、預計可用電度各自的大小排序。
門鎖、攝影機、小白盒清單沒有這些排序選項可選。
### 電錶清單出現「原廠系統維護中」是什麼意思？（維護期間度數不更新、無法儲值） {#jgb/G/power-meter-manufacturer-maintenance}
- phrasings:
  - {text: "電錶維護中是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶顯示原廠系統維護中怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "維護期間可以儲值嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶度數為什麼不會動", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/MaintenanceNotice.jsx, code:src/pages/iots/_parts/IotItem.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
當電錶所屬的廠商系統正在維護時，清單頁與單一電錶頁最上方都會出現一則紅色提示，寫著電錶原廠系統維護中並附上維護的起訖時間。
維護期間這支電錶的度數不會更新，也無法進行儲值，需等維護結束後再試。
這則提示目前只會出現在其中一家電錶廠商的電錶上，其他廠商的電錶不會顯示這則提示、仍可正常操作。
### 電錶顯示「目前連不上廠商」怎麼辦？（度數不會更新、儲值送不出去；業者跟租客都看得到） {#jgb/G/power-meter-vendor-unreachable}
- phrasings:
  - {text: "電錶連不上廠商是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼電錶儲值不了", source: "draft:outline-20260920", status: proposed}
  - {text: "租客看得到連不上廠商的提示嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶度數為什麼不會更新", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/ManufacturerServiceNotice.jsx, code:app/Http/Controllers/IotController.php]
- target_user: [property_manager, tenant]
- business_types: [system_provider]
- instance_applicability: general
如果目前連不上某個廠商，清單頁與單一電錶頁最上方都會出現一則提示，寫著目前連不上該廠商，並附上錯誤原因。
提示會說明「目前無法儲值送電，電錶度數也不會更新，請聯絡該廠商確認服務狀態」；這個提示沒有對應帳號可標示。
這則提示業者跟租客都看得到：被擋住儲值、度數不更新的是這支錶，不分身分都要讓人知道原因。
只有這個身分底下真的掛著會連不上的那家廠商的電錶時才會出現這則提示。
### 電錶顯示「服務到期」或「快到期」怎麼辦？（30 天內到期會提醒續訂；只有業者看得到，只出現在清單頁） {#jgb/G/power-meter-service-expiry}
- phrasings:
  - {text: "電錶服務快到期怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶帳號到期會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼有些電錶帳號沒有顯示到期提示", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶到期提示租客看得到嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/ManufacturerServiceNotice.jsx, code:app/Http/Controllers/IotController.php, code:src/pages/iots/_parts/Single.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
已到期或已回報連不上的帳號，每一個都會列出來；還沒發生問題的帳號最多只會列出最急的一行，如果剩餘天數在 30 天以內一定會列出來，天數還很遠、且已經有到期或連不上的紅字時，這一行日期才會被拿掉不顯示。
提示會寫出是哪一個帳號：已到期時寫「目前無法儲值送電，電錶度數也不會更新，請盡快向該廠商續訂」，30 天內快到期時才寫「到期後將無法儲值送電，電錶度數也不會更新，請盡快向該廠商續訂」。
底下沒有接任何電錶的廠商帳號不會出現在提示裡。
這組提示只有業者身分看得到，租客一律看不到；也只出現在電錶清單頁，單一電錶頁不會顯示。
### 電錶清單每一列顯示什麼？（型號序號、目前電度、狀態、所屬物件；儲值型才有預計可用電度與低電度警報） {#jgb/G/power-meter-list-row-fields}
- phrasings:
  - {text: "電錶清單有哪些欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶列表顯示什麼資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "儲值型電錶跟一般型差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "最後連線成功時間是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/IotItem.jsx, code:src/pages/iots/_parts/PowerTag.jsx, code:app/Http/Controllers/Admin/CustomerServiceController.php, code:app/Jobs/DaeJob.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
每一列會顯示設備名稱與序號、描述、目前電度、狀態標籤，以及所屬物件的縮圖。
狀態旁邊會另外寫出這支電錶最後一次真的連線成功的時間，跟畫面上方「畫面開啟時間」不是同一件事：後者只是打開這一頁的當下。
只有儲值型電錶會顯示預計可用電度（估算），一般型電錶這一欄固定顯示「非儲值電錶」。
儲值型電錶如果可用電度偏低，會在預計可用電度旁多顯示一個低電度警報標籤；這個警報的門檻值是廠商那邊同步過來的，JGB 介面本身沒有讓房東調整這個門檻的地方，儲值型分頁的清單最下面有一行提示，寫著若要修改低電度警報，要到台科電雲端儲值系統修改。
### 電錶清單列展開後能看什麼？（用電量走勢圖可選 1/7/30/90 天；CSV 只能下載前 90 天） {#jgb/G/power-meter-usage-chart-export}
- phrasings:
  - {text: "電錶用電量走勢圖去哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶清單怎麼匯出CSV", source: "draft:outline-20260920", status: proposed}
  - {text: "用電量圖表可以選幾天", source: "draft:outline-20260920", status: proposed}
  - {text: "CSV可以下載多久的資料", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/IotItem.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點一列可以展開看用電量走勢圖，時間區間可選 1 天、7 天、30 天、90 天。
也可以匯出成 CSV，CSV 只能下載前 90 天的資料。
### 電錶編輯頁能改什麼？（儲值型有基本設定／電錶資料／開立發票三個頁籤，一般型只有基本設定） {#jgb/G/power-meter-single-edit-tabs}
- phrasings:
  - {text: "電錶編輯頁可以改什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶設定有哪些頁籤", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶怎麼改描述", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶發票設定在哪裡", source: "draft:outline-20260920", status: proposed}
  - {text: "一般型電錶編輯頁有電錶資料頁籤嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/Single.vue, code:src/utils/constants/iots.ts, code:src/pages/iots/edit/Log.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
編輯頁最上面可以修改這支電錶的描述文字，方便辨識，按儲存即生效。
基本設定頁籤可以綁定或移除這支電錶所屬的物件；一般型電錶的編輯頁只有這一個頁籤。
儲值型電錶才會多出電錶資料頁籤，裡面是這支電錶的基本資料（電號、餘額、費率、預計可用電度）、預設顯示的電錶儲值歷程（儲值時間、金額、儲值前後金額、操作者），以及另外點開才看得到的費率異動歷程。
只有儲值型電錶、且帳號已開通自動開立發票的情況下，才會多出一個「開立發票」頁籤；租客登入時看不到這個頁籤。
### 一支電錶只能綁一個物件？（選擇物件的挑選頁是單選，選了一個之後其他物件會被鎖住不能再選） {#jgb/G/power-meter-single-estate-single-bind}
- phrasings:
  - {text: "電錶可以綁幾個物件", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶能不能綁多個物件", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶綁定物件的規則", source: "draft:outline-20260920", status: proposed}
  - {text: "選擇物件是單選還是可以多選", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/edit/Basic.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電錶編輯頁的基本設定頁籤按「選擇物件」進入的物件挑選頁是單選：選了一個物件之後，清單上其他物件的選項都會被鎖住，沒辦法再加選第二個。
租客登入時看不到「選擇物件」按鈕與刪除物件的叉叉，無法自行變更電錶的綁定物件。
### 怎麼切換電錶的供電狀態？（一般型：供電／斷電；儲值型：儲值／強開／斷電，切換中鎖按鈕只有儲值型有） {#jgb/G/power-meter-mode-switch}
- phrasings:
  - {text: "電錶怎麼斷電", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼切換電錶模式", source: "draft:outline-20260920", status: proposed}
  - {text: "強開模式是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶切換中不能點是為什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/TopUpSwitch.vue, code:src/pages/iots/_parts/PowerSwitch.vue, code:src/pages/iots/_parts/Single.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般型電錶只能在供電、斷電兩個狀態間切換；儲值型電錶則有儲值模式、強開模式、斷電模式三種可選。
點選其中一個模式會先跳出確認視窗，確認後才會真正送出切換指令。
只有連線中、且不是租客身分時才能看到切換按鈕。
儲值型電錶的切換按鈕在處理中時會變成灰色、暫時無法再點；一般型電錶的供電／斷電按鈕沒有這個切換中鎖住的效果。
### 電錶資料頁的餘額、費率、預計可用電度怎麼看？（只有儲值型電錶才有這個頁籤；費率由雲端儲值系統設定，可用電度＝餘額÷費率） {#jgb/G/power-meter-basic-info-fields}
- phrasings:
  - {text: "電錶餘額怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶費率是誰設定的", source: "draft:outline-20260920", status: proposed}
  - {text: "預計可用電度怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "電號在哪裡查", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/PowerMeterInfo.jsx, code:src/utils/constants/iots.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
這幾個欄位只有儲值型電錶的編輯頁看得到，一般型電錶沒有電錶資料頁籤，不會看到這些欄位。
電錶資料頁籤會顯示電號、目前餘額、費率、預計可用電度（估算）與最後連線成功時間五個欄位。
費率是依照房東或管理者到廠商的雲端儲值系統設定的數值，非租客身分可以點連結直接跳轉過去設定，JGB 頁面本身沒有可以修改費率的欄位。
預計可用電度的算法是目前餘額除以費率。
### 電錶怎麼儲值？（「儲值」按鈕就在清單列上，不用展開；金額固定四個選項，維護中或連不上廠商時按鈕會變灰） {#jgb/G/power-meter-topup-flow}
- phrasings:
  - {text: "電錶怎麼儲值", source: "draft:outline-20260920", status: proposed}
  - {text: "儲值金額可以自己輸入嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "儲值後帳單在哪裡看", source: "draft:outline-20260920", status: proposed}
  - {text: "儲值歷程在哪裡查", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/IotItem.jsx, code:src/components/Lightbox/PowerMeterTopUp.vue, code:src/pages/iots/edit/Log.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
儲值型電錶的清單列本身就有一個「儲值」按鈕，不用先展開；一般型電錶的清單列不會出現這個按鈕。
儲值金額固定是 1000、1500、2000、2500 四個選項其中一個，沒有可以自己輸入金額的欄位。
電錶原廠系統維護中、或目前連不上廠商時，這支電錶清單列上的「儲值」按鈕會直接變灰、無法點擊，是把按鈕鎖住，不是點下去才跳出提示視窗。
儲值後會在帳務管理產生一筆帳單，繳費方式會跟著合約約定的繳款方式走。
儲值送出後，可以到電錶編輯頁的電錶資料頁籤、「電錶儲值歷程」清單裡查到這一筆的儲值時間、金額、儲值前後金額與操作者。
### 電錶／門鎖／攝影機／小白盒頁面需要什麼條件才能進入？（需訂閱方案、且未超過物件數量上限） {#jgb/G/iot-entry-requirements}
- phrasings:
  - {text: "電錶頁面打不開", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖頁面顯示需要訂閱", source: "draft:outline-20260920", status: proposed}
  - {text: "IoT 功能需要訂閱方案嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件數量超過會怎樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:routes/web.php]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
電錶清單、以及門鎖／攝影機／小白盒清單這兩條路由，都掛了需要訂閱方案跟物件數量沒超過上限這兩道檢查，任一項不符合就進不去頁面。
### 開立發票頁籤裡面能填什麼？（目前只有帳單是否開立發票一個選項） {#jgb/G/power-meter-invoice-tab-fields}
- phrasings:
  - {text: "開立發票頁籤能填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "電錶發票要怎麼設定統編", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單開立發票是哪個選項", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/_parts/Invoice.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
開立發票頁籤目前只有一組是／否選項，決定這支電錶產生的帳單要不要自動開立發票，選好按儲存即可。
出租方統一編號、稅別、承租方是否要打統一編號、買受人統一編號與買受人名稱這幾個欄位，目前在畫面上都看不到，也沒有地方可以填寫。
### 電錶清單沒有資料時畫面顯示什麼？（分類內沒有設備寫「此分類尚無設備」；完全沒綁定寫「目前尚無綁定設備」，租客看不到綁定引導連結） {#jgb/G/power-meter-list-empty-state}
- phrasings:
  - {text: "電錶清單沒有資料會顯示什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "此分類尚無設備是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "目前尚無綁定設備怎麼處理", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/iots/list/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果目前已經有綁定電錶廠商，只是切到的分類（例如儲值型）底下沒有電錶，會顯示此分類尚無設備。
如果完全還沒綁定任何電錶廠商，會顯示目前尚無綁定設備，並附上一行提示，告訴非租客身分的使用者要到團隊管理（或其他設定）的進階設定裡去綁定；租客登入時看不到這行綁定引導文字。
## 裝置頁（門鎖、攝影機、小白盒） {#G-device-page}
### 門鎖／攝影機／小白盒清單長什麼樣？（型號序號、描述、狀態、所屬物件四欄，可依關鍵字搜尋，沒有排序選單） {#jgb/G/device-page-shared-list}
- phrasings:
  - {text: "門鎖清單長怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "攝影機列表有哪些欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "小白盒怎麼看清單", source: "draft:outline-20260920", status: proposed}
  - {text: "裝置清單怎麼搜尋", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/iot/index.blade.php, code:app/Iot.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
門鎖、攝影機、小白盒各自有獨立的裝置清單頁，欄位固定是型號＆序號、描述、狀態、所屬物件四欄。
可以用關鍵字搜尋描述、序號、設備型號或所屬物件名稱其中一種；這幾種裝置清單沒有像電錶清單那樣的大小排序選單。
清單裡完全沒有綁定設備時，會提示尚無綁定設備，並附上前往進階設定綁定廠商的連結。
### 門鎖清單怎麼直接開門／鎖門？（開門一定有、鎖門只有特定廠商支援；離線時按鈕不會顯示） {#jgb/G/device-page-lock-open-close}
- phrasings:
  - {text: "門鎖怎麼直接開門", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼在清單上鎖門", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼我的門鎖沒有鎖門按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖離線還能操作嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/iot/index.blade.php, code:app/Http/Controllers/IotController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在門鎖清單每一列可以直接按開門，按下後會先跳出確認視窗，確認才會真的送出開門指令。
鎖門按鈕只有 SkyWatch 品牌的門鎖才有，其他廠商的門鎖清單上只會看到開門一個按鈕。
SkyWatch 門鎖的狀態欄位會直接顯示已開門或已關門，其他門鎖只會顯示連線中或未連線，不會顯示目前開或關。
門鎖離線（未連線）時開門/鎖門按鈕都不會顯示。
門鎖顯示未連線時，畫面上沒有提供排查步驟或重新連線的操作說明，只能看到未連線這個狀態字樣本身。
### 裝置編輯頁的頁籤，門鎖跟攝影機／小白盒不一樣？（門鎖多出密碼設定、開門記錄兩個頁籤） {#jgb/G/device-edit-tabs-by-type}
- phrasings:
  - {text: "攝影機編輯頁有哪些頁籤", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖設定頁籤有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "小白盒可以改密碼嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "裝置編輯頁功能", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/entry/iot.js, code:resources/views/iot/index.blade.php, code:resources/views/iot/doorlock/basic.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
編輯頁最上方都可以修改裝置描述，方便辨識。
門鎖裝置的編輯頁有基本設定、密碼設定、開門記錄三個頁籤；攝影機與小白盒的編輯頁只有基本設定一個頁籤。
基本設定頁籤都可以選擇或移除這台裝置綁定的物件。
編輯按鈕在裝置所屬的分類群組被標記成不可編輯時會鎖住、變灰；不過目前程式把這個群組一律標記為可編輯，所以編輯按鈕在畫面上不會真的被這個機制鎖住。
### 私人門鎖跟共用門鎖差在哪？（私人只能綁一個物件，共用可以綁多個） {#jgb/G/device-lock-type-and-binding-limit}
- phrasings:
  - {text: "私人門鎖跟共用門鎖差別", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖可以綁幾間房", source: "draft:outline-20260920", status: proposed}
  - {text: "共用門鎖是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖類型怎麼選", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/iot/doorlock/basic.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
私人門鎖是個人房間的門鎖，只能綁定一個物件；共用門鎖是大樓大門、住家大門這類公用門鎖，可以綁定多個物件。
一旦這把鎖已經綁了超過一個物件，門鎖類型的選項就會鎖住私人門鎖這個選項，無法再切回私人門鎖。
### 門鎖密碼有哪三種？（房東個人密碼、租客個人密碼、租客共用密碼，權限各不同） {#jgb/G/device-lock-passwords-three-types}
- phrasings:
  - {text: "門鎖密碼有幾種", source: "draft:outline-20260920", status: proposed}
  - {text: "租客密碼房東能改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "共用密碼是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "門鎖密碼設定規則", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/iot/doorlock/password.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
密碼設定頁籤上有房東個人專屬密碼（6碼），是房東專用的解鎖密碼，可以編輯後儲存。
租客個人專屬密碼（4碼）預設是租客手機號碼末四碼，租客可以自行變更，房東不能修改內容，只能開關這組密碼要不要啟用。
共用門鎖才會出現租客共用密碼（6碼）區塊，房東可以新增、刪除，也可以一鍵複製一段包含密碼的通知文字方便傳給租客；畫面上雖然定義了「編輯密碼」按鈕，但這顆按鈕被設定成永遠不會顯示，實際上沒有編輯既有密碼內容的入口，只能刪除後重新新增一組。
私人門鎖不會顯示租客共用密碼這個區塊。
### 門鎖的開門記錄怎麼看？（可依日期查詢操作時間與動作，沒有記錄時會顯示尚無記錄） {#jgb/G/device-lock-open-log}
- phrasings:
  - {text: "門鎖開門記錄在哪裡看", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼查門鎖歷史紀錄", source: "draft:outline-20260920", status: proposed}
  - {text: "開門記錄有哪些欄位", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/iot/doorlock/log.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
開門記錄頁籤可以選擇記錄日期，切換後會重新載入該天的紀錄。
每一筆記錄顯示操作時間與動作兩個欄位；當天沒有任何記錄時會顯示尚無記錄。
### 小白盒綁定物件跟門鎖不同在哪？（小白盒不會讓物件被標記為「IoT裝置」，也不會擋刪除） {#jgb/G/device-gateway-not-counted}
- phrasings:
  - {text: "小白盒是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "小白盒綁物件有差嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件為什麼沒顯示IoT裝置標籤", source: "draft:outline-20260920", status: proposed}
  - {text: "物件刪不掉是不是因為有綁裝置", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/IotController.php, code:app/Estate.php, code:app/Http/Controllers/EstateController.php, code:resources/views/iot/index.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
小白盒綁定物件之後，該物件不會被系統標記為「IoT裝置」這個標籤；只有門鎖、電錶、攝影機這些非小白盒的裝置綁定物件後，該物件才會被標記為 IoT裝置。
物件如果還有 IoT裝置綁定（小白盒不算），會被擋下無法刪除，畫面會提示您無法刪除尚有 IoT 綁定的該物件；只綁小白盒的物件不受這個限制。
## 遠端解鎖（輸入解鎖密碼開門） {#G-remote-unlock}
### 遠端解鎖連結怎麼用？（輸入共用密碼按開門，密碼錯誤或連結失效會提示原因；找不到產生這個連結的入口） {#jgb/G/remote-unlock-page}
- phrasings:
  - {text: "遠端解鎖連結怎麼用", source: "draft:outline-20260920", status: proposed}
  - {text: "收到開門連結要怎麼開門", source: "draft:outline-20260920", status: proposed}
  - {text: "解鎖密碼輸入錯誤會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "這個開門連結為什麼失效", source: "draft:outline-20260920", status: proposed}
  - {text: "遠端解鎖連結怎麼產生", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/tools/unlock/Index.vue, code:app/Http/Controllers/ToolController.php, code:routes/web.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
打開遠端解鎖連結後，畫面上會顯示這台門鎖的名稱，並有一個欄位讓人輸入解鎖密碼，輸入完按開門即可送出。
這裡輸入的密碼會拿去比對這把門鎖的租客共用密碼，不是房東個人密碼或租客個人密碼。
密碼輸入錯誤時會提示密碼錯誤；連結本身失效（裝置不存在或連結碼不符）時會提示設備不存在並導回首頁。
密碼正確但門鎖實際開鎖失敗時，會提示門鎖開啟失敗。
在門鎖的編輯頁與密碼設定頁籤裡，找不到任何按鈕或畫面會產生、顯示這個遠端解鎖連結；連結裡的連結碼是用這台門鎖的建立時間算出來的固定值，不是每次點擊都重新產生的。
### 遠端解鎖連結需要登入嗎？（不用登入，只要有連結跟密碼就能開） {#jgb/G/remote-unlock-no-login}
- phrasings:
  - {text: "遠端解鎖要登入嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "開門連結免登入嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有帳號可以開門嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:routes/web.php, code:src/pages/tools/unlock/Index.vue]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
遠端解鎖頁面不需要先登入 JGB 帳號，只要開啟連結、輸入正確的密碼就能開門。
