# 實作任務：presales-grounding-gate（售前對話「無知識佐證不得生成」閘門）

> 建立時間：2026-09-04
> 需求：requirements.md v2（R1–R8）｜設計：design.md 1.0（7 元件、6 決策）｜落差：validation_gap.md（9 缺口）｜研究：research.md（12 題門檻實測）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後的補充測試
> ⚠️ 規則／模板缺席：`.kiro/settings/rules/tasks-*.md` 與 `templates/specs/tasks.md` 不存在，格式沿用 `documind-ocr-mapping/tasks.md`。
> 鐵律：**事實題無佐證 ⛔ 不呼叫 LLM**；**門檻比 final similarity、經 `retrieve()`**；**`fact_class` 封閉 enum、非法歸 `other`、⛔ 無關鍵字判類**；**⛔ 不動一般 b2b／b2c 檢索路徑**；TDD 先紅後綠、每條需求正反例各一；`backtest_session_` 前綴；改完必 rebuild `:8100` 實打；⛔ 不 dump env；DB 3645／3798 文字由業主執行 SQL。

## 1. 底座與改前基準（三項平行）

- [x] 1.1 (P) 售前閘門純函式模組（TDD）：新建 `services/presales_gate.py`——`presales_threshold()`（env `PRESALES_GROUNDING_THRESHOLD` 覆寫、否則 `DecisionConfig.load().kb_threshold`；壞值／越界回後者並 print 警告，⛔ 不 500）、`FactClass` 七值 enum 與 `parse_fact_class()`（非 str／不在 enum → `other`，⛔ 不做大小寫或同義正規化）、`HandoffReason`／`Handoff` 與 `build_handoff()`（敏感五類 → `sensitive_no_grounding`，否則 `no_grounding`）、`scan_handoff_mentions()`（封閉三詞「專人／真人／客服」）。測試：門檻好值／壞值／缺值／越界；enum 正反例含 `Pricing`／`price` 歸 other；reason 對映；三詞正反例。
  - 需求：1.2, 1.3, 2.2, 3.2, 4.1, 4.2
  - **收案註記（2026-09-04）**：RED→GREEN：`services/presales_gate.py`（`presales_threshold`／`FactClass`／`SENSITIVE`／`HANDOFF_WORDS`／`HandoffReason`／`Handoff.to_dict`／`build_handoff`／`build_llm_mention_handoff`／`scan_handoff_mentions`）；`tests/unit/conversational/test_presales_gate_req.py` 13 函式（parametrize 展開 39 案例）：門檻好／壞／缺／越界／NaN、變體 9 種歸 other、reason 對映、三詞正反例含「專業」近似詞。
- [x] 1.2 (P) 文案與 channel 資料化：`ConversationalConfig` 加 `handoff_message`／`handoff_channel`（DB metadata 供給；缺則 `PRESALES_HANDOFF_MESSAGE`＝D1 固定句、`PRESALES_HANDOFF_CHANNEL`＝env 預設 `line_official`）；`PRESALES_CONFIG` code 保底帶入。測試：DB 有值取 DB、無值取保底、env 覆寫 channel。
  - 需求：2.1, 4.1, 4.3
  - **收案註記（2026-09-04）**：RED→GREEN：`ConversationalConfig.handoff_message／handoff_channel`、`PRESALES_HANDOFF_MESSAGE`（D1 固定句，含「轉專人」釘字）、`PRESALES_HANDOFF_CHANNEL_DEFAULT='line_official'`、`effective_handoff_message()`／`effective_handoff_channel()`（DB > env > 保底）、`_config_from_row` 解析兩鍵、`PRESALES_CONFIG` 帶入；`test_presales_handoff_config_req.py` 5 測試。1.1＋1.2 合計 44 案例；`tests/unit/conversational` 全目錄 1291 過。
