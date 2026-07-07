# 實作任務：conversational-diagnosis（對話式診斷框架，合約為首案）

> 建立時間：2026-06-30
> 需求：requirements.md（R1–R8）｜設計：design.md（v1.1）｜落差：gap-analysis.md
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後的測試覆蓋子任務
> 鐵律：TDD（先紅後綠）；通用性硬約束（程式不得出現合約欄位/端點硬編，一律讀設定）；售前不回歸

## 1. 依分類查設定（config_for_category + by_category 索引）

- [x] 1.1 於 `services/conversational_config.py` 新增 `by_category` 快取索引：`_load` 時遍歷設定，將 `topic_scope.mode=='category'` 且 `enabled` 者以其 `category` 值為鍵建索引；`reset_cache` 一併清除。
  - 需求：1.3, 6.2
- [x] 1.2 實作 `async config_for_category(db_pool, category) -> Optional[ConversationalConfig]`：回該分類對應之啟用對話設定，無則 None。
  - 需求：1.3
- [x] 1.3 單元測試：分類命中→回設定；未命中/未啟用/`mode!=category`→None；多面向設定各自以其分類入索引；reset 後重載。**6 passed**（+既有對話 unit 不回歸，共 29 passed）
  - 需求：1.3, 6.2

## 2. 設定驅動收斂門檻（_has_basic_info）

- [x] 2.1 改 `conversational_engine.py::_has_basic_info(fields, config)`：有 `grounding_scope.required_slots` → 全部到齊才足夠；無 → 維持售前預設（identity/scale/pain）。`prepare`（行約 134）呼叫點補傳 `config`。
  - 需求：2.1, 2.5, 6.1
- [x] 2.2 單元測試：設 required_slots 未齊→不足（續追問）；齊→足夠；無 required_slots→沿用售前預設行為不變。**6 passed**（+對話 unit 不回歸，共 35 passed）
  - 需求：2.1, 2.5

## 3. 引擎注入 api_handler

- [x] 3.1 `ConversationalEngine.__init__` 新增 `api_handler` 參數並保存（可選預設 None，向後相容）；`app.py` 實例化處以 `get_api_call_handler(db_pool)` 注入。不改 api_call_handler。**2 passed**
  - 需求：3.1, 7.3
- [x] 3.2 啟動煙霧驗證：`import app` 成功（app.py 注入行不報錯）；對話 unit 共 **37 passed** 不回歸（既有 5 參數 stub 仍可建構）。
  - 需求：7.1, 7.3

## 4. API grounding（_ground_by_api，重用 execute_api_call + result_mapping）

- [x] 4.1 實作 `async _ground_by_api(state, config) -> ApiGroundingResult`：組 `session_data`(role_id/vendor_id/session_id/user_id) + `form_data=collected_fields` → 呼叫 `api_handler.execute_api_call(api_config, session_data, form_data)`；依 `grounding_scope.result_mapping.list_path` 取資料列判筆數。**清單路徑/id/label/refine 欄位一律讀 `result_mapping`，不得硬編合約欄位。** api_config 的 endpoint/params 讀 `grounding_scope`。**5 passed**（輸入組裝/重用 execute_api_call/設定驅動 endpoint+mapping/1·0·N 三路；+對話 unit 不回歸，共 42 passed）
  - 需求：3.1, 3.2, 3.3, 6.1, 6.3
- [x] 4.2 三路結果：1 筆→`{kind:converge, grounding}`（以 result_mapping 欄位 + formatted_response 組文字）；0 筆→`{kind:ask}`（查無、重問識別）；N 筆→`{kind:ask, candidates:[{id,label}]}`（依 result_mapping 取 id/label）；API 例外/逾時→安全 `{kind:ask}`（不拋出）。**5 passed**（1筆 label+formatted_response 組文字、0筆重問、N筆候選、例外/失敗安全 ask；+對話 unit 不回歸，共 47 passed）
  - 需求：3.4, 3.5, 3.6
- [x] 4.3 單元測試（mock api_handler）：1/0/N/例外四路正確；參數映射 slot 經 form_data 通道（`{form.contract_ref|if_numeric/if_text}`）正確解析；result_mapping 取欄位無合約硬編。**3 passed**（以真實 APICallHandler 驗 slot→form_data→`_resolve_param_value`：數字→contract_ids、文字→keyword、role_id 走 session_data；四路/零硬編已由 4.1+4.2 測試覆蓋；+對話 unit 不回歸，共 50 passed）
  - 需求：3.1, 3.2, 3.4, 3.5, 3.6, 6.1

