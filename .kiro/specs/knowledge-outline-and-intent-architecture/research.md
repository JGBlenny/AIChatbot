# 研究記錄：knowledge-outline-and-intent-architecture

> 建立時間：2026-09-06T10:13:36+0800（HEAD `138084fa`，分支 `feat/agentic-mcp`）
> 目的：記錄 design 前的整合點對碼、架構選項評估、相依性與風險。發現流程：**light**（既有系統擴展；無新外部服務、無新 LLM 供應商；主要風險在資料模型與流程機制，不在技術棧）。
> ⛔ 本檔每條事實附可重跑查證；未實查者明標。文件與程式衝突以程式為準（CANON）。

## 摘要

### 調查範圍
1. 既有 agent 路徑的四個接縫：大綱組裝（`services/agent/outline.py`）、prompt 組裝與資料段（`prompt_assembler.py`）、回合迴圈（`runtime.py`）、槽位工具（`tools/session.py`）。
2. 既有工具鏈能否承接正本：匯入（`tools/import_facet_knowledge.py`）、評估（`tools/agent_eval.py`）、缺口地圖（`coverage-map/`）、問法正本（`koyu-v2-phrasings.json`）。
3. skill 執行形態的機制面：Workflow 撰寫規約（`workflow-authoring`）、使用者層 hook 先例（`~/.claude/settings.json` 的 CANON hooks）、本 repo 的 `.claude/` 現況。
4. 已撤回的 DSP-035 Plan v3 有哪些零件可直接沿用。

### 關鍵發現
- **組裝器與注入面已經是「程式組裝、無 LLM、sha 綁定」的形狀**：`OutlineDoc{audience, version, sha256, token_count, sections, text}` 與 `PromptAssembler.build()` 的封閉參數表（`inspect.signature` 鎖住）都可原樣沿用；本 spec 只換**資料來源**（kb 列自動分類 → 正本細目），不動注入面白名單（R11.5／DSP-012）。
- **DSP-035 Plan v3 的 `CandidateOutlineDoc` 形狀可直接沿用**：runtime 建一個滿足 `OutlineDocLike` 的物件同時餵渲染側與 `_seed_outline_provenance` 解析側（r13 F-B 同一性）；把「段落」換成「細目」即可，三輪審查的 P1 處置（doc sha 綁定、主／影子共用 selector、fallback 三態、health 三態、`candidate_ids` 無原文）全部適用。
- **槽位預填不必等 `COLLECTING` 會話列**：`runtime.run_turn` 每回合以 `_slots_for_prompt(state)` 攤平後交 `PromptAssembler._slot_blocks`；身分預填可在此**從 `Identity` 派生、只進 prompt 不落 DB**，R8.2 需求票因此收窄為「`SlotKey` 擴充四值」，不需改 `slots_set` 的建列語義。
- **審核旗標已有兩個先例可對齊**：`knowledge_base.outline_approved_by`（DSP-012 R11.6，值為標記者字串）與 `help_center_pages.citable_requires_approval`（CHECK 約束：`citable=false OR approved_by IS NOT NULL`）。R2.7「池標記 vs 內容已審」以**值域約定**即可落地（`pool-marked-*` 前綴＝池標記；其餘＝內容已審），⛔ 不需新欄位、不需 migration。
- **Workflow 與 hook 在本 repo 零先例是刻意保留**（業主 2026-09-06 核可時定向）：使用者層 `~/.claude/settings.json` 已有 `PreToolUse(Read|Edit|Write)`／`PostToolUse(Edit|Write)`／`Stop` 三類 hook 掛 `~/.claude/canon/*.py` 的成熟樣板，本 spec 在 repo 層 `.claude/settings.json` 複製同形狀即可；Workflow 規約明訂 `meta` 純字面、`pipeline()` 預設、`schema` 強制結構化輸出、`agent()` 可掛 `agentType`，判者 fan-out 正是它的標準用例（adversarial verify／judge panel）。
- **live DB 對數（2026-09-06 實查，正對照 `active_all`）**：`outline_approved_by IS NOT NULL`＝**29**（與 F2 一致）、`is_active AND 'prospect'=ANY(target_user)`＝**25**（＝F2 的 21 已標＋4 未標）、`is_active` 全體＝**926**（PLAN v2 記 922，+4 為 2026-09-04 後新增，不影響本 spec）。查證：`docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tAc "SELECT (SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL),(SELECT count(*) FROM knowledge_base WHERE is_active AND 'prospect'=ANY(target_user)),(SELECT count(*) FROM knowledge_base WHERE is_active)"`。
- **幫助中心頁面在交付目錄是扁平檔名**（`*_zh-Hant.html` 92 份、`*_en.html` 79 份），⛔ 不是 `zh-Hant/` 子目錄；R7／R3 的分母工具要以檔名後綴切語系。查證：`ls "/Users/lenny/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818" | grep -c "_zh-Hant.html"` ⇒ 92。

