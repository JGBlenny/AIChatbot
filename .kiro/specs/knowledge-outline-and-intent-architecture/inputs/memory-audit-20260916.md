# 記憶健檢 2026-09-16（唯讀；裁決權在業主）

- 受審：`~/.claude/projects/-Users-chenqinghuang-dev-work-AIChatbot/memory/*.md` 106 份＋索引 `MEMORY.md`（`snapshots/` 不審）。
- 尺：`~/.claude/CLAUDE.md`「Memory Hygiene」兩道濾網——①三個月後仍成立、②四類正面清單（①為什麼這樣決定 ②試過什麼且失敗 ③看起來錯但其實對 ④外部系統與線上觀察）；機制／路由／檔名／欄位／行號不記；已修 bug／進度／下一步不記。
- 現況核對基準（影響大半 project 類判定）：**舊 REST 對話鏈已於 2026-09-11 全數刪除**（DSP-046，commit `7c905408`）——`services/chat.py`／`conversational_engine.py`／`llm_answer_optimizer.py`／`form_manager.py`／`sop_trigger_handler.py`／`api_call_handler.py`／`responsibility.py` 皆不存在；活線只剩 `services/agent/**`＋`/mcp`。`retrieval-decision-layer` 已封存（`.kiro/specs/archive/`，2026-09-01）。`.kiro/specs/{kb-coverage-completion,option-routing,category-multi-select,unit-coverage-rebuild}` 不存在。
- 判定形狀：**delete**＝只剩已修 bug／進度／機制，或被後續裁決取代且無「試過失敗」價值；**trim**＝教訓成立但夾死符號、死路徑、快照數字或進度；**keep**＝整檔靠四類之一站得住。

## 一、feedback 類（49）

