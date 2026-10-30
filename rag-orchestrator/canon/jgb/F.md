---
coarse: F
title: 修繕
scope: 報修、派工、進度與狀態、修繕通知；⛔ 費用入帳歸 E
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） {#F-repair-list}
### 修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存） {#jgb/F/repair-status-tabs}
- phrasings:
  - {text: "修繕單有幾個狀態", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單分頁有哪些", source: "draft:outline-20260920", status: approved}
  - {text: "修繕進度分幾個階段", source: "draft:outline-20260920", status: approved}
  - {text: "修繕總表怎麼分類", source: "draft:outline-20260920", status: approved}
- sources: [code:src/routes/repairs.js, code:src/pages/repair/Index.vue, code:app/Repair.php, code:routes/web.php, help:repair_zh-Hant.html]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
修繕單總表分成五個狀態分頁：申請修繕、安排修繕、完成修繕、結單、封存，每張修繕單同一時間只會出現在其中一個分頁。
幫助中心的修繕教學把處理流程依序分成新增修繕單、安排修繕、完成修繕、結單；「封存」則是另一個可以把修繕單移過去、也可以再移回其他狀態的分頁。
進入畫面後不需要自己選分頁，系統會直接停在「申請修繕」這個分頁。
修繕單總表這個頁面本身要先登入 JGB 帳號才能打開；但同樣屬於修繕功能的分享頁，並不受這條規則限制（另見「看修繕單分享頁需要先登入嗎」）。
### 修繕單總表可以怎麼搜尋或篩選？（案名／地址／經理人／租客關鍵字，加上單一組「修繕單時間段」下拉：報修時間起訖／最後更新時間起訖／7 日內申請報修三選一，還有分類／項目／是否緊急） {#jgb/F/repair-list-search-filter}
- phrasings:
  - {text: "修繕單怎麼搜尋", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單列表篩選條件", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼找特定物件的修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單可以用日期篩選嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單篩選條件怎麼重設", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:src/components/Lightbox/RepairAdvSearch.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
關鍵字搜尋可以指定用案名、地址、經理人或租客其中一種欄位去比對，如果不特別切換，預設是用案名去比對。
進階搜尋裡有一個「修繕單時間段」下拉選單，三個選項是「報修時間起訖」「最後更新時間起訖」「7 日內申請報修」，三選一，不是兩組各自獨立的日期區間。
切換這個下拉選單的選項時，另一種時間篩選會被清空，例如選了「最後更新時間起訖」，原本填的「報修時間起訖」就會被重設成空白，反之亦然。
進階搜尋視窗最下面有「重設條件」，點下去會把整個搜尋表單（關鍵字、時間段、分類、項目、是否緊急）都清回預設值。
### 修繕單總表的表格欄位顯示什麼？（物件地址、分類＆項目、報修日期、最後更新、結算金額、房東/管理者、租客） {#jgb/F/repair-list-columns}
- phrasings:
  - {text: "修繕單列表欄位說明", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單表格看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單總表欄位", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:app/Http/Controllers/RepairController.php, code:app/Repair.php, code:src/components/SurelyVue/Common/SingleUserCell.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
每一列會顯示物件地址、分類＆項目、報修日期、「最後更新」、結算金額、房東/管理者、租客這幾個欄位。
「房東/管理者」這欄顯示的是被指派負責這張修繕單的房東方帳號；「租客」這欄顯示的是這張修繕單本身記錄到的租客資料，系統不會另外去查這個物件目前實際的承租人是誰來補上，所以這張修繕單沒有記錄到租客資料時，這欄就是空的（只顯示「-」）。
如果這個分類目前尚未累積任何修繕單，表格會顯示「此分類目前尚未有修繕單」的提示文字，而不是報錯畫面。
### 修繕單總表怎麼排序、一頁看幾筆？（每頁 30／60／90 筆可選；排序選項裡的「結算金額」只有房東方帳號才看得到） {#jgb/F/repair-list-sort-and-pagination}
- phrasings:
  - {text: "修繕單一頁顯示幾筆", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單可以怎麼排序", source: "draft:outline-20260920", status: approved}
  - {text: "租客可以用金額排序修繕單嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
修繕單總表可以選擇每頁顯示 30、60 或 90 筆，沒有特別選擇的話預設是 30 筆。
排序選單裡有報修日期、最後更新時間、結算金額、分類、案名、租客這幾種排序方式，各自可以選由新到舊或由舊到新（或由大到小、由小到大）。
身分不是房東的帳號，排序選單裡不會出現「結算金額由大到小」跟「結算金額由小到大」這兩個選項。
### 「新增修繕單」按鈕誰看得到？（租客一定有；房東方要有「新增&編輯&刪除所屬」或「新增&編輯&刪除所有」修繕資料其中一項權限） {#jgb/F/repair-create-button-visibility}
- phrasings:
  - {text: "新增修繕單按鈕在哪", source: "draft:outline-20260920", status: approved}
  - {text: "誰可以新增修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼看不到新增修繕單按鈕", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:app/Http/Controllers/UserController.php, code:src/pages/estates/pick/_parts/pick.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客帳號登入都看得到「新增修繕單」按鈕。
房東方帳號要另外有「新增&編輯&刪除所屬修繕資料」或「新增&編輯&刪除所有修繕資料」其中一項權限，才會看到這顆按鈕。
點下去之後會先進入選擇物件的畫面，選好物件才能繼續填報修細節。
### 「結算總金額」是什麼？（只有房東方帳號登入時才會顯示；這個數字只加總目前這一頁看得到的修繕單，換頁或換每頁筆數就會不一樣） {#jgb/F/repair-total-visibility}
- phrasings:
  - {text: "修繕單結算總金額", source: "draft:outline-20260920", status: approved}
  - {text: "誰看得到修繕總金額", source: "draft:outline-20260920", status: approved}
  - {text: "結算總金額是全部加起來的嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「結算總金額：」這一行只有房東方帳號登入時才會顯示，租客帳號看不到。
這裡顯示的結算總金額，只是目前這一頁看得到的修繕單金額加總，不是這個分類篩選條件下全部修繕單的總和；換到下一頁或改每頁顯示筆數，這個數字就會跟著變。
### 誰能匯出修繕單？（要另外有匯出修繕資料的權限；而且這顆按鈕只有在「新增修繕單」按鈕會出現的身分底下才會一起出現，單獨有匯出權限而沒有編輯權限的房東方帳號看不到它） {#jgb/F/repair-export-visibility}
- phrasings:
  - {text: "怎麼匯出修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單可以匯出嗎", source: "draft:outline-20260920", status: approved}
  - {text: "有匯出權限但看不到匯出按鈕", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「匯出修繕單」這顆按鈕要另外有「匯出修繕資料」的權限才會出現。
這顆按鈕在畫面結構上是包在「新增修繕單」按鈕同一個區塊裡：只有身分是租客、或房東方帳號同時具備新增／編輯修繕權限時，這個區塊才會出現；房東方帳號如果只有匯出權限、沒有新增或編輯修繕的權限，就算有匯出權限也看不到「匯出修繕單」按鈕。
如果目前這個分類篩選條件下完全沒有修繕單，這顆「匯出修繕單」按鈕會變成無法點擊的灰階狀態。
### 修繕單總表怎麼切換狀態？（每列右邊的齒輪選單有「移至」各個狀態的選項，封存後仍然可以再移回其他狀態） {#jgb/F/repair-move-status-from-list}
- phrasings:
  - {text: "修繕單怎麼換分頁", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼把修繕單移到結單", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單狀態怎麼改", source: "draft:outline-20260920", status: approved}
  - {text: "封存的修繕單可以移回來嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
每一列右邊有一個齒輪選單，點開後會列出「移至『申請修繕』」「移至『安排修繕』」「移至『完成修繕』」「移至『結單』」「移至『封存』」這幾個選項（目前所在的那個狀態不會出現在清單裡）。
移動選單只給對這個物件有編輯修繕權限的房東方帳號使用；租客的齒輪選單沒有移動選項，只有一個查看／編輯用的按鈕。
封存不是最後不能回頭的狀態，被封存的修繕單一樣可以透過這個選單再移回申請修繕、安排修繕、完成修繕或結單；「結單」分頁的修繕單同樣可以再移回其他狀態，兩者在能不能移動這件事上沒有差別。
移動狀態成功之後，畫面上會跳出成功提示，並且直接把使用者帶到剛剛選擇的目標狀態分頁。
### 哪些身分會看到「查看」而不是「編輯＆查看」的齒輪按鈕文字？（大房東角色，以及對這張單只有「顯示所屬」、沒有「顯示所有」修繕資料權限的團隊成員；但這張單的經理人本人看到的仍是「編輯＆查看」） {#jgb/F/repair-view-only-roles}
- phrasings:
  - {text: "大房東可以改修繕單嗎", source: "draft:outline-20260920", status: approved}
  - {text: "誰只能看修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "查看跟編輯有什麼差別", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼列表裡少了幾張修繕單", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/RepairController.php, code:src/pages/repair/edit/Index.vue, code:app/Repair.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
齒輪選單裡開啟修繕單細節的按鈕，一般會顯示「編輯＆查看」；但登入身分是「大房東」時，這顆按鈕文字會變成「查看」。
房東方團隊成員如果對這個物件只有「顯示所屬修繕資料」的權限、沒有「顯示所有修繕資料」的權限，按鈕文字一樣會變成「查看」；不過，如果這位成員就是這張修繕單的經理人，系統會把這張單的修繕權限都視為開啟，看到的仍是「編輯＆查看」，也可以移動狀態。
如果房東方帳號對這個物件連「顯示所屬修繕資料」都沒有，這張修繕單的那一列根本不會出現在列表裡，不是顯示成唯讀，是完全看不到這一列。
齒輪按鈕文字的「編輯＆查看」跟「查看」只反映顯示修繕資料的權限與是不是大房東身分；能不能移動狀態、能不能在細節頁編輯，要看另一組「編輯修繕」的權限，這兩件事是分開判斷的。
大房東因為在細節頁的編輯判斷裡被直接排除，所以看到「查看」文字時也確實不能編輯或移動；但只有「顯示所屬」權限的團隊成員如果同時具備編輯所屬修繕的權限，齒輪按鈕文字一樣會變成「查看」，卻仍然可以移動狀態、在細節頁編輯。
### 修繕單總表可以用分類、項目、是否緊急篩選嗎？（可以；先選分類才能選項目，換分類會把已選的項目清空；「是否緊急」是一個勾選框，勾了才會加上這個條件） {#jgb/F/repair-list-filter-category-item-urgent}
- phrasings:
  - {text: "修繕單怎麼用分類篩選", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單搜尋可以選項目嗎", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼只看緊急修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "分類項目篩選怎麼用", source: "draft:outline-20260920", status: approved}
- sources: [code:src/components/Lightbox/RepairAdvSearch.vue, code:src/pages/repair/list/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階搜尋裡有「分類」跟「項目」兩個下拉選單：在還沒選分類之前，「項目」裡沒有可選的選項；選了分類之後，「項目」才會變成可以選、而且選項只會列出這個分類底下的項目。
如果重新換選另一個分類，原本選的「項目」會被清空，需要重新選一次。
「是否為緊急項目」是一個勾選框，不勾就不會加上這個篩選條件；勾了之後，總表只會顯示被標記為緊急的修繕單。
### 修繕單總表點「房東/管理者」或「租客」欄位會怎樣？（會彈出這個人的聯絡資訊卡） {#jgb/F/repair-list-contact-card}
- phrasings:
  - {text: "點房東管理者欄位會怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單列表點租客會出現什麼", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼看修繕單相關人的聯絡方式", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:src/components/SurelyVue/Common/SingleUserCell.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點一下「房東/管理者」這一欄，會跳出一張聯絡資訊卡，顯示這個帳號的聯絡資訊；點「租客」這一欄也會跳出同樣形式的聯絡資訊卡，顯示這欄記錄到的租客聯絡資訊；如果這欄沒有聯絡人資料，畫面只會顯示「-」，不能點，點了也不會跳出提示（另見「修繕單總表的表格欄位顯示什麼」）。
## 報修申請流程 {#F-repair-apply}
### 怎麼申請修繕單？（房東方從【修繕管理】>【修繕單總表】、租客從【我的報修】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換） {#jgb/F/repair-apply-flow-and-entry}
- phrasings:
  - {text: "怎麼新增修繕單", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼報修", source: "draft:outline-20260920", status: approved}
  - {text: "申請修繕流程", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單申請入口在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/list/Index.vue, code:src/pages/repair/applyProcess/Index.vue, code:src/utils/constants/repair.constant.ts, code:routes/web.php, help:repair_zh-Hant.html, code:app/Role.php, code:src/pages/repair/applyProcess/_parts/Detail.vue, code:app/Notification.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東方從【修繕管理】>【修繕單總表】、租客從【我的報修】>【修繕單總表】進入；租客頁面右上角有「新增修繕單」按鈕，房東方帳號則要有「新增&編輯&刪除所屬修繕資料」或「新增&編輯&刪除所有修繕資料」其中一項權限，才看得到這個按鈕。
申請修繕分成三步：先選要報修的物件，再選修繕分類與項目，最後填報修細節後送出；第一步（選物件）下方的按鈕是「取消」與「下一步」，第二步（選分類）是「上一步」與「下一步」，第三步（填細節）則是「上一步」與「申請修繕」。
租客可以自己在系統上申請報修，房東方也可以代租客申請；租客自己送出的修繕單，房東方與租客都看得到進度，但房東方在網頁上建立的修繕單目前不會同步到租客的修繕單總表，租客看不到。
填完報修細節按下「申請修繕」送出後，系統會直接把使用者帶回修繕單總表的「申請修繕」分頁。
LINE 在修繕流程裡用於通知（修繕單建立等階段會透過 LINE 推播），以及修繕單細節頁的分享按鈕；JGB 網頁介面沒有透過 LINE 發起報修的入口。
### 沒有租約在跑的物件也能申請修繕嗎？（可以，房東方只要建好物件就能申請，不用先有合約） {#jgb/F/repair-apply-without-contract}
- phrasings:
  - {text: "空屋可以報修嗎", source: "draft:outline-20260920", status: approved}
  - {text: "沒租客的房子能修繕嗎", source: "draft:outline-20260920", status: approved}
  - {text: "申請修繕要先有合約嗎", source: "draft:outline-20260920", status: approved}
- sources: [help:repair_zh-Hant.html, code:src/pages/repair/applyProcess/Index.vue, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
申請修繕不需要這個物件正在跑合約，房東方只要已經把物件建立在系統上，就可以幫這個物件新增修繕單。
就算物件目前是空屋、尚無租客入住，房東方一樣可以幫這個物件申請修繕。
### 報修分類項目怎麼選？（分類與項目都是系統設定的清單，選好之後在報修細節可以按「編輯」回上一步重選；有一個特定分類會多出讓使用者自己輸入名稱的欄位） {#jgb/F/repair-apply-category-item-other}
- phrasings:
  - {text: "修繕項目沒有我要的怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "報修分類怎麼選", source: "draft:outline-20260920", status: approved}
  - {text: "自訂修繕項目名稱", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Repair.php, code:src/utils/enums/repair.enum.ts, code:src/pages/repair/applyProcess/_parts/Detail.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選好報修物件後，系統會列出修繕分類跟項目讓使用者點選，項目是圖示卡片的形式；分類跟項目的清單內容是後台設定的資料，不是寫死在畫面上。
分類清單裡有一個分類被畫面認定為特殊分類：選到這個分類時，報修細節畫面會多出「自定義分類名稱」的輸入欄位，提示文字是「請輸入自定義分類名稱」，讓使用者自己打字說明要報修的項目。
選好分類和項目之後，在「報修細節」畫面上還可以點「編輯」，回到上一步重新挑選分類與項目。
### 報修細節要填什麼？（項目分類、問題必填；預約時段依身分決定是否必填；緊急修繕、佐證照片、備註選填；「通知及同步租客」是房東代租客申請時會看到的一個開關，但目前沒有實際作用） {#jgb/F/repair-apply-detail-fields}
- phrasings:
  - {text: "修繕單要填哪些資料", source: "draft:outline-20260920", status: approved}
  - {text: "報修細節必填欄位", source: "draft:outline-20260920", status: approved}
  - {text: "申請修繕表單欄位", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/applyProcess/_parts/Detail.vue, code:src/pages/repair/applyProcess/Index.vue, code:src/components/SwitchButton.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「項目分類」跟「問題」是必填欄位，問題可以從系統列出的選項裡選，也可以選「其他」自己輸入文字說明。
「緊急修繕」「佐證照片或影片」「備註」都是選填欄位，不是必填；「緊急修繕」旁邊的說明文字寫著：如果開啟「緊急修繕」，廠商將視狀況增加修繕費用，請斟酌使用。
如果是房東方幫目前有租客的物件申請修繕，畫面會多顯示一個標示為必填的「通知及同步租客」切換開關，說明文字是「本物件有租客承租中，是否要通知及同步於您租客的修繕單總表」；但這個開關目前沒有接上任何切換或儲存的邏輯，點擊它不會改變畫面呈現，也不會影響送出的資料。
「緊急修繕」的勾選框同樣沒有接上切換邏輯，不管使用者有沒有點擊，這張修繕單送出後在系統裡都會被記錄成「非緊急」。
備註欄位是用來寫其他想讓維修師傅知道的注意事項。
### 預約時段規則是什麼？（畫面上標示為必填，但實際上只有租客身分申請時系統才會擋下沒填的情況；房東申請時就算不填也能送出） {#jgb/F/repair-apply-reservation-slots}
- phrasings:
  - {text: "修繕預約時段怎麼填", source: "draft:outline-20260920", status: approved}
  - {text: "租客要選維修時間嗎", source: "draft:outline-20260920", status: approved}
  - {text: "可以約幾個修繕時段", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/applyProcess/Index.vue, code:src/pages/repair/applyProcess/_parts/Detail.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「預約時段」這個欄位在畫面上一律標示為必填，但真正會擋下「沒填就不能送出」的檢查，只有在申請人身分是租客時才會生效；身分是房東方時，就算完全不填，送出按鈕一樣可以按。
每組時段可以選日期跟一段從幾點到幾點的時間，最多可以「新增時段」到 5 組。
頁面上會提醒這個物件所在的時區，方便使用者知道填的時間是以哪個時區為準。
### 報修可以附照片或影片嗎？（照片最多 10 張；影片最長 30 秒或 100MB；支援 jpeg／jpg／png 圖片與 mov／mp4／webm 影片） {#jgb/F/repair-apply-photo-limit}
- phrasings:
  - {text: "報修可以傳照片嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單附件限制", source: "draft:outline-20260920", status: approved}
  - {text: "報修影片大小限制", source: "draft:outline-20260920", status: approved}
  - {text: "修繕照片幾張", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/applyProcess/_parts/Detail.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
申請修繕時可以上傳損壞處的照片或影片，方便維修師傅快速了解狀況；照片最多可以放 10 張，影片最長 30 秒或 100MB。
支援的圖片格式是 jpeg、jpg、png，影片格式是 mov、mp4、webm。
如果選擇的照片已經到 10 張的上限，上傳入口就會收起來，要先刪掉幾張才能繼續加。
### 新增修繕單後誰會收到通知？（租客送出時通知房東方；房東方在網頁上建立時只寄 Email 給房東方，租客不會收到通知） {#jgb/F/repair-apply-notifications}
- phrasings:
  - {text: "申請修繕會通知誰", source: "draft:outline-20260920", status: approved}
  - {text: "報修後誰會知道", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單送出通知", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/applyProcess/Index.vue, code:app/Notification.php, code:app/Role.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客送出修繕單後，房東方會收到通知中心訊息與 Email，房東方有綁定 LINE 的話也會收到 LINE 通知；租客自己不會另外收到通知。
房東方在網頁上建立修繕單時，系統只會寄 Email 給這張修繕單的房東方帳號；租客目前不會收到任何通知，也不會在自己的修繕單總表看到這張單。
送出成功後，畫面上也會另外跳出成功提示訊息，讓使用者知道這張修繕單已經建立好了。
送出後系統會直接把畫面帶回修繕單總表的「申請修繕」分頁，不需要額外操作確認。
### 安排廠商、完成修繕、結單時還會發哪些通知？（租客只有在這張修繕單會通知租客時才收得到；結單只寄 Email） {#jgb/F/repair-notifications-by-stage}
- phrasings:
  - {text: "安排修繕會通知租客嗎", source: "draft:outline-20260920", status: approved}
  - {text: "完成修繕後誰會知道", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單結單會通知誰", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Notification.php, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
管理者更新安排修繕的廠商資訊時，如果這張修繕單會通知租客，租客會收到通知中心訊息，有綁定 LINE 的話也會收到 LINE 推播。
管理者在「完成修繕」區塊儲存房東備註時，同樣只有會通知租客的修繕單，租客才會收到通知中心訊息與 LINE 推播。
修繕單移到「結單」時，系統只寄 Email：房東方一定會收到，租客則只有在這張修繕單會通知租客時才會收到；結單不發 LINE，也不發通知中心訊息。
租客自己送出的修繕單會通知租客；房東方在網頁上建立的修繕單目前一律不會通知租客。
## 修繕單編輯 {#F-repair-edit}
### 修繕單細節頁的進度時間軸顯示什麼？（申請修繕、安排修繕、完成修繕、結單、封存五個階段，以及各階段對應的日期） {#jgb/F/repair-edit-progress-timeline}
- phrasings:
  - {text: "修繕單進度怎麼看", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單細節頁面", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單時間軸", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點進一張修繕單的細節頁，最上面會有一條時間軸，依序是申請修繕、安排修繕、完成修繕、結單、封存五個階段，目前所在的階段會被標示出來。
各階段下方日期的來源不同：申請修繕是送出申請的時間，安排修繕是廠商安排紀錄裡填的修繕時間（有多筆時取第一筆），完成修繕是房東備註裡填的完成時間，結單與封存則是修繕單被移到該狀態的時間。
因此有日期不代表已經走到那個階段：例如還在安排修繕時，房東若先在房東備註填了完成時間，完成修繕下方就會顯示日期；從修繕單總表的齒輪選單把修繕單移回前面的狀態時，原本記下的結單、封存時間也不會清掉。
如果直接打開修繕單細節頁的網址、但網址裡沒有帶修繕單編號，系統會直接把使用者導回修繕單總表的「申請修繕」分頁。
### 修繕單細節頁怎麼列印？（右上角有「列印」按鈕，會叫出瀏覽器內建的列印視窗，可以印出來或存成 PDF） {#jgb/F/repair-edit-print}
- phrasings:
  - {text: "修繕單怎麼列印", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單可以存成 PDF 嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
頁面右上角有「列印」按鈕，可以把這張修繕單的內容印出來。
點「列印」的時候，系統會叫出瀏覽器本身的列印視窗，讓使用者選擇要印出來還是存成 PDF。
### 修繕單細節頁怎麼切換狀態？（下拉選單直接選要換到哪個階段，按「變更」儲存） {#jgb/F/repair-edit-switch-status}
- phrasings:
  - {text: "修繕單細節頁怎麼改狀態", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼在修繕單裡面切換階段", source: "draft:outline-20260920", status: approved}
  - {text: "細節頁的狀態下拉選單怎麼用", source: "draft:outline-20260920", status: approved}
  - {text: "選了狀態沒按變更會生效嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
有編輯權限的房東方帳號，在細節頁會看到「切換狀態」區塊，說明文字是「房東可根據實務狀況隨時切換修繕單的狀態」，用下拉選單選好想要的階段後按「變更」就會儲存。
租客帳號跟大房東角色打開這個頁面時，看不到「切換狀態」這個區塊，只有具備編輯修繕權限的房東方帳號才看得到。
選好想要的階段之後要按「變更」這顆按鈕，系統才會真的儲存，不是選了就自動生效。
### 誰不能編輯修繕單細節頁？（租客帳號、大房東角色不能切換狀態、不能改廠商資訊、不能寫房東備註；租客只能編輯自己的房客備註） {#jgb/F/repair-edit-cannot-edit-roles}
- phrasings:
  - {text: "租客可以改修繕單嗎", source: "draft:outline-20260920", status: approved}
  - {text: "大房東可以編輯修繕單嗎", source: "draft:outline-20260920", status: approved}
  - {text: "誰能改修繕單內容", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:src/pages/repair/edit/_parts/VendorContactSection.vue, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客帳號跟大房東角色打開修繕單細節頁，看不到「切換狀態」區塊，也不能編輯安排修繕的廠商資訊或填寫房東備註；租客唯一能在細節頁編輯的是自己的房客備註。
房東方帳號要有「新增&編輯&刪除所屬修繕資料」或「新增&編輯&刪除所有修繕資料」其中一項權限，而且不是大房東角色，才能編輯這張修繕單。
在「安排修繕」廠商資訊那一塊，就算已經有安排紀錄，租客跟大房東角色一樣看不到可以重新編輯的圖示。
### 修繕單細節頁顯示哪些報修時填的資料？（「細節補充」區塊底下：申請日期、是否緊急、照片、聯絡電話或 Email、物件區域與時區、分類項目、問題、備註、預約時段；房東方才看得到「細節補充」這個標題與說明文字） {#jgb/F/repair-edit-application-detail-readonly}
- phrasings:
  - {text: "修繕單細節頁看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單申請內容在哪看", source: "draft:outline-20260920", status: approved}
  - {text: "細節補充是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "報修資料能不能在細節頁改", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:src/pages/repair/edit/_parts/ApplicationDetail.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
報修資料連同安排修繕的廠商資訊，都放在「細節補充」這個大標題底下；這個標題跟說明文字「以下資訊房東可根據實務狀況補充填寫，如有提供，您的租客也會看到您提供的資訊」只有房東方帳號看得到，租客登入看不到這個標題（但底下的報修資料內容租客一樣看得到）。
細節頁會原樣顯示報修時填的資料，包含物件區域、物件時區、分類項目、問題、備註、預約時段這幾個欄位，這一段是唯讀的，不能在這裡直接修改。
電話跟Email顯示的是這張修繕單的房東方身分：如果這張單所屬的房東方是「團隊」身分，這裡顯示的會是「公司電話」跟「公司Email」；如果是「個人房東」身分，則顯示「手機號碼」跟「Email」——這是根據修繕單本身記錄的房東方身分與帳號決定的，不是根據當初提出這張報修申請的人。
只有這張修繕單被標記為緊急，這裡才會在申請日期旁邊多顯示一個「緊急」的標籤；但目前透過網頁申請修繕的流程，「緊急修繕」勾選框並沒有接上實際邏輯，勾了也不會讓這張單被標記為緊急（另見「報修細節要填哪些欄位，哪些是必填的」）。
### 怎麼安排修繕廠商？（填寫修繕時間、廠商名稱、維修人員、聯絡電話，儲存後會留下歷史紀錄可以展開查看） {#jgb/F/repair-edit-vendor-assign}
- phrasings:
  - {text: "怎麼填廠商資訊", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單怎麼指派維修人員", source: "draft:outline-20260920", status: approved}
  - {text: "廠商聯絡資料怎麼填", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/_parts/VendorContactSection.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
還沒安排廠商時，有編輯權限的帳號會看到「填寫廠商資訊」按鈕，不具編輯權限的帳號則只會看到「安排修繕廠商中」的文字。
填寫的欄位是修繕時間、廠商名稱、維修人員、聯絡電話，儲存後畫面會顯示這幾個欄位，並且多一個「編輯時間」記錄最後修改的時間。
如果同一張修繕單改派過不只一次廠商，可以點「展開歷史紀錄」看到之前每一次安排的紀錄。
### 「房東備註」要填什麼？（完成時間、備註文字最多 300 字、可以附照片，最多 10 張、單檔最大 10MB、支援 JPG／PNG／PDF；只有有編輯權限的房東方帳號能編輯） {#jgb/F/repair-edit-landlord-complete-memo}
- phrasings:
  - {text: "房東備註在哪填", source: "draft:outline-20260920", status: approved}
  - {text: "房東備註可以放照片嗎", source: "draft:outline-20260920", status: approved}
  - {text: "備註字數限制多少", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:src/pages/repair/_parts/MemoArea.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「完成修繕」這個區塊分左右兩欄，左邊是「房東備註」，可以填完成時間、結算金額、備註文字跟照片，只有有編輯權限的房東方帳號能編輯。
備註文字最多可以輸入 300 字。
照片最多可以放 10 張，支援 JPG、PNG、PDF 檔，單一檔案大小最大 10MB。
### 修繕結算金額在哪裡填、誰看得到？（在「完成修繕」的「房東備註」編輯模式填；「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；填了金額不會自動產生帳單） {#jgb/F/repair-edit-amount-visibility}
- phrasings:
  - {text: "修繕結算金額怎麼填", source: "draft:outline-20260920", status: approved}
  - {text: "完成修繕怎麼登記費用", source: "draft:outline-20260920", status: approved}
  - {text: "修繕金額會變成帳單嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕結算金額誰看得到", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:app/Http/Controllers/RepairController.php, code:src/pages/repair/_parts/MemoArea.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「結算金額」這個欄位只有身分是房東的帳號才會顯示，租客登入後看不到金額。
修繕單裡填的結算金額目前不會自動產生帳單，是修繕單自己的紀錄。
「結算金額」填在修繕單細節頁「完成修繕」區塊的「房東備註」裡：點「房東備註」右上角的編輯圖示進入編輯，填好「結算金額」後按「儲存」。
能編輯「房東備註」的只有房東方帳號，且要有「新增&編輯&刪除所屬修繕資料」或「新增&編輯&刪除所有修繕資料」權限；大房東角色與租客不能編輯。
### 「房客備註」是什麼？（右邊那一欄，放租客的備註文字與照片，只有租客自己能編輯；從網頁建立的修繕單都會顯示這一欄） {#jgb/F/repair-edit-tenant-memo}
- phrasings:
  - {text: "房客備註在哪", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單為什麼沒有房客備註", source: "draft:outline-20260920", status: approved}
  - {text: "租客可以留言嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/Index.vue, code:src/pages/repair/_parts/MemoArea.vue, code:src/pages/repair/applyProcess/Index.vue, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「完成修繕」右邊那一欄是「房客備註」，只放備註文字跟照片，不包含完成時間或結算金額欄位。
房客備註區塊會不會出現，看這張修繕單有沒有預約時段資料：在網頁上申請修繕時，預約時段至少會送出一列（就算沒填也一樣），所以從網頁建立的修繕單都會顯示房客備註區塊；只有完全沒有預約時段資料的修繕單，這一欄才會改成顯示「此修繕單為房東發起，無房客備註」。
房客備註只有租客自己的帳號能編輯，房東方帳號打開這一區只能查看，看不到編輯圖示。
### 怎麼把修繕單分享出去給廠商？（在修繕單細節頁點「分享」，電腦上可以複製連結或用 LINE 分享，手機上會直接叫出手機的分享選單；廠商點開連結不需要登入 JGB 帳號） {#jgb/F/repair-edit-share-to-vendor}
- phrasings:
  - {text: "修繕單怎麼分享給廠商", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼把修繕單傳給水電行", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單連結怎麼複製", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/edit/_parts/ApplicationDetail.vue, code:app/Http/Middleware/LoginCheck.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在修繕單細節頁裡，非租客身分的帳號會看到「分享訊息」區塊，說明文字是「如有配合的廠商，可使用下方分享功能，即可將申請單細節轉給廠商」，點「分享」按鈕後的反應依裝置而不同。
在電腦上，或手機瀏覽器不支援系統分享功能時，會開啟「分享修繕申請單」視窗，可以複製修繕單連結，或用 LINE 分享出去；在支援的手機瀏覽器上，會直接叫出手機內建的分享選單。
廠商拿到這個連結之後，打開它不需要先登入 JGB 帳號（另見「看修繕單分享頁需要先登入嗎」）。
## 修繕單分享頁 {#F-repair-share}
### 修繕單分享頁需要先登入嗎？（不需要，這個連結是公開的，系統特別把它排除在登入檢查之外，任何拿到網址的人都可以直接打開） {#jgb/F/repair-share-public-link}
- phrasings:
  - {text: "修繕分享連結要登入嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單連結廠商打得開嗎", source: "draft:outline-20260920", status: approved}
  - {text: "分享頁需要帳號嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕分享連結是公開的嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Middleware/LoginCheck.php, code:routes/web.php, code:src/pages/repair/share/Index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
修繕單分享頁不需要登入 JGB 帳號就能打開；系統判斷「使用者有沒有登入、要不要導去登入頁」的規則裡，特別把分享頁的網址排除在外，所以沒有登入的人一樣可以直接看到內容。
這跟修繕功能的其他頁面不一樣：修繕單總表跟修繕單細節頁都被系統設定成需要先登入才能進入，只有分享頁被單獨排除。
如果連結裡的修繕單編號查無資料，系統會把使用者導去官網首頁，而不是顯示分享內容。
### 分享連結誰看得到？（金額只有在瀏覽者本人目前登入身分是房東時才會顯示，且不會核對是不是這張修繕單相關的房東或租客） {#jgb/F/repair-share-visibility-summary}
- phrasings:
  - {text: "分享連結誰都能看嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕分享頁會外流個資嗎", source: "draft:outline-20260920", status: approved}
  - {text: "分享頁看得到金額嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/RepairController.php, code:src/pages/repair/share/Index.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「結算金額」在分享頁上要不要顯示，看的是瀏覽者目前自己登入 JGB 的身分是不是房東；如果瀏覽者根本沒有登入（分享頁本來就不需要登入），這個判斷會是否，所以看不到金額。
系統產生分享頁資料時，不會核對這個瀏覽者是不是這張修繕單相關的房東或租客；「結算金額」是否顯示，只看瀏覽者目前登入的身分是不是房東，和是否與這張修繕單有關無關。
### 分享連結會過期嗎？（目前不會，沒有天數限制） {#jgb/F/repair-share-no-expiry}
- phrasings:
  - {text: "修繕分享連結會過期嗎", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單連結多久失效", source: "draft:outline-20260920", status: approved}
  - {text: "分享連結有效期限", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
目前打開修繕單分享連結，並不會因為超過幾天就失效。
分享頁抓資料時只靠修繕單的編號去找，不受天數期限或物件目前狀態影響。
### 修繕單分享頁看得到什麼？（修繕申請單標題與是否緊急、照片、報修細節、安排的廠商資訊、房東備註與房客備註，全部都是唯讀；不會顯示物件廣告連結、縮圖，也沒有房東／承租方資訊側欄） {#jgb/F/repair-share-content}
- phrasings:
  - {text: "分享頁看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "修繕單連結打開會看到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "廠商點連結能看到哪些資訊", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/repair/share/Index.vue, code:app/Http/Controllers/RepairController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
分享頁最上面是「修繕申請單」標題跟申請日期，如果這張單被標記為緊急，旁邊會多顯示「緊急」標籤；但目前透過網頁申請修繕的流程，這個標記並不會因為勾選「緊急修繕」而被設定（另見「報修細節要填哪些欄位，哪些是必填的」）。
接下來會顯示報修時的照片、聯絡電話或Email、物件區域與時區、分類、問題、備註、預約時段等報修細節。
再來會顯示目前安排的廠商資訊（修繕時間、廠商名稱、維修人員、聯絡電話），以及房東備註跟房客備註。
分享頁上的廠商資訊跟備註全部都是唯讀，打開分享頁的人不能在這一頁編輯或留言。
分享頁不會顯示物件名稱、物件廣告連結、物件縮圖，也沒有一般細節頁右側那種列出房東方或承租方聯絡資訊的側欄，這幾項在分享模式下會被整段拿掉。
