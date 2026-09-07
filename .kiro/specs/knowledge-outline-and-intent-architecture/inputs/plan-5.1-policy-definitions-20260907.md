# Plan 切片 KOIA-5.1：`agent_rules.py` 定義搬遷——對話判準三段定義＋persona 三分支（2026-09-07）

> 狀態：**草案，待 plan-verifier → 業主核**（核准前 ⛔ 不寫碼）。對應 tasks 5.1、R4.4／R4.7、design 元件 7「對話邏輯」與「身分反問禁令」列、裁定 13（只寫定義不寫例子）。**起因**：4.4b 探針（`inputs/probe-report-20260907.md`）H1 翻轉 1/10、H4 命中；候選層通過（gold 在前五 0.906），回答層未過——A 層 30 回合有 22 回合模型拿到對的細目仍一次嘗試都不做就 `no_grounding` 轉人。業主 2026-09-07「起 5.1」。**驗收尺＝同一凍結題集重跑**（`eval/outline-probe-20260907.json`，sha `22aa2c10…`，⛔ 不改題）。

## 0. 結論先講

把 kb 3645 的售前對話判準（A 事實題直答／B 推薦題補問、補問欄位封閉集合一次一題、已知不重問、基本資訊門檻、已推薦後三態、中途岔題、fact_class 七值＋句形不是判準）**以定義句搬進** `_POLICY_TEXT`，並讓 `persona_provider` 依 `resolved_audience()` 分三支（潛在客戶／使用中的業者／租客）；**以「替換」達成，不以「加長」達成**——現行政策文 1,197 字、`_agent_rules_text` 739 字，兩者在「引用鐵則」上重複一整段，DSP-028 實測「提示詞越長 mini 越傾向先轉人」（perf README R2→R4：18.5% vs 10%），所以本片給政策文一條**長度上限＝現行 1,197 字**（單元測試釘住）。⛔ 不動引用契約（DSP-029a 的四段式標記與 nonce 檢查，是決策反轉，另列待裁）、⛔ 不動敏感程式側（5.3）、⛔ 不寫例子。**誠實預期**：perf README 判讀③已記錄「先轉人的題大綱其實有寫，屬模型判斷覆蓋的能力問題」——5.1 是規格內該做的第一刀，但翻轉率能不能過 50% 是重跑才知道的事；不過就停下交裁，⛔ 不再加提示詞特例。

## 1. 結果（outcome）

### 1.1 `services/agent/agent_rules.py`
1. **`_POLICY_TEXT` 改為三段定義（總長 ≤1,197 字，`⛔` 數量 ≤ 現行 10）**：
   - **【判準】**（新）：每輪先判使用者要什麼——**A 事實題**（問系統有沒有某能力、怎麼操作、某流程怎麼走、某條件是什麼）⇒ `kind=answer` 直接回答，⛔ 不反問身分或規模；**B 推薦題**（問適不適合、想解決管理困擾、要推薦方案）⇒ 已知資訊不足時 `kind=ask` 補問，足夠時 `kind=recommend`。**資料段有講到的就要答**：候選章節任一行能支撐一句回覆就構成回答依據；只有資料段與工具都沒有這題的內容才 `handoff`／`no_grounding`。（這條直接對 4.4b 的病灶 1。）
   - **【補問規則】**（新，B 用）：補問欄位封閉集合＝`identity`／`scale`（＝`unit_count`）／`team`／`pain`／`interested`；一次只問一題；已知或可推斷的欄位不再問；基本資訊門檻＝`identity`＋（`scale` 或 `pain`），達門檻即可 `recommend`；已給過推薦後：對方結束或接受 ⇒ 簡短回應不重述方案、追問細節 ⇒ `answer`、新題 ⇒ 依判準重判；推薦題進行中若插入事實題 ⇒ 先以 `answer` 答它。`identity` 槽位由系統填入、`identity_source=entry` 時不得再詢問身分；`identity_detail` 只填角色子類、不填姓名／公司／聯絡方式（4.2 句保留）。
   - **【fact_class】**（改寫現行段為定義）：七值 `feature`／`other`／`customer_reference`／`pricing`／`contract_sla`／`compliance`／`security`；`feature`＝系統功能、操作方式、有沒有某能力、流程與條件，**句形不是判準**——陳述句描述自己想做或已有的事也是在問功能；五類敏感值只在問客戶名單、報價數字、合約責任條款、法規遵循聲明、資安認證時落入，且一律 `kind=handoff`＋`sensitive_no_grounding`；`other`＝寒暄或與系統無關。
   - **保留**：四條鐵則（縮句不縮義）、輸出契約（`sentences` 一句一筆、`kind=fact` 必有 `refs` 原樣照抄、`kb.get` 允許句與 `outline:` 形狀、`handoff_reason` 值域）。**刪除**與 `prompt_assembler._agent_rules_text` 重複的「引用鐵則」敘述（該段已在指令區逐字存在），這是長度預算的來源。
