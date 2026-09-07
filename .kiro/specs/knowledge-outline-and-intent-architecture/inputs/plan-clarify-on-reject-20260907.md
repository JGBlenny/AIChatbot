# ⛔ 已否決（業主 2026-09-07「給選項的追問 我不要」）——Plan：首拒改選項式追問（agent 售前路徑；業主 2026-09-07「首拒改選項式追問，出 Plan」）

> 前置決策：DSP-035（開發基線＝gpt-5-mini＋`low`＋`AGENT_BUDGET_REWRITES=0`）。本 Plan 是它的延伸：重寫預算耗盡時（基線下＝第一次被 Verifier 拒），**不再一律走固定轉人句**，而是由程式**決定性**組一句選項式追問，選項＝這回合候選的細目標題；使用者點選後下一回合只帶那一節作答。⛔ 不叫模型生成追問、⛔ 不改提示詞、⛔ 不改 Verifier 尺、⛔ 不改 K／門檻。
> 依據（三輪探針，首拒回合 gold 在候選內）：`low` 13/17、預設 21/30、`minimal` 40/56 ⇒ 選項式追問七成以上會把正確章節擺在使用者面前。
> 版本：v3（2026-09-07）。第 1 輪 REVISE 三項 blocker 全 FIX：`QuickReply` 形狀、鎖定落點、評估指標資料路徑；另移除『找真人』末項（repo 內無對應快捷語處理，不造假的可點選項）。第 2 輪 REVISE 兩項 P2 全 FIX：鎖定比對改**兩側** `_norm`；評估工具合成回合必須在大綱仍在 state 上時發出、`miss_kind != "hit"` 記量測失效不計入。第 3 輪（closing）REVISE 一項 P2 FIX：既有彙總指標母體排除追問列與合成列（§1.4 末項、§3.2），否則 `kind=ask` 的追問列被 `answered=True` 吃進答到率、`fixed_rate` 虛降，與 DSP-035 基線失去可比性。**依主 session 政策，closing review 後不再自動送審；本 v4 交業主裁：核准或指定再審一輪。**

## 0. 摘要（slice 一片：`CLR-1`）

| 項 | 內容 |
|---|---|
| ID | `CLR-1` 首拒選項式追問＋下一回合單節鎖定＋評估工具追問後續 |
| 結果 | 重寫預算耗盡且候選機制命中時，回合結果 `kind="ask"`、固定追問句、`quick_replies`＝候選細目標題（既有 `QuickReply{text,value}` 形狀、候選序）；使用者送回的 `value` 與某候選的 `value` **逐字相等**（NFKC＋strip）時，下一回合組裝用的大綱＝只有該節＋toc；敏感題、無候選、降級臂、鎖定回合再被拒 ⇒ 行為**不變**（固定轉人句） |
| 非目標 | LLM 生成追問；追問句進提示詞；改 `agent_rules.py`；改 Verifier／rules json；改 `FineIndex`／`CandidateSelector`（K、鍵、門檻）；新增 REST／MCP 回應欄位（沿用既有 `QuickReply` 契約與 `quick_replies` 欄）；新增 `TurnTrace` 欄位；prod env；舊鏈；『找真人』快捷語（repo 無對應處理，⛔ 不加） |
| 擁有者 | executor（單片、單人）；fresh plan-verifier 前置、fresh verifier 後置（跨元件：runtime＋state＋eval 工具） |
| 前置 | DSP-035 已落（`3ff0d1e0`）；探針 54 小測產物在本機 `rag-orchestrator/.probe-run-54/smoke` |
| 預算 | 程式 ≤ 半天；量測探針 55：1 rep、`on` 臂、`--clarify-followup`，≤ $0.35（合成後續回合最多 +17 回合） |
| 停損 | 單元測試兩輪修不綠 ⇒ 停；探針 55 追問回合敏感漏 ≥1 ⇒ 停下交業主；gold ∈ 選項 < 50% ⇒ 停（機制前提不成立） |

## 1. 契約（executor 必守）

### 1.1 觸發條件（`services/agent/runtime.py:run_turn` 的 Verifier 拒絕分支）

現行：`if counters.rewrite_exhausted(self.budget): return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)`。

改為：耗盡時先判 `_should_clarify(verdict, out, sel_meta, agent_state)`，**全部成立**才走追問，否則維持 `_build_fixed("budget_exhausted")`（預設 `max_rewrites=2` 時同樣適用：兩次重寫都拒才到這裡；本 Plan ⛔ 不改程式預設值，基線靠 env 0）：

