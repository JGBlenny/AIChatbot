# LINE Bot 串接架構規劃與差距評估

> 版本：v1（2026-07-10）
> 範圍：LINE bot 串接修繕（優先場景），架構同時涵蓋帳單/合約等後續面向
> 前提決策：業者 bot 統一開在 JGB LINE Provider 底下（JGB 代管）；功能分流用 rich menu，不拆功能 bot

> ⚠️ **2026-09-11 更新：LINE bot 串接本身是現況且活著，⛔ 不要因為本文提到已刪模組就當整份退役。**
>
> 本文（v1，2026-07-10）提出的技術路徑是「新增 LINE Gateway，`chat` 管線零改動」
> ——把 LINE 流量正規化後打進既有的 `POST /api/v1/message`（`routers/chat.py`）。
> 這條路徑**已被實際上線的做法取代**：LINE OA 房東管家改走 `/mcp`
> （agentic-MCP，2026-09-08 demo 上線，見 `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`
> 與 `.claude/MAP.md` 〈agentic-MCP（LINE OA 房東管家）〉一節），而不是本文設想的
> 「LINE Gateway → 舊 chat 管線」。舊 chat 管線（`routers/chat.py`／
> `services/conversational_engine.py`／`services/form_manager.py`／
> `services/sop_orchestrator.py`／`services/vendor_sop_retriever_v2.py`）已於
> 2026-09-11 隨 commit `7c905408`／`10116570` 整批砍除，見 `.claude/DECISIONS.md`
> DSP-046。下文提到這些模組之處是**v1 規劃當時的技術假設**，不是現況；本文的
> 身份正規化模型、綁定流程、UID 值域政策、差距評估等內容是否仍對應
> `/mcp` 實作，本輪未逐項核對，留待下一次盤查——這是文件與實作的落差，交裁決，
> ⛔ 本輪不代為判斷 v1 規劃哪些段落仍適用。

## 1. 總體架構

核心原則：**新增 LINE Gateway 做「通道與身份正規化」，chat 管線零改動**。JGB 官方 bot 與各業者 bot 的 webhook 全部進同一個 gateway，正規化成現行 `VendorChatRequest` 後打 `/api/v1/message`，之後與 jgb2 Web 完全同路——SOP、表單、API 呼叫、知識隔離、計量額度全部照舊。

```
JGB 官方 bot ──webhook──┐
業者A bot（代管）──────┤                          ┌─ rag-orchestrator:8100
業者B bot（代管）──────┼─→ nginx(HTTPS) ─→ LINE Gateway ─→ POST /api/v1/message（X-API-Key）
                        │        │                │          POST /api/v1/images/upload
                        │        │                │
              LIFF 綁定頁 ←──────┘         line_channels（bot 註冊表）
              （JGB 登入）                  line_bindings（身份綁定表）
                                            line_sessions（session 映射）
```

### 1.1 身份正規化（同一條路的核心）

| 進入點 | vendor_id 來源 | role_id / user_id 來源 |
|---|---|---|
| 業者 bot | channel 本身（`line_channels.vendor_id`） | 綁定表；未綁定則缺省（一般問答可答、個資雙證降級＋推綁定卡片） |
| JGB 官方 bot | 綁定表（綁定時記下租客所屬業者） | 綁定表；未綁定只引導綁定 |

Gateway 自行解出 `vendor_id` 一併送出，**不依賴** jgb2-chat-integration.md §8.1 尚未實作的 role_id→vendor_id 反查；與現行 b2c 驗證層（vendor_id 必填）直接相容，計量/額度/隔離掛點不變。

送出格式：`{mode: "b2c", vendor_id, role_id, user_id, session_id, target_user: "tenant", message, image_urls?}`。

### 1.2 UID 值域（Provider 政策）

LINE userId 以 Provider 為值域：JGB Provider 底下所有 bot（官方＋代管業者）看到同一份 UID，**綁定一次全通**。業者若堅持自有 Provider 的既有 OA：UID 另一份、需在該 bot 內重綁、LIFF 需業者自行申請——綁定表以 `(channel_id, line_user_id)` 為 key 已預留此支線，但建議以「統一代管」為上架條款。

### 1.3 綁定流程（一次性認證，之後查表）

1. 未綁定用戶發話 → bot 回 LIFF 綁定卡片
2. LIFF 頁：`liff.getProfile()` 取 LINE userId ＋ 使用者登入 JGB 帳號
3. 驗證通過 → 寫入 `line_bindings`（LINE userId ↔ jgb_user_id + role_id + vendor_id）
4. 之後每則訊息 gateway 查表代入身份；LINE userId 不進 chat API 或 JGB API