| 檔 | 類型 | 判定 | 理由（四類之一或不屬） |
|---|---|---|---|
| feedback_agent_brief_no_git_stash | feedback | keep | ②實際發生的越界（stash -u 掃走別窗未提交檔）＋①brief 樣板固定段的理由。 |
| feedback_agent_brief_secrets | feedback | keep | ②金鑰明文進 transcript 的實案＋①「沒禁止的事代理會用最省事的方式做」的邊界原則。 |
| feedback_business_types_vs_target_user | feedback | keep | ①兩軸獨立的設計理由；`vendor_knowledge_retriever_v2.py` 仍以 business_types／target_user 兩軸過濾（D-002）。 |
| feedback_business_types | feedback | keep | ①業態欄位語義定案（system_provider＝b2b 池），與 D-002 同源。 |
| feedback_careful_actions | feedback | keep | ①業主偏好（破壞性操作只做明示範圍），多次糾正的定案。 |
| feedback_close_gaps_dont_wait | feedback | keep | ①事實缺口／決策缺口二分＋三次同型教訓；引用的 `outline-curation/scripts/source_audit.py` 仍在。 |
| feedback_commit_discipline | feedback | keep | ①業主偏好（中間結論不蓋章）。 |
| feedback_contract_keys_must_be_generic | feedback | keep | ①三布林被否決、改 `outcome` 八態的理由（DSP-043 在 DECISIONS.md 可核）。 |
| feedback_define_criteria_first | feedback | keep | ②三輪改判準的失敗＋①先定標準。 |
| feedback_define_object_under_test_first | feedback | keep | ①業主 2026-09-06 裁（受測物清單）＋②九輪回歸量錯對象的實案。 |
| feedback_deliverable_self_audit | feedback | keep | ②連續四輪被抓缺漏的實案＋①自稽核流程。 |
| feedback_deploy_correlation_first | feedback | keep | ②誤判 ELB 的歧路＋①部署時間相關性優先；是 project_admin_login_bounce 的耐久版。 |
| feedback_derive_from_code_not_docs | feedback | keep | ②六輪盤查仍寫錯入口的實案＋①反向推導原則；三層根因是可遷移的方法論。 |
| feedback_design_from_spec_and_code_not_memory | feedback | keep | ①業主 2026-09-16 糾正（三欄表）＋舊名用語病灶；`build_audience_outline`／`_STATIC_TOC_IDENTITY` 仍在程式中，警示有效。 |
| feedback_design_not_delivery | feedback | keep | ①業主偏好（設計題答目標形態）＋自診根因。 |
| feedback_dropped_means_dropped | feedback | keep | ①業主偏好（否決即定案）。 |
| feedback_embedding_integrity | feedback | keep | ③「補 keywords 會稀釋向量，一種講法一筆錨點才對」的實測（0.785→0.684）；question_summary 單一輸入仍是現行檢索契約。 |
| feedback_explain_mechanism_from_code_and_live_config | feedback | keep | ②講錯轉人機制的實案；`_wrap_verifier_observe_only`／`AGENT_VERIFIER_OBSERVE_ONLY` 仍在 `services/agent/`。 |
| feedback_false_green_verification | feedback | keep | ②integration 靜默略過、白名單漏檔、同步單檔炸相依三件實案＋③「零實跑判失敗」；數字（199／199）可留作正對照示例。 |
| feedback_hypothesis_driven_verification | feedback | keep | ①業主 2026-09-06 裁（命題／材料／推翻條件）。 |
| feedback_independent_verification | feedback | keep | ①業主明令（派代理、逐功能關卡）＋②量尺被打穿、換瞎尺兩次實證；長但每條都是裁決或失敗。 |
| feedback_investigate_before_asking | feedback | keep | ①業主偏好；根因案例仍成立。 |
| feedback_jgb_response_format | feedback | keep | ①明確場景 template、模糊才 LLM；與現行「formatter facts→LLM 組話」形狀一致（`_FACE_BUILDERS`）。內容薄，可考慮併入 feedback_no_llm_mechanical_decode。 |
| feedback_jgb_separate_file | feedback | trim | ①原則（JGB 邏輯獨立目錄）仍成立且 `services/jgb/` 已是現況，但點名的 `api_call_handler.py`／`jgb_response_formatter.py` 均已刪（DSP-046）——改寫成「放 `services/jgb/`」一句即可。 |
| feedback_kb_answer_quality | feedback | keep | ①知識 answer 寫法定案（兩次被退的理由）。 |
| feedback_kb_generation_method | feedback | keep | ②loop 190 失敗＋④UI 文案／值域／master 分支三個查證成本高的外部坑。 |
| feedback_kb_question_style | feedback | trim | ①question 短關鍵字定案（含 78%→94% 實測）keep；但「檢索機制事實」節有一條已失實：「主檢索器不做 target_user 過濾」——2026-06-20 起 b2b 已重啟 target_user 過濾（`tests/unit/retrieval/test_retriever_sql_filter_req.py` 斷言「b2b 嚴格 business_types＋target_user」），砍該句；0.1／0.9 權重與 keywords 不入 rerank 分支仍對（`base_retriever._finalize_scores`）。 |
| feedback_loop_cleanup | feedback | keep | ①清迴圈保留知識的裁決；`services/knowledge_completion_loop/` 仍在。 |
| feedback_measure_at_user_layer | feedback | trim | ①②療效只在使用者層量、自寫 SQL 差 70% 召回（`ORDER BY (1 -` 仍在 `base_retriever.py`）keep；但「正式入口 `POST /api/v1/message`」已於 2026-09-11 退役，現行入口是 `/mcp` `agent.turn`——改寫入口名，原則不變。 |
| feedback_multi_window_ownership | feedback | keep | ②兩次撞車實案＋①業主糾正。「2026-09-04 定案：M0 歸另一視窗」一句是當時分工，可刪。 |
| feedback_no_commit_kiro | feedback | keep | ①改判理由（不可逆性不對稱）。 |
| feedback_no_commit_scripts | feedback | keep | ①業主偏好。 |
| feedback_no_deploy_scripts | feedback | keep | ①業主偏好與理由。 |
| feedback_no_llm_mechanical_decode | feedback | trim | ②LLM 解碼三雷實測＋①facts 由程式算 keep；但 `_ground_by_api`、`base 系統脈絡` 隨舊鏈刪除，`/Users/chenqinghuang/dev/work/jgb2/master/app/Contract.php` 路徑不存在（現用 `git -C …/jgb2/dev2 show master:app/Contract.php`）——砍死符號、換路徑。 |
| feedback_no_push | feedback | keep | ①業主偏好。 |
| feedback_no_secret_in_argv | feedback | keep | ③「指令旁註明不放 argv」看起來對其實錯＋①三分法判讀。 |
| feedback_no_special_case_fixes | feedback | keep | ①業主 2026-09-05 裁＋②提示詞加例句反而讓 mini 放棄的實測。 |
| feedback_presales_knowledge_first | feedback | keep | ①業主 2026-09-04 裁（先補知識、⛔ 補完前不重提）；`PRESALES_EXTRACTIVE` 仍在 `presales_gate.py`。wiki 連結 `[[presales-grounding-gate-lessons]]` 對不到檔（應為 `project_presales_grounding_gate`）。 |
| feedback_prod_ops_self_run | feedback | keep | ①業主偏好（線上不代執行、部署不排進流程）。 |
| feedback_query_category_design | feedback | delete | 決策對象 `query_category`（form_action／api_data_query…）在現行 `app.py`／`services`／`routers` 0 命中（正對照：同法查 `build_visibility_predicate` 11 檔命中）——舊鏈概念隨 DSP-046 消失；「應用層推導不加 DB 欄位」的通則已無承載物。 |
| feedback_root_cause | feedback | keep | ①業主偏好。 |
| feedback_rule_vs_layer | feedback | keep | ②四輪規則淨貢獻 0 的實案＋①封閉／開放集合判準與錯誤方向可回復性。 |
| feedback_scenario_backtest_gate | feedback | keep | ①業主裁（收案必情境回測）＋②兩次假通過。wiki 連結 `[[assistant-report-workflow]]` 對不到記憶檔（它指的是 `docs/backtest/assistant-report-workflow.md`，該檔存在）。 |
| feedback_stale_container_invalidates_backtest | feedback | keep | ④本機兩個 rag-orchestrator 跑不同碼（prod compose 無 mount／dev compose 有 mount）＋②結論全數作廢的實案。 |
| feedback_surface_tradeoffs | feedback | keep | ①業主偏好。 |
| feedback_three_ways_to_count_usage | feedback | keep | ②同日兩次數錯＋③三種數法各有盲區；例子中的 `tools/audit_config.py` 已不存在，但只作案例引用、不影響結論。 |
| feedback_verifier_agent_delivery | feedback | keep | ④代理交不出件的兩種形態與判活法；引用的 retrieval-decision-layer R9.1.1 已封存，僅作出處。 |
| feedback_verify_before_advancing | feedback | keep | ①業主多次糾正＋②三種簡化驗證被戳破。 |
| feedback_verify_endpoint_at_protocol_level | feedback | keep | ④nginx 改寫害 /mcp 404 卻回 401 的線上觀察＋①協定層驗證。 |