## 5. prepare 控制流（候選選擇輪 + converge 降級回 ask + 比對）

- [x] 5.1 `prepare` 插點 B：`select=='api'` 收斂時呼叫 `_ground_by_api`；回 `ask`→發 ask-decision（非 converge），有 `candidates` 則寫入 `state['pending_candidates']` 並存檔；回 `converge`→以其 grounding 合成。`select!='api'` 走既有 `_converge_grounding` 不變。**4 passed**（api converge 用 API grounding、ctx=None/cta 抑制；0筆降級 ask、N筆寫 pending_candidates 並存檔、asked_count+1 維持上限保護；非 api 走既有 grounding 不觸發 _ground_by_api；+對話 unit 不回歸，共 54 passed）
  - 需求：3.4, 3.5, 2.4
- [x] 5.2 `prepare` 插點 A（pre-LLM 候選選擇輪）：`state['pending_candidates']` 存在時，以 `_match_candidate(user_message, candidates)`（序號/label/id 確定性比對）解析選擇；命中→設 id 槽位、清候選→走單筆收斂；未命中→再次列出反問。不依賴 LLM step。**9 passed**（_match_candidate 序號/id/label/序號優先/未命中 6 筆 + 插點 A 命中設 required_slots[0]=id 並單筆收斂、label 子字串命中、未命中反問保留候選且不觸發 LLM step/_ground_by_api 3 筆；+對話 unit 不回歸，共 63 passed）
  - 需求：3.5, 2.2, 2.3
- [x] 5.3 單元測試：插點 B 三路（converge/ask/存候選）；插點 A（命中→收斂、未命中→反問）；`_match_candidate` 序號/名稱/id 比對；售前（無 pending_candidates、select≠api）不觸發兩插點。**2 passed**（售前收斂走 _converge_grounding／售前追問走 LLM ask 分支，兩情境 _ground_by_api 皆不觸發＝R7.1 不回歸；插點 B 三路、插點 A 命中/未命中、_match_candidate 已由 5.1/5.2 測試覆蓋；+對話 unit 不回歸，共 65 passed）
  - 需求：3.4, 3.5, 2.2, 2.3, 7.1

## 6. 分類路由出口（handle_retrieval 知識分支入口）

- [x] 6.1 於 `routers/chat.py::handle_retrieval` 決策為 `knowledge` 後、串流/表單分支**之前**插入：最高順位知識達 `form_trigger_threshold` 且 `config_for_category(其分類)` 命中→`return await _conversational_respond(request, req, start_if_absent=True, config=diag_cfg)`；回 None（引擎降級）或未命中→落回既有處理。實作 `_knowledge_category(best_knowledge)` 取分類（categories 多值/category 單值以實際欄位為準）。**8 passed**（_knowledge_category 多值/單值/皆無；_diagnosis_config_for_knowledge 門檻命中/未達門檻/未命中/多值第二命中/best_knowledge=None）
  - 前置：檢索 `_format_result` 補帶 `category`/`categories`（兩 SELECT 加欄位），否則知識 dict 無分類、路由永不命中（additive，不改排序）。
  - 注：handle_retrieval 內 `_conversational_respond` 串接 + 降級落回為薄接線，由 6.2 整合測試覆蓋；全層 unit 共 **181 passed** 不回歸。
  - 需求：1.1, 1.2, 1.4, 4.4, 7.2
- [x] 6.2 整合測試：分類命中→起對話（回追問、續對話會話建立、stream/非 stream 契約正確）；未命中→維持表單/直接知識；引擎降級→落回不阻斷。**4 passed**（mock 檢索決策+引擎：命中非stream→_conversational_respond(start_if_absent=True,config=diag_cfg) 且不走 _build_knowledge_response；命中 stream→同契約；未命中→落 _build_knowledge_response 不起對話；引擎降級回 None→落回知識回應不阻斷。RUN_INTEGRATION=1 下執行；unit 181 passed/45 deselected 不回歸）
  - 需求：1.1, 1.2, 1.4, 7.2, 7.5

## 7. 後台設定頁（api grounding 欄位）(P)

