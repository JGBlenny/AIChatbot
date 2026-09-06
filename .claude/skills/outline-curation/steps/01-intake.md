# 步 1：intake

**輸入**：kb 列 JSON（呼叫端先匯出，腳本不讀 DB）、草稿 JSON、缺口地圖 JSON、既有正本 Markdown（選填）。
**輸出 schema**：`../schemas/intake.json`。
**形態**：腳本（`../scripts/intake.py`，決定性）。
**出口條件**：`intake.json` 產出且各輸入 `inputs_sha` 齊全；`object_under_test` 骨架的 `materials` 非空、`approved_by` 待業主填。
