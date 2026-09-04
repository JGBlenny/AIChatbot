# 落差分析：presales-grounding-gate（需求 v1 ↔ 現有程式）

> 2026-09-04。方法：對 `routers/chat.py`、`services/conversational_engine.py`、`services/llm_answer_optimizer.py`、`services/conversational_config.py`、`services/conversational_rules.py`、`services/usage_metering.py`、`services/decision_layer.py`、`services/base_retriever.py`、`services/vendor_knowledge_retriever_v2.py` 逐符號對碼，並查 jgb2 代理層與前端消費欄位。⚠️ `.kiro/settings/rules/gap-analysis.md` 不存在，沿用 `documind-ocr-mapping/validation_gap.md` 格式。
> ⛔ 本檔只給資訊與選項，不下最終決定；每條附可 grep 的符號。

## 一、現況：能直接沿用的東西

| 需求 | 既有機制 | 符號 |
|---|---|---|
| R1 門檻唯一讀值點 | 決策層已有唯一讀值點，`kb_threshold` 讀 `KB_SIMILARITY_THRESHOLD`；brain 的 `kb_search` 工具就是這樣拿門檻 | `services/decision_layer.py::DecisionConfig.load().kb_threshold`；`conversational_engine._make_kb_search` |
| R1 帶門檻的知識檢索 | `BaseRetriever.retrieve()` 在 application 端做 `similarity >= threshold` 過濾，且接受 `target_user／mode` kwargs、對 b2b 套 `business_types && system_provider` | `services/base_retriever.py::retrieve`（`_is_b2b = target_user in (...) or mode=='b2b'`） |
| R2 事實型／推薦型分流點 | `_converge_grounding` 已依 `converge_kind` 分 `answer`（`cta_mode=suppress`、`ctx=None`）與 `recommend`（`force`） | `conversational_engine._converge_grounding` |
| R2.3 事實型低溫 | `cta_mode in ("suppress","factual")` 已走 `LLM_ANSWER_SYNTH_TEMP`（預設 0.2） | `llm_answer_optimizer._build_presales_synth` |
| R3 封閉 enum 的解析慣例 | brain 輸出走 strict JSON schema（`additionalProperties: False`、`required` 全列），解析層 `_parse_conversational_step` 已有「越界值不製造半合法狀態」的規約 | `llm_answer_optimizer.CONVERSATIONAL_STEP_SCHEMA`（模組層 dict）、`_parse_conversational_step` |
| R4 回應欄位透傳 | `quick_replies` 已示範「引擎 result → `_conversational_to_response` → `VendorChatResponse`」與 SSE `metadata` 事件兩條透傳路 | `routers/chat.py::_conversational_to_response`、`_conversational_sse`（`_metadata["quick_replies"]`） |
| R4 jgb2 代理不擋新欄位 | 代理層原樣透傳上游 body 與狀態碰（註解自陳） | jgb2 `app/Http/Controllers/HelpAssistantController.php::chat` |
| R5 對話歷史 | `state["dialog"]` 已有最近 6 輪 `{u,a}`（u 截 200、a 截 300）；brain 已吃 `dialog[-4:]` | `conversational_engine._note_turn`、`_DIALOG_CAP`；`llm_answer_optimizer.conversational_step_result` 的 `hist_block` |
| R7 計量落點 | 每請求已有 `usage_events` context；`set_decision(snapshot)` 可掛任意 key 的決策快照（淺層合併、衝突推 prior）；`set_comparison(decision_case=)` 可寫 60 字以內字串 | `services/usage_metering.py::set_decision`、`set_comparison` |
| R8 測試骨架 | 已有 `tests/unit/conversational/test_presales_grounding_req.py`（mock retriever／`_grounding_by_*`）、`test_brain_strict_schema_req.py`（`_opt(llm_json)` 假 LLM）、`test_presales_compliance_req.py`（讀 code fallback 規則文字） | 同名檔 |

## 二、缺口：本案必須新建或改動的

### 缺口 1｜`_vector_search` 的 `similarity_threshold` 參數**根本不過濾**　`R1.1／1.4`

