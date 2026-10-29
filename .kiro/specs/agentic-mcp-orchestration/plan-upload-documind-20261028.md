# 計畫：附件改為瀏覽器直傳、三種檔案皆由 DocuMind 辨識（UD 片，2026-10-28，業主核可：「照建議」，含 §6 OQ13 兩階段資安）

## 第一段：終點指標與驗收廣度

- **目標文件**：本片的凍結驗收清單 `.kiro/specs/agentic-mcp-orchestration/acceptance-upload-documind-20261028.md`（核可後與規則一起寫入）。本片沒有上層目標文件訂附件量法，所以以本片清單為目標文件；同一目標的前兩片：無（新目標，重新計數）。
- **終點量法與現值**：

| 量法 | 現值（受測物版本） | 本片預期變化 |
|---|---|---|
| 附件三流程（修繕照片、收據、謄本）解決率（Intercom 口徑） | **現值未量**（runtime `7764d1e6`；量法：執行第 0 步，用現行抓網址管線跑同一批題） | 新管線 ≥ 改前，且每類 ≥ 改前 −1 場 |
| 附件流程錯筆卡（選錯紀錄＋欄值錯） | **現值未量**（同上） | 0 |
| 附件流程錯筆寫入 | **現值未量**（同上） | 0 |
| 文字回合 M0 解決率（A11，迴歸門檻） | **50/52**（runtime `7764d1e6`，2026-10-28 18:15～18:33；`~/jgb-archive/arch-step3-20261018/retest-20261028/m0r_score.json` summary「harness\|現在」「全部 50/52」） | 0（不退步，≥ 50/52） |

- A5～A7 各自的通過條件（分類樹逐字名稱、台幣整數、謄本欄位與改前一致）是「解決」與「錯筆卡」的判定內容，併入上表前三列計分，不另列。
- **本片預期終點變化為 0**：本片是業主裁定的架構改動（R1、R2），宣稱的是「換管線後不退步、錯筆維持 0」，不宣稱改善；它也不是某個正變化片的前提。依全域「終點指標」第 4 條，計入斷路器的 0 變化片——業主已同意（§6 OQ6）。

  ⇒ 依全域「終點指標」第 3 條，業主已明示接受「現值未量、核可後以 UD-0 量的改前值為基準」（§6 OQ3）。
- **廣度**（三題）：使用者層項目每項 ≥3 組資料 × ≥5 種不同輸入 × 每輸入 1 次（穩定性另計）；輸入分兩部分，都不由實作者寫、跑前凍結：客人說法由不讀程式的出題代理依 7 類說法產生；照片／收據／謄本合成檔由不讀程式、看不到實作的備料代理在 UD-0 產生或挑選（沿用既有素材時寫出原作者），清單凍結於 `~/jgb-archive/upload-direct-20261028/inputs/frozen-files.json`（含 sha256）；改前改後在同一批題上各跑一次（改前＝現行抓網址管線、改後＝直傳＋DocuMind）。詳見 §7 廣度表。

## 1. 業主規則（原話 → 可檢查條件）

| ID | 條件 | 原話（2026-10-28） | 讀法註記 |
|---|---|---|---|
| R1 | 瀏覽器把檔案直接上傳到 AIChatbot；JGB 不再為上傳建專用網域、存暫存檔或產生簽章網址（修繕單照片仍由 jgb2 存放，見 UD-3） | 「我要傳過來」＋選項「瀏覽器直接傳 AIChatbot」 | 業主聽過反對理由（瀏覽器直連違反現行邊界、JGB 仍需發憑證）後維持 |
| R2 | 謄本、收據／發票、修繕照片三種檔案，辨識一律由 DocuMind 做 | 選項「所有檔案都走 DocuMind」；「依樣傳到 documind」 | 「依樣」讀作「一樣、照樣（也送 DocuMind）」；業主裁定此讀法、送出前仍重新編碼（§6 OQ7） |
| R3 | DocuMind 只負責辨識；對應 JGB 修繕分類、急迫程度、金額格式等由 AIChatbot 處理 | 「-documind 只需要辨識照片吧？ 急迫性之類 不是你要處理」 | 延伸到收據金額格式（同理：JGB 專屬格式歸我方）；業主已裁（§6 OQ1） |
| R4 | 先把整條流程串通；DocuMind 的資安缺口之後修，但上正式機前修完；串通期間只送合成檔案 | 「功能串通後再修」；DocuMind 回覆「測試期間請只送合成檔案」（業主轉貼） | 依 §6 OQ12 |
| R5 | 給 JGB 的串接文件同步改成新做法 | 「也修改給 JGB 方的串接方式」 | 含接口文件與 API 規格 #22；另一視窗的 4 份檔只列待改處、⛔ 碰 |

## 2. 目標形態（業界做法，原文存 `~/jgb-archive/upload-direct-20261028/sources/`，以 web-drive 渲染取得）

逐家做法（⛔ 推成全業界）：

- **Microsoft Direct Line**（`microsoft-directline.md`）：宿主後端用 secret 換 token，token「valid for one conversation」、範例 `expires_in: 1800`，可綁 `user.id`；瀏覽器以 `Authorization: Bearer` 打 `POST /v3/directline/conversations/{id}/upload`（multipart）；「Uploaded files are deleted after 24 hours.」
- **Zendesk Sunshine Conversations**（`zendesk-sunshine-conversations.md`）：宿主後端用 signing key 簽 `scope: "user"` 的 JWT，signing key「must never include them in your client side」，建議有效期「a few minutes」；附件 `POST /v2/apps/{appId}/attachments`（multipart）回 `mediaUrl`，訊息再引用。
- **Twilio Conversations (classic)**（`twilio-conversations.md`）：宿主後端簽 Access Token（含 identity），預設 3600 秒；上傳後以 Media SID 引用；未掛到訊息的媒體 5 分鐘內回收。
- **PubNub**（`pubnub-presigned-and-stream-chat.md`）：宿主後端 grant token（「Your server. Holds the secretKey.」），可綁 User ID；預簽上傳 TTL「generally short, such as one minute」；單檔 5 MB。
- **Slack**（`slack.md`）：三步上傳（拿 `upload_url` → POST → `completeUploadExternal`），可用前先「scan the file for malware」；token 是 app 的 bot／user token，沒有給終端瀏覽器的短期憑證——與本案情境不同，只作對照。
- 不同做法：上傳方式有 multipart 直打 API（瀏覽器端：Direct Line；伺服器端：Zendesk v2）與先拿網址再直傳（PubNub 預簽、Slack `upload_url`）兩類；有效期從 1 分鐘（PubNub 預簽）到預設不過期（Stream）。

