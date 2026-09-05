# r10：DSP-028 逐句陣列契約——plan-verifier（fresh，2026-09-05）

**判定：REVISE**（方向確認優於替代方案「Verifier 容忍句數不等再對齊」——後者猜錯方向是放行）。

| # | 阻斷 | 處置 |
|---|---|---|
| 1 | 片段繼承 kind 卻未規定逐片段複核 ⇒ 疑問句夾斷言可整筆免引用（r2 安全審第 10 條病灶重開） | **FIX**：每片段各自跑 `_effective_kind` 與步③～④，比對用片段本文；新 fixture「fact＋question 同一筆、kind=question、cite=[]」須拒 UNCITED_ASSERTION，正對照「同筆只留問句」放行 |
| 2 | `sentences=[]` 且非 handoff ⇒ 空回覆全過 | **FIX**：步②加 SCHEMA；正對照 handoff＋合法 reason 放行 |
| 3 | `prompt_assembler.py` 引用鐵則段仍教 `sentence_map` | **FIX**：納入範圍；`rg sentence_map services/` 零命中為驗收 |
| 4 | design 元件 6 `AgentOutput` 同時有 `answer` 與 `sentences`、`Sentence` 未定義 | **FIX**：已收斂（1.4.10 標註、`Sentence` 定義、`SentenceCite` 刪除線） |
| 5 | `VerifierVerdict.sent` 語義未定 | **FIX**：`sent`＝筆索引；`trace_view` 改「筆次」；`agent_rules` 告知模型 |
| 6 | 驗收單邊只量「拒得少」 | **FIX**：四尺同列（budget_exhausted ≤20/162、forbid_hit ≤3/162、敏感 0 漏、self_test 全綠），任一退步即停；`budget_exhausted` 來源＝`topics.jsonl` `handoff_reason`；eval 加 `verifier_reasons`／`budget_exhausted_n` |
| 7 | 動反捏造閘門卻無本次安全審 | **FIX**：派唯讀 security-reviewer 審「步②逐句→逐筆＋片段繼承」，findings 與處置寫入 DSP-028 |

P3（採納）：`sentence_map==[]`⇒`sentences:[]`；SCHEMA 三種拒因各留 fixture；requirements 引用契約行與 design 時序圖已改；handoff 時 `sentences` 可空並寫進 `agent_rules`。

修訂後 Plan 正本：`.claude/DECISIONS.md` DSP-028（v2）。
