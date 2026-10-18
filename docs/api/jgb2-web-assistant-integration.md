# 接口 A：jgb2 站內幫手 → AIChatbot `/mcp`（`agent.turn`）

> **狀態：現況版（2026-10-16）。** 站內幫手已在正式機上線；JGB 已於 2026-10-15 17:38 起經 `/mcp` 呼叫。計畫：`.kiro/specs/agentic-mcp-orchestration/plan-assistant-11-items-20261014.md`（以下簡稱「計畫」）。
> 讀者：JGB（jgb2 後端）工程。本文件說「jgb2 代理怎麼呼叫我們」；反方向（我們呼叫 jgb2 的端點，以下稱**接口 B**）的現行正本是 `.kiro/specs/agentic-mcp-orchestration/jgb-api-spec-for-jgb-20261015.md`（已對碼 jgb2 master；列號 #16～#24 沿用），總帳 `jgb2-api-requests.md` 只指向該檔。接測清單見 `.kiro/specs/agentic-mcp-orchestration/jgb-acceptance-checklist-20261015.md`。
> 底層契約不重寫，**以 `docs/api/mcp-facade.md` 與 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/line-bot-integration-sheet-20260908.md` 為準**；本文件只寫站內幫手這條線的**取值、義務與對應**。
> 決策依據：DSP-011（權限由 jgb2 API 全權處理、本系統只管額度）、DSP-073（F9 專用上傳網域、F11 文件欄位）、DSP-074（查詢與統計限於該成員在 JGB 畫面上看得到的範圍）、DSP-075（對話模型 gpt-6-luna）、DSP-076（有型別文件值暫存到出卡為止）。

## 1. 分工與範圍

- 入口：JGB 站內幫手後端呼叫本文件的 `/mcp`，網址 `https://chatai.jgbsmart.com/rag-api/mcp`（本系統唯一的對外入口，各呼叫端共用同一網址）。舊 REST 鏈（`/rag-api/v1/message`）已於 2026-09-11 退役（DSP-046）。
- 我們（AIChatbot）：在 `agent.turn` 上完成站內幫手的 10 項對話能力；需要 jgb2 的資料與寫入，一律透過接口 B 的端點取得。接真 JGB 時，JGB 尚未開放的功能（統計三項、建立物件／合約／手動帳單）我方**不發請求**，由程式回固定句（§10）。
- 你們（JGB）：持有金鑰與登入身分、組 header、轉送使用者訊息與檔案、把回應畫成前端。站內幫手入口的功能開關與白名單是 JGB 端設定（§14）。
- ⛔ 瀏覽器不直連 `/mcp`（§6 F2-4）。

## 2. 部署前置（我方服務設定）

這些是 AIChatbot 服務端的環境變數，由我方部署時設定；列在這裡是因為少設任何一項，接測結果會與本文件不符。

