# Plan 切片 KOIA-3.2：`canon_assembler.py`＋啟動契約——agent 大綱改由正本組裝（2026-09-07）

> 狀態：**收案（2026-09-07）**：業主核准 (a)＋§8 照准；security-executor 實作（另加 front matter 受眾＝檔名檢查）；fresh verifier **CONFIRMED**（unit 959／integration 154；17 組身分×細目對 `build_visibility_predicate` 實跑零分歧；`make audit` PASS、29b 綠）。已知債：**P3** `build_outline` 未套 `canon_visible`——同一正本內對其他角色的細目內容仍進 system prompt（現況 38 條全 prospect 不可觸發；4.1 每回合子集時必須套，寫進 tasks 4.1）；P4 front matter 位元變動只改 `canon_sha256` 不改 `OutlineDoc.sha256`（同源檢查與 health 仍抓得到）；P4 空 `business_types`／`target_user` 與 SQL 對等的前提是匯入寫 NULL 而非 `'{}'`（7.x 驗）。前史：三輪 plan-verifier 皆 REVISE、皆已 FIX 進本文。security-sensitive（resolver／toc 套可見性＝附錄 E F7 修補）：security-reviewer 唯讀分析已完成（§7），核准後交 `security-executor`，完成後 fresh `verifier`。核准前 ⛔ 不寫碼。對應 tasks 3.2、design 元件 5、R2.6／R5.4／R5.9。前置 3.1 已收案（`fe5befa6`）、正本已 commit（`89b3e331`：`canon/prospect.md`＋`.json`，38 細目全 reviewed）。

## 0. 結論先講

售前 agent 的大綱從「DB 撈 29 列＋寫死分類表」改成「啟動時讀 git 正本、重算 sha、逐細目成節」；目錄與 `outline:*` 解析都先過「可見且已審」；正本缺檔／`.md` 與 `.json` 不同源／格式錯 ⇒ 啟動紅（只在 agent 開關打開時）。舊分類表五個常數退役。

## 1. 結果（outcome）

1. `services/agent/canon/canon_assembler.py`（新）：
   - `load_canon_or_die(canon_dir, audience) -> CanonDoc`：`audience` 限 `identity.Audience` 字面；`canon_dir` `Path(...).resolve()`；讀 `<audience>.md` → `parse_canon`；讀 `<audience>.json` 位元組，**與 `export_json(doc, <tmp>)` 重導出的位元組逐位元比對**（不是只比 `canon_sha256` 欄——sha 只算 `.md`，`.json` 內容改一位元 sha 仍相等，security-reviewer P1-1）；缺檔／不等／`CanonFormatError` ⇒ raise `CanonLoadError`（訊息含 resolved path）。內容**只**來自 `.md` 解析結果。
   - `resolve_canon_dir() -> Path`：預設 `<rag root>/canon`；`AGENT_CANON_DIR` 覆寫只在 `DB_ENV=test` 生效，否則忽略並 log warning；health 印 resolved path。
   - `build_outline(doc) -> OutlineDoc`：每細目一節，`id=fine.id`、標題＝`fine.title`（`_build_doc` 已自動加 `【<id>】` 前綴，⛔ 不重複加）、`citable=(fine.reviewed_by is not None)`、未審只出標題；粗目 G／F 承接原 `DSP009_DELIBERATE_GAPS`／`_CTA_TEXT` 的角色（正本已有 `G/*`、`F/contact-sales-demo`）。
   - `canon_visible(identity, fine, *, vendor_business_types: frozenset[str]) -> bool`（**3.3 `FineIndex.visible_subset` 的逐細目前身，規則照 design 元件 6 原文**）：`fine.reviewed_by is not None` ∧ 依 **與 SQL 同式的分支判準** `is_b2b = identity.target_user ∈ {property_manager, system_admin} or identity.mode == "b2b"`（⛔ 不是只看 mode——`build_visibility_predicate` 檔頭「手抄會漏的 9 條」之⑤；`Identity(target_user=property_manager, mode=b2c)` 必須走嚴格分支）——b2b：`fine.business_types ∩ {system_provider} ≠ ∅` ∧ (`target_user` 空 ∨ `tu ∈ fine.target_user`)；b2c：(`fine.business_types` 空 ∨ ∩ `vendor_business_types` ≠ ∅) ∧ (`target_user` 空 ∨ `tu ∈ fine.target_user` ∨ `all_users ∈ fine.target_user`)；`tu = VendorKnowledgeRetrieverV2._effective_target_user(identity.target_user)`（design 明訂重用、⛔ 不另寫；`outline.py` 的 `_TOC_AUDIENCE_TARGET_USER` 是 pm／tenant TOC 的窄映射，兩者用途不同、不合併）。`vendor_business_types` 由呼叫端傳（3.2 只有 prospect＝b2b，傳 `frozenset()`；b2c 分支只由 unit 正反例覆蓋）。**刻意不套的 SQL 條件**（對照 `build_visibility_predicate`）：`vendor_ids`（正本無 vendor 欄，匯入寫 NULL ⇒ 條件恆真）、`is_active`（正本無此旗標，未審＝不可引用由 `reviewed_by` 承擔）、保留分類 `系統脈絡／對話規則`（正本無此類細目）；**不新增** SQL 沒有的 `doc.audience == resolved_audience()`（受眾隔離靠「載入哪一份正本」，不靠逐細目比對）。
   - `build_canon_toc(doc, identity, *, vendor_business_types) -> OutlineSection`（另名，⛔ 不與 pm／tenant 的 `outline.build_toc(db_pool, audience, vendor_id)` 同名）：`outline:toc`、`citable=False`、只列 `canon_visible` 的細目一行 `<fine.id>｜<title>`。
   - `resolve_canon_section(doc, identity, section_id, *, vendor_business_types) -> ToolResult`：`outline:toc` 回 toc；`outline:<fine.id>` 先 `canon_visible`，不可見／未審／不存在 ⇒ `NO_MATCH`；可見已審 ⇒ 該節內容、`citable=True`。
