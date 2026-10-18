# 計畫：補充鐵則進系統提示詞（R1，2026-10-18）

> 業主原話：「也 提示詞強調「只能依資料回答，不夠就說缺什麼」 試試看 ?」（2026-10-17，實驗）；「驗完先補鐵則那一片」（2026-10-18）。
> 驗收清單：`.kiro/specs/agentic-mcp-orchestration/acceptance-supplement-rule-r1-20261018.md`
> 前置：寫入流程 W1（含 W1b、W1c）驗證結束（不論是否已 commit，R1 只動 `agent_rules.py` 與測試，與 W1 擁有檔不重疊）。

## 0. 現況（已對碼）

| 事實 | 查證 |
|---|---|
| 補充鐵則只在評估 shim 測過，repo 內 0 筆 | `grep -rln '補充鐵則\|資料段沒寫的細節' rag-orchestrator/services rag-orchestrator/config`（0）；正對照 `ASK_TARGETS`（7 檔） |
| 實驗做法：shim 在 `SHIM_EXTRA_RULE=1` 時把下列文字接到**system 訊息末尾** | `~/jgb-archive/bedrock-eval-20261017/shim/bedrock_shim.py` `_EXTRA` |
| 實驗結果：gpt-oss low 錯誤 6.7%（6/90）→ 0%（0/60），正確 88.9% → 90.0%，沒作答 3/90 → 4/60 | `~/jgb-archive/bedrock-eval-20261017/prompt/RESULT.md` |
| W1 最終盲判（每批 6 誘餌）：gpt-oss 錯誤 3／30（P05、P29、P30 皆補資料段沒寫的細節）；gpt-6-luna 錯誤 0／30 | `~/jgb-archive/bedrock-eval-20261017/w1/judge/w1_rejudge_*` |
| 業者／租客的政策文是 `agent_rules._POLICY_TEXT_NON_PROSPECT`；售前 `_POLICY_TEXT` 為 5.1 凍結（測試鎖 ≤1584 字、`⛔`≤8） | `grep -n "def policy_provider" rag-orchestrator/services/agent/agent_rules.py`；`grep -rn "len(agent_rules._POLICY_TEXT) <= 1584" rag-orchestrator/tests/unit/agent/` |
| ⚠️ 歷史：提示詞越長，模型越傾向先轉人而不作答（DSP-028 回歸實測） | `agent_rules.py` 模組 docstring「長度上限」段 |

鐵則原文（逐字照實驗 `_EXTRA`）：
「【補充鐵則】回覆裡每一句都必須能在資料段找到對應的原文；資料段沒寫的細節（畫面位置、按鈕、步驟、例外、替代做法、數字）一律不補、不推測。資料段只能回答一部分時，就只回答那部分，並明說「資料裡沒有提到」其餘部分。」

## 1. 終點指標

| 指標 | 現值 | 預期 | 來源 |
|---|---|---|---|
| gpt-oss 知識題錯誤（盲判） | 3／30 | ≤1／60 | W1 重判 |
| gpt-6-luna 知識題錯誤 | 0／30 | ≤1／60（不退步） | 同上 |
| gpt-6-luna 知識題正確 | 26／30（86.7%） | ≥49／60（現值減 5pp） | 同上 |
| 兩模型「沒作答」 | A 3／30、B 2／30 | A ≤12／60、B ≤10／60（現值比例＋10pp） | 同上 |
| 資料不足時明說缺什麼（探針 N1、N2） | 未量 | 每模型 states_missing ≥4／6、無據斷言 0 | 驗收 #2(a) |

## 2. 做什麼

1. `agent_rules.py` 新增常數 `_SUPPLEMENT_RULE`（上列原文，不含 `⛔`），**只接在 `_POLICY_TEXT_NON_PROSPECT` 末尾**（業者／租客）；售前 `_POLICY_TEXT` 不動（5.1 凍結，且實驗只量業者身分）。
2. 不改 assembler 順序。⚠️ 實驗是接在整段 system 訊息末尾，repo 版是政策文末尾——位置不同，由驗收實測量效果。
3. 模組 docstring「長度上限」段補記本次加長與理由（業主要求、實驗證據），比照 2026-09-08 那次。
4. 單元測試：鐵則逐字在 `_POLICY_TEXT_NON_PROSPECT`、不在 `_POLICY_TEXT`；`_POLICY_TEXT` 長度與 `⛔` 計數不變。

