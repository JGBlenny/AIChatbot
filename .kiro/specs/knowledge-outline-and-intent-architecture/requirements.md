# 需求規格：knowledge-outline-and-intent-architecture（知識大綱的建立與完善、口語多意圖下的對話架構、小量先於放量的驗證邏輯）

> 建立時間：2026-09-06　階段：requirements-generated（**v2**，依 fresh 審查 A1–A14／B1–B10／C1–C8 修訂）　語言：zh-TW
> 業主 2026-09-06 定義三支柱；平台層（MCP 工具邊界、Agent Runtime、Output Verifier、trace／計量本體、影子與 eval 工具）留在 `agentic-mcp-orchestration`，本 spec 只承接大綱、對話架構、驗證邏輯，並向平台層開需求票。
> ⚠️ 模板缺席：`.kiro/settings/rules/ears-format.md` 與 `templates/specs/requirements.md` 不存在，沿用 `agentic-mcp-orchestration/requirements.md` 格式。
> 編號規約：`R<n>.<m>` 兩段式，供 design／tasks 引用；⛔ 不用 a／b 子編號。待裁項以「（待裁 Dx）」標註，該條需求寫成**不預設答案的條件式**。

## 目標形態（業主 2026-09-06 定義）

> **第一原則（圖書館法）**：索引的是目錄——分類號（粗目）、書名（細目標題）、主題詞與「見／另見」參照（講法、交叉引用）、館藏標記（受眾／業態／審核狀態）；⛔ 不把內容片段當索引。找到書目才去讀內容（細目內容）並引用原句；Verifier 只查引文在不在書裡。控制詞彙（講法）由人維護、有出處與狀態。適用範圍：有人維護、量小（數十到數百條）的知識庫；切段落（chunking）是無序大語料的工具，不適用本系統。

```
skill（先有）：分析內容 → 提議粗目／細目 → 掛講法與缺口格 → 獨立判者標可答性 → 重量 → 差異給業主核 → 入庫
  每步 schema 輸出、閘門強制紀律、可回放、記成本；首次建立與日後重切同一條流程
大綱正本（每受眾一份，人審、版控、程式組裝、有 sha）
  售前：A 產品基本盤／B 適配／C 六大模組／D 方案試用／E 競品／F 導流／G 現有不足
  業者／LINE OA：依 chatai 文件與系統脈絡另定區塊，⛔ 不套售前切法
對話：入口帶身分 → 程式預填槽位 → 檢索選候選細目（標題＋講法向量）→ 模型判意圖／分叉才問／組話
      → Verifier 不放過捏造 → 可「部分回答＋帶理由轉人」（待裁 D2）
驗證：每個命題最小材料＋一把尺＋推翻條件，免費的先做；沒定義完受測物不開跑；材料以業主正本為優先
```

## 已查實的現況（2026-09-06；每條附可重跑查證，未實查者明標）