2. `services/agent/outline.py`（簽名不變，`app.py` 不改）：
   - `build_prospect_outline(db_pool)`（`db_pool` 保留於簽名、不再使用）：`load_canon_or_die(resolve_canon_dir(), "prospect")` → `build_outline(doc)` → **附 `outline:toc` 節**＝`build_canon_toc(doc, identity=Identity(mode="b2b", target_user="prospect", vendor_id=0), vendor_business_types=frozenset())`（啟動時用售前的**靜態身分**算一次；prospect 正本單一受眾、b2b 分支不依 vendor，故啟動時可算；**每回合的候選子集與 toc 是 4.1 `CandidateOutlineDoc`**，本片不做）→ `check_budget(doc, min(default_token_limit("prospect"), canon.budget_tokens))`（P2-3）。**`CanonDoc` 載體**：`OutlineDoc` 是 pydantic `BaseModel`（塞未宣告屬性會 raise、宣告欄位會被驗證／重建並進 `model_dump`），⛔ 不掛在 `OutlineDoc` 上；改由 `canon_assembler` 模組層註冊表 `register_canon(audience, doc)`／`get_canon(audience) -> CanonDoc | None`（`build_prospect_outline` 載入後註冊；提供 `reset_canon_registry()` 供測試隔離）。`OutlineDoc.sha256`、`OutlineDocLike`、`model_dump` 完全不變。
   - `make_outline_resolver(cache)` 簽名與 `OutlineResolver = Callable[[Identity, str], ToolResult]` 契約不變；內部：對 cache 的每個 audience 鍵查 `get_canon(audience)`，有 ⇒ 每回合呼叫 `resolve_canon_section(canon, identity, kb_id, vendor_business_types=frozenset())`（identity **per-call**，⛔ 不綁在工廠）；無註冊（pm／tenant TOC）⇒ 既有邏輯不變。這就是 F7 修補在產線的接線點（`app.py:_init_agent_runtime` 建的就是這個 resolver）。
   - **不再讀 DB**：`_fetch_prospect_pool_rows` 退役（§8.2）；退役 `SIX_MODULES`／`_classify_row`／`_classify_module_row`／`_CTA_TEXT`／`DSP009_DELIBERATE_GAPS`／`_extract_boundary_sentences`。**保留** `_fetch_toc_rows` 與 `build_toc(db_pool, audience, vendor_id)`（pm／tenant 現役，design 元件 5：vendor 過濾不得拿掉）。
