# 接口 A：jgb2 站內幫手 → AIChatbot `/mcp`（`agent.turn`、`agent.upload_ticket`）

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

> **狀態：現況版（2026-10-29）。** 站內幫手已在正式機上線；JGB 已於 2026-10-15 17:38 起經 `/mcp` 呼叫。計畫：`.kiro/specs/agentic-mcp-orchestration/plan-assistant-11-items-20261014.md`（以下簡稱「計畫」）。
> 讀者：JGB（jgb2 後端）工程。本文件說「jgb2 代理怎麼呼叫我們」；反方向（我們呼叫 jgb2 的端點，以下稱**接口 B**）的現行正本是 `.kiro/specs/agentic-mcp-orchestration/jgb-api-spec-for-jgb-20261015.md`（已對碼 jgb2 master；列號 #16～#24 沿用），總帳 `jgb2-api-requests.md` 只指向該檔。接測清單見 `.kiro/specs/agentic-mcp-orchestration/jgb-acceptance-checklist-20261015.md`。
> 底層契約不重寫，**以 `docs/api/mcp-facade.md` 與 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/line-bot-integration-sheet-20260908.md` 為準**；本文件只寫站內幫手這條線的**取值、義務與對應**。
> 決策依據：DSP-011（權限由 jgb2 API 全權處理、本系統只管額度）、DSP-073（F11 文件欄位）、DSP-122（附件由瀏覽器直傳 AIChatbot、三種檔案交 DocuMind 辨識）、DSP-074（查詢與統計限於該成員在 JGB 畫面上看得到的範圍）、DSP-075（對話模型 gpt-6-luna）、DSP-076（有型別文件值暫存到出卡為止）。

## 1. 分工與範圍

- 入口：JGB 站內幫手後端呼叫本文件的 `/mcp`，網址 `https://chatai.jgbsmart.com/rag-api/mcp`（現況：對話回合唯一的入口，各呼叫端共用同一網址；瀏覽器上傳另走 §7）。目標入口是專用對話 API，定案後本文件同步改。舊 REST 鏈（`/rag-api/v1/message`）已於 2026-09-11 退役（DSP-046）。
- 我們（AIChatbot）：在 `agent.turn` 上完成站內幫手的 10 項對話能力；需要 jgb2 的資料與寫入，一律透過接口 B 的端點取得。接真 JGB 時，本系統還沒接上的寫入（延期繳費、建立物件／合約／手動帳單）我方**不發請求**，由程式回固定句（§10）；這些端點 JGB staging 已開放（DSP-132）。
- 你們（JGB）：持有金鑰與登入身分、組 header、轉送使用者訊息、向我們取上傳票並交給瀏覽器（§7）、把回應畫成前端。檔案由瀏覽器直接傳到我們的上傳端點，不經你們的伺服器。站內幫手入口的功能開關與白名單是 JGB 端設定（§14）。
- ⛔ 瀏覽器不直連 `/mcp`，也不持有金鑰；瀏覽器只打上傳端點（§7），而且只帶上傳票（§6 F2-4）。

## 2. 部署前置（我方服務設定）

這些是 AIChatbot 服務端的環境變數，由我方部署時設定；列在這裡是因為少設任何一項，接測結果會與本文件不符。

| 設定 | 值／規則 | 為什麼 |
|---|---|---|
| `UVICORN_WORKERS` | **`1`** | MCP session 存在行程記憶體；多 worker 時約一半請求會回 404「unknown or expired session ID」（2026-10-15 實測）。`docker-compose.prod.yml` 已註明 `agent.turn` 須 1，預設值 4 不可用。上傳暫存同樣放行程記憶體（§7）：workers 不是 1 時，啟動檢查會關閉直傳並印原因，附件整條停用 |
| `AGENT_TURN_ENABLED`／`AGENT_STAGE` | `true`／達 `M1` | `agent.turn` 才會註冊（`tools/list` 看得到） |
| `AGENT_WRITE_TOOLS_ENABLED` | `true` | 寫入動作（確認後建立）才可見 |
| `USE_MOCK_JGB_API`／`JGB_API_BASE_URL` | 正式機：**`false`**／目前 `https://staging.jgbsmart.com`（開 www 時改 `https://www.jgbsmart.com`） | `true` 時走我方替身，不會打到 jgb2；`false` 時 `JGB_API_KEY` 必須在，否則啟動直接 raise |
| `AGENT_MODEL` | **`gpt-6-luna`**（DSP-075） | 對話模型。未設時退回 `OPENAI_MODEL`，可能落到較弱模型，驗收結果不可比 |
| `AGENT_REASONING_EFFORT` | **`none`**（DSP-075） | gpt-6-luna 帶工具呼叫時只能 `none` |
| `AGENT_VERIFIER_MODE` | 正式機：**`grounding_observe`**（業主 2026-10-15 裁示；程式預設是 `enforce`） | `grounding_observe`：引用類只記錄、極性與機敏類照擋；上線後同批 5 題知識題實測 `enforce` 答 1／5、`grounding_observe` 答 3／5。健檢因此會在 `premise.red_flags` 記 `verifier_grounding_observe_on_real_api`（`status` 轉 `red`），屬已知。接測結果以正式機現值為準 |
| `AGENT_BUDGET_TOOL_CALLS`／`AGENT_BUDGET_DEADLINE_S` | 正式機：**`3`**／**`20`** | 每回合工具呼叫上限／回合預算（秒）；程式預設 4／20 |
| `AGENT_ASSISTANT_KEY_IDS` | 逗號分隔的整數 `api_key_id`，**站內幫手那把金鑰必須列入，正式機必設**；正式機值 `101`（限定 vendor 4、非內部）（計畫 §3i 第 1 點） | 列入的金鑰，`X-JGB-Identity` 缺 `user_id` 即被拒（400 `IDENTITY_MISSING_USER_ID`，§4、§11）。**未設定或空字串 ⇒ 不對任何金鑰啟用**（其他用戶端的單證行為不變），所以漏設不會報錯、只會讓「缺 user_id 就拒」靜默失效；含非整數 ⇒ 服務啟動失敗並印原因 |
| `AGENT_TURN_TIMEOUT_S` | 程式預設 30 秒；**正式機 `90`**（文件回合預算＝`min(45, 此值 / 2)`＝45 秒） | DocuMind 呼叫的可用時間＝此值扣掉已耗時再扣 20 秒模型迴圈保留；不足 1 秒即不送、回「沒查成」。JGB 代理的逾時須大於此值（§3） |
| `AGENT_UPLOAD_ENDPOINT` | 預設開；設為關閉值時 `agent.upload_ticket` 不註冊、上傳端點不啟用 | 附件直傳的開關（§7） |
| `AGENT_UPLOAD_PUBLIC_URL` | 對外的 https 絕對網址，路徑須為 `/rag-api/v1/agent/uploads`；未設或不合格 ⇒ 直傳關閉（fail-closed） | 這個值原字回給 JGB 當 `upload_url`（§7）；測試與正式環境各設各的主機 |
| `AGENT_UPLOAD_ALLOWED_ORIGINS` | 上傳端點專用的 Origin 白名單，與 `/mcp` 的 `MCP_ALLOWED_ORIGINS` 分開。未設、空值或只有 `*` ⇒ 不檢查 Origin（回 `Access-Control-Allow-Origin: *`），閘門只有上傳票；有設 ⇒ 只放行名單內的 Origin，沒帶 Origin 也拒（DSP-122） | 瀏覽器直傳的 CORS 設定（§7）；目前測試與正式都不設 |
| `AGENT_ATTACHMENT_INPUT` | `upload_ids`（預設；非法值也採此值） | `agent.turn` 的附件只收 `upload_ids`（§3、§7） |
| `DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN`／`DOCUMIND_ALLOW_INSECURE_TEST_HOST`／`DOCUMIND_INSECURE_TEST_HOST` | **未設 ⇒ 謄本功能關閉**。正式機（chatai）目前設為 DocuMind 測試機（明文 http、無認證，DSP-124、DSP-125），合成檔防護開著，只送樣本檔（§7）。謄本、收據／發票、修繕照片的辨識都由 DocuMind 負責（§7、§7.3）。`DOCUMIND_BASE_URL` 必須 https 且必帶 `DOCUMIND_TOKEN`（暫以 `Authorization: Bearer` 送出，**待 DocuMind 確認認證格式**）；任何其他組合一律視同未設 ⇒ 文件回合照舊，不放行建立物件，使用者看到「未啟用」固定句（§7.3）。明文 http 只在 `DOCUMIND_ALLOW_INSECURE_TEST_HOST=1` **且** base URL 的主機與連接埠逐字等於 `DOCUMIND_INSECURE_TEST_HOST`（`host:port`）時允許；測試主機位址不寫進 repo。呼叫一律 `enable_llm=false` | 目前線上 DocuMind 為明文 http、無認證；開放 `www` 使用前須改 https＋認證（DSP-124） |
| 限流 | 每小時 **1200 次**，計數鍵 `(api_key_id, vendor_id)`（`LIMITS.turns_per_hour`；`AGENT_TURN_CAP` 已不再被讀取） | 見 §6 F2-5 |

