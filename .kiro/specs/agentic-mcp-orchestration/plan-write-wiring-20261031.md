# 計畫：寫入改接與照片報修接真 JGB（2026-10-31）

業主核可（2026-10-31：「那你繼續開發」；收尾審查修法與待裁題：「1 好、2a、其餘照建議」＝W1 修法核可、Q3 選 (a)、Q2 照片走 #22、Q4 斷路器續做）。本檔 §2 規則與 §5 清單即為本片的凍結規則與清單檔。

## 0. 目標正本定位

- 目標正本：`docs/architecture/TARGET_ARCHITECTURE.md`，碰到 §2 分工表「寫入全程」列、§6「修繕單附照片（待業主重裁）」、§8 差距表「修繕單照片」列；工作線目標 `.kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md` §4「照片與文件上傳」列（上線最低範圍，DSP-120、DSP-122）。建物件、建合約、手動帳單、改到期日不在上線最低範圍，業主 2026-10-31 指示一起上（§2 R1）。
- 分工表列：「寫入全程：缺哪欄、出不出卡、能不能送出、送出後回什麼」歸程式。本片只把程式送出的目的地從測試替身換成真 JGB，並把 JGB 的回應轉成程式固定句；不改誰決定什麼，不新增 AI 決定權。帶狀態的句子（拒絕、結果未確認）由程式產生（DSP-091）。
- 已知偏離：DSP-132「接真 JGB 時四個動作回固定句、照片不送檔」與 staging 現況不符，本片是接手片。照片路徑偏離目標正本 §6 與 DSP-130 的裁決時點，見 §2 Q2。KD 系列不碰。
- 系統定位（DSP-130）：JGB 工具仍在本系統內（JGB 工具移交片尚未開始）；本片只改呼叫端，不搬工具。
審查紀錄：/Users/chenqinghuang/jgb-archive/arch-step3-20261018/write-wiring/security-review-20261031.md
審查紀錄：/Users/chenqinghuang/jgb-archive/arch-step3-20261018/write-wiring/plan-verifier-r1-20261031.md
審查紀錄：/Users/chenqinghuang/jgb-archive/arch-step3-20261018/write-wiring/plan-verifier-r3-single-20261031.md
- 上三行：資安審查（處置見 §8）、plan-verifier 第 1 輪 REVISE（處置見 §9）、單點審查 READY。收尾審查 REVISE `/Users/chenqinghuang/jgb-archive/arch-step3-20261018/write-wiring/plan-verifier-r2-closing-20261031.md` 的唯一阻擋「連 www 時開關 on 會打到沒對過契約的 www」已修（W1、A2、§6），業主核可修法（「1 好」）後由單點審查判 READY。
- 風險觸發：有。(1) 對外寫入：送到 JGB 的寫入會寫進 JGB 正式資料庫（staging 與 www 共用，DSP-132）。(2) 資安：照片檔案上傳、寫入身分與歸屬、錯誤訊息外露。核可前 `security-reviewer` → `plan-verifier`；核可後交 `security-executor`；收案前 `verifier`。

## 1. 終點指標、斷路器與廣度

- 目標文件：`architecture-target-20261018.md` §1「每片怎樣算完成」的全部量法（解決率、錯筆卡、錯筆寫入等）與 §4「照片與文件上傳」列。
- 現值（讀碼，未實跑）：接真 JGB 時，文字修繕單送得出去（`create_repair` 的 `if not self.use_mock` 分支 POST JSON；`repair_create` 不在 `WRITE_NOT_SUPPORTED_ACTIONS`）；修繕照片不送（`action.py` `repair_create` 只在 `use_mock` 時取 `photo_files`，卡外有 `REPAIR_PHOTOS_NOT_ATTACHABLE_HINT`）；四個動作不送請求、回「尚未開放」（`confirm.py` `WRITE_NOT_SUPPORTED_ACTIONS`；`jgb_system_api.py` `_assistant_write` 的 `_proposed_not_available`、`agent_patch_bill_due_date`）。
- 本片預期：五項接 staging 都送得出去；JGB 回成功、回白名單內的拒絕原因（轉程式固定句），或結果無法確定時回「結果未確認」。終點量法不量（R2），只宣稱機制，成效未驗證。

### 斷路器報告（同一目標前兩片，待業主裁定，§2 Q4）

