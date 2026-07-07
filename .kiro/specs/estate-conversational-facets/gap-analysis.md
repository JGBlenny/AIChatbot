# 落差分析：estate-conversational-facets

> 分析日期：2026-07-04　基準：requirements.md（R1–R8）＋現行 codebase（四域全收案後）＋jgb2 真碼 gap 級盤查
> 定位：提供資訊與選項，不做最終決定；〔研究〕標記者入設計階段研究清單。

## 〇、對需求假設的三個修正（gap 盤查推翻/裁決）

1. **「零成塊知識」假設錯誤**——知識庫已有 28+ 筆物件相關知識：`categories='物件管理'`（3428-3434：狀態定義/刊登上架/下架/批次匯入/VR/自訂標籤/Dashboard）＋`條件診斷：物件`（3505-3507：為什麼不能新增/突然全部下架/不能建立合約）＋未標旗（3862 一物件多合約、3894 修改不影響既有合約快照原則、3895 刊登租金調整帳單不變）。**工作性質從「全新產製」變「盤點補標＋補缺」**（同前四域 backfill 工序）。
2. **estates 對外端點已存在**——`GET /external/v1/estates`＋`/estates/{id}`（routes/api.php:33,41，External\EstateApiController），與 meters 同群組同 middleware。**R4 輕 grounding 直接點亮**，不是選配了；G 趨近零（IoT 之後第二個）。
3. **狀態機已在 gap 級真碼裁決**（官方兩篇矛盾文章正式作廢）——見下節。

## 一、jgb2 真碼裁決（gap 級，file:line）

| 問題 | 真碼裁決 | 證據 |
|---|---|---|
| 物件狀態機 | **兩條獨立軸**：合約軸 status 位元 1=READY(未刊登)/2=PUBLISHED/4=HAVE_CONTRACT(**洽談中=有約未簽**)/8=CONTRACT_SIGNED(租約中)；刊登軸 `is_open`/`sell_is_open` 獨立旗標 | Estate.php:57-64、1055-1056、2369-2371 |
| 「洽談中」定義 | status==4：已綁合約但合約未走到簽署完成（contract.status < SIGNED） | Estate.php:4654-4674、2750-2810（getSticker） |
| 洽談中可做什麼 | **可編輯**（edit 無狀態 gate，只驗權限）、**不可刪**（有有效合約擋刪）、屬公開狀態 | EstateController.php:4811-4848、10456-10485 |
| 有約後編輯限制 | **無欄位鎖定機制**——合約存在只擋「刪除」；客服案「有約改不了」屬誤解/UI 操作問題，口徑走快照原則（3894 已有） | EstateController.php:4842-4848、10468-10476 |
| 建約前提 | 挑物件強制 status=2（刊登中）——「為什麼不能建立合約」真因（3861/3507 已有知識，補標即可） | EstateController.php:279-283 |
| 刪除影響 | 擋刪條件三：刊登中、有有效合約（「請先將合約解除」）、有 IoT 綁定；C-2 案「刪除後歷史合約會消失嗎」→ 有約根本刪不了 | EstateController.php:10456-10485 |
| 對外顯示地址 | **雙層行為證實**：對外廣告頁/Google Map 用 `display_address` 系（completeDisplayAddress），對內後台用 `address` 系（completeAddress）——文章口徑正確，客服案「改了還顯示完整地址」= 看的是後台 | Estate.php:3455、3466-3473、7975；ListingController.php:196 |
| 批次上傳 | preview/confirm 三段式＋專用 validators＋6MB 上限；need_subscription＋premises_limit middleware（額度不足也會擋——3456 知識已有） | EstateController.php:5987、11450-11508、248-256；Services/ImportPreview/Validators/ |

## 二、現況元件盤點（AIChatbot 端）

| 元件 | 現況 | 對本 spec 的意義 |
|---|---|---|
| 面向化底座全套 | 四域實戰 ×4（母子分類、三層脈絡、face、secondary_calls、deterministic_id、候選、收斂保底） | 純資料複製 |
| **category_config id 61 `物件管理`** | **已存在為頂層分類**（parent_value 空、is_active、10+ 筆知識已掛） | 母分類**重用不新建**；只補子分類＋parent 關係〔研究：選項見§四〕 |
| `條件診斷：物件`（id 68） | 舊條件診斷體系 3 筆（3505-3507），內容與新面向重疊（狀態機/建約前提/下架） | 補標掛新子面向 or 保留單發〔研究〕 |
| registry／wrapper 模式 | api_call_handler.py:59-75（jgb_contracts/jgb_meters 等） | `jgb_estates` 照 get_meters 模式新增，小工作 |
| 路由回歸 harness | tests/integration/conversational/test_facet_entry_routing_req.py（四域 70 案） | 直接擴物件案例 |
| help 素材 | 14 篇已抓（本 spec materials/help/，含 2025-12 點交快找新文） | 知識工程直接開工 |