**謄本功能的正式上線前提（DocuMind 端，非本系統可解）**：三件——① DocuMind 端的 S3 物件須關閉 public-read；② 複核佇列須有認證（現況無認證）；③ few-shot 留存須處理（謄本含所有權人資料）。三項未解之前，謄本功能只限測試期、合成素材。

## 3. 呼叫方式

```
POST {AICHATBOT_BASE}/mcp            MCP streamable HTTP（方法與 body 由 MCP 協定定）
  X-API-Key: <限定 vendor 的金鑰>      必帶；見 §6 F2-1
  X-JGB-Identity: <JSON>              必帶；見 §4
```

- **呼叫順序**：MCP streamable HTTP 是有 session 的——先 `initialize`（帶 `Accept: application/json, text/event-stream`），從回應標頭取 `Mcp-Session-Id`，之後每個請求（`tools/list`、`tools/call`）都帶 `Mcp-Session-Id`；沒先 `initialize` 直接打 `tools/list` 回 400「Missing session ID」。MCP session 存在我方行程記憶體，我方重啟後舊 session 作廢（回 404「unknown or expired session ID」），須重新 `initialize`。⛔ 與對話的 `session_id`（§5，放在 `X-JGB-Identity`）是兩回事。
- 以 MCP `tools/call` 呼叫工具 `agent.turn`；要附檔時，另在使用者開附件面板時呼叫 `agent.upload_ticket` 取上傳票（§7）。JGB 代理能呼叫的工具**只有 `agent.turn` 和 `agent.upload_ticket` 兩個**。連線成功判準：`initialize` 後 `tools/list` 回 200 且看得到 `agent.turn`（回 403 `VENDOR_*` 表示金鑰與 vendor 沒對上）。
- 輸入參數：

```jsonc
{ "message": "<0–2000 字，可空字串>",
  "upload_ids": ["upl_…", "…"],                                 // 選填；repair 最多 10 個、document 只能 1 個（§7）
  "attachment_purpose": "repair|document",                      // 帶了 upload_ids 就必填，且要和取上傳票時相同
  "context": "<≤500 字>" }                                      // 選填；本回合背景資訊，⛔ 當作使用者說的話
```

  `message`、`upload_ids` 不得兩者皆空（否則 `INVALID_INPUT`）。`attachment_purpose` 的值：`repair`＝報修照片；**謄本**或**收據／發票**用 `document`。`image_urls`、`file_urls` 已停用，帶了回 `INVALID_INPUT`。
- 一次性回傳，沒有逐字串流；逾時（`TOOL_TIMEOUT`，`AGENT_TURN_TIMEOUT_S`）程式預設 30 秒、正式機 90 秒（見 §2）。JGB 代理自己的逾時須大於實際生效值。

## 4. 身分 header `X-JGB-Identity`

由 JGB **伺服端**依登入 session 組成（§6 F2-2），放在 header：

```
X-JGB-Identity: {"vendor_id":<int>,"session_id":"<§5 規則>","mode":"b2b",
                 "target_user":"property_manager","role_id":"<團隊 role_id>","user_id":"<登入成員 user_id>"}
```

| 欄位 | 站內幫手的取值 |
|---|---|
| `vendor_id` | 該團隊所屬業者 id；必須在這把金鑰的 `vendor_ids` 內，否則 403 `VENDOR_NOT_IN_KEY_SCOPE` |
| `session_id` | 依 §5 產生 |
| `mode` | 固定 `"b2b"` |
| `target_user` | 固定 `"property_manager"` |
| `role_id` | 登入成員目前所在團隊的 role_id |
| `user_id` | **登入成員本人**的 user_id，**必帶**。我們對 jgb2 的每一次呼叫（查詢、統計、寫入 body）都帶 `role_id`＋`user_id`，由 JGB 依成員可見範圍過濾、驗能力與資源歸屬（接口 B #16～#24）。站內幫手金鑰（`AGENT_ASSISTANT_KEY_IDS` 內）缺 `user_id` 時整個請求被拒：HTTP 400、`code=IDENTITY_MISSING_USER_ID`。字面值 `"anonymous"` 不是合法 `user_id`：HTTP 400、`code=IDENTITY_MALFORMED` |

`role_id`／`user_id` 是**上游信任輸入**（DSP-011）：我們不驗真偽，所以 §6 的義務是安全前提，不是建議。

## 5. `session_id` 規則（F1）

1. **由 JGB 伺服端產生**，使用密碼學安全亂數（CSPRNG），**至少 128 bit**（例如 16 bytes 以上的隨機值，以 hex 或 base64url 編碼）。
2. **綁定 `(user_id, role_id)`**：JGB 端保存「這個 session_id 屬於哪個 user_id＋role_id」，每次轉送前核對，不符就不得使用。
3. **換人或換團隊就換**：登入、登出、切換團隊（role）時，一律產生新的 `session_id`。
4. ⛔ **不得由瀏覽器帶入**：瀏覽器送來的任何 session 識別值都不得直接當 `session_id`；瀏覽器只持有 JGB 自己的登入 session，由代理查表換出本欄位。
5. **長度 ≤ 80 字元**（我們的實際鍵是 `mcp:{api_key_id}:{vendor_id}:{session_id}`，受 `VARCHAR(100)` 限制，超長整回合 `INVALID_INPUT`）。
6. 同一段對話每一次呼叫帶**同一個** `session_id`；換 `session_id` 就是新對話，先前上下文看不到。對話歷史由我們保存，⛔ 不需要也不能回傳歷史。
7. **我方保證**（計畫 §3i 第 3 點）：同一 (api_key, vendor, session_id) 下，(user_id, role_id) 與建立時不同 ⇒ 不續用對話與確認卡；⛔ 防呼叫端冒用身分（DSP-011 信任在上游），依賴 F2「代理只呼叫工具白名單（`agent.turn`、`agent.upload_ticket`）」。
   細則：不續用＝視為新對話，舊的對話內容、待確認卡、已釋出的上下文一律不帶入。比對規則：位元組完全相等、不做正規化；匿名（無 `user_id`）續匿名可續，匿名與具名互換一律重置；待確認卡記錄建立者的 `(user_id, role_id)`，按鍵時先比對，不符與「不認得的確認鍵」同一處理，不兌現。實測：換人後按前人的確認鍵，得到「這筆確認已失效，請重新確認一次。」，jgb2 沒有寫入。
   **保證的邊界**：這道比對只防「同一 session_id 被不同的 `(user_id, role_id)` 用到」，不防呼叫端冒用身分——`user_id`／`role_id` 的真偽信任在上游，本系統不驗；整體安全依賴 §6 F2。第 1～4 點仍是 JGB 端的義務，不因我方比對而放寬。

