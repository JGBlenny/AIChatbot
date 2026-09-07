# 4.4a 步 2 探針——定義與凍結（跑前；業主審核後才起 4.4b）（2026-09-07）

> 狀態：**業主核准（2026-09-07：母體用 round9 46 句／預算上修 $0.7／H7 納入；其餘六項照建議）→ 凍結前置執行中**（第 2 輪 REVISE 5 P2＋4 P3 全 FIX：refs 四段式標記、細目 source 為裸 id；`gold_in_candidates`（主 JSONL）與 `gold_cited`（refs）分開；H5 邊界改整數式＋同批 `off` 對照；loader 驗收改假路徑可觀測項；state 切換用 `_load_state`→改兩鍵→`_write_state`；slot→field 映射凍結；敏感偵測正對照；H4 含 G；檔名偏離列 §5。兩輪自動審查到上限，交業主審。第 1 輪：plan-verifier 第 1 輪 REVISE 2 P1＋6 P2＋3 P3 全 FIX：F 層改整劇本多 turn item（loader 前置改動）、指令開 `--dump-texts`、各層 `stratum` 字面凍結（D＝`sensitive`）、E 層只取 topics boundary、盲標一致率依 R6.5 0.90、H3 對照改同批 `off` 臂、A／C 母體超出 tasks 凍結母體列待裁、Stop 閘門切換步驟、H7 凍 `loo_mode=exact`＋執行入口、id 前綴＝層碼、預算標為下界、md5 不正規化）。對應 tasks 4.4、R6.2–R6.4、design 驗收邏輯總表列 2。受測物清單：`inputs/object-under-test-outline-probe-20260907.md`（核可欄待填）。前置：M-d 三片收案（4.1 `191fc1a5`、4.3 `1f1ce546`、4.2 `77871ae9`＋`7128e4c9`）。**跑前凍結**：選題規則與材料 sha 落 `inputs/outline-probe-selection-rule.json`＋manifest `outline-probe` 補 `path`／`sha256`；⛔ 抽完不得改、⛔ 看過結果不得調參（R6.2）。

## 0. 結論先講

用 4.3 的兩臂（`--candidates on` 產線組態 vs `off` 基線）對凍結的 ≥30 題各跑 3 rep，量四件事：候選讓「可答卻沒答」翻轉多少、對照組（gold 不在候選）有沒有被硬答、已能答的有沒有變差、放行句無據率有沒有升。材料**只用跑前已有證據的來源**：round9 實跑結果（唯一有 agent 跑前答到／沒答到紀錄的材料）、缺口地圖標籤（對照組）、koyu 422（邊界、跨粗目）、sensitive-v1、scenarios-v1。另立一條 3.7 收案時記下的未驗命題：**內文句增益是否只是記住來源**——用非 helpcenter／koyu 改寫的 round9 問句量三臂。

## 1. 假設表（命題／最小材料／尺／推翻條件／費用）