1. `AGENT_CLARIFY_ON_REJECT` env 不是 `"0"`（預設開；只作回滾開關）。
2. `sel_meta is not None` 且 `sel_meta["miss_kind"] == "hit"` 且 `sel_meta["candidate_ids"]` 非空（降級臂 `index_unavailable`／`none_visible`／`no_candidate` 與「無候選機制」一律不追問）。
3. 不是敏感：`verdict.reason != "SENSITIVE_TOPIC"` 且 `out.fact_class not in SENSITIVE`（`services.presales_gate.SENSITIVE`）且 `out.kind != "handoff"`（模型自判轉人被拒＝schema 問題，仍走固定句）。
4. 本回合不是鎖定回合（`agent_state.get("clarify_pick")` 為 None；避免「鎖定單節仍被拒 ⇒ 再追問同一節」的迴圈）。

### 1.2 追問回合的輸出（`_build_clarify(candidate_ids)`，與 `_build_fixed` 同層的閉包）

- `kind="ask"`、`handoff=None`。
- `answer`＝模組常數 `CLARIFY_MESSAGE`（一句、無例子、無標題內嵌、無格式化占位）：「我想先確認您要了解的是下面哪一項，請點選；都不是的話，請再多描述一點您的問題。」——標題**只放 `quick_replies`**，⛔ 不拼進 `answer`（`answer` 會進 `dialog` 歷史與 SSE）。
- `quick_replies`＝`[{"text": title, "value": title} for id in candidate_ids]`，**與 `routers/chat.py:QuickReply` 同形狀**（`text`／`value` 必填、`style` 省略）；`title` 從**這回合組裝用的 `outline`**（`CandidateOutlineDoc`）以 id 查 `OutlineSection.title`。查不到的 id ⇒ 跳過並記 violation `clarify_title_missing`；全部查不到 ⇒ 不追問、走固定句。`value` 與 `text` 同一字串＝標題**原字串**（⛔ 不預先正規化；§1.3 比對時**兩側**現算 `_norm`）。
- `trace`：`final_kind="ask"`、`handoff_reason=None`、`violations` 追加 `"clarify_from_candidates"`（`violations` 為自由字串 list、無封閉值域——executor 對 `shadow.py`／`trace_view.py` 再確認一次，若有白名單即列入）；`candidate_ids`／`winning_key_kind`／`miss_kind` 照本回合值。
- `_finalize(..., is_fixed=True)`：`fixed_streak` 照算（`routers/agent_entry.py:_persist` 連續三次固定句 ⇒ `fallback_old_chain` 的既有規則不變，追問視同固定句）；`handoff_cache` 不寫（`_finalize` 只快取 `final_kind=="handoff"`）。
- `agent_state["clarify_pending"] = {"candidate_ids": [...], "values": [...]}`（`values`＝標題原字串，供顯示對照；只含細目 id 與標題字串，⛔ 不含使用者原句、⛔ 不含模型輸出）。`_persist` 只 pop `outline`，`clarify_pending` 隨 state 落地（小、無原文）。

### 1.3 下一回合的鎖定（落點＝`_select_outline`，⛔ 不在 `run_turn` 另組大綱）

- `run_turn` 在呼叫 `_select_outline` **之前**：`pending = agent_state.pop("clarify_pending", None)`（無論命中與否、開關開關與否都 pop，只活一回合）；`pick_id = None`；若 `pending` 且存在索引 i 使 `_norm(user_message) == _norm(pending["values"][i])`（**兩側都 `_norm`**，`_norm`＝`unicodedata.normalize("NFKC", s).strip()`；標題本身含全形空白（U+3000）或前後空白時仍可命中；⛔ 不做子字串、⛔ 不做相似度——這是「點選」的語義）⇒ `pick_id = pending["candidate_ids"][i]`（多個相等取最小 i）。
- `_select_outline(identity, outline, user_message, dialog, violations, *, pick_id=None)`：新增關鍵字參數。函式內：
  - `selector is None`／`outline is None`／canon 不符 ⇒ 原樣回傳（`sel_meta=None`），**鎖定不套用**。
  - 正常臂：照常 `selector.select(...)`（trace 的 `candidate_ids`／`winning_key_kind`／`miss_kind` 保持真實選取結果）；三條降級臂（`sel is None`／`none_visible`／`no_candidate`）**鎖定不套用**、回傳與現行逐字節相同。
  - `miss_kind=="hit"` 且 `pick_id` 非 None ⇒ 組裝用大綱改為 `CandidateOutlineDoc.from_selection(outline, {"candidate_ids": [pick_id]}, toc)`（`outline` 在此函式內就是 `agent_state["outline"]` 的**完整** `OutlineDoc`、`toc` 是函式內現算的區域變數——兩個引數都在手上）；`violations` 追加 `"clarify_pick_applied"`；`sel_meta` 照真實選取回（⛔ 不改 `winning_key_kind` 值域）。`pick_id` 不在 `outline.sections` ⇒ `from_selection` 拋 `ValueError`：捕捉、記 `clarify_pick_missing`、退回正常候選（⛔ 不炸回合）。
