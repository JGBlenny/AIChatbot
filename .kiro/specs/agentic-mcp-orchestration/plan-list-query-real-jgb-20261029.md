# 呼叫端對齊 JGB staging 實際端點：清單數量查詢與三個按確認才失敗的寫入（2026-10-29，短計畫，已收案（DSP-126））

本檔同時是規則與清單檔：§1 規則、§5 清單，業主核可後一起凍結。

- **業主裁定（2026-10-29）**：「我要同步進行」＝開工；「改走快速修正：不做資安審查，也不跑 verifier」。寫入改帶 `viewer_user_id` 屬成員範圍（授權），依此裁定不送資安審查；收案證據＝L1、L2、L4、L6、L7 單元與腳本、L3 改前改後、M0，完成報告標「未經 verifier」。

## 第一段：終點、廣度、改前對照

- **目標文件**：本檔 §5（沒有上層目標文件；本片由 jgb2 視窗 staging 情境測試的 F1、F2 觸發：`/Users/chenqinghuang/dev/work/jgb2/acceptance/13290303502/user-scenario-test-20261029.md`「發現」節）。
- **終點量法**：清單與數量題組在「對齊真 JGB 的 mock」上的解決數（§5 L3）。
  - 現值：未量。依程式推論接真 JGB 時為 0：三支統計工具接真 JGB 一律回固定句（`jgb2_stats._mock_only`）；物件查詢沒有名稱就回查無（`jgb2.query_estates`）。
  - 本片預期：L3 題組 ≥ 80% 解決，錯筆 0（唯讀，不出卡）。
  - 同一目標前兩片：無（新目標，照實寫）。
- **廣度**：1 組資料（mock vendor 4；可用資料組只有這一組，全用）× ≥ 15 種輸入（5 類：未繳／逾期帳單、最近帳單（不帶狀態）、物件數與清單、執行中修繕、即將到期合約；每類 ≥ 3 種說法，含口語、簡稱、一句兩件事、只講一半）× 每題 1 次。
  - 輸入由不讀程式的代理撰寫，跑前凍結。
  - 改前、改後各跑一次並列。改前＝現行程式加 mock 對齊（等同真 JGB 的行為）。

## 1. 業主原話與規則

| ID | 條件 | 原話 | 讀法註記 |
|---|---|---|---|
| L-R0 | 修根層：同一機制涵蓋清單與數量四類，⛔ 依詞句加特例（例：看到「未繳」才塞狀態） | 2026-10-29「從根層修」「問題是? 你能修 是補丁嗎 ?」「快速處理 避免繁瑣流程」 | 「快速」讀為：短計畫、不走完整審查迴圈（DSP-115）；「根層」由 L-R0 的「⛔ 特例」檢查 |
| L-R1 | 清單與數量題接真 JGB 時改打 JGB 的列表端點，⛔ 再打 AIChatbot 自訂、JGB 沒有的三條路徑（`bills/summary/unpaid`、`repairs/in-progress`、`contracts/expiring`） | 同上；觸發事件 F1「這個月有哪些帳單還沒繳？」→「這項統計目前還不支援」 | — |
| L-R2 | 「目前有幾間物件」類問題回總數（與清單），⛔ 回「想處理哪一件事？」 | 觸發事件 F2 | — |
| L-R3 | mock 不再提供 JGB 沒有的端點；JGB 有的篩選，mock 照同一組參數實作 | 主會話（量尺漏洞：M0、OV 都在 mock 上過，所以沒抓到 F1） | 主會話加的規則，業主可刪 |
| L-R5 | 接 staging 時，使用者按了確認的寫入不會因為我方打了 JGB 沒有的路徑或欄位形狀而失敗；JGB 沒開的動作在出卡前就說 | 2026-10-29「所以呢 ? 還有其他的吧」「需要開的 api 都列給 JGB」 | 主會話讀法：「其他」＝同一成因（呼叫端沒對齊 JGB 實際端點）的其他位置 |
| L-R4 | 分工照 DSP-091：AI 讀出條件，程式驗值、決定打哪支端點、帶哪些參數 | CLAUDE.md「對話線分工」 | — |

## 2. 目標形態

- **依據**：DSP-091 分工表「唯讀查詢的查詢與篩選（依 AI 理解出的條件；AI 自呼工具為後備）」由程式決定。業界依據沿用 DSP-091 已審原文，本片不另引。
- **對到本案**：
  - AI 只填封閉值域的條件，由程式驗值：狀態列舉、到期區間、物件。
  - 程式把條件換成 JGB 列表端點的參數，回「共 N 筆（＋總額）＋本頁明細＋還有幾筆」。
  - 值不在值域內 ⇒ 不送，改問客人。