3. `app.py::_init_agent_runtime`：不變（raise 在 `_agent_configured()` 為真時升啟動紅、否則 fail-soft——既有機制）；`health.py` 印 `canon_dir` resolved path 與 `canon_sha256`。
4. 不變量 29（P2-2）：`check_29_predicate_single_source` 對每個 target 強制 `_calls_predicate`（必須呼叫 `build_visibility_predicate`），記憶體鏡像 `canon_visible` 不可能通過 ⇒ ⛔ 不動 29 的 targets；`_fetch_prospect_pool_rows` 退役後從 29 targets 移除（同步 `test_29_current_search_functions_use_single_source` 釘死清單）。**另立 `check_29b_canon_visibility_single_source`**（同一 CHECKS 群、同 FAIL 語義）：以 `_func_node(("services/agent/canon/canon_assembler.py","canon_visible"))` 定位；規則＝存在、AST 內引用 `_effective_target_user`、且同檔 `build_canon_toc` 與 `resolve_canon_section` 的 AST 都呼叫 `canon_visible`（缺一 ⇒ FAIL）、`canon_visible` 內無 `vendor_ids`／`is_active` 字面（那是刻意不套的 SQL 條件，出現＝手抄）；meta 測試：真樹綠、三種假樹紅。「與 `build_visibility_predicate` 等價」的契約測試留 3.3（design 元件 11）。
5. 測試與文件更新（P2-1）：`tests/integration/agent/test_outline_req.py` 兩個以 DB 列為大綱來源的 prospect 測（`test_prospect_outline_includes_only_approved_row`、`test_prospect_outline_sha_reflects_pool_membership`）改為正本組裝形狀——節數＝38＋toc、`source_ids` 為 fine id 語義、**sha 隨 `.md` 位元組變而不隨 DB 列變**（tmp 複本改一位元 ⇒ sha 變、節數不變；UPDATE 池列 ⇒ sha 不變），⛔ 不得靠刪測達成綠；同檔 `test_toc_*` 不動；`tests/unit/agent/test_outline_unit_req.py` 模組層 import 退役名 ⇒ 改寫；`test_review_state_visibility_req.py` 三個測（0 列固定兩節、1 列三節、大綱來源）改為「正本組裝：38 節＋toc、不依 DB 列」（3.1 的 `kb.get` DB 謂詞測試保留）；`docs/knowledge/agent-readable-knowledge.md` 以退役符號為依據的段落同步改寫（CANON：文件不得宣稱已退役的機制）。

## 2. 現況事實（security-reviewer 2026-09-07 實查）

- `parse_canon_text` 的 `canon_sha256` 只涵蓋 `.md` 位元組；`export_json` 把該值與全部內容寫進 `.json` ⇒ 改 `.json` 內容不改 sha。
- `visible_subset` 全 repo 不存在（正對照：`content_reviewed_predicate` 存在）；正本 38 細目 `target_user`／`business_types` 皆繼承 doc 層 `[prospect]`／`[system_provider]`，無細目覆寫。
- 退役名只被測試引用（`test_outline_unit_req.py` 模組層 import 4 個；`test_outline_req.py` 兩測依賴 DB 列語義）；非測試程式碼無引用（`tools/agent_outline_dump.py`／`tools/agent_eval.py` 只用保留的 `build_prospect_outline`），但 `services/agent/canon/review_state.py` docstring 仍提 `_fetch_prospect_pool_rows`（改敘述）。退役清單補死碼：`NON_MODULE_CATEGORY_SECTIONS`、`_MODULE_FALLBACK_*`、`_BOUNDARY_TERMS`、`PRESALES_HANDOFF_MESSAGE` import。
- `agent_boundary.py` 29 的目標 `_fetch_prospect_pool_rows` 缺席時只加 note、仍回 True。
- token：正本內容字元數可重跑 `python3 -c "import sys;sys.path.insert(0,'rag-orchestrator');from services.agent.canon.canon_parser import parse_canon;d=parse_canon('rag-orchestrator/canon/prospect.md');print(sum(len(u) for f in d.fines() for u in f.content_units))"`（≈10.3k）；以 research 1.6 字元/token 估 ≈6.5K token；預設上限 10,000，餘裕約 30%；`_count_tokens` 無 tokenizer 時退化為 `len//2`。`.json` 比對樣式沿 `tests/unit/agent/test_canon_export_sync_req.py`：`export_json` 到暫存檔再讀位元組比對（它寫檔、非記憶體 API）。
- `DB_ENV` 只在 `tests/conftest.py` 讀、只在 dev compose 設；prod 不設 ⇒ 覆寫預設關閉。映像 `COPY . .`＋dev 掛載 `./rag-orchestrator:/app`，`canon/` 未被 gitignore。

