# 售前小幫手盤查的根因對碼（2026-09-04）

> ⚠️ 本文為 2026-09-04 的紀錄；文中的舊 REST 對話鏈相關模組（`routers/chat.py`／`conversational_engine.py` 等）已於 2026-09-11 退役，見 `.claude/DECISIONS.md` DSP-046。

> 對象：`docs/presales-assistant-quality-audit-20260902.md`（jgb2 側實機盤查，P0×3／P1×3／P2×1）。
> 方法：`/canon-audit dialogue-logic` 22 份整檔讀（四個唯讀代理分工，憑證已累計進主 session；CLI `status` 猜錯檔誤報 0/22，見 BACKLOG）＋ 本機 `:8100`（2026-09-04 00:43 image）以 prospect 身分重現。
> ⛔ 本檔只講「現在怎麼跑、為什麼會這樣」與可選修法；⛔ 不預選產品決策。每個事實附可 grep 的符號。

## 0. 一句話

售前對話**不走**一般 b2b 檢索路徑：prospect 帶 `session_id` 進來時，`routers/chat.py::handle_conversational_entry`（`CONVERSATIONAL_ENABLED_ROLES = {'prospect'}`）在分類、檢索、`_top1_relevance_gate` **之前**就把請求交給對話 brain；brain 收斂作答時的知識 grounding 用 `conversational_engine._converge_grounding` → `_vector_search(similarity_threshold=0.0, top_k=5)`，**沒有任何相關性門檻**，撈不到就塞占位字串照樣讓 LLM 生成。b2b 的 fail-closed 只守一般檢索路徑，對售前對話**一次都沒生效**。P0-1／P0-3／P1-2／P1-3 全部是這一條機制的四種外顯。

## 1. 路徑事實（本次盤查對碼）

| 事實 | 符號 |
|---|---|
| prospect 請求體只有 `message／mode=b2b／target_user=prospect／session_id`，無 role_id／user_id／vendor_id | `docs/jgb2-chat-integration.md` §3.3；`chat.py::_dispatch_message` b2b 無 vendor_id ⇒ `vendor_info={'id':0,'name':'JGB System'}` |
| 有 session_id ⇒ 進 brain（不經分類、不經 gate）；無 session_id 才落一般檢索 | `chat.py::handle_conversational_entry`、`_maybe_conversational_freetext`（`if not request.target_user or not request.session_id: return None`） |
| brain 每輪先判 ask／converge，converge 分 `answer`（事實題）與 `recommend`（推薦題） | `conversational_engine.prepare`；規則文字＝DB `knowledge_base 3645`（category 對話規則，覆蓋 `conversational_rules.CONVERSATIONAL_RULES_BY_ROLE['prospect']`） |
| 推薦型收斂前程式強制 identity＋(scale 或 pain)，不足就把 converge 改回 ask | `conversational_engine._has_basic_info`；log「推薦型收斂但基本資訊不足，先補問再收斂」 |
| 收斂作答的 grounding：`[user_message]+converge_topic` 做向量查詢，**門檻 0.0、top-5**，取前 3 筆 answer；查無 ⇒ 占位字串「（依系統脈絡的功能索引與已知情境給適合建議；…不杜撰、不報價）」照樣送 LLM | `conversational_engine._converge_grounding`（符號 `similarity_threshold=0.0`） |
| 一般檢索路徑零命中時，prospect 也**不會**收到固定查無句：`_handle_no_knowledge_found` 對 prospect 改用 `md_only_grounding` 占位字串再呼叫 `synthesize_presales_answer`，非空即覆蓋 fallback | `chat.py::_handle_no_knowledge_found`、`_maybe_synth_prospect_freetext` |
| 生成：`_build_presales_synth`，system prompt＝系統脈絡（DB 3798）＋`PRESALES_ANSWER_RULES`；事實型 temperature 0.2（`LLM_ANSWER_SYNTH_TEMP`），推薦型 0.5，brain 判定 0.4；無 seed | `llm_answer_optimizer._build_presales_synth`、`conversational_step_result` |
| 合成 prompt **不帶對話歷史**；歷史只餵 brain（`dialog[-4:]`，純文字兩行）；無任何「上一輪問句意圖／動詞」的結構化欄位 | `conversational_engine._note_turn`／`_DIALOG_CAP=6`；`_build_presales_synth` 輸入只有 context／grounding／user_question |
| 桌機與手機各自 localStorage 各自 `session_id`（TTL 6 h）⇒ 兩個獨立 brain state | jgb2 `useChat.ts::generateId`、`PresalesChat.vue persistKey='presales'` |
| 回應契約只有 `confidence`（恆 1.0），**沒有**「本題無知識佐證／需轉人」的結構化訊號 | `docs/api/conversational-api.md` Response A；本機實打 `intent_type=conversational, confidence=1.0` |
| prospect 可見知識：20 筆（18 筆售前＋對話規則 3645＋系統脈絡 3798）；`target_user IS NULL` 的知識**一律放行**給 prospect | DB `knowledge_base WHERE target_user @> ['prospect']`；`vendor_knowledge_retriever_v2` 註解「target_user IS NULL 一律放行；retrieval-fixes #5」；`conversational_engine` 符號 `target_user IS NULL OR target_user @>` |
| 售前規則裡唯一的「不確定就說不確定」只寫在**競品**那一條；對客戶名單／報價／SLA／法遵／資安等事實類**沒有**通則 | DB 3645／`PRESALES_ANSWER_RULES`；3798 §5b |
| 「專人」出口：規則文字「系統脈絡與知識都沒有的細節才導 demo/專人」；demo 連結只在 `cta_mode=force`（推薦型）附上；事實型回答只剩「專人」兩字沒有入口 | `PRESALES_ANSWER_RULES`、`PRESALES_CTA_RULES`、`_converge_grounding` 對 answer 型設 `cta_mode="suppress"` |