認證方式二選一（待 jgb2 確認）：
- **A（建議）**：LIFF 內嵌 jgb2 現有登入，成功後回 user_id + role_id
- **B（備援）**：租客在 JGB Web 產生 6 位綁定碼，回 LINE 貼給 bot；jgb2 只需一個產碼頁＋驗碼 API

### 1.4 Gateway 資料模型（新增三張表）

| 表 | Key | 欄位重點 |
|---|---|---|
| `line_channels` | channel_id | channel_secret、access_token（**加密存放**）、vendor_id（NULL＝JGB 官方 bot）、rich_menu 設定、enabled |
| `line_bindings` | (channel_id, line_user_id) | jgb_user_id、role_id、vendor_id、status、bound_at |
| `line_sessions` | (channel_id, line_user_id) | active session_id、last_activity_at |

Webhook 共用一支端點，以 LINE 送來的 `destination`（bot userId）反查 channel，用該 channel 的 secret 驗 `X-Line-Signature`。新業者上 LINE ＝ `line_channels` 加一列。

### 1.5 渲染層（chat 回應 → LINE 訊息）

| chat API 欄位 | LINE 呈現 | 處理 |
|---|---|---|
| `answer`（Markdown） | text message | 需 strip Markdown（LINE 不支援）；後期可轉 Flex |
| `quick_replies` | Quick Reply 按鈕 | **LINE 上限 13 顆**；estate api_search 已截斷 10 筆無虞，修繕分類 api_select 全量回傳（form_manager.py:2150-2203）超過時 gateway 需改 Flex 列表或分頁 |
| `current_field_type: image` | 收 LINE 圖片 → 下載 content → `POST /api/v1/images/upload`（S3）→ 以 image_urls 續傳 | 端點已存在（routers/images.py:25），gateway 做轉接 |
| `video_url` | video message | 直接映射 |
| `action_type: quota_blocked` | 中性文案 | 照現行語義 |

Session 管理：gateway 以 `(channel_id, line_user_id)` 維護 session_id（自產、避開計量排除前綴），閒置 30 分鐘輪替＋「重新開始」指令；與 form_sessions 的 30 分鐘過期清理（form_manager.py:2975-3003）語義對齊。

### 1.6 修繕場景（優先驗證路徑）

表單 `jgb_repair_create` 已就緒（create_jgb_repair_form.sql）：estate_id（api_search）→ damage_photo（image，最多 3 張＋辨識）→ category_id/item_id/broken_reason（級聯 api_select）→ broken_note → emergency_status → `create_repair(role_id, ...)` 建單回單號。

追溯設計：工單真身在 JGB，追溯＝隨時重新查詢 `get_repairs(role_id, user_id)`（jgb_system_api.py:306，已註冊為 `jgb_repairs`），與對話歷史、session 輪替解耦。入口三層：rich menu「查報修進度」postback、建單回執附單號與查詢提示、自由問法命中查詢知識。

**觸發機制**（三層架構——修繕本質是平台交易，不是業者知識，觸發不依賴 SOP）：
- **基線＝全域知識條目**：knowledge_base 本就支援 `action_type=form_fill`＋`form_id`（add_knowledge_base_missing_columns.sql:9）。建一筆全域修繕觸發知識指向 `jgb_repair_create`，所有業者自由輸入共用，新業者上架零動作。修繕觸發現在掛在 vendor 2 SOP 是歷史路徑，非架構必然。
- **客製＝業者 SOP 覆蓋**：業者要自己的報修引導（措辭/前置步驟）才建 SOP，仲裁時業者 SOP 優先於全域知識；vendor 2 現有修繕 SOP 就地成為客製範例。SOP 檢索維持業者維度嚴格過濾（vendor_sop_retriever_v2.py:108），不動隔離語義。
- **按鈕＝`trigger_form_id` 直接觸發**：rich menu postback 繞過檢索直接進表單，決定性且通用，**Phase 1 就做**，全案唯一管線擴充。

通用的表示法（已查實）：知識層歸屬為陣列欄位 `knowledge_base.vendor_ids`，檢索過濾 `(array_length(kb.vendor_ids,1) IS NULL OR kb.vendor_ids && [vendor_id])`（vendor_knowledge_retriever_v2.py:109）——**vendor_ids 留空＝通用**，b2c 檢索天然納入，現庫絕大多數知識即此模式（2026-07-11 實查 1007/1009 筆全域），零改動。

