# LINE bot 串接資訊（demo 版，2026-09-08 上線）

## 端點
- MCP（streamable HTTP）：`POST https://chatai.jgbsmart.com/rag-api/mcp`（方法 `tools/list`、`tools/call`）
- 伺服器對伺服器。⛔ 不要送 `Origin` header（送了必須在白名單內，否則 403）。
- 無 key 或 key 錯 ⇒ HTTP 401 `{"detail":"Invalid or missing API key"}`。
- 無 key ⇒ nginx 403；key 錯 ⇒ 401。**MCP 協定要先 `initialize`**（回 200＋`mcp-session-id` header，之後每個請求帶 `Mcp-Session-Id`）；直接打 `tools/list` 會回 400「Missing session ID」，那是協定不是路由問題。（2026-09-08 晚：`/rag-api/mcp` 曾 404，nginx 已加直通 location，已驗通。）

## Header（每個請求都帶）
```
X-API-Key: <demo key；名稱 line-bot-oa-demo，前綴 rgk_AEHV；由業主另行交付，⛔ 不進版控、不進日誌>
Content-Type: application/json
Accept: application/json, text/event-stream
X-JGB-Identity: {"mode":"b2b","target_user":"property_manager","vendor_id":4,"role_id":"20151","user_id":"12291","session_id":"<穩定假名>"}
```
- `vendor_id` 4＝demo 業者（替身資料）；`role_id`／`user_id` demo 固定 20151／12291。
- `session_id`：每段 LINE 對話一個穩定假名（⛔ 不要直接放 LINE userId）。同一 `session_id` 超過 30 分鐘沒動作 ⇒ 下一回合回應 `session_expired: true`，會話重新開始。

## 工具 `agent.turn`
輸入：
```json
{"message": "<0–2000 字>", "image_urls": ["https://relay.jgbsmart.com/...簽章網址", "..."], "context": "<≤500 字，選填，每回合可帶>"}
```
- `message` 可為空字串（只傳照片）；兩者皆空 ⇒ `INVALID_INPUT`。
- `context` 選填，≤500 字（超過整回合 `INVALID_INPUT`），**每回合可帶**：呼叫端提供的**本回合背景資訊**——進場時印給使用者的提示句、使用者所在頁面、已選的物件／帳單、上一步的結果等，用一段話寫就好。chatai 把它當**脈絡**看，⛔ 不當成使用者說的話——所以 ⛔ 不要把它併進 `message`，也不要為它多送一個回合。它不會被引用成事實，也不進對話歷史與紀錄（只記「有沒有帶」）。2026-09-09 業主裁：欄位是通用的背景資訊，不是「進場句」。
- **入口清單須對能力表**：`context` 帶進來的入口必須對得上 chatai 現有的能力（查帳單、查合約、查修繕、報修、延期…）；沒有對應能力的入口（例如「建立物件」）會得到 `out_of_scope`，⛔ 不要期待它被答出來。
  > ⚠️ **對碼註記（2026-09-09，T1）**：`outcome.state == "out_of_scope"` 目前**只有清單點選釘住那一戶之後問別戶／別戶寫入被擋**這條路徑會產生（`grep -n '"out_of_scope"' rag-orchestrator/services/agent/runtime.py` → `_apply_scope_exit` 與 `_scope_gate_confirm_request` 兩處）。「無對應能力的入口」今天實際落到的是追問或轉真人，**不是** `out_of_scope`。上面那一句是**目標行為**，⛔ 尚未有程式保證；呼叫端請先依 `outcome` 的實際值分支，⛔ 不要在這一格上寫死。
- `image_urls` 選填，最多 10 張，第 11 張起整回合 `INVALID_INPUT`；每張 ≤5,000,000 bytes；只收 `https://relay.jgbsmart.com` 的簽章網址（帶 `exp` 到期戳）；超過 5 張 chatai 內部分批辨識，時間不夠會明講「只看了前 N 張」。⛔ 不要把多張拆成兩個回合。