| 設定 | 值／規則 | 為什麼 |
|---|---|---|
| `UVICORN_WORKERS` | **`1`** | MCP session 存在行程記憶體；多 worker 時約一半請求會回 404「unknown or expired session ID」（2026-10-15 實測）。`docker-compose.prod.yml` 已註明 `agent.turn` 須 1，預設值 4 不可用 |
| `AGENT_TURN_ENABLED`／`AGENT_STAGE` | `true`／達 `M1` | `agent.turn` 才會註冊（`tools/list` 看得到） |
| `AGENT_WRITE_TOOLS_ENABLED` | `true` | 寫入動作（確認後建立）才可見 |
| `USE_MOCK_JGB_API`／`JGB_API_BASE_URL` | 正式機：**`false`**／`https://www.jgbsmart.com` | `true` 時走我方替身，不會打到 jgb2；`false` 時 `JGB_API_KEY` 必須在，否則啟動直接 raise |
| `AGENT_MODEL` | **`gpt-6-luna`**（DSP-075） | 對話模型。未設時退回 `OPENAI_MODEL`，可能落到較弱模型，驗收結果不可比 |
| `AGENT_REASONING_EFFORT` | **`none`**（DSP-075） | gpt-6-luna 帶工具呼叫時只能 `none` |
| `AGENT_VERIFIER_MODE` | 正式機：**`grounding_observe`**（業主 2026-10-15 裁示；程式預設是 `enforce`） | `grounding_observe`：引用類只記錄、極性與機敏類照擋；上線後同批 5 題知識題實測 `enforce` 答 1／5、`grounding_observe` 答 3／5。健檢因此會在 `premise.red_flags` 記 `verifier_grounding_observe_on_real_api`（`status` 轉 `red`），屬已知。接測結果以正式機現值為準 |
| `AGENT_BUDGET_TOOL_CALLS`／`AGENT_BUDGET_DEADLINE_S` | 正式機：**`3`**／**`20`** | 每回合工具呼叫上限／回合預算（秒）；程式預設 4／20 |
| `AGENT_ASSISTANT_KEY_IDS` | 逗號分隔的整數 `api_key_id`，**站內幫手那把金鑰必須列入，正式機必設**；正式機值 `101`（限定 vendor 4、非內部）（計畫 §3i 第 1 點） | 列入的金鑰，`X-JGB-Identity` 缺 `user_id` 即被拒（400 `IDENTITY_MISSING_USER_ID`，§4、§11）。**未設定或空字串 ⇒ 不對任何金鑰啟用**（其他用戶端的單證行為不變），所以漏設不會報錯、只會讓「缺 user_id 就拒」靜默失效；含非整數 ⇒ 服務啟動失敗並印原因 |
| `AGENT_TURN_TIMEOUT_S` | 程式預設 30 秒；**正式機 `90`**（文件回合預算＝`min(45, 此值 / 2)`＝45 秒） | DocuMind 呼叫的可用時間＝此值扣掉已耗時再扣 20 秒模型迴圈保留；不足 1 秒即不送、回「沒查成」。JGB 代理的逾時須大於此值（§3） |
| `IMAGE_URL_ALLOWLIST` | 正式機**未設**（採 compose 預設 `relay.jgbsmart.com`）；JGB 回覆專用上傳網域後由我方加入（**待 JGB 回覆網域**）；有設值是**取代**預設、不是附加；設成空字串＝全擋 | 抓圖白名單。**白名單內除 `relay.jgbsmart.com` 外，每個 host 都必帶 `exp`**（§7；`services/agent/image_fetch.py`） |
| `DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN`／`DOCUMIND_ALLOW_INSECURE_TEST_HOST`／`DOCUMIND_INSECURE_TEST_HOST` | 正式機**未設 ⇒ 謄本功能關閉**。謄本解析由 DocuMind 負責（§7.3）。`DOCUMIND_BASE_URL` 必須 https 且必帶 `DOCUMIND_TOKEN`（暫以 `Authorization: Bearer` 送出，**待 DocuMind 確認認證格式**）；任何其他組合一律視同未設 ⇒ 文件回合照舊，不放行建立物件，使用者看到「未啟用」固定句（§7.3）。明文 http 只在 `DOCUMIND_ALLOW_INSECURE_TEST_HOST=1` **且** base URL 的主機與連接埠逐字等於 `DOCUMIND_INSECURE_TEST_HOST`（`host:port`）時允許，**只限測試**，正式機不設；測試主機位址不寫進 repo。呼叫一律 `enable_llm=false` | 目前線上 DocuMind 為明文 http、無認證，**不得用於正式** |
| 限流 | 每小時 **1200 次**，計數鍵 `(api_key_id, vendor_id)`（`LIMITS.turns_per_hour`；`AGENT_TURN_CAP` 已不再被讀取） | 見 §6 F2-5 |

**謄本功能的正式上線前提（DocuMind 端，非本系統可解）**：三件——① DocuMind 端的 S3 物件須關閉 public-read；② 複核佇列須有認證（現況無認證）；③ few-shot 留存須處理（謄本含所有權人資料）。三項未解之前，謄本功能只限測試期、合成素材。

## 3. 呼叫方式