## 二、project 類（45）

| 檔 | 類型 | 判定 | 理由（四類之一或不屬） |
|---|---|---|---|
| project_admin_login_bounce | project | delete | 只記已修 bug（根因＋修法＋改動檔）；修法本身 grep 得到（`knowledge-admin/frontend/nginx.conf.template` 的 `auth_request`）；唯一耐久教訓「部署相關性優先」已獨立成 feedback_deploy_correlation_first。 |
| project_assistant_report_batch_20260731 | project | trim | 大半是已修案號、commit 與遺留待辦（T-1／B-1 的 `chat.py`、`_diagnosis_config_for_knowledge` 已隨舊鏈刪除）。留三句：④jgb2 `Bill::canCancel`＝已發送應到帳可收回；①修知識必同步掃決定性解碼器（`services/jgb/bills.py::_diagnose_cannot_cancel` 仍在）；③同檔 INSERT＋UPDATE 改名在已套環境會產生重複列。 |
| project_audit_system | project | trim | ②negative control 教訓（守門恆 False）與①「修一類 bug＝加一條不變量」keep；但「四不變量」已失實——`scripts/audit/check_invariants.sh` 現有不變量 1–12、14 共 13 條；「8 個關鍵檔 md5」也已改整目錄 digest（見 feedback_false_green_verification）。砍數字與清單。 |
| project_backtest_modernization_gap | project | trim | 全檔是 2026-07 回測數字快照與已修 harness bug，受測物是已退役的 `/api/v1/message` 鏈。只留③「⛔ 62.8% 查無來源不得引用；69.7% 唯一出處 `scripts/audit/reports/regrade291-triage.md` 且母體非 production holdout」。 |
| project_brain_kb_grounding_spec | project | delete | 實作對象 `conversational_step`／`_brain_tool_loop`／`SEARCH_KB_ENABLED` 隨 `llm_answer_optimizer.py` 刪除（src 0 命中；`search_kb` 僅剩 `usage_metering.py` 的計量欄）；「憑印象會幻覺」的證據仍在 `.kiro/specs/brain-kb-grounding/kb-comparison-r63.md`，通則已由 agent 線的 kb 工具制度化。 |
| project_category_dual_column | project | trim | ①「單數 category 只當角色標記、主題走 categories、兩欄不進 embedding」是決策 keep；其餘（`= ANY`／`unnest`、admin 前後端改用、parent_value 兩層）是 grep 得到的機制，且 spec `category-multi-select` 目錄已不存在。 |
| project_chatflow_retrieval_session | project | keep | ②「查過判定不改」四條（#6 已升為 D-002；#2 no-op 在 `services/decision_layer.py` docstring 仍可核）；留檔避免重做分析。`rag_engine.py` 已刪一句可去。 |
| project_conversation_first_assessment | project | delete | 2026-07-10 對舊鏈的骨架 C／P0–P3 遷移定案，已被 2026-09 agentic-MCP 全面取代（DSP-046 砍掉整條舊鏈）；`docs/conversation-first-architecture-assessment.md` 仍在，歷史查該檔即可；無「試過失敗」價值（是被架構更替淘汰，不是失敗）。 |
| project_conversation_retrieval_resilience | project | trim | ②五條「為什麼失敗」＋①重來要件 keep；「現狀（終局）」節全是 git 暫態（reset 到 cca0146、超前 13 顆、DB 殘留 migration）——砍掉，只留封存分支名。 |
| project_conversational_diagnosis_session | project | delete | 舊鏈實作紀錄（`_ground_by_api`、`chat.py` 出口、role_id 貫通已修、e2e 指令指向已不存在的 `tests/e2e/conversational/`）；耐久的「formatter 算 facts、LLM 組話」已在 feedback_no_llm_mechanical_decode；「integration 不進 CI 才會爛」已在 project_testing_traceability。 |
| project_conversational_facets_domains | project | trim | 合約／帳務／帳號／IoT／物件五域的 jgb2 外部事實（滯納金兩機制、台科電＝DAE、兩軸模型、estates 硬過濾 is_open）是④，keep；但「跨域陷阱」節四條全綁舊引擎（`grounding_scope` fallback `persona_role`、`conversational_engine` 0-row 短路、`_extract_identifier` 0 命中、`jgb_estates` 只剩 seed SQL）與「測試環境陷阱」的 e2e 套件已刪——砍這兩節。 |
| project_conversational_repair_session | project | trim | 舊引擎交易語義／配置鍵契約／扁平槽位鐵則已隨 `conversational_engine.py` 刪除；留④jgb2 `emergency_status` 語義反轉（`RepairController` 仍 `=== Repair::EMERGENCY_STATUS`，我方 `emergency_status` 10 檔仍在用）、④`/contracts/status-overview` 缺 `room_number`、①改共用 helper 收案必含既有面向 e2e。 |
| project_deploy_semantic_model | project | keep | ④2026-06-21 線上不同步實證＋③「只加知識不需重建 reranker（`/rerank` stateless）」的界定；`scripts/clear_vendor_cache.py` 仍在。 |
| project_domain_conversational_facets | project | trim | 大半是舊引擎與 admin 頁實作（`conversational_step`、optimizer 合成點、`_synth_context`、nginx `set` 陷阱）。留①「識別＝API 驗證式：先搜後提交、後端筆數當裁判、退掉語意 guard」與①「answer_rules 歸屬三度搬家的定案（共用 optimizer→面向脈絡→對話設定）」（`answer_rules`／`cta_rules`／`search_params` 仍在 `services/conversational_config.py`，agent 線 `turn_context.py` 等有引用）。 |
| project_entry_alias_vs_responsibility | project | keep | ①業主 2026-08-29 裁（entry identity 與 responsibility identity 分開）＋③「別套 3498 退役先例」；`entry-alias-registry.json` 仍在。 |
| project_facet_capability_selection_gap | project | keep | ③曾誤判「候選列表查無實作」的反例＋②正對照層級錯的教訓；`face_bill_response`／`result_mapping`／`candidate_cap` 仍在 src。 |
| project_holdout_scope_discipline | project | keep | ①業主裁（看過分布再改 scope＝依結果改 scope）。metadata 標 feedback 但檔名 project，無妨。 |
| project_jgb_api_integration | project | delete | 描述舊鏈「知識→表單→`api_call_handler`→JGBSystemAPI」整條路（已刪）；接續指引指向不存在的 `.kiro/specs/kb-coverage-completion/tasks.md`；jgb2 external API 事實由 `.claude/MAP.md#jgb2-chat-integration` 與 reference 類承接。 |
| project_jgb_audit_20260706 | project | trim | 60 題三輪百分比、commit、掛帳清單皆是進度快照。留④jgb2 繳費週期是 6 種月計（非 7 種週計）、④「信用卡失敗重試 3 次」全庫查無屬杜撰、①範疇外題維持誠實查無不補導引。 |
| project_jgb_product_context | project | trim | ④沒有 APP、AI 客服內嵌 Web 平台＋①IoT 是 B 端基本盤 keep；「未來才會開放 LINE」已過時——LINE OA 已是 `/mcp` demo 場景（MAP `#agentic-mcp`、DSP-042），改寫該句。 |
| project_jgb_system_knowledge | project | trim | ①知識分層、②embedding 不升級（<1%）、③B2B 池隔離非 bug、③泛詞命名吸走整族 keep；「SOP TriggerMode 只有 MANUAL／IMMEDIATE」綁已刪的 `sop_trigger_handler.py`（src 0 命中），砍。 |
| project_kb_updated_at_trigger_trap | project | keep | ③任何 kb UPDATE 撞 `update_kb_updated_at` 觸發不變量 10（trigger 仍被 `tests/integration/agent/test_visible_subset_sql_equiv_req.py` 引用）＋④售前池是 b2b 謂詞（`build_visibility_predicate` 仍在）。 |
| project_line_bot_plan | project | delete | 2026-07-10 為舊鏈設計的 LINE 三層觸發／表單直達；`docs/line-bot-integration-plan.md` 已移 `docs/archive/`；LINE 線現走 `/mcp`（DSP-042／043），舊規劃無「試過失敗」價值。 |
| project_llm_rewrite_deletes_injected_params | project | keep | ②舊鏈階段 2 因刪參數而永久停用＋③別在 facts 成文後再潤飾；出處已註明是刪檔前撈出。 |
| project_migration_convergence | project | keep | ①兩套 migration 收斂的裁決與判準；`database/migrations-legacy/DEPRECATED.md`、`database/run_migrations.sh` 閘仍在。「dev 帳本已套 83 筆」一句可去。 |
| project_mini_delegation_design | project | trim | ①②「模型判語義／契約解唯一目標／strict schema 管形狀、沒填≠填錯」是兩次實測推出的分工，通則仍適用 agent 線（`output_schema.py`）；但 `contract_singleton`／`model_delegate`／`delegate_facet_key` 在 src 0 命中（舊路由 brain 已刪）——砍符號名與 telemetry 一句，留分工表與兩個失敗。 |
| project_nli_premise_shape_must_match_production | project | keep | ②量尺輸入形狀不對齊線上的實測（1/3→0/3）；NLI 已依 DSP-034 全面撤出，但「canary 形狀必須對齊線上」的教訓與尺無關。可加一句「NLI 已撤出（DSP-034）」。 |
| project_nli_replacement_failed_frozen_constraints | project | keep | ②典型「試過且失敗」：換模型／串前提／組合尺皆碰同一天花板；DSP-034 撤出可補註。 |
| project_outline_catalog_not_chunks | project | keep | ①業主 2026-09-06／09-15 定案（目錄式、九架單一正本 DSP-058）＋②受眾分檔走過又廢；`canon/jgb/A.md…I.md`＋`CATALOG.md` 與 DSP-058 可核。 |
| project_pending_question_missing_column | project | delete | 只記已修 bug（欄位補上、dev/prod 已套）；消費端 `form_manager.py` 已刪，`pending_question` 現只剩 ledger SQL；wiki 連結 `[[project_form_prompt_bug]]` 指向不存在的檔。 |
| project_presales_grounding_gate | project | keep | ②四輪 e2e 三條教訓（每個自由文字欄位都是捏造出口、門檻治不了講法缺口）；`presales_gate.analyze_ask`／`PRESALES_EXTRACTIVE` 仍在，agent 線多檔引用。 |
| project_presales_target_user_routing | project | trim | ①用 target_user 區分 prospect、不寫特例（2026-06-20 裁）keep；但實作段落帶行號（`retriever_v2.py:63`）、已刪的 `rag_engine.py`、`VendorChatDemo.vue` 前端陷阱、option-routing 任務編號皆過時——砍到只剩決策＋「b2b＋無 role_id＝prospect」判準。 |
| project_retrieval_decision_layer | project | trim | ②三條缺陷模式（概念沒落成資料／證據引用丟限制／及格線在被驗方）是跨 spec 通則 keep；「現行狀態查 `.kiro/specs/retrieval-decision-layer/README.md`」已失效——該 spec 2026-09-01 封存至 `.kiro/specs/archive/`，改路徑或刪該句。 |
| project_retrieval_ranking_findings | project | keep | ④reranker 靜默永久停用且三個健檢看不出（修法已在 `semantic_reranker.py`：`_recheck_sec` 60 秒重探）＋③0.1／0.9 是「reranker 說了算」（`_finalize_scores` 仍如此）＋④客服回報 80% 是知識題。「線上需重 build image」一句是當時狀態，可去。 |
| project_retrieval_representation_contract | project | keep | ①業主 D1/D2/D3 裁（general 對齊 answer、instance 對齊 capability、不得補造 truth）；`services/retrieval_representation.py`＋不變量 12 可核。 |
| project_retrieval_robustness_spec_candidate | project | delete | 自述「本檔不含任何有效待辦」，且指定的接手 spec `retrieval-decision-layer` 也已封存；E-2／E-3 病灶綁舊面向引擎；證據正本在 `docs/backtest/assistant-report-regression.md` 與 `docs/research/conversation-retrieval-resilience-research.md`。 |
| project_retrieval_test_coverage | project | trim | 「哪些測試測什麼」是 grep 得到的機制（且路徑已搬到 `tests/unit/retrieval/`）；留③弱斷言陷阱（`in sql` 需反向斷言）與②mutation 檢查法；「最後一哩缺口：CI 未跑 integration」已失實（`.github/workflows/tests.yml` 有 `integration` job、`RUN_INTEGRATION: "1"`）。 |
| project_retriever_debug_bypass_keep | project | keep | ③零呼叫端但不得刪（`return_unfiltered`／`unfiltered_sink` 仍在 `base_retriever.py`／`retriever_v2.py`，`量測管線自證.md` 明文要求）。 |
| project_role_trust_boundary | project | keep | ①業主 2026-08-31／09-04（DSP-011）裁：不驗 role、⛔ 別補 middleware；`api_key_guard`／`quota_check`／`F-C25` 仍在 src。 |
| project_routing_baseline_drift | project | trim | ②真根因「關鍵字加成飽和塌陷」（`keyword_boost`＋`min(1.0, …)` cap 仍在 `_finalize_scores`）與①「categories／keywords 衛生是路由一部分」keep；13 failed→83/83、`test_facet_entry_routing_req.py`（已刪）、migration 檔名等收案進度砍。 |
| project_sop_role_isolation_gap | project | delete | SOP 檢索在新線無承接對象（DSP-046 明列「真正失去的能力」），「b2b 不走 SOP」的 `chat.py:1633` 已刪；撤案理由（harness 未帶 mode）已在 spec 目錄留檔，且被 feedback_stale_container… 同型教訓涵蓋。 |
| project_testing_traceability | project | trim | ④host 3.9 收集失敗、④integration 套件非決定性（同碼三跑 7/6/5）＋①換量尺不加跑次 keep；舉例的 `test_facet_entry_routing_req.py` 已刪，改寫成通則；ratchet 路徑 `rag-orchestrator/tools/coverage/check_baseline.py` 仍在。 |
| project_top1_gate_authority | project | trim | ①裁定 001（gate 只管直答、technical fail-open≠model stay）是決策，正本 `.kiro/specs/routing-authority-model/responsibility-governance-decision-record.md` 仍在；但承載符號 `_top1_relevance_gate`／`has_commit_authority`／`decision_source`／`services/responsibility.py` 全部 0 命中（舊鏈刪除），「終局」節六筆 commit 與 canary 射程是進度——砍到只留裁定與越權判準。 |
| project_trigger_vocabulary_debt | project | delete | P0（retriever 缺欄）已修（`test_trigger_config_passthrough_req.py` 鎖住）、P1 死欄位與 P2 門檻皆綁已刪的 `chat.py`／SOP 觸發；spec 目錄 `.kiro/specs/trigger-vocabulary-debt/` 留史即可。 |
| project_usage_quota | project | trim | 大半是機制（欄位、端點、快取秒數，`services/usage_metering.py`＋不變量 5/6 grep 得到）；留①「警示改寄信不進對話」與①「額度按訊息計（多輪 4 輪扣 4）」兩條裁決。 |

