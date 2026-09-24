# 事實表 A：agent 每回合大綱注入與啟動預算（2026-09-16）

盤查者 A。只列查得到的事實；每個數字附產生它的指令；否定結論附正對照。⛔ 不含改法、不含「應該」。

## 0. 受測物狀態（先讀，數字都掛在這個狀態上）

| 項目 | 事實 | 查證指令 |
|---|---|---|
| 程式＝**未提交的工作樹** | `outline.py`／`canon_assembler.py`／`canon_parser.py`／`candidate_selector.py`／`runtime.py`／`app.py`／`health.py`／`tools/agent_eval.py`／`tools/agent_outline_dump.py` 皆為 ` M`（已修改未提交）；`tests/unit/agent/test_library_view_req.py` 為 `??`（未追蹤）。HEAD（`7c905408`）的 `outline.py`／`canon_assembler.py` 內 **0 處** `jgb`，即圖書館形態（DSP-058／9.6 S3）尚未進版控。 | `git status --short rag-orchestrator/services/agent/ rag-orchestrator/app.py rag-orchestrator/tools/`；`git show HEAD:rag-orchestrator/services/agent/outline.py \| grep -c canon/jgb`（＝0） |
| 正本＝**未提交的工作樹** | 工作樹 `rag-orchestrator/canon/` 只有 `jgb/`（A–I.md＋CATALOG.md）、`jgb.json`、`README.md`；HEAD 仍是 `prospect.md/.json`＋`property_manager.md/.json`（工作樹已 `RM` 搬到 `docs/archive/2026-09/canon-pre-library/`）。 | `git ls-tree --name-only HEAD rag-orchestrator/canon/`；`git status --short \| grep canon` |
| 實測環境 | `docker-compose.dev.yml` 的 `rag-orchestrator` 服務掛載 `./rag-orchestrator:/app`（量的是工作樹）；容器內 `DB_ENV=test`、`AGENT_CANON_DIR` 未設 ⇒ `resolve_canon_dir()=/app/canon`；`tiktoken cl100k_base` 可用（`token_count_approx=False`）；三把 `AGENT_OUTLINE_TOKEN_LIMIT_*` env 皆未設。 | `grep -n "rag-orchestrator:/app\|DB_ENV" docker-compose.dev.yml`；實測腳本印出的 `[env]` 行（附錄 A） |
| 正本現況 | `version=2026-09-15.0`、`canon_sha256=b94acd638e35…`、`CanonDoc.audience="jgb"`。 | 附錄 A 腳本 `[canon]` 行 |

## 1. 事實表