```
POST {AICHATBOT_BASE}/mcp            MCP streamable HTTP（方法與 body 由 MCP 協定定）
  X-API-Key: <限定 vendor 的金鑰>      必帶；見 §6 F2-1
  X-JGB-Identity: <JSON>              必帶；見 §4
```

- **呼叫順序**：MCP streamable HTTP 是有 session 的——先 `initialize`（帶 `Accept: application/json, text/event-stream`），從回應標頭取 `Mcp-Session-Id`，之後每個請求（`tools/list`、`tools/call`）都帶 `Mcp-Session-Id`；沒先 `initialize` 直接打 `tools/list` 回 400「Missing session ID」。MCP session 存在我方行程記憶體，我方重啟後舊 session 作廢（回 404「unknown or expired session ID」），須重新 `initialize`。⛔ 與對話的 `session_id`（§5，放在 `X-JGB-Identity`）是兩回事。
- 以 MCP `tools/call` 呼叫工具 `agent.turn`；連線成功判準：`initialize` 後 `tools/list` 回 200 且看得到 `agent.turn`（回 403 `VENDOR_*` 表示金鑰與 vendor 沒對上）。
- 輸入參數：

```jsonc
{ "message": "<0–2000 字，可空字串>",
  "image_urls": ["https://<專用上傳網域>/…簽章網址", "…"],      // 選填，≤10
  "file_urls": ["https://<專用上傳網域>/….pdf?…"],               // 選填，≤1；只在 attachment_purpose=document 時可帶
  "attachment_purpose": "repair|document",                      // 選填；缺值＝repair
  "context": "<≤500 字>" }                                      // 選填；本回合背景資訊，⛔ 當作使用者說的話
```

  `message`、`image_urls`、`file_urls` 不得三者皆空（否則 `INVALID_INPUT`）。`attachment_purpose` 預設 `repair`＝報修照片；上傳**謄本**或**收據／發票**時必須帶 `document`。`repair` 用途帶 `file_urls` ⇒ `INVALID_INPUT`。
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
7. **我方保證**（計畫 §3i 第 3 點）：同一 (api_key, vendor, session_id) 下，(user_id, role_id) 與建立時不同 ⇒ 不續用對話與確認卡；⛔ 防呼叫端冒用身分（DSP-011 信任在上游），依賴 F2「代理只呼叫 agent.turn」。
   細則：不續用＝視為新對話，舊的對話內容、待確認卡、已釋出的上下文一律不帶入。比對規則：位元組完全相等、不做正規化；匿名（無 `user_id`）續匿名可續，匿名與具名互換一律重置；待確認卡記錄建立者的 `(user_id, role_id)`，按鍵時先比對，不符與「不認得的確認鍵」同一處理，不兌現。實測：換人後按前人的確認鍵，得到「這筆確認已失效，請重新確認一次。」，jgb2 沒有寫入。
   **保證的邊界**：這道比對只防「同一 session_id 被不同的 `(user_id, role_id)` 用到」，不防呼叫端冒用身分——`user_id`／`role_id` 的真偽信任在上游，本系統不驗；整體安全依賴 §6 F2。第 1～4 點仍是 JGB 端的義務，不因我方比對而放寬。

## 6. 金鑰與代理義務（F2）

