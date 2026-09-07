# 受測物定義清單——步 2 探針**重跑**（5.1 收案後；任務 4.4 重跑，`agent_eval.py --set outline-probe`）

> 依 Plan 5.1 §1.3-14：與 4.4b 同題集、同尺、同臂，**只換受測物＝`agent_rules.py`（5.1 定義文）**。基線＝`inputs/probe-report-20260907.md`。**核可欄非空後才准起 4.4b**（真模型、打 API）。
> 3.4 的清單 `inputs/object-under-test.md` 是步 1（離線召回）的，⛔ 本檔不覆蓋它、也不沿用它的核可。

核可：業主（2026-09-07 口頭核可，主 session 代填）

## 1. 受測物（本次量的是哪一份東西）

| 項 | 值 | 查證 |
|---|---|---|
| 知識正本 `rag-orchestrator/canon/prospect.md` | `canon_sha256 = 240e1a502a856217…`（version `2026-09-07.6`；與 3.4 全跑時同一份 ⇒ 3.4 embedding 快取仍有效） | `cd rag-orchestrator && python3 -c "from services.agent.canon.canon_parser import parse_canon; print(parse_canon('canon/prospect.md').canon_sha256)"` |
| 對話規則 `services/agent/agent_rules.py` | sha256 `5e392c00c57253fd…`（**5.1 定義版**：四鐵則逐字＋判準＋補問規則＋輸出契約，1,511 字；persona 三分支；4.4b 基線為 `5c14ec238ba2d238…`） | `shasum -a 256 rag-orchestrator/services/agent/agent_rules.py` |
| 候選機制 | `CandidateSelector`（K=5、無門檻、鍵＝標題＋approved 講法＋內文句取最大、同分 title>phrasing>content）；`FineIndex` 358 鍵；`CandidateOutlineDoc`（K 細目＋toc；降級＝可見細目全集＋toc） | commit `b61d8dd7`（3.7）、`191fc1a5`（4.1） |
| 身分 | 入口正規化（prospect ⇒ b2b）、`identity`／`identity_source` 強制槽位、`SlotKey` 十值 | commit `77871ae9`（4.2 S2a） |
| 評估工具 | `tools/agent_eval.py --candidates on/off`（`off` ⇒ `candidate_selector=None`；`on` ⇒ 真 embedding 索引，未就緒 exit 5） | commit `1f1ce546`（4.3） |
| 模型 | 與 round9 同：gpt-4o-mini（`--provider openai`）；Verifier 現行尺（DSP-029a ratio 0.5 ∧ 下限 4 ∧ 全極性，DSP-034 後） | `git log -1 -- rag-orchestrator/services/agent/verifier_rules*` |
| 執行組態 | `--chain agent --repeat 3`，兩臂各跑一次；`readonly_view=True`；⛔ 不影子、⛔ 不寫使用者可見狀態 | `build_real_runtime` docstring |

## 2. 覆蓋來源（材料從哪來、各能證什麼）

| 材料 | 來源 | 能證 | 證不了 |
|---|---|---|---|
| koyu 422 句（五型各 83–85；可對映 gold 153 句） | `coverage-map/sources/koyu-v2-phrasings.json`＋`inputs/phrasing-selection-rule-20260906.json`（規則三項全等）；gold＝`inputs/koyu-article-map.json`（31 篇有 gold） | 真問法在「正本已覆蓋的 31 篇」上的候選命中與翻轉 | 其餘 51 篇 koyu 內容；**內文鍵是否只記住來源**（問句與正本內文同源） |
| 缺口地圖 55 格 76 句＋可答性標籤 | `coverage-map/map-v2.json`；`runs/2026-09-06T00-00-00Z/answerability-canon-v3.json`（answerable 37／partial 12／deliberate_no 5／no_source 1） | `deliberate_no`／`no_source` 6 格＝**gold 不在候選的對照組**（必須維持轉人） | 同源、只證已知講法（3.4 已標） |
| round9 topics 54 句（T-contract-create：46 問法＋8 邊界）兩輪×3 rep 實跑結果 | `eval/perf-agent-regression-20260905/round9-dsp033/r9{a,b}/topics.jsonl` | **唯一有跑前 agent 實跑結果的材料**：0/6 答到 17 句（可答卻沒答候選）、≥4/6 答到 10 句（已能答候選）；問法**不是** helpcenter／koyu 改寫（perf 逐字稿來源）⇒ 是「內文句只記住來源」命題的可用材料 | 只涵蓋合約建立一個主題（粗目 C）；gold 需人工標到細目 |
| sensitive-v1 30 題（五類各 ≥5） | `eval/sensitive-v1.json` | 敏感 0 漏 | — |
| scenarios-v1 6 劇本 23 turn | `eval/scenarios-v1.json` | 多輪（同一 state 貫穿）、跨粗目（S1 房東流 9 turn 橫跨帳務／合約／客戶數／導流） | 劇本題有 verbatim 欄標示是否原句 |
| round9「13 題」對照組 | ⛔ **查無清單**：`round9` 在 spec 三份文件只出現在引用句，`eval/` 與 `reviews/` 都沒有 13 題的列表（正對照：同一 grep 對 `round9` 命中 README 與 F11） | — | 本檔以「round9 0/6 與 ≥4/6 的 27 句」作對照組定義，取代「13 題」（§4.4a 待裁 1） |

## 3. 事實 vs 待裁

- 事實：`AGENT_TURN_SPEC` stage 只開 prospect ⇒ 本探針身分固定 `Identity(vendor_id=…, target_user="prospect", mode="b2b")`（`agent_eval.make_agent_identity`／`EVAL_MODE`）；`identity_source` 恆 `anonymous`（契約：prospect 不帶 role_id／user_id）⇒ R4.2「entry 不反問」在本探針**量不到**（無 entry 流量），只量 anonymous 側「一次一題、已知不重問」。
- 事實：`--candidates on` 真 provider 路徑每回合一次查詢 embedding（≤3 s 逾時），索引 358 鍵啟動一次；`off` 臂整份大綱（3.2 起為正本組裝，未過可見性——prospect 全可見故等價）。
- 待裁：見 `inputs/plan-4.4a-outline-probe-definition-20260907.md` §5。
