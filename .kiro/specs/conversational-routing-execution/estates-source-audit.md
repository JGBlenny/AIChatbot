# `/estates` 端點盤查（jgb2 原始碼逐條對照）

> 2026-08-25｜語言 zh-TW｜**零 OpenAI 呼叫、未碰 staging／production**
> 來源：`jgb2/app/Http/Controllers/External/EstateApiController.php`（checkout `master 5eaebb7f0a`）
> 依 `transport-migration-inventory.md` §7 的六步協議執行；§8 第 4 項。

涵蓋三個註冊鍵、兩個真端點：

```text
jgb_estate_status   get_estate_status   GET /estates       EstateApiController@index
jgb_estates         get_estates         GET /estates       同上（修繕報修表單現役鍵，語義不同）
jgb_estate_detail   get_estate_detail   GET /estates/{id}  EstateApiController@show
```

## ① 投影鍵集合（`formatEstate()`）

列表形狀 **52 鍵**，含四個 `*_comment` 說明鍵（`role_id_comment`／`team_id_comment`／
`team_name_comment`）與衍生鍵（`url`、`avatar`／`gallery`／`floor_plan` 走 CDN 組址）。
單筆詳情（`formatEstate($estate, true)`）**額外** 5 鍵：
`description`／`traffic`／`nearby`／`notes`／`contract_required_fields`。

`contract_required_fields` 的形狀（`formatContractRequiredFields()`）：
`{all_filled, fields:[{field,label,is_filled}]}`，**一律列出 16 個必填欄位**
（8 基本 ＋ 4 地址 ＋ 4 顯示地址），`all_filled = empty(fail_fields)`。

## ② 恆定 where

```text
index  active=1 AND is_open=1（:52-53）＋ apiKey->applyAccessibleEstateScope($query)
show   active=1 AND is_open=1（:121-124）＋ apiKey->canAccessEstate($id) 否則 403
```

**`is_open=1` 是這支端點最重要的語義**：只回招租刊登中的物件。這正是物件面向
「查無＝非刊登中」sentinel 口徑的來源（`services/jgb/estates.py`）。

## ③ 參數解析語義（`applyFilters()`）

```text
status        where status = (int)          use_for     **僅** residential／business／parking_space
city_id       where city_id = (int)         district_id where district_id = (int)
rent_min/max  where rent >= / <= (int)      updated_after where updated_at >= (原字串)
user_id       where user_id = (int)         role_id     where role_id = (int)   ← 是篩選，不是授權
keyword       跳脫 % 與 _ 後 title LIKE '%kw%'
```

## ④ 過度寬鬆處（本次抓到的偏差）

```text
D1  投影外欄位  舊 _mock_get_estates 每列都有 `estate_room_number`——
                該欄只存在於 /repairs（RepairApiController.php:323），/estates 從不回它。
                **已移除**，並加投影 guard。
D2  keyword     舊替身比 `title` **或** `full_address`；production 只比 title。
                → 用地址關鍵字在替身查得到、在 production 查不到。**已修**。
D3  role_id     舊替身把傳入的 role_id **寫進每一列**，等於任何 role 都命中。
                production 是 where 篩選。**已修**（fixture 固定 role_id=20151）。
D4  is_open     舊替身完全沒有這道恆定 where，會回 production 查不到的物件；
                連帶 sentinel（found:False）分支在替身上永遠走不到。
                **已修**：fixture 新增 54305（is_open=0）專門證明過濾會咬。
D5  分頁排序    舊替身寫死 per_page=10／total_pages=1／has_more=False，且完全不排序。
                **已修**：預設 50、上限 200、ceil(total/per_page)、has_more=page<total_pages；
                排序白名單 id／created_at／updated_at／rent／size，其餘回退 updated_at desc。
D6  詳情形狀    舊替身回 `contract_required_fields = {all_filled:True, fields:[]}`——
                空 `fields` 是 production 產不出來的形狀。**已修**為 16 欄完整輸出；
                並補上 show 專屬的 description／traffic／nearby／notes（值為 None，不假造）。
```

## ⑤ 分頁與排序

```text
DEFAULT_PER_PAGE=50｜MAX_PER_PAGE=200｜page=max(1,(int)page)
total_pages = ceil(total/per_page)  ← **不特判 total=0**（結果同為 0，與 contracts 的寫法不同但同值）
has_more = page < total_pages
sort_by 白名單外 → updated_at；sort_direction 非 'asc' → desc
```

## ⑥ 仍未涵蓋（mock 結構上證不到，只有真 API 會現形）

```text
· apiKey->applyAccessibleEstateScope／canAccessEstate 的金鑰層圈定
· show 的 403（無權）與 404（不存在／非刊登中）之分——我方一律折疊為 success:False
· Cache::remember 5 分鐘（show 與 getTeamName 各一）造成的資料陳舊
· mapping.countries：由 countrys／citys／districts 三張表組出，替身不輸出 mapping 鍵
· 真實標題分佈（口語多詞配不中 title LIKE 是既有已知問題，非本次新增）
· updated_after 篩選：production 有，我方 adapter 從不傳
```

## 附帶查核：status 枚舉正確

`services/jgb/estates.py` 的 `ESTATE_STATUS_ZH`（1 未刊登／2 刊登中／4 洽談中／8 租約中）
與 `jgb2/app/Estate.php` 的 `ESTATE_READY=1`／`ESTATE_PUBLISHED=2`／
`ESTATE_HAVE_CONTRACT=4`／`ESTATE_CONTRACT_SIGNED=8` **逐值相符**，本次無需修改。
⚠️ 但 PHP 原始碼註記 2／4／8 皆為「公開狀態」——
**查得到 ≠ status=2**，兩軸（合約軸 status × 刊登軸 is_open）不可壓成一軸。

## 行為變更提醒

D3 修好之後，mock 模式下用**非 20151** 的 role_id 查 `jgb_estates`（修繕報修表單現役鍵）
會拿到空清單——這是 production 本來就會有的行為，不是回歸。
若要讓某個 demo role 查得到，改 fixture 的 `role_id`，**不要**把篩選改回 echo。

## 尚未做的事

estates **未**遷入 `JGBMockTransport`（`MIGRATED_ENDPOINTS` 仍是 bills／bill_detail／contracts）。
本次只把方法級 mock 的資料與過濾語義對齊原始碼；遷移是另一個 slice。
