# 9.8 啟動預算改尺＋不預組整份篩選結果（DSP-059 D′）計畫 v4 — 2026-09-16（plan-verifier 三輪；收尾輪三條 FIX 已納入，業主 2026-09-16 授權自判後開工）

> 依據：`.claude/DECISIONS.md` DSP-059；草案 `inputs/dsp-059-draft-20260916.md` §2 選項 D 表＋§6 D′；事實表 `inputs/factsheet-outline-injection-{A,B,crosscheck}-20260916.md`。
> 用語：九架正本 `canon/jgb/`、細目屬性 `target_user`、售前身分／業者身分的篩選結果、每回合注入＝K=5 候選＋目錄。

## 0. 定案（DSP-059，2026-09-16）

啟動只量兩尺：**任 K=5 可引用節 token 最大和**（`OUTLINE_K_TOKEN_LIMIT`，先訂 2,500）與**目錄 token**（`OUTLINE_TOC_TOKEN_LIMIT`，先訂 8,000），皆無標記 cl100k、env 只縮不放；⛔ 不再量整份篩選結果。啟動不預組任何身分的整份篩選結果；每回合由 `_select_outline` 從九架正本現組 K=5 節＋目錄；**降級只注入目錄**，內容走 `kb.get`；降級須外顯（health 紅＋violation）；`outline_sha`＝`canon_sha256`。

## 1. 目標與非目標

**目標**：`make audit` 與 `scripts/run-tests.sh unit|integration` 在 210 條正本（未審 190）下全綠；每一條注入路徑（命中／降級／無候選機制）都被兩尺蓋住；售前身分回合行為不變（同一題命中同一組 `candidate_ids`、同一段 toc）；**業者身分由現況「啟動被跳過 ⇒ `agent.turn` 回 `AGENT_UNAVAILABLE`」恢復為可服務**（現況：`build_audience_outline("property_manager")` 在 `check_budget` 拋 `OutlineBudgetExceeded`，`app.py::_init_agent_runtime` 只跳過；S1 兩尺皆過 ⇒ 業者身分被註冊）。

**非目標**（⛔ 不做）：B 目錄按需、補審內容、H 存廢、租客線、`canon_visible` 任何分支改動、`outline.py::build_toc`（DB 目錄）存廢（另記 dispute）、部署、資料庫寫入、常數以外的 prompt 文字改動。

## 2. 現況縫（全部對碼，符號可 grep）

