# 產品功能地圖:先找功能,再看它的規格 / 產線 / 判準

一級標題的骨幹是**已經蓋出來的東西**(產品功能)。

    - 面向 | `路徑` | 一句話

面向六種:`路由` `規格` `產線` `判準` `決策` `實測`
⛔ 不寫狀態(做了沒、剩幾題)——那是 DECISIONS 的事
⛔ 不寫行號(會漂)

⚠️ **本表刻意不完整。** 起始版本只涵蓋 `.kiro/specs/` 底下的 14 個功能——
那是本 repo 唯一經漂移檢測確認可信的正本群(漂移 0 的 47 份文件幾乎全在這裡)。
repo 內另有約 250 份非資料文件尚未指派角色,⛔ 未列於此**不代表**它沒有權威地位,
只代表還沒有人裁決它該算什麼。
`.kiro/specs/` 已於 2026-08-24 以**目錄宣告**整棵收編(見文末),⛔ 那不等於逐份裁決過。

⚠️ 寫進去的每一條都會被 refcheck 驗。**不完整可以,寫錯不行。**
本表 34 條路徑於 2026-08-22 全數機械驗證存在。

---

## 帳號對話面向 {#account-facets}

- 規格 | `.kiro/specs/account-conversational-facets/requirements.md` | 帳號領域四子面向:註冊驗證、登入排障、綁定異動、團隊成員權限
- 規格 | `.kiro/specs/account-conversational-facets/design.md` | 實作架構與機制數字定案
- 產線 | `rag-orchestrator/services/jgb/accounts.py` | 登入排障的決定性 fact-builder
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 1:動作知識必有面向接管或明確豁免
- 決策 | `.kiro/specs/account-conversational-facets/design.md` | 母分類劃分、API 掛點、b2c 初版範圍
- 規格 | `docs/api/account-api-contract.md` | 帳號 G/J 對外契約(交付 jgb2);消費端存在性驅動,不需同步上版

## 帳務對話面向 {#billing-facets}

- 規格 | `.kiro/specs/billing-conversational-facets/requirements.md` | 帳務五子面向:繳費金流、帳單異常、發票、滯納金、設定引導
- 規格 | `.kiro/specs/billing-conversational-facets/design.md` | 決定性計算與 formatter 分支透傳
- 產線 | `rag-orchestrator/services/jgb/bills.py` | 帳單 face builder 註冊表
- 產線 | `rag-orchestrator/services/jgb/invoices.py` | 發票邏輯
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 7:JGB 金額欄位一律走語義層,禁止重算
- 決策 | `.kiro/specs/billing-conversational-facets/design.md` | 分支劃分與金額禁重算原則

## Brain 知識庫落地 {#brain-kb-grounding}

- 規格 | `.kiro/specs/brain-kb-grounding/requirements.md` | 岔題即答要有知識背書,不靠印象回答
- 規格 | `.kiro/specs/brain-kb-grounding/design.md` | Callback 注入的工具圈與 async 邊界跨越
- 實測 | `.kiro/specs/brain-kb-grounding/tasks.md` | 岔題三態:進場、多輪、逸出
- 決策 | `.kiro/specs/brain-kb-grounding/design.md` | 工具圈內聚、async 重構、tools API 選型

## 合約對話面向 {#contract-facets}

- 規格 | `.kiro/specs/contract-conversational-facets/requirements.md` | 合約五子面向涵蓋完整生命週期
- 規格 | `.kiro/specs/contract-conversational-facets/design.md` | 資料驅動、決定性計算、face 參數貫穿
- 規格 | `.kiro/specs/contract-conversational-facets/g1-g4-api-contract.md` | 外部 API 契約定義
- 產線 | `rag-orchestrator/services/jgb/contracts.py` | 合約 face builder 註冊表
- 決策 | `.kiro/specs/contract-conversational-facets/design.md` | face 參數設計、formatter 分層、matcher 預先生成

## 對話式診斷 {#conversational-diagnosis}

- 規格 | `.kiro/specs/conversational-diagnosis/requirements.md` | API grounding 與分類路由進對話
- 規格 | `.kiro/specs/conversational-diagnosis/design.md` | select:api 分支、依分類查 config、三路出口
- 判準 | `.kiro/specs/conversational-diagnosis/gap-analysis.md` | 現行轉折點覆蓋分析
- 決策 | `.kiro/specs/conversational-diagnosis/design.md` | select 三路、config 依分類索引、API 參數透傳

## 對話式修繕 {#conversational-repair}

- 規格 | `.kiro/specs/conversational-repair/requirements.md` | 修繕交易面向、三輪完成、四業者同步
- 規格 | `.kiro/specs/conversational-repair/design.md` | confirm/execute 交易語義與決定性推斷
- 決策 | `.kiro/specs/conversational-repair/design.md` | 租約 mock、影像信心度、confirm 文案、execute 重用、計量埋點

## 領域化對話面向 {#domain-facets}

- 規格 | `.kiro/specs/domain-conversational-facets/requirements.md` | 領域化脈絡、混合 grounding、多筆候選辨識
- 規格 | `.kiro/specs/domain-conversational-facets/design.md` | 脈絡、合成、候選三邊界擴充
- 決策 | `.kiro/specs/domain-conversational-facets/design.md` | per-領域脈絡、face 衍生、scope 正規化
- 實測 | `docs/research/domain-conversational-facets-research.md` | 面向化架構定案:三層脈絡／候選辨識／中途切換(2026-07-06 對 jgb2 真碼盤查);⚠️ 見〈jgb2 盤查結論〉區塊的家族規約

## 物件對話面向 {#estate-facets}

- 規格 | `.kiro/specs/estate-conversational-facets/requirements.md` | 物件領域兩子面向:操作引導、現況診斷
- 規格 | `.kiro/specs/estate-conversational-facets/design.md` | 兩軸狀態機的決定性機制語義
- 規格 | `.kiro/specs/estate-conversational-facets/research.md` | 真碼盤查定案項
- 產線 | `rag-orchestrator/services/jgb/estates.py` | 物件 fact-builder 與狀態機解碼
- 決策 | `.kiro/specs/estate-conversational-facets/design.md` | API 直查、二級詳情、面向切換邊界

## 智慧設備對話面向 {#iot-facets}

- 規格 | `.kiro/specs/iot-conversational-facets/requirements.md` | 兩子面向:電表排障、設定引導
- 規格 | `.kiro/specs/iot-conversational-facets/design.md` | 離線優先機制語義與 DAE 同步語義
- 規格 | `.kiro/specs/iot-conversational-facets/research.md` | 台科電機制與 jgb2 真碼盤查
- 產線 | `rag-orchestrator/services/jgb/iot.py` | 電表 fact-builder 與離線優先判定
- 決策 | `.kiro/specs/iot-conversational-facets/design.md` | 離線優先機制、非決定性查詢處理、DAE 帳號失效整批停

## 額度管制 {#quota-management}

- 規格 | `.kiro/specs/quota-management/requirements.md` | 月訊息額度:設定、檢查、警示、攔截
- 規格 | `.kiro/specs/quota-management/design.md` | middleware 單點、快取化檢查、fail-open 哲學
- 產線 | `rag-orchestrator/services/usage_metering.py` | 額度檢查器
- 路由 | `rag-orchestrator/app.py` | 進出場 choke point 與攔截短路
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 6:額度一致性、幽靈攔截偵測、寬限模式燒錢雷達
- 決策 | `.kiro/specs/quota-management/design.md` | middleware 單點、快取生命週期、fail-open 原則

## 檢索決策層 {#retrieval-decision-layer}

