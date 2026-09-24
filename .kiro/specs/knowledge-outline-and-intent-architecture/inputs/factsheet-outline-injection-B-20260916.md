# 事實表：agent 每回合大綱注入與啟動預算（盤查者 B，2026-09-16）

> 性質：獨立盤查 B（與盤查者 A 互不知情）。每列只寫查得到的東西；⛔ 不推測、⛔ 不提改法、⛔ 不下「應該」。
> 受測物：**工作樹**（⛔ 不是 HEAD）。`git branch --show-current`＝`main`、`git log -1 --format=%h`＝`8ea8617b`（2026-09-12）；
> `git status --short rag-orchestrator/canon` ⇒ `?? rag-orchestrator/canon/jgb/`、`?? rag-orchestrator/canon/jgb.json`、
> `D  rag-orchestrator/canon/{prospect,property_manager}.{md,json}`、` M rag-orchestrator/canon/README.md`——
> 即圖書館正本（DSP-058／9.6／9.7）**尚未 commit**，HEAD 仍是兩份單檔正本。下表程式欄對工作樹，實測欄在 dev 容器（`docker-compose.dev.yml`，掛載 `./rag-orchestrator:/app`、`DB_ENV=test`）跑。
> 正本狀態（`parse_canon_dir("/app/canon/jgb")`）：`version=2026-09-15.0`、`canon_sha256[:12]=b94acd638e35`、細目 210、未審 190。
> 規格欄引用：`design.md`＝`.kiro/specs/knowledge-outline-and-intent-architecture/design.md`（1.19），`requirements.md`＝同目錄（v2.1），`agentic-mcp requirements.md`＝`.kiro/specs/agentic-mcp-orchestration/requirements.md`。

## 0. 一句話結論（純事實）

1. 每回合真正進 system prompt 的是 `CandidateOutlineDoc`＝**K=5 候選細目節＋當回合 `build_canon_toc` 的一節目錄**，經 `wrap_provenance_data("outline", …)` 逐句加標記；啟動組的整份受眾視圖只在「沒有候選機制」的路徑原樣注入。
2. `check_budget` 量的是**啟動期整份受眾視圖**（含未審細目的標題行＋靜態 toc）；每回合候選子集**沒有任何 token 守門**（`_select_outline`／`CandidateOutlineDoc` 零 `check_budget` 呼叫）。
3. 工作樹現況：prospect 視圖 6,187 tokens（上限 12,000，過）；**pm 視圖 10,896 tokens > 8,000 ⇒ `OutlineBudgetExceeded`**——repo 自帶測試 `test_real_views_fit_the_budget` 在容器內 **FAILED**（正對照同檔 `test_env_cannot_raise_the_cap` PASSED）；`tasks.md` 9.7 已把此事記為「DSP-059 候選（等業主裁）」。

## 1. 事實表