輸出（`tools/call` 結果的文字內容是 JSON）：
```json
{"answer": "<給使用者看的文字>", "kind": "answer|ask|handoff", "handoff": null, "quick_replies": [{"label": "...", "value": "..."}], "trace_id": "<hex>", "session_expired": false,
 "outcome": {"state": "answered|clarifying|confirm_pending|confirmed|cancelled|failed|handoff|out_of_scope", "expects": "text|choice|button|none", "action": "repair_create|bill_due_extend|null", "ref": {"type": "repair|bill|contract", "id": "12346"}}}
```
- `answer` 直接顯示。`kind=handoff` ⇒ `answer` 是固定的轉專人句，請掛「找真人」動作。
- `quick_replies` 有值就渲染成按鈕；使用者點了，把 `value` **原字串**當下一回合的 `message` 送回，⛔ 不要改寫。
- **畫面狀態只看 `outcome`**：`state==confirmed` ⇒ 任務完成（`ref` 是單號／帳單編號）；`confirm_pending` ⇒ 顯示三顆確認鍵；`clarifying` ⇒ 等文字或選項（看 `expects`）；`handoff` ⇒ 找真人；`out_of_scope` ⇒ 回清單；`failed` ⇒ 顯示 `answer` 的固定句。⛔ 不要解析 `answer` 字串。
- **照片**：同一使用者 3 秒內的照片與文字合成一次 `agent.turn`，不要拆回合。**LIFF** 六格一律走這條 MCP（relay 後端代打），不接 REST `/rag-api/v1/message`。

## 機器值（`value` 會出現的形狀）
| 形狀 | 意義 |
|---|---|
| `confirm_submit:<16 hex>` | 確認卡「✅ 確認送出」 |
| `confirm_edit:<16 hex>` | 「✏️ 我要修改」 |
| `confirm_cancel:<16 hex>` | 「❌ 取消」 |
| `<修繕分類名>` | 照片辨識信心低時的分類候選（≤3 顆，label＝value） |

確認卡回合：`kind=ask`、`answer` 是卡文字（物件／修繕分類／急迫程度／問題描述，可能多一行「另有未結單 N 張」）、`quick_replies` 三顆確認鍵。按送出 ⇒ 下一回合 `answer` 含單號；重按同一鍵不重複建單；過期後按舊鍵 ⇒ 固定句「這筆確認已失效，請重新確認一次。」

## 清單點選
使用者點清單那一筆時，把 `select:<type>:<id>` 當 `message` 送入：`type ∈ bill | contract | repair`，`id` 為 JGB 編號。回應是程式直答的該筆事實（`kind=answer`），之後追問用文字即可。不存在或不在範圍 ⇒ 「查無此筆」。點選後同一段對話只看那一戶，問別戶會回「這個對話只看你點選的那一戶；要查別戶請回清單點那一戶。」；要換戶就再點清單。

## 限制與錯誤
- 速率：每分鐘 60、每小時 120 回合（全體共用一把 key）；照片每小時 200 張。
- 工具層錯誤（`ok=false`）只有五碼：`INVALID_INPUT`／`NO_MATCH`／`TOOL_TIMEOUT`／`CONFIRMATION_REQUIRED`／`RATE_LIMITED`。
- HTTP：401 key；403 Origin／vendor 不在 key 範圍；400 `IDENTITY_*`（header JSON 壞、缺 vendor_id／session_id）。
- 單回合逾時 60 秒（帶照片時照片處理最多佔 15 秒）。

## demo 資料（替身）
帳單 756248（逾期 7 天）、756242（已繳）、769249（未到期）；合約 89481；電錶 1061；物件「基隆溫馨一人宅套房」（有未結單 8591）、「台北中正-小南門單身貴族分租套房B」。全表見 `inputs/demo-data-sheet-line-oa-20260908.md`。替身寫入只在記憶體，服務重啟歸零。

## 自測
```bash
curl -s -X POST https://chatai.jgbsmart.com/rag-api/mcp -K ./mcp-key.txt \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H 'X-JGB-Identity: {"mode":"b2b","target_user":"property_manager","vendor_id":4,"role_id":"20151","user_id":"12291","session_id":"linebot-test-1"}' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
（`mcp-key.txt` 內容一行：`header = "X-API-Key: <key>"`，600 權限。）預期 16 個工具，含 `agent.turn`、`jgb2.action.bill_due_extend`、`jgb2.action.repair_create`。

## 相關文件
- 契約細節：`inputs/mcp-client-contract-line-bot-20260907.md`
- 工作列：`inputs/line-bot-worklist-demo-20260908.md`
- 30 個驗收案例對照：`inputs/demo-scenarios-20260908/liff-30.json`