| 片 | 做了什麼 | 終點實際變化與來源 | 為何沒動或動得不明 |
|---|---|---|---|
| 填欄結構化（DSP-128，S1～S6） | AI 輸出換算後的值與指令，程式只驗格式與值域；換紀錄改程式按鈕 | 未收案、終點未正式量；同批決定性題組 on 對 off 錯筆卡 20→13（`~/jgb-archive/arch-step3-20261018/fill3/x5-onr`、`fill3/x5-offr`；根因 `fill3/x1r/x4_stop_rootcause.md`） | 依全域規則未量終點算 0 |
| 對話入口對齊（DSP-131） | 新增專用對話 API，與 `/mcp` 並存 | OV 扣錯筆解決 77→80、錯筆卡 2→3、M0 全部 47→48（`fill3/x1r/entry_close_notes.md`）；入口只轉接，變化研判是模型波動、不是入口造成 | 計畫本來就預期 0 |

指標現值：OV 嚴格 75/96、扣錯筆解決 80/96、M0 48/52（off，經新入口；`entry_close_notes.md`），已在業主上線門檻 7～8 成內。建議：**續做**——本片與前兩片都是上線前提（上線後才有真實流量可量），不是改善終點的片；上線後第一片恢復量終點。

- 廣度：本片全部是機制項，不宣稱使用者成效。

| 項目 | 類型 | 資料組 | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照 |
|---|---|---|---|---|---|---|
| A1～A8 | 機制項 | — | — | — | — | — |

上位驗收方式：`architecture-target-20261018.md` §1 終點量測；本片依業主指示不量，列為非目標（§5.3）。

## 2. 規則（業主原話轉寫）

| ID | 可檢查的條件 | 出處（業主原話，2026-10-31） | 讀法 |
|---|---|---|---|
| R1 | 照片報修、建物件、建合約、手動帳單、改到期日，五項接真 JGB 送得出去 | 「照片報修與寫入改接 都要一起上」 | 「寫入改接」照 HANDOFF §3 第 8 點讀成四個動作（#19～#21、#23）；照片＝#22 multipart（Q2） |
| R2 | 不排 OV、M0 這類整輪量測；驗收只用單元測試、每項一次 staging 實打、一次收案 verifier | 「不要在一直做拖時間的測試」「等你絕不都測完整 這功能也根本不用上」 | 收窄：不量使用者成效（§5.3） |
| R3 | 和填欄結構化 on 一起部署；不再比較 on／off 架構 | 「on 直接上線」「確定 on 架構 不要在比較浪費時間了」 | 部署順序，不是本片程式範圍 |
| R4 | 正式機改連 JGB staging API（`JGB_API_BASE_URL=https://staging.jgbsmart.com`） | 「阿你不會改成 staging ?」（回主會話 (A) 正式機連 www 開關先關／(B) 正式機改連 staging 兩案） | 選 (B)，佐證「我接 staging 也要能測到完整功能」。由業主跑 `~/jgb-archive/deploy-20261031/switch-jgb-staging.sh go`；2026-10-31 實測 staging 入口擋正式機來源 IP `3.114.12.10`（`diag`：不帶金鑰也回純文字 Forbidden），待 JGB 放行（上線事項規格書 L5） |
| R5 | 接 staging 時五項寫入與照片都能實際測到，本系統不擋：正式機 `JGB_WRITE_WIRING=on`（開關只當回退用） | 「我接 staging 也要能測到完整功能 不准檔」 | 照片辨識的合成檔防護不屬本片程式；業主 2026-10-31 自行執行 `switch-jgb-staging.sh photos-real` 關閉（出處：該腳本 `photos-real` 註解「執行即代表業主接受這個個資風險」與業主實跑輸出） |
| R6 | 資安項只做會改變結果的：錯筆寫入、資安與個資外露、會讓上線出錯的事（DSP-115 第 3 點）照修；其餘列後補，不擋今天上線 | 「我今天要把完整功能上線 不必要的資安別擋住」 | 「不必要」讀成 DSP-115 第 3 點以外的項目；§8 每列標「必修（理由）」或「後補」。「今天」：A7 用本機容器連 staging 跑（辦公室 IP 可達），不等正式機改連；今天部署的開關值見 §6 |

R4 的已知代價（裁定前已告知）：
- 同一個容器的 LINE OA 也會改連 staging：`JGB_API_BASE_URL` 只有一個，`responsibility_*` 模組與站內幫手共用 `jgb_system_api.py`。
- staging 是 JGB 未正式發佈的程式，資料庫是正式資料庫。
- 金鑰：讀取在 www 通過不代表在 staging 能寫（安審 P2-4）。部署前由業主跑不寫入探測（§6）。

