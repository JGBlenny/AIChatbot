> ⚠️ 2026-09-06 業主裁：本 Plan 撤回（見 knowledge-outline-and-intent-architecture 需求 D／設計決策表；改以「細目標題＋講法」目錄式檢索重立）。留檔供三輪審查處置參考。
# Plan v3：prospect agent 路徑「候選段落注入」（DSP-035 提案）— 2026-09-06
（v1→v2 併入 plan-verifier P1×3／P2×6；v2→v3 併入 security-reviewer P1×3／P2×6／P3×6。**§9「v3 修訂」與正文衝突時以 §9 為準。**）

## ⚠️ 需業主明示放行的事
本 slice **反轉已核准的 requirements**：`requirements.md` 摘要行「整池整理成 6–8K token 進上下文，不用向量檢索」、決策表第 3 條（撈鄰居＝張冠李戴來源）、非目標「答案分塊多向量檢索另案」、R5.1「同一份完整的產品大綱」。處置：四處以 DSP-035 註記「被取代／收窄」，⛔ 不刪原文；原理由（張冠李戴）由判準③（同批同判者的無據率不得升）覆蓋。

## 0. 問題陳述（量過的）
prospect agent 在 54 句 topics 上答到率 30%（舊鏈 55%）。獨立代理判 54 題中 39 題大綱可直接答（0 題無資料）；這 39 題 agent 只答 34%、舊鏈 71%。agent 未答的 155 回合＝Verifier 拒到預算用盡 75（48%）、**模型自報 no_grounding 68（44%）**、模型誤標敏感 12（8%）。依問法型：直接 51%／俗稱 42%／口語 19%／情境 12%（舊鏈 61／85／68／32）。⇒ gpt-4o-mini 在 3,078 tokens 整份大綱裡做不好「口語問法→段落」對應；舊鏈靠向量檢索做這件事。
離線上限（embedding-api，49 題 answerable/partial，gold＝代理標的依據句）：大綱切成 59 個【】段落（中位 81 字）時 top-3 召回 71%、**top-5 召回 86%**、平均帶入約 490 字；reranker 在 59 個短段落上無增益（82% vs 86%）；13 題「可答卻 6 次全沒答」top-5 命中 12 題。
（來源：`eval/perf-agent-regression-20260905/round9-dsp033/README.md` 附錄；scratchpad `outline_answerability.jsonl`）

## 1. 程式封套（program envelope）
**目標形態**：程式負責「找候選」、模型負責「判斷與組話」、Verifier 負責「不放過捏造」。prospect 回合前由程式對大綱段落做向量檢索取固定 K 段，以 DSP-029a 標記注入為可引用資料；模型只能引用被給的段落（第一道牆），Verifier 步③（DSP-029a 尺）與其餘六步不變（第二道牆）。
**反轉的既定決策**：design「prospect 大綱進上下文、不用向量檢索」→ 改為「程式選段、模型不得自選來源」。理由與數字如 §0；立 **DSP-035**。
**不做**：補講法（第二刀，另 slice）、fact_class 誤標的程式側覆寫（另 slice）、tenant／pm 路徑、reranker、任何 τ／K 的事後調參。
**slices**：S1 候選段落注入（本 Plan）；S2 索引側多向量講法錨點（一段多向量、取最大相似；錨點＝審過的表示法別名，D3 紀律，來源＝question_summary 關鍵字／幫助中心標題／koyu 未入測試集句子／上線後真流量回填；⛔ 54 句凍結題永不入索引；S1 收案、看清 14% 漏在哪一型哪幾格後才起）；S3 fact_class 程式側覆寫（第一人稱情境被誤標客戶案例；待 S1 數據）。⛔ 全程不做 LLM 查詢改寫（前 spec A/B 10/10 無差、+600–800 ms）。

## 2. Slice S1：候選段落注入
### 2.1 結果（outcome）
prospect 回合：程式以（當前使用者訊息＋上一則使用者訊息，若有）為查詢，對大綱段落（固定切法、穩定 id）做向量 top-K（**K=5 固定常數**，⛔ 不做事後調參），以現有 DSP-029a 機制注入為 `OUTLINE_TOOL_CALL_ID` 的 Provenance（每段一筆、source＝段落 id），另附**不可引用**的章節目錄（section id＋title）讓模型必要時 `kb.get("outline:<section>")` 讀整節。模型引用標記、`resolve_refs`、Verifier 七步、handoff／重寫預算完全不變。

