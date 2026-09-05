# r19：DSP-033 v5 closing（fresh plan-verifier，2026-09-05）

**判定：REVISE**（第二次 ⇒ 處置後 epoch 2、只開一次 closing）。五條皆為字面一致性：

| # | 級 | 阻斷 | 處置（v6） |
|---|---|---|---|
| 1 | P1 | 驗收⑧／P1-2 仍寫 ≥2，與 F-1 裁定 1/3 相反 | FIX：1/3；一句移 fabrications、兩句留 open 標盲點 |
| 2 | P1 | ③④基線單輪與併池並存 | FIX：併池 63/324、33.0%，2 輪合併 |
| 3 | P1 | ②門檻 13% vs 10%、「抓到>現行」無量法 | FIX：≤10%（F-1）；同批盲標 ×2、現行規則離線重算同批抓到率 |
| 4 | P2 | floor／窄化極性的拒因代碎與「僅供降級」矛盾 | FIX：沿用 QUOTE_NOT_COVERING／POLARITY_MISMATCH 代碼並收窄語義；驗收①三者分列 |
| 5 | P2 | 逾時 1.5 s 與對數×400 ms 並存 | FIX：唯一公式 對數×400 ms、上限 12 對 |
P3：`min_coverage_ratio` 移除、rules 1.4.0；F-14 不通過去向；F-16 → tasks 5.9。
