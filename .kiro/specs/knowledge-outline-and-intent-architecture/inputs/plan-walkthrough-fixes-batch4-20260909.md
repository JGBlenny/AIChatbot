# Plan：走查回修第四批（V1–V5）— 2026-09-09（第 3 稿：security-reviewer r1 八條＋plan-verifier r1 兩條已處置）

> 來源：line-bot 第二輪走查驗收（帳本 §1n；39 屏 0 轉人）——好了 H3／H4，半好 H1／H5，H2 變形（退回開場白），新冒出三件：記憶段被當該戶全部紀錄、`context` 開場白被當使用者的話、首句 60 s 逾時。
> 紀律同前三批：契約／schema／狀態機／出口閘門／正本定義層，⛔ 不寫特例；提示詞只寫定義不舉例；程式一筆、文件一筆；⛔ 不 push。

## 0. 程序封套 P-WT4

| 欄 | 內容 |
|---|---|
| 結果 | line-bot 第二輪劇本重放（現場報修 11 步、逾期帳單 10 步、連續對話 14 步；帶 `context`）：「這戶還有沒有別的單」查修繕單並含 8591（3/3）；「要不要打電話」「上次報修修好了沒」有前文時依前文答或查、⛔ 不退回開場白（3/3）；「延三天」原到期日已過 ⇒ 卡上新到期日＝今天＋3（3/3）；restart 後「我剛剛問了什麼」⇒ 說使用者還沒說過話、⛔ 不把畫面提示當使用者的話（3/3）；追問不附捏造的範例名稱；線③ 12/12；0 轉人。 |
| 非目標 | 催繳草稿工具；「建立帳單」格名與能力不對稱（line-bot 側）；換成員身分抓全量替身；極性回合層級比對（另列 V6 候選）。 |
| 切片 | V1 記憶段語義（executor；只動 `completed_actions.py`）→ V2 有前文的零查詢（executor；`runtime.py`）→ V3 延 N 天基準（security-executor；`confirm_card.py`／`tools/confirm.py`／`tools/action.py`）→ V4 畫面提示措辭＋**全部政策句**（executor；`agent_rules.py` **獨佔**，含 V1 那一句；plan-verifier r1 #1）→ V5 冷啟逾時（runbook）。V1／V3／V4 檔案互斥可並行；V2 依賴 V1 的記憶段標題。 |
| 驗收 | §6：單元 → smoke-rag（`grounding_observe`）第二輪劇本 3 輪＋線③ → fresh verifier → 部署。 |
| 回滾 | 各切片單一 commit revert；`agent_rules.py` 只由 V4 動，revert V4 即回復全部第四批政策句。 |
| 停止條件 | 線③ < 12/12；轉人 > 0（非敏感）；p95 > 15 s。 |

## 1. 事實（對碼）

- 記憶段標題「本對話已完成的動作：…」（`grep -n "本對話已完成的動作" rag-orchestrator/services/agent/completed_actions.py`）——沒說「不是該戶全部紀錄」；線上第二輪該時段 15 回合 `tool_calls=0`，「這戶還有沒有別的單」答「只有 12346」（三步前確認卡才印「另有未結單 1 張（8591）」）。
- S4 零查詢降級固定句 `ASK_TARGET_TEXT`（中性、無插值）——有前文時等於把對話清空（`grep -n "def _apply_handoff_without_lookup" rag-orchestrator/services/agent/runtime.py`）；對話歷史在 `agent_state["dialog"]`（`grep -n 'agent_state.get("dialog"' rag-orchestrator/services/agent/runtime.py`）。
- 延期：`bill_due_extend` 驗算 `date_expire_before + days == date_expire_after`（`grep -n "date_expire_before + days" rag-orchestrator/services/agent/confirm_card.py`）；S1 閘門擋過去日期但基準仍是原到期日 ⇒ 模型先算出 9/04 再問。
- `context` 資料段標籤 `caller.context`、來源 `caller:context#1`；空會話註記 `EMPTY_SESSION_TEXT="本會話沒有先前訊息。"`（`grep -n "EMPTY_SESSION_TEXT" rag-orchestrator/services/agent/runtime.py`）；restart 後模型把 `context` 的開場白當成使用者問的。
- 逾時：線上 08:22Z 一筆 `TOOL_TIMEOUT`，前一筆 log 是程式直答回合；發生在我方 16:1x 重部署後的第一則模型回合（冷啟：細目索引剛建、模型首呼）。

## 2. V1 — 記憶段語義（executor）