### 2.2 範圍（檔案）
- `services/agent/outline.py`：新增 `outline_paragraphs(section) -> list[OutlineParagraph{id, section_id, text, citable}]`——切法**逐字等於離線量測那把尺**：`re.split(r'\n(?=【)|\n(?=- )|\n\s*\n', section.text)` → strip → 丟 <15 字；id＝`f"{section.id}#p{k}"`（k 為節內序號，⛔ 不用 hash）。事實：`section.text` 是「- 講法：答案」一列一筆，【】只出現在 3 節的答案內文，此規則對現行大綱切出 **59 段、中位 81 字、最大 271**。**凍結資產** `eval/outline-paragraphs-20260906.json`（主 session 已從容器產出，含每段 id／sha256／文字、outline_sha256 90e9a987…、split_rule；recall@5 86% 即以此 59 段量得）。unit 測試：對現行大綱切段結果與凍結資產逐段 sha 相等；大綱一變（sha 不同）測試須明示「需重凍結」而非靜默過。判準①⑥與停損線由此 86% 導出。
- 新檔 `services/agent/candidate_selector.py`：`CandidateSelector(embedding_client, k=5)`。程式常數（⛔ 皆非事後調參項）：`K=5`、`QUERY_EMBED_TIMEOUT_S=3.0`、`PREPARE_CONCURRENCY=8`、查詢窗口＝當前 user 訊息＋對話歷史最後一則 user（無則單句），以單一空格連接。
  - `async prepare(doc)`：**在 `bootstrap.build_runtime` 與大綱重建時呼叫，⛔ 不在回合內冷啟**；以 `EmbeddingClient.get_embeddings_batch` 分批（每批 ≤8）取 59 段向量；任一段向量為 `None` ⇒ `ready=False`（⛔ 不以殘缺集合服務）。快取鍵＝`doc.sha256`。
  - `async select(query)`：查詢 embedding 以 `asyncio.wait_for(..., QUERY_EMBED_TIMEOUT_S)` 包住；cosine top-K，同分以 id 字典序。
  - **fallback 判定以回傳值三態，⛔ 不靠例外**（`EmbeddingClient` 吞例外回 `None`）：`ready=False`／查詢向量 `None`／逾時 ⇒ 回 `None` 給 runtime 表示「無候選」。⛔ 不呼叫 LLM、⛔ 不用 reranker。
- `services/agent/runtime.py`：**路徑 (a)——不動 `PromptAssembler.build` 簽名（R11.5 白名單、`test_build_signature_has_no_channel_for_tool_results` 維持綠）**。runtime 以 selector 結果建一個滿足 `OutlineDocLike` 的 `CandidateOutlineDoc{audience=doc.audience, sha256=doc.sha256, version=doc.version, sections=[OutlineSectionLike(id=p.id, title=<節 title>, text=p.text, citable=p.citable) for p in top_k] + [OutlineSectionLike(id="outline:toc", title="目錄", text=<section id＋title 清單>, citable=False)]}`，**同一個物件**同時給 `PromptAssembler.build(outline=…)` 渲染與 `_seed_outline_provenance` 建 `tool_results_by_id[OUTLINE_TOOL_CALL_ID]`（r13 F-B：編號側與解析側同一份清單；unit 以同一性斷言 `is`）。audience fail-closed 守門保留且必測（prospect identity＋非 prospect 來源 ⇒ raise）。
  - selector 回 `None`（三態任一）⇒ **回退為現行整份 `OutlineDoc`**（context 更多、不是更鬆），`TurnTrace.violations` 加 `candidate_fallback_full_outline`，`candidate_ids=[]`；trace 另加 `candidate_ids: list[str]`（只有 id、無原文）。**正對照測試**：注入必然回 `None` 的假 client ⇒ violations 必含該字串、fallback 計數必增；無故障案例計數為 0 且測試證明計數器「跑過」（先注入一次故障再一次正常，觀察 1→1）。