- `run_turn` 在 `pick_id` 非 None 時設 `agent_state["clarify_pick"] = pick_id`，回合結束（任何出口）前 pop；§1.1-4 讀它。
- 鎖定回合的 `_candidate_query` 不變（`user_message`＋上一則 user）——標題會進查詢字串，正常。

### 1.4 評估工具（`tools/agent_eval.py`）

- 新旗標 `--clarify-followup`（預設關）：`outline-probe` 集、`--chain agent` 下，某回合結果 `kind=="ask"` 且 `"clarify_from_candidates" in trace.violations` 時，工具**合成一個後續回合**：若該 turn 的 `gold` 任一 id 對應的候選 `value` ∈ `quick_replies`（以 `candidate_ids` 對 `gold` 取交集、再取對應 `value`）⇒ 以該 `value` 原字串為 `q` 再叫一次 `run_turn`（同 state），記錄為 `turn=<原 turn>`、JSONL 新鍵 `synthetic_pick: true`；否則不合成、只在原回合記 `pick_gold_in_options: false`。**合成回合必須在 `state["agent"]["outline"]` 仍在時發出**：`_run_scenario_agent` 現行在 `run_turn` 之後立刻 pop `outline`，合成回合要插在該 pop **之前**（或呼叫前重跑 `_set_outline_on_state(state, outline_doc)`），否則 `_select_outline` 走 `outline is None` 臂、鎖定與候選全部靜默失效。合成回合的 `EvalRecord` 若 `miss_kind != "hit"` ⇒ 記為**量測失效**（新封閉欄 `synthetic_invalid: bool`），⛔ 不得以 `answered=False`／`gold_in_candidates=False` 計入任何比率；報表「追問」節列出失效筆數。⛔ 不對敏感 stratum 合成（敏感題被追問即 `sensitive_leak` 照現行尺記）。
- `EvalRecord`／`to_jsonl_dict` 新增四個**封閉**欄位：`clarify: bool`（本回合是否追問）、`pick_gold_in_options: Optional[bool]`（追問回合才有值）、`synthetic_pick: bool`、`synthetic_invalid: bool`（合成回合且 `miss_kind != "hit"`）；`_NO_VERBATIM_KEYS` 斷言不動（四欄皆非原文）。
- `render_report_md` 新節「追問」，指標**只用 JSONL 既有與上述四欄**：追問回合數、gold ∈ 選項率、合成回合答到率（`answered`，分母排除 `synthetic_invalid`）、合成回合 `gold_in_candidates` 率（同分母）、合成回合量測失效筆數、追問回合與合成回合 `latency_ms` p50、追問回合中 `sensitive_expected` 數。**「引用 ∈ gold 率」⛔ 不列為工具交付**（refs 只在 `--dump-texts` 旁路；離線由主 session 的 `probe_analyze.py` 沿 H1 既有做法從 dump 解出，不進 `EvalRecord`）。
- **既有指標母體（封閉規則）**：`compute_hardlines`／`compute_stability`／`render_report_md` 既有各節（答到率、`fixed_rate`、`gold_in_candidates_rate`、敏感／禁詞硬線等）的母體＝`clarify == False and synthetic_pick == False` 的列；追問列（`kind="ask"`、`answer==CLARIFY_MESSAGE`）在 `EvalRecord` 上 `answered=False`（⛔ 不因 `answer` 非空而算答到），且與合成列一律**只進「追問」節**。報表同時列「既有指標母體列數」與「追問列＋合成列數」，兩者相加＝JSONL 總列數（自證）。這樣探針 55 的既有指標與 DSP-035 基線（54 小測，答到 17/49）同母體可比。
- `--dump-texts` 對合成回合照常 dump（`idx`／`turn`／`rep` 同原回合＋`synthetic_pick`）。
- invariant 34 檢查器（`scripts/audit/checks/canon_phrasing_frozen_disjoint.py`）：合成回合的 `q` 是正本標題，**不是**題集問句，⛔ 不進題集檔；檢查器讀的是題集 JSON，不受影響（executor 以 `make audit` 證）。

### 1.5 不變量（測試必證）