業主裁定（2026-10-31「1 好、2a、其餘照建議」）：Q2 走 #22；Q3 選 (a)，授權範圍照 (a) 原文；Q4 續做（斷路器報告的建議）。下列為裁定時的題目原文：
- **Q2　照片走哪條。** 目標正本 §6 記載業主先前選 B（JGB MCP server 申請上傳），DSP-130 把 B、E（multipart 換 `file_id`）、API 規格 #22 三選一排在 JGB 工具移交片開片時裁。先照 #22 做是偏離這兩點。建議 #22：今天上線只有它做得到——程式已寫好（`create_repair` 的 `photo_files` 分支，UD-3），staging 已收（`RepairController::collectBrokenPhotos`）；B 要 JGB 先有 MCP server，目前沒有。核可後改目標正本 §6、§8，另立決策取代 DSP-130 這一點（W10）。
- **Q3　A7 staging 實打的授權**（安審 P1-1）。這是代理經本系統寫 JGB 正式資料庫，不在全域常設例外（只限 `guard.open_guarded(..., mode="staging_team")` 列舉端點）內。二擇一：(a) 明示授權——端點 `POST /estates`、`POST /contracts`、`POST /bills/manual`、`PATCH /bills/{id}`、`POST /repairs`，團隊 20151，每端點 ≤3 筆，建出的 ID 列回報、刪除由業主決定；(b) 業主自己透過站內幫手（JGB staging 面板的站內幫手，經本系統）操作，代理只看結果。直接用 JGB 原生表單建資料證明不了 R1。
- **Q4　斷路器裁定**（§1 斷路器報告）：續做／改題／停線。

## 3. 已對過的 staging 契約（jgb2 `origin/staging` `544e8592eb`，讀碼；安審確認白名單逐鍵相符）

| 端點 | staging 白名單 | 我方現送（替身） | 差異 |
|---|---|---|---|
| `POST /api/external/v1/estates` | `EstateController::STORE_FIELDS` | `transport.py` `_ESTATE_BODY_KEYS` 相同 | 無 |
| `POST /api/external/v1/contracts` | `ContractController::STORE_FIELDS` | `_CONTRACT_BODY_KEYS` 相同 | 無 |
| `POST /api/external/v1/bills/manual` | `BillController::MANUAL_FIELDS` | `_BILL_BODY_KEYS` 相同 | 無 |
| `PATCH /api/external/v1/bills/{id}` | `BillController::DUE_FIELDS`：date_expire | 我方打 `PATCH /agent/v1/bills/{id}`、送 `due_date` | **路徑與鍵名都要改**；`rag-orchestrator/scripts/check_jgb_contract.py` 也還對著舊路徑 |
| `POST /api/external/v1/repairs` | `RepairController::STORE_FIELDS`；非 JSON 時取表單欄位（`ExternalWriteGuard::bodyParams`）；照片只收 JPEG/PNG、≤5,000,000 bytes、≤10 張，檔案與網址不得同時給 | 真 JGB 分支不送檔 | **要送 multipart** |

共同規則（`ExternalWriteGuard`）：身分只收 `role_id`＋`viewer_user_id`（正整數，缺則 400）；`role_id`、`viewer_user_id`、`idempotency_key` 永遠允許；白名單外 422；歸屬欄位 422；查不到一律 404。⇒ 我方 ⛔ 送 `confirmation_token`、`due_date_shift_days`。

成功回應形狀：實作時逐支讀 staging 各 controller 的成功回傳（例：`BillController::updateDueDate` 回 `formatBill`，不是我方 receipt 讀的 `due_date_before`），照抄成解析規則並註明 sha；讀不到或對不上的欄位，回執改用卡上的值；取不到 `data.id` 一律歸「結果未確認」（W7）。

## 4. 改動（W1～W10）