| # | 事實 | 查證 |
|---|---|---|
| F1 | 現行「售前大綱」＝`build_prospect_outline` 把 `outline_approved_by IS NOT NULL` 的列依 `SIX_MODULES` 分類表重排，另有 `NON_MODULE_CATEGORY_SECTIONS` 四類小節、`_MODULE_FALLBACK_SLUG` 兜底、`_extract_boundary_sentences` 邊界句段、`DSP009_DELIBERATE_GAPS` 刻意不補段、`_CTA_TEXT` 自寫 CTA 段（⛔ 不 import `PRESALES_CTA_RULES`），合計 14 節 | `rag-orchestrator/services/agent/outline.py` 上列符號 |
| F2 | 已標記列 **29**＝21 列 `target_user ∋ prospect` ＋ **8 列 `target_user IS NULL` 全域業者知識**（3335 對帳流程／3340 催繳／3342 繳費期限／3353 電表儲值／3355 生活公約／3356 訂閱取消／3357 物件批次匯入／3358 大房東授權），由 `IS NULL OR &&` 謂詞撈進售前大綱；4 列 prospect 未標（3645 對話規則列、3798 系統脈絡 append、5376／5377 依 DSP-026 取消）。⇒ 現行大綱混入業者操作知識，是「那不是售前大綱」的具體證據。舊文件的 31／32 為歷史值 | `SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL`（29）；`…AND 'prospect'=ANY(target_user)`（21）；`…AND NOT ('prospect'=ANY(coalesce(target_user,'{}')))`（8，列 id 如左） |
| F3 | `outline_approved_by='owner-20260905'` 來自 tasks 3.3 一次性 UPDATE（業主「幫我加」＝DB 寫入授權），**不是內容審核**；業主不認其為售前大綱 | `agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql`；tasks.md 3.3 收案註記 |
| F4 | 售前知識原稿 `jgb2/docs/presales-kb/01–03.md`（A–F）：本機三個 jgb2 checkout 未見；`git log --all --diff-filter=D` 於 jgb_1/jgb2 查刪除紀錄 0 筆（正對照：同指令列出其他已刪檔如 `tests/Unit/BillActivityLogCancelledBillIdMapTest.php`，查法有效）⇒ **未曾提交或在其他 repo**；記憶 `reference_presales_kb_source` 的路徑已失效，列 dispute。現存唯一正本＝F2 的 kb 列 | `find /Users/lenny/jgb -name '01-product-and-fit.md'`；`git -C …/jgb_1/jgb2 log --all --diff-filter=D --name-only` |
| F5 | 線上售前對話邏輯正本＝kb 3645「對話規則：售前顧問」（DB 覆寫程式預設 `PRESALES_CONFIG`）：每輪 A 事實題直答／B 推薦題補問；五欄位 identity／scale／team／pain／interested，一次一題、先同理再問、不重問、基本資訊門檻（identity＋scale 或 pain）、已推薦後三種回應、中途岔題；**fact_class 封閉七值每輪必填、「句形不是判準」（陳述句也算 feature）**；CTA 排版收束；不報價、競品中立、IoT 不主動；轉人訊息與通道由設定供給。**agent 路徑未搬**：`agent_rules.py::_POLICY_TEXT` 只有四條鐵則＋輸出契約（含一份 `_SENSITIVE_LINE` 由 `presales_gate.SENSITIVE` 反射）；`SlotKey` 六值（contract_ref／bill_ref／estate_ref／repair_ref／unit_count／business_type）無身分槽；`slots_set` 對無 `COLLECTING` 會話回 NO_MATCH、⛔ 不建列；`AgentOutput.kind` 有 ask／recommend 但無判準；agent 路徑轉人訊息硬掛 code 常數（`runtime.py` 兩處 `effective_handoff_message(None)`），DB metadata 從未被讀 | scratchpad `kb3645_presales_rules.md`；`services/agent/{agent_rules,runtime,tools/session}.py` |
| F6 | 入口已帶 `mode`／`target_user`／`role_id`／`user_id`／`vendor_id`（jgb2 面板、LINE 業務）；`Identity.resolved_audience()` 切工具範圍與可見謂詞；官網售前匿名 prospect、子身分未知；`agent_entry` 對缺值填 `vendor_id=0`、`target_user="tenant"`；模型端只收固定 persona 文字；`session.slots` 以 nonce 資料段渲染 | `routers/agent_entry.py`；`services/agent/prompt_assembler.py::_slot_blocks` |
| F7 | 同題不同受眾已分池：「合約／簽約／建約」pm 專屬 13 列＋面向列 4215（建約引導）／3825（系統脈絡建約子面向）；tenant 專屬 20 列；prospect 1 段（3600）；由 `build_visibility_predicate` 的 `target_user IS NULL OR &&`、業態、vendor 切。同池內身分子類分叉（法人 12 種範本／個人 4 種）未處理 | SQL：`is_active AND 'property_manager'=ANY(target_user) AND NOT 'tenant'=ANY(target_user) AND question_summary ILIKE ANY('{%建立合約%,%新增合約%,%建約%,%簽約%}')` ⇒ 13；tenant 同法 ⇒ 20 |
| F8 | 缺口地圖 v2.1：55 格＝已覆蓋 22／未覆蓋 27／刻意不補 5／一般建議 1；未覆蓋成因（依 cause_state 表）V 可見性 **12**（C08/C12/C15/C21/C25/C29/C33/C34/C37/C44/C46/C54）、FALSE_HIT／UNSTABLE 7、S 表示法 2、N_CAND 2、CTA 1、待 G0 2、回答未含必含 1。**無權威來源（G0=none）8 格**：C22／C25／C29／C39／C46／C52／C53／C54；C13／C55 有來源待寫。第二批 18 筆涵蓋 17 格待業主放行；C43 地圖為舊值（5379 已含必含句） | `presales-grounding-gate/coverage-map/map-v2.md` cause_state 表與逐格表；`scripts/knowledge-batches/presales-gapmap-batch2-20260904.json` |
| F9 | 問法正本 `coverage-map/sources/koyu-v2-phrasings.json`＝業主提供 85 篇 1,546 句（**幫助中心受眾**），型別 直接 268／口語 266／情境 269／俗稱 255／邊界 170／操作 318；附「必先確認」6 條、缺口 28 條、規則 3 條；先前只用 12 篇合約文章抽 54 句凍結集 | 檔內 `_meta`、`articles.*.phrasings[].type` 計數 |
| F10 | 檢索上限（免費量測，**代替品**）：以自動切 59 段＋**段落內文向量**對 49 題 answerable／partial，recall@1／3／5＝51／71／86%，top-5 約 490 字；整節層 top-3 94%；reranker 無增益（82% vs 86%）。細目標題匹配未量。agent 現況 answerable 39 題答到 34%（舊鏈 71%），未答 155 回合＝Verifier 拒到預算 48%／模型自報查無 44%／誤標敏感 8%；依問法型 直接 51／俗稱 42／口語 19／情境 12% | `agentic-mcp-orchestration/eval/perf-agent-regression-20260905/round9-dsp033/README.md` 附錄；段落資產與可答性標籤**僅在 scratchpad／容器、⛔ 未入版控** |
| F11 | Verifier 現行尺（DSP-034 後）＝DSP-029a ratio 0.5 ∧ 絕對下限 4 ∧ 全極性；同批盲標抓到 62.3%／誤殺 13.9%；NLI 已撤出線上 | DECISIONS DSP-034；round9 README |
| F12 | LINE OA 三線（chatai 四份文件；代管業務、同殼 `/rag-api/v1/message`、**不帶 `vendor_id`**、`mode=b2b`、`target_user=property_manager`）：知識需求＝③ 損壞分類樹／信心門檻／損壞判定／照片限制／會話過期；⑤ 帳單狀態語義／滯納金規則／資料邊界（無入帳日）／跨戶邊界；④ 三級語氣模板／8 佔位符／數字禁止／滯納金條件。API 實值（帳單明細、逾期次數、租約到期、電表、estate_id、emergency_status）⛔ 不入大綱。21 個驗收案例：表單流程 7／契約欄位 4／API 實值 5／知識 5。**阻擋事項**（chatai A1–A3：發 key、業務身分不查租約 `contract_id` 留空、回應補 quick_replies／form_completed）屬各面向 spec；**待驗／矛盾**：emergency_status 值域相反（C1）、直達路徑不回 image_recognition（C2）、`status-overview` 以 `to_user_id` 過濾（repair-capture-spec §0 警語） | `/Users/lenny/jgb/line-bot-platform/docs/chatai-*.md`（scout 盤點四表） |
| F13 | 既有資產：`.claude/skills/retrieval-improvement-loop`、`tools/agent_eval.py`（**四組**樣本骨架 topics／scenarios／sensitive／traffic，traffic 現況缺席）、`tools/agent_attempts_report.py`、缺口地圖工具、`build_toc`（依 vendor／target_user 過濾，系統脈絡列現查 26，⛔ 非常數）、`OUTLINE_TOKEN_LIMIT_DEFAULTS`（prospect 10k／pm 8k／tenant 8k） | 各檔案；`SELECT count(*) FROM knowledge_base WHERE is_active AND question_summary LIKE '系統脈絡%'` ⇒ 26 |
| F14 | `kb.get(整數 id)` 走 `tools/kb.py::fetch_visible_row`，**與 `outline_approved_by` 無關**（未審列可被直取） | `services/agent/outline.py::build_prospect_outline` docstring |
| F15 | agentic-mcp tasks 與本 spec 重疊：4.6 S1 候選段落注入（Plan v3 READY 未派工）、4.7 S2 多向量講法錨點、4.8 fact_class 覆寫、5.5 `retrieval-improvement-loop` skill 升版 | `agentic-mcp-orchestration/tasks.md` |

