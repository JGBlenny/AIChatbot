# r14：DSP-029 v3 closing review（fresh plan-verifier，2026-09-05）

**判定：REVISE**（第二次自動 REVISE ⇒ 主 session 全數處置、記 readiness epoch 2、只開一次 closing；再 REVISE 即暫停交業主）。

| # | 級 | 阻斷 | 處置（v4） |
|---|---|---|---|
| B1 | P1 | 標記格式三套並存（`[source#i]`／全形轉義＋`#` 正則／nonce＋`§`） | FIX：P0-1 與 P2-3 改寫為 r13#2 唯一版本；design 1.4.11 同步 |
| B2 | P1 | 大綱標記落在 `_build_doc` 拿不到 nonce、撞 sha／快取 | FIX：`_build_doc` 產物未標記；標記在 `PromptAssembler.build` 以 `outline.sections`＋既有 `nonce` 參數生成（簽名不動） |
| B3 | P1 | `known_open` 三句與「⇒ QUOTE_NOT_COVERING」互斥、無存放檔 | FIX：新檔 `known_open.json`（`expect_ok=True`、`known_open:true`），驗收⓪單列通過數 |
| P2 | — | 既有 fixture `quote`→`(source,unit)` 無通則 | FIX：通則寫入 P2-2 |
| P3 | — | 六處 description 測試遺漏；design 標「v2」 | FIX |
