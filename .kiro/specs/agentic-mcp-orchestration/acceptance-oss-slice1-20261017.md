# 驗收清單：gpt-oss 第一片（2026-10-17；業主核可後凍結）

計畫：`plan-oss-slice1-20261017.md`。業主原話：「先暫定 gpt-oss 去處理問題 38.7 秒 為什麼? 修繕有追問嗎 ?」「先做 1、2 再量 3」

| # | 對應業主字句 | 觀察點（業主使用的層） | 證據型態 | 通過條件 |
|---|---|---|---|---|
| 1 | 「38.7 秒 為什麼」→ 不再出現數十秒的失控回合 | 評估容器打 `/mcp agent.turn`（同 v2 設定，gpt-oss low），30 題×3 輪 | 每回合耗時與 completion tokens（`usage_events.decision_snapshot`） | 0 回合 completion > 2,000；最大耗時 ≤ 25 秒；若有截斷，trace 有 `llm_output_truncated` |
| 2 | 同上，不退步 | 同 1，gpt-6-luna 30 題×1 輪 | 同上＋盲判正確性 | 無截斷；正確率不低於 v2 同題結果 −10 個百分點 |
| 3 | 「修繕有追問嗎」→ 追問不再因 ask_target 漏填被退回 | 評估容器，gpt-oss，報修兩步×3 | 回覆文字、`verifier` 拒因 | 3 輪皆無 `ask_target_invalid`；第一句追問物件、第二句追問描述 |
| 4 | 「再量 3」→ 報修全流程三步 | 評估容器，gpt-oss 與 gpt-6-luna 各×3：「能幫我新增一張修繕單嗎」→「學生獨立套房可租補」→「冷氣不冷」 | outcome.state、tool_calls | **量測項，不設通過門檻**：照實回報每輪是否 confirm_pending、是否呼叫 confirm.request |
| 5 | 程式正確 | `scripts/run-tests.sh unit` | 測試輸出 | 紅燈與基準 9 條逐條相同；新測試綠；變異（拿掉上限、description 改回固定字串）紅 |

非目標（自業主字句收窄，附理由）：Bedrock 正式接線與金鑰（第二片，需安全審查）；部署正式機（另裁）；程式觸發 confirm.request（依第 4 項量測結果另案）。
