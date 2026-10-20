# W2 r4 文件核對：規則與驗收清單

對象：2026-10-19 下午改動、尚未經 verifier 確認的 W2 相關文件。本檔在核對開始前寫定、凍結。

## 一、業主原話

- 2026-10-19：「先幫我修改文件並驗證」——回應主視窗揭露「W2 計畫 r4、W2 驗收清單、HANDOFF-20261018 的 W2 那一行、目標正本 §4 的 W2 列，都未驗證」。
- 被核對文件所依據的原話：DSP-094「同意」、DSP-095 四項選擇、W2 r4「核可 r4 (Recommended)」（原文見 `.claude/DECISIONS.md` DSP-094、DSP-095 列與 `acceptance-truncation-w2-20261017.md` 第一節）。

## 二、規則

| ID | 可檢查條件 | 出處 | 讀法、收窄或放寬 |
|---|---|---|---|
| D-R0 | 核對範圍＝`plan-truncation-w2-20261017.md`、`acceptance-truncation-w2-20261017.md`、`HANDOFF-20261018.md`（W2 相關句）、`architecture-target-20261018.md` §4（W2 列與順序句）、`.claude/DECISIONS.md` DSP-093～095 列、`.claude/MAP.md` 決策列。 | 「文件」 | 讀為主視窗上一則揭露「未驗證」的那幾份，加上同一批改動牽動的決策紀錄與索引。主視窗的讀法，業主未另行核可。 |
| D-R1 | 計畫與驗收檔引用的業主原話，和業主實際說的逐字相同；規則沒有違反或擴大原話（偏離處有寫明）。 | 「驗證」 | 無。 |
| D-R2 | 收尾審查的兩條 REVISE 確實已在計畫正文修好：(a) 獨占範圍涵蓋「之後才加入快照的檔案」；(b) 1-0 重現門檻寫明「＋5 秒」，與 C9 同一門檻。 | 「驗證」 | 無。 |
| D-R3 | 計畫、驗收檔、DSP-094／095 引用的每個數字，都能在所指的來源找到，且數值相同。 | 「驗證」 | 無。 |
| D-R4 | 現行文件之間對 W2 的狀態與做法一致；沒有和 r4 相反的現行陳述；現行文件沒有用附註、刪除線、「已更正／已失效」保留舊內容（決策紀錄的「被 DSP-xxx 取代」標記除外）。 | 「修改文件」 | 讀為發現不一致就改正文。 |
| D-R5 | 這幾份文件引用的路徑（repo 內與 `~/jgb-archive/` 下）都存在；新增或改角色的文件有登在索引（MAP.md、HANDOFF 或目標正本）。 | 「修改文件」 | 無。 |

## 三、驗收清單

| # | 服務規則 | 觀察點 | 證據型態 |
|---|---|---|---|
| V1 | D-R1 | 將計畫與驗收檔第一節的業主引句，和 session transcript `~/.claude/projects/-Users-chenqinghuang-dev-work-AIChatbot/4326489a-336f-45d8-b078-933a38e1fdca.jsonl` 中業主訊息與 AskUserQuestion 回答逐字比對；並逐條檢查 W-R0～W-R9 的「讀法」欄，確認偏離都有寫明。 | grep 輸出、引句對照 |
| V2 | D-R2 | 計畫 §4 第 1-0 項有「＋5 秒」；計畫的獨占或回退段明寫涵蓋之後加入快照的檔案，且 `w2.patch` 檔案清單須等於實際改動的檔案。 | 檔內位置、原句 |
| V3 | D-R3 | 下列數字逐一對到來源：STEP0（`~/jgb-archive/arch-step3-20261018/w2/STEP0.md`）的 12/30、28/60、1/24、57/60、33/60、15/227、10,933、2,293、1,931、p50 1.23／最慢 2.47 秒、353 筆中 17 筆（K200 19、K2000 16）、正常主呼叫 126 筆 p95 2.63 秒、90 秒與 607 秒；`ra/report-ra.md` §2 的 K 14/20；`period/report-period.md` §5 的延期 11/12；`w2/run2/e2a_P.log` 的 60 回合、轉人 0、`TOOL_TIMEOUT` 1；道謝 run2 轉人或失敗 4/30；`ra/report-ra.md` §8 的 8 場與 6 場；程式 `_AGENT_TURN_OUTER_MARGIN_S = 5.0`（`rag-orchestrator/services/agent/mcp_facade.py`）、`DEFAULT_MAX_COMPLETION_TOKENS` 為 2000。 | 來源檔原句或指令輸出 |
| V4 | D-R4 | grep 範圍內現行文件中與 r4 相反的陳述（關鍵詞含「乾淨重試」「另案」「待核可」「r3」「草稿」及同義寫法），附正對照（同一指令要命中 r4 的現行句）；比對 HANDOFF W2 行、目標正本 §4 W2 列與順序句、DSP-095 內容三者一致。 | grep 輸出 |
| V5 | D-R5 | 列出這幾份文件引用的每個路徑並逐一 `ls`（附一個已知存在的正對照）；確認 MAP 決策列含 DSP-095、本檔登在 HANDOFF。 | 指令輸出 |
| V6 | 全部 | fresh `verifier` 對照本檔與業主原話，判定為 CONFIRMED。 | verifier 報告 |

## 四、非目標

- A+ 會讓其過時的文件（`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 模型自呼 `confirm.request` 段、`requirements.md` R4.2、`mcp-facade.md` 工具表）：現在描述的是程式實況，A+ 實作前改會變成錯的；排進 A+ 計畫。
- CANON 提示的 249 份未指派 Markdown：與本次改動無關。
- 他窗 4 份文件（`deploy-and-online-test-guide-20261015.md`、`jgb-acceptance-checklist-20261015.md`、`jgb2-api-requests.md`、`docs/deployment-runbook.md`）：業主指示不動。
- 程式改動（A 片、期別片）：不在本次核對範圍；期別片已另有 verifier CONFIRMED。