## 業主定義與既有裁定（本 spec 直接沿用）

| # | 裁定 | 出處 |
|---|---|---|
| 1 | 三支柱；skill 先有（切售前、補文件缺口都靠它） | 業主 2026-09-06 |
| 2 | 售前大綱＝原 A–F 切法的擴充（競品更多、現有不足）；其他受眾不套此切法 | 業主 2026-09-06 |
| 3 | 缺口地圖未覆蓋格應能補足「現有不足」；完善 skill 要能按受眾知道缺口或有能力補齊 | 業主 2026-09-06 |
| 4 | 索引目錄不索引內容（圖書館法）；粗目／細目／講法；重切走同一 skill 流程以保一致 | 業主 2026-09-06 |
| 5 | 口語由檢索層吃、意圖由模型判、敏感由程式兜；先匹配主題、知識分叉且身分未知才反問；入口帶身分則不重問 | 業主 2026-09-06 |
| 6 | 驗證要有邏輯：命題／最小材料／推翻條件，免費先做；⛔ 不把前一任務的凍結材料再跑一輪當放行證據；材料以業主正本優先、不造題 | 業主 2026-09-06 |
| 7 | skill 架構要評估 hook／Workflow／schema | 業主 2026-09-06 |
| 8 | ⛔ 不做 LLM 查詢改寫（A/B 10/10 無差、+600–800 ms） | routing spec Req.8 |
| 9 | 離線 runner 須複刻 production 旗標；比較性結論須 ≥30 可判定案例（單一 bug 重現／已知 case 回歸不受此限） | routing spec Req.9.3／9.4 |
| 10 | ⛔ 用被驗系統自己的排序判「已覆蓋」 | 缺口地圖 P2.5 |
| 11 | ⛔ 54 句凍結題入索引或成為講法 | agentic-mcp tasks 4.7 |
| 12 | NLI 撤出線上；重提條件＝新尺在凍結 holdout 上誤殺 ≤10% ∧ 抓到 > 現行 | DSP-034 |
| 13 | 禁止特例修改；提示詞只寫定義不寫例子；封閉詞表以類維護並量誤殺 | 記憶 `feedback_no_special_case_fixes` |
| 14 | 匯入事實以 jgb2 現況為準；合約 ⛔ 不支援批次匯入 | DSP-008 |
| 15 | 售前不開 D6 抽取式，先補知識 | 業主 2026-09-04 |
| 16 | 有 KB 寫入權＝有 system prompt 寫入權，接線視為安全決策 | DSP-012／R11.6 |