- `CLARIFY_MESSAGE` 為常數、不含 `{`／`%`／f-string 占位。
- `quick_replies` 的 `text`／`value` 只來自 `OutlineSection.title`；模型輸出（`out.sentences[*].text`）任何字串不得出現在 `quick_replies`／`answer`。
- 敏感題（`SENSITIVE_TOPIC` 或 `fact_class ∈ SENSITIVE`）被拒 ⇒ 仍是固定轉人句、`kind="handoff"`、`handoff_reason="budget_exhausted"`。
- 無候選（`sel_meta is None` 或 `miss_kind != "hit"`）⇒ 與現行逐字節相同。
- `clarify_pending` 只活一回合；鎖定回合被拒 ⇒ 固定句、不再追問；`clarify_pick` 回合結束必 pop。
- `AGENT_CLARIFY_ON_REJECT=0` ⇒ 全部路徑與現行相同，且殘留 `clarify_pending` 仍被 pop。
- 追問回合的 `TurnResult` 經 `routers/chat.py:_conversational_to_response`（非串流 REST 路徑）建 `VendorChatResponse` **不拋 `ValidationError`**。

## 2. 測試（TDD，先紅後綠；容器內 `scripts/run-tests.sh unit`）

新檔 `tests/unit/agent/test_runtime_clarify_on_reject_req.py`（沿 `test_runtime_req.py` 的假 provider／假 verifier／假 selector 夾具；`Budget(max_rewrites=0)` 或 env）：

1. 首拒＋候選命中 ⇒ `kind=="ask"`、`answer==CLARIFY_MESSAGE`、`quick_replies==[{"text":t,"value":t} for t in 五節標題]`、`trace.final_kind=="ask"`、`"clarify_from_candidates" in violations`、`handoff is None`、`clarify_pending=={"candidate_ids":[…],"values":[…]}`。
2. 首拒＋`SENSITIVE_TOPIC` ⇒ 固定句（正對照：同夾具 reason 換 `QUOTE_NOT_COVERING` 就變 ask）。
3. 首拒＋`fact_class="pricing"`（非 `SENSITIVE_TOPIC` 拒因）⇒ 固定句。
4. 首拒＋`sel_meta is None`／`miss_kind="index_unavailable"` ⇒ 固定句、`clarify_pending` 不寫。
5. 下一回合 `user_message` 與第 2 個 `value` 在 `_norm` 後相等（夾具：**標題本身含 U+3000 全形空白**、使用者回傳前後帶空白＋全形字）⇒ 組裝 outline 只有該節＋toc（假 assembler 抓 `outline.sections` 的 id 集合斷言）、`"clarify_pick_applied" in violations`、trace `candidate_ids` 仍是真實選取（假 selector 回 5 個）、`clarify_pending` 已 pop、回合結束 `clarify_pick` 已 pop。
6. 下一回合 `user_message` 不等於任何 `value` ⇒ 正常候選、`clarify_pending` 已 pop、無 `clarify_pick_applied`。
7. 鎖定回合再被拒 ⇒ 固定句（不追問第二次）。
8. `AGENT_CLARIFY_ON_REJECT=0` ⇒ 案 1 輸入得固定句；殘留 `clarify_pending` 仍被 pop。
9. 標題查不到（候選 id 不在 outline.sections）⇒ 跳過該項、記 `clarify_title_missing`；全部查不到 ⇒ 固定句。
10. 鎖定回合落在 `sel_meta is None`／`index_unavailable` ⇒ 與未鎖定時 outline 一致、無 `clarify_pick_applied`（鎖定不套用）。
11. `pick_id` 不在 `outline.sections` ⇒ `clarify_pick_missing`、退回正常候選、回合不炸。
12. 不變量：`CLARIFY_MESSAGE` 無占位；`quick_replies` 與 `out.sentences` 任何 text 無交集；`_norm` NFKC＋strip（⛔ 不小寫化、不去內部空白）；正對照：案 5 夾具改成不相關字串 ⇒ 正常候選、無 `clarify_pick_applied`。
13. 追問回合 `TurnResult` 走 `routers/chat.py:_conversational_to_response` 建 `VendorChatResponse` 不拋 `ValidationError`，且 `quick_replies[i].value` 等於候選標題原字串、`_norm(value)` 與 §1.3 的比對鍵相等。

