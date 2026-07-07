# 研究記錄：estate-conversational-facets

> 日期：2026-07-04　方法：jgb2 真碼平行盤查（gap 級一輪＋設計級兩輪）＋AIChatbot 現況盤點＋幫助中心 14 篇素材
> 定位：本文件為設計依據的唯一事實來源；與 help 文章/客服口徑衝突處一律以此為準。

## 摘要（定案清單）

| # | 問題 | 定案 | 證據 |
|---|---|---|---|
| 1 | 物件狀態機 | **兩條獨立軸**：合約軸 `status`（1 未刊登建立/2 刊登中/4 洽談中=有約未簽/8 租約中）× 刊登軸 `is_open`/`sell_is_open` | Estate.php:57-64、1055-1056 |
| 2 | 洽談中語義 | status==4＝已綁合約但未簽署完成；可編輯、不可刪、屬公開狀態 | Estate.php:4654-4674、2750-2810；EstateController.php:4811-4848、10456-10485 |
| 3 | 有約後編輯 | **無欄位鎖定機制**——合約只擋刪除；「有約改不了」屬誤解，口徑走快照原則（修改不影響既有合約，3894） | EstateController.php:4842-4848、10468-10476 |
| 4 | 建約前提 | 挑物件強制 status=2（刊登中）；欄位齊備檢查 `isCurrentDataCanCreateContract()` | EstateController.php:279-283；Estate.php:7918 |
| 5 | 刪除條件 | 三擋：刊登中、有有效合約（「請先將合約解除」）、有 IoT 綁定——「刪除後歷史合約會消失嗎」→ 有約根本刪不了 | EstateController.php:10456-10485 |
| 6 | 對外顯示地址 | 雙層證實：對外廣告頁/GMap 用 `display_address` 系（completeDisplayAddress）、後台用 `address` 系——「改了還顯示完整」= 看的是後台 | Estate.php:3455-3473、7975；ListingController.php:196 |
| 7 | estates 對外 API | `GET /external/v1/estates`＋`/{id}` 存在；**硬過濾 `active=1 AND is_open=1`（只回刊登中）** | routes/api.php:33,41；EstateApiController.php:53-54、121-124 |
| 8 | 批次上傳 | queue（EstateBatchJob，tries=1、timeout 1hr）；結果走通知中心 estate_batch；驗證＝11 必填欄＋3 數值欄＋10MB＋xls/xlsx＋額度 remainEstatesCount | EstateController.php:6202-6223、11490-11496；EstateBatchJob.php:24-27；Notification.php:9536-9555；EstateGeneralImportValidator.php:54-80 |
| 9 | 招租店舖 | 現行：URL `/p/{encryptId}`（route users.info）、支援自訂帳號/子網域；物件對外頁大頭照旁藍色房子 icon 仍在——2021 文章口徑基本正確 | routes/web.php:625、1459；Role.php:459-477（generateLessorStoreUrl）；estate/sell-show.blade.php:981-1002 |

## 主題一：estates 對外 API 白名單（EstateApiController 全盤）

**查詢參數**（EstateApiController.php:47-69、142-195）：page（預設 1）、per_page（預設 50、上限 200）、sort_by（id/created_at/updated_at/rent/size 白名單）、status（原始位元值精確比對）、use_for（residential/business/parking_space）、city_id、district_id、rent_min/max、updated_after、user_id、role_id、keyword（**只搜 title LIKE**，有 escape）。無 estate_id 參數（單筆走 show）。

**圈定機制**（ExternalApiKey.php:200-269）：與 meters 不同——estates 由 **API key 白名單自動圈定**（user_id/role_id IN 白名單），role_id 參數只是白名單內再過濾，非必填非權限來源。show 走 canAccessEstate，無權 403。

