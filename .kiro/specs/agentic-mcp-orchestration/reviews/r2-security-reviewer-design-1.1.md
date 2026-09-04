# r2 security-reviewer — design 1.1（2026-09-04）

REVISE

## P1（擋）
- `/mcp` 的 `quota_check` 無落點：`app.py:usage_metering_middleware` 的 `metered` 只認 `/api/v1/message` POST；`set_decision` ctx None 靜默略過。
- 額度／速率 key 由呼叫方字串決定：`INTERNAL_RULES` 的 `backtest_` 前綴 ⇒ `is_internal` ⇒ `quota_check` 短路；換 `session_id` 重置速率與 `KB_GET_SESSION_CAP`。
- `/mcp` 的 X-API-Key 受 `RAG_API_AUTH_ENFORCE`（預設關）左右，與新端點「無條件」不一致；不變量 19 只驗 `_EXEMPT_PREFIX`。
- DSP-011 前提失效無偵測器（監控只列成本／影子／拒率／tool_unavailable／p95）。
- 白名單句型三型複核擋不住疑問句夾斷言（「支援批次匯入合約，請問您有幾間？」），弱於 R6.2「不分 kind」與 R6.7；`sentence_map` 可整句不列。
- `build_visibility_predicate` 條件未列舉：9 條中 6 條沒點名（`is_active`、`_effective_target_user`、b2b 無 IS NULL＝D-002、`all_users`、查無業者 fail-closed、NOT NULL 差異）；不變量 20 是 AST 反重複不驗語義等價。
- `X-JGB-Identity` 缺欄位／不合法無 fail-closed：缺 `vendor_id` ⇒ `quota_check` 的 `not vendor_id` 短路放行。

## P2（不擋）
`outline:*` 讓 `系統脈絡` 內容變可引用（違反「永不當答案回傳」）且 `build_toc` 未要求 target_user 過濾（`_fetch_domain` 現況分層）；`confirm.request` summary 未綁 payload；Origin 無不變量／測試（`CORSMiddleware` `*`＋credentials，`api_key_guard` 放行 OPTIONS）；大綱進 system prompt 與 R11.1 字面衝突；`dialog` 未包裝。
## P3
導流白名單樣式偵測屬開放集合。

## 第一輪處置核對
擋住：Registry 守門／scope、導流白名單、nonce、SlotKey、token 條款、影子 sha、新端點 X-API-Key、token 表、NO_MATCH、verdict 結構化、readonly_view、help 匯入。擋一半：謂詞（條件未列）、句型複核、fact_class fail-closed（無數字時無網）、`jgb2.query` cap（key 可換）、速率 key、不變量 19、Origin、R5.3。