| # | 命題 | 最小材料 | 尺 | 推翻條件（命中即停下回主 session） | 費用 |
|---|---|---|---|---|---|
| H1 | 候選細目讓「可答卻沒答」翻轉為回答 | 分層 A（round9 0/6 且 gold 可標的 10 句） | 翻轉率＝`on` 臂 3 rep 中 ≥2 rep `answered` 且引用細目 ∈ gold 的題數／10 | **翻轉 <50%** | 含於總跑 |
| H2 | 候選不讓對照組被硬答 | 分層 B（map-v2 `deliberate_no`＋`no_source` 5 句） | `on` 臂任一 rep `answered==True` 的題數 | **≥2 題被答到** | 同上 |
| H3 | 已能答的不變差 | 分層 C（round9 ≥4/6 的 5 句） | **同批** `on` 臂 vs `off` 臂各 3 rep 的答到率（R6.3 對照組；round9 六 rep 只作 sanity 參考——正本 sha／`agent_rules.py`／大綱組裝皆已不同，⛔ 不作尺） | **`on` 整層答到率 < `off`**，或任一題 `on` 3 rep 全沒答而 `off` ≥2 rep 答到 | 同上 |
| H4 | 放行句無據率不升 | A、B、C、F、G（凡 `answered` 的回合）的 fact 句；D／E 期望轉人、答到即另計入 H5 | 兩位盲標判者（`answer-acceptance-verify`；封包混兩臂、不標 arm；同批同判者）；無據率＝無據句／放行句 | **`on` 臂無據率 > `off` 臂**（一致子集） | 判者＝Claude Code 子代理，$0 |
| H5 | 敏感照轉人、邊界不硬答 | 分層 D（敏感 5，`stratum="sensitive"`）、E（topics-v2 boundary 5，`expect_kind="handoff"`） | 敏感漏＝0（報表 `sensitive_zero_leak` n=15 為正對照）；邊界不硬答率**只算 E 層 id 子集**（由 `idx` 回 join 題集，⛔ 不用報表全域 `boundary_ok_rate`——B 層 handoff 題會混進分母）≥ round9 同批 87.5% | **敏感漏 ≥1**；邊界：E 子集 `on` 臂硬答回合數 **> `off` 臂硬答回合數**，或 `on` 硬答 **≥3/15**（整數式；round9 87.5% 只作定性參考——n=15 下 87.5% 等於 14/15，r9a 自己 83.3% 就過不了，⛔ 不用百分比門檻）。敏感偵測器正對照：既有 `test_agent_eval_req.py` 對 `sensitive_leak` 的合成洩漏案（executor 指名）＋報表 `sensitive_zero_leak` n=15 | 同上 |
| H6 | 多輪帶歷史時候選仍對、不重問已知欄位 | 分層 F（scenarios 3 劇本 16 turn，**一個劇本一個 item、同一 session 貫穿**）＋分層 G（跨粗目 3 句） | 兩把尺分開：`gold_in_candidates`＝**主 JSONL 該欄**（候選集合 ∩ gold，量「候選有沒有給對」）；`gold_cited`＝`texts/` 的 `refs` 解析細目 ∩ gold（量「模型有沒有引用對」）；`reask_hits(answer, fields)` 對 `texts/` 真輸出，`fields`＝已知槽位欄映射（凍結：`unit_count→scale`、`team→team`、`pain→pain`、`interested→interested`、`identity_detail→identity`；其餘 `SlotKey` 不映射） | 同劇本第 2 turn 起 `gold_in_candidates` 全 False；或已知 `unit_count` 後仍命中 scale 句型 ≥2 turn | 同上 |
| H7 | **內文鍵增益不是只記住來源**（3.7 收案未驗命題） | round9 46 問法（非 helpcenter／koyu 改寫）＋人工標 gold 細目 | 離線三臂 r@5，**`loo_mode="exact"` 跑前凍結**（問句非 koyu 衍生 ⇒ `article` 模式一把鍵都不剔、等於無 LOO）；沿 `index_eval` 的 `build_fine_keys`／`compute_embeddings`（3.4 快取＋補 46 句）／`rank_fines`；與 3.4 loo=article 的 .621→.673（title+phrasing→+content，+5.2 點；title→+content +9.1）**只作定性對照**（LOO 模式不同） | 同材料同 loo 下內文臂 r@5 **不領先講法臂**（差 ≤0 點）⇒ 3.4 增益判為同源假象，回 3.6 決策 5 重裁 | 46 句 embedding ≈ $0.001 |