| 縫 | 現況 | D′ |
|---|---|---|
| `outline.py::check_budget(doc, limit_tokens)` | 量整份篩選結果 `token_count`（含未審標題節）；`build_audience_outline` 第 4 步與 `app.py::_init_agent_runtime` 迴圈各呼叫一次（同 doc 兩次） | 保留為純函式（`test_outline_unit_req.py` 兩條釘它），⛔ 啟動不再呼叫；新增 `check_turn_budget(sections, toc_section, *, k_limit, toc_limit)`（吃節序列，不吃 doc 也不吃 canon：S1 由 `OutlineDoc.sections` 餵、S2 由現組節餵，同一支函式）。**量測式寫死**：只取 `citable=True` 且 `id != TOC_SECTION_ID` 的節（`TOC_SECTION_ID` 在 `canon/canon_assembler.py`，與 `outline.py` 循環相依 ⇒ 函式內 import，沿 `build_audience_outline` 現行做法）；每節 token＝`_count_tokens(f"【{s.id}】{s.title}\n{s.text}")`（與 `_build_doc` 的節組法同式，節間分隔字元不計）；K 上界＝最大的 `min(K, n)` 節之和，`K` 取自 `services/agent/canon/candidate_selector.py::K`（⛔ 不另寫常數）；toc＝`_count_tokens(toc_section.text)` 單獨對 `toc_limit` 比；任一超過 ⇒ raise `OutlineBudgetExceeded`（沿用例外型別） |
| `outline.py::OUTLINE_TOKEN_LIMIT_DEFAULTS`／`default_token_limit(audience)`／env `AGENT_OUTLINE_TOKEN_LIMIT_*` | 單尺 prospect 12,000／pm 8,000／tenant 8,000 | 兩張常數表 `OUTLINE_K_TOKEN_LIMIT`／`OUTLINE_TOC_TOKEN_LIMIT`（鍵同現況三個：prospect 2,500／8,000、property_manager 2,500／8,000、tenant 2,500／8,000，tenant 鍵保留與 `_AGENT_OUTLINE_AUDIENCES` 無關）＋env `AGENT_OUTLINE_K_TOKEN_LIMIT_{PROSPECT,PM,TENANT}`／`AGENT_OUTLINE_TOC_TOKEN_LIMIT_{PROSPECT,PM,TENANT}`（後綴沿 `OUTLINE_TOKEN_LIMIT_ENV` 現行三個；只縮不放，沿 `default_token_limit` 的 `min(int(raw), default)` 語義）；舊常數表、`OUTLINE_TOKEN_LIMIT_ENV`、`default_token_limit` 與舊 env 名**刪除** |
| `app.py::_init_agent_runtime` | 逐受眾 `build_audience_outline` → `outlines[aud]`；prepare 失敗只 `print` | `load_canon_or_die` → `register_canon` → `FineIndex.prepare` → 逐受眾以 `_STATIC_TOC_IDENTITY` 跑 `check_turn_budget`，**餵入＝該受眾 `canon_visible` 為真的全部細目 id（＝S1 `check_turn_budget` 實際計數的 citable 集合，`build_canon_sections(canon, identity, ids=可見已審 id)`）＋該受眾 toc**，⛔ 不是 `_axes_visible` 全集（未審 id 會觸發 `build_canon_sections` 的 raise）、⛔ 也不是 K 個選中節；產 `agent_audiences: frozenset`；prepare 失敗 ⇒ health 既有 `checks.canon.index.<audience>.state` 非 ready ⇒ 紅（`compute_agent_health` 現行判定） |
| `mcp_facade.py::_outline_for_audience`／`_agent_turn` 的 `agent_state["outline"]` | 查 `agent_outlines[aud]`，缺 ⇒ `_OUTLINE_UNAVAILABLE`（fail-closed）；每回合塞整份 doc、存檔前 pop | 改查 `agent_audiences`（fail-closed 語義不變：缺 ⇒ `AGENT_UNAVAILABLE`）；不再塞 `agent_state["outline"]` |
| `runtime.py::_select_outline(outline, …)` | 首段 `if outline is None: return`；`from_selection(full, sel, toc)`；`_fallback_visible` ⇒ `from_visible(可見已審全集, toc)` | 簽名改吃 `identity`＋`get_canon()`（audience 只由 `identity.resolved_audience()` 推導，⛔ 不當參數）；命中 ⇒ `CandidateOutlineDoc.from_canon(canon, identity, ids, toc)` → `canon_assembler.build_canon_sections`（逐 id 過 `canon_visible`，不可見 ⇒ raise，⛔ 不產空節；`sha256=canon_sha256`）；任何未命中／失敗 ⇒ `from_canon(canon, identity, [], toc)`（零節＋toc），violation `candidate_fallback_toc_only`；外層 guard：toc 失敗 ⇒ `miss_kind="empty_toc"`＋violation `candidate_toc_error`（`candidate_selector.MissKind` 改為五值 `hit／none_visible／no_candidate／index_unavailable／empty_toc`：**刪 `audience_mismatch`**——其唯一產出點是 `_select_outline` 比對預組 doc 的 `audience`，S2 後不存在；同步該檔 docstring 與 `runtime.py` 產出點）；canon 未註冊／無候選機制 ⇒ 回 `(None, None)`（`prompt_assembler` 容忍 None） |
| `prompt_assembler` `outline.audience != identity.resolved_audience()`；`_select_outline` `audience_mismatch` | 擋「facade 交錯受眾的預組 doc」 | 預組 doc 不存在 ⇒ `prompt_assembler` 的比對恆真、保留程式不動；`_select_outline` 的 `audience_mismatch` 分支**刪除**（它比的是預組 doc 的 `audience`，S2 後無此輸入）；兩者的測試改釘 `canon_visible` 隔離（見 S2 驗收 ④） |
| `agent_session.py::OUTLINE_KEY`／`KEY_SPECS`（11 鍵封閉）；`routers/agent_entry.py` 三處（未掛載）；`tools/agent_eval.py::_set_outline_on_state`；`bootstrap.py::build_runtime(outline_doc=)`；`health.py::_outline_sha`；`ShadowRunner` 工廠；`make_outline_resolver(cache)` | 整份篩選結果的消費者 | `OUTLINE_KEY` 移除（封閉鍵集 11→10，測試同步）；`agent_entry.py` 三處刪；`agent_eval` 改用 `from_canon`；`build_runtime` 去 `outline_doc`，`runtime.outline_sha = canon.canon_sha256`；health `outline_version`＝`canon.sha256.jgb`；resolver `cache` 分支刪 |
| `tools/agent_outline_dump.py`、`tools/agent_eval.py --candidates off`、`build_audience_outline`／`build_prospect_outline` | 離線工具與別名 | `build_audience_outline` 降為離線工具函式（搬 `tools/` 或留 `outline.py` 但 `app.py` 不呼叫）；`--candidates off` 臂定義＝「可見已審全集＋toc」並明標離線 |

