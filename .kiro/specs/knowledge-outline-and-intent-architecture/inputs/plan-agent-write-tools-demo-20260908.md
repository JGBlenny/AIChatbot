# Plan：`agent-write-tools`（demo 範圍，替身後端）v3 — 2026-09-08（r1 六條＋r2 五條 blocker 全部 FIX；r3 為關閉輪）

> 業主裁示（demo 帳本 §1b R1–R3）：demo 在 JGB 開 API 前舉行、整場跑替身；替身讀寫在一份 JSON；寫入工具升 demo 必做。本 Plan 是 roadmap 子 spec 2 `agent-write-tools` 的 **demo 切片**：目標形態不變（design 元件 3 `jgb2.action.<x>{payload, confirmation_token}→{receipt}`），先在替身上把整條鏈演通；真 `agent/v1` 簽章 client 與 JGB 端 `PATCH` 為 demo 後切片。security-reviewer 13 條處置見 §5；plan-verifier r1 處置見 §7。

## 0. 前置：DSP-038（待業主裁，⛔ 未裁不開工 W1）
一次裁三件（都是正本變更，程式⛔不得先行）：
1. **可見性閘**：`jgb2.action.*` 可見＝`AGENT_WRITE_TOOLS_ENABLED`（預設 false、進健檢）**AND** stage；design 元件 2 表 pm 由 M5 改 **M1**、tenant 保持 M4；requirements R4.4 改為「`AGENT_WRITE_TOOLS_ENABLED` 未開即不暴露任何寫入型工具；旗標只在替身或 JGB 憑證就緒時開」。（否決：只改 stage 無旗標＝上線即開寫入；只綁 `USE_MOCK_JGB_API`＝綁在預設 true 且健檢看不見的旗上。）
2. **確認綁定語義**：`confirm.request(summary, payload)` **簽名不變**（R4.2 文字不動）；`payload` 必含 `action`；**確認卡文字由程式 formatter 依 `action`＋`payload` 決定性產出**（⛔ 不用模型的 `summary` 當卡）；`summary_sha256` 欄改存**卡文字雜湊**、兌現時比對。design 元件 3 `confirm.request` 列同步改寫；受影響測試列在 W2。
3. **token 表只加一欄**（migration，可逆）：`agent_confirmation_tokens` 加 `pending_id text`（= `sha256(token)[:16]`，索引；⛔ 仍不存 payload／summary 原文，表的「只存雜湊」決定不變）。
4. **待確認的 `action`／`payload`／`receipt` 存 session 狀態**（`agent_state["pending_confirm"][pending_id]`，經既有 `state_store` 落 `form_sessions.collected_data`——與既有 `bill_ref`／`contract_ref` 槽位同一敏感等級與同一保留期；⛔ 不存 token）。R4.3「同一 token 重送回同一結果」以狀態內 `receipt` 實現。保留／清理：隨 session 既有 TTL；demo 期不另清理（取捨明列）。

## 0b. 前置：DSP-042（**業主 2026-09-08 裁：三件都採**；W-D 已落檔）
一次裁三件（都是正本變更，程式⛔不得先行；落檔在 W-D、擁有者＝主 session）：
1. **`AgentTurnOutput` 加選填鍵 `session_expired: bool`**（預設 false；只在「同 `session_id` 超過 30 分鐘再進」的那一回合為 true）。鍵序依實際落地順序：§3 先後 W8 在 W7 之前 ⇒ `session_expired` 是**第六鍵**、W7 的 `transcript` 順延為第七鍵（DSP-041 文字同步改「第七鍵」）；requirements R3.7 措辭改為「五鍵固定＋依落地順序加的選填鍵（`session_expired`、`transcript`）」；design 元件 4 回應表同步。
2. **清單點選機器值 `select:<type>:<id>` 成為對外契約**（R10-c）：第一版值域 `type ∈ {bill, contract, repair}`、`id` `^[A-Za-z0-9_-]{1,32}$`；由 line-bot 契約 v1 「select 列」承載；`estate`／`meter` 待工具層 ref 語義補齊後另裁開放。
3. **落檔清單**：`DECISIONS.md` DSP-042、requirements R3.7、design 元件 4（回應鍵）與元件 3（`jgb2.query.repairs` 加 `estate_id`）、line-bot 契約 select 列——全部列入 W-D 範圍，W8 範圍欄⛔ 不含正本。

## 1. 結果（outcome）與驗收
**結果**：pm 經 `/mcp` `agent.turn`，替身後端上：
1. 「900001 逾期了，幫我延 3 天」→ **該回合 `TurnResult.answer` 逐字＝程式產出的確認卡**（帳單 900001、原到期 2026/08/15、新到期 2026/08/18；⛔ 不經模型、不經 Verifier 改寫）＋三顆機器值 → 房東回 `confirm_submit:<pending_id>` → **Runtime**（⛔ 不是模型）以 `(session_id, pending_id)` 單述句兌現、取回 token、在行程內呼叫 `jgb2.action.bill_due_extend` → 替身 `PATCH /agent/v1/bills/900001` → receipt 存回表 → 回答「已延至 2026/08/18」；下一回合「900001 到期哪天」讀到 2026/08/18。
2. 「這戶熱水器壞了，直接幫我開單」→ 確認卡 → 送出 → `jgb2.action.repair_create` → 替身建修繕單 → 「這戶有沒有修繕單」查得到。
3. 反向五條（每條**唯一預期**）：(1) `confirm_cancel:<pid>`／`confirm_edit:<pid>` ⇒ token 燒掉、`receipt={"cancelled":true}`、替身無變更；(2) **重送** `confirm_submit:<pid>` ⇒ 回**同一 receipt id**（R4.3），替身該資源只有一筆變更；(3) 自由文字「好，送出」／裸 `confirm_submit`（無 pid）／錯 pid ⇒ 不寫、回「請用按鈕確認」；(4) 過期（10 分鐘）⇒ `CONFIRMATION_REQUIRED`、要求重新確認；(5) 替身注入失敗（`MOCK_FAIL_NEXT_WRITE=1`）⇒ 誠實回錯、`receipt={"error":…}`、替身無殘單、須重新確認（S-12：token 已燒是刻意）。

**主驗收**（R-寫，scratchpad `smoke/scenarios_write.json`，經 `/mcp`，最終起法＋`AGENT_WRITE_TOOLS_ENABLED=true`）：2 正向＋5 反向全過；`usage_events`／trace 有 `pending_id`＋receipt id；`health` 顯示 `use_mock_jgb_api=true`、`write_tools_enabled=true`。**入口隔離驗收（DB 可反證）**：先由 MCP 身分建一張 token（列 `session_id='mcp:98:4:s1'`），再以 REST 身分帶同字串 `session_id` 送 `confirm_submit:<pid>` ⇒ 該列 `redeemed=false` 不變、狀態無 receipt、`specs_for` 不含 `jgb2.action.*`；正對照＝同 pid 由 `/mcp` 送出可兌現得 receipt。**影子隔離驗收**：`readonly_view=True` 的 Runtime 收同訊息 ⇒ DB 0 次 UPDATE、列仍 `redeemed=false`；正對照＝`readonly_view=False` 兌現。次驗收：unit 新測試綠、既有不退（W2 列出的兩檔依新契約更新）、`make audit` PASS、security-executor 落地後 fresh verifier CONFIRMED。

## 2. 非目標（demo 不做）
- 真 `agent/v1` 簽章 client、憑證儲存與輪替——demo 後、JGB 開白名單與憑證後（S-3 DEFER）。
- jgb2 端 `PATCH /agent/v1/bills/{id}`＋`agentCanSee`——JGB 的事（需求文 §B′5，S-10 DEFER）。
- token 表加 `vendor_id`／REST 入口 session 命名空間（S-6）——demo 期靠 **`mcp_only`**（見 W1）讓 REST 入口根本看不到也呼叫不到寫入工具；上線前補。
- 建約、謄本建物件、建帳單——形狀同、demo 不演。

## 3. 切片