- `services/agent/prompt_assembler.py`：**簽名與渲染路徑不動**（吃到的 `outline` 是 `CandidateOutlineDoc`，每段一節、標記 `[nonce:outline:<section.id>§i]` 照舊）。只改政策文一句：「資料段是與問題最相關的幾段；若都不相關可用 kb.get 讀目錄中的整節」（定義、不寫例子）。`REF_RE` 第三段 `([^\]\s]+)§` 接受 `#`，段落 id `outline:lease#p3` 可解析；同一 tool 回傳內 source 唯一 ⇒ 不觸發 `ref_ambiguous`。
- `services/agent/health.py`：**新建**欄位 `candidate_selector: {ready: bool, paragraphs: int, outline_sha: str, fallback_total: int}`；`fallback_total` 為行程啟動以來累計（⛔ 無時間視窗——DSP-034 已撤除視窗機制；多 worker 各自一份，註解明寫）。**紅燈條件唯一且機械**：`ready == False`。fallback 的觀測面＝trace violations 與 agent_eval 統計（判準④）。
- `services/agent/shadow.py`、`trace_view.py`、`_emit_agent_decision`（`decision_snapshot.agent` 加 `candidate_ids`、`candidate_fallback`；同步 `tests/unit/agent/test_runtime_req.py::_ALLOWED_AGENT_DECISION_KEYS` 並保留「多一鍵會紅」自證；不變量 30＝`scripts/audit/checks/agent_boundary.py::check_30_decision_snapshot_no_verbatim` 的 `DECISION_BANNED_KEYS={answer,quote,text,user_message}`，新鍵不在其中、值為 id 列表無原文；`make audit` 在主檢出 `/Users/lenny/jgb/AIChatbot`（feat/agentic-mcp）執行）。
- `tools/agent_eval.py`：新增 `--candidates {on,off}`（**評估工具專用**的依賴注入：off ⇒ `build_runtime(candidate_selector=None)` 走整份大綱路徑＝基線 arm；⛔ 不是線上開關、不讀 env）；report 加 `candidate_fallback 回合數`、`avg_candidates`、`candidates_mode`；JSONL 加 `candidate_fallback: bool`、`candidates_mode`（同步 `_EXPECTED_JSONL_KEYS` 與其測試）。
- 評估資產：`scratchpad/r9_blind/outline_answerability.jsonl` 提升為 `.kiro/specs/agentic-mcp-orchestration/eval/topics-v2-answerability-20260906.jsonl`（54 行、僅題目 id／label／依據句前 20 字，無使用者資料）並登入 `samples-manifest.json`（sha256 凍結；⛔ 不得依結果改標）。
- 測試（unit，容器內）：切段穩定性（同節同 sha 兩次切段相同；15 字合併規則；id 序號）；selector 決定性（同查詢同向量兩次 top-K 相同、同分序）；查詢組法（單輪／多輪）；runtime 注入形狀（每段一筆 source 唯一 ⇒ 無 `ref_ambiguous`；toc `citable=False` ⇒ 引用它得 `SOURCE_NOT_CITABLE`）；fallback 路徑（假 embedding client 拋例外 ⇒ 整份大綱注入＋violations 記錄）；prompt 資料段不含未選段落；health 欄位；decision_snapshot 鍵白名單。整合：`test_agent_turn_req.py` 用假 embedding client（⛔ 不觸網）。
- 文件：DECISIONS 新列 DSP-035（列出被反轉的原決策與原理由、由判準③覆蓋的說明）；design「知識供給」段改寫；**requirements.md 四處**（摘要行、決策表第 3 條、非目標、R5.1）加 DSP-035 註記、⛔ 不刪原文；tasks 加 4.6／4.7／4.8；`nli-offline`／round9 不動。

### 2.3 非目標
⛔ 不改 Verifier 任何一步、不改 rules、不改 fixtures 語義、不加講法、不做 fact_class 覆寫、不動 tenant／pm、不用 reranker、不做 K／查詢窗口的事後調參、不做線上部署。