## 待業主裁決（只列真的需要業主的三項；其餘為設計決策或 skill 產出，見下節）

| # | 問題 | 何時裁 | 預設 |
|---|---|---|---|
| D1 **DB 寫入授權** | 正本第一次入庫時的兩筆寫入：(a) 第二批 18 筆草稿（`scripts/knowledge-batches/presales-gapmap-batch2-20260904.json`）**改為 skill 首跑的輸入**，隨正本一起審、一起入庫（不再單獨「放行」）；(b) `outline_approved_by` 由「owner-20260905 整批標記」改為由正本入庫寫入（已審列才標 owner，其餘改「pool-marked-20260905」） | 執行時（我給 SQL 與預期輸出，業主跑） | 依正本流程入庫 |
| D2 **契約改產品行為** | 一回合「部分回答（fact 句照驗）＋帶理由轉人（handoff 句免引用）」並存 | 步 2／3 探針證明需要時才裁 | 允許 |
| D3 **個資政策** | 真流量問句能否成為講法、去識別到什麼程度、保留期 | design 前 | 不留原句、去識別（人名／地址／合約號／電話）、保留 90 天 |

## 設計決策與 skill 產出（依業主已表達的方向，由主 session 定、業主審產出）

| 項 | 處置 |
|---|---|
| 售前正本怎麼建 | skill 第一次跑：以 F2 的 21 列 prospect 為輸入（8 列 `IS NULL` 業者列不屬售前，排除），依 A–G 切草稿；「現有不足」每格一句說法與競品段（只用既有來源）一併產出 → **業主審草稿**，不先裁方法 |
| agentic-mcp 收窄、DSP-035 撤回、4.6 撤／4.7 4.8 5.5 移交 | 依業主「開新 spec、平台層留著」照做，以一條 DSP 收尾 |
| 資料模型：格＝(受眾, 主題)、細目帶受眾維度、同受眾內互斥、跨受眾同主題＝各自細目＋「另見」 | design 決定並寫理由 |
| 匹配鍵：預設細目標題＋講法向量；內文向量作第三對照臂由 R6 步 1 量測 | design／步 1 |
| 對話邏輯照 kb 3645 搬為定義（含 fact_class 七值、句形不是判準、五欄位、基本資訊門檻、已推薦後三種回應），「事實題不問身分」改「知識分叉且未知才問」 | 依業主已述方向，design 落 |
| 受眾次序：售前先、LINE 知識區塊次 | 依業主已述 |
| LINE 可見性：本 spec 只定義可見細目集合＋契約測試；面向／API／契約欄位歸各 spec | 預設 |

## 名詞定義

- **skill（完善大綱流程）**：建立與重切大綱正本的單一流程，每步有 schema 輸出與閘門；⛔ 不是一份叮嚀文。
- **大綱正本**：某受眾可引用知識的人審文件（版控 Markdown），含粗目、細目、講法、內容項目、來源、審核者；程式由正本組裝成上下文文件（有 sha、token 預算）。⛔ 程式重排的 kb dump 不是正本。
- **粗目**：正本一級章節（區塊）；**細目**：粗目下一個可獨立回答的主題，有標題、講法、內容、受眾維度（設計決策：細目帶受眾維度）、穩定 id、內容 sha；檢索與覆蓋的基本單位。內容裡的句是引用單位（DSP-029a unit）。
- **講法**：掛在細目上的口語別名向量，只進打分面、不進 answer；有出處（question_summary／幫助中心／正本／真流量）、狀態（proposed／approved／retired）、命中數。
- **現有不足**：目前沒有的功能／沒有的資料／刻意不答的五類，含對外一句說法與出口；來源＝缺口地圖 N／待 G0／刻意不補格。
- **受測物定義清單**：開跑前一頁：知識正本、對話邏輯正本、覆蓋來源與閉環、材料能證什麼不能證什麼、事實 vs 待裁。
- **命題／推翻條件**：每個驗證步宣稱的假設與「看到什麼結果即判不成立」。

## 範圍

### 範圍內
- 完善大綱 skill 的架構與流程（R1）；各受眾正本的定義、重建、審核語義、組裝規則、重切（R2）；覆蓋閉環（R3）；對話邏輯與身分（R4）；口語多意圖架構的候選與證據導向選擇（R5）；驗證邏輯與材料（R6）；LINE OA 知識區塊（R7）；對平台層的需求票（R8）。