## 3. 不做

- 售前（prospect）政策文：凍結，且無實測。
- 意圖判斷呼叫的系統句（W1b／W1c）：與作答無關。
- Verifier 規則、grounding 模式（DSP-040）。

## 4. 擁有檔案與執行

- 擁有：`rag-orchestrator/services/agent/agent_rules.py`、`rag-orchestrator/tests/unit/agent/` 新測試檔。
- 改動小（一個常數＋接一處＋測試），由主會話直接實作（理由：單檔、無判斷分岔，派工的重建成本高於本身）；實測與盲判由主會話；收尾 fresh verifier。

## 5. 驗收

見清單（5 項）。

## 6. 回退

`git revert` 該 commit；或刪除接在 `_POLICY_TEXT_NON_PROSPECT` 末尾的常數。

## 7. 預算與停點

- 0.6M token；Bedrock／OpenAI 實測約 2×(60＋18) 回合，< US$1。
- 停點：清單 #1～#5 任一項未過 ⇒ 停、回報。⛔ 在本片內移動鐵則位置、改 assembler 順序、改寫鐵則文字或依模型分岔——任何一項都要業主另裁（位置差異見 §2 第 2 點：repo 版在政策文末尾，其後仍有 `_agent_rules_text`、工具清單、大綱資料段、slots，`prompt_assembler.PromptAssembler.build`）。

## 8. 執行紀錄（2026-10-18）——觸發停點

- 業主核可（「核可、開始」）。主會話實作：`agent_rules._SUPPLEMENT_RULE`（與 shim `_EXTRA` 逐字相同，105 字）接在 `_POLICY_TEXT_NON_PROSPECT` 末尾；`tests/unit/agent/test_supplement_rule_r1_req.py`；政策文相關測試 152 條通過；全量失敗清單＝基線（`r1/pytest.txt`）。未 commit。
- 實測（`~/jgb-archive/bedrock-eval-20261017/r1/`；盲判 `r1/judge/`，4 批各 6 誘餌皆 6/6）：

| 驗收 | gpt-oss（B） | gpt-6-luna（A） |
|---|---|---|
| #1／#3 錯誤（≤1/60） | 2/60（W1 3/30）✗ | 0/60 ✓ |
| #1／#3 正確 | 55/60（≥48）✓ | 47/60（≥49）✗ |
| #2(b) 沒作答 | 3/60（≤10）✓ | 13/60（≤12；W1 3/30）✗ |
| #2(a) 探針 states_missing | 0/6 ✗ | 0/6 ✗ |
| #4 R／D | 3/3／3/3 ✓ | 3/3／3/3 ✓ |

- #2(a) 根因（原始輸出 `r1/shim_*.jsonl`）：資料完全不足時兩模型皆依既有政策選 `kind=handoff`、`handoff_reason=no_grounding`、`sentences` 空 ⇒ 系統固定轉人句；零查詢轉人再被出口閘 `handoff_without_lookup` 換成「想處理哪一件事？」。補充鐵則只規範「資料只能回答一部分」，不涵蓋「完全沒有資料」；gpt-oss 將「戶籍遷入」自報為 compliance 敏感（被 `sensitive_self_report_overridden` 推翻）。gpt-oss 唯一作答回合推論「未提供 Apple Pay」（無據）。
- gpt-6-luna 沒作答由 10% 升到 21.7%——與 `agent_rules.py` docstring 所記「提示詞越長越傾向轉人」一致。
- 依 §7 停點：⛔ 在本片內移動位置、改寫文字、依模型分岔；交業主裁決。
- 業主裁示（2026-10-18）：「撤回 R1，改做「查無就說缺什麼」」。已還原 `agent_rules.py`（`git restore`，差異只含 R1 的 15 行）並刪除 R1 測試檔；R1 未 commit。鐵則待「查無就說缺什麼」那一片測完後再評估是否一併上。