| ID | 結果 | 範圍（檔案） | 驗收 | 擁有者 |
|---|---|---|---|---|
| **W0** 替身全覆蓋 | 讀全部＋`POST /repairs`、`POST /agent/v1/{bills,contracts,estates}`、`PATCH /agent/v1/bills/{id}` 只准 due_date、冪等（`Idempotency-Key`）、失敗注入 `MOCK_FAIL_NEXT_WRITE`、viewer 圈定依 fixture 宣告 | `services/jgb/transport.py`、`fixtures*.py`、新 JSON、`tests/unit/api/*` | 新測試綠、既有替身測試語義保留、audit PASS；R-讀 20 回合 | executor（進行中）→ verifier |
| **W-D** 正本同步 | DSP-038 落 `DECISIONS.md`；requirements R4.4、design 元件 2 stage 表、元件 3 `confirm.request` 列、`jgb2.action` 列（`mcp_only`＋兌現條件改為「Runtime `redeem_pending` 先燒、工具 `assert_redeemed`」逐字）、**資料模型 `agent_confirmation_tokens` 行加 `pending_id`**；帳本 §4 B3 契約補「value 帶 pending_id」；**DSP-042 三件（§0b）**：R3.7 選填鍵措辭、design 元件 4 回應表（`session_expired` 第六鍵、`transcript` 第七鍵）、元件 3 `jgb2.query.repairs` `estate_id`、DSP-041 文字「第六鍵」改「第七鍵」、line-bot 契約 select 列 | `.claude/DECISIONS.md`、`agentic-mcp-orchestration/{requirements,design}.md`、demo 帳本、`mcp-client-contract-line-bot` | 正本文字與 W1–W4 落地規則可逐字對照 | 主 session（裁後） |
| **W1** 入口隔離＋旗標＋健檢 | 新 `ToolSpec.mcp_only: bool`（預設 False）＋ `Identity.entry: Literal["mcp","rest"]` **預設 `"rest"`（fail-closed）**；設 `"mcp"` 的建構點**逐點**：`mcp_facade.parse_identity`（MCP 真身分，`namespaced_identity` 由它衍生故自動繼承）、`union_specs` 的 `_PROBE_IDENTITIES`（建構期決定 `mcp.add_tool` 清單）、`_ToolListFilter` 用的 `call.identity`（來自 `parse_identity`，已含）；其餘建構點（`routers/agent_entry.build_identity`、`health._PROBE_IDENTITY`、`outline.py`、`agent_eval.py`）不帶 ⇒ 預設 `rest`、永不見寫入工具。`_is_visible` 對 `mcp_only` 檢查 `identity.entry=="mcp"`（與 `for_model`／`readonly_view` 正交；Runtime 兌現呼叫維持 `for_model=True`）；`AGENT_WRITE_TOOLS_ENABLED` 讀取（`bootstrap.py`），可見＝旗標 AND stage；health 新旗 `use_mock_jgb_api`、`write_tools_enabled`、**`verifier_observe_only`**（R8）；`USE_MOCK_JGB_API=false` 且 `RealHttpTransport` 憑證空 ⇒ 啟動 raise（S-5） | `tools/registry.py`、`services/agent/identity.py`、`mcp_facade.py`、`routers/agent_entry.py`、`bootstrap.py`、`health.py`、`jgb_system_api.py`／`jgb/transport.py`（只加守門） | unit 三個面各一條、互不代替：(i) `specs_for`：不帶 `entry` 的 `Identity(...)`（含 `health._PROBE_IDENTITY`、`union_specs` 探針形狀）⇒ 無 `jgb2.action.*`；`entry="mcp"`＋旗標開＋stage 達 ⇒ 有；(ii) `tools/list`（`build_mcp_server`）：旗標開 ⇒ 列出、旗標關 ⇒ 不列；(iii) `registry.call(for_model=True)`：REST identity ⇒ NO_MATCH、MCP identity ⇒ 通。健檢旗實得；憑證空 raise 有測試 | security-executor |
| **W2** 決定性確認卡＋表擴欄 | migration（§0-3）；`confirm.py`：`payload.action` 必填（封閉 enum `bill_due_extend`／`repair_create`）、卡由新 `services/agent/confirm_card.py` 依 action 決定性 render、`summary_sha256=sha256(card)`、寫 `pending_id`（表只多這一欄）；`data` 回 `{pending_id, action, payload, card, quick_replies}`（供 Runtime 存進狀態；⛔ 不含 token），`quick_replies` 由 **`confirm.py:confirm_quick_replies(pending_id)`** 產出 `[{"label":…,"value":"confirm_submit:<pid>"},…]`（label／前綴沿用 `CONFIRM_QUICK_REPLY_VALUES`，舊鏈常數不動）；新 `redeem_pending(db, session_id, pending_id)` 單述句 `UPDATE … SET redeemed=true WHERE pending_id=$1 AND session_id=$2 AND redeemed=false AND expires_at>now() RETURNING token, payload_sha256, summary_sha256`（先燒後比對語義不變）；`assert_redeemed(db, token, session_id)`（W4 wrapper 用：`SELECT 1 WHERE token=$1 AND session_id=$2 AND redeemed=true`） | `database/migrations/2026090x_agent_confirmation_tokens_pending_id.sql`、`tools/confirm.py`、新 `confirm_card.py`、**`tests/unit/agent/test_session_confirm_tools_req.py`**（鍵集合斷言更新為 payload 內含 action）、**`tests/integration/agent/test_confirmation_tokens_req.py`**（`summary_sha256` 斷言改對卡文字） | unit：同 payload 同卡；改任一欄 ⇒ 雜湊不符；integration 五條既有（TOCTOU／重放／跨 session／過期／竄改）不退＋新增 redeem_pending／receipt 冪等 | security-executor |
| **W3** Runtime 確認段 | **守門順序**：`run_turn` 開頭 ① `identity.entry != "mcp"` ⇒ 整段不執行（REST 永不兌現）；② `self.readonly_view` ⇒ 整段不執行（影子 fail-closed，DSP-016）；③ 訊息**等值**匹配 `^confirm_(submit|edit|cancel):([0-9a-f]{16})$`（整句、無前後綴；正常對話不可能等值命中）且 `agent_state["pending_confirm"][pid]` 存在 ⇒ 不進模型。submit ⇒ `redeem_pending` → 有列 ⇒ 比對 `payload_sha256`／`summary_sha256` 與狀態內 payload／卡雜湊 → `registry.call(identity, f"jgb2.action.{action}", {"payload", "confirmation_token": token}, for_model=True)` → receipt 存 `pending_confirm[pid].receipt` → `TurnResult.answer` 由 formatter 依 receipt 組（模型不在迴圈）；無列 ⇒ 狀態有 receipt ⇒ 回同一 receipt（R4.3）；否則 `CONFIRMATION_REQUIRED` 固定句。cancel／edit ⇒ `redeem_pending` 燒 token、狀態 `receipt={"cancelled":true}`、不呼叫工具。**確認回合**：模型回合內出現 `confirm.request` 的 `ToolResult.ok` ⇒ 立即結束回合：`TurnResult(kind="ask", answer=data.card 逐字, quick_replies=data.quick_replies)`，模型當回合輸出丟棄、Verifier 不跑（卡是程式產出）；同時把 `{action, payload, card_sha256}` 存 `pending_confirm[pid]`。**token 只在 `run_turn` 內存活**：⛔ 不進 `agent_state`／`state_store`／`TurnResult`／trace／模型上下文（不變量測試：grep 狀態快照與 TurnResult 無 token 字串）。trace／`usage_events` 加 `pending_id`、`receipt_id`（不變量 30 白名單擴充） | `runtime.py`、`state_store.py`（`pending_confirm` 鍵）、`_emit_agent_decision` 白名單、`usage_metering` | integration：正向 2＋反向 5；`TurnResult.answer == confirm_card.render(action, payload)` 且 `sha256(answer) == 表中 summary_sha256`（反例＝採模型輸出會紅）；影子隔離、入口隔離兩條 DB 反證（§1）；token 不出現在 TurnResult／狀態快照 | security-executor |
| **W4** 寫入工具 | `tools/action.py`：`bill_due_extend`、`repair_create`（`scope="write"`、`mcp_only=True`、stage 依 DSP-038）；`registry.register()` 對 `scope=="write"` **強制**包共用 wrapper（S-9）：`assert_redeemed(token, session_id)` 為真才進 handler（token 由 Runtime 行程內傳入；重複執行由 Runtime 的狀態 receipt 擋在前面）、pm 要 `user_id`（S-8）、寫前讀一次確認資源在身分範圍、呼叫 `JGBSystemAPI.agent_patch_bill_due_date`／`create_repair`（demo 只有替身 transport；`Idempotency-Key=token`）、成功 ⇒ 回 receipt（Runtime 存狀態）；失敗 ⇒ 回 `{"error"}` 誠實回錯、不留殘單 | `tools/action.py`、`registry.py`、`jgb_system_api.py`（新方法、⛔ 不碰憑證） | unit：無 token／錯 session／未 redeemed／已有 receipt ⇒ 全擋或回同 receipt；替身 receipt；失敗不留殘單；**`repair_create` 接受父節點分類＋空描述**（line-bot 線③ Q：分類樹涵蓋不到時退回大類、描述留空、照樣開得成單，⛔ 不編葉節點） | security-executor |
| **W5** R-寫實跑 | 劇本 2 正向＋5 反向；帳本 §1 回填 | scratchpad 劇本、帳本 | §1 主驗收 | 主 session → verifier |
| **W6** 口語穩定度（業主 2026-09-08 R5：「完成度需要能夠應付真實用戶操作」） | **先量再修、修在規則層。** (a) 量：`scenarios_w6.json` 12 會話 36 回合，pm 經 `/mcp`、替身後端；指標＝可答題轉人率／資料事實答錯率／明確 ref 反問率／收尾語正確率／p50；基線 r1 52%、r2 48%、r3（Verifier 只觀察）7%（帳本 §1c）。 (b) **W6-b0 重放材料**（前置，`runtime.py`，security-executor W3 交件後）：`_emit_attempt` 紀錄補 `trace_id`、`user_message`、每個 ref 的 `resolved_quote`（解析後引文，⛔ 只在 `AGENT_ATTEMPT_LOG_PATH` 開時寫、預設關、只在替身實例用）；擷取一輪有閘 r4 作為離線重放集。 **W6-b3 Verifier 模式（優先，R8 改裁）**：正式參數 `AGENT_VERIFIER_MODE`（`grounding_observe` 預設／`strict`）：`grounding_observe` ⇒ 引用類拒因只記錄（attempt log＋trace `verifier[]` 保留真判定）不觸發改寫／轉人，機敏類（`SENSITIVE_TOPIC`、`_verify_routes`）照擋、拒兩次轉人只對機敏類；取代 `AGENT_VERIFIER_OBSERVE_ONLY`（拿掉 mock-only raise）；健檢 `verifier_mode`；unit：兩模式下同一組 fixtures 的行為矩陣（機敏案兩模式皆拒；引用案 strict 拒／observe 過且 trace 記真判定）；絆線計數腳本（從 attempts／trace 統計「observe 下若擋會擋且屬真該擋」）。**W6-b1 尺（DSP-039，備援、不排程）**：① 依片段所引用的來源分兩類——**(A) 工具事實片段**（所有 refs 皆 `jgb2:*`）：**值級檢查**，「值」＝封閉擷取樣式：整數／小數（含千分位）、`NT$`／`$` 前綴剝除後的金額、完整日期（`YYYY/MM/DD`＝`YYYY-MM-DD`＝`YYYY.MM.DD` 正規化 `YYYY-MM-DD`）、百分比、≥4 位連續數字當編號、**列舉狀態詞**（該域工具 mapping 的封閉標籤集合，例如帳單 待繳費／已繳費／待對帳、物件 刊登中／已下架、修繕 急迫／非緊急——來源＝`services/jgb/*.py` builder 的標籤表，程式讀取、⛔ 不手抄）；⛔ 部分日期（`8/15`、`8 月 15 日`）不與完整日期等價、⛔ 電話不納入（沿用步⑤ `_PHONE_RE`）、全形數字 NFKC 後同半形；**比對＝正規化後 token 等值，⛔ 非子字串**；片段內任一值不在「該句所引用各行的聯集」⇒ 新拒因 `VALUE_NOT_IN_SOURCE`；**(A) 類不再計算字元涵蓋率**；量詞逐字：每一個參與 ref 仍須各自通過 `min_quote_len` 與 `citable`，每一個參與 ref 的極性都須與片段一致（任一不一致 ⇒ `POLARITY_MISMATCH`）。**(B) 知識正本片段**（任一 ref 為 `outline:*`／`kb:*`／`help:*`，或混引）：維持現行規則不變（事實句須引用、單行涵蓋率、極性、citable）。機敏閘（步⑤ 導流／個資、敏感題轉人）兩類皆不動。 ② `_effective_kind` 定義化：**greeting／closing ＝ 命中封閉語義詞表 `closing_terms`（`config/agent_verifier_rules.json`，一類維護）∧ 無數字 ∧ 未命中 `assertion_terms` ∧ 無 URL ∧ 長度 ≤ `closing_max_chars`**（四條否定條件⛔ 不是充分條件，詞表命中是必要條件）；**question ＝ 命中 `interrogative_terms`（封閉表）∧ 未命中 `assertion_terms`**，句尾「。」允許但非獨立通過條件；不再依賴 `_GREETING_PHRASES`／`_QUESTION_ENDS` 字面。誤殺量測：以 r4 attempts 片段離線跑新舊 `_effective_kind`，列出型別翻轉清單，其中 0 筆含未引用事實斷言。 ③ 新拒因落地面：`output_schema.py` `VerdictReason` 加 `VALUE_NOT_IN_SOURCE`、`VerifierRules` 加 `closing_terms`／`interrogative_terms`／`closing_max_chars`；`config/agent_verifier_rules.json` 新詞表（`rules_sha` 隨之變，健檢／trace 只是顯示新值）；`runtime.py` `_REASON_HINTS` 補該拒因修法提示＋**鍵集合守測**（比照 `_SCHEMA_CAUSE_HINTS`：斷言涵蓋 `VerdictReason` 全部非 SCHEMA 拒因，刪鍵即紅）。 ④ fixtures：`known_fabrications.json` 全拒、`known_good.json` 全放、`known_open.json` 案例數不增（⛔ 不得搬檔）；新增：合併句值全在 ⇒ 過；**工具片段狀態詞錯（來源「待繳費」寫成「已繳費」，數字全對）⇒ `VALUE_NOT_IN_SOURCE`**；知識片段（`outline:*`）改寫散文仍走涵蓋率 ⇒ 既有預期不變；合併句改一值 ⇒ `VALUE_NOT_IN_SOURCE`；「18,000」對「18000」⇒ 過；「18000」對只含「180000」⇒ 拒；「2026/08/15」對「2026-08-15」⇒ 過；「8/15」對「2026-08-15」⇒ 拒；可引用 A＋不可引用 B、內容只出自 B ⇒ `SOURCE_NOT_CITABLE`；A 肯定＋B 否定、句取 B 寫成肯定 ⇒ `POLARITY_MISMATCH`；無數字無 URL 未命中 assertion_terms 的捏造句標 greeting、refs 空 ⇒ `UNCITED_ASSERTION`；greeting 含數字 ⇒ fact；問句句尾「。」含疑問詞 ⇒ question；`split_assertion_across_entries`／`question_with_assertion_in_same_entry` 既有預期不變。 **W6-b2 類別**（`agent_rules.py` 定義句、`conversational_config.py` 受眾固定句）：收尾語＝封閉類別定義句與對應 `kind`（短收尾、不轉人）；轉人固定句依受眾（pm「轉專人」）；「有明確 ref 仍反問」走 ask 政策定義。 (c) 延遲：line-bot 契約 typing 指示；模型 low→medium 以實測「每回合 +N s 對拒答率 −M%」裁。 | 劇本、`runtime.py`（`_emit_attempt`、`_REASON_HINTS`）、`verifier.py`、`output_schema.py`、`config/agent_verifier_rules.json`、`tests/fixtures/agent/known_*.json`、新 `tools/verifier_replay.py`（離線重放，進 repo）、`agent_rules.py`、`conversational_config.py`、line-bot 契約 | **確定性主驗收（W6-b1）**：`tools/verifier_replay.py` 以 r4 attempts（含 resolved 引文）逐筆重放新舊尺，輸出差異表；預期＝「舊拒新過」只含兩類（合併句值全在、無數字 greeting／question），「舊過新拒」＝0，事實無引用與 SCHEMA 仍拒；fixtures 三檔不變量全綠（`self_test` 啟動即證）。**次驗收（實跑）**：同劇本兩輪取合併率，可答題轉人率／反問率不高於 r2、事實答錯 0、禁詞 0；劣化超過 r1↔r2 既有變異（4 pp）即不過。**通過標準（待裁，建議）**：可答題轉人率 ≤20%、資料事實答錯 0、明確 ref 反問率 ≤10%、p50 ≤20 s。security-reviewer（W6-b1 專審）findings 處置進 §5 後、plan-verifier 對 W6-b1 單獨 READY 才派 | 主 session（量、重放腳本）＋**security-executor**（W6-b0／b1）＋executor（W6-b2）→ verifier |

| **W7** 語音進場（STT；業主 2026-09-08「開 W7，先用 gpt-4o-mini-transcribe」；**前置：DSP-041 已裁＋W-D 同步 R3.7／design 元件 4＋security-reviewer findings 進 §5c；缺一不派**） | (1) 新 `services/speech_to_text.py`：`STT_PROVIDER=openai|local|off`（預設 `off`）、`STT_MODEL=gpt-4o-mini-transcribe`、`language=zh`、OpenCC s2twp 轉繁；介面 `transcribe_urls(urls) -> Transcript{text, duration_s, model}` 與 `transcribe_bytes(data, mime)`（真線路品質驗收走這個、不經 URL）；`local` 後補不改介面。(2) **抓檔硬邊界**：`STT_AUDIO_URL_ALLOWLIST` 預設 `["relay.jgbsmart.com"]`（**unit 釘住預設值**）；`urlparse` 後 scheme 必為 https、host 與白名單**等值**（⛔ 子字串／後綴比對）、⛔ IP literal、⛔ 非 443 port、`follow_redirects=False` 顯式（3xx ⇒ `AUDIO_FETCH_FAILED`）、解析後 IP 落私網／loopback／link-local 即拒（DNS rebinding 殘窗明寫取捨）；簽章 URL `exp` 查詢參數先於抓檔預檢（過期 ⇒ `AUDIO_EXPIRED`＝時戳過期，⛔ 非驗簽；`sig` 驗簽待 line-bot 契約）；**硬閘＝bytes**：串流邊讀邊累計、超 `STT_MAX_BYTES`（5 MB）即中止連線 ⇒ `AUDIO_TOO_LARGE`（`Content-Length` 不可信）；秒數 best-effort（DSP-041 業主 2026-09-08 裁 (a)：模型不回 duration；**只在 relay 簽章 URL 帶 `dur` 時驗 ≤60 ⇒ `AUDIO_TOO_LONG`**，否則不擋）；段數在 `_agent_turn` 進場程式層檢查（>3 ⇒ `AUDIO_TOO_MANY`；`registry._validate_value` 順手補 `maxItems` 分支）；**時間預算（與 `agent_turn_timeout_s()`／`_AGENT_TURN_OUTER_MARGIN_S` 的關係寫死）**：`stt_budget = min(STT_MAX_BUDGET_S(預設 15), agent_turn_timeout_s() / 2)`，抓檔＋轉錄合計超過即放棄（`STT_TIMEOUT`）；帶 audio 的回合，內層 `run_turn` 逾時 ＝ `agent_turn_timeout_s() − stt_elapsed`（⛔ 不改外層 margin），保證內層仍先觸發、外層保險不先炸；STT client `max_retries=1`；**配額以 bytes 計**：`STT_BYTES_CAP_PER_HOUR`（預設 60 MB，鍵 `(api_key_id, vendor_id)`，行程內滑動窗，計入已下載 bytes）⇒ `AUDIO_QUOTA_EXCEEDED`（`dur` 可得時另計分鐘供健檢顯示，⛔ 不作閘）；音訊只在記憶體、⛔ 不落地。(3) **`/mcp` `agent.turn` schema**：`message` 改 `minLength 0`（仍 required）；新增 `audio_urls: {type: array, items: {type: string, maxLength 2048}, maxItems 3}`（strict 序列化走 `_openai_strict_parameters` 成 nullable；`_drop_null_optionals` 還原）；`_agent_turn` 早退改為「`message.strip()` 空 **且** `audio_urls` 空 ⇒ `INVALID_INPUT`」；有 audio ⇒ 先轉錄，`message` 空 ⇒ 以 transcript 為回合訊息，否則 `message + "\n" + transcript`；合併後超過 2000 字 ⇒ 截 transcript 至可容納長度（⛔ 不另外送旗標）。回應 `AgentTurnOutput` 加 `transcript: str|null`（第六鍵，DSP-041）；`STT_PROVIDER=off` 且帶 audio ⇒ `AUDIO_NOT_SUPPORTED`；不帶 audio ⇒ 行為與現行逐位元相同、`transcript=null`。(4) **transcript 的紀律（明寫）**：transcript 是使用者自述原文，**不經 Verifier、原樣回顯**給 line-bot（契約 B4：line-bot 端不記整包）；模型答案照常經機敏閘（R8 下機敏類仍擋）；**⛔ transcript 與音訊內容不得出現在 trace／`decision_snapshot`／`usage_events`／log／attempt log**（`"transcript"` 加進 `DECISION_BANNED_KEYS` 與 `FORBIDDEN_OUTPUT_KEYS`；transcript 作為回合訊息會隨 `_append_dialog` 落 `form_sessions.dialog`，與打字訊息同級、接受）——只允許 `audio_bytes`、`audio_seconds`（best-effort）、`stt_model`、錯誤碼；成本走 `openai_cost_tracking` `operation='stt'`（⛔ 不進 `model_breakdown`）；健檢 `stt_provider`、允許主機數／sha、當期分鐘。(5) **REST 入口＝非目標**（demo 只走 `/mcp`；`routers/chat.py` `VendorChatRequest` 加 `audio_urls` 為 ③ 併入時的事）。 | 新 `services/speech_to_text.py`；`services/agent/mcp_facade.py`（`AGENT_TURN_SPEC`、`_agent_turn`、`AgentTurnOutput`）；`services/usage_metering.py`（數值欄）；`docs/guides/deployment/ENVIRONMENT_VARIABLES.md`；line-bot 契約；`tests/unit/agent/test_stt_req.py`（假轉錄器）；`tests/integration/agent/test_stt_real_req.py`（真線路，gate `RUN_REAL_OPENAI=1`）；W-D：requirements R3.7、design 元件 4、`DECISIONS.md` DSP-041 | **unit（假轉錄器，0 次真抓檔）**：預設白名單＝`["relay.jgbsmart.com"]`；白名單外主機／http／IP／非 443／3xx／超大／`dur`>60／>3 段／`exp` 過期 ⇒ 各自錯誤碼且抓檔器 0 次呼叫；**配額**：連續呼叫至 `STT_BYTES_CAP_PER_HOUR` 用罄 ⇒ `AUDIO_QUOTA_EXCEEDED` 且抓檔器／轉錄器 0 次呼叫（正對照：未達配額 ⇒ 正常轉錄）；**逾時兩案（互不代替）**：(i) 假轉錄器耗盡 `stt_budget` ⇒ 回 `STT_TIMEOUT`、`run_turn` 0 次呼叫、`store.save` 不執行；(ii) 假轉錄器耗用 X（0 < X < `stt_budget`）＋假 `run_turn` 掛住永不返回 ⇒ 內層 `TimeoutError` 在總耗時 ≈ `agent_turn_timeout_s()` 觸發、`store.save` 不執行、外層 `wait_for`（`agent_turn_timeout_s()+_AGENT_TURN_OUTER_MARGIN_S`）未觸發（正對照：內層逾時若不扣 `stt_elapsed`，此測試必紅）；空 message＋合法 audio ⇒ 回合以 transcript 進行、回應 `transcript` 等於假轉錄；空 message＋無 audio ⇒ `INVALID_INPUT`；message＋transcript 合併超 2000 ⇒ transcript 被截、總長 ≤2000；`STT_PROVIDER=off`＋audio ⇒ `AUDIO_NOT_SUPPORTED`；`off`＋不帶 audio ⇒ 回應鍵集合＝五鍵＋`transcript=null`、其餘逐位元同現行；**以含特徵字串的假 transcript 跑完回合 ⇒ 該字串不出現在 trace 快照、`usage_events` 序列化、caplog**（正對照：`answer` 出現）；`make audit` 不變量 30 PASS。**擋在 registry／程式層，不是 SDK**（`agent.turn` 為 `facade_only`）。**真線路一次（`transcribe_bytes`，⛔ 不改程式預設白名單；URL 端到端可選：dev 部署值 `STT_AUDIO_URL_ALLOWLIST` 多列本機 https 替身主機）**：素材＝macOS `say -v Meijia -o /tmp/w7.aiff "信義區套房A 熱水器壞了 幫我開單"` 轉 m4a；斷言 transcript 含「信義區套房A」「熱水器」「開單」三詞、`stt_model==gpt-4o-mini-transcribe`、費用 ≤ US$0.01；素材與輸出留 scratchpad、⛔ 不進 repo。URL 路徑以 unit 假抓檔器覆蓋；失敗 ⇒ 停下交裁，⛔ 不放寬白名單。 | W-D ✓（DSP-041、R3.7、design 元件 4 兩句於 2026-09-08 r2 後改齊）→ security-reviewer ✓（§5c）→ plan-verifier r3（業主裁 (a) 後的關閉輪）→ **security-executor**（排在 W1b＋W4 後）→ verifier |