## 6. 金鑰與代理義務（F2）

| 編號 | 義務 |
|---|---|
| F2-1 | **金鑰只在 JGB 伺服端。** 我們另發一把**限定 vendor** 的金鑰給站內幫手（`vendor_ids` 只含展示團隊的 vendor、非 `is_internal`），不與其他呼叫端共用。金鑰不得出現在前端程式、頁面、瀏覽器可見的回應、log、指令列參數。 |
| F2-2 | **身分只由登入 session 組。** `vendor_id`／`role_id`／`user_id`／`target_user`／`mode` 一律由伺服端依登入 session 決定，⛔ 不採信任何瀏覽器送來的身分值。 |
| F2-3 | **代理只呼叫 `agent.turn` 和 `agent.upload_ticket` 兩個工具，且只轉 §3、§7 列出的參數**（`agent.turn`：`message`、`upload_ids`、`attachment_purpose`、選填 `context`；`agent.upload_ticket`：`attachment_purpose`）。不呼叫 `/mcp` 的其他工具（`jgb2.query.*`、`jgb2.action.*`、`kb.*`…），不加其他參數。身分鍵（`vendor_id`、`role_id`、`user_id`、`target_user`、`mode`、`viewer_user_id`）出現在工具參數時，我方**剝除、不採用**（`ToolRegistry.call`，不回錯誤、記 trace）；其他未宣告鍵 ⇒ `INVALID_INPUT`。身分鍵改為一律拒絕：**待業主裁**。 |
| F2-4 | **瀏覽器 ⛔ 直連 `/mcp`，也不持有金鑰。** 對話一律經 JGB 代理轉送；`/mcp` 帶 `Origin` 且不在 `MCP_ALLOWED_ORIGINS` 白名單回 403。瀏覽器唯一能打的是上傳端點（§7）：只帶上傳票、不帶金鑰與 `X-JGB-Identity`，閘門是上傳票；Origin 預設不檢查，要收緊時以 `AGENT_UPLOAD_ALLOWED_ORIGINS` 單獨設定。 |
| F2-5 | **限流是全站共用，需向使用者告知。** 每小時上限 1200 次，計數鍵是 `(api_key_id, vendor_id)`，**不含** `session_id`／`user_id`：同一業者所有成員共用同一桶，換 session 不會重置。計數器在行程記憶體，所以部署須 `UVICORN_WORKERS=1`（§2）。超過回 `RATE_LIMITED`；額度（`vendor_quotas`）達限回 429／`QUOTA_EXCEEDED`。前端遇到時請顯示「目前使用人數較多，請稍後再試」之類的固定句，⛔ 不要自動重試迴圈。 |
| F2-6 | **確認回合逾時，⛔ 自動重試。** 使用者按下確認鍵（`confirm_submit:…`）那一回合若逾時（`TOOL_TIMEOUT`）或連線中斷，結果是**未知**——寫入可能已發生。代理 ⛔ 不得自動重送；請顯示「處理逾時，請先到清單確認是否已建立，再決定要不要重送」，由使用者決定。一般（非確認）回合逾時，本回合狀態不會被存下，可由使用者手動重送。同一確認鍵重送回同一份結果、不重複建立，已在我方替身驗證；對真 jgb2 端點的冪等（接口 B 的 `idempotency_key`）要等接測才算數，在那之前請當作「可能重複建立」處理。 |

## 7. 圖片與文件上傳（F9，DSP-122）

站內幫手的檔案由瀏覽器直接傳到 AIChatbot 的上傳端點，`agent.turn` 只帶 `upload_ids`。JGB 不需要專用上傳網域、暫存檔或簽章網址。

流程總覽：

```
① JGB 後端 ──/mcp agent.upload_ticket──▶ AIChatbot   取得上傳票（綁定使用者與對話）
② JGB 後端 ──上傳票──▶ 瀏覽器
③ 瀏覽器   ──POST upload_url（Bearer 上傳票）──▶ AIChatbot   一次一個檔案，拿回 upload_id
④ 瀏覽器   ──訊息＋upload_id──▶ JGB 後端
⑤ JGB 後端 ──/mcp agent.turn（upload_ids）──▶ AIChatbot   照舊帶金鑰與 X-JGB-Identity
⑥ AIChatbot ──POST /api/external/v1/repairs（multipart，含照片）──▶ jgb2   只限報修照片
```

瀏覽器照舊不直連 `/mcp`，也不持有金鑰；只打第 ③ 步的上傳端點，而且只帶上傳票。金鑰、`X-JGB-Identity`、`session_id` 的規則都不變。

### 取得上傳票：`agent.upload_ticket`（JGB 後端 → AIChatbot，經 `/mcp`）

呼叫方式和 `agent.turn` 相同：同一個網址、同一把金鑰、同一個 `X-JGB-Identity`。`X-JGB-Identity` 一定要帶 `user_id`，沒帶就拒絕，回 `INVALID_INPUT`。

| 參數 | 必填 | 說明 |
|---|---|---|
| `attachment_purpose` | 是 | `repair`（報修照片），或 `document`（謄本、收據、發票） |

回傳：

```json
{
  "upload_url": "https://<AIChatbot 主機>/rag-api/v1/agent/uploads",
  "upload_token": "<不透明字串>",
  "expires_at": 1793185000,
  "max_files": 10,
  "max_bytes": 5000000,
  "accept": ["image/jpeg", "image/png", "image/webp"]
}
```

| 欄位 | 說明 |
|---|---|
| `upload_url` | 第 ③ 步要打的網址。請照回傳值使用，不要寫死在程式裡；測試環境和正式環境的主機可能不同。 |
| `upload_token` | 第 ③ 步放在 `Authorization: Bearer` 後面。不要放進網址，也不要寫進 log。 |
| `expires_at` | 到期時間，Unix 秒。發票後 **10 分鐘**到期。 |
| `max_files` | 這張票最多能傳幾個檔：`repair` 10 個，`document` 1 個。 |
| `max_bytes` | 單檔上限 5,000,000 bytes。 |
| `accept` | `repair`：`image/jpeg`、`image/png`、`image/webp`。`document`：`application/pdf`、`image/jpeg`、`image/png`。 |

- 一張上傳票綁定這六項：金鑰、`vendor_id`、`user_id`、`role_id`、`session_id`、`attachment_purpose`。只能用在發票時的那個對話。
- 使用者每次打開附件面板，取一張票就夠了。票過期就重新取，不要留到下一個對話用。