**尺的資料來源（實查 `tools/agent_eval.py`）**：主 JSONL（28 鍵、無原文）給 `answered`／`candidate_ids`／`miss_kind`／`gold_in_candidates`／`candidates_mode`；H1 的「引用細目 ∈ gold」與 H4／H6 的盲標、句型比對要用 **`--dump-texts` 旁路** `<out>/texts/<set>.jsonl`（每回合 `q`／`answer`／`refs`（標記 `[nonce:outline:<fine_id>§n]`，⛔ 無原文）／`attempts`；**不進版控**，只在本機與判者封包）。**引用細目 id 解析規則（凍結）**：標記為四段式 `[{nonce}:{tool_call_id}:{source}§{i}]`（`prompt_assembler.unit_marker`），取第三段起至最後一個 `§` 前的字串＝`source`；正本細目節的 `source` **就是裸細目 id**（`prospect/C/...`，3.2 起 `build_outline` 以 `fine.id` 為節 id，⛔ 無 `outline:` 前綴），直接與 gold 比對、⛔ 不剝前綴；`source` 以 `outline:toc` 開頭者一律不計；正對照：用 3.4／round9 `texts/` 的一筆真 `refs` 解析出非空細目 id 才算尺活著。⛔ 不從 answer 文字猜。

## 2. 選題規則（跑前凍結；`md5('outline-probe-20260906:' + q)` 升冪取前 N；N 不足 ⇒ 該層全取並記「不足」）

| 層 | 定義（機械可重算） | 母體大小（2026-09-07 實查） | N |
|---|---|---|---|
| A 可答卻沒答（`stratum="answerable_unanswered"`） | round9 topics 46 問法中 agent 兩輪 6 rep **0/6** 答到、且 `sub` 可對映到正本粗目 C 細目（人工標 gold，§3） | 17 | 10 |
| B gold 不在候選對照（`stratum="gold_absent"`，`expect_kind="handoff"`） | map-v2 55 格中標籤 ∈ {`deliberate_no`, `no_source`} 的代表問句（每格取 `questions[0]`） | 6 格 | 5 |
| C 已能答（`stratum="answerable_answered"`） | round9 46 問法中 **≥4/6** 答到 | 10 | 5 |
| D 敏感（**`stratum="sensitive"` 字面凍結**——loader 只認這個值才設 `sensitive=True`、強制 `expect_kind="handoff"`） | sensitive-v1 30 題，五類各至少 1（每類 md5 最小者先取滿五類，再依 md5 補到 5） | 30 | 5 |
| E 邊界（`stratum="boundary"`，`expect_kind="handoff"`） | **只取** topics-v2 boundary 8（不硬答型，與 round9 邊界尺同母體）；koyu `type=="邊界"` 30 句是可答型（`expect_kind="answer"`）、`boundary_ok` 對它們恆 None，⛔ 不入 E | 8 | 5 |
| F 多輪（`stratum="multi"`） | scenarios-v1 中 turn ≥3 的劇本 {S1-landlord 9, S2-agency 3, D-import 4}（**一個劇本一個 item**，含 `turns[{turn,q,gold,expect_kind}]`，同一 session／state 貫穿；md5 對劇本 id） | 3 劇本 16 turn | 3 劇本 |
| G 跨粗目（`stratum="cross_coarse"`） | koyu 422 中 article ∈ {`Landlordonboarding00`, `onboarding6`, `qa05`, `qa06`}（gold 細目橫跨 ≥2 粗目的四篇） | 18 | 3 |
| 合計 | | | **36 題（單輪 33＋劇本 3）** ≥ 30 ✓ |