| 主題 | 規格原句（引用＋節名） | 程式（檔案::符號＋一句它做什麼） | 實測數字（附指令） | 規格與程式一致？ |
|---|---|---|---|---|
| **每回合注入組成** | design 主要流程圖（prospect 回合）：「`outline ← CandidateOutlineDoc.from_selection(full, sel)`」「`P-->>R: system（persona(audience)＋定義＋K 細目資料段＋toc＋slots）＋dialog`」；design 元件 7 表「候選注入」列：「`outline = CandidateOutlineDoc.from_selection(doc_outline, sel, toc)`…同一物件餵 `_seed_outline_provenance` 與 `build_messages`」 | `services/agent/runtime.py::AgentRuntime._build_turn_context`：`outline = agent_state.get("outline")` → `await self._select_outline(identity, outline, user_message, dialog, acc.violations)` → `_seed_outline_provenance(outline)` 登記為 `tool_results_by_id["outline"]` → `assembler.build_messages(identity, outline, slots, dialog, tool_specs, nonce)`。`services/agent/prompt_assembler.py::PromptAssembler.build`：system 一則＝persona→policy→`_agent_rules_text`→工具一句話清單→`wrap_provenance_data("outline", OUTLINE_TOOL_CALL_ID, [(sec.id, provenance_units(sec.text))…], nonce, headers={id: "【id】title"})`→slots 各一段。`services/agent/outline.py::CandidateOutlineDoc._from_sections`：`sections = picked + [toc]`，text 以 `_build_doc` 的 `【id】title\ntext` 接法組 | 容器一回合（prospect，假向量後端，見 §3 附註 (3)）：候選 5 節＋toc 1 節；`CandidateOutlineDoc.token_count`（無標記）＝**1,889**；進 system 的資料段（含 nonce 行首標記）＝**2,752 tokens／3,777 chars**（候選 2,107＋toc 688）；整則 system（persona＋政策＋鐵則＋大綱段＋2 個 slots，不含工具清單）＝**5,451 tokens**。指令：§3 腳本 (A) `turn.prospect.*` | **一致**（組成＝K 候選＋toc＋slots，同一物件餵兩側） |
| **注入時未審細目怎麼出現** | design 元件 5 `build_outline` docstring：「未審細目：include_unreviewed_titles ⇒ 只出標題行、text=""、citable=False」；plan-9.6 §目標：「未審細目在本受眾視圖以標題現身、內容空、不可引用」 | `services/agent/canon/canon_assembler.py::build_outline`：納入判準 `_axes_visible`（不看 `reviewed_by`），`citable=canon_visible(...)`，未審 `text=""`。但每回合候選來源 `FineIndex.visible_subset`／`canon_visible` 只含已審 ⇒ `from_selection`／`from_visible` **不含未審節**；只有「沒有候選機制」路徑（`_select_outline` 回原 outline）才把 46 條標題行送進 prompt | prospect 視圖 59 節＝13 可引用＋46 只標題；46 條標題行包成資料段＝**2,406 tokens**（§3 腳本 (B) `title_only_block_tokens`）；一回合候選路徑 `candidate_sections=5` 全為可引用節（`sel_meta.candidate_ids` 5 條皆在 13 條可引用集合內） | **一致**（啟動視圖含標題；候選路徑不含） |
| **toc 是否每回合注入、大小** | design 元件 6「第二次機會」：「目錄節 `outline:toc`（citable=False）＋`kb.get("outline:<fine_id>")`」；design 1.16 變更歷史：「toc 每回合依身分 `build_canon_toc`」；design 非功能：「toc ≤300 字」 | `runtime.py::_select_outline`：每回合 `toc = build_canon_toc(canon, identity, vendor_business_types=…)`，所有降級／命中分支都把它接在末尾；`audience_mismatch` 分支用空 toc（`text=""`）。`canon_assembler.py::build_canon_toc`：每個 `canon_visible`（已審且兩軸可見）細目一行 `<id>｜<title>`，`citable=False`。啟動視圖裡的靜態 toc（`build_audience_outline` 附）在 `from_selection`／`from_visible` 中**不沿用**（`picked` 只取細目 id） | `build_canon_toc` 對靜態身分：prospect **13 行／518 chars／373 tokens**（節文字含標題 384）；pm **9 行／419 chars／283 tokens**（294）。包成資料段（含標記）：prospect **688 tokens**、pm **518 tokens**。指令：§3 腳本 (A) `toc.*`、腳本 (B) `toc_block_tokens` | **每回合注入：一致**。**大小：不一致**——規格「≤300 字」，實測 prospect 518 字／pm 419 字（字元數） |
| **K** | design 元件 6：`class CandidateSelector: K: Final[int] = 5`；design 主要流程圖「`Selection{candidate_ids≤5,…}`」；requirements R5.1「候選由程式選（固定 K、固定查詢組法、決定性）」；DSP-058「查目錄選細目（K=5）」 | `services/agent/canon/candidate_selector.py::K = 5`（模組常數）；`select` 取 `scored[:K]`；`runtime.py`／`turn_context.py` 以 `K as _CANDIDATE_K` 做 trace 形狀守門（`len(candidate_ids) > _CANDIDATE_K ⇒ candidate_ids_shape_invalid`）；⛔ 無 env、無建構參數可改 | `tests/unit/agent/test_candidate_selector_req.py:235`：`assert K == 5`。一回合 `sel_meta.candidate_ids` 長度＝5（§3 腳本 (A)）。指令：`grep -n "^K: int" rag-orchestrator/services/agent/canon/candidate_selector.py` | **一致** |
| **查詢組法** | design 元件 6 `select` docstring：「查詢＝當前 user 訊息＋上一則 user 訊息（程式規則，R5.10）」 | `runtime.py::_candidate_query`：`f"{user_message} {last_user_content}"`（dialog 由後往前第一則 `role=="user"`），無則單句；⛔ 不 log | — | **一致** |
| **降級注入什麼** | design 附錄 A 名詞：「**降級整份正本**：selector 三態任一失敗時注入整份 `OutlineDoc`」；design 主要流程圖 else 分支：「`outline ← 整份正本；violations += candidate_fallback_full_outline`」；design 元件 7 表：「或降級 `from_visible(可見細目全集, toc)`（**1.16 修訂：不是未過濾整份**）」；design 非功能：「失敗 ⇒ `not_ready`、回合走可見細目全集＋toc（`CandidateOutlineDoc.from_visible`）」 | `runtime.py::_select_outline::_fallback_visible`：`visible = selector.index.visible_subset(...)`（或無 selector 時逐條 `canon_visible`）→ `CandidateOutlineDoc.from_visible(outline, visible, toc)`。觸發：對照表有設但缺該受眾／`select` 回 `None`／`no_candidate`／例外。`none_visible` ⇒ `from_visible(outline, frozenset(), toc)`（只剩 toc）。`audience_mismatch` ⇒ 零細目節＋空 toc | prospect 降級（`from_visible`）：**14 節**（13 可引用＋toc）、`token_count` **3,751**（無標記）、資料段 **5,222 tokens**；pm 降級資料段 **2,105 tokens**（9 可引用＋toc）。指令：§3 腳本 (A) `degraded_*`、腳本 (B) `all_citable+toc_block_tokens` | **程式內部一致（可見已審全集＋toc）；design 內部自相矛盾**：附錄 A 與主要流程圖仍寫「整份正本」，元件 7／非功能／1.16 寫「可見細目全集＋toc」 |
| **「沒有候選機制」路徑（非降級）** | design 1.16：「`miss_kind` 值域 `{hit,none_visible,no_candidate,index_unavailable,None}`，`None`＝無候選機制（`--candidates off`／受眾無正本）」 | `runtime.py::_select_outline`：`outline is None`、或 `audience ∉ CANON_VIEW_AUDIENCES`、或 `get_canon() is None`、或（單數與複數 selector 皆未設）⇒ **原 outline 原樣回傳、`sel_meta=None`、不記 violation** ⇒ 啟動整份受眾視圖（含 46 條未審標題行＋靜態 toc）進 prompt。呼叫端：`tools/agent_eval.py::_run_agent_chain_fake`（`--candidates off` 時 `selector=None`） | 整份 prospect 視圖（含靜態 toc）包成資料段＝**7,585 tokens／9,551 chars**（§3 腳本 (A) `full_audience_view_data_block_tokens`） | **一致** |
| **啟動組什麼** | design 元件 5「呼叫鏈與失敗語義（寫死，E1）」：「`app.py::_init_agent_runtime` → `build_prospect_outline(db_pool)` 首行 `doc = load_canon_or_die(canon_dir, "prospect")` → `build_outline(doc)` → `check_budget(default_token_limit)`」；DSP-058：「一份目錄＋九架…受眾＝細目屬性」 | `app.py::_init_agent_runtime`：`load_canon_or_die(resolve_canon_dir())` 一次 → `register_canon` → `FineIndex.prepare` 一次（`wait_for(…, PREPARE_TOTAL_TIMEOUT_S=60)`，失敗 fail-soft 印警告）→ 對 `_AGENT_OUTLINE_AUDIENCES=("prospect","property_manager")` 逐受眾 `build_audience_outline(aud)` ＋ **再呼叫一次** `check_budget(doc, default_token_limit(aud))`（`build_audience_outline` 內部已呼叫過一次）→ 非基準受眾失敗只 `print` 跳過、基準受眾（prospect）失敗 raise → 外層 `_agent_configured()` 為真 ⇒ 啟動紅，否則 fail-soft。`outline.py::build_audience_outline`：`get_canon()` 沿用 → `build_outline(canon, audience, Identity(**_STATIC_TOC_IDENTITY[aud]), vendor_business_types)` → `build_canon_toc` → `_build_doc(sections=視圖節+[toc], version=canon.version)` → `check_budget`。`_STATIC_TOC_IDENTITY` 只有 prospect／property_manager（皆 `vendor_id=0, mode="b2b"`）；tenant `raise ValueError` | `build_audience_outline("prospect")`：**60 節（59 細目＋toc）、6,187 tokens（tiktoken cl100k，非近似）、6,631 chars、sha `ee70e2b9b941`、0.005 s**。`build_audience_outline("property_manager")`：**raise `OutlineBudgetExceeded: property_manager 大綱／目錄 token_count=10896 超過上限 8000（version=2026-09-15.0）`**（視圖 192 節＝9 可引用＋183 只標題；無 toc 時 10,600）。`build_audience_outline("tenant")`：`ValueError: audience='tenant' 沒有 git 正本靜態身分`。`load_canon_or_die` 0.028 s 通過（`.json`／`CATALOG.md` 逐位元同源）。指令：§3 腳本 (A) `audience_outline.*` | **簽名不一致**：design 元件 5 `load_canon_or_die(canon_dir, audience)`／`build_outline(doc, *, include_unreviewed_titles)` vs 程式 `load_canon_or_die(canon_dir)`／`build_outline(doc, audience, identity, *, vendor_business_types)`（design 1.11／DSP-058 已回寫元件 5 註記，但原介面碼塊未改）。**行為**：pm 視圖在工作樹啟動時會被跳過（非基準受眾） |
| **`check_budget` 量什麼** | agentic-mcp R5.5：「對大綱做 token 預算檢查：prospect 大綱 ≤ 10K token、pm／tenant 目錄 ≤ 8K token；超過 SHALL 大聲失敗（啟動時）」；design 非功能：「上下文由整份 3,078 tokens 降至 K=5 細目≈500–800 字＋toc ≤300 字」；`AGENTIC_MCP_ARCHITECTURE.md` §A-8：「逐回合注入 K 條候選那條路**沒有預算守門**——K 調大＝prompt 直接變長」 | `outline.py::check_budget(doc, limit)`：`doc.token_count > limit ⇒ raise OutlineBudgetExceeded`。`token_count` 由 `_count_tokens(text)`：tiktoken `cl100k_base`，取不到 ⇒ `len//2` 近似＋`token_count_approx=True`。被量的 `text`＝`_build_doc` 的 `【id】title\ntext` 接法（**不含 nonce 標記**）。呼叫點只有啟動：`build_audience_outline` 與 `app.py::_init_agent_runtime`（同一份 doc 各一次）；`_select_outline`／`CandidateOutlineDoc` **零呼叫**（`grep -n check_budget rag-orchestrator/services/agent/runtime.py` 無命中；正對照 `grep -n check_budget rag-orchestrator/app.py` 命中 2 行） | 被量的整份視圖 vs 實際注入：prospect 整份 6,187（量到）→ 一回合注入資料段 2,752 tokens（未量到）。同一批文字加標記後膨脹：候選 5 節無標記 1,889 → 有標記 2,107（toc 373 → 688）。K=5 上下界（prospect 13 條可引用節逐節含標記）：**最大 5 節 2,761＋toc 688＝3,449 tokens；最小 5 節 1,272＋toc＝1,960**；pm：最大 1,333＋518＝1,851、最小 819＋518＝1,337。指令：§3 腳本 (B) | **量的對象與規格不同**：R5.5 寫的上限值（10K）已被 design 1.12 改為 12,000；design 非功能「500–800 字＋toc ≤300 字」對照實測：候選 5 節文字 477–1,396 chars（極端組合）、toc 518 chars；「整份 3,078 tokens」為舊 prospect.md 時期數字，現視圖 6,187。架構文 §A-8「候選路徑無預算守門」與程式一致 |
| **上限來源** | design 元件 5 3.2 落地註：「`check_budget(min(env, doc.budget_tokens))`」；plan-9.6 §S3 表：「`default_token_limit` 改為 `min(env, 常數)`，正本 `budget_tokens` 不再是天花板」；`canon/README.md`：「token 預算上限由 `OUTLINE_TOKEN_LIMIT_DEFAULTS` 管（prospect 12000／pm 8000）；env 只能把它調小，⛔ 不能調大」 | `outline.py::OUTLINE_TOKEN_LIMIT_DEFAULTS = {"prospect": 12_000, "property_manager": 8_000, "tenant": 8_000}`；`default_token_limit(aud) = min(int(env) if env else default, default)`；`parse_canon_dir` 的 `CanonDoc.budget_tokens` 恆 0（架 front matter 無此鍵） | 容器 `parse_canon_dir(...).budget_tokens = 0`；`default_token_limit("prospect")=12000`（env 未設）。指令：§3 腳本 (A) `canon.budget_tokens`、`audience_outline.prospect.limit` | **與 design 元件 5 原句（`min(env, doc.budget_tokens)`）不一致，與 plan-9.6／README 一致** |
| **env 上限的作用** | design 元件 5 docstring 附註：「`AGENT_CANON_DIR` 覆寫僅在 `DB_ENV=test` 生效」；`docs/api/mcp-facade.md` §10：「`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT` 預設 `10000`…`_PM` 8000（子 spec 用，M1 尚未消費）」；`docker-compose.prod.yml` 註解：「`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT`（預設 10000）／_PM（預設 8000）／_TENANT（預設 8000）」；`AGENTIC_MCP_ARCHITECTURE.md` §A-9 表：「可由 `AGENT_OUTLINE_TOKEN_LIMIT_*` 覆寫」 | `outline.py::OUTLINE_TOKEN_LIMIT_ENV` 三鍵；`default_token_limit`：env 空 ⇒ 常數；env 非整數 ⇒ `ValueError`（啟動炸）；env 整數 ⇒ `min(env, 常數)`——**只能調小**。`canon_assembler.py::resolve_canon_dir`：`AGENT_CANON_DIR` 只在 `DB_ENV=test` 生效，否則 warning＋預設 `<rag root>/canon` | 容器 env：三個 `AGENT_OUTLINE_TOKEN_LIMIT_*` 皆未設、`AGENT_CANON_DIR` 未設、`DB_ENV=test`。repo 測試 `test_env_cannot_raise_the_cap`：設 `999999` ⇒ 仍 12,000；設 `1` ⇒ 1——容器內 **PASSED**（指令：`scripts/run-tests.sh unit tests/unit/agent/test_library_view_req.py -k env_cannot_raise_the_cap`） | **文件不一致**：`docs/api/mcp-facade.md` §10 與 `docker-compose.prod.yml` 註解寫 prospect 預設 10000（程式 12,000）、寫「pm 尚未消費」（程式啟動即組 pm 視圖）、寫「覆寫」（程式只准調小）。程式與 README／plan-9.6 一致 |
| **整份 `OutlineDoc` 的其他消費者** | design 元件 5：「`CanonDoc` → `OutlineDoc`（沿用 `_build_doc`／`check_budget`／`make_outline_resolver`）」；design 監控：「`PromptMeta.outline_sha` 複製自母 doc…不再標識本回合實際注入的文字」 | (1) `app.py`：`app.state.agent_outline`（＝prospect）、`app.state.agent_outlines[aud]`、`build_runtime(outline_doc=prospect)` ⇒ `runtime.outline_sha`（`services/agent/bootstrap.py::build_runtime`）、`ShadowRunner` 工廠、啟動 log `sections=… tokens=…`（prospect）；(2) `services/agent/mcp_facade.py::_outline_for_audience`／`_agent_turn`：每回合 `agent_state["outline"]=outlines[audience]`，存檔前 `pop`；取不到 ⇒ `NO_MATCH`／`AGENT_UNAVAILABLE`；(3) `services/agent/health.py::_outline_sha`：`checks.outline_version = runtime.outline_sha`（prospect 啟動值）；(4) `routers/agent_entry.py::_outline_for`（遷移橋，未掛載）；(5) `tools/agent_eval.py`：`build_audience_outline("prospect")` 餵回測；(6) `tools/agent_outline_dump.py`：`build_audience_outline(audience)` 匯出；(7) `outline.py::make_outline_resolver(dict(outlines))`：cache 只在正本未註冊時用；(8) `TurnInputsSnapshot.outline_sha = outline.sha256`（`CandidateOutlineDoc` 複製母 doc 的 sha，見下列） | `grep -rn --include='*.py' -e 'agent_outlines' -e 'outline_doc\b' -e 'build_audience_outline' rag-orchestrator | grep -v '^rag-orchestrator/tests/'`（非測試命中：`app.py` 12、`routers/agent_entry.py` 9、`tools/agent_eval.py` 24、`tools/agent_outline_dump.py` 4、`services/agent/mcp_facade.py` 13、`bootstrap.py` 4、`health.py` 5、`turn_context.py` 8、`shadow.py` 1、`trace_view.py` 2；正對照：`outline.py` 自身命中）。demo 帳本 L10：「`runtime.outline_sha` 行程級欄位是 prospect 值…P4」 | **一致**（規格未列消費者清單；`outline_sha` 語義規格已註明） |
| **`outline_sha` 每回合記什麼** | design 監控：「`PromptMeta.outline_sha` 複製自母 doc（Plan v3 P1-2），不再標識本回合實際注入的文字；要還原『這回合看了什麼』只能靠 `candidate_ids`」 | `outline.py::CandidateOutlineDoc.from_selection/from_visible`：`sha256=full.sha256`（母視圖 sha，⛔ 不重算）；`runtime.py::_build_turn_context`：`TurnInputsSnapshot(outline_sha=outline.sha256, candidate_ids=…, winning_key_kind=…, miss_kind=…)` → `TurnTrace`／`decision_snapshot.agent`（`turn_context.py::_emit_agent_decision`，形狀守門 `_candidate_ids_shape_valid`） | 一回合 `sel_meta`：`candidate_ids` 5 條、`winning_key_kind` ∈ {phrasing, content}、`miss_kind="hit"`（§3 腳本 (A)） | **一致** |
| **`kb.get("outline:toc")`** | design 元件 6「第二次機會」：「目錄節 `outline:toc`（citable=False）＋`kb.get("outline:<fine_id>")` 讀整細目」；design 元件 5：「`make_outline_resolver`…改為在回傳前套 `visible_subset`：不可見或未審一律 `NO_MATCH`」；政策文（`services/agent/agent_rules.py`）：「若都不相關，可用 `kb.get` 讀目錄列出的章節整節後再引用，id 形狀為 `outline:` 加上目錄那一行的章節 id」 | `services/agent/tools/kb.py::kb_get`：`kb_id.startswith("outline:")` ⇒ 交 `outline_resolver`（`None` ⇒ `NO_MATCH`），結果原樣回傳。`outline.py::make_outline_resolver`：受眾 ∉ `_STATIC_TOC_IDENTITY` ⇒ `NO_MATCH`；正本已註冊 ⇒ `canon_assembler.resolve_canon_section(canon, identity, kb_id, vendor_business_types=resolve_vendor_business_types(identity))`。`resolve_canon_section`：`"outline:toc"` ⇒ 當場 `build_canon_toc`（citable=False）；`"outline:<fine id>"` ⇒ `canon_visible` 才回內容（citable=True）；其餘（含裸 id）⇒ `NO_MATCH`。接線：`app.py` `FacadeDeps.get_outline_resolver=lambda: app.state.outline_resolver`（`make_outline_resolver(dict(outlines))`） | `tests/unit/agent/test_library_view_req.py::test_resolve_canon_section_cross_audience_is_no_match`／`test_tenant_resolver_is_no_match_even_with_registered_canon`（⛔ 本次未跑；由 9.6 S3 verifier CONFIRMED，tasks.md 9.6）。目錄行數同上列 toc（prospect 13／pm 9） | **一致** |
| **受眾／可見性軸（誰看得到哪些節）** | requirements R5.3：「可見性沿用 `mode`／`target_user[]`／業態／vendor 謂詞，在排序之前切出可見細目子集」；DSP-052 (c)：「b2b 分支取消空 `target_user` 放行」；DSP-058：「每個細目必填非空 `target_user`」 | `canon_assembler.py::_axes_visible`：`is_b2b=(effective_target_user ∈ {property_manager, system_admin}) or mode=="b2b"`；b2b ⇒ `business_types ∩ {system_provider}` 非空 **且** `target_user` 非空且含該角色；b2c ⇒ 業態空或 ∩ vendor 業態、`target_user` 空或含角色或 `all_users`。`canon_visible = reviewed_by is not None and _axes_visible`。`outline.py::resolve_vendor_business_types`：`vendor_id` 假值或受眾 prospect ⇒ `frozenset()` 不查 DB | 靜態身分下：prospect 兩軸可見 **59**、可引用 **13**；pm 兩軸可見 **192**、可引用 **9**；tenant（b2c 或 b2b，vendor 0）可引用 **0**（正對照：同函式對 pm 非 0）。指令：§3 腳本 (A) `canon.visible_by_identity` | **一致** |
| **正本細目數／未審數／各架** | DSP-058：「9.5 重切期…15 條拆併細目待補審（補審前不可見）」（MAP `#agentic-mcp`）；tasks.md 9.7：「正本 53→210 條，未審 190」 | `services/agent/canon/canon_parser.py::parse_canon_dir`（九架解析）；`FineItem.reviewed_by` 由 `- reviewed:` 行決定 | 容器：`fines_total=210`、`unreviewed_total=190`、`content_units_total=1,819`；各架（細目／未審）：A 16/16、B 17/16、C 22/19、D 55/55、E 48/47、F 26/19、G 12/11、H 0/0、I 14/7。工作樹 md 對照：`for f in rag-orchestrator/canon/jgb/[A-I].md; do grep -c '^### ' $f; grep -c '^- reviewed:' $f; done` ⇒ A 16/0、B 17/1、C 22/3、D 55/0、E 48/1、F 26/7、G 12/1、H 0/0、I 14/7（reviewed 合計 20＝210−190）。HEAD 舊檔對照：`git show HEAD:rag-orchestrator/canon/prospect.md \| grep -c '^### '` ⇒ 38（reviewed 38）；`property_manager.md` 39（reviewed 39） | **與 tasks.md 9.7 記錄一致**；MAP／DSP-058 的「15 條待補審」是 9.6 S2 時點（已被 9.7 擴充覆蓋，tasks.md 9.7 自述「`reviewed` 丟」） |
| **pm 視圖預算超限（工作樹）** | plan-9.6 §S3 驗收 ⑨：「真實兩視圖 `token_count` ≤ 各自常數」；plan-9.6 停損 3：「預算超過 ⇒ 停，交業主（⛔ 不自行放大常數）」；tasks.md 9.7 末段：「⚠️ DSP-059 候選（等業主裁）：整份視圖預算失效——pm 視圖（只標題）10,896 > 8,000 啟動即紅、全審後投影 prospect 35,893／pm 106,064 tokens…裁前 13 條釘子測試…紅屬預期，⛔ 不改常數」 | `outline.py::check_budget` raise；`app.py::_init_agent_runtime` 對非基準受眾 `except Exception ⇒ print("… 視圖未組成，跳過該受眾（agent.turn 對它回 AGENT_UNAVAILABLE）") ; continue`；`mcp_facade.py::_outline_for_audience`：`agent_outlines` 非空且查無該受眾 ⇒ `_OUTLINE_UNAVAILABLE` | 容器 `build_audience_outline("property_manager")` ⇒ `OutlineBudgetExceeded … token_count=10896 超過上限 8000`。repo 測試：`scripts/run-tests.sh unit tests/unit/agent/test_library_view_req.py -k real_views_fit_the_budget` ⇒ **`1 failed`**（同一例外）；正對照 `-k env_cannot_raise_the_cap` ⇒ `1 passed`。「全審後投影 35,893／106,064」⛔ 本次未量（見 §2） | **程式行為與 plan-9.6 停損句一致（raise、不放大）；工作樹狀態與 plan-9.6 驗收 ⑨ 不一致（pm 超限）；tasks.md 9.7 已記錄同一數字** |
| **啟動 `check_budget` 重複呼叫** | design 元件 5 呼叫鏈：`build_prospect_outline` → `build_outline` → `check_budget` 一次 | `outline.py::build_audience_outline` 末行 `check_budget(doc, default_token_limit(audience))`；`app.py::_init_agent_runtime` 迴圈內再 `check_budget(_doc, default_token_limit(_audience))` | `grep -n "check_budget" rag-orchestrator/app.py rag-orchestrator/services/agent/outline.py` ⇒ app.py 1 呼叫、outline.py 定義 1＋呼叫 1 | 規格未寫次數（兩次同 doc 同 limit，結果相同） |
| **`_seed_outline_provenance`／引用** | DSP-020：「大綱章節在回合開始預載成一筆 provenance（保留 `tool_call_id="outline"`）」；DSP-029a：標記 `[{nonce}:{tool_call_id}:{source}§{i}]` | `runtime.py::_seed_outline_provenance(outline)`：對 `outline.sections` 每節一筆 `Provenance(source=sec.id, text=sec.text, citable=sec.citable)`；`turn_context.py::ReservedCallIds.all` 含 `OUTLINE_TOOL_CALL_ID="outline"`（`services/agent/provenance_units.py`）；模型撞名 ⇒ `tool_call_id_collides_with_reserved`。`prompt_assembler.py::wrap_provenance_data` 的 units 與 `_seed_outline_provenance` 同取 `sec.text`＋同一把 `provenance_units` | 一回合 `_seed_outline_provenance` 輸入＝`CandidateOutlineDoc.sections`（6 節：5 候選 citable=True＋toc citable=False） | **一致** |
| **索引與 selector 就緒條件** | design 元件 6：「首行 `doc.canon_sha256 != index.prepared_sha ⇒ None`」「快取鍵＝正本 sha＋講法集 sha」；design 非功能：「啟動 prepare ≤2k 句、每批 8」 | `candidate_selector.py::CandidateSelector.select`：`state != "ready"` 或 sha 不符或查詢向量失敗 ⇒ `None`；`QUERY_EMBED_TIMEOUT_S=3.0` 硬上限。`app.py`：`asyncio.wait_for(_index.prepare(_canon), PREPARE_TOTAL_TIMEOUT_S)`（`fine_index.py` 常數 60）；兩受眾 `register_index` 同一個 `FineIndex` | `--no-deps` 容器內真後端 `EmbeddingUtilsBackend.prepare` ⇒ `TimeoutError`（embedding-api 未啟）；改假向量後端 `state=ready`（§3 附註 (3)）。`health.py::_canon_state()["index"]` 對 prospect／pm 必然相同（同一索引，health docstring 明寫） | **一致** |
| **健檢暴露的大綱欄位** | design API 設計：「`GET /api/v1/agent/health` 加 `canon: {audience, canon_sha256, phrasing_set_sha256, index_state, fine_items, approved_fine_items}`（每受眾一筆）」 | `health.py::_canon_state`：回 `{"dir", "sha256": {"jgb": canon_sha256}, "index": {audience: {state, prepared_sha, entries, dim, content_keys}}}`；`checks.outline_version = runtime.outline_sha`（prospect 啟動 sha）；⛔ 無 `fine_items`／`approved_fine_items`／`phrasing_set_sha256` 鍵 | `grep -n "fine_items\|approved_fine_items\|phrasing_set_sha256" rag-orchestrator/services/agent/health.py` ⇒ 0 命中（正對照 `grep -n "outline_version" …` ⇒ 命中） | **不一致**（規格列的 `fine_items`／`approved_fine_items` 程式無） |
| **tenant** | design 元件 5 docstring：「tenant 走 `build_toc` 的 DB 目錄」；`AGENTIC_MCP_ARCHITECTURE.md` §1：「`build_toc`（讀 DB 的那條 tenant 路徑）零生產呼叫端」；MAP：「`tenant` 無視圖，`make_outline_resolver` 對它一律 `NO_MATCH`」 | `outline.py::build_toc(db_pool, audience, vendor_id)` 保留（psycopg2 查 `系統脈絡` 列，vendor／target_user 過濾）；非測試呼叫端 0（`grep -rn "build_toc(" rag-orchestrator --include='*.py' \| grep -v tests` 只命中 `outline.py` 定義／docstring；正對照 `grep -rn "build_canon_toc(" …` 命中 runtime／canon_assembler／outline）；`_STATIC_TOC_IDENTITY` 無 tenant；`AGENT_TURN_SPEC["stage"]` 無 tenant 鍵 | `build_audience_outline("tenant")` ⇒ `ValueError`（§3 腳本 (A)） | **一致** |