| **W8** LIFF 線經 `/mcp`（R10／R10-c：LIFF 只做入口與呈現、清單點選以機器值 `select:<type>:<id>` 送入；線③④⑤ 28 情境／30 驗收案例由 `/mcp` 承接；前置：DSP-042 裁（§0b）＋W-D 落檔＋security-reviewer（`image_urls`）＋plan-verifier） | 五樣加法：**(1) 清單點選機器值 `select:<type>:<id>`**（R10-c；line-bot 零改動；security-reviewer S8-1～S8-13 處置見 §5d）：第一版 **`type ∈ {bill, contract, repair}`**（`estate`／`meter` 的 ref 在工具層是 keyword 語義，S8-13，補齊後再開；正則同步縮小）；`id` `^[A-Za-z0-9_-]{1,32}$`；Runtime 在進模型前以 `re.fullmatch`（⛔ 不 NFKC、不 strip）攔截、守門同確認段（`entry=="mcp"`、`readonly_view` 不執行）⇒ 封閉表 `_SELECT_TYPE_TO_TOOL={bill:"jgb2.query.bills", contract:"jgb2.query.contracts", repair:"jgb2.query.repairs"}` 與 `_SELECT_DEFAULT_FACE`（各域**最小揭露** face：bills「帳單異常」、contracts「續約」、repairs「修繕進度」；⛔ 不用「簽署排障」——facts 含租客 email／電話，S8-1；unit 釘住兩表鍵集合）⇒ `registry.call(identity, tool, {"face": default, "ref": id}, for_model=True)`（走既有四步：可見性、速率、schema；授權由 JGB API 全權 DSP-011）⇒ 命中 ⇒ **facts 出口再過一次 `_verify_routes`（URL／電話／導流；命中 ⇒ 該回合改回「查無此筆」，⛔ 不遮罩後送）——⚠️ `_verify_routes` 不含 email 樣式，email 面的唯一控制＝`_SELECT_DEFAULT_FACE` 封閉表＋unit 釘住三個 face 的 facts 不含 `@`（S8-1 處置同步改寫）**⇒ 寫槽位 `<type>_ref`（`write_slot` 封閉值域；找不到 COLLECTING 列 ⇒ 仍回 facts、trace 記 `slot_written=false`）、**作廢 `pending_confirm` 中尚無 `receipt` 的待確認筆**（標 `invalidated=true`，兌現時視同不存在 ⇒ `CONFIRMATION_REQUIRED` 固定句；⛔ 不刪已有 `receipt` 的筆——R4.3「重送回同一 receipt」與 runtime「不覆蓋既有 receipt」紀律不變）⇒ `TurnResult.answer`＝facts（程式產出、Verifier 不跑）、`kind=answer`；**dialog 只寫程式摘要**「已提供 <type> <id> 的資料」（⛔ facts 原文不進 dialog，S8-3）；空／不在範圍 ⇒ 固定句「查無此筆」（同一句，⛔ 不洩存在性；缺 `user_id` 致 `_degraded_response` 時 trace 記 violation，S8-12）。trace／`usage_events` 記 `select_type`、`has_ref`（⛔ 不記 id 原值，S8-6）。**已知取捨（契約措辭）**：真人可手打 ⇒ 最壞情況＝查到**整個 role 範圍內**（含其他租客）的資料（pm 單證；S8-10）；若日後對 tenant 開 `agent.turn`，`select:` 須另加雙證＋viewer 圈定。列舉掃描：`RATE_PER_MIN` 60／`AGENT_TURN_CAP` 120 同鍵（全體使用者共用 key，S8-9 接受並明列）。 (2) **照片進場 `image_urls`（2026-09-08 依 line-bot 契約與 security-reviewer S9 重寫；⛔ 與 W7 解耦，抓檔硬邊界由本項建、W7 落地時複用同一模組）**：`agent.turn` 加選填 `image_urls: {type: array, items: {type: string, maxLength 2048}}`（`maxItems` 在 registry 靜默無效 ⇒ 張數在 `_agent_turn` 程式層檢查：**上限 10**（業主 2026-09-08「可以超過三張」「超過五張分批送」），第 11 張起整回合 `INVALID_INPUT`（錯誤碼沿用封閉值域，S9-22 (a)；契約文字改寫為此）。**分批在 chatai 內部**（⛔ 不讓 line-bot 拆回合——第二批接不到同一張卡）：逐張抓檔→縮圖→丟原 bytes（任一時刻記憶體只有一張原檔＋已縮圖集），縮圖後每 **5 張一批**送辨識（多批結果程式合併：分類取信心最高者、`damage_visible` 任一為真即真、候選＝各批分類去重）；時間預算用完 ⇒ 以已處理的張數出卡；截斷告知**只進 facts 與卡外附加段**：Runtime 常數 `IMAGE_PARTIAL_TEXT = "只看了前 {n} 張照片（共 {m} 張）。"`，Runtime 依 `image.status=="partial"` 與 `processed`／`total` 自行組句、接在 `TurnResult.answer` 卡文字之後（同 W8 (3) `hint` 機制：⛔ 不進 `card`／`card_sha256`／dialog；⛔ 不靜默截斷）。**服務端自抓**（line-bot 把檔案存 relay，給 HMAC 簽章網址，chatai 下載）：新 `services/agent/image_fetch.py`（與 W7 共用形狀）——`IMAGE_URL_ALLOWLIST` 預設 `["relay.jgbsmart.com"]`（unit 釘住）；`urlparse` 後 scheme 必 https、host 與白名單**等值**、⛔ userinfo、⛔ IP literal、port ∈ {443, 空}；`httpx.AsyncClient(follow_redirects=False)` 顯式（3xx ⇒ `IMAGE_FETCH_FAILED` 內部碼 ⇒ 該張丟棄）；解析後 IP 落私網／loopback／link-local 即拒（DNS rebinding 殘窗明寫取捨）；簽章 `exp` 查詢參數先於抓檔預檢（過期 ⇒ 丟棄；⛔ 只稱時戳過期、非驗簽——HMAC 金鑰未交付，`sig` 由 relay 自驗，明寫依賴）；**硬閘＝bytes**：串流邊讀邊累計，超 `IMAGE_MAX_BYTES`（5,000,000）即中止連線（`Content-Length` 不可信）；抓回後過 `S3ImageService.validate_format`（staticmethod；MIME＋magic bytes，不符丟棄）→ **`downscale_image(data: bytes, max_px=1024) -> bytes`**（自 `S3ImageService.compress_image` 抽出的**模組級純函式**，⛔ 不需 S3 組態；`compress_image` 改為呼叫它、REST 行為逐位元不變；`services/s3_image_service.py` 列入本項檔案）（≤1024px、去 EXIF——**去 GPS 列為明示驗收**）→ base64 data URL 交 `ImageRecognitionService.analyze_images`（MCP 路徑 `detail` 程式釘 `low`、⛔ 不由 env；`max_retries=1` 顯式；模型 `IMAGE_RECOGNITION_MODEL`，gpt-5 系列需改 `max_completion_tokens`／不傳 temperature——同 runtime 既有處理）。**時間預算**：`image_budget = min(IMAGE_MAX_BUDGET_S(15), agent_turn_timeout_s()/2)` 涵蓋抓檔＋縮圖＋辨識；**預算用罄的唯一映射**：已完成辨識批次 ≥1 ⇒ `status="partial"`（以已處理張數出卡＋`IMAGE_PARTIAL_TEXT`）；0 批完成 ⇒ `status="timeout"`（`run_turn` 一次、answer 逐字 `IMAGE_TIMEOUT_TEXT`、不進模型）；帶圖回合內層 `run_turn` 逾時＝`agent_turn_timeout_s() − image_elapsed`（外層 margin 不動）。**配額**：`IMAGE_COUNT_CAP_PER_HOUR`（預設 200 張／`(api_key_id, vendor_id)`／行程內滑動窗）⇒ 超過回 `RATE_LIMITED`；成本走 `openai_cost_tracking` `operation='image_recognition'`（⛔ 不進 `model_breakdown`；額度看不到 vision 成本＝明列取捨；`_estimate_cost` 改依模型價目表）。**辨識輸出＝決定性驗證後的封閉值**：`damage_type`／`suggested_category` 以分類樹**封閉映射**（沿用 `action._resolve_category` 語義，對不上 ⇒ 缺值 ⇒ 卡上 `UNSPECIFIED_CATEGORY_ZH`）、`suggested_emergency ∈ {1,2}` 否則缺值、`confidence` 夾 [0,1]、`damage_visible` bool；**急迫卡值唯一決定者＝`confirm_card.emergency_status_of`（缺值＝1）**，vision 的預設 2 ⛔ 不得傳播；**`description` 硬規則留空**（vision 自由文字 ⛔ 不進 payload、不上卡、不進 `broken_reason`——照片內文字注入的唯一出口）；辨識結果以 **可引用的工具事實**進模型回合（r1 裁定接線）：`run_turn(identity, user_message, state, *, image: ImageTurnInput | None = None)` 新增具名選填參數（本切片擁有、同一 security-executor）；`ImageTurnInput`（`runtime.py` dataclass，**全封閉值**、⛔ 無模型自由文字）：`status ∈ {"ok","partial","failed","timeout"}`、`facts: str`（程式組句）、`processed: int`、`total: int`、`candidates: tuple[str, ...]`（分類樹節點名，低信心時 ≥2、否則空）、`suggested_category: str|None`（樹內名或 None）、`suggested_emergency: int|None`；**三條程式終止路徑一律由 `run_turn` 產出**（r2 裁 (a)）：`status=="failed"` ⇒ `TurnResult(answer=IMAGE_FAILED_TEXT, kind="answer")`、violation `image_recognition_failed`、經既有 trace 發射與 `_append_dialog`（同 `_finish_confirm_turn` 路徑，⛔ 不進模型）；`status=="timeout"` ⇒ 同上、answer `IMAGE_TIMEOUT_TEXT = "照片處理逾時，請少傳幾張或改用文字描述。"`、violation `image_timeout`；`candidates` 非空 ⇒ **低信心 ask 回合**：`TurnResult(kind="ask", answer=IMAGE_PICK_CATEGORY_TEXT("照片看起來可能是下列分類，請選一個："), quick_replies=[{label: n, value: n} for n in candidates])`、不建 pending、dialog 末則 assistant＝該固定句＋候選名（讓下一回合有前文），trace 照既有路徑；其餘（ok／partial）⇒ facts 進模型迴圈；`run_turn` 內以既有 `wrap_provenance_data("image.recognition", tool_call_id=f"img-{nonce[:8]}", …)` 包裝、`Provenance(source="image:recognition#<序號>", text=facts, citable=True)`，模型引用它的句子可通過 Verifier（驗收 (xii)）；⛔ 不併進 `message`、⛔ 不經 `agent_state`、⛔ 不直接產 `TurnResult`、⛔ 不新增建 pending 路徑（出卡仍走 `confirm.request` ⇒ `_scope_gate_confirm_request` 照常生效，S9-14）；**純照片回合**：`AGENT_TURN_SPEC` `message` 改 `minLength 0`（仍 required）、`_agent_turn` 早退改為「`message.strip()` 空 **且** `image_urls` 空 ⇒ `INVALID_INPUT`」（此兩處由 W8 (2) 擁有，W7 複用不再改；契約照片列同步「message 可空」）；看不出損壞（`damage_visible=false` 或 confidence < 門檻）⇒ facts 明說「照片看不出損壞」、卡上描述留空並明講；**分類樹注入**：`mcp_facade` 閉包 `repair_category_tree()`（形狀同 `open_repairs`，內部 `jgb2_tools._get_api().get_repair_categories()`）以具名參數注入影像段；`build_prompt(category_names=樹內名稱)` 餵樹；取不到樹（None／例外）⇒ `suggested_category` 一律缺值 ⇒ 卡上 `UNSPECIFIED_CATEGORY_ZH`、不回候選（⛔ 影像段不直呼 `JGBSystemAPI`）。**低信心候選**（`IMAGE_CONFIDENCE_MIN = 0.6`，常數）：`confidence < 門檻` 且樹內候選 ≥2 ⇒ **出卡前獨立 ask 回合**（不建 pending）：answer＝程式固定句「照片看起來可能是下列分類，請選一個：」，`quick_replies` ≤3 顆、`label` 與 `value` **皆為分類樹節點名逐字**（純文字、無新機器值文法；line-bot 原字串送回即成為下一回合的分類），⛔ 不含三顆確認鍵；使用者選後下一回合照常出卡（三顆確認鍵逐字＝`confirm_quick_replies(pid)`，無候選鍵）。**bytes 生命週期**：只在記憶體、⛔ 不落地、⛔ 不進 `agent_state`／`form_sessions`／trace／`decision_snapshot`／`usage_events`／log／例外訊息（`image_recognition_service.analyze_images` 的 `logger.error(f"...{e}")` 必改為只記例外類別名，S9-10 熱點）；允許記錄：張數、每張 bytes、縮圖後 bytes、模型名、耗時、內部錯誤碼。**vision 失敗必須可見**：trace violation `image_recognition_failed`＋固定句常數 `IMAGE_FAILED_TEXT = "照片處理失敗，請改用文字描述，或稍後再試。"`（回合以此結束、不進模型）＋健檢 `services/agent/health.py` 新鍵 `image_recognition: {enabled: bool, model: str, failures_1h: int, last_failure_at: str|null}`（`health.py` 列入本項檔案），⛔ 不沿用 REST 的靜默降級。**已知取捨（明列）**：簽章不綁租戶（line-bot 為唯一呼叫端持單一內部 key，綁定由 relay 負責；第二個呼叫端出現即升級 S9-15）；照片經 API 送 OpenAI 依其 API 資料政策（先照現行 REST 路徑，⛔ 不阻擋 demo；zero-retention 設定另列待查）；REST 路徑（`routers/chat.py` `validate_image_urls` 准 http、無白名單、回顯 `image_recognition`）**不在本項範圍**、為另一條信任模型，⛔ 不得混寫。
(3) 出卡前**未結單提示**：schema 工廠 `_jgb2_spec(domain, faces)` 加選填參數 `extra_properties: dict|None`（只有 `repairs` 傳 `{"estate_id": {"type": "string", "maxLength": 32}}`，其餘域逐位元不變、`additionalProperties: False` 保持）；`tools/jgb2.py` `query_repairs` 讀 `args.get("estate_id")` **透傳** `api.get_repairs(role_id=…, user_id=…, estate_id=…)`（`JGBSystemAPI.get_repairs` 本就支援；走 registry，⛔ 不直呼，S8-11；⛔ 只改 schema 不透傳＝S7-11 同型「靜默無效」）；**接線（r2 裁定）**：`mcp_facade` 建 registry 的閉包新增具名注入 `open_repairs`（形狀同 `db_pool`）傳進 `confirm_request(identity, args, *, db_pool, open_repairs)`；`open_repairs(identity, estate_name) -> {estate_id, count, ids} | None` 由閉包實作＝先以 `api.get_estate_status(role_id=identity.role_id, keyword=estate_name)`＋既有 `_resolve_estate` 取唯一列（與 `action.repair_create` 逐字同形；`role_id` 取不到 ⇒ 直接回 `None`、不加提示行；解析不到 ⇒ `None`），再 `reg.call(identity, "jgb2.query.repairs", {"face": "修繕進度", "estate_id": <id>}, timeout_s=<工具逾時>, stage=current_stage(), for_model=False)` 取未結狀態列（⛔ confirm.py 不直呼 `JGBSystemAPI`、不持有 registry）；`open_repairs=None` 或回 `None` ⇒ 不加提示行、卡照出，兌現時走既有「找不到物件」錯誤路徑；`estate_id` 存 `pending_confirm[pid]["estate_id"]`。**提示行在卡外（r2 裁定 (b)）**：`render(action, payload)` 與 `card_sha256` 逐位元不變（DSP-038-2「同 payload 同卡」不動、W2 驗收不動）；提示行「此物件另有未結單 N 張（單號…）」由 `confirm_request` 回傳的 `hint` 欄位帶出，Runtime 只把它接在 `TurnResult.answer` 卡文字之後、⛔ 不進 `card`／雜湊／dialog；取捨明列＝使用者看到的整段比雜湊涵蓋範圍多一行資訊性文字，該行不含任何可兌現內容；按鈕仍三顆（③N；併單由 line-bot 端處理）；(4) 工具 **`dunning.draft`**（read scope、決定性：依近一年逾期次數選語氣等級、回含佔位符模板，⛔ 模板不含阿拉伯數字、⛔ 不經模型改寫）——輸入 `bill_id`（由 `jgb2.query.bills` 取逾期次數／合約滯納金條款）；回應 `{tone_level, template, placeholders}`；(5) **`session_expired`**：`form_sessions` 無 `updated_at`（S8-7）⇒ 過期戳存 state JSON（`agent_state["last_turn_at"]`，經既有 `state_store`）；同 `session_id` 再進且超過 30 分鐘 ⇒ 先 `_close` 舊列（⛔ 不留 COLLECTING 殘列；`pending_confirm` 隨舊列作廢）再 `_start` 新列，回應加選填鍵 `session_expired: true`（第六鍵，§0b DSP-042；非過期回合 false）（③H／⑤H）。 | `mcp_facade.py`（schema／`_agent_turn`／`AgentTurnOutput` 加 `session_expired`／`_jgb2_spec` `extra_properties`）、`runtime.py`（`select:` 攔截段、facet_context→slots、image facts、出卡前查、`pending_confirm` 作廢）、`services/agent/tools/jgb2.py`（`query_repairs` 透傳 `estate_id`）、`services/agent/tools/confirm.py`（接收具名注入的 `open_repairs`、產出卡外 `hint` 欄位；⛔ 不呼叫 `_resolve_estate`／`JGBSystemAPI`、不持有 registry）、`mcp_facade.py` `open_repairs` 閉包（`_resolve_estate` 唯一呼叫點）、新 `services/agent/tools/dunning.py`、`services/agent/state_store.py`（過期戳）、`inputs/demo-scenarios-20260908/liff-30.json`（line-bot §6 案例經 `/mcp`）；**(2) 專屬**：新 `services/agent/image_fetch.py`、`services/image_recognition_service.py`（bytes 入口、log 熱點、模型參數）、`mcp_facade.py`（schema／`message minLength 0`／張數／預算／`repair_category_tree` 閉包）、`runtime.py`（`run_turn` `image: ImageTurnInput` 具名參數與 dataclass、`wrap_provenance_data` 進場、三條終止路徑、`IMAGE_PARTIAL_TEXT`／`IMAGE_FAILED_TEXT`／`IMAGE_TIMEOUT_TEXT`／`IMAGE_PICK_CATEGORY_TEXT`／`IMAGE_CONFIDENCE_MIN`、violations）、`services/s3_image_service.py`（`downscale_image` 抽出）、`services/agent/health.py`（`image_recognition` 鍵）、`tests/unit/agent/test_image_entry_req.py`（假抓檔器）、`tests/integration/agent/test_image_real_req.py`（真線路一次，gate `RUN_REAL_OPENAI=1`）；⛔ 正本與契約在 W-D | **確定性驗收（(1)(3)(5)，各附正對照；落點 `tests/unit/agent/test_select_entry_req.py`、`tests/integration/agent/test_select_entry_req.py`、`tests/unit/agent/test_session_expired_req.py`、(3) 接線與卡外提示行 `tests/unit/agent/test_session_confirm_tools_req.py` 增案）**：(xi) 假 `open_repairs` 注入 ⇒ `confirm.request(repair_create)` 出卡時對它恰 1 次呼叫、回傳 `hint` 非空；正對照＝`open_repairs=None` ⇒ 不加提示行、卡照出、假 `_get_api` 的 `get_repairs` 0 次；閉包 unit：假 `get_estate_status` 記錄參數 ⇒ 必含 `role_id`；正對照＝identity 無 `role_id` ⇒ `open_repairs` 回 `None`、假 `get_repairs` 0 次；(xii) 同 payload 下未結單 0 張與 2 張 ⇒ `card` 與 `card_sha256` 逐位元相同、提示行只出現在 `TurnResult.answer`；既有 `test_session_confirm_tools_req.py`／`test_confirmation_tokens_req.py` 不退；(i) `select:bill:<存在 id>` ⇒ `TurnResult.answer` 逐字＝bills「帳單異常」builder 對該列產出、`kind=="answer"`、模型 0 次呼叫；正對照＝不存在 id ⇒ 固定句「查無此筆」；(ii) `_SELECT_DEFAULT_FACE` 三個 face 對 fixture 全列 facts 逐字不含 `@` 與 `_PHONE_RE` 樣式；正對照＝同列資料以「簽署排障」face 產出含 `@`；(iii) 注入含 URL 的 facts ⇒ 回「查無此筆」；(iv) 回合後 `agent_state["dialog"]` 末則 assistant＝「已提供 <type> <id> 的資料」且不含 facts 任一行；(v) trace 快照與 `usage_events` 序列化不含 id 原值、含 `select_type`／`has_ref`；(vi) 無 COLLECTING 列 ⇒ 仍回 facts、trace `slot_written=false`；(vii) 缺 `user_id` ⇒ 「查無此筆」且 trace 有 violation；正對照＝帶 `user_id` 得 facts；(viii) 出卡→`select:`→重送同一 `confirm_submit:<pid>` ⇒ `CONFIRMATION_REQUIRED` 固定句（作廢）；正對照＝出卡→送出成功→`select:`→重送同一 pid ⇒ 仍回同一 receipt id（R4.3 不變）；(ix) 同 role 兩物件各有未結單 ⇒ 卡上 N 只算該 `estate_id`；正對照＝`query_repairs` 未透傳 `estate_id` 時此斷言必紅；(x) 過期回合 ⇒ `form_sessions` 該 namespaced key 無第二列 `state='COLLECTING'`、回應 `session_expired==true`；正對照＝未過期回合 `session_expired==false`。**次驗收（實跑）**：line-bot 兩份 spec §6 的 30 個驗收案例改寫為 `/mcp` 劇本（帶 `facet_context`／`image_urls`；照片素材合成、放白名單主機或以 `transcribe_bytes` 同款「直接餵 bytes」的測試入口）全跑，盲判「答到／處理到」；不變量：`image_urls` 不落地、不進 log；`dunning.draft` 模板 0 阿拉伯數字（unit）；`facet_context` 帶入值與現查衝突時答案取現查（unit）。 | DSP-042 裁 → W-D → security-reviewer → plan-verifier → **security-executor：(1) `select:` 全段（攔截、face 表、facts 出口複查、槽位、作廢、dialog 摘要、trace 欄位）＋(3) `estate_id` 透傳、`open_repairs` 注入與出卡前查＋(5) expired（`AgentTurnOutput`／`_agent_turn` 過期段／`state_store.py` 過期戳）＋(2) image／facet_context 面**——`mcp_facade.py`／`runtime.py`／`confirm.py` 在任一時點只有這一個擁有者；**executor：(4) dunning（只碰新檔 `tools/dunning.py`＋registry 註冊一行，於 security-executor 交件後派）** → verifier → 盲判 |

