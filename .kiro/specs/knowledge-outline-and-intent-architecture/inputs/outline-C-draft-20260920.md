# C 架草稿（jgb2 master @ b2ee2ac382ce；粗目 11、細目 81、句 171）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 社區列表與建立（8 條；頁：communities.index、communities.list、communities.pick）

### 社區總表顯示什麼資訊？（物件總數、招租／買賣廣告數、空置數量、本月應收與已收）
- 講法：社區總表看得到什麼／社區列表顯示哪些數字／空置數量怎麼算／每個社區的招租買賣數量在哪看
- 給誰看：property_manager
- 社區總表會列出每個社區的物件總數、招租中物件數量、買賣中物件數量，以及本月應總收與本月已總收金額。〔src/pages/communities/_parts/CommunityItem.vue〕
- 空置數量的計算方式是物件總數量減去有執行中合約的物件總數量。〔src/pages/communities/_parts/CommunityItem.vue〕
- 當社區已啟用差額發票時，該社區列會額外顯示「開設差額發票」標籤與底租金額。〔src/pages/communities/_parts/CommunityItem.vue〕

### 如何新增社區？（訂閱方案有可建立社區數量上限）
- 講法：怎麼新增社區／社區數量有上限嗎／新增社區按鈕在哪
- 給誰看：property_manager
- 在社區總表按下「新增社區」按鈕即可建立一筆新社區，建立後會直接進入社區編輯頁面。〔src/pages/communities/list/Index.vue〕
- 訂閱方案對可建立的社區數量有上限，達到上限時無法繼續新增社區。〔src/type/commit.ts〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/type/commit.ts | grep -n "subscribedPlanCommunityIsFull"', 'result': '1 hit：`subscribedPlanCommunityIsFull = "subscribedPlanCommunityIsFull", // 訂閱方案可以建立的社區數量已達上限`', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -nF "t(\'新增社區\')" → 至少 2 hits，證明檔案與 grep 條件本身有效'}`

### 怎麼批次新增社區、或複製現有社區建立新社區？
- 講法：批次新增社區怎麼做／社區可以用 Excel 匯入嗎／複製現有社區／有沒有現成社區範本可以複製
- 給誰看：property_manager
- 在「新增社區」按鈕旁的選單中選擇「批次新增」，可以下載指定格式的 Excel 範本填寫後上傳建立多筆社區。〔src/components/Lightbox/CommunitiesBatchAdd.vue〕
- 批次新增的上傳檔案大小上限為 10MB。〔src/components/Lightbox/CommunitiesBatchAdd.vue〕
- 選單中的「複製現有社區」會先進入社區選擇畫面，挑選一個已存在的社區做為範本再建立新社區；此選項只在目前篩選結果的社區列表不是空的時才會出現。〔src/pages/communities/list/Index.vue〕

### 社區總表怎麼搜尋與排序？（案名／地址關鍵字、縣市行政區、建物類型、捷運站）
- 講法：社區怎麼搜尋／社區列表篩選條件有哪些／怎麼依地區找社區／社區排序方式
- 給誰看：property_manager
- 社區總表的關鍵字搜尋欄可以輸入案名或地址查詢。〔src/pages/communities/list/_parts/CommunitiesAdvanceSearchBlock.jsx〕
- 進階搜尋提供國家、縣市、行政區、建物類型與捷運站等下拉篩選條件。〔src/pages/communities/list/_parts/CommunitiesAdvanceSearchBlock.jsx〕
- 列表也可以切換排序方式，選定的排序會被記住供下次進入沿用。〔src/pages/communities/list/Index.vue〕
- ⚠️ 待查：進階搜尋下拉的縣市／行政區／建物類型／捷運站中文標籤來自後端 searchOptions API 回傳值，程式端看不到逐字標籤字串，僅能確認欄位存在（country/city/district/building/MRT）。

### 社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原）
- 講法：社區怎麼刪除／社區可以刪除嗎／刪不掉社區怎麼辦／刪除社區的限制
- 給誰看：property_manager
- 社區列表項目的設定選單提供「刪除」選項，但只有在該社區底下的物件總數為 0 時才能刪除成功。〔src/pages/communities/_parts/CommunityItem.vue〕
- 若社區底下還有物件，點擊刪除會出現提示「無法刪除社區，需沒有任何物件才能刪除社區」。〔src/pages/communities/_parts/CommunityItem.vue〕
- 確認刪除的視窗會提醒「社區刪除後，將無法復原」，需再次確認才會真的刪除。〔src/components/Lightbox/CommunityDelete.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/_parts/CommunityItem.vue | grep -n "無法刪除社區"', 'result': "1 hit：`window.globalErrorShow(t('無法刪除社區，需沒有任何物件才能刪除社區'))`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/_parts/CommunityItem.vue | grep -n "quantities_of_estates" → 多筆 hits，證明檔案與 grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/components/Lightbox/CommunityDelete.vue | grep -n "將無法復原"', 'result': "1 hit：`{ t('社區刪除後，將無法復原，請問您確定要刪除「[s1]」嗎', [props.name]) }`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/components/Lightbox/CommunityDelete.vue | grep -n "props.name" → 至少 1 hit，證明檔案與 grep 條件本身有效'}`

### 社區總表可以匯出嗎？（需要匯出物件權限，會依目前篩選條件匯出）
- 講法：社區怎麼匯出／社區清單匯出功能／匯出社區要什麼權限
- 給誰看：property_manager
- 具備匯出物件權限的使用者，可以在社區總表點擊「匯出社區」，依目前的搜尋條件匯出整批社區資料，匯出工作會進入下載佇列。〔src/pages/communities/list/Index.vue〕
- 沒有匯出物件權限時，「匯出社區」按鈕不會顯示；有匯出物件權限、但目前篩選結果為 0 筆時，按鈕會顯示但無法點擊。〔src/pages/communities/list/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -n "export_estate"', 'result': '1 hit（第231行：`store.state.userData?.permission?.export_estate && <div class={...disabled...}>`——沒有 export_estate 權限時整個 && 運算式短路為 false／undefined，該 div 不會被渲染；`disabled` class 只在 pageNav.total === 0 時另外套用，兩者是各自獨立的條件）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -n "匯出社區" → 2 hits（第171、234行皆存在該按鈕文字，證明檔案與 grep 條件本身有效）'}`

### 社區總表每頁筆數可以調整嗎？（30／60／90項）
- 講法：社區總表每頁顯示幾筆／社區列表分頁筆數／怎麼調整每頁顯示社區數
- 給誰看：property_manager
- 社區總表下方可以選擇每頁顯示30項、60項或90項。〔src/pages/communities/list/Index.vue〕

### 誰看得到新增社區的入口？（總表右上角需要編輯物件權限；空狀態的批次新增／新增社區入口需要新增物件權限）
- 講法：新增社區按鈕不見了／誰可以新增社區／沒有編輯物件的權限看不到新增社區
- 給誰看：property_manager
- 只有具備編輯物件權限的使用者，才看得到社區總表右上角的「新增社區」按鈕與批次新增、複製現有社區的選單；沒有編輯物件的權限時，這些按鈕與選單都不會顯示。〔src/pages/communities/list/Index.vue〕
- 當該分類目前沒有任何社區時，畫面會改顯示空狀態；此時「此分類尚未有社區，您可以選擇😎：」文字與底下的「批次新增」「新增社區」按鈕，只有在使用者具備新增物件權限時才會出現，沒有新增物件權限的使用者只會看到「此分類尚未有社區」的提示文字。〔src/pages/communities/list/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -nF "userData?.permission?.edit_estate &&"', 'result': '1 hit：`store.state.userData?.permission?.edit_estate && <><LightboxCommunitiesBatchAdd />` —— && 短路，沒有編輯物件權限時整段（新增社區按鈕與批次新增/複製現有社區選單）都不會渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -nF "t(\'新增社區\')" → 至少 2 hits，證明檔案與 grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -nF "userData.permission?.add_estate"', 'result': '1 hit：`!isEmpty(store.state.userData.permission) && store.state.userData.permission?.add_estate` 三元運算式的條件，沒有新增物件權限時只會渲染 false 分支「此分類尚未有社區」，不會有批次新增／新增社區按鈕', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/list/Index.vue | grep -nF "此分類尚未有社區" → 2 hits，證明兩種文案（含選單／不含選單）都存在，grep 條件本身有效'}`

## 社區資料編輯（基本資料、照片與描述、介紹與交通）（6 條；頁：communities.edit、communities.edit.basic、communities.edit.gallery、communities.edit.intros）

### 社區編輯有哪些分頁？（基本資料、介紹與交通、照片與描述）
- 講法：社區編輯有哪些分頁／社區資料要編輯哪些項目／編輯社區從哪裡進去
- 給誰看：property_manager
- 社區編輯頁在「社區資訊」群組下分成「基本資料」「介紹與交通」「照片與描述」三個分頁，都屬於同一個社區資料。〔src/routes/communities.js〕
- 直接從社區總表點進「編輯社區」時，會先進入「基本資料」分頁。〔src/routes/communities.js〕

### 社區基本資料要填什麼？（社區名稱限30字、詳細地址與對外顯示地址、建築類型、總樓層、屋齡）
- 講法：社區基本資料要填什麼／社區名稱字數限制／對外顯示地址跟詳細地址差在哪
- 給誰看：property_manager
- 基本資料分頁的「社區名稱」欄位，輸入框的提示文字寫著限制30個字，用來告訴客戶這個社區叫什麼名字；查不到對應的長度驗證規則，無法確認超過30字時是否真的會被擋下。〔src/pages/communities/edit/Basic.vue〕
- 地址分成「詳細地址」與「對外顯示地址」兩組，對外顯示地址可以按「同詳細地址」直接帶入詳細地址的內容，且對外顯示地址會標記在 Google 地圖上。〔src/pages/communities/edit/Basic.vue〕
- 其他欄位還包含建築類型、總樓層（限純數字）與屋齡（限純數字）；另外還有一個「社區細節」欄位區塊，只有團隊被歸類為特定合作團隊時才會顯示，一般團隊看不到。〔src/pages/communities/edit/Basic.vue〕
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -nF "beyond360"', 'result': "1 hit：`specialRolesState.getSpecialGroupsByRole(store.state.userData?.role?.id)?.includes('beyond360')` && 短路包住「社區細節」整個區塊，一般團隊（不在 beyond360 特定合作團隊名單）不會渲染這個區塊", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -nF "t(\'社區細節\')" → 1 hit，證明「社區細節」區塊本身確實存在、grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -n "maxlength\\|maxLength"', 'result': '0 hits：整份檔案查不到 maxlength 或 maxLength 屬性，「限制30個字」目前只出現在 placeholder 提示文字，找不到對應的長度驗證規則', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -nF "限制 [s1] 個字" → 至少 2 hits，證明「限制30個字」文案本身確實存在於同一份檔案、grep 條件本身有效'}`
- ⚠️ 待查：「社區名稱」30字限制目前只在輸入框的 placeholder 文案看到，Basic.vue 裡查不到 maxlength 屬性或對應的驗證規則（如 yup schema），無法確認是否真的有強制驗證。

