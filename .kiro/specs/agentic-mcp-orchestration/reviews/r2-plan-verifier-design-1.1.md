# r2 plan-verifier — design 1.1（2026-09-04）

REVISE

[P1] 「個資圈定交 jgb2」繫於 `jgb2.query.<domain>` 帶 `viewer_user_id`，但本 repo `JGBSystemAPI.get_*` 會被 `**kwargs` 靜默吞掉（只有 `get_bill_visibility` 送出），且 §3.5 明寫只有 bills／contracts status-overview／payments／invoices 四支支援；estates／meters／accounts 無 jgb2 端圈定；mock `_bills_index` 帶該參數 raise `UnsupportedMockParameterError` — 修法：逐域列實際生效邊界並寫成可測驗收。
[P2] `get_<domain>` 機械映射對 accounts（無 `get_accounts`；ground 在 `get_team_members`／`get_member_permissions`／合約端點）與 estates（`detail` 需第二支 API）不成立 — 修法：domain→(API 方法, 註冊表, secondary) 三欄。
[P2] `ToolSpec.stage` 單一 Literal 表達不了 per-audience；矩陣 `jgb2.query` M0 與里程碑 M5 衝突。
[P2] `readonly_view` 無 Runtime 通路（只在 `specs_for`／`call`）。
[P2] R7.2 重播快取只剩 `handoff_cache` 鍵，無行為。
[P2] `audience_of` prospect「無 role_id」與 `CONVERSATIONAL_ENABLED_ROLES` 判準（只看 target_user）不符。
[P2] 附錄 C 只登 4 條 pv P1（原 6 條，合併列）；第一輪報告未落檔。
[P3] 步④寫 `ToolResult.citable`（實為 `Provenance`）；`text_for_model`「含 nonce」與工具簽名拿不到 nonce 兩說；`kb_id: int | str` 與 strict schema；R3.3 `skip_refine` 未提；M3 通過線掛未裁 D2。

## 第一輪處置核對
已處置：謂詞單一來源、五張表對碼（estates 三參數屬實）、R7.3／R3.4／R12.1、規則來源、quote 目標、預算表、D2–D5、決策 7（`retrieve()` 含 reranker 屬實）、sec P2 全部、P3 全部。部分：face enum（contracts 未命中落 `ACCOUNT_FACE_BUILDERS`）、Registry（readonly_view 通路）、注入九項（nonce 產生者）、矩陣（stage 表達）、里程碑（M2 綁 D2、M3 無線）、audience 推導（prospect）。