### 瀏覽器上傳（瀏覽器 → AIChatbot）

```
POST <upload_url>
Authorization: Bearer <upload_token>
Content-Type: multipart/form-data; boundary=…
表單欄位：file（一次一個檔案）
```

- 一次請求只放一個檔案，欄位名 `file`。要傳多個檔就送多次，每次都帶同一張票，總數不能超過 `max_files`。
- 用 `FormData` 送的時候，`Content-Type` 不要自己設，交給瀏覽器帶 boundary。
- 檔案型別依**檔案內容**判斷，不看副檔名，也不看瀏覽器送來的 `Content-Type`。瀏覽器送的檔名不會保存。
- 成功回 `201`：`{ "upload_id": "upl_…", "content_type": "image/jpeg", "size": 812345, "sha256": "<64 位小寫 hex>" }`。
- 失敗時 body 一律是 `{ "error_code": "…", "message": "…" }`；前端請依 `error_code` 判斷，不要直接把 `message` 顯示給使用者：

| HTTP | `error_code` | 意思 | 前端建議處理 |
|---|---|---|---|
| 400 | `UPLOAD_MALFORMED` | 不是 multipart、欄位名不是 `file`，或一次送了不只一個檔 | 修正前端送法 |
| 401 | `UPLOAD_TOKEN_INVALID` | 沒帶票，或票不對 | 重新取票 |
| 401 | `UPLOAD_TOKEN_EXPIRED` | 票過期 | 重新取票後再傳 |
| 403 | `ORIGIN_NOT_ALLOWED` | 只在設了 `AGENT_UPLOAD_ALLOWED_ORIGINS` 時出現：沒帶 Origin，或 Origin 不在名單內 | 不重試 |
| 413 | `FILE_TOO_LARGE` | 超過 `max_bytes` | 請使用者換小一點的檔 |
| 415 | `UNSUPPORTED_FILE_TYPE` | 檔案內容不是 `accept` 列的型別 | 請使用者換檔 |
| 429 | `UPLOAD_LIMIT_REACHED` | 這張票已經傳滿 `max_files` | 提示已達上限 |
| 429 | `RATE_LIMITED` | 同一使用者短時間內取票或上傳太多次 | 稍後再試 |

CORS：

- Origin 預設不檢查：任何 Origin、沒帶 Origin 都照收，能不能上傳只看上傳票。日後若設了 `AGENT_UPLOAD_ALLOWED_ORIGINS`（§2），就只放行名單內的 Origin。
- 上傳帶了 `Authorization` 標頭，瀏覽器會先送一次預檢（`OPTIONS`），由我們回應，前端不用另外處理。預檢的 `Access-Control-Allow-Origin` 是 `*`（設了白名單時改為請求的那個 Origin）；`Access-Control-Allow-Methods` 是 `POST`；`Access-Control-Allow-Headers` 是 `Authorization, Content-Type`；`Access-Control-Max-Age` 是 600 秒。
- **不帶 credentials**：上傳端點不看 cookie，也不回 `Access-Control-Allow-Credentials`。`fetch` 請用 `credentials: "omit"`；用 XHR 的話，`withCredentials` 保持 `false`。
- 需要的請求標頭只有 `Authorization`。不要帶 `X-API-Key` 或 `X-JGB-Identity`，帶了我們也會丟掉。
- 設了白名單且 Origin 不在名單內時，預檢回 `403`、不帶 `Access-Control-Allow-Origin`；實際上傳也回 `403 ORIGIN_NOT_ALLOWED`。
- 上傳主機和 `/mcp` 是同一台，JGB 現行 CSP 不用改。

```js
const fd = new FormData();
fd.append("file", file);
const res = await fetch(ticket.upload_url, {
  method: "POST",
  headers: { Authorization: `Bearer ${ticket.upload_token}` },
  body: fd,
  credentials: "omit",
});
```

### `agent.turn` 帶 `upload_ids`（JGB 後端 → AIChatbot）

- `upload_ids`：字串陣列。`repair` 最多 10 個；`document` 只能 1 個。帶了 `upload_ids` 就必須帶 `attachment_purpose`，而且要和取票時相同。
- `image_urls`、`file_urls` 停用，帶了回 `INVALID_INPUT`。`message` 和 `upload_ids` 兩個都沒帶，回 `INVALID_INPUT`。
- 每個 `upload_id` 只能用一次；只能由**同一把金鑰**，加上同一組 `vendor_id`、`user_id`、`role_id`、`session_id`、`attachment_purpose` 使用；上傳後 **30 分鐘**內有效。
- 遇到以下任一情況，**整則訊息**都不處理，回 `INVALID_INPUT`，也不會只處理其中幾個：過期、已經用過、不屬於這個 session 或金鑰／vendor／user／role 不符、用途不符、數量超過上限。處理方式：前端請使用者重新上傳，換到新的 `upload_id` 後再送。
- 同一使用者 3 秒內的檔案與文字請合成一次 `agent.turn`，不要拆回合。
- 照片型別 jpeg／png／webp；PDF 最多辨識前 5 頁（`DOC_MAX_PAGES`）。

### 辨識與檔案保存

- 謄本、收據／發票、修繕照片的辨識一律由 DocuMind 做；DocuMind 只負責辨識，對應 JGB 的修繕分類、急迫程度與金額格式由 AIChatbot 處理。
- 檔案只放在我們服務內部暫存（行程記憶體），用完即刪，內容不進 log。文件：引用它的那一輪對話結束就刪；照片：確認卡送出或作廢後刪；沒被引用的檔：最長 30 分鐘刪。正式站和 staging 規則一樣。
- 目前測試階段，只有我們提供的樣本檔會送去 DocuMind 辨識；其他檔案上傳和對話照常進行，但不送辨識，助理會請使用者用文字描述。開放真實檔案會另行通知。

### 7.1 照片附進修繕單（(6-2)）

- 回合帶 `attachment_purpose=repair` 與 `upload_ids`：照片交 DocuMind 辨識，我們對應修繕分類並出確認卡；使用者確認後建立修繕單，照片附進該張修繕單。
- 照片位元組由我們以 `multipart/form-data` 送給 jgb2 的 `POST /api/external/v1/repairs`（API 規格 §4 #22 方案 (a)）：原有文字欄位照舊放在同名表單欄位，照片放在 `broken_photos[]`，每筆是一個檔案。
- 送出前，照片一律重新編碼成 `image/jpeg`，並去掉 EXIF 和 GPS。每張修繕單最多 10 張，每張 ≤ 5,000,000 bytes；檔名由我方程式產生，格式 `photo-N.jpg`（⛔ 使用者檔名）。確認卡顯示「附照片：N 張」，N 與照片的 `sha256`（重新編碼後那份）納入確認卡雜湊；送出前重算比對，不符就不寫入。
- jgb2 收下照片、掛到這張修繕單，回應格式照舊；jgb2 也請自己驗一次型別，提供照片時加上 `X-Content-Type-Options: nosniff`。成員身分驗證與冪等同樣適用，同一個冪等鍵重送時照片不能重複掛（API 規格 §0）。
- jgb2 staging 已收 multipart（API 規格 #22；≤10 張、每張 ≤5,000,000 bytes、JPEG／PNG）。本系統還沒改接，接真 jgb2 時照片仍進不了修繕單，文字報修不受影響。⛔ JGB 不得回頭抓我方提供的任何網址。
- 缺必填欄位導致先追問再出卡時，照片仍會附進最終那張卡（只有「出卡」才消耗該回合的照片）。

