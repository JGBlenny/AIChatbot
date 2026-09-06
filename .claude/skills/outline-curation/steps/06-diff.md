# 步 6：diff

**輸入**：新舊正本 Markdown、`id_map` JSON。
**輸出 schema**：`../schemas/diff-report.json`＋`../schemas/cost.json`。
**形態**：腳本（`../scripts/diff_report.py`＋`../scripts/cost_ledger.py`，決定性）。
**出口條件**：`replacements[]` 每筆 `how` 落在 `content|merged_into|phrasing_only`；狀態檔 `diff_report`／`cost` 鍵已寫入；G4 獨立驗證——宣稱數字（成本、差異筆數）一律派 fresh verifier。缺 `id_map` ⇒ `diff_report.py` exit 2。