- [x] 1.3 (P) **改前基準快照**（⛔ 在任何程式改動前執行）：以 `scripts/backtest/run_batch.py`（`backtest_session_` 前綴）對 b2b 10 題跑一次存檔；另以本機 `:8100` prospect 身分把盤查 P0-1／P0-3／P1-3 兩輪／P2-1 原句各跑一次存 JSON（含 `answer`），作為 R6／R8 的 A 面。
  - 需求：6.2, 8.3
  - **收案註記（2026-09-04）**：⛔ 在任何程式改動影響 :8100 之前（image 仍為 00:43 版）：`baseline/b2b-10-batch.json`（T6 去重 5 題＋5 題 property_manager 知識題）→ `run_batch.py --prefix backtest_session_pgg_before`（vendor 1／role 20151／b2b／property_manager）→ `baseline/b2b-10-before.json`（10/10 HTTP 200）；`baseline/prospect-before.json`：P0-1 五次**五種**答案（其中兩次偏「可以支援」）、P0-3 答「可以查看財務數字」、P1-3 R2 漂移成「物件與合約的管理功能」、P2-1 反問戶數——四個症狀全數在 A 面留證，`handoff` 皆 None。

## 2. brain 的 `fact_class`（1.1 完成後）

- [x] 2.1 strict schema 與解析層（TDD）：`CONVERSATIONAL_STEP_SCHEMA` 的 `properties` 與 `required` 加 `fact_class`（schema `enum` 七值）；`_parse_conversational_step` 以 `parse_fact_class()` 正規化並放入 payload；`BRAIN_STRICT_SCHEMA` 關閉（`json_object`）時缺值 → `other`；brain 失敗／逾時走既有降級、⛔ 不因新欄位 500。更新 `test_brain_strict_schema_req.py::test_schema_is_strict_and_requires_every_field` 的欄位集合；新增缺值→other、非法值→other、strict 開關兩態測試。
  - 需求：3.1, 3.2, 3.4
  - **收案註記（2026-09-04）**：RED（10 紅）→ GREEN：`CONVERSATIONAL_STEP_SCHEMA` properties＋required 加 `fact_class`（enum 七值）；`_parse_conversational_step` 末段以 `presales_gate.parse_fact_class` 正規化（缺／非法 → other，⛔ 不猜變體）；`test_brain_fact_class_req.py` 9 函式（enum 七值、6 種非法、缺鍵、ask 不受影響、action 越界仍 reject、非 dict 仍 None、假 LLM 端到端）；既有 `test_brain_strict_schema_req.py` required 集合更新。
- [x] 2.2 規則文字四處同步＋業主 SQL：`conversational_rules.CONVERSATIONAL_RULES_BY_ROLE['prospect']` 加【fact_class】段（七值各一句定義＋一例）並把「導專人」句改為指向入口的話術；`PRESALES_ANSWER_RULES`（「系統脈絡與知識都沒有的細節才導 demo/專人」→「…才說『這題我幫您轉專人，點下方的找真人』」）、`PRESALES_CTA_RULES`（「由專人帶您看」句對齊同一入口）、`system_context.py` 內建脈絡「導向 demo 或專人」句同步；⛔ 保留「轉專人」「不報價」「不杜撰」字樣（`test_presales_compliance_req.py`／`test_persona_currentvalue_principle_req.py` 釘字）。產出 DB 3645／3798 的 UPDATE SQL 至 `.kiro/specs/presales-grounding-gate/sql/rules-20260904.sql`（業主執行，執行後 `reset_cache()` 或重啟）。測試：code fallback 含【fact_class】段與新話術、既有釘字仍在。
  - 需求：3.3, 4.3
  - **收案註記（2026-09-04）**：四處同步：`CONVERSATIONAL_RULES_BY_ROLE['prospect']` 加【fact_class】段（七值各一句＋例）、輸出 JSON 加 `fact_class`、(b) 段與【合規】的「導專人」改「這題我幫您轉專人，點下方的『找真人』」；`PRESALES_ANSWER_RULES` 同句＋新增「推薦時 ⛔ 不得含客戶名單／價格／合約／法遵／資安事實斷言」段（供 3.2 D3）；`PRESALES_CTA_RULES` 加「也可點下方『找真人』」；`system_context.MINIMAL_FALLBACK` 同句。`sql/rules-20260904.sql` 由 code 常數生成（3645 answer 逐字＝code fallback；3798 §6 兩格 replace），⛔ 業主執行；`test_presales_rules_handoff_req.py` 5 測試（含 SQL 與 code 同源斷言、既有釘字保留）。2.1＋2.2 33 案例；`tests/unit/conversational` 1315 過。