**本案目標形態**（逐點只歸給原文支持的廠商）：
1. 持主金鑰的宿主後端換一張**短效、受限**的憑證交給瀏覽器，瀏覽器不持主金鑰：Direct Line（token「valid for one conversation」、可綁 `user.id`）、Zendesk（user JWT，signing key「must never include them in your client side」）、Twilio（Access Token 含 identity）、PubNub（「Your server. Holds the secretKey.」）。對回 R1；照舊 ⛔ 瀏覽器持金鑰、⛔ 直連 `/mcp`。
2. 瀏覽器以 multipart 直傳平台端點：Direct Line（`/conversations/{id}/upload`，上傳本身即送出一則訊息、回 activity id）。「先上傳、拿 id、訊息再引用」：Twilio（Media SID）、Slack（`file_id`，complete 時分享）、Zendesk（`mediaUrl`，但其附件 API 屬 v2 伺服器端，原文「scope of user … cannot be used with the v2 API」）。本案組合「瀏覽器直傳＋回 `upload_id`＋對話由 JGB 後端引用」查無單一廠商完全相同，是上兩種做法的組合（第一原理：對話仍須經 JGB 後端轉送，所以上傳與訊息分開）。對回 R1。
3. 未被引用的上傳短時間回收：Twilio（未掛到訊息 5 分鐘內回收）。Direct Line 是不論是否引用一律 24 小時後刪；Zendesk 隨訊息、對話或使用者刪除；PubNub 依方案保存。本案取 30 分鐘（偏離 D2）。對回 R1。

辨識分工（R2／R3）：查無業界對應，依第一原理：辨識服務保持通用（DocuMind 不綁 JGB 分類樹），客戶專屬的對應與判斷放在持有該領域資料與對話上下文的一方（AIChatbot），符合 DSP-091「理解由 AI、下一步由程式」。

## 3. 差距（現況，皆附可 grep 符號）

| 項 | 現況 | 目標 |
|---|---|---|
| 上傳入口 | `agent.turn` 只收 `image_urls`／`file_urls`（`mcp_facade.AGENT_TURN_SPEC`、`_make_agent_turn._agent_turn`），我方抓網址（`image_fetch.fetch_image`、`validate_image_url`、`_exp_gate`、`EXP_MAX_AHEAD_S = 900`） | 新 MCP 工具 `agent.upload_ticket`＋HTTP `POST /api/v1/agent/uploads`＋`agent.turn` 收 `upload_ids` |
| 對外入口 | `/mcp` 為唯一對外入口；`McpServiceGate` 管 `GATED_PREFIXES = ("/mcp", "/api/v1/agent")`、OPTIONS 不豁免，瀏覽器帶 Origin 不在 `MCP_ALLOWED_ORIGINS` 回 403；同前綴下有 `routers/agent.py` 的 `/trace`；app 層 CORS `allow_origins=["*"]`、`allow_credentials=True`（`app.py` `CORSMiddleware`）；rag-orchestrator 在 `docker-compose.prod.yml` 發布 `8100:8100` | 上傳端點只對「路徑完全等於、方法 POST／OPTIONS」豁免 gate（S1），獨立 Origin 白名單（S8），⛔ 沿用 `*` |
| nginx | `location /rag-api/` 先 `auth_request /_admin_auth`，無 `X-API-Key` 時注入後台金鑰（`knowledge-admin/frontend/nginx.conf.template` `map $http_x_api_key`）；改寫 `/rag-api/(.*)`→`/api/$1` | 新 `location /rag-api/v1/agent/uploads`：不過後台 auth、不注入金鑰、只轉發；`client_max_body_size` 收斂到檔案上限 |
| 位元組存放 | 只在回合內記憶體，回合結束 `del`（`prepare_image_turn`、`prepare_document_turn`）；`broken_photos` 只送中繼資料（`_photo_meta`） | 上傳暫存（記憶體、⛔ 進 `agent_state`／trace／log；依 W1，`/mcp` 本來就須單一 worker：`docker-compose.prod.yml` `UVICORN_WORKERS: ${UVICORN_WORKERS:-4}` 的註解「/mcp 用 agent.turn 須 1」，但 `app.py` 預設 `UVICORN_WORKERS` 為 4 ⇒ 加啟動檢查，見 S12）。文件類（謄本、收據）：被 `agent.turn` 引用的那一回合結束即刪（與現行 `prepare_document_turn` 同）；照片：保留到被引用的確認卡兌現或作廢；未被引用的上傳一律最長 30 分鐘 |
| 辨識 | 照片：`ImageRecognitionService`（`IMAGE_RECOGNITION_MODEL`）直接產 `suggested_category`／`suggested_item`／`suggested_emergency`；文件：`DocumentExtractionService.extract` 一次呼叫分類＋抽取；謄本才送 DocuMind（`_deed_typed_fields` → `analyze_deed`） | 三種都送 DocuMind `/api/v1/analyze`（`transcript`／`receipt`／`repair_photo`；`receipt` 待 DocuMind 交付，見 P3）；類型判定見 §6 OQ2；對應分類樹與急迫程度、金額正規化由我方 |
| DocuMind 回應 | DocuMind `784dc09`：`repair_photo` 回 `defect_labels`、`description`、`confidence`，VLM 失敗時 `understand` 仍回空值，但每頁新增 `llm_calls`（`call_log.py`：`ok`、`error` 錯誤類別）；收據只能走 `bill`（水電帳單抽取器，取不到收據金額，§5 推翻 2 (d) 1） | 照片：`llm_calls` 有 `ok=false` ⇒ 判辨識失敗，空 `damaged_items` 且呼叫成功 ⇒「照片看不出損壞」；收據：`receipt` 的 `amount`（原始字串）依現行 `receipt_typed_fields` 規則轉台幣整數，`needs_confirmation` 內的欄位不上卡、改問使用者 |
| 照片交 jgb2 | `broken_photos` 送中繼資料物件陣列，與 jgb2 網址字串陣列不符（API 規格 #22） | `POST /api/external/v1/repairs` 以 multipart 送檔（JGB 已同意兩種都收，時程待填） |
| 給 JGB 的文件 | 接口文件 §7 寫專用上傳網域、簽章網址、`exp` ≤900 秒；API 規格 #22 建議 (b) | 改寫成上傳票＋直傳＋`upload_ids`；#22 改 (a)（草案：`~/jgb-archive/upload-direct-20261028/jgb-upload-spec-draft-20261028.md`） |