- [x] 7.1 `knowledge-admin/frontend/.../ConversationalConfigView.vue`：grounding 下拉新增 `api` 選項；`g_select==='api'` 時顯示 endpoint、params（key→模板）、required_slots、result_mapping 欄位；組 payload 寫入 `config.grounding_scope`。後端 payload 不改。**vite build ✓**（183 modules transformed 無誤）。下拉加 api 選項；api 區塊含 endpoint/required_slots(逗號)/params(每行 key=模板)/result_mapping(list_path·id_field·label_field·refine_param)；openNew 預設、openEdit 回填、buildConfig 組 {select:api,endpoint,required_slots,params,result_mapping} 寫入 grounding_scope；後端 payload 未動（僅前端 .vue 變更，dist 為 gitignore 產物）。
  - 注：專案無 JS 測試框架（pytest-only），驗證以 `vite build` 編譯通過為閘；建/改讀回一致由 7.2 驗。
  - 需求：5.1, 5.2, 5.3
- [x] 7.2 驗證：於設定頁建/改 api 型設定後讀回一致，且 `reset_cache` 後即時生效（後端既有快取清除）。**3 passed**（_config_from_row 原樣載回 api grounding_scope（含 params/result_mapping 巢狀）＝讀回一致 R5.3；reset_cache 後重載反映改後 endpoint＝即時生效 R5.4；未 reset 則沿用快取（佐證生效確由 reset 觸發）。後端 upsert 存 cfg 原樣入 generation_metadata 並 _reset_caches()、GET 原樣讀回，payload 契約未變。前端 build/讀回由 7.1 vite build 編譯閘把關；+對話 unit 不回歸，共 76 passed）
  - 需求：5.3, 5.4

## 8. 合約首案資料（對話規則 + 分類補標）

- [x] 8.1 新增 1 筆「合約診斷對話規則」（category=對話規則）：persona_role、rules_text（開場/追問識別/條件不足/查 API 或用知識/多筆反問/語氣）、`topic_scope={mode:category, category:條件診斷:合約}`、`grounding_scope={select:api, endpoint:jgb_contracts, required_slots:[contract_ref], params{role_id,contract_ids,keyword}, result_mapping{list_path:data, id_field:id, label_field:title, refine_param:contract_ids}}`。**5 passed**（種子 `database/migrations/seed_conversational_diagnosis_contract_rule.sql`：persona_role=property_manager、rules_text 含追問識別/條件不足/收齊converge/多筆反問/不杜撰；_config_from_row 解析 == 設計指定 config（topic_scope category + api grounding 全欄位）；冪等 WHERE NOT EXISTS；+對話 unit 不回歸，共 81 passed）。
  - 部署作業（DB 寫入，非單元測試執行）：`psql "$DATABASE_URL" -f database/migrations/seed_conversational_diagnosis_contract_rule.sql`，套用後清快取（重啟或後台任一儲存）即生效。persona_role=property_manager 不污染 freetext：`handle_conversational_entry` 硬限 `{'prospect'}`，診斷僅由分類路由進入。
  - 需求：8.1
- [x] 8.2 將缺分類的合約 form_fill 查詢知識補標 `條件診斷:合約`，使分類路由命中。**4 passed**（種子 `database/migrations/backfill_contract_knowledge_diagnosis_category.sql`：補多值 categories；以合約 API 端點識別合約查詢知識（自身 api_config 端點＝jgb_contracts，或 form_id 對應 form_schema 端點＝jgb_contracts），不硬編 id；冪等 NOT @>、僅 is_active、排除保留分類對話規則/系統脈絡；補標值與 8.1 設定 topic_scope.category 一致；補標後 _knowledge_category 取得診斷分類→路由可命中；+對話 unit 不回歸，共 85 passed）。
  - 部署作業（DB 寫入，非單元測試執行）：附預覽 SELECT，`psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_diagnosis_category.sql`，套用後清快取生效；一般合約知識（direct_answer 無此端點）不受影響＝維持靜態知識（三出口）。
  - 需求：8.2

## 9. 端到端驗證（真 jgb2 API）與行為保持