### 範圍外
- MCP 工具邊界、Runtime、Verifier 判定邏輯、trace／計量**本體**（agentic-mcp；本 spec 只開需求票）。
- LINE OA 面向流程、API 欄位、契約欄位（chatai A／B／F 項）→ conversational-routing-execution／各 facets spec。
- jgb2 API 開發；線上部署；業者／租客 agent 實作（M4／M5）；更換 embedding 模型。

## 需求

### Requirement 1：完善大綱 skill（先有；流程一致性由機制保證）
**使用者故事**：作為維護者，我第一次切售前、日後加內容重切、補文件缺口，都走同一條流程；每步產出可機器校驗、每個紀律有閘門，不因誰在跑而變形。
- R1.1 skill SHALL 以同一流程處理首次建立與日後重切：輸入（新增／變更內容、缺口地圖、既有正本）→ 分析並提議粗目／細目結構變更（拆、併、移、新增）→ 講法與缺口格重新掛到細目 → 獨立判者標可答性 → 重量覆蓋 → 產出結構差異與影響清單 → 業主核可後入庫。
- R1.2 每步 SHALL 有結構化輸出 schema（結構差異含 id 對應表；缺口格去向與補法類型；可答性標籤；講法提案含出處與狀態；覆蓋重量結果；成本），⛔ 不得以散文交付需人工再解讀的結果。
- R1.3 細目 id SHALL 在主題不變時保持穩定；拆併 SHALL 留下前後對應表；未附對應表的重切 ⛔ 不得入庫。
- R1.4 流程紀律 SHALL 由閘門強制：未產出「受測物定義清單」不得開跑；材料 sha 未凍結不得跑回歸；凍結測試題進入講法或索引即擋；重切未附 id 對應表不得入庫（比照 canon-audit Stop 閘門先例）。
- R1.5 設計階段 SHALL 以證據評估 skill 執行形態 ∈ {單一 SKILL.md 指引, Workflow 多代理管線（固定順序、schema、獨立判者 fan-out）, 混合}，評估面向：可重跑、每步可稽核、判者隔離（判者不得見系統判定）、成本與時間、失敗可從哪一步續跑；⛔ 不預設。
- R1.6 skill 產出 SHALL 可回放：輸入 sha（正本、材料、缺口地圖）＋步驟版本 ⇒ 同輸出；LLM 參與的步驟（分析、提議、判者）SHALL 標為非決定性並保留原始輸出供覆核。
- R1.7 skill SHALL 記錄每次執行成本（模型 token／費用、代理數、時間）並列入報告；整案 SHALL 有預算上限與「超支即停」（值由 design 定、業主核）。
- R1.8 相似細目檢查（R2.5）的工具 SHALL 只產待審清單，⛔ 不得自動合併（DSP-026 教訓：工具建議 7 列、人審後只 2 列成立）；合併與講法掛載 SHALL 可回滾。
- R1.9 skill SHALL 產出**取代**既有 kb 列與知識草稿的細目：舊形狀（一筆＝`question_summary`＋`answer`，含第二批 18 筆草稿）只在首跑時被讀取，產出後 SHALL 標記「由細目 <id> 取代」並退役（不再作索引或內容來源）；`question_summary` 關鍵字併入該細目講法、answer 文字成為細目內容或併入既有細目；此後內容以正本細目為準，kb 列由正本匯入衍生。取代對應表 SHALL 隨產出交付。
- R1.10 既有 `retrieval-improvement-loop` skill 與 `agent_eval` SHALL 整合為本流程的量測步（以細目為單位重跑，輸入正本 sha、輸出每粗目／細目的可答率與無據率）；agentic-mcp 5.5 移交本 spec。

