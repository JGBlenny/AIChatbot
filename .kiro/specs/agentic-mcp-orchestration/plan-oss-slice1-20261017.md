# 計畫：gpt-oss 第一片——輸出上限＋追問對象說明（2026-10-17，待業主核可）

> 業主原話（2026-10-17）：「先暫定 gpt-oss 去處理問題 38.7 秒 為什麼? 修繕有追問嗎 ?」「先做 1、2 再量 3」
> 驗收清單（核可即凍結）：`.kiro/specs/agentic-mcp-orchestration/acceptance-oss-slice1-20261017.md`
> 依據：`~/jgb-archive/bedrock-eval-20261017/v2/`（RESULT.md、RESULT-medium.md、repro_B.*、MED.*）

## 範圍
1. **輸出上限**：`runtime._next_model_message` 的 `chat.completions.create` 加 `max_completion_tokens`，值取 env `AGENT_MAX_COMPLETION_TOKENS`（預設 2000；非正整數 ⇒ 啟動即報錯，同 `AGENT_REASONING_EFFORT` 的 fail-loud 慣例）。`finish_reason == "length"` 時在 `violations` 記 `llm_output_truncated`（只記旗標，無內容）。被截斷的輸出照既有 SCHEMA 重寫／預算邏輯處理，⛔ 不另開出口。
   - 依據：gpt-oss 正常輸出 169 次 p99 1,408、最大 1,871；失控 12 次最小 2,793（灌空白換行至 8,192 上限，38～79 秒）。gpt-6-luna 正常最大 333。2000 攔得住全部失控、不截正常回答。
2. **追問對象說明**：`runtime._agent_output_response_format` 的 `ask_target` description 由 `output_schema.ASK_TARGETS` **程式產生**值域清單（⛔ 不另抄字面量），讓不讀 enum 的模型也看得到可填值。Verifier 的 `ask_target_invalid`（contract 類，照擋）與出口閘 `_apply_ask_target_gate` **一律不動**。
   - 依據：gpt-oss 推理原文「The allowed ask_target values? Not given explicitly」；現行 description 只寫「kind=ask 時必填」，值域只在 enum。
3. **量測報修全流程**（不改程式）：「能幫我新增一張修繕單嗎」→「學生獨立套房可租補」→「冷氣不冷」，看是否出確認卡（outcome=confirm_pending）。gpt-oss 與 gpt-6-luna 各 3 輪。結果決定是否加做「程式觸發 confirm.request」（另案）。

## 非目標（附理由）
- ⛔ Bedrock 正式接線、剝除 `<reasoning>`、金鑰設定（第二片，牽涉憑證，另做安全審查）。量測沿用評估用剝除層。
- ⛔ 剝除空白：JSON 解析本就容許空白，問題只在耗時，上限即解。
- ⛔ 程式依語意推斷 ask_target（屬詞表／語意補洞，違反「修法只修根層」）。
- ⛔ 放寬 Verifier 的 ask_target_invalid（業主 2026-09-09 T1 定的 fail-closed 契約）。
- ⛔ 部署正式機（另由業主裁示）。

## 改動檔案
- `rag-orchestrator/services/agent/runtime.py`（兩處）。
- `docker-compose.prod.yml`、`docker-compose.dev.yml`（宣告 `AGENT_MAX_COMPLETION_TOKENS`；`test_env_parity_req` 守）。
- 新增單元測試 `rag-orchestrator/tests/unit/agent/test_output_cap_and_ask_target_desc_req.py`。

## 驗證
- 全量單元：紅燈須與基準 9 條逐條相同（`~/jgb-archive/assistant-demo-20261014/red-baseline-s3.txt`）。
- 新測試＋變異（拿掉上限／改回固定 description 時要紅）。
- 實測（評估容器，替身 JGB）：見驗收清單。
- 完成後派 fresh verifier 對照驗收清單。

## 回退
單一 commit；回退＝revert。env 設大值（如 100000）即等同無上限。

## 預算與停點
約 0.5M tokens。停點：全量單元出現新紅燈且非本片造成以外的原因不明；或實測顯示 gpt-6-luna 退步（追問改變行為）⇒ 停下回報。

## 執行紀錄（2026-10-17）
- 業主核可（逐字）：「核可」。實作：runtime.py（上限、截斷旗標、ask_target 說明）、docker-compose.prod.yml（dev compose 依既有約定不宣告 AGENT_*，與上文「兩份 compose」不同）、新測試 9 條；變異 4 個皆紅並還原。
- 驗收（`acceptance-oss-slice1-20261017.md`；證據 `~/jgb-archive/bedrock-eval-20261017/s1/`）：
  - #1 **未過**：單次呼叫最大 2000（上限生效），但截斷後重寫使回合累計超過 2,000（P12 2125、P26 4000、P09 2204、P30 2153、R2/2 2112），這 4 個 P 回合最後轉人；最慢 26.7 秒 > 25 秒。
  - #2 **過**：gpt-6-luna 無截斷；盲判 24/30 correct、0 錯（誘餌 6/6）；v2 同題 82.2%。
  - #3 **未過**：兩步內 rnd2 R2 `ask_target_invalid` 轉人；rnd1 R2 回 kind=answer 又追問物件。
  - #4 量測：gpt-6-luna 3/3 confirm_pending；gpt-oss 0/3（只 1 次呼叫 confirm.request 且回缺欄）。
  - #5 **過**：全量 9 failed／4454 passed，失敗與基準逐條相同。
- fresh verifier：**CONFIRMED**（判定方向全部成立）；P3 兩條（#1 回合層級子條件、#3 引用範圍）已併入上列敘述。
- 結論：上限與說明保留；報修需「程式觸發 confirm.request＋程式帶入物件」（另案第二片）；截斷後重寫仍失控的處置併入第二片設計。
