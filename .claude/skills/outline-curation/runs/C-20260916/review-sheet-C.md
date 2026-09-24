# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/C/community-batch-create` | 社區建立與批次新增物件 | `jgb/C/community-batch-create` | 社區建立與批次新增物件 | keep | C/C/C | |
| 2 | `tmp:canon:jgb/C/property-management-overview` | 房源管理模組做什麼（含自訂狀態標籤） | `jgb/C/property-management-overview` | 房源管理模組做什麼（含自訂狀態標籤） | keep | C/C/C | |
| 3 | `tmp:canon:jgb/C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | `jgb/C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | merge | C/C/C | |
| 4 | `tmp:canon:jgb/C/rental-storefront-vr` | 招租店舖與 VR 看屋 | `jgb/C/rental-storefront-vr` | 招租店舖與 VR 看屋 | keep | C/C/C | |
| 5 | `tmp:draft:1` | 物件批次新增表格如何填寫？ | `jgb/C/property-batch-import` | 物件批次匯入：範本、表格填寫與上傳失敗 | new | C/C/C | |
| 6 | `tmp:draft:2` | 進階搜尋功能如何用? | `jgb/C/property-advanced-search` | 物件列表進階搜尋怎麼用 | new | C/C/C | |
| 7 | `tmp:kb:1396` | 社區公共設施有哪些 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 8 | `tmp:kb:2980` | 公共區域使用權限 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 9 | `tmp:kb:3049` | 公共設施使用權 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 10 | `tmp:kb:3050` | 公共設施義務 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 11 | `tmp:kb:3051` | 洗衣機使用規範 | `jgb/C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | new | ⚠️ ?/C/C | |
| 12 | `tmp:kb:3052` | 烘衣機使用規範 | `jgb/C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | new | ⚠️ ?/C/C | |
| 13 | `tmp:kb:3053` | 垃圾分類規範 | `jgb/C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | new | ⚠️ ?/C/C | |
| 14 | `tmp:kb:3054` | 垃圾回收時間 | `jgb/C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | new | ⚠️ ?/C/C | |
| 15 | `tmp:kb:3055` | 大型廢棄物處理 | `jgb/C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | new | ⚠️ ?/C/C | |
| 16 | `tmp:kb:3056` | 公共設施開放時間 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 17 | `tmp:kb:3057` | 公共設施損壞 | `jgb/C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | new | ⚠️ ?/?/C | |
| 18 | `tmp:kb:3058` | 公共設施使用 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 19 | `tmp:kb:3059` | 公共設施使用費用 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/?/C | |
| 20 | `tmp:kb:3060` | 公共設施規範 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 21 | `tmp:kb:3061` | 公共設施使用規範 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 22 | `tmp:kb:3062` | 公共設施爭議解決 | `jgb/C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | new | ⚠️ ?/C/C | |
| 23 | `tmp:kb:3063` | 公共設施使用變更 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 24 | `tmp:kb:3064` | 公共設施保險 | `jgb/C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | new | ⚠️ ?/C/C | |
| 25 | `tmp:kb:3157` | 社區活動 | `jgb/C/community-services-and-events` | 社區生活服務與活動（社區活動、包裹代收、社宅社區服務） | new | ⚠️ ?/C/C | |
| 26 | `tmp:kb:3245` | 公共設施使用義務 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 27 | `tmp:kb:3246` | 社區設施開放 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 28 | `tmp:kb:3247` | 公共設施使用規則 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 29 | `tmp:kb:3248` | 公共設施安全規範 | `jgb/C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | new | ⚠️ ?/C/C | |
| 30 | `tmp:kb:3249` | 公共設施爭議 | `jgb/C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | new | ⚠️ ?/C/C | |
| 31 | `tmp:kb:3263` | 社會住宅社區服務 | `jgb/C/community-services-and-events` | 社區生活服務與活動（社區活動、包裹代收、社宅社區服務） | new | ⚠️ ?/C/C | |
| 32 | `tmp:kb:3299` | 公共設施費用 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/?/C | |
| 33 | `tmp:kb:3300` | 公共設施投保 | `jgb/C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | new | ⚠️ ?/C/C | |
| 34 | `tmp:kb:3357` | 物件 批次匯入 上傳 | `jgb/C/property-batch-import` | 物件批次匯入：範本、表格填寫與上傳失敗 | new | C/C/C | |
| 35 | `tmp:kb:3428` | 物件狀態 定義條件 | `jgb/C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | merge | C/C/C | |
| 36 | `tmp:kb:3429` | 物件刊登 上架條件 | `jgb/C/property-listing-conditions` | 物件要怎麼刊登上架、刊登需要什麼條件 | new | C/C/C | |
| 37 | `tmp:kb:3430` | 物件下架 條件流程 | `jgb/C/property-unlisting` | 物件怎麼下架、為什麼突然全部下架 | new | C/C/C | |
| 38 | `tmp:kb:3431` | 物件批次匯入 Excel 建立 | `jgb/C/property-batch-import` | 物件批次匯入：範本、表格填寫與上傳失敗 | new | C/C/C | |
| 39 | `tmp:kb:3433` | 物件 VR 虛擬導覽 | `jgb/C/property-vr-tour` | 物件 VR 虛擬導覽怎麼綁、費用與拍攝找誰 | new | C/C/C | |
| 40 | `tmp:kb:3434` | 物件自訂標籤 分類管理 | `jgb/C/property-custom-tags` | 物件自訂標籤怎麼建、怎麼用來篩選 | new | C/C/C | |
| 41 | `tmp:kb:3468` | 社區管理 建立編輯 | `jgb/C/community-setup-and-property-binding` | 社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定） | new | C/C/C | |
| 42 | `tmp:kb:3469` | 社區與物件關係 綁定 | `jgb/C/community-setup-and-property-binding` | 社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定） | new | C/C/C | |
| 43 | `tmp:kb:3470` | 社區公開頁面 廣告展示 | `jgb/C/community-public-page` | 社區公開頁面是什麼、能拿來做什麼 | new | C/C/C | |
| 44 | `tmp:kb:3505` | 為什麼不能新增物件 | `jgb/C/property-add-blocked` | 為什麼不能新增物件 | new | ⚠️ C/C/? | |
| 45 | `tmp:kb:3506` | 物件為什麼突然全部下架 | `jgb/C/property-unlisting` | 物件怎麼下架、為什麼突然全部下架 | new | C/C/C | |
| 46 | `tmp:kb:4145` | 對外顯示地址 沒生效 還是完整地址 | `jgb/C/public-display-address` | 對外顯示地址改了為什麼後台還是完整地址 | new | C/C/C | |
| 47 | `tmp:kb:4146` | 招租店舖 房東對外首頁 入口 分享 | `jgb/C/storefront-entry-share` | 招租店舖入口在哪、怎麼分享、為什麼物件沒出現 | new | C/C/C | |
| 48 | `tmp:kb:4147` | 編輯物件 刊登物件 差異 儲存 | `jgb/C/property-edit-vs-publish` | 編輯物件與刊登物件差在哪、為什麼修改沒存到 | new | C/C/C | |
| 49 | `tmp:kb:4151` | 物件要怎麼刊登 上架流程 | `jgb/C/property-listing-conditions` | 物件要怎麼刊登上架、刊登需要什麼條件 | new | C/C/C | |
| 50 | `tmp:kb:4152` | 改了對外顯示地址 怎麼還是顯示完整地址 | `jgb/C/public-display-address` | 對外顯示地址改了為什麼後台還是完整地址 | new | C/C/C | |
| 51 | `tmp:kb:4154` | 這個物件現在什麼狀態 租客看得到嗎 | `jgb/C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | merge | C/C/C | |
| 52 | `tmp:kb:4262` | 社區設施 公共設施 健身房 交誼廳 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 53 | `tmp:kb:4272` | 管理員會代收包裹嗎 | `jgb/C/community-services-and-events` | 社區生活服務與活動（社區活動、包裹代收、社宅社區服務） | new | ⚠️ ?/C/C | |
| 54 | `tmp:kb:4276` | 社區有哪些公共設施可以用 | `jgb/C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | new | ⚠️ ?/C/C | |
| 55 | `tmp:kb:4648` | 即時物件出租率 百分比怎麼算 已出租數字來源 | `jgb/C/occupancy-rate-calculation` | 首頁即時物件出租率怎麼算、已出租數字從哪來 | new | C/C/C | |