| 主題 | 規格原句（引用＋節名） | 程式（檔案::符號＋一句它做什麼） | 實測數字（附指令） | 規格與程式一致？ |
|---|---|---|---|---|
| 每回合注入的內容組成（有候選機制時） | 主要流程圖（prospect 回合）：「`outline ← CandidateOutlineDoc.from_selection(full, sel)`」「`P-->>R: system（persona(audience)＋定義＋K 細目資料段＋toc＋slots）`」；元件 7 表「候選注入」列：「同一物件餵 `_seed_outline_provenance` 與 `build_messages`」 | `runtime.py::AgentRuntime.run_turn`：`outline = agent_state.get("outline")` → `await self._select_outline(identity, outline, user_message, dialog, acc.violations)` → `_seed_outline_provenance(outline)` 寫進 `acc.tool_results_by_id["outline"]` → `self.assembler.build_messages(identity, outline, slots, dialog, tool_specs, acc.nonce)`。`_select_outline` 命中時回 `CandidateOutlineDoc.from_selection(outline, sel, toc)`＝`sel["candidate_ids"]` 順序取 `full.sections` 中的節 ＋ 當回合 `toc` 一節（`outline.py::CandidateOutlineDoc._from_sections` 以 `_build_doc(sections=picked+[toc])` 組）。`prompt_assembler.py::PromptAssembler.build` 把 `outline.sections` 逐節經 `wrap_provenance_data("outline", OUTLINE_TOOL_CALL_ID, [(id, provenance_units(text))…], nonce, headers={id: "【id】title"})` 放進**唯一一則** system 訊息的第 ② 段（順序：persona→policy→`_agent_rules_text`→tool_lines→outline 資料段→slots）。 | prospect、假 embedding 後端（sha256 決定性向量，只為走到 `hit` 路徑、⛔ 不代表真排序）、q=「請問怎麼收租金」＋上一則「你們的系統是做什麼的」：`miss_kind=hit`、`sections=6`（5 候選＋1 toc）、`out.token_count=1334`（chars 1375）；5 候選節不含 toc＝949 tokens／832 chars；`wrap_provenance_data` 後實際注入段＝**2017 tokens**／2890 chars。第二題「合約到期怎麼續約」：候選 5 節 1657 tokens／1434 chars、`out.token_count=2042`、注入段 2870 tokens。pm 同法：兩題注入段 1599／1250 tokens（附錄 A、B） | 組成一致（K 細目＋toc）。**規格未寫**：`OutlineDoc.token_count`／`PromptMeta.outline_token_count` 量的是**無 nonce 標記**的 `text`，實際注入段（含每片段行首 `[nonce:outline:id§n]` 標記）比它大：1334→2017、6187→7523（整份視圖對照） |
| 每回合注入（無候選機制時） | 元件 7／流程圖未寫此分支 | `runtime.py::_select_outline`：`outline is None` ⇒ 原樣；`outline.audience ∉ CANON_VIEW_AUDIENCES` 或 `get_canon() is None` ⇒ 原樣＋`sel_meta=None`；`_selector_for(audience) is None` 且 `_candidate_selectors` 為空 ⇒ 原樣＋`sel_meta=None`（docstring：「這**不是**降級——是這條路根本沒有候選機制」）。此時注入的是啟動期整份受眾視圖（含啟動期靜態 toc）。 | 未另量（tenant 無視圖；產線 `app.py` 一律傳 `candidate_selectors=selectors` 非空） | 規格未寫 |
| toc 是否每回合注入、大小 | 元件 6「第二次機會」：「目錄節 `outline:toc`（citable=False）」；非功能「toc ≤300 字」；元件 5 3.2 落地註：「啟動 toc 用售前靜態身分算一次，每回合候選子集與 toc 是 4.1」 | 每回合：`runtime.py::_select_outline` 在取得 selector 後先 `toc = build_canon_toc(canon, identity, vendor_business_types=…)`（以**當回合身分**重算），所有 `CandidateOutlineDoc` 分支（`from_selection`／`from_visible`／`none_visible`）都把它接在最後一節；啟動期靜態 toc 因 id `outline:toc` 不在 `candidate_ids`／`visible_ids` 內而被丟掉（`outline.py::CandidateOutlineDoc` docstring 明寫）。`canon_assembler.py::build_canon_toc`：每個 `canon_visible`（已審且兩軸可見）細目一行 `<fine.id>｜<title>`、`citable=False`。`prompt_assembler.py::build` 對 toc 也走 `provenance_units(sec.text)` 逐行加標記。 | 靜態身分 toc：prospect **13 行／373 tokens／518 chars**；pm **9 行／283 tokens／419 chars**（附錄 A `(2)` 行）。toc 行數＝該身分 `canon_visible` 數（prospect 13、pm 9） | 每回合注入：一致。大小：**不一致**——規格「≤300 字」，實測 prospect 518 chars／373 tokens、pm 419 chars／283 tokens（規格「字」未定義是 chars 還是 tokens；以 chars 計兩者皆超、以 tokens 計 prospect 超） |
| K 值 | 元件 6：`class CandidateSelector: K: Final[int] = 5`；流程圖「`Selection{candidate_ids≤5…}`」；非功能「K=5 細目≈500–800 字」 | `candidate_selector.py` 模組層 `K: int = 5`（非類別屬性、非 `Final`）；`select` 取 `scored.sort(key=(-score, fine_id))[:K]`；`runtime.py` import 為 `_CANDIDATE_K`。 | 實測 `K=5`；兩受眾×兩題 `n_cand=5`。5 候選節（不含 toc、不含標記）：prospect 949／1657 tokens（832／1434 chars）、pm 821／618 tokens（790／620 chars）。prospect citable 細目節 tokens 分布：min 99、median 224、max 720；任 5 節最小和 725、最大和 1931（附錄 A `(3-分布)`） | K=5 一致；位置不一致（規格類別屬性 `Final`，程式模組常數）。「≈500–800 字」：以 chars 計本次 4 個樣本 620–1434，兩個在區間外；以 tokens 計 618–1657 |
| 降級路徑注入什麼 | 附錄 A 名詞：「**降級整份正本**：selector 三態任一失敗時注入整份 `OutlineDoc`」；流程圖 else 分支：「`outline ← 整份正本；violations += candidate_fallback_full_outline`」；**但**決策 2：「失敗方向是『可見細目全集＋toc』（1.16 修訂：⛔ 不是未過濾整份正本）」；非功能：「失敗 ⇒ `not_ready`、回合走可見細目全集＋toc（`CandidateOutlineDoc.from_visible`）」；元件 7 表：「降級 `from_visible(可見細目全集, toc)`（1.16 修訂：不是未過濾整份）」 | `runtime.py::_select_outline::_fallback_visible`：`selector.index.visible_subset(...)`（或無 selector 時逐細目 `canon_visible`）⇒ `CandidateOutlineDoc.from_visible(outline, visible, toc)`。觸發：`selector is None` 且對照表非空（`miss_kind=index_unavailable`＋violation `candidate_fallback_full_outline`）；`select` 回 `None`（同上）；`no_candidate`（不記 violation）；任何例外（violation `candidate_selector_error`）。`none_visible` ⇒ `from_visible(outline, frozenset(), toc)`＝只有 toc。受眾不符 ⇒ 空 toc＋零細目節＋`miss_kind=audience_mismatch`。`candidate_selector.py::select`：`state!="ready"`／`canon_sha256!=prepared_sha`／查詢向量 `None` 一律回 `None`。 | 降級 `from_visible`：prospect `sections=14`（13 可見＋toc）`token_count=3751`／3489 chars；pm `sections=10`（9＋toc）`token_count=1541`／1680 chars（附錄 B 「降級」行） | 程式與決策 2／非功能／元件 7 一致；**規格內部不一致**：附錄 A 名詞與主要流程圖 else 分支仍寫「整份正本」。另：`_fallback_visible` 產出**不含未審標題節**（`visible_subset` 只含已審），與啟動視圖（含 46／183 個標題 only 節）不同 |
| 啟動時組什麼 | 元件 5「呼叫鏈與失敗語義（寫死，E1）」：「`app.py::_init_agent_runtime` → `build_prospect_outline(db_pool)` 首行 `doc = load_canon_or_die(canon_dir, "prospect")` … → `build_outline(doc)` → `check_budget(default_token_limit)`」；正本生命週期圖 G：「啟動：build_outline＋FineIndex.prepare」 | `app.py::_init_agent_runtime`：`_load_canon_or_die(_resolve_canon_dir())`（無 audience 參數）→ `_register_canon` → `FineIndex(EmbeddingUtilsBackend()).prepare(_canon)`（`wait_for PREPARE_TOTAL_TIMEOUT_S`，失敗只 print）→ 對 `_AGENT_OUTLINE_AUDIENCES=("prospect","property_manager")` 逐一 `build_audience_outline(aud, _mcp_kb_pool)` 再 **`check_budget(_doc, default_token_limit(aud))`**（而 `build_audience_outline` 內部第 4 步已呼叫過同一個 `check_budget`）；prospect 失敗 ⇒ raise（外層依 `_agent_configured()` 決定啟動紅／fail-soft）；pm 失敗 ⇒ print「視圖未組成，跳過該受眾」`continue`。成功者：`register_index(aud, _index)`（兩受眾同一個 index）、`outlines[aud]=_doc`、`selectors[aud]=CandidateSelector(_index)`。`outline.py::build_audience_outline`：`get_canon()` 或載入→`build_outline(canon, audience, static_identity, vendor_business_types=resolve_vendor_business_types(static_identity))`→`build_canon_toc(...)`→`_build_doc(sections=view.sections+[toc], version=canon.version)`→`check_budget`。`build_prospect_outline` 只是薄別名，`app.py` 不再呼叫它。 | prospect 視圖：`token_count=6187`、`sections=60`（59 細目節＋1 toc）、citable 13、標題 only（未審）46、`limit=12000`、`sha=ee70e2b9b941…`。pm 視圖：**`OutlineBudgetExceeded: property_manager 大綱／目錄 token_count=10896 超過上限 8000`**（`sections=193`＝192 細目節＋toc；citable 9、標題 only 183；標題 only 節合計 9353 tokens）。既有測試 `tests/unit/agent/test_library_view_req.py::test_real_views_fit_the_budget` 對此工作樹 **FAILED**（`scripts/run-tests.sh unit "tests/unit/agent/test_library_view_req.py::test_real_views_fit_the_budget"`，1 failed in 2.60s） | 呼叫鏈**不一致**（規格寫 `build_prospect_outline`＋`load_canon_or_die(canon_dir,"prospect")`；程式是 `app.py` 自行載入單一正本、逐受眾 `build_audience_outline`）。規格 3.2 落地註已承認另名／改簽名，但 E1 那段原文未改。`check_budget` 在啟動路徑被呼叫**兩次**（規格未寫） |
| `check_budget` 量什麼 | 元件 5：「`check_budget(default_token_limit)`」；3.2 落地註：「`check_budget(min(env, doc.budget_tokens))`」；R5.5（引自程式 docstring）「大綱／目錄超過 token 預算——啟動即紅」 | `outline.py::check_budget(doc, limit_tokens)`：`doc.token_count > limit_tokens` ⇒ raise `OutlineBudgetExceeded`。`doc.token_count` 由 `_build_doc` 以 `_count_tokens(text)`（tiktoken cl100k；取不到 ⇒ `len//2`＋`approx=True`）算在 `text=_SECTION_SEP.join("【id】title\ntext")` 上——即**整份受眾視圖（含未審標題節＋靜態 toc）、不含 nonce 標記、不含 persona／policy／rules／tool_lines／slots**。 | 同上：prospect 6187 ≤ 12000；pm 10896 > 8000。`_count_tokens` 與 tiktoken 直算同值（腳本用同一函式） | 量測對象規格未明寫（規格未寫「含未審標題節」）；`min(env, doc.budget_tokens)` 那句與程式**不一致**（見下列） |
| 上限值來源 | 3.2 落地註：「`check_budget(min(env, doc.budget_tokens))`」；元件 4：front matter 固定鍵含 `budget_tokens` | `outline.py::OUTLINE_TOKEN_LIMIT_DEFAULTS = {prospect: 12_000, property_manager: 8_000, tenant: 8_000}`；`default_token_limit(audience) = min(int(env) if env else default, default)`（env 只能調小；docstring：圖書館形態架 front matter 無 `budget_tokens`，`parse_canon_dir` 恆回 0，故不再讀正本）。`canon_parser.py` 註：「架檔 front matter **恰**六鍵（⛔ 無 budget_tokens…）」。 | 容器內 `default_token_limit("prospect")=12000`（env 未設）。`docker-compose.prod.yml` 註解寫「`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT`（預設 10000）」；`outline.py` 常數 12_000（`grep -n "預設 10000" docker-compose.prod.yml`；`grep -n '"prospect": 12_000' rag-orchestrator/services/agent/outline.py`）。`outline.py` 內註「整份售前正本大綱（38 細目＋toc）cl100k 為 10,336 tokens」對應舊正本，非現況（現況 59 節 6187） | **不一致**：規格寫 `min(env, doc.budget_tokens)`，程式是 `min(env, 常數表)`、不讀正本；prod compose 註解預設值與程式常數不同 |
| `OUTLINE_TOKEN_LIMIT_*` env 的作用 | 元件 5（R5.5，經程式 docstring 引）：「env 對應表（呼叫端在啟動時讀）」 | `outline.py::OUTLINE_TOKEN_LIMIT_ENV`：`AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT`／`_PM`／`_TENANT`；`default_token_limit` 讀 env、非整數 ⇒ `ValueError`；效果＝**只能把上限調小**（`min(int(raw), default)`）。唯一消費者鏈：`app.py::_init_agent_runtime` 與 `build_audience_outline` 內的 `default_token_limit(audience)`，`audience` 只會是 `prospect`／`property_manager`（`_AGENT_OUTLINE_AUDIENCES`、`_STATIC_TOC_IDENTITY`）。 | 容器三把 env 皆 `None`。`_TENANT` 鍵：`default_token_limit("tenant")` 可呼叫，但 grep 整個非測試碼只有 `app.py:185` 與 `outline.py:417` 兩個呼叫點且都以受眾迴圈／參數驅動，無任何路徑傳入 `"tenant"`（正對照：同一 grep 命中 prospect 路徑；`build_audience_outline("tenant")` 直接 `ValueError`） | 一致（env 只縮不放）。tenant env 目前無消費路徑：規格未寫 |
| 整份 `OutlineDoc` 除了啟動與降級還有誰用 | 元件 5：「`outline` 介面改吃正本組裝結果」；資料流「`OutlineDoc` → `CandidateOutlineDoc`：子集＋toc；audience／version／sha 複製自母 doc」 | (a) `app.py`：`app.state.agent_outline`（＝prospect）、`app.state.agent_outlines[aud]`、`make_outline_resolver(dict(outlines))`、`build_runtime(outline_doc=outline_doc)`（`bootstrap.py`：只取 `outline_doc.sha256` 掛成 `runtime.outline_sha` 供 health）、ShadowRunner 工廠同樣 `outline_doc=outline_doc`。(b) `routers/agent_entry.py::_outline_for(app, audience)` 與 `mcp_facade.py::_outline_for_audience` 依受眾取 `agent_outlines[aud]` 塞進 `agent_state["outline"]`（存檔前 pop）——之後全由 `_select_outline` 換掉。(c) `runtime.py::run_turn`：`acc.snapshot.outline_sha = outline.sha256`（`CandidateOutlineDoc` 複製母 doc 的 sha ⇒ trace 的 outline_sha＝整份視圖 sha）。(d) `health.py::_outline_sha` 只讀 `runtime.outline_sha`（prospect 視圖 sha）。(e) `tools/agent_outline_dump.py`、`tools/agent_eval.py`（`build_audience_outline("prospect")`，`--candidates off` 時整份注入）。(f) `make_outline_resolver` 的 `cache` 只在 `get_canon() is None` 時查；`app.py` 先 `register_canon` 才建 resolver ⇒ 產線此 cache 路徑不會走到（程式事實，非量測）。 | 非測試碼 `grep -rln "OutlineDoc\b" --include='*.py' rag-orchestrator \| grep -v tests`：`tools/agent_outline_dump.py`、`prompt_assembler.py`、`canon_assembler.py`、`canon_parser.py`、`candidate_selector.py`、`runtime.py`、`outline.py`（7 檔）；`build_audience_outline` 非測試呼叫者：`app.py:183`、`tools/agent_outline_dump.py:323`、`tools/agent_eval.py:917,1030`（正對照：同 grep 命中 `outline.py` 自身定義） | 規格未寫 (c)(d)(f) |
| `kb.get("outline:toc")`／`outline:<id>` 的行為 | 元件 5：「`make_outline_resolver`（`kb.get("outline:<fine_id>")`）改為在回傳前套 `visible_subset`：不可見或未審一律 `NO_MATCH`」；元件 6「第二次機會」：「`kb.get("outline:<fine_id>")` 讀整細目」 | `outline.py::make_outline_resolver`：受眾 ∉ `_STATIC_TOC_IDENTITY`（tenant）⇒ `NO_MATCH`；`get_canon()` 有值 ⇒ `resolve_canon_section(canon, identity, kb_id, vendor_business_types=resolve_vendor_business_types(identity))`；否則查 `cache`。`canon_assembler.py::resolve_canon_section`：`"outline:toc"` ⇒ 以**當回合身分**重算 `build_canon_toc`，回 `ToolResult(ok=True, provenance=[citable=False], text_for_model=toc.text)`；`"outline:<fine.id>"` ⇒ `canon_visible`（已審且兩軸可見）才回 `"\n".join(content_units)`＋`citable=True`；非 `outline:` 前綴（含裸 id）／不可見／未審／不存在 ⇒ 同一個 `NO_MATCH`。 | 未另量（單元測試 `test_outline_unit_req.py::test_resolve_canon_section_*`、`test_library_view_req.py::test_tenant_resolver_is_no_match_even_with_registered_canon` 覆蓋；本次未跑） | 一致（規格寫 `visible_subset`，程式用其逐細目前身 `canon_visible`；3.2 落地註已載明） |
| 未審細目在啟動視圖與每回合 | 元件 5 `build_outline` docstring：「未審細目：include_unreviewed_titles ⇒ 只出標題行、text=""、citable=False」；元件 5 `build_toc`：「只列 visible 內且已審者」 | `canon_assembler.py::build_outline`：`_axes_visible` 為真即納入；`citable=canon_visible(...)`；未審 ⇒ `text=""`。`build_canon_toc` 只列 `canon_visible`。`_select_outline` 各分支的 `visible_subset`／`candidate_ids` 都以 `canon_visible` 為準 ⇒ 未審標題節**只在**「無候選機制原樣注入」時進 prompt。 | 正本 210 細目、已審 20、未審 190（粗目 8、講法 1019、內容句 1819）。prospect：兩軸可見 59＝13 已審＋46 未審；pm：192＝9＋183；tenant（b2c、業態 ∅）`canon_visible=0`。`target_user` 分布 {pm+prospect: 41, pm: 151, prospect: 18}；`business_types` 全 210 為 `system_provider`（附錄 A `(4)` 行） | 一致。規格 `include_unreviewed_titles` 參數程式無（恆納入標題）：規格未寫此差異 |
| 非功能「整份 3,078 tokens」基線 | 非功能：「上下文由整份 3,078 tokens 降至 K=5 細目≈500–800 字＋toc ≤300 字」 | `outline.py` 內註：「整份售前正本大綱（38 細目＋toc）cl100k 為 10,336 tokens」（舊 `prospect.md`） | 現況整份 prospect 視圖 `token_count=6187`（注入段 7523）；pm 10896 | **不一致**（規格 3,078／程式註 10,336／實測 6,187 三個數對應三個不同時點的正本；規格未標 3,078 的量測條件） |
| trace／health 回報的 token 數 | API 設計：「`GET /api/v1/agent/health` 加 `canon: {…}`」；未寫 token | `prompt_assembler.py::PromptMeta.outline_token_count` 透傳 `outline.token_count`；`app.py` 啟動印 `tokens={outline_doc.token_count}`（prospect 整份視圖）；`health.py` 只印 `outline_version=_outline_sha`（sha，非 token）。 | 啟動印值＝6187（同 (1)）；每回合 `PromptMeta.outline_token_count`＝`CandidateOutlineDoc.token_count`（1334／2042…），實際注入段 2017／2870 | 規格未寫 |

