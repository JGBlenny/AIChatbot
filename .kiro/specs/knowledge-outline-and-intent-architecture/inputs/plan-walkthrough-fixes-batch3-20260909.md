# Plan：走查回修第三批（U1–U3）— 2026-09-09（第 1 稿；業主未核，先備）

> 來源：第二批回測抓到的三個結構性缺口——(a)「尚未逾期」：事實段印「已逾期 8 天」模型答「尚未逾期」，本地 35 句中 3 句（≈9%），業主 00:44 截圖同型；Verifier 極性詞表沒有「尚未／未／還沒」，且線上觀察模式全放行。(b) 模型可把任何題自報成敏感類（`sensitive_no_grounding`）逃過兩出口（第二批 r2「要不要催他」）。(c) 純編號／純名詞的一句（「756248 你建議我怎麼做」「信仰」）定義句治不了，3/3 反問類型。
> 紀律同前兩批：契約／schema／狀態機／出口閘門／正本定義層，⛔ 不寫特例；詞表以「一類」維護並量誤殺；提示詞只寫定義。

## 0. 程序封套 P-WT3

| 欄 | 內容 |
|---|---|
| 結果 | 逾期／未逾期極性錯句在本地全部跑次中 0；觀察模式下極性與機敏類判定**照擋**（引用類仍觀察）、健檢顯示模式；模型自報敏感類與程式判定不符時以程式為準（統計＋降級）；純編號／短名詞一句由程式先查再進模型，「756248 你建議」3/3 直接依帳單資料答。 |
| 非目標 | DSP-039 值級尺整套（只做極性類）；催繳草稿工具；jgb2 側。 |
| 切片 | U1 Verifier 模式＋否定詞表一類（security-executor；W6-b3 落地）→ U2 程式側敏感判定（security-executor）→ U3 程式前置查詢（executor）。U1 獨立可先派。 |
| 驗收 | §5：每切片單元＋smoke-rag 三輪（走查＋變形集＋第二批劇本）＋fresh verifier；U1 另跑「極性誤殺量測」（對既有全部 jsonl 的答案重放 Verifier，記錄新增擋下的句子逐句人看）。 |
| 回滾 | 各切片單一 commit；U1 旗值回 `observe_only` 即恢復現狀。 |
| 停止條件 | 極性類誤殺（人判為對的句子被擋）> 2%；線③ < 12/12；轉人固定句增加超過基準 1 成。 |

## 1. 事實（對碼）

- 觀察模式：`app._wrap_verifier_observe_only` 把 `verify()` 所有不通過改成通過（`grep -n "return verdict if verdict.ok else" rag-orchestrator/app.py`）；只准配 mock。R8 設計的 `AGENT_VERIFIER_MODE=grounding_observe`（引用類觀察、機敏類照擋）**未落地**（`grep -rn AGENT_VERIFIER_MODE rag-orchestrator/services` → 0）。
- 極性檢查在 `verifier.py`「句子與引文有沒有否定詞須一致」（`grep -n POLARITY_MISMATCH rag-orchestrator/services/agent/verifier.py`），詞表 `config/agent_verifier_rules.json` `negation_terms` 十項，無「尚未／未／還沒／沒有逾期／不在逾期」。
- 敏感分類：`fact_class` 由模型自填（`output_schema.AgentOutput.fact_class`）；Verifier 只驗「敏感類配敏感原因」（第一批 S4），不驗「模型說敏感是否真敏感」。程式側有 `sensitive_patterns`（掃答案）與 presales_gate 的分類器（`grep -n "def _classify_fact_class" rag-orchestrator/services/agent/verifier.py`）。
- 純編號句：模型先問類型（第二批 r1–r3 3/3）；清單點選 `select:<type>:<id>` 已有程式直答路徑（`_run_select_segment`），可重用其查詢面。

## 2. U1 — Verifier 模式（W6-b3）＋否定詞表一類（security-executor）

- 新參數 `AGENT_VERIFIER_MODE ∈ {enforce, grounding_observe, observe_only}`（預設 `enforce`；demo 線上改 `grounding_observe`；`AGENT_VERIFIER_OBSERVE_ONLY=true` 視為 `observe_only` 相容一版後移除）。`grounding_observe`＝引用類（`UNCITED_ASSERTION`／`QUOTE_NOT_COVERING`／`SCHEMA`／`SOURCE_NOT_CITABLE`）只記錄，**極性類（`POLARITY_MISMATCH`）與機敏類（`SENSITIVE_TOPIC`／`ROUTE_NOT_ALLOWED`／`FORBIDDEN_TERM`）照擋**；拒兩次轉人只對照擋的類生效。讀值點唯一（`health.verifier_mode()`），健檢顯示；`observe_only` 仍只准配 mock。
- 否定詞表一類補齊：`negation_terms` += 「尚未」「未逾期」「還沒」「沒有逾期」「不在逾期」「並未」「未曾」（以「否定＋狀態」一類維護；⛔ 不加單字「未」——誤殺面太大，先量再說）；極性比對維持詞組層級。
- 誤殺量測（列入驗收）：對本機所有 `smoke/*.jsonl` 的回答句重放 Verifier（離線腳本，不進 repo），列出因新詞表或模式改變而「會被擋」的句子，逐句人看；誤殺率 ≤ 2% 才上。
- 驗收：單元（模式三態；極性類在 `grounding_observe` 下 `ok=False`；引用類 `ok=True` 並記錄）；「尚未逾期」句對「已逾期 8 天」引文 ⇒ `POLARITY_MISMATCH`（正對照：「已逾期 8 天」對同引文通過）；三輪回測「未逾期」0 次；線③ 12/12；runbook §20-2 改旗。

## 3. U2 — 程式側敏感判定（security-executor）

- 對**問句**跑既有 `sensitive_patterns`／presales_gate 分類（封閉樣式），得 `program_fact_class ∈ {sensitive, non_sensitive}`；模型自報敏感而程式判非敏感 ⇒ 不再豁免兩道降級閘（以程式判定為準），trace 記 `violations += ["sensitive_self_report_overridden"]`；程式判敏感而模型未報 ⇒ 既有 `SENSITIVE_TOPIC` 擋（不變）。
- 驗收：單元真值表；「要不要催他」（程式非敏感、模型自報敏感）⇒ 走兩出口；「你們抽成幾成」（程式敏感）⇒ 仍轉人；三輪 3/3。

## 4. U3 — 程式前置查詢（executor）

- 封閉條件：去標點後訊息為純數字（4–9 位）或 ≤ 6 字且無標點的短名詞；程式先以既有查詢面（帳單／修繕單／合約 by id；物件／社區 by keyword）查一次，結果（含查無）以可引用資料段注入（同記憶段通道，保留 id `pre-{nonce}`），再進模型；⛔ 不代模型作答、不改變 outcome。
- 驗收：「756248 你建議我怎麼做」⇒ 依帳單資料答／建議，不反問類型 3/3；「信仰」（無進場句）⇒ 查無 ⇒ 領域內追問 3/3；純數字非本 role 的 id ⇒ 查無句；線③不退步。

## 5. 驗證順序

同第二批 §6；U1 的誤殺量測先於三輪。