## 4. 路徑（切片）

前提（外部，不在本片執行範圍）：
- **P1 DocuMind 測試環境位址＋測試 token**（DocuMind 端提供，私下交付）。未到 ⇒ UD-2 的 DocuMind 實呼叫段暫停，UD-1、UD-3 照做。
- **P3 DocuMind 新功能**（DocuMind 2026-10-28 回覆，業主轉貼）：新文件類型 `receipt`（`amount` 原始字串、`date`、`field_confidences`、`needs_confirmation`；認「總計／合計／合計（含稅）／合計新臺幣／總金額」取總計，分不出放 `needs_confirmation`；必要欄位不含戶號；認無標籤電子發票日期）；`/api/v1/classify` 加 `receipt`；`repair_photo` 新增 `damaged_items`（字串陣列，不綁 JGB 分類）。時程：DocuMind 模型切換驗收完成後開工，日期未定。未交付 ⇒ UD-2 的收據、照片段暫停，謄本段與 UD-1、UD-3 照做。DocuMind 驗收素材：我方提供三張合成收據（含預期值）與合成修繕照片（業主轉寄）。
- **P2 DocuMind 上正式機前四項**（呼叫認證與 https、S3 改 private〔先改 ACL 再修存檔設定〕、few-shot 不跨客戶、保存期限）——DocuMind 已回覆屬實、上正式機前修；「few-shot 不跨客戶」與「保存期限與刪除方式」涵蓋照片與收據的 OCR 全文（DocuMind 2026-10-28 回覆）；複核佇列裡的 OCR 快照是否在涵蓋範圍內，回覆未寫明，列 §4.1 上正式機前必查 T7。**列上線條件，⛔ 進後補清單**（DSP-115 第 3 條）。

| 片 | 成果 | 服務規則 | 主要改動（＝該片獨占檔案） | 執行者 |
|---|---|---|---|---|
| UD-0 | 量改前現值：用現行抓網址管線，跑 §7 凍結題組 | 終點指標 | 只跑測試，不改碼；`~/jgb-archive/upload-direct-20261028/inputs/`、`ud0/` | 主會話（長跑）＋備料代理（general-purpose，不讀程式）＋sim-customer |
| UD-1 | 上傳票、直傳端點、`upload_ids`、暫存與回收、nginx location、上傳端點 Origin 白名單 | R1 | `mcp_facade`（新工具、`AGENT_TURN_SPEC`、`_agent_turn`）、`app.py`（新路由註冊、上傳路徑脫離全域 `CORSMiddleware`〔S8〕、workers 啟動檢查〔S12〕）、新 `routers/agent_uploads.py`、新 `services/agent/upload_store.py`、nginx template；上傳位元組接到現行 `prepare_image_turn`／`prepare_document_turn`（辨識不變，見 UD-2 條件）；`image_urls`／`file_urls` 保留在開關 `AGENT_ATTACHMENT_INPUT=upload_ids|urls` 後（預設 `upload_ids`，回滾用）；`services/agent/limits` 封閉表；對應測試檔 | `security-executor` |
| UD-2（收據／照片段等 DocuMind 補收據類型與照片物件名稱，§6 OQ10） | 三種檔案送 DocuMind；我方對應分類樹／急迫程度、金額正規化；DocuMind 空回應判失敗 | R2、R3 | `documind_client`（`analyze_deed` 泛化為 `analyze(document_type)`、`upload_name`、回應解析）、`prepare_image_turn`／`prepare_document_turn`、`_normalize_recognition`、`receipt_typed_fields` | `security-executor` |
| UD-3 | 照片位元組以 multipart 交 jgb2（mock 端先收）；確認卡兌現後才刪暫存 | R1、R2 | `jgb_system_api`（repairs 建立）、`tools/action.py`、`confirm_card`（照片仍以 sha256 綁卡）、mock jgb2 | `security-executor` |
| UD-4 | 給 JGB 的文件改寫；新決策紀錄 | R5 | `docs/api/jgb2-web-assistant-integration.md`（§2 `IMAGE_URL_ALLOWLIST`、§7、F9／F10 列）、`jgb-api-spec-for-jgb-20261015.md` #22、`.claude/decisions/DSP-122.md`（取代 DSP-073 的上傳網域部分與 2026-10-15「只有謄本走 DocuMind」）；另一視窗 4 份檔列待改處交業主 | `executor` |

順序：UD-0 與 UD-1 並行（OQ13）；之後 UD-2 → UD-3 → UD-4，依序單一寫者（UD-1～UD-3 都動 `mcp_facade.py`，⛔ 並行）；UD-4 在 UD-3 收案後開，文件內容以 UD-1～3 實作為準。各片獨占檔案以上表為準，跨片共用的 `mcp_facade.py` 只在當前片的執行期間歸該片。

**偏離與取捨**：
- D1 上傳票有效 10 分鐘：短於 Direct Line 範例 1800 秒、長於 PubNub 預簽 1 分鐘；理由：使用者選檔到上傳通常在數分鐘內，票只拿來上傳、不拿來對話。
- D2 暫存最長 30 分鐘：介於 Twilio 5 分鐘與 Direct Line 24 小時；理由：要撐到確認卡兌現（使用者看卡、改欄位需要時間），又不長存個資。
- D3 暫存放記憶體：與 MCP session 同在單一 worker（S12 強制）；代價：重啟即失效，使用者要重傳（卡兌現時缺位元組 ⇒ 不寫入，S5）。理由：不新增持久化個資；nginx 與框架的暫存檔另以 S3、S11 關掉。
- D4 不做掃毒：只 Slack 文件寫了會掃；我方以內容判型（magic bytes）＋重新編碼照片（現行 `downscale_image`、`reencode_photo_jpeg`）＋PDF 驗頭；掃毒列「相關但不在本次範圍」。
- D5 類型判定（謄本 vs 收據）：見 §6 OQ2。

**相關但不在本次範圍**：掃毒；真 JGB 前端串接與 staging 實測（等 JGB multipart 時程）；DocuMind 四項修正（P2，DocuMind 端）；正式機部署。

## 4.1 資安要求（核可前資安審查 2026-10-28 的處置；全部 FIX，分兩階段，§6 OQ13）

