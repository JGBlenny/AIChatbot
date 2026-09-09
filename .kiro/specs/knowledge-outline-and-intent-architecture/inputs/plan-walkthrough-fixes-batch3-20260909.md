# Plan：走查回修第三批（U1–U3）— 2026-09-09（第 4 稿＝收尾稿：security-reviewer r1 十一條＋plan-verifier r1 四條＋r2 兩條全數 FIX；本稿開唯一一輪收尾審查）

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
| 停止條件 | 極性類誤殺率 M÷N > 10%（N＝該輪 `POLARITY_MISMATCH` 命中句數、M＝人判為對卻被擋的句數；同時報 M÷全部重放句數）；線③ < 12/12；轉人固定句增加超過基準 1 成。 |

## 1. 事實（對碼）

- 觀察模式：`app._wrap_verifier_observe_only` 把 `verify()` 所有不通過改成通過（`grep -n "return verdict if verdict.ok else" rag-orchestrator/app.py`）；只准配 mock。R8 設計的 `AGENT_VERIFIER_MODE=grounding_observe`（引用類觀察、機敏類照擋）**未落地**（`grep -rn AGENT_VERIFIER_MODE rag-orchestrator/services` → 0）。
- 極性檢查在 `verifier.py`「句子與引文有沒有否定詞須一致」（`grep -n POLARITY_MISMATCH rag-orchestrator/services/agent/verifier.py`），詞表 `config/agent_verifier_rules.json` `negation_terms` 十項，無「尚未／未／還沒／沒有逾期／不在逾期」。
- 敏感分類：`fact_class` 由模型自填（`output_schema.AgentOutput.fact_class`）；Verifier 只驗「敏感類配敏感原因」（第一批 S4），不驗「模型說敏感是否真敏感」。程式側**沒有問句分類器**（security r1 F6：`_classify_fact_class` 全 repo 無定義，只剩 docstring 殘留；presales_gate 只有 `parse_fact_class`／`scan_handoff_mentions`／`looks_like_question`）；現有的是答案側 `sensitive_patterns` 掃描（`config/agent_verifier_rules.json`）。
- 純編號句：模型先問類型（第二批 r1–r3 3/3）；清單點選 `select:<type>:<id>` 已有程式直答路徑（`_run_select_segment`），其四步紀律（可見性／速率／schema／身分鍵剝除）走 `registry.call(identity, …)`，工具內另有身分閘 `_identity_gate_ok`——前置查詢必須走同一條，⛔ 不直呼 `tools/jgb2.py` 的函式。
- `verify()` 是**短路**的（`SENSITIVE_TOPIC` → marker → `UNCITED`/`SCHEMA` → `QUOTE_*`/`POLARITY`/`SOURCE_NOT_CITABLE` → `ROUTE` → `FORBIDDEN_TERM`），外層翻判定的作法會讓先命中的引用類把後面的機敏類與極性類**根本沒跑**（security r1 F1）。

## 2. U1 — Verifier 模式（W6-b3）＋否定詞表一類（security-executor）