| ID | 做什麼 | 檔 |
|---|---|---|
| W1 | 開關 `JGB_WRITE_WIRING`：只收 `on`／空＝off；只讀一次、存成 API 物件上的單一屬性，各閘門點都讀它；讀不到或其他值當 off（fail-closed）。**on 只在 `JGB_API_BASE_URL` 主機＝`staging.jgbsmart.com` 或替身模式時生效**；連 www 或其他主機時自動當 off 並記一行警告（§3 只對過 staging 契約，www 跑 master、沒有這些端點；收尾審查阻擋）。off 時行為與現在逐字相同。閘門點：`confirm.py` 7 處 `use_mock` 判斷、`action.py` `repair_create`、`jgb_system_api.py` 3 處 | `jgb_system_api.py`、`confirm.py`、`action.py`、`docker-compose.prod.yml` |
| W2 | on 且接真 JGB：`_assistant_write` 拿掉 `_proposed_not_available`，照現有身分覆寫規則送出 | `jgb_system_api.py` |
| W3 | on：改到期日改打 `PATCH /api/external/v1/bills/{id}`，body 只送 `date_expire`＋身分＋冪等鍵；`bill_id` 送出前驗純數字；替身路由、白名單、照片政策同步改成 staging 的值（5,000,000 bytes、JPEG/PNG）；`check_jgb_contract.py` 改對新路徑；成功回應照 §3 解析 | `jgb_system_api.py`、`services/jgb/transport.py`、`rag-orchestrator/scripts/check_jgb_contract.py`、`action.py` |
| W4 | on：照片真 JGB 路徑。`action.py` `repair_create` 在真 JGB 也取照片，位元組只能來自 `_card_photo_files`（綁定欄、重算 sha256 對卡上值、JPEG 判型）；取不到照現行回 `_photos_unavailable()` 擋下，⛔ 退回成不附照片照送。`create_repair` 有 `photo_files` 時送 multipart；拿掉卡外「照片不會送出」提醒 | `action.py`、`jgb_system_api.py`、`confirm.py` |
| W5 | on：`WRITE_NOT_SUPPORTED_ACTIONS` 不再攔四個動作；固定句只在 off 時用 | `confirm.py` |
| W6 | JGB 拒絕轉程式固定句，封閉白名單：(端點, 狀態碼, 訊息全文完全相符) → receipt 錯誤碼 → 程式固定句，全文照抄 staging `544e8592eb` 並註明 sha。列入：`MSG_NO_LESSEE`、`MSG_DUE_NOT_DRAFT`、`MSG_NO_SUBSCRIPTION`、`MSG_ESTATE_LIMIT`、`MSG_CONTRACT_LIMIT`、`MSG_ADDRESS_UNRESOLVED`、`MSG_COMPANY_PHONE`、`MSG_USER_PHONE`、`MSG_PARKING`、`MSG_ESTATE_INCOMPLETE`、`MSG_ESTATE_OWNER`、`MSG_ESTATE_CONTRACT_LIMIT`、修繕分類／項目兩句。404 照現行折成查無；白名單外 4xx、金鑰層（`MSG_ROOT_KEY`、`MSG_QUERY_KEY`、`MSG_NO_KEY`、`MSG_IDENTITY_REQUIRED`、`MSG_UNKNOWN_FIELD`、`MSG_OWNERSHIP_FIELD`）回現有 `ACTION_FAILED_TEXT`。receipt 錯誤碼是封閉值域（每句一碼＋`unconfirmed`＋`failed`），兌現段與同一張卡重按的 `_answer_for_receipt` 都依錯誤碼查同一張表，重按回同一句。走程式狀態句路徑，⛔ 經 `text_for_model`；log 只記端點樣板、狀態碼、錯誤碼 | `transport.py`、`action.py`、`runtime.py`（兌現失敗分支、`_answer_for_receipt`）、`confirm_card.py`（新固定句） |
| W7 | 請求可能已送到 JGB、但結果無法確定時，一律回「結果未確認，請到 JGB 畫面確認是否已建立，再決定要不要重送」程式固定句（receipt 錯誤碼 `unconfirmed`），⛔ 回「無法執行」：工具逾時 `TOOL_TIMEOUT`、HTTP 逾時、5xx、送出後的連線或讀取錯誤、2xx 非 JSON、2xx 缺 `data.id`。逾時：寫入 HTTP 逾時 multipart 60 秒、其他寫入 30 秒，讀取維持 10 秒；兌現段呼叫寫入工具的工具逾時（現為 `AgentRuntime` `tool_timeout_s=3.0`）改成大於寫入 HTTP 逾時加前置讀取時間（寫入工具 90 秒），其他工具維持 3 秒。目的：不讓客人重開新卡、新冪等鍵造成重複單（錯筆寫入） | `transport.py`、`jgb_system_api.py`、`action.py`、`runtime.py`、`confirm_card.py` |
| W8 | 寫入工具限站內幫手金鑰：`registry.py` 寫入閘加條件，呼叫端金鑰 id 在 `assistant_key_ids()` 才露出與執行寫入工具（本片讓四個動作第一次真的送出，是新增暴露面）。部署前檢查正式機 `AGENT_ASSISTANT_KEY_IDS` 有值（空值會讓連文字修繕在內的寫入工具全部消失，§6） | `registry.py` |
| W9 | （後補，R6）`JGB_API_BASE_URL` 主機白名單、`trust_env=False` | — |
| W10 | 文件：接口 A §1、§9、§10，`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、API 規格 §6、`HANDOFF` §3 第 8 點改成現況；業主裁 Q2 後改 `docs/architecture/TARGET_ARCHITECTURE.md` §6、§8 並立決策取代 DSP-130 照片裁決時點（文件衛生：改正文） | docs、`.claude/decisions/` |

## 5. 驗收清單

### 5.1 清單
| # | 規則 | 檢查 | 觀察點 | 證據 |
|---|---|---|---|---|
| A1 | R1 | 單元全套失敗集合＝現有 9 筆基準（`fill3/x1r/x6_unit.txt`） | `pytest` | 輸出檔 |
| A2 | R1 | W1 off：五項行為與改前逐字相同；每個閘門點 on/off 各一組；開關讀不到或非法值時當 off；開關 on 但 base URL 是 www 時當 off | 單元 | 測試 |
| A3 | R1 | W1 on：五項送出的 method、路徑、body 鍵集合各等於 §3 staging 白名單＋身分鍵＋冪等鍵；真 JGB 路徑 multipart 位元組 sha 等於卡上值；暫存缺照片時不寫入；`check_jgb_contract.py` 對 staging 通過 | 單元、腳本 | 測試、輸出 |
| A4 | R1、R6 | W6：白名單內每句轉成對應固定句；白名單外與金鑰層句子回 `ACTION_FAILED_TEXT`；同一張卡重按回同一句；log 不含 JGB 訊息全文 | 單元 | 測試 |
| A5 | R1、R6 | W7：模擬寫入工具耗時超過 3 秒、HTTP 逾時、5xx、送出後連線錯誤、2xx 非 JSON、2xx 缺 id，客人都看到「結果未確認」而不是「無法執行」；同一張卡重按回同一句 | 單元 | 測試 |
| A6 | R6 | W8：非站內幫手金鑰看不到、也執行不了寫入工具 | 單元 | 測試 |
| A7 | R1、R5 | staging 實打（依 Q3）：五項各一次，含一張照片的修繕；兩條拒絕（未綁承租方的合約開手動帳單、非待發送帳單改到期日）客人看到對應固定句、沒有寫入；同一張卡按兩次只有一筆 | staging 畫面、對話 API 回應 | 截圖、回應、建立的 ID |
| A8 | R2 | 收案 `verifier` 一次 | 報告 | 報告檔 |

### 5.2 A7 的前提
- 正式機要先能連 staging（R4，待 JGB 放行 IP）。放行前改以本機容器連 staging 跑（辦公室 IP 2026-10-31 實測可達 staging）；金鑰若不在已授權範圍，交業主提供，⛔ 自己找。
- 授權依 Q3。

### 5.3 非目標
- 不量 OV、M0、解決率、錯筆卡（R2）。
- 不碰 JGB 工具移交、雙胞胎、填欄結構化 r1。
- JGB 合入 master、staging 放行 IP 不是本片範圍（寫進 JGB 規格書 L5）。
- 上傳上限的極端情況（接近 5 MB 單張、10 張）不在 A7；列後補。

## 6. 部署與回退

- 部署前（業主執行）：(1) 不寫入探測——`POST /api/external/v1/estates` 只帶 header 金鑰、body 不帶身分；回 400「寫入請求必須帶 role_id 與 viewer_user_id」＝金鑰過第 1 關，回 401／403＝金鑰不能寫（安審 P2-4）；(2) 正式機 `AGENT_ASSISTANT_KEY_IDS` 有值（只檢查有沒有值，不印值）。兩項加進 `switch-jgb-staging.sh` 的 `probe` 模式（主會話改腳本）。
- 今天部署的開關值：`JGB_WRITE_WIRING=on` 隨部署一起設。正式機仍連 www 時，W1 自動當 off（四個動作回「尚未開放」、照片不送，與現在相同）；`switch-jgb-staging.sh go` 改連 staging 後，同一個值自動生效，不必再部署。
- 回退：`JGB_WRITE_WIRING` 留空＝四個動作回「尚未開放」、照片不送；注意文字修繕單本來就會送（§1）。R4 回退另需 `JGB_API_BASE_URL` 改回 `https://www.jgbsmart.com`（`switch-jgb-staging.sh rollback`）。