## 3. 引擎：grounding 門檻與 handoff 分支（1.1、1.2、2.1 完成後）

- [x] 3.1 `_converge_grounding` 改造（TDD）：vector 路改 `self.retriever.retrieve(query, vendor_id, top_k=3, similarity_threshold=presales_threshold(), target_user, mode)`；回傳 `ConvergeGrounding(text, ctx, cta_mode, empty, hits, threshold, score_source)`，空 grounding 時 `text=""`、⛔ 不再塞占位字串；`answer` 型且傳入 `prev_user_message` 時 query 併入上一輪問句；`retrieve()` 例外視為空（fail-closed）並記 `presales.error`；`ids`／`category` 兩路不變。更新 `test_presales_grounding_req.py::test_grounding_default_vector_path` 為 `retrieve.assert_awaited()`；新增：門檻傳入值＝`presales_threshold()`、零筆 → `empty=True` 且 text 空、prev 併入 query、例外 → empty。
  - 需求：1.1, 1.4, 1.5, 5.1
  - **收案註記（2026-09-04）**：RED（import 失敗）→ GREEN：`ConvergeGrounding` dataclass（可解包三元組向後相容、`from_legacy`）；`_converge_grounding` vector 路改 `retriever.retrieve(top_k=3, similarity_threshold=presales_threshold(), target_user, mode)`、零筆 `text=""`／`empty=True`（⛔ 無占位字串）、`prev_user_message` 只在 answer 型併入 query、例外 fail-closed 記 `error`；`prepare` 過渡：空 grounding 暫塞舊占位字串維持合成，並在 decision 暴露 `grounding_empty／hits／threshold／score_source／error`（3.2 接手分流後移除占位）。`test_converge_grounding_gate_req.py` 7 函式（8 案例）；既有 `test_grounding_default_vector_path` 改斷言 `retrieve` 被呼叫、`_vector_search` 不得被呼叫。⚠️ 閘門要求先整檔讀 `conversational-repair/design.md`、`brain-kb-grounding/design.md`——已讀，無矛盾（後者決策 3「沿用既有 KB 門檻」與本案一致）。
- [x] 3.2 `prepare`／`handle`／`stream_answer` 分流（TDD）：decision 帶 `fact_class`／`grounding_empty`／`grounding_hits`／`prev_turn`（僅 `converge_topic == state["last_converge_topic"]` 才帶）／預建 `handoff`；`answer ∧ empty` ⇒ `answer=config.handoff_message`、附 `handoff`、**optimizer 不被呼叫**、`stream_answer` 整句一次 yield；`answer ∧ hits>0` ⇒ 現行合成（`cta_mode=suppress`）並傳 `prev_turn`；`recommend ∧ empty` ⇒ 以系統脈絡推薦，`system_md` 追加禁事實斷言段（由 `PRESALES_ANSWER_RULES` 新段供給）；合成完成後 `scan_handoff_mentions()` 為真補 `llm_mentioned_handoff`；`_finalize_converge` 更新 `last_converge_topic`；每輪 `set_decision({"presales": {...}})`；日誌只 print `fact_class／hits／threshold／reason`，⛔ 不印 grounding 內容或使用者原句以外的推斷。測試：四條分支各一（含 `optimizer.synthesize_presales_answer.assert_not_called()`）、串流分支整句、`converge_topic` 變更不帶 prev_turn、快照鍵形狀、日誌行不含 grounding 文字。
  - 需求：2.1, 2.2, 2.3, 2.4, 2.6, 4.2, 5.4, 7.1, 7.2, 7.3
  - **收案註記（2026-09-04）**：RED（11 紅）→ GREEN：`prepare` 售前分流——`fact_class` 由 `parse_fact_class` 正規化；prev_turn 只在 answer 型且 `converge_topic == state['last_converge_topic']` 才帶（決定性守門）；`answer ∧ empty` ⇒ `kind='handoff'`（`build_handoff`＋`effective_handoff_message/channel`）、`_note_turn`＋`_save`、⛔ 不進 optimizer；`recommend ∧ empty` ⇒ 新占位（含「⛔ 不得含客戶名單…事實斷言」）維持推薦（D3）；3.1 過渡占位移除。`handle()`／`stream_answer()` 加 handoff 分支（整句一次）、傳 `prev_turn`；`_finalize_converge` 記 `last_converge_topic` 並以 `_attach_llm_mention_handoff` 後置掃描補 `llm_mentioned_handoff`（只加訊號不改文字）；`_meter_presales` → `usage_metering.set_decision({'presales': {...}})`；日誌只印 kind／fact_class／hits／threshold／score_source／error。`test_presales_handoff_branch_req.py` 11 測試（含 optimizer `assert_not_called`、跨 session 決定性、串流整句、快照命名空間、日誌不含 grounding 文字）；3.1 過渡測試改為斷言 `kind='handoff'`。`tests/unit/conversational` 1339 過。