## 研究主題

### 主題 1：大綱組裝與注入面——哪些不動、哪些換
**調查問題**：正本取代 kb 自動分類後，`outline.py`／`prompt_assembler.py`／`runtime.py` 各要動多少？
**研究方法**：現有程式碼分析（三檔全讀）。
**發現**：
- `outline.py::build_prospect_outline` 的資料來源＝`_fetch_prospect_pool_rows`（`outline_approved_by IS NOT NULL` ＋ `build_visibility_predicate`）→ `_classify_row`（`SIX_MODULES` 關鍵字表）→ 14 節（六模組／四類／兜底／`outline:boundary`／`outline:deliberate-gaps`／`outline:cta`）。`_build_doc` 的 sha 涵蓋 `version`＋`text`，`check_budget` 啟動即紅，`make_outline_resolver` 只查 cache——三者與資料來源無關，**可原樣保留**。
- `prompt_assembler.build()` 參數表封閉（`identity, outline, slots, dialog, tool_specs, nonce`），大綱經 `wrap_provenance_data("outline", …)` 逐章節片段編號（`[{nonce}:outline:{section.id}§{i}]`）；`_REF_RE` 第三段 `([^\]\s]+)§` 接受 `#`／`/`，細目 id 可含 `/`。
- `runtime.run_turn`：`outline = agent_state.get("outline")` → `_seed_outline_provenance(outline)` 建 `tool_results_by_id["outline"]` → `assembler.build_messages(identity, outline, slots, dialog, tool_specs, nonce)`；`_build_fixed` 用 `effective_handoff_message(None)`（F5：DB 設定從未被讀）。
- `app.py::_init_agent_runtime` 於啟動建 `agent_outline`＋`outline_resolver`；`agent_entry.handle_agent_entry` 只對 prospect 把 `app.state.agent_outline` 放進 `state["agent"]["outline"]`（記憶體，不落地）。
**結論與建議**：
- 新增 `services/agent/canon/`（parser／assembler／fine_index／candidate_selector），`build_prospect_outline` 改為薄包裝呼叫 `canon_assembler.build_outline(canon_doc)`；`SIX_MODULES`／`_classify_row`／`_CTA_TEXT`／`DSP009_DELIBERATE_GAPS`／`_extract_boundary_sentences` 隨正本 G／F 粗目退役（R2.6）。
- runtime 只加三處：回合前 `CandidateSelector.select()` 建 `CandidateOutlineDoc`（沿 Plan v3 路徑 (a)）、身分槽位派生、CTA 程式端附加；`effective_handoff_message(cfg)` 改吃 `config_for_target_user` 的設定（R4.6）。

### 主題 2：DSP-035 Plan v3 可沿用的零件與必須改的地方
**調查問題**：已撤回的候選段落注入設計，哪些是「段落」專屬、哪些是通用機制？
**研究方法**：讀 `reviews/plan-dsp035-s1-candidate-paragraphs-v3-WITHDRAWN.md` §2.2／§9。
**發現**：通用機制——`CandidateSelector.prepare(doc)` 於啟動預算向量、`select(doc, query)` 首行比對 `doc.sha256`（P1-2）、主／影子共用同一 selector 實例（P1-3）、health 三態 `{absent, not_ready, ready}`、回合內 `except Exception` ⇒ 整份大綱＋`candidate_selector_error`（P2-2）、`candidate_ids` 形狀斷言（P2-6）、selector ⛔ 不 log 查詢字串（P3-1）、`--candidates {on,off}` 為評估工具專用 DI（DSP-034 一致性）。段落專屬——`outline_paragraphs()` 切法、`#p<k>` id、59 段凍結資產、86% 停損線。
**結論**：機制全數沿用；切段換成正本細目（id 穩定、內容 sha）；匹配鍵由「內文向量」換成「標題向量＋講法向量取最大」（R5.2 預設），內文向量作 R6 步 1 的第三臂。停損線由步 1 重量，⛔ 不沿用 86%（F10 明標為代替品）。

