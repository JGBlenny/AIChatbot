# 2.6／2.7 前置 security review（唯讀，2026-09-05）— REVISE → 全數寫成 2.6／2.7 驗收句

[P1] `agent.turn` 狀態以純 `session_id` 存（`conversational_engine.get_state/_save/_close`、`form_manager._get_session_state_sync` 皆無 vendor 條件；正對照 `form_manager.py` 另處有 `vendor_id` 條件）⇒ 持 vendor 2 key 帶他人 session_id 可讀寫他人對話。處置：MCP 進來的回合狀態鍵改 `mcp:{api_key_id}:{vendor_id}:{session_id}` 命名空間（REST 路徑不變）；驗收：同 session_id 不同 vendor ⇒ 讀不到、原列不改。
[P2] `dialog_ref` 無語義 ⇒ 2.6 schema 只收 `message`（驗收：屬性集合 == {message}）。
[P2] 門面 3 秒工具逾時 vs 回合 20 秒 ⇒ `agent.turn` 獨立逾時 > `Budget.deadline_s`，取消不落半寫 state。
[P2] Runtime 直呼 `chat.completions.create` 繞過 `add_llm_usage` ⇒ token／費用不進事件層；內部 key 又免額度 ⇒ 2.6：改走 provider 包裝或以 `TurnTrace` token 灌 `add_llm_usage`，`agent.turn` 加每小時上限（比照 `KB_GET_CAP`）；驗收：一回合後事件列 `prompt_tokens > 0`。
[P2] `args_hash` 對低熵參數可字典反解 ⇒ 刪 `args_hash` 只留 `args_summary`（design 資料模型同步）。
[P2] Verifier `term_id` 為字面詞／regex ⇒ 快照存規則索引＋`rules_sha`；2.7 不印字面詞。
[P3] `handoff_cache` 無上限 ⇒ 每 session ≤50 筆 FIFO。
[P3] 2.7：`/api/v1/agent` 在 `GATED_PREFIXES` ⇒ 端點與 CLI 須帶 `X-JGB-Identity`；查 `decision_snapshot->'agent'->>'trace_id'` 無索引 ⇒ 時間窗＋LIMIT；輸出 `session_id` 遮罩為前綴＋雜湊；CLI 憑證走 `db_utils.get_db_config()`。
正對照：`form_manager.py:100` 有 vendor 條件證明 grep 有效；`facade_only` 可 grep 到程式落點證明 `dialog_ref` 確無實作；`add_llm_usage` 在 `llm_provider.py` 命中而 `services/agent/**` 無 `usage_metering` import（`mcp_facade.py` 有）。