2. **`persona_provider(identity)` 三分支**（依 `identity.resolved_audience()`，定義句、各 ≤150 字）：`prospect`＝現行售前顧問人設；`property_manager`＝已在使用系統的業者客服——解決操作、帳務、設定問題，不推銷方案、不問身分與規模；`tenant`＝租客客服——只談租客端能做的事（繳費、合約、報修、通知），不談業者端管理設定、不推銷。⚠️ 事實：`AGENT_TURN_SPEC` stage 只開 prospect，pm／tenant 分支今天無活流量；仍實作以滿足 R4.7 與快照測試。
3. `policy_provider` 維持回傳同一份 `_POLICY_TEXT`（三受眾共用判準；受眾差異只在 persona）。

### 1.2 測試（新檔 `tests/unit/agent/test_agent_rules_definitions_req.py`，`req("knowledge-outline-and-intent-architecture:5.1")`）
4. **快照（三分支）**：`persona_provider` 對三個受眾各回固定字串，逐字快照（測試內常數）；`policy_provider` 對三受眾回同一字串。
5. **定義存在**：政策文含「A 事實題」「B 推薦題」「一次只問一題」「已知」「不再問」「identity」「scale」「pain」「recommend」「句形不是判準」七值全列；含 4.1 允許句（`kb.get`、`整節後再引用`、`outline:`）與 4.2 身分句（`identity_source=entry`、`不得再詢問對方身分`、`identity_detail`）——既有 `test_agent_policy_kb_outline_req`／`test_identity_slots_contract_req` 兩案不改仍綠。
6. **不寫例子**：三段 persona 與政策文皆不含 `（如`、`(如`、`例如`、`例：`、`像是`（正對照：塞一個「例如」的假字串必紅）。
7. **長度上限**：`len(_POLICY_TEXT) <= 1197` 且 `_POLICY_TEXT.count("⛔") <= 10`；persona 各 ≤150 字（正對照：上限值寫在測試常數並註明來源＝2026-09-07 現行值與 DSP-028 R2→R4 實測）。
8. **不重複**：`_POLICY_TEXT` 不含 `_agent_rules_text` 已有的「一句一筆放進 `sentences`」「每個事實句必須引用」兩句的逐字複本（以子字串斷言）。
9. **不引用測試詞表**：`agent_rules.py` 不引用 `IDENTITY_REASK_PATTERNS`／`reask_hits`（既有 S2b 掃描涵蓋，重跑仍綠）。
10. 既有：`test_prompt_assembler_req.py::test_build_signature_has_no_channel_for_tool_results` 綠；`scripts/run-tests.sh unit tests/unit/agent/ tests/unit/_meta/ -rA` 全綠；`make audit` PASS。

### 1.3 主驗收（收案後、業主核定義文後）：**重跑 4.4 凍結題集**
11. `agent_eval --set outline-probe --chain agent --provider openai --candidates on --repeat 3 --dump-texts`（與 `off` 臂同法；≈$0.65）。對照 4.4b 基線：翻轉率（A 層 ≥2/3 rep 答到且引用 ∈ gold）1/10 → **目標 ≥5/10**；`budget_exhausted` 18/147 不得升；敏感誤判（`sensitive_no_grounding` 44 回合）不得升；H2 對照組仍 0/5 被答到；H5 敏感 0 漏；H4 盲標無據率不得高於基線 `on` 4/34（同封包法、附細目標題）。任一退步 ⇒ 停下交裁、⛔ 不再改提示詞。
12. 受測物清單另立 `inputs/object-under-test-outline-probe-51-<date>.md`（`agent_rules.py` 新 sha、正本 sha 不變、題集 sha 不變），業主核可欄；outline-gate state 切換同 4.4b 步驟。