## 3. 非目標

- 不做 `FineIndex`／向量匹配／`candidate_selector`（3.3）、不做每回合候選子集與動態 toc（4.1）；不做匯入（7.x）；不動 `build_visibility_predicate`（紅線）；不動 `kb.get`／`kb.search`（3.1 已定）；不改 rubric／正本內容；**不動 `_fetch_toc_rows`、`outline.build_toc`（pm／tenant 現役）與 `app.py`**。
- 不變量 29 與 canon 規則的**等價性**證明留 3.3。

## 4. 驗收（容器內；security-executor 做、fresh verifier 反證）

1. unit：`build_outline` 每細目一節、id＝fine id、標題行含 `【<fine.id>】`；未審細目 `citable=False` 且無內容句；已審 `citable=True`。
2. unit：`load_canon_or_die` 對真正本綠；`.md` 缺 ⇒ raise；`.json` **`canon_sha256` 欄以外**改一位元 ⇒ raise；`.json` 缺 ⇒ raise；`.md` 加一個空白 ⇒ raise（sha 變、json 不同源）；格式錯 ⇒ raise；`audience` 非字面 ⇒ raise。
3. unit：`resolve_canon_dir`：`DB_ENV=test`＋`AGENT_CANON_DIR` ⇒ 用覆寫（resolve 後）；無 `DB_ENV` ⇒ 忽略並 log。
4. unit：`canon_visible` 正反例——分支判準：`Identity(target_user=property_manager, mode=b2c)` 對 `business_types=[]` 細目 ⇒ **不可見**（走 b2b 嚴格分支，與 SQL 一致）；b2b：reviewed＋prospect ⇒ 可見；未審 ⇒ 否；`business_types=[]` ⇒ 否；`target_user=[tenant]` 對 prospect ⇒ 否；`target_user=[]` ⇒ 可見；b2c：`business_types=[]` ⇒ 可見、∩ vendor 非空 ⇒ 可見、∩ 空 ⇒ 否、`all_users` ⇒ 可見；`target_user=None` 走 `_effective_target_user` ⇒ tenant。`build_canon_toc` 只列可見已審；`resolve_canon_section` 對不可見／未審／不存在 id ⇒ `NO_MATCH`，可見已審 ⇒ 回內容且 `citable=True`；**經 `outline.make_outline_resolver` 建出的 resolver** 對同組輸入行為一致（接線證明）。
5. `check_budget` 用 `min(env, doc.budget_tokens)`：把上限降到低於實際 ⇒ raise（正對照：預設綠）。
6. integration（`_agent_configured()` 為真的測試組態；tmp 複本＋`AGENT_CANON_DIR`＋`DB_ENV=test`，⛔ 不動版控正本）：刪 `.md` ⇒ `_init_agent_runtime` 啟動紅；竄改 `.json` 一位元（非 sha 欄）⇒ 紅；未竄改 ⇒ 綠、`app.state.outline_resolver` 對未審／不存在 `outline:*` 回 `NO_MATCH`、對已審回 `citable=True`、`sections` 含 `outline:toc`（`citable=False`）、`health` 印 resolved path＋sha。
7. `make audit`：29 targets 移除 `_fetch_prospect_pool_rows` 後綠（既有三個 29 測試同步）；29b 真樹綠；假樹缺 `canon_visible`／只被一方呼叫／出現 `vendor_ids` 字面 ⇒ FAIL；27／28／30／31／32 不變。unit：`build_prospect_outline` 後 `get_canon("prospect")` 是同一 `CanonDoc`，且 `doc.sha256` 與未註冊時相同。
8. `scripts/run-tests.sh unit tests/unit/agent/ tests/unit/_meta/ tests/unit/audit/`＋`integration tests/integration/agent/` 綠（既有 8 個 conversational integration 失敗為前案，不在本片）；`test_outline_req.py` 至少一條測在正本 `.md` 改一位元時變紅（突變控制）。
9. 實作提醒（plan-verifier 註記）：`canon_assembler` 需 `outline._build_doc`／`OutlineSection`，`outline` 又需 `canon_assembler.get_canon`／`resolve_canon_section` ⇒ 模組層雙向 import 會循環，以函式內 import 解；29 的 meta 測試沒釘 targets 清單，移除 `_fetch_prospect_pool_rows` 不需改它們；29b 進 `CHECKS` 須零參數可呼叫、假樹以 `_read` monkeypatch（比照 `_self_test_29`）。
9. fresh verifier 對主張「啟動由 `.md` 重算並與 `.json` 逐位元同源；目錄與 resolver 套可見性；未審不可引用；退役名無殘留引用」反證。

