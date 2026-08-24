# Runtime-binding evidence source inventory：結果

> 2026-08-24｜語言 zh-TW｜依 `evidence-source-qualification-frozen.md`（E1–E6＋F-1～F-5，凍結於 `ad12269`）執行
> 執行方式：**唯讀**。未改任何檔、未進 seam、未產測資、未動 ruler、未重跑 cohort。
> 證據身份：`inventory_blind = false`｜`prior_exposure = declared`｜
> `candidate_selection_before_protocol = false`｜`qualification_rule_pre_frozen = true`

## 結論摘要

```text
QUALIFIED              3   （N1／N2／N3，全部為 newly-discovered，全部在**平台 external API** 側）
REJECTED               9
INSUFFICIENT_EVIDENCE  3   （N5／N7／N11）
```

**依 F-5 分開統計**：

```text
prior-exposed（7 項）      QUALIFIED 0 ｜ REJECTED 7 ｜ INSUFFICIENT 0
newly-discovered（8 項）   QUALIFIED 3 ｜ REJECTED 2 ｜ INSUFFICIENT 3
（另 N10／N12 為「掃查無 source 可判」，不計入 disposition 統計）
```

⚠️ **結果並非由先驗曝光項目主導**：G1 期間看過的七項**全數 REJECTED**，
三個 QUALIFIED 全部來自本輪新查的 `External\BillApiController` 與其權限中介層。

⚠️ 依 E5 對稱條款：QUALIFIED 只代表**合格的 applicability evidence source**，
**不代表** `Face SHALL enter`——後者仍屬 R2／authority design，不在本輪。

---

## Audited scope 覆蓋情形（F-2，「查過無所獲」也記）

| | ① entry seams | ② API registries | ③ state machines | ④ DB constraints | ⑤ request schema | ⑥ session state | ⑦ caller assertions | ⑧ execution bindings |
|---|---|---|---|---|---|---|---|---|
| **L1** 對話入口 | ✔ N8 | — | — | — | ✔ 無所獲 | ✔ N7 | ✔ 無所獲 | — |
| **L2** 檢索/決策 | ✔ N8 | — | — | — | — | — | — | — |
| **L3** 面向設定 | ✔ P4 | ✔ N6 | ✔ N10（無所獲） | ✔ P4／P5 | — | — | — | ✔ N6 |
| **L4** 引擎狀態 | ✔ N9 | — | ✔ N11 | ✔ N7 | — | ✔ N7 | ✔ N9 | ✔ N6 |
| **L5** API client | — | ✔ P6 | — | — | ✔ 無所獲（純 Python 預設值） | — | ✔ 無所獲（`_validate_identity` 僅檢查非空） | — |
| **L6** 平台 authority | — | ✔ N1／N2／P3 | ✔ P1／P7 | ✔ N12（全庫掃描，見下） | ✔ N1／N2 | — | — | ✔ N1／N2 |
| **L7** 身分/斷言 | — | — | — | — | — | — | ✔ N3／N4／N5 | ✔ N3 |
| **L8** chatbot 持久層 | — | — | — | ✔ N7（`form_sessions`） | — | ✔ N7 | — | — |

```text
✔ 已掃    ✖ 未掃    — 該格不適用
```

### F-4 停止規則：**scope 已補完**（程序義務，非研究選擇）

初版留下三個未掃格。業主裁定：**凡本來就在 `ad12269` 凍結 scope 內者，依 stopping rule 必須補完**
——`L3/L4 × ③ state machines` 與 `L6 × ④ DB constraints` 皆在 F-1／F-2 的凍結範圍內，
故已於本版補掃（N10／N11／N12），**非**看到結果後才擴大範圍。

```text
✅ 本輪**未**在找到第一個 QUALIFIED 後停止——N1 之後仍續掃 L7／L8，並回頭補完三個未掃格
✅ 正面結論（3 個 qualified source）成立
⚠️ 負面結論的**界線**：可說「在已完成的 audited scope 內未再找到其他 qualified source」，
   **仍不得**寫成「production 沒有」——F-1 已自陳本 scope 未證明覆蓋整個 relevant authority surface，
   且 legacy 表（含 `bills`）的建表 DDL 不在 repo，該部分**永遠**只能記為查不到（≠ 不存在）
```

### 補掃結果（N10／N11／N12）