### 2.4 收案（acceptance；跑前凍結）
同一套回歸（topics 54×3 rep、scenarios 23 turn×3 rep、sensitive 30×3；`--chain both`；**2 輪**），加盲標（兩位獨立代理、對「放行的 fact 句」標有據／無據；封包法同 round9）：
1. **answerable 39 題**（依凍結的 answerability 檔）agent 答到率（2 輪合併）≥ **60%**（現 34%；舊鏈 71% 為參考上限）。
2. 敏感 0 漏（任一 rep 漏即 FAIL）；禁詞 ≤3／輪。
3. **同批同判者**：同一輪回歸同時跑基線 arm（`--candidates off`）與 S1 arm（`--candidates on`），兩 arm 放行的 fact 句混成一個封包（不標 arm）交同兩位盲標代理；**S1 arm 無據率 ≤ 基線 arm 無據率**（一致子集）。跑前凍結此定義。
4. 正常回歸 `candidate_fallback` 回合 ＝ 0，且 unit 正對照證明計數器會動；降級演練：停 embedding-api 一回合 ⇒ 該回合在 ≤3 s 內回退整份大綱、trace violations 含 `candidate_fallback_full_outline`、health `candidate_selector.fallback_total` +1（`ready` 仍 true，因向量已在啟動時備妥）；另演練「啟動時 embedding-api 不在」⇒ `ready=false` ⇒ health 紅、回合全走整份大綱並記錄。
5. `run_turn` p95 ≤ 6 s（含每回合一次查詢 embedding；冷啟不存在，因 prepare 在啟動時完成）。
6. no_grounding 在 answerable 題的比例 ≤ 現 44% 的一半（≤ 22%）——這是本 slice 直接針對的病灶，單列。
7. 邊界 8 題不硬答 ≥ 現行同批（R9 83.3%／91.7%，取兩輪合併 87.5%）——候選段落更聚焦不得讓模型更敢硬答。
8. unit agent 全綠、`make audit` PASS、fresh verifier CONFIRMED。
**列明取捨**：召回漏掉的約 14% 會從「認不出」變成「真的沒給」→ 由目錄＋kb.get 補；context 從 3,078 tokens 降到約 500 字，成本下降、但每回合多一次 embedding 呼叫（本機約 50–100 ms）。

### 2.5 回滾
未部署（影子模式）；回滾＝`git revert` 本 slice commit（無開關、無殘留路徑——DSP-034 教訓）。

### 2.6 預算與停損
實作＋unit 約 1 天；兩輪回歸（兩 arm）約 2 小時、模型費約 $2.8；盲標兩位代理約 30 萬 tokens。停損：若 unit 綠但第一輪 answerable 答到率 < 45%（沒有動），停下回主 session 診斷（先看 candidate_ids 是否含 gold），⛔ 不調 K。

### 2.7 安全／信任邊界（待 security-reviewer 前置審，發現與處置補入此節）
候選由程式選、模型不得自選來源（工具邊界不變）；查詢文字送 embedding-api 與舊鏈相同（內部服務、無身分）；trace／snapshot 只記段落 id；目錄不可引用；prompt 注入面：段落內容仍經 `wrap_provenance_data` 消毒（同現行）。無新增憑證、無新增對外埠。

### 2.8 前置與擁有權
前置：DSP-034 已 commit（ccde97c）；embedding-api 在線（compose 既有）。擁有：executor（worktree、單一 owner）；主 session 收檔、跑回歸、派盲標與 verifier。