## 三、reference 類（12）

| 檔 | 類型 | 判定 | 理由（四類之一或不屬） |
|---|---|---|---|
| reference_assistant_reports_s3 | reference | trim | ④S3 路徑、寫入端、「回報≠報修」keep；「已知橫向問題」兩條（`{{servicehotline}}` 已修、RAG 搶答屬舊鏈）與 xlsx 本機位置砍。 |
| reference_canon_finishgate_traps | reference | keep | ④全域無 git 工具的兩個坑，`read_textual` 仍在 `~/.claude/canon/refcheck.py`（4 處）。 |
| reference_canon_token_ratio | reference | trim | ④1.1 字元/token、210 條時 10,896>8,000 的實測 keep；「DSP-059（spec 起草中）」是進度詞且 DECISIONS.md 尚無 DSP-059——改成「歸 DSP-059 裁」不寫狀態。 |
| reference_docker_desktop_vm_hang | reference | keep | ④本機 Docker VM 掛死處置與延遲慢 3–4 倍的觀察。 |
| reference_jgb_test_team_role | reference | keep | ④www role 20151 是測試團隊（業主裁）＋③`get_bills` 缺參數的 401 是本地 `_degraded_response`（仍在 src）。 |
| reference_jgb2_checkouts | reference | keep | ④四份 checkout 哪份可信（`dev2` 存在、`preview` 分支、本地有 `master` ref 已核）＋④preview 落後 production。 |
| reference_jgb2_contract_architecture | reference | trim | ④12 常數／status vs bit_status／違約金 type 仍與 `dev2 master:app/Contract.php` 一致；但開頭路徑 `/Users/chenqinghuang/dev/work/jgb2/interrogation` 不存在——改指 reference_jgb2_checkouts 的 dev2。 |
| reference_presales_kb_source | reference | keep | ④原稿路徑失效、git 歷史查無（含正對照）、現存唯一正本＝kb 29 列；本身已是「實況矛盾後改寫成終局」的形態，dispute 待業主。 |
| reference_prod_server_compose_binary | reference | keep | ④正式機只有 `docker-compose`、ec2-user、`migration_name` 欄。 |
| reference_smoke_rag_hot_swap_traps | reference | keep | ③健檢說的模式≠實例的模式＋④三個熱換坑（`confirm_card.py`、`AGENT_VERIFIER_MODE`、fixtures 自檢皆仍在）。 |
| reference_vendors_current | reference | trim | ①業者名單一律查 DB keep；但 `database/init/06-vendors-and-configs.sql` 已不存在（`database/init/` 為空），「seed 是舊資料」的陷阱對象消失；2026-07-11 的 4 業者與 SOP 分佈是快照、「疑似線上 bug」綁舊 `form_manager.py`——砍到一句。 |
| reference_workflow_tool_8gb_limit | reference | keep | ④本機資源極限與成本結構（cache write 主導）。 |