## 7. 成本與時間（估）

收尾計畫審查約 10 分鐘；實作約 2 小時（security-executor，W1～W8、W10）；A7 約 20 分鐘、模型呼叫約 15 次（五項＋兩條拒絕＋重按，每項 1～2 回合）；verifier 約 1 小時。

## 8. 資安審查處置（`security-review-20261031.md`）

| 發現 | 處置 | 必修／後補（R6） | 落點 |
|---|---|---|---|
| P1-1 staging 實打沒有授權依據 | FIX | 必修（對外寫入正式資料庫） | §2 Q3、§5.2 |
| P2-1 逾時、5xx 後重複建立 | FIX | 必修（錯筆寫入） | W7、A5 |
| P2-2 照片真 JGB 路徑漏 `action.py` | FIX | 必修（不修則照片送不出或錯送，R1 做不到） | W4、A3 |
| P2-3 W6 照字面會外露 | FIX：封閉白名單 | 必修（資安外露） | W6、A4 |
| P2-4 讀取證明不了金鑰能寫 | FIX：不寫入探測 | 必修（部署後才發現不能寫＝上線出錯） | §6 |
| P3-1 開關閘門分散 | 單一來源、fail-closed 照做；啟動失敗後補 | 必修部分：fail-closed（回退開關要可靠）；啟動失敗：後補 | W1、A2 |
| P3-2 現值寫錯、回退不完整 | FIX | 必修（事實錯誤） | §1、§6 |
| P3-3 替身比 staging 寬 | FIX | 必修（替身測過、真環境被拒＝上線出錯） | W3、A3 |
| P3-4 base URL 沒驗 | DEFER | 後補 | W9 |
| P4 冪等鍵用 token 原文、`trust_env`、PATCH id 檢查、`USE_MOCK_JGB_API` 判讀不一 | PATCH id 檢查併入 W3；其餘 DEFER | 後補 | W3、後補 |
| 待查 1 寫入工具未綁金鑰 | FIX | 必修（新增寫入暴露面） | W8、A6 |
| 待查 2 JGB 冪等服務格式 | A7「同卡按兩次」實測 | — | A7 |
| 待查 3 staging 上傳上限 | DEFER | 後補 | 後補 |
| 待查 4 `externalInvalidField` 是否插值 | W6 只收全文完全相符，插值句落到白名單外 | — | W6 |
| 待查 5 LINE OA 改連 staging 的讀取範圍、staging 是否記金鑰 | R4 執行前查 | 後補（R4 目前被擋） | R4 前提 |
| 待查 6 寫入失敗固定句是否誤導 | 併入 W7 | 必修 | W7 |