`vendor_knowledge_retriever_v2._vector_search` 註解自陳「SQL 不在 WHERE 端用 `>= threshold` 過濾（保留低分候選供 debug 顯示）」，只有 `LIMIT vector_limit`（預設 20）。所以 `_converge_grounding` 現行的 `similarity_threshold=0.0` 與改成 0.6 **行為相同**——參數是死的。真正的過濾在 `BaseRetriever.retrieve()` 的 application 端。

- 選項 A：`_converge_grounding` 的 vector 路改呼叫 `self.retriever.retrieve(query=..., top_k=3, similarity_threshold=<門檻>, target_user=..., mode=...)`（與 `_make_kb_search` 同款）。代價：`retrieve()` 會跑 keyword fallback／boost／reranker（若開）與較多 log；延遲多一段（reranker 曾實測會靜默停用，`project_retrieval_ranking_findings`）。
- 選項 B：保留 `_vector_search`，在 `_converge_grounding` 自己做 `[r for r in res if r["vector_similarity"] >= 門檻]`。代價：門檻語義變成「純向量分」，與 `KB_SIMILARITY_THRESHOLD` 比對的是 final `similarity`（tech.md「閾值對應欄位」）**不同尺**；等於發明第二套門檻語義。
- ⚠️ 既有測試 `test_grounding_default_vector_path` 斷言 `retriever._vector_search.assert_awaited()`——選 A 要改該斷言（它測的是「vector 路有被走到」，不是門檻）。

### 缺口 2｜`KB_SIMILARITY_THRESHOLD` 的實際預設是 0.55，不是需求 D2 寫的 0.6　`R1.2／D2`

`DecisionConfig.load()` 寫死 `os.getenv("KB_SIMILARITY_THRESHOLD", "0.55")`；steering `dialogue.md` 表寫 KB 最低 0.6、`knowledge.md` 寫 KNOWLEDGE_MIN_THRESHOLD 0.6、`retrieval-parameters.md` 寫 0.65 是「知識進入答題候選」門檻。三個數字三個命題。需求 D2 的「沿用 KB_SIMILARITY_THRESHOLD（0.6）」括號內數字**錯**，應改「沿用 `DecisionConfig.kb_threshold`（env 預設 0.55）」。售前池只有 20 筆，門檻 0.55 vs 0.65 的差異要用 prospect 20 題實測，不能拍腦袋。

### 缺口 3｜空 grounding 沒有「不生成」的出口　`R2.1／2.5／2.6`

- brain 路徑：`_converge_grounding` 在 `if not grounding` 塞占位字串後回傳，`handle()`／`stream_answer()` 一律呼叫 `synthesize_presales_answer(_stream)`。要加一個 `decision["kind"] == "handoff"`（或在 converge decision 帶 `grounding_empty=True`）讓 `handle`／`stream_answer` 直接回固定句、不進 optimizer。
- 無 session 路徑：`chat.py::_handle_no_knowledge_found` 的 `if request.target_user == 'prospect'` 分支以 `md_only_grounding` 呼叫 LLM。要改為回固定句＋handoff；`_meter_path('no_knowledge_found')` 已在，可沿用。
- 串流：`_conversational_sse` 的 `answer_chunk` 對固定句要整句一次 yield（比照 `ask` 分支）。
- ⚠️ 推薦型（`recommend`）空 grounding 目前也塞同一占位字串；D3 若維持推薦，占位字串要改寫（禁事實斷言），且**只**在 recommend 分支保留。

### 缺口 4｜brain schema 加 `fact_class` 要動 strict schema 的 `required`　`R3`

`CONVERSATIONAL_STEP_SCHEMA` 是 `strict: True` ＋ `additionalProperties: False` ＋ `required` 全列。新增欄位必須同時進 `properties` 與 `required`（strict 模式不允許可選欄位），enum 用 schema `enum` 鎖死；`BRAIN_STRICT_SCHEMA` 關閉時回退 `json_object`，此時 `fact_class` 可能缺 → 解析層歸 `other`（R3.2）。`_parse_conversational_step` 是唯一正規化點，加一段即可。既有 `test_schema_is_strict_and_requires_every_field` 會因 required 變動而需更新（它斷言欄位集合）。

### 缺口 5｜規則文字三處＋DB 一處要同步，且 DB 覆蓋 code　`R3.3／R4.3`