| ID | 要求 | 來源 | 驗收 | 階段 |
|---|---|---|---|---|
| S1 | `McpServiceGate` 只對「路徑完全等於 `/api/v1/agent/uploads`、方法 POST／OPTIONS」豁免；⛔ 前綴豁免、⛔ 把 `/api/v1/agent` 移出 `GATED_PREFIXES` | P2-1 | A1b | 測試環境前 |
| S2 | `LIMITS` 封閉表新增：暫存總位元組上限（滿則拒）、每個 `(api_key_id, vendor_id, user_id)` 每小時發票數與上傳數上限、票存放數上限 | P2-2 | A1c | 上正式機前 |
| S3 | app 層邊讀邊計數、超過即中止；票與 Origin 在讀 body 之前驗（ASGI 層串流解析，⛔ 用 `UploadFile` 先讀整包） | P2-3、P3-6 | A1d（直打 8100） | 上正式機前（測試環境前先做簡單大小上限：超過 `max_bytes` 回 413） |
| S4 | 合成檔防護放在 `documind_client` 唯一送出口，預設開、⛔ 用 env 關；比對「上傳原檔」sha256；解除條件＝上線關卡逐條驗過 DocuMind 四項；client ⛔ 讀取或往下傳 `file_url` | P2-4 | A9 | 本機與串通期間開；JGB 測試環境關（OQ13）；上正式機前依原條件 |
| S5 | 送 jgb2 前重算每張照片 sha256、與卡上值比對；缺或不符 ⇒ 不寫入、回固定句 | P2-5 | A13 | 測試環境前 |
| S6 | 票與 `upload_id` 綁 `namespaced_identity`（含 `api_key_id`）＋`user_id`＋`role_id`＋`attachment_purpose` | P3-1 | A2 | 測試環境前 |
| S7 | `agent.upload_ticket` 不論哪把金鑰都必帶 `user_id`，缺 ⇒ 拒 | P3-2 | A2 | 測試環境前 |
| S8 | 票與 `upload_id`：CSPRNG、256 bit、伺服端只存雜湊、定時比較、⛔ 放網址；上傳端點沒帶 Origin 一律拒；Origin 名單按環境分（正式只 www、測試只 staging，待查 T5）；上傳路徑脫離全域 CORS | P3-3、P3-4 | A1e | 測試環境前 |
| S9 | nginx 用 `location = /rag-api/v1/agent/uploads`；明寫 `proxy_set_header X-API-Key ""`、清 `X-JGB-Identity`；`proxy_request_buffering off`；⛔ 過 `auth_request` | P3-5、P3-6 | A1f | 測試環境前 |
| S10 | DocuMind 回的自由文字一律經 `sanitize_data_piece` 與封閉值驗證；分類只取 `_resolve_tree_name` 過得了的值；⛔ 原文進模型資料段。`damaged_items` → 分類樹葉節點的對應方式在 UD-2 照片段開工前定案（候選：經 `sanitize_data_piece`＋長度上限後由模型在封閉葉節點清單內選、程式驗 enum；或程式比對），涉本條，定案前送 security-reviewer | P3-7 | A5 | 上正式機前（UD-2 照片段開工前定案） |
| S11 | 送 DocuMind 與送 jgb2 的影像一律先重新編碼成 JPEG（去 EXIF／GPS、去夾帶內容）；確認卡與 jgb2 的 sha256 綁重新編碼後那份；丟棄瀏覽器檔名 | P3-8、P3-9、P3-10 | A5、A12 | 測試環境前 |
| S12 | 啟用直傳時啟動檢查 workers＝1，否則直傳關閉並印原因 | P3-12 | A1g | 測試環境前 |
| S13 | app 層直傳路由開關 `AGENT_UPLOAD_ENDPOINT`（預設開）；`AGENT_ATTACHMENT_INPUT` 非法值採 `upload_ids`（不抓網址） | P3-13 | A3 | 測試環境前 |
| — | P3-11 接口文件 F2-3、F2-4、§1、§15 一併改 | P3-11 | A10 | 測試環境前 |
| DEFER | P4-1 全域 CORS `*`＋`allow_credentials=True` 為既有狀態，記後補清單 | P4-1 | — | 上正式機前 |

上正式機前必查：
- T2（用 `jgb-prod-readonly`）：正式機 `UVICORN_WORKERS` 與行程數——workers≠1 時附件整條停用（推翻 1 (d) 4）。
- T7（問 DocuMind，再驗）：複核佇列（`ReviewQueueService.enqueue` 寫入的 `pages` OCR 快照）受保存期限與刪除方式約束。驗法：DocuMind 書面確認保存期限與刪除方式；串通期間送一張會觸發 `needs_review` 的合成收據，到期後請 DocuMind 回報該筆佇列紀錄已刪（附查詢輸出）。未確認 ⇒ 不上線（DSP-115 第 3 條，個資）。

待查（不評嚴重度，實作前或上線前查）：T1 正式／測試機 8100 是否外網可達（雲端安全群組）；T2 正式／測試機實際 `UVICORN_WORKERS`；T3 容器內 Starlette 的 multipart spool 門檻（S3 改串流後不影響）；T4 JGB CSP——JGB 回覆「正式站的 CSP 目前只放行這個主機」，視為 JGB 消息；T5 staging 與正式是否共用同一套 rag-orchestrator；T6 DocuMind 照片模型：DocuMind 回覆「今天上線的版本（784dc09）起，修繕照片改由 Amazon Bedrock 東京 Qwen3 VL 235B（flex）辨識」（DocuMind 消息）；repo `784dc09` 的分流表 `LLM_PROVIDER_BY_DOCUMENT_TYPE` 預設為空（commit 訊息「預設不變」），實際走哪個模型由其線上設定決定——收據注入素材要在 DocuMind 實際模型下重跑（A6）。

## 5. 推翻卡

反向攻擊：`prod-redteam`（新開、未參與提案，2026-10-28，受測版本 AIChatbot `c4603e13`、DocuMind `ee72216`），主會話逐條對碼查證；下文「主會話查證」欄標的是查證結果。