### 社區照片與描述可以上傳幾張圖片？（限1張，JPG/PNG，檔案大小最大10MB）
- 講法：社區照片上限幾張／社區封面圖怎麼傳／社區圖片格式限制
- 給誰看：property_manager
- 「照片與描述」分頁的社區相片，最多只能上傳1張，格式支援 JPG、PNG，檔案大小最大 10MB。〔src/pages/communities/edit/Gallery.vue〕

### 社區照片與描述什麼時候會跳出「已更新」提示？（存檔成功後才出現，不是上傳當下）
- 講法：社區照片上傳成功提示在哪／社區資料存檔提示／上傳照片後畫面沒反應正常嗎
- 給誰看：property_manager
- 「照片與描述」分頁按下儲存、社區資料更新成功後才會跳出提示：一般編輯流程一律顯示社區名稱加上「已更新」；只有在物件強制綁定導引流程中，社區是新建立的（非選擇既有社區）時，才會改顯示「創建成功」。〔src/pages/communities/edit/Gallery.vue〕
- 單純把照片上傳完成，不會立刻跳出這個提示，要等整個分頁儲存成功才會顯示。〔src/pages/communities/edit/Gallery.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Gallery.vue | grep -nF "創建成功"', 'result': "1 hit：`window.globalNoticeShow(...${t('創建成功')})` 只出現在 `if (isForceBinding)` 分支底下、且 `isExistedCommunity` 為 false（新建立的社區）時才會執行；一般編輯流程（!isForceBinding）與強制綁定流程中選擇既有社區（isExistedCommunity 為 true）都會走到「已更新」那一行", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Gallery.vue | grep -nF "已更新" → 2 hits（一般編輯流程、強制綁定流程選既有社區各一次），證明檔案與 grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Gallery.vue | grep -n "onUploaded"', 'result': '1 hit（第163行，AjaxUploader 的 onUploaded 只把新檔案 push 進 editStore.form.gallery 陣列，沒有呼叫任何提示函式）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Gallery.vue | grep -n "globalNoticeShow" → 3 hits，且都在 submitResultHandler 函式內（第111-145行區間），證明提示只綁在存檔流程、不是上傳流程'}`

### 社區介紹與交通怎麼填？（社區簡介、鄰近交通說明、可加多個鄰近捷運站）
- 講法：社區介紹要寫什麼／怎麼加捷運站／社區交通資訊在哪填
- 給誰看：property_manager
- 「介紹與交通」分頁可以填寫社區簡介文字說明與鄰近交通描述，讓客戶更了解社區細節。〔src/pages/communities/edit/Intros.vue〕
- 鄰近捷運站可以點選「新增鄰近捷運站」加入多筆，每筆需要選擇捷運線與停靠站。〔src/pages/communities/edit/Intros.vue〕

### 社區基本資料哪個欄位是必填？（只有社區名稱是必填）
- 講法：社區哪些欄位一定要填／社區名稱一定要填嗎／社區地址是必填嗎
- 給誰看：property_manager
- 社區基本資料分頁裡，標記為必填的欄位只有「社區名稱」一個，其餘欄位（地址、建築類型、總樓層、屋齡等）都不是必填。〔src/pages/communities/edit/Basic.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -n "after-required"', 'result': '只查得到 1 個 after-required 用在欄位標題上，就是「社區名稱」那一個 `<h4 class=\\"after-required\\">`', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/edit/Basic.vue | grep -n "屋齡" → 至少 1 hit，證明屋齡欄位本身確實存在、只是沒有 after-required 標記'}`

## 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁）（5 條；頁：communities.estates、estates.pick）

### 社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額）
- 講法：社區物件頁上面的卡片是什麼／社區概要顯示哪些數字／社區物件總覽在哪看
- 給誰看：property_manager
- 社區底下的物件清單頁最上方會顯示這個社區的概要卡片，包含招租廣告、買賣廣告、目前空置數量（皆以物件總數為分母）、建築類型與屋齡。〔src/pages/communities/estates/_parts/CommunityOverview.vue〕
- 卡片上也會顯示這個社區「本月應收金額」與「本月已收金額」。〔src/pages/communities/estates/_parts/CommunityOverview.vue〕
- 卡片右上角的選單可以「編輯」社區、「前往社區廣告」（社區公開頁），管理員身分才會看到「編輯」與「刪除社區」選項。〔src/pages/communities/estates/_parts/CommunityOverview.vue〕

### 社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變）
- 講法：社區物件怎麼切換招租買賣／總覽招租買賣分類在哪／社區物件清單分類切換
- 給誰看：property_manager
- 社區底下的物件清單提供「總覽-1」「招租」「買賣」三種分類切換。〔src/utils/constants/estate.js〕
- 切到「招租」時清單欄位會顯示招租廣告與租金，切到「買賣」時則顯示買賣廣告與售價，欄位標題會依所選分類自動變化。〔src/pages/communities/estates/_parts/ListTable.vue〕
- ⚠️ 待查：「總覽」分類的 label 在程式裡寫的是 `t('總覽-1')`（src/utils/constants/estate.js），repo 內查不到任何 zh-Hant 翻譯字典檔（find 全庫找不到 *zh-Hant* 的翻譯資料檔，只有無關的 vendor/giggsey locale 資料），無法確認這個翻譯 key 實際顯示出來的中文字串是「總覽」還是帶著「-1」字樣；本大綱一律以「總覽」書寫，但這是推測而非逐字驗證。

### 怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）
- 講法：社區物件怎麼新增／社區物件批次新增／複製現有物件／物件數量上限
- 給誰看：property_manager
- 有新增物件權限的使用者，在社區物件清單「所有物件」分類下可以點「新增物件」直接建立、選「批次新增」上傳表格，或選「複製現有物件」以既有物件為範本。〔src/pages/communities/estates/Index.vue〕
- 訂閱方案對可建立的物件數量有上限，達到上限時新增物件會被擋下並提示已達上限。〔src/pages/communities/estates/Index.vue〕
- 當社區內只剩非住宅類的「社區共用空間」物件、沒有其他物件時，不會提供「複製現有物件」選項。〔src/pages/communities/estates/Index.vue〕
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/estates/Index.vue | grep -n "property_purpose_key === 3"', 'result': '1 hit——`hasOnlyPublicAreaWithoutEstate` 判斷式，`property_purpose_key === 3` 對應後端 `Estate::SHARE_HOUSING`（社區共用空間），此判斷為 true 時「複製現有物件」選項不會出現', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/estates/Index.vue | grep -n "複製現有物件" → 至少 1 hit，證明該選項文字確實存在、grep 條件本身有效'}`

### 社區底下有差額發票、投報率頁籤嗎？（依團隊是否開通該功能才會出現，投入成本與投報率兩個頁籤是同一個開關）
- 講法：社區差額發票頁籤／社區投報率在哪看／社區物件頁籤有哪些
- 給誰看：property_manager
- 「所有物件」頁籤永遠存在，「差額發票」頁籤只在該社區開通差額發票功能時才會加入。〔src/utils/constants/community.js〕
- 「投入成本」與「投報率」兩個頁籤是由同一個開關控制的，開通投報率功能時這兩個頁籤會一起出現，沒辦法只開通其中一個。〔src/pages/communities/estates/Index.vue〕
- 沒有任何額外頁籤開通時，畫面不會顯示頁籤切換器，直接呈現物件清單。〔src/pages/communities/estates/Index.vue〕
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/estates/Index.vue | grep -n "hasTabs"', 'result': '2 hits：`hasTabs: computed(()=>{ return Boolean(singleData.data?.balance_invoice?.enabled) || Boolean(singleData.data?.community_roi?.enabled) })` 定義，以及 `state.hasTabs ? <ChoiceToggler...` 的渲染判斷——兩者皆為 false 時頁籤切換器不會渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/estates/Index.vue | grep -n "CommunityTab.estateList" → 至少 1 hit，證明「所有物件」分類本身固定存在、只是切換器 UI 被隱藏'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/estates/Index.vue | grep -nF "community_roi"', 'result': '3 hits：`isRoiEnabled`、`if (singleData.data?.community_roi?.enabled){ options.push(...CommunityRoiChoiceOptions) }`、`hasTabs` 都讀同一個 community_roi.enabled 旗標；push(...CommunityRoiChoiceOptions) 一次把「投入成本」與「投報率」兩個選項一起加入，沒有分開判斷的邏輯', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/utils/constants/community.js | grep -nF "投入成本" → 1 hit，證明 CommunityRoiChoiceOptions 常數裡確實把兩個頁籤定義在一起、grep 條件本身有效'}`

### 社區物件清單每頁筆數可以調整嗎？（30／60／90項）
- 講法：社區物件每頁顯示幾筆／物件清單分頁筆數／怎麼調整每頁項目數
- 給誰看：property_manager
- 社區物件清單下方可以選擇每頁顯示30項、60項或90項，預設為30項。〔src/pages/communities/estates/Index.vue〕

## 社區公開頁（社區詳情、社區總表）（4 條；頁：communities.show）