| id | source | 掃查結果 | disposition |
|---|---|---|---|
| **N10** | L3 × ③：面向設定是否宣告狀態機 | **無所獲**。`answer_mode`／`topic_scope` 皆為帶 code 預設的設定值（`services/conversational_config.py:29,38,115,119`），無狀態與轉移定義。另見 `by_category` 索引（`:161-167`）＝以 `topic_scope.category` 建的分類路由索引 | 無 source 可判；`by_category` 併入 **N8**（E4 不成立，分類命中） |
| **N11** | L4 × ③：會話狀態機 | `form_sessions.state` 的轉移**由 SQL WHERE 子句守衛**：完成動作為 `UPDATE ... SET state='COMPLETED' ... WHERE ... AND state='COLLECTING'`（`services/conversational_engine.py:488-489`；載入與建立見 `:450,471,481`）。即「非 COLLECTING 不能被完成」為 runtime 強制 | **INSUFFICIENT_EVIDENCE（E3）**——與 N7 同因：講的是會話生命週期，非新 entry 的 applicability |
| **N12** | L6 × ④：jgb2 全部 migration 的 enum／check 約束 | **決定性負面**：`grep -rc "->enum(" database/migrations/*.php` **零命中**；`CHECK (` 亦零命中；`App\Bill` **無** `$casts` 定義 | 無 source 可判。⚠️ 此結果**強化** P1／P2／P7 的 E1 判定：該層**根本不存在** DDL 級枚舉約束，故常數集無論如何都不會是 enforcement |

⚠️ N12 是本輪唯一一個**可以說得比較滿**的負面：在 repo 內**所有** migration 中，
enum／check 約束的數量是 **0**。但它仍**不涵蓋** legacy 表的原始 DDL。

---

## Qualified sources（逐條 E1–E6）

### N1｜單筆帳單的「存在 ＋ 歸屬 ＋ active」解析

```text
source            External\BillApiController@show（app/Http/Controllers/External/BillApiController.php:203-231）
                  路由 routes/api.php:155 GET /external/v1/bills/{bill_id}
runtime semantics 以 where('id',$billId)->where('owner_role_id',$roleId)->where('active',1)->first()
                  查詢；不符即 404「帳單不存在或無權存取」
discovered_from   L6 × ②／⑤／⑧
prior_exposed     false
```

| | 判定 | 依據 |
|---|---|---|
| **E1** runtime binding | ✅ | 由**實際資料存取路徑**強制，非常數命名或文件宣告；不符條件時 HTTP 404 |
| **E2** pre-entry availability | ✅ | 無狀態 GET，只需 `role_id`＋`bill_id`；`role_id` 於請求進入時即有（`routers/chat.py:3843`，缺值時由 `vendors.settings->>'jgb_role_id'` 補，`:4114-4124`）。⚠️ **目前實作在進場後才呼叫**——這是接線缺口，非可得性缺陷 |
| **E3** candidate relevance | ✅（限 bill-keyed Face） | 「此 query 指涉的帳單在本 role 下真實存在且有效」直接對應診斷面向的 instance 前提。⚠️ 對不以 bill 為鍵的 Face **無語義** |
| **E4** information independence | ✅ | 不是 similarity、不是 category；來自**另一個系統的資料存在性與歸屬**，與檢索分數正交 |
| **E5** no false closed-world | ⚠️ 條件成立 | 404 訊息**把「不存在」與「無權存取」合併**（`:230`）。故 404 **MUST** 映射為 `unknown`，**不得**映射為 `not_applicable` |
| **E6** provenance | ✅ | 產生者＝jgb2 平台；擁有者＝平台 bills 表；語義＝「該 role 擁有的 active 帳單」 |

**disposition：QUALIFIED**（E5 附強制條件）

### N2｜以識別條件解析「指涉基數」（0／1／多）

```text
source            External\BillApiController@index（同檔 :19-105）｜路由 routes/api.php:83
runtime semantics role_id 必填（缺→400）；可加 user_id／contract_id／bill_id／status／type／
                  month(YYYY-MM，轉 date_expire 區間比對，:76-85)；一律 where('active',1)
                  ＋ owner_role_id 或 viewer 圈定；回傳筆數即「此識別條件在本 role 下解析到幾筆」
discovered_from   L6 × ②／⑤／⑧
prior_exposed     false
```