## 3. 切片（依序 S1 → S2 → S3 → S4；每片落地樹必綠；下一片等上一片 verifier CONFIRMED）

### S1 尺：`check_turn_budget`＋兩張常數表＋啟動改呼叫（整份物件暫留，⛔ 不動 `_select_outline`）
- 出貨：`outline.py::check_turn_budget`（量測式見 §2 第 1 列）、`OUTLINE_K_TOKEN_LIMIT`／`OUTLINE_TOC_TOKEN_LIMIT`、`default_k_token_limit`／`default_toc_token_limit`（env 只縮不放）；刪 `OUTLINE_TOKEN_LIMIT_DEFAULTS`／`OUTLINE_TOKEN_LIMIT_ENV`／`default_token_limit`／舊 env 名；`build_audience_outline` 第 4 步呼叫 `check_turn_budget`（唯一的閘）；`app.py` 迴圈只為啟動 log 以相同輸入重算一次 `TurnBudget`，⛔ 不是第二道閘（S1 落地取捨：不改 `build_audience_outline` 回傳型別）；啟動 log 改印三數（K 上界／toc tokens／toc 行數）。**文件同片出貨**（否則不變量 41 與 ④ 紅）：`docs/architecture/SYSTEM_ARCHITECTURE.md` 三處——A-8「prompt 長度無閘…K 調大＝prompt 直接變長，⛔ 不會有任何東西擋」整段改寫為「K 上界已由 `check_turn_budget` 於啟動守住，K 調大即啟動紅」（⛔ 不是只換符號）、A-9 常數表列、A-9 查證指令、A-9 表 `check_budget(doc, limit)／OutlineBudgetExceeded` 列改寫為「純函式，離線工具／測試用；啟動預算已改由 `check_turn_budget` 守（K 上界＋toc 兩尺）」；`rag-orchestrator/canon/README.md` 預算句改為兩尺。承接 9.7 釘值債：`test_agent_turn_pm_outline_req`（3 條）、`test_library_view_req::test_toc_only_lists_this_audiences_reviewed_fines` 一併改。
- 驗收（否定帶正對照）：
  ① 合成 fixture（3 架、7 可引用節、2 未審）：K 上界＝以 §2 量測式手算的前 5 大節之和（釘整數值）、toc＝`_count_tokens(toc 節 text)`；把 `k_limit` 設 1 必 raise（正對照：設 10,000 通過）；未審標題節不計入（把未審節 text 塞 5,000 字仍通過）；可引用節只有 3 節時 K 上界＝3 節和（正對照：7 節時取 5）。
  ② 工作樹現行正本（210 條，`canon_sha256` 前綴 `b94acd638e35`，不符 ⇒ 停並重量）：兩身分 `check_turn_budget` 通過；印出的數**逐數相等**：售前 K 上界 1,931、toc 373；業者 toc 283（容許誤差 0；業者 K 上界為新量，印出後釘）。**尺可失敗的突變驗證**：把實作改成「全部可引用節求和」或「未審節也計入」，此條必紅（正對照：還原後綠）。
  ③ env 只縮不放，兩尺三身分各測：`AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT=1`／`AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM=1` ⇒ raise；`=99999` ⇒ 仍用常數（正對照：未設時＝常數）。
  ④ 舊符號零殘留（S1 範圍，兩道各帶同語料正對照）：(a) `grep -rn 'OUTLINE_TOKEN_LIMIT_DEFAULTS\|OUTLINE_TOKEN_LIMIT_ENV\|default_token_limit\|AGENT_OUTLINE_TOKEN_LIMIT_' rag-orchestrator --include=*.py` ⇒ 0（正對照：同 grep 對 `OUTLINE_K_TOKEN_LIMIT` 命中 `outline.py`）；(b) `grep -n '<同舊符號集>' docs/architecture/SYSTEM_ARCHITECTURE.md rag-orchestrator/canon/README.md`（⛔ 不帶 --include）⇒ 0（正對照：同兩檔 grep `OUTLINE_K_TOKEN_LIMIT\|OUTLINE_TOC_TOKEN_LIMIT` 各命中；正對照 0 命中＝尺失效，不得記綠）。完成報告貼四次輸出。全範圍零殘留在 S3 驗收。
  ④b `bash scripts/audit/check_invariants.sh` 全 PASS；`grep -n "沒有預算守門\|不會有任何東西擋" docs/architecture/SYSTEM_ARCHITECTURE.md` 0 命中；`grep -n "啟動即紅" docs/architecture/SYSTEM_ARCHITECTURE.md` 的命中行不掛在 `check_budget` 列（正對照：`grep -n check_turn_budget` 同檔命中）。⚠️ 不變量 41 對本次刪除不具可否證性（`tests/.coverage.json` 仍含舊符號），真正守門是 ④。
  ⑤ `scripts/run-tests.sh unit tests/unit/agent` 綠、`integration` agent 子集綠：`test_real_views_fit_the_budget` 改釘新尺；`test_env_cannot_raise_the_cap*`、`test_env_limit_lower_than_actual_raises` 改指新常數；`test_canon_assembler_req` 68/30、`test_outline_req` 47/21、`test_visible_subset_sql_equiv_req` 47/31 釘值改為 210 條正本的實值（腳本印出後釘，並以 `canon/jgb/CATALOG.md` 逐細目 `target_user` 欄獨立數一次交叉核，兩者相等才釘）。
  ⑥ 業者身分翻轉可觀察（不需真起 app）：新測試以工作樹正本 `build_audience_outline("property_manager")` 組出 outlines 餵 `FacadeDeps`，斷言 `mcp_facade._agent_turn_preflight` 對 property_manager 身分不回 `ERR_AGENT_UNAVAILABLE`；同一測試在 S1 前的程式下因 `OutlineBudgetExceeded` 必紅（executor 貼 S1 前後兩次輸出；verifier 自行重跑）。