### 社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件）
- 講法：社區詳情頁有什麼／社區公開頁看得到什麼／社區廣告頁內容
- 給誰看：property_manager、prospect
- 社區公開頁（社區廣告）會顯示「社區基本資訊」（類型、總樓層數、屋齡）、「社區交通與環境設施」（鄰近捷運站、鄰近交通）以及「社區介紹」文字說明。〔src/pages/communities/show/Index.vue〕
- 頁面下方的「社區所有刊登中物件」會分別列出招租中與買賣中的物件數量，各自可以點「更多」看更多物件。〔src/pages/communities/show/Index.vue〕
- 頁尾會顯示本社區的 JGB 編號，並附上房屋現況與法定用途的提醒文字。〔src/pages/communities/show/Index.vue〕

### 社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間、售價單價區間坪或平方公尺隨語系切換）
- 講法：社區價格區間在哪看／社區租金區間／社區售價單價區間／坪數單位切換
- 給誰看：property_manager、prospect
- 社區公開頁最上方會顯示該社區的「租賃金額區間」與「售價金額區間」，這兩個區間各自都只在有2筆資料時才會顯示。〔src/pages/communities/show/_parts/PageTop.vue〕
- 若社區有登記售價單價，最上方還會另外顯示「售價單價區間」，單位固定跟著網頁語系顯示：繁體中文 顯示坪，其他語系顯示平方公尺，使用者無法手動切換。〔src/pages/communities/show/_parts/PageTop.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/show/_parts/PageTop.vue | grep -nF "sell_price_range_per_unit"', 'result': '3 hits：`state.data?.sell_price_range_per_unit?.length === 2` 判斷式，以及底下兩個 `sell_price_range_per_unit[0]`／`[1]` 取值渲染——坪／平方公尺單位是這個「售價單價區間」區塊專用的，不是「租賃金額區間」「售價金額區間」的單位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/show/_parts/PageTop.vue | grep -nF "租賃金額區間" → 1 hit，證明檔案與 grep 條件本身有效'}`

### 社區公開頁怎麼分享？（分享燈箱、查看所有物件連結）
- 講法：社區頁面怎麼分享／社區查看所有物件連結／社區分享燈箱
- 給誰看：property_manager
- 頁面提供分享功能，點擊分享按鈕會開啟社區分享的燈箱。〔src/pages/communities/show/_parts/PageTop.vue〕
- 側邊欄也提供「查看所有物件」連結，可直接前往該社區的物件清單。〔src/pages/communities/show/_parts/AsideContact.vue〕

### 在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有管理員看得到這個選單）
- 講法：社區詳情頁怎麼編輯社區／社區公開頁回總表／社區詳情頁返回Dashboard
- 給誰看：property_manager
- 只有管理員身分的使用者，在社區廣告頁才會看到右上角的選單，選單有四個選項：「編輯」跳到社區編輯頁、「社區詳情」跳到該社區的管理端物件清單頁、「社區總表」回到社區列表、「返回 Dashboard」回到管理端首頁。〔src/pages/communities/show/Index.vue〕

## 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者）（5 條；頁：communities.forceBinding、communities.forceBinding.edit、communities.forceBinding.edit.binding、communities.forceBinding.welcome）

### 為什麼會出現「物件需綁定社區」的導引？（2022/05/12 社區功能上線，只有團隊擁有者能操作）
- 講法：為什麼要綁定社區／物件為什麼要綁社區／誰可以做物件綁定社區
- 給誰看：property_manager
- 系統於 2022/05/12 新增「社區」功能後，要求既有物件必須全數綁定至社區才能使用系統，因此舊帳號登入時會被導向這個綁定導引畫面。〔src/pages/communities/forceBinding/Welcome.vue〕
- 執行這個綁定動作需要是團隊擁有者身分，若不是團隊擁有者，畫面會顯示「權限不足」。〔src/pages/communities/forceBinding/Welcome.vue〕

### 物件綁定社區的導引起始畫面顯示什麼？（已綁定與尚未綁定的物件數量、需同意服務條款）
- 講法：綁定社區進度在哪看／還有幾個物件沒綁社區／綁定物件前要同意什麼
- 給誰看：property_manager
- 起始畫面會分別顯示目前「尚未綁定至社區」與「已成功綁定至社區」的物件數量。〔src/pages/communities/forceBinding/Welcome.vue〕
- 點擊「繼續」即代表同意 JGB 的服務條款與隱私權聲明才能往下一步。〔src/pages/communities/forceBinding/Welcome.vue〕

### 物件綁定社區導引有哪兩個步驟？（填寫社區資料、選擇欲綁定社區內的物件；未完成系統功能無法正常使用）
- 講法：綁定社區流程有幾步／先建社區還是先綁物件／沒綁完社區會怎樣
- 給誰看：property_manager
- 導引分兩步：第一步「填寫社區資料」，第二步「選擇欲綁定社區內的物件」。〔src/pages/communities/forceBinding/edit/Index.vue〕
- 在物件全數綁定完成之前，系統功能將無法正常使用。〔src/pages/communities/forceBinding/edit/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/forceBinding/edit/Index.vue | grep -n "系統功能將會無法正常使用"', 'result': "1 hit：`{t('因系統功能更新後，各功能皆採最新的社區物件來進行動作，故未綁定完成前，系統功能將會無法正常使用')}`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/forceBinding/edit/Index.vue | grep -n "填寫社區資料" → 1 hit，證明檔案與 grep 條件本身有效'}`

### 怎麼挑選要綁定的物件？（可關鍵字搜尋、每頁30/60/90項，確認綁定後無法修改）
- 講法：怎麼選要綁定的物件／綁定物件可以改嗎／綁定物件怎麼搜尋
- 給誰看：property_manager
- 選擇物件的畫面提供關鍵字搜尋、物件名稱、細節、招租廣告與買賣廣告數量欄位，每頁可切換30、60、90項。〔src/pages/communities/forceBinding/edit/Binding.vue〕
- 畫面上明確提示「確認綁定物件後，即不能修改」，確認綁定的視窗也會再次提醒「請確認欲綁定的物件，綁定後即不能修改」。〔src/pages/communities/forceBinding/edit/Binding.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/forceBinding/edit/Binding.vue | grep -n "即不能修改"', 'result': '2 hits：畫面提示與確認視窗各出現一次「確認綁定物件後，即不能修改」／「請確認欲綁定的物件，綁定後即不能修改」', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/communities/forceBinding/edit/Binding.vue | grep -n "30項" → 1 hit，證明檔案與 grep 條件本身有效'}`

### 綁定完成後會看到什麼？（全部綁完顯示恭喜，還有剩則提示繼續綁定）
- 講法：綁定完成畫面／還有物件沒綁完怎麼辦／綁定物件成功提示
- 給誰看：property_manager
- 當所有物件都綁定完成時，畫面會顯示「恭喜！你已經成功綁定所有物件」，並提供前往社區總表的按鈕。〔src/pages/communities/forceBinding/edit/Binding.vue〕
- 若還有物件尚未綁定完成，畫面則顯示「你完成最困難的部分！」並提示「你已經完成新增社區的必需步驟，但還有些物件尚未綁定完成」，可以點擊繼續綁定物件。〔src/pages/communities/forceBinding/edit/Binding.vue〕

## 物件列表與篩選（10 條；頁：estates.index、estates.list）

### 物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）
- 講法：物件總表怎麼新增物件／新增物件要選社區嗎／物件總表可以批次新增嗎／複製現有物件在物件總表
- 給誰看：property_manager
- 在物件總表點「新增物件」或「複製現有物件」，都會先導向社區選擇畫面，再回來建立或複製物件。〔src/pages/estates/list/_parts/PageTop.vue〕
- 目前物件總表沒有「批次新增」入口可以使用，這個選項目前是隱藏、不會顯示出來的。〔src/pages/estates/list/_parts/PageTop.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/PageTop.vue | grep -n "批次新增"', 'result': '1 hit，出現在 HTML 註解 `<!-- <a class=\\"option\\">` 開頭的區塊內（第98-99行一帶），代表整段選項被註解掉、不會渲染到畫面上', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/PageTop.vue | grep -n "communities.pick" → 至少 1 hit，證明「新增物件」「複製現有物件」走社區選擇畫面的路由設定真的存在、grep 條件本身有效'}`
- ⚠️ 待查：幫助中心文章 qa01（物件批次新增表格如何填寫？）描述『在物件管理的社區總表中，按下右上方新增物件旁的三角形，選擇「批次新增」』，但目前物件總表（src/pages/estates/list/_parts/PageTop.vue）的「批次新增」選項是被註解掉的死碼、畫面不會顯示；無法判斷是舊文件未更新、還是入口移到別處（例如社區底下的物件清單 communities.estates 仍保留批次新增）。

### 物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）
- 講法：物件總表顯示物件總數／還可以新增幾個物件／尚可新增物件數量在哪看
- 給誰看：property_manager
- 只有具備新增物件權限的使用者，才會在物件總表標題下方看到「目前物件總數」與「尚可新增」的數字，尚可新增的數量會依訂閱方案剩餘額度變動。〔src/pages/estates/list/_parts/PageTop.vue〕

### 物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、用途、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤）
- 講法：物件總表篩選條件有哪些／怎麼依經理人篩選物件／物件怎麼依社區篩選／租金範圍怎麼篩／格局怎麼篩選物件
- 給誰看：property_manager
- 物件總表的進階搜尋提供國家、縣市、行政區、經理人、大房東、社區、捷運站等下拉篩選。〔src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx〕
- 也可以依格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金、面積(坪)與標籤等條件縮小搜尋結果；沒有依用途篩選的選項（用途篩選只在挑選物件用的物件挑選器裡才有）。〔src/use/search/modules/room_count.js〕
- 篩選結果數量會顯示在搜尋條件下方，格式為目前顯示筆數／總筆數。〔src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx | grep -nF "EstateSearchKey.use_for"', 'result': '0 hits——物件總表的進階搜尋沒有渲染用途篩選欄位（雖然 EstateListQueries 常數裡有定義 use_for 這個查詢鍵，但這個畫面沒有用它）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx | grep -nF "EstateSearchKey.building" → 1 hit，證明檔案與 grep 條件本身有效、其他篩選確實存在'}`

### 物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）
- 講法：物件怎麼用租客手機搜尋／物件關鍵字搜尋範圍／用物件ID找物件
- 給誰看：property_manager
- 物件總表的關鍵字搜尋可以切換搜尋範圍為案名、地址、租客、ID、手機或信箱。〔src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx〕

