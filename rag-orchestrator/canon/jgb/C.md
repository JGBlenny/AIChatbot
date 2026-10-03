---
coarse: C
title: 社區與物件
scope: 社區建檔、物件新增與批次匯入、刊登與銷售、物件狀態與欄位；⛔ 物件上的租約歸 D、抄表歸 E
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 社區列表與建立 {#C-community-list}
### 社區總表顯示什麼資訊？（物件總數、招租／買賣廣告數、空置數量、本月應收與已收） {#jgb/C/community-list-overview-stats}
- phrasings:
  - {text: "社區總表看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社區列表顯示哪些數字", source: "draft:outline-20260920", status: proposed}
  - {text: "空置數量怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "每個社區的招租買賣數量在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/_parts/CommunityItem.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區總表會列出每個社區的物件總數、招租中物件數量、買賣中物件數量，以及本月應總收與本月已總收金額。
空置數量的計算方式是物件總數量減去有執行中合約的物件總數量。
當社區已啟用差額發票時，該社區列會額外顯示「開設差額發票」標籤與底租金額。
### 如何新增社區？（訂閱方案有可建立社區數量上限） {#jgb/C/community-add-single-and-limit}
- phrasings:
  - {text: "怎麼新增社區", source: "draft:outline-20260920", status: proposed}
  - {text: "社區數量有上限嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "新增社區按鈕在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/list/Index.vue, code:src/type/commit.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在社區總表按下「新增社區」按鈕即可建立一筆新社區，建立後會直接進入社區編輯頁面。
訂閱方案對可建立的社區數量有上限，達到上限時無法繼續新增社區。
### 怎麼批次新增社區、或複製現有社區建立新社區？ {#jgb/C/community-batch-add-and-copy}
- phrasings:
  - {text: "批次新增社區怎麼做", source: "draft:outline-20260920", status: proposed}
  - {text: "社區可以用 Excel 匯入嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "複製現有社區", source: "draft:outline-20260920", status: proposed}
  - {text: "有沒有現成社區範本可以複製", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/components/Lightbox/CommunitiesBatchAdd.vue, code:src/pages/communities/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「新增社區」按鈕旁的選單中選擇「批次新增」，可以下載指定格式的 Excel 範本填寫後上傳建立多筆社區。
批次新增的上傳檔案大小上限為 10MB。
選單中的「複製現有社區」會先進入社區選擇畫面，挑選一個已存在的社區做為範本再建立新社區；此選項只在目前篩選結果的社區列表不是空的時才會出現。
### 社區總表怎麼搜尋與排序？（案名／地址關鍵字、縣市行政區、建物類型、捷運站） {#jgb/C/community-list-filter-sort}
- phrasings:
  - {text: "社區怎麼搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "社區列表篩選條件有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼依地區找社區", source: "draft:outline-20260920", status: proposed}
  - {text: "社區排序方式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/list/Index.vue, code:src/pages/communities/list/_parts/CommunitiesAdvanceSearchBlock.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區總表的關鍵字搜尋欄可以輸入案名或地址查詢。
進階搜尋提供國家、縣市、行政區、建物類型與捷運站等下拉篩選條件。
列表也可以切換排序方式，選定的排序會被記住供下次進入沿用。
### 社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原） {#jgb/C/community-delete-requires-empty}
- phrasings:
  - {text: "社區怎麼刪除", source: "draft:outline-20260920", status: proposed}
  - {text: "社區可以刪除嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "刪不掉社區怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "刪除社區的限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/_parts/CommunityItem.vue, code:src/components/Lightbox/CommunityDelete.vue, code:app/Http/Controllers/CommunityController.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區列表項目的設定選單有「刪除社區」選項（只有具備編輯物件權限的使用者看得到），但只有在該社區底下的物件總數為 0 時才能刪除成功。
若社區底下還有物件，點擊刪除會出現提示「無法刪除社區，需沒有任何物件才能刪除社區」。
確認刪除的視窗會提醒「社區刪除後，將無法復原」，需再次確認才會真的刪除。
### 社區總表可以匯出嗎？（需要匯出物件權限，會依目前篩選條件匯出） {#jgb/C/community-export-list}
- phrasings:
  - {text: "社區怎麼匯出", source: "draft:outline-20260920", status: proposed}
  - {text: "社區清單匯出功能", source: "draft:outline-20260920", status: proposed}
  - {text: "匯出社區要什麼權限", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
具備匯出物件權限的使用者，可以在社區總表點擊「匯出社區」，依目前的搜尋條件匯出整批社區資料，匯出工作會進入下載佇列。
沒有匯出物件權限時，「匯出社區」按鈕不會顯示；有匯出物件權限、但目前篩選結果為 0 筆時，按鈕會顯示但無法點擊。
### 社區總表每頁筆數可以調整嗎？（30／60／90項） {#jgb/C/community-list-pagination}
- phrasings:
  - {text: "社區總表每頁顯示幾筆", source: "draft:outline-20260920", status: proposed}
  - {text: "社區列表分頁筆數", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼調整每頁顯示社區數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區總表下方可以選擇每頁顯示30項、60項或90項。
### 誰看得到新增社區的入口？（總表右上角需要編輯物件權限；空狀態的批次新增／新增社區入口需要新增物件權限） {#jgb/C/community-list-add-permission}
- phrasings:
  - {text: "新增社區按鈕不見了", source: "draft:outline-20260920", status: proposed}
  - {text: "誰可以新增社區", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有編輯物件的權限看不到新增社區", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有具備編輯物件權限的使用者，才看得到社區總表右上角的「新增社區」按鈕與批次新增、複製現有社區的選單；沒有編輯物件的權限時，這些按鈕與選單都不會顯示。
當該分類目前沒有任何社區時，畫面會改顯示空狀態；此時「此分類尚未有社區，您可以選擇😎：」文字與底下的「批次新增」「新增社區」按鈕，只有在使用者具備新增物件權限時才會出現，沒有新增物件權限的使用者只會看到「此分類尚未有社區」的提示文字。
## 社區資料編輯（基本資料、照片與描述、介紹與交通） {#C-community-edit}
### 社區編輯有哪些分頁？（基本資料、介紹與交通、照片與描述） {#jgb/C/community-edit-tabs}
- phrasings:
  - {text: "社區編輯有哪些分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "社區資料要編輯哪些項目", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯社區從哪裡進去", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/communities.js]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區編輯頁在「社區資訊」群組下分成「基本資料」「介紹與交通」「照片與描述」三個分頁，都屬於同一個社區資料。
直接從社區總表點進「編輯社區」時，會先進入「基本資料」分頁。
### 社區基本資料要填什麼？（社區名稱、詳細地址與對外顯示地址、建築類型、總樓層、屋齡） {#jgb/C/community-edit-basic-fields}
- phrasings:
  - {text: "社區基本資料要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社區名稱字數限制", source: "draft:outline-20260920", status: proposed}
  - {text: "對外顯示地址跟詳細地址差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/Basic.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
基本資料分頁的「社區名稱」欄位用來告訴客戶這個社區叫什麼名字，輸入框提示名稱限制在 30 個字以內。
地址分成「詳細地址」與「對外顯示地址」兩組，對外顯示地址可以按「同詳細地址」直接帶入詳細地址的內容，且對外顯示地址會標記在 Google 地圖上。
其他欄位還包含建築類型、總樓層（限純數字）與屋齡（限純數字）；另外還有一個「社區細節」欄位區塊，只有團隊被歸類為特定合作團隊時才會顯示，一般團隊看不到。
### 社區照片與描述可以上傳幾張圖片？（限1張，JPG/PNG，檔案大小最大10MB） {#jgb/C/community-edit-gallery-photo-limit}
- phrasings:
  - {text: "社區照片上限幾張", source: "draft:outline-20260920", status: proposed}
  - {text: "社區封面圖怎麼傳", source: "draft:outline-20260920", status: proposed}
  - {text: "社區圖片格式限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/Gallery.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「照片與描述」分頁的社區相片，最多只能上傳1張，格式支援 JPG、PNG，檔案大小最大 10MB。
### 社區照片與描述什麼時候會跳出「已更新」提示？（存檔成功後才出現，不是上傳當下） {#jgb/C/community-edit-gallery-save-notice}
- phrasings:
  - {text: "社區照片上傳成功提示在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "社區資料存檔提示", source: "draft:outline-20260920", status: proposed}
  - {text: "上傳照片後畫面沒反應正常嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/Gallery.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「照片與描述」分頁按下儲存、社區資料更新成功後才會跳出提示：一般編輯流程一律顯示社區名稱加上「已更新」；只有在物件強制綁定導引流程中，社區是新建立的（非選擇既有社區）時，才會改顯示「創建成功」。
單純把照片上傳完成，不會立刻跳出這個提示，要等整個分頁儲存成功才會顯示。
### 社區介紹與交通怎麼填？（社區簡介、鄰近交通說明、可加多個鄰近捷運站） {#jgb/C/community-edit-intros-and-transit}
- phrasings:
  - {text: "社區介紹要寫什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼加捷運站", source: "draft:outline-20260920", status: proposed}
  - {text: "社區交通資訊在哪填", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/Intros.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「介紹與交通」分頁可以填寫社區簡介文字說明與鄰近交通描述，讓客戶更了解社區細節。
鄰近捷運站可以點選「新增鄰近捷運站」加入多筆，每筆需要選擇捷運線與停靠站。
### 社區基本資料哪個欄位是必填？（只有社區名稱是必填） {#jgb/C/community-edit-basic-required-field}
- phrasings:
  - {text: "社區哪些欄位一定要填", source: "draft:outline-20260920", status: proposed}
  - {text: "社區名稱一定要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "社區地址是必填嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/edit/Basic.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區基本資料分頁裡，標記為必填的欄位只有「社區名稱」一個，其餘欄位（地址、建築類型、總樓層、屋齡等）都不是必填。
## 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） {#C-community-estates}
### 社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額） {#jgb/C/community-estates-overview-card}
- phrasings:
  - {text: "社區物件頁上面的卡片是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社區概要顯示哪些數字", source: "draft:outline-20260920", status: proposed}
  - {text: "社區物件總覽在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/estates/_parts/CommunityOverview.vue, code:app/Services/CommunityService.php, code:src/pages/communities/estates/Index.vue, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區底下的物件清單頁最上方會顯示這個社區的概要卡片，包含招租廣告、買賣廣告、目前空置數量（皆以物件總數為分母）、建築類型與屋齡。
卡片上也會顯示這個社區「本月應收金額」與「本月已收金額」。
卡片上的數量與金額只計入目前登入者有權限看到的物件：團隊擁有者看全部，其他成員依「查看所有物件」或「查看所屬物件」權限，大房東則只計入他可存取的物件。
電腦版卡片右上角的選單有「前往社區廣告」（社區公開頁）；具備編輯物件權限的使用者（團隊擁有者也包含在內）還會看到「編輯」與「刪除社區」選項。
手機等窄螢幕（寬度 991 以下）沒有這個選單，改在卡片下方顯示「編輯社區」「預覽廣告頁」「刪除社區」，其中「編輯社區」「刪除社區」同樣只有具備編輯物件權限的使用者看得到。
### 社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變） {#jgb/C/community-estates-category-switch}
- phrasings:
  - {text: "社區物件怎麼切換招租買賣", source: "draft:outline-20260920", status: proposed}
  - {text: "總覽招租買賣分類在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "社區物件清單分類切換", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/utils/constants/estate.js, code:src/pages/communities/estates/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區底下的物件清單提供總覽、招租、買賣三種分類切換。
切到「招租」時清單欄位會顯示招租廣告與租金，切到「買賣」時則顯示買賣廣告與售價，欄位標題會依所選分類自動變化。
### 怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制） {#jgb/C/community-estates-add-batch-copy}
- phrasings:
  - {text: "社區物件怎麼新增", source: "draft:outline-20260920", status: proposed}
  - {text: "社區物件批次新增", source: "draft:outline-20260920", status: proposed}
  - {text: "複製現有物件", source: "draft:outline-20260920", status: proposed}
  - {text: "物件數量上限", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/estates/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
有新增物件權限的使用者，在社區物件清單「所有物件」分類下可以點「新增物件」直接建立、選「批次新增」上傳表格，或選「複製現有物件」以既有物件為範本。
訂閱方案對可建立的物件數量有上限，達到上限時新增物件會被擋下並提示已達上限。
當社區內只剩公共區域物件、沒有其他物件時，不會提供「複製現有物件」選項。
### 社區底下有差額發票、投報率頁籤嗎？（差額發票看該社區是否開通；投入成本與投報率由團隊的投報率功能開關一起控制，租客、大房東與沒有「查看所有帳單」權限的成員看不到） {#jgb/C/community-estates-extra-tabs}
- phrasings:
  - {text: "社區差額發票頁籤", source: "draft:outline-20260920", status: proposed}
  - {text: "社區投報率在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "社區物件頁籤有哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/utils/constants/community.js, code:src/pages/communities/estates/Index.vue, code:app/Http/Controllers/CommunityController.php, code:app/Http/Controllers/Api/CommunityRoiController.php, code:app/Services/InvoiceService.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「所有物件」頁籤永遠存在，「差額發票」頁籤只在該社區開通差額發票功能時才會加入。
「投入成本」與「投報率」兩個頁籤是由同一個開關控制的，團隊開通投報率功能時這兩個頁籤會一起出現，沒辦法只開通其中一個；但即使團隊已開通，租客身分、大房東，以及沒有「查看所有帳單」權限的成員也看不到這兩個頁籤。
沒有任何額外頁籤開通時，畫面不會顯示頁籤切換器，直接呈現物件清單。
### 社區物件清單每頁筆數可以調整嗎？（30／60／90項） {#jgb/C/community-estates-pagination}
- phrasings:
  - {text: "社區物件每頁顯示幾筆", source: "draft:outline-20260920", status: proposed}
  - {text: "物件清單分頁筆數", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼調整每頁項目數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/estates/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社區物件清單下方可以選擇每頁顯示30項、60項或90項，預設為30項。
## 社區公開頁（社區詳情、社區總表） {#C-community-public-page}
### 社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件） {#jgb/C/community-show-content}
- phrasings:
  - {text: "社區詳情頁有什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社區公開頁看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社區廣告頁內容", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/show/Index.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
社區公開頁（社區廣告）會顯示「社區基本資訊」（類型、總樓層數、屋齡）、「社區交通與環境設施」（鄰近捷運站、鄰近交通）以及「社區介紹」文字說明。
頁面下方的「社區所有刊登中物件」會分別列出招租中與買賣中的物件數量，各自可以點「更多」看更多物件。
頁尾會顯示本社區的 JGB 編號，並附上房屋現況與法定用途的提醒文字。
### 社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間） {#jgb/C/community-show-price-range}
- phrasings:
  - {text: "社區價格區間在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "社區租金區間", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/show/_parts/PageTop.vue, code:app/Community.php, code:app/Services/CommunityService.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
社區公開頁最上方會顯示該社區刊登中物件的「租賃金額區間」與「售價金額區間」（從最低到最高金額），有對應的刊登物件時才會顯示。
### 社區公開頁怎麼分享？（分享燈箱或手機分享選單、查看所有物件連結） {#jgb/C/community-show-share}
- phrasings:
  - {text: "社區頁面怎麼分享", source: "draft:outline-20260920", status: proposed}
  - {text: "社區查看所有物件連結", source: "draft:outline-20260920", status: proposed}
  - {text: "社區分享燈箱", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/show/_parts/PageTop.vue, code:src/pages/communities/show/_parts/AsideContact.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
頁面提供分享功能，點擊分享按鈕會開啟社區分享的燈箱；在支援系統分享的行動裝置上，則會直接叫出手機的分享選單。
側邊欄也提供「查看所有物件」連結，會前往這個團隊的招租店舖頁。
### 在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有具備編輯物件權限的使用者看得到這個選單） {#jgb/C/community-show-editor-nav}
- phrasings:
  - {text: "社區詳情頁怎麼編輯社區", source: "draft:outline-20260920", status: proposed}
  - {text: "社區公開頁回總表", source: "draft:outline-20260920", status: proposed}
  - {text: "社區詳情頁返回Dashboard", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/show/Index.vue, code:app/Services/CommunityService.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有具備編輯物件權限的使用者（團隊擁有者也包含在內），在社區廣告頁才會看到右上角的選單，選單有四個選項：「編輯」跳到社區編輯頁、「社區詳情」跳到該社區的管理端物件清單頁、「社區總表」回到社區列表、「返回 Dashboard」回到管理端首頁。
## 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） {#C-community-force-binding}
### 為什麼會出現「物件需綁定社區」的導引？（2022/05/12 社區功能上線，只有團隊擁有者能操作） {#jgb/C/forcebinding-why-and-who}
- phrasings:
  - {text: "為什麼要綁定社區", source: "draft:outline-20260920", status: proposed}
  - {text: "物件為什麼要綁社區", source: "draft:outline-20260920", status: proposed}
  - {text: "誰可以做物件綁定社區", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/forceBinding/Welcome.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
系統於 2022/05/12 新增「社區」功能後，要求既有物件必須全數綁定至社區才能使用系統，因此舊帳號登入時會被導向這個綁定導引畫面。
執行這個綁定動作需要是團隊擁有者身分，若不是團隊擁有者，畫面會顯示「權限不足」。
### 物件綁定社區的導引起始畫面顯示什麼？（已綁定與尚未綁定的物件數量、需同意服務條款） {#jgb/C/forcebinding-welcome-progress}
- phrasings:
  - {text: "綁定社區進度在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "還有幾個物件沒綁社區", source: "draft:outline-20260920", status: proposed}
  - {text: "綁定物件前要同意什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/forceBinding/Welcome.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
起始畫面會分別顯示目前「尚未綁定至社區」與「已成功綁定至社區」的物件數量。
點擊「繼續」即代表同意 JGB 的服務條款與隱私權聲明才能往下一步。
### 物件綁定社區導引有哪兩個步驟？（填寫社區資料、選擇欲綁定社區內的物件；未完成系統功能無法正常使用） {#jgb/C/forcebinding-two-steps}
- phrasings:
  - {text: "綁定社區流程有幾步", source: "draft:outline-20260920", status: proposed}
  - {text: "先建社區還是先綁物件", source: "draft:outline-20260920", status: proposed}
  - {text: "沒綁完社區會怎樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/forceBinding/edit/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
導引分兩步：第一步「填寫社區資料」，第二步「選擇欲綁定社區內的物件」。
在物件全數綁定完成之前，系統功能將無法正常使用。
### 怎麼挑選要綁定的物件？（可關鍵字搜尋、每頁30/60/90項，確認綁定後無法修改） {#jgb/C/forcebinding-select-estates-irreversible}
- phrasings:
  - {text: "怎麼選要綁定的物件", source: "draft:outline-20260920", status: proposed}
  - {text: "綁定物件可以改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "綁定物件怎麼搜尋", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/forceBinding/edit/Binding.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選擇物件的畫面提供關鍵字搜尋、物件名稱、細節、招租廣告與買賣廣告數量欄位，每頁可切換30、60、90項。
畫面上明確提示「確認綁定物件後，即不能修改」，確認綁定的視窗也會再次提醒「請確認欲綁定的物件，綁定後即不能修改」。
### 綁定完成後會看到什麼？（全部綁完顯示恭喜，還有剩則提示繼續綁定） {#jgb/C/forcebinding-completion-states}
- phrasings:
  - {text: "綁定完成畫面", source: "draft:outline-20260920", status: proposed}
  - {text: "還有物件沒綁完怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "綁定物件成功提示", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/communities/forceBinding/edit/Binding.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
當所有物件都綁定完成時，畫面會顯示「恭喜」加上「你已經成功綁定所有物件」，並提供前往社區總表的按鈕。
若還有物件尚未綁定完成，畫面則顯示「你完成最困難的部分」並提示「你已經完成新增社區的必需步驟，但還有些物件尚未綁定完成」，可以點擊繼續綁定物件。
## 物件列表與篩選 {#C-estate-list}
### 物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口） {#jgb/C/estate-list-add-must-pick-community}
- phrasings:
  - {text: "物件總表怎麼新增物件", source: "draft:outline-20260920", status: proposed}
  - {text: "新增物件要選社區嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件總表可以批次新增嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "複製現有物件在物件總表", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/_parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在物件總表點「新增物件」或「複製現有物件」，都會先導向社區選擇畫面，再回來建立或複製物件。
目前物件總表沒有「批次新增」入口可以使用，這個選項目前是隱藏、不會顯示出來的。
### 物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量） {#jgb/C/estate-list-counter-and-limit}
- phrasings:
  - {text: "物件總表顯示物件總數", source: "draft:outline-20260920", status: proposed}
  - {text: "還可以新增幾個物件", source: "draft:outline-20260920", status: proposed}
  - {text: "尚可新增物件數量在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/_parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有具備新增物件權限的使用者，才會在物件總表標題下方看到「目前物件總數」與「尚可新增」的數字，尚可新增的數量會依訂閱方案剩餘額度變動。
### 物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤） {#jgb/C/estate-list-filters}
- phrasings:
  - {text: "物件總表篩選條件有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼依經理人篩選物件", source: "draft:outline-20260920", status: proposed}
  - {text: "物件怎麼依社區篩選", source: "draft:outline-20260920", status: proposed}
  - {text: "租金範圍怎麼篩", source: "draft:outline-20260920", status: proposed}
  - {text: "格局怎麼篩選物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx, code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlockM.jsx, code:src/pages/estates/list/Index.vue, code:tailwind.config.js]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件總表的進階搜尋提供國家、縣市、行政區、經理人、大房東、社區、捷運站等下拉篩選。
也可以依格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金、面積(坪)與標籤等條件縮小搜尋結果；沒有依用途篩選的選項（用途篩選只在挑選物件用的物件挑選器裡才有）。
手機（寬度小於 576px）上，即時合約狀態與合約到期日直接排在搜尋列上方，其餘條件收在「更多」裡；其中租金範圍只有在幣別為 TWD 時才會出現。
寬度 992px 以上的螢幕，搜尋條件下方會顯示「篩選結果」，格式為目前顯示筆數／總筆數；較窄的螢幕（含手機）沒有這一行。
### 物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱） {#jgb/C/estate-list-keyword-search}
- phrasings:
  - {text: "物件怎麼用租客手機搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "物件關鍵字搜尋範圍", source: "draft:outline-20260920", status: proposed}
  - {text: "用物件ID找物件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件總表的關鍵字搜尋可以切換搜尋範圍為案名、地址、租客、ID、手機或信箱。
### 物件總表可以批次操作嗎？（個人房東、大房東、租客身分不能；法人房東與社宅團隊成員可：匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示） {#jgb/C/estate-list-batch-actions}
- phrasings:
  - {text: "物件怎麼批次下架", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼一次刊登多筆物件", source: "draft:outline-20260920", status: proposed}
  - {text: "物件總表可以匯出嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useEstateTypes.js, code:src/pages/estates/list/_parts/ListTable.vue, code:src/components/Lightbox/EstatePublishResult.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
個人房東、大房東與租客身分的物件總表沒有勾選框，不能批次操作；法人房東與社宅團隊的成員也要至少有其中一項批次動作的權限，才會有勾選框。
勾選多筆物件後，依權限可以看到「匯出物件」「新增批次帳單」「批次刊登招租廣告」「批次取消刊登招租廣告」「刪除」等批次動作；其中「刪除」只有在勾選的物件全部都是「無合約」、且不是跨頁全選整份清單時才會出現。
批次刊登招租廣告時，完全沒有失敗物件會直接跳出已刊登件數的成功提示；只要有任何一件失敗，改成跳出結果視窗，顯示已刊登的件數，以及因資訊不齊全而沒有刊登的件數（全部失敗時標題是「招租廣告刊登失敗」）。
批次取消刊登招租廣告時，只有在完全沒有失敗物件時才會跳出下架成功件數的提示；若有物件失敗，畫面不會出現任何視窗或錯誤訊息。
### 物件狀態會影響哪些功能？（招租廣告狀態未刊登／刊登中，與合約狀態洽談中／租約中，是各自獨立的；刪除物件要求未刊登、沒有合約、沒有 IoT 綁定） {#jgb/C/estate-status-affects-actions}
- phrasings:
  - {text: "物件狀態影響什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "洽談中是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "物件狀態怎麼判斷", source: "draft:outline-20260920", status: proposed}
  - {text: "刊登中的物件可以刪除嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/search/modules/contractStatus.js, code:app/Estate.php, code:app/Http/Controllers/EstateController.php, code:src/use/search/modules/is_open.js, code:app/Contract.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件總表有兩組各自獨立的狀態：招租廣告狀態（未刊登／刊登中）與合約狀態（洽談中／租約中，沒有合約的物件另外標示為無合約），兩者不是同一組四選一的分類。
「洽談中」代表這個物件已經有合約，但還沒有任何一份完成簽署；一旦雙方都簽署完成就會變成「租約中」。
已歸入歷史的合約不列入判斷物件合約狀態的依據。
每個物件的操作選單會依權限，以及物件目前是否已刊登招租廣告，顯示「刊登招租廣告」或「取消刊登招租廣告」。
刪除單一物件時，物件必須是未刊登（不能是刊登中）、沒有尚未歸入歷史的合約，也沒有綁定 IoT 裝置，否則會被擋下並顯示原因。
### 物件總表每頁筆數可以調整嗎？（30／60／90項） {#jgb/C/estate-list-pagination}
- phrasings:
  - {text: "物件總表每頁顯示幾筆", source: "draft:outline-20260920", status: proposed}
  - {text: "物件列表分頁筆數", source: "draft:outline-20260920", status: proposed}
  - {text: "調整每頁顯示物件數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件總表下方可以選擇每頁顯示30項、60項或90項。
### 物件總表篩選還有哪些條件？（空間類型多選、「更多」：VR、有電梯、可開伙、可養寵物） {#jgb/C/estate-list-filters-space-type-and-others}
- phrasings:
  - {text: "物件怎麼篩VR", source: "draft:outline-20260920", status: proposed}
  - {text: "物件篩選可養寵物", source: "draft:outline-20260920", status: proposed}
  - {text: "物件篩選有電梯", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx, code:src/components/AdvGroupSelect.jsx, code:src/components/AdvGroupSelectMobile.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階搜尋提供「空間類型」多選篩選（例如整戶、套房、雅房等）。
另外還有一個「更多」按鈕，可以複選是否有VR、有電梯、可開伙、可養寵物。
### 物件總表怎麼切換總覽／招租／買賣？（三種分類切換） {#jgb/C/estate-list-category-switch}
- phrasings:
  - {text: "物件總表怎麼切換招租買賣", source: "draft:outline-20260920", status: proposed}
  - {text: "物件總覽招租買賣分類", source: "draft:outline-20260920", status: proposed}
  - {text: "物件列表分類切換", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/estates.js, code:src/utils/constants/estate.js, code:src/pages/estates/list/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件總表提供「總覽」「招租」「買賣」三種分類切換，切換後畫面上的物件清單會依分類重新載入。
### 物件總表怎麼排序？（排序選項由系統提供，寬度 576px 以上切換的排序會被記住） {#jgb/C/estate-list-sort-remembers-last}
- phrasings:
  - {text: "物件總表怎麼排序", source: "draft:outline-20260920", status: proposed}
  - {text: "上次選的排序方式還在嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件排序選項有哪些", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/list/Index.vue, code:src/components/ListSearchBar.vue, code:src/utils/constants/common.ts, code:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件總表的排序選項由系統提供，使用者可以在列表上方切換排序方式。
在寬度 576px 以上的畫面切換排序後，這個排序方式會記在瀏覽器裡。
下次進入物件總表、且網址沒有另外帶排序參數時，會自動帶入上次記住的排序方式，不論用多寬的畫面進入。
手機等寬度小於 576px 的畫面切換排序，不會被記成物件總表的排序，所以下次進入不會帶入手機上選的排序。
## 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） {#C-estate-edit}
### 物件基本資料的空間類型、用途、格局要怎麼填？ {#jgb/C/estate-edit-basic-space-type}
- phrasings:
  - {text: "物件用途怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "物件格局怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "虛擬辦公室是什麼意思", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料的「空間類型」是一個區塊標題：一般物件在底下先選「用途」（例如住宅、商用、土地、工業/廠房/倉庫、酒店，可選的用途會依團隊設定而不同），用途是必填；再依用途選擇對應的「格局」，例如整戶、套房、雅房，或辦公類型的獨立辦公室、固定辦公桌、共享辦公桌、虛擬辦公室、會員等，格局同樣是必填欄位。
社宅物件的基本資料不會顯示用途欄位。
「虛擬辦公室」格局說明為出租業者提供「商業地址」給企業「借址登記」使用、不做實際上班用途的辦公室；「會員」則是共享辦公室業者提供的會員方案。
### 物件的詳細地址與對外顯示地址有什麼差別？ {#jgb/C/estate-edit-basic-address}
- phrasings:
  - {text: "物件地址怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "對外顯示地址是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告地址跟實際地址不同", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料分別要填「詳細地址」與「對外顯示地址」，對外顯示地址可以點「同詳細地址」直接帶入詳細地址內容。
### 物件的樓層與房號要怎麼填？（頂加輸入+1、地下室輸入-1） {#jgb/C/estate-edit-basic-floor-room-number}
- phrasings:
  - {text: "頂加怎麼填樓層", source: "draft:outline-20260920", status: proposed}
  - {text: "地下室樓層怎麼寫", source: "draft:outline-20260920", status: proposed}
  - {text: "物件之幾房之幾床是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料要填所在樓層、總樓層、之幾房、之幾床（車位用途物件不需填之幾房之幾床）。
所在樓層輸入 +1 代表頂加，輸入 -1 代表地下室。
### 物件廣告頁可以隱藏群組/大樓名稱嗎？ {#jgb/C/estate-edit-basic-community-name-hide}
- phrasings:
  - {text: "物件可以不顯示社區名稱嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "廣告頁隱藏大樓名稱", source: "draft:outline-20260920", status: proposed}
  - {text: "群組名稱怎麼隱藏", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料的「群組/大樓名稱」欄位會帶入所屬社區名稱（唯讀），旁邊有「在物件廣告頁隱藏群組名稱」的勾選框，勾選後廣告頁就不會顯示社區/大樓名稱。
### 社宅物件建物謄本要填什麼？（申請謄本日期、段小段、謄本面積公式，不會顯示在廣告頁） {#jgb/C/estate-edit-building-transcript-social}
- phrasings:
  - {text: "社宅建物謄本要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅謄本面積怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅建物謄本會公開嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/building_transcript/Index.vue, code:src/routes/estates.js]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅物件的建物謄本分頁要求填寫申請謄本日期、地號（段小段中文、地號）、建號（段小段中文、建號）、建築完成日期與謄本面積，這些資料不會顯示在物件廣告頁上，主要用來方便未來完備合約資料。
謄本面積要以建物謄本所載面積為準，公式為主建物面積加附屬建物面積加持分公設面積減車位面積。
### 一般物件建物謄本可以填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物，皆非必填） {#jgb/C/estate-edit-building-transcript-general}
- phrasings:
  - {text: "一般物件建物謄本要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "土地標的清冊怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "稅籍編號在哪填", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/buildingTranscriptGeneral/Index.vue, code:src/pages/contracts/edit/buildingTranscript/General.vue, code:src/routes/estates.js]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般物件（即一般住宅物件，非社會住宅物件）的建物謄本分頁可以填寫「土地標的清冊」（段、小段、地號、租賃面積、都市土地使用分區，最多3筆）與坐落基地、稅籍編號；這些欄位都不是必填，這個分頁也不列入完成勾選。
同一分頁也可以填「專有部分」「主建物」「附屬建物」的相關資料。
### 物件附設傢俱怎麼設定？（依用途與格局分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁） {#jgb/C/estate-edit-facilities}
- phrasings:
  - {text: "附設傢俱怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "家電傢俱怎麼加", source: "draft:outline-20260920", status: proposed}
  - {text: "物件設備要怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/facilities/_parts/General.vue, code:src/pages/estates/edit/facilities/_parts/SocialHousing.vue, code:src/pages/estates/edit/facilities/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般物件的附設傢俱分頁會依用途、空間類型與格局分區顯示；社宅物件則使用另一套附設傢俱設定畫面。
住宅與旅館類物件先在「格局(套房)」這類標題的區塊選好各類空間的數量，頁面就會依數量產生各個空間區塊；每個空間區塊都能設定「家電」「傢俱」的數量，也能「自訂」項目名稱與數量，自訂最多 10 項。
住宅套房／雅房另有「戶內共用空間」區塊。
商用辦公類物件的家電、傢俱在「辦公空間」區塊設定，店面物件在「店面空間」區塊設定。
「商用」與「有建物」這兩個標題底下只有必填的「座位數」，不是設定家電、傢俱的地方。
車位用途與空地物件不需要設定格局，畫面會顯示「車位用途物件，不需要設定「格局」內容」或「空地用途物件，不需要設定「格局」內容」。
所有一般物件都有「大樓/社區空間」區塊，可以勾選「公設」與「安全設備」項目。
家電、傢俱與自訂項目的數量若設為 0，就不會顯示在物件廣告頁上。
需要先設定好用途、型態或格局，才能開始添加傢俱項目。
### 物件標題與照片有什麼限制？（標題最長60字、照片最多15張15MB、平面圖最多5張含PDF） {#jgb/C/estate-edit-gallery-title-photos}
- phrasings:
  - {text: "物件標題字數限制", source: "draft:outline-20260920", status: proposed}
  - {text: "物件照片可以傳幾張", source: "draft:outline-20260920", status: proposed}
  - {text: "物件平面圖怎麼上傳", source: "draft:outline-20260920", status: proposed}
  - {text: "第一張照片是封面嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/gallery/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「物件標題」與可另外啟用的「物件公開標題」都限制最長60字。
物件照片最多可上傳15張、每張檔案大小上限15MB，格式支援JPG、PNG，第一張照片會被設為封面照片，每張都可以加上文字描述。
物件平面圖最多可上傳5張、每張檔案大小上限15MB，格式支援JPG、PNG、PDF，上傳後會出現在廣告中。
### 物件介紹要填什麼？（房源簡介、鄰近交通，可加多筆鄰近捷運站） {#jgb/C/estate-edit-intro-transit}
- phrasings:
  - {text: "物件介紹要寫什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "房源簡介怎麼寫", source: "draft:outline-20260920", status: proposed}
  - {text: "物件怎麼加捷運站", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/intro/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件介紹分頁可以填寫房源簡介與鄰近交通說明，讓客戶更了解物件細節。
鄰近捷運站可以點「新增鄰近捷運站」加入多筆，每筆需選擇捷運線與停靠站。
### 物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告） {#jgb/C/estate-edit-vr-720}
- phrasings:
  - {text: "720VR怎麼拍", source: "draft:outline-20260920", status: proposed}
  - {text: "VR全景照要用什麼app", source: "draft:outline-20260920", status: proposed}
  - {text: "VR全景照可以用電腦編輯嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/vr/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
拍攝720 VR全景照之前，需要先在手機安裝「VR Maker」App，接著在物件的720 VR分頁掃描 QR Code 進行拍攝。
拍攝完成後若要編輯全景照細節，目前不支援用手機編輯，需要使用電腦（PC）開啟。
分頁下方有「啟用設定」，可以決定是否在招租廣告、買賣廣告中使用這組720 VR全景照。
### 物件可以換綁到別的社區嗎？（畫面上目前沒有這個操作入口） {#jgb/C/estate-edit-cannot-change-community}
- phrasings:
  - {text: "物件換社區", source: "draft:outline-20260920", status: proposed}
  - {text: "物件重新綁定社區", source: "draft:outline-20260920", status: proposed}
  - {text: "物件搬到別的社區", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料的「群組/大樓名稱」欄位只是唯讀顯示目前所屬社區，畫面上目前找不到任何按鈕或連結可以把已建立的物件改綁到另一個社區。
### 物件基本資料可以填朝向嗎？ {#jgb/C/estate-edit-basic-orientation}
- phrasings:
  - {text: "物件朝向怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "物件座向欄位", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/basic/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件基本資料分頁有「朝向」欄位可以填寫。
### 物件編輯有哪些分頁？（「物件資訊」與「廣告資訊」兩個群組；社宅與一般物件的建物謄本分頁互斥） {#jgb/C/estate-edit-tabs-overview}
- phrasings:
  - {text: "物件編輯有哪些分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "物件資訊跟廣告資訊差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅物件編輯分頁跟一般物件不一樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/estates.js]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件編輯頁分成「物件資訊」與「廣告資訊」兩個群組：「物件資訊」群組包含基本資料、標題與照片、附設傢俱、建物謄本、核實訊息、720 VR、物件介紹；「廣告資訊」群組底下再分「招租」與「買賣」兩個子群組，各自有招租詳情／刊登主資訊或買賣詳情／刊登主資訊。
建物謄本分頁依用途互斥：一般物件顯示一般物件的建物謄本內容，社宅物件顯示社宅物件的建物謄本內容，兩者不會同時出現；核實訊息分頁只有一般物件才會顯示。
## 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） {#C-rent-listing}
### 招租押金有法定上限嗎？（一般租賃契約押金最高不得超過兩個月租金） {#jgb/C/estate-rent-detail-deposit-cap}
- phrasings:
  - {text: "押金上限幾個月", source: "draft:outline-20260920", status: proposed}
  - {text: "押金可以收多少", source: "draft:outline-20260920", status: proposed}
  - {text: "押金計算方式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_detail/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
招租詳情的押金可以選擇「每月租金」的倍數或「固定金額」做為計算基準。
系統提示：根據中華民國內政部（租賃住宅市場發展及管理條例）規定，一般租賃契約押金額度最高不得超過兩個月租金。
### 招租詳情的最短租期、最快入住日、最快點交日怎麼填？ {#jgb/C/estate-rent-detail-move-in-lease-terms}
- phrasings:
  - {text: "最短租期選項有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "最快入住日怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "最快點交日設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_detail/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
最短租期可以選擇1個月、3個月、6個月、1年、2年，或選「其他」自訂數字＋單位（單位只有「年」「月」兩種可選，沒有「天」）。
最快入住日可以選「簽約後隨時入住」、「指定日期」或「其他」，最快點交日則可選「簽約後點交」、「指定日期」或「其他」。
### 招租條件要求可以設定什麼？（身份限制複選、養寵物可否、開伙可否、生活公約） {#jgb/C/estate-rent-detail-tenant-conditions}
- phrasings:
  - {text: "招租可以限制什麼身份", source: "draft:outline-20260920", status: proposed}
  - {text: "可以養寵物嗎怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "招租能不能開伙", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_detail/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
招租詳情的「條件要求」可以複選身份限制，選項包含學生、上班族、家庭、男性、女性。
也可以個別設定「養寵物」與「開伙」是否可以，並在「補充」欄位填寫生活公約等額外說明。
### 刊登主資訊的團隊資訊要在哪裡修改？（法人／社宅房東顯示公司資訊、到團隊資訊修改；個人房東顯示經理人資訊、到帳號資訊修改） {#jgb/C/estate-rent-contact-agency-info}
- phrasings:
  - {text: "經紀人證號在哪改", source: "draft:outline-20260920", status: proposed}
  - {text: "登記證號怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "刊登主資訊看不到經紀人資料", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_contact/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
當登入身分是法人房東或社宅房東時，「刊登主資訊」會顯示團隊的公司名稱、公司電話、公司Email等公司資訊，並提示需要修改要前往「團隊資訊」頁面。
當登入身分是個人房東時（非法人、非社宅），「刊登主資訊」顯示的是經理人的姓名、電話、Email，並提示需要修改要前往「帳號資訊」頁面，不是團隊資訊。
### 招租廣告可以隱藏經理人／房東的名稱、電話、Email嗎？（勾選框在「經理人資訊」或「刊登主資訊」的經理人卡片上，每種身分只有一組） {#jgb/C/estate-rent-contact-manager-and-hide}
- phrasings:
  - {text: "招租廣告可以不顯示電話嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼隱藏經理人名稱", source: "draft:outline-20260920", status: proposed}
  - {text: "廣告上隱藏Email", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_contact/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「經理人」與「廣告顯示經理人」兩個必填選擇欄位，只出現在法人房東與社宅房東的「經理人資訊」區塊，不是「刊登主資訊」區塊；個人房東畫面上沒有這兩個選擇欄位。
法人／社宅房東的「經理人資訊」區塊裡，廣告顯示經理人的卡片上有「在廣告上隱藏名稱」「在廣告上隱藏聯絡電話」「在廣告上隱藏Email」三個勾選框；個人房東畫面上，這三個勾選框則出現在「刊登主資訊」的經理人卡片上——兩種身分都只有這一組三個勾選框，不會重複出現。
填完刊登主資訊後，下一步會進入「預覽招租廣告」。
### 招租的核實訊息是什麼？（依租賃住宅市場發展條例核實產權登記與違建面積） {#jgb/C/estate-rent-verify-legal}
- phrasings:
  - {text: "核實訊息要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "產權登記已辦理未辦理是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "違建面積要填嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_verify/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
核實訊息要求勾選「產權登記」是「已辦理」（租賃標的在地政機關有產權登記）還是「未辦理」（租賃標的在地政機關無產權登記）。
內政部依照《住宅租賃市場發展條例》要求廣告內容應與事實相符，因此還要填寫租賃標的法定用途，以及未登記之改建、增建、加建、違建部分（分壹樓、所在樓層、頂樓、其他處所各自的面積）。
### 為什麼物件刊登不出去？（需要刊登物件或新增物件的權限；必填欄位沒填完會退回編輯頁） {#jgb/C/estate-rent-open-permission-and-validation}
- phrasings:
  - {text: "物件刊登不出去", source: "draft:outline-20260920", status: proposed}
  - {text: "刊登物件失敗原因", source: "draft:outline-20260920", status: proposed}
  - {text: "刊登物件需要什麼權限", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/EstateController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
執行「刊登物件」的使用者，必須對這個物件有刊登物件或新增物件其中一種權限，否則系統會擋下並提示「您無法刊登此物件」。
如果物件還有必填欄位沒有填完整，系統會擋下這次刊登，自動導回物件編輯頁，並且把左側選單直接跳到缺欄位的那個分頁，提示需要補齊的錯誤訊息。
### 招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金；特定合作團隊另有營業稅：應稅／零稅率／免稅） {#jgb/C/estate-rent-detail-price-and-tax}
- phrasings:
  - {text: "招租租金要填幣別嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "營業稅怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "招租面積怎麼填", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/edit/rent_detail/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
招租詳情要填「面積」、「幣別」與「每月租金」，這三個都是必填欄位；社宅物件的面積可以按「同建物謄本面積」直接帶入。
營業稅欄位只有特定合作團隊才會顯示，可以選擇「應稅」「零稅率」或「免稅」三種。
## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） {#C-estate-dashboard}
### 物件儀表板進去預設是哪個分頁？（一般預設招租表現，大房東直接進合約歷程；大房東看不到「限管理者查看」分頁群組） {#jgb/C/estate-dashboard-entry-and-groups}
- phrasings:
  - {text: "物件儀表板預設看哪頁", source: "draft:outline-20260920", status: proposed}
  - {text: "大房東能看物件儀表板哪些分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "物件Dashboard入口", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/estates.js, code:src/pages/estates/dashboard/_parts/TabNav.vue, code:app/Http/Controllers/EstateController.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般使用者進入物件儀表板預設會導向「招租表現」分頁；大房東從物件總表進入時，則會直接導到「合約歷程」。
分頁分成兩組：「限管理者查看」（招租表現、銷售表現）與「與大房東共享」（合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本；每月報表、每月對帳單只在團隊被歸類為特定合作團隊時才會加入這一組）。
當使用者身分是大房東時，畫面不會顯示「限管理者查看」這組分頁，只能看到「與大房東共享」的分頁內容。
社宅房東看不到「合約附件」這個分頁，其餘身分都看得到。
### 招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要） {#jgb/C/estate-dashboard-rent-performance}
- phrasings:
  - {text: "招租表現看什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "物件空置天數在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "廣告瀏覽次數在哪查", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/rent/Index.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
招租表現分頁會顯示物件的空置天數圖表（出租天數與空置天數）、廣告瀏覽次數與平均頁面瀏覽次數。
同一頁還會摘要顯示帳務表現（總收入、總支出、總結餘）、合約歷程摘要（只會顯示執行中與歷史合約）與修繕紀錄摘要，都可以點「更多」看完整內容。
### 物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期） {#jgb/C/estate-dashboard-contracts-history}
- phrasings:
  - {text: "合約歷程有哪些欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "物件歷史合約在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "合約歷程每頁筆數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/contracts/Index.vue, code:app/Role.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般房東登入時，合約歷程列表欄位是狀態、簽約類型、物件、承租人、租期、是否通知；社宅房東登入時，欄位改成只有合約名稱、承租人、租期三欄。
列表每頁可切換顯示30、60或90項。
### 物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表） {#jgb/C/estate-dashboard-bills-tabs}
- phrasings:
  - {text: "帳務收支子頁籤", source: "draft:outline-20260920", status: proposed}
  - {text: "物件統計報表在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "物件總收支怎麼看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/estates.js]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件儀表板的「帳務收支」分頁下方分成「總收支」與「統計報表」兩個子頁籤。
### 物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態） {#jgb/C/estate-dashboard-repair-status-flow}
- phrasings:
  - {text: "修繕紀錄狀態有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "修繕紀錄欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "物件修繕在哪看結算金額", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/repair/Index.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
修繕紀錄可依「申請修繕」「安排修繕」「完成修繕」「結單」四種狀態篩選。
列表欄位包含報修日期、最後更新、分類＆項目、物件地址、結算金額、房東/管理者、租客。
### 「附件清單」跟「合約附件」差在哪？（附件清單可上傳 JPG／PNG／PDF、每個物件最多 5 個檔案、單檔 10MB，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是固定的附件項目清單，可上傳圖片補充以避免日後爭議） {#jgb/C/estate-dashboard-attachments-vs-contract-attachments}
- phrasings:
  - {text: "合約附件要傳什麼文件", source: "draft:outline-20260920", status: proposed}
  - {text: "附件清單空間不夠怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "物件附件跟合約附件差別", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/attachments/Index.vue, code:src/pages/estates/dashboard/contractAttachments/index.vue, code:app/Http/Controllers/EstateController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「附件清單」可以上傳 JPG、PNG、PDF 檔案，每個物件最多存放 5 個檔案，每個檔案不可超過 10MB；畫面上方顯示「儲存空間」的已存檔案數與可存檔案數。
檔案數量用完後會跳出「儲存空間已滿」的提示並顯示剩餘可存的檔案數，需要先刪除不要的檔案，才能再上傳新檔案。
下載檔案不限身分都能做，但只有代理人且擁有新增物件權限的使用者才看得到「刪除檔案」的操作。
上傳附件到「附件清單」，具備編輯物件權限、是團隊擁有者，或是代理人且擁有新增物件權限，符合其中一種身分即可。
「合約附件」是固定的附件項目清單：出租方身份證明文件影本（正反面各一份，若為法人（公司）請上傳公司設立登記表）、授權代理人簽約同意書、建物所有權/有權出租之證明文件、使用執照影本、出租方同意轉租確認書、房屋位置格局示意圖、社區管理規約與住戶生活規約，以及其他（附註條款、稅籍證明等）。
「合約附件」頁面的說明寫明：如有以下附件，可上傳圖片做補充，以避免日後爭議；圖片僅支援 JPG、PNG 檔，檔案大小最大 10MB，每個項目限制的上傳檔案數量不同。
只有非大房東、且具備新增物件或編輯物件權限的使用者，才看得到合約附件的上傳與刪除操作。
### 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入或支出與金額，記事本沒有金額欄位；兩者都能附檔） {#jgb/C/estate-dashboard-runnings-vs-memos}
- phrasings:
  - {text: "流水帳怎麼記", source: "draft:outline-20260920", status: proposed}
  - {text: "物件記事本可以記什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "流水帳跟記事本差別", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/runnings/Index.vue, code:src/pages/estates/dashboard/memos/Index.vue, code:src/pages/estates/dashboard/runnings/_parts/LedgerContainer.vue, code:src/pages/estates/dashboard/memos/_parts/MemoContainer.vue, code:app/Http/Controllers/EstateController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「房東流水帳」新增一筆時，要填時間、費用類別（收入或支出）、幣別與金額；說明與對象可以留空。
「房東流水帳」也可以附加最多 3 個附件，每個檔案不超過 10MB，可以是圖片或 PDF。
沒有該物件編輯權限的使用者新增流水帳時會被擋下，並顯示「權限不足」。
「物件記事本」新增一筆時，只要填時間；說明與對象可以留空，同樣可以附加最多 3 個附件（每個不超過 10MB），沒有收入支出的金額欄位。
### 每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔） {#jgb/C/estate-dashboard-monthly-report-upload}
- phrasings:
  - {text: "每月報表怎麼上傳", source: "draft:outline-20260920", status: proposed}
  - {text: "每月對帳單格式限制", source: "draft:outline-20260920", status: proposed}
  - {text: "同一個月上傳兩次報表會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼批次上傳報表", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/_parts/MonthlyUpload.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
上傳每月報表或每月對帳單僅能上傳 PDF 檔案，檔案大小限制10MB，需要選擇年份、月份與指定物件（可一次指定多個物件批次上傳）。
若該月份已經有上傳過的檔案，重新上傳會直接覆蓋舊檔案。
每月報表／每月對帳單這兩個分頁只在團隊被歸類為特定合作團隊時才會出現在「與大房東共享」分頁群組裡，上傳完成後其他團隊成員與大房東就能在這裡下載。
### 物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限） {#jgb/C/estate-dashboard-top-cards}
- phrasings:
  - {text: "物件儀表板上面卡片是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "儀表板編輯捷徑不見了", source: "draft:outline-20260920", status: proposed}
  - {text: "儀表板可以直接編輯招租廣告嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/dashboard/_parts/TabNav.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件儀表板最上方固定顯示三張卡片：物件基本資訊（縮圖、名稱、地址）、招租廣告（狀態、預覽連結）、買賣廣告（狀態、預覽連結）。
招租廣告卡與買賣廣告卡右上角各自的編輯捷徑（鉛筆圖示），只有當登入身分是代理人，且擁有新增物件的權限時才會顯示。
## 單一物件廣告頁（招租） {#C-estate-public-page}
### 物件還沒刊登（未開放）時，廣告頁會怎麼顯示？（屋主看到的是預覽頁提示；其他人造訪會得到404） {#jgb/C/estate-house-preview-unpublished}
- phrasings:
  - {text: "物件沒刊登廣告頁還看得到嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告預覽頁", source: "draft:outline-20260920", status: proposed}
  - {text: "還沒刊登的物件連結有效嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php, code:app/Http/Controllers/EstateController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
當物件尚未刊登（未開放）時，物件的擁有者若打開廣告頁連結，畫面上方會顯示提示：「這是您的物件廣告預覽頁，此物件尚未完成刊登」
當物件未刊登（未開放）、且目前造訪者沒有查看該物件的權限（包含未登入的訪客與搜尋引擎爬蟲）時，系統會回傳 404，讓 Google 等搜尋引擎重新爬取後把頁面從索引中移除，避免物件聯絡資訊繼續留在搜尋結果裡。
### 簽約邀請連結會失效嗎？（連結會顯示倒數，過期後失效） {#jgb/C/estate-house-invite-countdown}
- phrasings:
  - {text: "簽約邀請連結會過期嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "合約邀請連結有時效嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "邀請連結多久失效", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客透過邀請連結打開物件廣告頁時，頁面上方會顯示「以下是來自［房東］的簽約邀請，本連結會於［剩餘時間］後失效，請把握時間完成簽約」的提示。
### 物件廣告頁顯示哪些內容？（照片／VR全景切換、設備與設施、交通與環境設施、溫馨提醒） {#jgb/C/estate-house-content-blocks}
- phrasings:
  - {text: "物件廣告頁有哪些內容", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁看不看得到VR", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁會顯示鄰近捷運站嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
如果物件有設定720 VR全景照，廣告頁的相簿區可以在「照片」與「VR全景」之間切換。
廣告頁的「設備與設施」標題本身一定會顯示（不管物件實際登記的設備數量是多少），但底下實際列出的設備／傢俱項目只在該分區加總數量大於0或有自訂項目時才會顯示。
廣告頁也會顯示「交通與環境設施」（地址、鄰近捷運站等）以及「溫馨提醒」區塊，內含本物件的 JGB 編號與房屋現況、法定用途的提醒文字。
### 物件廣告頁「聯絡房東」區塊顯示什麼？（房東電話／Email依隱藏設定決定是否顯示；公司廣告電話／Email不受隱藏設定影響） {#jgb/C/estate-house-contact-landlord}
- phrasings:
  - {text: "物件廣告頁聯絡房東怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "隱藏電話設定有效嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "廣告頁可以加房東Line嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件廣告頁的「聯絡房東」區塊，只有在物件沒有設定隱藏電話、隱藏Email時，才會顯示房東本人（或主要經理人）的電話與Email。
如果房東是法人（公司），區塊改顯示公司的廣告電話與廣告Email，這兩個欄位不受「隱藏電話」「隱藏Email」設定影響，只要公司有填就一定會顯示。
Line 聯絡方式（含一鍵複製 Line ID）只有在房東有填寫 Line 時才會顯示；WhatsApp 聯絡方式同樣只有在房東有填寫時才會顯示。
Facebook 也只有在房東有填寫連結時才會顯示「立即聯繫」按鈕，沒有填寫時這三種聯絡方式都不會出現。
### 物件廣告頁的網址會自動轉換嗎？（刊登中時，內部編號網址會自動轉址到 JGB 編號公開網址） {#jgb/C/estate-house-vs-show-url}
- phrasings:
  - {text: "物件廣告頁網址是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "物件連結會自動跳轉嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁網址為什麼變了", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/EstateController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件如果目前是刊登中（公開狀態），透過內部編號網址造訪、且網址沒有帶合約或邀請參數時，系統會自動轉址到 JGB 編號的公開廣告網址。
如果網址帶的合約是續約合約，系統會直接導向該合約的合約檢視頁，不會顯示物件廣告頁。
### 物件廣告頁有費用明細表嗎？（車位物件不顯示，其餘物件顯示生活費用表） {#jgb/C/estate-house-fees-table}
- phrasings:
  - {text: "物件廣告頁費用怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁有清潔費水電費嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "車位物件有費用表嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件廣告頁在物件不是車位用途時，會顯示一個生活費用表，列出各項費用與金額；車位用途的物件不會顯示這個費用表。
### 物件廣告頁有預約入住的按鈕嗎？（一般訪客看到「立即預約入住」，受邀簽約者看到「查看合約」） {#jgb/C/estate-house-appointment-cta}
- phrasings:
  - {text: "物件廣告頁怎麼預約看房", source: "draft:outline-20260920", status: proposed}
  - {text: "立即預約入住按鈕在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "受邀簽約的人看到什麼按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/estate/show.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件廣告頁的桌機版與手機版下方都固定顯示一顆按鈕：一般訪客看到的是「立即預約入住」，點擊會開啟預約入住的燈箱。
如果目前造訪者是被邀請簽約的對象，同一個位置的按鈕會改成「查看合約」，點擊直接前往該合約的簽署頁面，不會顯示預約入住的燈箱。
### 物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖） {#jgb/C/estate-house-info-card}
- phrasings:
  - {text: "物件廣告頁資料卡片有什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁看不看得到含哪些費用", source: "draft:outline-20260920", status: proposed}
  - {text: "物件廣告頁格局在哪看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/estates/show/_parts/EstateBasicInfo.vue, code:resources/views/estate/show.blade.php, code:app/Estate.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
物件廣告頁的資料卡片一定會顯示地址；社區名稱有值時才會額外顯示社區名稱。
租金金額有值時，卡片才會顯示「[金額] 元/月」；若該物件有設定「租金已包含」的費用項目，還會在下方加註「(含〈項目〉)」的說明。
用途不是商用時（住宅或車位），建築類型欄位在住宅用途顯示「建築類型與樓層」，在車位用途則退化為只顯示「建築類型」；格局欄位在住宅用途顯示房型格局，在車位用途則固定顯示「車位」二字。
用途是商用時，卡片改顯示「空間類型」與「座位數」。
不論哪種用途，卡片最下方都一定會顯示「面積」；有上傳物件平面圖時，還會額外顯示「物件平面圖」的縮圖列。
## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） {#C-team-storefront}
### 房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客） {#jgb/C/team-public-page-purpose}
- phrasings:
  - {text: "招租店舖是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "房東對外首頁怎麼用", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼進去我的招租店舖", source: "draft:outline-20260920", status: proposed}
- sources: [help:slug90_zh-Hant.html]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「房東對外首頁」（招租店舖）是房東對外宣傳用的頁面，除了房東聯絡資訊與基本介紹外，也會公開展示房東旗下所有分類為「刊登中」的物件，方便隨時分享給有興趣的潛在租客。
登入 JGB 後，點選側邊選單左上角大頭照上的藍色房子 Icon，就能連結到專屬的「房東對外首頁」。
### 招租店舖上可以直接編輯哪些內容？（橫幅照片、頭像、自我介紹；團隊身分另可改團隊名稱等欄位，需要「編輯團隊權限」） {#jgb/C/team-public-page-edit-and-banner}
- phrasings:
  - {text: "招租店舖封面照片怎麼換", source: "draft:outline-20260920", status: proposed}
  - {text: "改自我介紹會同步嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "招租店舖大頭照怎麼設", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/public/Index.vue, code:src/pages/users/public/_parts/AsideInfo.vue, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
招租店舖頁面上，只有管理者且具備「編輯團隊權限」的使用者看得到編輯入口；團隊身分儲存時，還要有「編輯團隊資訊」權限，否則會被擋下並顯示「您目前登入的帳號無法使用編輯團隊功能」。
個人房東身分可以更換頁面上方的橫幅照片（按「更換照片」）與頭像（頭像右下角的相機圖示），並編輯自我介紹。
團隊身分可以更換橫幅照片與頭像，並編輯團隊名稱、經理人證號、租賃管理員證號、公司電話、公司Email 與團隊介紹。
個人房東在這裡更換的頭像，與帳號資訊頁的照片是同一張；橫幅照片與自我介紹則不會出現在帳號資訊頁。
團隊身分在這裡改的團隊名稱，與「團隊資訊」頁的「團隊名稱」是同一個欄位。
更換橫幅照片時，畫面會建議尺寸為 1920 x 576。
### 招租店舖怎麼篩選物件？（篩選條件加關鍵字搜尋，手機版多數條件收在「更多」；可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30） {#jgb/C/team-public-page-filter-and-view}
- phrasings:
  - {text: "招租店舖怎麼篩選物件", source: "draft:outline-20260920", status: proposed}
  - {text: "招租店舖顯示模式", source: "draft:outline-20260920", status: proposed}
  - {text: "招租店舖每頁顯示幾筆", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/public/Index.vue, code:src/pages/users/public/_parts/PublicSearchBlock.jsx, code:src/pages/users/public/_parts/TopFilter.vue, code:src/pages/users/public/_parts/PublicSearchBlockM.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
畫面寬度 576px 以上時，招租店舖上方有一排篩選條件：經理人、國家、縣市、行政區、社區、捷運、空間類型、格局、建築類型、租金與面積（買賣模式則是售價與面積），以及 VR、有電梯、可開伙、可養寵物等其他條件。
畫面寬度 576px 以上時，上方還有關鍵字搜尋框，可以輸入案名、地址、經理人、社區。
畫面寬度小於 576px（手機）時，上方只直接顯示經理人、建築類型與「更多」，其餘條件收在「更多」裡；租金與售價只在幣別為新台幣時才出現；關鍵字搜尋框可以輸入案名、地址、經理人、大房東、租客、社區。
多團隊招募頁沒有經理人與社區這兩個篩選條件。
物件列表可以切換「小圖示」「大圖示」「條列式」三種顯示模式。
招租店舖的每頁筆數可選30、60或90項（預設30項），只有多團隊招募頁才提供10、30、60或90項（預設10項）。
沒有符合篩選條件的結果時，會顯示「沒有符合的結果」並建議調整篩選條件。
### 招租店舖怎麼分享？（電腦上開分享視窗可複製連結或分享到 FB、Line、LinkedIn；手機上會叫出系統分享選單；分享的是目前頁面的網址） {#jgb/C/team-public-page-share}
- phrasings:
  - {text: "招租店舖怎麼分享", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼分享招租店舖到Line", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/public/_parts/AsideInfo.vue, code:src/mixin/methods.js]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
點擊招租店舖資訊欄最下方的分享圖示，一般（電腦）瀏覽器會開啟分享視窗，可以複製連結，或分享到 Facebook、Line、LinkedIn。
在 Android、iOS 等手機或平板裝置上，如果瀏覽器支援系統分享功能，點擊分享圖示會直接叫出系統分享選單，不會出現上述分享視窗。
分享出去的網址就是目前這個招租店舖頁面的網址，已套用的篩選條件也會一併帶在網址上。
### 多團隊招募頁和一般招租店舖有什麼不同？（沒有指定住宅或商用時自動轉址到住宅、只顯示招租、不顯示社區篩選、每頁預設 10 筆） {#jgb/C/team-public-page-recruitment}
- phrasings:
  - {text: "招募頁每頁顯示幾筆", source: "draft:outline-20260920", status: proposed}
  - {text: "招募頁跟一般店舖的網址不一樣嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "招募頁跟招租店舖差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/users.js, code:src/pages/users/public/Index.vue]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
多團隊招募頁如果網址沒有帶物件用途，會自動轉址並補上「住宅」用途。
多團隊招募頁固定只顯示招租物件，且不會載入社區篩選模組，這兩點都跟一般招租店舖不同。
多團隊招募頁每頁預設顯示 10 筆，一般招租店舖則是 30 筆。
