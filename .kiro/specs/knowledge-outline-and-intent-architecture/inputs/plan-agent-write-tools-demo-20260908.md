# Plan：`agent-write-tools`（demo 範圍，替身後端）v3 — 2026-09-08（r1 六條＋r2 五條 blocker 全部 FIX；r3 為關閉輪）

> 業主裁示（demo 帳本 §1b R1–R3）：demo 在 JGB 開 API 前舉行、整場跑替身；替身讀寫在一份 JSON；寫入工具升 demo 必做。本 Plan 是 roadmap 子 spec 2 `agent-write-tools` 的 **demo 切片**：目標形態不變（design 元件 3 `jgb2.action.<x>{payload, confirmation_token}→{receipt}`），先在替身上把整條鏈演通；真 `agent/v1` 簽章 client 與 JGB 端 `PATCH` 為 demo 後切片。security-reviewer 13 條處置見 §5；plan-verifier r1 處置見 §7。

## 0. 前置：DSP-038（待業主裁，⛔ 未裁不開工 W1）
一次裁三件（都是正本變更，程式⛔不得先行）：
1. **可見性閘**：`jgb2.action.*` 可見＝`AGENT_WRITE_TOOLS_ENABLED`（預設 false、進健檢）**AND** stage；design 元件 2 表 pm 由 M5 改 **M1**、tenant 保持 M4；requirements R4.4 改為「`AGENT_WRITE_TOOLS_ENABLED` 未開即不暴露任何寫入型工具；旗標只在替身或 JGB 憑證就緒時開」。（否決：只改 stage 無旗標＝上線即開寫入；只綁 `USE_MOCK_JGB_API`＝綁在預設 true 且健檢看不見的旗上。）
2. **確認綁定語義**：`confirm.request(summary, payload)` **簽名不變**（R4.2 文字不動）；`payload` 必含 `action`；**確認卡文字由程式 formatter 依 `action`＋`payload` 決定性產出**（⛔ 不用模型的 `summary` 當卡）；`summary_sha256` 欄改存**卡文字雜湊**、兌現時比對。design 元件 3 `confirm.request` 列同步改寫；受影響測試列在 W2。
3. **token 表只加一欄**（migration，可逆）：`agent_confirmation_tokens` 加 `pending_id text`（= `sha256(token)[:16]`，索引；⛔ 仍不存 payload／summary 原文，表的「只存雜湊」決定不變）。
4. **待確認的 `action`／`payload`／`receipt` 存 session 狀態**（`agent_state["pending_confirm"][pending_id]`，經既有 `state_store` 落 `form_sessions.collected_data`——與既有 `bill_ref`／`contract_ref` 槽位同一敏感等級與同一保留期；⛔ 不存 token）。R4.3「同一 token 重送回同一結果」以狀態內 `receipt` 實現。保留／清理：隨 session 既有 TTL；demo 期不另清理（取捨明列）。

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
| **W-D** 正本同步 | DSP-038 落 `DECISIONS.md`；requirements R4.4、design 元件 2 stage 表、元件 3 `confirm.request` 列、`jgb2.action` 列（`mcp_only`＋兌現條件改為「Runtime `redeem_pending` 先燒、工具 `assert_redeemed`」逐字）、**資料模型 `agent_confirmation_tokens` 行加 `pending_id`**；帳本 §4 B3 契約補「value 帶 pending_id」 | `.claude/DECISIONS.md`、`agentic-mcp-orchestration/{requirements,design}.md`、demo 帳本、`mcp-client-contract-line-bot` | 正本文字與 W1–W4 落地規則可逐字對照 | 主 session（裁後） |
| **W1** 入口隔離＋旗標＋健檢 | 新 `ToolSpec.mcp_only: bool`（預設 False）＋ `Identity.entry: Literal["mcp","rest"]` **預設 `"rest"`（fail-closed）**；設 `"mcp"` 的建構點**逐點**：`mcp_facade.parse_identity`（MCP 真身分，`namespaced_identity` 由它衍生故自動繼承）、`union_specs` 的 `_PROBE_IDENTITIES`（建構期決定 `mcp.add_tool` 清單）、`_ToolListFilter` 用的 `call.identity`（來自 `parse_identity`，已含）；其餘建構點（`routers/agent_entry.build_identity`、`health._PROBE_IDENTITY`、`outline.py`、`agent_eval.py`）不帶 ⇒ 預設 `rest`、永不見寫入工具。`_is_visible` 對 `mcp_only` 檢查 `identity.entry=="mcp"`（與 `for_model`／`readonly_view` 正交；Runtime 兌現呼叫維持 `for_model=True`）；`AGENT_WRITE_TOOLS_ENABLED` 讀取（`bootstrap.py`），可見＝旗標 AND stage；health 新旗 `use_mock_jgb_api`、`write_tools_enabled`、**`verifier_observe_only`**（R8）；`USE_MOCK_JGB_API=false` 且 `RealHttpTransport` 憑證空 ⇒ 啟動 raise（S-5） | `tools/registry.py`、`services/agent/identity.py`、`mcp_facade.py`、`routers/agent_entry.py`、`bootstrap.py`、`health.py`、`jgb_system_api.py`／`jgb/transport.py`（只加守門） | unit 三個面各一條、互不代替：(i) `specs_for`：不帶 `entry` 的 `Identity(...)`（含 `health._PROBE_IDENTITY`、`union_specs` 探針形狀）⇒ 無 `jgb2.action.*`；`entry="mcp"`＋旗標開＋stage 達 ⇒ 有；(ii) `tools/list`（`build_mcp_server`）：旗標開 ⇒ 列出、旗標關 ⇒ 不列；(iii) `registry.call(for_model=True)`：REST identity ⇒ NO_MATCH、MCP identity ⇒ 通。健檢旗實得；憑證空 raise 有測試 | security-executor |
| **W2** 決定性確認卡＋表擴欄 | migration（§0-3）；`confirm.py`：`payload.action` 必填（封閉 enum `bill_due_extend`／`repair_create`）、卡由新 `services/agent/confirm_card.py` 依 action 決定性 render、`summary_sha256=sha256(card)`、寫 `pending_id`（表只多這一欄）；`data` 回 `{pending_id, action, payload, card, quick_replies}`（供 Runtime 存進狀態；⛔ 不含 token），`quick_replies` 由 **`confirm.py:confirm_quick_replies(pending_id)`** 產出 `[{"label":…,"value":"confirm_submit:<pid>"},…]`（label／前綴沿用 `CONFIRM_QUICK_REPLY_VALUES`，舊鏈常數不動）；新 `redeem_pending(db, session_id, pending_id)` 單述句 `UPDATE … SET redeemed=true WHERE pending_id=$1 AND session_id=$2 AND redeemed=false AND expires_at>now() RETURNING token, payload_sha256, summary_sha256`（先燒後比對語義不變）；`assert_redeemed(db, token, session_id)`（W4 wrapper 用：`SELECT 1 WHERE token=$1 AND session_id=$2 AND redeemed=true`） | `database/migrations/2026090x_agent_confirmation_tokens_pending_id.sql`、`tools/confirm.py`、新 `confirm_card.py`、**`tests/unit/agent/test_session_confirm_tools_req.py`**（鍵集合斷言更新為 payload 內含 action）、**`tests/integration/agent/test_confirmation_tokens_req.py`**（`summary_sha256` 斷言改對卡文字） | unit：同 payload 同卡；改任一欄 ⇒ 雜湊不符；integration 五條既有（TOCTOU／重放／跨 session／過期／竄改）不退＋新增 redeem_pending／receipt 冪等 | security-executor |
| **W3** Runtime 確認段 | **守門順序**：`run_turn` 開頭 ① `identity.entry != "mcp"` ⇒ 整段不執行（REST 永不兌現）；② `self.readonly_view` ⇒ 整段不執行（影子 fail-closed，DSP-016）；③ 訊息**等值**匹配 `^confirm_(submit|edit|cancel):([0-9a-f]{16})$`（整句、無前後綴；正常對話不可能等值命中）且 `agent_state["pending_confirm"][pid]` 存在 ⇒ 不進模型。submit ⇒ `redeem_pending` → 有列 ⇒ 比對 `payload_sha256`／`summary_sha256` 與狀態內 payload／卡雜湊 → `registry.call(identity, f"jgb2.action.{action}", {"payload", "confirmation_token": token}, for_model=True)` → receipt 存 `pending_confirm[pid].receipt` → `TurnResult.answer` 由 formatter 依 receipt 組（模型不在迴圈）；無列 ⇒ 狀態有 receipt ⇒ 回同一 receipt（R4.3）；否則 `CONFIRMATION_REQUIRED` 固定句。cancel／edit ⇒ `redeem_pending` 燒 token、狀態 `receipt={"cancelled":true}`、不呼叫工具。**確認回合**：模型回合內出現 `confirm.request` 的 `ToolResult.ok` ⇒ 立即結束回合：`TurnResult(kind="ask", answer=data.card 逐字, quick_replies=data.quick_replies)`，模型當回合輸出丟棄、Verifier 不跑（卡是程式產出）；同時把 `{action, payload, card_sha256}` 存 `pending_confirm[pid]`。**token 只在 `run_turn` 內存活**：⛔ 不進 `agent_state`／`state_store`／`TurnResult`／trace／模型上下文（不變量測試：grep 狀態快照與 TurnResult 無 token 字串）。trace／`usage_events` 加 `pending_id`、`receipt_id`（不變量 30 白名單擴充） | `runtime.py`、`state_store.py`（`pending_confirm` 鍵）、`_emit_agent_decision` 白名單、`usage_metering` | integration：正向 2＋反向 5；`TurnResult.answer == confirm_card.render(action, payload)` 且 `sha256(answer) == 表中 summary_sha256`（反例＝採模型輸出會紅）；影子隔離、入口隔離兩條 DB 反證（§1）；token 不出現在 TurnResult／狀態快照 | security-executor |
| **W4** 寫入工具 | `tools/action.py`：`bill_due_extend`、`repair_create`（`scope="write"`、`mcp_only=True`、stage 依 DSP-038）；`registry.register()` 對 `scope=="write"` **強制**包共用 wrapper（S-9）：`assert_redeemed(token, session_id)` 為真才進 handler（token 由 Runtime 行程內傳入；重複執行由 Runtime 的狀態 receipt 擋在前面）、pm 要 `user_id`（S-8）、寫前讀一次確認資源在身分範圍、呼叫 `JGBSystemAPI.agent_patch_bill_due_date`／`create_repair`（demo 只有替身 transport；`Idempotency-Key=token`）、成功 ⇒ 回 receipt（Runtime 存狀態）；失敗 ⇒ 回 `{"error"}` 誠實回錯、不留殘單 | `tools/action.py`、`registry.py`、`jgb_system_api.py`（新方法、⛔ 不碰憑證） | unit：無 token／錯 session／未 redeemed／已有 receipt ⇒ 全擋或回同 receipt；替身 receipt；失敗不留殘單；**`repair_create` 接受父節點分類＋空描述**（line-bot 線③ Q：分類樹涵蓋不到時退回大類、描述留空、照樣開得成單，⛔ 不編葉節點） | security-executor |
| **W5** R-寫實跑 | 劇本 2 正向＋5 反向；帳本 §1 回填 | scratchpad 劇本、帳本 | §1 主驗收 | 主 session → verifier |
| **W6** 口語穩定度（業主 2026-09-08 R5：「完成度需要能夠應付真實用戶操作」） | **先量再修、修在規則層。** (a) 量：`scenarios_w6.json` 12 會話 36 回合，pm 經 `/mcp`、替身後端；指標＝可答題轉人率／資料事實答錯率／明確 ref 反問率／收尾語正確率／p50；基線 r1 52%、r2 48%、r3（Verifier 只觀察）7%（帳本 §1c）。 (b) **W6-b0 重放材料**（前置，`runtime.py`，security-executor W3 交件後）：`_emit_attempt` 紀錄補 `trace_id`、`user_message`、每個 ref 的 `resolved_quote`（解析後引文，⛔ 只在 `AGENT_ATTEMPT_LOG_PATH` 開時寫、預設關、只在替身實例用）；擷取一輪有閘 r4 作為離線重放集。 **W6-b1 尺（`verifier.py`，security-executor；⛔ 非一般 executor；DSP-039 業主 2026-09-08 定稿「尺分兩類」）**：① 依片段所引用的來源分兩類——**(A) 工具事實片段**（所有 refs 皆 `jgb2:*`）：**值級檢查**，「值」＝封閉擷取樣式：整數／小數（含千分位）、`NT$`／`$` 前綴剝除後的金額、完整日期（`YYYY/MM/DD`＝`YYYY-MM-DD`＝`YYYY.MM.DD` 正規化 `YYYY-MM-DD`）、百分比、≥4 位連續數字當編號、**列舉狀態詞**（該域工具 mapping 的封閉標籤集合，例如帳單 待繳費／已繳費／待對帳、物件 刊登中／已下架、修繕 急迫／非緊急——來源＝`services/jgb/*.py` builder 的標籤表，程式讀取、⛔ 不手抄）；⛔ 部分日期（`8/15`、`8 月 15 日`）不與完整日期等價、⛔ 電話不納入（沿用步⑤ `_PHONE_RE`）、全形數字 NFKC 後同半形；**比對＝正規化後 token 等值，⛔ 非子字串**；片段內任一值不在「該句所引用各行的聯集」⇒ 新拒因 `VALUE_NOT_IN_SOURCE`；**(A) 類不再計算字元涵蓋率**；量詞逐字：每一個參與 ref 仍須各自通過 `min_quote_len` 與 `citable`，每一個參與 ref 的極性都須與片段一致（任一不一致 ⇒ `POLARITY_MISMATCH`）。**(B) 知識正本片段**（任一 ref 為 `outline:*`／`kb:*`／`help:*`，或混引）：維持現行規則不變（事實句須引用、單行涵蓋率、極性、citable）。機敏閘（步⑤ 導流／個資、敏感題轉人）兩類皆不動。 ② `_effective_kind` 定義化：**greeting／closing ＝ 命中封閉語義詞表 `closing_terms`（`config/agent_verifier_rules.json`，一類維護）∧ 無數字 ∧ 未命中 `assertion_terms` ∧ 無 URL ∧ 長度 ≤ `closing_max_chars`**（四條否定條件⛔ 不是充分條件，詞表命中是必要條件）；**question ＝ 命中 `interrogative_terms`（封閉表）∧ 未命中 `assertion_terms`**，句尾「。」允許但非獨立通過條件；不再依賴 `_GREETING_PHRASES`／`_QUESTION_ENDS` 字面。誤殺量測：以 r4 attempts 片段離線跑新舊 `_effective_kind`，列出型別翻轉清單，其中 0 筆含未引用事實斷言。 ③ 新拒因落地面：`output_schema.py` `VerdictReason` 加 `VALUE_NOT_IN_SOURCE`、`VerifierRules` 加 `closing_terms`／`interrogative_terms`／`closing_max_chars`；`config/agent_verifier_rules.json` 新詞表（`rules_sha` 隨之變，健檢／trace 只是顯示新值）；`runtime.py` `_REASON_HINTS` 補該拒因修法提示＋**鍵集合守測**（比照 `_SCHEMA_CAUSE_HINTS`：斷言涵蓋 `VerdictReason` 全部非 SCHEMA 拒因，刪鍵即紅）。 ④ fixtures：`known_fabrications.json` 全拒、`known_good.json` 全放、`known_open.json` 案例數不增（⛔ 不得搬檔）；新增：合併句值全在 ⇒ 過；**工具片段狀態詞錯（來源「待繳費」寫成「已繳費」，數字全對）⇒ `VALUE_NOT_IN_SOURCE`**；知識片段（`outline:*`）改寫散文仍走涵蓋率 ⇒ 既有預期不變；合併句改一值 ⇒ `VALUE_NOT_IN_SOURCE`；「18,000」對「18000」⇒ 過；「18000」對只含「180000」⇒ 拒；「2026/08/15」對「2026-08-15」⇒ 過；「8/15」對「2026-08-15」⇒ 拒；可引用 A＋不可引用 B、內容只出自 B ⇒ `SOURCE_NOT_CITABLE`；A 肯定＋B 否定、句取 B 寫成肯定 ⇒ `POLARITY_MISMATCH`；無數字無 URL 未命中 assertion_terms 的捏造句標 greeting、refs 空 ⇒ `UNCITED_ASSERTION`；greeting 含數字 ⇒ fact；問句句尾「。」含疑問詞 ⇒ question；`split_assertion_across_entries`／`question_with_assertion_in_same_entry` 既有預期不變。 **W6-b2 類別**（`agent_rules.py` 定義句、`conversational_config.py` 受眾固定句）：收尾語＝封閉類別定義句與對應 `kind`（短收尾、不轉人）；轉人固定句依受眾（pm「轉專人」）；「有明確 ref 仍反問」走 ask 政策定義。 (c) 延遲：line-bot 契約 typing 指示；模型 low→medium 以實測「每回合 +N s 對拒答率 −M%」裁。 | 劇本、`runtime.py`（`_emit_attempt`、`_REASON_HINTS`）、`verifier.py`、`output_schema.py`、`config/agent_verifier_rules.json`、`tests/fixtures/agent/known_*.json`、新 `tools/verifier_replay.py`（離線重放，進 repo）、`agent_rules.py`、`conversational_config.py`、line-bot 契約 | **確定性主驗收（W6-b1）**：`tools/verifier_replay.py` 以 r4 attempts（含 resolved 引文）逐筆重放新舊尺，輸出差異表；預期＝「舊拒新過」只含兩類（合併句值全在、無數字 greeting／question），「舊過新拒」＝0，事實無引用與 SCHEMA 仍拒；fixtures 三檔不變量全綠（`self_test` 啟動即證）。**次驗收（實跑）**：同劇本兩輪取合併率，可答題轉人率／反問率不高於 r2、事實答錯 0、禁詞 0；劣化超過 r1↔r2 既有變異（4 pp）即不過。**通過標準（待裁，建議）**：可答題轉人率 ≤20%、資料事實答錯 0、明確 ref 反問率 ≤10%、p50 ≤20 s。security-reviewer（W6-b1 專審）findings 處置進 §5 後、plan-verifier 對 W6-b1 單獨 READY 才派 | 主 session（量、重放腳本）＋**security-executor**（W6-b0／b1）＋executor（W6-b2）→ verifier |

先後：W0（進行中）→ W0b（整合修補＋repairs 讀工具）→ DSP-038 裁 → W-D → W1 → W2 → W3 → W4（W2–W4 同一 security-executor 契約）→ W5 → **W6**（可與 W1–W4 並行量基線；修的部分在 W5 後）。

## 4. 已裁與待裁
- 待裁：DSP-038 三件（§0）。建議全採。
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

## 6. 回退、預算、停止
- 回退：旗標關 ⇒ 工具不可見、兌現段不觸發（REST 本就不觸發）；migration 可逆（新欄 nullable、`pending_id` 可回填）；替身狀態行程級。
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