### 物件總表可以批次操作嗎？（匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示）
- 講法：物件怎麼批次下架／怎麼一次刊登多筆物件／物件總表可以匯出嗎
- 給誰看：property_manager
- 在物件總表勾選多筆物件後，依權限可以看到「匯出物件」「新增批次帳單」「批次刊登招租廣告」「批次取消刊登招租廣告」「刪除」等批次動作選單，其中「刪除」要求勾選的物件全部都沒有合約才能執行。〔src/use/config/useEstateTypes.js〕
- 批次刊登招租廣告完全沒有失敗物件時，會直接跳出「[數量]件招租廣告已刊登!」的成功提示，只要有任何一件失敗，改成跳出結果燈箱列出成功與失敗的物件；批次取消刊登招租廣告則只有在完全沒有失敗物件時才會跳出「[數量]件招租廣告下架成功!」的提示，若有物件失敗，畫面不會出現任何燈箱或錯誤訊息。〔src/pages/estates/list/_parts/ListTable.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/use/config/useEstateTypes.js | grep -n "requireAllNoContract"', 'result': "1 hit：`{ label: t('刪除'), ..., requireAllNoContract: true, onClick: ()=>{ store.commit('lightbox', 'EstateBatchDelete') } }`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/use/config/useEstateTypes.js | grep -nF "t(\'刪除\')" → 至少 1 hit，證明檔案與 grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/ListTable.vue | grep -nF "failed_estates_amount === 0"', 'result': '2 hits：closeRent（批次取消刊登）分支只在 failed_estates_amount===0 時跳成功提示、非0時什麼都不做直接刷新列表；openRent（批次刊登）分支同樣在===0時跳成功提示，非0時改開 estatePublishResult 結果燈箱——兩個分支對失敗的處理方式不同', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/list/_parts/ListTable.vue | grep -nF "estatePublishResult" → 至少 1 hit，證明結果燈箱只掛在 openRent（批次刊登）分支、closeRent 沒有對應的失敗燈箱，grep 條件本身有效'}`

### 物件狀態會影響哪些功能？（未刊登／刊登中／洽談中／合約中，各自能做的操作不同）
- 講法：物件狀態影響什麼／洽談中物件可以做什麼／物件狀態怎麼判斷
- 給誰看：property_manager、prospect
- 物件總表把物件分成「未刊登」「刊登中」「洽談中」「合約中」等分類，不同分類可執行的操作不同：未刊登可以編輯物件、刊登物件、刪除物件；刊登中可以編輯物件、取消刊登、新增或編輯合約。〔幫助中心:slug39_zh-Hant.html〕
- 「洽談中」代表這個物件已經有合約但還沒有任何一份完成簽署，一旦雙方都簽署完成就會變成「合約中」；此狀態下可以編輯物件、查看合約、編輯合約。〔幫助中心:slug39_zh-Hant.html〕
- 「合約中」狀態下可以查看合約，若租約在30天內到期，還可以編輯物件、刊登物件與查看合約；已歸入歷史的合約不列入判斷物件狀態的依據。〔幫助中心:slug39_zh-Hant.html〕
- 否定查證：`{'sentence_index': 1, 'grep': 'grep -n "還沒有任何一份完成簽署" /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/slug39_zh-Hant.html', 'result': '1 hit：「洽談中」代表這個物件<b>已經有合約，但還沒有任何一份完成簽署</b>', 'positive_control': 'grep -c "未刊登" /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/slug39_zh-Hant.html → 至少 1 hit，證明檔案與 grep 條件本身有效'}`
- ⚠️ 待查：這條主要依據幫助中心 slug39 文章；程式碼裡目前查得到的即時合約狀態篩選（src/use/search/modules/contractStatus.js）只有『無租約／洽談中／租約中』三態，且第三態的字面標籤是「租約中」而非文件的「合約中」，無法在程式端找到與文件完全一致、逐字對應的『未刊登／刊登中／洽談中／合約中』四態分類字串，兩者是否為同一機制的不同呈現無法判斷。

### 物件總表每頁筆數可以調整嗎？（30／60／90項）
- 講法：物件總表每頁顯示幾筆／物件列表分頁筆數／調整每頁顯示物件數
- 給誰看：property_manager
- 物件總表下方可以選擇每頁顯示30項、60項或90項。〔src/pages/estates/list/Index.vue〕

### 物件總表篩選還有哪些條件？（空間類型多選、其他群組：VR、有電梯、可開伙、可養寵物）
- 講法：物件怎麼篩VR／物件篩選可養寵物／物件篩選有電梯
- 給誰看：property_manager
- 進階搜尋提供「空間類型」多選篩選（例如整戶、套房、雅房等）。〔src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx〕
- 另外還有一組「其他」群組篩選，可複選是否有VR、有電梯、可開伙、可養寵物。〔src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx〕

### 物件總表怎麼切換總覽／招租／買賣？（三種分類切換）
- 講法：物件總表怎麼切換招租買賣／物件總覽招租買賣分類／物件列表分類切換
- 給誰看：property_manager
- 物件總表提供「總覽」「招租」「買賣」三種分類切換，切換後畫面上的物件清單會依分類重新載入。〔src/utils/constants/estate.js〕
- ⚠️ 待查：「總覽」分類的 label 在程式裡寫的是 `t('總覽-1')`（src/utils/constants/estate.js），repo 內查不到 zh-Hant 翻譯字典檔，無法確認實際顯示出來的中文字串是「總覽」還是帶著「-1」字樣；與 community-estates-category-switch 同一個已知落差，本大綱一律以「總覽」書寫。

### 物件總表怎麼排序？（排序選項由系統提供，上次選的排序方式會被記住並自動帶入）
- 講法：物件總表怎麼排序／上次選的排序方式還在嗎／物件排序選項有哪些
- 給誰看：property_manager
- 物件總表的排序選項由系統提供，使用者可以在列表上方切換排序方式。〔src/pages/estates/list/Index.vue〕
- 切換排序後，這個排序方式會被記住；下次進入物件總表、且網址沒有另外帶排序參數時，會自動帶入上次選擇的排序方式。〔src/pages/estates/list/Index.vue〕

## 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR）（13 條；頁：estates.edit、estates.edit.basic、estates.edit.building_transcript、estates.edit.building_transcript_general、estates.edit.facilities、estates.edit.gallery、estates.edit.intro、estates.edit.vr）

### 物件基本資料的空間類型、用途、格局要怎麼填？
- 講法：物件用途怎麼選／物件格局怎麼填／虛擬辦公室是什麼意思
- 給誰看：property_manager
- 物件基本資料的「空間類型」是一個區塊標題，底下先選「用途」（例如住宅、商用、土地、工業/廠房/倉庫、酒店），兩者都是必填欄位；再依用途選擇對應的「格局」，例如整戶、套房、雅房，或辦公類型的獨立辦公室、固定辦公桌、共享辦公桌、虛擬辦公室、會員等，格局同樣是必填欄位。〔src/pages/estates/edit/basic/Index.vue〕
- 「虛擬辦公室」格局說明為出租業者提供「商業地址」給企業「借址登記」使用、不做實際上班用途的辦公室；「會員」則是共享辦公室業者提供的會員方案。〔src/pages/estates/edit/basic/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -nF "t(\'空間類型\')"', 'result': '1 hit（第430行 `<h4 class=\\"mb-2\\">{{ t(\'空間類型\') }}</h4>`），是區塊標題（h4），不是欄位標籤（fieldTitle）；同一區塊內「用途」（第483行）與「格局」（第507行）才是各自標記 after-required 的必填欄位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -nF "t(\'用途\')" → 至少 1 hit，證明「用途」欄位本身確實存在、grep 條件本身有效'}`

### 物件的詳細地址與對外顯示地址有什麼差別？
- 講法：物件地址怎麼填／對外顯示地址是什麼／物件廣告地址跟實際地址不同
- 給誰看：property_manager
- 物件基本資料分別要填「詳細地址」與「對外顯示地址」，對外顯示地址可以點「同詳細地址」直接帶入詳細地址內容。〔src/pages/estates/edit/basic/Index.vue〕

### 物件的樓層與房號要怎麼填？（頂加輸入+1、地下室輸入-1）
- 講法：頂加怎麼填樓層／地下室樓層怎麼寫／物件之幾房之幾床是什麼
- 給誰看：property_manager
- 物件基本資料要填所在樓層、總樓層、之幾房、之幾床（車位用途物件不需填之幾房之幾床）。〔src/pages/estates/edit/basic/Index.vue〕
- 所在樓層輸入 +1 代表頂加，輸入 -1 代表地下室。〔src/pages/estates/edit/basic/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "parking_space"', 'result': '至少 1 hit：`<div v-if=\\"editStore.form.premises_use_for !== \'parking_space\'\\"` 包住之幾房之幾床欄位，車位用途時整段不渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "之幾房" → 至少 1 hit，證明欄位本身確實存在、grep 條件本身有效'}`

### 物件廣告頁可以隱藏群組/大樓名稱嗎？
- 講法：物件可以不顯示社區名稱嗎／廣告頁隱藏大樓名稱／群組名稱怎麼隱藏
- 給誰看：property_manager
- 物件基本資料的「群組/大樓名稱」欄位會帶入所屬社區名稱（唯讀），旁邊有「在物件廣告頁隱藏群組名稱」的勾選框，勾選後廣告頁就不會顯示社區/大樓名稱。〔src/pages/estates/edit/basic/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "在物件廣告頁隱藏群組名稱"', 'result': '1 hit：`}" />&nbsp;{{ t(\'在物件廣告頁隱藏群組名稱\') }}`', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "群組/大樓名稱" → 至少 1 hit，證明檔案與 grep 條件本身有效'}`

### 社宅物件建物謄本要填什麼？（申請謄本日期、段小段、謄本面積公式，不會顯示在廣告頁）
- 講法：社宅建物謄本要填什麼／社宅謄本面積怎麼算／社宅建物謄本會公開嗎
- 給誰看：property_manager
- 社宅物件的建物謄本分頁要求填寫申請謄本日期、地號（段小段中文、地號）、建號（段小段中文、建號）、建築完成日期與謄本面積，這些資料不會顯示在物件廣告頁上，主要用來方便未來完備合約資料。〔src/pages/estates/edit/building_transcript/Index.vue〕
- 謄本面積要以建物謄本所載面積為準，公式為主建物面積加附屬建物面積加持分公設面積減車位面積。〔src/pages/estates/edit/building_transcript/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -n "display_property_purpose_key: \\[2\\]"', 'result': '1 hit——`estates.edit.building_transcript` 這條路由的 meta 是 `display_property_purpose_key: [2]`（社宅），只在社宅物件顯示；一般物件走另一條路由', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -n "building_transcript" → 至少 4 hits（兩條路由各自的 name/path/component 定義），證明檔案與 grep 條件本身有效'}`