先後（業主 2026-09-08「先完成主功能」）：W0 ✓ → W0b ✓ → DSP-038 ✓ → W-D ✓ → W1a＋W2＋W3 ✓（verifier 中）→ **W1b＋W4** → **W5 R-寫** → **W8 LIFF 線經 /mcp**（R10；審查可與 W7 並行）→ W7 語音 → W6-b3 → W6-b2 → W6-b1（備援）。

## 4. 已裁與待裁
- 待裁：DSP-038 三件（§0）。建議全採。**DSP-042 三件（§0b）：已裁全採（2026-09-08），W-D 落檔完成 ⇒ W8 (1)(3)(5) 可派。**
- 已裁：R1–R3（帳本 §1b）。

## 5. security-reviewer 發現處置
| # | P | 處置 | 落點 |
|---|---|---|---|
| S-1 確認鏈斷在 Runtime | P1 | FIX | W3 |
| S-2 卡文字未綁 summary_sha256 | P1 | FIX（程式 render＋雜湊卡文字） | W2／DSP-038-2 |
| S-3 寫入工具／agent/v1 client 不存在 | P1 | FIX（工具＋替身）／DEFER（真簽章 client） | W4／非目標 |
| S-4 替身不支援寫入 | P1 | FIX | W0 |
| S-5 `USE_MOCK_JGB_API` 預設 true 健檢看不見；無憑證靜默呼叫 | P1 | FIX | W1 |
| S-6 REST 無 session 命名空間、token 表無 vendor | P2 | DEFER，緩解＝`mcp_only`（REST 入口 `entry="rest"` 看不到也呼叫不到寫入工具；兌現段只在 MCP 入口觸發） | W1 |
| S-7 REST 預設無認證、受眾自述 | P2 | FIX（`mcp_only`＋`entry`） | W1 |
| S-8 pm 單證對寫入不足 | P2 | FIX | W4 |
| S-9 registry 只驗 token 存在 | P2 | FIX（強制 wrapper） | W4 |
| S-10 jgb2 側無資源粒度 | P2 | DEFER → 需求文 §B′5 已補、交 JGB | 非目標 |
| S-11 無稽核落點 | P2 | FIX（狀態 `receipt`＋trace／usage_events `pending_id`／`receipt_id`） | W3 |
| S-12 先燒後比對是刻意 | P3 | 接受，反向 5 演出 | W5 |
| S-13 token 不可偽造 | P4 | 無事；v2 進一步讓 token 永不離開 DB／行程 | — |
| **新** token 若落 session 狀態＝靜態憑證面（r1 B2 附帶） | P1 | FIX：設計改為以 `(session_id, pending_id)` 兌現、token 只在 `run_turn` 內存活，加不變量測試 | W2／W3 |

### §5b security-reviewer 對 W6-b1（尺兩類化）的發現——**業主 2026-09-08「目前先紀錄，先完成主功能」：全部 DEFER（W6-b1 為備援、不排程）**

