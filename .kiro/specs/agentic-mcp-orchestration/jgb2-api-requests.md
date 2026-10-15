# jgb2 API 缺口總帳（mock 替代 → 日後一次請 JGB 開）

> 業主 2026-09-05：「JGB API 不足的部分可以用 mock 替代，之後整理一起請 JGB 開。」
> 本檔是**唯一總帳**：每一個 mock 都必須對得回這裡的一列；每一列都寫清楚「解除條件」。日後要請 JGB 開時，直接從本檔匯出一頁版。
> 來源三處合併：本 spec `jgb2-source-index.md` §6 缺口登記、line-bot-platform `docs/jgb-api-requests.md` §2、`docs/chatai-*.md` 提到的 JGB 端未驗證主張。

## 0. mock 紀律（⛔ 不遵守就不准 mock）

| 規則 | 為什麼 |
| --- | --- |
| **只在一個邊界 mock**：`rag-orchestrator/services/jgb_system_api.py` 的 `JGBSystemAPI`（既有 `USE_MOCK_JGB_API` 開關，22 個公開方法皆有 `if self.use_mock` 短路；站內幫手 S0 起另有 6 支提案方法，非 mock 模式一律回降級、不發請求）。agent 工具層（`services/agent/tools/jgb2.py`）與面向層 ⛔ 不各自造假 | 一個開關可全關；分散的假資料會混進正式路徑 |
| **mock 資料一律「錄」不「編」**：能打到的端點用真回應錄成 fixture（去識別、附錄製日期與端點版本）；JGB 還沒有的端點，fixture 形狀以本檔對應列的「期望契約」為準並標 `contract: proposed` | 編出來的欄位會變成我們對 JGB 的錯誤假設，日後對接時才炸 |
| **每個 mock 標回本檔列號**：fixture 檔名或 docstring 含 `jgb2-req#<n>`；本檔該列「現況替代」欄反向列出 fixture 路徑 | 解除條件成立時能一次找出要拆的 mock |
| **mock 路徑的結果 ⛔ 不得宣稱 e2e 已驗**：`agent_eval` 報表、perf 檔、收案紀錄一律標 `jgb_mock=true` 的題數；M3／M4 放行必須有真 API 路徑的 e2e | 「回測前先驗容器」同理：假的下游會讓整輪結論翻盤 |
| **正式環境 ⛔ 不開 mock**：`docker-compose.prod.yml` 預設 `USE_MOCK_JGB_API:-true`，本機 `.env` 已覆寫（容器啟動日誌 `use_mock=False`）；線上部署 runbook 必查此值 | 預設值是 true，忘了設就是全假資料上線 |
| **mock 有期限**：每列寫「解除條件」；JGB 開了就拆 mock、補真路徑 e2e、關列 | 沒有期限的 mock 會變永久 |

查證：`grep -n "use_mock" rag-orchestrator/services/jgb_system_api.py`；`docker logs aichatbot-rag-orchestrator 2>&1 | grep -o "use_mock=[A-Za-z]*"`。

## 1. 總帳

阻擋等級：🔴 沒有它整條線走不通　🟠 有替代但品質差　🟡 非阻擋　❓ 待對碼確認（不一定是缺口）
誰要：`agent`＝本 spec（M1–M5）；`facet`＝現有面向鏈（線③④⑤接入）；`line`＝line-bot 自己直打 JGB；`assistant`＝站內幫手（jgb2 網頁經 `/mcp` 的 `agent.turn`，pm 受眾；計畫 `plan-assistant-11-items-20261014.md`，#16 起）