### 一般物件建物謄本要填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物）
- 講法：一般物件建物謄本要填什麼／土地標的清冊怎麼填／稅籍編號在哪填
- 給誰看：property_manager
- 一般物件（即一般住宅物件，非社會住宅物件）的建物謄本分頁要求填寫「土地標的清冊」（段、小段、地號、租賃面積、都市土地使用分區，最多3筆，供實價登錄使用）與坐落基地、稅籍編號。〔src/pages/contracts/edit/buildingTranscript/General.vue〕
- 同一分頁也要填「專有部分」「主建物」「附屬建物」的相關資料。〔src/pages/contracts/edit/buildingTranscript/General.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Estate.php | grep -nF "GENERAL_HOUSING = 1"', 'result': '1 hit：`const GENERAL_HOUSING = 1; // 一般住宅` —— property_purpose_key=1 的產品用語是「一般住宅」，不是「一般出租」', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -nF "display_property_purpose_key: [1]," → 至少 1 hit，證明「一般物件」建物謄本路由確實只對 property_purpose_key=1 顯示、grep 條件本身有效'}`
- ⚠️ 待查：一般物件建物謄本分頁（buildingTranscriptGeneral/Index.vue）是 General.vue 元件的 wrapper（傳入 showAllFields=true），社宅物件的建物謄本頁（building_transcript/Index.vue）是完全不同的獨立元件；兩條路由的 meta.label 都叫「建物謄本」，程式端看不到解釋為何欄位集合差異這麼大的說明文字，僅能確認兩者互斥（display_property_purpose_key 分別為 [1] 與 [2]）。
- ⚠️ 待查：此處「一般物件」指 property_purpose_key=1（一般住宅），不是頁面內主建物／附屬建物自己的「用途」欄位（main_building_usage／sub_building_usage，如住家用、商業用）——兩者是不同概念，寫作時避免用「用途」一詞同時指涉兩者。

### 物件附設傢俱怎麼設定？（第一個區塊標題是格局(<空間類型>)，依空間分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁）
- 講法：附設傢俱怎麼填／家電傢俱怎麼加／物件設備要怎麼設定
- 給誰看：property_manager
- 附設傢俱分頁的第一個區塊標題是「格局(<空間類型>)」（例如「格局(套房)」），依空間分區列出可設定的家電、傢俱項目，也可以自訂項目名稱與數量；住宅套房／雅房另有「戶內共用空間」區塊。〔src/pages/estates/edit/facilities/_parts/General.vue〕
- 任何項目的數量若設為0，就不會顯示在物件廣告頁上。〔src/pages/estates/edit/facilities/_parts/General.vue〕
- 需要先設定好用途、型態或格局，才能開始添加傢俱項目。〔src/pages/estates/edit/facilities/_parts/General.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/facilities/_parts/General.vue | grep -n "數量為 0 者不會顯示在物件廣告頁上"', 'result': '3 hits（第216、734、914行，一般格局／住宅套房雅房戶內共用空間／其他格局各自的傢俱區塊都各自附一次這句提示）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/facilities/_parts/General.vue | grep -n "戶內共用空間" → 2 hits，證明檔案與 grep 條件本身有效'}`

### 物件標題與照片有什麼限制？（標題最長60字、照片最多15張15MB、平面圖最多5張含PDF）
- 講法：物件標題字數限制／物件照片可以傳幾張／物件平面圖怎麼上傳／第一張照片是封面嗎
- 給誰看：property_manager
- 「物件標題」與可另外啟用的「物件公開標題」都限制最長60字。〔src/pages/estates/edit/gallery/Index.vue〕
- 物件照片最多可上傳15張、每張檔案大小上限15MB，格式支援JPG、PNG，第一張照片會被設為封面照片，每張都可以加上文字描述。〔src/pages/estates/edit/gallery/Index.vue〕
- 物件平面圖最多可上傳5張、每張檔案大小上限15MB，格式支援JPG、PNG、PDF，上傳後會出現在廣告中。〔src/pages/estates/edit/gallery/Index.vue〕

### 物件介紹要填什麼？（房源簡介、鄰近交通，可加多筆鄰近捷運站）
- 講法：物件介紹要寫什麼／房源簡介怎麼寫／物件怎麼加捷運站
- 給誰看：property_manager
- 物件介紹分頁可以填寫房源簡介與鄰近交通說明，讓客戶更了解物件細節。〔src/pages/estates/edit/intro/Index.vue〕
- 鄰近捷運站可以點「新增鄰近捷運站」加入多筆，每筆需選擇捷運線與停靠站。〔src/pages/estates/edit/intro/Index.vue〕

### 物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告）
- 講法：720VR怎麼拍／VR全景照要用什麼app／VR全景照可以用電腦編輯嗎
- 給誰看：property_manager
- 拍攝720 VR全景照之前，需要先在手機安裝「VR Maker」App，接著在物件的720 VR分頁掃描 QR Code 進行拍攝。〔src/pages/estates/edit/vr/Index.vue〕
- 拍攝完成後若要編輯全景照細節，目前不支援用手機編輯，需要使用電腦（PC）開啟。〔src/pages/estates/edit/vr/Index.vue〕
- 分頁下方有「啟用設定」，可以決定是否在招租廣告、買賣廣告中使用這組720 VR全景照。〔src/pages/estates/edit/vr/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/vr/Index.vue | grep -n "不支援以手機編輯"', 'result': "1 hit：`{{ t('目前不支援以手機編輯 VR 全景照，請使用 PC 開啟') }}`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/vr/Index.vue | grep -n "VR Maker" → 至少 1 hit，證明檔案與 grep 條件本身有效'}`

### 物件可以換綁到別的社區嗎？（畫面上目前沒有這個操作入口）
- 講法：物件換社區／物件重新綁定社區／物件搬到別的社區
- 給誰看：property_manager
- 物件基本資料的「群組/大樓名稱」欄位只是唯讀顯示目前所屬社區，畫面上目前找不到任何按鈕或連結可以把已建立的物件改綁到另一個社區。〔src/pages/estates/edit/basic/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "@click.*[Cc]ommunity"', 'result': '0 hits——`changeCommunity` 函式雖然在 setup() 裡定義（第226行）並在 return 裡曝露出去（第416行），但整份檔案找不到任何 @click 或 onClick 綁定去呼叫它，畫面上沒有觸發入口', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/basic/Index.vue | grep -n "@click=" → 至少 1 hit（例如「同詳細地址」按鈕），證明這份檔案裡其他按鈕的 @click 綁定寫法確實找得到、grep 條件本身有效'}`

### 物件基本資料可以填朝向嗎？
- 講法：物件朝向怎麼填／物件座向欄位
- 給誰看：property_manager
- 物件基本資料分頁有「朝向」欄位可以填寫。〔src/pages/estates/edit/basic/Index.vue〕

### 物件編輯有哪些分頁？（「物件資訊」與「廣告資訊」兩個群組；社宅與一般物件的建物謄本分頁互斥）
- 講法：物件編輯有哪些分頁／物件資訊跟廣告資訊差在哪／社宅物件編輯分頁跟一般物件不一樣
- 給誰看：property_manager
- 物件編輯頁分成「物件資訊」與「廣告資訊」兩個群組：「物件資訊」群組包含基本資料、標題與照片、附設傢俱、建物謄本、核實訊息、720 VR、物件介紹；「廣告資訊」群組底下再分「招租」與「買賣」兩個子群組，各自有招租詳情／刊登主資訊或買賣詳情／刊登主資訊。〔src/routes/estates.js〕
- 建物謄本分頁依用途互斥：一般物件顯示一般物件的建物謄本內容，社宅物件顯示社宅物件的建物謄本內容，兩者不會同時出現；核實訊息分頁只有一般物件才會顯示。〔src/routes/estates.js〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -nF "display_property_purpose_key: [1],"', 'result': '2 hits：estates.edit.rent_verify（核實訊息）與 estates.edit.building_transcript_general（一般物件建物謄本）都只在 property_purpose_key=1（一般物件）顯示；estates.edit.building_transcript（社宅物件建物謄本）則是 display_property_purpose_key: [2]，兩條建物謄本路由互斥', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -nF "display_property_purpose_key: [1, 2]," → 至少 1 hit，證明多數分頁（如基本資料、標題與照片）是一般與社宅都顯示、grep 條件本身有效'}`

## 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實）（8 條；頁：estates.edit.rent_detail、estates.edit.rent_contact、estates.edit.rent_verify）

### 招租押金有法定上限嗎？（一般租賃契約押金最高不得超過兩個月租金）
- 講法：押金上限幾個月／押金可以收多少／押金計算方式
- 給誰看：property_manager、prospect
- 招租詳情的押金可以選擇「每月租金」的倍數或「固定金額」做為計算基準。〔src/pages/estates/edit/rent_detail/Index.jsx〕
- 系統提示：根據中華民國內政部（租賃住宅市場發展及管理條例）規定，一般租賃契約押金額度最高不得超過兩個月租金。〔src/pages/estates/edit/rent_detail/Index.jsx〕

### 招租詳情的最短租期、最快入住日、最快點交日怎麼填？
- 講法：最短租期選項有哪些／最快入住日怎麼填／最快點交日設定
- 給誰看：property_manager
- 最短租期可以選擇1個月、3個月、6個月、1年、2年，或選「其他」自訂數字＋單位（單位只有「年」「月」兩種可選，沒有「天」）。〔src/pages/estates/edit/rent_detail/Index.jsx〕
- 最快入住日可以選「簽約後隨時入住」、「指定日期」或「其他」，最快點交日則可選「簽約後點交」、「指定日期」或「其他」。〔src/pages/estates/edit/rent_detail/Index.jsx〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_detail/Index.jsx | grep -n "option value="', 'result': '只查得到 `<option value=\\"year\\">` 與 `<option value=\\"month\\">` 兩個選項，沒有 day/天的 option', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_detail/Index.jsx | grep -nF "t(\'年\')" → 1 hit，證明「年」選項確實存在、grep 條件本身有效'}`