## 2. 現況事實（主 session 2026-09-07 實查；查證指令附）
- `_POLICY_TEXT` 現長 1,197 字、`⛔` 10 個；`_agent_rules_text(nonce)` 739 字、`⛔` 13 個；`_PERSONA_TEXT` 150 字。`docker compose -f docker-compose.dev.yml run --rm rag-orchestrator python3 -c "from services.agent import agent_rules as ar; from services.agent.prompt_assembler import _agent_rules_text; print(len(ar._POLICY_TEXT), len(_agent_rules_text('0123456789abcdef')), len(ar._PERSONA_TEXT))"`
- 組裝順序（`PromptAssembler.build` ①）：persona → policy → `_agent_rules_text(nonce)`（資料／指令分界＋引用鐵則）→ 工具清單；`_agent_rules_text` 已含「一句一筆放進 `sentences`」「每個事實句必須引用…原樣照抄」，與 `_POLICY_TEXT` 輸出契約段重複。`grep -n "_agent_rules_text\|policy_provider" rag-orchestrator/services/agent/prompt_assembler.py`
- 現行 `_POLICY_TEXT` 註解記錄：2026-09-05 `diag_variants` 6×4 實測，DSP-028 加長的契約段讓 mini 第一次就轉人（1/6 答）、回 R1＋一行 4/6 答；perf README R2 10.5%／R3 9.9%／R4 18.5% 答到率，判讀「提示詞越長越傾向先轉人；先轉人的題大綱其實有寫，屬模型判斷覆蓋的能力問題」。`grep -n "diag_variants" -A3 .kiro/specs/agentic-mcp-orchestration/eval/perf-agent-regression-20260905/README.md`
- `AgentOutput.kind ∈ {answer, ask, recommend, handoff}`；`Sentence.kind ∈ {fact, question, greeting, routing}`；`handoff_reason` 值域由 schema description 給（`sensitive_no_grounding`／`no_grounding`）；`agent_eval` 的 `answered = bool(answer) and kind not in {"handoff"}`（`ask`／`recommend` 算 answered）。`grep -n "kind: Literal" rag-orchestrator/services/agent/output_schema.py; grep -n "HANDOFF_KINDS =" rag-orchestrator/tools/agent_eval.py`
- 拒因回饋 `_reason_hint` 已明說「⛔ 不要因為被拒就改成 handoff」；`_SCHEMA_CAUSE_HINTS["ref_invalid"]` 說「原樣照抄整串」——4.4b 仍有 48／56 個三段式畸形 refs，代表回饋句無法治這個病灶（契約層問題，§5）。`grep -n "_REASON_HINTS\|ref_invalid" rag-orchestrator/services/agent/runtime.py`
- `persona_provider` 現不分岔（docstring 明寫留給後續）；`resolved_audience()` 值域 `prospect`／`property_manager`／`tenant`。
- 既有政策文斷言：`test_agent_policy_kb_outline_req.py::test_policy_text_drops_ban_and_states_outline_prefix_shape`（需 `kb.get`、`整節後再引用`、`outline:`；不含原禁句）、`test_identity_slots_contract_req.py::test_policy_text_defines_identity_slots`（需 `identity_source=entry`、`不得再詢問對方身分`、`identity_detail`）。
- 來源文：`inputs/kb3645-presales-dialogue-rules-20260906.md`（含例子與 JSON 輸出契約——⛔ 不得謄抄，只取判準改寫為定義；舊鏈 `conversational_rules.py` 亦 ⛔ 不複製）。

## 3. 非目標
不動 `_agent_rules_text`（指令區）；不動 DSP-029a 引用契約與 `resolve_refs`／nonce 檢查（§5-1）；不動 `_REASON_HINTS`／`_SCHEMA_CAUSE_HINTS`；不動敏感程式側與 `FactClass`／`SENSITIVE`（5.3）；不做 CTA／handoff 設定接線（5.2）；不改 schema `description`（結構層選項，§5-3）；不改題集、不改 K／門檻／內文鍵；不寫例子；不改 `output_schema.py`。

## 4. 驗收（容器內）
§1.2-4～10 全綠；`make audit` PASS；fresh verifier 主張：「政策文為三段定義且長度 ≤1,197／`⛔` ≤10、無例子、無與指令區重複句、保留 4.1／4.2 兩句；persona 三分支逐字快照；既有測試全綠」。**主驗收 §1.3 在業主核定義文之後另跑**（定義文就是 prompt，tasks 5.1 驗證＝[業主審核]）。

## 5. 待業主裁
1. **引用契約（DSP-029a）是否放寬**——4.4b 兩臂各 48／56 個三段式畸形 refs、`budget_exhausted` 18／20 回合。選項 (a) 維持（本片不動，5.1 重跑後看數字）；(b) 解析時若 nonce 缺但 `(來源§編號)` 在本回合 provenance 唯一可解，視為合法（削弱 DSP-029a 的防偽憑據，需重開 DSP-029a）。本片採 (a)，(b) 列為 5.1 重跑後的下一刀候選。
2. **長度上限 1,197 字／`⛔` ≤10** 作為硬約束（替代：允許 +10%）。
3. **pm／tenant persona 定義句**由本片草擬，隨定義文一併交你審（tasks 5.1 驗證＝業主審核定義文；⛔ 未核前不跑主驗收）。
4. 若重跑翻轉率仍 <50%：下一刀走結構層（schema `description` 承載判準、或換模型）而非再改提示詞——先在此登記，屆時再裁。