## 9. v3 修訂（security-reviewer 前置審 2026-09-06，逐條處置；本節優先於前文）
### 9.1 P1（FIX）
- **P1-1 政策文**：`services/agent/agent_rules.py::_POLICY_TEXT` 現含「⛔ 不需要、也不要為了引用大綱去呼叫 `kb.get`」——**該檔進範圍**，此句改為允許句（定義、不寫例子）：「資料段是與問題最相關的幾段；若都不相關，可用 `kb.get` 依目錄章節 id 讀整節後再引用」。unit：政策文不得含原禁止語、必含允許語。（前文 §2.2 對 prompt_assembler 的「只改政策文一句」作廢——政策文正本不在該檔。）
- **P1-2 doc 綁定**：`CandidateSelector.select(doc, query)` 明收 doc，首行 `if doc.sha256 != self._prepared_sha: return None`；`CandidateOutlineDoc` 的 `audience`／`sha256`／`version` **一律從同一個 doc 複製**，⛔ 不得填 `identity.resolved_audience()`（否則 `test_prompt_assembler_req.py::test_outline_audience_mismatch_fails_closed` 變恆真）。unit：`prepare(docA)`＋`select(docB)` 必回 `None`；正對照 `select(docA)` 回 K 段。
- **P1-3 產線接線**：`app.py::_init_agent_runtime` **進範圍**——prospect 主 runtime 與影子 runtime **共用同一個已 prepare 的 selector 實例**（各建一份會讓影子與主線不同鏈）。health 欄位改三態 `candidate_selector.state ∈ {absent, not_ready, ready}`：`not_ready` 紅；`absent` 在 agent 啟用（`_agent_configured()` 為真）時亦紅（比照 `_check_agent_scope_ready` ⛔ 不把不知道印成綠）。unit：`tests/unit/agent/test_bootstrap_req.py` 加「產線路徑必須帶 selector」（與 `test_build_runtime_default_does_not_set_attempt_sink` 對稱）；`rg -n candidate_selector rag-orchestrator/app.py` 須兩處。
### 9.2 P2（FIX）
- **P2-1**：`PREPARE_TIMEOUT_S=20.0` 程式常數，`asyncio.wait_for` 包住整個 `prepare`；逾時 ⇒ `state=not_ready`（⛔ 不 raise、不掛啟動）。unit：永不回應的假 client ⇒ 在上限內回 not_ready（斷言耗時上界）。註：`UVICORN_WORKERS` 預設 4，各行程各自 prepare。
- **P2-2**：runtime 對 selector 的呼叫點 `except Exception` ⇒ 視同 `None`（整份大綱）＋ violations 記 `candidate_selector_error`（與 `candidate_fallback_full_outline` 分開）＋ `logger.warning`（⛔ 不帶查詢原文、不帶段落文字）。理由：fallback 方向是資訊更多，降級安全；violation 讓它在 trace 大聲。
- **P2-3**：`OutlineSectionLike` 是 Protocol 不可實例化；新增具體 `CandidateSection(BaseModel)`，`citable: bool` **必填無預設**。unit 直接對 `_seed_outline_provenance(candidate_doc)` 斷言 `outline:toc` 筆 `citable is False` 且某段落 `is True`（⛔ 不只測「引用 toc 得 SOURCE_NOT_CITABLE」）。
- **P2-4**：目錄行格式固定為「章節：<title>（要看整節請用 kb.get，id 是 <section.id>）」，⛔ 不含任何 `section.text`（unit 斷言目錄文字只由 `(id, title)` 組成）；**驗收新增 ⑨：topics `budget_exhausted`（2 輪合計）≤ round9 同批 84/324，且不得高於基線 arm 同批**。
- **P2-5**：降級演練判準改以 **trace violations**（每回合一筆、可歸屬）為準，`fallback_total` 只當觀測值；演練時 `UVICORN_WORKERS=1` 並寫進 README。刪除前文對 DSP-034 的引用（DSP-034 撤的是 NLI 線上路徑，非視窗告警機制本身）；改寫為「本 slice 影子期不做視窗告警；上線前另裁」。
- **P2-6**：unit 對 `candidate_ids` 加形狀斷言（每元素 `re.fullmatch(r"outline:[a-z0-9-]+#p\d+")`、長度 ≤ K），正對照放一個違規值必紅。
### 9.3 P3（處置）
- **P3-1（FIX）**：selector 呼叫 `EmbeddingClient.get_embedding(..., verbose=False)`；selector ⛔ 不得 log 查詢字串或段落文字（unit 用 caplog 斷言）。
- **P3-2（ACCEPT，明文）**：`candidate_ids` 是使用者問題的低解析度代理（5/59 個 id 可回推主題），為 §2.6 停損診斷所需，接受並記入 DSP-035。
- **P3-3（FIX）**：answerability 資產提升前驗每行鍵 ⊆ {idx,q,label,unit,why}（q 為凍結測試題句、非使用者資料），且每個 `unit` 前綴可在 `outline-paragraphs-20260906.json` 找到；不符即停。
- **P3-4（ACCEPT，明文）**：`outline_sha` 語義不變（候選文件複製母 doc 的 sha）；兩 arm 同 sha，區分靠 `candidate_ids`／`candidates_mode`。
- **P3-5（FIX 文字）**：今日無大綱熱重建路徑（`app.state.agent_outline` 只設一次），`prepare` 只在啟動時呼叫；前文「與大綱重建時呼叫」改為前提敘述：日後若加熱重建，prepare 與 doc 必須原子換手。
- **P3-6（REPORT，不動）**：`services/agent/outline.py::_fetch_prospect_pool_rows` docstring 稱不變量 29 略過本檔，但 `agent_boundary.py::check_29_predicate_single_source` targets 已含它——文件過時，交主 session／業主裁，非本 slice 範圍。
- **DSP-034 一致性（明文）**：`candidate_selector=None` 分支**不是**休眠開關，是 embedding-api 不可用時的降級路徑（真流量會走到）；`--candidates off` 只存在於評估工具；加一條可 grep 斷言：`services/` 下 ⛔ 不得出現讀取 candidates 相關 `os.environ` 的程式。
### 9.4 回歸報告
兩 arm 報表須標明 `candidates_mode=on` 為 production 組態、`off` 為評估基線（Req 9.4 精神）。