### 招租條件要求可以設定什麼？（身份限制複選、養寵物可否、開伙可否、生活公約）
- 講法：招租可以限制什麼身份／可以養寵物嗎怎麼設定／招租能不能開伙
- 給誰看：property_manager
- 招租詳情的「條件要求」可以複選身份限制，選項包含學生、上班族、家庭、男性、女性。〔src/pages/estates/edit/rent_detail/Index.jsx〕
- 也可以個別設定「養寵物」與「開伙」是否可以，並在「補充」欄位填寫生活公約等額外說明。〔src/pages/estates/edit/rent_detail/Index.jsx〕

### 刊登主資訊的團隊資訊要在哪裡修改？（法人／社宅房東顯示公司資訊、到團隊資訊修改；個人房東顯示經理人資訊、到帳號資訊修改）
- 講法：經紀人證號在哪改／登記證號怎麼設定／刊登主資訊看不到經紀人資料
- 給誰看：property_manager
- 當登入身分是法人房東或社宅房東時，「刊登主資訊」會顯示團隊的公司名稱、公司電話、公司Email等公司資訊，並提示需要修改要前往「團隊資訊」頁面。〔src/pages/estates/edit/rent_contact/Index.vue〕
- 當登入身分是個人房東時（非法人、非社宅），「刊登主資訊」顯示的是經理人的姓名、電話、Email，並提示需要修改要前往「帳號資訊」頁面，不是團隊資訊。〔src/pages/estates/edit/rent_contact/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -n "isCompany"', 'result': '3 hits：isCompany 定義為 `[3, 4].includes(config_rule_key)`（法人房東=3、社宅房東=4 都算 isCompany），第76行 `v-if="state.isCompany"` 包住公司資訊區塊，第329行 `v-if="!state.isCompany"` 包住個人房東（經理人）資訊區塊——兩者互斥、不會同時出現', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -n "刊登主資訊" → 2 hits（法人／個人房東各自的區塊標題），證明兩個區塊都真的存在'}`

### 招租廣告可以隱藏經理人／房東的名稱、電話、Email嗎？（勾選框在「經理人資訊」或「刊登主資訊」的經理人卡片上，每種身分只有一組）
- 講法：招租廣告可以不顯示電話嗎／怎麼隱藏經理人名稱／廣告上隱藏Email
- 給誰看：property_manager、prospect
- 「經理人」與「廣告顯示經理人」兩個必填選擇欄位，只出現在法人房東與社宅房東的「經理人資訊」區塊，不是「刊登主資訊」區塊；個人房東畫面上沒有這兩個選擇欄位。〔src/pages/estates/edit/rent_contact/Index.vue〕
- 法人／社宅房東的「經理人資訊」區塊裡，廣告顯示經理人的卡片上有「在廣告上隱藏名稱」「在廣告上隱藏聯絡電話」「在廣告上隱藏Email」三個勾選框；個人房東畫面上，這三個勾選框則出現在「刊登主資訊」的經理人卡片上——兩種身分都只有這一組三個勾選框，不會重複出現。〔src/pages/estates/edit/rent_contact/Index.vue〕
- 填完刊登主資訊後，下一步會進入「預覽招租廣告」。〔src/pages/estates/edit/rent_contact/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -nF "經理人資訊"', 'result': '1 hit（第182行），只出現在 `v-if="state.isCompany"`（法人／社宅房東）分支裡；「刊登主資訊」標題則在兩個分支各出現一次（法人／社宅房東分支第79行、個人房東分支第332行），「經理人」「廣告顯示經理人」兩個 VueSelect 都寫在第182行之後、同一個 isCompany 區塊內', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -nF "刊登主資訊" → 2 hits，證明兩個身分分支各自都有「刊登主資訊」標題、grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -nF "在廣告上隱藏名稱"', 'result': '2 hits：第295行（法人／社宅房東分支，廣告顯示經理人卡片下方）、第369行（個人房東分支，刊登主資訊卡片下方）——整份檔案總共只有這兩處，證明每種身分各自只有一組三個勾選框，不是同一分支裡各自獨立出現兩組', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/edit/rent_contact/Index.vue | grep -nF "isCompany" → 3 hits，證明兩個分支的判斷式確實存在、grep 條件本身有效'}`

### 招租的核實訊息是什麼？（依租賃住宅市場發展條例核實產權登記與違建面積）
- 講法：核實訊息要填什麼／產權登記已辦理未辦理是什麼意思／違建面積要填嗎
- 給誰看：property_manager、prospect
- 核實訊息要求勾選「產權登記」是「已辦理」（租賃標的在地政機關有產權登記）還是「未辦理」（租賃標的在地政機關無產權登記）。〔src/pages/estates/edit/rent_verify/Index.vue〕
- 內政部依照《住宅租賃市場發展條例》要求廣告內容應與事實相符，因此還要填寫租賃標的法定用途，以及未登記之改建、增建、加建、違建部分（分壹樓、所在樓層、頂樓、其他處所各自的面積）。〔src/pages/estates/edit/rent_verify/Index.vue〕

### 為什麼物件刊登不出去？（需要刊登物件或新增物件的權限；必填欄位沒填完會退回編輯頁）
- 講法：物件刊登不出去／刊登物件失敗原因／刊登物件需要什麼權限
- 給誰看：property_manager
- 執行「刊登物件」的使用者，必須對這個物件有刊登物件或新增物件其中一種權限，否則系統會擋下並提示「您無法刊登此物件」。〔app/Http/Controllers/EstateController.php〕
- 如果物件還有必填欄位沒有填完整，系統會擋下這次刊登，自動導回物件編輯頁，並且把左側選單直接跳到缺欄位的那個分頁，提示需要補齊的錯誤訊息。〔app/Http/Controllers/EstateController.php〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -n "您無法刊登此物件"', 'result': "2 hits（第10347、10411行，分別是刊登物件與另一處相同的權限擋下邏輯）：`if (!\\$publicEstate && !\\$addEstate) { return redirect()->route('estates.index')->with(['status-error' => ___('您無法刊登此物件')]); }`", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "public function open" → 1 hit，證明 open() 這個刊登動作的函式本身確實存在、grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "validateFields()"', 'result': "2 hits（第5751、10360行），第10360行就在 open() 函式內：`if (($validateFields = $estate->validateFields()) && isset($validateFields['status']) && !$validateFields['status']) { return redirect()->route('estates.edit', ...)->with(['premisesStep' => [...]]) }`，帶著 stepCurrent／stepCurrentSub 讓前端自動跳到缺欄位分頁", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -n "errorFields" → 至少 1 hit，證明錯誤欄位回傳機制確實存在、grep 條件本身有效'}`

### 招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金、營業稅：應稅／零稅率／免稅）
- 講法：招租租金要填幣別嗎／營業稅怎麼選／招租面積怎麼填
- 給誰看：property_manager
- 招租詳情要填「面積」（可勾選「同建物謄本面積」直接帶入）、「幣別」與「每月租金」，這三個都是必填欄位。〔src/pages/estates/edit/rent_detail/Index.jsx〕
- 營業稅可以選擇「應稅」「零稅率」或「免稅」三種。〔src/pages/estates/edit/rent_detail/Index.jsx〕

## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現）（9 條；頁：estates.dashboard、estates.dashboard.rent、estates.dashboard.contracts、estates.dashboard.bills、estates.dashboard.repair、estates.dashboard.attachments、estates.dashboard.runnings、estates.dashboard.contractAttachments、estates.dashboard.memos、estates.dashboard.monthlyReport、estates.dashboard.monthlyStatement、estates.monthlyUpload）

