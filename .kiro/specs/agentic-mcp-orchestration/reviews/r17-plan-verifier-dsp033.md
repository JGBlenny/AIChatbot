# r17：DSP-033 NLI 取代覆蓋＋極性——plan-verifier（fresh，2026-09-05）

**判定：REVISE**（P1 ×3、P2 ×9）。技術十條處置寫入 DSP-033 v2；P2-8（τ 選法偏離凍結判準）、P2-9（「取代」與 DSP-031「追加不取代」矛盾）**待業主裁**。

| # | 級 | 阻斷 | 處置 |
|---|---|---|---|
| P1-1 | P1 | 同步 HTTP 阻塞事件迴圈 | FIX：可 await；驗收加舊鏈 p95 不退步 |
| P1-2 | P1 | 自證／fixture 未納入；known_open 與驗收⑧衝突；無 client 注入縫 | FIX：必填注入、雙模式假 client、known_open 兩句移 fabrications |
| P1-3 | P1 | 掛 semantic-model 無記憶體預算與併發隔離 | FIX：獨立 `nli-model` 容器 1 GB limit、rerank 不退步尺 |
| P2-4 | P2 | 8002 對主機發佈 ⇒ 打掛即降級 | FIX：不發佈埠／綁 127.0.0.1 |
| P2-5 | P2 | 批次＋可設執行緒破壞決定性 | FIX：threads=1、逐對、4 位量化＋測試 |
| P2-6 | P2 | 驗收②單位錯（FDR vs 誤殺率） | FIX：回凍結定義、盲化標註 |
| P2-7 | P2 | ③④基線取單輪較好者 | FIX：R6/R7 併池、跑 2 輪合併 |
| P2-8 | P2 | τ 偏離凍結判準 | **待業主** |
| P2-9 | P2 | 與 DSP-031 矛盾未標 supersede | **待業主** |
| P2-10 | P2 | 權重執行期下載、sha 無期望值 | FIX：隨映像＋期望 sha |
| P2-11 | P2 | 範圍漏 output_schema 與四鏡射端 | FIX：補列 |
| P2-12 | P2 | ⑥量法未定 | FIX：run_turn 邊界、report 欄位 |

CONFIRMED：引文仍由程式解析、NLI 只判蘊涵；降級不開敏感出口；entail_score 合封閉欄位紀律；三個替代方案皆有離線依據。