**推翻 1：DSP-073 上傳網域＋簽章網址 → 瀏覽器直傳 AIChatbot（R1）**
- (a) 推翻：接口文件 §7「瀏覽器把檔案傳到 JGB 自己的上傳端點（不是我們的）」與 F9；F2-3「代理只呼叫 `agent.turn`」；F2-4（`mcp_facade.McpServiceGate` docstring「OPTIONS 不豁免：`/mcp` 僅 server-to-server，CORS 預檢本來就不該出現」）；DSP-073。
- (b) 原本為了：F9 只有決定、無理由句（`.claude/decisions/DSP-073.md`「核可，限定專用上傳網域 (Recommended)」）；觸發它的是 `image_fetch.py` `DEFAULT_IMAGE_URL_ALLOWLIST` 上方註記「放寬白名單是『停下交裁』的事，⛔ 不由改碼的人自己決定」。F10／#22 (b)：接口文件 §7.1「因為這樣我們不必轉送位元組、JGB 也不必抓我們的網址」。位元組只活一回合：接口文件 §7.3「只在本回合記憶體內取…其餘立即丟棄」。F2-3 自身理由：查不到（查過 DSP-073.md、DECISIONS DSP-073 列、plan-assistant §5b、接口文件 §6、§15）。
- (c) 新依據：業主裁定（業主消息）；業界對應見 §2（等級 A，原文存檔）。
- (d) 拿掉與補法：
  1. 瀏覽器碰不到我方 → 補：上傳票、Origin 白名單、S1／S8／S9（設計上補得回；`app.py` 已補進 UD-1 獨占檔）。
  2. 位元組只活一回合 → 補：文件類被引用那一回合結束即刪（與現行同）；照片要撐到卡兌現，⇒ **照片原檔跨回合留在記憶體**（最長 30 分鐘、⛔ 進 `agent_state`／log）。這擴大 DSP-073／DSP-076 的暫存範圍（DSP-076 只放行「會上卡的有型別值」）⇒ 業主接受（§6 OQ9）。
  3. 不轉送位元組 → 改成我方轉送照片給 jgb2：**JGB 交付前補不回**（multipart 時程待填）；另 API 規格 #22 記現行 `idempotency_key` 未宣告即被忽略，重送會重複掛照片 ⇒ 給 JGB 的規格加問冪等時程，列上線條件。
  4. 多 worker／重啟 → S12 只做到「不寫錯」：workers≠1 時直傳關閉，**附件整條停用**；回滾開關 `AGENT_ATTACHMENT_INPUT=urls` 在 JGB 已停建上傳網域後**沒有網址可抓、實際不能用**（§9 已改寫）。T2（正式機 workers 數）改列上正式機前必查。
- (e) 數據：無（沒有使用量或錯誤率數據顯示改了比較好）。需要的數據：同一批附件題在改前（抓網址）與改後（直傳）的成功上傳率與解決率；取得處：UD-0 量改前、A5～A8 量改後，同批題、同受測物版本紀錄。
- (f) 維持現況：代價＝JGB 要建專用上傳網域與簽章（JGB 已暫停此工作、改照新規格）；好處＝我方不保管檔案、`/mcp` 仍是唯一入口、照片不必轉送。
- (g) 反向攻擊：紅隊列 (d) 1～4 與事前驗屍三條（JGB multipart／冪等沒交付；部署 workers≠1 或重啟、`upload_id` 全失效且無退路；真瀏覽器整合問題要接 JGB 前端才會出現）。主會話查證：`app.py` `CORSMiddleware(allow_origins=["*"], allow_credentials=True)` 屬實、原 UD-1 獨占檔漏 `app.py` 屬實（已補）；文件類保留期與 A2 前後不一致屬實（已改）；其餘依碼推導，未實跑。
- **依推翻規則第 2 條**：(e) 為「無」⇒ 推薦應為「維持現況並取得數據」。但 (f) 的前提已變——JGB 已暫停建上傳網域、照新規格做，維持現況要 JGB 回頭建；這是業主消息、不是使用數據。本項業主已裁，本卡供紀錄並揭露 (d) 2～4 的代價；OQ9 業主已接受；上線條件見 §4.1 上正式機前必查。

**推翻 2：2026-10-15「只有謄本走 DocuMind」→ 三種都走 DocuMind（R2）**
- (a) 推翻：`plan-assistant-11-items-20261014.md` §7 業主裁示（2026-10-15，AskUserQuestion 逐字）「只有謄本用 DocuMind (Recommended)」（收據與修繕照維持本計畫抽取）；同檔 §3 第 4 點「謄本改由 DocuMind 解析（業主 2026-10-15，§7）」。
- (b) 原本為了：查不到選項的理由說明（查過 plan-assistant §3h、§7；DSP-073、DSP-076 列；HANDOFF-20261018；DSP-121；接口文件 §7.3）。間接脈絡：謄本改送 DocuMind 是因 S3 收尾審查時缺欄追問觸發不了；當時收據與照片已有我方封閉 schema 與實測（推論，等級 C）。
- (c) 新依據：業主裁定（業主消息）；DSP-121（10-28）已記「照片辨識改走 DocuMind（方向）」。
- (d) 拿掉與補法（主會話對 DocuMind `ee72216` 對碼查證）：
  1. **收據金額：現行補法補不回（已實測）**。DocuMind `bill_field_extractor.py` `PATTERNS["amount"]` 只認「本期應繳｜應繳金額｜應繳｜金額」，是水電／管理費帳單抽取器。主會話以同一正規式＋NFKC 對三張既有合成收據的文字跑：電子發票（總計 588）→ 取不到；手寫收據（合計新臺幣、表頭「金　額」）→ 取不到；注入發票（總計 860）→ 取不到；正對照「本期應繳金額：NT$ 1,234」→ 1,234。現行我方抽取：S3 verifier 8/8。`enable_llm=true` 才會呼叫 LLM 補欄，但會注入跨客戶 few-shot（DocuMind 已承認）。
  2. **收據可能出錯筆卡（依碼推導）**：若 OCR 依欄讀出「金額 1,650 700」，正規式取到單項 1,650，信心固定 `_MATCH_CONFIDENCE = 0.9`，高於門檻，不進 `needs_confirmation`；`expected.json` 明文「⛔ 不得取單項」。錯筆卡屬 DSP-115 第 3 條、不得後補。
  3. **類型判定：DocuMind 分類器沒有收據類別（已對碼）**。`document_classifier.py` `DocumentClassifier.classify` 只回 transcript／lease／id_card／unknown，沒有 bill ⇒ 收據送 `/classify` 一律 null。
  4. **OCR 全文進 DocuMind 複核佇列（依碼推導）**：`analyze.py` `_apply_confidence_gating` 在 `needs_review` 為真時呼叫 `ReviewQueueService(db).enqueue(result={"pages": pages, …})`，把各頁 OCR 結果寫進 DocuMind DB。現行 bill 無 `REQUIRED_FIELDS` ⇒ 退回 `KEY_FIELDS = ("amount", "date", "account_no")`，收據沒有戶號就必進佇列；DocuMind 新類型 `receipt` 的必要欄位不含戶號，可拿掉這個觸發，但低信心照樣入佇列。DocuMind 回覆的「保存期限與刪除方式」是否涵蓋佇列裡的這份 OCR 快照，回覆沒有寫明 ⇒ 列 §4.1 上正式機前必查 T7，確認並驗過前不上線。
  5. **照片對到分類樹葉節點：現行補法補不回**。`repair_photo_processor.py` `understand` 只回 `defect_labels`（提示詞例：漏水、壁癌、龜裂、設備損壞）、`description`、`confidence`；S10「只取 `_resolve_tree_name` 過得了的值」是逐字比對，瑕疵標籤不等於床、椅子等葉節點名。「描述 → 分類樹」由誰、用什麼模型、值域怎麼封閉，計畫未定。
  6. 照片看得出的急迫程度（現行 `suggested_emergency`）、低信心候選、「看不出損壞」與「DocuMind 失敗」的區分、幣別閘：DocuMind 都沒有對應欄位（依碼推導，紅隊 (1)-6～9）。
