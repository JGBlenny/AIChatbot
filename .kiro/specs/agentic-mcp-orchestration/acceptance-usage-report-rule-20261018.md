# 驗收清單：計畫預算改為回報實際用量（全域 CLAUDE.md＋記憶，2026-10-18，凍結）

業主原話：「預算的部分我覺得有點沒有? 我看不出來哪次有作用的」；選「拿掉 token 上限，改回報實際用量」（選項原文：「計畫不再寫 token 上限當停點；每片收尾回報子代理實際用量（從任務通知加總）與模型 API 費用；停點只用看結果的條件（實測未過、審查兩次退回）。需更新全域規則中 Plan 必備欄位的 budget 與舊記憶。」）。

| # | 對應業主字句 | 宣稱 | 觀察點 | 通過條件 |
|---|---|---|---|---|
| 1 | 「拿掉 token 上限」 | Plan 必備欄位不再有 budget，明文禁止 token 上限當停點 | `~/.claude/CLAUDE.md` Plan gate 一句 | 該句含 `usage report`、不含 `budget`；含「⛔ token caps as stop conditions」 |
| 2 | 「改回報實際用量」 | 定義回報內容與時點 | 同上 | 寫明「子代理 token 由任務通知加總＋模型／API 費用，於每片收尾回報」 |
| 3 | 「停點只用看結果的條件」 | 停點不再含預算 | 同上 | 寫明停點只用結果條件；Recovery 段「exhausted budget/quota」指外部額度／授權，非 token 上限（並存不衝突） |
| 4 | 「更新舊記憶」 | 舊記憶改寫成新規則、索引同步 | `memory/feedback_budget_estimate_fixed_overhead.md`、`memory/MEMORY.md` | 記憶本文為新規則並附 Why（含業主原話）；索引行描述新規則；無殘留「上限一次定實」作為現行規則 |
| 5 | — | 其他節未被改動 | `~/.claude/CLAUDE.md` 與改動前快照比對 | 除 Plan gate 該句與「設計方法」節外，其他節逐字不變 |
