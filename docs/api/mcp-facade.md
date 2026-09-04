# MCP 門面（`/mcp`）串接契約

> spec `agentic-mcp-orchestration` 任務 1.7 交付物（design.md 元件 4 指定）
> 建立：2026-09-04　適用：rag-orchestrator
> 讀者：要從**伺服器端**接上 JGB 工具面的工程（jgb2 後端、LINE bot 後端、回測工具、
> 內部操作者的 Claude Code）。

## 0. 一句話

`/mcp` 是 **server-to-server 的工具插座**，不是公開認證面。
它只做兩件事：**確認你是誰家的 key**（服務層閘）與**記你用了多少**（額度）；
「這個人能看到哪些個資」由 jgb2 `external/v1` 全權決定（DSP-011）。

## 1. 目前狀態（⚠️ 先讀）

| 項目 | 狀態 |
|---|---|
| 服務層閘（X-API-Key／Origin／X-JGB-Identity） | **已上線可用**，且已有整合測試 |
| 額度計量（一次工具呼叫一列 `usage_events`） | **已實作並實測** |
| MCP 工具面（`tools/list`／`tools/call`） | **尚未掛載**——Python MCP SDK 與現行 `fastapi==0.104.1` 相依衝突，待業主裁決是否升 fastapi |

> 相依衝突實查（可重跑）：
> `pip install --dry-run 'fastapi==0.104.1' 'mcp==2.1.1'` ⇒ `ResolutionImpossible`
> （fastapi 要 `anyio<4.0.0`、mcp 要 `anyio>=4.9`）。細節與硬裝後的實測後果見
> `rag-orchestrator/requirements.txt` 的 MCP 區塊。
> **在裁決前**：`/mcp` 的三道閘照常生效（缺 key 401、非白名單 Origin 403、
> 身分 header 不合法 400／403），過閘後因工具面未掛而回 404。

## 2. 端點與必帶 header

```
POST /mcp                       （MCP streamable HTTP；方法與 body 由 MCP 協定定）
  X-API-Key: <內部服務金鑰>       必帶，無條件（見 §3）
  X-JGB-Identity: <JSON>          必帶，見 §4
  Origin: <來源>                  選帶，見 §5
```

`/mcp` 與 `/mcp/` 都可以（服務端會把無尾斜線的路徑改寫掉，
⛔ 不會用 307 轉址——MCP client 的 HTTP 層預設不跟隨轉址，那會讓握手直接失敗）。

## 3. 服務層閘：`X-API-Key` **無條件**必帶

- `/mcp` 與 `/api/v1/agent/*` **不受 `RAG_API_AUTH_ENFORCE` 開關左右**。
  該旗標關著時，其他路徑不驗金鑰，但這兩條路徑仍一律 401。
  （不變量 28；`_EXEMPT_PREFIX` ⛔ 不得含 `/mcp`。）
- 理由：DSP-011 把「額度」定為本系統對呼叫者的唯一控制，而額度綁在 API key 紀錄上。
  沒有 key 就沒有額度歸屬，等於沒有控制。

金鑰由 `api_keys` 表發行（只存 sha256，不存明文）。
**取得方式**：照 `docs/deployment-runbook.md` §16「後台『登入即被踢』修復：
/rag-api 認證通道」的 **16-1 發行金鑰**流程（產生 → 入庫 → 寫 `.env`）另發一把，
`name` 改成足以辨識用途者（例如 `mcp-jgb2-backend`），並依 §3 的兩欄設定
`is_internal`／`vendor_ids`。⛔ 本文件與任何 repo 內文件都不寫金鑰值，
⛔ 金鑰也不得出現在指令的 argv（用檔案或 stdin 傳）。
⛔ 線上發行由業主自行執行（本專案規約：prod 破壞性操作不代跑）。

金鑰紀錄上與 `/mcp` 有關的兩個欄位（migration
`rag-orchestrator/database/migrations/20260904_api_keys_agent_scope.sql`）：

| 欄位 | 語義 |
|---|---|
| `is_internal` | 這把 key 的 `/mcp` 流量是否算內部（內部＝不計額度） |
| `vendor_ids` | 這把 key 可代表的業者白名單。**`NULL` ＝ 不限**；`{}`（空陣列）＝ 全拒 |

> ⚠️ `/mcp` 的「內部流量」判定**只看 key**。`/api/v1/message` 沿用的
> `session_id` 前綴規則（`backtest_`／`loop_`／`smoke_`…）**⛔ 不適用於 `/mcp`**——
> 那是呼叫方自己取的字串，若拿它決定計不計額度，等於讓呼叫方自己把額度關掉。