| # | P | 一句話 | 處置 |
|---|---|---|---|
| V-1 | P1 | 聯集無 ref 數上限、無單 ref 貢獻下限 ⇒ 多引幾行湊涵蓋（跨 ref 夾帶） | DEFER；啟用時加 `max_union_refs`（建議 3）＋每 ref 貢獻下限 |
| V-2 | P1 | greeting 由整段等值改「命中詞表」⇒「您的合約已經生效，謝謝您。」單片段免引用 | DEFER；啟用時型別判定改逐子句（`_split_clauses`） |
| V-3 | P2 | question 同型放寬（句尾「。」＋含疑問詞） | DEFER；同 V-2 逐子句；`interrogative_terms` ⛔ 不收「您／要／試試」 |
| V-4 | P2 | 中文數字（一萬八）不在值樣式，`sensitive_patterns` 皆 `\d` 起手 | DEFER；⚠️ 一旦擋住 `known_open::nli_not_entailed_extra_condition` 會由開轉擋，需業主裁 |
| V-5 | P2 | 值等值只證「數字在來源某處」不證欄位對應（編號 3357 vs 金額 3,357） | DEFER；驗收語言須寫「值非來源出現＝拒」 |
| V-6 | P1（可達性） | 金額寫「元」即被步① `SENSITIVE_TOPIC` 攔、值級檢查不可達；⛔ 不得為 demo 放寬 `sensitive_patterns`（尺共用、會打穿售前價格閘） | DEFER；記為 R8 觀察模式的已知面：觀察模式下 SENSITIVE_TOPIC 亦不擋（r3 敏感題由模型自行轉人） |
| V-7 | P2 | 部分日期不等價可能因來源側拆整數而失效 | DEFER；兩側共用 longest-match consuming 擷取器 |
| V-8 | P3 | 「無數字」若用 `[0-9]` 會被非 ASCII 數字繞 | DEFER；NFKC 後 Unicode 數字判定 |
| V-9 | P2 | `closing_terms` 不含問候詞 ⇒ 三個 known_good 翻、`self_test` 啟動即紅 | DEFER；詞表須涵蓋問候＋收尾 |
| V-10 | P3 | 所有參與 ref 極性一致比現行嚴；比例反向不在 `negation_terms` | DEFER；列 known_open |
| Q4 | — | **尺共用**（REST／MCP 同一 `agent_runtime.verifier`；影子另建但同規則檔）；`verify()` 無 audience 分支 ⇒ 尺一改售前路徑同步改、探針 55 數字不可直比；分受眾尺無機制、⛔ 不在 `verify()` 內加受眾條件 | 記錄：任何尺變更以凍結題集回歸 prospect |
| Q5 | — | 離線重放需補每 ref 的 `quote`／`citable`／`source`＋`trace_id`；`user_message` 重放不需要（`verify()` 不讀）⛔ 不落地；帶 `quote` 的 sink 須非 mock 即 raise；attempts 檔明文 append 需進 `.gitignore` | 記錄：W6-b0 若啟用照此 |


### §5c security-reviewer 對 W7（語音進場）的發現與處置（2026-09-08）

| # | P | 一句話 | 處置 | 落點 |
|---|---|---|---|---|
| S7-1 | P1 | 本 repo 第一個「伺服器端抓呼叫端 URL」面，無現成白名單 | FIX：hostname 等值＋https＋port 443＋`follow_redirects=False` 顯式＋解析後 IP 落私網／loopback／link-local 即拒；DNS rebinding 殘窗只靠 TLS 主機名壓、明寫取捨 | W7 (2) |
| S7-2 | P3 | 圖片路徑 `validate_image_urls` 放行 http、無白名單（抓檔者是 OpenAI，風險類別不同） | DEFER：backlog（https only＋S3 主機白名單），⛔ 不併 W7 | 非目標 |
| S7-3 | P2 | relay 簽章契約在 repo 0 命中，`sig` 驗不了 | FIX：只做 `exp` 明文過期預檢（`AUDIO_EXPIRED`＝時戳過期，⛔ 不稱驗簽）；`sig` HMAC 演算法與密鑰列 line-bot 契約待定 | W7 (2)、契約 |
| S7-4 | P2 | `gpt-4o-mini-transcribe` 不回 duration、本機無解碼依賴 ⇒ 「≤60 秒」無量測點 | FIX：秒數 best-effort（relay 簽章 URL 若帶 `dur` 則一併驗）；硬閘只留 bytes，串流邊讀邊累計、超即中止（`Content-Length` 不可信） | W7 (2) |
| S7-5 | P2 | 抓檔＋轉錄撞 `AGENT_TURN_TIMEOUT_S` 外層 35 s，失敗時錢已花；SDK `max_retries` 預設 2 | FIX（r2 後措辭）：單一 `stt_budget = min(STT_MAX_BUDGET_S(15), agent_turn_timeout_s()/2)`，超過即 `STT_TIMEOUT` 早退；帶 audio 回合內層 `run_turn` 逾時＝`agent_turn_timeout_s() − stt_elapsed`（外層 margin 不動、內層仍先觸發）；STT client `max_retries=1` 顯式 | W7 (2)(3) |
| S7-6 | P2 | 現有速率無音訊維度（一則語音＝一次工具呼叫；上界 ≈$1.1／小時／key／worker） | FIX（r2 後措辭）：配額以 bytes 計——`STT_BYTES_CAP_PER_HOUR`（預設 60 MB，同 `(api_key_id, vendor_id)` 鍵、行程內滑動窗、計已下載 bytes）⇒ `AUDIO_QUOTA_EXCEEDED`；分鐘只在 `dur` 可得時供健檢顯示、⛔ 不作閘；健檢 `stt_provider`（不致紅） | W7 (2)、health |
| S7-7 | P2 | 「轉錄走既有 PII 閘」不存在（輸入面無閘，`verify()` 不讀 `user_message`） | FIX：措辭＝「transcript 與 `message` 同等待遇（皆無輸入閘）、不經 Verifier、原樣回顯」 | W7 (4) |
| S7-8 | P1 | transcript 會隨 `_append_dialog` 落 `form_sessions`（與打字訊息同級，接受）；但 `DECISION_BANNED_KEYS`／`FORBIDDEN_OUTPUT_KEYS` 無 `transcript` | FIX：兩個封閉集合各加 `"transcript"`（通用改動）；不變量 30 涵蓋 | W7 (4)、`scripts/audit/checks/agent_boundary.py`、`trace_view.py` |
| S7-9 | P3 | `transcript` 回傳＝使用者原話在回應再複製一份 | FIX：契約補「`transcript` 與 `answer` 同級，⛔ 不入 log、不落 LINE 端 DB」 | 契約 |
| S7-10 | P2 | STT 成本進 `model_breakdown` 會把整筆 `est_cost_usd` 清 null（`DEFAULT_PRICING` 無此模型） | FIX：走 `openai_cost_tracking` `operation='stt'`（沿用 `image_recognition_service._record_cost`），⛔ 不進 `model_breakdown` | W7 (4)、`usage_metering` |
| S7-11 | P1 | `maxItems` 在 `registry._validate_value` 不存在，寫了靜默無效 | FIX：段數檢查做在程式層（`_agent_turn` 進場）⇒ `AUDIO_TOO_MANY`；並在 `_validate_value` 補 `maxItems` 分支（通用） | W7 (3)、`registry.py` |
| S7-12 | P1 | `message` 空被兩道擋（schema `minLength 1`＋`_agent_turn` 早退） | FIX（v2 已寫）：兩處同改＋unit 釘第二道 | W7 (3) |
| S7-13 | P2 | `agent.turn` 是 `facade_only`，strict 序列化走不到；MCP 面 `array` 映裸 list | FIX：schema 照寫，驗收語言＝「擋在 registry，不是 SDK」 | W7 驗收 |
| S7-14 | P2 | `AgentTurnOutput` 第六鍵逾越 R3.7 | FIX：DSP-041 已裁、W-D 已同步 | DECISIONS／R3.7／design |
| S7-15 | P2 | 真線路不需放寬白名單、也不該寫程式特例；`USE_MOCK_JGB_API` 預設 true 不能當閘 | FIX：白名單就是部署值——dev 的 `STT_AUDIO_URL_ALLOWLIST` 可多列本機 https 替身主機、prod 只有 relay；健檢印允許主機數／sha；程式預設值不變（unit 釘住） | W7 驗收、health |

### §5d security-reviewer 對 W8 (1)(3)(5) 的發現與處置（2026-09-08）

| # | P | 一句話 | 處置 | 落點 |
|---|---|---|---|---|
| S8-1 | P1 | `select:contract:` 若選「簽署排障」face，facts 含租客 email／電話明文；繞過模型即無 Verifier 擋 | FIX：預設 face 封閉表選最小揭露＝**email 面唯一控制**（unit 釘住三個 face 的 facts 不含 `@`）；facts 出口再過 `_verify_routes` 只涵蓋 URL／電話／導流（⚠️ 無 email 樣式，r1 指出）（命中改「查無此筆」） | W8 (1) |
| S8-2 | P1 | 各域預設 face 未定＝揭露面未定 | FIX：`_SELECT_DEFAULT_FACE` 封閉表＋unit 釘住 | W8 (1) |
| S8-3 | P2 | facts 以 assistant 身分進 dialog＝第三方文字進歷史 | FIX：dialog 只寫程式摘要 | W8 (1) |
| S8-4 | P2 | 工具名複數（bills）與 `<type>` 單數不對應 | FIX：`_SELECT_TYPE_TO_TOOL` 映射表＋正對照驗收 | W8 (1) |
| S8-5 | P2 | `meter_ref` 不在 `SlotKey` 值域 | FIX：第一版不開 `meter` | W8 (1) |
| S8-6 | P2 | `select_ref` 進 trace 違反「不記 ref 原值」 | FIX：只記 `select_type`／`has_ref` | W8 (1) |
| S8-7 | P2 | `session_expired` 依不存在的 `updated_at`；過期換新留 COLLECTING 殘列 | FIX：過期戳存 state；過期先 `_close` 再 `_start` | W8 (5) |
| S8-8 | P3 | 整句等值應 `fullmatch`；⛔ 不 NFKC | FIX | W8 (1) |
| S8-9 | P3 | 列舉掃描：全體共用 key 的每分 60／每小時 120 | 接受並明列 | 契約 |
| S8-10 | P3 | 契約「最壞情況」偏窄——pm 單證＝整個 role 範圍 | FIX：契約改寫；tenant 開放前提列出 | 契約 |
| S8-11 | P2 | 未結單提示無可用參數，照字面只能繞過 registry | FIX：`jgb2.query.repairs` 加 `estate_id` 走 registry | W8 (3) |
| S8-12 | P3 | 缺 `user_id` 時 `get_repairs` 降級成空、無聲 | FIX：驗收正對照＋violation 記錄 | W8 (1)(3) |
| S8-13 | P3 | `select:estate:`／`select:meter:` 的 ref 被當 keyword 送 | FIX：第一版只開 bill／contract／repair | W8 (1) |
## 6. 回退、預算、停止
- 回退：旗標關 ⇒ 工具不可見、兌現段不觸發（REST 本就不觸發）；migration 可逆（新欄 nullable、`pending_id` 可回填）；替身狀態行程級。
- **W7 回退**：`STT_PROVIDER=off`（預設）＋不帶 `audio_urls` ⇒ `agent.turn` 行為逐位元同現行（回歸測試釘住）；移除 `audio_urls` 鍵與 `transcript` 欄即完全回退，無 DB 變更。**W7 預算**：security-executor ≤2 次交付；真線路轉錄呼叫 ≤5 次、費用 ≤ US$0.05；verifier 1。**W7 停止**：需放寬預設白名單或關閉 https／重導向檢查才能過驗收 ⇒ 停下交裁；DSP-041 未裁 ⇒ 不開工；無合法真線路素材 ⇒ 真線路驗收標 INCONCLUSIVE 交裁、⛔ 不以 URL 路徑替代。
- **W8 回退**：`select:` 攔截段與 `session_expired` 鍵移除即逐位元回退（無 DB schema 變更；`_jgb2_spec` 的 `extra_properties` 預設 None ⇒ 其餘域不變）；**已知不可逆面**＝(5) 過期時 `_close` 把舊列 `state` 改 `COMPLETED`（既有 `_close` 語義），回退後已關的列不復原——取捨：過期列本就不該再續、demo 期接受；`pending_confirm` 作廢只標記不刪，可回復。**W8 預算**：security-executor ≤4 次交付（(1)(2)(3)(5) 同一擁有者、可分批但同檔不跨批平行）、executor ≤1 次（(4)，序列化在 security-executor 之後）；verifier 1；盲判 1 輪（30 案例）。**W8 停止**：DSP-042 未裁 ⇒ 不開工；需放寬 `_SELECT_DEFAULT_FACE`（露出 email／電話）或放寬 `_verify_routes` 才能過驗收 ⇒ 停下交裁；確定性驗收 (i)–(x) 任一紅 ⇒ 不進次驗收；盲判線③ 12 案「整條走完」＜8 或 forbid 命中 >0 ⇒ 不宣稱 done。
- 預算：W1 1 security-executor；W2–W4 1 security-executor（≤3 次交付）；W0 verifier 1、W1–W4 verifier 1；plan-verifier r2 為關閉輪。
- 停止：W0 verifier REFUTED（已發生 → W0b）；DSP-038 未裁；任一 P1 處置落不下；R-寫 正向兩條任一不過即不宣稱 done；W6 通過標準未裁不得宣稱「可應付真實用戶」。

## 7. plan-verifier r1 處置
| r1 | 處置 |
|---|---|
| B1 `facade_only` 非 REST/MCP 邊界、與 W3 互斥 | FIX：新 `mcp_only`＋`Identity.entry`，與 `for_model` 正交；入口隔離驗收獨立一條 |
| B2 token 到 Runtime 無人擁有；落 session 狀態＝新憑證面 | FIX：token 不離開 DB；`redeem_pending(session_id, pending_id)` 取回、行程內交工具；W2 擁有表擴欄與函式、W3 擁有取用；不變量測試 |
| B3 重送語義矛盾（R4.3） | FIX：依 R4.3 回同一 receipt，`receipt` 欄（migration）；反向 2 唯一預期 |
| B4 改簽名打破測試與 R4.2 | FIX：簽名不變、`payload.action`；受影響兩測試檔列入 W2；語義變更入 DSP-038-2 |
| B5 DSP-038 未裁卻是 W1 前置；正本無人同步 | FIX：§0 前置、W-D 切片（主 session） |
| B6 機器值無生產者、與常數衝突 | FIX：`confirm_quick_replies(pending_id)` 在 W2，沿用常數當 label／前綴；line-bot 契約 B3 在 W-D 補 |