| # | 需求（端點／參數／文件） | 誰要 | 等級 | 現況替代（mock／繞法） | 解除條件 | 出處 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `GET /contracts/status-overview` 加 `estate_id` 查詢參數 | facet（線③）、agent M4 | 🟡 | 業務路徑不查租約、`contract_id` 留空開單（確認訊息無租客名） | JGB 補參數；chatai 改 prefill 用 `estate_id` | line-bot `jgb-api-requests.md` §2.6 E1 |
| 2 | `POST /repairs` 的 `contract_id` 為 nullable、開單人由 `agentUser` 帶入——**JGB 端主張未經我方驗證** | facet（線③）、agent M4 | ❓ | 先以 mock 回 201；真路徑用測試團隊 role 20151 打一張再刪 | JGB 確認或我方實打證實 | `chatai-repair-capture-spec.md` 頂部警語 |
| 3 | `emergency_status` 值域：`1=緊急/2=非緊急` 還是相反；缺值預設 | facet（線③）、agent M4 | 🔴 上線前必答 | 不 mock——值域猜錯會把急件派成不急；在確認前 `suggested_emergency` 缺值一律留空讓人選 | JGB 以 DB 真值回答 | `chatai-requests.md` C1；`chatai-repair-capture-spec.md` R7 |
| 4 | `GET /bills` 缺**入帳日**欄位 | facet（線⑤）、agent M5 | 🟡 | 誠實回「JGB 沒有此資料」；⛔ 不用 `updated_at` 冒充、不 mock 一個假日期 | JGB 加欄位（若業務上需要） | `chatai-digest-followup-spec.md` §1 註、情境 D |
| 5 | 帳單 `category`（屋主直收／屋主提領／備用金…）的 `mapping` 標籤表 | agent M5、知識 | 🟠 | 本 repo 硬表暫補（標 `jgb2-req#5`）；答不出「屋主直收帳單是什麼」 | `BillApiController.getMapping()` 補 `category` | `jgb2-source-index.md` §6 缺口 4 |
| 6 | 訂閱方案：`GET /roles/{role_id}/subscription` 有端點無文件 | agent（業者問方案） | 🟠 | 以執行期 `mapping.plan_type` 自描述為準；文件缺口列知識待補 | JGB 補 `docs/api/subscription.md` | `jgb2-source-index.md` §6 缺口 2 |
| 7 | `contract_renew`／`iot_meter` 面向 `search_params` 是 `keyword`，非 id 直查——數字 id 能否唯一命中 | facet（線⑤）、agent M5 | ❓ | agent 路徑 `jgb2.query.*` 已以 `ref` 直查（bills 已驗；contracts／meters 待驗） | 我方實打驗證；不需 JGB 動 | `chatai-requests.md` C4 |
| 8 | 修繕**歷史／進度**查詢（線⑤ C 類追問） | facet、agent M5 | 🟠 | `GET /repairs` 已存在（含 `is_urgent` 過濾）⇒ 缺的是我方面向／工具，不是 JGB API；第一版不開追問 | 我方 M5 開 `jgb2.query.repairs` | `chatai-digest-followup-spec.md` R4 |
| 9 | `GET /communities`、`POST /communities` | line（建立物件流程） | 🔴（line） | line-bot 自行處理；不進 chatai | JGB 新端點 | line-bot `jgb-api-requests.md` §2 A1–A2 |
| 10 | `POST /estates` 開到對外（現在 IP 白名單群組） | line | 🔴（line） | 同上 | JGB 調整權限群組 | 同上 A3 |
| 11 | `POST /contracts` 真建約（`agent/v1` 那支是造假資料工具） | line；agent M4 若做建約 | 🔴（line） | 同上；agent M4 首批寫入**不含建約** | JGB 新端點 | 同上 B1；`chatai-requests.md` §0 地雷 |
| 12 | 帳單憑據上傳 | line | 🟠（line） | 同上 | JGB 新端點 | 同上 C |
| 13 | 抄表回寫（`/meters` 只有讀） | line；agent M4 候選 | 🟡 | 同上 | JGB 新端點 | 同上 D1 |
| 14 | 業者 API 四張權限表無 migration | agent（DSP-011 前提偵測、開新 key） | 🟡 | 權限真相問線上 DB | JGB 把 schema 進 migration | `jgb2-source-index.md` §6 缺口 3 |
| 15 | `status-overview` 以 `to_user_id` 過濾——JGB 端主張未驗 | facet（線③） | ❓ | — | 我方實打或 JGB 確認 | `chatai-repair-capture-spec.md` 頂部警語 |
| 16 | **未收帳單統計（本月／逾期，加總＋逐筆明細，依成員可見範圍）**。`GET /api/external/v1/bills/summary/unpaid`（⚠️ 刻意不叫 `/bills/unpaid`：會被 `/bills/{bill_id}` 吃掉）。參數：`role_id`（必）、`user_id`（必，＝登入成員 viewer）、`scope`（必：`this_month`｜`overdue`）、`as_of`（選，`YYYY-MM-DD`，省略＝伺服器今日）、`page`／`per_page`（預設 50、上限 200）。語義：「未收」＝`status` 2 待繳費或 8 待對帳（⚠️ 8 是否算未收待 JGB 確認）；`this_month`＝`date_expire` 落在 `as_of` 當月；`overdue`＝`date_expire < as_of`；**只計該成員在 JGB 畫面上看得到的帳單**（DSP-074：依成員可見範圍**過濾**，⛔ 不是 mcp-facade §4.2 的「圈定成空」）。回應：`{success:true, data:{scope, as_of, currency, count, total_amount, items:[{id, contract_id, estate_id, title, sub_title, total, currency, date_expire(YYYYMMDD 整數), status}]}, pagination}`；`count`／`total_amount` 涵蓋**全部符合者**，只有 `items` 分頁。錯誤碼：400 缺 `role_id`／`user_id`；422 `scope`／`as_of` 非法或帶了未知參數；404「不存在或無權存取」（`role_id` 非 viewer 所屬團隊，或 `user_id` 不是該團隊成員）。越權：折疊成 404 同一句，⛔ 不另給可區分的訊息。 | assistant（站內幫手 (4)） | 🔴 | 替身：`services/jgb/transport.py` `_assistant_unpaid_bills`，資料 `services/jgb/fixture_data/assistant_demo_vendor4.json`（`jgb2-req#16`、`contract: proposed`） | JGB 實作並與本列契約逐欄對齊；我方拆守衛、補真路徑 e2e | 計畫 §3b、§3c；DSP-074 |
| 17 | **執行中修繕清單（全量或分頁，依成員可見範圍）**。`GET /api/external/v1/repairs/in-progress`。參數：`role_id`（必）、`user_id`（必，viewer）、`page`／`per_page`。語義：執行中（未結案）＝`status` 1 申請中、2 安排修繕、16 完成修繕；排除 32 結單、64 封存；排序 `apply_at` 新到舊；只含該成員可見者。回應：`{success:true, mapping:{status, emergency_status}, data:{count, items:[{id, status, emergency_status, estate_id, estate_title, estate_full_address, category_id, category_name, item_id, item_name, broken_reason, broken_note, apply_at, assign_at, complete_at, updated_at}]}, pagination}`（⛔ 不含報修人電話／email）。錯誤碼與越權同 #16。 | assistant（(5)） | 🔴 | 替身：`transport.py` `_assistant_in_progress_repairs`（`jgb2-req#17`、`contract: proposed`） | 同 #16 | 計畫 §3b、§3c |
| 18 | **N 個月內到期合約（依成員可見範圍）**。`GET /api/external/v1/contracts/expiring`。參數：`role_id`（必）、`user_id`（必，viewer）、`months`（選，1～24，預設 3）、`as_of`（選）、`page`／`per_page`。語義：`active=1`、`is_newest=1`、`is_history=0`，且 `as_of ≤ date_end ≤ as_of + months 個月`（兩端含；月底夾到當月最後一天）；只含該成員可見者；`days_left` 由伺服端算好。回應：`{success:true, data:{months, as_of, window_end, count, items:[{id, title, estate_id, city, district, address, rent, deposit_amount, date_start, date_end, status, bit_status, days_left}]}, pagination}`。錯誤碼：同 #16，另 `months` 超出範圍 422。越權同 #16。 | assistant（(8)） | 🔴 | 替身：`transport.py` `_assistant_expiring_contracts`（`jgb2-req#18`、`contract: proposed`） | 同 #16 | 計畫 §3b |
| 19 | **建立物件（照使用者給的值）**。`POST /api/external/v1/estates`。body：身分欄位 `role_id`、`user_id`（必，登入成員）；必填 `title`（≤60）、`city`、`district`（JGB 以名稱解析代碼，對不到 422；⚠️ `city` 的「台」「臺」是否視同**待 JGB 回答**，見 §1b，我方目前以 JGB 既有資料寫法「台」送出）、`address`（≤100）、`use_for`（`residential`｜`business`｜`parking_space`）；選填 `space_type`、`building`（⚠️ 這兩欄值域我方未定，**待 JGB 回答**：是自由文字還是代碼表？若為代碼表請給值域；回覆前我方只收使用者原話、不自行對照代碼）、`room_count`（0～99）、`size`（>0）、`rent`（0～99,999,999）、`floor`、冪等鍵 `idempotency_key`（**放在 JSON body**，不是 header：我方 transport 沒有 header 通道，`services/jgb_system_api.py` `_assistant_write`）。⛔ 沒給的欄位留空，不補隨機值；⛔ 歸屬欄位見 #23。回應：`{success:true, data:<formatEstate 投影，**必含 `id`**（我方以 `data.id` 取新編號，缺 `id` 視同失敗：`action._created_id`）>}`（新物件 `role_id`／`team_id` 取自 body 身分、`status=1`，建立者與團隊擁有者可見）。錯誤碼：400 缺必填；422 歸屬／未知欄位、值非法、縣市行政區無法解析；404 折疊。⚠️ 我方建立後以 #24 的單筆物件讀取（帶 role＋viewer）確認物件看得到；現行物件讀取只回「刊登中」物件，已出租物件可能被判查無（見 #24）。 | assistant（(9-1)(9-2)） | 🔴 | 替身：`transport.py` `_assistant_create_estate`（`jgb2-req#19`、`contract: proposed`）。⚠️ 與 #9／#10 並存：#9／#10 仍屬 line | JGB 實作並對齊；`agent/v1` 造假資料工具 ⛔ 沿用 | 計畫 §0、§3b；總帳 #11 |
| 20 | **建立合約（照使用者給的值）**。`POST /api/external/v1/contracts`。body：身分欄位 `role_id`、`user_id`（必）；必填 `estate_id`、`date_start`、`date_end`（`YYYY-MM-DD`，結束晚於起始）、`rent`（1～99,999,999），`to_user_email`／`to_user_phone` 至少一個；選填 `deposit_amount`（≥0，預設 0）、`title`（≤60，預設物件標題）、冪等鍵。語義：物件須屬該團隊且該成員看得到。回應：`{success:true, data:<formatContract 投影，**必含 `id`**>}`（新合約 `status=1`、`bit_status=1`、`active=1`、`is_newest=1`、`is_history=0`；不含內部欄位 `to_user_id`）。錯誤碼：400 缺必填；422 歸屬／未知欄位、日期或金額或 email／電話格式非法；404 折疊（物件不存在、屬他團隊、或該成員看不到——同一句，且先於欄位值檢查）。 | assistant（(10-1)） | 🔴 | 替身：`transport.py` `_assistant_create_contract`（`jgb2-req#20`、`contract: proposed`） | 同 #19 | 計畫 §3b；總帳 #11 |
| 21 | **建立手動帳單**。`POST /api/external/v1/bills/manual`（⚠️ 不叫 `POST /bills`：避免與一般帳單端點混淆）。body：身分欄位 `role_id`、`user_id`（必）；必填 `contract_id`、`title`（≤60）、`total`（>0、≤9,999,999）、`date_expire`（`YYYY-MM-DD`）；選填 `sub_title`（≤100）、冪等鍵。語義：合約須屬該團隊且該成員看得到。回應：`{success:true, data:<formatBill 投影，**必含 `id`**>}`（`type=3` 新增帳單；初始 `status=1` 待發送——⚠️ 初始狀態待 JGB 確認）。錯誤碼：400 缺必填；422 歸屬／未知欄位、值非法；404 折疊。 | assistant（(11-1)(11-2)） | 🔴 | 替身：`transport.py` `_assistant_create_bill`（`jgb2-req#21`、`contract: proposed`） | 同 #19 | 計畫 §3b |
| 22 | **修繕單附照片**（擴充既有 `POST /api/external/v1/repairs`，與總帳 #2 同一支）。body 新增 `user_id`（必，登入成員；見 #23）與 `broken_photos`。`broken_photos` 為中繼資料陣列 `[{filename, content_type, size, sha256}]`：`filename` 由我方程式產生、形如 `photo-N.ext`（⛔ 使用者檔名）；`content_type` 只會是 `image/jpeg`｜`image/png`｜`image/webp`；`size`、`sha256` 取**原檔**位元組；一張修繕單最多 5 張，超過時我方**全部不附**並在確認卡上說明，確認卡顯示「附照片：N 張」。**上傳方式**：JGB 擇一並回覆——(a) `multipart/form-data`，欄位 `photos[]`，每張 ≤5 MB、`image/jpeg｜png｜webp`、最多 5 張；(b) 預簽上傳後以 JGB 自己產生的識別碼引用。**我方建議 (b)**：照片本來就在 JGB 的專用上傳網域（接口 A §7），我方不轉送位元組，body 只帶 JGB 的上傳識別碼加中繼資料，也不需要 JGB 開 multipart；選 (a) 時我方需另做位元組上傳（S6 後再排）。⛔ JGB 不得回頭抓我方提供的網址（安全審查 F10）。替身因 `Transport` 只傳 JSON，只驗每張中繼資料 `{filename, content_type, size, sha256}`（`sha256` 為 64 位小寫 hex；超過張數／大小／型別 ⇒ 422）。錯誤碼：同 #23，另 422 照片不合規。越權：`estate_id`／`contract_id` 非本團隊或該成員看不到 ⇒ 404 折疊。⚠️ 只有載入 `assistant_demo` 段的 fixture 才啟用這些加碼檢查，其他 fixture 行為不變。 | assistant（(6-2)） | 🟠 | 替身：`transport.py` `_create_repair`＋`_assistant_repair_checks`（`jgb2-req#22`、`contract: proposed`） | JGB 定上傳方式並實作；我方依其方式改 S3 | 計畫 §3b、§5b F10 |
| 23 | **寫入 body 身分規則（規則列，無獨立端點）**：所有寫入（#19～#22）body 一律帶 `role_id`＋`user_id`（登入成員，由 jgb2 面板授權後帶出，DSP-011）；**JGB 負責驗**：(a) `user_id` 是否為 `role_id` 團隊成員（⚠️ 待查：現況是否驗 viewer ∈ role）；(b) 該成員有無對應能力（`add_estate`／`add_contract`／`add_bill`／`edit_repair`…；⚠️ 替身**未**實作能力檢查）；(c) 引用資源（`estate_id`／`contract_id`）屬該團隊且該成員看得到。**歸屬欄位 ⛔ 由呼叫端指定**：body 含 `team_id`、`owner_user_id`、`owner_role_id`、`vendor_id`、`to_user_id`、`agent_user_id`、`created_by`、`issue_target_role_id` 任一 ⇒ 422（訊息「歸屬欄位由登入身分決定，不得指定」）；未宣告的欄位 ⇒ 422（「不支援的欄位」），比照 `PATCH /bills` 只准改到期日的先例。**越權回應形狀**：`{success:false, error:{code:404, message:"不存在或無權存取"}}`，不存在與無權存取同一句、**資源狀態不變**。冪等：`idempotency_key`（**JSON body 欄位**，不是 header），同鍵重送回同一份 receipt、不重複建。**擴及既有「改帳單到期日」**：我方現行以 `PATCH /agent/v1/bills/{id}`（body `due_date`、`idempotency_key`）延長到期日；本規則同樣適用——body 帶 `role_id`＋`user_id`，JGB 驗成員有對應能力（能力名稱由 JGB 定）與該帳單屬本團隊且該成員看得到；不可見（他團隊或該成員看不到）回 404、與不存在同一句、同形狀（我方對 403 與 404 同樣當作「查不到」，請附 `error.code`）。⚠️ **`agent/v1` 是同事產測試資料的造假資料工具、認證為 ssh-ed25519 簽章（總帳 #11；計畫 §0），我方對它的依賴屬既有疑慮**：請 JGB 一併回答此動作的正式對外路徑（例如 `PATCH /api/external/v1/bills/{id}`，只准改到期日）；回覆前此動作只有替身走得通。 | assistant（(2)(3)） | 🔴 | 無獨立替身端點——由 #19～#22 替身的 F4 行為與單元測試 `tests/unit/jgb/test_assistant_mock_contract_req.py` 落實（`jgb2-req#23`、`contract: proposed`） | JGB 實作並以本列規則逐條接測 | 計畫 §5b F3／F4／F5；DSP-011 |
| 24 | **既有讀取端點依成員可見範圍過濾**：`GET /repairs`、`GET /estates`、`GET /meters`、帳號（recharge account）讀取，帶 `viewer_user_id`（沿用 bills／contracts 既有慣例；各端點既有 `user_id` 語義不變）時，結果限於該成員在 JGB 畫面上看得到的範圍（DSP-074）；⛔ 不是圈定成空（改寫 mcp-facade §4.2 對站內幫手的語義）；缺 `viewer_user_id` 維持現行（整個 role）。越權／不在範圍的單筆讀取折疊成 404「不存在或無權存取」（回應請附 `error.code`，我方依此與 403 同樣判為「查不到」）。**新增單筆物件讀取**：`GET /api/external/v1/estates/{id}` 須帶 `role_id`＋`viewer_user_id`，回該成員看得到的那一筆（含已出租、下架等非刊登中狀態）。⚠️ 原因：我方目前讀物件只有 `GET /estates`（列表、**只回刊登中物件**），建立合約／手動帳單前要驗物件存在，已出租物件會被誤判成「查無」。**越權與不存在的回應**：(1) 形狀相同（同一句「不存在或無權存取」）；(2) **回應時間不可區分**（不得因查資源與驗權限的順序，讓兩者耗時有可量測差異，避免探測資源是否存在）；(3) 越權回 403 或 404 皆可，**但須全站一致**（我方兩者同樣當作「查無」，接口 A §10）。錯誤碼同既有端點。 | assistant（(3)） | 🟠 | **無獨立替身端點**——過濾行為已由 S1 落實於既有端點的替身（`services/jgb/transport.py` 在 assistant fixture 下依 `*_visibility` 對修繕、物件、電表、帳號、合約、帳單過濾，可見範圍宣告在 `assistant_demo_vendor4.json`）（`jgb2-req#24`）；S5 已落地：單筆 `GET /estates/{id}` 帶 `role_id`＋`viewer_user_id`，他團隊或看不到回 404、與不存在不可區分（回應時間不可區分屬 JGB 義務，我方替身不模擬，延後）；替身的讀取端點（帳單、合約、修繕、物件單筆與列表）對他團隊 role 一律同形折疊（列表空、單筆 404）；`GET /repairs/categories` 也會帶 `role_id`＋viewer（JGB 可忽略）；帳號（accounts）讀取的路徑段只收純數字 | JGB 實作並接測；我方 S5 起所有呼叫帶 viewer | 計畫 §3b、§3c；DSP-074 |

