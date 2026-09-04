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
- 路由 | `rag-orchestrator/routers/chat.py` | 分類路由進對話、依分類取 config 進場
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 1:動作知識必有面向接管或明確豁免
- 決策 | `.kiro/specs/account-conversational-facets/design.md` | 母分類劃分、API 掛點、b2c 初版範圍
- 規格 | `docs/api/account-api-contract.md` | 帳號 G/J 對外契約(交付 jgb2);消費端存在性驅動,不需同步上版

## 帳務對話面向 {#billing-facets}

- 規格 | `.kiro/specs/billing-conversational-facets/requirements.md` | 帳務五子面向:繳費金流、帳單異常、發票、滯納金、設定引導
- 規格 | `.kiro/specs/billing-conversational-facets/design.md` | 決定性計算與 formatter 分支透傳
- 產線 | `rag-orchestrator/services/jgb/bills.py` | 帳單 face builder 註冊表
- 產線 | `rag-orchestrator/services/jgb/payments.py` | 繳費狀態判因素材
- 產線 | `rag-orchestrator/services/jgb/invoices.py` | 發票邏輯
- 路由 | `rag-orchestrator/services/jgb_response_formatter.py` | 帳務分支的 face 透傳
- 判準 | `scripts/audit/check_invariants.sh` | 不變量 7:JGB 金額欄位一律走語義層,禁止重算
- 決策 | `.kiro/specs/billing-conversational-facets/design.md` | 分支劃分與金額禁重算原則

## Brain 知識庫落地 {#brain-kb-grounding}

- 規格 | `.kiro/specs/brain-kb-grounding/requirements.md` | 岔題即答要有知識背書,不靠印象回答
- 規格 | `.kiro/specs/brain-kb-grounding/design.md` | Callback 注入的工具圈與 async 邊界跨越
- 產線 | `rag-orchestrator/services/llm_answer_optimizer.py` | search_kb function calling
- 路由 | `rag-orchestrator/services/conversational_engine.py` | async kb_search closure 的建構與注入
- 實測 | `.kiro/specs/brain-kb-grounding/tasks.md` | 岔題三態:進場、多輪、逸出
- 決策 | `.kiro/specs/brain-kb-grounding/design.md` | 工具圈內聚、async 重構、tools API 選型

## 合約對話面向 {#contract-facets}

- 規格 | `.kiro/specs/contract-conversational-facets/requirements.md` | 合約五子面向涵蓋完整生命週期
- 規格 | `.kiro/specs/contract-conversational-facets/design.md` | 資料驅動、決定性計算、face 參數貫穿
- 規格 | `.kiro/specs/contract-conversational-facets/g1-g4-api-contract.md` | 外部 API 契約定義
- 產線 | `rag-orchestrator/services/jgb/contracts.py` | 合約 face builder 註冊表
- 路由 | `rag-orchestrator/services/api_call_handler.py` | face 參數貫穿到 API 呼叫
- 判準 | `rag-orchestrator/tests/unit/conversational/test_step_scope_face_req.py` | face 與 scope 正規化驗收
- 判準 | `rag-orchestrator/tests/unit/conversational/test_engine_scope_face_req.py` | 引擎端 face 處理驗收
- 決策 | `.kiro/specs/contract-conversational-facets/design.md` | face 參數設計、formatter 分層、matcher 預先生成

## 對話式診斷 {#conversational-diagnosis}

- 規格 | `.kiro/specs/conversational-diagnosis/requirements.md` | API grounding 與分類路由進對話
- 規格 | `.kiro/specs/conversational-diagnosis/design.md` | select:api 分支、依分類查 config、三路出口
- 產線 | `rag-orchestrator/services/conversational_engine.py` | select:api grounding 分支
- 產線 | `rag-orchestrator/services/api_call_handler.py` | API 呼叫重用
- 路由 | `rag-orchestrator/routers/chat.py` | 分類到 config 的路由出口
- 判準 | `.kiro/specs/conversational-diagnosis/gap-analysis.md` | 現行轉折點覆蓋分析
- 決策 | `.kiro/specs/conversational-diagnosis/design.md` | select 三路、config 依分類索引、API 參數透傳

## 對話式修繕 {#conversational-repair}