## 4. 合成 prompt 帶上一輪（3.2 前可先做；與 3.x 平行）

- [x] 4.1 (P) `_build_presales_synth`／`synthesize_presales_answer(_stream)` 加關鍵字參數 `prev_turn: Optional[dict] = None`（`chat.py` 三處既有直呼不變）；`prev_turn` 非空時 prompt 加【上一輪】使用者／你 兩行與「本輪追問延續上一輪的動作意圖；追問主題在可用知識無對應時明說『這部分我沒有資料』，⛔ 不得換一組功能回答」。測試：以假 LLM 擷取 messages，斷言 prompt 含／不含上一輪段；`prev_turn=None` 時 prompt 與改前逐字相同。
  - 需求：5.2, 5.3
  - **收案註記（2026-09-04）**：`_build_presales_synth`／`synthesize_presales_answer`／`synthesize_presales_answer_stream` 加 keyword-only `prev_turn: Optional[dict]=None`；有值才插【上一輪】兩行＋「延續上一輪的動作意圖／這部分我沒有資料／⛔ 不得換一組功能」段，放在【使用者問題】之前；`None` 或兩值皆空 ⇒ prompt 逐字不變。`test_presales_synth_prev_turn_req.py` 5 測試（含簽名 keyword-only 斷言、model／temperature 不變）。3.1＋4.1 合計 18 案例；`tests/unit/conversational` 1328 過。

## 5. Router 契約與無 session 路徑（1.1、1.2 完成後；兩項平行）

- [x] 5.1 (P) `HandoffSignal` Pydantic 子模型與 `VendorChatResponse.handoff: Optional[HandoffSignal]`；`_conversational_to_response` 透傳 `result["handoff"]`；`_conversational_sse` 在 `metadata` 事件加 `handoff`（與 `quick_replies` 同位置），串流結束後對累積文字 `scan_handoff_mentions()` 補 `llm_mentioned_handoff`。測試：無 handoff 時欄位為 `None` 且回應 JSON 鍵存在值 null；有 handoff 時形狀與 enum 值域；SSE metadata 含鍵；既有 `quick_replies` 行為不變。
  - 需求：4.1, 4.4
  - **收案註記（2026-09-04）**：RED（import 失敗）→ GREEN：`HandoffSignal`（`Literal` 封閉 reason／fact_class）、`VendorChatResponse.handoff: Optional[HandoffSignal]`（鍵恆存在、值 null）；`_conversational_to_response` 透傳 `result['handoff']`；`_conversational_sse` 累積 chunk，`metadata` 事件帶 `handoff`（引擎已建者透傳；否則以 `scan_handoff_mentions` 對串流全文補 `llm_mentioned_handoff`），無則鍵不出現。`tests/unit/chat_flow/test_presales_handoff_contract_req.py` 6 測試（含 enum 封閉、`quick_replies` 不變、SSE 事件序）。