### 7.2 文件：一次一份

- 上傳**謄本、收據、發票**時，取票與回合都須帶 `attachment_purpose=document`；檔案是 PDF 或照片，用 1 個 `upload_id`，**一次一份文件**。
- 文件回合預設只做摘要與讀取，**不寫入**；只有下列兩種文件種類、且解析狀態為成功或部分成功時，才放行對應的建立動作（其餘文件種類、或文件種類與動作不符，一律不放行）：

| 文件種類 | 放行的建立動作 |
|---|---|
| 建物謄本（`building_deed`） | 建立物件（`estate_create`） |
| 收據／發票（`bill_receipt`） | 建立手動帳單（`manual_bill_create`） |

- 文件上讀到的值**只有封閉表內、有型別的欄位**會進確認卡與送出的 body（DSP-073／076）；文件的自由文字（開立人、付款人、品名、參考編號、備註等）⛔ 進確認卡、body、log、trace。其他欄位使用者必須自己說，而且必須是使用者**自己打的字**（自文件回合起、最多 5 回合內的使用者訊息中的原文），模型代填或從文件推出來的文字一律不採用，視為缺欄、由系統追問。
- 這些有型別的文件值依 DSP-076 暫存到「出卡、按取消、下一個不同動作的出卡、或第 5 回合」為止，之後清除；暫存內容不含使用者訊息或文件自由文字。
- 注意：文件回合中**模型回給使用者的那段話**會留在對話歷史裡（既有行為，DSP-076 未涵蓋），歷史依 §12 的保存規則處理。

### 7.3 謄本（(9-2)）：由 DocuMind 解析

- 我們判定為建物謄本後，把**同一份已通過上列檢查的檔案位元組**送 DocuMind 解析（`DOCUMIND_BASE_URL`；我方模型不代抽謄本欄位）。回應只在本回合記憶體內取下列欄位，其餘（所有權部、統編、住址、他項權利、原文）立即丟棄，不進 log、trace、任何狀態：
  - **電子謄本**（恰好 1 筆且標示部存在）：縣市、行政區、建物門牌（地址，去掉縣市行政區前綴）、主要用途（對照成 `residential`／`business`／`parking_space`，對不到則缺）、總面積、層次（恰一筆時轉成「N樓」，否則缺）；物件名稱由程式取地址。
  - **掃描或拍照**：只取地址、主要用途、總面積、樓層，且該欄不在 DocuMind 的待確認清單、信心 ≥ 0.85；**縣市與行政區不取**（OCR 錯字風險），一律由系統追問使用者補。
  - **一份 PDF 含多張謄本** ⇒ 不填，請使用者一次上傳一張。謄本一次一份：1 個 PDF 或 1 張照片，且 PDF 頁數須 ≤ `DOC_MAX_PAGES`。
  - DocuMind 回錯誤或逾時 ⇒ 固定句「沒查成」，請使用者重傳或改用文字建立；⛔ 改用我方模型代抽。
  - **謄本四句固定句**（逐字，由程式決定、不經模型；出處 `rag-orchestrator/services/agent/document_extract.py` 的 `DOCUMENT_NOTICE_TEXTS`）：
    - 未啟用：「目前無法自動讀取建物謄本；要建立物件，請直接把縣市、行政區、地址與用途打字給我。」
    - 沒查成：「這次謄本沒有讀取成功；請重新上傳一次，或直接把物件資料打字給我。」
    - 一次一份：「請一次只上傳一份建物謄本（一個 PDF 或一張照片），我再幫您讀取。」
    - 不是謄本：「這份文件讀不出建物謄本的內容；請確認上傳的是建物謄本，或直接把物件資料打字給我。」
- ⛔ 所有權人姓名、統編、所有權人住址不會出現在確認卡、送給 jgb2 的 body、log、trace。
- DocuMind 未啟用（`DOCUMIND_BASE_URL` 未設或設定不合 §2）時，謄本回合不放行建立物件，使用者看到「未啟用」固定句。
- 掃描件（照片）不取縣市、行政區、樓層：一律由使用者補。縣市寫入 jgb2 時，我方目前以 JGB 既有資料寫法「台」送出；「台」「臺」是否視同待 JGB 回答（API 規格 §3 #19）。

### 7.4 收據／發票（(11-2)）

- **只取金額**：收據上的金額映射為帳單 `total`，條件是幣別為台幣（或未標幣別）、金額為**整數**（台幣元）、且該欄未被標為「不確定」；否則不填、由系統追問。
- **收據日期**只作確認卡外的**提示**（「收據日期：…」），不進確認卡的送出欄位、不進 body。
- **帳單項目（`title`）與到期日（`date_expire`，繳費期限）必須由使用者給**（使用者原話），到期日不得早於今天；合約由使用者以編號或名稱指稱（見 §9）。文件上的開立人、付款人、品名一律不採用。

## 8. 回應與前端對應

`tools/call` 結果的文字內容是 JSON：

```jsonc
{ "answer": "<給使用者看的文字>", "kind": "answer|ask|recommend|handoff", "handoff": null,
  "quick_replies": [ {"label": "…", "value": "…"} ], "trace_id": "<hex>", "session_expired": false,
  "outcome": { "state": "answered|clarifying|confirm_pending|confirmed|cancelled|failed|handoff|out_of_scope",
               "expects": "text|choice|button|image|file|none",
               "action": "<寫入動作名>|null", "ref": {"type": "…", "id": "…"} } }
```

| 回應欄位 | 前端怎麼畫 |
|---|---|
| `answer` | 直接顯示成一則助理訊息。**⛔ 不解析 `answer` 字串**來決定畫面。 |
| `quick_replies` | 有值就渲染成按鈕。使用者點了，把該項的 `value` **原字串**當下一回合的 `message` 送回，⛔ 不要改寫。 |
| `outcome.state` | 畫面狀態只看這個（值域見下表）。 |
| `outcome.expects` | 這一輪要開的輸入方式（值域見下表）。 |
| `kind=handoff` | `answer` 是固定的轉專人句，掛「找真人」動作。 |
| `session_expired` | 為 `true` 表示同一 `session_id` 超過 30 分鐘再進入，舊的待確認卡已作廢；前端可提示「對話已重新開始」。 |
| `trace_id` | 回報問題時附上，對得回我方紀錄。 |

**`outcome.state`**

| 值 | 前端 |
|---|---|
| `answered` | 一般回答（含清單點選直答、查無此筆） |
| `clarifying` | 等使用者補資料（看 `expects`）；缺必填欄位時由程式追問（見 §10） |
| `confirm_pending` | 顯示確認卡（§9） |
| `confirmed` | 任務完成；`ref` 是單號／編號 |
| `cancelled` | 已取消，jgb2 端沒有任何寫入 |
| `failed` | 顯示 `answer` 的固定句 |
| `handoff` | 顯示「找真人」 |
| `out_of_scope` | 回清單 |

**`outcome.expects`**

| 值 | 前端開什麼輸入 |
|---|---|
| `text` | 輸入框 |
| `choice` | 選項鍵 |
| `button` | 確認卡三顆鍵 |
| `image` | 傳照片鍵（讓使用者拍照／選相簿，⛔ 不要只開輸入框） |
| `file` | 傳檔鍵 |
| `none` | 不等輸入 |