- (e) 數據：無；且 (d) 1、3 是反向的 A 級證據（實測／對碼）。需要的數據：同一批收據與照片題，我方抽取對 DocuMind 抽取的欄位正確率、錯筆卡數與解決率；取得處：UD-0 量我方抽取（改前），UD-2 收據／照片段完成後以 A5、A6 量 DocuMind（改後），同批題。
- (f) 維持現況（收據、照片仍用我方抽取，只有謄本走 DocuMind）：代價＝辨識分兩處、與 DSP-121 方向不一致；好處＝已實測（收據 S3 verifier 8/8）、不受 DocuMind P2 牽制、無跨客戶 few-shot 與複核佇列外露。
- (g) 反向攻擊：見 (d)；紅隊另列待查：DocuMind 照片延遲是否超出 `image_budget_s()`＝min(15, 回合逾時/2)；`description` 是否穩定提到物件名（DocuMind 改以 `damaged_items` 回物件，P3）；DocuMind 用的模型能否抵住收據上的指令注入（現行注入素材在我方模型下通過）。
- **依推翻規則第 2 條**，主會話推薦維持現況（收據、照片仍用我方抽取）並取得 (e) 的數據；業主看過本卡後裁示維持推翻 2（OQ8）。DocuMind 要支援收據與照片，需 DocuMind 端先補：收據抽取器（認「總計／合計」、取總計不取單項、`REQUIRED_FIELDS` 不含戶號）、分類器加 `receipt`、照片回物件名稱（DocuMind 已同意，見 §4 P3）。

## 6. 業主裁示（2026-10-28）

業主原話：OQ8「收據和照片 都是用 DocuMind」；其餘各題「全部照建議」（回覆主會話所列的建議表）。

| 題 | 裁示 |
|---|---|
| OQ1 | 收據金額格式（台幣整數、不確定不填）由我方處理（R3 的延伸） |
| OQ2 | 謄本與收據的類型：DocuMind `/classify` 加上收據類別後用它；在那之前由客服在對話裡問使用者一句「這是謄本還是收據」（不呼叫我方文件模型，A4 不變） |
| OQ3 | 終點現值核可後於 UD-0 量（UD-0 不改程式）；UD-1 在獨立 worktree 與 UD-0 並行開發，UD-0 量的是常駐服務 runtime `7764d1e6`，不受影響（OQ13） |
| OQ4 | 直接部署 chatai 正式機供 JGB staging 驗 AC8（DSP-124）；先部署 r1 修正前的程式並接通 DocuMind，⛔ 等 r1 與 M0，r1 完成後另行部署（DSP-125） |
| OQ5 | 只送合成檔或網路公開取得、不含客戶資料的影像（業主 2026-10-28：「可以送 因為那也是網路抓的」，見 OQ11）；資料組不足 3 組照實報 |
| OQ6 | 同意本片終點預期 0 變化（只宣稱不退步、錯筆 0），計入斷路器的 0 變化片 |
| OQ7 | 「依樣」＝也送 DocuMind；送出前一律重新編碼成 JPEG、去 EXIF／GPS（S11） |
| OQ8 | 收據與照片都走 DocuMind（維持 R2）；取捨見 §5 推翻 2 (d) 1～6 |
| OQ9 | 接受照片原檔留在我方記憶體到確認卡兌現或作廢，最長 30 分鐘，⛔ 進 `agent_state`／trace／log |
| OQ10 | 缺口由 DocuMind 補（收據類型、分類加收據、照片回物件名稱、失敗與「看不出損壞」分開）；UD-1 直傳不等，UD-2 的收據／照片段等 DocuMind 交付；⛔ 過渡開 `enable_llm=true`。需求訊息已交業主轉寄；DocuMind 2026-10-28 回覆同意（新類型 `receipt`、`classify` 加 `receipt`、`damaged_items`、以 `llm_calls` 區分失敗；時程未定），見 §4 P3 |

業主裁示（收斂審查 2026-10-28 後新增）：

| 題 | 裁示 |
|---|---|
| OQ11 | 修繕照片用網路公開取得的真實照片，可以送 DocuMind（業主：「可以送 因為那也是網路抓的」）。`fixtures/repair-1～3.jpg` 為 Wikimedia CC 照片（署名見該目錄 README）；`w9-docs/photos/` 6 張來源未記錄，依業主說明屬網路取得。這 9 張由主會話挑選 ⇒ 只作中間證據；計分組由備料代理在 UD-0 從網路公開來源另挑 ≥3 組、記下來源網址，⛔ 含人物與可辨識地址 |
| OQ13 | 資安要求分兩階段（業主：「就是我不停的說 我要上測試 你一直卡資安」→ 主會話提拆法 → 業主「照建議」）：§4.1「測試環境前」8 項（S1、S5〜S9、S11〜S13）做完即可交 JGB 測試環境；S2、S3、S10、T2、T7、P2 移到「上正式機前」。S4 改為：本機與串通期間預設開；JGB 測試環境部署時關閉，改由 JGB 測試人員只用我方提供的 12 張樣本（`~/jgb-archive/upload-direct-20261028/documind-samples/`）；照片送出前一律重新編碼、去 GPS（S11）。核可後不再送計畫審查，直接開 UD-1 |
| OQ12 | 我方先備妥；JGB 會在 JGB 測試環境串接（業主：「你先準備好 我JGB 會上 測試環境」）。本片收案＝本機端到端（模擬 JGB 前端）通過，且交付可給 JGB 測試環境串接的版本與串接說明；JGB 測試環境實接列上線前驗收。我方測試環境部署由業主執行 |