- [x] 5.2 (P) `_handle_no_knowledge_found` prospect 分支：刪 `md_only_grounding` 合成呼叫，`fallback_answer=config.handoff_message`、`response.handoff=build_handoff(FactClass.other, ...)`（無 brain ⇒ other）、保留 `_meter_path('no_knowledge_found')`、加 `set_decision({"presales": {..., "path": "no_session"}})`；非 prospect 分支逐位元不變。測試：prospect 零命中不呼叫 optimizer、回固定句＋handoff；非 prospect 回既有 fallback 且 `handoff is None`。
  - 需求：1.5, 2.5, 7.1
  - **收案註記（2026-09-04）**：`_handle_no_knowledge_found` prospect 分支：刪 `md_only_grounding`＋`synthesize_presales_answer` 呼叫，改 `build_handoff(FactClass.other, channel, message)`（`config_for_target_user` 供文案，DB > env > 保底）、`set_decision({'presales': {..., 'path': 'no_session'}})`、`_meter_path('no_knowledge_found')` 保留；最終 `VendorChatResponse(handoff=_handoff)`，非 prospect 恆 None。`test_presales_no_session_handoff_req.py` 3 測試（含 optimizer `assert_not_called`、非 prospect 既有兜底不變）。5.1＋5.2 9 案例；`tests/unit/chat_flow`＋`conversational` 1372 過。

## 6. 文件（與 5.x 平行）

- [x] 6.1 (P) `docs/api/conversational-api.md` Response 加 `handoff` 欄位、出現條件（三種 reason）、SSE metadata 形狀、前端預期行為（畫「找真人」入口；欄位可選、未升級不受影響）；`docs/jgb2-chat-integration.md` §3.3 加同一契約與 jgb2 切片 2 對齊註記；`docs/presales-assistant-rootcause-20260904.md` §4 加回鏈到本 spec。
  - 需求：4.5
  - **收案註記（2026-09-04）**：`docs/api/conversational-api.md`：Response A 加 `handoff` 欄位＋專節（形狀、三種出現條件、前端預期行為、相容、⛔ 不得用文字判斷）、Response B 的 `metadata` 註記；`docs/jgb2-chat-integration.md` §3.3 加契約與上線對齊警語、§5 回應格式加 `handoff` 行；`docs/presales-assistant-rootcause-20260904.md` §4 加回鏈本 spec。

## 7. 回歸、實打與收案（1–6 完成後）

- [x] 7.1 全套與突變控制：`make test-unit` 全綠（既有紅 `test_verdict_ruler_req` 不計）；三向突變各至少一條轉紅並還原——門檻改 0.0（`presales_threshold` 回 0）、移除 handoff 分支（answer∧empty 仍進 optimizer）、移除 prev_turn 併入；記錄轉紅測試名。
  - 需求：6.1, 6.3, 8.1, 8.2
  - **收案註記（2026-09-04）**：`make test-unit` 2325 過、唯一紅＝既有 `tests/unit/backtest/test_verdict_ruler_req.py`；無新依賴（`requirements.txt` 無 diff）、無佐證路徑少一次 LLM 呼叫。三向突變（改→跑→還原→md5 對照 OK）：M1 `presales_threshold` 回 0.0 ⇒ 8 紅（`test_threshold_*` 5 條＋grounding 門檻斷言）；M2 拿掉 `answer∧empty` handoff 分支 ⇒ 5 紅（`test_answer_with_empty_grounding_returns_fixed_sentence_without_llm`、`test_non_sensitive_class_*`、`test_stream_answer_yields_fixed_sentence_once_for_handoff`、`test_decision_snapshot_has_presales_namespace`、`test_prepare_exposes_grounding_empty_flag`）；M3 拿掉 prev_user_message 併入 ⇒ 2 紅（`test_prev_user_message_is_merged_into_query_for_answer_kind`、`test_prev_turn_used_only_when_converge_topic_unchanged`）。還原後 58 案例全綠。
  - **7.2 前置觀察（2026-09-04，5.x rebuild 後 smoke，⚠️ 業主尚未執行 DB 3645 SQL）**：① P0-1／P0-3／P1-3 R1 皆回固定句＋`handoff`，但 P0-1 的 `fact_class=other`（brain 仍用 DB 舊規則、無【fact_class】段）⇒ reason 落 `no_grounding` 而非 `sensitive_no_grounding`——**SQL 執行後再量**。② P1-3 R2「那物件跟合約呢？」被 brain 判成 `recommend` ⇒ 走 D3 系統脈絡推薦（「集中管理／電子簽章」），仍是名詞繼承動詞丟失、無 handoff——R2.4 的禁斷言只擋五類事實，擋不住功能推薦；待 DB 規則（(b) 追問→answer）生效後重測，仍漂移則列 REVISE 候選。③ 有知識題（免費試用）文字含「客服」⇒ `llm_mentioned_handoff` 曾配「沒有可靠資料」句（矛盾）⇒ 已改為 `PRESALES_HANDOFF_ENTRY_HINT` 入口提示（測試釘住、文件同步）。