## 5. 回滾／預算／停損

- 回滾：刪 `canon_assembler.py`、還原 `outline.py`／`health.py`／`agent_boundary.py`／三個測試檔。$0。
- 停損：若 `_fetch_toc_rows` 或退役名仍被非測試模組引用（security-reviewer 說無，執行時再驗），停下列表交裁；verifier REFUTED 兩次即停。

## 6. 對 design 的偏離（待回寫）

- 元件 5 `build_toc(doc, visible)` 簽名改 `build_toc(doc, identity)`（visible 由 `canon_visible` 計算，3.3 換成 `FineIndex.visible_subset`）。
- `canon_visible` 規則（§8.1）若核准，寫進 design 元件 5 與元件 11 契約前身。

## 7. security-reviewer findings 處置

| # | 級 | 內容 | 處置 |
|---|---|---|---|
| P1-1 | P1 | sha 只算 `.md`，`.json` 竄改偵測不到 | FIX：`.json` 與記憶體 `export_json` 逐位元比對；內容只從 `.md` |
| P1-2 | P1 | `visible_subset` 不存在，3.2 要自定規則 | **交業主（§8.1）**：提議 `canon_visible` 規則 |
| P2-1 | P2 | 退役名被測試模組層 import | FIX：改寫三個測試檔 |
| P2-2 | P2 | 29 對 outline 失去目標且靜默略過 | FIX：29 目標改 `canon_visible`（usage ≥2） |
| P2-3 | P2 | 預算 env 無上限、忽略 `budget_tokens` | FIX：`min(env, doc.budget_tokens)` |
| P3-1 | P3 | `AGENT_CANON_DIR` 路徑／audience | FIX：resolve、字面限制、health 印路徑 |
| P3-2 | — | 啟動紅路徑與映像／掛載確認 | 事實，無動作 |

## 8. 待業主核

1. **canon 細目可見性規則**：照 design 元件 6 `visible_subset` 原文（雙分支、`vendor_business_types` 由呼叫端傳、重用 `_effective_target_user`），本片以逐細目 `canon_visible` 實作、3.3 包成 `visible_subset`。**要你核的是「刻意不套」清單**：`vendor_ids`（正本無）、`is_active`（以 reviewed 代）、保留分類（正本無）；以及**不新增** `doc.audience==身分受眾` 比對（隔離靠載入哪份正本）。現況 38 細目全可見。
2. **`_fetch_prospect_pool_rows` 退役**：大綱不再讀 DB（正本是 git、DB 是衍生）；3.1 才接上去的謂詞在此函式隨之退役，但 `kb.get` 的 3.1 接線不變。替代：保留該函式不呼叫（多一條死碼）。建議退役。
3. 測試改寫範圍（P2-1）：`test_outline_unit_req.py` 大幅改寫、`test_review_state_visibility_req.py` 兩處斷言改成正本組裝形狀。