- 執行者：`executor`。verifier 針對 ①②③④④b⑤⑥。完成報告須加一行：「舊 env `AGENT_OUTLINE_TOKEN_LIMIT_*` 自 S1 起無效，S3 前勿照 runbook 設」。

### S2 物件移除：`_select_outline` 從正本現組＋降級只注入目錄＋消費者十處＋降級外顯（單一不可分割落地；security-reviewer 2026-09-16 九條 F1–F9 已納入）
- 出貨：§2 表第 3–8 列全部（第 8 列：`tools/agent_outline_dump.py`／`tools/agent_eval.py` 改用 `build_canon_sections`＋`visible_subset` 重建「可見已審全集＋toc」離線臂、`build_audience_outline` 降為離線工具函式且 `app.py` 不再呼叫），並依安審修正：
  - **F3(a)／F1** 組節住在 `canon_assembler.py::build_canon_sections(canon, identity, ids, *, vendor_business_types)`（29b `CANON_VISIBLE_CALLERS` 加此名，⛔ 不加 `outline.py` 內的符號）：逐 id 查 fine，節組法**與 `build_outline` 同式四欄**（`canon_assembler.build_outline` 現行逐字）：`id=fine.id`（⛔ 不加 `outline:` 前綴——前綴由 `kb.get`／DSP-029a 標記端自帶，此處重複加會改動 `text` 與逐節 token）、`title=fine.title`、`text="\n".join(fine.content_units)`、`source_ids=[]`、`citable=True`（不可見者已 raise，不會產生 `citable=False` 節）；`from_canon` 另釘 `audience=identity.resolved_audience()`、`version=canon.version`、`sha256=canon.canon_sha256`（`_build_doc` 接成 `【id】title\ntext`）；`canon_visible` 為假（不可見／未審／不存在）⇒ **raise**（落到 `_select_outline` 的 `except` ⇒ toc-only 降級＋violation `candidate_invisible_id`），⛔ 不靜默 skip、⛔ 不以 `citable=False` 空節代替；`outline.py::CandidateOutlineDoc.from_canon(canon, identity, ids, toc)` 只轉呼叫。**F6／F7**：`from_canon` 與 `_select_outline` ⛔ 不得有 `audience` 參數，audience 只由 `identity.resolved_audience()` 推導；`_select_outline` 簽名改吃 `identity`＋`get_canon()`。
  - **F2** `app.state.agent_audiences: frozenset`，`mcp_facade._outline_for_audience` 改為「屬性存在即權威」：`None`／非集合／空集合／不含該受眾 ⇒ `_OUTLINE_UNAVAILABLE`，⛔ 不留 falsy 回退；刪單數 `app.state.agent_outline` 與 prospect 回退分支；baseline 受眾失敗 ⇒ 外層 except（開關開＝啟動紅）維持。
  - **F5** `vendor_business_types` 一回合只解析一次，轉發到三個新呼叫點：`build_canon_toc`／`selector.select`／`build_canon_sections`。
  - **F4** `test_identity_taint_ast_req.py::_SINK_NAMES` 加 `build_canon_sections`／`from_canon`，並補一條 `_POSITIVE_CONTROLS`。
  - **F9** 降級外顯沿用 `health.py::_canon_state()` 既有的 `_index_state()` 判定（⛔ 不做第二份判定），只驗「非 ready ⇒ 節紅」成立；violation `candidate_fallback_toc_only`（取代 `candidate_fallback_full_outline`；同片改名 `tools/agent_eval.py::_CANDIDATE_VIOLATION_KINDS` 與 fallback 率三處消費點、`test_agent_eval_req` 的 `candidate_fallback：n/n` 斷言）。**文件同片出貨**（否則不變量 41 紅）：`docs/architecture/SYSTEM_ARCHITECTURE.md` 「兩種『沒有候選』」段（含 `candidate_fallback_full_outline` 字面與「原樣整份大綱」語義）改寫為 D′ 語義，同檔 `miss_kind` 值域表改五值（加 `empty_toc`、刪 `audience_mismatch`）；S3 對該檔的範圍排除此段。
  - **F8（淨收益，⛔ 之後別加回）**：`agent_state["outline"]` 不再進持久化 session 狀態（層 2／3 正是為它而設）；`make_outline_resolver` 的 `cache` 分支（對 requester 不套 `canon_visible`、未審節當 `ok=True`）刪除。