**白名單欄位**（formatEstate :204-293）：id/url/user_id/role_id/team_name/serial_id/**title**/**status（原始位元值）**/**bit_status**、位置系（country~district、**address/full_address 真實完整地址有露出**、display_address/full_display_address、經緯度）、特性（use_for/space_type/building/room_count/size/direction/floor/total_floor）、財務（rent/currency/deposit 系/fees/management_fee）、設施、媒體（avatar/gallery/floor_plan/vr_url）、社區（community_id/name）、created_at/updated_at（ISO-8601 UTC）。聯絡資訊（phone/email/姓名）不露出。

**show 額外**（:282-290）：description/traffic/nearby/notes＋**`contract_required_fields`：{all_filled: bool, fields:[{field,label,is_filled}]}**（isCurrentDataCanCreateContract，1hr 快取）——「能不能建約（欄位面）」的現成真值訊號。show 另有 5 分鐘快取。

**設計含意**：
- **is_open=1 硬過濾是本域 grounding 的天花板**：非刊登物件（未刊登/已下架）完全查不到——「為什麼查不到/是不是下架了」無法正面查證，只能以「對外刊登清單中找不到」為弱信號反推〔口徑：找不到＋名稱確認無誤 ⇒ 目前非刊登中；不得斷言「已刪除」〕。放寬過濾/露出 is_open 記 **G-E1**。
- 「能不能建約」決策樹可完整覆蓋：查得到（=刊登中）→ show 的 contract_required_fields 直答缺哪些欄；查不到 → 建約前提是刊登中（EstateController.php:279-283），指路先刊登。
- **個資紅線**：address/full_address 露出但消費端**不出口**（answer 只用 title＋display_address——display 系本來就是對外遮蔽版）；聯絡資訊 API 本身不露，無需遮罩。
- status 原始位元值——**轉譯由 builder 決定性做**（1/2/4/8 → 未刊登/刊登中/洽談中/租約中），沿機械解碼用程式原則。
- 識別鏈：keyword 只搜 title → wrapper 沿 meters 模式（拉頁 ≤200＋client 端 token 化過濾＋純數字先 id 直配）；深欄位（contract_required_fields）僅 show 有 → 鎖定後以 **secondary_call → jgb_estate_detail(id)** attach（既有 secondary_calls 機制，零改引擎）。

## 主題二：批次上傳機制鏈（客服案「處理中 20 分鐘」真因）

流程：上傳（10MB/xls 驗證）→ preview（EstateGeneralImportValidator 逐列：11 必填欄 B/C/D/G/H/K/L/O/R/U/AB、3 數值欄 N/O/S，訊息「{欄位}為必填欄位/必須為數值」）→ confirm（重驗防繞過、面積類別必選、額度 remainEstatesCount 超額開 subscribedPlanIsFull）→ **dispatch EstateBatchJob 入 queue**（先發「系統處理中」通知）→ Job 完成發 estate_batch 通知（total/成功/失敗筆數，連回物件列表）。

**J-E1（交 JGB 候選）**：EstateBatchJob `tries=1`、無失敗通知路徑——worker 掛/超時（timeout 3600s）時使用者**永遠停在「處理中」**，與客服案吻合。建議：failed() handler 發失敗通知。

**知識口徑**：批次結果去**通知中心**看（成功/失敗筆數）；停「處理中」超過一小時屬系統端異常，導客服（不要教使用者重傳造成重複建立）。

## 主題三：招租店舖現行機制

- URL：`/p/{encryptId}`（encrypt_id(role_id) 或自訂 customer_account；帳號=子網域時直接用子網域根路徑）——Role.php:459-477。
- 入口：①物件對外頁房東資訊卡（大頭照旁藍色房子 icon「查看所有物件」）；②後台側邊選單（ApiController getAside 回傳 customerAccountURL）。
- 展示範圍：該 role 刊登中物件（與 estates API 同一 is_open 語義）；資訊連動會員中心帳號資訊（2021 文章此段仍準）。

## 主題四：AIChatbot 端現況與整合點

- **母分類重用**：category_config id 61 `物件管理` 已存在（頂層、is_active、10+ 筆知識已掛 categories）——migration 只補 2 子分類（parent_value='物件管理'）＋母層系統脈絡，零遷移。
- 既有知識 28+ 筆分三類：`物件管理`（3428-3434：狀態/刊登/下架/批次/VR/標籤/Dashboard）、`條件診斷：物件`（3505-3507）、未標旗（3862/3894/3895）——逐筆存廢/補標/兩軸口徑複核入 tasks（3428 狀態定義若為單軸描述必改）。
- registry 模式：api_call_handler.py:59-75——新增 `jgb_estates`（index）＋`jgb_estate_detail`（show）兩鍵。
- 路由回歸：tests/integration/conversational/test_facet_entry_routing_req.py 四域 70 案——擴物件案（含合約域最小對比對）。
- 「資料未儲存」：前端行為無後端真碼可盤——知識以操作順序提醒收尾（編輯後按儲存再離開；切頁不自動存），不臆測前端實作。

## 面向切分定案（研究結論）

**2 子面向，按「通則 how-to vs 個案現況」切**（優於需求初擬的「建立編輯 vs 對外曝光」主題切）：

1. **`物件操作引導`**（select=category）——建立/批次上傳（含失敗原因與通知中心）/編輯 vs 刊登差異/狀態機與各狀態能做什麼/儲存行為/對外顯示地址雙層/廣告頁可見性/招租店舖。8 案型 how-to 單 persona 分流（billing_setup_guide 先例）；對外曝光案量太小（3 型）不值獨立四件套，併入後 R3.4 條款成立（併面向不減內容）。
2. **`物件現況診斷`**（select=api jgb_estates）——「這個物件為什麼不能建約/現在什麼狀態/租客看得到嗎」個案型：查得到 → status 轉譯＋contract_required_fields 判建約缺欄；查不到 → 非刊登中口徑（弱信號紅線：不斷言刪除）。secondary_call attach show 深欄位。

## 補充驗證（任務 1.3，2026-07-04 真資料）

- **status 位元互斥性成立**：preview 三組（37305：125 筆 {8:110, 2:12, 4:3}／20151：47 筆 {8:28, 2:10, 4:9}／key 全域：200 筆 {8:84, 2:103, 4:13}）DISTINCT 皆 ∈ {2,4,8}，無組合值——design Issue 3 銷案，builder 未知值標注為純防禦。
- **兩軸模型真資料印證**：status=8（租約中）物件大量出現在 is_open=1 清單——租約中仍可刊登中，證實兩軸獨立。
- **實作偏差**：`jgb_estates` 鍵為修繕報修表單（form_schemas jgb_repair_create）現役——面向改用新鍵 `jgb_estate_status`（拉頁+token 過濾+sentinel+status_zh 轉譯欄）＋`jgb_estate_detail`（空 id 優雅降級），舊鍵零改動。

## 風險與緩解

| 風險 | 緩解 |
|---|---|
| 「物件」與合約域 title 搜尋鏈誤吸（五域最高） | 錨點用操作強詞（刊登/批次上傳/招租店舖）；路由測試最小對比對（「這份合約的物件地址錯了」→合約域 vs「物件要改對外顯示地址」→本域） |
| estates API 只回刊登中 → 現況診斷半盲 | 「查不到」口徑紅線（不斷言）＋G-E1 記缺口；知識層補齊非刊登場景通則 |
| 既有 2026-06 批知識單軸口徑 | 逐筆複核表（存廢工序），兩軸模型為準 |
| full_address 個資 | builder/answer 只出 title＋display_address，完整地址不出口＋單元負斷言 |