### 主題 3：skill 執行形態——hook＋Workflow 的最小可行落點
**調查問題**：閘門要掛哪些事件、Workflow 要包哪幾步、本 repo 缺什麼？
**研究方法**：讀 `~/.claude/settings.json` hooks、`workflow-authoring` 規約、`.claude/skills/retrieval-improvement-loop/SKILL.md` 五道閘門、`.claude/settings.local.json`。
**發現**：
- 使用者層 hook 樣板：`PreToolUse` matcher `Read|Edit|Write` → `spec_gate.py`（M1「改 X 前必讀 Y」）；`PostToolUse` matcher `Edit|Write` → `refcheck.py`／`taskcheck.py`；`Stop` → `finishgate.py`（timeout 900）。hook 以 `sh -c '[ -f … ] && exec python3 … || exit 0'` 包裝，缺檔即放行。
- 本 repo `.claude/` 只有 `settings.local.json`（allow 清單）、`skills/`、`MAP.md`、`DECISIONS.md`、`canon.json`、`prerequisites.json`；無 `settings.json`、無 `hooks/`、無 `workflows/`、無 `agents/`。
- Workflow 規約：`agent(prompt, {schema, label, phase, effort, agentType})` 強制結構化輸出；`pipeline()` 預設、`parallel()` 只在需要全部結果時；判者隔離＝各 agent 獨立上下文、prompt 不含系統判定；可 `resumeFromRunId` 續跑；`Date.now()`/`Math.random()` 不可用（時間戳由 `args` 傳入）。
- `retrieval-improvement-loop` 五道閘門（G1 前提／G2 管線自證／G0 權威來源／G4 獨立驗證／G3 單一變因）靠 SKILL.md 文字；`g2_selftest.py` 已是可執行閘門的雛形。
**結論**：
- 閘門（R1.4）落 repo 層 `.claude/settings.json` 三個 hook：`PreToolUse(Edit|Write)` 守正本檔（無 id 對應表／材料 sha 未凍結即擋）、`PostToolUse(Edit|Write)` 驗正本 schema、`Stop` 驗「受測物定義清單」與「凍結題不入講法」。腳本放 `.claude/hooks/outline_gate.py`，同一支腳本依 hook 事件分派。
- Workflow（R1.5）只包**三步**：提議結構（judge panel N=3 → 合成）、判可答性（判者 fan-out，每格 2 判者＋不一致時第 3 判者）、重量覆蓋（機械，可不用 agent）。其餘步驟（讀輸入、差異表、入庫）為決定性腳本，⛔ 不進 Workflow。
- 最小試作（R1.5）＝「判可答性」一步：輸入 55 格＋正本草稿，量成本（token／時間）、判者一致率、可回放（同 args 同 runId 續跑）。

### 主題 4：審核狀態與 `kb.get` 直取的約束落點
**調查問題**：R2.7／R5.4「只放行內容已審」要動哪些讀取點？
**研究方法**：讀 `tools/kb.py::fetch_visible_row`、`outline.py::_fetch_prospect_pool_rows`、`vendor_knowledge_retriever_v2.build_visibility_predicate`、`help_center_pages` migration。
**發現**：`fetch_visible_row` 只拼 `build_visibility_predicate`，不看 `outline_approved_by`（F14）；`build_visibility_predicate` 刻意不含相關性條件（docstring 明寫）；不變量 29 要求可見性謂詞單一來源（`check_29_predicate_single_source` 掃 `_vector_search`／`_keyword_search`／`fetch_visible_row`）。
**結論**：新增 `services/agent/canon/review_state.py::content_reviewed_predicate()`（回 `AND kb.outline_approved_by IS NOT NULL AND kb.outline_approved_by NOT LIKE 'pool-marked-%'`）作**第二個單一來源**，只在 agent 路徑的 `fetch_visible_row` 與正本組裝拼接；⛔ 不併進 `build_visibility_predicate`（那會影響舊鏈檢索）。不變量新增一條掃 `kb.get` 路徑必拼此謂詞（R8.4 需求票）。