## 2. 呼叫者／否定結論的正對照

| 否定結論 | grep 樣式 | 命中清單（非測試碼） | 正對照 |
|---|---|---|---|
| `check_budget` 除 `app.py::_init_agent_runtime` 與 `outline.py::build_audience_outline` 外無其他產線呼叫者 | `grep -rn "check_budget" --include='*.py' rag-orchestrator \| grep -v /tests/` | `app.py:184`、`outline.py:378`（docstring）、`outline.py:417`、`outline.py:459`（定義）、`outline.py:468`（註） | 同 grep 命中定義處 `outline.py:459` |
| `build_toc(db_pool, audience, vendor_id)`（pm／tenant DB 目錄）**無產線呼叫者** | `grep -rn "build_toc(" --include='*.py' rag-orchestrator \| grep -v /tests/` | 只有 `outline.py:30`（docstring）、`outline.py:438`（定義）、`canon_assembler.py:358`（docstring）；測試 `test_outline_unit_req.py`、`tests/integration/agent/test_outline_req.py` 有呼叫 | 同 grep 命中定義處與測試 |
| `_select_outline` 只在 `run_turn` 一處被產線呼叫 | `grep -rn "_select_outline" --include='*.py' rag-orchestrator \| grep -v /tests/` | `runtime.py:2632`（呼叫）、`runtime.py:1445`（定義）、其餘為註解 | 命中定義處 |
| `get_canon()` 產線呼叫者 | `grep -rn "get_canon()" --include='*.py' rag-orchestrator \| grep -v /tests/` | `outline.py:394`（build_audience_outline）、`outline.py:542`（resolver）、`runtime.py:1476`（_select_outline）、`tools/agent_eval.py:666` | 命中定義 `canon_assembler.py:232` |
| `OUTLINE_TOKEN_LIMIT_*` env 在 compose 檔只出現於註解 | `grep -n "OUTLINE_TOKEN_LIMIT" docker-compose.dev.yml docker-compose.prod.yml` | `docker-compose.dev.yml:117`（註解）、`docker-compose.prod.yml:276`（註解，寫「預設 10000」） | 同檔 `grep -n "MCP_ALLOWED_ORIGINS" docker-compose.dev.yml` 命中非註解行 `:113` |