## 2. 我沒查到／查不到的（逐條；否定結論皆附正對照）

1. **真 embedding 後端下的一回合注入大小**：容器以 `--no-deps` 起，`EmbeddingUtilsBackend` 對 `http://embedding-api:5000` ⇒ `TimeoutError`；改用決定性假向量（sha256→8 維）讓 selector 走 `hit` 路徑量 token。⇒ **候選「是哪 5 條」不代表線上排序**，token 數字只代表「5 節＋toc 的一種組合」；已用 §1「上限來源」列的 K=5 上下界補足範圍。⛔ 未起 embedding-api（8 GB 機器，記憶 `reference_docker_desktop_vm_hang`）。
2. **tasks.md 9.7 的「全審後投影 prospect 35,893／pm 106,064 tokens」**：本次未重算（那是把 190 條未審視為已審的投影，不是現況）。
3. **`build_toc`（DB 系統脈絡目錄）的行數／token**：需 DB 與 `系統脈絡` 列；`--no-deps` 無 postgres，且該函式零生產呼叫端（正對照 `build_canon_toc` 有 3 處），未量。
4. **線上／常駐容器實際值**：`aichatbot-rag-orchestrator`（Up 3 days）跑的是映像，⛔ 不是工作樹（記憶 `feedback_stale_container_invalidates_backtest`）；本表全部數字來自 `docker compose run --rm`（掛載工作樹），⛔ 不代表 prod。
5. **`.env` 是否設了 `AGENT_OUTLINE_TOKEN_LIMIT_*`**：依任務規約 ⛔ 未讀 `.env`；只知 dev compose 容器內三鍵皆未設（`os.environ.get` 皆 `None`）。
6. **`docs/api/mcp-facade.md` §10 與 `docker-compose.prod.yml` 註解的 10000**：查無來源說明其為刻意保留；只記為與程式常數（12,000）不同。
7. **design 附錄 A「降級整份正本」是否刻意保留**：design 1.16 已改元件 7／非功能，附錄 A 與主要流程圖未同步；未查到裁決紀錄（`grep -n "附錄 A\|整份正本" design.md` 命中該兩處，無「維持」字樣）。
8. **`kb.get("outline:*")` 的實跑**：本次未打 `/mcp`；只引 9.6 S3 verifier CONFIRMED（tasks.md）與單元測試存在（未跑）。
9. **repo 全套單元測試現況**：只跑了 `test_library_view_req.py` 兩條；tasks.md 9.7 自述「裁前 13 條釘子測試…紅屬預期」，⛔ 未逐條驗證那 13 條。
10. **正對照聲明**：所有「0 命中／無」的 grep 皆同時列了必中項（見各列）；`parse_canon_dir` 的 `budget_tokens=0` 以 `fines_total=210` 同一次呼叫為正對照；`tenant` 可引用 0 以 pm 非 0 為正對照。