> ✅ 已於 2026-07-02 真實環境實跑全綠：常駐容器（aichatbot-rag-orchestrator，USE_MOCK_JGB_API=false、preview 真 jgb2 API）內 `RUN_E2E=1` 執行 `tests/e2e/conversational/`（本 spec 7 支＋domain-facets 5 支）**12 passed**。env：TEST_ROLE_ID=20151、TEST_VENDOR_ID=4（本庫無 7）、TEST_CONTRACT_REF_ONE=85100、TEST_CONTRACT_REF_MULTI=基隆溫馨一人宅套房、TEST_CONTRACT_REF_MANY=物件名稱是溫馨（裸關鍵字 LLM 不當識別，需句式）。實跑時修正骨架過時常數 DIAG_CATEGORY「條件診斷:合約」→「狀態判斷」（實作定名）。
> 🔧 前置修正（9.x 實跑必須，已 offline 驗證）：**role_id 貫通** — `_ground_by_api` 的 session_data 需自 state 取 role_id，但 `_start` 原未存；已修 `_start` 寫入會話識別（role_id/vendor_id/session_id/user_id）、`prepare`/`handle` 新增 `role_id` 參數、`_conversational_respond` 傳 `request.role_id`。新增 3 筆 unit（test_session_identity_threading_req.py）；全層 unit 共 **201 passed** 不回歸。未修則 e2e 打 jgb2 API 無 role_id、查不到使用者合約。
> 實跑前置見 e2e 檔頭 docstring（套種子、清快取、設 JGB_API_* 與 TEST_CONTRACT_REF_* env）。

- [x] 9.1 e2e（容器內 TestClient + 真服務 + 真 jgb2 API，role_id=20151）：模糊問句→追問（條件不足）→提供識別→收齊→回真實狀態/資訊；一般合約知識→轉靜態知識（三出口）。**骨架：** test_ambiguous_then_identify_converges / test_general_contract_knowledge_goes_static / test_stream_contract_diagnosis_event_sequence。已實跑綠（2026-07-02）。
  - 需求：2.2, 4.1, 4.2, 4.3, 8.3, 8.4
- [x] 9.2 e2e：API 回 0 筆→重問確認；多筆→列候選反問→選擇→單筆收斂。**骨架：** test_zero_result_reasks / test_multiple_results_list_then_select。已實跑綠（2026-07-02；REF_NONE 用預設「查無此合約xyz」、REF_MULTI=基隆溫馨一人宅套房 3 筆同名）。
  - 需求：3.4, 3.5, 8.5
- [x] 9.3 回歸驗證：售前（prospect）對話流程不變；非診斷面向查詢（表單/直接知識）不變；全層 pytest（unit/integration/e2e）綠。**骨架：** test_prospect_conversation_unchanged / test_non_diagnosis_query_unchanged。已實跑綠（2026-07-02）：unit **327 passed**、integration **24 passed**（修 2 支過時斷言：test_facet_diagnosis_multiturn 三層脈絡標記仍期望舊草稿的 bit_status/各階段下一步，實作已改 formatter 解碼＋新脈絡內容，改斷言現行種子語句；並將 USE_MOCK_JGB_API 由 setdefault 改硬設，常駐容器 false 蓋不掉會誤打真 API）、e2e **12 passed**。
  - 需求：7.1, 7.2, 7.4, 8.6

## 10. 通用性驗證（零合約硬編）

- [x] 10.1 以第二個「假面向」設定（mock 端點 + 不同 result_mapping 欄位）驗證：僅加設定即可啟用對話診斷、走通 ask→api→多筆，**無需改任何程式**；靜態掃描確認 ①②③④ 程式碼無合約欄位/端點字面硬編。**6 passed**（第二面向 mock_widgets/list_path:rows/id:uid/label:name/refine:widget_ids：_ground_by_api 1筆converge·0筆ask·N筆候選依其 result_mapping、插點A 候選選擇設 required_slots[0]=widget_ref 全由設定驅動零改程式；inspect.getsource 靜態掃描 _has_basic_info/_ground_by_api/_match_candidate/_ask_pick_again/_dig_path/prepare/config_for_category/_load/_knowledge_category/_diagnosis_config_for_knowledge 皆無 jgb_contracts/contract_ref/contract_ids/條件診斷 字面）。
  - 掃描揪出並修正：_has_basic_info/_ground_by_api docstring 原以「合約 contract_ref」舉例 → 改為面向中性敘述（合約字面僅存於設定/種子/測試）；全層 unit 共 **198 passed** 不回歸。
  - 需求：6.1, 6.2, 6.3

## 下一步
- 審核任務；通過後逐 Stage 實作（建議每任務間清 context）：
```bash
/kiro:spec-impl conversational-diagnosis 1.1
```