- 驗收（否定帶正對照）：
  ① 同題同身分：改前後 `candidate_ids`、sections id 序列、toc 文字、**組出的 `CandidateOutlineDoc.text` 全文**逐位元相同（凍結題集＝九架中 `reviewed` 細目所掛的 `approved` 講法，依 `A→I`、檔內順序取前 10 條當查詢×售前／業者兩身分（腳本挑選並印出 id；正本 sha 已釘 `b94acd638e35`），改前 dump 到 `inputs/s2-freeze-before-20260916.json`，改後 diff 為空；突變正對照：`build_canon_sections` 的 text 加前綴 ⇒ 此條必紅）。
  ①b 啟動三數重釘：S2 後啟動印出的售前 k_upper／toc_tokens 與業者 k_upper／toc_tokens 與 S1 ② 所釘（1,931／373；873／283）逐數相等、誤差 0（突變正對照：餵入集合改成前 5 節 ⇒ 必紅）。
  ② 降級：monkeypatch `_embed_query` 回 None ⇒ sections 零細目節、toc 存在、violation 含 `candidate_fallback_toc_only`、注入段 token ≤ toc 上限（正對照：不 patch 時 5 節）。
  ③ 降級外顯：`_index.prepare` 拋例外 ⇒ health `checks.canon.index.<audience>.state != "ready"` 且 `compute_agent_health` 判紅；每回合 `miss_kind="index_unavailable"`＋violation `candidate_fallback_toc_only`（正對照：正常啟動 `ready`＋綠）。
  ④ 隔離改釘本體（合成 canon fixture，四格各帶正對照）：(a) `target_user=[property_manager]` 細目 ∉ 售前回合的 `sections`／`text`／toc（正對照：`[prospect, property_manager]` 出現）；(b) `business_types: [rental]` 細目對業者身分不可見（D-002 回歸網，⛔ 不得補 `IS NULL` 放行）；(c) `reviewed` 缺的細目**連標題都不進** `sections`／`text`／toc；(d) `system_admin` 身分（路由到 property_manager 受眾、`effective_target_user` 仍 `system_admin`）看不到 `[property_manager]` 細目——唯一抓得到「用 audience 標籤當過濾鍵」的格。`test_outline_audience_mismatch_fails_closed`／`test_audience_mismatch_returns_no_fine_sections` 改寫為此四格（**改寫不更名**：別窗 `.kiro/specs/testing-traceability/traceability-matrix.*` 以測試名釘住）。
  ④b **F1 契約**：`ids` 含一個未審／不可見細目 ⇒ raise 被接成 toc-only 降級，該 id 與標題不出現在 `sections`／`text`，violations 同時含 `candidate_invisible_id` 與 `candidate_fallback_toc_only`（既有 `candidate_selector_error` 只在 selector 本身拋例外時記；正對照：全可見 ⇒ 5 節）。
  ⑤ 例外不逸出：monkeypatch `build_canon_toc` 拋例外 ⇒ 回合完成、`miss_kind="empty_toc"`＋violation `candidate_toc_error`（正對照：不 patch 時 toc 非空）；**新增**測試（`test_candidate_selector_req` 現無值域相等斷言）：`set(get_args(MissKind)) == {"hit","none_visible","no_candidate","index_unavailable","empty_toc"}`，每值在計畫文內有 S2 後的產出點（`select`：hit／none_visible／no_candidate；`_select_outline`：index_unavailable／empty_toc）；移除 `empty_toc` 或留 `audience_mismatch` ⇒ 必紅。
  ⑥ **F2 fail-closed**：移植 `test_agent_turn_pm_outline_req.py::test_failed_pm_view_skips_pm_only_and_fails_closed`——業者身分超限 ⇒ `agent_audiences == frozenset({"prospect"})`、`preflight(PM) == ERR_AGENT_UNAVAILABLE`、`preflight(PROSPECT) is None`；**F2 直接組 `FacadeDeps`**（`agent_runtime`／`agent_session_store` 皆非 None，⛔ 不經 app 啟動 fixture，因 baseline 失敗會在 preflight ① 短路）：`agent_audiences` ∈ {屬性不存在, None, 非集合, `frozenset()`} 四形狀各斷言 `preflight(PROSPECT) == ERR_AGENT_UNAVAILABLE`，正對照 `frozenset({"prospect"})` ⇒ None（`FacadeDeps` 須帶合法 `api_key_id`／`vendor_id`／`session_id` 與未觸頂的時速，否則 preflight ③④ 會以無關理由回 `INVALID_INPUT`；突變：`_outline_for_audience` 改回空集合讀單數屬性 ⇒ ≥1 形狀翻 None ⇒ 必紅）；tenant 反例一行。
  ⑦ 死輸入零殘留：`grep -rn 'agent_state\[.outline.\]\|agent_outlines\|OUTLINE_KEY\|outline_doc=\|agent_outline\b' rag-orchestrator --include=*.py` 非測試 0 命中（正對照：`agent_audiences` 命中）；`agent_session.py` 一併改：`OUTLINE_KEY`、`KEY_SPECS`、模組層 `assert len(KEY_SPECS) == 11`、`AgentSession.outline` property、`__all__`、docstring「11 個鍵」；`test_key_specs_covers_exactly_eleven_keys` 改名 `..._ten_keys` 並改 10。
  ⑧ `outline_sha`：health `outline_version` == `canon.sha256.jgb`；trace `snapshot.outline_sha` == `canon_sha256`。
  ⑨ 改名零殘留：`grep -rn 'candidate_fallback_full_outline\|audience_mismatch' rag-orchestrator docs --include=*.py --include=*.md` 0 命中（正對照：`candidate_fallback_toc_only` 於 `runtime.py`／`tools/agent_eval.py`／`SYSTEM_ARCHITECTURE.md` 各命中）；`python3 scripts/audit/checks/doc_inline_symbols.py` PASS。
  ⑨b **F3 可否證**：`python3 scripts/audit/checks/agent_boundary.py --self-test` 全綠、不變量 29／29b PASS；突變驗證：把 `build_canon_sections` 內的 `canon_visible` 呼叫拿掉 ⇒ 29b 必紅（正對照：還原後綠）；`_self_test_29b` 的 `clean_src` 假樹同步加 `build_canon_sections`。`make audit` 全綠；unit＋integration 綠。
  ⑩ **F5 一致性**：`test_select_outline_forwards_resolved_vendor_business_types_to_all_three_call_sites` 改為三個新呼叫點收到同一個 sentinel 物件、`resolve_vendor_business_types` 在 `_select_outline` 範圍內只呼叫一次（同回合 `kb.get` 經 `make_outline_resolver` 的再解析不計；正對照：任一點 patch 掉 ⇒ 紅）。