## 3. 實測指令（可重跑；容器＝`docker-compose.dev.yml` 的 `rag-orchestrator`，`--no-deps`，唯讀）

執行方式（兩支腳本皆以 stdin 餵入，⛔ 不寫工作樹）：

```sh
cd /Users/chenqinghuang/dev/work/AIChatbot
docker compose -f docker-compose.dev.yml run --rm -T --no-deps rag-orchestrator python3 - < <(cat <<'EOF'
# ── 腳本 (A)：受眾視圖／toc／一回合／正本統計 ──
import asyncio, hashlib, json, math, os, sys
sys.path.insert(0, "/app"); os.environ.setdefault("MCP_ALLOWED_ORIGINS", "-")
from services.agent.canon.canon_parser import parse_canon_dir
from services.agent.canon.canon_assembler import (TOC_SECTION_ID, build_canon_toc, canon_visible,
    load_canon_or_die, register_canon, resolve_canon_dir, _axes_visible)
from services.agent.identity import Identity
from services.agent.outline import (CANON_VIEW_AUDIENCES, OUTLINE_TOKEN_LIMIT_DEFAULTS, _STATIC_TOC_IDENTITY,
    _count_tokens, build_audience_outline, default_token_limit, resolve_vendor_business_types, CandidateOutlineDoc)
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
def tok(t): n,a=_count_tokens(t); return {"tokens":n,"approx":a,"chars":len(t)}
async def main():
    OUT={"env":{k:os.environ.get(k) for k in ("DB_ENV","AGENT_CANON_DIR","AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT","AGENT_OUTLINE_TOKEN_LIMIT_PM","AGENT_OUTLINE_TOKEN_LIMIT_TENANT")}}
    d=parse_canon_dir(str(resolve_canon_dir()/"jgb")); fines=list(d.fines())
    OUT["canon"]={"version":d.version,"sha12":d.canon_sha256[:12],"budget_tokens":d.budget_tokens,
        "fines_total":len(fines),"unreviewed_total":sum(f.reviewed_by is None for f in fines)}
    vis={}
    for aud,fields in _STATIC_TOC_IDENTITY.items():
        i=Identity(**fields); vbt=resolve_vendor_business_types(i)
        etu=VendorKnowledgeRetrieverV2._effective_target_user(i.target_user)
        vis[aud]={"axes_visible":sum(_axes_visible(etu,i.mode,f,vbt) for f in fines),
                  "citable":sum(canon_visible(i,f,vendor_business_types=vbt) for f in fines)}
    for name,i in (("tenant_b2c",Identity(vendor_id=0,target_user="tenant",mode="b2c")),("tenant_b2b",Identity(vendor_id=0,target_user="tenant",mode="b2b"))):
        vis[name]={"citable":sum(canon_visible(i,f,vendor_business_types=frozenset()) for f in fines)}
    OUT["canon"]["visible_by_identity"]=vis
    canon=load_canon_or_die(resolve_canon_dir()); register_canon(canon); docs={}; OUT["audience_outline"]={}
    for aud in ("prospect","property_manager","tenant"):
        try:
            doc=await build_audience_outline(aud); docs[aud]=doc
            fs=[s for s in doc.sections if s.id!=TOC_SECTION_ID]
            OUT["audience_outline"][aud]={"token_count":doc.token_count,"approx":doc.token_count_approx,"sections":len(doc.sections),
                "fine_citable":sum(s.citable for s in fs),"fine_title_only":sum(not s.citable for s in fs),"chars":len(doc.text),
                "limit":default_token_limit(aud),"sha12":doc.sha256[:12]}
        except Exception as e: OUT["audience_outline"][aud]={"exception":f"{type(e).__name__}: {e}"}
    OUT["toc"]={}
    for aud,fields in _STATIC_TOC_IDENTITY.items():
        i=Identity(**fields); t=build_canon_toc(canon,i,vendor_business_types=resolve_vendor_business_types(i))
        OUT["toc"][aud]={"lines":len(t.text.split("\n")) if t.text else 0,"text":tok(t.text),"section":tok(f"【{t.id}】{t.title}\n{t.text}")}
    from services.agent import runtime as R
    from services.agent.canon.candidate_selector import CandidateSelector, K
    from services.agent.canon.fine_index import FineIndex
    from services.agent.prompt_assembler import PromptAssembler, new_nonce, wrap_provenance_data
    from services.agent.provenance_units import OUTLINE_TOOL_CALL_ID, provenance_units
    from services.agent.agent_rules import persona_provider, policy_provider
    OUT["K"]=K
    class Fake:  # 決定性假向量：只為走 hit 路徑量 token，⛔ 不代表真排序
        async def embed(self,texts):
            o=[]
            for t in texts:
                h=hashlib.sha256(t.encode()).digest(); v=[(b-128)/128 for b in h[:8]]; n=math.sqrt(sum(x*x for x in v)) or 1
                o.append([x/n for x in v])
            return o
    idx=FineIndex(Fake()); await idx.prepare(canon); OUT["index_state"]=idx.state
    rt=R.AgentRuntime.__new__(R.AgentRuntime); rt._candidate_selector=None; rt._candidate_selectors={a:CandidateSelector(idx) for a in CANON_VIEW_AUDIENCES}
    asm=PromptAssembler(persona_provider,policy_provider); OUT["turn"]={}
    def block(secs,nonce): return wrap_provenance_data("outline",OUTLINE_TOOL_CALL_ID,[(s.id,provenance_units(s.text)) for s in secs],nonce,headers={s.id:f"【{s.id}】{s.title}" for s in secs})
    for aud,q in (("prospect","你們系統適合小房東嗎 要怎麼收費"),("property_manager","怎麼邀請團隊成員進來")):
        if aud not in docs: continue
        i=Identity(**_STATIC_TOC_IDENTITY[aud],session_id="s"); v=[]
        out,meta=await rt._select_outline(i,docs[aud],q,[],v); n=new_nonce()
        fs=[s for s in out.sections if s.id!=TOC_SECTION_ID]; ts=[s for s in out.sections if s.id==TOC_SECTION_ID]
        vis_ids=idx.visible_subset(i,canon,vendor_business_types=resolve_vendor_business_types(i))
        deg=CandidateOutlineDoc.from_visible(docs[aud],vis_ids,ts[0])
        OUT["turn"][aud]={"violations":v,"sel_meta":meta,"candidate_outline.token_count":out.token_count,
            "block(candidates+toc)":tok(block(out.sections,n)),"block(candidates)":tok(block(fs,n)),"block(toc)":tok(block(ts,n)),
            "system_prompt":tok(asm.build(i,out,{"identity":aud,"identity_source":"anonymous"},[],[],n).messages[0]["content"]),
            "degraded.token_count":deg.token_count,"degraded.sections":len(deg.sections),"degraded.block":tok(block(deg.sections,n)),
            "full_view.block":tok(block(docs[aud].sections,n))}
    print(json.dumps(OUT,ensure_ascii=False,indent=1,default=str))
asyncio.run(main())
EOF
)
```