## 10. 待業主明示放行（送審前總結）
1. 反轉 requirements.md 四處既核准條文（DSP-035）。
2. 接受 `candidate_ids` 低解析度代理進 decision_snapshot。
3. 兩輪回歸兩 arm 的模型費約 $2.8 與盲標代理費用。

## 11. S2 設計備忘（2026-09-06 與業主討論定向；⛔ 不在 S1 範圖，S2 立案時以此為起點）
**目標形態**：一段多向量（段落本文 1 向量＋每個講法錨點 1 向量），檢索取「查詢 vs 該段所有向量」的最大值；⛔ 不把多種講法接成一條字串算一個向量（會平均成一團、每種問法都對不準——`question_summary` 塞多會失效的原因）。

**存放與對應**
- 新表 `agent_paragraph_anchors`（正統 migration）：`kb_id`、`paragraph_key`、`phrasing`、`source ∈ {question_summary, helpcenter, koyu, traffic}`、`status ∈ {proposed, approved, retired}`、`approved_by`、`approved_at`、`hit_count`、`last_hit_at`。⛔ 不放進 `knowledge_base`：任何 kb UPDATE 撞 `updated_at` trigger 連鎖不變量 10 並改變大綱版本；錨點是進場別名不是知識內容（勿重蹈錨點 vs 責任的層級錯配）。
- `paragraph_key = sha256(段落文字)[:16]`，⛔ 不用序號：知識文字一改 key 消失、掛在上面的錨點成孤兒進待審清單，由人決定重掛或退役（內容變了講法是否仍適用要人判）。
- 索引＝已核可錨點 × 現行段落，於啟動時建；快取鍵＝大綱 sha＋錨點集 sha，health 印兩個 sha。

**來源與審核**
- `question_summary`：程式自動導出（該筆講法關鍵字掛到其所有子段），不審、隨知識列同步——**可提前為 S1 第三 arm**（`on+summary`），因為零新內容。
- `helpcenter`／`koyu`：工具批次提案 → dry-run 在凍結測試集量 recall@5 與依問法型變化 → 業主放行 → `approved`（與知識批次匯入同紀律）。
- 離線生成：模型離線對每段產生候選講法，工具去重＋排除凍結題，人只勾選不撰寫（審核者看得到段落本文）。
- `traffic`：上線後「被問、放行、引用段落 X、盲標有據」的原句去識別後提案掛 X；必過人審（誤掛會製造錯召回）。
- ⛔ 54 句凍結測試題永不入表（工具層拒絕相同或極近句）。

**汰換與稽核**
- trace 記 `candidate_ids` 與勝出向量 id → 每錨點 `hit_count`。
- 規則：長期零命中退役（改狀態不刪）；命中但 gold 在別段者列誤召回清單、優先退役或改掛；每段錨點上限 8，超過以命中數與近似度去重。
- 每次錨點集變動在凍結測試集重跑召回、數字進 README；⛔ 不憑感覺上線。

**容錯理由（為何錨點不必對得完全準）**：檢索只負責把 K 段撈進來，不排第一；A 題錨點搶到 B 題的查詢，只要 B 段也在 top-5，由模型在候選裡判斷；引錯段的句子由 Verifier 覆蓋∧極性尺擋（同批抓到 62%，非全能）。會痛的只有兩種：B 被擠出 top-5（錨點上限與去重的存在理由）、A／B 不同節但講法相近（靠誤召回稽核）。

**規模與成本**：一段 3–6 個框架不同的錨點即足（直接／俗稱／情境／反面），超過 8 多為重複；1,000 多個向量建索引一次幾秒、費用不到一分錢；線上每回合只算查詢一個向量＋記憶體 cosine（<1 ms）。reranker 在 S1（59 段）無增益，S2 錨點撐大候選池後再量，不預設。

**不做**：LLM 查詢改寫（前 spec A/B 10/10 無差、+600–800 ms）；把講法塞進 `question_summary` 或 answer；用被驗系統自己的排序判「已覆蓋」。
