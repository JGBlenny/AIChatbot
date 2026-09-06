# 步 4：answerability

**輸入**：`phrasing-map.json`。
**輸出 schema**：`../schemas/answerability.json`。
**形態**：Workflow 判者（1.4 實作）——每格 2 判者、不一致加第 3，`deterministic=false`，原始輸出留 `../journal/`。
**出口條件**：`needs_rubric_revision=false`（為 `true` 時 Stop hook 擋）；成本落在步 4 上限（≤180 代理／$3）內。