### 主題 5：驗證材料與工具鏈的對接
**調查問題**：R6 四步各用哪支工具、缺什麼？
**研究方法**：讀 `tools/agent_eval.py` 參數與 manifest 紀律、`inputs/phrasing-selection-rule-20260906.json`、`inputs/outline-paragraphs-proxy-20260906.json`、`coverage-map/demand-v2.json` 的 `_meta.states`。
**發現**：
- `agent_eval.py`：`--set {topics,scenarios,sensitive,traffic}`、`--chain {old,agent,both}`、`--provider {fake,openai}`、`--repeat N`、manifest sha 不符 exit 3；`EvalRecord` 18 欄；無 rubric 判對錯（A3 未實作，指向 `answer-acceptance-verify` skill）。
- 問法選題規則已凍結（422 句、sha `b771a6e5…`、每篇每型取 1 句、排除凍結 54 句與「操作」型）；段落代替品 59 段（`outline_sha256 90e9a987…`）明標 ⛔ 不作索引。
- 缺口地圖狀態機（`cause_state`／`entry_state`／`coverage`）已定義於 `demand-v2.json._meta.states`，格 id `C01–C55`。
**結論**：
- 步 1（$0）：新工具 `tools/canon/index_eval.py`——輸入正本 JSON＋422 句（各句對得到細目者為 gold，由判者標）；三臂（標題／標題＋講法／＋內文）留一輪替；輸出 recall@1/3/5 依粗目×問法型。
- 步 2／3：`agent_eval.py` 加 `--set outline-probe`（新樣本集，manifest 登記）與 `--candidates {on,off}`；rubric 判對錯走 `answer-acceptance-verify`（skill 已存在）。
- 步 4：放量走 `--set traffic`（現況缺席，需 D3 裁後才有材料）。

## 技術選型

### 選型 1：正本格式
| 方案 | 優點 | 缺點 | 適用場景 |
|---|---|---|---|
| A Markdown＋front matter | 人審／diff／code review 天然 | 需 parser；講法多時檔案長 | 人審為主 |
| B JSON／YAML | schema 校驗、直接餵組裝器 | 人審不友善 | 機器為主 |
| **C 混合：Markdown 正本，parser 單向導出 JSON（同 sha）** | 兩邊各得其所；JSON 是**衍生物**不入人審 | parser 是新元件 | 本案 |
**最終選擇**：C。**理由**：R2.9 把正本寫入權視為 system prompt 寫入權，審核必須發生在 diff 可讀的介面（Markdown＋git）；組裝器、匯入工具、索引都吃結構化輸入 ⇒ 由 parser 決定性導出、JSON 帶 `canon_sha256`（＝Markdown 位元組 sha），健康檢查印同一個 sha 證明兩邊同源。

### 選型 2：細目索引存放
**最終選擇**：記憶體內（啟動時 `prepare`，快取鍵＝正本 sha＋講法集 sha；health 三態），沿 Plan v3 P1-3。**理由**：量級 ≤2k 向量；無 migration；決定性；多 worker 各算一份的成本＝啟動時一批 embedding 呼叫（≤2k 句、每批 ≤8）。pgvector 新表（方案 B）留作講法數超過 5k 時的升級路徑。

### 選型 3：講法表
**最終選擇**：講法存在正本檔內（版控、review），命中數由 trace（`winning_phrasing_id`，R8.3）在 `usage_events.decision_snapshot.agent` 累積，離線以 SQL 聚合回填報表。**理由**：R2.9 治理（審核走 review）；零命中退役＝改正本內 `status`，可 revert；tasks 4.7 的新表方案改為**升級路徑**（講法量或回填頻率超過檔案可承受時）。

### 選型 4：skill 執行形態（R1.5 已定向）
**最終選擇**：hook（紀律）＋Workflow（判者 fan-out／結構提議）＋決定性腳本（其餘步驟）。詳主題 3。

## 相依性分析