| 編號 | 義務 |
|---|---|
| F2-1 | **金鑰只在 JGB 伺服端。** 我們另發一把**限定 vendor** 的金鑰給站內幫手（`vendor_ids` 只含展示團隊的 vendor、非 `is_internal`），不與其他呼叫端共用。金鑰不得出現在前端程式、頁面、瀏覽器可見的回應、log、指令列參數。 |
| F2-2 | **身分只由登入 session 組。** `vendor_id`／`role_id`／`user_id`／`target_user`／`mode` 一律由伺服端依登入 session 決定，⛔ 不採信任何瀏覽器送來的身分值。 |
| F2-3 | **代理只呼叫 `agent.turn`，且只轉 §3 列出的參數**（`message`、`image_urls`、`file_urls`、`attachment_purpose`、選填 `context`）。不呼叫 `/mcp` 的其他工具（`jgb2.query.*`、`jgb2.action.*`、`kb.*`…），不加其他參數。身分鍵（`vendor_id`、`role_id`、`user_id`、`target_user`、`mode`、`viewer_user_id`）出現在工具參數時，我方**剝除、不採用**（`ToolRegistry.call`，不回錯誤、記 trace）；其他未宣告鍵 ⇒ `INVALID_INPUT`。身分鍵改為一律拒絕：**待業主裁**。 |
| F2-4 | **瀏覽器 ⛔ 直連 `/mcp`。** 對話一律經 JGB 代理轉送。我們不為瀏覽器放行 Origin（帶 `Origin` 且不在 `MCP_ALLOWED_ORIGINS` 白名單回 403），也不會為了前端方便放寬。 |
| F2-5 | **限流是全站共用，需向使用者告知。** 每小時上限 1200 次，計數鍵是 `(api_key_id, vendor_id)`，**不含** `session_id`／`user_id`：同一業者所有成員共用同一桶，換 session 不會重置。計數器在行程記憶體，所以部署須 `UVICORN_WORKERS=1`（§2）。超過回 `RATE_LIMITED`；額度（`vendor_quotas`）達限回 429／`QUOTA_EXCEEDED`。前端遇到時請顯示「目前使用人數較多，請稍後再試」之類的固定句，⛔ 不要自動重試迴圈。 |
| F2-6 | **確認回合逾時，⛔ 自動重試。** 使用者按下確認鍵（`confirm_submit:…`）那一回合若逾時（`TOOL_TIMEOUT`）或連線中斷，結果是**未知**——寫入可能已發生。代理 ⛔ 不得自動重送；請顯示「處理逾時，請先到清單確認是否已建立，再決定要不要重送」，由使用者決定。一般（非確認）回合逾時，本回合狀態不會被存下，可由使用者手動重送。同一確認鍵重送回同一份結果、不重複建立，已在我方替身驗證；對真 jgb2 端點的冪等（接口 B 的 `idempotency_key`）要等接測才算數，在那之前請當作「可能重複建立」處理。 |

## 7. 圖片與文件上傳（F9，DSP-073）

站內幫手的檔案經 `image_urls`（照片）與 `file_urls`（PDF）傳入。流程與條件：

1. 瀏覽器把檔案傳到 **JGB 自己的上傳端點**（不是我們的）。JGB 驗型別、大小，存放到**專用上傳網域**。
2. **網址由 JGB 伺服端產生**，⛔ 不使用瀏覽器提供的網址。
3. 放進 `image_urls`／`file_urls` 的網址必須同時滿足：
   - **專用上傳網域**：專供使用者上傳檔案，⛔ 不得是 `www` 或 API 主機，也不得與憑 IP 信任的內部主機共用。網域由 JGB 指定（**待 JGB 回覆**），我們把它加進 `IMAGE_URL_ALLOWLIST`（我方設定，部署時才改）；
   - **簽章＋短期到期，`exp` 必帶**：網址帶簽章與 `exp`（到期時間戳）。白名單內除 `relay.jgbsmart.com`（程式寫死的豁免，與本線無關）外每個主機都必帶 `exp`；`exp` 必須是**單一整數**（Unix 秒）、未過期、距現在 ≤ 900 秒（15 分鐘）；缺、空值、出現多個，或超過 900 秒，整個檔案被擋。我們的預檢只判 `exp`，不驗簽，簽章由 JGB 端自驗；
   - **https、不轉址**：我們抓檔時 `follow_redirects=false`，遇到轉址即失敗；
   - **≤ 5 MB**（5,000,000 bytes），超過我們中止連線並整份丟棄；
   - **網址由伺服端產生**（見第 2 點）。
4. 每回合最多 10 張照片、最多 1 份 PDF；同一使用者 3 秒內的檔案與文字請合成一次 `agent.turn`，不要拆回合。
5. 照片型別 jpeg／png／webp；PDF 最多辨識前 5 頁（`DOC_MAX_PAGES`）。

### 7.1 照片附進修繕單（(6-2)）

