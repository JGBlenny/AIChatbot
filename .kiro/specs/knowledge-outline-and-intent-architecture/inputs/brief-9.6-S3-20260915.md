# 9.6 S3 執行契約（security-executor）— 2026-09-15

前置：S1 CONFIRMED；S2 CONFIRMED（2026-09-15 fresh verifier：53/0 不符、未審 15 受眾一致、重導出逐位元同、跨架講法現況 0 重複；advisory A3＝跨架唯一無守門 → 本片規格 1）。受測物指紋：`canon_sha256=2684fe7b77c8ee062d61197ab2245ca425c2d27d711553acaa0f51fab413f0af`。母計畫 `plan-9.6-library-canon-20260915.md` v4 §2 表、§3 S3、§5。定案 DSP-058。**這是唯一的行為切換點，單一不可分割落地：程式＋所有簽名呼叫點＋測試＋封存同一批改完，落地時樹必綠。**

## 結果（一句）
agent 路徑改讀 `canon/jgb/`（一份正本），依靜態身分產 prospect／pm 兩份**受眾視圖**；受眾隔離靠細目 `target_user`＋`business_types`，視圖零外洩、audience 不符 fail-closed；舊兩份正本封存。

## ⛔ 邊界
- ⛔ 不讀 `.env`、不印金鑰；⛔ git stash／commit／push；⛔ 不碰 `.agents/`／`.codex/`（主 session 同步）；⛔ 不對 DB 寫入；⛔ 不動 `canon_visible` 的 b2c 分支語義（§5-3 REJECT）；⛔ 不動 `build_visibility_predicate`；⛔ 不改 `scripts/audit/checks/agent_boundary.py` 的規則②（`_references_name(canon_visible, TARGET_USER_NORMALIZER)`）——`canon_visible` 本體必須仍直接呼叫 `VendorKnowledgeRetrieverV2._effective_target_user`。
- ⛔ 不手改 `canon/jgb/*.md`／`CATALOG.md`（hook 有 diff_report 閘；資料已由 S2 落定）。
- 看舊版 `git show HEAD:<path>`；否定結論帶正對照；測試在容器：`scripts/run-tests.sh unit|integration <args>`。

## 範圍（可改）
程式：`rag-orchestrator/services/agent/canon/canon_parser.py`、`canon_assembler.py`、`rag-orchestrator/services/agent/outline.py`、`runtime.py`（只 `_select_outline`／`_selector_for` 相關段）、`rag-orchestrator/app.py`（`_init_agent_runtime`）、`rag-orchestrator/services/agent/health.py`（`_canon_state`）、`.claude/hooks/outline_gate.py`。
稽核：`scripts/audit/checks/agent_boundary.py`（`CANON_VISIBLE_CALLERS`＋`_self_test_29b` 的 `clean_src`）、`scripts/audit/checks/canon_visibility_reconcile.py`。
工具：`rag-orchestrator/tools/canon/index_eval.py`、`tools/agent_outline_dump.py`、`tools/agent_eval.py`、`tools/gapmap/coverage_map.py`。
測試：`tests/unit/agent/test_canon_assembler_req.py`、`test_outline_unit_req.py`、`test_candidate_outline_req.py`、`test_agent_policy_kb_outline_req.py`、`test_candidate_selector_req.py`、`test_agent_turn_pm_outline_req.py`、`test_canon_parser_req.py`、`test_canon_export_sync_req.py`、`test_fine_index_content_parity_req.py`、`test_index_eval_req.py`、`test_probe_three_arm_req.py`、`test_vendor_business_types_resolution_req.py`、`tests/unit/_meta/test_outline_gate_req.py`、`tests/unit/audit/test_agent_boundary_req.py`、`tests/unit/audit/test_canon_invariants_req.py`、`tests/integration/agent/test_canon_startup_req.py`、`test_outline_req.py`、`test_review_state_visibility_req.py`、`test_visible_subset_sql_equiv_req.py`；fixtures 目錄；新測試檔 `tests/unit/agent/test_library_view_req.py`（本片 ①～⑥⑨）。
資料／文件：`rag-orchestrator/canon/{prospect,property_manager}.{md,json}` → `docs/archive/2026-09/canon-pre-library/`（`git mv`，各 `.md` 首行前加表頭「⛔ 不是現況：2026-09-15 DSP-058 改為 `canon/jgb/` 圖書館形態；本檔已掉出 hook `CANON_RE` 掃描」）；`rag-orchestrator/canon/README.md` 改寫成圖書館形態（重導出指令改 `parse_canon_dir`＋`export_json`／`export_catalog`）。⛔ `.claude/MAP.md`／`DECISIONS.md` 由主 session 改。