- 新參數 `AGENT_VERIFIER_MODE ∈ {enforce, grounding_observe, observe_only}`（預設 `enforce`；demo 線上改 `grounding_observe`；`AGENT_VERIFIER_OBSERVE_ONLY=true` 解析成 `observe_only`，相容一版後移除）。讀值點唯一 `health.verifier_mode()`；健檢輸出 `verifier_mode`（**保留** `verifier_observe_only` 鍵，煙囪 §20-5 有斷言；security F3）。
- **模式感知放在 `OutputVerifier.verify()` 內部**（security F1）：`verify()` 改為「逐類檢查，觀察類命中只記到 verdict 的 `observed` 清單、⛔ 不 return，繼續跑後面的類；照擋類命中才 return `ok=False`」；觀察類（`grounding_observe`）**以拒因＋子成因界定**（plan-verifier r2 #1：`SCHEMA` 是共用拒因，含 `marker_in_answer`（nonce／標記外洩）與 `handoff_reason_mismatch`（S4 敏感配對，U2 准入建立在它之上）等安全子成因，⛔ 不得整類觀察）：`UNCITED_ASSERTION`／`QUOTE_TOO_SHORT`／`QUOTE_NOT_COVERING`／`SOURCE_NOT_CITABLE`，以及 `SCHEMA` 中**只有**引用解析子成因 `ref_invalid`／`ref_source_not_found`／`ref_ambiguous`／`unit_out_of_range`；其餘 `SCHEMA` 子成因（`marker_in_answer`／`handoff_reason_invalid`／`handoff_reason_mismatch`／`ask_target_invalid`／`empty_*`）、極性類（`POLARITY_MISMATCH`）與機敏類（`SENSITIVE_TOPIC`／`ROUTE_NOT_ALLOWED`／`FORBIDDEN_TERM`）照擋；`enforce`＝全部照擋；`observe_only`＝全部觀察（維持現行語義）。`_verify_ref` 內 `QUOTE_TOO_SHORT`→`QUOTE_NOT_COVERING`→`POLARITY_MISMATCH` 的短路同樣改成「觀察類記錄後續跑」，讓覆蓋率先掛的句子仍拿得到極性判定。**多 ref 聚合規則**（plan-verifier r1 #3、r2 #2）：一句的多筆 refs 中，**極性類與機敏類任一 ref 命中即 `ok=False`**（reason 取該類；防被別的 ref 洗掉）；**引用類維持既有「至少一 ref 完整通過即通過、否則回 last_failure」**（r11 F-1 刻意設計，⛔ 不改，`enforce` 預設拒絕率不變、`self_test` 的 `known_good.json` 必須仍全綠）；觀察類只記入 `observed`。`VerifierVerdict` 新增 `observed: list[str]`（預設空；schema_cause 鍵集合測試不受影響）。外層 `app._wrap_verifier_observe_only` 只留相容層（讀解析後的 mode）。
- 觀察類**不遞增** `counters.rewrites`（security F4 前提）；`_build_fixed("budget_exhausted")` 的 reason 不在 `NON_SENSITIVE_HANDOFF_REASONS`，引用類單獨失敗不會多一條到轉人的路（F4 已對碼）。
- **自證釘死 enforce**（security F2）：`bootstrap.build_runtime` 的 `verifier.self_test`（`known_fabrications.json` 全拒）以 `enforce` 模式跑，⛔ 不受環境旗影響。
- **守衛看解析後的 mode**（security F3）：`observe_only` 且非 mock ⇒ 啟動 raise（同現行）；`grounding_observe` 且 `USE_MOCK_JGB_API=false` ⇒ `premise.red_flags` 記紅（健檢可見，不阻起）——這是第一個能在真 API 上關掉引用檢查的組態，runbook §20-7 回切段要寫明。
- 否定詞表一類補齊：`negation_terms` += 「尚未」「未逾期」「還沒」「沒有逾期」「不在逾期」「並未」「未曾」（以「否定＋狀態」一類維護；⛔ 不加單字「未」）；極性比對維持詞組層級。⚠️ 極性是對稱判定，主要誤殺來自**引文側**含否定詞（security F5）——量測必須看到引文。
- 誤殺量測（列入驗收；security F5：現行 `_emit_attempt` 不記引文，重放算不出）：U1 在 `AGENT_ATTEMPT_LOG_PATH` 有設時（dev 專用旗，⛔ 線上不設）把每句的 `resolved_unit`（引文原文）一併記進 attempt；量測＝smoke-rag 以 `grounding_observe`＋attempt log 重跑走查／變形集／第二批劇本各一輪，統計 `POLARITY_MISMATCH` 命中，逐句人看（句子＋引文並列）；產出三個絕對值：命中 N、人判誤殺 M、全部重放句數 T；**分母＝N**，M÷N ≤ 10% 才上（同時報 M÷T）；命中的「尚未逾期」對「已逾期 8 天」為正對照。
- 驗收：單元（模式三態；`grounding_observe` 下極性類 `ok=False`、引用類 `ok=True` 且 verdict 帶 `observed`；**多 ref 混合 fixture**：ref A 覆蓋不足＋極性一致、ref B 覆蓋足＋極性不符 ⇒ `ok=False`、`reason=POLARITY_MISMATCH`；**同時違反引用類與 `forbid_terms` 的 fixture 在 `grounding_observe` 下 `ok=False`**（F1 的短路證明）；`grounding_observe` 下 `marker_in_answer` 與 `handoff_reason_mismatch` 各一案 ⇒ `ok=False`、正對照 `ref_source_not_found` 一案 ⇒ `ok=True` 且 `observed` 含之；`enforce` 下「ref A 覆蓋不足＋ref B 全過」⇒ `ok=True`（既有語義不變）、「ref A 極性一致＋ref B 極性不符」⇒ `ok=False`；`observe_only`＋非 mock ⇒ 啟動 raise；`grounding_observe`＋非 mock ⇒ `premise.red_flags`；self_test 在任何 mode 旗下皆綠）；「尚未逾期」句對「已逾期 8 天」引文 ⇒ `POLARITY_MISMATCH`（正對照：「已逾期 8 天」通過）；三輪回測「未逾期」0 次；線③ 12/12；runbook §20-2／§20-7 改旗與回切說明。