- 規格 | `.kiro/specs/conversational-repair/requirements.md` | 修繕交易面向、三輪完成、四業者同步
- 規格 | `.kiro/specs/conversational-repair/design.md` | confirm/execute 交易語義與決定性推斷
- 產線 | `rag-orchestrator/services/conversational_engine.py` | confirm/execute 分支
- 產線 | `rag-orchestrator/services/jgb/repair_prefill.py` | 修繕單預填邏輯
- 路由 | `rag-orchestrator/routers/chat.py` | 面向鍵直達路由、損傷圖對應面向
- 決策 | `.kiro/specs/conversational-repair/design.md` | 租約 mock、影像信心度、confirm 文案、execute 重用、計量埋點

## 領域化對話面向 {#domain-facets}

- 規格 | `.kiro/specs/domain-conversational-facets/requirements.md` | 領域化脈絡、混合 grounding、多筆候選辨識
- 規格 | `.kiro/specs/domain-conversational-facets/design.md` | 脈絡、合成、候選三邊界擴充
- 產線 | `rag-orchestrator/services/conversational_engine.py` | scope/face 正規化與狀態機擴充
- 產線 | `rag-orchestrator/services/system_context.py` | 系統脈絡的領域化查詢
- 路由 | `rag-orchestrator/routers/chat.py` | 混合 grounding 分支
- 判準 | `rag-orchestrator/tests/unit/conversational/test_engine_scope_face_req.py` | scope/face 明列、衍生、失敗三態驗收
- 決策 | `.kiro/specs/domain-conversational-facets/design.md` | per-領域脈絡、face 衍生、scope 正規化
- 實測 | `docs/research/domain-conversational-facets-research.md` | 領域面向的現行 ground-truth(2026-08-22 triage 判為現行索引,非快照)

## 物件對話面向 {#estate-facets}

- 規格 | `.kiro/specs/estate-conversational-facets/requirements.md` | 物件領域兩子面向:操作引導、現況診斷
- 規格 | `.kiro/specs/estate-conversational-facets/design.md` | 兩軸狀態機的決定性機制語義
- 規格 | `.kiro/specs/estate-conversational-facets/research.md` | 真碼盤查定案項
- 產線 | `rag-orchestrator/services/jgb/estates.py` | 物件 fact-builder 與狀態機解碼
- 路由 | `rag-orchestrator/services/conversational_engine.py` | 二級呼叫取物件詳情
- 決策 | `.kiro/specs/estate-conversational-facets/design.md` | API 直查、二級詳情、面向切換邊界

## 智慧設備對話面向 {#iot-facets}