## 2. 七題根因對照

| 盤查項 | 根因（機制層） | 本機重現（2026-09-04 01:0x，`backtest_session_presales_*`） |
|---|---|---|
| **P0-1** 事實性問題現場生成、兩次相反 | grounding 無門檻＋查無仍生成；規則只禁「杜撰」沒有「無佐證⇒不確定」的結構化分支；兩裝置兩 session、temperature 0.2–0.5 無 seed ⇒ 立場可翻 | 同題連問 5 次：3 次「並未特別針對 600 戶以上…」、1 次「案場資訊我無法提供」＋反問身分、1 次「並未…案例分享，建議試用」。知識庫**沒有任何**客戶名單／案場資料，五個答案都是無佐證生成；「並未特別針對」本身就是編出來的事實 |
| **P0-2** 滿嘴專人不指路 | 事實型 `cta_mode=suppress` 不附 CTA 塊；規則只叫模型「導專人」沒給入口；回應無 `escalate` 訊號可讓前端畫按鈕 | 5 次中 4 次出現「與我們的專人聯繫」，只有 2 次帶 pricing 連結，0 次帶任何真人入口 |
| **P0-3** 權限問題答反 | 知識缺口＋P0-1 機制：prospect 池只有 3584／3602 兩筆泛談「團隊權限」，沒有「可否隱藏財務數字／哪些開關」；grounding 撈到最近的泛談，LLM 順著「權限管理」生成 | 「收租組可以看不到財務數字嗎？」→「可以根據設定的權限來查看財務數字…允許您為不同成員分配不同的權限」——沒答「可以藏」，方向偏「看得到」 |
| **P1-1** 只給方法論不給數字 | 知識庫本無電費區間；規則「不報價」與「不杜撰」正確地擋掉數字，但沒有「給可操作下一步」的規則 | 未重現（非本輪重點） |
| **P1-2** 匯入回答覆誦不完整 | 同 P0-1；prospect 池無匯入條目，撈到 `target_user IS NULL` 的 3357（物件批次匯入）當底稿 | 見 P1-3 R1 |
| **P1-3** 追問繼承名詞不繼承動詞 | 合成 prompt 不帶上一輪 Q/A；檢索 query 只用當輪原句＋`converge_topic`；brain 有 4 輪歷史但只用來決定 ask／converge | R1「舊系統的資料能匯進來嗎？」→ 以 3357 原文作答（.xls、Ctrl+Shift+V）；R2「那物件跟合約呢？」→「物件和合約的資料也可以透過批次匯入」——**合約可匯入是編的**，知識庫無此條 |
| **P2-1** 起手式先反問戶數 | **這是設計**：`_has_basic_info` 強制 identity＋(scale∨pain) 才能推薦收斂；規則「優先補問 scale」 | 「我是個人房東」→「請問您管理的物件數量大約有多少呢？」 |

## 3. 事實衝突（⛔ 未裁不得選邊）

**DSP-008**：盤查 §P1-3 引 jgb2 查證「只有帳單支援批次匯入，物件／合約／租客都要手動建」；chatai 知識庫 3357（物件批次匯入，JGB 協助提供表格）、3431（物件批次匯入 Excel）、3476（租客批次匯入 Excel）、3404（帳單 Excel 批次匯入）皆 `is_active`，系統脈絡 3798 也列「租客批次匯入」。**兩邊對「物件／租客能不能批次匯入」互相矛盾。** 這決定 P1-2 是「答不完整」還是「答錯」，也決定知識該補還是該改。