- 活規則在 DB `knowledge_base 3645`（category 對話規則），`load_rules` DB 優先、code fallback 只在查無時用；兩者現在內容相同、只差 markdown 粗體（比對後 `same_after_norm=False` 僅因 `**`）。
- 要改四處：DB 3645（業主寫 SQL；⚠️ category 對話規則**不在**不變量 10 母體，也不在不變量 17 的 declared 集，寫入不會觸發稽核紅燈——已核 `instance_applicability_contract.py` 的 `NOT IN ('對話規則','系統脈絡')` 與 `r10p_population_integrity.py` 的 `declared` 定義）、`conversational_rules.CONVERSATIONAL_RULES_BY_ROLE['prospect']`、`conversational_config.PRESALES_ANSWER_RULES`、`PRESALES_CTA_RULES`；另 `system_context.py` 內建脈絡也有一句「無法確認的事實導向 demo 或專人」（第五處，DB 3798 為活值）。
- 既有測試 `test_presales_compliance_req.py` 讀 code fallback 斷言合規字樣，`test_persona_currentvalue_principle_req.py` 斷言「轉專人」在 persona 內——改話術時要保留這些字。
- ⚠️ 進程快取：`conversational_rules._cache`、`conversational_config._cache` 改 DB 後要 `reset_cache()` 或重啟。

### 缺口 6｜`handoff` 欄位：後端一行，前端零消費　`R4.1／4.4／4.5`

- 後端：`VendorChatResponse` 加 `handoff: Optional[Dict]`（或 Pydantic 子模型），`_conversational_to_response` 與 `_conversational_sse` 的 `_metadata` 各加一處，`_handle_no_knowledge_found` 回應加一處。
- 前端：jgb2 `useChat.ts` 只讀 `data.answer／quick_replies／form_triggered`（非串流）與 SSE `metadata` 的同三鍵；**不會**讀 `handoff`。切片 2 的 LINE 入口按鈕是 jgb2 的工（範圍外），但契約要先在 `docs/api/conversational-api.md`、`docs/jgb2-chat-integration.md` 寫死，否則對方沒得照抄。
- 「專人／真人／客服 必帶 handoff」（R4.2）在有 grounding 的 LLM 路徑無法保證——模型仍可能自發寫「專人」。選項：(a) 只對決定性路徑斷言；(b) 對 LLM 輸出做後置掃描，命中字樣即補 `handoff{reason:"llm_mentioned_handoff"}`。(b) 是關鍵字規則，但治的是**封閉集合**（三個詞）且只加訊號不改文字，可接受；需求 R4.1 的 `reason` enum 要多一值。

### 缺口 7｜多輪：合成 prompt 與檢索 query 都拿不到上一輪　`R5`

- `_converge_grounding(state, converge_topic, user_message, config, converge_kind)` 已有 `state`，`state["dialog"][-1]["u"]` 即上一輪問句——只差併進 `kw`。
- `_build_presales_synth(grounding, accumulated_context, system_context_md, user_question, cta_mode)` 無歷史參數；要加可選 `prev_turn: Optional[dict]`，`handle()`／`stream_answer()` 從 `decision["state"]` 取出傳入。⚠️ `synthesize_presales_answer` 在 `chat.py` 有三處直呼（`_maybe_synth_prospect_freetext`、`_handle_no_knowledge_found`、`_maybe_synthesize_presales_leaf`），新參數必須有預設值。
- 「岔題不被拖走」（R5.4）：brain 規則 (c) 判全新主題時 `converge_topic` 會換；程式層可用「本輪 `converge_topic` 與上一輪不同 ⇒ 不併上一輪問句」當決定性守門，⛔ 不另做語義判斷。

### 缺口 8｜`usage_events` 的 `escape_kind`／`entry_tier` 欄位存在但**全 repo 無寫入者**　`R7`

grep `services routers` 零命中（正對照 `decision_case` 有 `set_comparison` 寫入）。三個選項：(a) 用 `set_decision({"presales_handoff": reason, "fact_class": ...})` 落 `decision_snapshot`（JSONB，免 migration，可查但要 `->>`）；(b) 為 `escape_kind` 補 setter（欄位已在表，語義「逃生種類」貼近 handoff）；(c) `set_comparison(decision_case="presales_handoff:<fact_class>")`（60 字內、既有欄位、可 GROUP BY）。(a) 最省、(c) 最好查、(b) 最貼語義但要確認該欄位當初的設計意圖（`retrieval-decision-layer` 封存 spec 內，⛔ D-003 不得列為前置必讀）。