## 3. 我沒查到／查不到的

1. **真 embedding 後端下的候選集**：容器內未接 embedding 服務，(3) 用 sha256 假向量走 `hit` 路徑；候選 id 與其 token 數**只代表「5 節＋toc」的尺寸樣本**，⛔ 不代表線上排序。真後端下的每回合注入量未量到。
2. **完整 system prompt 總 token**（persona＋policy＋rules＋tool_lines＋outline 段＋slots）：未量（需組 `PromptAssembler` 與 tool registry；本次只量 outline 資料段）。
3. **HEAD 提交版的數字**：本次全部量在未提交工作樹；HEAD 的 `canon/prospect.md`＋舊 `outline.py` 未另量（另一視窗正在改，⛔ 不動它的檔）。
4. 規格非功能句「整份 3,078 tokens」的量測來源（哪一版正本、哪個計數器）：design.md 內無出處；`grep -rn "3,078\|3078" .kiro/specs/knowledge-outline-and-intent-architecture/` 只命中該句本身。
5. 規格「K=5 細目≈500–800 字」「toc ≤300 字」的「字」是 chars 還是 tokens：規格未定義；本表兩種都列。
6. `kb.get("outline:*")` 的行為只對碼、未在容器內實跑（既有單元測試覆蓋，本次未執行整批）。
7. pm 視圖超預算（10896 > 8000）在**真實啟動**下的實際輸出（`app.py` print「視圖未組成，跳過該受眾」＋ pm `agent.turn` 回 `AGENT_UNAVAILABLE`）：只對碼推得，未起 app 驗；已用同一函式鏈的單元測試 `test_real_views_fit_the_budget` 實跑確認 raise。
8. 線上（prod）三把 `AGENT_OUTLINE_TOKEN_LIMIT_*` 是否有設：未查（⛔ 不讀 `.env`）。