- 前置：security-reviewer 已完成（本節）；送 plan-verifier 時附其 F1–F9 處置。執行者：`executor`。verifier 針對 ①①b②③④④b⑤⑥⑦⑨⑨b⑩。

### S3 文件／釘值／鏡像（不含程式簽名改動）
- 出貨：`design.md` 元件 5（含現況段）／元件 7／正本生命週期／資料轉換／監控／錯誤處理依草案 §2 A 表＋D 表逐列改（原句→新句，⛔ 不留舊碼塊）；`docs/api/mcp-facade.md` §10 env 名；`docs/deployment-runbook.md` env 三行；`docker-compose.dev.yml`／`docker-compose.prod.yml` env 註解；`.kiro/specs/agentic-mcp-orchestration/design.md` 兩處 env 名；本 spec `requirements.md` env 名；`docs/architecture/SYSTEM_ARCHITECTURE.md` 啟動段（⛔ 不含 S2 已改的「兩種『沒有候選』」段與 `miss_kind` 值域表）；`.claude/MAP.md` 的「受眾不符 ⇒ `audience_mismatch`」句改為 `canon_visible` 隔離句；`tasks.md` §9.7 釘子測試清單與 9.8 落地紀錄；`.agents/`／`.codex/` 鏡像手動同步；`canon/README.md` 降級句。
- 驗收：不變量 41／42 綠；refcheck 綠；`grep -rn 'build_audience_outline' docs .kiro/specs/*/design.md` 只剩「離線工具」語境（正對照：`check_turn_budget` 命中）；**全範圍舊符號零殘留**：`grep -rn --include=*.py --include=*.md --include=*.yml --include=*.sh 'OUTLINE_TOKEN_LIMIT_DEFAULTS\|OUTLINE_TOKEN_LIMIT_ENV\|default_token_limit\|AGENT_OUTLINE_TOKEN_LIMIT_' rag-orchestrator docs docker-compose.dev.yml docker-compose.prod.yml .kiro/specs/*/design.md .kiro/specs/*/requirements.md` 0 命中（`--include` 白名單排除 `tests/.coverage.json` 執行期產物），明列必改檔：`docs/deployment-runbook.md`、`docs/api/mcp-facade.md`、`docs/architecture/SYSTEM_ARCHITECTURE.md`、`rag-orchestrator/canon/README.md`、`docker-compose.dev.yml`、`docker-compose.prod.yml`（註解，`docker compose config -q` 仍過）、`.kiro/specs/knowledge-outline-and-intent-architecture/design.md`、`.kiro/specs/knowledge-outline-and-intent-architecture/requirements.md`、`.kiro/specs/agentic-mcp-orchestration/design.md`；明示排除：`.kiro/specs/*/tasks.md` 與 `validation_gap.md`（歷史帳／快照，沿不變量 42 的排除規則）（正對照：同 grep 對 `OUTLINE_K_TOKEN_LIMIT` 命中）。
- 執行者：`mech-executor`。verifier 針對 grep 與稽核。