- 規格 | `.kiro/specs/iot-conversational-facets/requirements.md` | 兩子面向:電表排障、設定引導
- 規格 | `.kiro/specs/iot-conversational-facets/design.md` | 離線優先機制語義與 DAE 同步語義
- 規格 | `.kiro/specs/iot-conversational-facets/research.md` | 台科電機制與 jgb2 真碼盤查
- 產線 | `rag-orchestrator/services/jgb/iot.py` | 電表 fact-builder 與離線優先判定
- 路由 | `rag-orchestrator/routers/chat.py` | 電表清單查詢與篩選
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
- 路由 | `rag-orchestrator/routers/chat.py` | 檢索前後與路由三個攔截點
- 判準 | `rag-orchestrator/tests/unit/decision/test_decision_layer_equivalence_req.py` | 大規模對拍的嚴格等價測試
- 判準 | `scripts/audit/checks/decision_threshold_ast.py` | 不變量 8 的 AST 檢查,含規避寫法自我測試
- 決策 | `.kiro/specs/archive/retrieval-decision-layer/decisions/DECISIONS.md` | D-01 起的決策彙整(已封存)
- 判準 | `docs/retrieval-parameters.md` | 參數台帳:每個可調參數的現值、控制什麼、有沒有實證;⛔ 沒有實證欄位的參數不要動
- 規格 | `docs/architecture/DATABASE_SCHEMA.md` | 39 表 schema;三個檢索過濾欄位的描述與實際 SQL 一致(2026-09-01 帳本判可依據)
- 決策 | `docs/retrieval-recall-audit-20260822.md` | 前案盤查與裁決:適用性把關改 precision-first、b2b `business_types` 嚴格過濾是刻意隔離**勿改**;⚠️ 文內已自行宣告第六、七節量化結果失效
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-doc-status-ledger.md` | b2b／檢索過濾／門檻主題的**文件可信度分流**:哪幾份可依據、哪幾份照做會出事
- 規格 | `docs/architecture/retriever-pipeline.md` | 檢索管線架構:分數合成與 vector/rerank 的適用條件(程式註解多處引用)

## SOP 受眾隔離 {#sop-audience-isolation}

- 規格 | `.kiro/specs/sop-audience-isolation/requirements.md` | SOP 受眾隔離與 target_user 維度
- 規格 | `.kiro/specs/sop-audience-isolation/design.md` | schema 加欄、資料回填、補位知識
- 規格 | `.kiro/specs/sop-audience-isolation/research.md` | 內容體系查證與受眾錯位根因
- 產線 | `rag-orchestrator/services/vendor_sop_retriever_v2.py` | retriever 單點過濾與 SQL 謂詞
- 路由 | `rag-orchestrator/services/sop_orchestrator.py` | SOP 查詢穿線
- 決策 | `.kiro/specs/sop-audience-isolation/design.md` | schema 同型別語義、審表閘門、補位知識路徑
- 規格 | `docs/features/sop/README.md` | SOP 系統文檔索引
- 規格 | `docs/guides/features/SOP_GUIDE.md` | SOP 系統完整指南(v2.0 整合版)
- 判準 | `docs/guides/reference/SOP_QUICK_REFERENCE.md` | 新增 SOP 的操作快速參考

## 觸發語彙債 {#trigger-vocabulary-debt}

- 規格 | `.kiro/specs/trigger-vocabulary-debt/requirements.md` | 觸發配置檢索斷鏈修復與死欄位移除
- 規格 | `.kiro/specs/trigger-vocabulary-debt/design.md` | 三層不改語義、仲裁分數埋點、欄位偵測降級
- 產線 | `rag-orchestrator/services/vendor_knowledge_retriever_v2.py` | 觸發三欄透傳
- 產線 | `rag-orchestrator/services/usage_metering.py` | 仲裁比較 hook 與欄位偵測降級
- 路由 | `rag-orchestrator/routers/chat.py` | 仲裁分數埋點呼叫點
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

## 對話邏輯與路由執行(主線) {#dialogue-logic}

⚠️ 測對話邏輯之前用 `/canon-audit dialogue-logic` 起盤查——下列每一份**整檔讀完**才算數,
Stop 閘門會擋到讀完為止。⛔ 這一份清單存在的理由:沒有必讀清單時,測試會反覆漏掉已裁決的前提。

- 規格 | `.kiro/specs/conversational-routing-execution/requirements.md` | 主線唯一 spec 的需求正本
- 規格 | `.kiro/specs/conversational-routing-execution/design.md` | 責任/提名/授權架構設計正本
- 決策 | `.kiro/specs/conversational-routing-execution/HANDOFF-20260901.md` | 現行交接:主線是什麼、哪些事實別再重查、已知錯誤文件與工具地雷
- 決策 | `.kiro/specs/conversational-routing-execution/mainline-map.md` | 收束盤點:已 CLOSED／帶 claim ceiling／PAUSED 三態與 release policy
- 決策 | `.kiro/specs/conversational-routing-execution/PLAN-retrieval-coverage.md` | 現行計畫 v2,逐筆事實以此為準
- 判準 | `.kiro/specs/conversational-routing-execution/a03-retrieval-failure-taxonomy.md` | 檢索失敗分類:四種失敗類型的判定尺
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-batch-selection-rule.frozen.md` | b2b 批次選題規則(凍結)
- 實測 | `.kiro/specs/conversational-routing-execution/b2b-b2c-pool-audit.md` | b2b／b2c 資源池盤查
- 實測 | `.kiro/specs/conversational-routing-execution/b2b-ground-truth.md` | b2b 標註基準
- 規格 | `docs/jgb2-chat-integration.md` | 三種身分形狀決定資源池——⚠️ 挑測試身分前必讀
- 判準 | `docs/retrieval-parameters.md` | 量測紀律:不要離線重建 pipeline、比較性結論 30 題起跳
- 決策 | `docs/retrieval-recall-audit-20260822.md` | 前案裁決:precision-first、b2b 嚴格過濾勿改
- 判準 | `.kiro/specs/conversational-routing-execution/b2b-doc-status-ledger.md` | b2b／檢索過濾／門檻主題的**文件可信度分流**:哪幾份可依據、哪幾份照做會出事
- 產線 | `rag-orchestrator/services/conversational_engine.py` | 對話狀態機與 confirm/execute 分支
- 產線 | `rag-orchestrator/services/llm_answer_optimizer.py` | `conversational_step` 的 action／scope 驗證順序
- 路由 | `rag-orchestrator/routers/chat.py` | 面向進場、適用性把關、三個攔截點
- 規格 | `docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` | 對話架構母圖(被主線 spec 引用 8 次);⚠️ §3 過濾公式與兩處門檻敘述已於 2026-09-01 對碼修正,決策樹本體與 `decide_arbitration` 逐條相符
- 規格 | `docs/architecture/facet-architecture.md` | 面向化三層疊加的邏輯與資料佈局(取代 design.md 元件1/D2 的兩層版本)
- 判準 | `docs/routing-gate-acceptance.md` | pre-entry routability gate 驗收契約——**實作前凍結,⛔ 指標定義與通過線不得改**
- 實測 | `scripts/audit/reports/regrade291-triage.md` | **69.7% 基準的唯一出處**(548 題乾淨重跑;舊寬鬆基準 60.2%)
- 規格 | `docs/features/conversational-presales.md` | 對話式回答模式本身:單次直答 → 多輪自適應收斂(prospect 為第一個套用者)
- 規格 | `docs/api/conversational-api.md` | 對話式回答的對外串接指南