## 四、統計

| 判定 | feedback | project | reference | 合計 |
|---|---|---|---|---|
| keep | 44 | 16 | 8 | **68** |
| trim | 4 | 19 | 4 | **27** |
| delete | 1 | 10 | 0 | **11** |
| 合計 | 49 | 45 | 12 | 106 |

delete 清單（11）：feedback_query_category_design、project_admin_login_bounce、project_brain_kb_grounding_spec、project_conversation_first_assessment、project_conversational_diagnosis_session、project_jgb_api_integration、project_line_bot_plan、project_pending_question_missing_column、project_retrieval_robustness_spec_candidate、project_sop_role_isolation_gap、project_trigger_vocabulary_debt。共同形狀：十份中九份的承載程式在 2026-09-11 舊鏈刪除時消失，且沒有獨立於該鏈的「試過失敗」價值。

## 五、索引 `MEMORY.md` 與檔案內容不一致清單

雙向對帳：索引 106 行 ↔ 106 檔**一對一、無孤兒、無死連結**（`python3` 正則對帳，正對照＝全部命中）。以下是 hook 文字與檔案內容／現況對不上的行：

| 索引行 | 不一致點 |
|---|---|
| `[不變量稽核體系](project_audit_system.md) — make audit 四不變量` | 檔與 hook 都寫「四」，`scripts/audit/check_invariants.sh` 現為 13 條（1–12、14）。 |
| `[檢索韌性 spec 候選](project_retrieval_robustness_spec_candidate.md) — …由 retrieval-decision-layer 取代` | 接手 spec 已於 2026-09-01 封存（`.kiro/specs/archive/retrieval-decision-layer/`），hook 指向已停線。 |
| `[JGB API 整合](project_jgb_api_integration.md) — 知識/表單/API/格式化持續擴充的整合現況` | 「現況」全是已刪舊鏈（`api_call_handler`、表單→API）；hook 把歷史寫成現況。 |
| `[pending_question 欄位缺失](project_pending_question_missing_column.md) — 曾致離題續答失效，dev/prod 皆已套` | hook 本身即「已修 bug＋狀態」；檔內連結 `[[project_form_prompt_bug]]` 無此檔。 |
| `[對話優先架構評估](project_conversation_first_assessment.md) — 定案混合骨架 C、遷移 P0-P3` | 定案已被 DSP-046（砍舊鏈、只剩 agentic-MCP）取代，hook 未標「已被取代」。 |
| `[LINE bot 串接規劃](project_line_bot_plan.md) — 三層觸發定案…E1 真 API 是上線 gate` | LINE 現走 `/mcp`（DSP-042／043），三層觸發綁已刪 SOP／表單機制；hook 未標歷史。 |
| `[brain-kb-grounding](project_brain_kb_grounding_spec.md) — Brain 掛 search_kb` | Brain（`conversational_step`）已刪，`search_kb` src 僅剩計量欄。 |
| `[觸發語彙債](project_trigger_vocabulary_debt.md) — 知識層觸發配置曾半失效` | P0 已修、其餘綁已刪 `chat.py`；hook 仍是立案語氣。 |
| `[top1 gate 權限裁定](project_top1_gate_authority.md) — gate 只管直接回答` | 裁定成立，但 `_top1_relevance_gate`／`has_commit_authority` 已不存在；hook 讀來像現行機制。 |
| `[mini 委派分工定案](project_mini_delegation_design.md) — …契約解唯一目標` | `contract_singleton`／`delegate_facet_key` src 0 命中；分工通則成立、符號已死。 |
| `[領域化對話面向](project_domain_conversational_facets.md) — 面向化三層系統脈絡＋候選辨識＋中途切換` | 三層脈絡與中途切換綁已刪 `conversational_engine`；hook 描述死機制。 |
| `[對話式合約診斷](project_conversational_diagnosis_session.md)`、`[對話式修繕](project_conversational_repair_session.md) — 引擎交易語義＋配置鍵契約` | 兩者引擎已刪；修繕 hook 裡只有「emergency_status 語義反轉」仍成立。 |
| `[SOP 角色隔離改判撤案](project_sop_role_isolation_gap.md) — …b2b 不走 SOP` | 現況是「整條線都不走 SOP」（DSP-046 SOP 檢索無承接），hook 的 b2b/b2c 對比已無意義。 |
| `[業者現況查 DB](reference_vendors_current.md) — init seed 是舊資料勿引` | `database/init/` 已空，seed 檔不存在。 |
| `[療效只在使用者那層量](feedback_measure_at_user_layer.md)` | hook 無誤，但檔內「正式入口 `POST /api/v1/message`」已退役（現 `/mcp`）。 |
| `[KB question 用主題關鍵字](feedback_kb_question_style.md)` | hook 無誤，但檔內「主檢索器不做 target_user 過濾」與現行 b2b 過濾（D-002＋`test_retriever_sql_filter_req.py`）矛盾。 |
| `[jgb2 合約架構 ground-truth](reference_jgb2_contract_architecture.md)` | hook 無誤，檔內路徑 `jgb2/interrogation` 不存在。 |