- 規格 | `.kiro/specs/archive/retrieval-decision-layer/requirements.md` | ⛔ 已封存、非主線;其 DecisionConfig 仍在生產運行故勿刪
- 規格 | `.kiro/specs/archive/retrieval-decision-layer/design.md` | ⛔ 已封存、非主線:八個元件與決策集中化
- 規格 | `.kiro/specs/archive/retrieval-decision-layer/HALTED.md` | 停案理由與仍在生產運行的部分
- 產線 | `rag-orchestrator/services/decision_layer.py` | 決策中樞與門檻的唯一讀值點
- 判準 | `rag-orchestrator/tests/unit/decision/test_decision_layer_equivalence_req.py` | 大規模對拍的嚴格等價測試
- 判準 | `scripts/audit/checks/decision_threshold_ast.py` | 不變量 8 的 AST 檢查,含規避寫法自我測試
- 決策 | `.kiro/specs/archive/retrieval-decision-layer/decisions/DECISIONS.md` | D-01 起的決策彙整(已封存)
- 判準 | `docs/retrieval-parameters.md` | 參數台帳:每個可調參數的現值、控制什麼、有沒有實證;⛔ 沒有實證欄位的參數不要動
- 規格 | `docs/architecture/DATABASE_SCHEMA.md` | 39 表 schema;三個檢索過濾欄位的描述與實際 SQL 一致(2026-09-01 帳本判可依據)
- 決策 | `docs/retrieval-recall-audit-20260822.md` | 前案盤查與裁決:適用性把關改 precision-first、b2b `business_types` 嚴格過濾是刻意隔離**勿改**;⚠️ 文內已自行宣告第六、七節量化結果失效
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-doc-status-ledger.md` | b2b／檢索過濾／門檻主題的**文件可信度分流**:哪幾份可依據、哪幾份照做會出事
- 規格 | `docs/architecture/retriever-pipeline.md` | 檢索管線架構:分數合成與 vector/rerank 的適用條件(程式註解多處引用)

## ⛔ SOP（對話路徑零讀取）與受眾隔離 {#sop-audience-isolation}

⚠️ **本節所有文件描述的 SOP 檢索機制已於 2026-09-11 隨舊 REST 對話鏈整批刪除**
（`.claude/DECISIONS.md` DSP-046）：`services/agent/**` 現查無任何 SOP 引用，
**業者改 SOP 對機器人回答永遠零效果**——⛔ 不是快取、不是生效時序。
後台 CRUD（`routers/platform_sop.py` 15 條路由）仍可用。詳見
`docs/architecture/SYSTEM_ARCHITECTURE.md` §4。
⚠️ 本節 2026-07-05 的「已改判撤案」是**另一件事**（b2b 本就不走 SOP），
⛔ 不能替代上面這條。


- 規格 | `.kiro/specs/sop-audience-isolation/requirements.md` | SOP 受眾隔離與 target_user 維度
- 規格 | `.kiro/specs/sop-audience-isolation/design.md` | schema 加欄、資料回填、補位知識
- 規格 | `.kiro/specs/sop-audience-isolation/research.md` | 內容體系查證與受眾錯位根因
- 決策 | `.kiro/specs/sop-audience-isolation/design.md` | schema 同型別語義、審表閘門、補位知識路徑
- 規格 | `docs/features/sop/README.md` | SOP 系統文檔索引
- 規格 | `docs/guides/features/SOP_GUIDE.md` | SOP 系統完整指南(v2.0 整合版)
- 判準 | `docs/guides/reference/SOP_QUICK_REFERENCE.md` | 新增 SOP 的操作快速參考

## 觸發語彙債 {#trigger-vocabulary-debt}

- 規格 | `.kiro/specs/trigger-vocabulary-debt/requirements.md` | 觸發配置檢索斷鏈修復與死欄位移除
- 規格 | `.kiro/specs/trigger-vocabulary-debt/design.md` | 三層不改語義、仲裁分數埋點、欄位偵測降級
- 產線 | `rag-orchestrator/services/vendor_knowledge_retriever_v2.py` | 觸發三欄透傳
- 產線 | `rag-orchestrator/services/usage_metering.py` | 仲裁比較 hook 與欄位偵測降級
- 決策 | `.kiro/specs/trigger-vocabulary-debt/design.md` | 透傳不解讀、欄位偵測降級、機械防回歸

## 使用量計量 {#usage-metering}

- 規格 | `.kiro/specs/usage-metering/requirements.md` | 全維度使用事件、日粒度統計、計費原料
- 規格 | `.kiro/specs/usage-metering/design.md` | middleware + contextvar + 火忘寫入三層
- 規格 | `.kiro/specs/usage-metering/research.md` | LLM 單價研究
- 產線 | `rag-orchestrator/services/usage_metering.py` | 使用脈絡歸集器與 fire-and-forget 寫入
- 路由 | `rag-orchestrator/app.py` | middleware 進出場與串流/非串流 finalize 分支
- 路由 | `rag-orchestrator/services/llm_provider.py` | token 埋點
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 5:內部事件標誌與 vendor_id 缺失率雷達
- 決策 | `.kiro/specs/usage-metering/design.md` | contextvar 同生命週期、fail-open 掉線續行、統計走聚合

## ⛔ 舊 REST 對話鏈(已退役,2026-09-11) {#dialogue-logic}

⚠️ **本節所指的舊 REST 對話鏈生產程式碼已於 2026-09-11 全數砍除**
（31 個模組，完整清單見 commit `7c905408`／`10116570` 的 diff）。本節下方仍列出的規格／決策／
判準文件，其中關於 b2b 資源池隔離、precision-first 適用性把關、retrieval
量測紀律等**設計理由與裁決**對現行 agentic-MCP 線的檢索/知識治理仍可能有效
（該線同樣做 kb 檢索與 grounding），但「產線／路由」欄位所指的程式碼本體
已不存在，`conversational-routing-execution` 這條主線是否整體轉列封存，
本輪文件整理不代為裁決，交人判斷。現行唯一活線見下方 `#agentic-mcp` 一節。

- 架構 | `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` | **對話線現況總覽（2026-09-08 上線；目標見 `TARGET_ARCHITECTURE.md`）**：§0a 誰呼叫誰（MCP 門面、AgentRuntime、工具層、JGB API，一回合的 AI 呼叫）；`/mcp` `agent.turn` 的門面（13 步進場）→Runtime 四段管線（段一**六條**程式終止路徑／九段注入／模型迴圈＋Verifier／四道出口閘）→工具註冊→替身；寫入鏈、別戶邊界、照片硬邊界、組態、已知限制。改這條線先讀它，再讀現行交接 `HANDOFF-20261018.md` 與目標正本 `architecture-target-20261018.md`

⚠️ 🔴 **測現行對話邏輯請用 `/canon-audit agentic-mcp`，⛔ 不是本節。** 本節保留供翻舊設計理由；若真要讀本節來源，用 `/canon-audit dialogue-logic` 起盤查——下列每一份**整檔讀完**才算數,
Stop 閘門會擋到讀完為止。⛔ 這一份清單存在的理由:沒有必讀清單時,測試會反覆漏掉已裁決的前提。

- 規格 | `.kiro/specs/conversational-routing-execution/requirements.md` | 主線唯一 spec 的需求正本
- 規格 | `.kiro/specs/conversational-routing-execution/design.md` | 責任/提名/授權架構設計正本
- 決策 | `.kiro/specs/conversational-routing-execution/HANDOFF-20260901.md` | 現行交接:主線是什麼、哪些事實別再重查、已知錯誤文件與工具地雷
- 決策 | `.kiro/specs/conversational-routing-execution/PLAN-retrieval-coverage.md` | 現行計畫 v2,逐筆事實以此為準
- 判準 | `.kiro/specs/conversational-routing-execution/a03-retrieval-failure-taxonomy.md` | 檢索失敗分類:四種失敗類型的判定尺
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-batch-selection-rule.frozen.md` | b2b 批次選題規則(凍結)
- 實測 | `.kiro/specs/conversational-routing-execution/b2b-b2c-pool-audit.md` | b2b／b2c 資源池盤查
- 實測 | `.kiro/specs/conversational-routing-execution/b2b-ground-truth.md` | b2b 標註基準
- 規格 | `docs/jgb2-chat-integration.md` | 三種身分形狀決定資源池——⚠️ 挑測試身分前必讀
- 判準 | `docs/retrieval-parameters.md` | 量測紀律:不要離線重建 pipeline、比較性結論 30 題起跳
- 決策 | `docs/retrieval-recall-audit-20260822.md` | 前案裁決:precision-first、b2b 嚴格過濾勿改
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-doc-status-ledger.md` | b2b／檢索過濾／門檻主題的**文件可信度分流**:哪幾份可依據、哪幾份照做會出事
- 規格 | `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` | 舊 REST 對話鏈的架構母圖,2026-09-12 刪至只剩四節:§0 三層責任分層(概念)、§3 檢索過濾與加成、§11 系統角色、§12 參數速查;⛔ 其餘章節(意圖分類／信心度／SOP 編排／表單／仲裁)的程式已於 2026-09-11 刪除,章節一併移除。現況架構走 `SYSTEM_ARCHITECTURE.md` 與 `AGENTIC_MCP_ARCHITECTURE.md`
- 規格 | `docs/architecture/facet-architecture.md` | 面向化三層疊加的邏輯與資料佈局(取代 design.md 元件1/D2 的兩層版本)
- 實測 | `scripts/audit/reports/regrade291-triage.md` | **69.7% 基準的唯一出處**(548 題乾淨重跑;舊寬鬆基準 60.2%)
- 規格 | `docs/api/conversational-api.md` | 對話式回答的對外串接指南

## agentic-MCP（/mcp 對話線；LINE OA 為 demo 期場景之一）{#agentic-mcp}

⚠️ 與上面「⛔ 舊 REST 對話鏈(已退役)」(`#dialogue-logic`) 是**不同的兩條線**：`dialogue-logic` 是
`conversational-routing-execution` 舊有 HTTP chat 路由主線——⛔ **該線已於 2026-09-11 整條退役**（`POST /api/v1/message` 與 31 個模組刪除，commit `7c905408`）；本節是現行**唯一**活線。

- 規格 | `docs/architecture/SYSTEM_ARCHITECTURE.md` | **現況全景正本**（v4.0，2026-09-12）：核心是 `AgentRuntime`、`/mcp` 只是四個門面之一；六域 15 face；知識兩條路；六域隔離不對稱
- 正本 | `rag-orchestrator/canon/jgb/CATALOG.md` | **知識正本目錄（衍生物，⛔ 不手改）**：架層兩行（`## <架> <標題>`＋`scope:`），粗目若帶 slug 則多一行 `### <粗目 id> <粗目標題>`，每細目一行 id｜標題｜target_user｜approved 講法（DSP-129）；由 `export_catalog` 重產，`load_canon_or_die` 啟動時與九架逐位元比對。DSP-058（2026-09-15）圖書館形態：一目錄＋九架，受眾＝細目必填屬性；舊兩份受眾檔封存：DSP-067 換正本前 `docs/archive/2026-09/canon-pre-dsp067/`（2026-09-23 已移出工作樹，內容在 git `c06575a9`）（舊 210 條，S1／S2 的正對照組）、9.6 圖書館化前 `canon-pre-library/`、9.5 重切前 `canon-pre-recut/`；舊版封存 `docs/archive/2026-09/canon-pre-recut/`；格式規則與審核流程見 `canon/README.md`；2026-10-04 實查 **57 粗目／539 細目、已審 525**（只有已審細目的內容可被模型引用、未審細目只出標題（`canon_assembler.py` 的 `citable`）；現值以 `jgb.json` 與 `endpoint_progress.py` 為準，⛔ 照抄本行）
- 判準 | `docs/architecture/BOUNDARY.md` | **系統邊界唯一正本**：三個桶（本系統／呼叫端／外部相依）＋易混詞歸屬表＋一句話測試「把呼叫端整個換掉這句話還成立嗎」。⚠️ `quick_replies`／`line_official`／`confirm_qr_labels` 名字有外部血統但**是本系統自己的契約**，⛔ 不得當外部名詞清掉；由不變量 40 機械強制
- 產線 | `docs/guides/development/how-to-add-a-query-capability.md` | **怎麼加一個查詢能力**：先分「新 face／新域／跨列彙總」三類；加 face 的三個陷阱（face 只選 builder 不選資料源、builder 簽名是單列、參數列被 strict 測試凍死）；⛔ 跨列彙總在現行形狀下表達不出來
- 決策 | `docs/architecture/TARGET_ARCHITECTURE.md` | **架構唯一正本（目標，設計以它為準）**：本系統是對話服務，不是 MCP 系統；誰決定哪個環節的分工表、原則 P0～P8、目標架構圖與邊界、與現況的差距；每份計畫必須引用原則編號（DSP-091、DSP-127、DSP-130、DSP-131）。改對話程式與寫計畫前由閱讀閘門強制讀完，不變量 47 核對各現況文件都標了目標
- 決策 | `.kiro/specs/agentic-mcp-orchestration/architecture-target-20261018.md` | **工作線目標正本**：目標與 M0 基線、每片驗收方式、業界原文、差距細項（KD、RD）、分片路徑與上線四步；架構本身見 `TARGET_ARCHITECTURE.md`
- 進度 | `.kiro/specs/agentic-mcp-orchestration/HANDOFF-20261018.md` | **工作線交接正本**：各片狀態、待業主裁事項、安全規則、環境暫態；新視窗從這裡開工
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-division-guard-20261020.md` | DG 分工防偏離片計畫（業主 2026-10-20 核可）：兩道檢查的業界依據、差距、DG-1～DG-6、回復與停點
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-division-guard-20261020.md` | DG 片凍結驗收：業主原話、規則 DG-R1～R7、清單 V0～V9
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-arch-who-calls-who-20261030.md` | 架構文件「誰呼叫誰」凍結驗收：業主原話、規則 AR-1～AR-4、清單 C1～C6
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-b-write-replies-program-20261020.md` | B 片計畫（業主 2026-10-20 核可，DSP-099）：寫入情境回話由程式、帶狀態句判讀閘、候選清單分給模型／給人兩份；業界依據、差距、B1～B7、回復與停點
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-b-write-replies-program-20261020.md` | B 片凍結驗收：業主原話 1～9、規則 B-R0～B-R15、清單 V0～V16
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-a2a-write-candidates-20261020.md` | A-2a 片計畫（業主 2026-10-20 核可，DSP-103）：寫入時名稱對到多筆由程式列候選、`pick:` 按鈕與打字選定、程式專用選定通道；業界依據、差距、偏離、停點與審查處置
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-a2a-write-candidates-20261020.md` | A-2a 片凍結驗收：業主原話 1～5、規則 A2-R0～A2-R13、非目標 N1～N2、清單 V0～V17（含 V2b）
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-overall-acceptance-step3-20261021.md` | 第 3 步整體驗收 OV 計畫（業主 2026-10-21 核可）：`de7f4653` 與現在同題對照、獨立代理產的廣度題組、M0 題組照目標正本重測；業界依據、差距、P0～P8、停點；結果交裁後落 DSP-106～108
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-overall-step3-20261021.md` | OV 凍結規則與清單：業主原話、規則 OV-R1～R5、Q3＝(a) 判定式、Q4＝(a)、廣度表、清單 V0～V10
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-pick-right-record-20261021.md` | 「選對紀錄」片計畫 r5（業主 2026-10-21 核可，DSP-107）：同名物件／合約帶可分辨欄位的候選由 AI 回編號（Q1 甲′）、帳單先定物件再依合約取帳單、金額與計費期間比對、確認卡加欄位；業界依據、差距、偏離、業主裁示 Q1～Q4、資安與審查處置 §11～§14
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-name-lenient-f12-20261022.md` | F12 名稱寬鬆查找計畫（DSP-110）：查無時程式讀音前篩＋AI 回清單內編號＋程式驗證補齊、一律列候選；(甲) 查無／(乙) 缺名稱／(丙) 名稱先查三觸發點；業界依據、實打診斷、差距 G-0～G-6、資安處置 §4.8、待裁 §6、審查處置 §10
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-name-lenient-f12-r6-20261024.md` | F12 規則與清單 r6（2026-10-24 業主核可凍結）：選定後改口 FR-12～FR-16、復原第 4、5 輪追加、業主原話 13～29
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-post-pick-commands-20261024.md` | 選定後回合改指令式計畫（業主核可，2026-10-25 收案，DSP-112）：AI 回依序指令 pick／nth／name／clear、程式執行且最後一個生效；業界原文、差距、改動點、審查紀錄 §7、修復輪 1 §8（含終點指標與斷路器）
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-post-pick-commands-20261024.md` | 指令式規則與清單（核可凍結，sha256 記於 repo 外 `f12/cmd/ACCEPTANCE_FROZEN_cmd.txt`）：業主原話、規則 C-1～C-13、廣度表、清單 F0～F11、F8、F9
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-twins-manual-bill-20261025.md` | 雙胞胎與手開帳單合約計畫 r5（未核可，暫停至上線後，DSP-115）：目標與終點表、業界原文、差距、路徑、§7.1 每次執行、資安處置 §11、三輪審查處置 §12～§14
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-twins-manual-bill-20261025.md` | 雙胞胎與手開帳單合約規則與清單 r5（未核可、未凍結）：業主原話 1～6（含 2026-10-25 四題裁定）、規則 TM-0～TM-12、廣度表、清單 V0～V12
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-truncation-w2-20261017.md` | W2 截斷與串流計畫 r4（業主核可，2026-10-26 收案，DSP-116）：明示 JSON 句、串流讀到結束、只有真截斷才重寫、回合期限
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-truncation-w2-20261017.md` | W2 凍結規則與清單；收案報告在 repo 外 `w2/report-w2-close.md`
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-closing-handoff-e-20261026.md` | E 片計畫（2026-10-26 業主核可，2026-10-27 收案，宣稱收窄為標籤與出口，DSP-117）：道謝收尾與明確要真人由程式決定——每個使用者文字回合另發一次標籤呼叫（wants_human／resolved／none）、程式轉人／收尾樣板、追問欄位中的標籤確認、開關 `AGENT_CLOSING_HANDOFF`；業界原文、差距、終點表、§7 每次執行、§6 r4～r9 業主裁示、§10 審查處置
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-closing-handoff-e-20261026.md` | E 片規則與清單（業主核可、凍結，r4～r9 增補皆經核可，sha256 記於 `~/jgb-archive/arch-step3-20261018/e/ACCEPTANCE_FROZEN.txt`）：業主原話 O1～O6、規則 E-R1～E-R13、清單 E1～E14、非目標、廣度表
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-fill-answer-only-20261027.md` | 「填欄只填答覆」片計畫 r4（2026-10-27 業主核可，2026-10-28 收案，宣稱收窄為單欄追問回合，DSP-117／DSP-118）：寫入意圖呼叫回資料段與答覆段、程式只填答覆段並以資料段加閘、不覆寫已填欄、開關 `AGENT_FILL_DATA_TEXT`；業界原文、差距、終點表、§6 第 1～13 點業主裁示、§7 每次執行、§9 後補清單；收案報告在 repo 外 `fill/report-fill-close.md`
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-fill-answer-only-20261027.md` | 「填欄只填答覆」規則與清單 r4（業主核可、凍結，sha256 記於 `~/jgb-archive/arch-step3-20261018/fill/acceptance-frozen.sha256`）：業主原話、規則 FA-R1～FA-R12、清單 FA0～FA11、廣度表、非目標
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-fill-wide-20261028.md` | 「填欄擴及首句、卡後、多欄回合」片計畫（DSP-119，r2，業主 2026-10-28 核可）：第一句、確認卡後打字、多欄追問回合也只填資料段、逐值加閘；業界原文、差距 G1～G8、路徑、終點表、§7 每次執行、§8 待裁
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-fill-wide-20261028.md` | 「填欄擴及首句、卡後、多欄回合」規則與清單（r2，業主 2026-10-28 核可、凍結）：業主原話、規則 FW-R1～FW-R14、清單 FW0～FW13、廣度表、非目標
- 計畫 | `.kiro/specs/agentic-mcp-orchestration/plan-upload-documind-20261028.md` | UD 片計畫（業主 2026-10-28 核可）：附件改瀏覽器直傳 AIChatbot（上傳票＋`upload_ids`）、謄本／收據／修繕照片皆由 DocuMind 辨識；業界依據、差距、UD-0～UD-4、資安兩階段（測試環境前／上正式機前）、推翻卡、業主裁示 OQ1～OQ13
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-upload-documind-20261028.md` | UD 片凍結規則 R1～R5、清單 A1～A13、廣度表
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-docs-handoff-cleanup-20261027.md` | 本線文件整理與過時清理的規則 D-R1～D-R4 與清單 C1～C11（2026-10-27 業主核可、凍結；併 E 收案執行；D-R4 為程式註解清理）
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-name-lenient-f12-r5-20261022.md` | F12 規則與清單 r5（2026-10-22 業主核可凍結；F12 收案的終點量法依此，DSP-112）：業主原話 1～11、規則 FR-1～FR-11、廣度表、清單 F0～F9（宣稱依據 F3″）
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-name-lenient-f12-20261022.md` | F12 規則與清單 r4（2026-10-22 業主核可凍結，紀錄）：r4 量測依此判（F3′ 27/50 未達）
- 驗收 | `.kiro/specs/agentic-mcp-orchestration/acceptance-pick-right-record-20261021.md` | 選對紀錄規則與清單 r5（2026-10-21 業主核可、凍結）：業主原話 1～7、規則 PR-0～PR-11、非目標 N1～N4、廣度表、清單 V0～V12
- 判準 | `rag-orchestrator/tests/unit/agent/test_b_write_replies_program_req.py` | B 片單元驗收：KD-3／KD-4 接手、寫入情境程式回話、乙′、判讀閘（含失敗 fail-closed、nonce 資料段、原文不落紀錄）、讀到的值、候選清單不外漏提示
- 判準 | `rag-orchestrator/tests/unit/agent/test_dsp091_division_contract_req.py` | DSP-091 分工契約測試：程式列 R1～R6 必過契約、已知偏離現況探針（偏離消失即失敗，清單只減不增）、靜態檢查
- 判準 | `rag-orchestrator/tests/unit/agent/dsp091_known_deviations.py` | 已知偏離登記 `KNOWN_DEVIATIONS`（須與目標正本 §3.1 同一組 KD 與接手片）、`DIVISION_ROWS`
- 判準 | `scripts/audit/checks/division_guard.py` | 不變量 45：§3.1 與登記一致（靜態）＋近 7 天 `confirm_source:` 標記無 `model:unregistered`（線上；無程式樣本判「未判」）
- 判準 | `scripts/audit/checks/acceptance_breadth.py` | 不變量 46：驗收廣度表結構（全域「驗收廣度」第 1 條）——GOV-4 核可後首次加入或未追蹤的 `.kiro/specs/**/acceptance*.md` 須有七欄 `## 廣度` 表、使用者層不同輸入數 ≥5、「上位驗收方式：」行；`--self-test`；尚未接入 `check_invariants.sh`
- 產線 | `.kiro/specs/agentic-mcp-orchestration/deploy-and-online-test-guide-20261015.md` | 站內幫手正式機維運指南：現況、正式機 env、§3 部署 11 步（業主執行）、§4 線上測試（真 JGB）、§5 回退；gpt-oss 切換上線走這份（目標正本 §4.1 第 4 步）
- 紀錄 | `.kiro/specs/agentic-mcp-orchestration/audit-oss-replacement-20261018.md` | gpt-oss 替換盤查（2026-10-18）：§E 四步任務安排＝目標正本 §4.1 上線路徑的出處
- 規格 | `.kiro/specs/agentic-mcp-orchestration/jgb-spec-structured-card-draft-20261019.md` | **給 JGB 的需求稿（草稿、未寄出）**：面板改接 `agent.turn` 與確認卡已在 jgb2 preview（未進 master）、上線前 JGB 端事項（合入、正式環境設定）、preview 面板與回應欄位對照；上線後的 C 片結構化 `card` 提案
- 規格 | `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` | 總覽：`/mcp` `agent.turn` 門面→四段管線（Plan R R1 後：`turn_segments`／`turn_context`／模型迴圈／`exit_gates`）→工具註冊→替身；組態、已知限制、模型行為假設表
- 紀錄 | `.kiro/specs/agentic-mcp-orchestration/requirements.md` | 母 spec 需求（2026-09 M0～M3 時期，含 D2 延遲／答到率驗收線）；現行架構與分工以 `docs/architecture/TARGET_ARCHITECTURE.md` 為準，工作線目標與驗收以 `architecture-target-20261018.md` 為準
- 紀錄 | `.kiro/specs/agentic-mcp-orchestration/design.md`、`tasks.md`、`research.md`、`validation_gap.md` | 母 spec 設計、任務、研究、差距（2026-09 M0～M3 時期）；現行狀態看 HANDOFF
- 產線 | `rag-orchestrator/services/agent/runtime.py` | `AgentRuntime.run_turn`／`_run_turn_body`（四段管線接線）
- 產線 | `rag-orchestrator/services/agent/exit_gates.py` | 四道出口閘依序表 `EXIT_GATES`
- 產線 | `rag-orchestrator/services/agent/turn_context.py` | `TurnAccumulator`／`ReservedCallIds`／九段資料注入
- 產線 | `rag-orchestrator/services/agent/verifier.py` | `OutputVerifier`，`AGENT_VERIFIER_MODE` 三態（`enforce`／`grounding_observe`／`observe_only`）
- 產線 | `rag-orchestrator/services/agent/mcp_facade.py` | `/mcp` 門面：驗 key／Origin／身分 header、命名空間、每呼叫記錄
- 規格 | `docs/api/mcp-facade.md` | **`/mcp` 對外串接契約**：三道閘（401／403／400）、`X-JGB-Identity` 明文 JSON（⛔ 無 base64）、16 支工具與各自 `stage`、錯誤碼、額度
- 正本 | `rag-orchestrator/canon/jgb/A.md` | **會進模型脈絡的知識正本（九架之一，A 帳號與身分；B…I 同形）**：一架可容**多個粗目**（`## 標題 {#A-slug}`，Plan 9.10 S1 起；裸字母 `{#A}` 已於 S5（2026-09-24）停用、目錄路徑大聲拒絕）、細目帶必填 `target_user`／`business_types`，id `jgb/<架>/<slug>`；agent 啟動時 `load_canon_or_die` 讀九架、依靜態身分（`_STATIC_TOC_IDENTITY`）只驗兩尺預算（`check_turn_budget`），不預組任何身分的整份篩選結果；每回合 `build_canon_sections` 現組 K=5 節（未審／不可見 id raise）；⛔ 改它等於改模型看到的內容，配套 `canon/jgb.json`＋`CATALOG.md` 由 `load_canon_or_die` 啟動時逐位元比對；跨架講法重複 parser 與 hook 都擋
> 衍生物（**不列入盤查應讀**：業主 2026-10-18 選「拿掉，改用一行指令」，1.1 MB 每次需多代理分段讀；內容由上列正本 `canon/jgb/A.md`…`I.md` 產生；審核數改用 `python3 -c "import json;d=json.load(open('rag-orchestrator/canon/jgb.json'));f=[x for c in d['coarses'] for x in c['fines']];print(sum(1 for x in f if x.get('reviewed_by')),len(f))"`）`rag-orchestrator/canon/jgb.json`：`export_json(parse_canon_dir("canon/jgb"))` 的導出，⛔ 不手改；CI `test_canon_export_sync_req` 與啟動期 `load_canon_or_die` 逐位元比對。⚠️ 售前／業者身分只涵蓋 prospect／property_manager（`outline.CANON_VIEW_AUDIENCES`）——`tenant` 無篩選結果，`make_outline_resolver` 對它一律 `NO_MATCH`；跨受眾隔離只在 `canon_assembler.canon_visible` 一道（`build_canon_sections` 對不可見 id raise ⇒ 降級只注入目錄）
- 判定 | `docs/architecture/agent-path-retired-symbols.md` | agent 路徑上已退役的符號帳本（查「這個還在不在」先看這裡）
- 產線 | `rag-orchestrator/services/agent/limits.py` | DSP-045 額度封閉表（⛔ 不讀 env 覆寫）
- 產線 | `rag-orchestrator/services/agent/session_persistence.py` | `AgentSessionStore`：會話狀態層（`get_state`／`start`／`save`／`close`）。⚠️ 2026-09-11 自舊引擎抽出，SQL 逐字照搬，同一張 `form_sessions`、同一個 `form_id='conversational'`
- 產線 | `rag-orchestrator/services/form_contract.py` | 確認卡按鈕值與表單 id 常數（⚠️ 值寫進 DB／送給呼叫端，⛔ 不得改）
- 判準 | `rag-orchestrator/tests/unit/agent/test_pipeline_golden_req.py` | Plan R 回放等價 golden（`TurnTrace` 全欄位逐位比對）
- 判準 | `rag-orchestrator/tests/unit/agent/test_pipeline_order_req.py` | 四道出口閘順序表測試
- 判準 | `scripts/smoke/` | 真模型 smoke 對照計分尺（`mcp_smoke.py`／`b4_score.py`／`liff_score.py`）
- 決策 | `.claude/DECISIONS.md` | DSP-091 混合式分工、DSP-092 同 session 唯一可兌現確認卡、DSP-095 W2 處置方式（明示 JSON、截斷走現行重寫、卡住呼叫查根因）、DSP-116 W2 撤串流空白早停（期限切斷、接受 C3／T 殘餘）、DSP-117 E 片收窄收案與「填欄只填答覆」片列上線前必修、DSP-118「填欄只填答覆」片收窄收案（沒點名的英數道謝緊貼答覆列已知偏離）、DSP-119 另開「填欄擴及首句、卡後、多欄回合」片（與第 4 步同時進行）、DSP-099 B 片寫入回話由程式與判讀閘、DSP-100 B 片收窄收案、DSP-102 W-R3 前判真值、DSP-103～104 A-2a 片、DSP-106 A-2a 宣稱收窄、DSP-107 新增選對紀錄片與上線範圍 A＋期別＋A+＋B＋A-2a＋選對紀錄＋E＋W2 及第 3 步執行順序（取代 DSP-101 順序與範圍）、DSP-108 模擬客人回合上限只計打字句、DSP-085 寫入由程式掌握；DSP-037～045（pm 受眾開放、寫入工具正本、Verifier 兩類拒因、DSP-040 引用類絆線、W7 語音、W8 LIFF、outcome 七鍵、DSP-044 照片文字撤銷、DSP-045 額度封閉表）
- 實測 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/demo-ledger-line-oa-20260907.md` | demo 帳本：模型換測（luna／terra）、延遲量測、病灶審查

## 大綱三層重建（DSP-067；現行九架正本的來源）{#outline-drafting}

- 定義 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/definitions-outline-baseline-20260919.md` | 目標、分母 D1、三層 D2、身分 D3、來源 D6、審核 D7、產物定位 D8、順序 D10（DSP-067 後已改寫）
- 骨架 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/outline-skeleton-20260920.md` | 九架 → 57 粗目 → 頁；10 頁排除、11 處換架（業主「同意」）
- 總表 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/outline-summary-20260920.md` | 九架條數（57／515／1,327）＋ 81 條待裁 open_questions（⛔ 未選邊）
- 草稿 | `.claude/skills/outline-curation/runs/outline-20260920/` | drafts-A…I.json（每句 evidence 逐字、否定句 not_supported_greps；jgb2 `b2ee2ac382ce`）；人讀版 `inputs/outline-<架>-draft-20260920.md`
- 規約 | `.claude/skills/outline-curation/steps/00c-topic-first-drafting.md` | 起草與逐句對源規則（釘住 commit、死碼掃描、標籤取自 `t()`、實作字眼只進 evidence、衝突不選邊）
- 分母 | `.claude/skills/outline-curation/steps/00-feature-surface.md` | 步 0a 頁面樹 183 頁（`page_surface.py`）；0b 頁×身分只作粒度對照（有細目≠答對）
- 決策 | `.claude/DECISIONS.md` | DSP-065／065a（分母＝頁面樹、剔除無頁路由）、DSP-066（代理先審業主終審）、DSP-067（三層、57 粗目、210 條不當材料）
- 交接 | `.kiro/specs/knowledge-outline-and-intent-architecture/HANDOFF-20260923.md` | 本線交接正本：開頭＝終點指標現值與一句話現況；§12＝已審推進流程（9.15～9.22 各計畫、固定流程、踩過的坑、未審與待裁）
- 計畫 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.22-remaining-14-closeout-20261003.md` | 最近一份已審推進計畫；剩 14 條的 id 在 §0、處置與下一步在 §6「9.22 停止」（D1「修整條」規則在 plan-9.21 §1）
- 判準 | `scripts/audit/checks/outline_plan_discipline.py` | 不變量 43：寫入須附全數逐句核對證據、本線 commit 須附驗證證據、計畫須有 plan-meta；`--extract` 取出驗證代理證據（規則與已知限制在 docstring、HANDOFF §12-2）
- 守門 | `.githooks/commit-msg` | commit 當下執行已 commit 的不變量 43 檢查器（`git config core.hooksPath .githooks`）；檢查器、hook、`check_invariants.sh` 受 `.claude/settings.json` 權限規則保護
- 證據 | `.kiro/specs/knowledge-outline-and-intent-architecture/verification/` | 驗證代理證據 JSON（`Verified-by:` 指向此處；base＝父 commit）
- 計畫 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.10-three-level-canon-20260921.md` | 正本改三層的程式面 Plan（S1–S6，各片擁有檔案／驗收／停止條件；量測表）
- 對照 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/coarse-ids-20260921.md` | 粗目 id 凍結表 57 列（生成腳本的唯一來源，⛔ 不機械轉寫、⛔ 生成後不可改）

⚠️ **正本 `rag-orchestrator/canon/jgb/` 現況（2026-10-04 查 `jgb.json`）：57 粗目／539 細目、已審 525 條**——只有已審細目的內容可被模型引用、未審細目只出標題（`canon_assembler.py` 的 `citable`）；終點指標與未審清單以 HANDOFF 開頭與 §12-4 為準（數字每次重跑 `endpoint_progress.py`，⛔ 照抄本行）。舊 210 條曾封存於 `docs/archive/2026-09/canon-pre-dsp067/`，該目錄已移出工作樹，內容只在 git `c06575a9`。Plan 9.10 程式面各片狀態見 HANDOFF §3。

## jgb2 串接契約 {#jgb2-chat-integration}

- 規格 | `docs/jgb2-chat-integration.md` | 一支 API 三種身分形狀:`mode`＋`target_user`＋`role_id` 決定回答資源池與跨業者隔離;`vendor_id` jgb2 不送,由 AI 側經 role_id 解出
- 判準 | `rag-orchestrator/services/vendor_knowledge_retriever_v2.py` | b2b 資源池的實際過濾點(`business_types`／`target_user` 謂詞)

⚠️ 三種身分形狀是**對外契約**,⛔ 不屬於任何單一對話面向 —— 帶錯 `mode` 即受眾錯位,
而 `target_user` 漏帶時系統只依 mode 推導、`prospect` **不會**被自動推導。

## JGB 產品事實帳本 {#jgb-product-facts}

- 正本 | `docs/knowledge/jgb-product-facts.md` | 受眾中立的產品事實，逐條附 jgb2 程式引用（path:symbol＋查證日）；售前／業者正本各自從這裡改寫成自己的層級，⛔ 不直接開放另一受眾的細目
- 消費者 | `rag-orchestrator/canon/README.md` | 正本細目以 `sources: [docs:knowledge/jgb-product-facts.md#<anchor>]` 引用帳本
- 產生者 | `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/coverage-map-20260907.json` | 哪些格因缺事實而列不足／待裁，帳本補的就是這些格

⚠️ 帳本記的是「系統內有沒有這個機制」，⛔ 不記當前設定值（那走 API）、⛔ 不記價格（走 /pricing）。

## 專案層級索引 {#project-index}

- 規格 | `docs/deployment-runbook.md` | 統一部署 runbook:§0–§10 依序執行,§11 為部署後掛帳

⚠️ 本區塊放**跨功能、不屬於任何單一產品功能**的正本。⛔ 不是雜物區——
每一條同樣要能說出「它回答哪個命題」,只是那個命題橫跨多個功能。

## 專案層級規則(目錄宣告) {#steering}

- 規格 | `.kiro/steering/` | 專案層級規則與脈絡:product / tech / structure / testing / knowledge / dialogue / ai-usage / debugging-workflow

⚠️ 依 `CLAUDE.md`「Load entire `.kiro/steering/` as project memory」——這 9 份是全專案生效的正本,
⛔ 不屬於任何單一功能,所以不放在上面的功能區塊裡。

## Kiro 規格樹(目錄宣告) {#kiro-specs-tree}

- 規格 | `.kiro/specs/` | Kiro 規格樹:17 個功能各一資料夾,`requirements` / `design` 是該功能的正本

⚠️ 結尾斜線=**遞迴涵蓋**該目錄下全部 89 份。⛔ 這是一次目錄層級的收編,
**不等於**逐份都已裁決為現行——上面逐功能列出的 14 個,才是經漂移檢測確認可信的那批。
⚠️ 同資料夾內的 `tasks.md` 帶施工狀態、`research.md` / `gap-analysis.md` 是當時的調查快照;
引用它們之前一律重新查證,⛔ 不得直接當現況。

## 工具與流程設定(目錄宣告) {#tooling}

- 產線 | `.claude/skills/` | 本專案自建的流程 skill:檢索改善產線、留出集驗證、接受度對帳、設定治理審查
- 產線 | `.claude/MAP.md` | 本表自身
- 產線 | `.claude/DECISIONS.md` | 裁決帳本
- 產線 | `.kiro/settings/` | spec 產出的規則與模板(design-discovery／design-principles／templates)
- 實測 | `.kiro/issues/` | 待解的線上問題單:reranker 回零、SOP 候選間歇空白

⚠️ 這區是**怎麼幹活**的設定,⛔ 不是產品事實 —— 引用它們不能當成系統行為的證據。

## 產線輔助說明(目錄宣告) {#codebase-readmes}

- 產線 | `semantic_model/` | 語意模型的訓練、部署、路由規則與效能分析說明
- 產線 | `scripts/` | 腳本目錄的使用說明、盤點與稽核報告
- 產線 | `database/` | migration 體系與 seed 的使用說明
- 產線 | `data/` | 知識單元格式與業者知識範本說明
- 產線 | `knowledge-admin/` | 知識後台前端的說明與遷移紀錄
- 產線 | `rag-orchestrator/README.md` | 主服務的使用說明
- 產線 | `rag-orchestrator/services/jgb/README.md` | JGB 整合層的端點、認證與 `bit_status` 對照
- 產線 | `rag-orchestrator/artifacts/responsibility/README.md` | responsibility 產物說明

⚠️ 這區是**隨程式走的操作說明**,⛔ 不是產品功能正本 —— 它們回答「這個目錄怎麼用」,
不回答「系統對使用者做什麼」。⚠️ 其中 `rag-orchestrator/services/jgb/README.md` 壞引用密度高
(`/canon-triage` 列為「整份可能已退休」),⛔ 引用前一律對碼。

## repo 根目錄 {#repo-root}

- 產線 | `README.md` | 專案入口與環境起法
- 產線 | `CLAUDE.md` | 本專案的事實紀律與工作流規約
- 實測 | `CHANGELOG.md` | 變更歷史 ⚠️ 內含大量指向已刪檔的歷史區段,⛔ 那是紀錄不是腐爛

⚠️ 本區塊三段(工具設定／產線輔助／根目錄)於 2026-09-04 加入,一次收編 80 份,
覆蓋率 353→433 / 558。⛔ 目錄宣告**不等於**逐份裁決為現行 —— 同 `.kiro/specs/` 的先例。

## 操作指南 {#guides}

⚠️ 這 23 份於 2026-09-04 **逐份判讀**後列入(非目錄宣告),每份都確認過自稱描述現況。
⛔ 判為現行**不等於**內容已對碼 —— 見各條的註記。

### API 與規範

- 規格 | `docs/guides/api/api-path-conventions.md` | 對外 API 該用哪個路徑前綴、怎麼命名(自標「狀態: ✅ 生效中」)

### 部署與環境

- 產線 | `docs/guides/deployment/AUTH_DEPLOYMENT_GUIDE.md` | 管理員登入認證要怎麼部署上去
- 產線 | `docs/guides/deployment/AWS_S3_VIDEO_SETUP.md` | 知識庫影片上傳需要的 S3 儲存桶怎麼設
- 規格 | `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | 每個環境變數的意義與預設值(清冊)

### 開發

- 規格 | `docs/guides/development/FRONTEND_DEV_MODE.md` | 前端開發／生產雙模式各自怎麼跑、差在哪
- 產線 | `docs/guides/development/KNOWLEDGE_EXTRACTION_GUIDE.md` | 從 LINE 對話萃取知識到回測的工作流程
- 產線 | `docs/guides/development/MARKDOWN_TO_PDF_GUIDE.md` | Markdown 轉 PDF 的可用工具與作法

### 功能

- 規格 | `docs/guides/features/CACHE_SYSTEM_GUIDE.md` | 三層快取各層存什麼、何時失效
- 產線 | `docs/guides/features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md` | 知識批量匯入匯出與 UPSERT 語義
- 產線 | `docs/guides/features/LOOKUP_IMPORT_EXPORT_GUIDE.md` | Lookup 表批量匯入匯出與複合鍵
- 產線 | `docs/guides/features/PERMISSION_SYSTEM_QUICK_GUIDE.md` | RBAC 角色與權限怎麼設定
- 產線 | `docs/guides/features/SOP_EXCEL_IMPORT_GUIDE.md` | SOP Excel 匯入的金流欄位怎麼處理

### 入門與速查

- 路由 | `docs/guides/README.md` | 指南目錄的任務導航:要做某件事該讀哪一份
- 產線 | `docs/guides/getting-started/QUICKSTART.md` | Docker 起服務與驗證是否活著
- 產線 | `docs/guides/getting-started/PERMISSION_QUICK_START.md` | 權限系統的資料庫建置與實作步驟
- 規格 | `docs/guides/reference/LOOKUP_TABLE_QUICK_REFERENCE.md` | Lookup 表系統速查 ⚠️ 檔內狀態欄寫「📝 規劃中」(2026-02-04)**已過時**:`rag-orchestrator/routers/lookup.py` 實際存在
- 規格 | `docs/guides/reference/PRIORITY_QUICK_REFERENCE.md` | 知識優先級加成怎麼算、什麼時候適用

⚠️ **同批已退休、⛔ 不在此列**:`docs/guides/deployment/PGVECTOR_SETUP.md`(自標歷史快照)、
`MARKDOWN_GUIDE.md`(其 `markdown_generator` 子系統全 repo 零命中,已歸檔至 `docs/archive/2026-09/`)。

## API 文件 {#api-docs}

⚠️ 這 13 份於 2026-09-04 逐份判讀後列入。⛔ 判為現行**不等於**內容已對碼 —— 見各條警語。

### 交付 jgb2 的對外契約

- 規格 | `docs/api/billing-api-contract.md` | 帳務 G/J 對外契約(交付 jgb2);⚠️ 檔內「✓ 已驗證」是 2026-07 當時狀態,用前對 jgb2 現碼重驗
- 規格 | `docs/api/estate-api-contract.md` | 物件領域對外契約(交付 jgb2);⚠️ 同上,驗證狀態為 2026-07 快照
- 規格 | `docs/api/g1-g4-api-contract.md` | G1–G4 合約欄位擴充契約(四個時間戳／`to_user_login_email`／`is_newest`);⚠️ 逐 gate 的「✓ 已修復並驗證」是 2026-07-02 當時狀態
- 規格 | `docs/api/iot-api-contract.md` | IoT J/G 契約(台科電＝DAE);⚠️ 檔內「jgb2 已修復並部署(2026-07-04)」是當時狀態
- 規格 | `docs/api/repair-api-contract.md` | 修繕租約清單契約,含 E1 真 API 上線 gate 的分支落差提醒;⚠️ 驗證狀態為 2026-07-12 快照
- 規格 | `docs/api/jgb-contracts-api-spec.md` | 合約查詢 API 的完整規格提案(2026-04-20,早於上述分領域契約);⚠️ **疑似已被 `g1-g4-api-contract.md` 等欄位增量契約取代,但無任何一份明說取代關係——待裁**

⚠️ 這批是**混合體**:欄位與介面定義是雙方仍在遵守的約定(現行),而逐條「✓ 已驗證」是時點狀態。
⛔ 不得整檔當快照排除——那會把還在生效的欄位約定一起靜音。
⚠️ 同群的 `docs/api/account-api-contract.md` 已列於〈帳號對話面向〉,體例相同。

### jgb2 規格副本

- 規格 | `docs/api/jgb_external_api_spec.md` | jgb2 `external/v1` 端點規格副本(v1.1);⚠️ **只列 14 支,jgb2 實有 24 支**——缺 `recharge-accounts` 兩支／`repairs` 三支／`tenants/registration-status`／`meters` 兩支／`roles` members 兩支;完整清單見 `.kiro/specs/agentic-mcp-orchestration/jgb2-source-index.md` §3.4

### 本 repo 自己的 API

- 規格 | `docs/api/API_REFERENCE_PHASE1.md` | 聊天／快取管理／業者管理等核心 API 的端點與參數;⚠️ 檔名的「Phase 1」是功能集合命名,文件版本已到 3.1 且含 Phase 3 優化
- 規格 | `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` | 知識後台九模塊 API(39 支端點:知識／測試情境／回測／認證／管理員／角色／配置／API 金鑰);⚠️ 與 `KNOWLEDGE_ADMIN_API.md` 只重疊 2 支,⛔ 不是它的超集
- 規格 | `docs/api/KNOWLEDGE_ADMIN_API.md` | 知識管理的 6 支端點規格;⚠️ 其中 `DELETE`／`PUT /api/knowledge/{id}`、`GET /api/vendors`、`POST /api/login` 四支**不在** `API_REFERENCE_KNOWLEDGE_ADMIN.md` 內,⛔ 兩份不可互相取代
- 規格 | `docs/api/loops_api.md` | 知識完善迴圈的生命週期端點;⚠️ **文件記載的 10 支裡有 8 支已刪**(start／execute-iteration／validate／complete-batch／pause／resume／cancel／start-next-batch,隨執行機制退役);產線 `rag-orchestrator/routers/loops.py` 現存 5 支**皆為 GET 查詢**,⛔ 引用前先對碼
- 規格 | `docs/api/loop_knowledge_api.md` | 迴圈生成知識的審核端點(待審查詢／單筆與批量審核／重複偵測);產線在 `rag-orchestrator/routers/loop_knowledge.py`

### 目錄索引

- 路由 | `docs/api/README.md` | `docs/api/` 與 `docs/design/` 的 API 文件導航;⚠️ 2026-09-04 補上同目錄 14 份之前,它只導向 `../design/` 三份與 `../guides/api/` 一份,同目錄一份都沒列

## 功能文件 {#feature-docs}

⚠️ 這 12 份於 2026-09-04 逐份判讀後列入。同目錄原有的 `DUAL_EMBEDDING_RETRIEVAL.md`、`KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md`、`conversational-presales.md`
已於 2026-10-18 刪除（D5；歸檔副本在 `docs/archive/2026-09/`）。

### 檢索與知識

- 決策 | `docs/features/KNOWLEDGE_SCOPE_SIMPLIFICATION.md` | 知識範圍為何從 `scope` 欄位改成 `vendor_id` 判定,以及回滾路徑
- 規格 | `docs/features/DOCUMENT_CONVERTER.md` | Word/PDF 轉 Q&A 的端點、支援格式與成本估算

### 表單

- 規格 | `docs/features/FORM_MANAGEMENT_SYSTEM.md` | 動態表單收集系統的 Schema、API 與前端整合
- 規格 | `docs/features/knowledge-form-auto-option.md` | 表單自動選擇的改進設計方案(2026-02-05)；⚠️ 歷史設計案：`trigger_form_condition` 欄位已刪（同主題的 `knowledge-form-auto-quick-ref.md` 已於 2026-10-18 刪除）

### 系統管理

- 規格 | `docs/features/AUTH_SYSTEM_README.md` | 管理後台 JWT 認證怎麼運作、安全設定要注意什麼
- 規格 | `docs/features/PERMISSION_SYSTEM_README.md` | RBAC 的角色、權限分類與前後端用法

### SOP

- 決策 | `docs/features/sop/implementation/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md` | 為何限制觸發模式與後續動作的有效組合,以及前後端各擋哪一段
- 規格 | `docs/features/sop/optimization/SOP_KEYWORDS_COMPARISON.md` | `keywords` 與 `trigger_keywords` 差在哪、各自何時生效
- 判定 | `docs/features/sop/SOP_TRIGGER_MODE_UPDATE_INDEX.md` | 2026-02-03 的 SOP 觸發模式 UI 更新紀錄(歷史);⛔ 觸發模式在對話路徑上已不存在

### 目錄索引

- 路由 | `docs/features/README.md` | `docs/features/` 與 `sop/` 子樹共 19 份的導航;⚠️ 2026-09-04 依實況重建——此前它自稱 24 份、提到的 30 個檔名有 **19 個已不存在**(存活率 36%)且漏列 8 份

⚠️ **同批已判快照、⛔ 不在此列**:`docs/features/sop/testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md`
(測試日期 2026-02-03＋測試資料＋發現問題＋簽核,快照特徵齊全)。

## 設計文件 {#design-docs}

⚠️ 這 9 份於 2026-09-04 逐份判讀後列入,且**逐一驗證過對應實作是否存在**(見各條)。
`agentic-mcp-orchestration` 的架構目標見 `#agentic-mcp`;`LOOKUP_TABLE_SYSTEM_DESIGN.md`
在 `canon.json` 的 `discover_exclude`。

### API 架構

- 規格 | `docs/design/CORE_API_FUNCTIONS_REFERENCE.md` | API 統一處理架構有哪些核心函數、各自負責什麼
- 路由 | `docs/design/API_CONFIGURATION_GUIDE.md` | 知識要觸發 API 呼叫時,設定檔怎麼寫、參數怎麼映射

### 知識動作與表單


### 權限

- 規格 | `docs/design/PERMISSION_SYSTEM_DESIGN.md` | RBAC 的資料表結構、前後端分工與實作階段規劃;產線在 `knowledge-admin/backend/`(`routes_roles.py` 的 `/api/roles`、`routes_auth.py`、`auth_utils.py`)
- 規格 | `docs/design/PERMISSION_UI_DESIGN.md` | 權限管理前端的頁面、元件與互動流程;⚠️ 它點名的 `knowledge-admin/frontend/src/config/menu.js` 與 `components/AppMenu.vue` **已不存在**(11 個引用中 2 個失效),其餘前端實作仍在(`composables/usePermission.js`、`directives/permission.js`)

🔴 **本 repo 有兩個後端服務,查證實作時 ⛔ 不可只搜其中一個**:
`rag-orchestrator/`(AI 客服主服務)與 `knowledge-admin/backend/`(知識後台:權限／角色／認證)。
⚠️ 2026-09-04 曾因只搜 `rag-orchestrator/routers/` 而誤判「RBAC 權限系統查無 API 面」——
正對照組當時取自同一目錄,只證明 grep 會動、不證明範圍對。

## 部署與使用手冊 {#deploy-and-manuals}

⚠️ 這 8 份於 2026-09-04 逐份判讀後列入。同批另有 9 份判為快照,見文末。

### 部署(四份分工明確,⛔ 別挑錯本)

- 路由 | `docs/deployment/README.md` | 這次部署該讀哪一本;⚠️ 版本歷史區段停在 2026-01-28,且宣稱歷史紀錄已遷至 `archive/deployment-logs/` 但實際在 `records/`
- 產線 | `docs/deployment/DEPLOY_GUIDE.md` | **無遷移需求的日常小版更**怎麼部署;⚠️ 檔內第 3 行逐字:「2026-07-06 起,五域面向＋計量額度批次的部署一律走 `docs/deployment-runbook.md`……本文件僅適用『無遷移需求的日常小版更』」
- 判準 | `docs/deployment/DEPLOY_CHECKLIST.md` | 每次部署都必須逐項確認什麼(自稱「不要跳過任何步驟」)

⚠️ 主線 runbook 是 `docs/deployment-runbook.md`,已列於〈專案層級索引〉。

### 使用手冊

- 產線 | `docs/user-guides/VENDOR_SOP_USER_GUIDE.md` | Platform 與 Vendor 兩種角色各自怎麼配置 SOP 流程
- 判定 | `docs/user-guides/knowledge-loop-status.md` | 知識完善迴圈剩下什麼:5 支 GET 查詢＋3 支審核端點(逐支實測);⛔ 啟動迴圈／執行迭代的端點已不存在(`grep -c "@router.post" rag-orchestrator/routers/loops.py` ＝0);想跑改善輪走 `.claude/skills/retrieval-improvement-loop/`

⚠️ 上三份是**同主題的入門／標準／深度三層**,同日(2026-05-18)更新,**無任何一份明說取代關係**。

⚠️ **同批已判快照、⛔ 不在此列**:`docs/maintenance/audit_2026-06-26.md`(全 repo 文件健全度稽核)、
`docs/deployment/records/20260729_{deploy,steps}.md`(某次部署的紀錄與逐步手冊)、
`docs/changelog/2026-02-10-remove-none-auto-trigger-modes.md`、
`docs/frontend/{batch_review,loop_management}_requirements.md`(檔頭「版本 1.0／建立時間 2026-03-27／對應任務 Task 9.2、9.3」,是**已交付的需求快照**——其引用的 `.kiro/specs/backtest-knowledge-refinement/` 已不存在,且**執行機制已於 2026-09 退役**,只剩查詢與審核面)、
以及 `docs/archive/2026-06/` 三份(見下)。

🔴 **`docs/archive/2026-06/` 三份的翻案紀錄**:`FORM_FILLING_INTEGRATION_PLAN.md`、
`FORM_FILLING_CODE_CHANGES.md`、`KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md` 先前判 `unsure`
(代理判 index、主 session 因「說不出排除理由」覆寫)。2026-09-04 找到決定性證據翻為快照:
`docs/maintenance/audit_2026-06-26.md` §B「封存(多餘/歷史)→ `docs/archive/2026-06/`」逐字列出
「form-filling(5):FORM_FILLING **規劃/草案**(保留 DIALOG_DESIGN)」與
「knowledge-action(3):KNOWLEDGE_ACTION **實作筆記**(保留 SYSTEM_DESIGN、QUICK_REFERENCE)」。
⚠️ 這是 `unsure` 的正確用法:當時查無證據就掛著,證據出現才翻案,⛔ 不是硬選一個。

## 架構、回測、測試 {#arch-backtest-testing}

⚠️ 這 12 份於 2026-09-04 逐份判讀後列入,其中 3 份為時點紀錄——沿用〈jgb2 盤查結論〉
的家族規約:**面向 `實測`＋一句話帶日期＋ triage 判快照**,⛔ 不是現況宣告。

### 架構

- 規格 | `docs/architecture/SYSTEM_ARCHITECTURE.md` | **現況系統全景正本**(v4.0,2026-09-12):核心是 `AgentRuntime`、`/mcp` 只是四個門面之一;15 個 face 與六域隔離不對稱;知識兩條路(git canon 自動注入 vs `kb.search` 模型調用);`tenant` 在新線不存在。對話線內部見 `AGENTIC_MCP_ARCHITECTURE.md`

### 測試

- 判準 | `docs/testing/api-integration-testing-guide.md` | Knowledge Admin API 的 `action_type`／`api_config` 支援怎麼驗收
- 判準 | `docs/testing/LOOKUP_SYSTEM_TEST_GUIDE.md` | Lookup 查詢系統(電費寄送區間、模糊匹配、地址)的三種測法與驗收準則
- 實測 | `docs/testing/multiturn-smoke-scripts.md` | 多輪 smoke 測試劇本與當時的測試身分(2026-07-12 整理;vendor 2、`mode=b2b`、`role_id=37305`)

## jgb2 盤查結論(Ground-truth Research) {#ground-truth-research}

🔴 **家族規約(業主 2026-09-04 裁,選項 C)**:這批全部是「**某次**對 jgb2 真碼的盤查結論」,
⛔ **不是現況宣告**。面向一律 `實測`,一句話一律帶盤查日期。
兩軸分開處理:MAP 給角色(找得到、知道它是什麼);`canon.json` 的
`docs/research/*-research.md` 排除它們的壞引用(那些引用指向 **jgb2 的路徑**,
在本 repo 不存在是預期行為,⛔ 不是腐爛)。
⚠️ 依據 `docs/research/README.md` 第 4 行逐字:「jgb2 持續演進;本目錄為『當時盤查』的
證據快照,**重大版更後如行為不符,先重盤再改斷言**」。
⛔ **不判現行的理由**:2026-09-04 實測 jgb2 一年 93 筆 commit 動 external controller、
文件同步率僅 14%,`docs/api/jgb_external_api_spec.md` 已漏 10 支端點 ——
宣告 2026-07 的盤查為「現行」會讓下一個人把過期事實當現況引用。

- 路由 | `docs/research/README.md` | 這批盤查各自答了哪個領域的什麼真相(目錄定位與導航)
- 實測 | `docs/research/billing-conversational-facets-research.md` | 滯納金兩機制、超商逢 5 撥付、發票開立時點、金流狀態機(2026-07-03)
- 實測 | `docs/research/estate-conversational-facets-research.md` | 物件兩軸狀態模型(`status`×`is_open`)與刊登條件(2026-07-04)
- 實測 | `docs/research/iot-conversational-facets-research.md` | 台科電＝DAE、電表機制、G 趨近零(2026-07-04)
- 實測 | `docs/research/conversational-diagnosis-research.md` | 合約診斷 v1 的 12 狀態首盤(2026-06-30)
- 實測 | `docs/research/quota-management-research.md` | 額度管制的裁決紀錄與 codebase 實查(2026-07-06)
- 實測 | `docs/research/usage-metering-research.md` | 使用量計量的裁決紀錄與 codebase／jgb2 實查(2026-07-06)
- 實測 | `docs/research/sop-audience-isolation-research.md` | **撤案 spec** 的 jgb2 真相三題:金流支付枚舉／電費六模式／統編(2026-07-04)
- 實測 | `docs/research/conversation-retrieval-resilience-research.md` | 檢索韌性的 P0→P2 改造順序覆核(2026-08-03);🔴 **該 spec 已由業主定性失敗、整案還原(main 與分支回 `cca0146`)**,⛔ 其設計方向已被推翻,只留調研脈絡

⚠️ 另兩份同家族的 `contract-` 與 `account-conversational-facets-research.md` 未列於此,
但已由同一條 `docs/research/*-research.md` 樣式涵蓋排除,體例一致。

## docs 根目錄 {#docs-root}

⚠️ 這 6 份於 2026-09-04 逐份判讀後列入。同批另有 5 份判為快照,見文末。

### 索引(兩份,分工明確且互相引用)

- 路由 | `docs/INDEX.md` | **主索引**:按「我要做什麼」找文件(架構／API／指南／回測／測試);第 3 行反向指向 `README.md`
- 路由 | `docs/README.md` | `docs/` 有哪些子目錄與常用入口;第 5 行明說「找特定主題?請先看 INDEX.md」

⚠️ 兩份是**分工不是重複**——`README` 答「這裡有什麼」,`INDEX` 答「我要做 X 該讀哪份」。

### 架構

- 規格 | `docs/architecture-overview.md` | 系統現況總覽:三類使用者與路由順位、對話面向、資料體系分工、計量與額度、品質三層、已知債總表
- 判定 | `docs/chat-architecture-overview.md` | 2026-09-12 刪至 27 行,只剩六條演化原則(2026-07-10 定案);觸發語彙診斷移交 `.kiro/specs/trigger-vocabulary-debt/`。現況架構走 `SYSTEM_ARCHITECTURE.md`
- 決策 | `docs/conversation-first-architecture-assessment.md` | 檢索中心骨架是否仍合適的評估與拍板:混合骨架候選 C 定案(2026-07-10)、P0–P3 四階段遷移;⚠️ **本檔是 2026-07-10 的評估快照,其拍板結論後續是否被 `agentic-mcp-orchestration` 主線取代,待裁**

### 設定

- 規格 | `docs/LLM_PROVIDER_MIXED_CONFIG_GUIDE.md` | 混合 LLM Provider 怎麼配置、成本怎麼優化、如何遷移

⚠️ **同批已判快照、⛔ 不在此列**(其中兩份自標,逐字):
`docs/SMART_RETRIEVAL_QUICK_REF.md`——「⚠️ **歷史文件**(2026-01-28)。當前架構細節請參考
`docs/architecture/retriever-pipeline.md`」;
`docs/API_ENDPOINTS_COMPLETE_INVENTORY.md`——「⚠️ **Snapshot:2026-02-17,未持續維護**……
名稱中的 "Complete" 僅指快照當時」(它盤的是**本 repo** 兩個後端的端點,提及 jgb2 0 次);
另 `docs/presales-assistant-quality-audit-20260902.md`(2026-09-02 實機測試報告)、
`docs/presales-assistant-rootcause-20260904.md`(2026-09-04 根因對碼)。