| | 判定 | 依據 |
|---|---|---|
| **E1** | ✅ | 篩選條件由 SQL where 子句強制；`month` 另有 `preg_match('/^\d{4}-\d{2}$/')` 格式強制 |
| **E2** | ✅ | 同 N1，無狀態 GET。⚠️ 客戶端已有識別解析器 `bill_ref`（`services/jgb_system_api.py:108-131`），但目前於**進場後**才使用 |
| **E3** | ✅（限 bill-keyed Face） | 「解析到 ≥1 筆」是 instance-specific 的**正向**證據；「0 筆」只是 unknown（見 E5） |
| **E4** | ✅ | 基數來自平台資料，與檢索分數／分類字串正交 |
| **E5** | ⚠️ 條件成立 | 0 筆可能是「真的沒有」也可能是「識別條件抽取錯誤」→ **MUST** 映射 `unknown` |
| **E6** | ✅ | 同 N1 |

**disposition：QUALIFIED**（E5 附強制條件）

⚠️ 這一項**正是本輪 positive-proof 方向的具體對應物**，且平台側已有既成模式：
`grounding_scope.search_params` 的註解自陳「**API 驗證式（後端當裁判）**：明列多組搜尋嘗試，
依序試、第一組有結果即止」（`services/conversational_engine.py:868-870`）。
⚠️ **但該模式目前只在進場後用於挑候選**，**未**作為 applicability evidence 使用。

### N3｜成員可見性探測（`viewer_user_id`）

```text
source            App\Http\Middleware\ExternalViewerScope（:20-37）＋ App\Support\VisibleScope::resolve
                  ＋ Bill::queryThisUser（BillApiController@index:41-47）
runtime semantics 帶 viewer_user_id → 解析該成員在該 role 的權限主體並圈定查詢；
                  index 的 bill_id 篩選註解自陳其用途：「搭配 viewer_user_id 做『某成員看不看得到
                  這張帳單』的可見性探測：有回=看得到、空=看不到」（:62）
discovered_from   L7 × ⑦／⑧
prior_exposed     false
```

| | 判定 | 依據 |
|---|---|---|
| **E1** | ✅ | 圈定由 controller 對自身 query 實際套用；解析失敗直接回錯誤（middleware `:26-31`） |
| **E2** | ✅ | 同為無狀態 GET |
| **E3** | ✅（限可見性語義的 Face） | 直接對應「租客看不到某一筆帳單」這類責任；⚠️ 對操作可否類 Face 無語義 |
| **E4** | ✅ | 與 similarity／category 完全無關 |
| **E5** | ✅ | 「空＝看不到」是該探測**自身定義的語義**，非由沉默推論；仍不得外推到「該 Face 不適用」 |
| **E6** | ✅ | 產生者＝平台權限層；語義＝該成員主體在該 role 下的可見範圍 |

**disposition：QUALIFIED**

---

## Rejected（附**哪一條**不成立）

| id | source | prior_exposed | 不成立的條件 | 依據 |
|---|---|---|---|---|
| **P1** | `App\Bill` 狀態／型態常數（`app/Bill.php:40-79`） | true | **E1** | class constant 是命名慣例非寫入端 enforcement；`bills` 建表 migration 不在 repo，DDL 層 enum／check 查不到（G1 已判 INSUFFICIENT，本輪同判 E1 不成立） |
| **P2** | `App\BillActivityLog::ACTION_*`（`:42-44`） | true | **E1** | `action` 欄為 `string(50)`（migration `:27`），非 enum；docblock 自陳只涵蓋部分異動 |
| **P3** | web route registry ＋ `BillController::batch` switch 分派 | true | **E3** | 它界定「有哪些 endpoint」，對**這個 query 是否適用某 Face** 無語義（每個 query 都一樣） |
| **P4** | 面向設定列（`conversational_config.py:15,23`，`knowledge_base` 的 `category='對話規則'`） | true | **E1** | 面向由後台資料列定義、零改程式；無 constraint 強制其內容 |
| **P5** | `entity_noun`（`conversational_engine.py:941`） | true | **E1** | 自由字串設定值，且有 code 預設 `"合約"`；非 enforce 的事實 |
| **P6** | `jgb_system_api` client 方法面（2062 行） | true | **E3** | 界定「對話端能呼叫什麼」，**每個 query 都相同**，無鑑別力 |
| **P7** | OBS-1：`bills.status` 常數含「待對帳／待查收」（`app/Bill.php:40-46`） | true | **E1** | 同 P1。⚠️ 依 `incidental-observations.md` 規約，本次為其**重新受審**結果，未因先前記錄取得任何優先地位 |
| **N4** | `ExternalApiAuth` 的 `_resource`／`_action` 權限（`:69-82`） | false | **E3** | 權限**確實被強制**（403，E1 ✅），但**每個 query 對同一把 key 恆定**——與 impostor control 同型，無鑑別力 |
| **N8** | `decision_layer.facet_entry_eligible`（`services/decision_layer.py:191-199`） | false | **E4** | 判準＝`similarity >= form_trigger_threshold`＋分類命中，**正是** R1 §1.2 已 REFUTED 的形態 |