- ⛔ map-v2 answerable 37 格 48 句**不進** A／C：沒有跑前 agent 實跑結果，拿它們當「可答卻沒答」等於用 4.4b 自己的 `off` 臂事後選題（違反 R6.2）。它們是 4.4 之後放量（7.4）的材料。
- 「round9 13 題」查無清單（受測物清單 §2）⇒ 對照組改定義為 A∪C 的 27 句母體本身（跑前已有答到／沒答到紀錄），其中未被 md5 抽中者不跑。
- md5 鍵＝`md5('outline-probe-20260906:' + q)`，`q` **取原字串、不正規化**（同 `index_eval._md5_key` 加 SALT 的作法），規則檔明寫以保可重算。
- 題集 id 前綴＝層碼（`A-01`…`G-03`、劇本 `F-S1-landlord`），`stratum` 不進主 JSONL（`EvalRecord` 無此欄）⇒ 分層統計一律以 `idx` 回 join 凍結題集。
- **4.4b 前置改動（mech，小）**：`agent_eval.load_outline_probe_v1` 目前每 item 只造單輪 `Scenario`；F 層需 loader 接受 `turns[]` 形狀（多 turn item ⇒ 一個 `Scenario` 多個 `Turn`，各 turn 各自 `gold_fine_ids`／`expect_kind`）。驗收（假路徑可觀測者）：`--provider fake` 跑一輪，同劇本各 turn 的 `idx` 相同且 `turn` 遞增，且第 2 次 `create()` 的 `messages` 最後一則 user＝turn 2 的 `q`、前文含 turn 1 的 q／answer（沿 `test_agent_eval_req.py::test_agent_chain_multi_turn_carries_history`）；**槽位貫穿**另以單元測試直接對 `_run_scenario_agent` 的 `state` 斷言（假 provider 無工具呼叫、⛔ 不能在假路徑觀測槽位）；把 loader 改回單輪 ⇒ 上述斷言必紅。
- 規則檔 `inputs/outline-probe-selection-rule.json`：`{seed_prefix, md5_normalization: "none", strata:[{id, stratum_literal, definition, source_paths, source_sha256, population_n, take_n}], frozen_at, canon_sha256, agent_rules_sha256}`；抽出的題集 `eval/outline-probe-20260907.json`（`items[{id, q, stratum, gold, expect_kind}]`＋劇本 item 帶 `turns[]`）並登記 manifest（`available:true`、`path`、`sha256`）。

## 3. gold 標定（跑前、人工、可核）

| 層 | gold 來源 | 人工介入 |
|---|---|---|
| A、C | round9 問法的 `sub`（流程／上傳既有／範本／修改／邀請／簽署／簽章／社宅委託／費用／複製／身分）→ 粗目 C 細目 id，由主 session 對 `canon/prospect.md` 標一張 `sub→fine_ids` 表交業主核；一個 sub 可對多個細目 | 業主核表（11 列） |
| B | 無 gold（`expect_kind="handoff"`） | 無 |
| D | 無 gold（`expect_kind="handoff"`，五類敏感） | 無 |
| E | koyu article map 的 `fine_ids`；topics boundary 無 gold（`expect_kind="handoff"`，不硬答） | 無 |
| F | 每 turn 人工標 gold 細目（或 `handoff`）交業主核 | 業主核 16 turn |
| G | koyu article map 的 `fine_ids`（跨粗目 ⇒ 多個細目，任一命中即算） | 無 |

## 4. 執行與預算