### S4 上線前置：toc-only 降級答到率回測（反證代理條件 ii；⛔ 部署由業主）
- 出貨：`tools/agent_eval.py` 兩臂（現況「可見已審全集」降級 vs D′「toc only」降級）對凍結題集跑一輪；報告 `inputs/backtest-9.8-degrade-20260916.md`。
- 驗收：命題／最小材料／推翻條件先寫（記憶 `feedback_hypothesis_driven_verification`）；推翻條件＝答到率或 `no_grounding` 明顯劣於現況（腰斬）⇒ 停，降級改「toc＋K 上界內固定子集」另立切片。
- 執行者：主會話派情境代理；verifier 針對報告數字可回溯。

## 4. 回滾
S1／S2 各單一 commit，`git revert` 即回；S2 若 revert，S1 仍成立（尺獨立於物件）。無資料變更。

## 5. 停點
- S1 ②：現行正本任一身分 `check_turn_budget` 超限 ⇒ 停（表示 2,500／8,000 訂錯，交業主）。
- S2 ①：改前後 `candidate_ids` 不同 ⇒ 停（表示現組節規則與 `build_outline` 不等價）。
- S4 推翻條件命中 ⇒ 停。
- 線上 `.env` 若設有 `AGENT_OUTLINE_TOKEN_LIMIT_*` ⇒ 業主自查後改名（草案 §4 第 9 題），⛔ 我不讀 `.env`。

## 6. 成本
S1 executor 1＋verifier 1；S2 security-reviewer 1＋executor 1＋verifier 1；S3 mech 1＋verifier 1；S4 情境代理 ≤ 3＋verifier 1。plan-verifier 每片 1。

## 7. 前置
DSP-059 已記；正本 210 條在工作樹（`canon/jgb/` 在 git 為 `??` 未追蹤，`git ls-files rag-orchestrator/canon/jgb` 為空；dev 容器掛 `./rag-orchestrator:/app`，測試讀到的就是工作樹這份）；容器 `docker compose -f docker-compose.dev.yml` 可跑測試。