## 3. U2 — 程式側敏感判定（security-executor）

- **新建**問句側封閉樣式分類 `question_sensitive(message) -> bool`（security F6：沒有既有分類器可重用）：樣式表放 `config/agent_verifier_rules.json` 新鍵 `question_sensitive_patterns`（以 SENSITIVE 五類各一組正則維護，同 `sensitive_patterns` 的形狀），**`VerifierRules` 新增欄位 `question_sensitive_patterns: list[str]`（預設空表）**（plan-verifier r1 #2：pydantic 白名單會靜默忽略未宣告鍵）＋正對照測試「`VerifierRules.load(出貨規則檔).question_sensitive_patterns` 筆數＝檔內筆數、非空」；⛔ 不寫字串特例；附誤判量測（對本機所有劇本的使用者訊息跑一次，命中逐句人看）。
- **只改閘的資格、⛔ 不改寫 `out.fact_class`**（security F7）：兩道閘各自的**准入守衛行**（plan-verifier r1 #1：現行第一道守衛 `handoff_reason not in NON_SENSITIVE_HANDOFF_REASONS ⇒ return`，而模型自報敏感時 Verifier 強制 `handoff_reason=sensitive_no_grounding`，光改 fact_class 豁免到不了）改為封閉條件：「`handoff_reason ∈ NON_SENSITIVE_HANDOFF_REASONS`」**或**「`handoff_reason == "sensitive_no_grounding"` 且 `fact_class ∈ SENSITIVE` 且 `question_sensitive(message) is False`」可進閘；後者進閘後不再享 `fact_class` 豁免（走兩出口固定句，⛔ 不會吐敏感內容）、trace `violations += ["sensitive_self_report_overridden"]`。⛔ 不改 `NON_SENSITIVE_HANDOFF_REASONS` 集合本身（§2 F4 前提依賴它）。程式判敏感（`question_sensitive True`）⇒ 一律不進閘、仍轉人。答案側 `SENSITIVE_TOPIC` 掃描在 enforce 與 grounding_observe 下都保留（縱深）；程式判敏感而模型未報 ⇒ 既有擋法不變。
- 記錄（security F8）：NO_JUDGEMENT 分支寫 `ask_target=confirm_intent` 會成為 T3 肯定語訊號；降級後多的回合只會擴大「授權執行查詢」的面，寫入仍需 `confirm_submit` 兌現。DSP-011：⛔ 不拿分類結果改工具可見性。
- 驗收：單元真值表含「`fact_class=SENSITIVE`＋`handoff_reason=sensitive_no_grounding`＋程式判非敏感 ⇒ 走 NO_JUDGEMENT／追問」與正對照「程式判敏感 ⇒ 仍轉人」；規則檔載入正對照；「要不要催他」（程式非敏感、模型自報敏感）⇒ 走兩出口；「你們抽成幾成」（程式敏感）⇒ 仍轉人；三輪 3/3。

## 4. U3 — 程式前置查詢（executor）