## 3. 差距（現況，可重跑）

JGB 已照規格（`jgb-api-spec-for-jgb-20261015.md` §1「擴充既有讀取端點」）完成 #16～#18 與 #24：jgb2 commit `535b380873`（2026-10-28，「讀取擴充 #16 #17 #18 #24」），在 `origin/staging`，未進 `origin/master`。同檔 §7 第 1 點寫「JGB 定案後改呼叫端與解析」，AIChatbot 端沒做，所以 F1 是 AIChatbot 沒跟上。

擴充前 `origin/master` `b7f98c0d82` 的 `External/BillController.php` 已有單一 `status` 篩選、月份篩選（比對 `date_expire`）與 `total`；`External/EstateController.php` 不帶 keyword 也回 `total`。所以「這個月未繳」「有幾間物件」在 master 端點上就答得出來，固定句 `NOT_SUPPORTED_TEXT`「JGB 系統尚未開放這個查詢」從一開始就不成立。

| 類 | AIChatbot 現在打的 | JGB staging 現有（`origin/staging` `32b91847fa`） |
|---|---|---|
| 未繳／逾期帳單 | `GET /bills/summary/unpaid`（#16，JGB 沒有；`git show 0596af4d~1:rag-orchestrator/services/jgb_system_api.py | grep -n "summary/unpaid"`） | `GET /api/external/v1/bills`：`status`（2＝應到帳／待繳費、16＝已到帳…，`BillController::FILTERABLE_STATUSES`）、`date_expire_from`／`date_expire_to`；回 `count`、`total_amount` |
| 物件數與清單 | 沒名稱 ⇒ 查無（`grep -n "estates 無預設列表" rag-orchestrator/services/agent/tools/jgb2.py`） | `GET /estates` 不帶 keyword 回 `total`、分頁 |
| 執行中修繕 | `GET /repairs/in-progress`（#17，JGB 沒有） | `GET /repairs`：`status`（`Repair::statusLabels()`）、`estate_id`、`is_urgent` |
| 即將到期合約 | `GET /contracts/expiring`（#18，JGB 沒有） | `GET /contracts/status-overview`：`date_end_from`／`date_end_to` |
| 附照片報修（#22） | `create_repair` 有照片就送 multipart 檔案 `broken_photos[]`（`grep -n "broken_photos\[\]" rag-orchestrator/services/jgb_system_api.py`）；規格 §7 寫「JGB 的 multipart 上線前，接真 JGB 時不送 `broken_photos`」 | `External/RepairController.php` store 驗 `'broken_photos.*' => 'url'`，收檔會 422（推論，未實跑） |
| 改到期日（#23） | `PATCH /agent/v1/bills/{id}`，接真 JGB 沒有守衛（`grep -n "agent_patch_bill_due_date" rag-orchestrator/services/jgb_system_api.py`） | 沒有這條；`agent/v1` 另需 `internal_api_ip`＋`agent_auth`。按確認後必失敗（推論，未實跑） |
| 寫入成員身分（#24、規格 §0） | 寫入 body 送 `user_id`（`grep -n "data\[\"user_id\"\]" rag-orchestrator/services/jgb_system_api.py`） | 中介層 `ExternalViewerScope` 只認 `viewer_user_id`，未帶則不套成員範圍 |
| 修繕細項 | 父分類時 `item_id=None`（`grep -n "item_id=item_id" rag-orchestrator/services/agent/tools/action.py`） | store 驗 `'item_id' => 'required|integer'`；預設「其他」在 staging 有幾個細項：未查 |
| mock | 三支 proposed 端點都有替身（`git show 0596af4d~1:rag-orchestrator/services/jgb/transport.py | grep -n "jgb2-req#16"`） | — |

## 4. 路徑（本片範圍，每項對回規則）

1. **統計三支工具改打現有端點**（L-R1、L-R4）：`jgb2.stats.unpaid_bills`／`in_progress_repairs`／`expiring_contracts` 的工具名與參數不變（F1 顯示模型選工具正確，錯在後端端點），後端改成上表右欄，並拿掉 `_mock_only`。
   - 「本月」「逾期」換成 `status=2`＋到期區間。
   - 執行中修繕的狀態集合從 `Repair::statusLabels()` 定。
   - 「N 個月內」換成 `date_end` 區間。