## 9. plan-verifier W6-b1 r1 處置（2026-09-08）
| r1 | 處置 |
|---|---|
| 尺放寬未過 security-reviewer、擁有者矛盾 | FIX：security-reviewer 專審（進行中，findings 進 §5 落點 W6-b1）；擁有者改 security-executor |
| 聯集量詞未定（citable／極性繞道） | FIX：量詞逐字——聯集只放寬涵蓋與值；每個參與 ref 各自過 `min_quote_len`／`citable`、極性全一致 |
| greeting 三否定條件當充分條件 | FIX：`closing_terms` 封閉詞表為必要條件＋長度上限；fixtures 加 greeting 形捏造句 |
| question 規則二義、已出貨 fixture 翻轉 | FIX：question ＝ `interrogative_terms` ∧ ¬`assertion_terms`；`split_assertion_across_entries` 預期不變列入驗收；誤殺量測用 r4 片段離線跑 |
| 新拒因落地面缺（`_REASON_HINTS` 靜默空提示） | FIX：範圍補 `output_schema.py`／rules json／`runtime.py`；`_REASON_HINTS` 鍵集合守測 |
| 「值」與比對語義未定 | FIX：封閉擷取樣式＋正規化＋token 等值；部分日期不等價；電話沿用步⑤ |
| 驗收靠 LLM 變異 | FIX：W6-b0 補 resolved 引文進 attempts、r4 為重放集；`tools/verifier_replay.py` 確定性主驗收；實跑改次驗收＋比較協定 |

## 8. plan-verifier r2 處置
| r2 | 處置 |
|---|---|
| B1 卡文字未成為使用者答案 | FIX：W3「確認回合」——`TurnResult.answer` 逐字＝`data.card`，模型輸出丟棄、Verifier 不跑；integration 斷言 `sha256(answer)==summary_sha256` |
| B2 影子回合會兌現 | FIX：W3 守門 ②（`readonly_view` ⇒ 整段不執行）＋影子隔離 DB 反證 |
| B3 `mcp_only` 管不到兌現段；REST 可冒 namespace | FIX：W3 守門 ①（`entry!="mcp"` ⇒ 整段不執行）；入口隔離驗收改為 DB 反證（列 `redeemed=false`） |
| B4 `Identity.entry` 無預設、建構點不全、可見面未拆 | FIX：預設 `"rest"`；設 `mcp` 的點逐列（`parse_identity`、`union_specs` 探針、`_ToolListFilter` 繼承）；驗收拆 `specs_for`／`tools/list`／`call` 三面 |
| B5 表存 payload 原文反轉「只存雜湊」 | FIX（改設計）：表只加 `pending_id`（雜湊）；`action`／`payload`／`receipt` 進 session 狀態（DSP-038-4，含保留取捨）；W-D 補資料模型行與 `jgb2.action` 列 SQL |

## 10. plan-verifier W7 r1 處置（2026-09-08）
| r1 | 處置 |
|---|---|
| 無 security-reviewer findings | FIX：專審進行中 → §5c；W7 列加「findings 進 §5c 後才派」前置 |
| `message minLength 1` 矛盾、`transcript_truncated` 無落點 | FIX：`minLength 0`＋`_agent_turn` 早退改「兩者皆空才 INVALID_INPUT」；超長截 transcript、不送旗標 |
| R3.7／design 正本變更無 DSP、無擁有者 | FIX：DSP-041＋W-D 同步（主 session）為前置 |
| REST 落點符號不存在 | FIX：REST 改非目標（`VendorChatRequest` 留 ③ 併入） |
| 真線路驗收有放寬白名單暗門 | FIX：品質驗收走 `transcribe_bytes`（不經 URL）；URL 路徑 unit 假抓檔器；預設白名單 unit 釘住；放寬即停 |
| 「log 無音訊以外內容」語義反向 | FIX：改為正向禁止句＋特徵字串測試＋不變量 30 |
| 「轉錄走既有 PII 閘」不存在 | FIX：明寫 transcript 不經 Verifier、原樣回顯；答案側機敏閘不變 |
| §6 無 W7 | FIX：補回退／預算／停止 |

## 11. plan-verifier W7 r2 處置（2026-09-08，業主裁 60 秒 (a) best-effort）
| r2 | 處置 |
|---|---|
| STT 預算撞外層 35 s、內層不先觸發 | FIX：`stt_budget=min(15, timeout/2)`；內層 `run_turn` 逾時＝`timeout − stt_elapsed`；驗收加逾時順序 unit |
| design 元件 4 兩句未改 | FIX：「schema 只收 message」「語音走 REST SSE／voice-turn-budget」改為 DSP-041 措辭 |
| 60 秒硬限 vs 不可量測；契約缺兩碼 | FIX（業主裁 (a)）：best-effort、只在 `dur` 可得時驗；契約／DSP-041 對齊；補 `AUDIO_TOO_MANY`／`AUDIO_QUOTA_EXCEEDED` |
| 分鐘配額無計量基礎 | FIX：改 `STT_BYTES_CAP_PER_HOUR`；驗收加配額用罄案例 |

## 12. plan-verifier W7 r3 處置（2026-09-08）——**W7 審查暫停（PAUSED_VERIFICATION，三輪）**：兩條皆文字同步（§5c S7-5／S7-6 改為 r2 後措辭；逾時驗收拆 (i)(ii)）已改；依「先完成主功能」W7 排在 W1b＋W4、R-寫 之後，屆時開最後一次 fresh review 再派。

## 13. plan-verifier W8 r1 處置（2026-09-08）
| r1 | 處置 |
|---|---|
| DSP-042 內容全無、正本落在程式擁有者 | FIX：新增 §0b 三件（`session_expired` 第六鍵＋R3.7 措辭、`select:` 契約值域、落檔清單）；W-D 範圍補 DSP-042 五項；W8 範圍欄移除正本；§4 補待裁；DSP-041「第六鍵」改「第七鍵」列入 W-D |
| 驗收無可推翻檢查 | FIX：W8 驗收欄補確定性 (i)–(x)（各附正對照＋測試檔落點），30 案例盲判降為次驗收 |
| `_jgb2_spec` 共用工廠、`query_repairs` 不透傳、`estate_id` 來源未寫 | FIX：`extra_properties` 只對 repairs；範圍補 `tools/jgb2.py` 透傳；來源＝出卡時 `_resolve_estate(payload["estate_name"])` 存 `pending_confirm[pid]["estate_id"]`；驗收 (ix) 正對照 |
| `_verify_routes` 無 email 樣式 | FIX（擇 (b)）：email 面唯一控制＝封閉 face 表＋unit (ii)；§5d S8-1 同步改寫；⛔ 不動 `verifier.py` |
| 清 `pending_confirm` 與 R4.3 衝突 | FIX：只作廢尚無 `receipt` 的筆（`invalidated=true`），驗收 (viii) 雙向 |
| (1)(3) 無擁有者 | FIX：擁有者欄逐項對應，(1)(2)(3) security-executor、(4)(5) executor |
| §6 無 W8 | FIX：補回退（含 `_close` 不可逆取捨）／預算／停止 |

## 14. plan-verifier W8 r2 處置（2026-09-08）——**兩輪自動 REVISE 已達上限；本輪逐條裁定後只開一次關閉審查（r3）**
| r2 | 處置 |
|---|---|
| `confirm.py` 取不到 registry／stage／timeout，S8-11「走 registry」無接線 | FIX：閉包具名注入 `open_repairs`（形狀同 `db_pool`），閉包內以 `_resolve_estate` 取 id、`reg.call(jgb2.query.repairs, estate_id, stage=current_stage())`；驗收 (xi) |
| 提示行與 DSP-038-2「同 payload 同卡」／`card_sha256` 相衝 | FIX（裁 (b)）：提示行在卡外、由 `hint` 欄位帶出接在 answer 之後、⛔ 不進 card／雜湊／dialog；取捨明列；驗收 (xii) |
| `mcp_facade.py` 同檔雙擁有者 | FIX：(5) 併入 security-executor，executor 只做 (4) 新檔且序列化在後；預算改 ≤4／≤1 |

## 15. plan-verifier W8 r3 處置（2026-09-08）——**W8 審查暫停（PAUSED_VERIFICATION，三輪）**
| r3 | 處置 |
|---|---|
| 範圍欄殘句「confirm.py 出卡時 `_resolve_estate`」與 (3) r2 裁定矛盾 | FIX（文字）：範圍欄改為 confirm.py 只收 `open_repairs`／出 `hint`，`_resolve_estate` 唯一呼叫點＝`mcp_facade` 閉包 |
| 閉包 `get_estate_status` 缺 `role_id` ⇒ 跨 role 解析 | FIX（文字）：接線句加 `role_id=identity.role_id`，取不到回 `None`；驗收 (xi) 補閉包 unit＋正對照 |

兩條皆已改字；業主 2026-09-08「等你指示再開下一輪?」⇒ 開 r4（業主指示續審）：**READY**。W8 (1)(3)(5) 開工前置只剩：DSP-042 業主裁（§0b 三件）→ W-D 落檔 → security-executor。(2) image_urls 仍待 security-reviewer 專審；(4) dunning 序列化在後。

**W8 (1)(3)(5) 完成（2026-09-08）**：DSP-042 裁＋W-D `ace24b46` → security-executor 交件 `b86e7fde`（第一次派工停擺 600 s 重派）→ verifier **CONFIRMED**（unit 1341／integration 35／audit 只紅不變量 3；A1–A4 見帳本 §1h）→ 後續修正 `3bf28e79`（未知 pid 固定句，實跑 L3-H 發現）→ 窄範圍 verifier r2。取捨（執行者列）：unit 檔名 `test_select_entry_unit_req.py`（basename 撞 integration）；`slot_written` 進快照白名單 18→21；`_verify_routes` 缺席 fail-closed；缺 `user_id` 記 violation 交下游閘；hint 張數受 `JGB2_CANDIDATE_CAP`；ref id 進 dialog 摘要不進 trace。剩：(2) image_urls（security-reviewer 專審 → security-executor）、(4) dunning.draft（executor，序列化在後）。

## 16. 切片 L15：答案層會話邊界三分（業主 2026-09-08「先做 L15」；帳本 §1h／§3 L15）

**結果**：line-bot 線⑤ L5-C／L5-J／L5-A／L5-K 四案改判「答到／正確處理」，W6 36 回合與 R-讀 20 回合不退；線③ 12/12 出卡不退。

**三件，各自一層，⛔ 不寫例子只寫定義**：

| # | 病灶 | 層 | 做法 | 驗收（正對照） |
|---|---|---|---|---|
| (a) 別戶邊界 | 由清單進場（`select:` 命中）後問別戶，模型整包回答（L5-C）；正本 C/followup-session-single-item-boundary：清單進場只看那一戶、問別戶退出並指路；聊天直接進場可切換（⛔ 不動） | **程式判定，⛔ 不交模型**（`feedback_no_llm_mechanical_decode`）：戶＝`estate_id` 等值（bills／contracts／repairs 列都有 `estate_id`，封閉集合） | **（本格為 r1 後定稿，§16b 各條已併入）** ① `tools/jgb2.py`：`_ok_single(domain, tag, facts, cap, *, estate_id: str|None=None, scoped: bool=False)`；**只在實體列**呼叫點傳 `scoped=True`＋`estate_id=str(row["estate_id"])`（bills／contracts／repairs 實體列；estates 列用 `str(row["id"])`；meters 列用 `str(row["estate_id"])`）⇒ `data["scope"]={"estate_id": <str|None>}`；**不帶 scope 鍵**（封閉例外）：`repairs face="修繕分類"` 靜態樹、accounts 域、estates sentinel（`found=False`）、任何候選清單（`_ok_candidates`）。② `runtime.py` `_run_select_segment`：**每個** `select:` 回合先寫 `agent_state["select_scope"]`（命中且列有 estate_id ⇒ `{"type", "estate_id": str}`；失敗／缺值 ⇒ `None`）再走任何早退。③ **Runtime 模型迴圈**：`registry.call` 回 `ToolResult` 後、`_wrap` 前，若 `agent_state["select_scope"]` 非 None 且工具名以 `jgb2.query.` 開頭：(3a) 結果 `data` 有 `scope` 鍵 ⇒ `str(scope.estate_id)` ≠ scope ⇒ **範圍外**；`scope.estate_id is None` ⇒ 範圍外＋violation `select_scope_unknown`（fail-closed）；(3b) 工具名 ∈ 封閉清單 {`jgb2.query.bills`, `jgb2.query.contracts`, `jgb2.query.repairs`, `jgb2.query.meters`（比 `estate_id`）, `jgb2.query.estates`（比 `id`）} 且 `data.candidates` 為 list ⇒ Runtime 以 `str(...)==scope` 過濾（其餘域如 accounts 的候選⛔ 不過濾、不比對），過濾後非空 ⇒ 以 `tools.jgb2._candidates_text(domain, query, rows)` 重繪 `text_for_model` 與 `provenance[0].text`、`data.candidates` 換成過濾後列；為空 ⇒ 範圍外；(3c) 無 scope 鍵且非候選 ⇒ 不比對。**範圍外的替換**＝同一個 `ToolResult` 物件改為 `ok=True, data={"facts":"","candidates":None,"skip_refine":True}, provenance=[], text_for_model=SCOPE_TOOL_TEXT`（常數「（這一筆不在本對話的範圍內）」），violation `select_scope_exit`；替換後那一份寫入 `tool_results_by_id[tc.id]` 並經 `_wrap` 進 messages（⛔ 原 facts 不進 messages／provenance／trace）。回合計數 `scope_in`／`scope_out`。④ **接句點唯一**：模型迴圈產出的每一個 `TurnResult`（正常答案、模型自判 handoff、`_build_fixed`）在 `_finalize` 之前經 `_apply_scope_exit(result)`：`scope_out>0 and scope_in==0` ⇒ 整個答案改為 `SCOPE_EXIT_TEXT`、`kind="answer"`、`handoff=None`（⛔ 不進 handoff cache，因 final_kind 非 handoff）；`scope_out>0 and scope_in>0` ⇒ `answer = answer.rstrip() + "\n" + SCOPE_EXIT_TEXT`；否則不動。dialog 存接句後的 answer（與使用者所見一致）。⑤ **固定句**：`runtime.py` 模組常數 `SCOPE_EXIT_TEXT = "這個對話只看你點選的那一戶；要查別戶請回清單點那一戶。"`（與 `SELECT_NOT_FOUND_TEXT` 同處），單一句、對所有受眾一體適用（tenant 現無 `agent.turn` 入口）。⑥ **寫入路徑**（L15-03）：`mcp_facade._open_repairs` 改為物件解析成功即回 `{"estate_id": str, "count", "ids"}`（`count` 可為 0）、只有解析不出物件才回 `None`；Runtime `_begin_pending_confirm` 有 `select_scope` 時——`repair_create`：`data.estate_id` 非 None 且 ≠ scope ⇒ 不建 pending、回 `SCOPE_EXIT_TEXT`；`None`（解析不出）⇒ 放行出卡（執行時同一支 `_resolve_estate` 必 NO_MATCH，跨戶寫入不可能）；`bill_due_extend`：邊界依 L15-08＝**物件**——Runtime 以 `registry.call(identity, "jgb2.query.bills", {"face": _SELECT_DEFAULT_FACE["bill"], "ref": str(payload.bill_id)}, for_model=False)` 取 `data.scope.estate_id`（結果只讀 scope、⛔ 不進 messages）；≠ scope 或 None ⇒ 不建 pending、固定句（fail-closed）；同物件不同帳單 ⇒ 放行。⑦ 換一筆 `select:` ⇒ ② 覆蓋；會話過期 ⇒ 舊列關閉、scope 隨之消失；L15-04 (A)：select 後聊天問別戶 ⇒ 同 ③④。⛔ 不改契約（line-bot 零改動）、⛔ 不加 trace 新鍵（只用 violations） | 見本節「§16 修訂後範圍」的確定性驗收 (i)–(xvi)（唯一驗收清單；本格不另列） |
| (b) 同戶跨類指路 | 一句兩題（帳單＋合約）答了帳單就反問或漏（L5-K）；合約以帳單編號當 keyword 查不到 | 契約層（工具描述＝定義）＋規則層（定義句） | ① `mcp_facade._jgb2_spec` description 依域補一句定義：contracts「keyword 是物件名稱或承租人名；帳單編號查不到合約，同戶合約先用該帳單的物件名稱查」；bills「keyword 是物件名稱」（其餘域不動）；② `agent_rules._POLICY_TEXT_NON_PROSPECT`【判準】加一條：「一句多題：能查到的先答完，查不到的那一題明說查不到並指路，⛔ 不因一題查不到而整句反問」 | unit：description 含該句（契約守測）；規則文本含該句；L5-K 實跑答到合約到期日；W6「一句兩意圖」既有案不退 |
| (c) 自述數字以現查為準 | 「清單寫 12 天」被反問（L5-J，原始輪照抄） | 規則層（定義句） | `_POLICY_TEXT_NON_PROSPECT`【判準】加一條：「使用者自述的數字（清單上看到的天數、金額、日期）不是查詢條件也不是答案；一律以工具現查為準，不一致時明講兩者」 | unit 規則文本含該句；L5-J 實跑算出 78 天並明講與 12 天不一致；`known_fabrications` 不退 |