- 回合帶 `attachment_purpose=repair`（預設）與 `image_urls`：我們辨識損壞物品與分類，出確認卡；使用者確認後建立修繕單，照片附進該張修繕單。
- 送給 jgb2 的只有每張照片的**中繼資料**，放在 `broken_photos`：`[{filename, content_type, size, sha256}]`。`filename` 由我方程式產生，形如 `photo-N.ext`（⛔ 使用者檔名）；`content_type` 依檔案內容判定，只會是 `image/jpeg`、`image/png`、`image/webp`；`size` 與 `sha256` 都取**原檔位元組**（`sha256` 為 64 位小寫 hex）。確認卡顯示「附照片：N 張」，N 納入確認卡雜湊。
- 一張修繕單最多附 5 張；超過 5 張時**全部不附**，並在確認卡上說明。
- **現況與已知落差**：有照片時，我方程式把上述物件陣列放進 `POST /api/external/v1/repairs` 的 `broken_photos`；jgb2 既有端點的 `broken_photos` 是**網址字串陣列**（每筆 `url` 規則、最多 10），形狀不符會回 400（API 規格 §4 #22）。「接真 JGB 時暫不送 `broken_photos`」我方**尚未實作**；JGB 尚未接上照片網域、正式機 `IMAGE_URL_ALLOWLIST` 未設，所以目前不會有照片進來，文字報修不受影響。
- **照片位元組怎麼交給 jgb2：待 JGB 依 API 規格 §4 #22 回覆。** 我們建議 JGB 選 (b)（照片本來就在 JGB 的上傳網域，以 JGB 自己的上傳識別碼引用），因為這樣我們不必轉送位元組、JGB 也不必抓我們的網址。⛔ JGB 不得回頭抓我方提供的網址。選定前，我方只送中繼資料，jgb2 端看不到影像內容。
- 缺必填欄位導致先追問再出卡時，照片仍會附進最終那張卡（只有「出卡」才消耗該回合的照片）。

### 7.2 文件：一次一份

- 上傳**謄本、收據、發票**時，回合須帶 `attachment_purpose=document`；檔案可走 `file_urls`（PDF）或 `image_urls`（照片），**一次一份文件**。
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
  - 建立修繕單：必填物件（`estate_name`，名稱或編號）與問題描述（`description`），缺則由程式追問（§10）；分類（`category_name`，須在修繕分類樹內，父節點或葉節點皆可）、急迫程度（`emergency_status`）選填。急迫程度我方以 jgb2 網頁行為為準送出：**2＝緊急、1＝非緊急，缺值＝非緊急**；jgb2 對外 API 的 `getMapping` 標反，待 JGB 修（API 規格 §5）。
  - 建立物件：必填 `title`、`city`、`district`、`address`、`use_for`；選填 `space_type`、`building`、`room_count`、`size`、`rent`、`floor`。
  - 建立合約：物件（以名稱或編號指稱）、`date_start`、`date_end`、`rent`，`to_user_email`／`to_user_phone` 至少一個；選填 `deposit_amount`、`title`。
  - 建立手動帳單：合約（以編號或名稱指稱）、`title`、`total`、`date_expire`（不得早於今天）；選填 `sub_title`。
  - 金額只收整數元；`date_expire` 之外的合約日期不設「不得早於今天」（登錄既有租約時起始日早於今天是常態），只驗格式與 `date_end` 晚於 `date_start`。
  - 這些動作只對業者身分開放。