## 附錄 A：實測指令（容器內，只讀）

```sh
docker compose -f docker-compose.dev.yml run --rm -T --no-deps -w /app -e PYTHONPATH=/app \
  --entrypoint python3 rag-orchestrator - <<'EOF'
import asyncio, hashlib, math, os, statistics, sys
sys.path.insert(0, "/app"); os.chdir("/app")
from services.agent import outline as o
from services.agent.canon import canon_assembler as ca
from services.agent.identity import Identity
from services.agent.canon.fine_index import FineIndex, reset_index_registry
from services.agent.canon.candidate_selector import CandidateSelector, K
from services.agent.prompt_assembler import wrap_provenance_data, new_nonce
from services.agent.provenance_units import OUTLINE_TOOL_CALL_ID, provenance_units
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
import tiktoken; tiktoken.get_encoding("cl100k_base"); print("[env] tiktoken ok")
tok = o._count_tokens
async def main():
    print("[env]", ca.resolve_canon_dir(), os.environ.get("DB_ENV"), {k: os.environ.get(k) for k in o.OUTLINE_TOKEN_LIMIT_ENV.values()})
    docs = {}
    for aud in ("prospect", "property_manager"):
        try:
            d = await o.build_audience_outline(aud); docs[aud] = d
            fs = [s for s in d.sections if s.id != ca.TOC_SECTION_ID]
            print("(1)", aud, d.token_count, d.token_count_approx, len(d.text), len(d.sections), len(fs), sum(s.citable for s in fs), o.default_token_limit(aud), d.version, d.sha256[:12])
        except Exception as e: print("(1)", aud, "例外", type(e).__name__, e)
    canon = ca.get_canon(); print("[canon]", canon.version, canon.canon_sha256[:12], canon.audience)
    for aud, f in o._STATIC_TOC_IDENTITY.items():
        ident = Identity(**f); toc = ca.build_canon_toc(canon, ident, vendor_business_types=o.resolve_vendor_business_types(ident))
        print("(2)", aud, len(toc.text.splitlines()), tok(toc.text), len(toc.text))
    fines = list(canon.fines()); print("(4)", len(fines), sum(f.reviewed_by is None for f in fines), len({f.coarse_id for f in fines}), sum(len(f.phrasings) for f in fines), sum(len(f.content_units) for f in fines))
    for aud, f in o._STATIC_TOC_IDENTITY.items():
        ident = Identity(**f); etu = VendorKnowledgeRetrieverV2._effective_target_user(ident.target_user)
        print("(4)", aud, sum(ca._axes_visible(etu, ident.mode, x, frozenset()) for x in fines), sum(ca.canon_visible(ident, x, vendor_business_types=frozenset()) for x in fines))
    for aud, d in docs.items():
        per = sorted(tok(f"【{s.id}】{s.title}\n{s.text}")[0] for s in d.sections if s.id != ca.TOC_SECTION_ID and s.citable)
        print("(3-分布)", aud, per[0], statistics.median(per), per[-1], sum(per[:5]), sum(per[-5:]))
    def vec(t, dim=16):
        h = hashlib.sha256(t.encode()).digest(); v = [((b/255.0)*2-1) for b in h[:dim]]; n = math.sqrt(sum(x*x for x in v)) or 1.0; return [x/n for x in v]
    class Fake:
        async def embed(self, texts): return [vec(t) for t in texts]
    reset_index_registry(); index = FineIndex(Fake()); await index.prepare(canon)
    from services.agent import runtime as rt
    r = rt.AgentRuntime.__new__(rt.AgentRuntime); r._candidate_selector = None; r._candidate_selectors = {a: CandidateSelector(index) for a in o._STATIC_TOC_IDENTITY}
    for aud, f in o._STATIC_TOC_IDENTITY.items():
        ident = Identity(**f)
        view = ca.build_outline(canon, aud, ident, vendor_business_types=frozenset()); toc = ca.build_canon_toc(canon, ident, vendor_business_types=frozenset())
        d = o._build_doc(audience=aud, sections=list(view.sections)+[toc], version=canon.version)   # pm 超預算故繞過 check_budget 直組
        for q, prev in (("請問怎麼收租金", "你們的系統是做什麼的"), ("合約到期怎麼續約", None)):
            viol = []; out, meta = await r._select_outline(ident, d, q, [{"role":"user","content":prev}] if prev else [], viol)
            secs = list(out.sections); nonce = new_nonce()
            block = wrap_provenance_data("outline", OUTLINE_TOOL_CALL_ID, [(s.id, provenance_units(s.text)) for s in secs], nonce, headers={s.id: f"【{s.id}】{s.title}" for s in secs})
            cand = [s for s in secs if s.id != ca.TOC_SECTION_ID]; ct = "\n\n---\n\n".join(f"【{s.id}】{s.title}\n{s.text}" for s in cand)
            print("(3)", aud, q, meta["miss_kind"], meta["candidate_ids"], viol, len(secs), tok(ct)[0], len(ct), out.token_count, len(out.text), tok(block)[0], len(block))
        vis = index.visible_subset(ident, canon, vendor_business_types=frozenset()); fb = o.CandidateOutlineDoc.from_visible(d, vis, toc)
        print("(3-降級)", aud, len(fb.sections), fb.token_count, len(fb.text), len(vis))
asyncio.run(main())
EOF
```