## 4. 身分 header `X-JGB-Identity`

一個 JSON 物件，放在 header：

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `vendor_id` | int（或整數字串） | ✅ | 業者 ID；必須存在於 `vendors` 表 |
| `session_id` | str | ✅ | 對話／呼叫串識別碼，**由呼叫端產生**，見 §4.1 |
| `mode` | `"b2b"` \| `"b2c"` | — | 缺或非法 ⇒ 正規化為 `"b2c"` |
| `target_user` | str | — | `tenant`／`landlord`／`property_manager`／`system_admin`／`prospect`；未知或缺 ⇒ 正規化為 `tenant` |
| `role_id` | str \| null | — | jgb2 雙證之一，見 §4.2 |
| `user_id` | str \| null | — | jgb2 雙證之二；同時是 `viewer_user_id`（bills／contracts 的圈定依據） |

範例：

```
X-JGB-Identity: {"vendor_id":1,"session_id":"jgb2-web-8f3c…","mode":"b2c",
                 "target_user":"tenant","role_id":"20151","user_id":"99887"}
```

### 4.0 fail-closed 規則（拒絕一律不透露細節）

| 情況 | 回應 | `code` |
|---|---|---|
| header 缺、JSON 不合法、不是物件 | 400 | `IDENTITY_MALFORMED` |
| 缺 `vendor_id`（或不是整數） | 400 | `IDENTITY_MISSING_VENDOR_ID` |
| 缺 `session_id`（或空白） | 400 | `IDENTITY_MISSING_SESSION_ID` |
| `vendor_id` 不在 `vendors` 表 | 403 | `VENDOR_UNKNOWN`（同時計入前提偵測告警） |
| `vendor_id` 不在這把 key 的 `vendor_ids` 內 | 403 | `VENDOR_NOT_IN_KEY_SCOPE` |
| 缺／錯 `X-API-Key` | 401 | `API_KEY_REQUIRED` |
| Origin 不在白名單 | 403 | `ORIGIN_NOT_ALLOWED` |

**信任邊界**：這些欄位是**上游信任輸入**（DSP-011：`role_id`／`user_id` 由 jgb2 面板
授權後帶出），本系統 ⛔ 不驗它們的真偽、⛔ 不簽發 bearer。
唯一由本系統守的是**知識池可見性**（`vendor_ids`／`business_types`／`target_user`／
保留分類），那住在本系統 DB，jgb2 管不到。

### 4.1 `session_id` 由呼叫端產生，且**跨回合穩定**

- 同一段對話的每一次呼叫**必須帶同一個 `session_id`**——服務端以它為鍵存
  對話歷史與 slots（`form_sessions.collected_data`，與 REST 路徑同源）。
  換 `session_id` ＝ 換一段新對話，先前的上下文不會被看到。
- ⛔ **不要**把 `session_id` 拿來當免額度的開關：`/mcp` 的內部判定只看 key（§3）。
- 速率限制的桶是 `(api_key_id, vendor_id)`，**不含 `session_id`**——換 session
  不會重置計數，這是刻意的。

### 4.2 `role_id=null` 的租客組合，以及它的可見性後果

`{"vendor_id":1,"session_id":"…","target_user":"tenant","role_id":null}` 是**合法**組合。
後果分兩塊，⚠️ 兩塊的答案不一樣：

| 面 | 結果 |
|---|---|
| **知識池**（`kb.get`／`kb.search`／`help.read`） | 照 tenant 池給——`role_id` 不參與知識可見性判定 |
| **jgb2 個資**（`jgb2.query.*`） | 一律 `NO_MATCH`——`JGBSystemAPI` 要 `role_id`＋`user_id` **雙證**，缺一即拒 |

所以「只想查知識、不查個資」的呼叫端可以不帶 `role_id`／`user_id`；
要查帳單／合約／物件等個資，兩個都要帶，且 bills／contracts 會把 `user_id` 當
`viewer_user_id` 交給 jgb2 圈定可見範圍（Layer 2）。

### 4.3 對話歷史歸服務端

呼叫端 ⛔ 不需要（也不應該）自己回帶歷史訊息。歷史與 slots 由服務端依
`session_id` 存取；工具面的每次呼叫是無狀態的單次查詢。

## 5. Origin 三態

| 情況 | 結果 | 為什麼 |
|---|---|---|
| **沒有 `Origin` header** | 放行 | server-to-server client 本來就不送 Origin |
| 有 `Origin` 且在 `MCP_ALLOWED_ORIGINS` | 放行 | 明示允許的來源 |
| 有 `Origin` 且不在白名單 | **403** | 瀏覽器直連／DNS rebinding |