- `completed_actions_line` 標題改為「本對話裡建立或修改過的：…（只是這段對話做過的事，⛔ 不是該戶的全部紀錄）」（定義句放在資料段內，模型每回合看得到）。
- 政策定義一句「問某一戶有哪些修繕單或帳單，一律以查詢結果為準，⛔ 不以本對話的記憶段代答。」——**由 V4 一併寫入** `_POLICY_TEXT_NON_PROSPECT`（V1 ⛔ 不動 `agent_rules.py`）。
- 驗收：單元（標題文字、記憶段仍可引用）；情境：建單後「這戶還有沒有別的單」⇒ 走 `jgb2.query.repairs`（trace tool_calls ≥ 1）且答案含 8591；3/3。

## 3. V2 — 有前文的零查詢（executor）

- 程式（閉合）：回合開始時從 `agent_state["dialog"]` 最近 6 則與 `completed_actions` 抽 **編號**（重用 `_PRE_LOOKUP_ID_RE`，⛔ 不另寫正則；去重、最多 5 個；security r1 #6：8 位日期／金額也會被撈到，標籤改寫「本對話最近出現的數字編號（可能含日期或金額）」）⇒ **釘住範圍時（`SELECT_SCOPE_KEY` 非 None）不注入**（security r1 #4：與 `completed_actions_line`／前置查詢同一套 L15 紀律）；非空時注入不可引用資料段 `RECENT_REFS_LABEL`（文字先過 `sanitize_data_piece`；保留 id `ref-{nonce[:8]}` 無條件加入集合；同 `context` 通道）。
- 改寫放在**模型迴圈內**（security r1 #5：`_apply_handoff_without_lookup` 在 `_finalize`、迴圈外不得再呼叫模型）：在 T2 改寫提示旁新增分支「輸出為非敏感轉人 ∧ 本回合 `tool_call_records` 為空 ∧ recent refs 非空 ⇒ 消耗一次 `max_rewrites`、帶定義句『對象不明但本對話最近提到編號時，先當它是那一筆：依資料段回答或先查詢，⛔ 不反問哪一戶。』重回模型」；**預算已耗盡 ⇒ 直接跳過改寫落到出口閘**（⛔ 不走 `_build_fixed("budget_exhausted")`，否則 `handoff_reason` 變了 `ASK_TARGET_TEXT` 到不了——同 T2 已記的坑）。改寫後仍零查詢轉人 ⇒ `_apply_handoff_without_lookup` 照舊落 `ASK_TARGET_TEXT`。沒有 recent refs ⇒ 現行行為不變。
- 驗收：單元（抽編號封閉規則、無插值固定句不變、改寫消耗預算、無 refs 路徑不變）；情境：「756248 …逾期了嗎」→「那我要不要打電話給他」⇒ 依帳單事實給建議或查詢，⛔ 不出「想處理哪一件事」；「上次報修的修好了沒」（前文有物件）⇒ 查修繕單；3/3。

## 4. V3 — 延 N 天基準（security-executor）

- 定義：`days` 的基準＝「原到期日與今天較晚者」；`confirm_card.render(action, payload, *, today: Optional[date] = None)`——**關鍵字參數、⛔ 不從 payload／args 讀任何 `today` 鍵**（security r1 #2：payload 是模型控制的）；驗算改為 `max(before, today) + days == after`；**兩個呼叫點都要傳 `bills._today()`**：`confirm.request`（出卡）與 `action._validated_payload`（兌現，security r1 #1：兌現端沒帶 today 會在 token 已燒之後 `_invalid_input()`，每張 V3 卡都兌現不了）；`today` 缺省只給測試與舊呼叫端用（維持舊驗算）；⛔ 不得以放寬 `days` 驗算來「解決」（它與 `payload_digest` 一起是卡↔payload 的綁定）。工具描述同步定義：「延後天數從原到期日或今天較晚的一天起算；算出來的新到期日一定在今天之後。」（並改掉舊句「必須等於 date_expire_before 往後加上 days 天」）；S1 的 `not_before_today` 閘不變（縱深）；起算日那一行只在既有 `_render_bill_due_extend` 分支內加，⛔ 不在外面加 action 名判斷。
- 卡上加一行「起算日：YYYY/MM/DD」（決定性，讓「延後 11 天」那種數字不再讓人遲疑）。
- **跨午夜規則**（plan-verifier r1 #2：token TTL 600 s 可能跨一個午夜，兌現端若用當日時鐘做嚴格等式會 `_invalid_input()`）：兌現端 `_validated_payload(today=兌現日)` 的驗算改為「等式對 `today` **或 `today − 1 天`** 任一成立即通過」（單一決定性規則：TTL < 24 h ⇒ 出卡日只可能是兌現日或前一天；⛔ 不是特例分支）；S1 `not_before_today` 閘仍以兌現當日新時鐘檢查（縱深）。出卡端維持嚴格等式（只有一個 today）。
- payload 若帶 `today` 鍵 ⇒ **一律 `INVALID_INPUT`**（render 拒未知鍵；plan-verifier 註記：二擇一固定為拒絕）。
- 驗收：單元（before < today ⇒ 基準 today；before ≥ today ⇒ 基準 before；缺 today ⇒ 舊行為；閘門仍擋 after < today；**出卡→兌現整鏈**：before 9/01、today 9/09、days 3、after 9/12 的卡在 `confirm.request` 出卡且在兌現端通過 `_validated_payload`、寫入成功；**跨日案例**：同一張卡、兌現日 9/10 ⇒ 通過（today−1 成立）；兌現日 9/11 ⇒ `_invalid_input()`（已超過 TTL 語義，正對照）；payload 帶 `today` 鍵 ⇒ `INVALID_INPUT`）；情境：756248（到期 9/01、今天 9/09）「延三天」⇒ 出卡、新到期日＝今天＋3、起算日＝今天；3/3。

