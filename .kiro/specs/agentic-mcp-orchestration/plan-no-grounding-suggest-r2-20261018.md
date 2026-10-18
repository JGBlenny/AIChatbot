# 計畫：查無依據時點名缺什麼＋最接近方向追問（R2，2026-10-18，第 2 稿）

> 業主原話：「也 提示詞強調「只能依資料回答，不夠就說缺什麼」 試試看 ?」（2026-10-17）；R1 停點後選「撤回 R1，改做「查無就說缺什麼」」；點名方式選「程式引用使用者原話」；問「等等 系統裡「查無依據」 依樣網路上其他人是怎麼做? 最接近的方向追問 ?」後，對「點名缺什麼，再列出最接近的 2～3 個章節讓使用者點選：就是業界的「最接近方向追問」。多出來的工作是相關度門檻，以及做成可點選的按鈕。」回「這種」。
> 驗收清單：`.kiro/specs/agentic-mcp-orchestration/acceptance-no-grounding-suggest-r2-20261018.md`
> 第 2 稿：依 plan-verifier r1（REVISE 5 條）修訂，處置見 §9。

## 0. 現況（已對碼）

| 事實 | 查證 |
|---|---|
| 非敏感「查無依據」有兩個出口：①零查詢（本回合無任何有效查詢，`turn_context.zero_lookup`）⇒ 出口閘 `_apply_handoff_without_lookup` 改成 `ASK_TARGET_TEXT`「想處理哪一件事？講名稱或編號就可以。」（`kind=answer`、clarifying）；②查過仍 `no_grounding`（或 `llm_mentioned_handoff`）⇒ 固定轉人句 `PRESALES_HANDOFF_MESSAGE`（`kind=handoff`，前端掛「找真人」）。另有預算耗盡 `budget_exhausted` 固定句（`TurnAccumulator.build_fixed`） | `grep -n "^ASK_TARGET_TEXT\|^NON_SENSITIVE_HANDOFF_REASONS\|def _apply_handoff_without_lookup" rag-orchestrator/services/agent/exit_gates.py`；`grep -n "def zero_lookup\|def build_fixed" rag-orchestrator/services/agent/turn_context.py` |
| R1 探針實測（12 回合）：A（gpt-6-luna）N1 三輪＝`no_grounding` 1、`budget_exhausted` 2；N2 三輪皆零查詢出口；B（gpt-oss）N1 兩輪零查詢出口、一輪模型作答「…未提供 Apple Pay 付款方式」（無據推論）；N2 三輪皆零查詢出口（模型自報 compliance 被推翻） | `~/jgb-archive/bedrock-eval-20261017/r1/N1_A.json`、`N2_A.json`、`N1_B.json`、`N2_B.json`（`state`、`snap.handoff_reason`、`snap.violations`） |
| 每回合程式已選 K=5 候選章節（`candidate_selector.Selection.scores` 有分數）；`runtime._select_outline` 的 `sel_meta`／`TurnInputsSnapshot` 目前不帶分數 | `grep -n "class Selection\|scores:" rag-orchestrator/services/agent/canon/candidate_selector.py`；`grep -n "class TurnInputsSnapshot" rag-orchestrator/services/agent/turn_context.py` |
| ⚠️ 既有決議 1：候選選取**刻意不設分數門檻** | `candidate_selector.py` docstring「為什麼沒有分數門檻」 |
| ⚠️ 既有決議 2：`ASK_TARGET_TEXT`「單一句、⛔ 無任何插值（同 `SCOPE_EXIT_TEXT` 的紀律——帶物件名稱等於用回話的差別揭露存在性）」 | `exit_gates.py` `ASK_TARGET_TEXT` 上方註解 |
| ⚠️ 既有決議 3：敏感五類一律固定句轉人（DSP-009）；零查詢出口為 Plan 9.11 D（業主 2026-09-24 核可）；出口閘「順序即契約」、⛔ 改閘簽名 | `.claude/DECISIONS.md` DSP-009；`exit_gates.py` `EXIT_GATES` 註解 |
| 前端契約：`kind=handoff` 的 `answer` 是固定轉專人句、掛「找真人」、`expects=none`（不等輸入）；`quick_replies` 有值就渲染成按鈕、點了以 `value` 原字串當下一則 `message` | `docs/api/jgb2-web-assistant-integration.md` §8；`turn_context.py` `default_outcome` |