### 物件儀表板進去預設是哪個分頁？（預設招租表現；大房東看不到「限管理者查看」分頁群組）
- 講法：物件儀表板預設看哪頁／大房東能看物件儀表板哪些分頁／物件Dashboard入口
- 給誰看：property_manager
- 進入物件儀表板預設會導向「招租表現」分頁。〔src/routes/estates.js〕
- 分頁分成兩組：「限管理者查看」（招租表現、銷售表現）與「與大房東共享」（合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本；每月報表、每月對帳單只在團隊被歸類為特定合作團隊時才會加入這一組）。〔src/routes/estates.js〕
- 當使用者身分是大房東時，畫面不會顯示「限管理者查看」這組分頁，只能看到「與大房東共享」的分頁內容。〔src/pages/estates/dashboard/_parts/TabNav.vue〕
- 社宅房東看不到「合約附件」這個分頁，其餘身分都看得到。〔src/routes/estates.js〕
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/_parts/TabNav.vue | grep -n "isBigLandlord"', 'result': '2 hits（第248、326行），都是 `v-if="!dashboardStore.state?.isBigLandlord"` 包住「限管理者查看」這組分頁按鈕的渲染，isBigLandlord 為 true 時整組不渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/_parts/TabNav.vue | grep -n "tabWithGroup" → 至少 1 hit，證明分頁分組機制本身確實存在、grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 3, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/_parts/TabNav.vue | grep -n "hideConfigRuleKey"', 'result': '1 hit——`(store.state.userData.role.config_rule_key != node.meta?.hideConfigRuleKey)` 這條判斷式套用在 estates.js 裡每個分頁的 meta 上，合約附件的 meta 是 `hideConfigRuleKey: [4]`，故 config_rule_key===4 時該分頁被濾掉', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/routes/estates.js | grep -n "label: \'合約附件\'" → 1 hit，證明合約附件分頁本身確實存在於路由表'}`

### 招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要）
- 講法：招租表現看什麼／物件空置天數在哪看／廣告瀏覽次數在哪查
- 給誰看：property_manager
- 招租表現分頁會顯示物件的空置天數圖表（出租天數與空置天數）、廣告瀏覽次數與平均頁面瀏覽次數。〔src/pages/estates/dashboard/rent/Index.vue〕
- 同一頁還會摘要顯示帳務表現（總收入、總支出、總結餘）、合約歷程摘要（只會顯示執行中與歷史合約）與修繕紀錄摘要，都可以點「更多」看完整內容。〔src/pages/estates/dashboard/rent/Index.vue〕

### 物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期）
- 講法：合約歷程有哪些欄位／物件歷史合約在哪看／合約歷程每頁筆數
- 給誰看：property_manager
- 一般房東登入時，合約歷程列表欄位是狀態、簽約類型、物件、承租人（租客身分登入時這一欄標題會改成「出租人」，且不顯示「是否通知」欄）、租期、是否通知；社宅房東登入時，欄位改成只有合約名稱、承租人、租期三欄。〔src/pages/estates/dashboard/contracts/Index.vue〕
- 列表每頁可切換顯示30、60或90項。〔src/pages/estates/dashboard/contracts/Index.vue〕

### 物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表）
- 講法：帳務收支子頁籤／物件統計報表在哪看／物件總收支怎麼看
- 給誰看：property_manager
- 物件儀表板的「帳務收支」分頁下方分成「總收支」與「統計報表」兩個子頁籤。〔src/routes/estates.js〕

### 物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態）
- 講法：修繕紀錄狀態有哪些／修繕紀錄欄位／物件修繕在哪看結算金額
- 給誰看：property_manager
- 修繕紀錄可依「申請修繕」「安排修繕」「完成修繕」「結單」四種狀態篩選。〔src/pages/estates/dashboard/repair/Index.vue〕
- 列表欄位包含報修日期、最後更新、分類＆項目、物件地址、結算金額、房東/管理者、租客。〔src/pages/estates/dashboard/repair/Index.vue〕
- ⚠️ 待查：路由與分頁選單上的標籤是「修繕紀錄」（src/routes/estates.js: label: '修繕紀錄'），但頁面自己的大標題用的是「修繕記錄」（src/pages/estates/dashboard/repair/Index.vue: t('修繕記錄')），兩個字不一致，本大綱統一採用選單上的「修繕紀錄」，但無法判斷哪一個才是刻意的正式名稱。

### 「附件清單」跟「合約附件」差在哪？（附件清單自由上傳、有儲存空間上限，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是租賃法定文件的固定清單）
- 講法：合約附件要傳什麼文件／附件清單空間不夠怎麼辦／物件附件跟合約附件差別
- 給誰看：property_manager
- 「附件清單」可自由上傳任意檔案，總儲存空間有上限（顯示已用/總量），檔案數量與大小都有限制，空間不足時可以「加價購」；下載檔案不限身分都能做，但只有代理人且擁有新增物件權限的使用者才會看到「刪除檔案」的操作。〔src/pages/estates/dashboard/attachments/Index.vue〕
- 「合約附件」則是固定的租賃法定文件清單，包含授權代理人簽約同意書、建物所有權/有權出租之證明文件、使用執照影本、出租方同意轉租確認書、房屋位置格局示意圖、社區管理規約與住戶生活規約、其他（附註條款、稅籍證明等），以及出租方身份證明文件影本，圖片僅支援JPG、PNG，檔案大小最大10MB，每個項目的上傳數量限制不同。〔src/pages/estates/dashboard/contractAttachments/index.vue〕
- 上傳附件到「附件清單」，具備編輯物件權限、是團隊擁有者，或是代理人且擁有新增物件權限，符合其中一種身分即可。〔src/pages/estates/dashboard/attachments/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/attachments/Index.vue | grep -n "download"', 'result': '2 hits（第348、371行，桌機圖示與手機下拉選單各一個下載連結），皆使用瀏覽器原生 download 屬性、沒有任何 v-if 權限判斷；同一份檔案裡 `isAgent && store.state.userData?.permission?.add_estate` 這個判斷式出現3次（第34行用於控制上傳按鈕，第353、376行分別包住桌機／手機的刪除操作）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/attachments/Index.vue | grep -nF "isAgent && store.state.userData?.permission?.add_estate" → 3 hits，證明刪除操作確實被權限判斷包住、grep 條件本身有效'}`

### 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入/支出金額，記事本只是純文字備註）
- 講法：流水帳怎麼記／物件記事本可以記什麼／流水帳跟記事本差別
- 給誰看：property_manager
- 「房東流水帳」的每筆紀錄要填時間、說明、對象、類別（收入或支出）、費用，也可以附加附件。〔src/pages/estates/dashboard/runnings/Index.vue〕
- 「物件記事本」的每筆紀錄只需要填時間、說明、對象與附件，沒有收入支出的金額欄位。〔src/pages/estates/dashboard/memos/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/memos/Index.vue | grep -n "金額"', 'result': '0 hits——物件記事本頁面完全沒有出現「金額」二字，沒有收入支出欄位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/estates/dashboard/memos/Index.vue | grep -n "說明" → 1 hit，證明檔案與 grep 條件本身有效'}`

### 每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔）
- 講法：每月報表怎麼上傳／每月對帳單格式限制／同一個月上傳兩次報表會怎樣／怎麼批次上傳報表
- 給誰看：property_manager
- 上傳每月報表或每月對帳單僅能上傳 PDF 檔案，檔案大小限制10MB，需要選擇年份、月份與指定物件（可一次指定多個物件批次上傳）。〔src/pages/estates/dashboard/_parts/MonthlyUpload.jsx〕
- 若該月份已經有上傳過的檔案，重新上傳會直接覆蓋舊檔案。〔src/pages/estates/dashboard/_parts/MonthlyUpload.jsx〕
- 每月報表／每月對帳單這兩個分頁只在團隊被歸類為特定合作團隊時才會出現在「與大房東共享」分頁群組裡，上傳完成後其他團隊成員與大房東就能在這裡下載。〔src/routes/estates.js〕

### 物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限）
- 講法：物件儀表板上面卡片是什麼／儀表板編輯捷徑不見了／儀表板可以直接編輯招租廣告嗎
- 給誰看：property_manager
- 物件儀表板最上方固定顯示三張卡片：物件基本資訊（縮圖、名稱、地址）、招租廣告（狀態、預覽連結）、買賣廣告（狀態、預覽連結）。〔src/pages/estates/dashboard/_parts/TabNav.vue〕
- 招租廣告卡與買賣廣告卡右上角各自的編輯捷徑（鉛筆圖示），只有當登入身分是代理人，且擁有新增物件的權限時才會顯示。〔src/pages/estates/dashboard/_parts/TabNav.vue〕

## 單一物件廣告頁（招租）（8 條；頁：web:estates.house、web:estates.show）

### 物件還沒刊登（未開放）時，廣告頁會怎麼顯示？（屋主看到的是預覽頁提示；其他人造訪會得到404）
- 講法：物件沒刊登廣告頁還看得到嗎／物件廣告預覽頁／還沒刊登的物件連結有效嗎
- 給誰看：property_manager、prospect
- 當物件尚未刊登（未開放）時，物件的擁有者若打開廣告頁連結，畫面上方會顯示提示：「這是您的物件廣告預覽頁，此物件尚未完成刊登。」〔resources/views/estate/show.blade.php〕
- 當物件未刊登（未開放）、且目前造訪者沒有查看該物件的權限（包含未登入的訪客與搜尋引擎爬蟲）時，系統會回傳 404，讓 Google 等搜尋引擎重新爬取後把頁面從索引中移除，避免物件聯絡資訊繼續留在搜尋結果裡。〔app/Http/Controllers/EstateController.php〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "下架物件對所有人（含搜尋引擎爬蟲）一致回 404"', 'result': '2 hits（show()、house() 兩個函式各自的權限檢查前各有一次同樣的註解），緊接著都是 `abort(404);`', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "abort(404)" → 至少 1 hit，證明檔案與 grep 條件本身有效'}`

### 簽約邀請連結會失效嗎？（連結會顯示倒數，過期後失效）
- 講法：簽約邀請連結會過期嗎／合約邀請連結有時效嗎／邀請連結多久失效
- 給誰看：property_manager、prospect
- 租客透過邀請連結打開物件廣告頁時，頁面上方會顯示「以下是來自［房東］的簽約邀請，本連結會於［剩餘時間］後失效，請把握時間完成簽約！」的提示。〔resources/views/estate/show.blade.php〕

### 物件廣告頁顯示哪些內容？（照片／VR全景切換、設備與設施、交通與環境設施、溫馨提醒）
- 講法：物件廣告頁有哪些內容／物件廣告頁看不看得到VR／物件廣告頁會顯示鄰近捷運站嗎
- 給誰看：property_manager、prospect
- 如果物件有設定720 VR全景照，廣告頁的相簿區可以在「照片」與「VR全景」之間切換。〔resources/views/estate/show.blade.php〕
- 廣告頁的「設備與設施」標題本身一定會顯示（不管物件實際登記的設備數量是多少），但底下實際列出的設備／傢俱項目只在該分區加總數量大於0或有自訂項目時才會顯示。〔resources/views/estate/show.blade.php〕
- 廣告頁也會顯示「交通與環境設施」（地址、鄰近捷運站等）以及「溫馨提醒」區塊，內含本物件的 JGB 編號與房屋現況、法定用途的提醒文字。〔resources/views/estate/show.blade.php〕

### 物件廣告頁「聯絡房東」區塊顯示什麼？（房東電話／Email依隱藏設定決定是否顯示；公司廣告電話／Email不受隱藏設定影響）
- 講法：物件廣告頁聯絡房東怎麼看／隱藏電話設定有效嗎／廣告頁可以加房東Line嗎
- 給誰看：property_manager、prospect
- 物件廣告頁的「聯絡房東」區塊，只有在物件沒有設定隱藏電話、隱藏Email時，才會顯示房東本人（或主要經理人）的電話與Email。〔resources/views/estate/show.blade.php〕
- 如果房東是法人（公司），區塊改顯示公司的廣告電話與廣告Email，這兩個欄位不受「隱藏電話」「隱藏Email」設定影響，只要公司有填就一定會顯示。〔resources/views/estate/show.blade.php〕
- Line 聯絡方式（含一鍵複製 Line ID）只有在房東有填寫 Line 時才會顯示；WhatsApp 聯絡方式同樣只有在房東有填寫時才會顯示。Facebook 也只有在房東有填寫連結時才會顯示「立即聯繫」按鈕，沒有填寫時這三種聯絡方式都不會出現。〔resources/views/estate/show.blade.php〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "hide_phone"', 'result': "至少 3 hits，其中第1206、1408行是 `@if (empty($estate->hide_phone) && !empty($landlordInfo['phone']))`，證明房東本人電話確實被 hide_phone 這個旗標控制", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "聯絡房東" → 2 hits，證明「聯絡房東」區塊標題本身確實存在、grep 條件本身有效'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "advertising_company_phone"', 'result': '2 hits，兩處都只用 `!empty(...)` 判斷、完全沒有搭配 hide_phone／hide_email 的檢查，跟房東本人電話（@if 同時檢查 empty($estate->hide_phone) 那組）寫法明顯不同', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "hide_phone" → 至少 3 hits，證明 hide_phone 這個判斷確實存在於同一份檔案、只是沒有套用到公司電話那段'}`
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "尚未提供"', 'result': '3 hits（第1249、1433行是 facebook 區塊的死碼，第1276行是 whats_app 區塊同樣寫法的死碼）：三元運算式的 false 分支（尚未提供）都被包在對應的 `@if (!empty(...))` 裡面，外層 @if 已保證非空，false 分支永遠不會被執行到，是死碼', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "立即聯繫" → 至少 2 hits，證明「立即聯繫」文案本身真實存在、只是「尚未提供」那一半是死碼'}`
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -nF "!empty(\\$premisesContact[\'line\'])"', 'result': '2 hits：第1253行在「資料卡片_舊」死區塊（1356–1536行）之前，是活碼；第1437行落在該死區塊內，是死碼。Line 一鍵複製 Line ID 整段都包在第1253行這個活碼 @if 裡面，房東沒填 Line 時整段不會渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -nF "whats_app" → 至少 2 hits，證明 WhatsApp 聯絡方式本身確實存在於同一個聯絡區塊、grep 條件本身有效'}`