## 7. 驗收清單（草案；核可後凍結到 acceptance 檔）

| # | 規則 | 項目 | 觀察點 | 證據 |
|---|---|---|---|---|
| A1 | R1 | 上傳票＋直傳：jpg／png／webp／pdf 成功回 `upload_id`；無票 401、過期 401、Origin 不在名單 403、超大 413、內容型別不符 415（副檔名騙不過）、超過張數 429。另：(b) 不帶金鑰打 `/api/v1/agent/trace` 仍 401（正對照）、不變量 28 AST 測試全綠；(c)〔上正式機前〕S2 三項上限各觸發一次；(d)〔上正式機前〕直打 8100 送超大檔與無票請求，於讀完 body 前被拒（測試環境前只驗超大回 413）；(e) 從 `https://evil.example` 預檢不帶 ACAO、沒帶 Origin 被拒；(f) 後端收到的請求沒有 `X-API-Key`；(g) workers≠1 時直傳關閉 | 對本機實際 HTTP（經 nginx location 與直打 8100）發請求 | 指令輸出存檔 |
| A2 | R1 | `upload_id` 綁定：換金鑰、換 vendor／user／role／session、換用途、用第二次、過 30 分鐘 ⇒ `INVALID_INPUT`；缺 `user_id` 發票被拒；文件類於引用回合結束後、照片於卡兌現或作廢後、未引用者於 30 分鐘後，暫存已刪 | `/mcp` 實呼叫＋暫存計數 | 指令輸出 |
| A3 | R1 | `image_urls`／`file_urls` 在預設開關下回 `INVALID_INPUT`；切 `urls` 恢復舊行為（回滾） | `/mcp` 實呼叫 | 指令輸出 |
| A4 | R2 | 三種檔案各送 DocuMind 一次、`document_type` 正確，且我方視覺／文件模型 0 次呼叫（`damaged_items` 對應分類樹若定案用模型，只限文字、封閉清單，另計）；DocuMind `/classify` 尚無收據類別時，`document` 用途的上傳先由客服問使用者「謄本還是收據」再送（§6 OQ2） | DocuMind 測試端存取紀錄＋我方 trace | 紀錄節錄 |
| A5 | R2、R3 | 使用者層：修繕照片報修→確認卡類別／項目為分類樹逐字名稱、急迫程度依對話→確認→mock jgb2 收到 multipart、照片 sha256 與上傳相同 | 模擬客人經 pickchat 實跑＋mock 寫入紀錄 | 對話紀錄、寫入紀錄 |
| A6 | R2、R3 | 使用者層：收據→手動帳單卡金額＝台幣整數、不確定不填→確認 | 同上 | 同上 |
| A7 | R2 | 使用者層：謄本→建物件卡欄位與改前一致 | 同上 | 同上 |
| A8 | R2、R3 | A5～A7 錯筆卡＝0、錯筆寫入＝0；解決率改後 ≥ 改前、每類 ≥ 改前 −1 | `ov_precheck.py`／`score_pick.py` 口徑 | 計分檔 |
| A9 | R4 | 串通期間送 DocuMind 的檔案全部來自凍結的檔案清單（合成檔或網路公開影像，§6 OQ5）；送一張不在清單的檔 ⇒ 拒送、大聲失敗（正對照：清單內的檔照送）；JGB 測試環境部署設定關閉此防護（OQ13），本機預設開 | `documind_client` 送出口 | 指令輸出 |
| A10 | R5 | 接口文件（含 §1、§2、§6 F2-3／F2-4、§7、§15、F9／F10）與 #22：現行陳述不再出現專用上傳網域、簽章網址、`exp`、`image_urls`、建議 (b)、「代理只呼叫 `agent.turn`」、「不為瀏覽器放行 Origin」；新做法出現，且明寫 JGB 代理可呼叫的工具白名單只有 `agent.turn`、`agent.upload_ticket`（F2-3 的限制保留）；附正對照（同指令命中新詞） | grep | 指令輸出 |
| A12 | R1 | 跑完 A1～A8 後，log 與 trace 裡 grep 測試檔名與內容標記 0 筆（正對照：同指令命中一個已知 log 字串） | grep 容器 log 與 trace | 指令輸出 |
| A13 | R1、R2 | 出卡後重啟服務再按確認 ⇒ 不寫入、回固定句；照片被換（sha256 不符）⇒ 不寫入 | `/mcp` 實呼叫＋mock 寫入紀錄 | 指令輸出 |
| A11 | R1 | 文字回合不受影響：M0 56 場解決率 ≥ 50/52（本 session 現值，runtime `7764d1e6`，`~/jgb-archive/arch-step3-20261018/retest-20261028/m0r_score.json`） | 同 M0 跑法 | 計分檔 |

## 廣度

| 項目 | 類型 | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者（說法／檔案） | 改前對照 |
|---|---|---|---|---|---|---|
| A1～A4 | 機制項 | — | — | — | — | — |
| A5 修繕照片 | 使用者層 | UD-0 由備料代理從網路公開來源挑 ≥3 組（§6 OQ5、OQ11）；`w9-docs/photos/` 6 張與 `fixtures/repair-1～3.jpg` 由主會話挑選 ⇒ 只作中間證據、⛔ 計分 | ≥5（7 類說法） | 1 | 出題代理＋sim-customer／備料代理；照片來源見 §6 OQ11 | UD-0 同批題、runtime `7764d1e6` |
| A6 收據 | 使用者層 | UD-0 由備料代理新產合成收據 ≥3 組／只用合成檔（§6 OQ5）；既有 `receipt-1`、`receipt-2`、`receipt-inject.jpg` 由本線主會話（S3 片，`scripts/make_receipts.py`）產生 ⇒ 只作中間證據、⛔ 計分（另交 DocuMind 當其驗收素材） | ≥5 | 1 | 出題代理＋sim-customer／備料代理 | 同上 |
| A7 謄本 | 使用者層 | UD-0 由備料代理新產合成謄本 ≥3 組；既有 `assistant-demo-20261014/fixtures/deed.pdf`、`deed-photo.jpg` 由本線主會話（S3 片，2026-10-15，`scripts/make_deed.py`）產生，屬實作方 ⇒ 只作中間證據、⛔ 計分 | ≥5 | 1 | 出題代理＋sim-customer／備料代理 | 同上 |
| A8 | 使用者層（彙總） | 同 A5～A7 | 同上 | 1 | 同上 | 同上 |
| A9～A10、A12、A13 | 機制項 | — | — | — | — | — |
| A11 | 使用者層（迴歸） | M0 題組 1 組 | 29 種輸入（56 場，多數輸入 2 次；判分 52 場，依 HANDOFF §0.5 終點表「29 題 56 場（判分 52）」，另 4 場不計的原因本計畫未查） | 多數 2 | M0 第 2 步出題代理 | m0r 50/52 |