**範圍（檔案）**：`services/agent/tools/jgb2.py`（`_ok_single` scope）、`services/agent/runtime.py`（`select_scope`、迴圈後比對、`SCOPE_EXIT_TEXT` 取受眾固定句）、`services/agent/agent_rules.py`（兩定義句）、`services/agent/mcp_facade.py`（兩域 description）、受眾固定句所在檔（`conversational_engine` 的固定句表或 `agent_rules`，以現況為準）、新 `tests/unit/agent/test_select_scope_req.py`、既有 rules／spec 守測。
**非目標**：聊天進場的別戶限制（正本說可切換）；tenant；模型判「同戶」。
**擁有者**：(a) security-executor（跨戶資料邊界）；(b)(c) 同一交付（同檔 `runtime.py`／`mcp_facade.py` 單一擁有者）。
**回退**：移除 `select_scope` 存取與比對段即回退；description／規則句為文字。**預算**：security-reviewer 1、plan-verifier ≤2、security-executor ≤2 次交付、verifier 1。**停止**：(a) 若必須讓模型判戶才能達成 ⇒ 停下交裁；L5-C 仍答別戶且 (a) 已落地 ⇒ 查 `estate_id` 來源而非放寬。

### §16b security-reviewer 對 L15 的發現與處置（2026-09-08）

| # | P | 一句話 | 處置 | 落點 |
|---|---|---|---|---|
| L15-01 | P2 | 候選清單路徑（無 ref／keyword 的 `fetch_default`）不帶 scope，整個 role 的列連金額進 `text_for_model`——正是 L5-C 的漏 | FIX：有 `select_scope` 時，bills／contracts／repairs 的候選列**先以 `estate_id` 等值過濾再組文字**；過濾後為空 ⇒ 視同範圍外（同 (a)③ 替換規則） | (a)①③ |
| L15-02 | P2 | estates／meters 不在邊界 ⇒ 由清單進場可讀別戶物件／電錶 | FIX：estates 以列 `id`、meters 以列 `estate_id` 進 `scope`（兩處 `_ok_single` 呼叫點都有值） | (a)① |
| L15-03 | P2 | 寫入路徑繞過：`_open_repairs` 解任意 `estate_name`、提示行洩別戶未結單；`bill_due_extend` 可延別戶帳單 | FIX：Runtime `_begin_pending_confirm` 有 `select_scope` 時——`repair_create` 比對 `data.estate_id`、`bill_due_extend` 比對 `bill_ref` 槽位＝payload `bill_id`；不等 ⇒ 不建 pending、回範圍固定句 | (a)⑤（新） |
| L15-04 | P2 | scope 釘住整段對話（`session_id` 契約＝整段對話），select 之後聊天式切換別戶也被擋，與正本「聊天進場可切換」在同一 session 內衝突 | **已裁（業主 2026-09-08）(A)**：session 級釘住（line-bot 零改動；再點清單即覆蓋 scope；聊天要換戶＝回清單點）；驗收加「select 後聊天問別戶 ⇒ 範圍固定句」；否決 (B) 每筆清單新 `session_id` | (a)④、驗收 |
| L15-05 | P2 | select 失敗／回傳無 estate_id 時舊 scope 殘留 | FIX：每一個 `select:` 回合**先**寫 `select_scope`（失敗＝None）再走任何早退 | (a)②④ |
| L15-06 | P2 | 列缺 `estate_id` 時靜默 fail-open | FIX：有 scope 而單列無 `estate_id` ⇒ **fail-closed**（視同範圍外）＋violation `select_scope_unknown`；停止條件：demo 資料若合法缺值 ⇒ 停下交裁 | (a)③ |
| L15-07 | P3 | int／str 不等值；`_ok_single` 拿不到列 | FIX：兩側 `str()`；`_ok_single(..., estate_id: str|None=None)` 明確參數；unit 混 int／str | (a)① |
| L15-08 | P3 | 邊界＝物件（estate）而正本說「那一筆／其他租客」；同物件歷史合約仍可讀；`簽署排障` face 在模型迴圈可達 | **已裁（業主 2026-09-08）邊界＝物件**：同一物件的帳單／合約／修繕（含歷史）都可追問；正本 C/followup-session-single-item-boundary 補「戶＝物件」（version 2026-09-08.4）；`簽署排障` 列 S8-1 已知面 | (a)、正本 |
| L15-09 | P3 | (a)「立即結束」與 (b)「能答的先答」相衝；contracts keyword 放寬重查會把鄰戶單列命中變整回合退出 | FIX：範圍外工具結果**不結束回合**，改以程式固定工具訊息「（該筆不在本會話範圍）」替換（無 facts）、記 violation；回合結束時若有任一替換 ⇒ 程式在答案末尾接指路固定句；整回合全為範圍外 ⇒ 只剩固定句。unit 兩方向各一 | (a)③ 改寫 |
| L15-10 | P3 | (c) 句禁止用自述數字當查詢條件，連編號也被禁 | FIX 措辭：識別碼（帳單／合約／修繕／物件編號）可當 ref／keyword；數值（天數、金額、日期）不是證據、一律現查 | (c) |
| L15-11 | P3 | 新 trace 鍵 `scope_exit` 撞白名單守測（兩檔不在範圍） | FIX：不加新鍵，只用 `violations += ["select_scope_exit"]` | (a)③ |
| L15-12 | P3 | 呼叫方要機器可讀 `scope_exit` 回合狀態鍵 | DEFER：輸出鍵另切片（第八鍵，依 §0b 序）；本切片只有固定句＋trace | §2 非目標補列 |
| L15-13 | P4 | 範圍固定句 ≠「查無此筆」＝同 role 內存在性揭露 | ACCEPT：同憑證本可讀；unit 釘固定句為常數、無 id／名稱插值 | 驗收 |
| L15-14 | P4 | `select_scope.estate_id` 落 state、violation 無 id | ACCEPT | — |
| L15-15 | P4 | 替身 `_bills_show` 只看 role_id ⇒ 本地測不到跨 role 隔離 | 驗收註明：只證物件邊界，不證跨 role | 驗收 |
| L15-16 | P3 | (b)(c) 規則句與 5.1 定義文（另一視窗、`_POLICY_TEXT_NON_PROSPECT` 凍結＋字數上限）同檔衝突 | DEFER：(b)(c) 的**規則句**移交 5.1 定義文擁有者（帳本 L15 註記）；L15 只留 (a)＋(b) 的工具描述句 | 範圍縮 |

**§16 修訂後範圍**：(a) select_scope（含候選過濾、estates／meters、寫入路徑、失敗寫 None、fail-closed、str 正規化、替換不結束回合）＋(b) 兩域 description 定義句。(b)(c) 規則句 → 5.1。L15-04／L15-08 已裁（A／物件）。**擁有者**：security-executor 一次交付（`runtime.py`、`tools/jgb2.py`、`mcp_facade.py` 兩域 description、新 `tests/unit/agent/test_select_scope_req.py`、`test_session_confirm_tools_req.py` 增案）。**驗收（確定性，各附正對照）**：(i) select bill(E1) → 模型查 bill(E2) 單列 ⇒ 該工具結果被替換為固定工具訊息、答案末尾接範圍固定句、violation `select_scope_exit`、facts 不在 answer／dialog／trace；正對照＝查同物件 contract(E1) ⇒ 正常；(ii) 無 select（聊天進場）查 E2 ⇒ 正常；(iii) 候選清單含 E1／E2 列 ⇒ 只剩 E1 列進文字；全 E2 ⇒ 視同範圍外；(iv) select 失敗（NO_MATCH）⇒ `select_scope=None`、之後查 E2 正常（舊 scope 不殘留）；(v) 單列缺 `estate_id` ⇒ 範圍外＋`select_scope_unknown`；(vi) estates／meters 別戶 ⇒ 範圍外＋`select_scope_exit`；正對照＝同戶 estates／meters ⇒ 正常 facts、無 violation、`data["scope"]["estate_id"]` 逐字等於列 `id`／`estate_id`；(vi-b) 有 scope 時 `jgb2.query.accounts(keyword=…)` 候選逐字不變、無 violation、答案末尾不含 `SCOPE_EXIT_TEXT`，正對照＝同回合 bills 別戶候選被濾除；(vii) `confirm.request(repair_create)` 別戶 estate ⇒ 不建 pending、固定句；`bill_due_extend` 以 `payload.bill_id` 現查得到的 `scope.estate_id` ≠ select_scope 或為 None ⇒ 同；正對照＝同物件（含同物件不同帳單）照常出卡（與 (xvi) 同向）；(viii) int／str estate id 混用等值；(ix) 範圍固定句為常數、無插值；(x) select 後聊天問別戶 ⇒ 固定句（L15-04 (A)）；(xi) description 含定義句；(xii) 範圍外回合 messages 中該 `tool_call_id` 的 content 不含 facts 片段且 `tool_results_by_id[tc.id].provenance == []`，正對照＝同戶回合 content 逐字含 facts；(xiii) 有 scope 時 `jgb2.query.repairs(face="修繕分類")` 照常回樹、無 violation；(xiv) 三案接句：部分範圍外 ⇒ answer 末尾逐字 `SCOPE_EXIT_TEXT`；全範圍外（含模型回 handoff）⇒ answer 逐字 `SCOPE_EXIT_TEXT`、`kind=answer`、handoff cache 無此鍵；無範圍外 ⇒ 末尾不含；(xv) `repair_create` 同戶無未結單 ⇒ 出卡；別戶無未結單 ⇒ 不建 pending；解析失敗 ⇒ 出卡；(xvi) `bill_due_extend` 同物件不同帳單 ⇒ 出卡、別戶 ⇒ 固定句、查不到 estate ⇒ 固定句；既有 select／confirm／W6 suites 不退。實跑：L5-C 改「退出＋指路」、L5-K 答到合約、線③ 12/12 不退。

### §16c plan-verifier L15 r1 處置（2026-09-08）
| r1 | 處置 |
|---|---|
| 替換只寫 text_for_model，模型實看 provenance ⇒ fail-open；候選過濾由誰做 | FIX：(a)③ 明寫 Runtime 在 `_wrap` 前同時覆寫 provenance／text_for_model／data／`tool_results_by_id`；候選由 Runtime 過濾並以 `_candidates_text` 重繪；驗收 (xii) |
| fail-closed 擋到無物件維度的回傳（修繕分類樹、accounts） | FIX：`scope` 鍵只在實體列呼叫點加（封閉清單），無鍵不比對；驗收 (xiii) |
| §16 (a)③ 舊句與 §16b 矛盾 | FIX：(a) 做法格整格重寫（無「立即結束」「scope_exit=true」「無 estate_id ⇒ 照常」） |
| 接句點與 Verifier／handoff／cache 互動未定 | FIX：唯一接句點 `_apply_scope_exit` 於 `_finalize` 前，對三種 TurnResult 一體適用；全範圍外 ⇒ 短路固定句 kind=answer；驗收 (xiv) |
| `SCOPE_EXIT_TEXT` 落點與受眾 | FIX：`runtime.py` 常數、逐字給定、單一句一體適用 |
| `repair_create` 以提示行副產物 `estate_id` 判邊界，`None` 方向未定 | FIX：`_open_repairs` 解析成功即回 estate_id（count 可 0）；`None` ⇒ 放行（執行時同解析必 NO_MATCH）；驗收 (xv) |
| `bill_due_extend` 拿不到槽位、維度與 L15-08 衝突 | FIX：改為物件維度，Runtime 現查該帳單 `scope.estate_id`（for_model=False、不進 messages）；None ⇒ fail-closed；驗收 (xvi) |

### §16d plan-verifier L15 r2 處置（2026-09-08）——兩輪自動 REVISE 已達上限，改字後開一次關閉輪 r3
| r2 | 處置 |
|---|---|
| (a) 列驗收欄仍為 r1 前舊文（fail-open 那套） | FIX：整格改為指向「§16 修訂後範圍」的 (i)–(xvi) 唯一清單 |
| (3b) 候選過濾未排除 accounts（無 estate_id ⇒ 必空 ⇒ 誤判範圍外） | FIX：(3b) 適用域改封閉清單五域，其餘不過濾；驗收 (vi-b) |
| (vi) 無正對照，estates／meters 整域失效也能過 | FIX：(vi) 補同戶正對照與 `scope.estate_id` 等於列值 |

### §16e plan-verifier L15 r3 處置（2026-09-08）
| r3 | 處置 |
|---|---|
| (vii) `bill_due_extend` 半句仍是槽位維度舊文，與 (xvi)／(a)⑥ 相反 | FIX（文字）：改為物件維度現查判準，同物件不同帳單＝出卡 |

業主先前指示「文字層修正直接續審」⇒ 開 r4。

**r4：READY**（2026-09-08）。待業主核可後派 security-executor（一次交付）。

