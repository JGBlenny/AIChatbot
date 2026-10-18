# D5 steering 盤點表（2026-10-18）

依據：業主 2026-10-17 裁示「文件過時、依程式更正」；T11（確定錯的刪或更正、判不出的留著並列清單）。
範圍：`.kiro/steering/` 現有檔案（`find .kiro/steering -name '*.md'` 計 10 份）。其中 `plan-touchpoint-checklist.md` 是 D2 新建、`answer-eval-and-probe.md` 是 D1 新建（且工作樹另有 D3 的未提交增行）；兩者 D5 只判定、不編輯。本表列原 9 份加 D2 檔 1 份。

判定三類：現行正確／依程式更正／刪除（刪除＝整段刪，檔案本身都保留）。

| 檔 | 判定 | 本次變更（段落層級） | 主要證據（可重跑） |
|---|---|---|---|
| ai-usage.md | 依程式更正＋刪除 | 刪 §1 六列迴圈任務（智能分類／聚類／SOP 生成／知識生成／分類選擇／群組選擇）；刪 §2 迴圈溫度程式塊（改為指向現行呼叫點）；刪 §3 `OpenAICostTracker`／`PRICING`／`BudgetExceededError`／預算警告範例與批次大小範例，改寫為「成本進 `openai_cost_tracking`、計價見 `usage_metering.py`」；§5 三個迴圈 prompt 範例整段刪；§6 迭代成本估算與預算表整段刪；§7 `RAG_API_URL` 預設改 `http://rag-orchestrator:8100`、刪 `VENDOR_ID`／`BACKTEST_ONLY` 兩行；對話回合列改寫為程式回退鏈並指向 DSP-075／DSP-080；核心原則 1、5 去掉預算警告與迴圈彙總句 | `ls rag-orchestrator/services/knowledge_completion_loop`（只剩 `__init__.py`、`embedding_client.py`）；`grep -rn OpenAICostTracker rag-orchestrator`、`BudgetExceededError`（零命中）；`grep -rn "適度聚類\|applicable_questions" rag-orchestrator`（零命中）；`grep -n RAG_API_URL docker-compose.prod.yml knowledge-admin/backend/app.py`；`grep -rnE "getenv\(.VENDOR_ID\|BACKTEST_ONLY" --include='*.py' --include='*.yml' .`（零命中）；`grep -n "INSERT INTO openai_cost_tracking" rag-orchestrator/services/image_recognition_service.py rag-orchestrator/services/agent/mcp_facade.py`；`grep -n DEFAULT_PRICING rag-orchestrator/services/usage_metering.py`；`grep -n AGENT_MODEL rag-orchestrator/services/agent/runtime.py` |
| dialogue.md | 依程式更正 | 「受眾只有兩種」的 canon 路徑改為 `rag-orchestrator/canon/jgb/A.md…I.md`＋`CATALOG.md`、受眾改由 `build_outline` 篩選；face 數 15 → 16 並列各域數 | `ls rag-orchestrator/canon/jgb`；`sed -n 1,10p rag-orchestrator/canon/README.md`；`grep -n "FACE_BUILDERS" rag-orchestrator/services/jgb/bills.py rag-orchestrator/services/jgb/contracts.py rag-orchestrator/services/jgb/accounts.py rag-orchestrator/services/jgb/repairs.py rag-orchestrator/services/jgb/iot.py rag-orchestrator/services/jgb/estates.py` 數 key：5+5+2+2+1+1＝16；正對照 `grep -rn "agent.turn" .kiro/steering`（命中 dialogue.md、debugging-workflow.md、testing-code.md，皆為現行或已更正） |
| knowledge.md | 依程式更正 | `FORM_TRIGGER_THRESHOLD` 內部矛盾改為與檔頭一致（無消費者）；兩處「閾值 ≥0.6（`KNOWLEDGE_MIN_THRESHOLD`）」改為 `KB_SIMILARITY_THRESHOLD` 預設 0.65，並註明 `knowledge_min=0.6` 無消費者、該 env 名不存在 | `grep -rn --include='*.py' "form_trigger_threshold\|facet_entry_eligible\|form_trigger_eligible\|decide_arbitration" rag-orchestrator \| grep -v tests`（只剩 `decision_layer.py` 自身）；`grep -n "KB_SIMILARITY_THRESHOLD\|knowledge_min" rag-orchestrator/services/decision_layer.py`；`grep -n DecisionConfig rag-orchestrator/services/agent/tools/kb.py`；`grep -rn KNOWLEDGE_MIN_THRESHOLD`（程式零命中） |
| product.md | 依程式更正 | 「15 個 face」→ 16；「信心度評估與答案合成已刪」改為執行路徑已刪、補 `disable_answer_synthesis` 旗標名殘留；價值主張第 1 點的自動缺口發現改為已刪、現行改由 `retrieval-improvement-loop` skill；「現況增補」標題與單一真相源改指 `docs/architecture/SYSTEM_ARCHITECTURE.md`（architecture-overview.md 現為指路檔） | `grep -n disable_answer_synthesis rag-orchestrator/services/usage_metering.py rag-orchestrator/services/agent/shadow.py`；face 同上；`head -30 docs/architecture-overview.md`（檔頭自稱指路檔）；`ls .claude/skills/retrieval-improvement-loop` |
| structure.md | 依程式更正 | steering 樹：刪 `operations.md`、補其餘檔；`routers/agent.py` 說明更正；services/agent 補 14 檔（affirmative／bill_period／limits／text_norm／trace_view／provenance_units／bootstrap／agent_session／output_schema／write_forms／completed_actions／image_fetch／document_extract，tools 補 `jgb2_stats.py`）；services/jgb 補 invoices／fixture_store／fixtures／point_refund_selection；`resolve_template` 說明更正；docs/backtest 樹改為實際檔；`docker-compose.yml` → `docker-compose.dev.yml`；匯入範例改為存在的符號；DB 段補「權威 schema 不在現行 migrations」「三個 migration 目錄」並更正 knowledge_base 欄位；環境變數段：模型回退鏈、`KNOWLEDGE_GEN_MODEL`／`DOCUMENT_CONVERTER_MODEL` 鏈、`EMBEDDING_MODEL` 讀者、`ENABLE_QUERY_REWRITE` 與 `_B2B` 的程式 fallback、`BILLING_*` 標未使用；現況增補 face 數與單一真相源 | `ls rag-orchestrator/services/agent rag-orchestrator/services/jgb rag-orchestrator/services/agent/tools docs/backtest`；`ls docker-compose*.yml`；`grep -n "resolve_template" rag-orchestrator/services/vendor_parameter_resolver.py`（檔內自呼叫；檔外零）；`grep -rn --include='*.py' "BILLING_API" . \| grep -v tests`（零）；`grep -n "ENABLE_QUERY_REWRITE" rag-orchestrator/services/query_rewriter.py rag-orchestrator/services/base_retriever.py docker-compose.dev.yml docker-compose.prod.yml`；`grep -n "KNOWLEDGE_GEN_MODEL\|DOCUMENT_CONVERTER_MODEL" rag-orchestrator/services/knowledge_generator.py rag-orchestrator/services/knowledge_import_service.py rag-orchestrator/services/document_converter_service.py`；`grep -n "EMBEDDING_MODEL" rag-orchestrator/services/llm_provider.py rag-orchestrator/tools/canon/ruler_eval.py`；`grep -rliE "CREATE TABLE( IF NOT EXISTS)? +(public\.)?knowledge_base" database rag-orchestrator/database rag-orchestrator/migrations`（只有 init-legacy／backups）；`sed -n 1,40p database/init-legacy/02-create-knowledge-base.sql` |
| tech.md | 依程式更正 | 目錄樹 `utils/` → `tools/`、Utils 層改為 `services/*_utils.py`；`routers/agent.py` 說明更正（prefix `/api/v1/agent`；`/mcp` 是 `mcp_facade.py` 的 `Mount`）；face 15 → 16（行內與現況增補，合約 4 → 5）；刪迴圈批次處理一句；AI 模型段改為程式回退鏈（對話／文件轉換／知識匯入／知識生成），消除文件轉換 gpt-4o／gpt-4o-mini 的內部矛盾；刪 `PERFECT_MATCH_THRESHOLD` 等四顆門檻對應說明（改標無讀者）；刪 `BACKTEST_BATCH_LIMIT`、`RAG_RETRIEVAL_LIMIT` 兩句；`/api/v1/chat` 範例更正；`config/` 補 `agent_verifier_rules.json`；單一真相源改指 SYSTEM_ARCHITECTURE.md | `ls rag-orchestrator rag-orchestrator/config`；`grep -n "prefix\|@router" rag-orchestrator/routers/agent.py`；`grep -n 'Mount("/mcp"' rag-orchestrator/services/agent/mcp_facade.py`；`grep -rn --include='*.py' --include='*.yml' -l "SYNTHESIS_THRESHOLD\|RAG_RETRIEVAL_LIMIT\|BACKTEST_BATCH_LIMIT" .`（無非測試讀者；`PERFECT_MATCH_THRESHOLD` 等在 `docker-compose.prod.yml` 僅出現於註解 212–214 行）；`grep -rn "api/v1/chat" --include='*.py' rag-orchestrator \| grep -v tests`（零） |
| debugging-workflow.md | 依程式更正 | 3b「那五個子系統已刪」改為四個（意圖分類／SOP 觸發／表單狀態機／答案優化），並說明 `decision_layer.py` 仍在、`KB_SIMILARITY_THRESHOLD` 由 `kb.py` 讀；前端清單的 `docker-compose.yml` → dev／prod 兩份 | `grep -n "DecisionConfig" rag-orchestrator/services/agent/tools/kb.py`；`ls docker-compose*.yml`；`ls knowledge-admin/frontend/src/config/api.js knowledge-admin/frontend/src/components/LoopManagementTab.vue`（確認其餘引用存在） |
| testing-code.md | 現行正確（本次不改） | 無。D1 擁有（加連結行），D5 只判定 | `ls tests rag-orchestrator/tests/e2e/api`（根 `tests/` 與唯一 e2e 檔存在）；`ls .github/workflows/tests.yml rag-orchestrator/.coveragerc`；文中 `/api/v1/message` 與 `knowledge_completion_loop` 皆在「已刪除／已退役」句內 |
| answer-eval-and-probe.md | 現行正確（本次不改） | 無。D1 新增、D3 另有未提交增行，D5 只判定 | 內容為評估骨架規範與環境坑；檔內引用的 `scripts/run-tests.sh`、`docker-compose.prod.yml` 存在（`ls`）；其餘依賴 repo 外 `~/jgb-archive/` 未查 |
| plan-touchpoint-checklist.md | 現行正確（不判、不編輯） | D2 於本切片進行中建立，未列入 D5 範圍 | — |