仲裁已查實（詳 docs/chat-architecture-overview.md §3）：SOP 與知識並行檢索後比分（chat.py:1815-2104），分數接近且 SOP 有後續動作時 SOP 優先（Case 3.1）→ 業者覆蓋語義成立；邊角：通用知識分數高出 0.15 以上時知識勝，客製 SOP 錨點需對齊通用問法。另 Step 0.5（chat.py:3823）損傷圖片可直接觸發修繕 SOP——LINE 租客直接傳故障照片即進報修，Phase 2 圖片轉接通了之後天然生效。取捨：通用觸發＝每業者預設開報修，不用 JGB 修繕模組的業者需 per-vendor 開關（vendor_configs 參數）。

**業者客製分層**（能用輕的不用重的：參數→知識→SOP→表單）：
① 參數差異（電話/時段）→ `vendor_configs`；② 政策問答 → `knowledge_base` `vendor_ids=[X]`；③ 引導/前置流程 → `vendor_sop_items` 覆蓋通用錨點（vendor 2 現況即此模式）；④ 表單結構差異 → 現被 `UNIQUE(form_id)`（create_form_tables.sql:16）擋住，但解析層已支援業者變體（form_manager.py:102 `ORDER BY vendor_id DESC NULLS LAST`）——需求出現時改唯一鍵為 `(form_id, vendor_id)` 即可啟用，需求出現前不動。

### 1.7 整體架構分層（LINE 案的架構底座）

```
入口層   rich menu 按鈕(trigger_form_id) ─────────────┐（繞過語義，直達執行）
語義層   知識錨點 knowledge_base（通用=vendor_ids空／業者=vendor_ids[X]）
         └─ SOP 覆蓋 vendor_sop_items（業者客製路由＋開場，命中優先）
                          ↓ action_type 分派（chat.py:3033）
執行層   direct_answer │ api_call(lookup／jgb_*) │ form_fill(表單→chaining→決策樹) │ conversational(對話面向)
資料層   knowledge.answer │ vendor_configs(業者參數) │ lookup_tables(業者資料集) │ JGB API(平台個資,雙證)
```

- 職責：入口層給直達路徑、語義層認出意圖（薄）、執行層分派動作、資料層按歸屬回答事實。
- 業者資料三格（歸屬×形狀）：參數單值→vendor_configs；資料集多列→lookup_tables（純業者維度、決定性組合無 LLM，lookup.py:172-199）；租客個資→JGB API 雙證。
- lookup 錨點可通用、資料天生業者維度：品質＝業者資料就緒度，與 repair_enabled 同族——上架 checklist 統一管「模組開關＋lookup 資料已匯」。
- SOP 定位：業者客製的路由與開場節點，交棒對話流程層（表單/決策樹）；資訊型 SOP 留檢索直答，交易型 SOP 路由進流程（判準：有沒有「下一步」）。
- Gateway 只接觸入口層，語義層以下透明；未來帳單/合約面向上 LINE 只動語義層錨點與知識。

## 2. 差距評估

### 2.1 已就緒（零改動直接沿用）

| # | 項目 | 佐證 |
|---|---|---|
| 1 | 修繕建單表單（含照片、級聯、緊急度） | create_jgb_repair_form.sql、add_damage_photo_field_to_repair_form.sql |
| 2 | JGB API client：create_repair / get_repairs / estates / categories | jgb_system_api.py:306-412 |
| 3 | 圖片上傳端點（multipart → S3 → presigned URL）＋ chat API `image_urls` | routers/images.py:25、chat.py:3548 |
| 4 | 結構化回應（quick_replies / form_id / current_field_type / progress） | chat.py:3721-3758 |
| 5 | 使用量計量與額度（middleware 逐訊息掛 vendor_id） | app.py:171-234、add_usage_events.sql |
| 6 | X-API-Key 認證＋key 管理端點 | app.py:237-243、create_api_keys_table.sql |
| 7 | 個資雙證降級（缺 role_id/user_id 誠實降級） | jgb2-chat-integration.md §7 |

### 2.2 缺口——AI 系統側

