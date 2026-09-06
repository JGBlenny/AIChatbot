# 步 2：structure

**輸入**：`intake.json`。
**輸出 schema**：`../schemas/structure-proposal.json`。
**形態**：Workflow 判者（1.4 實作）——3 角度（使用者提問路徑／內容邊界／受眾層級）fan-out 後合成，`deterministic=false`，原始輸出留 `../journal/`。
**出口條件**：三角度提案齊全、人審合成後的 `synthesis` 欄非空；成本落在步 2 上限（≤6 代理／$0.5）內，否則 `cost_ledger.py` 擋。