## 未查證清單（本次未動文字，需何種證據才能判）

### ai-usage.md
- §1「複雜推理 gpt-4o 0.7」「測試題生成 gpt-4o 0.8」兩列：找不到對應程式呼叫點。證據：grep 測試題生成的 `chat.completions` 呼叫與其 temperature；找得到則核對、找不到則刪列。
- 「文件轉換 gpt-4o 0.3」：程式 fallback gpt-4o、temperature 0.3 已對上（`document_converter_service.py`），但 prod compose 預設是 gpt-4o-mini，實際線上值未查（需看正式機 env）。
- `DB_PORT`、`OPENAI_API_KEY` 必需性、tenacity 退避參數「1s,2s,4s,8s」（範例碼，非實碼）：未逐一對程式。
- §4 `API 重試機制` 範例：`tenacity` 在 requirements 與 `knowledge_completion_loop/embedding_client.py` 有用，但該範例的 `call_openai_api` 不是真實函式。證據：確認對話路徑重試實作（`services/llm_provider.py`）後決定改寫或刪。
- 模型價格（gpt-4o-mini／gpt-4o 每百萬 token 單價）：外部價格，未查原文（比對 `usage_metering.py` 的 `DEFAULT_PRICING` 可核）。

### dialogue.md
- 「13 步進場契約」「六條終止路徑」「九段注入」「四道閘」：檔內已指向程式自述，本次未逐項重數。證據：`turn_segments.py` docstring、`exit_gates.py::EXIT_GATES`、`mcp_facade.py` 進場步驟註解。
- 「`AGENT_TURN_SPEC["stage"]` 無 tenant 鍵」「`audience_of` 映射」：未重核。
- 「系統角色對應」表 2026-09-12 已逐一確認存在；本次僅抽核 canon／jgb 兩列。