- **卡上編號＝寫入編號**：建立合約的物件、建立手動帳單的合約，在**出卡時**就以帶 viewer 的查詢解析成唯一一筆，卡上印出名稱與編號；使用者確認後寫入的就是卡上那一筆，寫入前再以帶 viewer 的單筆讀確認該筆仍屬本團隊且看得到，否則回「查不到」固定句，⛔ 不會依名稱改寫到別筆。名稱對到多筆或零筆 ⇒ 不出卡（零筆走「查不到」固定句；多筆請使用者指定）。
- **對話釘住物件時**：已在某物件的範圍內操作時（清單點選 `select:bill｜contract｜repair:<id>` 後），對**別戶**的寫入（含建立合約、手動帳單、物件、修繕單）一律以固定句擋下（`SCOPE_EXIT_TEXT`）、不出卡、不寫入。實測（2026-10-15）：釘住 `select:bill:<id>` 後對別戶的四種寫入 4／4 被擋，對該物件本身的三種寫入皆出卡。
- **JGB 尚未開放的寫入動作**：接真 JGB（`USE_MOCK_JGB_API=false`）時，`estate_create`、`contract_create`、`manual_bill_create` **不出確認卡**，程式直接回固定句（§10）。`bill_due_extend`（改帳單到期日）目前仍呼叫 `PATCH /agent/v1/bills/{id}`，該路由在 jgb2 master 與 preview 查無（API 規格 §4 #23），正式路徑待 JGB 回覆。

## 10. 缺欄追問與固定句

- **缺必填欄位**：不出卡，由**程式**追問（⛔ 模型自寫追問會被 Verifier 降級轉人）：`kind=ask`、`outcome.state=clarifying`、`outcome.expects=text`。追問句形如「要完成這筆建立，還需要：地址、用途。…」，缺欄標籤出自固定詞彙（⛔ 帶使用者值）。使用者補一句即出卡。修繕單缺物件或問題描述也走這條（`REPAIR_MISSING_LABELS`：「物件」「問題描述」），「能幫我新增一張修繕單嗎」「幫我報修」這類開頭第一句即被程式追問、不出卡。
- **追問後的回答接回原流程**：上一回合追問的是物件／社區／地址時，使用者下一句若是 7～30 字、不含句讀的一串名稱，程式拿去與該成員可見的物件比對（`_PRE_LOOKUP_NAME_ASK_TARGETS`）；比對不到不注入，照一般對話處理。
- **查不到**：查詢帶明確編號或名稱時，jgb2 回 403、404，或成功但結果為空，一律同一句固定句「系統裡查不到這個編號或名稱。」；無權（他團隊、該成員看不到）與不存在**不區分**，避免探測資料是否存在。行為：程式以固定句回覆（⛔ 不靠模型自行措辭）。**請 JGB 越權與不存在統一回 404「不存在或無權存取」並附 `error.code`**（API 規格 §0-1）；我方對 403 與 404 同樣當作「查不到」。
- **沒查成**（上游其他失敗、逾時）：不是「查無」，**不說「查不到」**；使用者會看到「這筆操作目前無法執行」（寫入）或轉人。
- **JGB 尚未開放的功能**：統計三項（未收帳單、執行中修繕、N 個月內到期合約）與建立物件／合約／手動帳單，接真 JGB 時我方**不發請求**，程式以固定句結束回合（`kind=answer`、`outcome.state=answered`、`outcome.expects=text`，不經模型）：
  - 統計：「這項統計目前還不支援：JGB 系統尚未開放這個查詢，開放後就能直接查。」（`jgb2_stats.NOT_SUPPORTED_TEXT`）
  - 建立物件／合約／手動帳單：「這個動作目前還不支援：JGB 系統尚未開放建立物件、合約或手動帳單，開放後就能直接建立。」（`confirm.WRITE_NOT_SUPPORTED_TEXT`）
  JGB 依 API 規格開放對應端點、我方改呼叫後，這兩句不再出現。
