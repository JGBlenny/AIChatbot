# r1 security-reviewer — design 1.0（2026-09-04）

## P0
- MCP bearer 的 claims 即身分，信任鏈整條未定義：`MCP_BEARER_SECRET` 共享祕密、repo 無入站 bearer 驗證（正對照 `api_key_auth.verify_api_key`）。→ **業主裁 DSP-011 REJECT**。
- 「role_id 由上游授權」前提在 MCP 門面失效：外部 agent 直打 `/mcp` 以任意 role_id 取他人資料（memory project_role_trust_boundary 成立條件）。→ **DSP-011 REJECT**；補償條件＝前提失效偵測（r2 P1）。
- `kb.get` 同一謂詞不存在；`_grounding_by_ids` SQL 只有 `is_active`，`_grounding_by_category`／`system_context._fetch_base` 無 `vendor_ids`；謂詞 4 份手抄各不同。複製會漏：①保留分類 ②`vendor_ids IS NULL OR &&` ③`is_active` ④`_effective_target_user` fail-safe ⑤`is_b2b` 兩條件 OR ⑥b2b 無 IS NULL 放行（D-002）⑦b2c 加 `all_users` ⑧查無業者 `[]` fail-closed ⑨`embedding`／`keywords` NOT NULL 差異。→ FIX（1.1 單一來源；1.2 條件表＋差分等價）。

## P1
`ToolRegistry.call` 無白名單／scope；逐字不驗相關（否定翻轉、6 字通用引用、拼接）；`assertion_terms` 開放語義用封閉集合治；導流句豁免是注入直達口；`wrap_tool_data` 分隔符可偽造、openapi 洩工具形狀；`session.slots.set` 持久注入；敏感五類仰賴自報＋數字檢查無規則來源（`parse_fact_class` 未知回 other fail-open）；`jgb2.query` keyword 超取（`get_contracts` role_id 單證、`get_bills` 分支不需 user_id）；token 未綁摘要、兌現未重算；`ShadowRecord` 落全文違反 `usage_metering._to_row` 「不含原文」。

## P2
門面無預算／速率（`kb.get` 列舉抽池）；`/mcp` 與 `api_key_guard`／`_EXEMPT_PREFIX` 關係未定（nginx 有帶任意 X-API-Key 即跳過 JWT 的先例）；新端點無認證且 `auth_enforced` 預設關；Origin（`allow_origins=["*"]`＋credentials）；`ConfirmationToken` 無儲存／熵／鎖定；R5.3 與保留分類排除衝突（`_fetch_base` 無 vendor 過濾）；`FORBIDDEN`／`NO_MATCH` 存在性 oracle。

## P3
`VerifierVerdict.detail` 夾原文；影子在 M4 後雙重執行；`help_center_pages` 匯入完整性。

## 設計已正確處理
身分鍵禁入 input_schema＋Runtime 丟棄；敏感五類先於引用；斷言不分 kind；確認同意固定機器值＋token 兌現（優於 `_CONSENT_WORDS` 子字串）；M0–M3 不註冊寫入；零命中不降級；封閉回傳欄位；`args_hash` 落計量；`ToolError` 遮罩；影子 `is_internal`。

未驗證：線上 `RAG_API_AUTH_ENFORCE` 值；`/mcp` 網路暴露面（nginx 只 proxy `/api/`、`/rag-api/`）。