**`outcome.action`**（僅寫入類回合有值）：`repair_create`（建立修繕單）、`bill_due_extend`（延長帳單到期日）、`estate_create`（建立物件）、`contract_create`（建立合約）、`manual_bill_create`（建立手動帳單）。

**`outcome.ref.type`**（`state=confirmed` 時 `ref` 有值）：`repair`、`bill`、`contract`、`estate`。五個寫入動作確認成功後 `ref` 都非 null：建立物件／合約／手動帳單的 `ref` 分別為 `estate`／`contract`／`bill` 與對應編號。物件的回覆文字與對話記憶**只印物件名稱、不印 id**（業主裁示）；`outcome.ref.id` 照常回傳給程式。

**前端不得對未知值報錯**：`state`、`expects`、`action`、`ref.type` 日後可能擴充，一律依 `outcome.state` 與 `answer` 呈現。

### 清單點選

使用者點清單中的某一筆時，把 `select:<type>:<id>` 當 `message` 送入（目前 `type ∈ bill｜contract｜repair`，`id` 為 JGB 編號，`^[A-Za-z0-9_-]{1,32}$`）。查不到或不在範圍一律回「查無此筆」。

### 寫入時的候選選擇

寫入時使用者給的名稱對到多筆（例：同名合約兩份），本系統回 `kind=ask`、`outcome.state=clarifying`、`outcome.expects=choice`，`answer` 列出候選，`quick_replies` 每筆一顆，`value` 為 `pick:<contract|estate|bill>:<id>`（`id` 同上形狀）。前端照一般 `quick_replies` 處理：點了就把 `value` 原字串當下一回合 `message` 送回，⛔ 改寫。選項過期或不屬這份清單時，本系統回固定句「這個選項已經失效了。要處理哪一筆，請重新告訴我。」（DSP-103）。使用者也可以直接打字講編號或描述，不必點按鈕。

- **一次最多 10 顆**：候選最多記 20 筆，畫面與 `quick_replies` 列前 10 筆（超過時 `answer` 末句請使用者講編號）；前端 ⛔ 自行截斷或補按鈕。
- **延長帳單到期日先選物件**：物件名稱同名多筆時，先列物件候選（`pick:estate:<id>`，每筆附縣市區、樓層、租金、狀態、有無有效合約），選定物件後才列（或直接出）該物件的帳單候選（`pick:bill:<id>`，每筆附標題、狀態、計費期間、到期日、金額）。
- **客人講了金額或計費期間**：本系統用它縮小帳單範圍；都對不上時，`answer` 第一句說明對不上，並列該物件該期的帳單供選。使用者按了與先前講法不符的那張，確認卡照按的那張出，卡上多一行「提醒：您先前說 N 元，這張是 M 元」。
- **確認卡的可分辨欄位**：延期卡另列物件名稱與編號、帳單標題、帳單金額、計費期間；修繕卡與建立合約卡另列物件位置（縣市區＋樓層）；建立手動帳單卡另列合約期間。這些值一律由本系統從 JGB 查得的資料印出；JGB 的名稱或標題含換行、不可見字元或過長時印「—」。
- 候選清單只帶辨識所需欄位，⛔ 含承租人聯絡資料、地址、經緯度。

## 9. 確認卡與寫入

所有寫入（修繕單、物件、合約、手動帳單）一律先出確認卡，使用者按了才寫入；模型無法跳過確認（使用者說「不用確認直接建」也一樣出卡）。

- 確認卡回合：`kind=ask`、`outcome.state=confirm_pending`、`outcome.expects=button`，`answer` 是卡片文字——**逐欄列出將送出的每一欄**（含中文標籤），使用者沒給的選填欄位**不出現、不補值**；`quick_replies` 為三顆鍵：

| `value` 形狀 | 意義 | 前端動作 |
|---|---|---|
| `confirm_submit:<16 hex>` | ✅ 確認送出 | 按下後，把該 `value` 原字串當下一回合 `message` 送回 |
| `confirm_edit:<16 hex>` | ✏️ 我要修改 | 同上 |
| `confirm_cancel:<16 hex>` | ❌ 取消 | 同上；取消後 jgb2 端不會有任何寫入 |

- **重送冪等**：重按同一顆 `confirm_submit` 不會重複建立（回同一份結果，我方以確認鍵為冪等鍵）。過期、換人（§5 第 7 點）或不認得的確認鍵，得到固定句「這筆確認已失效，請重新確認一次。」
- 前端 ⛔ 不得自行組 `confirm_*` 字串，只能送回我們給的 `value`。
- 逾時處理見 §6 F2-6。
- **各動作的欄位**（封閉表；多給的鍵、任何身分或歸屬鍵一律不收）：
  - 建立修繕單：必填物件（`estate_name`，名稱或編號）與問題描述（`description`），缺則由程式追問（§10）；分類（`category_name`，須在修繕分類樹內，父節點或葉節點皆可）、急迫程度（`emergency_status`）選填。急迫程度我方以 jgb2 網頁行為為準送出：**2＝緊急、1＝非緊急，缺值＝非緊急**；jgb2 對外 API 的 `getMapping` 與此一致（jgb2 #13295897160）。
  - 建立物件：必填 `title`、`city`、`district`、`address`、`use_for`；選填 `space_type`、`building`、`room_count`、`size`、`rent`、`floor`。
  - 建立合約：物件（以名稱或編號指稱）、`date_start`、`date_end`、`rent`，`to_user_email`／`to_user_phone` 至少一個；選填 `deposit_amount`、`title`。
  - 建立手動帳單：合約（以編號或名稱指稱）、`title`、`total`、`date_expire`（不得早於今天）；選填 `sub_title`。
  - 金額只收整數元；`date_expire` 之外的合約日期不設「不得早於今天」（登錄既有租約時起始日早於今天是常態），只驗格式與 `date_end` 晚於 `date_start`。
  - 這些動作只對業者身分開放。
- **卡上編號＝寫入編號**：建立合約的物件、建立手動帳單的合約，在**出卡時**就以帶 viewer 的查詢解析成唯一一筆，卡上印出名稱與編號；使用者確認後寫入的就是卡上那一筆，寫入前再以帶 viewer 的單筆讀確認該筆仍屬本團隊且看得到，否則回「查不到」固定句，⛔ 不會依名稱改寫到別筆。名稱對到多筆或零筆 ⇒ 不出卡（零筆走「查不到」固定句；多筆請使用者指定）。
- **對話釘住物件時**：已在某物件的範圍內操作時（清單點選 `select:bill｜contract｜repair:<id>` 後），對**別戶**的寫入（含建立合約、手動帳單、物件、修繕單）一律以固定句擋下（`SCOPE_EXIT_TEXT`）、不出卡、不寫入。實測（2026-10-15）：釘住 `select:bill:<id>` 後對別戶的四種寫入 4／4 被擋，對該物件本身的三種寫入皆出卡。
- **本系統還沒接上的寫入動作**：接真 JGB（`USE_MOCK_JGB_API=false`）時，`estate_create`、`contract_create`、`manual_bill_create`、`bill_due_extend` **不出確認卡、不發請求**，程式直接回固定句（§10）；文件回合回的是文件回合專用固定句。JGB staging 已開 `POST /api/external/v1/estates`、`/contracts`、`/bills/manual` 與 `PATCH /api/external/v1/bills/{id}`（只改 `date_expire`），本系統的呼叫還沒改接（DSP-132）。