## 1b. 待 JGB 回答（#16～#24 彙整）

每列 ⛔ 由我方猜；回覆前我方一律照「期望契約」實作替身、標 `contract: proposed`。**須 JGB 回答者**（`阻擋`＝沒答案無法上線接測）：

| 列 | 問題 | 阻擋 | 我方暫行處置 |
|---|---|---|---|
| #16 | 「未收」是否含 `status` 8 待對帳（現行假設：2 待繳費＋8 待對帳）？ | 否（影響數字） | 照假設實作，接測時以 JGB 畫面的未收數字對照 |
| #16～#18 | 路徑、參數、回應欄位是否接受（含 `bills/summary/unpaid` 路徑命名、分頁參數、`days_left` 由伺服端算）；#17 執行中＝`status` 1／2／16 是否正確；#18 `active=1、is_newest=1、is_history=0` 與月底夾法是否與 JGB 畫面「即將到期」一致 | 是 | 以本檔各列為準 |
| #19 | `space_type`、`building` 的值域（自由文字或代碼表）；`district` 名稱解析對不到的錯誤形狀 | 否（選填欄） | 只收使用者原話 |
| #19 | 建物件的 `city` 以名稱解析時，「台」「臺」是否視同？若否請給標準寫法 | 否（影響建物件成功率） | 以 JGB 既有資料寫法「台」送出 |
| #19／#24 | 物件讀取需**帶 viewer 的單筆端點**（`GET /estates/{id}`，含已出租／非刊登中）；現行 `GET /estates` 只回刊登中物件，已出租物件被誤判查無 | 是（建立合約／手動帳單依賴） | 替身單筆讀取折疊 404；真路徑在 JGB 提供前，已出租物件的建合約／開帳單可能被誤判「查不到」 |
| #20 | 合約建立後的 `status`／`bit_status` 初值是否與替身一致；`deposit_amount` 未給預設 0 是否可接受 | 否 | 照替身 |
| #21 | 手動帳單初始 `status`（替身 1 待發送）是否正確；是否需另有「發送」動作 | 否 | 照替身 |
| #22 | **照片上傳方式 (a) multipart 或 (b) 預簽上傳＋識別碼**（我方建議 (b)）；JGB 上傳網域名稱（接口 A §7，亦用於 `IMAGE_URL_ALLOWLIST`）；該網域是否與憑 IP 信任的主機共用；每單照片上限 5 張是否一致 | 是（照片附進修繕單） | 只送中繼資料 `{filename, content_type, size, sha256}` |
| #23 | (a) `user_id` 是否為 `role_id` 團隊成員的驗證現況；(b) 成員能力（`add_estate`／`add_contract`／`add_bill`／`edit_repair`…）的檢查；(c) 歸屬欄位清單與 422 訊息；(d) 越權回 **403 或 404**（二擇一、全站一致，並附 `error.code`）；(e) **改帳單到期日**（我方現用 `PATCH /agent/v1/bills/{id}`，造假資料工具）的正式對外路徑 | 是 | 替身未實作能力檢查；到期日延長只有替身走得通 |
| #24 | 讀取端點 `viewer_user_id` 過濾語義（過濾而非圈定成空）；新增單筆 `GET /estates/{id}` 帶 role＋viewer；**越權與不存在回應時間不可區分**；回應形狀相同 | 是 | 我方每次呼叫都帶 role＋viewer |