```sh
docker compose -f docker-compose.dev.yml run --rm -T --no-deps rag-orchestrator python3 - < <(cat <<'EOF'
# ── 腳本 (B)：K=5 候選資料段的上下界（逐可引用節含標記 token） ──
import json, os, sys
sys.path.insert(0, "/app"); os.environ.setdefault("MCP_ALLOWED_ORIGINS", "-")
from services.agent.canon.canon_assembler import build_canon_toc, build_outline, load_canon_or_die, resolve_canon_dir
from services.agent.identity import Identity
from services.agent.outline import _STATIC_TOC_IDENTITY, _count_tokens, resolve_vendor_business_types
from services.agent.prompt_assembler import new_nonce, wrap_provenance_data
from services.agent.provenance_units import OUTLINE_TOOL_CALL_ID, provenance_units
canon=load_canon_or_die(resolve_canon_dir()); n=new_nonce(); out={}
def block(secs): return wrap_provenance_data("outline",OUTLINE_TOOL_CALL_ID,[(s.id,provenance_units(s.text)) for s in secs],n,headers={s.id:f"【{s.id}】{s.title}" for s in secs})
for aud,fields in _STATIC_TOC_IDENTITY.items():
    i=Identity(**fields); vbt=resolve_vendor_business_types(i)
    view=build_outline(canon,aud,i,vendor_business_types=vbt); toc=build_canon_toc(canon,i,vendor_business_types=vbt)
    cit=[s for s in view.sections if s.citable]; to=[s for s in view.sections if not s.citable]
    per=sorted(((_count_tokens(block([s]))[0],s.id,len(s.text)) for s in cit),reverse=True); tb=_count_tokens(block([toc]))[0]
    out[aud]={"view_token_count(no toc)":view.token_count,"citable":len(cit),"title_only":len(to),
        "title_only_block_tokens":_count_tokens(block(to))[0] if to else 0,"toc_block_tokens":tb,
        "per_citable_section":[{"id":i_,"tokens":t,"chars":c} for t,i_,c in per],
        "max5":sum(t for t,*_ in per[:5]),"min5":sum(t for t,*_ in per[-5:]),
        "max5+toc":sum(t for t,*_ in per[:5])+tb,"min5+toc":sum(t for t,*_ in per[-5:])+tb,
        "all_citable+toc":_count_tokens(block(cit+[toc]))[0]}
print(json.dumps(out,ensure_ascii=False,indent=1))
EOF
)
```