### 物件廣告頁的網址會自動轉換嗎？（刊登中時，內部編號網址會自動轉址到 JGB 編號公開網址）
- 講法：物件廣告頁網址是什麼／物件連結會自動跳轉嗎／物件廣告頁網址為什麼變了
- 給誰看：property_manager
- 物件如果目前是刊登中（公開狀態），透過內部編號網址造訪、且網址沒有帶合約或邀請參數時，系統會自動轉址到 JGB 編號的公開廣告網址。〔app/Http/Controllers/EstateController.php〕
- 如果網址帶的合約是續約合約，系統會直接導向該合約的合約檢視頁，不會顯示物件廣告頁。〔app/Http/Controllers/EstateController.php〕
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "return redirect()->route(\'contracts.show\', array_merge("', 'result': "1 hit：`return redirect()->route('contracts.show', array_merge(['id' => $contract->id], $rType));` —— 續約合約會被導向 contracts.show（合約檢視頁），不是簽名頁面", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/EstateController.php | grep -nF "如果該合約為續約合約" → 1 hit，證明這段續約合約重導向邏輯確實存在、grep 條件本身有效'}`
- ⚠️ 待查：程式裡該段的註解寫「則直接導向到簽名頁面」，但實際 redirect 目標是 route('contracts.show')（合約檢視頁），註解文字與程式行為不一致，本條依程式行為書寫。

### 物件廣告頁有費用明細表嗎？（車位物件不顯示，其餘物件顯示生活費用表）
- 講法：物件廣告頁費用怎麼看／物件廣告頁有清潔費水電費嗎／車位物件有費用表嗎
- 給誰看：property_manager、prospect
- 物件廣告頁在物件不是車位用途時，會顯示一個生活費用表，列出各項費用與金額；車位用途的物件不會顯示這個費用表。〔resources/views/estate/show.blade.php〕
- 否定查證：`{'sentence_index': 0, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "fees-table"', 'result': "2 hits（開始與結束標籤 `<fees-table ...></fees-table>`），且整段包在 `@if ($premisesInfoBasic['premises_use_for'] !== 'parking_space')` … `@endif` 裡面", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/estate/show.blade.php | grep -n "parking_space" → 至少 1 hit，證明車位用途判斷條件確實存在、grep 條件本身有效'}`

### 物件廣告頁有預約入住的按鈕嗎？（一般訪客看到「立即預約入住」，受邀簽約者看到「查看合約」）
- 講法：物件廣告頁怎麼預約看房／立即預約入住按鈕在哪／受邀簽約的人看到什麼按鈕
- 給誰看：property_manager、prospect
- 物件廣告頁的桌機版與手機版下方都固定顯示一顆按鈕：一般訪客看到的是「立即預約入住」，點擊會開啟預約入住的燈箱。〔resources/views/estate/show.blade.php〕
- 如果目前造訪者是被邀請簽約的對象，同一個位置的按鈕會改成「查看合約」，點擊直接前往該合約的簽署頁面，不會顯示預約入住的燈箱。〔resources/views/estate/show.blade.php〕

### 物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖）
- 講法：物件廣告頁資料卡片有什麼／物件廣告頁看不看得到含哪些費用／物件廣告頁格局在哪看
- 給誰看：property_manager、prospect
- 物件廣告頁的資料卡片一定會顯示地址；社區名稱有值時才會額外顯示社區名稱。〔src/pages/estates/show/_parts/EstateBasicInfo.vue〕
- 租金金額有值時，卡片才會顯示「[金額] 元/月」；若該物件有設定「租金已包含」的費用項目，還會在下方加註「(含〈項目〉)」的說明。〔src/pages/estates/show/_parts/EstateBasicInfo.vue〕
- 用途不是商用時（住宅或車位），建築類型欄位在住宅用途顯示「建築類型與樓層」，在車位用途則退化為只顯示「建築類型」；格局欄位在住宅用途顯示房型格局，在車位用途則固定顯示「車位」二字。〔src/pages/estates/show/_parts/EstateBasicInfo.vue〕
- 用途是商用時，卡片改顯示「空間類型」；「座位數」欄位只有在用途是商用、且空間類型不是店面、也不是整層空間時才會顯示。〔src/pages/estates/show/_parts/EstateBasicInfo.vue〕
- 不論哪種用途，卡片最下方都一定會顯示「面積」；有上傳物件平面圖時，還會額外顯示「物件平面圖」的縮圖列。〔src/pages/estates/show/_parts/EstateBasicInfo.vue〕

## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選）⇄ 由 A 移入（5 條；頁：users.public、web:share）

### 房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）
- 講法：招租店舖是什麼／房東對外首頁怎麼用／怎麼進去我的招租店舖
- 給誰看：property_manager、prospect
- 「房東對外首頁」（招租店舖）是房東對外宣傳用的頁面，除了房東聯絡資訊與基本介紹外，也會公開展示房東旗下所有分類為「刊登中」的物件，方便隨時分享給有興趣的潛在租客。〔幫助中心:slug90_zh-Hant.html〕
- 登入 JGB 後，點選側邊選單左上角大頭照上的藍色房子 Icon，就能連結到專屬的「房東對外首頁」。〔幫助中心:slug90_zh-Hant.html〕

### 招租店舖上可以直接編輯哪些內容？（封面照片、大頭照、姓名、自我介紹，會連動帳號資訊）
- 講法：招租店舖封面照片怎麼換／改自我介紹會同步嗎／招租店舖大頭照怎麼設
- 給誰看：property_manager
- 在招租店舖頁面可以即時編輯「封面照片」「大頭照」「姓名」「自我介紹」，相關修改會連動變更到「會員中心＞帳號資訊」內。〔幫助中心:slug90_zh-Hant.html〕
- 更換封面照片時，畫面會建議尺寸為 1920 x 576。〔src/pages/users/public/Index.vue〕

### 招租店舖怎麼篩選物件？（鄉鎮區或捷運、類型與格局，可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30）
- 講法：招租店舖怎麼篩選物件／招租店舖顯示模式／招租店舖每頁顯示幾筆
- 給誰看：property_manager
- 招租店舖提供「鄉鎮/區或捷運」與「類型與格局」兩組篩選條件。〔src/pages/users/public/Index.vue〕
- 物件列表可以切換「小圖示」「大圖示」「條列式」三種顯示模式；招租店舖的每頁筆數可選30、60或90項（預設30項），只有多團隊招募頁才提供10、30、60或90項（預設10項）。〔src/pages/users/public/Index.vue〕
- 沒有符合篩選條件的結果時，會顯示「沒有符合的結果」並建議調整篩選條件。〔src/pages/users/public/Index.vue〕
- 否定查證：`{'sentence_index': 2, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/users/public/Index.vue | grep -n "沒有符合的結果"', 'result': '1 hit：`<h3 class=\\"font-700\\">{ t(\'沒有符合的結果\') }</h3>`', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/users/public/Index.vue | grep -n "小圖示" → 1 hit，證明檔案與 grep 條件本身有效'}`

### 招租店舖怎麼分享？（可分享至FB、Line、LinkedIn，加入團隊且設定客製帳號可有專屬短網址）
- 講法：招租店舖怎麼分享／招租店舖有沒有短網址／怎麼分享招租店舖到Line
- 給誰看：property_manager、prospect
- 招租店舖左側選單提供快捷鍵，可以快速分享此頁面至 FB、Line 或 LinkedIn，也可以複製連結。〔幫助中心:slug90_zh-Hant.html〕
- 如果房東所屬團隊有設定客製短網址，分享出去的網址會是該客製短網址；否則會用系統自動產生的一組固定網址代替。〔app/Http/Controllers/IndexController.php〕

### 多團隊招募頁是什麼？（沒有指定住宅或商用時自動轉址到住宅、強制只顯示招租、不顯示社區篩選、每頁預設10筆）
- 講法：多團隊招募頁是什麼／招募頁跟一般店舖的網址不一樣嗎／招募頁跟招租店舖差在哪
- 給誰看：property_manager、prospect
- 多團隊招募頁如果網址沒有帶物件用途，會自動轉址並補上「住宅」用途。〔src/routes/users.js〕
- 多團隊招募頁固定只顯示招租物件，且不會載入社區篩選模組，這兩點都跟一般招租店舖不同。〔src/pages/users/public/Index.vue〕