### Requirement 2：大綱正本與區塊定義
**使用者故事**：作為知識維護者，我要知道某受眾的大綱有哪些粗目、細目，每細目含什麼、來源是誰審的，而不是看程式碼怎麼分類。
- R2.1 THE SYSTEM SHALL 為每個受眾維護一份人審大綱正本（版控），列出粗目、細目、每細目的標題／講法／內容項目／來源（kb id／幫助中心 slug／業主宣告）／審核者與日期。審核者角色與流程依 R2.9。
- R2.2 售前正本 SHALL 採 A 產品基本盤／B 適配判斷／C 六大模組／D 方案與試用／E 競品事實與差異／F 導流 CTA／G 現有不足；其他受眾的粗目 SHALL 另以正本定義，⛔ 不得沿用售前切法。（正本草稿由 skill 產出、業主審）
- R2.3 正本 SHALL 有粗目／細目兩層；細目 SHALL 有標題、講法（多個、各有出處與狀態）、內容（可引用句）、受眾維度（設計決策：細目帶受眾維度）。細目 SHALL 是檢索與覆蓋的基本單位。
- R2.4 缺口地圖的格 SHALL 與細目對應：格＝(受眾, 主題)、細目帶受眾維度 ⇒ 一格對一細目（設計決策，design 記理由）。
- R2.5 同一受眾內細目 SHALL 互斥：一個可獨立回答的主題只有一個細目；相似或重疊者 SHALL 合併或以「另見」交叉引用；正本入庫時 SHALL 檢查細目標題（含講法）向量兩兩相似度，過近者列待審（處置依 R1.8）。跨受眾同主題不同層級（能力／操作／權益）⛔ 不視為重複。
- R2.6 THE SYSTEM SHALL 由正本以程式組裝上下文文件（無 LLM、版本戳、sha256、token 預算檢查——沿用 `OUTLINE_TOKEN_LIMIT_DEFAULTS` 或於 design 明寫新值），⛔ 不得由 kb 列自動分類重排充當正本；現有 `outline:boundary`／`deliberate-gaps`／`cta` 三段 SHALL 併入正本的 G 與 F 粗目，⛔ 不並存兩套。
- R2.7 THE SYSTEM SHALL 以不同標記值區分「池標記」與「內容已審」（待裁 D1，執行時），組裝與 `kb.get(整數 id)` 直取路徑（F14）SHALL 只放行「內容已審」的細目來源列。
- R2.8 THE SYSTEM SHALL 對每個細目給穩定 id 與內容 sha；細目內容變更 SHALL 使依賴它的講法與測試進入待審，⛔ 不得靜默沿用。
- R2.9 正本寫入權 SHALL 視為 system prompt 寫入權（裁定 16）：變更 SHALL 走版控＋code review＋可 revert；審核者身分與時間 SHALL 入正本與稽核；⛔ 不得由 DB 直接 UPDATE 繞過正本。
- R2.10 正本 SHALL 明列「現有不足」（G 粗目）：每格一句對外說法與出口（專人／定價頁／demo／留資），可被引用，使模型能有據地說「目前沒有」。（說法由 skill 草擬、業主審）

### Requirement 3：覆蓋閉環（缺口地圖 → 大綱）
**使用者故事**：作為業主，我要每個未覆蓋格都有去向，且缺口按受眾判——入口帶了身分，缺口仍是該身分大綱的缺口。
- R3.1 THE SYSTEM SHALL 為每格記錄去向 ∈ {已進細目 id, 現有不足, 刻意不補, 待業主裁}，⛔ 不得有無去向的未覆蓋格。
- R3.2 覆蓋 SHALL 以受眾×主題為單位維護，⛔ 不得以任一受眾的覆蓋代表全體。
- R3.3 WHEN 一批知識放行並進正本，THE SYSTEM SHALL 重組上下文文件並重量缺口地圖，報告格狀態變化。
- R3.4 覆蓋判定 SHALL 獨立於被驗系統：正解細目由人或獨立判者標（裁定 10）；報告 SHALL 附判者一致率。
- R3.5 THE SYSTEM SHALL 把「回答未含必含」（內容修正）與「有知識但撈不到」（檢索／講法）分開報。
- R3.6 WHEN 某主題在受眾 X 缺、在受眾 Y 有，skill SHALL 列為「跨受眾缺口」並提出補法：以 Y 的知識為底改寫為 X 的層級（能力／操作／權益）成草稿進待審，⛔ 不得直接把 Y 的列開放給 X。
- R3.7 skill SHALL 對每格輸出補法類型 ∈ {補知識, 補講法, 列現有不足, 跨受眾改寫, 合併相似細目, 交裁決} 並附最小驗證（哪幾句問法、預期細目）；補完 SHALL 重量該格。

### Requirement 4：對話邏輯與身分
**使用者故事**：作為潛在客戶或業者，我問同一件事時，系統要知道我是誰、只在知識真的依身分分叉而它又不知道時才問我。
- R4.1 THE SYSTEM SHALL 在回合開始時由程式把入口身分（audience；子身分若入口可得）預填進 `session.slots` 並以資料段呈現給模型；模型 ⛔ 不得自選身分。前置：`SlotKey` 擴充 `identity`／`team`／`pain`／`interested`（scale＝既有 `unit_count`）且預填時機不依賴 `COLLECTING` 會話列已存在（F5）——需求票見 R8.2。
- R4.2 WHEN 入口已帶身分，THE SYSTEM SHALL NOT 對該身分反問；契約測試：業者與 LINE 通道回合不得出現身分反問句型。
- R4.3 WHEN 候選細目依身分子類分叉且對應槽位未知，THE SYSTEM SHALL 允許先給共通部分再問一題確認分支；⛔ 不得硬選一支作答。
- R4.4 售前對話邏輯 SHALL 以定義搬入 agent（依業主已述方向）：A 事實題直答／B 推薦題補問；補問欄位封閉集合、一次一題、已知不重問、基本資訊門檻；已推薦後三種回應；中途岔題；fact_class 七值與「句形不是判準」與 agent 既有敏感判定合併為一份。
- R4.5 CTA（試用／demo／留資／定價頁）SHALL 由程式依 `kind=recommend` 或使用者明確要行動時附加，⛔ 不由模型自寫連結；一般追問不附；CTA 文字來源 SHALL 為設定（沿用 `PRESALES_CTA_RULES` 的內容，不再由 `outline.py` 自寫）。
- R4.6 轉人訊息與通道 SHALL 由設定供給（`conversational_config` DB 覆寫 > env > 程式常數）；agent 路徑現為硬掛常數（F5），SHALL 改接。
- R4.7 persona SHALL 依受眾分支（潛在客戶／使用系統的業者／租客），以定義描述、不寫例子。