## 10. 缺欄追問與固定句

- **缺必填欄位**：不出卡，由**程式**追問（⛔ 模型自寫追問會被 Verifier 降級轉人）：`kind=ask`、`outcome.state=clarifying`、`outcome.expects=text`。追問句形如「要完成這筆建立，還需要：地址、用途。…」，缺欄標籤出自固定詞彙（⛔ 帶使用者值）。使用者補一句即出卡。修繕單缺物件或問題描述也走這條（`REPAIR_MISSING_LABELS`：「物件」「問題描述」），「能幫我新增一張修繕單嗎」「幫我報修」這類開頭第一句即被程式追問、不出卡。
- **追問後的回答接回原流程**：上一回合追問的是物件／社區／地址時，使用者下一句若是 7～30 字、不含句讀的一串名稱，程式拿去與該成員可見的物件比對（`_PRE_LOOKUP_NAME_ASK_TARGETS`）；比對不到不注入，照一般對話處理。
- **查不到**：查詢帶明確編號或名稱時，jgb2 回 403、404，或成功但結果為空，一律同一句固定句「系統裡查不到這個編號或名稱。」；無權（他團隊、該成員看不到）與不存在**不區分**，避免探測資料是否存在。行為：程式以固定句回覆（⛔ 不靠模型自行措辭）。**請 JGB 越權與不存在統一回 404「不存在或無權存取」並附 `error.code`**（API 規格 §0-1）；我方對 403 與 404 同樣當作「查不到」。
- **沒查成**（上游其他失敗、逾時）：不是「查無」，**不說「查不到」**；使用者會看到「這筆操作目前無法執行」（寫入）或轉人。
- **本系統還沒接上的功能**：延期繳費與建立物件／合約／手動帳單，接真 JGB 時我方**不發請求**，程式以固定句結束回合（`kind=answer`、`outcome.state=answered`、`outcome.expects=text`，不經模型）。這兩句現在寫「JGB 系統尚未開放」，與 DSP-132 不符，改接時一起拿掉：
  - 延期繳費：「這個動作目前還不支援：JGB 系統尚未開放延期繳費（調整帳單到期日），開放後就能直接辦理。」（`confirm.BILL_DUE_EXTEND_NOT_SUPPORTED_TEXT`）
  - 建立物件／合約／手動帳單：「這個動作目前還不支援：JGB 系統尚未開放建立物件、合約或手動帳單，開放後就能直接建立。」（`confirm.WRITE_NOT_SUPPORTED_TEXT`）
  我方改呼叫 JGB 端點後，這兩句不再出現。
- 統計三項（未收帳單、執行中修繕、N 個月內到期合約）打 JGB 既有列表端點（`jgb2_stats`，DSP-126）；「共 0 筆」是事實，直接回 0 筆；上游錯誤時走固定句，⛔ 不印 0。
- 明細多筆時一律「共 N 筆」＋逐筆列出；超過一頁（修繕清單每頁 ≤20 筆）會問「要不要看下一頁」，使用者要看就繼續問，我方帶 `page` 再查。
- **建立失敗原因目前不回傳**，見 §12。

## 11. 錯誤碼

HTTP 層（在進入工具之前）：

| HTTP | `code` | 意義與建議處理 |
|---|---|---|
| 400 | `IDENTITY_MALFORMED`／`IDENTITY_MISSING_VENDOR_ID`／`IDENTITY_MISSING_SESSION_ID` | header 組錯（含 `user_id` 字面值為 `anonymous`，回 `IDENTITY_MALFORMED`）；是 JGB 端程式問題，不是使用者問題，不要重試。 |
| 400 | `IDENTITY_MISSING_USER_ID` | 站內幫手金鑰（`AGENT_ASSISTANT_KEY_IDS` 內）的 `X-JGB-Identity` 缺 `user_id`；JGB 端程式問題，不要重試。 |
| 401 | `API_KEY_REQUIRED` | 缺或錯金鑰；檢查 F2-1。 |
| 403 | `ORIGIN_NOT_ALLOWED` | 帶了不在白名單的 `Origin`；代理不應帶 `Origin`（F2-4）。 |
| 403 | `VENDOR_UNKNOWN`／`VENDOR_NOT_IN_KEY_SCOPE` | vendor 不存在，或不在這把金鑰範圍內（vendor 不在金鑰範圍 ⇒ 403）。 |
| 429 | （額度達限） | 全站共用（F2-5），顯示固定句、不自動重試。 |

工具層（`tools/call` 以 MCP `ToolError` 回，訊息只含業務代碼）：

| 代碼 | 意義與建議處理 |
|---|---|
| `INVALID_INPUT` | 輸入不合法（`message`／`upload_ids` 皆空、超長、`upload_ids` 超過上限（`repair` 10、`document` 1）、`upload_id` 過期／已用過／不屬於此對話或用途不符、帶了 `image_urls`／`file_urls`、`agent.upload_ticket` 的 `X-JGB-Identity` 缺 `user_id`、`session_id` 過長、帶了未宣告的鍵…）；不要原樣重試，附件類請使用者重新上傳。 |
| `NO_MATCH` | 查不到**或沒權限**（刻意不區分）；顯示固定句。 |
| `TOOL_TIMEOUT` | 逾時（預設 30 秒）；一般回合本回合不落狀態，可手動重送；**確認回合見 F2-6**。 |
| `RATE_LIMITED` | 每小時上限，全站共用（F2-5）。 |
| `QUOTA_EXCEEDED`／`METERING_UNAVAILABLE` | 額度達限／計量不可用而拒絕服務；通知我方，不要重試。 |
| `AGENT_UNAVAILABLE` | 我方 agent runtime 未接妥（伺服器狀態）；顯示固定句，稍後再試。 |
| `CONFIRMATION_REQUIRED` | 確認碼無法兌現（fail-closed：寫入必須經確認，兌現不了就不寫）；請使用者重新走一次確認，若反覆出現請附 `trace_id` 回報。 |

jgb2 端點（接口 B）的越權一律折疊成「不存在或無權存取」404（API 規格 §0-1；我方對 403、404 同樣當作「查不到」，§10），我們對使用者只顯示固定句，不外洩細節；我方日誌只記方法、端點樣板、例外類別與狀態碼，⛔ 記查詢值與身分值。

## 12. 已知限制