### 外部 API 與服務
| 服務 | 版本 | 用途 | 注意事項 |
|---|---|---|---|
| embedding-api（`services/embedding_utils.EmbeddingClient`） | 既有 | 細目標題／講法向量、查詢向量 | 30 s timeout、吞例外回 `None` ⇒ selector 三態判定；⛔ 不換模型（範圍外） |
| OpenAI Chat Completions（`llm_provider`） | 既有 | agent 回合、Workflow 判者 | 判者走 Claude Code 子代理（Workflow），⛔ 不走本系統 provider |
| jgb2 `external/v1` | 既有 | LINE 受眾實值 | ⛔ 不入正本（R7.1） |

### 函式庫與套件
| 套件 | 版本 | 用途 | 風險 |
|---|---|---|---|
| `tiktoken` | 0.14.0（既有） | token 預算 | 取不到編碼退近似值（既有 `_count_tokens`） |
| `pydantic` | ≥2.13 | CanonDoc／FineItem 模型 | 無 |
| `python-frontmatter` 或自寫 | — | Markdown front matter | **自寫**（避免新依賴；front matter 只有固定五鍵） |

## 現有程式碼分析

### 相關模式與慣例
- 單一謂詞來源：`build_visibility_predicate`（不變量 29）；本案新增第二個單一來源 `content_reviewed_predicate`，同樣以 checker 守。
- 「同一物件餵兩側」：`_seed_outline_provenance(outline)` 與 `build_messages(outline)` 吃同一個 `OutlineDocLike`（r13 F-B）。
- 「程式常數＝已審核來源」：`agent_rules.py` 進版控、走 review（DSP-012 選項 A）；正本沿用同一治理層級。
- 「無原文」：`decision_snapshot.agent*` 不得含 `answer/quote/text/user_message`（不變量 30）；新鍵 `candidate_ids`／`winning_phrasing_id`／`miss_kind` 皆為 id／列舉。
- 評估工具紀律：manifest sha 不符 exit 3；`--provider fake` 預設；`--dump-texts` 不進版控。

### 整合點
| 整合點 | 檔案／符號 | 改動型態 |
|---|---|---|
| 大綱資料來源 | `services/agent/outline.py::build_prospect_outline` | 改為讀正本 JSON；保留 `_build_doc`／`check_budget`／`make_outline_resolver` |
| 候選注入 | `services/agent/runtime.py::run_turn`（`outline = agent_state.get("outline")` 之後） | 加 selector 呼叫與 `CandidateOutlineDoc` |
| 身分槽位 | `runtime.py::_slots_for_prompt`、`tools/session.py::SlotKey` | 派生預填＋enum 擴四值 |
| CTA／handoff | `runtime.py::_build_fixed`、`_finalize`；`conversational_config.effective_handoff_message` | 改吃 `config_for_target_user(identity)` |
| 直取約束 | `tools/kb.py::fetch_visible_row` | 拼 `content_reviewed_predicate()` |
| 匯入 | `tools/import_facet_knowledge.py` | 加 `approved_by`／`replaces` 欄位（批次由 `tools/canon/export_batch.py` 導出） |
| 評估 | `tools/agent_eval.py` | `--candidates`、新樣本集 |
| health | `services/agent/health.py` | `canon: {audience, canon_sha, index_sha, state}` |
| 不變量 | `scripts/audit/checks/agent_boundary.py`、`check_invariants.sh` | 新增 32–34（編號接續 27–31） |

## 效能考量
| 指標 | 目標值 | 測試方法 | 備註 |
|---|---|---|---|
| `run_turn` p95 | ≤ 6 s（現行 4.5 s＋一次查詢 embedding） | `agent_eval` `latency_p95_ms` | 冷啟不存在（啟動時 prepare） |
| 啟動 prepare | ≤ 2k 句、每批 ≤8 ⇒ 約 250 次呼叫 | 啟動日誌 | 失敗 ⇒ `not_ready` 紅、回合走整份正本 |
| 上下文 | 候選細目 K=5 ⇒ 約 500–800 字（vs 現行 3,078 tokens 整份） | trace `prompt_tokens` | 目錄（citable=False）另佔 ≤ 300 字 |