- [x] 7.2 rebuild `:8100` 後實打（`backtest_session_` 前綴）：P0-1 原句連問 5 次逐字相同且 `handoff.reason=sensitive_no_grounding`；P0-3 原句回固定句（知識未補前）；P1-3 兩輪 R2 不含「合約可匯入」且對「合約」明說沒有資料；P2-1 行為不變（範圍外）；b2b 10 題 A/B 與 1.3 基準逐字 diff＝0；量 20 題 brain 降級率（research Q1）記入 `perf-<date>.md`。
  - 需求：6.2, 8.3
  - **收案註記（2026-09-04）**：DB 3645／3798 SQL 已套（我代跑，兩段 UPDATE 1）並重啟；:8100 image＝5.x＋入口提示修正。P0-1 五次逐字相同＋`sensitive_no_grounding／customer_reference` ✅；P0-3 固定句 ✅；P1-3 兩輪皆 handoff、R2 無「合約可匯入」 ✅；P2-1 不變 ✅；b2b 10 題 A/B 9/10 逐字相同，唯一差異為診斷面向追問句的 LLM 非決定性（同碼兩次也不同），路徑／action_type 10/10 相同；20 題降級率 **0/20**、敏感五類分類全對。⚠️ 兩項未達／待裁，寫在 `perf-20260904.md`：① 門檻 0.55 擋掉「電子發票」（3601 final 0.534，盤查正面項）⇒ 建議 env `PRESALES_GROUNDING_THRESHOLD=0.5`；② 延遲 NFR 未達——安靜 P0-1 median 8.31 s vs 改前 6.35 s，`retrieve()` 比舊 vector 路多 1.5–2 s（reranker／keyword），淨持平到略高。