### 0.1 業界做法與本計畫的對照（設計前查證；渲染＝以 web-drive 開官方頁取原文）

| 業界做法 | 來源 | 本計畫 |
|---|---|---|
| 找不到可信內容時：提供現有來源中最接近的內容、表達不確定、請客人說清楚 | Intercom Fin 官方說明「Share context from available sources」「Express uncertainty」「Attempt to answer if possible, or ask the customer for clarification」（已渲染） | **照做**：情形 A／B 有選項時列最接近章節＋追問；樣板句表達不確定／沒找到 |
| 無流程或文件可用時走 cannot-handle 備援（請換說法／告知找不到） | Rasa Conversation Patterns「Activate cannot handle (fallback) pattern if no flow or relevant documents apply」（已渲染）；「請換說法」細節僅搜尋摘要 | **照做**：無選項時「可以換個說法，或講名稱、編號」 |
| 備援要給客人另一條路，不只承認失敗 | Freshworks「should include an alternate option … not just be an admittance of failure」（已渲染） | **照做**：按鈕選項；無選項的查過回合保留「找真人」 |
| 一律保留真人出口；連續兩次備援後轉真人 | 業者部落格（搜尋摘要，**未渲染**，可信度低） | **待業主決定**：情形 A／B 降級為追問時本回合無「找真人」按鈕（前端契約：按鈕只掛在 `kind=handoff`）；可選做法＝同一會話連續第二次落入本出口 ⇒ 不再降級、維持轉人。未納入本稿範圍，列 §5 |
| 記錄觸發備援的問句以找知識缺口 | 業者說明頁（搜尋摘要，未渲染） | **部分照做**：trace 記 `no_grounding_suggest:<A|B>` 次數可統計；⛔ 記原話（隱私紀律），缺口分析另議 |

## 1. 終點指標

| 指標 | 現值（R1 探針 12 回合） | 預期 |
|---|---|---|
| 探針回覆點名使用者問的那一項（分母＝全部探針回合） | A 0／6；B 1／6（唯一點名的那回合是無據推論） | 兩模型各 ≥5／6，且無據斷言 0 |
| 按鈕選項與問題相關（保留題，盲判） | 無此功能 | ≥80% |

（預算耗盡回合不套用樣板——見 §3.4——故預期為 ≥5/6 而非 6/6。）

## 2. 第 0 步：門檻校準（實作前，不改 repo）

1. **校準集**（定門檻用）：查無依據／含糊類同母體查詢 ≥30 句——正本無此主題的問句 ≥20 句（每句以 `grep -c` 於 `rag-orchestrator/canon/jgb.json` 證明關鍵詞 0 筆，附正對照）＋含糊句 ≥10 句。**保留集**（驗收 #2 用，不參與定門檻）：另 ≥10 句同母體，與校準集無交集。v2 可作答題至多當對照，⛔ 進門檻計算。題目清單存 `~/jgb-archive/bedrock-eval-20261017/r2/step0_queries.json`（標註 calib／holdout）。
2. 在評估容器以既有 `CandidateSelector`、業者身分、**照 `runtime._candidate_query` 組查詢字串**（單輪即當句），算每句 top-5 候選、標題、分數，存 `r2/step0_candidates.json`。
3. blind-judge 逐對判「這個章節是不是回答這個問題的合理方向」（相關／不相關）；每批混入誘餌對（明顯相關、明顯無關各 3），**該批 ≥5/6 才採用，未達即整批重判一次，仍未達 ⇒ 停**。
4. 只用校準集算各分數門檻下的「列出選項相關率」與「至少能列 1 項的比例」，產出 `r2/STEP0.md`（分列校準集／保留集題目與誘餌命中數），**交業主選門檻值**（建議值＝相關率 ≥80% 的最低分數）。⛔ 主會話自行定門檻。找不到相關率 ≥80% 的門檻 ⇒ 停、交業主。