- `MCP_ALLOWED_ORIGINS` 是逗號分隔清單。
- **未設定 ⇒ 服務啟動即失敗**（大聲失敗，⛔ 不預設放行）。
  若刻意不允許任何瀏覽器來源，設為 `-`（單一減號）＝空集合。
  兩份 compose 皆已宣告 `MCP_ALLOWED_ORIGINS: ${MCP_ALLOWED_ORIGINS:--}`。
- ⚠️ **`/mcp` 僅 server-to-server**。瀏覽器不能持金鑰；瀏覽器端請走
  `POST /api/v1/message`（REST＋SSE）。⛔ 不要為了「讓前端連得上」而放寬白名單。

## 6. 額度與計量

- **一次工具呼叫 ＝ 一列 `usage_events`**（不變量 31）。門面是唯一寫入者；
  HTTP middleware 對 `/mcp` 只做「達限短路」（429），⛔ 不重複落事件。
- 事件列的辨識欄位：`channel='mcp'`、`processing_path='mcp:<工具名>'`。
  ⛔ 不落問題原文與回答全文。
- 額度達限（`vendor_quotas.block_on_exceed`）⇒ HTTP 層 429；
  工具層則以 `QUOTA_EXCEEDED` 代碼回錯。
- **計量不可用時拒絕服務**：`USAGE_METERING_ENABLED=false` 或計量 context 建不起來
  ⇒ 工具呼叫直接以 `METERING_UNAVAILABLE` 拒絕。理由：額度是本系統對呼叫者的
  唯一控制，量不到就等於沒有控制，⛔ 不靜默放行。

## 7. 工具與錯誤代碼

工具清單依身分而異（`tools/list` 會依 `X-JGB-Identity` 過濾；真正的硬閘在呼叫時）。
M0 階段：

| 工具 | prospect | property_manager | tenant |
|---|---|---|---|
| `kb.get` | ✅ | ✅ | ✅ |
| `kb.search` | — | ✅ | ✅ |
| `help.read` | ✅ | ✅ | ✅ |
| `jgb2.query.{bills,contracts,accounts,meters,estates}` | — | ✅ | ✅ |

工具錯誤以 MCP `ToolError` 拋出，**訊息只含業務代碼**（⛔ 無 SQL、無例外文字、
無身分、無原文）：`NO_MATCH`／`TOOL_TIMEOUT`／`INVALID_INPUT`／`RATE_LIMITED`／
`CONFIRMATION_REQUIRED`，加上門面層的 `API_KEY_REQUIRED`／`ORIGIN_NOT_ALLOWED`／
`VENDOR_UNKNOWN`／`VENDOR_NOT_IN_KEY_SCOPE`／`IDENTITY_*`／`QUOTA_EXCEEDED`／
`METERING_UNAVAILABLE`。

> ⚠️ 「查不到」與「沒權限」對呼叫端**一律是 `NO_MATCH`**——這是刻意的，
> 避免 `/mcp` 變成一支「這筆資料存不存在」的探測 API。

## 8. 前提偵測（DSP-011 破了要重開）

DSP-011 成立的前提是「`/mcp` 只有上游／內部呼叫者」。以下四項任一出現即代表
前提可能已破，應重新檢視是否需要真正的認證層（tasks 1.8 會把它接進
`GET /api/v1/agent/health`）：

1. `/mcp` 出現非預期的 `api_key_id` 分佈
2. `vendor_id` 不在 `vendors` 表的請求
3. 帶著**非白名單 Origin** 的請求（缺 Origin 只記錄、不告警）
4. `RAG_API_AUTH_ENFORCE` 關著時 `/mcp` 仍有流量

## 9. 相關檔案

| 檔案 | 內容 |
|---|---|
| `rag-orchestrator/services/agent/mcp_facade.py` | 門面本體（三道閘、額度落點、工具接線、MCP server 建構） |
| `rag-orchestrator/services/api_key_auth.py` | `require_api_key_unconditional`／`verify_api_key` |
| `rag-orchestrator/database/migrations/20260904_api_keys_agent_scope.sql` | `api_keys.is_internal`／`vendor_ids` |
| `rag-orchestrator/tests/integration/agent/test_mcp_facade_req.py` | 兩道閘與額度落點的整合驗收（不變量 31 的覆蓋來源） |
| `.kiro/specs/agentic-mcp-orchestration/design.md` | 元件 4（本文件的規格母本）、附錄 B 不變量 27–31 |