- [x] 7.3 獨立 verifier 複現 7.1／7.2 全部項目（brief 含指紋、⛔ 不動 `:8100`、⛔ DB 只 SELECT、已知紅燈免責句）；REFUTED 逐條 FIX／DEFER／REJECT 後才可宣告完成。
  - 收案紀錄（2026-09-04，業主裁 A）：斷言 verifier 兩輪→CONFIRMED；情境 e2e 四輪（perf §6–9）：第 1–3 輪 REFUTED 各修結構（own-question 再查、inline 只回 handoff、fact_class 覆寫、重問重播、「沒有資料」入詞集、D6 抽取式、inline 一律抽取、R2.11 ask 反問句閘門、R2.12 抽取式帶 handoff）；第 4 輪 **A/B/D/E/F 過（67 turns 0 捏造）、C 過度封鎖 5/9 不過**——成因是 3600／3610 缺口語講法（門檻無解，perf §9 分數表），屬範圍外知識補充，業主選 A：**主張收窄為「不捏造」成立、口語過度封鎖列 BACKLOG（❓ P2）**。
  - 二次裁決（同日）：業主「不要 D6，補完知識再考慮」⇒ D6 改 env `PRESALES_EXTRACTIVE` 開關預設關，三條路有知識交 LLM 合成；**第 5 輪 e2e CONFIRMED**（perf §10：五類 0 漏、功能邊界 1/15 壓線、答題品質改善、過度封鎖 6/9 屬知識講法缺口）。知識側待補清單見 BACKLOG。
  - 需求：8.4
  - **收案註記（2026-09-04）**：兩輪獨立 verifier。第一輪 **REFUTED**：P2 F-1（prospect `ask` 分支非串流不帶 handoff、串流卻帶；固定句入對話史被複述）＋A1（線上門檻實為 compose env 0.65）、A2（匯入題零命中）、A3（recommend 占位塞指令進知識槽）、A4、A5（ask 輪無計量）。處置：F-1／A3／A4 FIX；A1 文件更正；A2／A5 DEFER。修 F-1 時二次實打抓到同類漏洞——`ask` 的 `inline_answer` 無 grounding 就斷言「合約也可以匯入」⇒ 新增 **R2.7** 閘門（inline 過門檻、空則固定句＋handoff、計量 `path=inline`）、規則文字加禁令、SQL 重生已套 DB。第二輪（收尾，範圍收窄）**CONFIRMED 7/7**：1378 過／全套 2331 過（唯一紅既有）；F-1 決定性複現帶 `llm_mentioned_handoff`、config=None 不崩不誤掛；P1-3 R2 ×4 皆帶 handoff、P0-1 ×3 固定句未退化、串流同語義；b2b 10 題 action_type／http 10/10、answer 9/10（第 7 題 LLM 非決定性）、獨立探針 handoff 10/10 null；計量 `path='inline'` 6 列；突變單點轉紅還原 md5 一致；config 不進 SSE／JSON、兩個標記 0/3、0/5 被抄。Advisory 全 DEFER（BACKLOG）：A-1 P3 `next_question` 無機械閘門、2/8 漏功能斷言（handoff 已在，R4.2 判準未觸發）；A-2 P4 inline 放行分支不計量；A-3 P4 inline＋next_question 整句重複（既有形狀）；A-4 P4 `EMPTY_GROUNDING_MARK` 不外洩僅 n=3；A-5 P4 `run_batch.py` 不採集 `handoff`（空對照）。
  - **e2e 情境回測（業主「幫我派代理驗實際對話 e2e」，2026-09-04）**：兩輪皆 REFUTED → 修五處（本輪問句自身過門檻／inline 閘門直接 handoff／fact_class≠other 以 answer 處理／逐項對照指令／同題重問重播、封閉詞加「沒有資料」；R2.7–2.9、R5.1 v4）→ B2／B3／B4／B5 消除、推薦型不誤擋；**殘留 B1（LLM 對部分相關 grounding 過度推廣，2 次 1 中）待業主 D6**；過度封鎖擴大待 D2。詳 `perf-20260904.md` §6–7。⚠️ 本 spec 因此**未達可宣告完成**：D6／D2 裁決前 B1 仍在。

## 需求追溯

| 需求 | 任務 |
|---|---|
| 1.1–1.5 | 1.1、3.1、5.2 |
| 2.1–2.6 | 1.1、1.2、3.2、5.2 |
| 3.1–3.4 | 1.1、2.1、2.2 |
| 4.1–4.5 | 1.1、1.2、2.2、3.2、5.1、6.1 |
| 5.1–5.4 | 3.1、3.2、4.1 |
| 6.1–6.3 | 1.3、7.1、7.2 |
| 7.1–7.3 | 3.2、5.2 |
| 8.1–8.4 | 1.3、7.1、7.2、7.3 |

## 待業主（不阻擋 1–6，阻擋 7.2 的兩項）

- DB 3645／3798 文字 SQL 執行（2.2 產出）——未執行則 code 保底文案生效、行為一致。
- jgb2 切片 2 的 `channel` 實際值與按鈕上線時間（D1／Q2）——影響固定句是否指向存在的按鈕。