## 3. 做什麼（門檻核可後）

**插入點（唯一）**：`exit_gates.finalize` 中，`EXIT_GATES` 全部跑完之後、`AgentSession.end_turn`／handoff cache 寫入與 `_emit_agent_decision` 之前，新增後處理 `_apply_no_grounding_suggest(result, agent_state, user_message, acc)`。⛔ 加入 `EXIT_GATES`、⛔ 改任何閘的簽名或順序；它只看閘跑完後的**最終**結果。

**套用條件（封閉欄位，全部成立）**：
- 情形 A（零查詢出口）：最終 `answer == ASK_TARGET_TEXT` 且 `trace.violations` 含 `handoff_without_lookup`（`_apply_handoff_without_lookup` 寫入的既有標記）；或
- 情形 B（查過仍查無）：最終 `kind == "handoff"`、`trace.handoff_reason ∈ NON_SENSITIVE_HANDOFF_REASONS`、`fact_class` 不在敏感五類、**非** `zero_lookup`；
- 且：`SELECT_SCOPE_KEY is None`、非文件回合、使用者當句消毒後非空。

**分數傳遞**：`TurnInputsSnapshot` 新增 `candidate_scores: dict`（只限本回合 `candidate_ids`），由 `_select_outline` 寫入；⛔ 進 trace／`decision_snapshot`（`build_trace` 不讀它）。

**樣板（程式產出，⛔ 交模型改寫）**：`{原話}`＝使用者當句過 `sanitize_data_piece`、去句尾標點與空白，>30 字截斷加「…」。`{選項}`＝本回合候選中分數 ≥ 門檻者依分數取前 3 的細目問句標題（正本原文、過 `sanitize_data_piece`）。
- 情形 A（**未查詢**語義，⛔ 說「沒有找到」）：
  - 有選項：「我還不確定「{原話}」指的是哪一部分。最接近的是下面幾項，是想問這些嗎？」＋`quick_replies`（`label`＝`value`＝問句標題）；`kind=answer`、`outcome=clarifying`、`expects=choice`。
  - 無選項：「我還不確定「{原話}」指的是哪一部分；可以換個說法，或講名稱、編號。」；`expects=text`。
- 情形 B（**查過**語義）：
  - 有選項：改為 `kind=answer`、`outcome=clarifying`、`expects=choice`、`handoff=None`（與 Plan 9.11 D 把零查詢轉人降級成追問同一做法）：「我在資料裡沒有找到關於「{原話}」的說明。最接近的是下面幾項，是想問這些嗎？」＋`quick_replies`。
  - 無選項：維持 `kind=handoff`（前端照舊掛「找真人」、`expects=none`）；`answer` 與 `handoff["message"]` 一起改為「我在資料裡沒有找到關於「{原話}」的說明，幫您轉專人——點下方的『找真人』。」。
- ⇒ **按鈕只出現在 `kind=answer` 的追問回合**，⛔ 與 `kind=handoff` 同時出現（符合前端契約，不改契約文件）。

**3.4 不套用**：敏感五類（含模型自報敏感未被推翻者）、`budget_exhausted`（模型未能在時限內作答，「沒有找到」不為真）、`NO_DATA_TEXT`、`NO_JUDGEMENT_TEXT`、確認卡、程式追問、`select:`、文件回合。

**trace**：記固定字串 violation `no_grounding_suggest:<A|B>`、`no_grounding_suggest_count:<n>`；⛔ 記原話或標題。

## 4. 存在性揭露（既有決議 2）的處置

- 樣板插入的是**使用者自己剛說的話**與**正本（產品說明）章節標題**，不含任何租戶資料（物件、合約、帳單名稱或編號）。
- 是否走到本出口、以及 `{原話}` 的內容，都不取決於「該名稱在系統中是否存在」：情形 A 本回合沒有查詢；情形 B 由模型自報查無觸發——同一句話不論系統裡有沒有對應資料，出的句型相同（差別只在模型作答與否，這是既有行為，非本片引入）。
- 選項來自 `CandidateSelector` 的可見子集（已依受眾與業態過濾），只列正本問句標題。
- 仍屬既有紀律的放寬，送 **security-reviewer** 唯讀審查後再判定就緒；結論與處置寫入 §9.2。