### 缺口 9｜b2b 回歸的 A/B 工具　`R6.2`

`scripts/backtest/run_batch.py`（`_REQUIRED_PREFIX='backtest_session_'`）與 `compare_runs.py` 已在；今天稍早 `RERANK_FUSION_WEIGHT` A/B 已用過同一套（10 題逐字比對）。無新建需求，但要在 tasks 明列「改前跑一次存檔、改後跑一次 diff」。

## 三、實作路線比較

| 路線 | 內容 | 優點 | 代價 |
|---|---|---|---|
| **A 引擎內閘門**（建議） | `_converge_grounding` 改走 `retrieve()`＋門檻；回傳多一個 `grounding_empty`；`handle`／`stream_answer` 對 answer 型空 grounding 走固定句；`_handle_no_knowledge_found` prospect 分支同步 | 改動全在售前路徑（`CONVERSATIONAL_ENABLED_ROLES={'prospect'}` 守門），一般 b2b 零觸碰；沿用既有門檻讀值點與 `retrieve()` 過濾 | 兩處（brain 路／無 session 路）要各改；`retrieve()` 帶 reranker 的延遲 |
| B 前置閘門 | 在 `handle_conversational_entry` 之前先跑一次帶門檻檢索，空即 handoff、不進 brain | 一處攔截 | 推薦型對話（identity／scale 收集）本來就不需要知識，前置檢索會把「我是個人房東」這種話也判成無佐證 ⇒ 誤殺整條推薦流程；多一次檢索 |
| C 只改 prompt | 規則文字加「無知識就說不確定」 | 零程式 | 就是現況——規則已寫「不杜撰」仍生成；LLM 不是閘門（P0-1 五次實測） |

## 四、待研究清單（進 design 前解）

1. **門檻值實測**：以 prospect 20 筆池，對盤查 24 題＋今天 4 題跑 `retrieve()`，看 0.55／0.6／0.65 各留幾筆、哪些正解被砍——決定 D2，⛔ 不憑直覺。
2. **`retrieve()` 在 vendor_id=0、mode=b2b、target_user=prospect 下的過濾結果**是否與現行 `_vector_search` 同一批候選（business_types 條件相同？）；差異即行為變化，要列入回歸。
3. **strict schema 加欄位對 brain 成功率的影響**：gpt-4o-mini 在 strict 模式對新 enum 欄位的遵從率；失敗 ⇒ `conversational_step` 回 None ⇒ 整輪降級（`prepare` 回 None → 落一般檢索）。要量 20 題的降級率。
4. **固定句的語言與 markdown**：jgb2 面板是否渲染 markdown（`PRESALES_ANSWER_RULES` 要求 markdown 連結，推定會渲染）；固定句要不要帶 LINE 連結還是純文字＋按鈕。
5. **`escape_kind` 欄位的原設計意圖**（缺口 8 選項 b 的前提）。

## 五、對需求書的回修建議（核可前）

1. D2 括號數字改為「`DecisionConfig.kb_threshold`，env 預設 **0.55**」；並加註三個門檻命題不同（0.55 決策層／0.6 steering 舊值／0.65 檢索候選）。
2. R1.1 補一句：門檻比對的是 **final `similarity`**（經 `retrieve()`），⛔ 不是純向量分——否則缺口 1 的選項 B 會被當成合法實作。
3. R4.1 `reason` enum 加 `llm_mentioned_handoff`（缺口 6 的後置掃描），或把 R4.2 收窄為「決定性路徑必帶、LLM 路徑盡力」——二擇一寫明。
4. R5.4 明寫決定性守門：「以 `converge_topic` 是否變更判斷是否併上一輪問句」。
5. R7.1 指定落點（缺口 8 三選一），避免 design 再開一次題。
6. 範圍外補一條：「DB 3645／3798 的文字更新由業主執行 SQL，本 spec 提供文字與 SQL」——寫入雖不觸發稽核，但仍是 DB 寫入。