## 規格（對應計畫 §2）
1. **parser**：`parse_canon_dir` 加「跨架講法唯一」（NFKC 同文的 approved／proposed 講法不得出現在兩個細目，跨架亦然 ⇒ `CanonFormatError`；同架內既有檢查不變）與「架 front matter `title` 須等於架內 `## 標題`」；hook 對 `canon/jgb/*.md` 的 `check_phrasing_unique` 改為以整個 `jgb/` 目錄為作用域（同值規則）。
2. **assembler**：`load_canon_or_die(canon_dir)`（無 audience 參數）：`parse_canon_dir(base/"jgb")`＋`base/"jgb.json"` 逐位元＝`export_json` 重導出＋`base/"jgb"/"CATALOG.md"` 逐位元＝`export_catalog` 重導出，任一不同 ⇒ `CanonLoadError`。`register_canon(doc)`／`get_canon()`／`reset_canon_registry`／`canon_registry_shas() -> {"jgb": sha}`。`canon_visible` 拆：`_axes_visible(effective_target_user, mode, fine, vendor_business_types)`（受眾＋業態，不看 reviewed）；`canon_visible(identity, fine, *, vendor_business_types)`＝`fine.reviewed_by is not None and _axes_visible(VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user), identity.mode, fine, vbt)`——對外真值表逐格不變（`test_visible_subset_sql_equiv_req` 釘）。`build_outline(doc, audience, identity, *, vendor_business_types)`：只納 `_axes_visible` 為真的細目；其中 `canon_visible` 真 ⇒ 含內容 `citable=True`，假（未審）⇒ 標題＋`text=""`＋`citable=False`（今日語義）；`_build_doc(audience=audience, …)`，⛔ 不得填 `doc.audience`（＝`jgb`）。`build_canon_toc`／`resolve_canon_section` 不變。
3. **outline**：`_STATIC_TOC_IDENTITY` 不變；`build_audience_outline(audience)`：`canon = get_canon() or load_canon_or_die(resolve_canon_dir())`（第一個受眾載入並註冊，第二個沿用同一份），`build_outline(canon, audience, static_identity, …)`＋toc，`check_budget(doc, default_token_limit(audience))`；`default_token_limit(audience)` 改 `min(env 值 or 常數, OUTLINE_TOKEN_LIMIT_DEFAULTS[audience])`；`make_outline_resolver`：受眾 ∉ `_STATIC_TOC_IDENTITY` ⇒ 一律 `_no_match()`，⛔ 不取 doc。`build_prospect_outline` 薄別名保留。
4. **runtime `_select_outline`**：`canon = get_canon() if audience in _STATIC_TOC_IDENTITY else None`；`canon is None` ⇒ 沿用現行分支；**`outline.audience != identity.resolved_audience()` ⇒ fail-closed：回傳不含任何細目節的 outline（只留 toc 節或空）＋`sel_meta.miss_kind="audience_mismatch"`**（⛔ 不回未過濾整份）。`_selector_for` 不變。
5. **app**：`_init_agent_runtime`：load 一次（失敗＝整條 agent 路徑不可用，走既有外層 except 語義）；`FineIndex.prepare(canon)` 一次；`register_index(aud, index)` 兩受眾指同一物；`selectors[aud] = CandidateSelector(index)`；視圖 `outlines[aud]` 仍逐受眾。`health._canon_state` 讀 `canon_registry_shas()` 新形狀，docstring 註明 `index_registry_states` 的 `entries`／`content_keys`／`prepared_sha` 兩受眾相同、⛔ 不當受眾覆蓋率指標。
6. **29b**：`CANON_VISIBLE_CALLERS` 加 `build_outline`；`_self_test_29b` 的 `clean_src` 與 `test_agent_boundary_req._CANON_CLEAN_SRC` 同步加第三個 caller（`build_outline` 內須直接出現 `canon_visible(` 呼叫；`_axes_visible` 另呼叫）。`canon_visibility_reconcile.py`：`load_canon_or_die(resolve_canon_dir())`，兩組身分（b2b pm／b2b prospect）各命中 ≥1（既有正對照）。
7. **工具**：`index_eval.py`：`--canon` 接目錄（`_load_fines`：目錄 ⇒ `parse_canon_dir`，檔 ⇒ `parse_canon`；`freeze_materials` 對目錄記 `parse_canon_dir(...).canon_sha256`）＋`--target-user <值>`（只留 `fine.target_user` 含該值，⛔ 不走 `canon_visible`）；`agent_outline_dump.py`／`agent_eval.py` 改 `build_audience_outline`／新簽名；`coverage_map.py` 改 `parse_canon_dir`＋`canon.name`（`audience` 欄由 `--audience` 指定）。
8. **測試**：既有測試依新簽名改 fixture／id（`prospect/X/slug`→`jgb/X/slug`）；`test_canon_startup_req.py` fixture 改複製 `canon/jgb/`＋`jgb.json`（含 CATALOG）；`test_canon_assembler_req` 釘 12＋3 未審 id 改新 id；`test_build_prospect_outline_registers_same_doc_and_leaves_sha_unchanged` 作廢，改釘「prospect 視圖細目 id 集合＝`runs/library-20260915/id_map.json` 映射後的舊 prospect 集合（38）」；三條被「15 條未審」打破的 integration 舊釘（`test_canon_startup_req::test_resolver_applies_visibility_and_toc_is_not_citable`、`test_outline_req::test_prospect_outline_is_assembled_from_canon`、`test_visible_subset_sql_equiv_req::test_real_prospect_canon_visibility`）改成對現況（含未審不可引用）成立。⚠️ `test_confirmation_tokens_req` ×4＋`test_agent_turn_req::test_confirm_token_is_bound_to_the_namespaced_session` 的紅＝`_StubVerifier.verify` 缺 `audience` kwarg（commit `fee4d09c` 的既有殘骸），**⛔ 不在本片範圍**，⑫ 的判準對它們排除。