## 三、逐需求落差

- **R1 底座**：落差＝純資料，但母分類**重用既有 61**——子分類 migration 寫 parent_value='物件管理'，不新建母列〔研究：display_name 是否要改；既有 10+ 筆知識的 categories 已是母值，天然吃母層脈絡〕。
- **R2 建立與編輯引導**：落差＝系統脈絡＋persona＋知識補缺。狀態機口徑已裁決（兩軸模型是脈絡核心——文章單軸模型是矛盾根源）；「資料未儲存」屬前端操作行為〔研究：無真碼可盤則知識以操作順序提醒收尾〕；批次失敗原因集〔研究：validators 逐條盤〕。
- **R3 對外曝光**：落差＝知識補缺（display_address 雙層已裁決、招租店舖入口 UI 路徑需以現行版驗證 2021 文章〔研究〕）。面向數選項見§四。
- **R4 輕 grounding**：**端點存在，落差＝wrapper＋config**。〔研究核心：EstateApiController@index/show 白名單欄位——status/is_open/display_address 露不露出？query 參數有無 keyword？決定收斂能答「這個物件現在能不能刊登/建約」到什麼深度〕
- **R5 單發知識**：報表匯出/進階搜尋/點交快找——純產製；VR 既有 3433 知識**與 R5.2「不做 VR 知識」衝突**〔研究：3433 存廢——傾向保留但改導 istaging/客服口徑〕。
- **R6 知識工程**：existing 28+ 筆盤點補標為主、新產製為輔（預估新知識量比 IoT 更少）。
- **R7 誤吸邊界**：「物件」一詞在合約域 title 搜尋鍵/建約引導（3861 掛建約引導）高頻——雙向點名測試是重點；「物件綁電表」IoT、「經理人」帳號域同前。
- **R8 測試**：照模式擴，無新落差。

## 四、實作策略選項

| 決策點 | 選項 A（傾向） | 選項 B | 權衡 |
|---|---|---|---|
| 母分類 | **重用 id 61 `物件管理`**，補 2 子分類 parent 關係 | 新建母分類、遷移舊標 | A 零遷移、既有知識自動吃母層脈絡；B 命名自由但要動 10+ 筆資料，無收益 |
| 面向數 | **2 面向**（建立編輯／對外曝光） | 1 面向合併 | 案型受眾同（都是 PM）、對外曝光案量小——若脈絡字數擠得下，B 反而少一套四件套〔設計定案；R3.4 已保留併面向條款〕 |
| 條件診斷 3 筆 | 補標掛新子面向（雙分類共存） | 保留純單發 | A 讓「為什麼不能建約」進面向多輪；B 零風險但面向少了診斷入口 |
| grounding 深度 | index+show 白名單夠就做「物件現況直答」 | 白名單太窄則純 category | 〔研究後定〕存在性驅動，缺欄位記 G |

## 五、設計階段研究清單

1. `External\EstateApiController` index/show 白名單欄位與 query 參數（R4 深度定案）。
2. ImportPreview validators 失敗原因集（R2.5 批次排查分支）。
3. 招租店舖/對外首頁現行 UI 入口驗證（2021 文章 vs 現版）。
4. 既有 28+ 筆知識逐筆存廢/補標表（含 3433 VR 口徑改寫、3505-3507 掛面向）。
5. 「資料未儲存」前端儲存行為確認（無真碼則知識收尾）。
6. 面向數 2 vs 1 以脈絡字數與案型密度定案。

## 六、風險

- **誤吸風險最高的一域**：「物件」是合約域識別鏈的日常詞（title 搜尋鍵）——路由測試必須含「這份合約的物件地址錯了」（應進合約/資料異動出口）vs「物件改地址」（本域）這類最小對比對。
- 素材年代：2021 文章 UI 路徑大概率過時（IoT 先例：泛稱 vs 官方路徑），知識產製一律以現行驗證為準。
- 既有 3428-3434 批知識產製於 2026-06（JGB 系統知識庫 121 筆時期）——口徑品質待逐筆對狀態機裁決複核（單軸描述者要改兩軸）。