## 4. 修法方向（三層，可分開做；每層列代價）

> 4.1／4.2／4.4 已立案實作：`.kiro/specs/presales-grounding-gate/`（requirements v2、design 1.0、tasks）；4.3 知識層另案（匯入待 DSP-008）、4.5 產品層待業主。

### 4.1 機制層：售前 grounding 加門檻＋「無佐證的事實題不生成」
- `_converge_grounding` 的 `similarity_threshold=0.0` 改為讀既有門檻（`retrieval-parameters.md` 的 `KB_SIMILARITY_THRESHOLD=0.65` 或售前專用 env），撈不到就是**真的撈不到**。
- grounding 為空時，依 brain 已輸出的 `converge_kind`／`converge_topic` 決定：事實題（`answer`）⇒ 回固定「這題我沒有可靠資料，幫您轉專人」句＋`handoff` 訊號，⛔ 不呼叫 LLM；推薦題（`recommend`）維持現行以系統脈絡功能索引推薦（那是它的本職）。
- 盤查要求的五類（客戶名單／報價／合約 SLA／法遵／資安）是**開放語義**，⛔ 不用關鍵字規則硬判（`feedback_rule_vs_layer`）；由 brain 的 JSON 多回一個 `fact_class`（enum，封閉集合）再由程式決定出口。
- 代價：售前「沒知識也能聊」的體驗會變硬；20 筆知識池太薄，門檻一開會有大量查無 ⇒ 4.3 必須同步。

### 4.2 契約層：回應加結構化轉人訊號、話術對齊入口
- `VendorChatResponse` 加 `handoff: {"reason": "...", "channel": "line_official"}`（或同義欄位），讓 jgb2 面板依訊號畫「找真人」按鈕（切片 2 的 LINE 官方帳號）。
- 規則文字（DB 3645／`PRESALES_ANSWER_RULES`）把「導專人」改成「說『這題我幫您轉專人，點下方的找真人』」；兩邊上線時間對齊。
- 代價：跨 repo 契約變更，要 jgb2 一起改。

### 4.3 知識層（不改程式）
- 補 prospect 可見的權限模型條目（哪些可獨立開關、財務相關有哪幾個、收租／修繕／財務組合）——來源 jgb2 `role_characters`（`show_role_payment`／`show_role_subscription`）；⛔ 依 `feedback_kb_generation_method` 先理解情境再寫，不丟 GPT 生成。
- 匯入條目等 DSP-008 裁決後再動。
- 客戶規模／案例類：**刻意不補**——那是業務要拿的資料，不該進知識；由 4.1 讓它穩定走「不確定＋轉人」。

### 4.4 多輪（P1-3）
- `_build_presales_synth` 帶入上一輪 Q/A（`dialog[-1]`）；`_converge_grounding` 的檢索 query 在 `answer` 型時併入上一輪問句。
- 代價：小；但要驗「岔題」情境不被上一輪拖走。

### 4.5 產品層（P2-1，業主決定）
- 起手式後先給該身分一項具體價值再問，或提供「先看常見問題」旁路——改的是 DB 3645 規則文字與 `_has_basic_info` 的門檻語義，⛔ 不是 bug。

## 5. 要業主決定的

1. 4.1 要不要做（改的是售前對話核心，b2b 一般檢索路徑不受影響但需回歸）；`fact_class` 由 brain 判還是先只用「grounding 空」一刀切。
2. 4.2 的 `handoff` 欄位名與 jgb2 上線節奏。
3. DSP-008：物件／租客到底能不能批次匯入。
4. P2-1 起手式體驗要不要改。
5. 客戶規模／案例類是否一律不進知識、一律轉人。

## 6. 驗收對照盤查

- P0-1：同題 5 次立場一致 ⇒ 4.1 後在本機以 `backtest_session_presales_*` 連打 5 次，五次皆為固定轉人句。
- P0-2：每次出現「專人」必帶 `handoff` 訊號（程式斷言，不靠讀文字）。
- P0-3：「收租組可以看不到財務數字嗎？」→ 含「可以」與開關名 ⇒ 4.3 條目上線後回測。
- P1-3：兩輪匯入問答，R2 不得出現知識庫沒有的「合約可匯入」。

## 7. 本次副產物

- DSP-008 已登記；`make audit` 不受本檔影響。
- 工具觀察：canon CLI `audit.py status` 沒帶 session id、靠「最近被改的憑證檔」猜，本次猜錯而誤報 0/22；實際主 session 憑證檔已有 22 份的整檔紀錄。已記 BACKLOG P3。