- 統計類（JGB 開放後）的「共 0 筆」是事實，直接回 0 筆；上游錯誤時走固定句，⛔ 不印 0。
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
| `INVALID_INPUT` | 輸入不合法（`message`／`image_urls`／`file_urls` 皆空、超長、圖片超過 10 張、文件超過 1 份、`repair` 用途帶 `file_urls`、`session_id` 過長、帶了未宣告的鍵…）；不要原樣重試。 |
| `NO_MATCH` | 查不到**或沒權限**（刻意不區分）；顯示固定句。 |
| `TOOL_TIMEOUT` | 逾時（預設 30 秒）；一般回合本回合不落狀態，可手動重送；**確認回合見 F2-6**。 |
| `RATE_LIMITED` | 每小時上限，全站共用（F2-5）。 |
| `QUOTA_EXCEEDED`／`METERING_UNAVAILABLE` | 額度達限／計量不可用而拒絕服務；通知我方，不要重試。 |
| `AGENT_UNAVAILABLE` | 我方 agent runtime 未接妥（伺服器狀態）；顯示固定句，稍後再試。 |
| `CONFIRMATION_REQUIRED` | 確認碼無法兌現（fail-closed：寫入必須經確認，兌現不了就不寫）；請使用者重新走一次確認，若反覆出現請附 `trace_id` 回報。 |

jgb2 端點（接口 B）的越權一律折疊成「不存在或無權存取」404（API 規格 §0-1；我方對 403、404 同樣當作「查不到」，§10），我們對使用者只顯示固定句，不外洩細節；我方日誌只記方法、端點樣板、例外類別與狀態碼，⛔ 記查詢值與身分值。

## 12. 已知限制

- **建立失敗原因只回固定句**：寫入失敗（例如縣市行政區 jgb2 無法解析、欄位值被 jgb2 拒絕）時，使用者只看到「這筆操作目前無法執行」，我們目前不回傳失敗原因（P3 延後）。確認卡不預檢縣市行政區，真 jgb2 由接口 B #19 解析，所以非預期區域要到按下確認後才失敗。
- **接真 JGB 時，統計三項與建立物件／合約／手動帳單回固定句、改帳單到期日無可用路徑**：見 §9、§10。
- **知識題與驗證**：正式機 `AGENT_VERIFIER_MODE=grounding_observe`（§2）；知識題中位約 4 秒（2026-10-15 正式機 20 題：答出 11、p90 約 9 秒）。舊知識庫零列已審時 `kb.search` 不給對話模型（門面照列，`docs/api/mcp-facade.md`）；細目索引在開機逾時後背景重建（正式機約 3～4 分鐘），重建完成前只有目錄。
- **偶發轉人**：可見帳單的查詢偶發 `QUOTE_NOT_COVERING` 轉人；成員看不到的物件建修繕單時，不出卡、不寫入，但回覆為轉人或反問、不一定是 §10 的固定句；照片建單首回合偶發轉人（12 次中 1 次，追問後出卡）。以上皆為 P3，持續量測中。
- **`form_sessions` 無清除排程**：對話狀態表目前沒有定期清除機制；保存期限與清除由後續另案處理（不在本計畫範圍）。
- **記憶功能（項 7「記住一件事」）已撤除**：不做；使用者說「記住…」時沒有任何跨對話記憶。
- **文件回合的模型回答留在對話歷史**：見 §7.2 末段。
- **照片位元組尚未交給 jgb2，且送出形狀與既有端點不符**：見 §7.1，待 #22（建議 (b)）。
- **謄本功能的上線前提未解**：正式機 DocuMind 未設、謄本功能關閉；見 §2 末段（DocuMind 端三件）；DocuMind 認證格式（暫用 `Authorization: Bearer`）待 DocuMind 確認。
- **對話歷史依 `session_id` 保存、不由呼叫端回傳**；30 分鐘後再進入視為過期（`session_expired`）。

## 13. 待確認與待裁