- **建立失敗原因只回固定句**：寫入失敗（例如縣市行政區 jgb2 無法解析、欄位值被 jgb2 拒絕）時，使用者只看到「這筆操作目前無法執行」，我們目前不回傳失敗原因（P3 延後）。確認卡不預檢縣市行政區，真 jgb2 由接口 B #19 解析，所以非預期區域要到按下確認後才失敗。
- **接真 JGB 時，延期繳費（改帳單到期日）與建立物件／合約／手動帳單回固定句**：見 §9、§10。
- **知識題與驗證**：正式機 `AGENT_VERIFIER_MODE=grounding_observe`（§2）；知識題中位約 4 秒（2026-10-15 正式機 20 題：答出 11、p90 約 9 秒）。舊知識庫零列已審時 `kb.search` 不給對話模型（門面照列，`docs/api/mcp-facade.md`）；細目索引在開機逾時後背景重建（正式機約 3～4 分鐘），重建完成前只有目錄。
- **偶發轉人**：可見帳單的查詢偶發 `QUOTE_NOT_COVERING` 轉人；成員看不到的物件建修繕單時，不出卡、不寫入，但回覆為轉人或反問、不一定是 §10 的固定句；照片建單首回合偶發轉人（12 次中 1 次，追問後出卡）。以上皆為 P3，持續量測中。
- **`form_sessions` 無清除排程**：對話狀態表目前沒有定期清除機制；保存期限與清除由後續另案處理（不在本計畫範圍）。
- **記憶功能（項 7「記住一件事」）已撤除**：不做；使用者說「記住…」時沒有任何跨對話記憶。
- **文件回合的模型回答留在對話歷史**：見 §7.2 末段。
- **照片交給 jgb2 的 multipart 本系統還沒改接**：見 §7.1、API 規格 #22；改接前真 jgb2 不附照片。
- **謄本功能的上線前提未解**：正式機目前接 DocuMind 測試機、只收樣本檔（§2）；見 §2 末段（DocuMind 端三件）；DocuMind 認證格式（暫用 `Authorization: Bearer`）待 DocuMind 確認。
- **對話歷史依 `session_id` 保存、不由呼叫端回傳**；30 分鐘後再進入視為過期（`session_expired`）。

## 13. 待確認與待裁

| 項目 | 內容 | 誰回答 |
|---|---|---|
| 工具參數塞身分鍵 | 現況為剝除不採用（§6 F2-3）；是否改為一律拒絕（`INVALID_INPUT`） | 業主 |
| 修繕單照片改接 multipart | API 規格 §4 #22：staging 已開，本系統改接 `POST /api/external/v1/repairs` 的 `broken_photos[]` 後照片才進得了修繕單 | AIChatbot |
| 改帳單到期日改接 | API 規格 §4 #23：staging 已開 `PATCH /api/external/v1/bills/{id}` | AIChatbot |
| 越權統一 404、寫入的成員身分驗證、冪等、歸屬欄位拒絕 | API 規格 §0 | JGB |
| 建立物件／合約／手動帳單的端點 | API 規格 §1、§3；開放後我方改呼叫端（API 規格 §7） | JGB |
| DocuMind 認證格式與上線前提 | §2 末段 | DocuMind 端 |

## 14. JGB 端設定

- 站內幫手功能開關與白名單（哪些團隊／成員看得到入口）是 **JGB 端設定**，不在我方。
- 站內幫手使用一把限定 vendor 的專用金鑰（`api_keys.id=101`，非內部）；金鑰值由我方另行交付，⛔ 不寫在任何文件。
- 接測方式：接口 B 的每個端點上線後，JGB 以 `.kiro/specs/agentic-mcp-orchestration/jgb-acceptance-checklist-20261015.md` 接測（AIChatbot 端驗收項 A1～A14 的真 API 版本）。

## 15. 條文對照表（安全審查／計畫 → 本文件章節）

| 條文 | 內容 | 本文件章節 |
|---|---|---|
| F1 | `session_id` 由 JGB 伺服端 CSPRNG（≥128 bit）產生、綁 `user_id`＋`role_id`、登入登出換團隊即換、⛔ 瀏覽器帶入、≤80 字；我方保證與邊界 | §5（第 1～5 點為 JGB 義務，第 7 點為我方保證，計畫 §3i 第 3 點） |
| F2-1 | 金鑰只在伺服端，另發限定 vendor 的 key | §6 F2-1 |
| F2-2 | 身分只由登入 session 組 | §6 F2-2；§4 |
| F2-3 | 代理只呼叫 `agent.turn`、`agent.upload_ticket`，只轉宣告的參數 | §6 F2-3；§3；§7 |
| F2-4 | 瀏覽器 ⛔ 直連 `/mcp`、不持金鑰；只打上傳端點 | §6 F2-4；§1；§7 |
| F2-5 | 限流共用，需告知 | §6 F2-5；§11 |
| F2-6 | 確認回合逾時 ⛔ 自動重試 | §6 F2-6；§9；§11 |
| F9 | 附件瀏覽器直傳 AIChatbot：上傳票（綁使用者與對話、10 分鐘）、上傳端點預設不檢查 Origin、不帶 credentials、單檔 ≤5 MB 依內容判型、`upload_ids`（一次性、30 分鐘） | §7；§2（`AGENT_UPLOAD_*`） |
| F10 | 照片附進修繕單：我方以 multipart `broken_photos[]` 送檔（重新編碼 JPEG、去 EXIF／GPS、最多 10 張）、雜湊綁定確認卡、JGB ⛔ 回頭抓我方網址 | §7.1；接口 B #22 |
| F11 | 文件值只放封閉表內有型別欄位 | §7.2～§7.4（計畫 §5b F11、DSP-073／076、§3h） |
| DSP-074 | 查詢與統計限於成員可見範圍、每次呼叫帶 viewer | §4（`user_id`）；接口 B #16～#18、#24（計畫 §3c、§3i 第 1 點） |
| DSP-075 | 對話模型 gpt-6-luna、`AGENT_REASONING_EFFORT=none` | §2（計畫 §3e） |
| 部署前置 `UVICORN_WORKERS=1` | MCP session 在行程內 | §2（計畫 §3e 環境發現 1） |
| `AGENT_ASSISTANT_KEY_IDS` | 站內幫手金鑰必帶 `user_id`；缺 ⇒ 400 `IDENTITY_MISSING_USER_ID`；`anonymous` ⇒ 400 `IDENTITY_MALFORMED` | §2；§4；§11（計畫 §3i 第 1 點） |
| `AGENT_TURN_TIMEOUT_S` | 正式機 90 秒；文件回合預算 `min(45, 逾時/2)` | §2；§3 |
| 查無與無權同一句 | jgb2 回 403、404 或成功但空 ⇒「系統裡查不到這個編號或名稱。」，程式固定句；其他失敗不說查不到 | §10（計畫 §3i 第 2 點） |
| 還沒接上的寫入的固定句 | 延期繳費、建立物件／合約／手動帳單：接真 JGB 時不發請求、程式固定句 | §10；§9 |
| 缺欄程式追問 | `outcome=clarifying`、固定詞彙 | §10（計畫 §3f，S2 修正輪） |
| 確認卡封閉欄位、卡上編號＝寫入編號 | 各動作欄位表、出卡時綁定編號 | §9（計畫 §3f 第 1、1d 點，§5b F3） |
| `outcome.action`／`ref.type` 值域 | 含 `estate` | §8（計畫 §3i 第 5 點） |
| 謄本由 DocuMind 解析 | 取值規則、四句固定句、掃描件不取縣市行政區樓層、所有權人資料不出現；`enable_llm=false`、https＋Token | §7.3；§2（計畫 §3h 第 4 點） |
| 文件回合放行 | `building_deed`→建立物件、`bill_receipt`→手動帳單；其餘不放行 | §7.2 |
| F1 我方保證 | 同 (api_key, vendor, session_id) 下 (user_id, role_id) 不同 ⇒ 不續用對話與確認卡 | §5 第 7 點 |
| 收據只取金額 | 台幣整數、收據日期只作卡外提示、繳費期限由使用者給 | §7.4（計畫 §3h 第 5 點） |
| 已知限制 | 建立失敗原因、`form_sessions` 清除、記憶撤除、偶發轉人 | §12（計畫 §3f 延後、§5b 待查、§3g） |