## 5. 不做

- 改候選選取、Verifier、政策文、補充鐵則（R1 已撤回）、前端契約文件。
- `NO_DATA_TEXT`、`NO_JUDGEMENT_TEXT`、`budget_exhausted`。
- 售前（prospect）：同一後處理會套用（出口共用），驗收只量業者身分；若需排除另裁。
- 「連續第二次落入本出口改轉真人」（§0.1 業界線索、未渲染）：待業主決定是否另案納入。

## 6. 擁有檔案與執行

- 擁有：`rag-orchestrator/services/agent/exit_gates.py`（後處理與樣板常數）、`runtime.py`（`_select_outline` 寫分數）、`turn_context.py`（`TurnInputsSnapshot.candidate_scores`）、`rag-orchestrator/tests/unit/agent/` 新測試、`tests/fixtures/agent/pipeline_golden.json`（只限出口文字、`kind`、`quick_replies`、`outcome` 的預期變動，逐案列出）。
- 實作：依 security-reviewer 結論決定 `executor` 或 `security-executor`；收尾 fresh verifier。

## 7. 回退

`git revert`；或後處理改為直接 return（樣板不套用）。

## 8. 預算與停點

- 第 0 步 0.4M；實作與驗證 1.2M；模型費用 < US$1。
- 停點：第 0 步誘餌重判仍未達或找不到 ≥80% 門檻 ⇒ 停；驗收任一項未過 ⇒ 停、回報；⛔ 在本片內改候選選取、Verifier、閘順序或前端契約。

## 9. 審查處置

### 9.1 plan-verifier r1（REVISE 5 條）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | 未涵蓋 `budget_exhausted`；驗收可空集合通過；§0「12 次全落」不實 | FIX：§3.4 明列不套用並附理由；§1 預期改 ≥5/6；§0 逐筆改正；驗收分母＝全部探針回合 |
| 2 | 插入點與 `quick_replies` 殘留 | FIX：§3 唯一插入點＝`finalize` 閘後；封閉條件；分數經 `TurnInputsSnapshot` 不進 trace；`handoff["message"]` 同改；驗收加三種回合 `quick_replies` 為空 |
| 3 | `kind=handoff`＋按鈕與前端契約衝突 | FIX：按鈕只出在 `kind=answer` 追問回合；情形 B 有選項時降級為追問（同 9.11 D），無選項維持轉人無按鈕 |
| 4 | 第 0 步樣本母體與循環驗證 | FIX：§2 校準集／保留集分離、同母體、誘餌條件與重判、照 `_candidate_query` 組查詢 |
| 5 | 違反 `ASK_TARGET_TEXT` 無插值紀律；零查詢說「沒有找到」不實 | FIX：§4 揭露與理由＋送 security-reviewer；情形 A 改「我還不確定…指的是哪一部分」 |

### 9.2 security-reviewer

（待填）

## 10. 撤銷（2026-10-18）

業主問「列出的按鈕 業界不是這樣吧?」——主會話更正：Intercom Fin 原文是「Share context from available sources」（以相關內容作答、表達不確定、請客人說清楚），列文章按鈕是較早一代（Zendesk 舊 Answer Bot 文章推薦）；本稿把 Fin 說成列按鈕，是因候選清單現成而包裝成業界做法。業主改選「Fin 式：部分回答＋說缺什麼＋追問」⇒ 本計畫撤銷、未實作，由 `plan-partial-answer-gap-r3-20261018.md` 取代。security-reviewer（第 2 稿）結論：無 P0／P1，P2 兩條（情形 B 在逾時／上游失敗時說「沒有找到」為假話；情形 B 有選項未改 `trace.final_kind` 致 handoff cache 重播出按鈕），隨撤銷一併不處理；其中「沒查成⛔ 講成不存在」的紀律於 R3 同樣適用。