**L15 完成（2026-09-08）**：業主「派」→ security-executor `95b511c0`（unit 1372／integration 35／audit 27–31 PASS）→ verifier **CONFIRMED**（8 子宣稱＋12 探針；附帶 A1 P4：confirm 卡回合走 `_finish_confirm_turn` 不經 `_finalize` ⇒ 該回合不接指路句、邊界不受影響，列後續；A2 handoff cache 回放為固定句、無風險）。實跑兩輪見帳本 §1h。取捨：寫入閘另立 `_scope_gate_confirm_request`；`_apply_scope_exit` 放 `_finalize` 首句；全範圍外同步清 `handoff_reason`。剩：(b)(c) 規則句 → 5.1；`scope_exit` 輸出鍵另切片；A1。

### §5e security-reviewer 對 W8 (2) 照片線的發現與處置（2026-09-08；兩輪：第二輪依 line-bot「chatai 自己下載」契約改向）

| # | P | 一句話 | 處置 | 落點 |
|---|---|---|---|---|
| S9-1 | P1 | 「白名單同 W7」懸空（W7 未落地、且其主機是音訊 relay） | FIX：W8 (2) 自建 `image_fetch.py`＋`IMAGE_URL_ALLOWLIST`，W7 落地時複用 | (2) |
| S9-2 | P1 | 服務端自抓 ⇒ W7 全套硬邊界（等值主機、https、不跟轉址、私網 IP、串流 bytes、exp 預檢）必建 | FIX：逐條寫入 (2) | (2) |
| S9-3 | P3 | S3 `public-read` 不在 MCP 路徑（照片存 relay） | 移出範圍，併 REST backlog | §2 |
| S9-4 | P2 | `exp` 預檢有意義但 `sig` 驗不了（金鑰未交付） | FIX 措辭：時戳預檢＋依賴 relay 自驗 | (2) |
| S9-5 | P1 | registry 無 `maxItems`／`pattern` ⇒ 靜默無效 | FIX：張數在 `_agent_turn` 程式層；白名單⛔ 不用 schema pattern | (2) |
| S9-6 | P1 | >3 張三方矛盾（契約拒／L3-F 收 5／碼截 3） | **業主裁 2026-09-08「可以超過三張」「超過五張分批送」**：上限 10、chatai 內部每 5 張一批、預算用完明講只看前 N 張、第 11 張起 `INVALID_INPUT`；`analyze_images` 的 `[:3]` 截斷對 MCP 路徑移除；契約列改寫；L3-F 的「JGB 單照片數＝5」為非目標（`repair_create` 不送照片） | (2)、W-D |
| S9-7 | P1 | 時間預算未寫死（抓檔＋縮圖＋辨識） | FIX：`image_budget` 算式＋內層逾時扣除＋`max_retries=1` | (2) |
| S9-8 | P2 | 無圖片維度配額；`detail` 由 env | FIX：`IMAGE_COUNT_CAP_PER_HOUR` 200 張（重新導出、⛔ 不抄 W7 60 MB）；`detail` 程式釘 low | (2) |
| S9-9 | P2 | 成本不可歸屬、`_estimate_cost` 平頭費率 | FIX 措辭：`operation='image_recognition'`、不進 `model_breakdown`、價目表 | (2) |
| S9-10／10b | P1 | 缺圖片原文紀律；`logger.error(f"{e}")` 在 bytes 模型下可能把 base64 寫進 log | FIX：bytes 生命週期段＋熱點必改＋caplog 正反對照 | (2) |
| S9-11／12／13 | P1／P2／P1 | 照片內文字注入直達卡與寫入；卡上分類非封閉；`suggested_emergency` 預設 2 與卡預設 1 相反 | FIX：`description` 硬留空、分類封閉映射出卡前解析、急迫唯一決定者 `emergency_status_of`、決定性驗證器 | (2) |
| S9-14 | P2 | image facts 若直產 `TurnResult` 會繞過寫入閘 | FIX：只產 facts 進模型、⛔ 不直產 `TurnResult`；驗收 select_scope 正反對照 | (2) |
| S9-15 | P2 | 簽章不綁租戶 | **ACCEPT（假設，業主可翻）**：唯一呼叫端單一 key；第二呼叫端出現升 P1 | (2) 取捨 |
| S9-16 | P3 | gpt-5 參數不相容；REST 靜默降級 | FIX：參數依模型；MCP 失敗可見 | (2) |
| S9-17 | P2 | REST 與 MCP 為兩條信任模型 | DEFER REST；§2 非目標明寫 | §2 |
| S9-18 | P2 | bytes ⛔ 不得經 `run_turn`／`agent_state` | FIX：獨立工具事實進場 | (2) |
| S9-19 | P2 | 契約無 image 列 | FIX：W-D 補列（relay 網域、TTL 900／≤3600、**上限 5 張**、5,000,000 bytes、錯誤＝`INVALID_INPUT`、辨識結果不回顯） | W-D |
| S9-20 | P3 | L3-P 期望待裁；L3-D 斷言在 /mcp 不可觀測 | L3-P：兩處損壞 ⇒ 卡上分類取信心最高者、描述留空、候選 `quick_replies` 列另一處（假設，業主可翻）；L3-D 斷言改為卡文字「描述（未填寫）」 | 劇本 |
| S9-21 | P1 | 記憶體／DoS（3×5 MB＋base64＋請求副本） | FIX：串流中止＋逐張抓回即縮 1024px、丟原 bytes（10 張時任一時刻只有一張原檔在記憶體）；每批 ≤5 張 base64；併發上界＝`RATE_PER_MIN` 明列 | (2) |
| S9-22 | P1 | 錯誤碼封閉五值 | **(a) 沿用 `INVALID_INPUT`（假設，業主可翻）**；契約 422 改寫；W7 音訊碼同列待改 | (2)、W-D |
| S9-23 | P2 | 內容型別未驗 | FIX：`validate_format` | (2) |
| S9-24 | P3 | 去 EXIF（GPS）為副作用 | FIX：列明示驗收 | (2) |
| 政策 | — | OpenAI 保留期／DPA 無陳述 | **記為已知取捨（假設，業主可翻）**：先照現行 REST 路徑；zero-retention 設定列 §4 待查 | §4 |

**W8 (2) 驗收（確定性，各附正對照；`tests/unit/agent/test_image_entry_req.py` 假抓檔器＋假辨識器）**：(i) 白名單預設值釘住；白名單外主機／http／IP／userinfo／非 443／3xx／超 5,000,000 bytes（串流中止、抓檔器呼叫 1 次、辨識器 0 次）／`exp` 過期／非圖片 magic bytes ⇒ 該張丟棄且辨識器 0 次；正對照＝合法網址 ⇒ 抓檔 1 次、辨識 1 次；(ii) 11 張 ⇒ `INVALID_INPUT`、抓檔器 0 次；5 張 ⇒ 5 次抓檔、辨識 1 批 5 張（⛔ 不截 3）；8 張 ⇒ 8 次抓檔、辨識 2 批（5＋3）、合併結果分類＝信心最高者；假抓檔器每張耗用使 8 張超預算 ⇒ 只處理前 N 張、辨識只收 N 張、`TurnResult.answer` 卡文字之後逐字含 `IMAGE_PARTIAL_TEXT`（n=N, m=8）而 `card`／`card_sha256` 與全處理時逐位元相同（正對照＝截斷句誤入 render ⇒ 必紅）；`message=""`＋合法 `image_urls` ⇒ 回合正常（非 `INVALID_INPUT`），正對照＝`message=""`＋無 `image_urls` ⇒ `INVALID_INPUT`；(iii) 帶 GPS EXIF 的測試圖 ⇒ 送辨識的 bytes 無 EXIF、尺寸 ≤1024（正對照＝原檔有 EXIF）；(iv) 逾時兩案（本切片自有）：(iv-a) 假抓檔器使第一批辨識前就耗盡 `image_budget` ⇒ 以 `ImageTurnInput(status="timeout")` 呼叫 `run_turn` 恰 1 次、answer 逐字 `IMAGE_TIMEOUT_TEXT`、violation `image_timeout`、辨識器 0 次、dialog 末則＝該句（正對照＝第一批完成後才耗盡 ⇒ `status="partial"`、出卡＋`IMAGE_PARTIAL_TEXT`，即 (ii) 那一案）；(iv-b) 假辨識器耗用 X（0<X<`image_budget`）＋假 `run_turn` 掛住 ⇒ 內層逾時在 ≈`agent_turn_timeout_s()` 觸發（已扣 image_elapsed）、`store.save` 不執行、外層 `wait_for` 未觸發（正對照＝不扣 image_elapsed 則必紅）；(v) 配額用罄 ⇒ `RATE_LIMITED`、抓檔 0 次；(vi) 辨識回不在樹的分類 ⇒ 卡上 `UNSPECIFIED_CATEGORY_ZH`；回 `suggested_emergency=2` 而使用者未表明 ⇒ 卡上「非緊急」（vision 建議不傳播）；回自由文字 description ⇒ 卡上「（未填寫）」、payload description 空；(vii) `damage_visible=false` ⇒ facts 含「看不出損壞」、卡描述留空；低信心（confidence 0.4、樹內候選 2）⇒ 該回合 `kind="ask"`、`trace_id` 非空、無 pending、`quick_replies` 每顆 `label==value` 且 ∈ 分類樹節點名、⛔ 無 `confirm_*`、`agent_state["dialog"]` 末則 assistant＝`IMAGE_PICK_CATEGORY_TEXT`＋候選名；使用者下一回合只回其中一個節點名（無 `image_urls`）⇒ 出卡、`quick_replies` 逐字＝`confirm_quick_replies(pid)`；正對照＝高信心（0.9）⇒ 直接出卡、無候選鍵；假分類樹注入為 None ⇒ 一律 `UNSPECIFIED_CATEGORY_ZH`、無候選、假 `get_repair_categories` 0 次直呼；(viii) 特徵 bytes／base64 片段跑完回合不出現在 trace 快照、`usage_events`、`form_sessions` 列、caplog（正對照＝answer 出現分類名）；辨識例外訊息含特徵字串 ⇒ log 只有例外類別名；(ix) `select_scope` 指 A 戶時帶圖回合對 B 戶 ⇒ 不出卡（正對照＝無 scope 照常出卡）；(x) vision 失敗 ⇒ 回應 `trace_id` 非空、trace 快照 violation `image_recognition_failed`、answer 逐字 `IMAGE_FAILED_TEXT`、dialog 末則＝該句、健檢 `image_recognition.failures_1h ≥1` 與 `last_failure_at` 非 null（正對照＝成功回合 `failures_1h==0`、無 violation）；逾時 ⇒ answer 逐字 `IMAGE_TIMEOUT_TEXT`、violation `image_timeout`；(xi) 不帶 `image_urls` ⇒ 回應逐位元同現行；(xii) 假辨識器回固定分類 ⇒ `messages` 含 `image.recognition` 標籤資料段、模型引用它的句子通過 Verifier（`trace.verifier` 無 `UNCITED_ASSERTION`），正對照＝不帶圖 ⇒ 該資料段不存在；(xiii) 未設 `S3_BUCKET_NAME`／無 AWS 憑證環境跑完整帶圖回合不拋例外、送辨識 bytes ≤1024px 且無 EXIF，正對照＝既有 `upload_image` 測試不退；`make audit` 不變量 27–31 PASS。**真線路一次**（`RUN_REAL_OPENAI=1`；素材＝scratchpad `photos/` 六張，⛔ 不進 repo）：leak／breaker／lock／mold 各出對應分類卡、plain ⇒「看不出損壞」、two_damages ⇒ 一張卡＋候選；gpt-4o 與 gpt-5-mini 各跑一輪並排，費用 ≤ US$0.10。**主驗收**：LIFF L3-C／D／F／R7b／P 五案經 `/mcp` 實跑盲判。
**§6 補 W8 (2)**：回退＝移除 `image_urls` 鍵與 `image_fetch.py` 掛載即逐位元回退、無 DB 變更；預算＝security-executor ≤3 次交付、verifier 1、真線路辨識 ≤12 次；停止＝需放寬白名單或關閉 https／轉址／私網檢查才能過驗收 ⇒ 停下交裁；`description` 硬留空若擋住五案任一 ⇒ 停下交裁（⛔ 不放行自由文字）。**先後**：security-executor 於 L15 交件後（`runtime.py` 單一擁有者）。

### §5f plan-verifier W8 (2) r1 處置（2026-09-08）
| r1 | 處置 |
|---|---|
| facts 進模型無管道、`wrap_tool_data` 不可引用 ⇒ UNCITED_ASSERTION | FIX：`run_turn` 加 `image_facts`／`image_notice` 具名選填；`wrap_provenance_data` 合成 `img-<nonce>` id、`citable=True`；驗收 (xii) |
| 純照片回合被 `minLength 1` 擋 | FIX：`message minLength 0`＋早退「兩者皆空」由 W8 (2) 擁有；驗收 (ii) 補兩案；契約 message 可空 |
| 「卡上明講只看前 N 張」撞卡雜湊 | FIX：`IMAGE_PARTIAL_TEXT` 走卡外附加段（同 hint）；驗收 (ii) 改為卡逐位元不變 |
| 分類樹來源與接線未定 | FIX：`repair_category_tree` 閉包注入（同 `open_repairs`）；None ⇒ 缺值；驗收 (vii) 補正對照 |
| 低信心 quick_replies 無落點／文法／門檻 | FIX：出卡前獨立 ask 回合、`label==value`＝樹節點名、無確認鍵、`IMAGE_CONFIDENCE_MIN=0.6`；驗收 (vii) |
| `compress_image` 是實例方法、需 S3 組態 | FIX：抽 `downscale_image` 模組級純函式，`s3_image_service.py` 入範圍；驗收 (xiii) |
| 健檢旗名未給、`health.py` 不在範圍 | FIX：`image_recognition` 鍵四欄、`IMAGE_FAILED_TEXT` 常數、`health.py` 入範圍；驗收 (x) |

### §5g plan-verifier W8 (2) r2 處置（2026-09-08）——兩輪自動 REVISE 已達上限，改字後開一次關閉輪 r3
| r2 | 處置 |
|---|---|
| 三條程式終止路徑（失敗／逾時／低信心 ask）無擁有層與注入通道 | FIX（裁 (a)）：`run_turn` 具名參數改為封閉值 `ImageTurnInput`（status／facts／processed／total／candidates／建議值），三條路徑一律由 runtime 產出、經既有 trace 與 dialog；驗收 (vii)(x) 補 trace_id／dialog 落點 |

### §5h plan-verifier W8 (2) r3 處置（2026-09-08）
| r3 | 處置 |
|---|---|
| 預算用罄同時映到 partial 與 timeout | FIX（文字）：≥1 批完成 ⇒ partial；0 批 ⇒ timeout |
| 驗收 (iv) 照抄 W7「run_turn 0 次」與 (x) 相衝 | FIX（文字）：(iv-a)(iv-b) 改為本切片自有兩案，與 (x) 一致 |

依業主先例「文字層修正直接續審」⇒ 開 r4。

**r4：READY**（2026-09-08）。待業主核可後派 security-executor（一次交付；真線路用 scratchpad `photos/` 六張、gpt-4o 與 gpt-5-mini 並排）。