另：三個 wiki 連結對不到檔（不在索引、在檔內）：`feedback_presales_knowledge_first`→`[[presales-grounding-gate-lessons]]`；`feedback_scenario_backtest_gate`→`[[assistant-report-workflow]]`（指 docs 檔）；`project_pending_question_missing_column`→`[[project_form_prompt_bug]]`。

## 六、查證指令（可重跑）

```bash
# 舊鏈刪除與封存的事實
git log -1 --format='%h %ad %s' --date=short 7c905408
grep -E '^\| DSP-046 \|' .claude/DECISIONS.md | cut -c1-400
ls .kiro/specs/archive/
# 死檔／死符號（正對照：base_retriever.py 存在、build_visibility_predicate 11 檔命中）
ls rag-orchestrator/services/{chat,conversational_engine,llm_answer_optimizer,form_manager,sop_trigger_handler,api_call_handler,responsibility}.py
cd rag-orchestrator && for s in _top1_relevance_gate has_commit_authority contract_singleton query_category SEARCH_KB_ENABLED TriggerMode _extract_identifier build_visibility_predicate; do echo "$s $(grep -rl -F "$s" app.py services routers | wc -l)"; done
# 仍活著的承載物
grep -n '_recheck_sec' rag-orchestrator/services/semantic_reranker.py
grep -n '0.9 × rerank_score' rag-orchestrator/services/base_retriever.py
grep -rl -F return_unfiltered rag-orchestrator/services
grep -n '不變量 [0-9]*：' scripts/audit/check_invariants.sh | wc -l
grep -nE '^  (unit|integration):' .github/workflows/tests.yml
# 外部事實正對照
git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show master:app/Contract.php | grep -c 'const CONTRACT_'
ls /Users/chenqinghuang/dev/work/jgb2/dev2/docs/presales-kb   # 預期不存在
ls database/init/                                             # 預期為空
grep -c read_textual ~/.claude/canon/refcheck.py
```