### 瓶頸分析
- embedding-api 是啟動與每回合的唯一外部依賴；三態降級已在 Plan v3 定型。
- Workflow 判者 fan-out 的成本＝格數 × 判者數 × 每判者上下文；55 格 × 2 判者 ≈ 110 個子代理，在 16 併發上限下約 7 輪；R1.7 預算上限由 design 定（見 design 決策 7）。

## 安全性考量
### 威脅模型
- 正本＝system prompt 的一部分（DSP-012）：任何能改正本檔的人＝能改 prompt ⇒ 寫入權＝code review 權（R2.9）。
- 講法來源若含真流量原句 ⇒ 個資進版控（D3）。
- 候選注入把「模型自選來源」改為「程式選來源」——縮小注入面；目錄 `citable=False` 防止引用目錄行當事實。
### 緩解措施
- 正本只在 git；DB 是衍生物；`kb.get` 整數路徑受 `content_reviewed_predicate` 約束（R8.4）。
- D3 預設：不留原句、去識別四類（人名／地址／合約號／電話）、保留 90 天；去識別為 skill 的一步（schema 輸出）。
- selector ⛔ 不 log 查詢字串（Plan v3 P3-1）。

## 風險登記
| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|---|---|---|---|---|---|
| 售前 A–G 原稿不存在（F4），正本只能由 21 列重排，E 競品極薄 | 商業 | 高 | 高 | skill 首跑產出 G「現有不足」＋E 由既有 1 列＋幫助中心；業主審草稿時補或標不足 | 開放 |
| 細目標題匹配上限未量（F10 是內文代替品） | 技術 | 高 | 中 | R6 步 1 三臂先量，$0；結果決定 R5.2 與講法密度 | 開放 |
| 判者變異（兩批盲標對同尺差 9 點） | 技術 | 中 | 高 | R6.5 一致率 <90% 加第三判者；Workflow 判者 prompt 不含系統判定 | 開放 |
| Workflow／hook 首例成本超估 | 時程 | 中 | 中 | 最小試作只做「判可答性」一步，量完再排其餘兩步 | 開放 |
| 平台票（R8.1–8.4）未排 ⇒ R4.1／R5.8／R5.9 落不了 | 時程 | 高 | 中 | design 標依賴順序；R8.2 已收窄為 enum 擴充；R8.4 為一行謂詞 | 開放 |
| LINE 受眾可見集合未實查（vendor_id 缺值→0） | 技術 | 中 | 中 | R7.4 契約測試前先一次 SQL 對照 | 開放 |

## 開放問題
### 問題 1：正本細目與 kb 列的雙軌期
**描述**：R1.9 要舊列退役、kb 由正本衍生；但舊鏈（非 agent）仍讀 kb。
**影響範圍**：`knowledge_base` 的 prospect 池；`build_prospect_outline` 舊路徑。
**可能解法**：(a) 正本匯入時對舊列寫 `replaced_by=<細目 id>`（`generation_metadata`）並 `outline_approved_by='pool-marked-20260905'`；舊鏈不受影響。(b) 直接 `is_active=false`。
**決策狀態**：**已決定 (a)**——舊鏈仍讀（不動舊鏈是本 spec 範圍外的硬約束），只讓 agent 路徑不再把它們當索引或內容來源。

### 問題 2：講法向量的「一講法一向量」與 embedding 呼叫量
**描述**：講法數若達 2k，啟動 prepare 約 250 批呼叫。
**決策狀態**：接受（啟動一次；快取鍵不變即不重算；失敗走三態降級）。

## 時間軸
| 日期 | 活動 | 結果 | 後續行動 |
|---|---|---|---|
| 2026-09-06 | 需求 v2 核可、R1.5 定向 hook＋Workflow | 本檔＋design 1.0 | 業主審 design |

## 參考資源
- `.kiro/specs/agentic-mcp-orchestration/{design.md,research.md,reviews/plan-dsp035-s1-candidate-paragraphs-v3-WITHDRAWN.md}`
- `~/.claude/settings.json`（hooks 樣板）；`workflow-authoring` skill
- `.claude/skills/retrieval-improvement-loop/SKILL.md`、`.claude/skills/answer-acceptance-verify/`
- `rag-orchestrator/database/migrations/20260904_create_help_center_pages.sql`（審核約束先例）
- `.claude/DECISIONS.md` DSP-009／012／026／034