`tests/unit/agent/test_agent_eval_req.py` 追加：假 runtime 第 1 回合回 ask＋`clarify_from_candidates`＋`quick_replies` 含 gold 標題 ⇒ `--clarify-followup` 合成第 2 回合、JSONL 兩列（`synthetic_pick` false／true、`pick_gold_in_options` true）；gold 不在選項 ⇒ 不合成、`pick_gold_in_options=False`；敏感 stratum ⇒ 不合成；**合成回合收到的 `state["agent"]["outline"]` 非 None 且該列 `miss_kind=="hit"`**；正對照：故意不塞 outline 的夾具 ⇒ 該列 `synthetic_invalid=True`、報表失效筆數＝1、不計入 gold ∈ 候選率；`render_report_md` 「追問」節每項指標有值；`_NO_VERBATIM_KEYS` 斷言通過；**母體案**：夾具含 1 列追問＋1 列合成＋若干正常列，`compute_hardlines(...)["agent"]` 的 answered 分子／分母與 `fixed_rate`、`compute_stability` 的 `answered_rate`／`gold_in_candidates_rate` 與「只餵正常列」逐值相同；報表既有節母體列數＋「追問」節列數＝總列數。

既有測試：`test_runtime_req.py` 的 `budget_exhausted` 案在預設 `max_rewrites=2` 下仍應成立；若既有夾具讓 `miss_kind=="hit"`，以 `AGENT_CLARIFY_ON_REJECT=0` 或無候選夾具維持其斷言——**executor 不得改既有斷言語義**，只調夾具。

## 3. 驗收（fresh verifier 對「主張」核）

主張：「重寫預算耗盡且候選命中、非敏感時，回合回選項式追問（`QuickReply` 形狀、標題只來自大綱），使用者送回逐字相等的 `value` 後下一回合組裝用大綱只有該節；敏感／無候選／降級臂／鎖定回合再拒／回滾開關關閉時，行為與現行逐字節相同。」

1. 單元 `scripts/run-tests.sh unit tests/unit/agent/ -q` 全綠；`make audit` PASS。
2. 探針 55（量測，非門檻收案）：`docker compose -f docker-compose.dev.yml run -d --name probe55 -e AGENT_MODEL=gpt-5-mini -e AGENT_REASONING_EFFORT=low -e AGENT_BUDGET_REWRITES=0 -e OPENAI_TIMEOUT_S=60 rag-orchestrator sh -c 'python3 tools/agent_eval.py --set outline-probe --chain agent --provider openai --candidates on --repeat 1 --dump-texts --clarify-followup --out /app/.probe-run-55/on; echo on_rc=$?; echo ALLDONE'`。報：追問回合數（預期 ≈ 首拒 17 減敏感／無候選）、gold ∈ 選項率（**前提門 ≥ 50%**，預期 ≈ 76%）、合成回合量測失效筆數（**必須 0**，否則工具有錯、數字作廢）、既有指標母體列數（預期 49）＋追問／合成列數（相加＝總列數）、既有答到率（同母體對 54 基線 17/49 比）、合成回合答到率、追問回合 p50（預期 ≈ 單次回合 5 s）、敏感漏（**0**）、`budget_exhausted` 列數（預期只剩無候選／敏感／鎖定回合被拒）。離線：主 session 以 `probe_analyze.py` 從 dump 解合成回合「引用 ∈ gold」；合成回合放行句併入 H4 封包、兩判者盲標。
3. verifier 額外探針：`routers/agent_entry.py` SSE metadata 帶 `quick_replies`（讀碼＋案 13）；`clarify_pending` 經 `_persist` 落地後下一回合仍可讀（in-memory store）。

## 4. 回滾

`AGENT_CLARIFY_ON_REJECT=0`（env）；或 revert 單一 commit。關閉狀態下 `clarify_pending` 仍被 pop（§1.3 第一步不受開關影響），⛔ 不留殭屍鍵。

## 5. 風險與待裁

- **追問句措辭**是使用者可見文案，本 Plan 給預設句；業主可改字，⛔ 不改語義（一句、無標題內嵌）。
- **無『找真人』選項**：使用者若都不是，依句子提示再描述；下一回合走正常路徑。若探針顯示「都不是」情境多，另案裁是否加專屬出口（需先有上游處理）。
- **標題當查詢**：鎖定回合仍跑 `_select_outline`，trace 記真實選取；若真實選取沒把 pick 排第一，是 3.x 標題鍵的觀察點，不影響本回合。
- **`fixed_streak`**：追問計入固定句連擊；三次 ⇒ 回退舊鏈（既有）。探針 55 報追問觸發回退的回合數；頻繁則另案裁。
- 本 Plan **不改 `max_rewrites` 程式預設**（仍 2）；預設是否改 0 待探針 55 後與 DSP-035 一起裁。
