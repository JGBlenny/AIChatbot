# 2026-10-19 本線文件改動全面核對：規則與驗收清單

對象：本工作線 2026-10-19 在工作樹裡、相對 `4bb48114` 的所有 Markdown 改動。本檔在核對開始前寫定、凍結。前一輪 W2 r4 文件核對見 `acceptance-docs-w2-r4-20261019.md`（verifier CONFIRMED，提出建議 A1～A5）。

## 一、業主原話

- 2026-10-19：「先幫我修改文件並驗證」。
- 2026-10-19：「照建議，一起驗」——回覆主視窗兩個問題：
  - (1) 今天其他未驗證的文件改動要不要一起驗；
  - (2) A1～A4 要不要照建議改（建議：A1～A4 改、A5 不動）。

## 二、規則

| ID | 可檢查條件 | 出處 | 讀法、收窄或放寬 |
|---|---|---|---|
| S-R0 | 核對範圍＝`git status` 中本線的 Markdown 改動與新檔（相對 `4bb48114`）：`.claude/DECISIONS.md`（DSP-092～096）、`.claude/MAP.md`、`.claude/decisions/DSP-092.md`、`HANDOFF-20261018.md`、`architecture-target-20261018.md`、第 3 步計畫與驗收清單的修改、`plan-period-parse-20261019.md`、`acceptance-period-parse-20261019.md`、`plan-truncation-w2-20261017.md`、`acceptance-truncation-w2-20261017.md`、`jgb-spec-structured-card-draft-20261019.md`、`acceptance-docs-w2-r4-20261019.md`、本檔。 | 「一起驗」 | 讀為前一輪報告「讀法 B」：今天所有未驗證的文件改動。他窗 4 份不在範圍內（業主指示不動）。 |
| S-R1 | A1～A4 依建議改好：(A1) W2 計畫的「本來也會完成」耗時與 token 區間、正常完成輸出的最高 token 數，與 `w2/run2/` 原始資料相符；(A2) 執行順序的出處指向真正記載順序的決策；(A3) W-R6 不再列在「業主原話」底下，改寫明來源；(A4) HANDOFF §6 工作樹清單與 `git status` 相符。A5 不動。 | 「照建議」 | 無。 |
| S-R2 | 範圍內文件引用的業主原話，和 transcript 逐字相同（允許省略換行與選項的「 (Recommended)」）；決策列的「業主」來源有對應的業主訊息。 | 「驗證」 | 無。 |
| S-R3 | 範圍內文件對程式、資料、commit、外部系統的事實陳述，和實際程式、檔案、git 或報告相符。 | 「驗證」 | 讀為逐句核對可查證的陳述；設計意圖與待裁事項不算事實陳述。 |
| S-R4 | 現行文件之間一致，沒有與現況相反的現行陳述；現行文件不以附註、刪除線、「已更正／已失效」保留舊內容。紀錄（有日期的報告、凍結清單、決策列、已實作的計畫）不改寫，但它們與現行文件的衝突要列出。 | 「修改文件並驗證」 | 依全域「文件衛生」節區分現行文件與紀錄。 |
| S-R5 | 範圍內文件引用的路徑都存在；新增或改角色的文件登在索引（MAP.md、HANDOFF 或目標正本）。 | 「修改文件」 | 無。 |

## 三、驗收清單

| # | 服務規則 | 觀察點 | 證據型態 |
|---|---|---|---|
| X1 | S-R1 | 重跑 `w2/run2/` 篩選，對照 W2 計畫的 393～1,999 token、3.8～16.4 秒、最高 1,999。`grep -n "A+、B 之後\|DSP-096"` 檢查 DECISIONS、HANDOFF、目標正本、W2 計畫。W2 計畫 §1.1 的 W-R6 句；HANDOFF §6 對照 `git status --short`。 | 指令輸出、原句 |
| X2 | S-R2 | 範圍內每段業主引句，對照 `~/.claude/projects/-Users-chenqinghuang-dev-work-AIChatbot/4326489a-336f-45d8-b078-933a38e1fdca.jsonl`（grep，⛔ 整檔讀）。 | 引句對照與行號 |
| X3 | S-R3 | 逐句核對可查證的陳述，包括：commit 號、程式符號與常數、測試檔、報告數字、容器與指令、DSP-092 的機制（`rag-orchestrator/services/agent/tools/confirm.py`）。JGB 需求稿的 jgb2 陳述以 jgb2 checkout 唯讀查（`~/dev/work/jgb2/` 下；先看分支，讀 master 用 `git show`）；查不完的寫「未查完」。 | 指令輸出、檔內位置 |
| X4 | S-R4 | 對範圍內現行文件 grep 與現況相反的陳述（例如「未 commit」與 git 不符、「待核可」對已核可、舊順序、舊出處），每個 grep 附正對照；列出紀錄與現行文件的衝突。 | grep 輸出 |
| X5 | S-R5 | 範圍內文件引用的每個 repo 與 `~/jgb-archive/` 路徑都用 `ls` 或 `test -e` 檢查，附正對照；新檔都有索引登錄。 | 指令輸出 |
| X6 | 全部 | fresh `verifier` 對照本檔與業主原話，判定為 CONFIRMED。分兩位：甲負責 JGB 需求稿、期別片計畫與驗收以外的檔；乙負責 JGB 需求稿、期別片計畫與驗收；跨檔一致性由甲負責。 | verifier 報告 |

## 四、非目標

- 他窗 4 份文件：業主指示不動。
- 程式改動本身的正確性：A 片已收案，期別片已有 verifier CONFIRMED。
- A+ 實作後才會過時的文件（AGENTIC_MCP_ARCHITECTURE 等）：排進 A+。
- 紀錄的內容：不改寫，例如 STEP0 把驅動資料的數字掛在重放句、期別片計畫「DSP-094 的順序」。只列出它們和現行文件的衝突。