## 驗收（全部要跑、貼數字；合成 fixture＝`tests/fixtures/canon_jgb/` 或新建 pm-only／prospect-only／共用／未審各 1 的目錄）
① 視圖零外洩：pm-only 細目的 **id 與標題** 不在 prospect 視圖 `text`；正對照：共用細目兩視圖都在、prospect-only 在 prospect 視圖；兩視圖 section 數皆 > 0。
② `resolve_canon_section("outline:<pm-only>")` 對 prospect 身分 `NO_MATCH`；正對照 pm 身分回內容。
③ `CandidateSelector.select` 以 `_FakeBackend`（先例 `test_agent_turn_pm_outline_req.py`）讓 pm-only 最相似：prospect 身分不回它；正對照 pm 身分回它。
④ `Identity(mode="b2b", target_user="tenant")` 可見集合＝∅（正對照 pm 非空）；tenant 受眾經 `make_outline_resolver` ⇒ `NO_MATCH`；`_select_outline` 對 tenant 走 `canon is None` 分支。
⑤ `OutlineDoc.audience` 與身分不符 ⇒ `_select_outline` 回傳不含細目節（正對照：相符時含候選）。
⑥ 候選 ⊆ 視圖 section id；塞視圖外 id ⇒ fallback 不崩。
⑦ 真實正本：15 條未審在本受眾視圖標題現身、`text==""`、`citable==False`，在另一受眾視圖連標題都沒有；`kb.get("outline:<未審 id>")` 兩身分皆 `NO_MATCH`；正對照 `jgb/A/account-registration` 在 prospect 視圖…⚠️ 它本身是未審（S2 ②），改用已審的 `jgb/B/team-management-overview` 做正對照。
⑧ 啟動：`test_canon_startup_req.py` 綠；`canon_registry_shas()=={"jgb": …}`；兩視圖組出（貼各自 section 數與 token_count）。
⑨ 預算：`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT=999999` ⇒ 上限仍 12000（正對照設 1 ⇒ `check_budget` raise）；真實兩視圖 `token_count` ≤ 12000／8000。
⑩ 29b：**未改檢查器規則**下該 checker 自測綠（含「現樹 canon_visible 通過」），且暫時拿掉 `build_outline` 的 `canon_visible(` 呼叫時規則③紅（驗一次放回）。
⑪ 完整性 grep（全 repo `*.py`＋`.claude/skills/**/*.py`＋`scripts/**/*.py`）：`canon\.audience|build_prospect_outline|get_canon\(|register_canon\(|load_canon_or_die\(|build_outline\(|budget_tokens|parse_canon\(|canon/prospect\.md|canon/property_manager\.md` 命中檔案集合 ⊆ 本 brief「範圍」＋`docs/archive/`；正對照 `app.py`／`outline.py` 必中；貼命中清單。
⑫ 樹綠：`scripts/run-tests.sh unit` **全套** 0 failed；`integration tests/integration/agent` 的 failed 集合 ⊆ {上述 5 條 `_StubVerifier` 案}（多一條即失敗）；`tests/unit/audit/` 綠；`make audit` 的紅只剩不變量 3／41（既有）。
⑬ `index_eval --canon rag-orchestrator/canon/jgb --target-user prospect`：先 `--dry-run`（貼 `n`／`articles_with_gold`；指到不存在目錄 ⇒ 大聲失敗），再全跑；母體 38、id 經 `id_map` 對得上 `inputs/index-eval-recut-20260915.json`；per-type r@5 與該檔逐項比對，有差列出並解釋（母體／講法集／向量快取三者逐一對），⛔ 不擅自改基線。
⑭ 封存：`git status` 顯示兩份舊檔為 `R`（rename 到 `docs/archive/2026-09/canon-pre-library/`）且表頭已加；`rag-orchestrator/canon/` 只剩 `jgb/`、`jgb.json`、`README.md`。

## 交件格式
改／新增／搬移檔清單；①～⑭ 每條指令＋輸出摘要（含數字）；取捨與已知債；安全面自述（哪裡新增了 fail-closed、哪裡刻意沒動）。