```sh
# 正／負對照（repo 自帶測試，容器內；runner 會 pip install requirements-test.txt）
scripts/run-tests.sh unit tests/unit/agent/test_library_view_req.py -k real_views_fit_the_budget -p no:cacheprovider   # ⇒ 1 failed：OutlineBudgetExceeded property_manager 10896 > 8000
scripts/run-tests.sh unit tests/unit/agent/test_library_view_req.py -k env_cannot_raise_the_cap -p no:cacheprovider   # ⇒ 1 passed
# 工作樹 vs HEAD
git status --short rag-orchestrator/canon; git ls-tree --name-only HEAD rag-orchestrator/canon/
for f in rag-orchestrator/canon/jgb/[A-I].md; do printf "%s fines=%s reviewed=%s\n" "$f" "$(grep -c '^### ' $f)" "$(grep -c '^- reviewed:' $f)"; done
```

附註：(1) tiktoken `cl100k_base` 在容器內可用（`token_count_approx=False`，所有 token 數皆非近似）。(2) 腳本 (A) 的 `view_token_count` 含靜態 toc，腳本 (B) 的不含（6,187−5,802≈toc 節 384＋分隔符；pm 10,896−10,600 同理）。(3) 一回合實測用假向量後端（見 §2 第 1 條）；`--no-deps` 下真後端 `TimeoutError`。(4) 本表寫入時間 2026-09-16；工作樹 `canon/jgb/` 為未提交狀態，數字隨 9.7 補審而變。