### Requirement 5：口語多意圖下的架構（以證據選）
**使用者故事**：作為使用者，我用自己的講法、一句話夾兩件事時，系統要找到對的細目、判對我要什麼、答有據的部分並把其餘轉給人。
- R5.1 THE SYSTEM SHALL 把「講法→細目」交給檢索層：候選由程式選（固定 K、固定查詢組法、決定性），模型只能引用被給的細目內容；引用單位＝細目內容的句（DSP-029a unit，Verifier 不變）。
- R5.2 匹配鍵 SHALL 以**細目標題向量＋講法向量（取最大）**為預設；「內文向量」SHALL 作為對照臂列入 R6 步 1 量測（設計決策），⛔ 不得在無量測下先驗排除或採用。⚠️ F10 的 86% 為內文匹配的代替品數字。
- R5.3 可見性 SHALL 沿用 `mode`／`target_user[]`／業態／vendor 謂詞，在排序之前切出該身分的可見細目子集（與 `build_visibility_predicate` 同一套，⛔ 不另造）。
- R5.4 細目 SHALL 帶審核狀態，只有「內容已審」者進上下文與索引（部分審過的正本可先部署已審粗目）；未審細目所屬粗目仍列於目錄，模型能說「此部分目前無資料」而 ⛔ 不得撈到未審內容（含 `kb.get` 直取，R2.7）。
- R5.5 講法 SHALL 有出處、狀態、命中數；⛔ 凍結測試題不得成為講法；⛔ 不把多種講法接成一條字串算一個向量；每細目講法數上限與去重由 design 定；真流量來源 SHALL 先去識別（待裁 D3）。
- R5.6 THE SYSTEM SHALL 能偵測講法誤掛（勝出講法所屬細目 ≠ 判者正解）並支援退役與回滾；零命中講法 SHALL 依規則退役（改狀態不刪）。
- R5.7 意圖（要能力／要路徑／要價格／要推薦／需先確認）SHALL 由模型在候選內判定；敏感五類 SHALL 以程式規則為準、模型判定只作建議。
- R5.8 IF 業主裁定 D2 允許，THEN 契約 SHALL 允許一回合「部分回答（fact 句照驗）＋帶理由轉人（handoff 句免引用）」並存（平台層承接，R8.1）。
- R5.9 WHEN 候選皆不相關，THE SYSTEM SHALL 提供粗目目錄與整塊讀取工具作第二次機會，並在 trace 把「查無」與「有但沒認出」分開可辨（R8.3）。
- R5.10 THE SYSTEM SHALL NOT 以 LLM 改寫查詞；多輪查詢濃縮 SHALL 為程式規則（裁定 8）。
- R5.11 reranker 是否納入 SHALL 於候選池規模確定後以離線量測決定（時點＝R6 步 1 完成後；門檻＝top-5 召回增益 ≥5 點且 p95 不退步），⛔ 不預設。

### Requirement 6：驗證邏輯（小量先於放量）
**使用者故事**：作為業主，我要每一次測試都回答一個明確的問題，且能提前告訴我這條路不通。
- R6.1 每個變更 SHALL 先有「受測物定義清單」與「假設表」（命題／最小材料／尺／推翻條件／費用），業主核可後才開跑（R1.4 閘門）。
- R6.2 驗證 SHALL 由免費到付費排序：離線召回／留一驗證（embedding）→ 小探針（真路徑、多條件對照）→ 放量回歸；任一步被推翻 SHALL 停下回主 session，⛔ 不得邊跑邊調參數。
- R6.3 每個探針 SHALL 含區分機制與副作用的對照組（gold 不在候選的題應維持轉人；已能答的題不得變差；敏感照轉人；邊界不硬答）。
- R6.4 材料 SHALL 以業主正本為優先（問法正本、缺口地圖代表問句、劇本），選題規則與 sha 跑前凍結；每份材料 SHALL 標明「能證什麼／證不了什麼」；**比較性結論 SHALL ≥30 可判定案例**（裁定 9），已知 case 回歸（如 round9 的 13 題）只作對照組、⛔ 不作放行證據。
- R6.5 盲標 SHALL 由不知系統判定的獨立判者 ≥2（人或代理）進行；二分一致率 <90% 時 SHALL 加第三判者或回修判準；比較兩把尺或兩個 arm SHALL 同批同判者。
- R6.6 放量門檻 SHALL 在探針結果後、放量前凍結並由業主核可；報告 SHALL 標明每個 arm 哪個是 production 組態（裁定 9）。
- R6.7 幫助中心受眾的問法只證檢索層對口語的承載力，⛔ 不得用來下售前問法分佈或講法建表的結論；售前問法分佈以真流量（樣本 C）為準。