既有測試實跑：`scripts/run-tests.sh unit "tests/unit/agent/test_library_view_req.py::test_real_views_fit_the_budget" -p no:cacheprovider` ⇒ `FAILED … OutlineBudgetExceeded: property_manager 大綱／目錄 token_count=10896 超過上限 8000（version=2026-09-15.0）`。

## 附錄 B：實測原始輸出（2026-09-16，工作樹）

```
[env] tiktoken cl100k_base 可用
[env] resolve_canon_dir = /app/canon DB_ENV= test AGENT_CANON_DIR= None
[env] AGENT_OUTLINE_TOKEN_LIMIT_PROSPECT|PM|TENANT = None
(1) prospect: token_count=6187 approx=False chars=6631 sections=60 (細目節=59 + toc=1) citable細目=13 標題only(未審)=46 limit=12000 version=2026-09-15.0 sha=ee70e2b9b941
(1) property_manager: 例外 OutlineBudgetExceeded: property_manager 大綱／目錄 token_count=10896 超過上限 8000（version=2026-09-15.0）
[canon] version= 2026-09-15.0 canon_sha256= b94acd638e35 audience欄= jgb
(2) prospect: toc 行數=13 tokens=373 字元=518   (2) property_manager: toc 行數=9 tokens=283 字元=419
(4) 細目數=210 未審=190 已審=20 粗目數=8 講法總數=1019 內容句總數=1819
(4) prospect: 兩軸可見=59 已審可見=13 未審但在視圖=46   (4) property_manager: 兩軸可見=192 已審可見=9 未審但在視圖=183
(4) tenant(b2c,∅): canon_visible=0
(4) target_user 分布: {('property_manager','prospect'): 41, ('property_manager',): 151, ('prospect',): 18}；business_types: {('system_provider',): 210}
(3-分布) prospect: citable 細目節 tokens min=99 median=224 max=720 合計=3354; 任5節最小和=725 最大和=1931
[prospect] q='請問怎麼收租金'(+上一則): hit, 5 候選 tokens=949 chars=832 | out.token_count(含toc)=1334 chars=1375 | wrap 後注入段 tokens=2017 chars=2890
[prospect] q='合約到期怎麼續約': hit, 5 候選 tokens=1657 chars=1434 | out.token_count=2042 chars=1977 | 注入段 tokens=2870 chars=3789
[prospect] 整份視圖 wrap 後 tokens=7523 chars=9551（doc.token_count=6187）；降級 from_visible: sections=14 token_count=3751 chars=3489
[property_manager] 啟動視圖 token_count=10896 chars=13977 sections=193 citable=9 標題only=183 | 標題only 節合計 tokens=9353 | toc tokens=283
[property_manager] q='請問怎麼收租金'(+上一則): hit, 5 候選 tokens=821 chars=790 | out.token_count=1116 | 注入段 tokens=1599 chars=2231
[property_manager] q='合約到期怎麼續約': hit, 5 候選 tokens=618 chars=620 | out.token_count=913 | 注入段 tokens=1250 chars=1901
[property_manager] 降級 from_visible: sections=10 token_count=1541 chars=1680 visible_subset=9
```