## 5. V4 — 畫面提示與空會話措辭（executor）

- `context` 資料段文字加固定前綴「畫面提示（呼叫端顯示給使用者的，不是使用者說的話）：」——**先 `sanitize_data_piece` 再加前綴**，前綴是常數、不含任何呼叫端輸入（security r1 #7）；`EMPTY_SESSION_TEXT` 改「這段對話裡使用者還沒有說過話。」；政策定義兩句：「畫面提示與開場句不是使用者的問題，⛔ 不當成使用者說過的話回述。」「追問時 ⛔ 不附自行編造的範例名稱或編號；要舉就用本對話或查詢結果裡出現過的。」
- 驗收：單元（前綴、非引用）；情境：restart 後「我剛剛問了什麼」⇒ 說使用者還沒說過話；「基隆溫馨一人宅套房」單獨一句 ⇒ 認作物件（走查詢或出卡），追問不出現「A棟302」類捏造例；3/3。

## 6. V5 — 冷啟逾時（runbook，不動碼）

- 事實：逾時發生在重部署後第一則模型回合。處置：runbook §20-3 加一步「起服務後由部署者用 `curl`／harness 打一回合暖機（任一查詢題），確認 `agent_turn` log 出現後才通知呼叫端」；帳本記「首回合 p95 另計」。
- 若下一輪仍見非冷啟逾時 ⇒ 另開 Plan 量預算（`AGENT_BUDGET_DEADLINE_S` 45 s vs 門面 60 s）。

## 7. 驗證順序

1. 每切片容器內 `tests/unit/agent` 全綠（0 收集＝失敗）。
2. smoke-rag（線上同組態＋`context`）：line-bot 第二輪劇本轉成 `scenarios_lb2.json`（三線關鍵 25 回合）3 輪＋線③ 1 輪；`b2_score`／`wt_score` 沿用。
3. fresh verifier；REFUTED ⇒ 修一輪。
4. 部署（暖機一回合）→ 通知 line-bot 第三輪。

## 8. 安全／信任面（交 security-reviewer：V2 dialog 抽編號注入、V3 卡片驗算改基準）

- V2 注入的只有封閉數字 token（來自使用者自己說過或程式印過的），不可引用、不進歷史；⛔ 不擴大工具範圍（DSP-011）。
- V3 動的是寫入前的驗算（安全面）：`today` 只由呼叫端以 `bills._today()` 傳入；缺省舊行為；S1 閘門不動。

## 9. 安全／信任面（security-reviewer r1 處置）

| # | 發現 | 處置 |
|---|---|---|
| 1 P1 | V3 兌現端 `_validated_payload` 沒帶 today ⇒ 卡出得來兌現不了（token 已燒） | FIX：兩個呼叫點都傳 `bills._today()`；⛔ 不放寬 days 驗算（§4） |
| 2 P2 | `today` 若從 payload 讀，模型可控基準 | FIX：關鍵字參數、不讀 payload（§4） |
| 3 — | 卡雜湊一致性、跨午夜 | 雜湊：同一次 render、安全；跨午夜：#1 處置後兌現端有時鐘 ⇒ 改為「today 或 today−1 任一成立」規則（plan-verifier r1 #2，§4） |
| 4 P2 | V2 recent refs 繞過 L15 範圍 | FIX：釘住範圍不注入（§3） |
| 5 P2 | V2 改寫不得在迴圈外呼叫模型；預算耗盡的坑 | FIX：迴圈內分支、耗盡跳過（§3） |
| 6 P3 | 編號正則重用；日期／金額混入 | FIX：重用 `_PRE_LOOKUP_ID_RE`、標籤改寫（§3） |
| 7 — | V4 前綴無注入面 | FIX 措辭：先 sanitize 再加常數前綴（§5） |
| 8 — | 通用規則 | 起算日只在既有 render 分支內；`CONFIRM_FIELD_ATTRS` 不動（§4） |

plan-verifier r1（兩條 P2）：#1 `agent_rules.py` 由 V4 獨佔、V1 政策句併入 V4（§0／§2）；#2 兌現端跨午夜規則「today 或 today−1」＋跨日測試（§4／§9 #3）。