### Requirement 7：LINE OA 知識區塊（僅知識與口語材料）
**使用者故事**：作為代管業務，在 LINE 裡拍照報修、追問帳單、要催繳草稿時，系統的知識要幫我理解邊界與禁止項，數字一律來自 JGB。
- R7.1 LINE OA 正本 SHALL 只含知識層（分類樹、流程規則、狀態語義、資料邊界、語氣分級、禁止項）；API 實值 SHALL 標為「來自 JGB API」且 ⛔ 不寫進正本。
- R7.2 THE SYSTEM SHALL 維護「什麼時候說不」清單為可引用細目（無入帳日不推算、滯納金看合約不自乘、修繕進度無面向不答、跨戶追問即退出）。
- R7.3 文件中的矛盾與待驗（emergency_status 值域、image_recognition 回傳、`status-overview` 過濾）SHALL 在正本內列為「待裁決／待驗」，⛔ 不得寫成事實。
- R7.4 LINE 受眾的 `(mode, target_user, role_id, vendor_id 缺值)` 對應的可見細目集合 SHALL 明文定義並有契約測試（現況入口對缺 vendor_id 填 0、b2b 分支套 `system_provider` 嚴格過濾，F6／F12）。
- R7.5 21 案例中屬知識類（5）SHALL 成為本 spec 材料；表單流程／契約欄位／API 實值類交各自 spec。
- R7.6 文件中的實際使用者輸入句 SHALL 收錄為 LINE 受眾口語材料（照抄、標情境與多輪）。

### Requirement 8：對平台層（agentic-mcp）的需求票與紀律
**使用者故事**：作為兩個 spec 的維護者，我要平台層知道本 spec 需要它改什麼、為什麼，且不在本 spec 偷改平台。
- R8.1 需求票 A：輸出契約允許「部分回答＋帶理由轉人」並存（依 D2）。
- R8.2 需求票 B：`SlotKey` 擴充（identity／team／pain／interested）與槽位預填不依賴 `COLLECTING` 會話列；persona_provider 依受眾分支。
- R8.3 需求票 C：trace／decision_snapshot 記 `candidate_ids`（細目 id）、選中細目 id、「查無」vs「有但沒認出」、講法勝出 id（供命中數），⛔ 無原文（不變量 30）。
- R8.4 需求票 D：`kb.get(整數 id)` 受「內容已審」旗標約束（R2.7）；outline 介面改吃正本組裝結果。
- R8.5 需求票 E：`nli_model/` 保留為離線抽審工具（DSP-034），可作盲標輔助，⛔ 不接線上。
- R8.6 紀律：⛔ 不 push；⛔ 不動線上；DB 寫入需業主授權；禁止特例修改；提示詞只寫定義；每次收案 SHALL 列取捨與已知債（材料偏差、判者變異、環境延遲不可比）。

## 驗收邏輯總表（跑前凍結的骨架；數字待 D 裁與上限量測後填）

| 步 | 命題 | 材料 | 尺 | 推翻條件 | 費用 | 對應需求 |
|---|---|---|---|---|---|---|
| 0 | 正本定義完整：每格有去向、每細目有來源與講法 | 正本＋缺口地圖 | 無去向格＝0；無來源細目＝0；受測物定義清單已核 | 任一非 0 | $0 | R1.4、R2、R3.1 |
| 1 | 口語→細目的檢索上限（三臂：標題／標題＋講法／標題＋講法＋內文） | 對得到細目的正本口語句，留一輪替（≥30 題／型） | recall@5 依粗目×問法型 | 口語／情境臂間差 <10 點 ⇒ 該臂不值得；結論限檢索層（R6.7） | $0 | R5.2、R5.5、R5.11 |
| 2 | 候選細目＋身分槽位讓模型從「查無」轉為回答且不猜 | 新選 ≥30 題（跑前凍結）：可答卻沒答／gold 不在候選對照／已能答／敏感／邊界／多輪／跨粗目；round9 13 題只作對照 | 翻轉率；對照組維持轉人；引用細目＝gold；無據率 | 翻轉 <50%；對照組被「答到」≥2；已能答變差 | <$0.5 | R5.1–5.4、R4.1–4.3 |
| 3 | 對話邏輯搬遷後流程正確 | 六套劇本＋LINE 口語材料 | A/B 判對率、補問一次一題、身分不重問、CTA 只在收斂、零捏造 | 任一契約測試紅 | ~$0.3 | R4 |
| 4 | 放量回歸 | 正本材料（規模待裁） | 依受眾×問法型的答到率／無據率／不硬答／敏感 0 漏 | 門檻由步 1–3 結果定、跑前凍結 | 待裁 | R6.6 |