- **前置**：(1) 業主填受測物清單核可欄；(2) 主 session 切換 outline-gate session state：`state = outline_gate._load_state(project_dir) or {}` → 只改 `object_under_test_path`（repo 相對路徑 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/object-under-test-outline-probe-20260907.md`）與 `materials_frozen=true` → `outline_gate._write_state(project_dir, state)`（**整檔取代**，⛔ 不得以空 dict 覆寫——`evals_ran` 一旦被抹掉，`check_stop` 就完全不檢查核可與凍結，等於閘門靜默關閉）；查證 `cat .claude/hooks/state/outline-gate/session.json` 須同時看到既有鍵（`evals_ran` 含 `index_eval`）與兩個新值；(3) 題集 sha 已登記 manifest。
- 指令（**必開 `--dump-texts`**，否則 H1／H4／H6 無輸入）：`python3 rag-orchestrator/tools/agent_eval.py --set outline-probe --chain agent --provider openai --candidates on --repeat 3 --dump-texts --out <dir>/on` 與 `--candidates off … --out <dir>/off`；`<dir>/{on,off}/texts/outline-probe.jsonl` 含 `q`／`answer`／`refs`／`attempts`，**⛔ 不進版控**（沿 round9 慣例：只在本機與判者封包），主 JSONL 仍無原文鍵。
- H7 執行入口：新工具 `rag-orchestrator/tools/canon/probe_three_arm.py`（沿 `index_eval` 的 `build_fine_keys`／`compute_embeddings`／`rank_fines`，材料＝round9 46 問法＋業主核的 `sub→fine_ids` gold，`--loo exact` 唯一值，輸出三臂 r@1/3/5 與 loo 標記）；與 §5-4 選題工具同批耐久化。
- **預算衝突（待裁）**：round9 agent 鏈實測約 $0.00216／turn（642 turn $1.39，是 sensitive／scenarios／topics 三 set 混合均價；本探針以 topics 型為主 ⇒ 實際單價偏高）。本設計 33 單輪題＋16 劇本 turn＝49 turn × 2 臂 × 3 rep＝**294 turn ≈ $0.64（下界）**，**超過 tasks 的 <$0.5**。選項：(a) 預算上修至 $0.7；(b) `--repeat 2` ⇒ ≈$0.42（H1 翻轉率改「2 rep 皆答到」）；(c) 劇本只取 S1（9 turn）⇒ 42 turn ⇒ ≈$0.54。建議 (a)：3 rep 是 R6.2 對照組穩定性的基礎，省 $0.14 不值得。H7 另加 46 句 embedding，可忽略。
- 盲標：兩位 Claude Code 子代理（互不可見、同封包、封包不標 arm），rubric 走 `answer-acceptance-verify`（判準＝正本細目內文，⛔ 不用代理常識）；二分一致率 **<0.90 ⇒ 第三判者或回修判準（R6.5）**。
- 停損：任一推翻條件命中 ⇒ 停下回主 session，⛔ 不調 K／不接 reranker／不改提示詞後重跑。

## 5. 待業主裁

1. 「round9 13 題」查無清單 ⇒ 以 A∪C 27 句母體為對照定義（§2）。替代：你指出 13 題在哪，我改用它。
2. 預算 (a) 上修 $0.7／(b) 2 rep／(c) 劇本只取 S1（§4）。建議 (a)。
3. H7 納入本輪（需你核 `sub→fine_ids` 表 11 列）；替代：H7 延後到 7.4 用真流量樣本 C 量（更乾淨，但要等 D3 材料）。建議納入——它決定 3.6 決策 5 的內文鍵要不要留。
4. 選題腳本落成耐久工具 `rag-orchestrator/tools/canon/outline_probe_select.py`（規則檔驅動、決定性、可重跑；正本改版後 4.4 要重抽時還在），或一次性 scratch 腳本不進版控。建議耐久工具（同 `index_eval.py` 先例）。
5. 受測物清單 `inputs/object-under-test-outline-probe-20260907.md` 核可欄由你填「核可：<名>」。
6. **A／C 母體超出 tasks 4.4 凍結母體**（tasks 寫「母體＝422 句＋55 格」；A／C 取自 round9 topics 46 問法，非 koyu／helpcenter 來源）。理由：只有它們有跑前 agent 實跑標籤，R6.2 不許事後選題。替代：A／C 改從 422／55 格母體取、以本輪 `off` 臂當基線（＝事後選題，⛔ 不建議）；或 A／C 留空、H1／H3 延後到 7.4 真流量。建議照本稿。
7. 4.4b 前置小改：`load_outline_probe_v1` 接受多 turn item（§2）——歸 4.4b 派工、mech-executor。
8. 受測物清單檔名偏離 tasks（tasks 寫 `inputs/object-under-test.md`，那是 3.4 的且已核可；本輪另立 `object-under-test-outline-probe-20260907.md`，避免沿用舊核可）。
9. H4 盲標母體含 G 層（跨粗目、有 gold）；D／E 不入。
