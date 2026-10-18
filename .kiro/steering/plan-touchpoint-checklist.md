# 寫計畫前的接點盤查清單 Steering

> 由 spec **dev-workflow-hardening** D2 沉澱（2026-10-18）。做法照 Google 設計文件「Teams should standardize what these concerns are in their case.」（團隊自訂固定清單，原文存 `~/jgb-archive/devflow-20261018/sources/google-doc-best-practices.txt` 與 `google-design-docs.txt`）；下列八項是本專案依 W1／R2／R3 計畫審查退回紀錄自家歸納的，⛔ 不是 Google 所列項目。

**何時用**：任何會改 `rag-orchestrator/` 行為的計畫，送 `plan-verifier` 之前。

**怎麼用**：把下表複製進計畫，每項填「證據」欄（可 grep 的符號＋路徑，⛔ 行號當事實）或「不適用理由」欄，兩欄至少填一欄；送審 brief 附上整張表。

| # | 接點 | 要回答的問題 | 曾被退回的事例 | 證據（可 grep 的符號＋路徑） | 不適用理由 |
|---|---|---|---|---|---|
| 1 | 插入點 | 新邏輯插在哪個函式、哪個閘之前或之後？前後順序是不是既有契約？ | W1 r1「觸發插入點未定義」；R2 r1「插入點與 quick_replies 殘留」 |  |  |
| 2 | 狀態生命週期 | 新增或沿用的會話狀態何時建立、何時清除？要不要登記 `KEY_SPECS`？ | W1 security F6「生命週期須進 KEY_SPECS」 |  |  |
| 3 | 開關回退 | 開關關掉時，輸出格式與行為是否和改前逐位相同？strict schema 會不會因此改變？ | W1 r1 #5、r2 #1、r3 #6、r4 #1（off 不等於回到現行） |  |  |
| 4 | 計量與觀察紀錄 | trace、violation、`decision_snapshot`、用量計費會不會漏記或多記？ | R3 第 1 稿「trace 計數管道」 |  |  |
| 5 | 出口路徑 | 每條結束路徑（作答、追問、轉人、固定句）會不會被新邏輯繞過或改走？ | W1 r2 #6「非終結撤回與既有出口衝突」；r5 #2「接回路徑走不到」 |  |  |
| 6 | 鎖住原句的既有測試 | 哪些測試逐字鎖住要改的句子或行為？列出要同步改的測試 | R3 第 2 稿 #7「應列出會改的測試」 |  |  |
| 7 | 既有紀律與決議 | 與 `.claude/DECISIONS.md`、既有規則句（如「提問一律 `kind=ask`」）有沒有衝突？ | R3 第 2 稿 #2「頂層 kind 與提問規則衝突」；W1 r3 #4「改變現行行為」 |  |  |
| 8 | 受影響文件 | 改到的機制在哪些文件被描述？同一片一起更新（照 Google「Change your documentation in the same CL as the code change.」） | `faffb2b6` 前四份主要架構文件落後於程式 |  |  |

**判分規則（量測用）**：plan-verifier 的每條 REVISE Blocker，逐條判是否對得到上表八項之一，判定寫進該計畫的審查處置表；同一輪任一條對到即算「接點類輪」。