| # | 缺口 | 規模 | 說明 |
|---|---|---|---|
| G1 | **LINE Gateway 服務**（全新） | 大 | webhook 驗簽、channel 路由、綁定、session 映射、渲染層、圖片轉接；建議獨立 compose 服務 |
| G2 | **修繕查詢知識條目未建** | 小 | `jgb_repairs` API 在、觸發知識不在；需建知識條目（action_type=api_call）＋問法錨點＋煙囪。⚠️ 知識層觸發配置半失效（P0：retriever SELECT 缺 trigger_mode 等欄，詳 chat-architecture-overview.md §3）——建錨點以 auto 直觸發為準，或先修 P0 |
| G3 | Markdown→LINE 純文字轉換 | 小 | gateway 渲染層內處理 |
| G4 | 選項 >13 顆的呈現 | 小 | 修繕分類全量回傳；gateway 需 Flex/分頁支線 |
| G5 | form_sessions 清理無排程 | 小 | cleanup_expired_sessions() 已實作但無 cron；需排程觸發 |
| G6 | ~~`pending_question` prod 套用~~ **已收案** | — | 2026-07-11 查實：7/7 prod dump 的 form_sessions 已含該欄位，prod 已套用 |
| G7 | 公網 HTTPS webhook 端點 | 中 | LINE webhook 硬需求；nginx 加 route＋TLS，gateway 進 compose |
| G8 | 租客視角補全案（§9） | 中 | 修繕表單不受影響；LINE 開放自由問答前需收案（帳務面向問法錨點為業者視角） |
| G9 | chat API `trigger_form_id` 擴充 | 小 | 按鈕直接觸發表單、繞過 SOP 檢索；決定性＋通用（不依賴業者 SOP），全案唯一管線擴充，**Phase 1 做**（見 §1.6） |
| G10 | **修繕觸發／表單綁死 vendor 2＋vendor 4 疑似壞觸發** | 中→**高** | 2026-07-11 實查：修繕 SOP 在 vendor 2（75 條）與 vendor 4（75 條，整包複製）；vendor 1/3 無觸發。表單 form_schemas vendor_id=2，而表單解析帶 vendor 過濾（form_manager.py:100 `vendor_id=%s OR NULL`）→ **vendor 4 觸發 SOP 後表單載入失敗**（觸發得了進不去，需煙囪證實）——per-vendor 複製 SOP 的路已被走過且證明會壞，通用化（表單升 NULL＋全域觸發知識）同時修此 bug。知識層無任何 jgb_repair_create 觸發條目（實查 0 筆） |

### 2.3 缺口——外部依賴

| # | 依賴 | 對象 | 說明 |
|---|---|---|---|
| E0 | **LINE 平台行為核實** | LINE 官方文件 | 本文件的平台斷言（UID 以 Provider 為值域、LIFF 取 userId、quick reply 上限 13）**未對現行官方文件驗證**（2026-07-11 證據分級盤點列 D 級）——LINE spec 動工的第一個任務即核實此批，錯一條綁定設計就要改 |
| E1 | **JGB 真實 API 對接** | JGB | 修繕 API 目前 mock（`USE_MOCK` fallback，jgb_system_api.py:318）；LINE 端到端上線前必須切真 |
| E2 | 綁定認證支援（方案 A 或 B） | jgb2 | LINE 串接案唯一需 jgb2 新做的東西 |
| E3 | Provider / Messaging API channel / LIFF app 申請 | LINE Console | 含業者代管條款談定 |

## 3. 分期

**Phase 1 — MVP 端到端（修繕）**：G1（gateway 核心：單 channel、驗簽、綁定、文字＋quick reply 渲染）＋ G2、G6、G7、G9 ＋ E2、E3（JGB bot 一支）→ 驗收：LINE 上完整跑通「綁定 → 按鈕報修（trigger_form_id）與自由輸入報修（SOP）→ 回單號 → 查進度」。E1 若未切真，先以 mock 驗流程、真 API 對接為上線 gate。

**Phase 2 — 多業者與圖片**：多 channel 動態註冊＋業者上架流程（代管條款）、G10 觸發架構落地（表單升全域＋全域觸發知識＋per-vendor 開關）、damage_photo 圖片轉接、G4 Flex 處理、G5 排程、rich menu 三格（報修/帳單/合約）。

**Phase 3 — 全面開放問答**：G8 租客視角補全案收案後，開放自由問答；Flex 卡片化（工單列表輪播）、帳單/合約面向接入（架構已通，僅知識與錨點工作）。

## 4. 安全事項（實作時走 security-sensitive 流程）

- webhook `X-Line-Signature` HMAC-SHA256 驗簽（per-channel secret）
- `line_channels.access_token` 加密存放；X-API-Key 僅存 gateway server 端
- 綁定端點防護（LIFF idToken 驗證、防代綁）；綁定表視同個資對應表
- 未綁定即無 role_id/user_id，個資查詢由現行雙證機制自動降級（不依賴 gateway 自律）