2. **沒名稱 ⇒ 列表加總數**（L-R2）：`jgb2.query.estates` 沒有 `ref`／`keyword` 時打 `GET /estates`，回總數加第一頁，與 contracts 的 `fetch_default` 同一形狀。`jgb2.query.bills` 無條件時同樣回「共 N 筆＋最近一頁」，排序依到期日。觸發事件：jgb2 視窗 2026-10-29 第二場「列一下最近的帳單」也被回「這項統計目前還不支援」（trace `e78320da…`），模型選了未繳統計，說明無條件列帳單沒有可用出口。
3. **mock 對齊**（L-R3）：刪掉三支 proposed 替身；mock 的 `/bills`、`/repairs`、`/contracts/status-overview`、`/estates` 照 JGB 參數實作篩選與 `count`／`total`。
4. **按確認才失敗的三個寫入**（L-R5）：
   - 附照片報修：照規格 §7，接真 JGB 時不送照片檔，卡上寫明「照片暫時無法附上，修繕單照建」；JGB 開 multipart 後拿掉。
   - 改到期日：接真 JGB 時比照 #19～#21 的 `WRITE_NOT_SUPPORTED_TEXT`，出卡前就說尚未開放。
   - 寫入成員身分：寫入一律帶 `viewer_user_id`（JGB 定案的參數名，規格 §7 第 2 點）。
   - 修繕細項：先查 staging「其他」分類的細項數；多於一個時改成出卡前追問細項，⛔ 送 `item_id=None`。
5. **呼叫端契約檢查**（L-R3、L-R5）：腳本抽出 AIChatbot 打的每條 JGB 路徑與方法，對 jgb2 `origin/staging` 的 `routes/api.php` 比對；不在的必須掛在「接真 JGB 出卡前停」或「不發請求」的守衛下，否則非 0 退出。正對照：`GET /api/external/v1/bills` 必須比對到。部署前跑。
6. **測試**：單元測試涵蓋參數換算、驗值、分頁、上游失敗回固定句；改 `tests/unit/jgb/test_assistant_mock_contract_req.py` 對應的契約測試。

**相關但不在本次範圍**：
- J1 改期限（#23 PATCH）、J2 修繕附照片（multipart）要 JGB 開端點，另擬訊息交業主轉 JGB。
- J3 建物件／合約／手開帳單（#19～#21）：JGB 尚未做。規格要求在 `external/v1` 新做（`jgb-api-spec-for-jgb-20261015.md` §3），`origin/staging` `32b91847fa`、`origin/master` `b7f98c0d82` 的 `routes/api.php` 查無。`internal/v1`、`agent/v1` 既有的 `POST /estates`、`/contracts`、`/bills` 是產測試資料用，同節寫明不能沿用。

**偏離**：統計三支保留工具名，沒有併進 `jgb2.query.*`。理由是不動模型看到的工具集，避免牽動其他題型；代價是兩套查詢工具並存。

## 5. 驗收清單

| # | 規則 | 項目 | 觀察點 | 證據 | 類型 |
|---|---|---|---|---|---|
| L1 | L-R1、L-R4 | 單元：三支統計工具接真 JGB（`use_mock=False` 的替身 transport）時，送出的路徑與參數等於上表右欄；狀態與區間驗值；上游失敗回 `ERROR_TEXT`；不再出現 `not_supported` | pytest | 測試輸出 | 機制項 |
| L2 | L-R2、L-R3 | 單元：`query.estates` 無名稱回總數＋第一頁；mock 不再有三支 proposed 路由（正對照：`/bills` 仍在） | pytest | 測試輸出 | 機制項 |
| L3 | L-R0～L-R2 | 使用者層：§第一段題組，改前、改後並列；改後 ≥ 80% 解決，所報數字與 mock 資料逐筆相符 | 模擬客人經 MCP 對話 | 對話目錄＋計分 | 使用者層 |
| L4 | 迴歸 | 全量單元新增失敗 0（基準 9 筆）；M0 ≥ 50/52 | `scripts/run-tests.sh unit`；M0 56 場 | 輸出檔 | 機制項 |
| L6 | L-R5 | 單元：接真 JGB 替身 transport 下，附照片報修不送檔、卡上有說明；改到期日出卡前回尚未開放；寫入帶 `viewer_user_id` | pytest | 測試輸出 | 機制項 |
| L7 | L-R3、L-R5 | 契約檢查腳本在本片改完的工作樹上 0 筆未守衛的缺路徑；故意加一條假路徑時非 0 | 腳本輸出 | 輸出檔 | 機制項 |
| L5 | L-R1 | 上線後由 jgb2 視窗在 staging 重跑 F1、F2 的原句（業主部署後） | staging 畫面 | 該視窗紀錄檔 | 使用者層（上線後） |

## 廣度

| 項目 | 類型 | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照 |
|---|---|---|---|---|---|---|
| L1、L2、L4、L6、L7 | 機制項 | — | — | — | — | — |
| L3 | 使用者層 | 1／1 | ≥ 15 | 1 | 不讀程式的代理，跑前凍結 | 同題組在現行程式＋mock 對齊上 |
| L5 | 使用者層 | 1／1（staging 20151） | 2 | 1 | jgb2 視窗 | P0 試跑結果 |

