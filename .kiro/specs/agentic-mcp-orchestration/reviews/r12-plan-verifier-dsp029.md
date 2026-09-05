# r12：DSP-029 引用指向來源句編號——plan-verifier（fresh，2026-09-05）

**判定：REVISE**（方向確認：優於「保留 quote＋最長公共子串修復」與「unit／quote 雙軌」）。

| # | 級 | 阻斷 | 處置（DSP-029 v2） |
|---|---|---|---|
| 1 | P0 | unit 標記無法在 `wrap_tool_data` 產生；大綱標題行與 `kb_search` 合併文字讓編號與 `Provenance.text` 錯位 | FIX：unit 只由 provenance 逐筆產生；大綱在 `outline.py` 逐節標記、標題不編號；工具在 runtime 於 `wrap_tool_data` 前生成；無 provenance 工具不標記 |
| 2 | P0 | 動 PromptAssembler 簽名撞 R11.5 白名單測試 | FIX：不動簽名，落點改 outline.py／runtime.py |
| 3 | P1 | 整句引文稀釋 `min_coverage_chars=4`，牆更弱 | FIX：片段側相對覆蓋率 0.5＋絕對下限 4（rules 1.3.0）；R4 三個真捏造句進 fixture |
| 4 | P1 | 政策文／鐵則／拒因回饋三處仍教抄 quote | FIX：三處同改；`rg quote` 驗收 |
| 5 | P1 | 驗收無反向尺、R1 42% 是假象 | FIX：拒因分佈落表；答到率以 R4 為基準；20 筆獨立抽審無據率 ≤ R4 基線（跑前先量） |
| 6 | P2 | DSP-021 ③ 的 source 容錯消失 | FIX：canonicalize 先跑；source 不存在 ⇒ SCHEMA 子成因單獨計數上限 5/162；兩種已知抄錯仍放行 |
| 7 | P2 | fixture 轉換規則缺、兩拒因不可達 | FIX：逐案規則＋新增 7 案；11 拒因覆蓋維持 |
| 8 | P2 | 標記可被抄進 text／來源文字可偽造標記 | FIX：來源 `[]` 轉全形；Verifier 掃 answer 標記樣式 ⇒ SCHEMA |
| 9 | P2 | `fact_class`／`handoff_reason` 的 `Field(description)` 會被覆寫丟掉 | FIX：說明留在覆寫字面；六處 description 非空測試 |