## jgb2 串接契約 {#jgb2-chat-integration}

- 規格 | `docs/jgb2-chat-integration.md` | 一支 API 三種身分形狀:`mode`＋`target_user`＋`role_id` 決定回答資源池與跨業者隔離;`vendor_id` jgb2 不送,由 AI 側經 role_id 解出
- 路由 | `rag-orchestrator/routers/chat.py` | 身分欄位驗證與 vendor 補全的進場點
- 判準 | `rag-orchestrator/services/vendor_knowledge_retriever_v2.py` | b2b 資源池的實際過濾點(`business_types`／`target_user` 謂詞)

⚠️ 三種身分形狀是**對外契約**,⛔ 不屬於任何單一對話面向 —— 帶錯 `mode` 即受眾錯位,
而 `target_user` 漏帶時系統只依 mode 推導、`prospect` **不會**被自動推導。

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
- 產線 | `tests/` | 測試套件的執行說明與資料集說明
- 產線 | `database/` | migration 體系與 seed 的使用說明
- 產線 | `data/` | 知識單元格式與業者知識範本說明
- 產線 | `knowledge-admin/` | 知識後台前端的說明與遷移紀錄
- 產線 | `rag-orchestrator/README.md` | 主服務的使用說明
- 產線 | `rag-orchestrator/services/jgb/README.md` | JGB 整合層的端點、認證與 `bit_status` 對照
- 產線 | `rag-orchestrator/artifacts/responsibility/README.md` | responsibility 產物說明

⚠️ 這區是**隨程式走的操作說明**,⛔ 不是產品功能正本 —— 它們回答「這個目錄怎麼用」,
不回答「系統對使用者做什麼」。⚠️ 其中多份壞引用密度高(`/canon-triage` 的處置清單裡
`tests/data/README.md`、`tests/integration/README_*.md`、`rag-orchestrator/services/jgb/README.md`
被列為「整份可能已退休」),⛔ 引用前一律對碼。

## repo 根目錄 {#repo-root}

- 產線 | `README.md` | 專案入口與環境起法
- 產線 | `CLAUDE.md` | 本專案的事實紀律與工作流規約
- 實測 | `CHANGELOG.md` | 變更歷史 ⚠️ 內含大量指向已刪檔的歷史區段,⛔ 那是紀錄不是腐爛

⚠️ 本區塊三段(工具設定／產線輔助／根目錄)於 2026-09-04 加入,一次收編 80 份,
覆蓋率 353→433 / 558。⛔ 目錄宣告**不等於**逐份裁決為現行 —— 同 `.kiro/specs/` 的先例。