上位驗收方式：無

## 6. 每次執行

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模與成本（跑前估計） |
|---|---|---|---|
| L3 改前 | 證明量尺看得到問題 | 改前不是約 0 ⇒ 量尺或推論錯，停下查 | ≥ 12 場 × 約 1 分（M0 每場實測），模擬客人約 15 萬 token（M0 56 場約 60 萬換算） |
| L3 改後 | 本片有沒有效 | < 80% 或有數字對不上 ⇒ 不收案 | 同上 |
| M0 | 有沒有打壞文字回合 | < 50/52 ⇒ 不收案 | 56 場約 16 分、約 60 萬 token |

- **停點**：L3 改前不是約 0；改動需要 JGB 改端點才能完成（⇒ 停、交業主）。
- **用量**：收案時報子代理 token 合計。

## 驗證紀錄（2026-10-29，未經 verifier）

- **收案裁定**：L3 改後未達 80%；業主 2026-10-29 選 A「照現狀收這一段」（出自主會話建議，等級 C），即降標收案：統計題接上真 JGB 先上線，「模型不查就反問」記為下一片。
- **L3**（計分 `~/jgb-archive/listquery-20261029/l3/score.md`，主會話自判、未盲判）：1 組資料 × 31 種輸入（5 類，不讀程式的代理撰寫，跑前凍結，sha `6bcda5e7…`）× 1 次。
  - 改前（`047f88a4`）0/31；改後（工作樹凍結，`runtime.py` `349fa5c5…`、`jgb_system_api.py` `e7ea7282…`）11/31（35%）。兩者都在真 JGB 模式，打同一個容器內假 JGB（改後替身）。
  - 改後所報數字全部與對照答案相符（`l3/oracle.md`）；唯讀、錯筆 0。
  - 未解決 20 題：13 題最後一回合 `tool_calls=0`（模型沒查就反問），同一批說法改前也反問。
- **L4 單元**：全量 9 failed／7459 passed，失敗清單與基準（`fix-r1/ud2b-unit-full-baseline.txt`）逐條相同（`~/jgb-archive/listquery-20261029/unit-full-after-l3.txt`）。
- **L4 M0**：51/52（`~/jgb-archive/listquery-20261029/m0/m0u_score.json`，受測物 `lqm0-after`＝同一份改後凍結，mock 模式）。唯一未過 W-R3_k1＝判分要「滴水」、卡上「一直滴」，與上次 M0 同一場同一原因。
- **L1、L2、L6**：`tests/unit/jgb/test_list_query_real_jgb_req.py` 等，含在上列全量單元內。
- **L7**：契約檢查腳本 24 條送出路徑：20 條 JGB 有、4 條在守衛下、0 條未守衛；注入假路徑時非 0。
- **L5**：未做，待業主部署後由 jgb2 視窗在 staging 重跑 F1、F2 原句。

## 後補清單

1. 唯讀清單題「要不要查」仍由模型決定，13/31 沒查就反問（L3 02～04、06～09、13～17、23）。本片 §4 第 1 項保留模型自呼工具，屬 DSP-091 裁示三的過渡；計畫當時漏寫「過渡」與接手片，L-R4 實際未達成。接手片＝目標正本路徑 G（唯讀查詢由程式執行，KD-7）。
2. 「最近的帳單」查成本月未繳（L3 10、11）；指名物件時列了未來的待發送帳單、漏了已逾期的兩筆（12）。
3. 一句兩件事只答一件（22、31）；31 回「資料裡沒有提到未繳的帳單資訊」，實際有 10 筆未繳。
4. 物件存在但沒有合約時回「系統裡查不到這個編號或名稱」（30）。
5. 「報修沒結案」第二句有查卻回「這次沒有替你送出或變更任何資料」（24）。
6. 修繕卡的物件名稱顯示 AI 擷取的字、不是紀錄名稱（M0 C-R_k2、W-R2_k2「捷仕堂 溫馨雅房可租」；寫入的 `estate_id` 67422 正確）。改前程式用同兩句可重現（`~/jgb-archive/listquery-20261029/m0/replay/`）。
7. 同名物件時客人說「有 X 月帳單的那間」，客服不幫篩、重列兩筆（M0 W-D2、W-D4）；延期候選第 1 張是 990003（改前同）。
8. 修繕分類未追問、一律「其他（未指定，歸其他）」（改前同）。
9. 物件列表只含刊登中（JGB `/estates` 行為，回覆已註明）；`get_invoices` 仍送 `user_id`（未查）；修繕 `item_id`（§3 末列，未做）。