| 項目 | 內容 | 誰回答 |
|---|---|---|
| 工具參數塞身分鍵 | 現況為剝除不採用（§6 F2-3）；是否改為一律拒絕（`INVALID_INPUT`） | 業主 |
| 照片交付方式與上傳網域 | API 規格 §4 #22：(a) multipart 或 (b) 預簽上傳＋識別碼；專用上傳網域名稱（我方加入 `IMAGE_URL_ALLOWLIST`）；定案前照片進不了修繕單 | JGB |
| 改帳單到期日的正式路徑 | API 規格 §4 #23 | JGB |
| 越權統一 404、寫入的成員身分驗證、冪等、歸屬欄位拒絕 | API 規格 §0 | JGB |
| 統計三項、建立物件／合約／手動帳單的端點 | API 規格 §1、§3；開放後我方改呼叫端（API 規格 §7） | JGB |
| `emergency_status` 對外 mapping | API 規格 §5：以網頁（2＝緊急）為準，修 `getMapping` | JGB |
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
| F2-3 | 代理只呼叫 `agent.turn`，只轉宣告的參數 | §6 F2-3；§3 |
| F2-4 | 瀏覽器 ⛔ 直連 `/mcp` | §6 F2-4；§1 |
| F2-5 | 限流共用，需告知 | §6 F2-5；§11 |
| F2-6 | 確認回合逾時 ⛔ 自動重試 | §6 F2-6；§9；§11 |
| F9 | 專用上傳網域、簽章＋短期 `exp`（單一整數、未過期、≤900 秒；白名單內除 `relay.jgbsmart.com` 必帶）、https 不轉址、≤5 MB、網址由伺服端產生 | §7；§2（`IMAGE_URL_ALLOWLIST`） |
| F10 | 照片附進修繕單：`broken_photos` 只送中繼資料、雜湊綁定、最多 5 張、JGB ⛔ 回頭抓我方網址 | §7.1；接口 B #22（計畫 §3h 第 6 點、§5b F10） |
| F11 | 文件值只放封閉表內有型別欄位 | §7.2～§7.4（計畫 §5b F11、DSP-073／076、§3h） |
| DSP-074 | 查詢與統計限於成員可見範圍、每次呼叫帶 viewer | §4（`user_id`）；接口 B #16～#18、#24（計畫 §3c、§3i 第 1 點） |
| DSP-075 | 對話模型 gpt-6-luna、`AGENT_REASONING_EFFORT=none` | §2（計畫 §3e） |
| 部署前置 `UVICORN_WORKERS=1` | MCP session 在行程內 | §2（計畫 §3e 環境發現 1） |
| `AGENT_ASSISTANT_KEY_IDS` | 站內幫手金鑰必帶 `user_id`；缺 ⇒ 400 `IDENTITY_MISSING_USER_ID`；`anonymous` ⇒ 400 `IDENTITY_MALFORMED` | §2；§4；§11（計畫 §3i 第 1 點） |
| `AGENT_TURN_TIMEOUT_S` | 正式機 90 秒；文件回合預算 `min(45, 逾時/2)` | §2；§3 |
| 查無與無權同一句 | jgb2 回 403、404 或成功但空 ⇒「系統裡查不到這個編號或名稱。」，程式固定句；其他失敗不說查不到 | §10（計畫 §3i 第 2 點） |
| JGB 未開放功能的固定句 | 統計三項、建立物件／合約／手動帳單：接真 JGB 時不發請求、程式固定句 | §10；§9 |
| 缺欄程式追問 | `outcome=clarifying`、固定詞彙 | §10（計畫 §3f，S2 修正輪） |
| 確認卡封閉欄位、卡上編號＝寫入編號 | 各動作欄位表、出卡時綁定編號 | §9（計畫 §3f 第 1、1d 點，§5b F3） |
| `outcome.action`／`ref.type` 值域 | 含 `estate` | §8（計畫 §3i 第 5 點） |
| 謄本由 DocuMind 解析 | 取值規則、四句固定句、掃描件不取縣市行政區樓層、所有權人資料不出現；`enable_llm=false`、https＋Token | §7.3；§2（計畫 §3h 第 4 點） |
| 文件回合放行 | `building_deed`→建立物件、`bill_receipt`→手動帳單；其餘不放行 | §7.2 |
| F1 我方保證 | 同 (api_key, vendor, session_id) 下 (user_id, role_id) 不同 ⇒ 不續用對話與確認卡 | §5 第 7 點 |
| 收據只取金額 | 台幣整數、收據日期只作卡外提示、繳費期限由使用者給 | §7.4（計畫 §3h 第 5 點） |
| 已知限制 | 建立失敗原因、`form_sessions` 清除、記憶撤除、偶發轉人 | §12（計畫 §3f 延後、§5b 待查、§3g） |
