# 步 3：phrasing

**輸入**：`structure-proposal.json`、講法來源（幫助中心／問法正本）。
**輸出 schema**：`../schemas/phrasing-map.json`。
**形態**：腳本＋人審（相似細目只出待審清單，⛔ 不自動合併）。
**出口條件**：`phrasings[]` 每筆狀態為 `proposed`；`similar_pairs[]` 待人審裁決前不得視為已解決。