## B. 拆分（split）——一個舊細目拆成多個新細目

（本次無拆分）

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/C/community-facilities-and-hours`《社區有哪些公共設施、開放時間、費用與變更通知》 | `tmp:kb:1396`＋`tmp:kb:4262`＋`tmp:kb:4276`＋`tmp:kb:3056`＋`tmp:kb:3058`＋`tmp:kb:3246`＋`tmp:kb:3063`＋`tmp:kb:3059`＋`tmp:kb:3299` | 來源為租客視角、內容須改寫成業者層級（業者訂規範、會被租客問）；「有哪些設施、何時可用（含假期調整、變更需通知）、要不要另收費」是租客問業者的同一組設施資訊；1396／4262／4276 為空內文或純查詢入口只當入口；3059／3299 的費用僅為設施資訊的一項，依契約留 C 不送 E。 | |
| `jgb/C/community-facility-disputes`《公共設施損壞責任、使用爭議處理與責任保險》 | `tmp:kb:3057`＋`tmp:kb:3062`＋`tmp:kb:3249`＋`tmp:kb:3064`＋`tmp:kb:3300` | 來源為租客視角、內容須改寫成業者層級（業者訂規範、會被租客問）；設施損壞的責任歸屬、住戶間使用爭議的協商與調解流程、設施責任保險三者同屬「出事誰負責、怎麼處理」的責任面，依契約歸為一個「爭議與保險」細目；3057 依契約留 C 不送 F，損壞責任在此答、報修流程另見 F。 | |
| `jgb/C/community-facility-usage-rules`《公共設施使用規範：權利、義務、安全規範與違規後果》 | `tmp:kb:2980`＋`tmp:kb:3049`＋`tmp:kb:3050`＋`tmp:kb:3245`＋`tmp:kb:3061`＋`tmp:kb:3248`＋`tmp:kb:3060`＋`tmp:kb:3247` | 來源為租客視角、內容須改寫成業者層級（業者訂規範、會被租客問）；權利、義務、安全規範與違規後果是同一套業者訂定的使用規範的四個面向，拆開任一面向都不完整；多筆 kb 為同題重複寫法併為一題。 | |
| `jgb/C/community-garbage-disposal`《社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範》 | `tmp:kb:3053`＋`tmp:kb:3054`＋`tmp:kb:3055`＋`tmp:kb:3051`＋`tmp:kb:3052` | 來源為租客視角、內容須改寫成業者層級（業者訂規範、會被租客問）；垃圾怎麼丟（分類、時間、大型廢棄物）與共用洗衣烘衣設備規範皆為業者訂定的日常生活規範，依契約歸為一個「垃圾與洗衣」細目，與通用設施規範分層。 | |
| `jgb/C/community-services-and-events`《社區生活服務與活動（社區活動、包裹代收、社宅社區服務）》 | `tmp:kb:3157`＋`tmp:kb:3263`＋`tmp:kb:4272` | 來源為租客視角、內容須改寫成業者層級（業者訂規範、會被租客問）；社區提供的非設施類服務（活動、包裹代收、社宅社區服務）性質相同、彼此不重疊，合為一個「生活服務」細目；4272 為空內文入口只當入口。 | |
| `jgb/C/community-setup-and-property-binding`《社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定）》 | `tmp:kb:3468`＋`tmp:kb:3469` | 三角度皆把 3468＋3469 併為一題（社區建檔步驟、編輯、一對多歸戶、公共區域物件、社宅強制綁定彼此依賴才完整）；社區是物件本身的歸屬屬性歸 C，與批次匯入分開。 | |
| `jgb/C/property-batch-import`《物件批次匯入：範本、表格填寫與上傳失敗》 | `tmp:kb:3431`＋`tmp:kb:3357`＋`tmp:kb:tmp:draft:1` | 三角度皆把 3357／3431／draft:1 併為一題（步驟、.xls 與純文字貼上、欄位填法、匯入後為未刊登）；業者操作層級，與 prospect 的 community-batch-create 分層另見，不併入既有細目。 | |
| `jgb/C/property-listing-conditions`《物件要怎麼刊登上架、刊登需要什麼條件》 | `tmp:kb:3429`＋`tmp:kb:4151` | 兩角度獨立成題：上架三前提（訂閱、額度、必填欄位）與上架效果為一完整命題；4151 為空內文入口只當講法。與下架分開，避免一細目兩主題。 | |
| `jgb/C/property-status-meaning`《物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思》 | `tmp:kb:tmp:canon:jgb/C/property-status-meaning`＋`tmp:kb:3428`＋`tmp:kb:4154` | 三角度一致 merge：3428 的合約軸／刊登軸兩軸定義與既有細目同命題互補，答案不因受眾而異故兩受眾共用；4154 為空內文入口（租客看不看得到＝刊登軸）只當講法吸收。 | |
| `jgb/C/property-unlisting`《物件怎麼下架、為什麼突然全部下架》 | `tmp:kb:3430`＋`tmp:kb:3506` | 兩角度獨立成題：手動下架、必填欄位驗證失敗自動下架、方案失效整批下架共用同一機制，拆開各自不完整；方案續約本身另見 I。 | |
| `jgb/C/public-display-address`《對外顯示地址改了為什麼後台還是完整地址》 | `tmp:kb:4145`＋`tmp:kb:4152` | 三角度皆獨立成題：對外顯示地址是物件本身的屬性設定，只作用於廣告頁與地圖、後台永遠完整地址；4152 為空內文入口只當講法。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| content_boundary 把既有細目 community-batch-create 拆成「批次新增物件」（吸收 3357／3431／draft:1）與「社區建立與歸屬」（吸收 3468／3469）兩個 op=split 細目。 | 契約規定既有細目只准 keep／merge、⛔ 不拆；其拆出的兩個主題確實成立，改為只掛新材料的 op=new 細目 property-batch-import 與 community-setup-and-property-binding，既有細目原 id 不動作 prospect 層級另見。 | |
| content_boundary 把既有細目 rental-storefront-vr 拆成「招租店舖」（吸收 4146）與「VR 導覽」（吸收 3433）兩個 op=split 細目。 | 同上，契約禁拆既有細目；4146 與 3433 各自以 op=new 成立 storefront-entry-share 與 property-vr-tour，既有細目 keep。 | |
| content_boundary 把 community-batch-create、rental-storefront-vr、community-public-page、property-vr-tour 的 target_user 標為 prospect＋property_manager 共用。 | user_question_path 與 audience_level 兩角度皆判既有細目為 prospect 能力層級、操作細目為 property_manager；同命題答案因受眾而異時各受眾各一細目，不設共用版以免混層。 | |
| audience_level 把 3429／4151（上架條件）與 3430／3506（下架）併成一個 property-listing-publish-unpublish 細目。 | 另兩角度皆分開；「怎麼上架」與「為什麼被下架」是不同起點的問題，合併會讓一細目含兩主題，違反一主題一細目。 | |
| audience_level 把 3470（社區公開頁）與 4146（招租店舖入口分享）併成 storefront-and-community-page-sharing。 | 另兩角度皆分開；社區公開頁（社區層級）與招租店舖（團隊層級）是兩個不同頁面，使用者會分開問，互為另見即可。 | |
| audience_level 把 3505（為什麼不能新增物件）列 out_of_shelf 送 I。 | 另兩角度皆留 C：提問以「新增物件按不了」為起點，本架保留排查入口，額度與角色機制分別另見 I／B。 | |
| user_question_path 把 30 筆租客視角的社區公共設施／規範列全數列 out_of_shelf 且 suggested_shelf 為「-」（無架可去）。 | 契約裁定採多數留 C 標 property_manager（業者訂規範、會被問），且 suggested_shelf 只准寫架字母；來源改寫成業者層級的要求已寫入各細目 reason。 | |
| content_boundary 把 3057（公共設施損壞責任）送 F、3059／3299（設施費用是否含管理費）送 E。 | 契約明列這三筆在留 C 的租客視角清單內（多數留 C）；損壞責任歸屬與爭議／保險同屬責任面歸 community-facility-disputes-and-insurance，報修流程另見 F；費用僅為設施資訊的一項歸 community-facilities-and-hours，不獨立成帳務命題。 | |
| audience_level 把 22 筆公共設施相關 kb 併成單一 community-facility-rules-and-entitlements、另 8 筆併成 community-living-services，共兩個細目。 | 22 筆涵蓋設施清單、開放時間、費用、規範、罰則、損壞、爭議、保險，超出「一個可獨立回答的主題」；依契約歸成五個細目（設施與時段／使用規範／垃圾與洗衣／爭議與保險／生活服務）。 | |
| content_boundary 把社區規範拆成七個細目（設施與時段、使用規範、洗衣烘衣、垃圾、爭議、保險、服務與活動各自獨立）。 | 契約指定歸成少數幾個細目；洗衣烘衣與垃圾同為日常生活規範併為「垃圾與洗衣」、爭議與保險同為責任面併為「爭議與保險」（並收 3057 損壞責任），其餘三個沿用 content_boundary 的切法與 id。 | |
| user_question_path 把 3011（公益出租人減稅）列 out_of_shelf 但 suggested_shelf 為「-」。 | 另兩角度皆判 E（錢怎麼算歸帳務），取多數；契約要求 suggested_shelf 只寫架字母。 | |
| 同題異名 slug：community-create-edit（uqp）／community-create-and-binding（cb）vs community-setup-and-property-binding；property-unlisting-reasons（uqp）vs property-unlisting；property-edit-and-save（al）vs property-edit-vs-publish；property-display-address（cb）vs public-display-address；property-vr-binding（al）vs property-vr-tour；property-custom-tags-howto（al）vs property-custom-tags；property-list-advanced-search（al）vs property-advanced-search；occupancy-rate-metric（cb）vs occupancy-rate-calculation；property-cannot-create（cb）vs property-add-blocked；property-batch-import-howto（al）vs property-batch-import。 | 主題與來源集合相同，僅 slug 不同；取兩角度共用的 slug，三者各異時取最能同時涵蓋來源命題者（3468＋3469 取含 binding 者）。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 22 | 0 | 0 | 0 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/C/community-facilities-and-hours` | merge |
| `jgb/C/community-facility-disputes` | merge |
| `jgb/C/community-facility-usage-rules` | merge |
| `jgb/C/community-garbage-disposal` | merge |
| `jgb/C/community-services-and-events` | merge |
| `jgb/C/community-setup-and-property-binding` | merge |
| `jgb/C/property-batch-import` | merge |
| `jgb/C/property-listing-conditions` | merge |
| `jgb/C/property-status-meaning` | merge |
| `jgb/C/property-unlisting` | merge |
| `jgb/C/public-display-address` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

（無）