### knowledge.md
- IVFFlat 索引：只在 `database/init-legacy/` 與 `database/fixes/` 的 SQL 中出現，現行 DB 是否實際使用 IVFFlat 或 HNSW 需查 DB（`\d knowledge_base`）。
- §3 配置 A 的 `trigger_form_condition`／`trigger_conditions`／`auto_keywords`：`rag-orchestrator/database/migrations/drop_knowledge_trigger_dead_columns.sql` 要刪這三欄，但是否已於各環境執行未知。證據：查 DB 欄位。
- §2 `knowledge_type`／`response_type` 偽碼與 §4「SOP vs Knowledge Base 路由」的 `generate_sop`／`generate_knowledge_base`：`generate_knowledge_base` 程式零命中、`response_type` 零命中；但 `routers/loop_knowledge.py`、`routers/knowledge_generation.py` 仍掛在 `app.py` 且用 `knowledge_type`。證據：讀這兩支路由的審核同步邏輯後判斷偽碼是否仍描述現行審核流程。
- §5 審核流程（`pending_review`→`approved`）：路由仍在，執行器已無；`loop_generated_knowledge` 表是否仍有新增列未查。
- 核心原則 1、4 與 `source='loop'`：描述的仍是歷史資料與後台審核，是否算現行未判。