- 封閉條件：去標點後訊息為純數字（4–9 位）或 ≤ 6 字且無標點的短名詞；`ref` 先過封閉字集 `^[A-Za-z0-9_-]{1,32}$`（security F9），原值 ⛔ 不進 trace（S8-6）。
- 查詢**一律走 `self.registry.call(identity, …)`**（與 `_run_select_segment` 同四步：可見性／速率／schema／身分鍵剝除；工具內身分閘 `_identity_gate_ok` 照跑），⛔ 不直呼 `tools/jgb2.py`；範圍＝呼叫者 role／user 原本就能查的同一組工具（不擴大授權面）。純數字：帳單／修繕單／合約 by id；短名詞：物件 keyword 查詢，只開視域內查詢、⛔ 不開 `select` 未開的 `estate`／`meter` ref 語義（S8-13）。
- 結果（含查無）經 `sanitize_data_piece`＋`wrap_provenance_data` 同通道注入為可引用資料段；保留 id `pre-{nonce[:8]}` **在回合最開始無條件算出並加入 `reserved_ids`**（security F10），⛔ 不是「有前置查詢才算」；查無與無權限同一句（L15-13）。⛔ 不代模型作答、不改變 outcome。
- 驗收：「756248 你建議我怎麼做」⇒ 依帳單資料答／建議，不反問類型 3/3；「信仰」（無進場句）⇒ 查無 ⇒ 領域內追問 3/3；純數字非本 role 的 id ⇒ 查無句；線③不退步。

## 5. 驗證順序

同第二批 §6；U1 的誤殺量測先於三輪。

## 6. 安全／信任面（security-reviewer r1 處置）

| # | 發現 | 處置 |
|---|---|---|
| F1 P1 | 外層翻判定會讓短路後的機敏類沒跑 | FIX：模式感知進 `verify()` 內部、觀察類記錄後續跑（§2） |
| F2 P2 | self_test 受模式旗影響會啟動紅 | FIX：自證釘 enforce（§2） |
| F3 P2 | 守衛綁舊 env；grounding_observe 可在真 API 關引用檢查 | FIX：守衛看解析後 mode；非 mock 進 red_flags；健檢保留舊鍵（§2） |
| F4 P3 | 拒兩次轉人互動 | 已對碼無新洞；觀察類不遞增 rewrites（§2） |
| F5 P2 | 誤殺來自引文側；重放缺引文 | FIX：attempt 記 `resolved_unit`（dev 旗）＋觀察模式重跑量測（§2） |
| F6 P1 | 引用的分類器不存在 | FIX：新建問句側封閉樣式表＋誤判量測（§3） |
| F7 P1 | 改寫 fact_class 會反轉答案側擋法 | FIX：只改閘資格、不改 fact_class；答案側掃描保留（§3） |
| F8 P2 | NO_JUDGEMENT 的 confirm_intent 擴大 T3 訊號面 | 記錄（§3） |
| F9 P2 | 前置查詢須走 registry 帶身分；id 枚舉 | FIX：registry.call、封閉字集、ref 不進 trace、查無同句（§4） |
| F10 P2 | 保留 id 必須無條件算 | FIX（§4） |
| F11 P3 | 第三方 facts 注入通道；keyword 模糊搜尋 | FIX：同通道 sanitize；只開視域內查詢、不開新 ref 語義（§4） |

plan-verifier r1（四條）：#1 P1 兩道閘准入守衛加「自報敏感且程式判非敏感」條件、不改集合（§3）；#2 `VerifierRules.question_sensitive_patterns` 欄位＋載入正對照（§3）；#3 多 ref 聚合＝照擋類任一命中即擋、`VerifierVerdict.observed`（§2）；#4 誤殺率分母＝N、報 N／M／T（§0／§2）。U3 對碼可行：`registry.call(identity, name, args, timeout_s, stage=…)` 需帶 `stage`；`reserved_ids` 加 `pre-` 無條件成立。
plan-verifier r2（兩條）：#1 P1 觀察類以子成因界定，`SCHEMA` 的安全子成因照擋（§2）；#2 P2 任一命中即擋只限極性與機敏類，引用類維持既有聚合（§2）。