⚠️ **N4／P3／P6 三者是同一種錯誤形態**：runtime 確實 enforce，但**不隨 query 改變**。
E1 過而 E3 不過——這正是 E3 存在的理由。

---

## Insufficient evidence（不得預設倒向任一側）

| id | source | prior_exposed | 卡在哪一條 | 說明 |
|---|---|---|---|---|
| **N5** | `ExternalApiAuth` 的 role 白名單（`:87-110`） | false | **E3** | E1 ✅（403 強制），但程式自陳為 **opt-in**：「有設白名單才強制；沒設＝不限團隊」。是否具鑑別力取決於**本系統 API key 實際是否設定白名單**——那需查 production 資料，本輪唯讀範圍內無法判定 |
| **N7** | `form_sessions`（`database/migrations-legacy/create_form_tables.sql:43-56`） | false | **E3** | `form_id ... REFERENCES form_schemas(form_id)` 是**真 FK**（E1 ✅），但它證明的是「有一個進行中的面向會話」＝**續輪**語義，對「**新的** entry 是否適用」的語義未定。⚠️ 另注意 `state VARCHAR(50)` 無 enum、`collected_data JSONB` 無約束，面向鍵 `config_key` 就存在該 jsonb 內（`routers/chat.py:445`）——即「哪個面向在進行」本身**不受約束** |

---

## 另記：一個必須拆開看的 source（避免重蹈 G1 的常數陷阱）

**N6｜面向自帶的可執行 API binding**（`grounding_scope.endpoint／params／search_params`，
`services/conversational_engine.py:864-870`）——**必須拆成兩件事**：

```text
binding 宣告本身   「本面向使用端點 E、參數 P」
                   → 存在後台可編的設定值中，**無 enforcement**
                   → **E1 不成立** → 作為 source 判 REJECTED

binding 執行結果   「以 E×P 在本 role 下打回來幾筆」
                   → 由平台 SQL 強制 → **E1 成立**
                   → 但這個事實**就是 N1／N2**，N6 只是它的**載體**，不是獨立 source
```

⚠️ 這與 G1 對 `App\Bill` 常數的判定是**同一個判準**：宣告 ≠ 強制。
本輪特意把它寫出來，避免下一輪把「Face 宣告了什麼」誤當成 runtime-binding evidence。

---

## 依事前綁定，這批結果指向哪裡（**只陳述綁定，不設計 member**）

協議事前寫定的四種結局中，本輪落在**第二種**：

```text
qualified source 主要是 **Face 自己可證明的 executable facts**
（Face X 可查的 entity／state、machine-enforced precondition）
→ 可能給 **D3** 新 shape
```

依據：N1／N2／N3 全部是**平台側可執行、per-query 變動的事實**，
且其取用方式與「某個 Face 綁定哪個查詢」相關，而非 routing／request 側的解析產物。

⚠️ **request 側目前未產出任何 qualified source**：
L1／L5 的 ⑤／⑦ 掃查結果為無所獲——`_validate_identity` 僅檢查非空
（`services/jgb_system_api.py:48-50`），`role_id` 為呼叫端**斷言**且平台白名單為 opt-in（N5 未定）。
故本輪**不**支持「demand proof × offer proof 組合 member」這一結局，**也不排除**它——
D1 側需要的是新的 information shape，本輪未找到。

## 本輪**未**回答（協議輸出限制）

```text
❌ 未設計任何 member（D1／D3／組合皆無）
❌ 未宣稱 positive-proof architecture 成立
❌ 未改任何 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
⚠️ scope 已補完（N10／N11／N12），故**可**說「在已完成的 audited scope 內未再找到其他 qualified source」；
   **仍不得**說「production 沒有」——legacy 表 DDL 不在 repo，且 F-1 未證明覆蓋整個 authority surface
❌ 未動 production；未產測資；ruler 0.058928 仍凍結未用
```