### product.md
- 「品質三層：系統回測（迴圈＋多輪模擬＋v3 評審＋金標，按受眾分庫）」：「迴圈」字樣與現行 `retrieval-improvement-loop` skill 的關係未核。證據：對照 `.claude/skills/retrieval-improvement-loop/SKILL.md` 與 `make` 目標。
- 「審核中心」「視頻知識」「覆蓋率分析」「AI 輔助測試題生成」：後台功能存在性未逐項核（需看 `knowledge-admin/frontend` 路由與 `routers/`）。
- 「目標用戶隔離」列出的 `system_admin`、`landlord`：未查現行 `target_user` 值域。

### structure.md
- test_scenarios／backtest_results 欄位清單：與 `database/init-legacy/09-create-test-scenarios.sql` 不一致（init 無 `vendor_id`、有 `passed`／`system_answer`），但後續 migration 可能改過。證據：查 DB `\d test_scenarios`、`\d backtest_results`。
- `knowledge-admin/frontend/src/views/CategoryConfigView.vue`、`embedding-service/`、`semantic_model/` 的內容：目錄存在，內容未逐檔核。
- 「scripts/」樹中 `knowledge-batches`、`smoke`、`deployment` 存在；`audit/checks/` 一支一條未重數。
- 命名模式章節的範例檔（`unified_job_service.py` 等）本次抽核存在，未逐一確認。
- 「.kiro/settings/」：fact-check 回報「找不到」，本次實查**存在**（含 `rules/`、`templates/`），故保留原文。
- 「品質三層」與 tech.md 同句，未查證項同上。
- `rag-orchestrator/migrations/` 的檔案現況（僅確認首批為 `add_loop_features*.sql`）。

### tech.md
- 「`services/agent/` 30 檔」：`ls` 計 31 個 `.py` 含 `__init__.py`，視為相符，未另改。
- 檢索分數公式（0.1×vector + 0.9×rerank）、`_vector_search` LIMIT（SOP 50、KB 100）、「優先級加成 >0.7 +0.15」、關鍵字加成倍率：未重核（`base_retriever.py` 內可查，2026-04 重構段）。
- 「`print()` 進行即時日誌」、「連接池 min_size／max_size」、「Redis TTL」：慣例性描述，未逐一對程式。
- 「AgentRuntime 的四個門面之一」：dialogue.md／architecture-overview.md 同說，未重核 `agent_eval`、`shadow` 等是否為門面。
- 部署段 `K8s ConfigMap/Secret`：repo 是否有 K8s 配置未查。

### debugging-workflow.md
- 「`GET /api/v1/agent/trace/{trace_id}`」「`/health` 回 `verifier_mode`／`use_mock_jgb_api`／`limits`」：路由存在（`routers/agent.py`），回傳欄位未逐一核。
- `req.app.state.db_pool` 與 `routers/loops.py` 的 HTTPException 慣例：未核。
- 「環境變數 `agent_turn` log 行格式」：`_emit_agent_decision` 欄位未重核。

### testing-code.md
- 「根 `./tests/`：手動工具腳本樹（D6）」：根 `tests/` 目錄存在，但「手動工具腳本樹」「排除於 CI／覆蓋率」未核。證據：`ls tests`、`rag-orchestrator/.coveragerc`、`.github/workflows/tests.yml`。
- 「12 個 e2e 檔 67 個 test／2670 行已刪除」歷史數字：未核（可由 git log 查）。
- `make test`／`make test-cov`／`make trace` 目標存在性、CI 各 job 設定：未核。

### answer-eval-and-probe.md
- 全檔依賴 repo 外 `~/jgb-archive/eval-harness/`、`xp-spike.txt`：D1 驗收範圍，D5 不核。

## 交叉說明
- 其他 compose 檔、`docs/`、`.claude/MAP.md` 不在本切片範圍。`docs/architecture-overview.md` 仍寫「15 個 face」，與本次更正的 16 不一致，留給 D5 的 docs 部分處理（本切片不得編輯）。
- 所有 steering 檔中 `knowledge_completion_loop`、`/api/v1/message` 的剩餘命中（`grep -rn "knowledge_completion_loop\|/api/v1/message\|dialogue-logic" .kiro/steering`）：product.md、testing-code.md、structure.md、ai-usage.md、tech.md 的句子皆標明「只剩…／已刪／已退役」；structure.md 的 `knowledge_completion_loops`（尾端有 s）是仍存在的資料表名，非退役機制。`dialogue-logic` 在 steering 零命中。
