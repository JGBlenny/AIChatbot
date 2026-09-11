# MCP 門面（`/mcp`）串接契約

> spec `agentic-mcp-orchestration` 任務 1.7 交付物（design.md 元件 4 指定）
> 建立：2026-09-04　適用：rag-orchestrator
> 讀者：要從**伺服器端**接上 JGB 工具面的工程（jgb2 後端、LINE bot 後端、回測工具、
> 內部操作者的 Claude Code）。

> ⚠️ **2026-09-08 demo 上線後對碼修正**（本檔其餘段落寫於 2026-09-04）：`agent.turn` 對 `prospect` 與 `property_manager` 都是 M1；輸入 `message` `minLength 0`（可空）＋選填 `image_urls`（≤10 張 relay 簽章網址；兩者皆空才 `INVALID_INPUT`）；輸出**七鍵**＝五鍵＋`session_expired: bool`（DSP-042）＋`outcome{state, expects, action, ref}`（DSP-043：回合結果的封閉描述，呼叫端只看它決定畫面、⛔ 不解析 `answer` 字串；`transcript` 第八鍵屬 W7 語音，**尚未落地**）；機器值 `confirm_*:<pending_id>` 與 `select:<type>:<id>` 由 Runtime 在模型前處理。串接方請以 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/line-bot-integration-sheet-20260908.md` 為準；架構見 `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`。

## 0. 一句話

`/mcp` 是 **server-to-server 的工具插座**，不是公開認證面。
它只做兩件事：**確認你是誰家的 key**（服務層閘）與**記你用了多少**（額度）；
「這個人能看到哪些個資」由 jgb2 `external/v1` 全權決定（DSP-011）。

## 1. 目前狀態（⚠️ 先讀）

| 項目 | 狀態 |
|---|---|
| 服務層閘（X-API-Key／Origin／X-JGB-Identity） | **已上線可用**，且已有整合測試 |
| 額度計量（一次工具呼叫一列 `usage_events`） | **已實作並實測** |
| MCP 工具面（`tools/list`／`tools/call`） | **SDK 已為正式相依**（DSP-014 裁 A）——`requirements.txt` 已升 web stack 承載 `mcp==2.1.1` |
| 整回合工具 `agent.turn`（§7.1） | **已實作**（任務 2.6）；預設 **關閉**，要 `AGENT_TURN_ENABLED=true` ＋ `AGENT_STAGE=M1` 才註冊。prospect 與 property_manager 皆 M1（DSP-037，2026-09-07） |

> **DSP-014（2026-09-04 裁 A）**：原本的 `fastapi==0.104.1` × `mcp==2.1.1` 相依
> 衝突（fastapi 要 `anyio<4.0.0`、mcp 要 `anyio>=4.9`）已藉由升級 web stack 解除：
> fastapi 0.115.14／starlette 0.46／pydantic 2.13／anyio 4.15／uvicorn 0.52。
> 版本與理由見 `rag-orchestrator/requirements.txt` 的 MCP 區塊。
>
> `mcp_facade.mcp_sdk_available()` 因此**只是防禦性守衛**，⛔ 不再代表「尚未安裝」：
> 它讓 `/mcp` 的三道閘（缺 key 401、非白名單 Origin 403、身分 header 不合法
> 400／403）在 image 供裝出錯時仍然成立（工具面掛不上、過閘後回 404），
> 而不是整個 app 起不來。正常部署下它必為可用；回不可用代表**供裝壞了**。

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

> ⚠️ `/mcp` 的「內部流量」判定**只看 key**。⚠️ **2026-09-11 舊鏈退役**：
> 曾經存在的 `/api/v1/message`（已刪除，`routers/agent_entry.py` 未掛載於
> `app.py`，無此路由）沿用的是 `session_id` 前綴規則（`backtest_`／`loop_`／
> `smoke_`…）——那套規則**⛔ 不適用於 `/mcp`**，即使日後有新入口比照辦理也一樣：
> `session_id` 是呼叫方自己取的字串，若拿它決定計不計額度，等於讓呼叫方自己把
> 額度關掉。

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
  對話歷史與 slots（`form_sessions.collected_data`；⚠️ 2026-09-11 舊鏈退役前，該表曾與 REST 路徑〔已刪除〕共用，現在 `/mcp` 是唯一寫入者）。
  換 `session_id` ＝ 換一段新對話，先前的上下文不會被看到。
- ⚠️ `/mcp` 的實際鍵是 **`mcp:{api_key_id}:{vendor_id}:{session_id}`**（命名空間，
  見 §7.1）：同一個 `session_id` 換 key／換 vendor 就是另一段對話（歷史上與已刪除的
  REST 路徑也不互通）。整把鍵受 `VARCHAR(100)` 限制 ⇒ `session_id` 請留在 80 字以內。
- ⛔ **不要**把 `session_id` 拿來當免額度的開關：`/mcp` 的內部判定只看 key（§3）。
- 速率限制的桶是 `(api_key_id, vendor_id)`，**不含 `session_id`**——換 session
  不會重置計數，這是刻意的。

### 4.2 `role_id`／`user_id` 缺漏時的可見性後果

`{"vendor_id":1,"session_id":"…","target_user":"tenant","role_id":null}` 是**合法**組合。
後果分兩塊，⚠️ 兩塊的答案不一樣：

| 面 | 結果 |
|---|---|
| **知識池**（`kb.get`／`kb.search`／`help.read`） | 照該受眾的池給——`role_id`／`user_id` 不參與知識可見性判定 |
| **jgb2 個資**（`jgb2.query.*`） | 依受眾要幾張證，見下表 |

**jgb2 個資的證件要求（受眾決定，⛔ 不是全域同一條規則）**

受眾由 `target_user`／`mode` 決定性推導（`services/agent/identity.py:audience_of`）：

| 受眾 | `jgb2.query.bills`／`.contracts` | `jgb2.query.accounts`／`.meters`／`.estates` |
|---|---|---|
| `tenant`（含 `target_user` 缺／未知） | **雙證**：`role_id`＋`user_id`，缺一即 `NO_MATCH` | **雙證**，缺一即 `NO_MATCH` |
| `prospect` | **雙證**（實務上工具本身對 prospect 永不可見——`stage` 缺 prospect 鍵） | 同左 |
| `property_manager`（含 `mode="b2b"`） | **單證**：`role_id` 即可；`user_id` 可缺 | **雙證**，缺一即 `NO_MATCH` |

- **為什麼 pm 是單證**：pm 查的是自己名下**整個 role**的帳單／合約。帶了 `user_id`
  反而會讓 jgb2 用 `viewer_user_id` 圈定成「這個 user 看得到的」，把 pm 自己的查詢
  過濾成空。
- **`viewer_user_id` 的圈定條件**：bills／contracts 在 `user_id` **非空時**才把它當
  `viewer_user_id` 轉發給 jgb2（Layer 2 圈定）；`user_id` 缺時**不圈定**——jgb2 只認
  `role_id`，回的是整個 role 的資料。這正是 tenant 必須雙證的理由：少一張證不是
  「查得少」，是「查得比該看的多」。
- **落點**：`rag-orchestrator/services/agent/tools/jgb2.py:_identity_gate_ok`
  （bills／contracts）與 `JGBSystemAPI._validate_identity`（其餘三域）。
  受眾算不出時 **fail-closed 當 tenant**（要雙證）。

所以「只想查知識、不查個資」的呼叫端可以不帶 `role_id`／`user_id`；
租客要查帳單／合約／物件等個資，`role_id` 與 `user_id` **兩個都要帶**。

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
- ⚠️ **`/mcp` 僅 server-to-server**。瀏覽器不能持金鑰。⚠️ **2026-09-11 舊鏈退役**：
  過去瀏覽器端走的 `POST /api/v1/message`（REST＋SSE）已刪除，且**目前沒有替代
  的瀏覽器直連入口**——`/mcp` 是 MCP 協定門面，⛔ 不是 REST JSON／SSE 的替代品，
  不能直接拿給瀏覽器用。瀏覽器端對話目前無可用入口（既知缺口，非本文件範圍）。
  ⛔ 不要為了「讓前端連得上」而放寬白名單。

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

M1 階段另加一支**整回合**工具（見 §7.1）：

| 工具 | prospect | property_manager | tenant |
|---|---|---|---|
| `agent.turn` | ✅（且需 `AGENT_TURN_ENABLED=true`） | — | — |

工具錯誤以 MCP `ToolError` 拋出，**訊息只含業務代碼**（⛔ 無 SQL、無例外文字、
無身分、無原文）：`NO_MATCH`／`TOOL_TIMEOUT`／`INVALID_INPUT`／`RATE_LIMITED`／
`CONFIRMATION_REQUIRED`，加上門面層的 `API_KEY_REQUIRED`／`ORIGIN_NOT_ALLOWED`／
`VENDOR_UNKNOWN`／`VENDOR_NOT_IN_KEY_SCOPE`／`IDENTITY_*`／`QUOTA_EXCEEDED`／
`METERING_UNAVAILABLE`／`AGENT_UNAVAILABLE`（僅 `agent.turn`，見 §7.1）。

> ⚠️ 「查不到」與「沒權限」對呼叫端**一律是 `NO_MATCH`**——這是刻意的，
> 避免 `/mcp` 變成一支「這筆資料存不存在」的探測 API。

## 7.1 `agent.turn`：一次呼叫跑完一整個回合（M1）

> spec `agentic-mcp-orchestration` 任務 2.6｜design 元件 4「`agent.turn` 工具」段、
> 決策 15、R3.7

其餘工具是**零件**（查一筆知識、查一張帳單），`agent.turn` 是**成品**：你丟一句
使用者說的話，服務端跑完「模型選工具 → 取事實 → 產出 → Output Verifier 逐句驗
引用 → 過不了就固定句＋轉人」整條鏈，回你一段可以直接顯示的答覆。

**M1 只開 prospect（售前）身分。** 租客／業者的對話能力在子 spec
（`agent-tenant-audience`），此處 `stage` 缺鍵＝**永不可見**，⛔ 不是「還沒開」。

### 輸入

```jsonc
// tools/call → name: "agent.turn"
{ "message": "我有 600 戶，你們的合約怎麼建立？", "image_urls": [] }   // message 0–2000 字（可空）；image_urls 選填 ≤10；兩者不得皆空
```

**只有 `message` 這一個參數**。⛔ 沒有 `dialog_ref`、⛔ 不能帶對話歷史、
⛔ 不能帶任何身分鍵（`vendor_id`／`role_id`／`user_id`／`target_user`／`mode`
一律在服務端被剝掉並記進 trace）。身分與 session 全部來自 `X-JGB-Identity`。

### 輸出

```jsonc
{
  "answer": "…",              // 要顯示給使用者的那段話（已經過 Verifier）
  "kind": "answer",           // answer | ask | recommend | handoff
  "handoff": null,            // 轉人時是 {reason, fact_class, channel, message}
  "quick_replies": [],        // 機器值清單，直接當按鈕用
  "trace_id": "…"             // 對得回 usage_events.decision_snapshot.agent（任務 2.7）
}
```

⛔ **不回 `citations`**：引用是 Verifier 的內部證據，回給你只會外洩「哪一列知識的
哪一段字」。⛔ **不回被拒的草稿**：Verifier 拒兩次時 `answer` 是固定句，模型那兩
份被拒的文字只留在服務端的重寫上下文裡，一個字都不外流。

### 對話怎麼接起來（session 契約）

- `session_id` **由你產生**，同一段對話跨回合用同一個（放在 `X-JGB-Identity`）。
- 對話歷史與 slots **由服務端保存**，⛔ 你不需要、也不能回傳歷史。
- 服務端存放位置是 `form_sessions.collected_data`，鍵是
  **`mcp:{api_key_id}:{vendor_id}:{session_id}`**（命名空間）。這代表：
  - 換一把 key、或換一個 `vendor_id`，即使 `session_id` 一模一樣，**讀到的是另
    一段對話**，也改不到原本那一列。這是刻意的隔離，⛔ 不是 bug；
  - ⚠️ **2026-09-11 舊鏈退役**：過去的 `/api/v1/message`（REST，已刪除）走裸
    `session_id`，與 `/mcp` 的命名空間鍵**天然分池**——歷史上同一個 `session_id`
    在兩條入口是兩段對話，⛔ 不曾互通，此事實不因舊鏈刪除而改變（`form_sessions`
    表仍是同一張，`/mcp` 現在是唯一寫入者）；
  - 整把鍵受 `form_sessions.session_id` 的 `VARCHAR(100)` 限制 ⇒ 你的
    `session_id` 太長時會拿到 `INVALID_INPUT`。實務上留 80 字以內即可。

### 一次性回傳，⛔ 沒有逐字串流

MCP 工具結果是一次回完的，**首字＝整段完成**（決策 15 明列的代價）。
⚠️ **2026-09-11 舊鏈退役**：過去可以走 REST 的 `POST /api/v1/message` + SSE
取得逐字串流，該端點已刪除；`/mcp` 目前**沒有**逐字串流的替代方案，
這是刻意接受的代價（決策 15），不是尚待補的功能。

### 逾時

`AGENT_TURN_TIMEOUT_S`（預設 **30 秒**）——刻意大於回合預算 `Budget.deadline_s`
（20 秒），⛔ 不是門面對其他工具那個 3 秒。逾時或呼叫被取消 ⇒ 回 `TOOL_TIMEOUT`，
而且**這一回合的狀態不會被存下來**（⛔ 不落半寫），你可以直接重試。

### 每小時上限

`AGENT_TURN_CAP`（預設 **120 次／小時**），計數 key 是 **`(api_key_id, vendor_id)`**
——⛔ 換 `session_id` 不會重置。超過回 `RATE_LIMITED`。
⚠️ 這個計數器是**行程內記憶體**，多 worker 部署時實際上限是
`AGENT_TURN_CAP × worker 數`（與既有的 `RATE_PER_MIN`／`KB_GET_CAP` 同一個限制）。
真正的花費控制在額度層（`usage_events`），這裡只是護欄。

### 回切開關 `AGENT_TURN_ENABLED`

**預設 `false`**。關閉 ⇒ 這支工具**根本不註冊**，`tools/list` 看不到它、呼叫它
回 `NO_MATCH`——⛔ 不是「註冊了但拒絕」。要回切就把 env 改回 false 再重啟，
其餘工具面不受影響（5.1 回切演練含這一格）。
⚠️ `AGENT_AUDIENCES` **管不到它**：那支 env 原本只管 REST 入口
（`routers/agent_entry.py`）要不要把哪些身分導進 agent 鏈；⚠️ **2026-09-11 舊鏈
退役**後 `routers/agent_entry.router` 未掛載於 `app.py`，這支 env **目前沒有生效
路徑**（讀了也不影響任何路由），留著只是尚未清理的殘留設定。

### ⚠️ 給外部 MCP client 的一句話：`facade_only` 對你是**單層**設計

`agent.turn` 標了 `facade_only=True`，意思是「**服務端內部那個模型**看不到它」
（模型工具清單與影子視圖都不含），因此模型不可能自己呼叫 `agent.turn` 造成遞迴。

但**你**——連上 `/mcp` 的那個 MCP client——本身就是一個模型（或由模型驅動）。
對你而言這一層不存在：你看得到、也叫得動 `agent.turn`。這是**設計意圖**，不是
漏洞，代價要講清楚：

- 你每呼叫一次 `agent.turn`，服務端就跑一整個回合（多次 LLM 呼叫），
  **每一次都計額**（一次呼叫恰一列 `usage_events`，token 彙總在該列）；
- 所以 ⛔ 不要在你自己的工具迴圈裡把 `agent.turn` 當成「便宜的知識查詢」。
  要查知識就用 `kb.get`／`kb.search`／`help.read`；`agent.turn` 是要**整段客服
  回覆**時才用的。

### 服務未接妥時

`AGENT_UNAVAILABLE`：服務端的 agent runtime 還沒建起來（或建立失敗）。
這是伺服器狀態，⛔ 不是你的請求有問題；重試前先看 `GET /api/v1/agent/health`
的 `checks.rules_sha`——它是這個行程實際帶著的那把 Verifier 規則尺的 sha256，
`"pending"` 代表 runtime 尚未接上。

## 8. 前提偵測（DSP-011 破了要重開）

DSP-011 成立的前提是「`/mcp` 只有上游／內部呼叫者」。以下四項任一出現即代表
前提可能已破，應重新檢視是否需要真正的認證層（tasks 1.8 會把它接進
`GET /api/v1/agent/health`）：

1. `/mcp` 出現**未登錄**（`verify_api_key` 查無）或**非 `is_internal`** 的
   `api_key_id`（任務 2.8 起；`api_key_id` 整體分佈仍輸出為觀測值，不再以
   「非零即紅」判）
2. `vendor_id` 不在 `vendors` 表的請求
3. 帶著**非白名單 Origin** 的請求（缺 Origin 只記錄、不告警）
4. `RAG_API_AUTH_ENFORCE` 關著時 `/mcp` 仍有流量

## 9. 相關檔案

| 檔案 | 內容 |
|---|---|
| `rag-orchestrator/services/agent/mcp_facade.py` | 門面本體（三道閘、額度落點、工具接線、MCP server 建構） |
| `rag-orchestrator/services/api_key_auth.py` | `require_api_key_unconditional`／`verify_api_key` |
| `rag-orchestrator/database/migrations/20260904_api_keys_agent_scope.sql` | `api_keys.is_internal`／`vendor_ids` |
| `rag-orchestrator/services/agent/state_store.py` | `agent.turn` 的狀態命名空間鍵（`NamespacedStateStore`） |
| `rag-orchestrator/services/agent/runtime.py` | `AgentRuntime.run_turn`——`agent.turn` 的回合邏輯（⚠️ 2026-09-11 舊鏈退役前曾與 REST 入口共用同一條） |
| `rag-orchestrator/tests/integration/agent/test_mcp_facade_req.py` | 兩道閘與額度落點的整合驗收（不變量 31 的覆蓋來源） |
| `rag-orchestrator/tests/integration/agent/test_agent_turn_req.py` | `agent.turn` 的整合驗收（跨業者隔離、兩回合、Verifier 拒兩次、計量） |
| `rag-orchestrator/tests/unit/agent/test_agent_turn_req.py` | `agent.turn` 的 unit 驗收（可見性、命名空間、逾時、上限） |
| `.kiro/specs/agentic-mcp-orchestration/design.md` | 元件 4（本文件的規格母本）、附錄 B 不變量 27–31 |

## 10. env 一覽（部署參考；完整版含查證指令見 `docs/deployment-runbook.md` §19-5）

本文件 §5–§7.1 已就地說明 `MCP_ALLOWED_ORIGINS`／`RATE_PER_MIN`／`KB_GET_CAP`／
`AGENT_TURN_ENABLED`／`AGENT_TURN_TIMEOUT_S`／`AGENT_TURN_CAP` 各自的行為；
以下補齊與 `/mcp` 相關、但分散在其他模組（大綱組裝、影子、身分/追蹤）的其餘 env，
彙整成一張表方便部署時查閱：

| env | 預設 | 作用 |
|---|---|---|
| `AGENT_STAGE` | `M0` | 部署里程碑；工具可見性以 `stage[audience] <= AGENT_STAGE` 判定（`services/agent/mcp_facade.py:current_stage`） |
| `AGENT_AUDIENCES` | 空 | ⚠️ **2026-09-11 舊鏈退役**：原本是 REST 入口（已刪除的 `/api/v1/message`）分流用，`routers/agent_entry.router` 現未掛載於 `app.py`，**目前無生效路徑**；**不影響** `/mcp`／`agent.turn` 的可見性（見 §7.1「回切開關」段） |
| `AGENT_SHADOW_AUDIENCES` | 空 | 影子跑動的 audience 白名單（`services/agent/shadow.py`） |
| `AGENT_SHADOW_MONTHLY_USD_CAP` | `50.0`（USD） | 影子月成本上限，超過自動關 |
| `AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT` | `10000` | 售前大綱 token 預算（`services/agent/outline.py`） |
| `AGENT_OUTLINE_TOKEN_LIMIT_PM` | `8000` | pm 目錄 token 預算（子 spec 用，M1 尚未消費） |
| `AGENT_OUTLINE_TOKEN_LIMIT_TENANT` | `8000` | tenant 目錄 token 預算（子 spec 用） |
| `AGENT_MODEL` | 未設 ⇒ 退回 `OPENAI_MODEL` ⇒ 再無則 `gpt-4o-mini` | agent runtime 模型名（`services/agent/runtime.py`） |
| `AGENT_TRACE_WINDOW_DAYS` | `7` | `agent_trace` 查詢時間窗（`services/agent/trace_view.py`） |
| `JGB2_CANDIDATE_CAP` | `5` | `jgb2.query.*` 候選列筆數上限（`services/agent/tools/jgb2.py`） |

`AGENT_BUDGET_TOOL_CALLS`／`AGENT_BUDGET_REWRITES`／`AGENT_BUDGET_DEADLINE_S`（預設 4／2／20.0；DSP-040 起 `REWRITES` 只對**機敏類**拒因計數，引用類拒因只記錄不重寫——`AGENT_VERIFIER_MODE=grounding_observe`；demo 起法另設 `DEADLINE_S=45`）：由 `services/agent/bootstrap.py:budget_from_env` 讀取（2026-09-05 補上；5.3 查證時發現 design 列了但程式沒讀），壞值／≤0 退回預設。