上位驗收方式：無。

## 8. 執行排定（測試選擇）

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模理由 | 跑前成本（估） |
|---|---|---|---|---|
| UD-0 改前批 | 改後是否不輸改前（R2 取捨） | 改前值即 A8 門檻基準 | 3 類 × ≥3 組 × ≥5 輸入＝≥45 場，廣度下限 | m0r 實測：56 場、6 位模擬客人並行、18 分（`m0r_driver.log` 18:15:31→18:33:03）⇒ 每位每場約 1.9 分；UD-0 ≥45 場、4 位並行 ⇒ 約 45×1.9÷4≈21 分（附件場較慢未實測，先跑第 1 批校準）；sim token 約 34 萬／56 場（m0r）⇒ 約 28 萬 |
| A1～A4、A9、A10 | 機制是否照規格 | 任一不過 ⇒ 修、不進 A5 | 機制項，逐條一次 | 數分鐘、0 模型呼叫（A4 除外：3 次 DocuMind） |
| A5～A8 改後批 | 終點指標與錯筆 | 錯筆 ≥1 ⇒ 停、交業主；解決率輸改前 ⇒ 交業主 | 與 UD-0 同批題 | 同 UD-0（約 21 分、約 28 萬 token） |
| A11 M0 | `_agent_turn` 共用入口改動有沒有傷文字回合 | <50/52 ⇒ 查、修 | 改的是所有回合共用的入口，判不出影響範圍 ⇒ 全跑（測試選擇第 2 條第二種） | 約 18 分、約 34 萬 token（m0r 實測） |

## 9. 回滾、停點、用量

- 回滾：`AGENT_ATTACHMENT_INPUT=urls` 恢復抓網址——⚠️ 只在 JGB 仍提供上傳網域時有效；JGB 已停建上傳網域後，回滾＝附件停用（文字回合不受影響）；DocuMind 路由以 `DOCUMIND_ROUTE_TYPES`（預設 `transcript,receipt,repair_photo`）縮回只謄本；nginx 新 location 移除即關閉直傳。
- 停點：錯筆卡或錯筆寫入 ≥1；A9 出現非合成檔；DocuMind 測試 token 未到（UD-2 實呼叫段暫停，其餘照做）。
- 用量（至本版）：子代理 984,870 token（盤點 2 位 129,887＋145,299、業界調查 185,708、資安審查 174,446、計畫審查 123,936、紅隊 225,594）；之後於收案時加總。

## 9.1 後補清單（DSP-115 第 2 條；收案時一起處理）

| 項 | 來源 | 不修下一步會變嗎 | 處置 |
|---|---|---|---|
| A11 迴歸只用 M0 1 組、重複場次計成案例 | 收斂審查 2026-10-28 第 6 條 | 不變：A11 只當文字回合不退步門檻，不影響 UD-0、UD-1 | DEFER：收案報告改寫成「1 組 × 29 輸入 × 多數 2 次」並另報按輸入去重的通過數；可用組數與未用理由於收案時補 |
| P4-1 全域 CORS `*`＋`allow_credentials=True` | 資安審查 2026-10-28 | 不變：既有狀態，直傳端點已脫離全域 CORS（S8） | DEFER |
| A2「照片於卡兌現或作廢後暫存已刪」：UD-1 沒有 `STORE.release` 的正式呼叫者，照片只靠 30 分鐘到期回收 | UD-1 verifier 2026-10-29 F1（P2） | 不變：本表 §4 已把「確認卡兌現後才刪暫存」排在 UD-3；30 分鐘上限仍在（OQ9） | DEFER 到 UD-3：UD-1 宣稱不含此項；UD-3 收案時以 `/mcp` 出卡→確認／作廢→暫存計數驗 |
| `tests/integration/agent/test_agent_turn_req.py` 在 main `c4603e13` 已 8 failed（`agent.turn: NO_MATCH`，`_outline_for_audience` 早退）；UD-1 新整合檔共用其輔助函式 ⇒ 3 failed | UD-1 驗證 2026-10-29（乾淨 c4603e13 worktree 與 main 工作樹皆重現） | 不變：UD-1 使用者層證據改由真服務 `ud1-after` 的 HTTP／`/mcp` 取得 | DEFER：修輔助函式後重跑 `test_upload_direct_mcp_req.py`（含 A2 暫存刪除計數）；動過該檔的 commit 為 d1ddc084、42c92448 |
| `upload_public_url_problem` 接受 `https://host/?a=/rag-api/v1/agent/uploads`（路徑其實是 `/`） | UD-1 verifier 2026-10-29 advisory（P3） | 不變：只在 env 設錯時發生 | DEFER：改以 `urlsplit` 的 path 判斷並拒 query／fragment |
| A2 換金鑰、換 vendor 只有單元證據 | UD-1 verifier 2026-10-29 INCONCLUSIVE | 不變：綁定比對同一函式，換 user／role／session／用途已在 `/mcp` 實測 | DEFER：有第二把測試金鑰時補實測 |

## 10. 另一視窗 4 份檔的待改處（⛔ 本片不碰，交業主轉）

- `jgb2-api-requests.md`：#22 列「照片上傳方式 (a)／(b)；專用上傳網域」→ 改 (a) multipart、刪上傳網域。
- `jgb-acceptance-checklist-20261015.md`：凡驗專用上傳網域、簽章網址、`exp`、`image_urls`／`file_urls` 的條目 → 改驗上傳票、直傳、`upload_ids`。
- `deploy-and-online-test-guide-20261015.md`、`docs/deployment-runbook.md`：`IMAGE_URL_ALLOWLIST` 設定步驟 → 改成上傳端點 Origin 白名單與 nginx location。
  （各檔確切行未讀；依 DSP-115 與本計畫，只列方向，由該視窗對碼。）
