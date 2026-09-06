# 步 5：reweigh

**輸入**：`answerability.json`。
**輸出 schema**：`../schemas/coverage-reweigh.json`。
**形態**：腳本（`reweigh.py`，呼叫 `tools/gapmap/coverage_map.py` 重量，決定性）。
**出口條件**：每格皆有去向欄；無去向格數＝0。
**下一步**：`coverage-map.json` 有 not_available／owner_decision 格 ⇒ 先走 [步 5b](05b-source-audit.md)，⛔ 不得直接交業主。
