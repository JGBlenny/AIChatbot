# 凍結驗收：本線文件整理與過時清理（2026-10-27）

> 業主核可：2026-10-27（AskUserQuestion 三題：九月檔「刪兩份、其餘轉紀錄」、他窗 4 份「列出過時點交那窗」、時機「X8 回來後併 E 收案」）。核可後規則與清單凍結，縮減需再核可。
> 增補（2026-10-27，業主核可）：業主問程式註解「像是這些 為什麼記錄在程式裡？」，再於 AskUserQuestion 選「併進這次文件整理一起清」⇒ 加 D-R4、C11。
> 類型：全為機制項（文件正確性），不宣稱使用者成效。

## 業主原話

「且相關的文件 因為還有一些任務還沒處理 都要整理清楚 方便後續處理銜接」
「過時 錯誤 內容也順便盤查清理」
「像是這些 為什麼記錄在程式裡？」（指程式註解裡的量測數字、沿革與 repo 外路徑）；選項「併進這次文件整理一起清」

## 規則

| ID | 可檢查條件 | 來源原話 | 範圍取捨 |
|---|---|---|---|
| D-R1 | 本線現行文件（HANDOFF、目標正本、MAP `#agentic-mcp`、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、`jgb-spec-structured-card-draft-20261019.md`、`issues-after-golive-20261015.md`）所寫現況與程式／容器／決策一致 | 「相關的文件…都要整理清楚」 | 紀錄（計畫、凍結清單、報告、決策列）不改；他窗 4 份不寫入（業主裁示） |
| D-R2 | 每一個未處理任務只在 HANDOFF 一張待辦表出現一次，每列有：項目、擋不擋上線、等誰、從哪接（檔案路徑） | 「還有一些任務還沒處理…方便後續處理銜接」 | — |
| D-R3 | 過時／錯誤陳述改正文、⛔ 附註或刪除線；`roadmap.md`、`m0-owner-steps.md` 刪除，引用處改 `git show <固定sha>:<path>`；`requirements.md`、`design.md`、`tasks.md`、`research.md`、`validation_gap.md` 在 MAP 改角色為紀錄、內文不改 | 「過時 錯誤 內容也順便盤查清理」 | 他窗 4 份只唯讀盤查，過時點附證據列進 HANDOFF 待辦、由該窗或業主決定 |
| D-R4 | `rag-orchestrator/services/` 下含「`jgb-archive`」「業主 YYYY-」「計畫 §」的 31 個 `.py` 檔（清單：`~/jgb-archive/arch-step3-20261018/docs-cleanup/code-comments/targets.txt`）：註解與 docstring 只留機制說明與「勿改回」理由（寫成會發生什麼錯）；量測數字、修正編號、裁示日期、計畫章節號、repo 外路徑、「第一版／本版」沿革移出；行為不變 | 「為什麼記錄在程式裡？」「併進這次文件整理一起清」 | 只動註解與 docstring；決策 ID（DSP-…）可留作依據；字串常數、提示詞、log 訊息不動；tests/ 不在範圍 |

## 驗收清單

| # | 規則 | 檢查 | 觀察點 | 證據 |
|---|---|---|---|---|
| C1 | D-R1 | HANDOFF 標題、§0、§2.1 的 E 狀態與 X8 結果一致；§3 容器 md5 等於 `docker exec aichatbot-rag-orchestrator md5sum /app/services/agent/runtime.py`；重建指令含 `-p aichatbot` 與 writelog | 檔案＋容器實查 | grep 與指令輸出 |
| C2 | D-R1 | MAP `#agentic-mcp` 的 E 驗收行寫 r6／E-R13／E14；新增本檔一行 | MAP | grep |
| C3 | D-R1 | 目標正本 §4 E 列狀態與收案結果一致 | 檔案 | grep |
| C4 | D-R1 | JGB 需求稿的上線範圍決策 ID、jgb2 commit 與日期為現況；未做事項移入 HANDOFF 待辦 | 檔案 | grep＋決策列對照 |
| C5 | D-R1 | `issues-after-golive-20261015.md` 每列逐一對碼：已修的刪列（依據寫決策 ID 或 commit）、未修的轉 HANDOFF 待辦 | 檔案＋程式 grep | 每列一條可重跑指令 |
| C6 | D-R2 | HANDOFF 待辦表每列四欄齊全；散落的待裁／待查（§2.3、§2.4、需求稿 §3、接口 B §6 擋上線題）都已併入或寫明來源 | HANDOFF | 逐列對照 |
| C7 | D-R3 | `roadmap.md`、`m0-owner-steps.md` 刪前 `git diff --quiet` 確認與 HEAD 相同；刪後 grep 兩檔名，現行文件只剩 `git show` 指標 | git＋grep | 指令輸出 |
| C8 | D-R3 | grep 舊結論原句與同義改寫（「起草中」「執行中」「c37bf502」「E-R12」「DSP-094」等），現行文件 0 命中；同指令對新結論有命中當正對照 | grep | 指令輸出 |
| C9 | D-R3 | 他窗 4 份的過時點附證據列在 HANDOFF 待辦，4 份檔 `git diff` 無本 session 改動 | git＋HANDOFF | 指令輸出 |
| C11 | D-R4 | 每檔改前改後 AST（去 docstring）相同，附正對照（故意改一個常數應判不同）；31 檔重 grep 三個樣式，剩下的每處寫明保留理由；移出的每句在移除帳本列出原文與它已在哪份紀錄（計畫、報告、決策）；全套單元測試失敗清單等於基準 `~/jgb-archive/arch-step3-20261018/e/unit-after-fix10.failed` | 程式＋單元測試 | AST 腳本輸出、grep、帳本、測試輸出 |
| C10 | 全部 | `bash .claude/canon-accept.sh` 在最終工作樹通過 | 指令 | 輸出 |

## 非目標

- 紀錄類檔不改寫（全域「文件衛生」第 3 條）。
- 他窗 4 份不寫入（業主 2026-10-27 裁示）。
- 九月 Kiro 檔內文不改（業主選「其餘轉紀錄」）。