另：#2、#3（`emergency_status` 值域）等既有列的待答事項不變，見各列。

## 2. 給 JGB 的一頁版（日後匯出時用）

> **2026-10-15 已匯出並對碼 jgb2 master**：`jgb-api-spec-for-jgb-20261015.md`。對碼結果推翻本檔 #16～#24 的部分設計（統計改為擴充既有 `GET /bills`／`/repairs`／`/contracts/status-overview`；`GET /estates/{id}` 已存在、改為放寬；既有 `POST /repairs` 的 `broken_photos` 是網址陣列；`PATCH /agent/v1/bills/{id}` 在 master／preview 查無；`emergency_status` 網頁為 2＝緊急、對外 mapping 標反）。**給 JGB 一律以該檔為準**，本檔 §1 #16～#24 為原始提案紀錄。

只匯出「解除條件」欄需要 JGB 動作的列：**#1、#3、#4、#5、#6、#9–#14、#16–#24**；#2／#7／#8／#15 是我方要驗或要做的，⛔ 不要寄給 JGB。
排序：🔴 先（#3、#9–#11、#16–#21、#23）→ 🟠（#5、#6、#12、#22、#24）→ 🟡（#1、#4、#13、#14）。
#16～#24 是站內幫手（`plan-assistant-11-items-20261014.md`）的接口 B：路徑與欄位皆 `contract: proposed`，以各列為準；**各列需 JGB 回答的事項彙整在 §1b，匯出時一併附上**。JGB 實作後，以 `docs/api/jgb2-web-assistant-integration.md`（接口 A）與 `jgb-acceptance-checklist-20261015.md`（A1～A14 的真 API 版接測清單）接測。
匯出時 #16～#24 的重點（逐列細節以 §1 各列為準）：
- 全部端點每次呼叫都帶 `role_id`＋`user_id`（登入成員）；讀取依成員可見範圍**過濾**（DSP-074）、寫入驗成員能力與資源歸屬（#23）；歸屬欄位（`team_id`、`owner_*`、`vendor_id`、`to_user_id`、`agent_user_id`、`created_by`、`issue_target_role_id`）由呼叫端指定一律 422。
- 越權與不存在同形（404「不存在或無權存取」，或全站一致的 403），**回應時間不可區分**。
- #22 照片：我方建議 (b) 預簽上傳＋JGB 識別碼；⛔ 回頭抓我方網址。
- #23 擴及「改帳單到期日」：`agent/v1` 為造假資料工具，請 JGB 給正式對外路徑。
- #24 新增 `GET /estates/{id}`（帶 `role_id`＋`viewer_user_id`，含已出租物件）；他團隊或看不到回 404、與不存在不可區分；回應時間不可區分屬 JGB 義務。
- #23／#24 越權回 403 或 404 皆可，須全站一致並附 `error.code`。
- #19 `space_type`／`building` 值域待 JGB 定；`city` 的「台」「臺」是否視同待 JGB 答。
每列附：要什麼、為什麼、我們現在怎麼繞、誰在等（agent 哪個里程碑／line 哪條線）。

## 3. 維護

- 新增 mock 之前先在此加列；拆 mock 時把該列狀態改「已開，mock 已拆（commit）」。
- 每次 `jgb2-source-index.md` §8 同步作業跑完，對照本檔：JGB 端有動的列更新解除狀態。
- 本檔不記進度以外的事實；JGB 端行為的權威來源仍是 `jgb2-source-index.md`。