## 9. plan-verifier 第 1 輪處置（`plan-verifier-r1-20261031.md`）

| 阻擋 | 處置 | 落點 |
|---|---|---|
| 1 W7 被 3 秒工具逾時包住、漏了多種「可能已寫入」結果 | FIX | W7、A5、§3 成功回應形狀 |
| 2 W6／W7 落點檔漏 `runtime.py`、`confirm_card.py`，重按句不一致 | FIX：補檔、receipt 錯誤碼封閉值域 | W6、W7、A4、A5 |
| 3 「不必要的資安別擋住」沒有規則承接 | FIX | R6、§8 必修／後補欄 |
| 4 Q2 漏業主先前選 B 與 DSP-130 裁決時點 | FIX | §0、Q2、W10 |
| 5 斷路器應現在觸發 | FIX：附斷路器報告，交業主裁 | §1、Q4 |
| 後補 1～8 | 4（腳本路徑）、6（`AGENT_ASSISTANT_KEY_IDS` 檢查）、7（R5 出處）、8（Q3 (b) 經站內幫手）已併入；1、2、3、5 不改變下一步，記後補 | §3、§6、R5、Q3 |

## 10. 收案時的清單收窄（業主 2026-10-31 核可）

業主裁定：「接受 API 讀回並收窄」（回 verifier INCONCLUSIVE 的待裁題）。
- A7 的觀察點由「staging 畫面」改為 staging 對外 API 讀回（明細／列表）；畫面層未看。
- A7 的「送出」與「附照片報修」只有實作者輸入的證據；verifier 的新說法只驗到出卡（按確認與上傳照片被 auto mode classifier 擋下），這兩條路徑的廣度標未驗證。
收案報告：`~/jgb-archive/arch-step3-20261018/write-wiring/report-close.md`。
